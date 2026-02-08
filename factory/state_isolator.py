"""State isolation for factory scenario runs.

Snapshots and restores the global ``STATE_SET`` in ``watserface.state_manager``
so that each scenario leaves no side-effects on subsequent runs.
"""

from __future__ import annotations

import copy
from types import TracebackType
from typing import Any, Dict, Optional, Type


class StateIsolator:
    """Context manager that deep-copies STATE_SET on entry and restores it on exit.

    Usage::

        from factory.state_isolator import StateIsolator

        with StateIsolator():
            state_manager.set_item('face_swapper_model', 'test_model')
            # ... run scenario ...
        # state_manager is back to its original values here
    """

    _snapshot: Dict[str, Any]

    def __enter__(self) -> "StateIsolator":
        from watserface import state_manager  # deferred to avoid import-order issues

        self._snapshot = {
            "cli": copy.deepcopy(state_manager.STATE_SET["cli"]),
            "ui": copy.deepcopy(state_manager.STATE_SET["ui"]),
        }
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        from watserface import state_manager

        state_manager.STATE_SET["cli"] = self._snapshot["cli"]
        state_manager.STATE_SET["ui"] = self._snapshot["ui"]
