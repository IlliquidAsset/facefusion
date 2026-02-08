# WatserFace Software Factory

> Scenario-driven quality validation for face-swap outputs.

## What is the Factory?

The Factory is a structured testing framework inspired by the [StrongDM factory model](https://www.strongdm.com/) for validating face-swap visual quality at scale. Rather than manual spot-checks, it defines quality expectations as declarative YAML scenarios that are executed against the WatserFace pipeline and evaluated through metric gates, an optional LLM-based perceptual judge, and golden reference comparisons.

Each scenario specifies a swap configuration (source image, target frame, preset), a set of metric assertions (SSIM, PSNR, identity similarity, etc.), and optional perceptual evaluation dimensions. The runner loads scenarios, orchestrates the face swap, measures outputs against gates, and produces a structured pass/fail report. This enables repeatable, automated quality assurance as the pipeline evolves.

## Quick Start

```bash
# Run all critical scenarios
python -m factory.runner factory/scenarios/definitions/ --priority critical

# Run with LLM judge enabled
python -m factory.runner factory/scenarios/definitions/ --llm-judge

# Write JSON report
python -m factory.runner factory/scenarios/definitions/ --output-json results.json

# Skip certain scenario types
python -m factory.runner factory/scenarios/definitions/ --skip-types comparative regression
```

## Populating Fixtures

Fixture images must be user-provided and cannot be shipped in the repository due to privacy and licensing concerns. See [factory/fixtures/README.md](fixtures/README.md) for detailed setup instructions.

```
factory/fixtures/
├── source_faces/
│   └── default.png          # Source identity image
├── target_frames/
│   ├── default.png          # Clean target frame
│   └── occluded.png         # Target with occlusion
├── target_videos/
│   ├── short_clip.mp4       # ~5s test video
│   └── thirty_seconds.mp4   # 30s stress test video
└── golden/                  # Managed by GoldenRegistry
```

Scenarios will gracefully skip when referenced fixtures are missing, so you can run the suite at any time without populating every file.

## Writing Scenarios

Scenarios are YAML files in `factory/scenarios/definitions/`. Each defines a swap setup, metric assertions, and optional judge/golden config:

```yaml
name: swap_identity_preservation
description: "Basic face swap with Balanced preset — validates identity is preserved"
type: visual_quality
priority: critical
tags: [identity, core, balanced]
setup:
  source_image: source_faces/default.png
  target_image: target_frames/default.png
  preset: balanced
assertions:
  metrics:
    - metric: identity_similarity
      operator: ">="
      value: 0.65
    - metric: ssim
      operator: ">="
      value: 0.70
  llm_judge:
    enabled: true
    model: claude-sonnet-4-20250514
    min_samples: 3
    dimensions:
      identity_preservation: 6.0
      boundary_blending: 5.0
```

### Available Metrics

| Metric | Range | Notes |
|--------|-------|-------|
| `ssim` | [0, 1] | Structural similarity (higher = better) |
| `psnr` | [0, +inf) | Peak signal-to-noise ratio (higher = better) |
| `identity_similarity` | [0, 1] | Raw cosine similarity clamped [0,1] -- NOT (x+1)/2 |
| `blur_score` | [0, 1] | Laplacian variance normalized (higher = sharper) |
| `artifact_score` | [0, 1] | Edge artifact detection (lower = better) |
| `lpips` | [0, 1+] | Perceptual distance via pyiqa (lower = better) |
| `overall_score` | [0, 1] | Weighted composite score |

### Scenario Types

| Type | Description |
|------|-------------|
| `visual_quality` | Single swap, evaluate metrics + optional LLM judge |
| `performance` | Swap with VRAM/timing tracking |
| `comparative` | Two-preset comparison (not yet wired) |
| `regression` | Golden reference comparison (not yet wired) |

## LLM Judge

The LLM judge is an opt-in perceptual evaluator enabled via `--llm-judge`. It requires `ANTHROPIC_API_KEY` to be set. When the key is missing or empty, the judge gracefully skips and marks results as `skipped=True`.

The judge evaluates 5 perceptual dimensions on a 1-10 scale:

- **Identity Preservation** -- Does the output look like the source person?
- **Boundary Blending** -- Are face-background seams visible?
- **Lighting Consistency** -- Does lighting match the target scene?
- **Expression Naturalness** -- Does the expression look natural?
- **Uncanny Valley** -- Does the result avoid the uncanny valley?

Judge results are **advisory only** and do not affect the pass/fail status of a scenario. Multiple samples are aggregated (median + mean) for stability.

## Golden References

Golden references are baseline outputs that you register once, then compare future runs against to detect regressions. They are managed via `GoldenRegistry`:

```python
from factory.golden.registry import GoldenRegistry

registry = GoldenRegistry(Path("factory/fixtures/golden"))

# Register a baseline
registry.register("swap_identity_preservation", Path("output.png"))

# Later, retrieve it for comparison
entry = registry.get("swap_identity_preservation")
```

The `GoldenComparator` computes SSIM and LPIPS distances between a new output and the registered golden image, reporting whether the result falls within tolerance.

## Architecture

```
Scenario YAML --> Loader --> Runner
                               |-- Orchestrator (face swap)
                               |-- MetricGate (SSIM, PSNR, LPIPS, etc.)
                               |-- PerformanceTracker (VRAM, timing)
                               |-- VisionJudge (LLM perceptual eval)
                               +-- GoldenComparator (regression)
```

Key modules:

| Module | Path | Purpose |
|--------|------|---------|
| Schema | `factory/scenarios/schema.py` | Pydantic models for scenario YAML |
| Loader | `factory/scenarios/loader.py` | Parse + validate YAML files |
| Runner | `factory/runner.py` | CLI + orchestration logic |
| MetricGate | `factory/gates/metrics.py` | Compute and gate on quality metrics |
| PerformanceTracker | `factory/gates/performance.py` | VRAM + timing measurement |
| VisionJudge | `factory/judges/vision_judge.py` | LLM-based perceptual evaluation |
| Aggregator | `factory/judges/aggregator.py` | Multi-sample judge aggregation |
| GoldenRegistry | `factory/golden/registry.py` | Register and retrieve baselines |
| GoldenComparator | `factory/golden/comparator.py` | Compare outputs to golden refs |
| Orchestrator | `factory/orchestrator.py` | Face-swap execution (passthrough stub) |
| StateIsolator | `factory/state_isolator.py` | Isolate global state during runs |
| Identity | `factory/identity.py` | Compute identity cosine similarity |

## pytest Integration

```bash
# Discover all tests
pytest factory/ --collect-only

# Run only schema validation tests (fast, no GPU)
pytest factory/test_scenarios.py -k "test_scenario_loads"

# Run with custom markers
pytest factory/ -m "not gpu"
```

## Version

v0.1.0 -- Initial release. Orchestrator swap is a passthrough stub; comparative and regression scenarios are stubs.
