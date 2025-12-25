## 2024-10-24 - File Upload Constraints
**Learning:** Users can select any file type in `gradio.File` uploaders by default, which can lead to confusion and errors when unsupported files are uploaded.
**Action:** Always specify `file_types` in `gradio.File` components to filter the OS file picker to supported formats only. This is a quick win for preventing user error.
