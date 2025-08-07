#!/usr/bin/env python3
import sys
import subprocess

def main():
    # 1) Install the GPU ONNX runtime
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "--no-cache-dir", "onnxruntime-gpu"
    ], check=True)

    # 2) Install all FaceFusion dependencies for CUDA
    subprocess.run([
        sys.executable, "install.py",
        "--onnxruntime", "cuda",
        "--skip-conda"
    ], check=True)

    # 3) Launch the full FaceFusion UI on your GPU
    subprocess.run([
        sys.executable, "facefusion.py", "run",
        "--execution-providers", "cuda"
    ], check=True)

if __name__ == "__main__":
    main()
