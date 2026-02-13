# Draft: WatserFace Software Factory

## Requirements (confirmed)
- Build a Software Factory inspired by StrongDM's model (https://factory.strongdm.ai/)
- Scenario-driven, not test-driven — scenarios as "holdout sets" outside codebase
- Must handle subjective visual output (face swaps, normal maps, inpainting)
- User has provided an extremely detailed build spec with 4 phases

## User's Detailed Spec (received)
The user provided a complete build specification including:
1. **Phase 1**: Scenario Framework + Metric Gates (`factory/` directory structure, Pydantic schemas, YAML scenario definitions, metric gates, performance gates, regression gates, CLI runner, pytest integration)
2. **Phase 2**: LLM-as-Judge Harness (vision evaluation via Anthropic API, structured prompts, statistical aggregation with median/variance)
3. **Phase 3**: Golden Reference Registry (manifest.json, register/compare golden references)
4. **Phase 4**: User Story Scenarios (casual user swap, quality vs fast tradeoff, video OOM, training checkpoint resume)

## Existing Infrastructure (verified via code reading)

### `watserface/studio/quality_checker.py` (VERIFIED)
- `QualityChecker` class with: `compute_ssim`, `compute_psnr`, `compute_identity_similarity`, `compute_blur_score`, `compute_artifact_score`
- `QualityMetrics` dataclass: ssim, psnr, identity_similarity, blur_score, artifact_score, overall_score
- `AutoQualityFilter`: frame-level accept/reject with configurable thresholds
- Weighted overall score: ssim(0.25) + psnr(0.15) + identity(0.30) + blur(0.15) + artifact(0.15)
- Already has: comparison view, slider comparison, difference heatmap
- **Import path**: `from watserface.studio.quality_checker import QualityChecker` ✅

### `watserface/training/validators/quality.py` (VERIFIED)
- `QualityValidator` with InsightFace (buffalo_l) ArcFace integration
- Identity cosine similarity threshold: 0.6 default
- Face detection confidence threshold: 0.7
- Visual artifact detection: blur (Laplacian variance), color artifacts (HSV saturation)
- `RecursiveRepair` class: uses diffusion inpainting for automated repair
- Video analysis with frame sampling
- **Import path**: `from watserface.training.validators.quality import QualityValidator` ✅

### `eval/` directory (VERIFIED)
- Standalone evaluation harness for face-swap identity preservation
- `eval_identity.py`: single-pair ArcFace cosine similarity
- `eval_batch.py`: batch evaluation across frames
- `eval_occlusion.py`: occlusion robustness testing (clean vs occluded)
- `compare_results.py`: architecture comparison (FaceDancer vs REFace) with kill threshold (p95 identity >= 0.85)
- `prepare_test_set.py`: creates test set structure (clean, occluded, complex, extreme_angle)
- Uses `insightface` directly, no WatserFace dependencies

### Test Infrastructure
- Existing tests: `tests/test_quality_metrics.py` (SSIM tests)
- `tests/test_lip_blend.py` (edge SSIM, custom SSIM impl)
- `tests/test_vision.py` (needs investigation)
- Many CLI tests: face_swapper, face_enhancer, face_editor, etc.
- Framework: pytest

## Research Findings (from librarian)

### Multi-tier quality approach recommended:
- **Tier 1 (Fast)**: PSNR, SSIM — fast smoke tests, poor human correlation
- **Tier 2 (Perceptual)**: LPIPS (recommended primary metric), NIQE, BRISQUE
- **Tier 3 (Face-specific)**: ArcFace cosine sim (identity), AU detection (expression)
- **Tier 4 (VLM-as-Judge)**: Multimodal LLM evaluation — emerging, use as advisory not gate

### Key tools:
- `pyiqa`: Comprehensive IQA library with LPIPS, NIQE, BRISQUE, SSIM, FID, KID
- `insightface`: Already in use for ArcFace (buffalo_l)
- LPIPS: Best correlation with human perception for perceptual quality
- Face-specific: No production-ready face-swap-specific quality metric yet

### LLM-as-Judge findings:
- Multimodal LLMs CAN assess visual quality but struggle with fine-grained distinctions
- Best approach: pairwise comparison > absolute scoring
- Median of N samples (N=3-5) reduces variance
- Flag high-variance dimensions (std > 2.0) as "unreliable"
- Cost concern: $0.01-0.05/image — expensive at scale
- **Recommendation**: Use as Tier 4 advisory, not primary gate

## Technical Decisions

### User's spec aligns well with research findings:
- Pydantic schemas for scenario definitions ✅
- YAML-based scenarios (holdout pattern) ✅  
- MetricAssertion with operator/value ✅
- LLMJudgeConfig with min_samples=3 and per-dimension thresholds ✅
- Golden reference registry with regression comparison ✅
- CLI runner + pytest integration ✅

### Potential gaps/questions to explore:
1. **LPIPS not in spec**: User's spec uses SSIM/PSNR/identity_similarity/blur/artifact but NOT LPIPS — research strongly recommends LPIPS as primary perceptual metric
2. **Expression preservation**: No AU (Action Unit) detection in spec — research recommends it
3. **No-reference metrics**: NIQE/BRISQUE not in spec — useful for artifact detection without reference
4. **Comparative scenario type**: Needs special runner logic (run both presets, compare deltas) — complex
5. **Training checkpoint scenario**: Needs special runner logic (train, interrupt, resume, compare) — complex
6. **Fixture population**: How will test images be provided? Git LFS? User-provided? Generated?
7. **Cost management**: LLM judge at scale could be expensive — need budget/skip controls
8. **blur_degradation metric**: Referenced in YAML but not in QualityChecker — needs to be derived

## Decisions Made (Interview)
1. **LPIPS**: YES — add pyiqa dependency, integrate LPIPS as first-class metric
2. **Complex scenario types**: Build ALL types now (comparative, regression, visual_quality, performance)
3. **Delivery**: One plan, all 4 phases. Phases are commit boundaries.
4. **GPU requirement**: GPU required. No CPU fallback needed.
5. **blur_degradation**: Rename to blur_score (use existing QualityChecker metric directly)
6. **Test fixtures**: User-populated, README instructions, helper script for frame extraction

## Scope Boundaries
- INCLUDE: Full factory/ directory with scenarios, gates, judges, golden registry
- INCLUDE: CLI runner + pytest integration
- INCLUDE: User story scenarios as YAML
- INCLUDE: LPIPS via pyiqa as first-class metric
- INCLUDE: All scenario types (visual_quality, performance, comparative, regression)
- EXCLUDE: Actually populating fixture images (user responsibility)
- EXCLUDE: CI/CD pipeline configuration (GitHub Actions, etc.)
- EXCLUDE: CPU fallback paths
