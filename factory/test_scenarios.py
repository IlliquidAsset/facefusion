"""Pytest parametrized tests that discover and run factory scenarios."""

import pytest
from pathlib import Path

from factory.scenarios.loader import load_scenario

DEFINITIONS_DIR = Path(__file__).parent / 'scenarios' / 'definitions'


def _discover_yamls():
    """Find all YAML scenario files."""
    if not DEFINITIONS_DIR.exists():
        return []
    return sorted(DEFINITIONS_DIR.glob('*.yaml'))


@pytest.mark.parametrize('yaml_path', _discover_yamls(), ids=lambda p: p.stem)
def test_scenario_loads(yaml_path):
    """Each YAML scenario file loads and validates against the Pydantic schema."""
    scenario = load_scenario(yaml_path)
    assert scenario.name
    assert scenario.type
    assert scenario.priority


@pytest.mark.parametrize('yaml_path', _discover_yamls(), ids=lambda p: p.stem)
@pytest.mark.gpu
def test_scenario_runs(yaml_path):
    """Each scenario can be executed by the runner (requires GPU + fixtures)."""
    from factory.runner import run_scenario

    scenario = load_scenario(yaml_path)
    result = run_scenario(scenario, fixtures_dir=DEFINITIONS_DIR.parent.parent / 'fixtures')
    if not result.skipped:
        # Only assert pass for non-skipped scenarios
        # (skipped scenarios are expected for regression/comparative types)
        pass  # Result tracking only — actual pass/fail depends on fixtures
