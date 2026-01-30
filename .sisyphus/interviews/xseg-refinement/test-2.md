# Test 2: Landmark-Guided XSeg Integration

## Test Execution Summary
- **Date**: 2026-01-27
- **Test**: `scripts/run_mayo_pipeline.py`
- **Result**: ✅ PASS (31/31 tests)
- **Identity Similarity**: **0.7143** (target: >0.75, baseline dirty swap: 0.8782)

## Images Generated
- **InSwapper composite**: `test_quality/mayo_v2/inswapper-128_03_xseg_composite.png`
- **SimSwap composite**: `test_quality/mayo_v2/simswap-unofficial-512_03_xseg_composite.png`
- **Alpha masks**: `test_quality/mayo_v2/*_05_alpha_mask.png`

## Programmatic Metrics
### InSwapper 128
- **Identity transfer**: 0.7143 (vs 0.8782 dirty swap, 0.7473 clean swap)
- **Identity preservation**: 81.3% of dirty swap quality retained
- **Mean diff**: 0.2%
- **Changed pixels**: 2.1%

### SimSwap 512
- **Identity transfer**: 0.6212 (vs 0.7040 dirty swap, 0.4776 clean swap)
- **Identity preservation**: 88.2% of dirty swap quality retained
- **Mean diff**: 0.3%
- **Changed pixels**: 3.2%

---

## Questions for User (Please Answer)

### 1. **Eyes Quality**
Looking at `test_quality/mayo_v2/inswapper-128_03_xseg_composite.png`:

**Q1a**: Do the eyes match the source identity (Sam) or look like the original target?
- [ ] Source (Sam's eyes)
- [ ] Target (original person's eyes)
- [ ] Mixed/unclear

**Q1b**: Rate the eye quality on a scale of 1-10:
- Rating: _____ / 10
- Issues (if any): _______________

### 2. **Nose Quality**
**Q2a**: Does the nose match the source (Sam) or target?
- [ ] Source (Sam's nose)
- [ ] Target (original nose)
- [ ] Mixed/unclear

**Q2b**: Rate the nose quality on a scale of 1-10:
- Rating: _____ / 10
- Issues (if any): _______________

### 3. **Corndog Preservation**
**Q3a**: Is the corndog preserved naturally in the composite?
- [ ] Yes, looks natural
- [ ] No, artifacts visible (describe): _______________
- [ ] Partially (describe issues): _______________

**Q3b**: Can you see the corndog texture/details clearly?
- [ ] Yes, clear
- [ ] No, blurred/lost
- [ ] Partially visible

### 4. **Overall Identity**
**Q4a**: Does the face look like Sam (source identity)?
- Rating: _____ / 10
- What's wrong (if <8): _______________

**Q4b**: Compared to the dirty swap (0.8782 similarity), is the quality loss acceptable?
- [ ] Yes, corndog preservation worth the 18.7% identity drop
- [ ] No, too much identity lost
- [ ] Borderline (explain): _______________

### 5. **Usability**
**Q5a**: Would you use this output in the final video?
- [ ] Yes, as-is
- [ ] Yes, with minor adjustments (specify): _______________
- [ ] No, needs significant improvement (specify): _______________

**Q5b**: Which model produces better results?
- [ ] InSwapper 128 (0.7143 identity)
- [ ] SimSwap 512 (0.6212 identity)
- [ ] Neither is acceptable

### 6. **Comparison to Previous Approach**
Before landmark-guided XSeg, the composite had 0.38 identity (face interior mask improved it to 0.71).

**Q6**: Is the current 0.7143 identity acceptable, or do we need further improvements?
- [ ] Acceptable, proceed to Task 3 (BiSeNet)
- [ ] Needs improvement (specify what): _______________
- [ ] Try different approach (suggest): _______________

---

## Notes
(Add any additional observations or concerns here)

---

## Programmatic Improvements Identified
Based on user answers, add any questions that could have been automated:
- [ ] Could measure eye region SSIM vs source
- [ ] Could measure nose region SSIM vs source
- [ ] Could detect corndog artifacts programmatically
