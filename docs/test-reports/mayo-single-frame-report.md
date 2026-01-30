# Single Frame Mayonnaise Transparency Test Report

**Date**: January 26, 2026  
**Task**: Phase 2.5 Task 3 (#88)  
**Status**: PASS

---

## Test Configuration

- **Script**: `test_phase25_transparency.py`
- **Target**: `/Users/kendrick/Documents/FS Source/zBam.png` (corn dog with mayo)
- **Swap**: `previewtest/solution_dirty_swap.png`
- **Depth**: `previewtest/frame_depth.png`
- **Compositing Formula**: `Final = (Dirty_Swap * (1 - Alpha)) + (Original_Target * Alpha)`
- **Depth Threshold**: 0.74 (188/255)

## Results

### Clean Baseline (No Occlusion)
- **SSIM vs Target**: 0.9993
- **SSIM vs Swap**: 0.9730
- **Status**: PASS

### Mayo Occluded
- **SSIM vs Target**: 0.6368
- **SSIM vs Swap**: 0.9592
- **Status**: PASS

### Video Temporal Coherence
- **Frames processed**: 10
- **Temporal consistency**: 0.9995
- **Target**: >0.9
- **Status**: PASS

## Output Files

| File | Size | Description |
|------|------|-------------|
| `previewtest/phase25_mayo_occluded_alpha.png` | 17K | Alpha mask from depth estimation |
| `previewtest/phase25_mayo_occluded_result.png` | 4.5M | Composited result |
| `previewtest/phase25_mayo_occluded_comparison.png` | 917K | Before/after comparison |
| `previewtest/phase25_clean_baseline_result.png` | - | Clean baseline result |

## Analysis

### SSIM Interpretation
- **Clean baseline SSIM 0.9993**: Near-perfect compositing when no occlusion present
- **Mayo SSIM 0.6368 vs target**: Expected - the face swap changes the face significantly
- **Mayo SSIM 0.9592 vs swap**: High similarity to dirty swap, meaning compositing preserves most of the swap while adding mayo back

### Temporal Coherence
- **0.9995**: Excellent temporal consistency across 10 frames
- Well above 0.9 target

## Conclusion

The Mayonnaise Strategy compositing formula works correctly:
1. Dirty swap preserves face identity under occlusion
2. Depth-based alpha mask correctly identifies mayo as foreground
3. Compositing restores mayo on top of swapped face
4. Temporal coherence is maintained across frames

**User validation required**: Visual QA needed to confirm mayo looks natural.
