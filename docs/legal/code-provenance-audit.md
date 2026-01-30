# Code Provenance Audit: WatserFace vs FaceFusion

**Date**: 2026-01-30
**Purpose**: Determine what percentage of WatserFace code is derived from FaceFusion (OpenRAIL-AS) vs. original work, to inform licensing strategy for commercialization.

---

## Summary

| Category | Files | Lines | % of Total |
|----------|-------|-------|-----------|
| **(A) FaceFusion-derived** (unmodified or lightly modified) | ~153 | ~23,739 | **63%** |
| **(B) Heavily modified** (FaceFusion origin, >50% rewritten) | ~5-8 | ~2,000 | **5%** |
| **(C) Fully original WatserFace** | ~43 | ~10,644 | **28%** |
| **Shared/config/init** | misc | ~1,220 | **3%** |
| **Total** | ~196 | ~37,603 | 100% |

---

## Category A: FaceFusion-Derived (Unmodified/Lightly Modified)

**153 files, ~23,739 lines**

These files are substantially the same as FaceFusion 3.3.4. They form the core inference pipeline, UI framework, and utility infrastructure.

### Core Pipeline (cannot be removed without rewrite)
- `watserface/core.py` — Application lifecycle
- `watserface/face_detector.py` — Face detection wrapper
- `watserface/face_classifier.py` — Face classification
- `watserface/face_recognizer.py` — ArcFace identity embedding
- `watserface/face_selector.py` — Face selection logic
- `watserface/face_store.py` — Face caching
- `watserface/inference_manager.py` — ONNX session management
- `watserface/execution.py` — Device/provider management
- `watserface/normalizer.py` — Input normalization
- `watserface/vision.py` — Image I/O utilities

### Processor Modules (FaceFusion standard)
- `watserface/processors/modules/face_swapper.py` (842 lines) — **Heavily modified** (Category B, see below)
- `watserface/processors/modules/face_enhancer.py` — GFPGAN/CodeFormer wrapper
- `watserface/processors/modules/frame_enhancer.py`
- `watserface/processors/modules/frame_colorizer.py`
- `watserface/processors/modules/face_debugger.py`
- `watserface/processors/modules/face_editor.py`
- `watserface/processors/modules/age_modifier.py`
- `watserface/processors/modules/expression_restorer.py`
- `watserface/processors/modules/lip_syncer.py`

### UI Framework
- `watserface/uis/` — Entire Gradio UI framework (~25+ files)
- Layouts, components, core rendering

### Utilities
- `watserface/ffmpeg.py`, `watserface/ffmpeg_builder.py` — Video I/O
- `watserface/filesystem.py`, `watserface/temp_helper.py`
- `watserface/download.py`, `watserface/hash_helper.py`
- `watserface/config.py`, `watserface/args.py`, `watserface/state_manager.py`
- `watserface/wording.py`, `watserface/choices.py`, `watserface/types.py`

### Assessment
**These files ARE the FaceFusion project.** They carry the OpenRAIL-AS license. Any commercial product using these files is bound by OpenRAIL-AS restrictions, including the prohibition on non-consensual intimate imagery.

---

## Category B: Heavily Modified (FaceFusion Origin, Significantly Rewritten)

**~5-8 files, ~2,000 lines**

These files started as FaceFusion code but have been substantially rewritten:

| File | Lines | Modifications |
|------|-------|--------------|
| `face_helper.py` | 495 | Added: `create_normal_map()`, `warp_lip_to_target()`, `TemporalBBoxStabilizer`, `TemporalLandmarkStabilizer`, `transform_points_3d()` |
| `face_masker.py` | 247 | Added: `create_mesh_hull_mask()`, `create_occlusion_mask_guided()`, `create_mouth_interior_mask()`, `create_inpainting_mask()`, `create_composite_mask()` |
| `face_landmarker.py` | 281 | Added: MediaPipe 478-point detection, hybrid mode, Z-coordinate capture |
| `face_analyser.py` | 130 | Added: Temporal stabilization integration |
| `face_swapper.py` | 842 | Added: `swap_face_hybrid()`, dirty swap pipeline, hybrid model registration |

### Assessment
These files contain both FaceFusion code and significant original contributions. The original additions (normal maps, TPS warping, mesh hulls, hybrid landmarks) are novel, but they're interleaved with FaceFusion's code. **Extracting just the original portions would require refactoring.**

---

## Category C: Fully Original WatserFace Code

**~43 files, ~10,644 lines**

These files have no FaceFusion equivalent. They were created entirely for WatserFace:

### Studio Module (8 files)
- `watserface/studio/` — Unified workflow UI, identity builder, occlusion trainer, orchestrator, project management, quality checker, export presets, state management

### Training Infrastructure (22 files)
- `watserface/training/` — Complete training backend: core orchestration, dataset extraction, landmark smoothing, device utils
- `watserface/training/models/` — XSeg U-Net, InstantID adapter, LoRA adapter
- `watserface/training/datasets/` — XSeg, InstantID, LoRA dataset loaders
- `watserface/training/trainers/` — Identity, XSeg, LoRA training loops
- `watserface/training/validators/` — Quality validation

### Depth Estimation (3 files)
- `watserface/depth/` — DKT estimator, monocular depth, temporal depth smoothing

### Inpainting (4 files)
- `watserface/inpainting/` — Diffusion wrapper, ControlNet integration, boundary detection

### Transparency/Occlusion Pipeline (3 files)
- `watserface/processors/modules/transparency_handler.py` (750+ lines) — XSeg compositing, alpha computation, lip shadow, temporal video processing
- `watserface/processors/modules/lip_fringe.py` (123 lines) — Contact shadow painting
- `watserface/processors/modules/occlusion_inpainter.py` — Generative inpainting orchestration

### Standalone Modules (3 files)
- `watserface/face_inpainter.py` — LaMa ONNX integration
- `watserface/identity_profile.py` — Identity embedding management
- `watserface/preset_manager.py` — Smart preview preset management

### Assessment
**This code is entirely original and owned by the WatserFace author.** It can be relicensed freely. However, much of it depends on Category A infrastructure (imports, types, state management) and cannot run standalone without a compatible runtime.

---

## Licensing Implications

### For Commercialization in Adult Content

1. **Category A code (63%) is a hard blocker.** OpenRAIL-AS explicitly restricts use for creating non-consensual intimate imagery. Even if all content is consensual, the license's wording is ambiguous enough to create legal risk.

2. **Category C code (28%) is freely licensable** by the author under any terms.

3. **Category B code (~5%) is a gray area.** The original additions could be extracted, but the FaceFusion substrate would need replacement.

### Recommended Path

**Clean-room rewrite of Category A is NOT necessary for the commercial pivot.** Here's why:

The commercial product will use a **new architecture** (FaceDancer or REFace), not FaceFusion's inference pipeline. The Category A code (face_detector, face_swapper, inference_manager, UI framework) will be **replaced entirely**, not carried forward.

What the commercial product actually needs:
- Face detection → Use InsightFace directly (Apache 2.0) or FaceDancer's built-in RetinaFace
- Face swap → FaceDancer (MIT) or REFace (Apache 2.0) — neither is FaceFusion-derived
- Identity embedding → InsightFace ArcFace (Apache 2.0 for the library, check model weights)
- Enhancement → GFPGAN (Apache 2.0) or CodeFormer (S-Lab License)
- CLI framework → Built from scratch (argparse/click)

**The only Category C code worth carrying forward is institutional knowledge** (.sisyphus/ plans, learnings, decisions) and evaluation scripts — none of which are FaceFusion-derived.

---

## Decision

**The commercial product should be built on new foundations (FaceDancer/REFace + InsightFace + GFPGAN), not on the FaceFusion fork.** This eliminates the OpenRAIL-AS constraint entirely.

The WatserFace fork remains as:
- R&D archive (legacy/v0.10-compositing branch)
- Knowledge base (.sisyphus/ directory)
- Test asset repository (test images, evaluation methodology)

No FaceFusion code enters the commercial product. No clean-room rewrite needed — we're building new, not copying old.

---

## Remaining Question

**Training data provenance for FaceDancer and REFace** — what datasets were these models trained on, and do those datasets permit commercial use in adult content? (See separate report: training-data-provenance.md)
