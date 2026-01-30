#!/usr/bin/env python3
"""Batch evaluation: score a source face against every frame in a results directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    collect_images,
    cosine_similarity,
    extract_embedding,
    load_image,
    setup_logging,
    write_json,
    logger,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch identity scoring: compare a source face against all images in a directory.",
    )
    parser.add_argument("--source", required=True, help="Path to the source face image")
    parser.add_argument("--results-dir", required=True, help="Directory of output/swapped face images")
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

    frames = collect_images(args.results_dir)
    if not frames:
        logger.error("No images found in %s", args.results_dir)
        sys.exit(1)

    scores: list[dict] = []
    no_face_count = 0

    for frame_path in frames:
        tgt_img = load_image(frame_path)
        tgt_emb = extract_embedding(tgt_img, args.embedding_model)
        if tgt_emb is None:
            no_face_count += 1
            logger.warning("No face detected: %s", frame_path.name)
            continue
        score = cosine_similarity(src_emb, tgt_emb)
        scores.append({"frame": frame_path.name, "identity_score": round(score, 4)})

    import numpy as np

    score_values = [s["identity_score"] for s in scores]

    result = {
        "source": str(args.source),
        "results_dir": str(args.results_dir),
        "num_frames": len(frames),
        "num_scored": len(scores),
        "num_no_face": no_face_count,
        "mean_identity": round(float(np.mean(score_values)), 4) if score_values else None,
        "p50_identity": round(float(np.percentile(score_values, 50)), 4) if score_values else None,
        "p95_identity": round(float(np.percentile(score_values, 5)), 4) if score_values else None,
        "min_identity": round(float(np.min(score_values)), 4) if score_values else None,
        "max_identity": round(float(np.max(score_values)), 4) if score_values else None,
        "scores": scores,
        "embedding_model": args.embedding_model,
    }

    write_json(result, args.output)


if __name__ == "__main__":
    main()
