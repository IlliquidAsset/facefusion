# Test 3: BiSeNet Lip-Only Occlusion

## Test Execution Summary
- **Date**: 2026-01-27
- **Test**: `scripts/test_bisenet_occlusion.py`
- **Result**: ✅ PASS
- **Alpha Coverage**: **1.8%** (target: lip-only, baseline: 57% raw XSeg, 7.6% landmark-guided)

## Images Generated
- **BiSeNet alpha overlay**: `test_quality/xseg_guided/test3_bisenet.png`
  - JET colormap heatmap overlaid on face crop
  - Cool colors (blue) = alpha=0 (keep swap)
  - Warm colors (red) = alpha=1 (blend original back)

## Programmatic Metrics
- **Alpha coverage**: 1.8% (97% reduction from 57% raw XSeg, 76% reduction from 7.6% landmark-guided)
- **Coverage type**: Lip regions only (upper-lip + lower-lip from BiSeNet)
- **Test result**: 33/33 PASSED (31 transparency + 2 BiSeNet)
- **Shape**: (785, 519) - matches face crop dimensions
- **Dtype**: float32
- **Range**: [0, 1]

---

## Questions for User (Please Answer)

### 1. **Alpha Coverage Restriction**
Looking at `test_quality/xseg_guided/test3_bisenet.png`:

**Q1a**: Is the alpha coverage restricted to lips only?
- [ ] Yes, only lips show warm colors
- [ ] No, other areas also warm (specify): _______________
- [ ] Partially (describe): _______________

**Q1b**: Compared to landmark-guided (7.6%), is 1.8% coverage appropriate?
- [ ] Yes, more focused is better
- [ ] No, too restrictive (missing occlusion areas)
- [ ] About right

### 2. **Eyes and Nose**
**Q2a**: Are the eyes fully swapped (no original bleed)?
- [ ] Yes, eyes are completely from source
- [ ] No, some original showing (describe): _______________
- [ ] Can't tell from alpha mask

**Q2b**: Is the nose fully swapped?
- [ ] Yes, nose is completely from source
- [ ] No, some original showing (describe): _______________
- [ ] Can't tell from alpha mask

### 3. **Lip Occlusion Quality**
**Q3a**: Does the corndog show through naturally in lip regions?
- [ ] Yes, looks natural
- [ ] No, artifacts visible (describe): _______________
- [ ] Can't tell from alpha mask alone

**Q3b**: Is 1.8% coverage sufficient for the corndog occlusion?
- [ ] Yes, covers the occlusion
- [ ] No, missing parts of corndog
- [ ] Too much (covering non-occluded lip areas)

### 4. **Comparison: Landmark-Guided vs BiSeNet**
**Q4a**: Which approach produces better alpha masks?
- [ ] Landmark-guided (7.6% coverage, lip+nose polygon)
- [ ] BiSeNet (1.8% coverage, semantic lip regions)
- [ ] Equal quality
- [ ] Need to see composites to decide

**Q4b**: Rate BiSeNet approach 1-10:
- Rating: _____ / 10
- Reason: _______________

### 5. **Semantic Regions Accuracy**
**Q5a**: Does BiSeNet's lip segmentation accurately match the actual lip area?
- [ ] Yes, precise
- [ ] No, too small (missing lip edges)
- [ ] No, too large (includes non-lip areas)
- [ ] Can't tell from visualization

**Q5b**: Should we expand BiSeNet regions beyond just lips?
- [ ] No, lips only is correct
- [ ] Yes, add nose regions
- [ ] Yes, add other regions (specify): _______________

### 6. **Next Steps**
**Q6**: Should we:
- [ ] Use BiSeNet for final implementation (1.8% coverage)
- [ ] Use landmark-guided for final implementation (7.6% coverage)
- [ ] Combine both approaches
- [ ] Need to see full composites before deciding

---

## Notes
(Add any additional observations or concerns here)

---

## Programmatic Improvements Identified
Based on user answers, add any questions that could have been automated:
- [ ] Could measure eye/nose region alpha values programmatically
- [ ] Could compare BiSeNet lip mask vs landmark polygon overlap
- [ ] Could measure corndog coverage completeness
