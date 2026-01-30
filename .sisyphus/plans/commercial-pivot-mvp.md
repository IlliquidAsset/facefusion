# WatserFace Commercial Pivot: Architecture Evaluation & MVP

## TL;DR

> **Quick Summary**: Evaluate FaceDancer and REFace as replacement architectures for WatserFace's compositing pipeline, resolve licensing constraints, and build a CLI-based MVP that a small adult studio could use for face synthesis on pre-shot footage. The social mission: reduce exploitation in adult film by enabling consenting people to license their likeness without being physically present.
> 
> **Deliverables**:
> - Legal/license clearance (Phase 0 gate)
> - Architecture evaluation with hard identity-score kill criteria (Phase 1)
> - Fine-tuned model achieving 0.90+ identity score (Phase 2)
> - Working CLI tool: source face + target footage folder in, swapped frames out (Phase 3)
> 
> **Estimated Effort**: Large (6-10 weeks)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Legal clearance -> Architecture eval -> Fine-tune winner -> MVP CLI
> **Total Budget**: <$5,000 (GPU rental ~$800-$2,000, legal ~$200-$300, remainder for iteration)

---

## Context

### Original Request
Commercialize WatserFace as a face-swap tool for the adult film industry. Social mission: reduce the need for physical actors and the subsequent abuse/exploitation. Consenting real people license their likeness. Bootstrapping with <$5k budget.

### Interview Summary
**Key Discussions**:
- Current compositing pipeline (5-model stack) caps at ~0.80-0.82 identity score. Commercial adult content requires ~0.90+ because the face IS the product.
- Devil's Advocate exercise across 3 rounds revealed diminishing returns on compositing refinement and that a single highest-leverage fix (mask hardening) outperforms months of layering work.
- FaceDancer (MIT, WACV 2023) and REFace (Apache 2.0, WACV 2025) identified as alternative single-stage architectures that handle occlusion natively.
- FaceFusion's OpenRAIL-AS license explicitly prohibits the intended use case. User believes codebase has diverged sufficiently to relicense, and is comfortable with ground-up rewrite if needed.
- Hardware: M4 MacBook Air 16GB (development only, not training). Training requires rented GPUs.
- Target customers: small adult studios. No committed first customer yet.

**Research Findings**:
- FaceDancer: Single-stage, IFSR preserves occlusion/pose/lighting natively, MIT license, 256px native (needs upscaling)
- REFace: Diffusion-based, self-supervised inpainting framing, 512px native, 4.7s/frame, Apache 2.0
- FRVD (July 2025): Video diffusion with best temporal consistency, but unclear licensing
- GPU rental market: A100 80GB at ~$1.27/hr (Vast.ai), RTX 4090 at ~$0.35/hr
- Current WatserFace: ~10,615 lines custom / ~37,603 total (28% custom, 72% FaceFusion-derived)

### Metis Review
**Identified Gaps** (addressed below):
- No legal gate before technical work (added as Phase 0)
- No target resolution/framerate specified (added to acceptance criteria)
- No identity score kill criteria for evaluation phase (added: 0.85 minimum to proceed)
- No consent verification mechanism defined (scoped to JSON manifest for MVP)
- No first-customer validation (added as parallel task)
- Training data provenance risk for candidate models (added to legal review)
- Budget breakdown not formalized (added per-phase caps)

---

## Work Objectives

### Core Objective
Determine whether FaceDancer or REFace (or neither) can replace WatserFace's compositing pipeline at commercial quality (0.90+ identity score), then build a minimum viable product around the winning architecture.

### Concrete Deliverables
1. Legal opinion or decision on licensing path (clean-room vs. relicense vs. new foundation)
2. Quantitative evaluation report: identity scores, processing time, resolution, occlusion handling for FaceDancer and REFace on standardized test set
3. Fine-tuned model optimized for the target domain
4. CLI tool: `watserface-swap --source face.png --target-dir ./frames/ --output-dir ./output/`
5. Consent manifest schema and validator

### Definition of Done
- [ ] Legal path resolved with documented decision
- [ ] Architecture chosen with quantitative justification
- [ ] Identity score >= 0.90 (AuraFace cosine similarity — Apache 2.0 replacement for ArcFace) on 95th percentile of test frames
- [ ] Output resolution >= 1024x1024 (upscaled if base model is smaller)
- [ ] CLI processes a folder of frames unattended (no per-frame manual intervention)
- [ ] Processing speed: 30 minutes of 1080p30 footage completes in under 48 hours on single A100
- [ ] Consent manifest JSON included with every output

### Must Have
- Single-stage face swap (no compositing pipeline)
- Native occlusion handling (model understands what's in front of the face)
- Identity conditioning at inference time (no retraining per source identity)
- Batch processing (folder in, folder out)
- Works on rented A100/4090 for processing, M4 Mac for development
- MIT or Apache 2.0 compatible licensing throughout

### Must NOT Have (Guardrails)
- NO training from scratch (fine-tuning only, budget doesn't support full training)
- NO web UI in MVP (CLI + config file only — UI is v2)
- NO real-time processing (batch-only — real-time is v2)
- NO multi-face scenes in MVP (single face swap per frame — multi-face is v2)
- NO audio/lip-sync (visual-only — audio is a separate product)
- NO configurable multi-backend abstraction (pick ONE architecture, commit to it)
- NO compositing pipeline carryover (if new architecture handles occlusion natively, delete old code)
- NO FaceFusion-derived code in the commercial product (clean licensing)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest, 56+ existing tests)
- **User wants tests**: YES (automated verification for identity scores and quality gates)
- **Framework**: pytest + custom eval scripts

### Automated Verification Approach

Each phase has hard kill criteria verified by automated scripts. No subjective "looks good enough."

**Identity Measurement**:
```bash
# Standardized identity evaluation
python eval_identity.py \
  --source faces/source.png \
  --target-dir frames/ \
  --output-dir results/ \
  --model arcface
# Output: results/identity_scores.json
# Contains: per-frame cosine similarity, p50, p95, mean, min
```

**Quality Gate Pattern**:
```bash
# Phase 1 gate: proceed if p95 identity >= 0.85
jq '.p95_identity >= 0.85' results/identity_scores.json
# Phase 2 gate: proceed if p95 identity >= 0.90
jq '.p95_identity >= 0.90' results/identity_scores.json
```

---

## Execution Strategy

### Parallel Execution Waves

```
Pre-Phase (Immediate - Before anything):
└── Task -1: Branch Strategy (archive master → legacy/v0.10-compositing, create clean master)

Phase 0 (Immediate - Week 1):
├── Task 0: Legal/License Resolution [GATE - blocks everything]
└── Task 0.5: Customer Discovery (parallel, no dependency)

Phase 1 (After Phase 0 - Week 2-3):
├── Task 1: Build Evaluation Harness [no dependency beyond Phase 0]
├── Task 2: Evaluate FaceDancer [depends: 1]
└── Task 3: Evaluate REFace [depends: 1, parallel with 2]
    └── Task 4: Architecture Decision [depends: 2, 3] [GATE - kill if neither hits 0.85]

Phase 2 (After Phase 1 - Week 4-6):
├── Task 5: Training Data Pipeline [depends: 4]
├── Task 6: Fine-Tune Winning Architecture [depends: 5]
└── Task 7: Upscaling Integration [depends: 4, parallel with 5-6]

Phase 3 (After Phase 2 - Week 7-9):
├── Task 8: CLI Tool [depends: 6, 7]
├── Task 9: Consent Manifest System [depends: 4, parallel with 8]
└── Task 10: End-to-End Validation [depends: 8, 9]

Critical Path: Task -1 → Task 0 → Task 1 → Task 2/3 → Task 4 → Task 5 → Task 6 → Task 8 → Task 10
```

### Budget Allocation

| Phase | Budget Cap | Purpose |
|-------|-----------|---------|
| Phase 0 | $300 | Legal consultation |
| Phase 1 | $50 | GPU rental for evaluation (few hours) |
| Phase 2 | $1,500 | GPU rental for fine-tuning (multiple runs) |
| Phase 3 | $200 | GPU rental for validation runs |
| Reserve | $1,950 | Iteration, unexpected costs, second training run |
| **Total** | **$4,000 allocated, $1,000 reserve** | |

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| -1 | None | 0, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | None |
| 0 | -1 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | 0.5 |
| 0.5 | None | None (informational) | 0 |
| 1 | 0 | 2, 3 | None |
| 2 | 1 | 4 | 3 |
| 3 | 1 | 4 | 2 |
| 4 | 2, 3 | 5, 6, 7, 8, 9 | None (decision point) |
| 5 | 4 | 6 | 7 |
| 6 | 5 | 8 | 7 |
| 7 | 4 | 8 | 5, 6 |
| 8 | 6, 7 | 10 | 9 |
| 9 | 4 | 10 | 5, 6, 7, 8 |
| 10 | 8, 9 | None (final) | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Approach |
|------|-------|---------------------|
| Phase 0 | 0, 0.5 | Human tasks (legal, customer outreach) — plan provides checklists |
| Phase 1 | 1, 2, 3, 4 | delegate_task(category="ultrabrain") for eval harness; category="quick" for individual evals |
| Phase 2 | 5, 6, 7 | delegate_task(category="unspecified-high") — GPU-intensive, iterative |
| Phase 3 | 8, 9, 10 | delegate_task(category="unspecified-high") for CLI; category="quick" for manifest |

---

## TODOs

---

### Pre-Phase: Branch Strategy

---

- [x] -1. Archive Current Master & Create Clean Branch [DONE]

  **What to do**:
  - Archive current master branch as `legacy/v0.10-compositing` (preserves all compositing pipeline work, XSeg research, lip deformation layers, Mayo strategy — fully recoverable)
  - Create a new clean `master` branch from the archive point
  - Remove FaceFusion-derived source code from new master (keep: .sisyphus/, docs/, eval test images, scripts that are fully original)
  - Keep git history intact on the legacy branch — nothing is lost
  - Update README.md on new master to reflect commercial pivot (remove FaceFusion attribution from product description, keep in ATTRIBUTION.md for historical record)
  - The new master starts lean: plans, eval harness (Task 1), and new architecture code going forward

  **Exact commands**:
  ```bash
  # 1. Tag the current state for easy reference
  git tag v0.10.0-compositing-final -m "Final state of compositing pipeline before commercial pivot"

  # 2. Create legacy branch from current master
  git branch legacy/v0.10-compositing master

  # 3. Stay on master, begin cleanup
  # (Subsequent tasks will remove FaceFusion-derived code as the new architecture is built)
  ```

  **What stays on new master**:
  - `.sisyphus/` — all plans, notepads, learnings (institutional knowledge)
  - `docs/` — legal decisions, architecture decisions, validation reports
  - `eval/` — evaluation harness (to be built in Task 1)
  - `test_quality/` — test images (zBam.png, Sam_Generated.png — original test assets)
  - `scripts/` — original scripts (evaluation, comparison grids)
  - `.github/` — CI workflows (to be updated)
  - `ROADMAP.md`, `CHANGELOG.md` — updated for new direction

  **What gets removed from new master (over Phase 1-2, not immediately)**:
  - `watserface/` package (FaceFusion-derived core — replaced by new architecture)
  - `venv/` (rebuild with new dependencies)
  - FaceFusion-specific configs (`watserface.ini`)

  **Must NOT do**:
  - Do NOT delete the legacy branch ever — it's the full history of R&D
  - Do NOT force-push or rewrite history — clean branch divergence only
  - Do NOT remove test images or .sisyphus knowledge base

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard git branching operations
  - **Skills**: [`git-master`]
    - `git-master`: Branch management, tagging, safe operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (must be first)
  - **Blocks**: All subsequent tasks
  - **Blocked By**: None

  **References**:
  - Current branch state: `git log --oneline -5` for recent commits
  - `ATTRIBUTION.md` — FaceFusion attribution to preserve

  **Acceptance Criteria**:
  ```bash
  # Legacy branch exists
  git branch --list 'legacy/v0.10-compositing' | grep -q 'legacy'

  # Tag exists
  git tag --list 'v0.10.0-compositing-final' | grep -q 'v0.10'

  # We're on master
  git branch --show-current | grep -q 'master'

  # Legacy branch has the full compositing codebase
  git ls-tree --name-only legacy/v0.10-compositing | grep -q 'watserface'

  # .sisyphus preserved on master
  test -d .sisyphus/plans
  test -d .sisyphus/notepads
  ```

  **Commit**: YES
  - Message: `chore: archive compositing pipeline, prepare for commercial pivot`
  - Files: Updated README.md, any cleanup
  - Pre-commit: `git branch --list 'legacy/v0.10-compositing' | grep -q 'legacy'`

---

### Phase 0: Legal & Business Foundation

---

- [x] 0. Legal/License Resolution [GATE]

  **What to do**:
  - Audit FaceFusion-derived code: identify every file in watserface/ that is substantially copied from FaceFusion (the 72% non-custom code)
  - Categorize each file: (a) unmodified FaceFusion, (b) heavily modified, (c) fully original
  - Determine if commercial use in adult content is viable under any interpretation of OpenRAIL-AS
  - Research FaceDancer (MIT) and REFace (Apache 2.0) license compatibility with commercial adult content
  - Research training data provenance: what datasets were FaceDancer and REFace trained on? Do those datasets have terms restricting NSFW use? (CelebA, FFHQ, VGGFace2 — check each)
  - Research deepfake legislation in user's jurisdiction (US states with criminal penalties for synthetic sexual content)
  - Decision: (a) relicense WatserFace custom code under permissive license + build new foundation, OR (b) clean-room rewrite everything, OR (c) negotiate with FaceFusion author
  - Document decision with rationale

  **Must NOT do**:
  - Do not write any commercial code before this task completes
  - Do not assume "diverged enough" is legally sufficient without analysis

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Legal analysis requires careful reasoning about license implications across multiple codebases
  - **Skills**: [`git-master`]
    - `git-master`: Need git blame/log to trace code provenance to FaceFusion vs. original
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser automation needed
    - `frontend-ui-ux`: No UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 0.5)
  - **Parallel Group**: Wave 0 (with Task 0.5)
  - **Blocks**: ALL subsequent tasks
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `watserface/` — entire package directory, trace each .py file origin via `git log --follow`
  - `ATTRIBUTION.md` — documents what came from FaceFusion
  - `CHANGELOG.md` — documents WatserFace modifications

  **External References**:
  - FaceFusion license: https://github.com/facefusion/facefusion/blob/master/LICENSE.md (OpenRAIL-AS full text)
  - FaceDancer license: https://github.com/felixrosberg/FaceDancer/blob/main/LICENSE (MIT)
  - REFace repo: https://github.com/Sanoojan/REFace (Apache 2.0)
  - CelebA terms: https://mmlab.ie.cuhk.edu.hk/projects/CelebA.html
  - FFHQ terms: https://github.com/NVlabs/ffhq-dataset

  **Acceptance Criteria**:

  ```bash
  # Verify decision document exists
  test -f docs/legal/license-decision.md
  # Verify it contains required sections
  grep -q "## Decision" docs/legal/license-decision.md
  grep -q "## FaceFusion Derivation Analysis" docs/legal/license-decision.md
  grep -q "## Training Data Provenance" docs/legal/license-decision.md
  grep -q "## Jurisdiction Risk" docs/legal/license-decision.md
  ```

  **Commit**: YES
  - Message: `docs(legal): license decision and code provenance analysis`
  - Files: `docs/legal/license-decision.md`
  - Pre-commit: None

---

- [ ] 0.5. Customer Discovery (Human Task)

  **What to do**:
  - Identify 3-5 small adult production studios or independent producers
  - Reach out with value proposition: "What if your performers didn't need to be on set for every scene?"
  - Validate: Would they pay for this? What quality bar do they require? What's their current workflow?
  - Document: pricing sensitivity, quality expectations, format requirements (resolution, framerate, codec)
  - This is a human networking task — the plan documents what to ask, not how to find contacts

  **Questions to ask potential customers**:
  1. What resolution/framerate do you deliver in? (1080p30? 4K60?)
  2. How much would you pay per minute of processed footage?
  3. What's your biggest production cost that this could reduce?
  4. Would you accept 48-hour turnaround for a 30-minute scene?
  5. Is consent verification documentation important to your business? (legal cover)
  6. What occlusion scenarios matter most? (hands on face, body-on-body, hair, props)

  **Must NOT do**:
  - Do not build features based on assumed needs — validate first
  - Do not promise timelines or capabilities

  **Recommended Agent Profile**:
  - **Category**: N/A (Human task)

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 0)
  - **Parallel Group**: Wave 0 (with Task 0)
  - **Blocks**: Nothing (informational, feeds into Phase 3 priorities)
  - **Blocked By**: None

  **References**: None (human networking task)

  **Acceptance Criteria**:
  ```bash
  # Verify customer discovery notes exist
  test -f docs/business/customer-discovery.md
  # Contains at least one interview
  grep -c "## Interview:" docs/business/customer-discovery.md | xargs test 1 -le
  ```

  **Commit**: YES
  - Message: `docs(business): customer discovery notes`
  - Files: `docs/business/customer-discovery.md`

---

### Phase 1: Architecture Evaluation

---

- [ ] 1. Build Evaluation Harness

  **What to do**:
  - Create `eval/` directory with standardized evaluation scripts
  - `eval/eval_identity.py`: Takes source face + output face, computes ArcFace cosine similarity
  - `eval/eval_batch.py`: Runs identity eval across a folder of frame pairs, outputs JSON with p50, p95, mean, min scores
  - `eval/eval_occlusion.py`: Specifically tests frames with known occlusions (corndog test, hand-over-face)
  - `eval/prepare_test_set.py`: Assembles a standardized test set of 50-100 frame pairs:
    - 30% clean (no occlusion) — baseline quality
    - 30% simple occlusion (single object: hand, food, phone)
    - 20% complex occlusion (multiple objects, hair, fingers spread)
    - 20% extreme angles (profile, 45+ degree yaw)
  - Use existing test images (zBam.png, Sam_Generated.png) plus additional pairs from public datasets
  - All metrics output as JSON for automated comparison
  - ArcFace model: use existing watserface/face_recognizer.py or standalone insightface

  **Must NOT do**:
  - Do not use any FaceFusion-derived code in eval harness if legal decision says clean-room
  - Do not include subjective quality assessments — metrics only

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Evaluation framework requires careful metric design and robust scripting
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser needed
    - `git-master`: No git operations in this task

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (first in Phase 1)
  - **Blocks**: Tasks 2, 3
  - **Blocked By**: Task 0

  **References**:

  **Pattern References**:
  - `watserface/face_recognizer.py` — existing ArcFace integration for identity scoring
  - `test_quality/` — existing quality output directory structure
  - `scripts/run_lip_deformation_eval.py` — example of metrics pipeline (SSIM, edge SSIM, LAB color shift)

  **External References**:
  - ArcFace/InsightFace: https://github.com/deepinsight/insightface (identity embedding extraction)
  - FaceDancer eval code: https://github.com/felixrosberg/FaceDancer (their eval scripts for reference)

  **Acceptance Criteria**:
  ```bash
  # Eval scripts exist and are executable
  python eval/eval_identity.py --help  # exits 0
  python eval/eval_batch.py --help     # exits 0
  
  # Test set prepared
  ls eval/test_set/clean/ | wc -l       # >= 15 pairs
  ls eval/test_set/occluded/ | wc -l    # >= 15 pairs
  ls eval/test_set/extreme/ | wc -l     # >= 10 pairs
  
  # Smoke test: eval on one pair produces valid JSON
  python eval/eval_identity.py --source eval/test_set/clean/source_01.png --target eval/test_set/clean/target_01.png --output /tmp/test.json
  jq '.identity_score' /tmp/test.json   # returns a float
  ```

  **Commit**: YES
  - Message: `feat(eval): standardized evaluation harness with identity scoring`
  - Files: `eval/*.py`, `eval/test_set/`
  - Pre-commit: `python eval/eval_identity.py --help`

---

- [ ] 2. Evaluate FaceDancer

  **What to do**:
  - Clone FaceDancer repo: https://github.com/felixrosberg/FaceDancer
  - Set up environment (may need separate venv/conda)
  - Download pretrained model weights
  - Run inference on the standardized test set from Task 1
  - Measure: identity score (ArcFace), processing time per frame, output resolution, SSIM
  - Specifically test occlusion handling: run on corndog frames, hand-over-face frames
  - Document: which occlusion types it handles well vs. poorly
  - Note: FaceDancer native resolution is 256×256 — measure raw AND with GFPGAN upscaling to 1024
  - Generate comparison grid: source | target | FaceDancer output | upscaled output
  - All results in `eval/results/facedancer/`

  **Must NOT do**:
  - Do not fine-tune yet — evaluation only with pretrained weights
  - Do not integrate into WatserFace codebase — standalone evaluation

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: External repo setup, model download, GPU inference
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 3)
  - **Parallel Group**: Wave 1 (with Task 3)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - FaceDancer repo: https://github.com/felixrosberg/FaceDancer
  - FaceDancer paper: https://openaccess.thecvf.com/content/WACV2023/papers/Rosberg_FaceDancer_Pose-_and_Occlusion-Aware_High_Fidelity_Face_Swapping_WACV_2023_paper.pdf
  - Key architecture: Adaptive Feature Fusion Attention (AFFA) + Interpreted Feature Similarity Regularization (IFSR)

  **Acceptance Criteria**:
  ```bash
  # Results JSON exists with all required metrics
  test -f eval/results/facedancer/scores.json
  jq '.mean_identity' eval/results/facedancer/scores.json  # returns float
  jq '.p95_identity' eval/results/facedancer/scores.json   # returns float
  jq '.mean_time_seconds' eval/results/facedancer/scores.json
  jq '.output_resolution' eval/results/facedancer/scores.json
  
  # Comparison grid generated
  test -f eval/results/facedancer/comparison_grid.png
  
  # Occlusion-specific results
  jq '.occlusion_scores' eval/results/facedancer/scores.json | jq length  # >= 10
  ```

  **Commit**: YES
  - Message: `eval(facedancer): baseline evaluation on standardized test set`
  - Files: `eval/results/facedancer/`
  - Pre-commit: `test -f eval/results/facedancer/scores.json`

---

- [ ] 3. Evaluate REFace

  **What to do**:
  - Clone REFace repo: https://github.com/Sanoojan/REFace
  - Set up environment (likely needs diffusers, transformers, torch)
  - Download pretrained model weights
  - Run inference on same standardized test set from Task 1
  - Measure: identity score (ArcFace), processing time per frame, output resolution, SSIM
  - Specifically test occlusion handling on same frames as Task 2
  - Note: REFace is 512×512 native — measure raw AND with upscaling to 1024
  - Note: REFace uses diffusion (4.7s/frame reported) — document actual timing on A100 vs 4090
  - Generate same comparison grid format as Task 2
  - All results in `eval/results/reface/`

  **Must NOT do**:
  - Do not fine-tune yet — evaluation only with pretrained weights
  - Do not integrate into WatserFace codebase — standalone evaluation

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: External repo setup, diffusion model, GPU inference
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 2)
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - REFace repo: https://github.com/Sanoojan/REFace
  - REFace paper: https://openaccess.thecvf.com/content/WACV2025/papers/Baliah_Realistic_and_Efficient_Face_Swapping_A_Unified_Approach_with_Diffusion_WACV_2025_paper.pdf
  - Key architecture: DDIM sampling, CLIP feature disentanglement, mask shuffling for occlusion

  **Acceptance Criteria**:
  ```bash
  # Same structure as Task 2
  test -f eval/results/reface/scores.json
  jq '.mean_identity' eval/results/reface/scores.json
  jq '.p95_identity' eval/results/reface/scores.json
  jq '.mean_time_seconds' eval/results/reface/scores.json
  
  test -f eval/results/reface/comparison_grid.png
  jq '.occlusion_scores' eval/results/reface/scores.json | jq length  # >= 10
  ```

  **Commit**: YES
  - Message: `eval(reface): baseline evaluation on standardized test set`
  - Files: `eval/results/reface/`

---

- [ ] 4. Architecture Decision [GATE]

  **⚠️ UPDATE (2026-01-30 — License Decision)**: FaceDancer code is CC BY-NC-SA 4.0, so it CANNOT be the commercial architecture regardless of quality. REFace architecture (MIT) is the only viable path. Evaluation of both is still useful to establish quality ceilings and calibrate expectations, but the commercial decision is effectively pre-determined: REFace architecture + SD initialization + AuraFace identity encoder.

  **What to do**:
  - Compare FaceDancer and REFace results side-by-side
  - Create decision matrix weighing: identity score, occlusion handling, speed, resolution, license, fine-tunability
  - Apply kill criteria:
    - If REFace pretrained weights achieve p95 identity >= 0.85: proceed (quality ceiling is reachable with fine-tuning)
    - If REFace does NOT hit 0.85 but FaceDancer DOES: we know the quality is achievable architecturally but REFace may need more training data/compute. Proceed cautiously.
    - If NEITHER hits 0.85: **STOP. Reassess entire approach.** Options: (a) evaluate FRVD if licensing clears, (b) explore other diffusion-based architectures
  - Document decision with quantitative justification
  - Include: "What would need to change to reach 0.90?" analysis for REFace

  **Must NOT do**:
  - Do not choose based on "potential" — choose based on measured scores
  - Do not proceed past this gate if neither hits 0.85

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Critical architecture decision with quantitative analysis
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Tasks 2 and 3)
  - **Blocks**: Tasks 5, 6, 7, 8, 9, 10
  - **Blocked By**: Tasks 2, 3

  **References**:

  **Pattern References**:
  - `eval/results/facedancer/scores.json` — FaceDancer quantitative results
  - `eval/results/reface/scores.json` — REFace quantitative results
  - `.sisyphus/notepads/*/learnings.md` — lessons from compositing pipeline (what ceiling looks like)

  **Acceptance Criteria**:
  ```bash
  # Decision document exists
  test -f docs/architecture/decision.md
  grep -q "## Winner:" docs/architecture/decision.md
  grep -q "## Kill Criteria Result:" docs/architecture/decision.md
  grep -q "## Path to 0.90:" docs/architecture/decision.md
  
  # If kill criteria failed, a STOP document exists instead
  # (eval script should exit non-zero if p95 < 0.85 for both)
  ```

  **Commit**: YES
  - Message: `docs(architecture): architecture decision with quantitative justification`
  - Files: `docs/architecture/decision.md`

---

### Phase 2: Fine-Tuning & Enhancement

---

- [ ] 5. Training Data Pipeline

  **⚠️ UPDATE (2026-01-30 — License Decision)**: CelebA-HQ and CelebAMask-HQ are NON-COMMERCIAL. VGGFace2 is NON-COMMERCIAL. ArcFace weights are non-commercial. Must use only CC BY-licensed data and AuraFace (Apache 2.0) as identity encoder.

  **What to do**:
  - Build data preparation scripts for training REFace architecture from SD initialization
  - Data sources (ALL commercially licensed):
    1. **FFHQ CC BY-only subset**: Filter FFHQ's 70K images to the ~30-35K that are CC BY licensed (not CC BY-NC). Requires parsing the FFHQ metadata JSON for license info.
    2. **Synthetic face generation**: Use StyleGAN3 or SDXL to generate additional training faces (~10-20K) to supplement the filtered FFHQ set. No consent issues with synthetic faces.
    3. **Synthetic occlusion augmentation**: Take clean face images, programmatically paste occlusions (hands, objects, random shapes) to create supervised pairs
  - Pipeline outputs:
    - `data/clean/` — faces without occlusion (ground truth)
    - `data/occluded/` — same faces with synthetic occlusion applied
    - `data/masks/` — occlusion masks (binary)
    - `data/embeddings/` — **AuraFace** identity embeddings per face (NOT ArcFace)
    - `data/manifest.json` — metadata mapping all pairs, including license provenance per image
  - Target: 10,000-30,000 training pairs (start with FFHQ CC BY subset, augment with synthetic)
  - Identity encoder: **AuraFace (Apache 2.0)** — must verify quality parity with ArcFace before committing
  - Occlusion augmentation types:
    - Random rectangular/elliptical patches (baseline augmentation)
    - Hand segmentation masks from EgoHands or similar dataset
    - Object overlays at random positions within face region
  - Split: 90% train, 10% validation (held-out identities, not just held-out images)

  **Must NOT do**:
  - Do not use images without verifiable license compatibility
  - Do not create real NSFW training data — synthetic occlusion on SFW faces is sufficient for the geometric problem
  - Do not over-engineer — start with 10k pairs, measure, then scale

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Data engineering with augmentation pipeline, dataset management
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 7)
  - **Parallel Group**: Wave 2a (with Task 7)
  - **Blocks**: Task 6
  - **Blocked By**: Task 4

  **References**:

  **Pattern References**:
  - `watserface/training/` — existing training infrastructure (patterns for data loading, augmentation)
  - `watserface/face_masker.py` — existing mask generation (patterns for occlusion mask synthesis)

  **External References**:
  - FFHQ dataset: https://github.com/NVlabs/ffhq-dataset (70k high-quality face images)
  - CelebA-HQ: https://github.com/tkarras/progressive_growing_of_gans (30k high-quality faces)
  - EgoHands dataset: http://vision.soic.indiana.edu/projects/egohands/ (hand segmentation masks)

  **Acceptance Criteria**:
  ```bash
  # Data pipeline produces expected outputs
  python data/prepare_training_data.py --dataset ffhq --num-pairs 1000 --output data/
  ls data/clean/ | wc -l     # >= 1000
  ls data/occluded/ | wc -l  # >= 1000
  ls data/masks/ | wc -l     # >= 1000
  
  # Manifest is valid
  python -c "import json; d=json.load(open('data/manifest.json')); assert len(d['pairs']) >= 1000"
  
  # Embeddings generated
  ls data/embeddings/ | wc -l  # >= 1000
  ```

  **Commit**: YES
  - Message: `feat(data): training data pipeline with synthetic occlusion augmentation`
  - Files: `data/*.py`, `data/manifest.json`

---

- [ ] 6. Fine-Tune Winning Architecture

  **What to do**:
  - Set up fine-tuning pipeline for the architecture chosen in Task 4
  - Use training data from Task 5
  **⚠️ UPDATE (2026-01-30 — License Decision)**: Cannot fine-tune FROM REFace pretrained weights (non-commercial training data). Must train FROM Stable Diffusion v1-4 initialization using REFace architecture code (MIT). This is significantly more compute than fine-tuning and may require the full $1,500 budget + reserve.

  - Training strategy:
    - Initialize REFace architecture from Stable Diffusion v1-4 weights (RAIL-M, commercial OK)
    - Train using FFHQ CC BY-only data + synthetic augmentation from Task 5
    - Use **AuraFace** (Apache 2.0) as identity loss signal (NOT ArcFace)
    - Likely need full training of diffusion U-Net attention layers, not just LoRA
  - Training schedule:
    - Start with 10k pairs, 50 epochs, eval on validation set every 5 epochs
    - Track: identity score (**AuraFace** cosine similarity), FID, processing time
    - Early stopping if validation identity score plateaus for 3 consecutive evals
  - Budget enforcement: hard cap at $1,500 GPU spend (track with provider billing)
  - If first run doesn't hit 0.90: analyze failure mode, adjust data/hyperparams, retry ONCE with remaining budget
  - Save checkpoints every 10 epochs
  - Export final model to ONNX if possible (for CPU/MPS inference later)

  **Must NOT do**:
  - Do not exceed $1,500 GPU budget for this task
  - Do not train from scratch — fine-tune from pretrained weights only
  - Do not chase marginal gains past 0.90 — that's post-MVP optimization
  - Do not skip validation — every 5 epochs, measure on held-out set

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: ML training requires iterative monitoring and adjustment
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (GPU-bound, needs monitoring)
  - **Parallel Group**: Sequential
  - **Blocks**: Task 8
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `watserface/training/` — existing training loop patterns (device detection, checkpointing)
  - `watserface/optimization/onnx_converter.py` — ONNX export patterns

  **External References**:
  - FaceDancer training: https://github.com/felixrosberg/FaceDancer/tree/main/train
  - LoRA fine-tuning patterns: https://huggingface.co/docs/diffusers/training/lora

  **Acceptance Criteria**:
  ```bash
  # Fine-tuned model exists
  test -f models/finetuned/best_checkpoint.pth  # or .onnx
  
  # Validation scores meet threshold
  python eval/eval_batch.py \
    --model models/finetuned/best_checkpoint.pth \
    --test-set eval/test_set/ \
    --output eval/results/finetuned/scores.json
  
  jq '.p95_identity >= 0.90' eval/results/finetuned/scores.json  # true
  
  # Training log shows convergence
  test -f models/finetuned/training_log.json
  python -c "
  import json
  log = json.load(open('models/finetuned/training_log.json'))
  assert log['best_identity_score'] >= 0.90
  assert log['total_gpu_cost_usd'] <= 1500
  "
  ```

  **Commit**: YES
  - Message: `feat(model): fine-tuned [architecture] achieving {score} identity score`
  - Files: `models/finetuned/`, `eval/results/finetuned/`

---

- [ ] 7. Upscaling Integration

  **What to do**:
  - Integrate a face enhancement/upscaling step for the winning architecture's output
  - If FaceDancer (256px native): critical — need 4x upscale to 1024
  - If REFace (512px native): helpful — 2x upscale to 1024
  - Options (evaluate in order of preference):
    1. GFPGAN 1.4 (already in WatserFace codebase, known quality)
    2. Real-ESRGAN (general purpose, good on faces)
    3. CodeFormer (face-specific, high quality)
  - Measure identity score BEFORE and AFTER upscaling (upscaling can shift identity)
  - Find optimal blend ratio (learned from Phase 2.5 experience: 80% was "golden config")
  - Keep it simple: one upscaler, one blend ratio, no configurable stack

  **Must NOT do**:
  - Do not build a configurable enhancement pipeline
  - Do not use FaceFusion-derived enhancement code if clean-room required
  - Do not let upscaling reduce identity score by more than 0.02

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Integration of existing model, straightforward testing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 5, 6)
  - **Parallel Group**: Wave 2a
  - **Blocks**: Task 8
  - **Blocked By**: Task 4

  **References**:

  **Pattern References**:
  - `watserface/processors/modules/` — existing face enhancer integration patterns
  - `.sisyphus/notepads/mediapipe-hybrid-mask/learnings.md` — "GFPGAN 1.4 at 80% blend" as golden config

  **External References**:
  - GFPGAN: https://github.com/TencentARC/GFPGAN
  - CodeFormer: https://github.com/sczhou/CodeFormer

  **Acceptance Criteria**:
  ```bash
  # Upscaler produces expected resolution
  python upscale/upscale.py --input test_256.png --output test_1024.png
  python -c "from PIL import Image; img=Image.open('test_1024.png'); assert min(img.size) >= 1024"
  
  # Identity preservation after upscaling
  python eval/eval_identity.py --source source.png --target test_1024.png --output /tmp/upscale_test.json
  python -c "import json; s=json.load(open('/tmp/upscale_test.json')); assert s['identity_score'] >= 0.88"
  ```

  **Commit**: YES
  - Message: `feat(upscale): face enhancement integration with identity preservation check`
  - Files: `upscale/*.py`

---

### Phase 3: MVP Assembly

---

- [ ] 8. CLI Tool

  **What to do**:
  - Build the core product: a command-line tool that processes footage
  - Interface:
    ```
    watserface-swap \
      --source face.png \
      --target-dir ./frames/ \
      --output-dir ./output/ \
      --model models/finetuned/best_checkpoint.pth \
      --device cuda \
      --consent-manifest consent.json
    ```
  - Behavior:
    1. Load source face, extract identity embedding
    2. For each frame in target-dir (sorted):
       a. Detect face(s) in frame
       b. Select the target face (largest, or specified by bbox)
       c. Run swap model with identity conditioning
       d. Upscale output
       e. Save to output-dir with same filename
    3. Log: per-frame identity score, processing time, any skipped frames
    4. Summary: total frames, mean identity score, total time, frames skipped
  - Error handling:
    - No face detected → skip frame, log warning, pass through original
    - Multiple faces → swap largest face only (MVP scope), log info
    - Low identity score (<0.80) → still output, but flag in log
  - Config file support: `watserface.yaml` for defaults (model path, device, thresholds)
  - NO GUI, NO web server, NO API — CLI only

  **Must NOT do**:
  - Do not add multi-face support (v2)
  - Do not add real-time preview (v2)
  - Do not add video input/output (user extracts frames with ffmpeg, reassembles after)
  - Do not add any FaceFusion-derived code

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core product with error handling, logging, configuration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 9)
  - **Parallel Group**: Wave 3 (with Task 9)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 6, 7

  **References**:

  **Pattern References**:
  - `watserface/core.py` — existing CLI entry point patterns (argument parsing, processing loop)
  - `watserface/processors/modules/face_swapper.py` — existing swap pipeline flow

  **External References**:
  - Click or argparse for CLI: standard Python patterns
  - YAML config: PyYAML

  **Acceptance Criteria**:
  ```bash
  # CLI runs and produces output
  watserface-swap --source eval/test_set/clean/source_01.png \
                  --target-dir eval/test_set/clean/ \
                  --output-dir /tmp/cli_test/ \
                  --model models/finetuned/best_checkpoint.pth
  
  # Output files exist
  ls /tmp/cli_test/ | wc -l  # >= number of input frames
  
  # Summary log produced
  test -f /tmp/cli_test/processing_log.json
  jq '.total_frames' /tmp/cli_test/processing_log.json
  jq '.mean_identity_score' /tmp/cli_test/processing_log.json
  
  # Identity quality check
  jq '.mean_identity_score >= 0.88' /tmp/cli_test/processing_log.json  # true
  ```

  **Commit**: YES
  - Message: `feat(cli): watserface-swap command-line tool for batch face swapping`
  - Files: `cli/*.py`, `watserface.yaml`

---

- [ ] 9. Consent Manifest System

  **What to do**:
  - Define a JSON schema for consent verification
  - Schema:
    ```json
    {
      "version": "1.0",
      "source_identity": {
        "name": "Jane Doe",
        "consent_date": "2026-01-29",
        "consent_type": "likeness_license",
        "license_id": "uuid-here",
        "identity_hash": "sha256-of-arcface-embedding"
      },
      "processing": {
        "tool": "watserface-swap",
        "tool_version": "1.0.0",
        "model": "finetuned-v1",
        "processing_date": "2026-02-15",
        "frame_count": 54000,
        "mean_identity_score": 0.92
      }
    }
    ```
  - CLI integration: `--consent-manifest consent.json` flag
  - Validator: `watserface-verify --manifest output/manifest.json` — checks schema validity, identity hash matches
  - Embed manifest hash in output metadata (EXIF or sidecar file)
  - This is the minimum credible consent chain for MVP. NOT a legal compliance system — just a machine-readable record.

  **Must NOT do**:
  - Do not build a consent database or web portal (v2)
  - Do not implement cryptographic signing (v2)
  - Do not claim legal compliance — this is documentation, not certification

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: JSON schema + validator, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 8)
  - **Parallel Group**: Wave 3 (with Task 8)
  - **Blocks**: Task 10
  - **Blocked By**: Task 4

  **References**: None (new system, no codebase precedent)

  **Acceptance Criteria**:
  ```bash
  # Schema file exists
  test -f schemas/consent_manifest.schema.json
  
  # Validator works
  watserface-verify --manifest test_fixtures/valid_manifest.json   # exits 0
  watserface-verify --manifest test_fixtures/invalid_manifest.json # exits 1
  
  # CLI embeds manifest in output
  watserface-swap --source face.png --target-dir frames/ --output-dir out/ \
    --consent-manifest consent.json
  test -f out/manifest.json
  jq '.processing.frame_count' out/manifest.json  # returns integer
  ```

  **Commit**: YES
  - Message: `feat(consent): consent manifest schema and validator`
  - Files: `schemas/`, `cli/verify.py`

---

- [ ] 10. End-to-End Validation

  **What to do**:
  - Full pipeline test: source face + 100-frame target sequence → output frames
  - Measure on the complete pipeline (swap + upscale + consent manifest):
    - Identity score: p95 >= 0.90
    - Output resolution: >= 1024×1024
    - Processing time: <= 10s/frame on A100 (= ~17 minutes for 100 frames)
    - All frames processed (no crashes)
    - Consent manifest valid
    - Processing log complete
  - Test on 3 different source identities × 3 different target sequences = 9 combinations
  - Include at least 2 sequences with heavy occlusion
  - Generate final quality report: `docs/validation/mvp-validation-report.md`
  - This is the "ship/no-ship" decision point

  **Must NOT do**:
  - Do not use NSFW content for validation — use standard face-swap test material
  - Do not accept partial results — all 9 combinations must pass

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive validation across multiple test cases
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (final gate)
  - **Parallel Group**: Sequential (last task)
  - **Blocks**: None (final)
  - **Blocked By**: Tasks 8, 9

  **References**:

  **Pattern References**:
  - `eval/eval_batch.py` — batch evaluation harness from Task 1
  - `eval/test_set/` — standardized test set

  **Acceptance Criteria**:
  ```bash
  # Validation report exists
  test -f docs/validation/mvp-validation-report.md
  
  # All 9 combinations tested
  ls eval/results/e2e/ | wc -l  # >= 9
  
  # All pass quality gate
  python eval/validate_mvp.py --results-dir eval/results/e2e/
  # Exits 0 if: all 9 combos have p95_identity >= 0.90,
  #             all frames processed, all manifests valid
  
  # Processing speed check
  jq '.mean_time_per_frame_seconds <= 10' eval/results/e2e/combo_01/scores.json  # true
  ```

  **Commit**: YES
  - Message: `docs(validation): MVP end-to-end validation report`
  - Files: `docs/validation/mvp-validation-report.md`, `eval/results/e2e/`

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|------------|---------|-----------|--------------|
| -1 | `chore: archive compositing pipeline, prepare for commercial pivot` | README.md | Legacy branch + tag exist |
| 0 | `docs(legal): license decision and provenance analysis` | docs/legal/ | File exists with required sections |
| 1 | `feat(eval): standardized evaluation harness` | eval/*.py | `--help` exits 0 |
| 2 | `eval(facedancer): baseline evaluation results` | eval/results/facedancer/ | JSON with scores |
| 3 | `eval(reface): baseline evaluation results` | eval/results/reface/ | JSON with scores |
| 4 | `docs(architecture): decision with quantitative justification` | docs/architecture/ | Winner selected or STOP |
| 5 | `feat(data): training data pipeline` | data/*.py | 1000+ pairs generated |
| 6 | `feat(model): fine-tuned model` | models/finetuned/ | p95 identity >= 0.90 |
| 7 | `feat(upscale): enhancement integration` | upscale/*.py | 1024+ output verified |
| 8 | `feat(cli): watserface-swap tool` | cli/*.py | Batch processing works |
| 9 | `feat(consent): manifest schema and validator` | schemas/, cli/verify.py | Validation passes |
| 10 | `docs(validation): MVP validation report` | docs/validation/ | All 9 combos pass |

---

## Success Criteria

### Verification Commands
```bash
# Full MVP validation
python eval/validate_mvp.py --results-dir eval/results/e2e/
# Expected: "PASS: 9/9 combinations meet all quality gates"

# Identity score check
jq '.p95_identity' eval/results/e2e/*/scores.json
# Expected: all >= 0.90

# Consent manifest check
watserface-verify --manifest eval/results/e2e/combo_01/manifest.json
# Expected: exit 0
```

### Final Checklist
- [ ] Legal path resolved and documented
- [ ] Architecture chosen with quantitative data (not gut feel)
- [ ] Fine-tuned model achieves 0.90+ identity (p95)
- [ ] CLI tool processes folders unattended
- [ ] Output resolution >= 1024×1024
- [ ] Consent manifest embedded in every output
- [ ] Total spend <= $4,000
- [ ] No FaceFusion-derived code in commercial product
- [ ] Processing speed: 30min of footage in < 48hrs on single A100
