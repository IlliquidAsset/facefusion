# Fixture Images

This directory contains fixture images and videos used for factory testing. **Fixture images must be user-provided** and cannot be shipped in the repository due to privacy and licensing concerns.

## Directory Structure

```
fixtures/
├── source_faces/          # Source identity images (your face dataset)
├── target_frames/         # Individual target frames for testing
├── target_videos/         # Target videos for batch processing
├── golden/                # Golden reference outputs (expected results)
└── generate_fixtures.py   # Helper script for automated frame extraction
```

## Setup Instructions

### 1. Provide Source Faces
Place your source identity images in `source_faces/`:
```
fixtures/source_faces/
├── identity_1.jpg
├── identity_2.jpg
└── ...
```

### 2. Provide Target Videos
Place target videos in `target_videos/`:
```
fixtures/target_videos/
├── video_1.mp4
├── video_2.mp4
└── ...
```

### 3. Extract Frames (Automated)
Use the `generate_fixtures.py` helper script to extract frames from videos:

```bash
python factory/fixtures/generate_fixtures.py \
  --video fixtures/target_videos/video_1.mp4 \
  --output-dir fixtures/target_frames \
  --every-n-frames 30
```

This will:
- Extract every 30th frame from the video
- Save frames as PNG files with zero-padded naming (frame_0000.png, frame_0001.png, etc.)
- Create the output directory if it doesn't exist

### 4. Generate Golden References
After running face swaps, save expected outputs to `golden/`:
```
fixtures/golden/
├── video_1_identity_1.png
├── video_1_identity_2.png
└── ...
```

## Usage in Tests

Tests will load fixtures from these directories to validate face-swap quality across different scenarios.

## Notes

- **Privacy**: Never commit real face images to the repository
- **Size**: Use `.gitignore` to exclude fixture directories from version control
- **Organization**: Keep source faces and target frames organized by identity/scenario
