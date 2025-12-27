## 2024-05-22 - Leveraging Existing Wording for Tooltips
**Learning:** Many Gradio components lack the `info` parameter, even though descriptive help text is available in `wording.py`. Leveraging existing wording to add tooltips is a high-impact, low-effort win that improves discoverability without cluttering the UI.
**Action:** When working on UI components, always check `wording.py` for `help` keys that can be mapped to the `info` parameter of Gradio components.
