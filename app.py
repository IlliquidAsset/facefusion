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
    
    # 2.5) Install basic training dependencies (lightweight ones)
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--no-cache-dir", "matplotlib", "numpy", "pillow"
        ], check=False)  # Don't fail if these don't install
    except Exception:
        print("Warning: Some training dependencies could not be installed")

    # 3) Launch the full FaceFusion UI with training tab on your GPU
    subprocess.run([
        sys.executable, "facefusion.py", "run",
        "--execution-providers", "cuda",
        "--ui-layouts", "default", "training"
    ], check=True)

if __name__ == "__main__":
    main()
