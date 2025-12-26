## 2024-03-24 - Accessibility for Hidden Labels in Gradio
**Learning:** Gradio components with `show_label=False` are invisible to screen readers unless a `label` is explicitly provided.
**Action:** Always add a descriptive `label` argument even when `show_label=False` to ensure screen readers can identify the component's purpose.
