# Autonomous Quality Iteration Loop: Factory × REFace × RunPod

## TL;DR

> **Quick Summary**: Wire the existing Software Factory to evaluate REFace (the commercially viable face-swap architecture), set up a RunPod GPU as the execution environment, and configure an autonomous Ralph loop where oh-my-opencode reads factory metrics, diagnoses quality issues, adjusts code/parameters, pushes to RunPod, re-runs scenarios, and iterates — completely hands-off until metrics pass or progress stalls.
> 
> **Deliverables**:
> - Factory orchestrator wired to REFace (replaces passthrough stub)
> - RunPod GPU environment configured with SSH + git
> - SSH execution bridge (push code → run factory remotely → pull results)
> - Autonomous iteration controller with escalation rules
> - First quality baseline: real metric numbers for REFace on factory scenarios
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 2 waves
> **Critical Path**: Fixtures (human) → REFace local validation → Orchestrator wiring → RunPod setup → Iteration controller → First autonomous run

---

## Context

### Original Request
"With the Software Factory and recursive judging in place, how can we run this? I would like to test this locally even if at 720p at a lower bitrate."

Through consultation, this evolved into: build an autonomous quality iteration loop where oh-my-opencode (Sisyphus) reads factory metrics, adjusts code, pushes to cloud GPU, re-runs, and loops until quality passes or plateaus — completely hands-off for the user.

### Interview Summary
**Key Discussions**:
- User is NOT a programmer — wants maximum agent autonomy
- Factory is fully scaffolded (23 Python files, 9 YAML scenarios) but orchestrator is a passthrough stub
- REFace (MIT/Apache 2.0) is the only commercially viable architecture — legal already resolved
- Exo distributed compute: USELESS for this workload (LLM-only)
- BlackMagic eGPU: DEAD END (no ROCm on macOS)
- REFace on M4 16GB: tight but feasible in fp16 with 10 DDIM steps (~2-4s/frame)
- RunPod: A40 48GB VRAM (already provisioned), SSH enabled
- Factory thresholds are SACRED — the user's voice. Never modified by the loop.
- Agent is oh-my-opencode/Sisyphus, not any specific LLM

**Research Findings**:
- REFace: PyTorch + diffusers, 512×512 native, 50 DDIM steps default, --ddim_steps configurable, MPS compatible
- REFace memory: ~6-8GB fp16, needs torch.mps.empty_cache() between frames on 16GB M4
- REFace invocation: CLI-based via `scripts/one_inference.py`, needs Python wrapper for persistent model loading
- RunPod: A40 48GB (provisioned), SSH access, standard git, no platform lock-in
- Factory outputs structured JSON: ScenarioResult with metric_results, performance_result, judge_result
- Existing eval scripts in `eval/` already have REFace invocation patterns (`run_reface_eval.sh`)

### Metis Review
**Identified Gaps** (addressed):
- **Fixture images are a total blocker** — factory produces only SKIPs without them. User must provide source_faces/default.png and target_frames/default.png as Step 0.
- **REFace integration gap wider than discussed** — REFace uses CLI invocation with folder I/O, not a Python API. Need persistent model loading wrapper, not subprocess calls per frame.
- **MPS validation unconfirmed** — Must verify REFace runs on M4 MPS before building anything
- **Plateau detection undefined** — Added concrete rules: delta < 0.01 for 3 iterations, hard cap 20 iterations, $10 budget guard
- **No rollback mechanism** — Each iteration = one git commit, track best_iteration, auto-revert on regression
- **Scenario scope** — Image-only for v1; video scenarios deferred (comparative/regression types not wired)
- **Sacred file boundaries** — `factory/scenarios/definitions/`, `factory/gates/`, `factory/judges/`, `factory/identity.py` are OFF-LIMITS for autonomous changes

---

## Work Objectives

### Core Objective
Wire the factory to REFace, set up RunPod as the GPU execution environment, and build an autonomous iteration loop that reads factory metrics → diagnoses issues → adjusts code/parameters → re-runs → repeats until quality passes or requires human judgment.

### Concrete Deliverables
- `factory/orchestrator.py::_execute_swap()` calls REFace instead of returning passthrough
- `vendors/REFace/` cloned with dependencies installed
- `factory/reface_bridge.py` — Python wrapper for persistent REFace model loading
- RunPod pod configured with SSH, git, all dependencies
- `factory/scripts/run_remote.sh` — SSH bridge for remote factory execution
- `factory/iteration_controller.py` — autonomous loop with escalation logic
- `factory/iteration_log.json` — structured log of all iterations
- `.sisyphus/workflows/quality-iteration-loop.md` — Ralph loop configuration

### Definition of Done
- [x] REFace cloned and checkpoint downloaded (5.7GB)
- [x] `factory/reface_bridge.py` created with persistent model loading
- [x] `factory/orchestrator.py` wired to call REFace (not passthrough)
- [x] `factory/remote.py` SSH bridge implemented with full error handling
- [x] `factory/iteration_controller.py` with escalation rules and plateau detection
- [x] `factory/escalation_rules.json` with 6 escalation conditions
- [x] `.sisyphus/workflows/quality-iteration-loop.md` workflow documented
- [ ] `python -m factory.runner factory/scenarios/definitions/swap_identity_preservation.yaml --output-json results.json` produces non-zero identity_similarity (🚫 BLOCKED — needs SSH to RunPod)
- [ ] Remote execution via SSH produces identical factory results as local (🚫 BLOCKED — needs SSH key)
- [ ] Iteration controller completes at least 3 cycles autonomously (🚫 BLOCKED — needs SSH)
- [ ] Escalation triggers fire correctly (🚫 BLOCKED — needs live iterations)
- [ ] Each iteration creates a git commit (🚫 BLOCKED — needs live iterations)
- [ ] Best iteration is tracked and auto-rollback works (🚫 BLOCKED — needs live iterations)

### Must Have
- REFace running on RunPod A40 (48GB VRAM) via factory orchestrator
- Persistent model loading (load once, swap many frames)
- SSH execution bridge (local → RunPod → results back)
- Structured iteration log with metrics per cycle
- Git commit per iteration for rollback safety
- Escalation rules: pass, plateau, dead end, budget, max iterations
- Image-based scenarios only (swap_identity_preservation, swap_occlusion_handling, user_casual_balanced_swap)

### Must NOT Have (Guardrails)
- **NO modifications to `factory/scenarios/definitions/*.yaml`** — these are the user's quality standards
- **NO modifications to `factory/gates/`, `factory/judges/`, `factory/identity.py`, `factory/runner.py`** — trusted factory infrastructure
- **NO FaceDancer integration** — CC BY-NC-SA, cannot be used commercially
- **NO video scenarios** — image-only for v1 of the loop
- **NO model training** — inference parameter optimization only, `watserface/training/` is out of scope
- **NO factory threshold relaxation** — if metrics can't meet thresholds, escalate to human
- **NO persistent RunPod infrastructure** — ephemeral pods, spin up → run → spin down
- **NO Exo or distributed compute** — wrong tool for this workload
- **NO eGPU optimization** — dead end, ROCm not on macOS
- **NO more than 20 iterations** without human escalation
- **NO more than $10 RunPod spend** without human notification

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks are verifiable WITHOUT any human action.
> The factory IS the verification system — its JSON output is the single source of truth.

### Test Decision
- **Infrastructure exists**: YES (pytest + factory)
- **Automated tests**: YES (factory scenarios ARE the tests)
- **Framework**: Factory runner + pytest integration (existing)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| REFace inference | Bash (python) | Run inference, check output image exists, check memory |
| Factory integration | Bash (factory runner) | Run scenario, parse JSON, check non-zero metrics |
| SSH bridge | Bash (ssh) | Remote command execution, JSON over SSH |
| Iteration loop | Bash (controller) | Run 2-3 iterations, check log, verify git commits |
| Escalation | Bash (controller) | Force plateau/budget conditions, verify escalation fires |

---

## Execution Strategy

### Parallel Execution Waves

```
Phase 0 (HUMAN PREREQUISITE — blocks everything):
└── Task 0: User provides fixture images

Phase 1 (After fixtures):
├── Task 1: Clone REFace + validate on M4 MPS
└── Task 2: Set up RunPod pod (parallel with Task 1)

Phase 2 (After Tasks 1, 2):
├── Task 3: Wire factory orchestrator to REFace
└── Task 4: Build SSH execution bridge (parallel with Task 3)

Phase 3 (After Tasks 3, 4):
└── Task 5: Build iteration controller + escalation rules

Phase 4 (After Task 5):
└── Task 6: First autonomous run (monitored first 2-3 iterations, then hands-off)

Critical Path: Task 0 → Task 1 → Task 3 → Task 5 → Task 6
Parallel Speedup: ~30% (Tasks 1||2, Tasks 3||4)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 0 | None (human) | 1, 2, 3, 4, 5, 6 | None |
| 1 | 0 | 3 | 2 |
| 2 | 0 | 4 | 1 |
| 3 | 1 | 5 | 4 |
| 4 | 2 | 5 | 3 |
| 5 | 3, 4 | 6 | None |
| 6 | 5 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| Phase 0 | 0 | Human task — user provides images |
| Phase 1 | 1, 2 | task(category="deep") for REFace setup; task(category="quick", load_skills=["git-master"]) for RunPod |
| Phase 2 | 3, 4 | task(category="deep") for orchestrator wiring; task(category="quick") for SSH bridge |
| Phase 3 | 5 | task(category="ultrabrain") — iteration controller is the novel engineering |
| Phase 4 | 6 | `/ralph-loop` — autonomous execution |

---

## TODOs

- [x] 0. User Provides Fixture Images [HUMAN TASK — COMPLETED]

  **What to do**:
  - The user must provide at minimum TWO images:
    1. `factory/fixtures/source_faces/default.png` — a face to use as the swap source (the identity to impose)
    2. `factory/fixtures/target_frames/default.png` — a face to swap onto (the target frame)
  - Optionally:
    3. `factory/fixtures/target_frames/occluded.png` — a target frame with partial occlusion (hand, glasses, etc.)
  - Images should be clear, well-lit, frontal or near-frontal faces
  - Resolution: at least 512×512 (REFace native resolution)
  - Format: PNG or JPG
  - These can be ANY faces — they are test fixtures, not production data

  **Why this blocks everything**: Without fixture images, every factory scenario returns `SKIP` with "Missing fixture(s)". The entire pipeline produces zero useful data.

  **Must NOT do**:
  - Do not auto-download celebrity faces (license/consent issues)
  - Do not generate synthetic faces yet (adds complexity before we know the pipeline works)

  **Recommended Agent Profile**:
  - **Category**: N/A (Human task)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (must be first)
  - **Blocks**: ALL subsequent tasks
  - **Blocked By**: None

  **References**: None (user action)

  **Acceptance Criteria**:

  ```
  Scenario: Fixture images exist and are valid
    Tool: Bash
    Steps:
      1. test -f factory/fixtures/source_faces/default.png
      2. test -f factory/fixtures/target_frames/default.png
      3. python -c "
         import cv2
         src = cv2.imread('factory/fixtures/source_faces/default.png')
         tgt = cv2.imread('factory/fixtures/target_frames/default.png')
         assert src is not None, 'Source image unreadable'
         assert tgt is not None, 'Target image unreadable'
         assert min(src.shape[:2]) >= 256, f'Source too small: {src.shape}'
         assert min(tgt.shape[:2]) >= 256, f'Target too small: {tgt.shape}'
         print(f'Source: {src.shape}, Target: {tgt.shape} — OK')
         "
    Expected Result: Both images exist, readable, at least 256×256
    Evidence: Command output with image dimensions
  ```

  **Commit**: YES
  - Message: `feat(factory): add test fixture images for quality evaluation`
  - Files: `factory/fixtures/source_faces/default.png`, `factory/fixtures/target_frames/default.png`

---

- [x] 1. Clone REFace + Validate on Target Hardware [PARTIALLY COMPLETE — VALIDATION BLOCKED]

  **Status**: 
  - ✅ REFace cloned to `vendors/REFace/`
  - ✅ Checkpoint downloaded (5.7GB saved.ckpt)
  - ✅ Setup script created: `scripts/setup_reface.sh`
  - 🚫 **Validation on RunPod blocked** — SSH key `~/.ssh/id_ed25519` not available
  
  **What was done**:
  - Clone REFace repository into `vendors/REFace/`
  - Download REFace pretrained model checkpoint (~3.8GB) to `vendors/REFace/models/REFace/checkpoints/saved.ckpt`
  - Download dependency models (face_parsing, arcface, DLIB landmarks)
  - Create `scripts/setup_reface.sh` that automates: clone + install deps + download checkpoint
  - Add `vendors/REFace` to `.gitignore`
  
  **What remains (blocked)**:
  - Validate REFace runs inference on RunPod A40 48GB (CUDA)
  - Run single inference with fixture images and verify output
  - Record inference time, peak memory, output resolution

  **Must NOT do**:
  - Do not commit REFace model weights to git
  - Do not modify REFace source code yet (that's Task 3)
  - Do not attempt to fine-tune REFace (inference only)
  - Do not spend time debugging MPS if it doesn't work — RunPod is the primary target

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: External repo setup with dependency resolution, model download, hardware validation across MPS and CUDA. May encounter environment issues requiring diagnosis.
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: Git operations here are simple clone + ignore, not complex history work
    - `playwright`: No browser interaction needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: Task 0

  **References**:

  **Pattern References**:
  - `eval/gpu_setup.sh` — Existing script that clones REFace into vendors/, installs deps. Follow this pattern.
  - `eval/run_reface_eval.sh:87-97` — REFace CLI invocation pattern with --ddim_steps, --outdir, --target_folder, --src_folder
  - `eval/gpu_setup.sh:29-45` — REFace checkpoint download pattern

  **External References**:
  - REFace repo: https://github.com/Sanoojan/REFace
  - REFace inference script: `scripts/one_inference.py` — the entry point for single-image inference
  - REFace config: `configs/train.yaml` — contains model architecture settings, image_size, channels

  **WHY Each Reference Matters**:
  - `gpu_setup.sh`: Already solves the clone + deps + checkpoint download problem. Adapt, don't reinvent.
  - `run_reface_eval.sh`: Shows exact CLI args for REFace inference. The bridge in Task 3 will need these.
  - `configs/train.yaml`: Needed to understand REFace's expected input format and resolution.

  **Acceptance Criteria**:

  ```
  Scenario: REFace produces output image from fixture inputs
    Tool: Bash
    Steps:
      1. ls vendors/REFace/scripts/one_inference.py
      2. Assert: file exists
      3. mkdir -p /tmp/reface_test/source /tmp/reface_test/target /tmp/reface_test/output
      4. cp factory/fixtures/source_faces/default.png /tmp/reface_test/source/
      5. cp factory/fixtures/target_frames/default.png /tmp/reface_test/target/
      6. cd vendors/REFace && python scripts/one_inference.py \
           --outdir /tmp/reface_test/output \
           --target_folder /tmp/reface_test/target \
           --src_folder /tmp/reface_test/source \
           --ddim_steps 10 --n_samples 1
      7. Assert: at least one output image exists in /tmp/reface_test/output/
      8. python -c "
         import cv2
         import glob
         outputs = glob.glob('/tmp/reface_test/output/**/*.png', recursive=True)
         assert len(outputs) > 0, 'No output images found'
         img = cv2.imread(outputs[0])
         assert img is not None, 'Output image unreadable'
         print(f'Output: {img.shape} — REFace inference works')
         "
    Expected Result: REFace produces a face-swapped output image
    Evidence: Command output with image dimensions

  Scenario: Setup script is reproducible
    Tool: Bash
    Steps:
      1. bash scripts/setup_reface.sh --dry-run 2>&1
      2. Assert: script exists and shows what it would do
    Expected Result: Automated setup is scriptable
    Evidence: Dry-run output

  Scenario: REFace checkpoint exists after setup
    Tool: Bash
    Steps:
      1. ls -lh vendors/REFace/checkpoints/ 2>/dev/null || ls -lh vendors/REFace/models/ 2>/dev/null
      2. Assert: checkpoint file(s) exist, total size > 1GB
    Expected Result: Model weights downloaded
    Evidence: File listing with sizes
  ```

  **Commit**: YES
  - Message: `feat(vendors): add REFace setup script and validate inference`
  - Files: `scripts/setup_reface.sh`, `.gitignore` (updated), `vendors/REFace/.gitkeep`
  - Pre-commit: `test -f scripts/setup_reface.sh`

---

- [x] 2. Set Up RunPod GPU Environment

  **What to do**:
  - RunPod pod is ALREADY PROVISIONED by the user:
    - GPU: **NVIDIA A40 (48GB VRAM)** — excellent headroom for REFace
    - RAM: 50GB system
    - CPUs: 9
    - SSH: `ssh 6j5e16kr33f7fr-64410bf1@ssh.runpod.io -i ~/.ssh/id_ed25519`
    - SSH key: `~/.ssh/id_ed25519` (also available in parent folder of project: `/Users/kendrick/Documents/dev/`)
    - **NOTE**: Do NOT commit the SSH connection string or key path to git. Store in a local `.env` or pass as environment variables.
  - Create `scripts/runpod_setup.sh` — a script to run on a fresh RunPod pod that:
    1. Clones the watserface repo
    2. Runs `scripts/setup_reface.sh` (from Task 1) to install REFace + deps
    3. Installs factory dependencies (`pip install pyyaml pydantic pyiqa`)
    4. Installs insightface + onnxruntime-gpu (for identity embeddings)
    5. Downloads InsightFace buffalo_l model (~300MB, needed for ArcFace identity scoring)
    6. Runs a quick smoke test: `python -m factory.runner --help`
    7. Prints "RunPod setup complete. SSH connection string: ..."
  - Add RunPod SSH config to the agent's environment (NOT committed to git):
    - Host: `ssh.runpod.io`
    - User: `6j5e16kr33f7fr-64410bf1`
    - Key: `~/.ssh/id_ed25519`
  - Create `scripts/run_remote_factory.sh`:
    - Takes SSH connection info + scenario path as arguments
    - SSHs to RunPod, runs `git pull`, runs factory runner, captures JSON output
    - Copies results back via SCP or prints to stdout
  - Add RunPod setup instructions to a `RUNPOD_SETUP.md` in `.sisyphus/` (not in docs/ — this is operational, not documentation)

  **Must NOT do**:
  - Do not create permanent RunPod infrastructure (pods are ephemeral)
  - Do not store RunPod credentials in git
  - Do not configure RunPod volumes or persistent storage (keep it simple)
  - Do not attempt GPU cluster setup (single pod only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Shell scripting, SSH configuration, no complex logic
  - **Skills**: [`git-master`]
    - `git-master`: Need to handle git clone/pull patterns on remote machine

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 4
  - **Blocked By**: Task 0

  **References**:

  **Pattern References**:
  - `eval/gpu_setup.sh` — Existing GPU setup script (clone repos, install deps, download models). Adapt for RunPod.
  - `.github/workflows/ci.yml` — Shows which dependencies are needed for the test suite

  **External References**:
  - RunPod docs: https://docs.runpod.io/pods/connect-to-a-pod — SSH connection setup
  - InsightFace model download: buffalo_l auto-downloads on first use, but can be pre-cached

  **WHY Each Reference Matters**:
  - `gpu_setup.sh`: Already contains the dependency installation sequence for GPU environments
  - `ci.yml`: Shows which packages are needed for tests (pytest, flake8, etc.)

  **Acceptance Criteria**:

  ```
  Scenario: RunPod setup script runs end-to-end
    Tool: Bash (SSH to RunPod)
    Preconditions: RunPod pod running with SSH enabled
    Steps:
      1. scp scripts/runpod_setup.sh root@<runpod-ip>:/tmp/
      2. ssh root@<runpod-ip> "bash /tmp/runpod_setup.sh"
      3. Assert: exit code 0
      4. ssh root@<runpod-ip> "cd /workspace/watserface && python -m factory.runner --help"
      5. Assert: shows factory runner usage
    Expected Result: Pod fully configured, factory runnable
    Evidence: Setup script output + factory --help output

  Scenario: Remote factory execution script works
    Tool: Bash
    Steps:
      1. bash scripts/run_remote_factory.sh \
           --host <runpod-ip> --port <port> \
           --scenario factory/scenarios/definitions/swap_identity_preservation.yaml \
           --output /tmp/remote_result.json
      2. python -c "
         import json
         with open('/tmp/remote_result.json') as f:
           r = json.load(f)
         assert 'scenarios_run' in r
         print(f'Remote run: {r[\"scenarios_run\"]} scenarios, {r[\"scenarios_passed\"]} passed')
         "
    Expected Result: Factory results returned over SSH as valid JSON
    Evidence: Parsed JSON output
  ```

  **Commit**: YES
  - Message: `feat(infra): add RunPod setup and remote execution scripts`
  - Files: `scripts/runpod_setup.sh`, `scripts/run_remote_factory.sh`, `.sisyphus/RUNPOD_SETUP.md`
  - Pre-commit: `bash -n scripts/runpod_setup.sh && bash -n scripts/run_remote_factory.sh`

---

- [x] 3. Wire Factory Orchestrator to REFace

  **What to do**:
  - This is THE critical integration task. The factory orchestrator's `_execute_swap()` currently returns a passthrough (target_frame copy). It must call REFace instead.
  
  - **Step 1: Create `factory/reface_bridge.py`**
    - This module wraps REFace's inference into a Python-callable API
    - `REFaceBridge` class:
      - `__init__(config_path, checkpoint_path, device='cuda', ddim_steps=50)`: Loads REFace model ONCE (persistent)
      - `swap(source_image: np.ndarray, target_image: np.ndarray) -> np.ndarray`: Performs face swap
        - Internally: save source/target to temp dirs → run REFace inference pipeline → read output → return as numpy array
        - OR: import REFace's inference code directly and call the model (preferred — avoids subprocess overhead)
      - `swap_batch(source: np.ndarray, targets: List[np.ndarray]) -> List[np.ndarray]`: Batch mode
    - Model loading pattern: Follow `eval/utils.py` singleton pattern (load once, reuse)
    - Device handling: auto-detect CUDA vs MPS vs CPU
    - Must support configurable DDIM steps (10 for fast local, 50 for full quality)
  
  - **Step 2: Modify `factory/orchestrator.py`**
    - Replace the passthrough in `_execute_swap()` (line ~209) with a call to `REFaceBridge.swap()`
    - The bridge should be lazily initialized (first call loads the model)
    - Add a `--reface-steps` argument or environment variable for DDIM step count
    - Keep the existing embedding extraction, VRAM tracking, and timing code — it all still works
  
  - **Step 3: Validate end-to-end**
    - Run: `python -m factory.runner factory/scenarios/definitions/swap_identity_preservation.yaml --output-json results.json`
    - The identity_similarity metric MUST be > 0.0 (proves the swap happened, not passthrough)
    - If identity_similarity is > 0.0 but below the scenario threshold (0.65): that's FINE for now. It means the pipeline works but needs optimization — exactly what the iteration loop is for.

  **Must NOT do**:
  - Do not modify REFace source code in `vendors/REFace/` (keep it clean for updates)
  - Do not use subprocess calls per frame (too slow — model reloads each time)
  - Do not change the `SwapResult` dataclass signature (consumers depend on it)
  - Do not modify `factory/runner.py` or `factory/gates/` (trusted infrastructure)
  - Do not import from `watserface.uis` or `gradio`

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Must understand REFace's internal inference pipeline, the factory orchestrator's contract, and create a clean bridge between two codebases. Requires reading REFace source to find the right import points.
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser work
    - `git-master`: No complex git operations

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `factory/orchestrator.py:209-223` — The exact function to replace (`_execute_swap`). Shows current passthrough stub, expected inputs/outputs.
  - `factory/orchestrator.py:140-180` — `run_swap()` public API showing how `_execute_swap` is called and what it feeds into (embedding extraction, timing).
  - `eval/run_reface_eval.sh:87-97` — REFace CLI invocation pattern showing exact arguments and folder structure.
  - `eval/utils.py:get_insightface_model()` — Singleton model loading pattern. Use this pattern for REFaceBridge.
  - `factory/state_isolator.py` — State isolation context manager (used by orchestrator for preset management).

  **API/Type References**:
  - `factory/orchestrator.py:SwapResult` — Dataclass contract: source_frame, target_frame, result_frame, source_embedding, result_embedding, elapsed_seconds, peak_vram_mb. Bridge must produce all these.
  - `factory/identity.py:compute_identity_similarity` — Takes two embeddings, returns raw cosine clamped [0,1]. The orchestrator already calls this after the swap.

  **External References**:
  - REFace `scripts/one_inference.py` — Entry point for REFace inference. Read this to understand the invocation chain: load config → build model → sample → decode → save.
  - REFace `ldm/models/diffusion/ddim.py` — The DDIM sampler. `ddim_steps` parameter controls quality/speed tradeoff.

  **WHY Each Reference Matters**:
  - `orchestrator.py:209`: This is the ONE function to change. Everything else in the orchestrator is correct.
  - `eval/run_reface_eval.sh`: Shows the proven invocation pattern — don't guess, follow what already works.
  - `eval/utils.py`: The singleton pattern ensures REFace loads once. Without this, every frame pays a 30-60s model load penalty.
  - `SwapResult`: The bridge must fill ALL fields. Missing fields will crash downstream metric evaluation.

  **Acceptance Criteria**:

  ```
  Scenario: Factory scenario produces non-zero identity similarity
    Tool: Bash
    Steps:
      1. python -m factory.runner \
           factory/scenarios/definitions/swap_identity_preservation.yaml \
           --output-json /tmp/wired_result.json
      2. python -c "
         import json
         with open('/tmp/wired_result.json') as f:
           r = json.load(f)
         assert r['scenarios_skipped'] == 0, f'Scenario skipped: {r}'
         result = r['results'][0]
         identity_metrics = [m for m in result['metric_results'] if m['metric_name'] == 'identity_similarity']
         assert len(identity_metrics) > 0, 'No identity metric found'
         score = identity_metrics[0]['actual_value']
         assert score > 0.0, f'Identity similarity is {score} (still passthrough?)'
         print(f'Identity similarity: {score:.4f}')
         print(f'Scenario passed: {result[\"passed\"]}')
         for m in result['metric_results']:
           print(f'  {m[\"metric_name\"]}: {m[\"actual_value\"]:.4f} {m[\"expected_operator\"]} {m[\"expected_value\"]} → {\"PASS\" if m[\"passed\"] else \"FAIL\"}')
         "
    Expected Result: Non-zero metrics, swap actually happened
    Evidence: Full metric breakdown in command output

  Scenario: REFace bridge loads model once (persistent)
    Tool: Bash
    Steps:
      1. python -c "
         import time
         from factory.reface_bridge import REFaceBridge
         t0 = time.time()
         bridge = REFaceBridge()  # First load
         t1 = time.time()
         load_time = t1 - t0
         import numpy as np
         img = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
         t2 = time.time()
         result1 = bridge.swap(img, img)  # First swap
         t3 = time.time()
         result2 = bridge.swap(img, img)  # Second swap (no reload)
         t4 = time.time()
         first_swap = t3 - t2
         second_swap = t4 - t3
         print(f'Model load: {load_time:.1f}s')
         print(f'First swap: {first_swap:.1f}s')
         print(f'Second swap: {second_swap:.1f}s')
         assert second_swap < load_time, 'Second swap should be much faster than initial load'
         print('Persistent model loading confirmed')
         "
    Expected Result: Second swap much faster than first (no model reload)
    Evidence: Timing output

  Scenario: SwapResult has all required fields populated
    Tool: Bash
    Steps:
      1. python -c "
         from factory.orchestrator import run_swap
         result = run_swap(
           'factory/fixtures/source_faces/default.png',
           'factory/fixtures/target_frames/default.png',
           preset='balanced'
         )
         assert result.result_frame is not None, 'result_frame is None'
         assert result.source_embedding is not None, 'source_embedding is None'
         assert result.result_embedding is not None, 'result_embedding is None'
         assert result.elapsed_seconds > 0, 'No timing recorded'
         print(f'SwapResult: frame={result.result_frame.shape}, time={result.elapsed_seconds:.2f}s')
         "
    Expected Result: All SwapResult fields populated
    Evidence: Command output with field values
  ```

  **Commit**: YES
  - Message: `feat(factory): wire orchestrator to REFace with persistent model bridge`
  - Files: `factory/reface_bridge.py`, `factory/orchestrator.py`
  - Pre-commit: `python -c "from factory.reface_bridge import REFaceBridge; print('Bridge importable')"`

---

- [x] 4. Build SSH Execution Bridge

  **What to do**:
  - Create `factory/remote.py` — Python module for remote factory execution:
    - `RemoteExecutor` class:
      - `__init__(host, port, user='root', key_path='~/.ssh/id_rsa')`: SSH connection config
      - `sync_code()`: Runs `git push` locally, then `ssh <host> "cd /workspace/watserface && git pull"`
      - `run_factory(scenario_path, output_json='/tmp/factory_result.json', ddim_steps=50) -> FactoryReport`:
        - SSH command: `cd /workspace/watserface && python -m factory.runner <scenario> --output-json <output>`
        - SCP result back or capture from stdout
        - Parse JSON into FactoryReport dataclass
      - `run_all_scenarios(priority='critical', ddim_steps=50) -> FactoryReport`: Run all scenarios at specified priority
      - `get_gpu_info() -> dict`: SSH to check GPU name, VRAM, driver version
      - `estimate_cost(start_time) -> float`: Calculate RunPod cost based on elapsed time and GPU rate
    - Error handling: SSH timeout, connection refused, JSON parse failure, factory crash
    - Logging: All SSH commands logged with timestamps
  
  - Create `scripts/run_remote_factory.sh` — Shell wrapper for CLI usage:
    ```bash
    ./scripts/run_remote_factory.sh --host <ip> --port <port> --scenario <path> --output <json>
    ```

  **Must NOT do**:
  - Do not store SSH credentials in code (use ~/.ssh/config or environment variables)
  - Do not create complex deployment pipelines (keep it: git push → ssh run → scp results)
  - Do not attempt parallel remote execution (one factory run at a time)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: SSH wrapper + JSON parsing, well-defined inputs/outputs
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: Task 5
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `factory/runner.py:ScenarioResult, FactoryReport` — The JSON schema that remote execution must return
  - `scripts/run_remote_factory.sh` — If this was started in Task 2, extend it here

  **Acceptance Criteria**:

  ```
  Scenario: Remote executor syncs code and runs factory
    Tool: Bash
    Preconditions: RunPod pod running, SSH configured
    Steps:
      1. python -c "
         from factory.remote import RemoteExecutor
         executor = RemoteExecutor(host='<ip>', port=<port>)
         executor.sync_code()
         report = executor.run_factory('factory/scenarios/definitions/swap_identity_preservation.yaml')
         print(f'Scenarios run: {report.scenarios_run}')
         print(f'Passed: {report.scenarios_passed}')
         print(f'Failed: {report.scenarios_failed}')
         "
      2. Assert: report has valid scenario counts
    Expected Result: End-to-end remote execution works
    Evidence: Report summary output

  Scenario: Cost estimation works
    Tool: Bash
    Steps:
      1. python -c "
         import time
         from factory.remote import RemoteExecutor
         executor = RemoteExecutor(host='<ip>', port=<port>)
         start = time.time()
         time.sleep(2)
         cost = executor.estimate_cost(start)
         print(f'Estimated cost for 2s: \${cost:.4f}')
         assert cost > 0
         "
    Expected Result: Cost tracking functional
    Evidence: Cost estimate output
  ```

  **Commit**: YES
  - Message: `feat(factory): add SSH remote execution bridge for RunPod`
  - Files: `factory/remote.py`, `scripts/run_remote_factory.sh`

---

- [x] 5. Build Iteration Controller + Escalation Rules

  **What to do**:
  - This is the brain of the autonomous loop. Create `factory/iteration_controller.py`:
  
  - **IterationController class**:
    - `__init__(remote_executor, scenarios, max_iterations=20, budget_cap=10.0)`:
      - `remote_executor`: RemoteExecutor from Task 4
      - `scenarios`: list of scenario YAML paths to evaluate
      - `max_iterations`: hard cap (default 20)
      - `budget_cap`: RunPod dollar cap (default $10)
    - `run_iteration() -> IterationResult`:
      1. Sync code to remote (`git push` + remote `git pull`)
      2. Run factory scenarios on remote GPU
      3. Parse results into structured metrics
      4. Log iteration to `factory/iteration_log.json`
      5. Create git commit with: iteration number, metric summary, what changed
      6. Return IterationResult
    - `diagnose(results: FactoryReport) -> Diagnosis`:
      - Analyze which metrics failed and by how much
      - Categorize failures: identity (face not recognizable), boundary (visible seams), quality (artifacts), performance (too slow)
      - Suggest adjustment direction (this is what the executing agent reads to decide what to change)
    - `check_escalation(history: List[IterationResult]) -> Optional[EscalationReason]`:
      - Check all escalation rules (see below)
      - Return None if loop should continue, or EscalationReason if it should stop
    - `track_best() -> int`: Returns iteration number with best overall metrics
    - `rollback_to_best()`: `git revert` to best iteration's commit
  
  - **Escalation Rules** (machine-parseable, stored in `factory/escalation_rules.json`):
    ```json
    {
      "success": {
        "condition": "all_scenarios_pass",
        "action": "stop",
        "message": "All factory scenarios pass. Quality targets achieved."
      },
      "plateau": {
        "condition": "best_metric_delta_lt_0.01_for_3_iterations",
        "action": "stop",
        "message": "Metrics plateaued. Best identity_similarity={best}. Threshold={target}."
      },
      "regression": {
        "condition": "metrics_worse_than_best_for_2_iterations",
        "action": "rollback_to_best_then_try_different_approach",
        "max_retries": 2
      },
      "max_iterations": {
        "condition": "iteration_count_gte_20",
        "action": "stop",
        "message": "Hit 20 iteration cap. Best results at iteration {best_iteration}."
      },
      "budget": {
        "condition": "estimated_cost_gte_10.00",
        "action": "stop",
        "message": "RunPod spend approaching ${budget_cap}. Stopping to conserve budget."
      },
      "crash": {
        "condition": "factory_runner_nonzero_exit_no_json",
        "action": "inspect_fix_retry_once",
        "max_retries": 1
      }
    }
    ```
  
  - **IterationResult dataclass**:
    - `iteration_number`, `timestamp`, `git_commit_hash`
    - `factory_report`: FactoryReport (full results)
    - `metrics_summary`: Dict[str, float] (key metrics extracted for easy comparison)
    - `changes_made`: str (description of what was changed this iteration)
    - `status`: Literal["running", "passed", "failed", "plateau", "escalated", "rolled_back"]
    - `cost_so_far`: float (cumulative RunPod spend)
  
  - **Iteration Log** (`factory/iteration_log.json`):
    - Append-only JSON Lines format (one JSON object per iteration)
    - Survives across sessions (if Ralph loop is interrupted and resumed)
    - Includes full metrics history for trend analysis
  
  - **Ralph Loop Integration**:
    - Create `.sisyphus/workflows/quality-iteration-loop.md` describing the workflow:
      1. Read iteration_log.json to understand current state
      2. If no iterations yet: run first iteration to get baseline
      3. Read latest IterationResult.diagnosis
      4. Based on diagnosis, decide what to change (this is the agent's creative contribution)
      5. Make the change (edit code/config)
      6. Run next iteration via IterationController
      7. Check escalation
      8. If no escalation: loop back to step 3
      9. If escalation: stop and report to user

  **Must NOT do**:
  - Do not modify factory scenario thresholds (SACRED)
  - Do not modify factory gates/judges/identity code (trusted infrastructure)
  - Do not exceed escalation limits (20 iterations, $10 budget)
  - Do not skip git commits between iterations (rollback safety)
  - Do not run multiple iterations concurrently (sequential only)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: This is the novel engineering — building a self-correcting optimization loop with escalation logic, diagnosis heuristics, and rollback safety. Requires careful state management and clear decision boundaries.
  - **Skills**: [`git-master`]
    - `git-master`: Needs to create commits per iteration, track commit hashes, revert on regression

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on Tasks 3 AND 4)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 3, 4

  **References**:

  **Pattern References**:
  - `factory/runner.py:FactoryReport, ScenarioResult` — The output schema that the controller consumes
  - `factory/remote.py:RemoteExecutor` (Task 4) — The execution interface the controller uses
  - `factory/orchestrator.py:SwapResult` — Understanding what metrics come from where
  - `eval/compare_results.py` — Comparison and reporting patterns (human-readable summaries)

  **Documentation References**:
  - `.sisyphus/workflows/ralph-visual-qa.md` — Existing Ralph workflow pattern. Follow this structure for the new workflow.

  **WHY Each Reference Matters**:
  - `FactoryReport`: The controller's input — must parse this correctly to extract metrics
  - `RemoteExecutor`: The controller's action interface — sync + run + pull results
  - `ralph-visual-qa.md`: Shows how to structure a Ralph workflow document for oh-my-opencode

  **Acceptance Criteria**:

  ```
  Scenario: Controller runs one iteration and logs it
    Tool: Bash
    Preconditions: Tasks 3 and 4 complete, RunPod available
    Steps:
      1. python -c "
         from factory.iteration_controller import IterationController
         from factory.remote import RemoteExecutor
         executor = RemoteExecutor(host='<ip>', port=<port>)
         controller = IterationController(executor, 
           scenarios=['factory/scenarios/definitions/swap_identity_preservation.yaml'])
         result = controller.run_iteration()
         print(f'Iteration {result.iteration_number}: status={result.status}')
         print(f'Metrics: {result.metrics_summary}')
         print(f'Cost so far: \${result.cost_so_far:.2f}')
         "
      2. Assert: iteration logged, metrics present
      3. test -f factory/iteration_log.json
      4. python -c "
         import json
         with open('factory/iteration_log.json') as f:
           lines = [json.loads(l) for l in f if l.strip()]
         assert len(lines) >= 1, 'No iterations logged'
         print(f'Iteration log has {len(lines)} entries')
         "
    Expected Result: One iteration completed and logged
    Evidence: Iteration result + log file

  Scenario: Escalation detects plateau
    Tool: Bash
    Steps:
      1. python -c "
         from factory.iteration_controller import IterationController, IterationResult
         # Simulate 3 iterations with no improvement
         history = [
           IterationResult(iteration_number=1, metrics_summary={'identity_similarity': 0.45}),
           IterationResult(iteration_number=2, metrics_summary={'identity_similarity': 0.455}),
           IterationResult(iteration_number=3, metrics_summary={'identity_similarity': 0.458}),
         ]
         controller = IterationController(None, [])
         reason = controller.check_escalation(history)
         assert reason is not None, 'Should detect plateau'
         assert 'plateau' in reason.type.lower()
         print(f'Escalation detected: {reason.type} — {reason.message}')
         "
    Expected Result: Plateau detected after 3 iterations with delta < 0.01
    Evidence: Escalation reason output

  Scenario: Git commit created per iteration
    Tool: Bash
    Steps:
      1. git log --oneline -5
      2. Assert: recent commits include iteration markers (e.g., "iteration-1:", "iteration-2:")
    Expected Result: Each iteration has a traceable git commit
    Evidence: Git log output

  Scenario: Escalation rules file is valid JSON
    Tool: Bash
    Steps:
      1. python -c "
         import json
         with open('factory/escalation_rules.json') as f:
           rules = json.load(f)
         required = ['success', 'plateau', 'regression', 'max_iterations', 'budget', 'crash']
         for r in required:
           assert r in rules, f'Missing rule: {r}'
         print(f'All {len(required)} escalation rules defined')
         "
    Expected Result: All escalation rules present and valid
    Evidence: Rule count output
  ```

  **Commit**: YES
  - Message: `feat(factory): add iteration controller with escalation rules and Ralph loop workflow`
  - Files: `factory/iteration_controller.py`, `factory/escalation_rules.json`, `.sisyphus/workflows/quality-iteration-loop.md`

---

- [ ] 6. First Autonomous Run (Monitored Kickoff) [BLOCKED — SSH KEY REQUIRED]

  **Status**: 🚫 **BLOCKED** — Cannot proceed without SSH access to RunPod
  
  **Blocker**: SSH key `~/.ssh/id_ed25519` not available on this machine
  - Expected key: `~/.ssh/id_ed25519` (for RunPod host `6j5e16kr33f7fr-64410bf1@ssh.runpod.io`)
  - Available key: `~/.ssh/lightning_rsa` (permission denied by RunPod)
  - Alternative: `/Users/kendrick/Documents/dev/id_rsa` (permission denied by RunPod)
  
  **Prerequisites Complete**:
  - ✅ Task 0: Fixtures ready
  - ✅ Task 1: REFace cloned and checkpoint downloaded
  - ✅ Task 2: RunPod setup scripts ready
  - ✅ Task 3: Orchestrator wired to REFace
  - ✅ Task 4: SSH bridge implemented
  - ✅ Task 5: Iteration controller with escalation rules
  - ✅ Workflow documented in `.sisyphus/workflows/quality-iteration-loop.md`
  
  **What to do** (when unblocked):
  - Execute `/ralph-loop` workflow as documented
  - The executing agent should:
    1. Read the workflow in `.sisyphus/workflows/quality-iteration-loop.md`
    2. Run the first iteration manually and inspect results carefully
    3. Based on the diagnosis from IterationController, make the first code adjustment
    4. Run the second iteration, verify the loop mechanics work
    5. If iterations 1-2 work correctly, the Ralph loop takes over autonomously
  
  - **What the agent adjusts each iteration** (autonomy boundaries):
    - ✅ REFace inference parameters (DDIM steps, scale, sampler config)
    - ✅ Preprocessing: image resizing, face alignment, color space conversion, mask generation
    - ✅ Postprocessing: blending, feathering, color matching, upscaling
    - ✅ Bridge code (`factory/reface_bridge.py`): how REFace is invoked, input preparation, output handling
    - ✅ New preprocessing/postprocessing modules (can create new files)
    - ✅ Different face detectors or alignment methods
    - ✅ ADD new factory scenarios (for targeted testing)
    - ❌ Factory scenario thresholds (`factory/scenarios/definitions/` — SACRED)
    - ❌ Factory gate logic (`factory/gates/`, `factory/judges/`, `factory/identity.py`)
    - ❌ Factory runner (`factory/runner.py`)
    - ❌ Model training (no fine-tuning or LoRA)
    - ❌ REFace model architecture (no modifying the diffusion model itself)
  
  - **Escalation triggers** (loop stops when):
    - ✅ All targeted factory scenarios PASS
    - ⚠️ Metrics plateau: best identity_similarity delta < 0.01 for 3 consecutive iterations
    - 🛑 Architectural dead end: agent determines current approach cannot reach thresholds
    - 💰 Budget: cumulative RunPod cost ≥ $10
    - 🔢 Max iterations: 20

  - **Initial scenario targets** (image-only, skip video/comparative/regression):
    - `swap_identity_preservation.yaml` — core quality test
    - `swap_occlusion_handling.yaml` — occlusion robustness
    - `user_casual_balanced_swap.yaml` — user story: balanced preset

  **Must NOT do**:
  - Do not modify sacred files (see ❌ list above)
  - Do not exceed budget or iteration caps
  - Do not run video scenarios (v2)
  - Do not train models
  - Do not skip git commits between iterations

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: The agent needs to understand face-swap quality issues, diagnose metric failures, and creatively adjust preprocessing/bridge code to improve results. This requires deep domain understanding.
  - **Skills**: [`git-master`]
    - `git-master`: One commit per iteration, rollback on regression
  - **Execution method**: `/ralph-loop` — autonomous iteration until escalation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None (this IS the goal)
  - **Blocked By**: Task 5

  **References**:

  **Pattern References**:
  - `.sisyphus/workflows/quality-iteration-loop.md` (Task 5) — The workflow this task executes
  - `factory/iteration_controller.py` (Task 5) — The controller driving the loop
  - `factory/reface_bridge.py` (Task 3) — The primary code the agent will modify
  - `factory/orchestrator.py` — The swap execution entry point

  **Documentation References**:
  - `AGENTS.md` — Project architecture context (2.5D pipeline, occlusion handling, quirks)
  - `.sisyphus/plans/software-factory.md` — Understanding the factory's design intent

  **Acceptance Criteria**:

  ```
  Scenario: At least 3 iterations completed
    Tool: Bash
    Steps:
      1. python -c "
         import json
         with open('factory/iteration_log.json') as f:
           lines = [json.loads(l) for l in f if l.strip()]
         assert len(lines) >= 3, f'Only {len(lines)} iterations completed'
         for entry in lines:
           print(f'Iteration {entry[\"iteration_number\"]}: '
                 f'identity={entry[\"metrics_summary\"].get(\"identity_similarity\", \"N/A\"):.4f}, '
                 f'status={entry[\"status\"]}')
         print(f'Total iterations: {len(lines)}')
         "
    Expected Result: 3+ iterations with improving or stable metrics
    Evidence: Iteration log summary

  Scenario: Escalation triggered appropriately
    Tool: Bash
    Steps:
      1. python -c "
         import json
         with open('factory/iteration_log.json') as f:
           lines = [json.loads(l) for l in f if l.strip()]
         last = lines[-1]
         assert last['status'] in ('passed', 'plateau', 'escalated', 'max_iterations', 'budget'), \
           f'Unexpected final status: {last[\"status\"]}'
         print(f'Final status: {last[\"status\"]}')
         if last['status'] == 'passed':
           print('SUCCESS: All factory scenarios pass!')
         else:
           print(f'Escalated: {last.get(\"escalation_reason\", \"unknown\")}')
         "
    Expected Result: Loop terminated via a valid escalation rule
    Evidence: Final status and reason

  Scenario: Each iteration has a git commit
    Tool: Bash
    Steps:
      1. python -c "
         import json, subprocess
         with open('factory/iteration_log.json') as f:
           lines = [json.loads(l) for l in f if l.strip()]
         for entry in lines:
           commit = entry.get('git_commit_hash')
           if commit:
             result = subprocess.run(['git', 'log', '--oneline', '-1', commit], capture_output=True, text=True)
             print(f'Iteration {entry[\"iteration_number\"]}: {result.stdout.strip()}')
         "
    Expected Result: Every iteration traceable in git history
    Evidence: Git log per iteration

  Scenario: Budget stayed within cap
    Tool: Bash
    Steps:
      1. python -c "
         import json
         with open('factory/iteration_log.json') as f:
           lines = [json.loads(l) for l in f if l.strip()]
         total_cost = lines[-1].get('cost_so_far', 0)
         print(f'Total RunPod cost: \${total_cost:.2f}')
         assert total_cost <= 12.0, f'Budget exceeded: \${total_cost:.2f}'
         "
    Expected Result: Cost within acceptable range
    Evidence: Cost total
  ```

  **Commit**: YES (multiple commits — one per iteration, automated by the controller)
  - Message pattern: `iteration-N: [what changed] (identity={score}, status={status})`
  - Files: Varies per iteration (reface_bridge.py, orchestrator.py, new preprocessing modules)

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|------------|---------|-----------|--------------|
| 0 | `feat(factory): add test fixture images` | factory/fixtures/ | Images readable |
| 1 | `feat(vendors): add REFace setup and validate inference` | scripts/setup_reface.sh, .gitignore | REFace produces output |
| 2 | `feat(infra): add RunPod setup and remote execution scripts` | scripts/runpod_setup.sh, scripts/run_remote_factory.sh | Remote factory runs |
| 3 | `feat(factory): wire orchestrator to REFace with persistent model bridge` | factory/reface_bridge.py, factory/orchestrator.py | Non-zero identity_similarity |
| 4 | `feat(factory): add SSH remote execution bridge for RunPod` | factory/remote.py | Remote results parseable |
| 5 | `feat(factory): add iteration controller with escalation rules` | factory/iteration_controller.py, factory/escalation_rules.json | Iteration logs correctly |
| 6 | `iteration-N: ...` (multiple, automated) | Varies | Factory metrics improving |

---

## Success Criteria

### Verification Commands
```bash
# Factory runs end-to-end with REFace
python -m factory.runner factory/scenarios/definitions/swap_identity_preservation.yaml \
  --output-json /tmp/final_check.json
python -c "import json; r=json.load(open('/tmp/final_check.json')); print(f'Identity: {r[\"results\"][0][\"metric_results\"][0][\"actual_value\"]:.4f}')"
# Expected: identity_similarity > 0.0 (baseline), ideally approaching 0.65 (threshold)

# Iteration log exists with multiple entries
wc -l factory/iteration_log.json
# Expected: >= 3 lines

# Git history shows iteration commits
git log --oneline --grep="iteration-" | head -10
# Expected: Multiple iteration commits

# Budget check
python -c "import json; lines=[json.loads(l) for l in open('factory/iteration_log.json') if l.strip()]; print(f'Cost: \${lines[-1].get(\"cost_so_far\", 0):.2f}')"
# Expected: <= $10.00
```

### Final Checklist
- [ ] REFace produces face-swapped output images
- [ ] Factory orchestrator calls REFace (not passthrough)
- [ ] Factory scenarios produce non-zero metrics
- [ ] Remote execution on RunPod works via SSH
- [ ] Iteration controller logs results as JSON
- [ ] Each iteration creates a git commit
- [ ] Escalation rules fire correctly (plateau, budget, max iterations)
- [ ] Best iteration is tracked for rollback
- [ ] Factory scenario thresholds were NEVER modified
- [ ] Factory gate/judge code was NEVER modified
- [ ] Total RunPod spend ≤ $10
