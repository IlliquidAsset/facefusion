from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from factory.remote import FactoryReport, RemoteExecutor

JsonMap = dict[str, object]
RulesMap = dict[str, JsonMap]


@dataclass
class IterationResult:
    iteration_number: int
    timestamp: str
    git_commit_hash: str
    factory_report: FactoryReport
    metrics_summary: dict[str, float]
    changes_made: str
    status: Literal['running', 'passed', 'failed', 'plateau', 'escalated', 'rolled_back']
    cost_so_far: float
    escalation_reason: str | None = None


@dataclass
class EscalationReason:
    type: str
    message: str
    data: JsonMap = field(default_factory=lambda: cast(JsonMap, {}))


class IterationController:
    executor: RemoteExecutor
    scenarios: list[str]
    max_iterations: int
    budget_cap: float
    log_path: Path
    iteration_count: int
    start_time: float
    best_iteration: int | None
    best_metric_value: float
    history: list[IterationResult]
    rules: RulesMap

    def __init__(
        self,
        remote_executor: RemoteExecutor,
        scenarios: list[str],
        max_iterations: int = 20,
        budget_cap: float = 10.0,
        log_path: str = 'factory/iteration_log.json',
    ):
        self.executor = remote_executor
        self.scenarios = scenarios
        self.max_iterations = max_iterations
        self.budget_cap = budget_cap
        self.log_path = Path(log_path)

        self.iteration_count = 0
        self.start_time = time.time()
        self.best_iteration = None
        self.best_metric_value = 0.0
        self.history = []

        rules_path = Path(__file__).with_name('escalation_rules.json')
        self.rules = self._load_rules(rules_path)

    def run_iteration(self, changes_description: str = '') -> IterationResult:
        self.iteration_count += 1
        timestamp = datetime.now().isoformat()

        status: Literal['running', 'passed', 'failed', 'plateau', 'escalated', 'rolled_back'] = 'running'
        escalation_reason: str | None = None
        metrics: dict[str, float] = {}
        commit_hash = 'unknown'

        try:
            if not self.executor.sync_code():
                raise RuntimeError('sync_code returned False')

            report = self._run_scenarios()
            metrics = self._extract_metrics(report)
            commit_hash = self._create_git_commit(metrics)

            if report.scenarios_failed == 0 and report.scenarios_run > 0:
                status = 'passed'
            else:
                status = 'failed'
        except Exception as exc:
            report = FactoryReport(
                scenarios_run=0,
                scenarios_passed=0,
                scenarios_failed=0,
                scenarios_skipped=0,
                results=[],
            )
            status = 'failed'
            escalation_reason = f'factory_runner_nonzero_exit_no_json: {exc}'
            commit_hash = self._create_git_commit(metrics)

        cost_so_far = self.executor.estimate_cost(self.start_time)
        result = IterationResult(
            iteration_number=self.iteration_count,
            timestamp=timestamp,
            git_commit_hash=commit_hash,
            factory_report=report,
            metrics_summary=metrics,
            changes_made=changes_description,
            status=status,
            cost_so_far=cost_so_far,
            escalation_reason=escalation_reason,
        )

        identity_score = metrics.get('identity_similarity', 0.0)
        if self.best_iteration is None or identity_score > self.best_metric_value:
            self.best_metric_value = identity_score
            self.best_iteration = self.iteration_count

        self._log_iteration(result)
        self.history.append(result)
        return result

    def _run_scenarios(self) -> FactoryReport:
        if not self.scenarios:
            raise ValueError('At least one scenario path is required')

        scenarios_run = 0
        scenarios_passed = 0
        scenarios_failed = 0
        scenarios_skipped = 0
        elapsed_seconds = 0.0
        all_results: list[JsonMap] = []

        for scenario_path in self.scenarios:
            report = self.executor.run_factory(scenario_path)
            scenarios_run += report.scenarios_run
            scenarios_passed += report.scenarios_passed
            scenarios_failed += report.scenarios_failed
            scenarios_skipped += report.scenarios_skipped
            all_results.extend(self._normalize_results(cast(list[object], report.results)))

        return FactoryReport(
            scenarios_run=scenarios_run,
            scenarios_passed=scenarios_passed,
            scenarios_failed=scenarios_failed,
            scenarios_skipped=scenarios_skipped,
            results=all_results,
        )

    def _extract_metrics(self, report: FactoryReport) -> dict[str, float]:
        metrics = {
            'scenarios_run': float(report.scenarios_run),
            'scenarios_passed': float(report.scenarios_passed),
            'scenarios_failed': float(report.scenarios_failed),
        }

        identity_scores: list[float] = []
        scenario_results = self._normalize_results(cast(list[object], report.results))
        for scenario_result in scenario_results:
            metric_results = self._normalize_results(self._as_list(scenario_result.get('metric_results')))
            for metric in metric_results:
                if metric.get('metric_name') != 'identity_similarity':
                    continue
                identity_scores.append(self._to_float(metric.get('actual_value'), default=0.0))

        if identity_scores:
            metrics['identity_similarity'] = max(identity_scores)
            metrics['identity_similarity_mean'] = sum(identity_scores) / len(identity_scores)

        return metrics

    def _create_git_commit(self, metrics: dict[str, float]) -> str:
        identity = metrics.get('identity_similarity', 0.0)
        message = f'iteration-{self.iteration_count}: identity={identity:.4f}'

        _ = subprocess.run(['git', 'add', '-A'], check=False)
        _ = subprocess.run(['git', 'commit', '-m', message, '--allow-empty'], check=False)

        rev_parse = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_parse.returncode == 0:
            return rev_parse.stdout.strip()[:12]
        return 'unknown'

    def _log_iteration(self, result: IterationResult) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        report = result.factory_report
        report_results = self._normalize_results(cast(list[object], report.results))
        report_payload: JsonMap = {
            'scenarios_run': report.scenarios_run,
            'scenarios_passed': report.scenarios_passed,
            'scenarios_failed': report.scenarios_failed,
            'scenarios_skipped': report.scenarios_skipped,
            'results': report_results,
        }
        log_entry: JsonMap = {
            'iteration_number': result.iteration_number,
            'timestamp': result.timestamp,
            'git_commit_hash': result.git_commit_hash,
            'factory_report': report_payload,
            'metrics_summary': result.metrics_summary,
            'changes_made': result.changes_made,
            'status': result.status,
            'cost_so_far': result.cost_so_far,
            'escalation_reason': result.escalation_reason,
        }

        with open(self.log_path, 'a') as handle:
            _ = handle.write(json.dumps(log_entry) + '\n')

    def check_escalation(self, history: list[IterationResult]) -> EscalationReason | None:
        if not history:
            return None

        latest = history[-1]

        if latest.status == 'passed' and latest.factory_report.scenarios_failed == 0:
            return EscalationReason(
                type='success',
                message=self._rule_message('success', 'All scenarios passed.'),
            )

        if latest.iteration_number >= self.max_iterations:
            return EscalationReason(
                type='max_iterations',
                message=self._rule_message(
                    'max_iterations',
                    'Iteration cap reached. Best result at iteration {best_iteration}.',
                ).format(best_iteration=self.best_iteration or 0),
                data={'best_iteration': self.best_iteration or 0},
            )

        if latest.cost_so_far >= self.budget_cap:
            return EscalationReason(
                type='budget',
                message=self._rule_message(
                    'budget',
                    'Budget cap reached at ${budget_cap}.',
                ).format(budget_cap=self.budget_cap),
                data={'budget_cap': self.budget_cap},
            )

        if latest.escalation_reason and latest.escalation_reason.startswith('factory_runner_nonzero_exit_no_json'):
            return EscalationReason(
                type='crash',
                message='Factory runner crashed before producing JSON output.',
                data={'max_retries': self._rule_int('crash', 'max_retries', 1)},
            )

        if len(history) >= 3:
            recent_scores = [
                iteration.metrics_summary.get('identity_similarity', 0.0)
                for iteration in history[-3:]
            ]
            if max(recent_scores) - min(recent_scores) < 0.01:
                return EscalationReason(
                    type='plateau',
                    message=self._rule_message(
                        'plateau',
                        'Metrics plateaued. Best identity_similarity={best}. Threshold={target}.',
                    ).format(best=self.best_metric_value, target=0.65),
                    data={'best': self.best_metric_value, 'target': 0.65},
                )

        if len(history) >= 2 and self.best_iteration is not None:
            recent = history[-2:]
            if all(
                iteration.metrics_summary.get('identity_similarity', 0.0) < self.best_metric_value
                for iteration in recent
            ):
                return EscalationReason(
                    type='regression',
                    message='Metrics regressed from best. Consider rollback.',
                    data={
                        'best_iteration': self.best_iteration,
                        'max_retries': self._rule_int('regression', 'max_retries', 2),
                    },
                )

        return None

    def track_best(self) -> int:
        return self.best_iteration or 0

    def rollback_to_best(self) -> bool:
        if self.best_iteration is None:
            return False

        commits_to_revert = [
            iteration.git_commit_hash
            for iteration in self.history
            if iteration.iteration_number > self.best_iteration
        ]

        for commit_hash in reversed(commits_to_revert):
            result = subprocess.run(['git', 'revert', '--no-edit', commit_hash], check=False)
            if result.returncode != 0:
                return False

        return True

    def diagnose(self, report: FactoryReport) -> JsonMap:
        failures: list[JsonMap] = []
        suggestions: list[str] = []
        categories: list[str] = []

        scenario_results = self._normalize_results(cast(list[object], report.results))
        for scenario_result in scenario_results:
            if self._to_bool(scenario_result.get('passed'), default=True):
                continue

            metric_results = self._normalize_results(self._as_list(scenario_result.get('metric_results')))
            for metric in metric_results:
                if self._to_bool(metric.get('passed'), default=True):
                    continue

                name_obj = metric.get('metric_name')
                name = name_obj if isinstance(name_obj, str) else 'unknown'
                actual = self._to_float(metric.get('actual_value'), default=0.0)
                expected = self._to_float(metric.get('expected_value'), default=0.0)

                failures.append(
                    {
                        'metric': name,
                        'actual': actual,
                        'expected': expected,
                        'gap': expected - actual,
                    }
                )

                if name == 'identity_similarity':
                    categories.append('identity')
                    suggestions.append('Increase REFace DDIM steps or improve face alignment before swap.')
                elif name in {'ssim', 'psnr', 'blur_score', 'artifact_score'}:
                    categories.append('quality')
                    suggestions.append('Adjust blending and boundary masks to reduce visual artifacts.')
                elif name == 'lpips':
                    categories.append('perceptual')
                    suggestions.append('Tune color matching and denoise settings to improve perceptual quality.')
                else:
                    categories.append('unknown')
                    suggestions.append(f'Inspect metric definition for {name} and add a targeted adjustment.')

        summary = 'No failing metrics detected.'
        if failures:
            categories = list(dict.fromkeys(categories))
            suggestions = list(dict.fromkeys(suggestions))
            summary = f'{len(failures)} metric failure(s) across {len(categories)} category(ies).'

        return {
            'failures': failures,
            'suggestions': suggestions,
            'categories': categories,
            'summary': summary,
        }

    def _rule_message(self, rule_name: str, fallback: str) -> str:
        rule = self.rules.get(rule_name)
        if not rule:
            return fallback
        message = rule.get('message')
        if isinstance(message, str):
            return message
        return fallback

    def _rule_int(self, rule_name: str, key: str, fallback: int) -> int:
        rule = self.rules.get(rule_name)
        if not rule:
            return fallback
        return self._to_int(rule.get(key), default=fallback)

    @staticmethod
    def _load_rules(rules_path: Path) -> RulesMap:
        with open(rules_path) as handle:
            raw_rules = cast(object, json.load(handle))

        if not isinstance(raw_rules, dict):
            raise ValueError(f'Invalid escalation rules format: {rules_path}')

        rules: RulesMap = {}
        raw_rule_map = cast(dict[object, object], raw_rules)
        for key, value in raw_rule_map.items():
            if not isinstance(key, str):
                continue
            if not isinstance(value, dict):
                continue
            rules[key] = cast(JsonMap, value)
        return rules

    @staticmethod
    def _normalize_results(values: list[object]) -> list[JsonMap]:
        normalized: list[JsonMap] = []
        for value in values:
            if isinstance(value, dict):
                normalized.append(cast(JsonMap, value))
        return normalized

    @staticmethod
    def _as_list(value: object) -> list[object]:
        if isinstance(value, list):
            return cast(list[object], value)
        return []

    @staticmethod
    def _to_bool(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {'1', 'true', 'yes'}:
                return True
            if lowered in {'0', 'false', 'no'}:
                return False
        return default

    @staticmethod
    def _to_float(value: object, default: float) -> float:
        if isinstance(value, bool):
            return default
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    @staticmethod
    def _to_int(value: object, default: int) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default
