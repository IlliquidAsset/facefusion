"""Metric gates for evaluating face-swap quality against assertions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

from factory.identity import compute_identity_similarity
from factory.scenarios.schema import MetricAssertion
from watserface.studio.quality_checker import QualityChecker


@dataclass
class GateResult:
    metric_name: str
    expected_operator: str
    expected_value: float
    actual_value: float
    passed: bool


_OPERATOR_FNS = {
    '>=': lambda actual, expected: actual >= expected,
    '<=': lambda actual, expected: actual <= expected,
    '>': lambda actual, expected: actual > expected,
    '<': lambda actual, expected: actual < expected,
    '==': lambda actual, expected: abs(actual - expected) < 0.0001,
    '!=': lambda actual, expected: abs(actual - expected) >= 0.0001,
}

SUPPORTED_METRICS = frozenset({
    'ssim', 'psnr', 'identity_similarity', 'blur_score',
    'artifact_score', 'lpips', 'overall_score',
})


class MetricGate:
    """Evaluates face-swap output frames against metric assertions."""

    def __init__(self) -> None:
        self._checker: Optional[QualityChecker] = None
        self._lpips_metric = None  # lazy pyiqa metric

    @property
    def checker(self) -> QualityChecker:
        if self._checker is None:
            self._checker = QualityChecker()
        return self._checker

    def _get_lpips_metric(self):
        """Lazily initialise pyiqa LPIPS metric."""
        if self._lpips_metric is None:
            try:
                import pyiqa
                self._lpips_metric = pyiqa.create_metric('lpips')
            except ImportError:
                self._lpips_metric = None
        return self._lpips_metric

    @staticmethod
    def _to_tensor(img: np.ndarray):
        """Convert BGR uint8 numpy image to NCHW float32 torch tensor in [0, 1]."""
        import torch

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        t = torch.from_numpy(rgb).float() / 255.0
        return t.permute(2, 0, 1).unsqueeze(0)

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------

    def _compute_metric(
        self,
        metric: str,
        source_frame: np.ndarray,
        target_frame: np.ndarray,
        result_frame: np.ndarray,
        source_embedding: Optional[np.ndarray],
        result_embedding: Optional[np.ndarray],
    ) -> float:
        if metric == 'ssim':
            return self.checker.compute_ssim(target_frame, result_frame)

        if metric == 'psnr':
            return self.checker.compute_psnr(target_frame, result_frame)

        if metric == 'identity_similarity':
            if source_embedding is None or result_embedding is None:
                return 0.0
            return compute_identity_similarity(source_embedding, result_embedding)

        if metric == 'blur_score':
            return self.checker.compute_blur_score(result_frame)

        if metric == 'artifact_score':
            return self.checker.compute_artifact_score(result_frame)

        if metric == 'lpips':
            lpips_fn = self._get_lpips_metric()
            if lpips_fn is None:
                return float('nan')
            return float(lpips_fn(self._to_tensor(target_frame), self._to_tensor(result_frame)))

        if metric == 'overall_score':
            metrics = self.checker.compute_metrics(
                source_frame, target_frame, result_frame,
                source_embedding, result_embedding,
            )
            return metrics.overall_score

        raise ValueError(f'Unsupported metric: {metric!r}. Supported: {SUPPORTED_METRICS}')

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        source_frame: np.ndarray,
        target_frame: np.ndarray,
        result_frame: np.ndarray,
        source_embedding: Optional[np.ndarray],
        result_embedding: Optional[np.ndarray],
        assertion: MetricAssertion,
    ) -> GateResult:
        """Evaluate a single metric assertion and return a GateResult."""
        actual = self._compute_metric(
            assertion.metric,
            source_frame, target_frame, result_frame,
            source_embedding, result_embedding,
        )

        op_fn = _OPERATOR_FNS.get(assertion.operator)
        if op_fn is None:
            raise ValueError(f'Unsupported operator: {assertion.operator!r}')

        passed = op_fn(actual, assertion.value)

        return GateResult(
            metric_name=assertion.metric,
            expected_operator=assertion.operator,
            expected_value=assertion.value,
            actual_value=actual,
            passed=passed,
        )

    def evaluate_all(
        self,
        source_frame: np.ndarray,
        target_frame: np.ndarray,
        result_frame: np.ndarray,
        source_embedding: Optional[np.ndarray],
        result_embedding: Optional[np.ndarray],
        assertions: List[MetricAssertion],
    ) -> List[GateResult]:
        """Evaluate a list of metric assertions, returning results for each."""
        return [
            self.evaluate(
                source_frame, target_frame, result_frame,
                source_embedding, result_embedding, a,
            )
            for a in assertions
        ]
