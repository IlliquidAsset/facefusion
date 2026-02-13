#!/usr/bin/env python3
"""
Quick quality comparison: vary DDIM steps and guidance scale.
Reuses cached alignment data by symlinking to the original results_video dir.
Only processes 8 frames (1 batch) per config to keep it fast.
"""

import os
import sys
import json
import time
import subprocess
import shutil
from datetime import datetime

REFACE_DIR = "/workspace/watserface/vendors/REFace"
CACHED_BASE = os.path.join(REFACE_DIR, "results_video")
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


def run_config(name, ddim_steps, scale):
    outdir = os.path.join(OUTPUT_BASE, name)
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)

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
        CACHED_BASE,
        "--n_samples",
        "8",
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

    log_path = f"/tmp/quality_{name}.log"
    write_status("inference", f"{name}: steps={ddim_steps}, scale={scale}")

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
        print(f"FAILED {name}: exit {proc.returncode}")
        print(tail)
        return None

    model_out = os.path.join(outdir, "model_outputs")
    results_dir = os.path.join(outdir, "results")
    n_crops = len(os.listdir(model_out)) if os.path.exists(model_out) else 0
    n_results = len(os.listdir(results_dir)) if os.path.exists(results_dir) else 0
    print(f"{name}: {n_crops} crops, {n_results} composites, {elapsed:.0f}s")
    return {"crops": n_crops, "composites": n_results, "time": round(elapsed, 1)}


def main():
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    write_status("init", "Quality comparison: steps & scale sweep")

    configs = [
        ("steps10_s3.5", 10, 3.5),
        ("steps25_s3.5", 25, 3.5),
        ("steps50_s3.5", 50, 3.5),
        ("steps50_s5.0", 50, 5.0),
        ("steps50_s7.5", 50, 7.5),
    ]

    results = {}
    for name, steps, scale in configs:
        print(f"\n=== {name} (steps={steps}, scale={scale}) ===")
        r = run_config(name, steps, scale)
        if r:
            results[name] = r

    write_status(
        "done", f"Quality sweep complete: {len(results)}/{len(configs)} configs"
    )
    print(f"\nResults:\n{json.dumps(results, indent=2)}")

    with open(os.path.join(OUTPUT_BASE, "summary.json"), "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
