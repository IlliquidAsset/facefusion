# Face-Swap Evaluation Harness

Standalone evaluation tools for measuring face-swap identity preservation quality. Uses `insightface` (Apache 2.0) directly — no WatserFace/FaceFusion dependencies.

## Setup

```bash
pip install -r eval/requirements.txt
```

The `buffalo_l` model pack will auto-download on first run (~300MB).

## Scripts

### Single-pair identity score

```bash
python eval/eval_identity.py \
  --source source_face.png \
  --target output_face.png \
  --output results.json
```

### Batch evaluation

```bash
python eval/eval_batch.py \
  --source source_face.png \
  --results-dir output_frames/ \
  --output scores.json
```

### Occlusion robustness

```bash
python eval/eval_occlusion.py \
  --source source_face.png \
  --clean-dir clean_results/ \
  --occluded-dir occluded_results/ \
  --output occlusion_scores.json
```

### Prepare test set structure

```bash
python eval/prepare_test_set.py --output-dir eval/test_set
```

Creates subdirectories (`clean/`, `occluded/`, `complex/`, `extreme_angle/`) and a `manifest.json` template. Add your test images manually.

## Embedding models

Default: `arcface` (via insightface's buffalo_l). Pass `--embedding-model auraface` to use AuraFace (not yet implemented — reserved for future use).

## GPU Evaluation (FaceDancer & REFace)

To evaluate candidate architectures on a rented GPU instance:

```bash
# 1. One-time setup (installs deps, clones repos, downloads weights)
bash eval/gpu_setup.sh

# 2. Run FaceDancer evaluation
bash eval/run_facedancer_eval.sh --source face.png --target-dir frames/

# 3. Run REFace evaluation  
bash eval/run_reface_eval.sh --source face.png --target-dir frames/

# 4. Compare results
python3 eval/compare_results.py
```

Results are saved to `eval/results/facedancer/scores.json` and `eval/results/reface/scores.json`. The comparison script generates a decision-ready summary with kill criteria assessment.

**Estimated GPU time**: FaceDancer ~50ms/frame, REFace ~5-15s/frame (50 DDIM steps).

## Output format

All scripts output pretty-printed JSON (indent=2) to stdout or to the path given by `--output`.
