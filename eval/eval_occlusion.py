#!/usr/bin/env python3
"""Occlusion robustness evaluation: compare identity scores for clean vs occluded frames."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    collect_images,
    cosine_similarity,
    extract_embedding,
    load_image,
    logger,
    setup_logging,
    write_json,
)


def _score_directory(
    src_emb: Any,
    directory: str,
    embedding_model: str,
) -> tuple[list[dict], int]:
    frames = collect_images(directory)
    scores: list[dict] = []
    no_face = 0
    for frame_path in frames:
        tgt_img = load_image(frame_path)
        tgt_emb = extract_embedding(tgt_img, embedding_model)
        if tgt_emb is None:
            no_face += 1
            logger.warning("No face detected: %s", frame_path.name)
            continue
        score = cosine_similarity(src_emb, tgt_emb)
        scores.append({"frame": frame_path.name, "identity_score": round(score, 4)})
    return scores, no_face


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure face-swap identity robustness under occlusion by comparing clean vs occluded results.",
    )
    parser.add_argument("--source", required=True, help="Path to the source face image")
    parser.add_argument("--clean-dir", required=True, help="Directory of clean (no occlusion) output frames")
    parser.add_argument("--occluded-dir", required=True, help="Directory of occluded output frames")
    parser.add_argument("--output", default=None, help="Path to write JSON results (default: stdout)")
    parser.add_argument(
        "--embedding-model",
        default="arcface",
        choices=["arcface", "auraface"],
        help="Embedding model to use (default: arcface)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    src_img = load_image(args.source)
    src_emb = extract_embedding(src_img, args.embedding_model)
    if src_emb is None:
        logger.error("No face detected in source image: %s", args.source)
        sys.exit(1)

    clean_scores, clean_no_face = _score_directory(src_emb, args.clean_dir, args.embedding_model)
    occluded_scores, occluded_no_face = _score_directory(src_emb, args.occluded_dir, args.embedding_model)

    import numpy as np

    clean_vals = [s["identity_score"] for s in clean_scores]
    occluded_vals = [s["identity_score"] for s in occluded_scores]

    clean_mean = round(float(np.mean(clean_vals)), 4) if clean_vals else None
    occluded_mean = round(float(np.mean(occluded_vals)), 4) if occluded_vals else None

    identity_drop = None
    if clean_mean is not None and occluded_mean is not None:
        identity_drop = round(clean_mean - occluded_mean, 4)

    result = {
        "source": str(args.source),
        "clean_dir": str(args.clean_dir),
        "occluded_dir": str(args.occluded_dir),
        "clean_num_frames": len(clean_scores) + clean_no_face,
        "clean_num_scored": len(clean_scores),
        "clean_num_no_face": clean_no_face,
        "occluded_num_frames": len(occluded_scores) + occluded_no_face,
        "occluded_num_scored": len(occluded_scores),
        "occluded_num_no_face": occluded_no_face,
        "clean_mean_identity": clean_mean,
        "occluded_mean_identity": occluded_mean,
        "identity_drop": identity_drop,
        "clean_scores": clean_scores,
        "occluded_scores": occluded_scores,
        "embedding_model": args.embedding_model,
    }

    write_json(result, args.output)


if __name__ == "__main__":
    main()
