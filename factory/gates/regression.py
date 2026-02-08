"""Regression gates for comparing face-swap output against golden references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from watserface.studio.quality_checker import QualityChecker


@dataclass
class RegressionResult:
    ssim_to_golden: float
    lpips_to_golden: Optional[float]
    within_tolerance: bool


class RegressionGate:
    """Compares a face-swap output image to a golden reference."""

    def __init__(self) -> None:
        self._checker: Optional[QualityChecker] = None
        self._lpips_metric = None

    @property
    def checker(self) -> QualityChecker:
        if self._checker is None:
            self._checker = QualityChecker()
        return self._checker

    @staticmethod
    def _to_tensor(img: np.ndarray):
        """Convert BGR uint8 numpy image to NCHW float32 torch tensor in [0, 1]."""
        import torch

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        t = torch.from_numpy(rgb).float() / 255.0
        return t.permute(2, 0, 1).unsqueeze(0)

    def _compute_lpips(self, img1: np.ndarray, img2: np.ndarray) -> Optional[float]:
        """Compute LPIPS between two images, returning None if pyiqa unavailable."""
        if self._lpips_metric is None:
            try:
                import pyiqa
                self._lpips_metric = pyiqa.create_metric('lpips')
            except ImportError:
                return None

        try:
            return float(self._lpips_metric(self._to_tensor(img1), self._to_tensor(img2)))
        except Exception:
            return None

    def compare_to_golden(
        self,
        output_path: str,
        golden_path: str,
        tolerance: float = 0.05,
    ) -> RegressionResult:
        """Compare output image to golden reference.

        Parameters
        ----------
        output_path:
            Path to the face-swap output image.
        golden_path:
            Path to the golden reference image.
        tolerance:
            Maximum allowed SSIM deviation from 1.0.
            ``within_tolerance = ssim >= (1.0 - tolerance)``.

        Returns
        -------
        RegressionResult with SSIM, optional LPIPS, and pass/fail flag.
        """
        output_img = cv2.imread(output_path)
        golden_img = cv2.imread(golden_path)

        if output_img is None:
            raise FileNotFoundError(f'Could not read output image: {output_path}')
        if golden_img is None:
            raise FileNotFoundError(f'Could not read golden image: {golden_path}')

        ssim = self.checker.compute_ssim(output_img, golden_img)
        lpips_val = self._compute_lpips(output_img, golden_img)
        within = ssim >= (1.0 - tolerance)

        return RegressionResult(
            ssim_to_golden=ssim,
            lpips_to_golden=lpips_val,
            within_tolerance=within,
        )
