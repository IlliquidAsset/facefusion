#!/usr/bin/env python3
"""Create standardized test set directory structure and manifest template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CATEGORIES = {
    "clean": "No occlusion — clear frontal or near-frontal face (target: 30% of set)",
    "occluded": "Simple occlusion — hand, cup, microphone, etc. (target: 30% of set)",
    "complex": "Complex occlusion — fingers over face, hair, overlapping objects (target: 20% of set)",
    "extreme_angle": "Extreme pose — profile view, 45+ degree yaw (target: 20% of set)",
}


def create_manifest_template(base_dir: Path) -> dict:
    manifest: dict = {
        "description": "WatserFace evaluation test set manifest",
        "categories": {},
        "images": [],
    }
    for cat, desc in CATEGORIES.items():
        manifest["categories"][cat] = {"description": desc, "count": 0}

    manifest["_example_image_entry"] = {
        "filename": "frame_001.png",
        "category": "clean",
        "notes": "Optional description of the frame",
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the directory structure and manifest template for a standardized face-swap test set.",
    )
    parser.add_argument(
        "--output-dir",
        default="eval/test_set",
        help="Root directory for the test set (default: eval/test_set)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    base = Path(args.output_dir)
    for cat in CATEGORIES:
        cat_dir = base / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        if args.verbose:
            print(f"Created: {cat_dir}", file=sys.stderr)

    manifest = create_manifest_template(base)
    manifest_path = base / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Test set structure created at: {base}")
    print(f"Manifest template written to: {manifest_path}")
    print(f"Subdirectories: {', '.join(CATEGORIES.keys())}")
    print("Add your test images to the appropriate subdirectories, then update manifest.json.")


if __name__ == "__main__":
    main()
