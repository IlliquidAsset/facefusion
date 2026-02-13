#!/usr/bin/env python3
"""
Single-frame quality comparison: 10 vs 50 DDIM steps.
Uses the cached alignment data to avoid re-processing.
Outputs raw 512x512 crops and 1024x1024 upscaled versions for comparison.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

REFACE_DIR = "/workspace/watserface/vendors/REFace"
SOURCE = "/workspace/watserface/factory/fixtures/source_faces/sam_sources/Sam10.jpg"
VIDEO = "/workspace/watserface/factory/fixtures/target_videos/zBambola.mp4"
OUTPUT_BASE = "/workspace/watserface/factory/results/quality_test"
STATUS_PATH = "/workspace/watserface/factory/results/live_status.json"


def write_status(phase, detail):
    s = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "detail": detail,
        "pid": os.getpid(),
    }
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w") as f:
        json.dump(s, f, indent=2)


def run_inference(ddim_steps, scale, n_samples, outdir_name):
    outdir = os.path.join(OUTPUT_BASE, outdir_name)
    base_dir = os.path.join(OUTPUT_BASE, "base_" + outdir_name)
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(base_dir, exist_ok=True)

    cmd = [
        sys.executable,
        "scripts/inference_swap_video.py",
        "--config",
        "configs/train.yaml",
        "--ckpt",
        "models/REFace/checkpoints/saved.ckpt",
        "--target_video",
        VIDEO,
        "--src_image",
        SOURCE,
        "--outdir",
        outdir,
        "--Base_dir",
        base_dir,
        "--n_samples",
        str(n_samples),
        "--ddim_steps",
        str(ddim_steps),
        "--scale",
        str(scale),
        "--seg12",
        "--faceParser_name",
        "default",
        "--faceParsing_ckpt",
        "Other_dependencies/face_parsing/79999_iter.pth",
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = REFACE_DIR + ":" + env.get("PYTHONPATH", "")

    log_path = f"/tmp/quality_test_{outdir_name}.log"
    write_status("inference", f"{outdir_name}: steps={ddim_steps}, scale={scale}")

    t0 = time.time()
    with open(log_path, "w") as lf:
        proc = subprocess.Popen(
            cmd, cwd=REFACE_DIR, env=env, stdout=lf, stderr=subprocess.STDOUT
        )
        proc.wait()
    elapsed = time.time() - t0

    if proc.returncode != 0:
        with open(log_path) as f:
            tail = f.read()[-500:]
        print(f"FAILED {outdir_name}: exit {proc.returncode}")
        print(tail)
        return None

    model_out = os.path.join(outdir, "model_outputs")
    results = os.path.join(outdir, "results")
    n_model = len(os.listdir(model_out)) if os.path.exists(model_out) else 0
    n_results = len(os.listdir(results)) if os.path.exists(results) else 0
    print(f"{outdir_name}: {n_model} crops, {n_results} composites, {elapsed:.0f}s")
    return {"crops": n_model, "composites": n_results, "time": elapsed}


def main():
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    write_status("init", "Quality comparison: 10 vs 50 DDIM steps")

    configs = [
        ("steps10_scale3.5", 10, 3.5, 1),
        ("steps50_scale3.5", 50, 3.5, 1),
        ("steps50_scale5.0", 50, 5.0, 1),
        ("steps50_scale7.5", 50, 7.5, 1),
    ]

    results = {}
    for name, steps, scale, n in configs:
        write_status("inference", f"Running {name}...")
        print(f"\n=== {name} (steps={steps}, scale={scale}) ===")
        r = run_inference(steps, scale, n, name)
        if r:
            results[name] = r

    write_status("done", f"Quality test complete: {len(results)} configs tested")
    print(f"\nResults: {json.dumps(results, indent=2)}")

    with open(os.path.join(OUTPUT_BASE, "summary.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
