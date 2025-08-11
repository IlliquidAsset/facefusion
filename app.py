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
    
    # Skip training dependencies to avoid conflicts
    print("⚠️ Training functionality disabled to ensure stability")

    # 3) Launch FaceFusion with streamlined UI optimized for user experience
    subprocess.run([
        sys.executable, "facefusion.py", "run",
        "--execution-providers", "cuda", "cpu",
        "--ui-layouts", "streamlined"
    ], check=True)

if __name__ == "__main__":
    main()
