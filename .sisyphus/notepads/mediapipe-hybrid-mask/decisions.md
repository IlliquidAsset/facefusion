# Architectural Decisions - MediaPipe Hybrid Mask Plan

## [2026-01-27T23:30] Plan Initialization

**Architecture:**
- Hybrid landmarker: 2DFAN for swap alignment (stable) + MediaPipe478 for mask (dense)
- Composite mask: MediaPipe mesh hull - XSeg obstructions
- Lip deformation: 3-layer approach (geometry warp → texture blend → boundary inpaint)

**Guardrails:**
- MUST NOT modify `thin_plate_spline_warp()` signature
- MUST NOT touch XSeg pipeline or training
- MUST NOT run LaMa on full face (≤15px band only)
- Each lip layer must be independently toggleable
- Ralph loop exit: max 5 iterations OR 3 consecutive <1% improvement

---
