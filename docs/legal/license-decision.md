# License Decision: WatserFace Commercial Pivot

**Date**: 2026-01-30
**Status**: DECIDED
**Supporting Documents**:
- [Code Provenance Audit](code-provenance-audit.md)
- [Jurisdiction Risk Assessment](jurisdiction-risk.md)
- [Training Data Provenance](training-data-provenance.md)

---

## Decision

**Build the commercial product on entirely new foundations. No FaceFusion code. No pretrained weights from non-commercial sources.**

---

## FaceFusion Derivation Analysis

The WatserFace codebase is 63% FaceFusion-derived (OpenRAIL-AS). This code will NOT enter the commercial product. The new product uses a different architecture (REFace MIT code + new training), so no clean-room rewrite is needed — we're building new, not extracting old.

The FaceFusion fork is preserved as R&D history on the `legacy/v0.10-compositing` branch.

**Decision**: No FaceFusion code in commercial product. No licensing conflict.

---

## Training Data Provenance

This is the critical finding. **Neither FaceDancer nor REFace pretrained weights can be used commercially:**

| Component | Block Reason |
|-----------|-------------|
| FaceDancer code | CC BY-NC-SA 4.0 (non-commercial) |
| FaceDancer weights | Trained on VGGFace2 (CC BY-NC) |
| REFace weights | Trained on CelebAMask-HQ (non-commercial); README explicitly prohibits commercial use |
| ArcFace weights | Trained on MS-Celeb-1M (retracted, non-commercial) |

**What IS commercially usable:**

| Component | License |
|-----------|---------|
| REFace architecture (code) | MIT |
| Stable Diffusion v1-4 weights | RAIL-M (commercial OK with behavioral restrictions) |
| GFPGAN | Apache 2.0 |
| InsightFace library code | MIT |
| AuraFace (ArcFace replacement) | Apache 2.0 |

**Decision**: Use REFace architecture (MIT) initialized from Stable Diffusion (RAIL-M), trained on commercially-licensed face data, with AuraFace replacing ArcFace.

---

## Jurisdiction Risk

US federal and state laws overwhelmingly target **nonconsensual** synthetic intimate content. The TAKE IT DOWN Act (2025) criminalizes nonconsensual deepfakes but does not prohibit consensual use.

**Risk level: MODERATE.** The consent manifest system (Task 9) is legally essential, not optional.

Key risks: evolving legislation, platform/payment-processor resistance, ambiguous jurisdictions (Utah).

**Decision**: Proceed with legal consultation ($200-500) before launch. Build consent manifest into the product from day one.

---

## Commercial Architecture Stack

| Layer | Solution | License |
|-------|----------|---------|
| Face swap architecture | REFace (code only) | MIT |
| Diffusion backbone | Stable Diffusion v1-4 | RAIL-M |
| Identity encoder | AuraFace | Apache 2.0 |
| Face detection | InsightFace RetinaFace | MIT |
| Enhancement/upscaling | GFPGAN | Apache 2.0 |
| Training data | FFHQ CC BY-only subset + synthetic augmentation | CC BY / Generated |
| CLI framework | Built from scratch | Original |

**All components are commercially licensable.** The training data path (FFHQ CC BY filter + synthetic) is the cheapest option (~$0 data cost) but may reduce dataset size to ~30-35K faces. Synthetic augmentation via StyleGAN3/SDXL supplements the gap.

---

## Impact on Plan

Tasks 2-3 (evaluation) proceed unchanged — pretrained weights are fine for quality assessment.

Tasks 5-6 (training) require revision:
- **Cannot** fine-tune from REFace pretrained weights
- **Must** train from SD v1-4 initialization using REFace architecture
- **Must** use FFHQ CC BY-only images + synthetic faces as training data
- **Must** replace ArcFace with AuraFace as identity loss signal
- Budget impact: Phase 2 may need the full $1,500 cap + some reserve due to training from weaker initialization

Task 4 (architecture decision) is effectively pre-decided: **REFace architecture is the only viable commercial option** (FaceDancer code is CC BY-NC-SA). Evaluation still useful to establish quality ceiling and fine-tuning targets.

---

## NOT Legal Advice

This document synthesizes technical research, not legal counsel. Consult a licensed attorney before commercial launch.
