#!/usr/bin/env bash
# Run REFace evaluation on a set of target frames
# Usage: bash eval/run_reface_eval.sh --source <face.png> --target-dir <frames/>
#
# Prerequisites: Run gpu_setup.sh first
# Output: eval/results/reface/scores.json
#
# NOTE: REFace expects folder inputs. This script creates temp folders per-frame
# and collects outputs. REFace is SLOW (~5-15s/frame with 50 DDIM steps).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENDORS_DIR="$PROJECT_DIR/vendors"
REFACE_DIR="$VENDORS_DIR/REFace"
RESULTS_DIR="$SCRIPT_DIR/results/reface"

# Parse args
SOURCE=""
TARGET_DIR=""
DDIM_STEPS=50
SCALE=3.5
while [[ $# -gt 0 ]]; do
    case $1 in
        --source) SOURCE="$2"; shift 2 ;;
        --target-dir) TARGET_DIR="$2"; shift 2 ;;
        --ddim-steps) DDIM_STEPS="$2"; shift 2 ;;
        --scale) SCALE="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 --source <face.png> --target-dir <frames/> [--ddim-steps 50] [--scale 3.5]"
            exit 0 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

if [ -z "$SOURCE" ] || [ -z "$TARGET_DIR" ]; then
    echo "Error: --source and --target-dir are required"
    echo "Usage: $0 --source <face.png> --target-dir <frames/>"
    exit 1
fi

echo "=== REFace Evaluation ==="
echo "Source: $SOURCE"
echo "Target dir: $TARGET_DIR"
echo "DDIM steps: $DDIM_STEPS"
echo "Scale: $SCALE"
echo "Results: $RESULTS_DIR"

# Verify setup
if [ ! -f "$REFACE_DIR/models/REFace/checkpoints/saved.ckpt" ]; then
    echo "Error: REFace checkpoint not found. Run gpu_setup.sh first."
    exit 1
fi

mkdir -p "$RESULTS_DIR/frames"

# REFace needs source in a folder
TEMP_SRC_DIR=$(mktemp -d)
cp "$SOURCE" "$TEMP_SRC_DIR/"

# ---------- Step 1: Run REFace on each target frame ----------
echo ""
echo "[1/3] Running REFace inference..."
FRAME_COUNT=0
TOTAL=$(find "$TARGET_DIR" -maxdepth 1 -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) | wc -l | tr -d ' ')
echo "  Processing $TOTAL frames (expect ~5-15s each)..."

START_TIME=$(date +%s)

for target_img in "$TARGET_DIR"/*.{png,jpg,jpeg}; do
    [ -f "$target_img" ] || continue
    BASENAME=$(basename "$target_img")
    OUTPUT_PATH="$RESULTS_DIR/frames/$BASENAME"

    if [ -f "$OUTPUT_PATH" ]; then
        FRAME_COUNT=$((FRAME_COUNT + 1))
        continue
    fi

    # REFace needs target in a folder too
    TEMP_TGT_DIR=$(mktemp -d)
    TEMP_OUT_DIR=$(mktemp -d)
    TEMP_BASE_DIR=$(mktemp -d)
    cp "$target_img" "$TEMP_TGT_DIR/"

    CUDA_VISIBLE_DEVICES=0 python3 "$REFACE_DIR/scripts/one_inference.py" \
        --outdir "$TEMP_OUT_DIR" \
        --target_folder "$TEMP_TGT_DIR" \
        --src_folder "$TEMP_SRC_DIR" \
        --config "$REFACE_DIR/configs/train.yaml" \
        --ckpt "$REFACE_DIR/models/REFace/checkpoints/saved.ckpt" \
        --Base_dir "$TEMP_BASE_DIR" \
        --n_samples 1 \
        --scale "$SCALE" \
        --ddim_steps "$DDIM_STEPS" \
        2>/dev/null || { echo "  WARN: Failed on $BASENAME"; rm -rf "$TEMP_TGT_DIR" "$TEMP_OUT_DIR" "$TEMP_BASE_DIR"; continue; }

    # Find the output file (REFace puts it in a nested structure)
    REFACE_OUTPUT=$(find "$TEMP_OUT_DIR" -name "*.png" -type f | head -1)
    if [ -n "$REFACE_OUTPUT" ]; then
        cp "$REFACE_OUTPUT" "$OUTPUT_PATH"
    else
        echo "  WARN: No output found for $BASENAME"
    fi

    rm -rf "$TEMP_TGT_DIR" "$TEMP_OUT_DIR" "$TEMP_BASE_DIR"

    FRAME_COUNT=$((FRAME_COUNT + 1))
    ELAPSED_SO_FAR=$(( $(date +%s) - START_TIME ))
    AVG_PER_FRAME=$(echo "scale=1; $ELAPSED_SO_FAR / $FRAME_COUNT" | bc 2>/dev/null || echo "?")
    echo "  [$FRAME_COUNT/$TOTAL] $BASENAME — avg ${AVG_PER_FRAME}s/frame"
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "  Done: $FRAME_COUNT frames in ${ELAPSED}s"

rm -rf "$TEMP_SRC_DIR"

# ---------- Step 2: Run eval harness ----------
echo ""
echo "[2/3] Running identity evaluation..."
python3 "$SCRIPT_DIR/eval_batch.py" \
    --source "$SOURCE" \
    --results-dir "$RESULTS_DIR/frames" \
    --output "$RESULTS_DIR/scores.json"

echo ""
echo "[3/3] Results summary:"
python3 -c "
import json
with open('$RESULTS_DIR/scores.json') as f:
    d = json.load(f)
print(f'  Frames scored: {d[\"num_scored\"]}/{d[\"num_frames\"]}')
print(f'  Mean identity: {d[\"mean_identity\"]:.4f}')
print(f'  P50 identity:  {d[\"p50_identity\"]:.4f}')
print(f'  P95 identity:  {d[\"p95_identity\"]:.4f}')
print(f'  Min identity:  {d[\"min_identity\"]:.4f}')
print(f'  Processing:    ${ELAPSED}s total')
"

echo ""
echo "=== REFace evaluation complete ==="
echo "Full results: $RESULTS_DIR/scores.json"
