## 2025-05-15 - Training Options Accessibility
**Learning:** Hardcoded labels in new features (like Training) often miss accessibility features like tooltips (`info` param in Gradio). Moving them to a central `wording.py` ensures consistency and easier localization/maintenance.
**Action:** When adding new UI components, always add labels and help text to `wording.py` first, then reference them.
