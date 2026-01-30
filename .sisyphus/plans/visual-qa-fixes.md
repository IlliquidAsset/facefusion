# Visual QA Output Fixes + Perspective-Aware Mesh Hull Mask

## TL;DR

> **Quick Summary**: Fix 3 QA visualization scripts that produce unusably small/uncropped images, fix XSeg model loading in comparison script, and add Z-depth filtering to `create_mesh_hull_mask()` so it respects camera perspective instead of including self-occluded face regions.
> 
> **Deliverables**:
> - Properly cropped & labeled QA output images (grid + separate files)
> - XSeg panel restored in hybrid comparison grid
> - Perspective-aware mesh hull mask (Z-filtered)
> - All images re-generated and presented to user for final visual QA
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 (XSeg fix) → Task 3 (mesh hull Z-filter) → Task 5 (visual QA)

---

## Context

### Original Request
User ran visual QA test loop and found:
1. Diff map is a tiny colored speck on a 3404×1868 black canvas — useless
2. Before/after lip warp images are full-frame — warp invisible at display scale
3. Synthetic blend comparison is 240×40 pixels — unreadable
4. XSeg panel missing in hybrid comparison grid
5. Mesh hull contour extends beyond the visible face edge at 3/4 view angles — covers self-occluded cheek

### Interview Summary
**Key Discussions**:
- QA output format: User wants BOTH labeled grid panels AND separate cropped files
- Lip warp exaggeration: Keep 1.3x/1.1x (sufficient once properly cropped)
- Synthetic canvas: Increase to 512×512
- 3D→2D projection: HIGH PRIORITY fix, research first approach
- XSeg loading: Fix for CPU-only mode

**Research Findings**:
- MediaPipe face oval indices are a fixed 3D mesh boundary, NOT visibility-aware
- Z-coordinate = relative depth from face center, scaled to face width. Negative = closer to camera
- MediaPipe `visibility` field is broken (always 0) since 2021 — Z is the only reliable signal
- FaceFusion avoids the problem by using 68pt landmarks (inherently 2D-projected)
- Recommended: Z-threshold filtering with adaptive `z_median + 0.5 * max(z_std, floor)` threshold

### Metis Review
**Identified Gaps** (addressed):
- Z-filtering fallback for near-profile: Added minimum-landmark guard (≥6 points) with fallback to unfiltered hull
- z_std floor guard: Added `max(z_std, 0.02)` to prevent degenerate frontal-view filtering
- Regression risk: Added requirement that Z-filtering is additive (optional flag, unfiltered path preserved)
- XSeg model existence: Verified `.assets/models/xseg_1.onnx` exists on disk — issue is missing state keys only

---

## Work Objectives

### Core Objective
Fix QA visualization outputs to be human-reviewable at display resolution, restore XSeg comparison panel, and add perspective-aware Z-filtering to mesh hull mask generation.

### Concrete Deliverables
- Modified `scripts/ralph_lip_warp_review.py` — lip ROI crop, labeled grid, separate files
- Modified `scripts/ralph_lip_blend_review.py` — 512×512 canvas, full image saves, labeled grid
- Modified `scripts/generate_hybrid_comparison.py` — XSeg init fix, updated outputs
- Modified `watserface/face_masker.py:create_mesh_hull_mask()` — Z-filtering with adaptive threshold
- Re-generated test images in `test_quality/` for user review

### Definition of Done
- [ ] All QA images are ≥512px on shortest dimension
- [ ] All QA images have burned-in text labels
- [ ] XSeg panel appears in hybrid comparison grid
- [ ] Mesh hull contour does not extend beyond visible face silhouette at 3/4 view
- [ ] Frontal-view mesh hull mask is unchanged (Z-filter is no-op)
- [ ] All existing tests pass

### Must Have
- Both grid composite AND individual cropped files for each QA output
- Z-filtering is additive — `use_z_filter=True` parameter, original unfiltered path preserved
- Minimum-landmark guard after Z-filtering (≥6 points fallback to unfiltered)
- z_std floor `max(z_std, 0.02)` to prevent frontal-view degeneracy

### Must NOT Have (Guardrails)
- DO NOT change face swap pipeline behavior — mask function only
- DO NOT modify landmark detection or face alignment code
- DO NOT add new dependencies
- DO NOT combine mesh hull changes with QA script changes in same commit
- DO NOT add CLI flags for Z-threshold — hardcode adaptive formula
- DO NOT compute new metrics in QA scripts — visual output only
- DO NOT fix MediaPipe integration bugs from Phase 2.5 (separate scope)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **User wants tests**: YES (unit tests for Z-filtering + manual visual QA)
- **Framework**: pytest (existing)

### For Each Task
- Unit tests for Z-filtering logic (synthetic landmarks, known Z values)
- Visual output verification by user (present images after each run)
- `pytest tests/test_mesh_hull_mask.py tests/test_composite_mask.py` must pass

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Fix XSeg loading in generate_hybrid_comparison.py [no dependencies]
├── Task 2: Fix QA output sizing in ralph_lip_warp_review.py [no dependencies]
└── Task 2b: Fix QA output sizing in ralph_lip_blend_review.py [no dependencies]

Wave 2 (After Wave 1):
├── Task 3: Add Z-filtering to create_mesh_hull_mask() [depends: 1 for visual validation]
└── Task 4: Update generate_hybrid_comparison.py to pass Z-filter flag [depends: 1, 3]

Wave 3 (After Wave 2):
└── Task 5: Re-run all scripts, present images to user [depends: all above]

Critical Path: Task 1 → Task 3 → Task 5
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3, 4 | 2, 2b |
| 2 | None | 5 | 1, 2b |
| 2b | None | 5 | 1, 2 |
| 3 | 1 (for validation context) | 4, 5 | None |
| 4 | 1, 3 | 5 | None |
| 5 | All | None | None (final) |

---

## TODOs

- [ ] 1. Fix XSeg loading in generate_hybrid_comparison.py

  **What to do**:
  - Add missing state_manager keys to `init_state()`: `face_occluder_model` ('xseg_1'), `face_parser_model` ('bisenet_resnet_34'), `face_detector_angles` ([0]), `face_selector_mode` ('one'), `face_selector_order` ('large-small'), `face_selector_age_start` (0), `face_selector_age_end` (100), `face_selector_gender` (None), `face_recognizer_model` ('arcface_inswapper'), `execution_thread_count` (4)
  - Verify XSeg panel appears in output grid (should show 6 panels: Original, Landmarks, Contour, Heatmap, XSeg, Composite)
  - Update the JPG output path default in argparse (already done, verify)

  **Must NOT do**:
  - Do NOT change the masking logic itself
  - Do NOT add new panels beyond Original/Landmarks/Contour/Heatmap/XSeg/Composite

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Simple config addition — single file, ~10 lines of state_manager.set_item calls

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 2b)
  - **Blocks**: Tasks 3, 4
  - **Blocked By**: None

  **References**:
  - `scripts/test_xseg_guided.py:13-30` — Complete state_manager setup that works for XSeg
  - `scripts/generate_hybrid_comparison.py:26-37` — Current incomplete init_state()
  - `watserface/face_masker.py:200-226` — create_occlusion_mask() showing what state it needs
  - `watserface/face_masker.py:146-150` — get_inference_pool() using face_occluder_model key

  **Acceptance Criteria**:
  - [ ] `venv/bin/python3 scripts/generate_hybrid_comparison.py --target "/Users/kendrick/Documents/FS Source/zBam.png"` → produces grid with 6 panels (not 4)
  - [ ] No "XSeg unavailable" error in output
  - [ ] `pytest tests/test_mesh_hull_mask.py tests/test_composite_mask.py -q` → all pass

  **Commit**: YES
  - Message: `fix(scripts): add missing state_manager keys for XSeg loading in hybrid comparison`
  - Files: `scripts/generate_hybrid_comparison.py`

---

- [ ] 2. Fix QA output sizing in ralph_lip_warp_review.py

  **What to do**:
  - Crop before/after/diff to lip ROI with 80px padding (already computed in script as `x_min/y_min/x_max/y_max`)
  - Upscale cropped images to 512px tall (preserving aspect ratio, INTER_LANCZOS4)
  - Generate labeled grid: `Before Warp | After Warp | Diff (10x)` with text labels burned in
  - Save grid as `warp_comparison.jpg` (quality 90) — this is the PRIMARY output for QA
  - Save individual crops as `before_warp.jpg`, `after_warp.jpg`, `diff_map.jpg` (quality 85)
  - Diff map must be computed on the CROPPED region, not the full frame

  **Must NOT do**:
  - Do NOT change warp exaggeration (keep 1.3x/1.1x)
  - Do NOT change metrics computation logic
  - Do NOT add new metrics or visualizations

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Single file change, output formatting only

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2b)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - `scripts/ralph_lip_warp_review.py:79-130` — Current save logic (full-frame saves)
  - `scripts/ralph_lip_warp_review.py:92-98` — lip ROI bounding box computation (reuse for crop)
  - `scripts/generate_hybrid_comparison.py:19-23` — `resize_preserving_aspect()` utility (pattern to follow)

  **Acceptance Criteria**:
  - [ ] `warp_comparison.jpg` is a 3-panel labeled grid, ≥512px tall
  - [ ] Lip area fills ≥60% of each panel (visible at display scale)
  - [ ] `diff_map.jpg` shows colored lip deformation filling the image (not a speck on black)
  - [ ] Before and after panels show VISIBLE difference in lip area
  - [ ] Present images to user for visual QA

  **Commit**: YES
  - Message: `fix(scripts): crop lip warp QA output to ROI with labeled grid panels`
  - Files: `scripts/ralph_lip_warp_review.py`

---

- [ ] 2b. Fix QA output sizing in ralph_lip_blend_review.py

  **What to do**:
  - Increase synthetic canvas from 256×256 to 512×512 (scale all coordinates 2x)
  - Increase ellipse size proportionally (40→80 x-radius, 20→40 y-radius)
  - Update ROI crop coordinates (y1,y2,x1,x2 all 2x)
  - Save comparison as 3-panel labeled grid: `Target | Swapped | Result` at full 512×512 panel size with text labels
  - Also save individual full images (`synthetic_target.jpg`, `synthetic_swapped.jpg`, `synthetic_result.jpg`)
  - Also save ROI comparison grid with zoomed-in lip region

  **Must NOT do**:
  - Do NOT change blend_lip_identity() function behavior
  - Do NOT change SSIM or color shift metric formulas

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Single file change, coordinate scaling + output formatting

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - `scripts/ralph_lip_blend_review.py:33-71` — Current synthetic test + save logic
  - `scripts/ralph_lip_blend_review.py:36-41` — Canvas size and ellipse coordinates to scale
  - `scripts/ralph_lip_blend_review.py:54` — ROI coordinates to scale
  - `scripts/ralph_lip_blend_review.py:67` — Comparison hstack (change to labeled grid)

  **Acceptance Criteria**:
  - [ ] `synthetic_comparison.jpg` is a 3-panel labeled grid, each panel 512×512
  - [ ] Ellipse lip shapes clearly visible with creases/lines distinguishable
  - [ ] Individual images are each 512×512
  - [ ] Edge SSIM and color shift metrics still pass (>0.8 SSIM)
  - [ ] Present images to user for visual QA

  **Commit**: YES
  - Message: `fix(scripts): increase synthetic blend canvas to 512×512 with labeled grid`
  - Files: `scripts/ralph_lip_blend_review.py`

---

- [ ] 3. Add Z-depth filtering to create_mesh_hull_mask()

  **What to do**:
  - Add `use_z_filter: bool = True` parameter to `create_mesh_hull_mask()`
  - When `use_z_filter=True` AND landmarks have 3 columns (X,Y,Z):
    1. Extract Z values of face oval landmarks: `z_vals = landmarks_478[FACE_OVAL_INDICES, 2]`
    2. Compute adaptive threshold: `z_median = numpy.median(z_vals)`, `z_std = max(numpy.std(z_vals), 0.02)`, `z_thresh = z_median + 0.5 * z_std`
    3. Filter: keep only face oval points where `z < z_thresh`
    4. Minimum landmark guard: if `len(filtered) < 6`, fall back to unfiltered hull
    5. ConvexHull the filtered points, fillConvexPoly
  - When `use_z_filter=False` OR landmarks are (478,2): use existing unfiltered behavior
  - Update `create_composite_mask()` to pass through `use_z_filter` parameter
  - Write tests:
    - Test with synthetic (478,3) landmarks at frontal (Z ≈ 0 for all) → filter is no-op
    - Test with synthetic (478,3) landmarks simulating 3/4 view (far side Z >> 0) → filter removes far-side points
    - Test with (478,2) landmarks → graceful fallback to unfiltered
    - Test with near-profile (most Z > threshold) → minimum-6 guard activates, fallback to unfiltered

  **Must NOT do**:
  - Do NOT change landmark detection code
  - Do NOT change face alignment
  - Do NOT add CLI flags or state_manager keys for Z-threshold
  - Do NOT modify any mask functions OTHER THAN `create_mesh_hull_mask()` and `create_composite_mask()`

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
    - Requires careful math (Z-stats, threshold tuning), test writing, and regression awareness

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential)
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Task 1 (need XSeg comparison for visual validation)

  **References**:
  - `watserface/face_masker.py:321-352` — Current `create_mesh_hull_mask()` function
  - `watserface/face_masker.py:355-390` — `create_composite_mask()` that calls mesh hull
  - `watserface/face_landmarker.py:228` — Where Z is computed: `lm.z * w`
  - `watserface/face_helper.py:439-454` — `transform_points_3d()` preserves Z through affine transforms
  - `tests/test_mesh_hull_mask.py` — Existing tests (must still pass)
  - `tests/test_composite_mask.py` — Existing composite mask tests

  **Callers that need updating** (from ast-grep search):
  - `scripts/generate_hybrid_comparison.py:72` — `create_mesh_hull_mask(face_crop, lm_crop)` — update to pass `use_z_filter=True`
  - `watserface/face_masker.py:372` — `create_composite_mask()` internal call — auto-forwarded via new parameter
  - `tests/test_mesh_hull_mask.py` — existing tests use (478,2) synthetics → will use unfiltered path → still pass
  - `tests/test_composite_mask.py` — same

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_mesh_hull_mask.py tests/test_composite_mask.py -q` → all pass (existing + new)
  - [ ] New test: frontal landmarks (Z≈0) → coverage matches unfiltered (regression)
  - [ ] New test: 3/4 view landmarks (far side Z >> 0) → coverage is LESS than unfiltered (filter works)
  - [ ] New test: (478,2) input → graceful fallback, same as before
  - [ ] New test: near-profile (most Z > threshold) → min-6 guard triggers, uses unfiltered fallback
  - [ ] Visual: re-run `generate_hybrid_comparison.py` → mesh hull contour hugs visible face edge

  **Commit**: YES
  - Message: `feat(masker): add Z-depth filtering to mesh hull mask for perspective-aware boundaries`
  - Files: `watserface/face_masker.py`, `tests/test_mesh_hull_mask.py`

---

- [ ] 4. Update generate_hybrid_comparison.py to use Z-filtering

  **What to do**:
  - Pass `use_z_filter=True` to `create_mesh_hull_mask()` call
  - Update contour visualization to use Z-filtered landmarks for display too (convexHull of filtered points)
  - Add a 5th panel: "Z-Filtered Hull" heatmap alongside original "Mesh Hull Heatmap" for comparison

  **Must NOT do**:
  - Do NOT change init_state() (already fixed in Task 1)
  - Do NOT modify XSeg/composite mask logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Small change — pass flag + add visualization panel

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Tasks 1, 3)
  - **Blocks**: Task 5
  - **Blocked By**: Tasks 1, 3

  **References**:
  - `scripts/generate_hybrid_comparison.py:72` — Current `create_mesh_hull_mask()` call
  - `scripts/generate_hybrid_comparison.py:86-103` — Panel construction logic
  - Task 3 output — the new `use_z_filter` parameter

  **Acceptance Criteria**:
  - [ ] Grid now shows: Original, Landmarks, Contour (Z-filtered), Mesh Hull, Z-Filtered Hull, XSeg, Composite
  - [ ] Z-Filtered Hull panel shows tighter mask at 3/4 view
  - [ ] Present to user for visual comparison

  **Commit**: YES (group with Task 3)
  - Message: `feat(scripts): add Z-filtered hull panel to hybrid comparison grid`
  - Files: `scripts/generate_hybrid_comparison.py`

---

- [ ] 5. Re-run all scripts + present images to user for final visual QA

  **What to do**:
  - Run: `venv/bin/python3 scripts/generate_hybrid_comparison.py --target "/Users/kendrick/Documents/FS Source/zBam.png"`
  - Run: `venv/bin/python3 scripts/ralph_lip_warp_review.py`
  - Run: `venv/bin/python3 scripts/ralph_lip_blend_review.py`
  - Run: `venv/bin/python3 scripts/measure_chin_crease.py --image "/Users/kendrick/Documents/FS Source/zBam.png"`
  - Present ALL output images to user using `Read` tool (shows inline in chat)
  - Ask user specific questions about each image
  - Document any issues user identifies

  **Must NOT do**:
  - Do NOT commit test_quality/ files
  - Do NOT modify scripts — only run them

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
    - Script execution + image presentation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final, after all others)
  - **Blocks**: None
  - **Blocked By**: All previous tasks

  **References**:
  - All scripts in `scripts/` directory
  - Output directories: `test_quality/hybrid/`, `test_quality/lip_deformation/`

  **Acceptance Criteria**:
  - [ ] All scripts run without errors
  - [ ] All output images ≥512px on shortest dimension
  - [ ] All images have burned-in text labels
  - [ ] User approves visual quality
  - [ ] Images are shown to user via Read tool (inline display)

  **Commit**: NO (generated outputs only)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `fix(scripts): add missing state_manager keys for XSeg loading` | generate_hybrid_comparison.py | run script, 6 panels |
| 2 | `fix(scripts): crop lip warp QA output to ROI with labeled grid` | ralph_lip_warp_review.py | run script, check dimensions |
| 2b | `fix(scripts): increase synthetic blend canvas to 512×512` | ralph_lip_blend_review.py | run script, check dimensions |
| 3+4 | `feat(masker): add Z-depth filtering to mesh hull mask` | face_masker.py, test_mesh_hull_mask.py, generate_hybrid_comparison.py | pytest + visual |

---

## Success Criteria

### Verification Commands
```bash
venv/bin/python3 -m pytest tests/test_mesh_hull_mask.py tests/test_composite_mask.py -q  # All pass
venv/bin/python3 scripts/generate_hybrid_comparison.py --target "/Users/kendrick/Documents/FS Source/zBam.png"  # 7 panels, no errors
venv/bin/python3 scripts/ralph_lip_warp_review.py  # Grid + crops, ≥512px
venv/bin/python3 scripts/ralph_lip_blend_review.py  # 512×512 panels
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All existing tests pass
- [ ] User has visually approved all output images
- [ ] Z-filtered mesh hull hugs visible face silhouette at 3/4 view
- [ ] Frontal-view mesh hull is unchanged (regression check)
