#!/usr/bin/env python3
"""Single-pair identity scoring: source face vs output face."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import compute_identity_score, setup_logging, write_json


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute ArcFace identity similarity between a source face and an output face.",
    )
    parser.add_argument("--source", required=True, help="Path to the source face image")
    parser.add_argument("--target", required=True, help="Path to the output/swapped face image")
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

    result = compute_identity_score(args.source, args.target, args.embedding_model)
    write_json(result, args.output)


if __name__ == "__main__":
    main()
