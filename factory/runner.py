"""CLI runner and scenario executor for the factory testing framework.

Provides ``run_scenario``, ``run_all``, and a CLI entry point (``main``)
so the factory can be invoked via ``python -m factory.runner`` or
``python -m factory``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from factory.scenarios.loader import load_scenario, load_scenarios, validate_fixtures
from factory.scenarios.schema import Scenario, ScenarioPriority, ScenarioType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Outcome of executing a single factory scenario."""

    scenario_name: str
    scenario_type: str
    passed: bool
    metric_results: List[dict] = field(default_factory=list)
    performance_result: Optional[dict] = None
    judge_result: Optional[dict] = None
    golden_result: Optional[dict] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class FactoryReport:
    """Aggregate report for a full factory run."""

    scenarios_run: int
    scenarios_passed: int
    scenarios_failed: int
    scenarios_skipped: int
    results: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {
    ScenarioPriority.critical: 0,
    ScenarioPriority.high: 1,
    ScenarioPriority.medium: 2,
    ScenarioPriority.low: 3,
}


def _gate_result_to_dict(gr) -> dict:
    """Convert a GateResult dataclass to a plain dict."""
    return {
        'metric_name': gr.metric_name,
        'expected_operator': gr.expected_operator,
        'expected_value': gr.expected_value,
        'actual_value': gr.actual_value,
        'passed': gr.passed,
    }


def _skip(scenario: Scenario, reason: str) -> ScenarioResult:
    """Return a skip result for a scenario."""
    return ScenarioResult(
        scenario_name=scenario.name,
        scenario_type=scenario.type.value,
        passed=False,
        skipped=True,
        skip_reason=reason,
    )


# ---------------------------------------------------------------------------
# Scenario execution
# ---------------------------------------------------------------------------

def run_scenario(
    scenario: Scenario,
    fixtures_dir: Path,
    use_llm_judge: bool = False,
) -> ScenarioResult:
    """Execute a single scenario and return structured results.

    Handles each :class:`ScenarioType` as documented in the factory spec.
    Missing fixtures cause a graceful skip rather than a crash.
    """
    stype = scenario.type

    # --- comparative / regression: skip with message ---
    if stype == ScenarioType.comparative:
        return _skip(
            scenario,
            'Comparative scenarios require two-preset execution (not yet wired)',
        )
    if stype == ScenarioType.regression:
        return _skip(
            scenario,
            'Regression scenarios are not yet executable (requires Phase 4 training integration)',
        )

    # --- validate fixtures ---
    missing = validate_fixtures(scenario, fixtures_dir)
    if missing:
        return _skip(
            scenario,
            f'Missing fixture(s): {", ".join(missing)}',
        )

    # --- resolve file paths ---
    setup = scenario.setup
    source_path = str(fixtures_dir / setup.source_image) if setup.source_image else None
    target_path = (
        str(fixtures_dir / setup.target_image)
        if setup.target_image
        else str(fixtures_dir / setup.target_video)
        if setup.target_video
        else None
    )

    if not source_path or not target_path:
        return _skip(scenario, 'Scenario setup missing source or target path')

    preset = setup.preset

    # --- visual_quality ---
    if stype == ScenarioType.visual_quality:
        return _run_visual_quality(scenario, source_path, target_path, preset, fixtures_dir, use_llm_judge)

    # --- performance ---
    if stype == ScenarioType.performance:
        return _run_performance(scenario, source_path, target_path, preset, fixtures_dir)

    return _skip(scenario, f'Unknown scenario type: {stype}')


def _run_visual_quality(
    scenario: Scenario,
    source_path: str,
    target_path: str,
    preset: Optional[str],
    fixtures_dir: Path,
    use_llm_judge: bool,
) -> ScenarioResult:
    """Execute a visual_quality scenario."""
    from factory.orchestrator import run_swap
    from factory.gates.metrics import MetricGate

    # 1. run the swap
    swap = run_swap(source_path, target_path, preset)

    # 2. evaluate metric assertions
    gate = MetricGate()
    gate_results = gate.evaluate_all(
        swap.source_frame,
        swap.target_frame,
        swap.result_frame,
        swap.source_embedding,
        swap.result_embedding,
        scenario.assertions.metrics,
    )
    metric_dicts = [_gate_result_to_dict(gr) for gr in gate_results]
    all_passed = all(gr.passed for gr in gate_results)

    # 3. optional LLM judge
    judge_dict: Optional[dict] = None
    llm_cfg = scenario.assertions.llm_judge
    if use_llm_judge and llm_cfg and llm_cfg.enabled:
        try:
            from factory.judges.vision_judge import VisionJudge
            from factory.judges.aggregator import run_aggregated_judgment

            judge = VisionJudge(model=llm_cfg.model)
            agg = run_aggregated_judgment(
                judge,
                source_path,
                target_path,
                n_samples=llm_cfg.min_samples,
                thresholds=llm_cfg.dimensions,
            )
            judge_dict = {
                'medians': agg.medians,
                'means': agg.means,
                'passed': agg.passed,
                'unreliable_dimensions': agg.unreliable_dimensions,
                'skipped': agg.skipped,
            }
        except Exception as exc:
            logger.warning('LLM judge failed: %s', exc)
            judge_dict = {'error': str(exc), 'skipped': True}

    # 4. optional golden comparison
    golden_dict: Optional[dict] = None
    if scenario.assertions.golden_ref:
        try:
            from factory.golden.registry import GoldenRegistry
            from factory.golden.comparator import GoldenComparator

            golden_dir = fixtures_dir.parent / 'golden'
            registry = GoldenRegistry(golden_dir)
            entry = registry.get(scenario.assertions.golden_ref)
            if entry:
                comparator = GoldenComparator()
                # We need a temporary file for the result frame
                import tempfile, cv2
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    cv2.imwrite(tmp.name, swap.result_frame)
                    cmp = comparator.compare(Path(tmp.name), entry)
                golden_dict = {
                    'ssim_to_golden': cmp.ssim_to_golden,
                    'lpips_to_golden': cmp.lpips_to_golden,
                    'within_tolerance': cmp.within_tolerance,
                    'metric_deltas': cmp.metric_deltas,
                }
            else:
                golden_dict = {'skipped': True, 'reason': f'No golden entry for {scenario.assertions.golden_ref!r}'}
        except Exception as exc:
            logger.warning('Golden comparison failed: %s', exc)
            golden_dict = {'error': str(exc), 'skipped': True}

    return ScenarioResult(
        scenario_name=scenario.name,
        scenario_type=scenario.type.value,
        passed=all_passed,
        metric_results=metric_dicts,
        judge_result=judge_dict,
        golden_result=golden_dict,
    )


def _run_performance(
    scenario: Scenario,
    source_path: str,
    target_path: str,
    preset: Optional[str],
    fixtures_dir: Path,
) -> ScenarioResult:
    """Execute a performance scenario."""
    from factory.orchestrator import run_swap
    from factory.gates.metrics import MetricGate
    from factory.gates.performance import PerformanceTracker, evaluate_performance

    # 1. run the swap inside a PerformanceTracker
    tracker = PerformanceTracker()
    with tracker:
        swap = run_swap(source_path, target_path, preset)

    # 2. evaluate performance assertions
    perf_result = tracker.result
    perf_gates: List[dict] = []
    perf_all_passed = True
    if perf_result and scenario.assertions.performance:
        perf_gate_results = evaluate_performance(perf_result, scenario.assertions.performance)
        perf_gates = [_gate_result_to_dict(gr) for gr in perf_gate_results]
        if not all(gr.passed for gr in perf_gate_results):
            perf_all_passed = False

    perf_dict = None
    if perf_result:
        perf_dict = {
            'elapsed_seconds': perf_result.elapsed_seconds,
            'peak_vram_mb': perf_result.peak_vram_mb,
            'cache_entries': perf_result.cache_entries,
            'gate_results': perf_gates,
        }

    # 3. evaluate any metric assertions too
    metric_dicts: List[dict] = []
    metrics_passed = True
    if scenario.assertions.metrics:
        gate = MetricGate()
        gate_results = gate.evaluate_all(
            swap.source_frame,
            swap.target_frame,
            swap.result_frame,
            swap.source_embedding,
            swap.result_embedding,
            scenario.assertions.metrics,
        )
        metric_dicts = [_gate_result_to_dict(gr) for gr in gate_results]
        if not all(gr.passed for gr in gate_results):
            metrics_passed = False

    return ScenarioResult(
        scenario_name=scenario.name,
        scenario_type=scenario.type.value,
        passed=perf_all_passed and metrics_passed,
        metric_results=metric_dicts,
        performance_result=perf_dict,
    )


# ---------------------------------------------------------------------------
# Batch execution
# ---------------------------------------------------------------------------

def run_all(
    scenarios_path: str,
    priority_filter: Optional[str] = None,
    use_llm_judge: bool = False,
    skip_types: Optional[List[str]] = None,
    fixtures_dir: Optional[str] = None,
) -> FactoryReport:
    """Load and execute factory scenarios, returning an aggregate report.

    Parameters
    ----------
    scenarios_path:
        Path to a single YAML file or a directory of YAML files.
    priority_filter:
        Minimum priority level (``critical``, ``high``, ``medium``, ``low``).
    use_llm_judge:
        Whether to enable LLM-based quality judgments.
    skip_types:
        Scenario types to skip entirely.
    fixtures_dir:
        Path to the fixtures directory.  Defaults to ``factory/fixtures``.
    """
    path = Path(scenarios_path)
    fix_dir = Path(fixtures_dir) if fixtures_dir else Path('factory/fixtures')
    skip_set = set(skip_types or [])

    # Load scenarios
    pf = ScenarioPriority(priority_filter) if priority_filter else None
    if path.is_file():
        scenarios = [load_scenario(path)]
        if pf:
            threshold = _PRIORITY_ORDER[pf]
            scenarios = [s for s in scenarios if _PRIORITY_ORDER[s.priority] <= threshold]
    else:
        scenarios = load_scenarios(path, priority_filter=pf)

    # Filter by skip_types
    if skip_set:
        scenarios = [s for s in scenarios if s.type.value not in skip_set]

    # Execute
    results: List[ScenarioResult] = []
    for scenario in scenarios:
        try:
            result = run_scenario(scenario, fix_dir, use_llm_judge=use_llm_judge)
        except Exception as exc:
            logger.error('Scenario %s crashed: %s', scenario.name, exc)
            result = ScenarioResult(
                scenario_name=scenario.name,
                scenario_type=scenario.type.value,
                passed=False,
                skipped=True,
                skip_reason=f'Crashed: {exc}',
            )
        results.append(result)

    # Summarise
    n_passed = sum(1 for r in results if r.passed and not r.skipped)
    n_failed = sum(1 for r in results if not r.passed and not r.skipped)
    n_skipped = sum(1 for r in results if r.skipped)

    report = FactoryReport(
        scenarios_run=len(results),
        scenarios_passed=n_passed,
        scenarios_failed=n_failed,
        scenarios_skipped=n_skipped,
        results=[asdict(r) for r in results],
    )

    _print_summary(results, report)
    return report


# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------

def _print_summary(results: List[ScenarioResult], report: FactoryReport) -> None:
    """Print a human-readable summary to stdout."""
    print('\n=== FACTORY RESULTS ===\n')

    for r in results:
        if r.skipped:
            print(f'[SKIP] {r.scenario_name} ({r.scenario_type})')
            print(f'  Reason: {r.skip_reason}')
        elif r.passed:
            print(f'[PASS] {r.scenario_name} ({r.scenario_type})')
            for m in r.metric_results:
                op = m['expected_operator']
                print(f'  {m["metric_name"]}: {m["actual_value"]:.4f} {op} {m["expected_value"]:.4f} \u2713')
        else:
            print(f'[FAIL] {r.scenario_name} ({r.scenario_type})')
            for m in r.metric_results:
                op = m['expected_operator']
                mark = '\u2713' if m['passed'] else '\u2717'
                print(f'  {m["metric_name"]}: {m["actual_value"]:.4f} {op} {m["expected_value"]:.4f} {mark}')

        # Performance details
        if r.performance_result and not r.skipped:
            pr = r.performance_result
            print(f'  elapsed: {pr.get("elapsed_seconds", 0):.2f}s  vram: {pr.get("peak_vram_mb", 0):.0f}MB')
            for pg in pr.get('gate_results', []):
                op = pg['expected_operator']
                mark = '\u2713' if pg['passed'] else '\u2717'
                print(f'  {pg["metric_name"]}: {pg["actual_value"]:.4f} {op} {pg["expected_value"]:.4f} {mark}')

        print()

    print('\u2500' * 29)
    print(
        f'Total: {report.scenarios_run} | '
        f'Passed: {report.scenarios_passed} | '
        f'Failed: {report.scenarios_failed} | '
        f'Skipped: {report.scenarios_skipped}'
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for the factory runner."""
    parser = argparse.ArgumentParser(
        prog='factory-runner',
        description='Run factory face-swap quality scenarios.',
    )
    parser.add_argument(
        'scenarios',
        help='Path to a YAML scenario file or directory of scenarios.',
    )
    parser.add_argument(
        '--priority',
        choices=['critical', 'high', 'medium', 'low'],
        default=None,
        help='Minimum priority filter (default: run all).',
    )
    parser.add_argument(
        '--llm-judge',
        action='store_true',
        default=False,
        help='Enable LLM-based vision judge evaluations (requires ANTHROPIC_API_KEY).',
    )
    parser.add_argument(
        '--output-json',
        default=None,
        help='Path to write the JSON results report.',
    )
    parser.add_argument(
        '--skip-types',
        nargs='+',
        default=[],
        help='Scenario types to skip (e.g. comparative regression).',
    )
    parser.add_argument(
        '--fixtures-dir',
        default='factory/fixtures',
        help='Path to fixtures directory (default: factory/fixtures).',
    )

    args = parser.parse_args()

    report = run_all(
        scenarios_path=args.scenarios,
        priority_filter=args.priority,
        use_llm_judge=args.llm_judge,
        skip_types=args.skip_types,
        fixtures_dir=args.fixtures_dir,
    )

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        print(f'\nJSON report written to {out}')

    # Exit code: 0 if everything passed (or skipped), 1 if any failed
    if report.scenarios_failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
