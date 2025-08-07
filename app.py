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
    
    # 2.5) Install training dependencies for Spaces
    try:
        # Install PyTorch CPU version (lighter for Spaces)
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--no-cache-dir", 
            "torch==2.1.0+cpu", 
            "torchvision==0.16.0+cpu", 
            "-f", "https://download.pytorch.org/whl/torch_stable.html"
        ], check=False)
        
        # Install other training dependencies
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--no-cache-dir", 
            "transformers>=4.30.0",
            "diffusers>=0.20.0", 
            "huggingface_hub>=0.16.4",
            "matplotlib>=3.7.0",
            "accelerate>=0.20.3"
        ], check=False)
        
        print("✅ Training dependencies installed successfully")
    except Exception as e:
        print(f"⚠️ Warning: Some training dependencies could not be installed: {e}")

    # 3) Launch the full FaceFusion UI with training tab on your GPU
    subprocess.run([
        sys.executable, "facefusion.py", "run",
        "--execution-providers", "cuda",
        "--ui-layouts", "default", "training"
    ], check=True)

if __name__ == "__main__":
    main()
