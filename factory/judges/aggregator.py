"""Statistical aggregation for multi-sample LLM judge evaluations."""

import logging
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from factory.judges.prompts import DIMENSIONS
from factory.judges.vision_judge import JudgeResult, VisionJudge

logger = logging.getLogger(__name__)


@dataclass
class AggregatedJudgment:
    """Aggregated result from multiple LLM judge evaluations."""

    medians: Dict[str, float]
    means: Dict[str, float]
    stds: Dict[str, float]
    passed: Dict[str, bool]
    unreliable_dimensions: List[str]
    all_results: List[JudgeResult]
    skipped: bool = False


def aggregate_judgments(
    results: List[JudgeResult],
    thresholds: Optional[Dict[str, float]] = None,
) -> AggregatedJudgment:
    """Aggregate multiple judge results into statistical summaries.

    Args:
        results: List of individual :class:`JudgeResult` instances.
        thresholds: Per-dimension minimum median to pass.
            Dimensions not listed default to ``passed=True``.

    Returns:
        An :class:`AggregatedJudgment` with medians, means, stds, and pass/fail.
    """
    if thresholds is None:
        thresholds = {}

    valid = [r for r in results if not r.skipped]

    if not valid:
        logger.warning("All judge results were skipped — returning skipped aggregate")
        return AggregatedJudgment(
            medians={},
            means={},
            stds={},
            passed={},
            unreliable_dimensions=[],
            all_results=results,
            skipped=True,
        )

    medians: Dict[str, float] = {}
    means: Dict[str, float] = {}
    stds: Dict[str, float] = {}
    passed: Dict[str, bool] = {}
    unreliable: List[str] = []

    for dim in DIMENSIONS:
        values = [
            float(r.scores[dim]) for r in valid if dim in r.scores
        ]
        if not values:
            continue

        med = statistics.median(values)
        mean = statistics.mean(values)
        std = statistics.pstdev(values)  # population stdev (no n-1 correction)

        medians[dim] = med
        means[dim] = mean
        stds[dim] = std

        if std > 2.0:
            unreliable.append(dim)

        if dim in thresholds:
            passed[dim] = med >= thresholds[dim]
        else:
            passed[dim] = True

    logger.info(
        "Aggregated %d valid results (%d skipped, %d unreliable dims)",
        len(valid),
        len(results) - len(valid),
        len(unreliable),
    )

    return AggregatedJudgment(
        medians=medians,
        means=means,
        stds=stds,
        passed=passed,
        unreliable_dimensions=unreliable,
        all_results=results,
    )


def run_aggregated_judgment(
    judge: VisionJudge,
    source_path: str,
    output_path: str,
    n_samples: int = 3,
    thresholds: Optional[Dict[str, float]] = None,
) -> AggregatedJudgment:
    """Run the judge multiple times and aggregate the results.

    Args:
        judge: A :class:`VisionJudge` instance.
        source_path: Path to source identity image.
        output_path: Path to face-swapped output image.
        n_samples: Number of evaluation runs.
        thresholds: Per-dimension minimum median to pass.

    Returns:
        An :class:`AggregatedJudgment` with statistical summaries.
    """
    if thresholds is None:
        thresholds = {}

    results: List[JudgeResult] = []
    for i in range(n_samples):
        logger.info("Running judge evaluation %d/%d", i + 1, n_samples)
        result = judge.evaluate(source_path, output_path)
        results.append(result)

        # Short-circuit: if first result is skipped for systemic reason, don't retry
        if result.skipped and i == 0:
            logger.info("First evaluation skipped — aborting remaining samples")
            break

    return aggregate_judgments(results, thresholds)
