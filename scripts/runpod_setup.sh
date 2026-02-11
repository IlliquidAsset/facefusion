#!/bin/bash
# RunPod GPU Environment Setup Script
# 
# This script configures a fresh RunPod A40 instance with all dependencies
# needed for the WatserFace factory and REFace inference.
#
# Usage: bash runpod_setup.sh [--dry-run]
#
# Prerequisites:
# - RunPod pod running with SSH enabled
# - Python 3.11+ available
# - ~50GB free disk space (for models + repo)

set -e

# Configuration
REPO_URL="https://github.com/IlliquidAsset/facefusion.git"
REPO_DIR="/workspace/watserface"
PYTHON_CMD="python3"
DRY_RUN="${1:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_cmd() {
    local cmd="$1"
    local desc="$2"
    
    if [ -n "$DRY_RUN" ]; then
        echo "[DRY-RUN] $desc"
        echo "  $ $cmd"
    else
        log_info "$desc"
        eval "$cmd" || {
            log_error "Failed: $desc"
            return 1
        }
    fi
}

# Main setup
main() {
    log_info "RunPod Setup Starting..."
    
    if [ -n "$DRY_RUN" ]; then
        log_warn "Running in DRY-RUN mode (no changes will be made)"
    fi
    
    # Step 1: Clone repository
    if [ ! -d "$REPO_DIR" ]; then
        run_cmd "git clone $REPO_URL $REPO_DIR" "Cloning WatserFace repository"
    else
        log_warn "Repository already exists at $REPO_DIR, skipping clone"
    fi
    
    # Step 2: Install system dependencies
    run_cmd "apt-get update" "Updating package manager"
    run_cmd "apt-get install -y git curl wget build-essential" "Installing system dependencies"
    
    # Step 3: Install Python dependencies
    run_cmd "cd $REPO_DIR && $PYTHON_CMD -m pip install --upgrade pip setuptools wheel" "Upgrading pip"
    run_cmd "cd $REPO_DIR && $PYTHON_CMD -m pip install -r requirements.txt" "Installing base requirements"
    run_cmd "cd $REPO_DIR && $PYTHON_CMD -m pip install -r requirements-training.txt" "Installing training requirements"
    
    # Step 4: Install factory dependencies
    run_cmd "$PYTHON_CMD -m pip install pyyaml pydantic pyiqa" "Installing factory dependencies"
    
    # Step 5: Install InsightFace + ONNX Runtime GPU
    run_cmd "$PYTHON_CMD -m pip install insightface onnxruntime-gpu" "Installing InsightFace and ONNX Runtime GPU"
    
    # Step 6: Download InsightFace buffalo_l model
    log_info "Downloading InsightFace buffalo_l model (~300MB)..."
    if [ -z "$DRY_RUN" ]; then
        $PYTHON_CMD << 'PYTHON_EOF'
import insightface
import os

# Create model directory
model_dir = os.path.expanduser("~/.insightface/models")
os.makedirs(model_dir, exist_ok=True)

# Load buffalo_l model (auto-downloads if not present)
try:
    app = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_model='retinaface')
    print("[INFO] InsightFace buffalo_l model ready")
except Exception as e:
    print(f"[WARN] InsightFace model download: {e}")
    print("[INFO] Model will be downloaded on first use")
PYTHON_EOF
    else
        echo "[DRY-RUN] Download InsightFace buffalo_l model"
    fi
    
    # Step 7: Run REFace setup (if setup_reface.sh exists)
    if [ -f "$REPO_DIR/scripts/setup_reface.sh" ]; then
        run_cmd "cd $REPO_DIR && bash scripts/setup_reface.sh" "Setting up REFace"
    else
        log_warn "setup_reface.sh not found, skipping REFace setup"
    fi
    
    # Step 8: Smoke test - factory runner help
    run_cmd "cd $REPO_DIR && $PYTHON_CMD -m factory.runner --help" "Running factory smoke test"
    
    # Step 9: Verify GPU availability
    if [ -z "$DRY_RUN" ]; then
        log_info "Checking GPU availability..."
        $PYTHON_CMD << 'PYTHON_EOF'
import torch
if torch.cuda.is_available():
    print(f"[INFO] GPU available: {torch.cuda.get_device_name(0)}")
    print(f"[INFO] CUDA version: {torch.version.cuda}")
    print(f"[INFO] GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("[WARN] No GPU detected (CPU mode only)")
PYTHON_EOF
    fi
    
    log_info "RunPod setup complete!"
    log_info "Repository location: $REPO_DIR"
    log_info "Next: Run factory scenarios with: python -m factory.runner <scenario.yaml>"
}

# Run main
main "$@"
