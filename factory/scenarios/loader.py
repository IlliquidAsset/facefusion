"""YAML loading and validation for factory test scenarios."""

from pathlib import Path
from typing import List, Optional

import yaml

from factory.scenarios.schema import Scenario, ScenarioPriority


# Priority ordering: critical (0) > high (1) > medium (2) > low (3)
_PRIORITY_ORDER = {
    ScenarioPriority.critical: 0,
    ScenarioPriority.high: 1,
    ScenarioPriority.medium: 2,
    ScenarioPriority.low: 3,
}


def load_scenario(path: Path) -> Scenario:
    """Read a YAML file and return a validated Scenario."""
    with open(path, 'r') as fh:
        data = yaml.safe_load(fh)
    return Scenario(**data)


def load_scenarios(
    directory: Path,
    priority_filter: Optional[ScenarioPriority] = None,
) -> List[Scenario]:
    """Discover and load all .yaml scenario files in *directory*.

    Parameters
    ----------
    directory:
        Folder containing scenario YAML files (non-recursive).
    priority_filter:
        If set, only return scenarios whose priority is **>=** this level
        (critical > high > medium > low).

    Returns
    -------
    List of scenarios sorted by priority (critical first), then by name.
    """
    scenarios: List[Scenario] = []
    for yaml_path in sorted(directory.glob('*.yaml')):
        scenarios.append(load_scenario(yaml_path))

    if priority_filter is not None:
        threshold = _PRIORITY_ORDER[priority_filter]
        scenarios = [
            s for s in scenarios
            if _PRIORITY_ORDER[s.priority] <= threshold
        ]

    scenarios.sort(key=lambda s: (_PRIORITY_ORDER[s.priority], s.name))
    return scenarios


def validate_fixtures(scenario: Scenario, fixtures_dir: Path) -> List[str]:
    """Check that referenced fixture files exist on disk.

    Returns a list of missing file paths (empty when everything is present).
    """
    missing: List[str] = []
    for field in ('source_image', 'target_image', 'target_video'):
        value = getattr(scenario.setup, field)
        if value is not None:
            full_path = fixtures_dir / value
            if not full_path.exists():
                missing.append(str(full_path))
    return missing
