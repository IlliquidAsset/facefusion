## 2026-01-13 - Project Orientation
**Learning:** This is a Python/Gradio face processing application with a modular UI system.
**Action:** Focus on Gradio-specific accessibility improvements (aria-labels, loading states) and small UX wins in frequently used components.

## 2026-01-13 - Tooltip Consistency
**Learning:** Gradio's `Dropdown` component supports an `info` parameter for tooltips. `watserface/wording.py` often contains help text that isn't being displayed in the UI.
**Action:** When identifying UI components, check `wording.py` for unused 'help' strings that can be added as `info` parameters.

## 2026-01-14 - Leveraging Centralized Wording for UX
**Learning:** The project uses a centralized `watserface/wording.py` which contains detailed help strings (`help.*`) that were not being utilized in key input fields like `File` and `CheckboxGroup`. Gradio 4+ supports `info` on these components, allowing us to easily surface this existing content to users without creating new strings.
**Action:** Systematically audit other UI components (beyond dropdowns) to see if corresponding `help.*` keys exist and apply them as `info` tooltips.
