# Ralph QA Review — 2026-01-29

## Oracle Summary
- Auto-resolved: 3 issues (1 noise, 1 false positive, 1 expected limitation)
- Auto-fixable (pending): 2 (color shift, sharpness enhancement)
- Questions for you: 3

## Metrics Summary

| Step | Identity | BG SSIM | Color Shift | Sharpness | Status |
|------|----------|---------|-------------|-----------|--------|
| Baseline (dirty swap) | 0.879 | 1.000 | 9.50 | 4.8 | ⚠️ Identity suspiciously high |
| XSeg Composite | 0.873 | — | — | — | ✅ Only -0.006 drop |
| Video (30 frames) | 0.845 | — | — | — | ✅ Temporal consistency 0.972 |

### InSwapper 128 Identity Scores
| Variant | Score | Note |
|---------|-------|------|
| Dirty swap (occluded) | 0.879 | ⚠️ Above expected 0.55–0.80 |
| XSeg composite | 0.873 | ✅ Negligible drop |
| Clean swap (no occlusion) | 0.747 | 🔍 Lower than occluded — paradox |

## Questions

- [Image 01 vs 02 vs 03]: Look at dirty swap, XSeg composite, and original target side by side. Does the swapped face look naturally integrated, or does it look like a paste job? Oracle notes: identity score 0.879 is above the expected range (0.55–0.80), which may indicate the model isn't adapting enough to target geometry.

- [Metric Design]: The identity metric currently rewards outputs that look exactly like the source. A swap that adapts jawline/eye shape to the target scores LOWER. Should we add a naturalness metric (pose alignment, geometry matching) alongside raw identity similarity?

- [Image 04]: Look at the lip region around the corndog occlusion. Does the lip shadow/fringe blending look seamless, or is there a visible halo/hard edge where the occlusion meets swapped skin?
