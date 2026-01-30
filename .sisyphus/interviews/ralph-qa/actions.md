# Ralph QA Actions — 2026-01-29

## User Decisions

### Q1: Face Integration Quality (key_09 dirty swap vs key_08 original)
**Answer**: Everything above the nose looks perfect. Skin detail loss noted but attributed to 128px resolution (expected).
**Verdict**: Swap quality is acceptable above the nose. No under-adaptation concern from user's visual assessment.

### Q2: Metric Design (identity vs naturalness)
**Answer**: Revisit later.
**Action**: Keep current raw cosine similarity metric. Flag for review after more runs accumulate data. Do NOT add naturalness metric now.

### Q3: Lip Blending Quality (key_06 guided lip overlay)
**Answer**: Blending looks seamless WHERE the mask covers. BUT the guided lip mask doesn't cover the full corndog-mouth intersection. Specifically:
- Missing width AND height of the mouth, justified to bottom of top lip
- XSeg mask itself looks good
- **Root cause investigation needed**: User wants to see the facial MESH (not convex hull) drawn over the target to verify cheek index markers are landing on actual cheeks
- If cheek markers are correct, the mesh needs to stretch all the way across the face and all the way down
- Mouth placement may become easier once mesh coverage is fixed

## Action Items for Sisyphus

### PRIORITY 1: Mesh Diagnostic Overlay
- [ ] Generate a mesh visualization (NOT hull) overlaid on the original target frame (key_01_original.png)
- [ ] Show individual landmark indices, especially cheek markers
- [ ] User needs to verify cheek index markers land on actual cheeks
- [ ] Output to: `test_quality/Run 0007/key_XX_mesh_overlay.png`

### PRIORITY 2: Guided Lip Mask Coverage Fix (blocked by P1)
- [ ] After mesh verification, extend guided lip mask to cover full mouth width and height
- [ ] Justify mask to bottom of top lip line
- [ ] Ensure mask stretches across full face width and down

### PRIORITY 3: Auto-Fixes (Oracle-approved, proceed without user input)
- [ ] Apply LAB histogram matching for color shift (9.5 → target <3.0)
- [ ] Apply GFPGAN 1.4 @ 80% blend for sharpness (already validated Phase 2.5)
- [ ] Fix artifact detector baseline (compare against source-warped-to-target, not original)

### DEFERRED
- [ ] Identity metric redesign (naturalness/pose-alignment) — revisit after more run data

## Oracle Auto-Resolved Summary

| Issue | Verdict | Action |
|-------|---------|--------|
| XSeg identity drop (-0.006) | NOISE | No action needed |
| Artifact detector 100% FAIL | FALSE POSITIVE | Fix baseline comparison (P3) |
| Sharpness 4.8 | EXPECTED | 128px limitation; GFPGAN as enhancement (P3) |
| Color shift 9.5 LAB | REAL, auto-fixable | LAB histogram matching (P3) |
