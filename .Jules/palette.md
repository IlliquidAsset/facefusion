## 2024-05-22 - [Initial Setup]
**Learning:** Found existing UI components using Gradio. Identified missing labels on icon-only/hidden-label components as a recurring pattern.
**Action:** When working with Gradio components that have `show_label=False`, always ensure a `label` property is still passed for accessibility.
