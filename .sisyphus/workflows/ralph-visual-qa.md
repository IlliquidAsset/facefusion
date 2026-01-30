# Ralph Visual QA Workflow

## Trigger Command
**`/ralph-qa`** or **`ralph-qa`** in conversation

## Purpose
Structured visual QA review of output images with human-in-the-loop for issues requiring human judgment.

## Workflow

### Phase 0: Baseline Quality Gate (Milestone 0) — MANDATORY FIRST STEP

**Before evaluating ANY advanced pipeline output (lip deformation, transparency, inpainting), you MUST first validate the baseline "dirty swap" quality.** This is the Milestone 0 check — it validates the foundation before measuring improvements on top of it.

#### What to Measure on the Dirty Swap (No Layers Applied)

Run these metrics on the `loop_0_baseline/result.jpg` (dirty swap with no lip deformation, no transparency, no inpainting):

| Metric | How to Compute | Notes |
|--------|---------------|-------|
| **Identity Similarity** | Cosine similarity of ArcFace embeddings between source face and swapped result face | Use `arcface_inswapper` model already loaded. `numpy.dot(source_emb, result_emb)` where both are L2-normalized 512-d vectors |
| **Background SSIM** | SSIM on non-face regions (mask out face bounding box, measure rest) | Already have `compute_ssim()` in eval script — apply to full frame with face bbox masked out |
| **Face Sharpness** | Laplacian variance of the swapped face crop | `cv2.Laplacian(gray_crop, cv2.CV_64F).var()` |
| **Color Shift (LAB)** | Mean CIE LAB distance between swapped face and target face | Already computed in `compute_metrics()` — reuse `color_shift_lab` |
| **Edge Discontinuity** | Mean gradient magnitude at mask boundary | Dilate face mask by 5px, compute Sobel gradient at boundary pixels |

#### Implementation Instructions for `run_lip_deformation_eval.py`

Add a new function `compute_baseline_quality()` that runs AFTER the dirty swap is generated (after line 335) and BEFORE the lip deformation loop begins. This function should:

1. **Extract face embeddings** from both source and swapped result using ArcFace:
   ```python
   from watserface.face_analyser import get_one_face, get_many_faces
   # source_face already detected above — use source_face.normed_embedding
   # Re-detect face on dirty_swap to get result embedding
   result_faces = get_many_faces([dirty_swap])
   result_face = get_one_face(result_faces)
   identity_sim = float(numpy.dot(source_face.normed_embedding, result_face.normed_embedding))
   ```

2. **Compute background SSIM** (mask out face region):
   ```python
   face_mask = numpy.zeros(target_img.shape[:2], dtype=numpy.uint8)
   bbox = target_face.bounding_box.astype(int)
   face_mask[bbox[1]:bbox[3], bbox[0]:bbox[2]] = 255
   # Invert mask for background
   bg_mask = (face_mask == 0)
   target_bg = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)[bg_mask].astype(numpy.float32)
   result_bg = cv2.cvtColor(dirty_swap_bgr, cv2.COLOR_BGR2GRAY)[bg_mask].astype(numpy.float32)
   # Flatten comparison (simple MSE-based proxy, or reshape for SSIM)
   bg_ssim = 1.0 - (numpy.mean((target_bg - result_bg) ** 2) / (255.0 ** 2))
   ```

3. **Compute face sharpness**:
   ```python
   face_crop_gray = cv2.cvtColor(dirty_swap_bgr[bbox[1]:bbox[3], bbox[0]:bbox[2]], cv2.COLOR_BGR2GRAY)
   sharpness = float(cv2.Laplacian(face_crop_gray, cv2.CV_64F).var())
   ```

4. **Save baseline quality metrics** as `loop_0_baseline/baseline_quality.json`:
   ```json
   {
     "identity_similarity": 0.XX,
     "background_ssim_proxy": 0.XX,
     "face_sharpness_laplacian": XX.X,
     "color_shift_lab": X.XX,
     "milestone_0_targets": {
       "identity_similarity": "TBD — user sets during first interview",
       "background_ssim": ">= 0.90",
       "color_shift_lab": "< 5.0"
     }
   }
   ```

5. **Print baseline quality summary** prominently:
   ```
   ============================================================
   MILESTONE 0: BASELINE SWAP QUALITY
   ============================================================
   Identity Similarity:  0.XXXX  (target: TBD by user)
   Background Integrity: 0.XXXX  (target: >= 0.90)
   Face Sharpness:       XXX.X   (reference only)
   Color Shift (LAB):    X.XX    (target: < 5.0)
   ============================================================
   ```

6. **Do NOT gate on identity similarity yet** — the target score will be set during the first human QA interview. Save the measured value so the human can decide what's acceptable.

#### Baseline Review in Prometheus Interview

The baseline swap MUST be **Slide 01** in the composite image. Prometheus asks about it FIRST, before any layer questions.

Sisyphus includes the baseline as a cropped face ROI in `review_composite.jpg` slide 01.

Prometheus asks:
```
[Image 01]: This is the baseline swap (no layers applied). Identity similarity: [X].
            What score is acceptable as the minimum? For reference, competitive tools achieve 0.85+ on clean swaps.
```

Record the user's answer as the `identity_similarity_target` in `baseline_quality.json` and in `.sisyphus/notepads/*/decisions.md`. All subsequent evaluations compare against this user-set target.

---

### Phase 1: Automated Analysis (Sisyphus)

**Agent: Sisyphus (executor)**

Sisyphus runs the eval scripts, generates all output images, and computes all metrics. For each output:

1. Run automated checks (dimensions, coverage metrics, SSIM, identity, etc.)
2. Classify issues:

| Classification | Action |
|----------------|--------|
| **Solvable by Agent** | Fix immediately, do not ask user. Re-run. |
| **Requires Human Judgment** | Queue for Prometheus interview handoff |

3. Fix everything fixable (artifacts, missing files, wrong dimensions, metrics below threshold)
4. **When all agent-fixable issues are resolved**, prepare the interview handoff package (see below)

**Sisyphus solves these itself — NEVER ask the user:**
- "The image is 256px, should I upscale?" → Just upscale it
- "There's a rectangular artifact" → Fix the blending code
- "SSIM is below threshold" → Iterate until it passes
- "The file wasn't generated" → Fix the code that generates it

---

### Phase 2: Oracle Analysis (Sisyphus → Oracle → Prometheus)

**When Sisyphus has finished all automated work**, it consults Oracle BEFORE handing off to Prometheus. Oracle is the diagnostic brain that sits between raw metrics and human questions.

**Agent: Oracle (read-only reasoning specialist)**

#### Why Oracle Before Prometheus

| Without Oracle | With Oracle |
|---|---|
| Prometheus asks: "Identity dropped 0.01. Accept?" | Oracle says: "The 0.01 drop is within ArcFace embedding noise (σ=0.008 on repeated measurements of same image). This is NOT a real regression — it's measurement variance. No question needed." |
| Prometheus asks: "Is this color shift acceptable?" | Oracle says: "LAB shift of 3.5 is caused by the blend layer averaging skin tones across the mask boundary. Reducing blend radius from 15px to 8px would fix this without identity cost. Sisyphus should try this before asking the human." |
| Sisyphus tries 3 random fixes for regression | Oracle says: "Sharpness dropped because the TPS warp uses bilinear interpolation. Switching to INTER_LANCZOS4 in `warp_lip_to_target()` would preserve sharpness. This is a one-line fix." |
| Human gets 6 questions | Human gets 2 questions (Oracle resolved 4 automatically) |

#### Oracle Consultation Points (AUTO-TRIGGERED)

Oracle is invoked automatically at these points — no manual trigger needed:

**1. After Layer Stack Test — Regression Diagnosis**

When `check_regressions()` finds ANY regression, Sisyphus invokes Oracle BEFORE attempting fixes:

```
delegate_task(
  subagent_type="oracle",
  prompt="""
  REGRESSION DIAGNOSIS for WatserFace Ralph QA.

  Layer "{label}" caused regression on: {metrics_list}

  Metrics before layer:
  {prev_metrics_json}

  Metrics after layer:
  {curr_metrics_json}

  Layer implementation: {file_path}:{line_range}

  Questions:
  1. Is this regression real or measurement noise? (Consider: ArcFace embedding variance,
     SSIM sensitivity to sub-pixel shifts, LAB color space quantization)
  2. What is the ROOT CAUSE? (Algorithmic: interpolation, blending, coordinate transform?
     Or parametric: threshold too aggressive, radius too large?)
  3. What is the TARGETED FIX? (Specific parameter change, algorithm swap, or code edit.
     Not "try different values" — give the exact fix.)
  4. Is this an inherent trade-off that requires human judgment, or a solvable bug?

  Return:
  - diagnosis: "noise" | "parametric" | "algorithmic" | "trade-off"
  - fix: {specific code change} or null if trade-off
  - confidence: 0.0-1.0
  - human_question_needed: true/false
  - explanation: {1-2 sentences for the human if needed}
  """,
  run_in_background=false
)
```

**2. After Baseline Quality Measurement — Context Setting**

After Phase 0 baseline metrics are computed, Oracle contextualizes the numbers:

```
delegate_task(
  subagent_type="oracle",
  prompt="""
  BASELINE QUALITY ANALYSIS for WatserFace Ralph QA.

  Baseline metrics (dirty swap, no layers):
  {baseline_quality_json}

  Swapper model: {model_name}
  Source image: {source_resolution}
  Target image: {target_resolution}

  Questions:
  1. Are these metrics consistent with expected performance for {model_name}?
     (InSwapper 128px → expect identity ~0.65-0.75 due to low resolution.
      SimSwap 512px → expect identity ~0.75-0.85.)
  2. Is the identity score limited by the model's resolution or by a bug?
  3. What is a REALISTIC identity target for this model/resolution combination?
  4. Are any metrics suspiciously bad (indicating a pipeline bug rather than model limitation)?

  Return:
  - expected_identity_range: [min, max] for this model
  - realistic_target: float
  - suspicious_metrics: list (any that suggest bugs)
  - recommended_question_for_human: string (contextually framed)
  """,
  run_in_background=false
)
```

This means Prometheus can present the baseline question with Oracle's context:
```
[Image 01]: Baseline swap. Identity: 0.71.
            Oracle notes: InSwapper 128px typically achieves 0.65-0.75.
            This score is at the top of the expected range for this model.
            A higher target would require switching to SimSwap 512px.
            What minimum is acceptable?
```

**3. After All Layers Complete — Stack Interaction Analysis**

After the full cumulative stack test, Oracle analyzes cross-layer interactions:

```
delegate_task(
  subagent_type="oracle",
  prompt="""
  LAYER STACK ANALYSIS for WatserFace Ralph QA.

  Cumulative metrics by layer:
  {layer_stack_report_json}

  Questions:
  1. Are any layers interfering with each other? (e.g., warp undoing blend's work)
  2. Would reordering the stack improve results? (e.g., blend before warp)
  3. Are there diminishing returns? (e.g., inpaint adds 0.001 SSIM but 7s processing)
  4. What is the optimal subset of layers for this specific input pair?

  Return:
  - interactions: list of detected layer interactions
  - recommended_order: list (if different from current)
  - recommended_subset: list (layers worth keeping)
  - explanation: string
  """,
  run_in_background=false
)
```

#### Oracle Output: Triage Report

Oracle writes `.sisyphus/interviews/ralph-qa/oracle_triage.md`:

```markdown
# Oracle Triage — [date]

## Noise vs Real
| Metric Δ | Verdict | Reasoning |
|----------|---------|-----------|
| Identity -0.01 | NOISE | ArcFace σ=0.008, delta within 1.5σ |
| Lip SSIM +0.03 | REAL | Consistent improvement across ROI |
| Color +0.3 LAB | REAL but FIXABLE | Blend radius too large (see fix) |

## Auto-Fixes (for Sisyphus)
1. `face_helper.py:warp_lip_to_target()` — change INTER_LINEAR → INTER_LANCZOS4
2. `transparency_handler.py:blend_lip_identity()` — reduce blend_radius from 15 to 8

## Questions for Human (for Prometheus)
Only 2 questions needed (down from 6):
- [Image 01]: Baseline identity 0.71 — acceptable for InSwapper 128px? (top of expected range)
- [Image 04]: Mask boundary visible at chin. Accept or request fix?

## Layer Stack Recommendation
- Current order: warp → blend → inpaint
- Recommended: blend → warp → inpaint (blend first gives warp better color context)
- Recommended subset: warp + blend (inpaint adds 7.8s for +0.001 SSIM — not worth it)
```

---

### Phase 3: Handoff Package (Sisyphus prepares, informed by Oracle)

**After Oracle analysis**, Sisyphus applies any auto-fixes Oracle recommended, re-runs affected layers, then prepares the handoff.

Sisyphus saves to `.sisyphus/interviews/ralph-qa/`:

1. **`review_composite.jpg`** — Single composite image with ALL slides needing human review, numbered sequentially. Each slide:
   - Is **cropped to the relevant region** (face ROI, lip ROI, mask boundary — not the full 3404×1868 frame)
   - Is **numbered** in the top-left corner: `01`, `02`, `03`, ...
   - Is ≥512px on the shortest dimension
   - Has a brief burned-in label (e.g., "Baseline Swap", "After Lip Warp", "Mask Boundary")
   - **Only includes slides that Oracle flagged as needing human judgment** (noise-level regressions and auto-fixable issues are excluded)

2. **`review_questions.md`** — Structured list of questions, **curated by Oracle's triage**:
   ```markdown
   # Ralph QA Review — [date]

   ## Oracle Summary
   - Auto-resolved: 4 issues (2 noise, 2 auto-fixed)
   - Questions for you: 2

   ## Metrics Summary
   | Step | Identity | Lip SSIM | Color Shift | Sharpness | Status |
   |------|----------|----------|-------------|-----------|--------|
   | Baseline | 0.71 | — | 3.2 | 142.3 | ✅ |
   | +lip_warp | 0.71 | 0.83 | 3.2 | 141.8 | ✅ (after Oracle fix) |
   | ... | | | | | |

   ## Questions
   - [Image 01]: Baseline swap. Identity: 0.71 (top of InSwapper 128px range). What minimum is acceptable?
   - [Image 02]: Mask boundary visible at chin crease. Accept or should this be softened?
   ```

3. **`oracle_triage.md`** — Oracle's full analysis (Prometheus reads for context)

4. **`review_metadata.json`** — Machine-readable context:
   ```json
   {
     "total_slides": 2,
     "oracle_auto_resolved": 4,
     "oracle_auto_fixes_applied": 2,
     "slides": [...],
     "oracle_triage": "oracle_triage.md",
     "layer_stack_report": "layer_stack_report.json",
     "baseline_quality": "baseline_quality.json"
   }
   ```

#### Handoff Trigger

Sisyphus writes to `.sisyphus/HANDOFF_READY.md`:
```markdown
# Handoff Ready: Ralph Visual QA Interview

All automated work complete. Oracle analysis applied.

**Oracle resolved:** 4 issues automatically (2 noise, 2 code fixes applied)
**Questions remaining:** 2 (require human judgment)

**For Prometheus:** Review `.sisyphus/interviews/ralph-qa/` and conduct human interview.
**Composite image:** `.sisyphus/interviews/ralph-qa/review_composite.jpg`
**Questions:** `.sisyphus/interviews/ralph-qa/review_questions.md`
**Oracle context:** `.sisyphus/interviews/ralph-qa/oracle_triage.md`
```

---

### Phase 4: Human Interview (Prometheus)

**Agent: Prometheus (planner/consultant)** — NOT Sisyphus

Prometheus reads the handoff package AND Oracle's triage report, then presents the review to the user.

#### Pre-Interview: Read Oracle Context

Before asking any questions, Prometheus reads:
1. `oracle_triage.md` — What Oracle already resolved, and WHY each remaining question needs a human
2. `review_metadata.json` — How many questions, which slides
3. `review_questions.md` — The curated question list

Prometheus uses Oracle's context to **frame questions with expert reasoning**. Don't just ask "is this OK?" — explain what Oracle found and why the human's judgment is needed.

#### Interview Rules

1. **Show the composite image FIRST** — one image with all numbered slides
2. **Briefly note what Oracle already handled** — "Oracle auto-resolved 4 issues. 2 questions remain for you."
3. **Ask questions ONE AT A TIME**, referencing the slide number
4. **Include Oracle's context** in the question framing when relevant
5. **Use the Question tool** for structured multi-choice when applicable
6. **Only ask what requires human judgment** — Oracle and Sisyphus already handled everything else

#### Question Format

Every question follows this exact format:

```
[Image <##>]: <question>
```

Examples:
```
[Image 01]: What identity similarity score is acceptable as the minimum baseline? Current: 0.71.
[Image 02]: Does the lip shape look natural here, or does it look externally pressed?
[Image 03]: Identity dropped 0.01 after lip warp. Accept this trade-off for better lip shape?
[Image 04]: Is the color transition at the mask boundary noticeable?
```

#### Multi-Choice (use Question tool when possible)

```
[Image 03]: Identity dropped from 0.71 → 0.70 after lip warp. The lip shape improved visually.

Options:
  (a) Accept trade-off — lip shape matters more
  (b) Reject — identity must not decrease, disable lip warp
  (c) Try reducing warp intensity (currently 1.3x)
```

#### One Slide, Multiple Questions

A single slide MAY have more than one question. Ask them sequentially:

```
[Image 01]: First — does this look like the source person?
[Image 01]: Second — is the skin tone a natural match for the target lighting?
```

---

### Phase 5: Resolution (Prometheus → Sisyphus, Oracle assists)

After collecting ALL human feedback, Prometheus:

1. Documents every decision in `.sisyphus/notepads/*/decisions.md`
2. Writes action items to `.sisyphus/interviews/ralph-qa/actions.md`:
   ```markdown
   # Actions from Ralph QA Interview — [date]

   ## User Decisions
   - Identity target set to: 0.68 (user accepts current baseline)
   - Mask boundary: NEEDS FIX (color transition too visible)

   ## Oracle Auto-Resolved (no human input needed)
   - Identity -0.01 from lip_warp: NOISE (within ArcFace σ)
   - Sharpness -3%: AUTO-FIXED (switched to LANCZOS4 interpolation)
   - Color +0.3 LAB: AUTO-FIXED (reduced blend radius 15→8px)
   - Inpaint layer: DISABLED by Oracle recommendation (7.8s for +0.001 SSIM)

   ## Action Items for Sisyphus
   - [ ] Set identity_similarity_target = 0.68 in baseline_quality.json
   - [ ] Fix mask boundary color blending (see Image 02 feedback)
   - [ ] Re-run eval with fixes applied
   - [ ] Prepare new review_composite.jpg for follow-up QA (only changed images)
   ```
3. Hands back to Sisyphus for execution of action items
4. If action items require non-trivial fixes → Sisyphus consults Oracle for targeted fix guidance before implementing
5. After Sisyphus implements fixes → re-runs eval → Oracle re-triages → new handoff to Prometheus (only changed slides)

---

## What Requires Human Judgment (Prometheus asks these)

| Category | Examples |
|----------|----------|
| **Aesthetic quality** | "Does this look natural?" |
| **Contextual fit** | "Is this appropriate for the target video?" |
| **Subjective thresholds** | "Is this level of X acceptable?" |
| **Identity verification** | "Does this still look like the source person?" |
| **Trade-off decisions** | "Accept -0.01 identity for better lip shape?" |
| **Target setting** | "What score is acceptable as minimum?" |

## What Does NOT Require Human Judgment (Sisyphus fixes these)

| Category | Agent Action |
|----------|--------------|
| **Technical failures** | Fix code, re-run |
| **Missing outputs** | Debug and regenerate |
| **Metrics below threshold** | Iterate until passing |
| **Visible code artifacts** | Fix the algorithm |
| **Wrong dimensions/format** | Correct automatically |
| **File not found** | Check paths, regenerate |

## Evaluation Order (MANDATORY)

Every Ralph QA session MUST follow this order:

```
Phase 0: Baseline Quality Gate          [Sisyphus]
    │
Phase 1: Automated Analysis + Fixes     [Sisyphus]
    │    (layer stack test, regression guard)
    │
Phase 2: Oracle Analysis + Triage       [Oracle]
    │    (diagnose regressions, auto-fix, filter noise,
    │     contextualize metrics, curate human questions)
    │
Phase 3: Handoff Package                [Sisyphus]
    │    (composite image, curated questions, Oracle context)
    │
Phase 4: Human Interview                [Prometheus]
    │    (only questions Oracle couldn't resolve)
    │
Phase 5: Resolution + Re-run            [Prometheus → Sisyphus → Oracle]
         (action items, fixes, re-eval if needed)
```

**Agent responsibilities:**
| Agent | Role | Handles |
|-------|------|---------|
| **Sisyphus** | Executor | Runs evals, applies fixes, generates images, prepares handoffs |
| **Oracle** | Diagnostician | Analyzes regressions, identifies root causes, filters noise, recommends fixes, contextualizes metrics |
| **Prometheus** | Interviewer | Conducts human QA with Oracle's context, records decisions, assigns action items |

If the baseline swap fails quality checks (identity too low, visible artifacts, color mismatch), **stop and fix the foundation before evaluating advanced features.** No amount of lip deformation or transparency handling can fix a bad base swap.

### Baseline Quality Metrics Location
- `test_quality/lip_deformation/loop_0_baseline/baseline_quality.json`
- `test_quality/lip_deformation/loop_0_baseline/result.jpg`

### User-Set Targets Location
After the first interview, targets are stored in:
- `baseline_quality.json` → `identity_similarity_target` field
- `.sisyphus/notepads/*/decisions.md` (for persistence across sessions)

---

## Layer Regression Guard — INVARIANT: Every Layer Must Improve or Hold

### The Rule

**Every layer added to the pipeline must produce output that is equal to or better than its input on ALL tracked metrics.** If adding a layer makes ANY metric worse, that layer has regressed and must be fixed before proceeding.

This is not a suggestion. This is a hard invariant.

```
BASELINE (dirty swap) ──[Layer N]──► OUTPUT
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ FOR EACH METRIC: │
                              │ output >= input? │
                              └────────┬────────┘
                                  │         │
                                 YES        NO
                                  │         │
                                  ▼         ▼
                              PROCEED    REGRESSION
                                         SUBLOOP
```

### Tracked Metrics (Compare Layer Output vs Layer Input)

| Metric | Regression = | Tolerance |
|--------|-------------|-----------|
| **Identity Similarity** | output < input | None — must not decrease |
| **Lip Region SSIM** | output < input | -0.005 grace (measurement noise) |
| **Edge SSIM** | output < input | -0.01 grace |
| **Color Shift (LAB)** | output > input (shift increased) | +0.5 grace |
| **Face Sharpness** | output < input × 0.90 (>10% loss) | 10% degradation allowed |
| **Background Integrity** | output ≠ input outside face region | Zero tolerance — layers must not touch non-face pixels |

### How to Measure: Cumulative Layer Stack

The eval script already runs toggle tests (each layer independently). Extend this to a **cumulative stack test**:

```
Step 0: baseline           = dirty_swap (no layers)
Step 1: +xseg_mask         = apply XSeg masking to baseline
Step 2: +lip_warp          = apply lip warp to Step 1 output
Step 3: +lip_blend         = apply lip blend to Step 2 output
Step 4: +lip_inpaint       = apply boundary inpaint to Step 3 output
Step 5: +transparency      = apply transparency handler to Step 4 output (when available)
Step 6: +generative_repaint = apply generative inpainting to Step 5 output (when available)
```

At each step, compute ALL tracked metrics and compare to the previous step.

#### Implementation Instructions for `run_lip_deformation_eval.py`

Add a `run_cumulative_layer_test()` function that:

1. **Defines the layer stack** as an ordered list:
   ```python
   LAYER_STACK = [
       # (label, function, kwargs)
       ('baseline', None, {}),  # Step 0: no-op, just the dirty swap
       ('xseg_mask', apply_xseg_composite, {'xseg_mask': xseg_mask_full}),
       ('lip_warp', warp_lip_to_target, {'source_lm': swapped_lip_lm, 'target_lm': target_lip_lm}),
       ('lip_blend', blend_lip_identity, {'target': target_rgb, 'lip_lm': target_lip_lm}),
       ('lip_inpaint', inpaint_lip_boundary, {'lip_lm': target_lip_lm, 'xseg_mask': xseg_mask_full}),
       # Future layers append here:
       # ('transparency', apply_transparency, {...}),
       # ('generative_repaint', apply_generative_repaint, {...}),
   ]
   ```

2. **Run each layer cumulatively**, measuring after each:
   ```python
   current_result = dirty_swap.copy()
   prev_metrics = compute_baseline_quality(current_result, ...)  # Step 0

   for i, (label, layer_fn, kwargs) in enumerate(LAYER_STACK[1:], start=1):
       # Apply layer
       current_result = layer_fn(current_result, **kwargs)

       # Measure
       current_metrics = compute_all_metrics(current_result, ...)

       # Check regression
       regressions = check_regressions(prev_metrics, current_metrics, label)

       if regressions:
           # ENTER REGRESSION SUBLOOP
           handle_regression(label, regressions, prev_metrics, current_metrics)
       else:
           print(f"  ✅ {label}: all metrics held or improved")

       prev_metrics = current_metrics
   ```

3. **Save cumulative results** as `layer_stack_report.json`:
   ```json
   {
     "stack": [
       {"step": 0, "label": "baseline", "metrics": {...}},
       {"step": 1, "label": "xseg_mask", "metrics": {...}, "regressions": []},
       {"step": 2, "label": "lip_warp", "metrics": {...}, "regressions": ["identity_similarity"]},
       ...
     ],
     "overall_pass": false,
     "regressed_layers": ["lip_warp"]
   }
   ```

### The Regression Subloop (Oracle-Assisted)

When a layer causes regression, the agent MUST enter this subloop **before continuing to the next layer**:

```
┌──────────────────────────────────────────────────────────┐
│              REGRESSION SUBLOOP (Oracle-Assisted)          │
│                                                           │
│  Layer "{label}" regressed on: {metrics_list}              │
│                                                           │
│  Step 1: CONSULT ORACLE (MANDATORY — before ANY fix)      │
│    │                                                      │
│    │  Oracle receives: prev_metrics, curr_metrics,         │
│    │  layer source code, input/output images               │
│    │                                                      │
│    │  Oracle returns:                                      │
│    │    diagnosis: "noise" | "parametric" | "algorithmic"  │
│    │              | "trade-off"                             │
│    │    fix: {specific change} or null                     │
│    │    human_needed: true/false                           │
│    │                                                      │
│    ├── IF diagnosis == "noise":                            │
│    │   → NOT a real regression. Log and SKIP. Proceed.     │
│    │                                                      │
│    ├── IF diagnosis == "parametric":                       │
│    │   → Oracle gives exact parameter change.              │
│    │   → Sisyphus applies fix. Re-run. Re-check.          │
│    │   → Max 2 Oracle-guided attempts (not 3 blind ones). │
│    │                                                      │
│    ├── IF diagnosis == "algorithmic":                      │
│    │   → Oracle identifies code-level fix.                 │
│    │   → Sisyphus implements. Re-run. Re-check.           │
│    │   → If fix fails, Oracle re-analyzes with new data.  │
│    │   → Max 2 Oracle-guided attempts.                    │
│    │                                                      │
│    └── IF diagnosis == "trade-off":                        │
│        → INHERENT conflict between metrics.                │
│        → Oracle frames the trade-off for Prometheus.       │
│        → Queued for human interview (Phase 4).             │
│        → Oracle provides: what's gained, what's lost,      │
│          whether it's worth asking about.                  │
│                                                           │
│  Step 2: IF Oracle fix applied → re-run layer, re-check   │
│          IF regression resolved → proceed to next layer    │
│          IF still regressed after 2 Oracle attempts →      │
│            → Oracle re-classifies as "trade-off"           │
│            → Queue for human interview                     │
│                                                           │
│  Step 3: RECORD in oracle_triage.md                        │
│    ├── RESOLVED: "Layer X regression was {diagnosis}.       │
│    │   Fixed by {change}. No human input needed."          │
│    │                                                      │
│    └── ESCALATED: "Layer X has inherent trade-off:         │
│        {gain} vs {loss}. Human must decide."               │
│                                                           │
│  Step 4: PROCEED to next layer                             │
│          (using resolved output or pre-layer output         │
│           if trade-off is pending human decision)           │
└──────────────────────────────────────────────────────────┘
```

**Key difference from the old subloop:** Sisyphus never guesses. Oracle diagnoses first, then Sisyphus applies a targeted fix. This turns 3 blind attempts into 1-2 informed ones, and filters out noise so the human only sees real trade-offs.
```

### Regression Check Function

```python
def check_regressions(prev: dict, curr: dict, label: str) -> list[dict]:
    """Compare current layer output against previous layer output.
    Returns list of regressed metrics with details."""
    regressions = []

    CHECKS = [
        # (metric_key, direction, tolerance, description)
        ('identity_similarity', 'higher_is_better', 0.0,
         'Identity similarity must not decrease'),
        ('lip_ssim', 'higher_is_better', 0.005,
         'Lip SSIM allows 0.005 measurement noise'),
        ('edge_ssim', 'higher_is_better', 0.01,
         'Edge SSIM allows 0.01 measurement noise'),
        ('color_shift_lab', 'lower_is_better', 0.5,
         'Color shift allows +0.5 LAB units'),
        ('face_sharpness', 'higher_is_better_pct', 0.10,
         'Sharpness allows 10% degradation'),
        ('non_lip_max_delta', 'zero_tolerance', 0.0,
         'Background pixels must not change'),
    ]

    for key, direction, tolerance, desc in CHECKS:
        if key not in prev or key not in curr:
            continue

        p, c = prev[key], curr[key]
        regressed = False

        if direction == 'higher_is_better':
            regressed = c < (p - tolerance)
        elif direction == 'lower_is_better':
            regressed = c > (p + tolerance)
        elif direction == 'higher_is_better_pct':
            regressed = c < (p * (1.0 - tolerance))
        elif direction == 'zero_tolerance':
            regressed = c > tolerance

        if regressed:
            regressions.append({
                'metric': key,
                'previous': float(p),
                'current': float(c),
                'delta': float(c - p),
                'tolerance': tolerance,
                'description': desc,
                'layer': label,
            })

    return regressions
```

### Print Format for Regression Detection

```
============================================================
⚠️  REGRESSION DETECTED: Layer "lip_warp"
============================================================
  identity_similarity:  0.7143 → 0.6980  (Δ -0.0163)  ❌ REGRESSED
    Tolerance: 0.0 (must not decrease)

  lip_ssim:             0.8234 → 0.8350  (Δ +0.0116)  ✅ improved
  edge_ssim:            0.7800 → 0.7950  (Δ +0.0150)  ✅ improved
  color_shift_lab:      3.20   → 3.45    (Δ +0.25)    ✅ within tolerance
  face_sharpness:       142.3  → 138.1   (Δ -4.2)     ✅ within 10%
  non_lip_max_delta:    0.0    → 0.0                   ✅ unchanged
------------------------------------------------------------
  REGRESSED METRICS: 1 of 6
  ACTION: Entering regression subloop for "lip_warp"
============================================================
```

### Adding New Layers in the Future

When a new layer is implemented (e.g., generative repaint, transparency handler), it is added to `LAYER_STACK` by appending to the list. The regression guard automatically covers it — no additional configuration needed.

```python
# To add a new layer, just append:
LAYER_STACK.append(
    ('generative_repaint', apply_generative_repaint, {'model': 'lama', ...})
)
# The regression guard will automatically check it against the previous layer's output.
```

**Every new layer gets the same treatment: prove you help, or get disabled.**

---

## Completion

After all images reviewed:
1. Summarize decisions made
2. List any follow-up work items
3. Commit fixes if any code changed
4. **Update baseline_quality.json with user-set targets** if this was the first interview
5. **Update layer_stack_report.json** with cumulative pass/fail for each layer
6. **Record any accepted trade-offs** in `.sisyphus/notepads/*/decisions.md` with rationale
