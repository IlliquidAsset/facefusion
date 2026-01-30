#!/usr/bin/env python3
"""
Compare FaceDancer and REFace evaluation results side-by-side.
Generates a decision-ready summary for Task 4 (Architecture Decision).

Usage:
    python3 eval/compare_results.py [--output eval/results/comparison.json]
"""

import argparse
import json
import os
import sys


def load_scores(path):
    """Load scores JSON, return None if missing."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Compare FaceDancer and REFace evaluation results."
    )
    parser.add_argument(
        "--facedancer-scores",
        default="eval/results/facedancer/scores.json",
        help="Path to FaceDancer scores JSON",
    )
    parser.add_argument(
        "--reface-scores",
        default="eval/results/reface/scores.json",
        help="Path to REFace scores JSON",
    )
    parser.add_argument(
        "--output",
        default="eval/results/comparison.json",
        help="Path to write comparison JSON (default: eval/results/comparison.json)",
    )
    parser.add_argument(
        "--kill-threshold",
        type=float,
        default=0.85,
        help="Minimum p95 identity score to proceed (default: 0.85)",
    )
    args = parser.parse_args()

    fd = load_scores(args.facedancer_scores)
    rf = load_scores(args.reface_scores)

    if fd is None and rf is None:
        print("Error: No evaluation results found.")
        print(f"  Expected: {args.facedancer_scores}")
        print(f"  Expected: {args.reface_scores}")
        sys.exit(1)

    comparison = {
        "kill_threshold": args.kill_threshold,
        "facedancer": None,
        "reface": None,
        "recommendation": None,
    }

    print("=" * 60)
    print("  ARCHITECTURE COMPARISON — Task 4 Decision Support")
    print("=" * 60)
    print(f"  Kill threshold (p95 identity): >= {args.kill_threshold}")
    print()

    metrics = ["mean_identity", "p50_identity", "p95_identity", "min_identity"]

    # Header
    print(f"  {'Metric':<20} {'FaceDancer':>12} {'REFace':>12} {'Winner':>10}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*10}")

    for model_name, scores, key in [("facedancer", fd, "facedancer"), ("reface", rf, "reface")]:
        if scores is not None:
            comparison[key] = {
                "num_frames": scores.get("num_frames", 0),
                "num_scored": scores.get("num_scored", 0),
                "mean_identity": scores.get("mean_identity", 0),
                "p50_identity": scores.get("p50_identity", 0),
                "p95_identity": scores.get("p95_identity", 0),
                "min_identity": scores.get("min_identity", 0),
                "passes_kill": scores.get("p95_identity", 0) >= args.kill_threshold,
            }

    for metric in metrics:
        fd_val = fd.get(metric, 0) if fd else None
        rf_val = rf.get(metric, 0) if rf else None

        fd_str = f"{fd_val:.4f}" if fd_val is not None else "N/A"
        rf_str = f"{rf_val:.4f}" if rf_val is not None else "N/A"

        if fd_val is not None and rf_val is not None:
            winner = "FaceDancer" if fd_val > rf_val else "REFace" if rf_val > fd_val else "Tie"
        elif fd_val is not None:
            winner = "FaceDancer"
        elif rf_val is not None:
            winner = "REFace"
        else:
            winner = "N/A"

        print(f"  {metric:<20} {fd_str:>12} {rf_str:>12} {winner:>10}")

    # Kill criteria
    print()
    fd_passes = fd is not None and fd.get("p95_identity", 0) >= args.kill_threshold
    rf_passes = rf is not None and rf.get("p95_identity", 0) >= args.kill_threshold

    print(f"  Kill criteria (p95 >= {args.kill_threshold}):")
    if fd is not None:
        status = "PASS" if fd_passes else "FAIL"
        print(f"    FaceDancer: {status} (p95={fd.get('p95_identity', 0):.4f})")
    else:
        print(f"    FaceDancer: NOT EVALUATED")

    if rf is not None:
        status = "PASS" if rf_passes else "FAIL"
        print(f"    REFace:     {status} (p95={rf.get('p95_identity', 0):.4f})")
    else:
        print(f"    REFace:     NOT EVALUATED")

    # Recommendation
    print()
    if fd_passes and rf_passes:
        # Both pass — but FaceDancer is CC BY-NC-SA, so REFace is the only commercial option
        recommendation = "REFace (both pass quality gate, but FaceDancer code is CC BY-NC-SA — not commercially viable)"
    elif rf_passes and not fd_passes:
        recommendation = "REFace (passes quality gate; FaceDancer does not)"
    elif fd_passes and not rf_passes:
        recommendation = "CAUTION: FaceDancer passes but is CC BY-NC-SA (non-commercial). REFace fails quality gate. Consider: more training data, longer fine-tuning, or alternative architectures."
    else:
        recommendation = "STOP: Neither architecture meets the kill threshold. Reassess approach."

    comparison["recommendation"] = recommendation
    print(f"  RECOMMENDATION: {recommendation}")
    print()
    print("  NOTE: FaceDancer code license (CC BY-NC-SA) prohibits commercial use.")
    print("  REFace architecture (MIT) is the only commercially viable path.")
    print("  FaceDancer results serve as a quality ceiling reference only.")
    print("=" * 60)

    # Write JSON
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n  Full comparison: {args.output}")


if __name__ == "__main__":
    main()
