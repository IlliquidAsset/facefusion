## 2026-01-13 - Project Orientation
**Learning:** This is a Python/Gradio face processing application with a modular UI system.
**Action:** Focus on Gradio-specific accessibility improvements (aria-labels, loading states) and small UX wins in frequently used components.

## 2026-01-13 - Tooltip Consistency
**Learning:** Gradio's `Dropdown` component supports an `info` parameter for tooltips. `watserface/wording.py` often contains help text that isn't being displayed in the UI.
**Action:** When identifying UI components, check `wording.py` for unused 'help' strings that can be added as `info` parameters.

## 2026-01-14 - File Input Context
**Learning:** `gradio.File` components often lack context about what they accept beyond the file extension filter. Reusing CLI help text from `wording.py` (e.g., `help.source_paths`) works perfectly for the `info` tooltip.
**Action:** Audit all `gradio.File` inputs to ensure they have descriptive `info` tooltips sourced from existing wording keys.
