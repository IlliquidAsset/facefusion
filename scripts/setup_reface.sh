#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENDORS_DIR="$PROJECT_DIR/vendors"
REFACE_DIR="$VENDORS_DIR/REFace"

DRY_RUN=0
SKIP_DEPS=0

PYTHON_BIN=""
if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "Error: python/python3 not found in PATH." >&2
    exit 1
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --skip-deps)
            SKIP_DEPS=1
            shift
            ;;
        --help)
            cat <<'EOF'
Usage: bash scripts/setup_reface.sh [--dry-run] [--skip-deps]

Options:
  --dry-run   Print commands without executing
  --skip-deps Skip dependency installation (still clone/download models)
EOF
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

run_cmd() {
    local cmd="$*"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "[dry-run] $cmd"
        return 0
    fi
    eval "$cmd"
}

echo "=== REFace setup ==="
echo "Project: $PROJECT_DIR"
echo "REFace:  $REFACE_DIR"

run_cmd "mkdir -p \"$VENDORS_DIR\""

if [[ ! -d "$REFACE_DIR/.git" ]]; then
    run_cmd "git clone https://github.com/Sanoojan/REFace.git \"$REFACE_DIR\""
else
    echo "REFace repository already present; skipping clone."
fi

if [[ "$SKIP_DEPS" -eq 0 ]]; then
    run_cmd "$PYTHON_BIN -m pip install --upgrade pip"
    run_cmd "$PYTHON_BIN -m pip install torch torchvision torchaudio"
    run_cmd "$PYTHON_BIN -m pip install huggingface_hub"
    run_cmd "$PYTHON_BIN -m pip install -r \"$REFACE_DIR/requirements.txt\""
    run_cmd "$PYTHON_BIN -m pip install -e \"git+https://github.com/CompVis/taming-transformers.git@master#egg=taming-transformers\""
    run_cmd "$PYTHON_BIN -m pip install -e \"git+https://github.com/openai/CLIP.git@main#egg=clip\""
else
    echo "Skipping dependency installation (--skip-deps)."
fi

run_cmd "mkdir -p \"$REFACE_DIR/models/REFace/checkpoints\""
run_cmd "mkdir -p \"$REFACE_DIR/Other_dependencies/face_parsing\""
run_cmd "mkdir -p \"$REFACE_DIR/Other_dependencies/arcface\""
run_cmd "mkdir -p \"$REFACE_DIR/Other_dependencies/DLIB_landmark_det\""

if [[ ! -f "$REFACE_DIR/models/REFace/checkpoints/saved.ckpt" ]]; then
    run_cmd "$PYTHON_BIN -m huggingface_hub.commands.huggingface_cli download Sanoojan/REFace last.ckpt --local-dir \"$REFACE_DIR/models/REFace/checkpoints\""
    run_cmd "mv \"$REFACE_DIR/models/REFace/checkpoints/last.ckpt\" \"$REFACE_DIR/models/REFace/checkpoints/saved.ckpt\""
else
    echo "Checkpoint already present; skipping download."
fi

if [[ ! -f "$REFACE_DIR/Other_dependencies/face_parsing/79999_iter.pth" ]]; then
    run_cmd "$PYTHON_BIN -m huggingface_hub.commands.huggingface_cli download Sanoojan/REFace Other_dependencies/face_parsing/79999_iter.pth --local-dir \"$REFACE_DIR\""
fi

if [[ ! -f "$REFACE_DIR/Other_dependencies/arcface/model_ir_se50.pth" ]]; then
    run_cmd "$PYTHON_BIN -m huggingface_hub.commands.huggingface_cli download Sanoojan/REFace Other_dependencies/arcface/model_ir_se50.pth --local-dir \"$REFACE_DIR\""
fi

if [[ ! -f "$REFACE_DIR/Other_dependencies/DLIB_landmark_det/shape_predictor_68_face_landmarks.dat" ]]; then
    run_cmd "$PYTHON_BIN -m huggingface_hub.commands.huggingface_cli download Sanoojan/REFace Other_dependencies/DLIB_landmark_det/shape_predictor_68_face_landmarks.dat --local-dir \"$REFACE_DIR\""
fi

echo ""
echo "Setup complete."
echo "Checkpoint: $REFACE_DIR/models/REFace/checkpoints/saved.ckpt"
