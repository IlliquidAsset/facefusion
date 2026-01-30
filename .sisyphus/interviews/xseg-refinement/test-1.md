# Test 1: Landmark-Guided XSeg Alpha Mask

## Test Execution Summary
- **Date**: 2026-01-27
- **Test**: `scripts/test_xseg_guided.py`
- **Result**: ✅ PASS
- **Alpha Coverage**: **7.6%** (target: <15%, baseline: 57%)

## Images Generated
- **Alpha mask overlay**: `test_quality/xseg_guided/test1_alpha_mask.png`
  - JET colormap heatmap overlaid on face crop
  - Cool colors (blue) = alpha=0 (keep swap)
  - Warm colors (red) = alpha=1 (blend original back)

## Programmatic Metrics
- **Alpha coverage**: 7.6% (87% improvement from 57% raw XSeg)
- **Test result**: PASSED (coverage < 15%)
- **Shape**: (785, 519) - matches face crop dimensions
- **Dtype**: float32
- **Range**: [0, 1]

---

## Questions for User (Please Answer)

### 1. **Alpha Coverage Distribution**
Looking at `test_quality/xseg_guided/test1_alpha_mask.png`:

**Q1a**: In the heatmap, which areas show warm colors (red/yellow = high alpha = will blend original back)?
- [ ] Only the corndog/food
- [ ] Corndog + lips
- [ ] Corndog + lips + nose
- [ ] Other (describe): _______________

**Q1b**: Are there any face features (eyes, nose, cheeks) incorrectly marked as occluded (warm colors)?
- [ ] Yes (describe which features): _______________
- [ ] No, only lips/nose/corndog are warm

### 2. **Expected Occlusion Areas**
Based on the original zBam.png image:

**Q2a**: What % of the face should ideally have alpha > 0 (blend original back)?
- [ ] 0-5% (corndog tip only)
- [ ] 5-10% (corndog + immediate lip area)
- [ ] 10-15% (corndog + lips + part of nose)
- [ ] >15% (describe): _______________

**Q2b**: Is the current 7.6% coverage appropriate for this image?
- [ ] Yes, looks correct
- [ ] No, too low (missing occlusion areas)
- [ ] No, too high (covering non-occluded areas)

### 3. **Landmark Polygon Accuracy**
The algorithm uses landmarks 48-67 (lips) + 27-35 (nose) to create the interior polygon.

**Q3a**: Does the polygon appear to correctly cover the lip/nose region where the corndog is?
- [ ] Yes, polygon matches occlusion area
- [ ] No, polygon is too small (missing occluded areas)
- [ ] No, polygon is too large (includes non-occluded areas)

**Q3b**: Should we adjust the landmark selection?
- [ ] Keep current (48-67 lips + 27-35 nose)
- [ ] Add more landmarks (specify which): _______________
- [ ] Remove landmarks (specify which): _______________

### 4. **Visual Quality Assessment**
**Q4a**: On a scale of 1-10, how well does this alpha mask represent the actual occlusion in zBam.png?
- Rating: _____ / 10
- Reason: _______________

**Q4b**: What would make this better?
- [ ] Nothing, it's good as-is
- [ ] Expand coverage slightly
- [ ] Reduce coverage slightly
- [ ] Other (describe): _______________

### 5. **Next Steps**
**Q5**: Should we proceed to Task 2 (integrate into TransparencyHandler) with this alpha mask approach?
- [ ] Yes, proceed as-is
- [ ] Yes, but adjust _______________  first
- [ ] No, rethink the approach because _______________

---

## Notes
(Add any additional observations or concerns here)

---

## Programmatic Improvements Identified
Based on user answers, add any questions that could have been automated:
- [ ] None yet (first test)
