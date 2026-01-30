# WatserFace Video Swap Quality Analysis

## Critical Issues Identified

### 1. Mouth Interior Detection - BROKEN
**Problem**: Inner lip landmarks detect the lip LINE, not the actual mouth opening.

**Measurements (Frame 72)**:
- Inner lip height: **8.2px** (WRONG - this is just the lip line)
- Outer lip height: **37.5px** (correct)
- Ratio: 0.220 (inner should be ~70-80% of outer when mouth open)
- Nose width: 42.1px (for comparison)

**Root Cause**: 2dfan4 68-point landmarker places inner lip points (60-67) at the lip EDGE, not the actual mouth cavity opening. When mouth is open with food, the actual opening is much larger.

**Impact**: Mouth interior mask is too small, doesn't preserve corndog properly.

---

### 2. Face Size Jitter - SEVERE
**Problem**: Face size varies wildly frame-to-frame, causing visible flashing.

**Measurements (30 frames)**:
- Bounding box area variance: **22.8%** (95,557 to 120,053 px²)
- Face height variance: **30.4%** (166.6 to 228.4 px)
- Largest single-frame jump: **9,326 px²** (frame 22→23)
- Average frame-to-frame change: 2,280 px²

**Frames with major jitter**:
- Frame 12→13: 7,514 px² change
- Frame 22→23: 9,326 px² change  
- Frame 26→27: 4,854 px² change

**Root Cause**: Face detector (YOLO) and landmarker (2dfan4) produce inconsistent bounding boxes and landmark positions across frames. No temporal stabilization.

**Impact**: Face appears to "breathe" or flash smaller/larger every few frames.

---

### 3. Eye Quality - SimSwap vs InSwapper
**Problem**: SimSwap 512 has worse perceptual eye quality despite higher technical metrics.

**Measurements**:
| Metric | InSwapper 128 | SimSwap 512 |
|--------|---------------|-------------|
| Left eye sharpness | 107.9 | 264.9 |
| Left eye edges | 27.4 | 41.5 |
| Right eye sharpness | 41.9 | 70.3 |
| Right eye edges | 18.6 | 27.6 |

**Paradox**: SimSwap has 2-3x higher sharpness/edge metrics, but eyes look WORSE perceptually.

**Hypothesis**: SimSwap over-sharpens, creating artificial edges. InSwapper preserves natural eye texture better. Metrics don't capture perceptual quality.

---

### 4. Quality Metrics - INADEQUATE
**Problem**: Current metrics (diff_mean, identity_score) don't detect:
- Eye quality degradation
- Face size jitter
- Mouth misalignment
- Temporal inconsistency

**Missing Metrics**:
- Perceptual quality (LPIPS, FID)
- Temporal stability (optical flow consistency)
- Facial feature alignment (eye/mouth position accuracy)
- Artifact detection (over-sharpening, unnatural edges)

---

### 5. XSeg Cheekbone Masking - PARTIALLY FIXED
**Problem**: Left cheekbone (landmarks 1-3, 41) incorrectly marked as occluded.

**Status**: Cheek protection mask implemented, but may need tuning.

**Verification Needed**: Check if landmarks 1, 2, 3, 41 are now properly preserved.

---

### 6. Temporal Smoothing - INSUFFICIENT
**Problem**: 5-frame window smoothing reduced flicker by 74%, but jitter remains.

**Current**: Mask temporal smoothing only
**Missing**: 
- Landmark temporal smoothing (Savitzky-Golay filter)
- Bounding box stabilization
- Optical flow-based motion compensation

---

## Recommendations

### Immediate Fixes (High Priority)

1. **Fix Mouth Interior Detection**
   - Use outer lip polygon instead of inner lip
   - Expand by 20-30% inward to capture actual opening
   - Use brightness + edge detection to find true mouth cavity

2. **Stabilize Face Size**
   - Implement temporal smoothing on bounding boxes
   - Use exponential moving average (EMA) for landmarks
   - Consider optical flow for motion prediction

3. **Revert to InSwapper for Eyes**
   - Use InSwapper 128 for eye regions
   - Use SimSwap 512 for rest of face
   - Blend at eye boundaries

4. **Implement Proper Quality Metrics**
   - Add LPIPS for perceptual quality
   - Add temporal consistency score
   - Add facial feature alignment check

### Medium Priority

5. **Improve XSeg Cheekbone Fix**
   - Verify landmarks 1-3, 41 are preserved
   - Tune protection mask strength

6. **Enhanced Temporal Smoothing**
   - Add Savitzky-Golay filter for landmarks
   - Implement optical flow compensation

### Low Priority

7. **Investigate Diffusion Resolution**
   - Check if model resolution matches video resolution
   - Verify no downsampling in pipeline

---

## Test Results Summary

| Test | Status | Notes |
|------|--------|-------|
| Resolution (SimSwap 512) | ⚠️ PARTIAL | Better texture, worse eyes |
| XSeg Temporal | ⚠️ PARTIAL | 74% flicker reduction, jitter remains |
| DKT Trajectory | ❌ NOT TESTED | Implemented but not validated |
| Cheekbone Fix | ⚠️ NEEDS VERIFICATION | Implemented, unclear if working |
| Mouth Depth | ❌ BROKEN | Mask too small, misaligned |
| Overall Quality | ❌ UNUSABLE | Multiple critical issues |

---

## Files for Review

**Mask Overlays (Transparent)**:
- `overlay_ALL_MASKS_combined.png` - All masks on one image
- `overlay_mouth_interior.png` - Shows mouth mask (too small)
- `overlay_xseg_occluded.png` - Shows XSeg occlusion detection
- `overlay_cheekbone_protection.png` - Shows cheek protection

**Analysis**:
- `mouth_size_analysis_detailed.png` - Shows inner/outer lip landmarks
- `eye_quality_comparison.png` - InSwapper vs SimSwap eyes (3x zoom)

**Videos**:
- `video_ALL_FIXES_combined.mp4` - All fixes applied (still broken)
- `FINAL_before_after.mp4` - Baseline vs fixed comparison
