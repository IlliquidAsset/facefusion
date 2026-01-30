# Lip Fringe: Bug Fixes, Integration & QA

## TL;DR

> **Quick Summary**: Fix 2 bugs in Gemini's `lip_fringe.py` (color sampling + alpha cap), add shadow pass and seam blur to compositing pipeline, wire lip fringe into `transparency_handler.py`, and run a QA pass to verify visually.
> 
> **Deliverables**:
> - Fixed `lip_fringe.py` with correct color sampling and blend cap
> - Shadow + seam blur added to composite step in `transparency_handler.py`
> - Lip fringe integrated into `process_frame_xseg()` pipeline
> - Updated tests covering the bug fixes
> - Run 0005 QA output for visual verification
> 
> **Estimated Effort**: Quick (~1-2 hours)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 (fix bugs) → Task 3 (integrate) → Task 4 (QA)

---

## Context

### Original Request
Fix the lip fringe implementation (created by Gemini) based on Oracle's code review, integrate it into the pipeline, and run a QA pass.

### Interview Summary
**Key Discussions**:
- TPS lip warp approach failed — landmark detector gives wrong targets for occluded lips
- Oracle recommended "boundary lip fringe" — paint lip-colored crescent at XSeg mask edge
- Gemini implemented `lip_fringe.py` — Oracle reviewed and found 2 bugs + 2 missing pieces
- User confirmed fringe should be lip-only, not generalized to other occlusion types
- Previous TPS warp code in `run_video_qa.py` should be removed/replaced with fringe call

### Research Findings
- **Composite location**: `TransparencyHandler._composite()` at line 509 of `transparency_handler.py`. Formula: `result = dirty_swap_f * (1.0 - alpha) + original_f * alpha`
- **Integration point**: `process_frame_xseg()` lines 258-286, where `target_face`, `face_bbox`, and computed `alpha` are all in scope before `_composite()` call at line 286
- **Landmark coordinate space**: Landmarks stored in `face.landmark_set['68']` are full-frame coords. Must subtract bbox origin `(x1, y1)` for crop-local coords — same transform already done at lines 273-274 for `create_occlusion_mask_guided()`
- **Coordinate space at composite**: `_composite()` operates in full-frame space. Alpha is computed in crop space then embedded into full-frame zeros array (lines 280-281)

### Metis Review
**Identified Gaps** (addressed):
- Color sampling may sample corndog pixels → Task 1 fixes this
- Alpha cap missing (1.0 = painted look) → Task 1 fixes this  
- Landmark coordinate space unclear → Resolved: crop-local, subtract `(x1, y1)`
- No-op condition for closed-mouth targets → Task 1 adds early-exit when no fringe overlap
- Profile/side angle landmark degradation → Existing `countNonZero` guard handles this

---

## Work Objectives

### Core Objective
Make the lip fringe visually convincing by fixing bugs, adding complementary effects (shadow + seam blur), and wiring into the pipeline.

### Concrete Deliverables
- `watserface/processors/modules/lip_fringe.py` — bug-fixed
- `watserface/processors/modules/transparency_handler.py` — integration + shadow + seam blur
- `tests/test_lip_fringe.py` — updated tests covering bug fixes
- `test_quality/YYYY.MM.DD.HHmm Run 0005/` — QA output

### Definition of Done
- [ ] All unit tests pass: `./venv/bin/python -m pytest tests/test_lip_fringe.py -v`
- [ ] All existing pipeline tests pass: `./venv/bin/python -m pytest tests/ -v`
- [ ] Run 0005 generated with lip fringe active

### Must Have
- Color sampling excludes occluded pixels
- Blend cap at 0.6 (configurable constant)
- Shadow pass on original at occlusion edge in lip region
- Gaussian seam blur σ=1.5 on composite alpha
- Lip fringe called before composite in `process_frame_xseg()`
- Landmarks transformed to crop-local coords before passing to lip_fringe

### Must NOT Have (Guardrails)
- DO NOT modify XSeg mask generation or landmark detection
- DO NOT generalize fringe to non-lip regions
- DO NOT add new pip dependencies
- DO NOT alter the core Mayonnaise composite formula in `_composite()`
- DO NOT add UI/config parameters — hardcode constants with named variables
- DO NOT touch processors outside `lip_fringe.py` and `transparency_handler.py`
- DO NOT modify `face_masker.py` or `face_swapper.py`

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **User wants tests**: YES (tests-after)
- **Framework**: pytest via `./venv/bin/python -m pytest`

### Automated Verification

Each task includes executable verification. All tests run via:
```bash
./venv/bin/python -m pytest tests/test_lip_fringe.py -v
./venv/bin/python -m pytest tests/ -v
```

QA run via:
```bash
./venv/bin/python scripts/run_video_qa.py
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Fix lip_fringe.py bugs + update tests
└── Task 2: Add shadow pass + seam blur to transparency_handler.py

Wave 2 (After Wave 1):
└── Task 3: Wire lip fringe into process_frame_xseg()

Wave 3 (After Wave 2):
└── Task 4: QA Run 0005

Critical Path: Task 1 → Task 3 → Task 4
Parallel Speedup: Tasks 1 and 2 run simultaneously
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3 | 2 |
| 2 | None | 3 | 1 |
| 3 | 1, 2 | 4 | None |
| 4 | 3 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | `delegate_task(category="quick", load_skills=[], run_in_background=true)` x2 |
| 2 | 3 | `delegate_task(category="quick", load_skills=[], run_in_background=false)` |
| 3 | 4 | `delegate_task(category="quick", load_skills=[], run_in_background=false)` |

---

## TODOs

- [ ] 1. Fix lip_fringe.py bugs + update tests

  **What to do**:
  - **Bug 1 — Color sampling exclusion**: In `apply_lip_fringe()`, when `lip_color is None`, the `sample_mask` must exclude the occlusion area. After creating the eroded lip hull, bitwise-AND with `inv_occlusion` (inverted occlusion mask). Add fallback: if `countNonZero(sample_mask) < 20`, sample directly from landmark point 66 (inner lower lip center): `dirty_swap[landmarks[66][1], landmarks[66][0]]`.
  - **Bug 2 — Blend cap**: Add `BLEND_STRENGTH = 0.6` constant. Multiply `final_alpha` by `BLEND_STRENGTH` before compositing. This prevents solid-color strip at mask edge.
  - **Robustness**: Add assertion or comment that non-uint8 masks are assumed float [0,1]. Add early return if `landmarks` has fewer than 68 points or if lip points are all zeros.
  - **Update tests**: Add test case with synthetic occlusion covering lip area — assert sampled color has low green channel (occlusion is green in test). Add test asserting `final_alpha.max() <= 0.6 + epsilon`.

  **Must NOT do**:
  - Do NOT change the function signature
  - Do NOT add new parameters
  - Do NOT generalize beyond lip region

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file edit, well-scoped bug fixes
  - **Skills**: `[]`
    - No special skills needed — pure Python/numpy edits
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Not applicable — backend image processing

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `watserface/processors/modules/lip_fringe.py:67-80` — Current color sampling code that needs the occlusion exclusion fix
  - `watserface/processors/modules/lip_fringe.py:94-98` — Current alpha computation that needs the blend cap

  **API/Type References**:
  - `watserface/processors/modules/lip_fringe.py:5-11` — Function signature (do not change)
  - OpenCV `cv2.mean()` — Used for color sampling, needs mask argument updated
  - OpenCV `cv2.countNonZero()` — For fallback threshold check

  **Test References**:
  - `tests/test_lip_fringe.py:6-24` — Existing synthetic data fixture (extend with occluded lip scenario)
  - `tests/test_lip_fringe.py:26-48` — Existing pixel assertion test (add alpha cap assertion)

  **Acceptance Criteria**:

  ```bash
  # Agent runs:
  ./venv/bin/python -m pytest tests/test_lip_fringe.py -v
  # Assert: All tests pass, including new tests for:
  #   - test_color_sampling_excludes_occlusion
  #   - test_alpha_cap_below_threshold
  ```

  ```bash
  # Agent runs:
  ./venv/bin/python -c "
  import numpy as np, cv2
  from watserface.processors.modules.lip_fringe import apply_lip_fringe
  # Create synthetic: gray image, green occlusion covering lips
  img = np.full((200,200,3), 128, dtype=np.uint8)
  cv2.ellipse(img, (100,100), (40,20), 0, 0, 360, (50,50,200), -1)
  mask = np.zeros((200,200), dtype=np.float32)
  cv2.rectangle(mask, (80,90), (120,110), 1.0, -1)  # covers lip center
  lm = np.zeros((68,2), dtype=np.int32)
  for i in range(20):
      a = (i/20.0)*2*3.14159
      lm[48+i] = [int(100+40*np.cos(a)), int(100+20*np.sin(a))]
  result = apply_lip_fringe(img.copy(), mask, lm, fringe_width=5)
  print('PASS: no crash')
  "
  # Assert: prints "PASS: no crash"
  ```

  **Commit**: YES (groups with Task 2)
  - Message: `fix(lip-fringe): exclude occluded pixels from color sampling, cap blend alpha at 0.6`
  - Files: `watserface/processors/modules/lip_fringe.py`, `tests/test_lip_fringe.py`
  - Pre-commit: `./venv/bin/python -m pytest tests/test_lip_fringe.py -v`

---

- [ ] 2. Add shadow pass + seam blur to transparency_handler.py

  **What to do**:
  - **Shadow pass**: In `process_frame_xseg()`, after computing the XSeg occlusion alpha but before calling `_composite()`, add a shadow darkening step on the original frame at the occlusion boundary in the lip region. Implementation:
    - Compute distance transform from occlusion mask edge (same approach as lip_fringe)
    - Restrict to lip region (landmarks 48-67 convex hull)
    - Create shadow alpha: `shadow_alpha = clip(1.0 - dist/3.0, 0, 1) * lip_boundary * 0.3`
    - Apply: `original_shadowed = original * (1 - shadow_alpha)`
    - Pass `original_shadowed` instead of `original` to `_composite()`
  - **Seam blur**: Before passing alpha to `_composite()`, apply Gaussian blur: `alpha = cv2.GaussianBlur(alpha, (5,5), 1.5)`. NOTE: Check if a blur is already applied (lines 280-282). If so, adjust sigma or replace — do NOT double-blur.
  - Both operate in **crop-local coordinates** for shadow (on `face_crop`), and **full-frame** for seam blur (on the full alpha before composite).

  **Must NOT do**:
  - Do NOT modify `_composite()` itself
  - Do NOT apply shadow outside the lip region (would darken fingers/fists incorrectly)
  - Do NOT add shadow to non-XSeg pipeline paths

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, additive logic before existing composite call
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Not applicable

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `watserface/processors/modules/transparency_handler.py:258-286` — `process_frame_xseg()` method where shadow and blur must be inserted
  - `watserface/processors/modules/transparency_handler.py:280-282` — Existing alpha blur (check if already present, avoid double-blur)
  - `watserface/processors/modules/transparency_handler.py:509` — `_composite()` line: `result = dirty_swap_f * (1.0 - alpha) + original_f * alpha`
  - `watserface/processors/modules/transparency_handler.py:273-274` — Landmark coordinate transform: `landmarks_crop = landmarks_68 - [x1, y1]`

  **API/Type References**:
  - `watserface/processors/modules/transparency_handler.py:487` — `_composite(self, original, dirty_swap, alpha)` signature
  - OpenCV `cv2.distanceTransform` — For shadow falloff
  - OpenCV `cv2.GaussianBlur` — For seam smoothing

  **WHY Each Reference Matters**:
  - Lines 258-286: This is the exact scope where you insert new code. Read the whole block to understand data flow.
  - Lines 280-282: CRITICAL — if a blur already exists here, you must not add another one. Check first.
  - Lines 273-274: Shows how landmarks are already transformed for this scope. Reuse the same pattern.

  **Acceptance Criteria**:

  ```bash
  # Agent runs:
  ./venv/bin/python -m pytest tests/ -v
  # Assert: All existing tests still pass (no regression)
  ```

  ```bash
  # Agent runs:
  ./venv/bin/python -c "
  from watserface.processors.modules.transparency_handler import TransparencyHandler
  print('Import OK')
  "
  # Assert: No import errors
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `feat(composite): add lip shadow pass and seam blur for smoother occlusion edges`
  - Files: `watserface/processors/modules/transparency_handler.py`
  - Pre-commit: `./venv/bin/python -m pytest tests/ -v`

---

- [ ] 3. Wire lip fringe into process_frame_xseg()

  **What to do**:
  - In `process_frame_xseg()` (transparency_handler.py), after the dirty swap is produced but BEFORE `_composite()` is called:
    1. Import `apply_lip_fringe` from `watserface.processors.modules.lip_fringe`
    2. Get 68-point landmarks: `landmarks_68 = target_face.landmark_set.get('68')`
    3. Transform to crop coords: `landmarks_crop = landmarks_68 - np.array([x1, y1])`  (same pattern as line 273-274)
    4. Get occlusion mask in crop space (this should already be computed as part of the alpha — reuse it or extract the XSeg raw mask)
    5. Call: `dirty_swap_crop = apply_lip_fringe(dirty_swap_crop, xseg_mask_crop, landmarks_crop, fringe_width=5)`
    6. Continue to `_composite()` with modified dirty_swap
  - **Coordinate space**: `apply_lip_fringe` must receive the crop-space image and crop-space landmarks. The dirty swap at the integration point may be full-frame — if so, extract the crop `dirty_swap[y1:y2, x1:x2]`, apply fringe, write back.
  - **Also wire into `process_video_xseg_guided()`** if it has a similar composite path (line 356+). Same pattern.
  - **Remove old TPS warp** code from `scripts/run_video_qa.py` if it calls `warp_lip_to_target`. Replace with lip fringe call or remove entirely (the pipeline handles it now).

  **Must NOT do**:
  - Do NOT change `_composite()` signature or logic
  - Do NOT add lip fringe to non-XSeg pipeline paths (those don't have occlusion masks)
  - Do NOT pass full-frame landmarks to crop-space lip_fringe

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Wiring/glue code, not complex logic
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed until commit time

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential)
  - **Blocks**: Task 4
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `watserface/processors/modules/transparency_handler.py:258-286` — `process_frame_xseg()` — THE integration point. Read entire method.
  - `watserface/processors/modules/transparency_handler.py:273-274` — Existing landmark transform pattern to copy
  - `watserface/processors/modules/transparency_handler.py:356+` — `process_video_xseg_guided()` — secondary integration point, same pattern
  - `scripts/run_video_qa.py` — Contains old `warp_lip_to_target` call to remove

  **API/Type References**:
  - `watserface/processors/modules/lip_fringe.py:5-11` — `apply_lip_fringe(dirty_swap, occlusion_mask, landmarks, fringe_width=5, lip_color=None)` signature
  - `watserface/face_helper.py` — Contains `warp_lip_to_target` (the old approach to remove from QA script)

  **WHY Each Reference Matters**:
  - Lines 258-286: You must read this entire method to understand where dirty_swap, alpha, landmarks, and bbox are in scope. The insertion point is between alpha computation and `_composite()` call.
  - Lines 273-274: Copy this exact pattern for the landmark transform. Don't reinvent.
  - `run_video_qa.py`: The old TPS warp call needs to go. Search for `warp_lip_to_target` and remove/replace.

  **Acceptance Criteria**:

  ```bash
  # Agent runs:
  ./venv/bin/python -m pytest tests/ -v
  # Assert: All tests pass
  ```

  ```bash
  # Agent runs:
  grep -n "apply_lip_fringe" watserface/processors/modules/transparency_handler.py
  # Assert: At least one match (import + call)
  ```

  ```bash
  # Agent runs:
  grep -n "warp_lip_to_target" scripts/run_video_qa.py
  # Assert: No matches (old code removed)
  ```

  **Commit**: YES
  - Message: `feat(pipeline): integrate lip fringe into XSeg composite, remove TPS warp`
  - Files: `watserface/processors/modules/transparency_handler.py`, `scripts/run_video_qa.py`
  - Pre-commit: `./venv/bin/python -m pytest tests/ -v`

---

- [ ] 4. QA Run 0005

  **What to do**:
  - Run the video QA script to generate Run 0005 with lip fringe active
  - Verify output files are created in timestamped folder
  - Check metrics in `run_summary.json` — identity and temporal consistency should not regress significantly from Run 0004 (identity ~0.84, temporal ~0.97)

  **Must NOT do**:
  - Do NOT modify the QA script (beyond what Task 3 already changed)
  - Do NOT change test video or frame range

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single command execution + metric check
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final)
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:

  **Pattern References**:
  - `scripts/run_video_qa.py` — QA script to execute
  - `test_quality/2026.01.29.0940 Run 0004/run_summary.json` — Baseline metrics to compare against

  **Acceptance Criteria**:

  ```bash
  # Agent runs:
  ./venv/bin/python scripts/run_video_qa.py
  # Assert: exits 0, creates new timestamped folder in test_quality/
  ```

  ```bash
  # Agent runs:
  ls test_quality/ | tail -1
  # Assert: new "Run 0005" folder exists
  ```

  ```bash
  # Agent runs:
  python -c "
  import json
  with open('test_quality/$(ls test_quality/ | grep 0005)/run_summary.json') as f:
      d = json.load(f)
  print(f'temporal: {d[\"temporal_consistency\"]:.3f}')
  print(f'identity_dirty: {d[\"identity\"][\"dirty_swap\"]:.3f}')
  print(f'identity_composite: {d[\"identity\"][\"xseg_composite\"]:.3f}')
  assert d['temporal_consistency'] > 0.95, 'Temporal regression!'
  assert d['identity']['xseg_composite'] > 0.80, 'Identity regression!'
  print('METRICS OK')
  "
  # Assert: prints "METRICS OK"
  ```

  **Evidence to Capture:**
  - [ ] `run_summary.json` metrics printed
  - [ ] All 11 diagnostic images + 5-frame sequence generated

  **Commit**: NO (QA output is in .gitignore)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1+2 | `fix(lip-fringe): exclude occluded pixels from color sampling, cap blend alpha at 0.6` | lip_fringe.py, test_lip_fringe.py | pytest tests/test_lip_fringe.py |
| 1+2 | `feat(composite): add lip shadow pass and seam blur for smoother occlusion edges` | transparency_handler.py | pytest tests/ |
| 3 | `feat(pipeline): integrate lip fringe into XSeg composite, remove TPS warp` | transparency_handler.py, run_video_qa.py | pytest tests/ |

---

## Success Criteria

### Verification Commands
```bash
./venv/bin/python -m pytest tests/ -v                    # All tests pass
./venv/bin/python scripts/run_video_qa.py                # Run 0005 generated
grep "apply_lip_fringe" watserface/processors/modules/transparency_handler.py  # Integration present
grep "warp_lip_to_target" scripts/run_video_qa.py        # Old code removed (no matches)
```

### Final Checklist
- [ ] Color sampling excludes occluded pixels
- [ ] Blend alpha capped at 0.6
- [ ] Shadow pass active in lip region
- [ ] Seam blur applied (σ=1.5, no double-blur)
- [ ] Lip fringe wired into process_frame_xseg()
- [ ] Old TPS warp removed from run_video_qa.py
- [ ] Run 0005 metrics: temporal > 0.95, identity > 0.80
- [ ] All tests pass
