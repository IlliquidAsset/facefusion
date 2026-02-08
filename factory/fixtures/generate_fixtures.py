#!/usr/bin/env python3
"""
Generate fixture frames from video files.

Extracts frames from a video at configurable intervals and saves them as PNG files
with zero-padded naming for use in factory testing.

Usage:
    python generate_fixtures.py --video input.mp4 --output-dir ./frames
    python generate_fixtures.py --video input.mp4 --output-dir ./frames --every-n-frames 60
"""

import argparse
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    print("Error: opencv-python-headless is required. Install with: pip install opencv-python-headless")
    sys.exit(1)


def extract_frames(video_path: str, output_dir: str, every_n_frames: int = 30) -> None:
    """
    Extract frames from a video file.

    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        every_n_frames: Extract every Nth frame (default: 30)

    Raises:
        FileNotFoundError: If video file doesn't exist
        ValueError: If video cannot be opened or has no frames
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    # Validate input
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        raise ValueError(f"Video has no frames: {video_path}")

    frame_count = 0
    extracted_count = 0

    print(f"Extracting frames from: {video_path}")
    print(f"Total frames: {total_frames}")
    print(f"Extracting every {every_n_frames} frames")
    print(f"Output directory: {output_dir}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Extract every Nth frame
        if frame_count % every_n_frames == 0:
            # Zero-padded filename
            output_path = output_dir / f"frame_{extracted_count:04d}.png"
            cv2.imwrite(str(output_path), frame)
            extracted_count += 1

            if extracted_count % 10 == 0:
                print(f"  Extracted {extracted_count} frames...")

        frame_count += 1

    cap.release()

    print(f"\nExtraction complete!")
    print(f"Extracted {extracted_count} frames to: {output_dir}")


def main():
    """Parse arguments and extract frames."""
    parser = argparse.ArgumentParser(
        description="Extract frames from a video file for factory testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract every 30th frame (default)
  python generate_fixtures.py --video input.mp4 --output-dir ./frames

  # Extract every 60th frame
  python generate_fixtures.py --video input.mp4 --output-dir ./frames --every-n-frames 60

  # Extract every frame
  python generate_fixtures.py --video input.mp4 --output-dir ./frames --every-n-frames 1
        """,
    )

    parser.add_argument(
        "--video",
        required=True,
        help="Path to input video file",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save extracted frames",
    )

    parser.add_argument(
        "--every-n-frames",
        type=int,
        default=30,
        help="Extract every Nth frame (default: 30)",
    )

    args = parser.parse_args()

    try:
        extract_frames(args.video, args.output_dir, args.every_n_frames)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
