# Issues & Gotchas - MediaPipe Hybrid Mask Plan

## [2026-01-27T23:30] Plan Initialization

**Known Issues:**
- Chin hull contour too tight (61.3% coverage) - clips chin skin on zBam.png
- Mesh hull shape doesn't follow actual jawline at chin (needs expansion)
- Lip deformation not yet validated - MediaPipe landmarks may hallucinate default position instead of tracking actual deformed lips

**Blockers:**
- Task 8.5 gates Tasks 9-12: If lip landmarks don't track deformation, TPS approach must be redesigned

**Risks:**
- LaMa inpainting boundary band might be visible if blend/warp quality is poor
- Each lip layer adds complexity - must remain independently toggleable for debugging

---
