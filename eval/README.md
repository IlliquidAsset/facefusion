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

## Output format

All scripts output pretty-printed JSON (indent=2) to stdout or to the path given by `--output`.
