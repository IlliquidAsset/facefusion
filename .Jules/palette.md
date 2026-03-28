## 2026-01-13 - Project Orientation
**Learning:** This is a Python/Gradio face processing application with a modular UI system.
**Action:** Focus on Gradio-specific accessibility improvements (aria-labels, loading states) and small UX wins in frequently used components.

## 2026-01-13 - Tooltip Consistency
**Learning:** Gradio's `Dropdown` component supports an `info` parameter for tooltips. `watserface/wording.py` often contains help text that isn't being displayed in the UI.
**Action:** When identifying UI components, check `wording.py` for unused 'help' strings that can be added as `info` parameters.

## 2026-01-13 - Gradio File Component Limitation
**Learning:** `gradio.File` component does not support the `info` parameter for tooltips, unlike `Dropdown` or `Textbox`, causing `TypeError` on initialization.
**Action:** Do not attempt to add `info` to `gradio.File` components. Use `label` augmentation or adjacent text components for help instructions.
