## 2026-01-13 - Project Orientation
**Learning:** This is a Python/Gradio face processing application with a modular UI system.
**Action:** Focus on Gradio-specific accessibility improvements (aria-labels, loading states) and small UX wins in frequently used components.

## 2026-01-13 - Tooltip Consistency
**Learning:** Gradio's `Dropdown` component supports an `info` parameter for tooltips. `watserface/wording.py` often contains help text that isn't being displayed in the UI.
**Action:** When identifying UI components, check `wording.py` for unused 'help' strings that can be added as `info` parameters.

## 2026-01-13 - Formatting Help Strings
**Learning:** Help strings in `wording.py` may contain placeholders (e.g., `{choices}`) that need to be formatted at runtime using data not available in `wording.py`.
**Action:** Always check if a help string requires `.format()` before passing it to the `info` parameter.
