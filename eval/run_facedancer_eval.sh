#!/usr/bin/env bash
# Run FaceDancer evaluation on a set of target frames
# Usage: bash eval/run_facedancer_eval.sh --source <face.png> --target-dir <frames/>
#
# Prerequisites: Run gpu_setup.sh first
# Output: eval/results/facedancer/scores.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENDORS_DIR="$PROJECT_DIR/vendors"
FACEDANCER_DIR="$VENDORS_DIR/FaceDancer"
RESULTS_DIR="$SCRIPT_DIR/results/facedancer"

# Parse args
SOURCE=""
TARGET_DIR=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --source) SOURCE="$2"; shift 2 ;;
        --target-dir) TARGET_DIR="$2"; shift 2 ;;
        --help) echo "Usage: $0 --source <face.png> --target-dir <frames/>"; exit 0 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

if [ -z "$SOURCE" ] || [ -z "$TARGET_DIR" ]; then
    echo "Error: --source and --target-dir are required"
    echo "Usage: $0 --source <face.png> --target-dir <frames/>"
    exit 1
fi

echo "=== FaceDancer Evaluation ==="
echo "Source: $SOURCE"
echo "Target dir: $TARGET_DIR"
echo "Results: $RESULTS_DIR"

# Verify setup
if [ ! -f "$FACEDANCER_DIR/model_zoo/FaceDancer_config_c_HQ.h5" ]; then
    echo "Error: FaceDancer weights not found. Run gpu_setup.sh first."
    exit 1
fi

mkdir -p "$RESULTS_DIR/frames"

# ---------- Step 1: Run FaceDancer on each target frame ----------
echo ""
echo "[1/3] Running FaceDancer inference..."
FRAME_COUNT=0
TOTAL=$(find "$TARGET_DIR" -maxdepth 1 -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) | wc -l | tr -d ' ')
echo "  Processing $TOTAL frames..."

START_TIME=$(date +%s)

for target_img in "$TARGET_DIR"/*.{png,jpg,jpeg}; do
    [ -f "$target_img" ] || continue
    BASENAME=$(basename "$target_img")
    OUTPUT_PATH="$RESULTS_DIR/frames/$BASENAME"

    if [ -f "$OUTPUT_PATH" ]; then
        FRAME_COUNT=$((FRAME_COUNT + 1))
        continue
    fi

    python3 "$FACEDANCER_DIR/test_image_swap_multi.py" \
        --facedancer_path "$FACEDANCER_DIR/model_zoo/FaceDancer_config_c_HQ.h5" \
        --img_path "$target_img" \
        --swap_source "$SOURCE" \
        --img_output "$OUTPUT_PATH" \
        2>/dev/null || echo "  WARN: Failed on $BASENAME"

    FRAME_COUNT=$((FRAME_COUNT + 1))
    if [ $((FRAME_COUNT % 10)) -eq 0 ]; then
        echo "  Processed $FRAME_COUNT/$TOTAL frames..."
    fi
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "  Done: $FRAME_COUNT frames in ${ELAPSED}s"

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
print(f'  Processing:    ${ELAPSED}s total, ~{ELAPSED/max($FRAME_COUNT,1):.1f}s/frame')
"

echo ""
echo "=== FaceDancer evaluation complete ==="
echo "Full results: $RESULTS_DIR/scores.json"
