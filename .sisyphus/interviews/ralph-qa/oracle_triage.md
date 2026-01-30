# Oracle Triage — 2026-01-29

## Key Finding: Identity Metric May Be Broken

The occluded target swap (0.879) scoring HIGHER than the clean target swap (0.747) suggests the cosine similarity metric rewards under-adaptation — outputs that look like the source face pasted on, rather than naturally blended into target geometry.

**Expected InSwapper 128 range: 0.55–0.80.** Our 0.879 is above expected range.

## Noise vs Real

| Metric Δ | Verdict | Reasoning |
|----------|---------|-----------|
| Identity -0.006 (XSeg composite) | NOISE | Within ArcFace measurement variance |
| Color shift 9.5 LAB | REAL, FIXABLE | LAB histogram matching post-process will fix |
| Sharpness 4.8 | REAL, EXPECTED | 128px native resolution — known limitation |
| Artifact score 100% | FALSE POSITIVE | Diff detector comparing against wrong baseline (original target face) |
| Occluded > Clean identity | SUSPICIOUS | Metric likely measuring wrong thing |

## Auto-Fixes Applied by Sisyphus

None yet — awaiting human judgment on metric validity before optimizing.

## Auto-Fixes Available (not yet applied)

1. **Color shift** → LAB histogram matching (Quick, <1h)
2. **Artifact detector** → Switch to no-reference metric or compare against source-warped-to-target (Short, 1-4h)
3. **Sharpness** → GFPGAN 1.4 @ 80% blend (already validated in Phase 2.5)

## Questions for Human (3 questions)

Only 3 questions needed — Oracle resolved the rest:

1. **[Image 01 vs 02 vs 03]**: Visual quality assessment — does the swap look natural or pasted?
2. **Metric design**: Should we add naturalness/pose-alignment alongside identity similarity?
3. **[Image 04]**: Does the lip shadow/fringe blending look seamless around the occlusion?

## Layer Stack Recommendation

Not applicable yet — this is the first baseline measurement. No layers have been evaluated cumulatively.
