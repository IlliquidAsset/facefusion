# Training Data Provenance: FaceDancer & REFace

**Date**: 2026-01-30
**Purpose**: Determine if FaceDancer and REFace pretrained models can be used commercially for adult content production.

---

## BOTTOM LINE: Neither Model Can Be Used Commercially As-Is

Every layer of the stack is blocked:

| Component | License | Commercial? | Adult Content? |
|-----------|---------|-------------|---------------|
| **FaceDancer code** | CC BY-NC-SA 4.0 | NO | NO |
| **FaceDancer weights** | Trained on VGGFace2 (CC BY-NC) | NO | NO |
| **REFace code** | MIT | YES | YES |
| **REFace weights** | Trained on CelebAMask-HQ (non-commercial) | NO | NO |
| **ArcFace weights** (both models) | Non-commercial research only | NO | NO |
| **Stable Diffusion v1-4** (REFace init) | CreativeML Open RAIL-M | YES (with restrictions) | Behavioral restrictions apply |

**REFace's own README explicitly states**: "Use of this model for commercial purposes is strictly prohibited."

---

## FaceDancer: Fully Non-Commercial

### Code License
CC BY-NC-SA 4.0 — prohibits commercial use of code AND derivatives.

### Training Data
- **VGGFace2**: CC BY-NC 4.0 (non-commercial). 3.3M celebrity face images scraped from Google without individual consent. Download links now removed from official site.
- **ArcFace encoder**: Trained on MS-Celeb-1M (retracted by Microsoft in 2019 due to ethical concerns). Non-commercial weights only.

### Verdict
No path to commercial use. Would need to retrain the entire model from scratch on a new dataset, using new architecture code (since the code itself is NC).

---

## REFace: Code is MIT, But Weights Are Blocked

### Code License
MIT — fully permissive, commercial use allowed. This means the **architecture design** can be reused.

### Training Data
- **CelebAMask-HQ**: Non-commercial research only. 30K celebrity face images. Authors explicitly prohibit commercial use of models trained on this data.
- **Stable Diffusion v1-4**: RAIL-M allows commercial use with behavioral restrictions (no illegal content, no exploitation of minors, etc.). This is the one clear component.

### ArcFace Identity Encoder
- InsightFace framework code: MIT (commercial OK)
- Pretrained model weights: Non-commercial only. Trained on MS-Celeb-1M.
- **This is a known blocker across the industry.** Multiple HuggingFace discussions flag this.

### Verdict
Can use the **architecture** (MIT code) but must retrain from scratch. Cannot use pretrained weights.

---

## ArcFace: The Hidden Blocker

Both FaceDancer and REFace use ArcFace for identity embedding. The pretrained weights are non-commercial. This means:

1. Any model that uses ArcFace embeddings as a training signal inherits the restriction
2. Any inference pipeline using ArcFace for identity scoring needs replacement

### Commercially-Licensed Alternative
**AuraFace** — Apache 2.0 licensed face recognition model. Would need to verify quality parity with ArcFace and potentially retrain the face-swap model using AuraFace embeddings.

---

## Stable Diffusion v1-4: Usable With Caveats

The CreativeML Open RAIL-M license allows commercial use but carries behavioral restrictions:
- Must not generate illegal content
- Must not exploit minors
- Must not generate defamatory/harassing content
- Derivative models must carry the same restrictions

The LAION-2B training data has legal challenges (ongoing lawsuits from Getty Images, individual artists). However, the model weights themselves are licensed for commercial use under RAIL-M.

**For adult content with consenting adults**: RAIL-M does not appear to prohibit this, provided the content is legal in the jurisdiction.

---

## Path Forward for Commercial Use

To build a commercially viable product, ALL of the following are required:

### 1. Architecture (Solved)
Use REFace's architecture (MIT licensed). The paper's methodology and code are freely usable.

### 2. Training Data (Unsolved — Biggest Blocker)
Need a face dataset with commercial licensing. Options:
- **License a commercial dataset** from a data provider (cost unknown)
- **Collect your own dataset** with proper consent (expensive, time-consuming)
- **Use FFHQ subset** — some images are CC BY (commercial OK) but others are CC BY-NC. Would need to filter to commercial-only images (~40-50% of the 70K)
- **Synthetic face generation** — use StyleGAN3/SDXL to generate training faces (no real person consent needed, but quality may differ)

### 3. Identity Encoder (Solvable)
Replace ArcFace with AuraFace (Apache 2.0) or another commercially-licensed face recognition model.

### 4. Diffusion Initialization (Solved)
Stable Diffusion v1-4 (RAIL-M) or SDXL (RAIL-M) can be used commercially.

### 5. Enhancement/Upscaling (Solved)
GFPGAN is Apache 2.0. Usable commercially.

---

## Revised Budget Impact

The training data blocker significantly changes the economics:

| Approach | Cost | Time | Risk |
|----------|------|------|------|
| Filter FFHQ to CC BY-only images + synthetic augmentation | $0 (data) + $800-1500 (training) | 2-3 weeks | Medium — reduced dataset size may hurt quality |
| Generate synthetic faces with StyleGAN3/SDXL | $200-500 (generation GPU) + $800-1500 (training) | 3-4 weeks | Medium — synthetic data distribution differs from real |
| License commercial dataset | $1,000-10,000+ (unknown) | 1-2 weeks + negotiation | Low technical risk, high cost risk |
| Collect own dataset with consent | $500-2000 (logistics) | 4-8 weeks | Low legal risk, very slow |

**Recommendation**: Start with FFHQ CC BY-only filter + synthetic augmentation. Cheapest path to test if the architecture works before investing in better data.

---

## Impact on Plan

The Phase 1 evaluation (Tasks 2 and 3) remains valid — we can still evaluate FaceDancer and REFace's pretrained models for quality assessment. But the Phase 2 fine-tuning strategy must change:

- Cannot fine-tune FROM pretrained weights (non-commercial)
- Must train FROM Stable Diffusion initialization + REFace architecture
- Need commercially-licensed face data
- Need ArcFace replacement (AuraFace)

This increases Phase 2 cost and timeline significantly.
