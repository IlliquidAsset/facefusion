## 2026-01-13 - Project Orientation
**Learning:** This is a Python/Gradio face processing application with a modular UI system.
**Action:** Focus on Gradio-specific accessibility improvements (aria-labels, loading states) and small UX wins in frequently used components.

## 2026-01-13 - Tooltip Consistency
**Learning:** Gradio's `Dropdown` component supports an `info` parameter for tooltips. `watserface/wording.py` often contains help text that isn't being displayed in the UI.
**Action:** When identifying UI components, check `wording.py` for unused 'help' strings that can be added as `info` parameters.

## 2026-01-13 - Input Help Text
**Learning:** Core file inputs (`SOURCE_FILE`, `TARGET_FILE`) and output paths (`OUTPUT_PATH_TEXTBOX`) were missing explanation tooltips, despite the help text existing in `wording.py` under `help.source_paths`, `help.target_path`, and `help.output_path`.
**Action:** Always verify if a component has an associated help string in `wording.py` and map it to the `info` parameter to improve usability for first-time users.
