## 2026-01-13 - Project Orientation
**Learning:** This is a Python/Gradio face processing application with a modular UI system.
**Action:** Focus on Gradio-specific accessibility improvements (aria-labels, loading states) and small UX wins in frequently used components.

## 2026-01-13 - Tooltip Consistency
**Learning:** Gradio's `Dropdown` component supports an `info` parameter for tooltips. `watserface/wording.py` often contains help text that isn't being displayed in the UI.
**Action:** When identifying UI components, check `wording.py` for unused 'help' strings that can be added as `info` parameters.

## 2026-01-13 - Verification Constraints
**Learning:** The testing environment lacks `ffmpeg`, causing widespread failures in media-related tests. Pure UI component changes in Python can be verified via `flake8` and visual code inspection, as running the full app or test suite is restricted.
**Action:** Rely on static analysis (`flake8`) and careful code review for UI changes when full integration testing is impossible.
