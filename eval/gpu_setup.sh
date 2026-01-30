#!/usr/bin/env bash
# GPU Instance Setup — Run ONCE after SSH into rented GPU
# Usage: bash eval/gpu_setup.sh
#
# Prerequisites: CUDA GPU (A100/4090), conda installed, ~20GB disk space
# Estimated time: 10-15 minutes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENDORS_DIR="$PROJECT_DIR/vendors"

echo "=== WatserFace Evaluation GPU Setup ==="
echo "Project dir: $PROJECT_DIR"
echo "Vendors dir: $VENDORS_DIR"

mkdir -p "$VENDORS_DIR"

# ---------- 1. Eval harness deps ----------
echo ""
echo "[1/4] Installing eval harness dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# ---------- 2. FaceDancer setup ----------
echo ""
echo "[2/4] Setting up FaceDancer..."
if [ ! -d "$VENDORS_DIR/FaceDancer" ]; then
    git clone https://github.com/felixrosberg/FaceDancer.git "$VENDORS_DIR/FaceDancer"
fi

pip install tensorflow-addons opencv-python-headless scipy scikit-image moviepy==1.0.3 imageio imageio-ffmpeg requests tqdm
pip install huggingface_hub

# Download weights
cd "$VENDORS_DIR/FaceDancer"
mkdir -p arcface_model retinaface model_zoo

if [ ! -f "arcface_model/ArcFace-Res50.h5" ]; then
    echo "  Downloading ArcFace weights..."
    huggingface-cli download felixrosberg/ArcFace ArcFace-Res50.h5 --local-dir ./arcface_model/
fi
if [ ! -f "retinaface/RetinaFace-Res50.h5" ]; then
    echo "  Downloading RetinaFace weights..."
    huggingface-cli download felixrosberg/RetinaFace RetinaFace-Res50.h5 --local-dir ./retinaface/
fi
if [ ! -f "model_zoo/FaceDancer_config_c_HQ.h5" ]; then
    echo "  Downloading FaceDancer weights..."
    huggingface-cli download felixrosberg/FaceDancer FaceDancer_config_c_HQ.h5 --local-dir ./model_zoo/
fi

cd "$PROJECT_DIR"

# ---------- 3. REFace setup ----------
echo ""
echo "[3/4] Setting up REFace..."
if [ ! -d "$VENDORS_DIR/REFace" ]; then
    git clone https://github.com/Sanoojan/REFace.git "$VENDORS_DIR/REFace"
fi

cd "$VENDORS_DIR/REFace"

# REFace needs specific torch version — check if torch is already installed
if ! python3 -c "import torch; print(torch.__version__)" 2>/dev/null; then
    pip install torch torchvision torchaudio
fi

if [ -f requirements.txt ]; then
    pip install -r requirements.txt 2>/dev/null || echo "  (some REFace deps may need manual install)"
fi

pip install -e "git+https://github.com/CompVis/taming-transformers.git@master#egg=taming-transformers" 2>/dev/null || true
pip install -e "git+https://github.com/openai/CLIP.git@main#egg=clip" 2>/dev/null || true

# Download REFace checkpoint
mkdir -p models/REFace/checkpoints
if [ ! -f "models/REFace/checkpoints/saved.ckpt" ]; then
    echo "  Downloading REFace checkpoint (~3.8GB)..."
    huggingface-cli download Sanoojan/REFace last.ckpt --local-dir ./models/REFace/checkpoints/
    if [ -f "models/REFace/checkpoints/last.ckpt" ]; then
        mv models/REFace/checkpoints/last.ckpt models/REFace/checkpoints/saved.ckpt
    fi
fi

# Download dependency models
mkdir -p Other_dependencies/face_parsing Other_dependencies/arcface Other_dependencies/DLIB_landmark_det
echo "  NOTE: REFace dependency models (face_parsing, arcface, DLIB) may need manual download."
echo "  See: https://huggingface.co/Sanoojan/REFace/tree/main"
echo "  Place files in vendors/REFace/Other_dependencies/"

cd "$PROJECT_DIR"

# ---------- 4. Verify ----------
echo ""
echo "[4/4] Verifying setup..."
echo -n "  FaceDancer weights: "
[ -f "$VENDORS_DIR/FaceDancer/model_zoo/FaceDancer_config_c_HQ.h5" ] && echo "OK" || echo "MISSING"
echo -n "  REFace checkpoint:  "
[ -f "$VENDORS_DIR/REFace/models/REFace/checkpoints/saved.ckpt" ] && echo "OK" || echo "MISSING"
echo -n "  insightface:        "
python3 -c "import insightface; print('OK')" 2>/dev/null || echo "MISSING"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Place test images: source face + target frames"
echo "  2. Run: bash eval/run_facedancer_eval.sh --source <face.png> --target-dir <frames/>"
echo "  3. Run: bash eval/run_reface_eval.sh --source <face.png> --target-dir <frames/>"
echo "  4. Run: python3 eval/compare_results.py  (after both evals)"
