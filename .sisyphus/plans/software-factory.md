# WatserFace Software Factory

## TL;DR

> **Quick Summary**: Build a scenario-driven Software Factory (`factory/`) that validates face-swap quality through YAML-defined scenarios, metric gates (SSIM, PSNR, LPIPS, ArcFace identity), LLM-as-judge perceptual evaluation, and golden reference regression — enabling non-interactive development where code changes are validated against visual quality standards without human review.
> 
> **Deliverables**:
> - `factory/` directory with scenario framework, metric gates, LLM judge, golden registry
> - 6+ YAML scenario definitions (technical + user stories)
> - CLI runner (`python -m factory.runner`) + pytest integration
> - Headless face-swap orchestrator (Gradio-independent)
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 2 waves
> **Critical Path**: Task 1 (deps) → Task 2 (schemas) → Task 3 (orchestrator) → Task 4 (gates) → Task 5 (runner) → Task 8 (scenarios)

---

## Context

### Original Request
Build a Software Factory for the WatserFace project, inspired by StrongDM's factory model (https://factory.strongdm.ai/). The core challenge: visual outputs (face swaps) are subjective, requiring a multi-tier validation approach combining deterministic metrics, perceptual metrics, LLM-as-judge evaluation, and golden reference regression.

### Interview Summary
**Key Discussions**:
- User provided extremely detailed 4-phase build specification
- Agreed to add LPIPS via pyiqa as first-class metric alongside SSIM/PSNR/identity
- All 4 scenario types (visual_quality, performance, comparative, regression) to be built
- GPU required — no CPU fallback
- `blur_score` used directly (not derived `blur_degradation`)
- Single plan covering all 4 phases

**Research Findings**:
- LPIPS correlates best with human perception (Zhang et al., CVPR 2018)
- LLM-as-judge is emerging but NOT production-ready as primary gate — use as advisory
- ArcFace cosine similarity > 0.6 is standard for identity preservation
- Median of N samples (N=3-5) with variance flagging is best practice for LLM judge
- pyiqa provides GPU-accelerated LPIPS, NIQE, BRISQUE in single package

### Metis Review
**Identified Gaps** (addressed):
- **Identity similarity normalization mismatch**: Three different implementations exist (`QualityChecker` normalizes `(x+1)/2`, `QualityValidator` returns raw cosine, `eval/utils` clamps `[0,1]`). Factory uses raw cosine clamped `[0,1]` as canonical form.
- **No headless orchestrator**: `QualityChecker` requires pre-computed embeddings; no simple `swap(source, target) -> result` API exists. Factory must build one.
- **State isolation for comparative scenarios**: `PresetManager.apply_preset()` mutates global state. Factory needs `StateIsolator` context manager.
- **Gradio dependency in training**: Training functions use `gradio.Progress()` default params. Regression scenario type deferred to Phase 4 with Gradio mock/bypass.
- **No PyYAML/Pydantic in deps**: Both must be added to requirements.
- **Fixture storage strategy**: Synthetic for unit tests, download-on-demand for integration, no binary files in git.
- **LPIPS library choice**: Existing `lpips` package already in test deps vs `pyiqa`. Decision: use `pyiqa` for broader metric suite (NIQE, BRISQUE, LPIPS in one package).

---

## Work Objectives

### Core Objective
Build a self-contained `factory/` module that defines, loads, executes, and reports on visual quality scenarios for the WatserFace face-swap pipeline, enabling automated quality validation of code changes.

### Concrete Deliverables
- `factory/` Python package at project root
- Pydantic scenario schema with YAML serialization
- Metric gate evaluation engine wrapping existing quality infrastructure
- LLM-as-judge harness with Anthropic API integration
- Golden reference registry with regression detection
- CLI runner with JSON/human-readable output
- pytest parametrized test integration
- 6+ scenario YAML definitions

### Definition of Done
- [x] `python -m factory.runner --help` shows usage
- [x] `pytest factory/ -v` discovers and runs ≥10 tests
- [x] A single-image face swap scenario runs end-to-end and produces JSON results
- [x] LLM judge gracefully degrades when `ANTHROPIC_API_KEY` is unset
- [x] Golden reference register → compare round-trip is deterministic

### Must Have
- Pydantic v2 schema for scenarios with strict validation
- YAML scenario loading with file existence pre-check
- Metric gates: SSIM, PSNR, identity_similarity (raw cosine), blur_score, artifact_score, LPIPS
- Performance gates: VRAM tracking, wall-clock time
- Comparative scenario support (two-preset delta comparison)
- LLM judge with structured prompts, N-sample aggregation, variance flagging
- Golden reference manifest with baseline scores
- CLI entry point independent of Gradio UI
- pytest integration via YAML parametrize

### Must NOT Have (Guardrails)
- **NO imports from `watserface.uis` or `gradio`** — factory is headless
- **NO binary fixture images committed to git** without LFS
- **NO `(x+1)/2` identity normalization** — use raw cosine clamped to `[0, 1]` matching `eval/utils.py`
- **NO LLM judge enabled by default** — opt-in via `--llm-judge` CLI flag
- **NO parallel scenario execution** — run sequentially to avoid global state corruption
- **NO training/regression scenarios in Phases 1-3** — stub with clear error message until Phase 4
- **NO over-engineered abstractions** — favor simple, readable code over clever patterns
- **NO auto-generated documentation files** — README.md only as specified

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> Every criterion is verified by running a command or using a tool.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: YES (Tests-after, not TDD — factory tests validate the factory itself)
- **Framework**: pytest (existing)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| Module imports | Bash (`python -c`) | Import module, check no errors |
| Schema validation | Bash (`python -c`) | Load YAML, validate Pydantic, check fields |
| Metric computation | Bash (`python -c`) | Compute on synthetic images, check ranges |
| CLI runner | Bash (`python -m factory.runner`) | Run with --help, run with test YAML |
| pytest integration | Bash (`pytest --collect-only`) | Verify test discovery, parametrization |
| LLM judge graceful degradation | Bash (unset API key, run judge) | Verify skip, no crash |
| End-to-end | Bash (full scenario run) | JSON output with expected fields |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Add dependencies (pyyaml, pydantic, pyiqa)
└── Task 6: LLM Judge harness (no deps on metric gates)

Wave 2 (After Task 1):
├── Task 2: Scenario schema + YAML loader (needs pydantic, pyyaml)
├── Task 3: Headless orchestrator (needs pyiqa)
└── Task 7: Golden reference registry (needs pydantic)

Wave 3 (After Tasks 2, 3):
├── Task 4: Metric gates (needs schema + orchestrator)
└── Task 5: Performance gates (needs schema)

Wave 4 (After Tasks 4, 5, 6, 7):
├── Task 8: Scenario YAML definitions
└── Task 9: CLI runner + pytest integration

Wave 5 (After Task 9):
└── Task 10: End-to-end validation + fixture helper

Critical Path: 1 → 2 → 4 → 9 → 10
Parallel Speedup: ~35% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3, 5, 7 | 6 |
| 2 | 1 | 4, 8, 9 | 3, 6, 7 |
| 3 | 1 | 4 | 2, 6, 7 |
| 4 | 2, 3 | 9 | 5 |
| 5 | 2 | 9 | 4 |
| 6 | None | 9 | 1, 2, 3, 5, 7 |
| 7 | 1 | 9 | 2, 3, 6 |
| 8 | 2 | 9 | 4, 5, 6, 7 |
| 9 | 4, 5, 6, 7, 8 | 10 | None |
| 10 | 9 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 6 | quick, unspecified-high |
| 2 | 2, 3, 7 | unspecified-high (parallel) |
| 3 | 4, 5 | unspecified-high (parallel) |
| 4 | 8, 9 | unspecified-high, deep |
| 5 | 10 | deep |

---

## TODOs

- [x] 1. Add Factory Dependencies

  **What to do**:
  - Add `pyyaml>=6.0` to `requirements.txt`
  - Add `pydantic>=2.0` to `requirements.txt`
  - Add `pyiqa>=0.1.10` to `requirements.txt`
  - Verify `lpips` is already in requirements (used in tests)
  - Create `factory/__init__.py` with version string `__version__ = '0.1.0'`
  - Create empty directory structure: `factory/scenarios/`, `factory/scenarios/definitions/`, `factory/gates/`, `factory/judges/`, `factory/golden/`, `factory/fixtures/`, `factory/results/`
  - Create `factory/fixtures/README.md` explaining fixture population strategy
  - Create `factory/fixtures/generate_fixtures.py` helper script that extracts frames from user-provided video using cv2

  **Must NOT do**:
  - Do not add binary fixture images
  - Do not add `gradio` as a factory dependency

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file creation and dependency additions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 6)
  - **Blocks**: Tasks 2, 3, 5, 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `requirements.txt` — existing dependency format and structure
  - `watserface/__init__.py` — package init pattern

  **Documentation References**:
  - `eval/README.md` — example of eval-adjacent README explaining setup and usage

  **Acceptance Criteria**:

  ```
  Scenario: Dependencies install without conflict
    Tool: Bash
    Steps:
      1. pip install pyyaml pydantic pyiqa --dry-run
      2. Assert: no dependency conflicts reported
      3. python -c "import yaml; import pydantic; print('deps OK')"
      4. Assert: prints "deps OK"
    Expected Result: All three packages resolve cleanly
    Evidence: Command output captured

  Scenario: Factory package structure exists
    Tool: Bash
    Steps:
      1. python -c "import factory; print(factory.__version__)"
      2. Assert: prints "0.1.0"
      3. ls factory/scenarios/definitions/ factory/gates/ factory/judges/ factory/golden/ factory/fixtures/ factory/results/
      4. Assert: all directories exist
    Expected Result: Package importable, all directories present
    Evidence: Command output captured

  Scenario: Fixture helper script runs
    Tool: Bash
    Steps:
      1. python factory/fixtures/generate_fixtures.py --help
      2. Assert: shows usage with --video and --output-dir arguments
    Expected Result: Helper script has CLI interface
    Evidence: Help output captured
  ```

  **Commit**: YES
  - Message: `feat(factory): scaffold factory directory and add dependencies`
  - Files: `requirements.txt`, `factory/__init__.py`, `factory/scenarios/__init__.py`, `factory/scenarios/definitions/`, `factory/gates/__init__.py`, `factory/judges/__init__.py`, `factory/golden/__init__.py`, `factory/fixtures/README.md`, `factory/fixtures/generate_fixtures.py`, `factory/results/.gitkeep`

---

- [x] 2. Scenario Schema + YAML Loader

  **What to do**:
  - Create `factory/scenarios/schema.py` with Pydantic v2 models:
    - `ScenarioPriority` enum: critical, high, medium, low
    - `ScenarioType` enum: visual_quality, performance, comparative, regression
    - `MetricAssertion` model: metric (str), operator (Literal[">=", "<=", "==", ">", "<", "!="]), value (float)
    - `LLMJudgeConfig` model: enabled (bool, default False), model (str, default "claude-sonnet-4-20250514"), min_samples (int, default 3), dimensions (Dict[str, float])
    - `SetupConfig` model: source_profile, source_image, target_image, target_video, preset, lora_model (all Optional[str])
    - `Assertions` model: metrics (List[MetricAssertion]), llm_judge (Optional[LLMJudgeConfig]), performance (Dict[str, float]), golden_ref (Optional[str])
    - `Scenario` model: name, description, type, priority, setup, assertions, tags (List[str])
  - Create `factory/scenarios/loader.py`:
    - `load_scenario(path: Path) -> Scenario`: loads single YAML, validates with Pydantic
    - `load_scenarios(directory: Path, priority_filter: Optional[ScenarioPriority] = None) -> List[Scenario]`: discovers all `.yaml` files, loads each, optionally filters by minimum priority
    - `validate_fixtures(scenario: Scenario, fixtures_dir: Path) -> List[str]`: pre-checks that referenced fixture files exist, returns list of missing files
  - Add `__init__.py` exports for `factory/scenarios/`

  **Must NOT do**:
  - Do not validate fixture file existence at Pydantic schema level (deferred to runtime)
  - Do not import any watserface modules in schema.py

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Clean data modeling with Pydantic v2, YAML parsing — well-scoped but needs precision
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 7)
  - **Blocks**: Tasks 4, 8, 9
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `watserface/studio/quality_checker.py:10-27` — `QualityMetrics` dataclass pattern for structured metric results
  - `watserface/args.py` — pattern for enum-based configuration options

  **API/Type References**:
  - `watserface/types.py` — project type conventions

  **External References**:
  - Pydantic v2 docs: https://docs.pydantic.dev/latest/ — model_validator, field_validator syntax

  **Acceptance Criteria**:

  ```
  Scenario: Valid YAML loads and validates
    Tool: Bash
    Steps:
      1. Create a minimal test YAML inline
      2. python -c "
         from factory.scenarios.schema import Scenario, ScenarioType, ScenarioPriority
         import yaml
         data = {
           'name': 'test', 'description': 'test desc',
           'type': 'visual_quality', 'priority': 'critical',
           'setup': {'source_image': 'test.png', 'target_image': 'target.png', 'preset': 'balanced'},
           'assertions': {'metrics': [{'metric': 'ssim', 'operator': '>=', 'value': 0.7}]}
         }
         s = Scenario(**data)
         assert s.type == ScenarioType.visual_quality
         assert s.priority == ScenarioPriority.critical
         assert len(s.assertions.metrics) == 1
         print('Schema validation passed')
         "
      3. Assert: prints "Schema validation passed"
    Expected Result: Pydantic validates all fields correctly
    Evidence: Command output

  Scenario: Invalid scenario type raises ValidationError
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.schema import Scenario
         from pydantic import ValidationError
         try:
           Scenario(name='bad', description='bad', type='nonexistent', priority='critical',
                    setup={}, assertions={})
         except ValidationError as e:
           print(f'Caught ValidationError: {len(e.errors())} errors')
         "
      2. Assert: prints "Caught ValidationError: 1 errors"
    Expected Result: Invalid enum value rejected
    Evidence: Error output

  Scenario: YAML loader discovers scenario files
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.loader import load_scenarios
         from pathlib import Path
         scenarios = load_scenarios(Path('factory/scenarios/definitions'))
         print(f'Loaded {len(scenarios)} scenarios')
         for s in scenarios:
           print(f'  - {s.name} ({s.type.value}, {s.priority.value})')
         "
      2. Assert: prints loaded count and scenario names
    Expected Result: All YAML files in definitions/ discovered and loaded
    Evidence: Command output

  Scenario: Fixture validator catches missing files
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.loader import validate_fixtures
         from factory.scenarios.schema import Scenario
         s = Scenario(name='test', description='test', type='visual_quality',
                      priority='critical',
                      setup={'source_image': 'nonexistent.png'},
                      assertions={})
         from pathlib import Path
         missing = validate_fixtures(s, Path('factory/fixtures'))
         print(f'Missing: {missing}')
         assert len(missing) > 0
         print('Fixture validation works')
         "
      2. Assert: reports nonexistent.png as missing
    Expected Result: Missing fixtures detected at validation time
    Evidence: Command output
  ```

  **Commit**: YES
  - Message: `feat(factory): add Pydantic scenario schema and YAML loader`
  - Files: `factory/scenarios/schema.py`, `factory/scenarios/loader.py`, `factory/scenarios/__init__.py`

---

- [x] 3. Headless Face-Swap Orchestrator

  **What to do**:
  - Create `factory/orchestrator.py` — the single biggest missing piece identified by Metis
  - This module provides a high-level API: `run_swap(source_path, target_path, preset='balanced') -> SwapResult`
  - `SwapResult` dataclass: `source_frame`, `target_frame`, `result_frame`, `source_embedding`, `result_embedding`, `elapsed_seconds`, `peak_vram_mb`
  - The orchestrator must:
    1. Load source and target images via cv2
    2. Detect faces via the existing face detection pipeline (`watserface.face_detector` or `watserface.face_analyser`)
    3. Extract ArcFace embeddings from source face
    4. Apply the specified preset via `state_manager` (with state isolation)
    5. Run the face swap pipeline
    6. Extract ArcFace embedding from result face
    7. Track VRAM and timing
    8. Return structured `SwapResult`
  - Create `factory/state_isolator.py`:
    - `StateIsolator` context manager that snapshots `state_manager` state before entry and restores on exit
    - Must handle the keys used by `PresetManager` — research these via `ast_grep_search` for `state_manager.set_item` calls
  - Create `factory/identity.py`:
    - Wrap identity scoring using raw cosine similarity clamped to `[0, 1]` — matching `eval/utils.py` normalization
    - `compute_identity_similarity(emb1, emb2) -> float`: raw cosine, clamped `[0, 1]`
    - Do NOT use `QualityChecker.compute_identity_similarity` which normalizes via `(x+1)/2`
    - Initialize InsightFace `buffalo_l` lazily (singleton pattern like `eval/utils.py`)

  **Must NOT do**:
  - Do not import from `watserface.uis` or `gradio`
  - Do not use `QualityChecker.compute_identity_similarity` — its normalization is incompatible
  - Do not create a new face detection model — reuse existing `watserface.face_analyser` where possible

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires understanding the full face-swap pipeline, global state management, and multiple module interactions. Must trace through face_analyser → face_detector → face_swapper chain.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 7)
  - **Blocks**: Task 4
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `eval/utils.py` — identity scoring pattern (standalone, raw cosine, InsightFace singleton)
  - `watserface/face_analyser.py` — face detection + embedding extraction pipeline
  - `watserface/face_detector.py` — face detection API
  - `watserface/state_manager.py` — global state API (get_item, set_item)
  - `watserface/studio/quality_checker.py:93-106` — identity similarity computation (DO NOT follow this normalization)
  - `test_preview.py` — example of running a face swap outside Gradio

  **API/Type References**:
  - `watserface/types.py:VisionFrame` — image type used throughout pipeline
  - `watserface/face_store.py` — face cache interface

  **Documentation References**:
  - `AGENTS.md:Thread Safety` — `MEDIAPIPE_FACE_MESH` is global, protected by `THREAD_LOCK`
  - `AGENTS.md:Smart Preview` — how PresetManager toggles global state

  **WHY Each Reference Matters**:
  - `eval/utils.py`: The canonical identity scoring pattern — follow this, not QualityChecker
  - `state_manager.py`: Must understand all state keys to build StateIsolator
  - `test_preview.py`: Shows how to invoke swaps programmatically without UI
  - `face_analyser.py`: Entry point for face detection + embedding extraction

  **Acceptance Criteria**:

  ```
  Scenario: StateIsolator preserves and restores state
    Tool: Bash
    Steps:
      1. python -c "
         from factory.state_isolator import StateIsolator
         from watserface import state_manager
         # Set initial state
         state_manager.set_item('face_swapper_model', 'original_model')
         with StateIsolator():
           state_manager.set_item('face_swapper_model', 'modified_model')
           assert state_manager.get_item('face_swapper_model') == 'modified_model'
         # After exit, state should be restored
         assert state_manager.get_item('face_swapper_model') == 'original_model'
         print('State isolation works')
         "
      2. Assert: prints "State isolation works"
    Expected Result: State restored after context exit
    Evidence: Command output

  Scenario: Identity similarity uses raw cosine
    Tool: Bash
    Steps:
      1. python -c "
         import numpy as np
         from factory.identity import compute_identity_similarity
         # Identical embeddings should give 1.0
         emb = np.random.randn(512).astype(np.float32)
         sim = compute_identity_similarity(emb, emb)
         assert abs(sim - 1.0) < 0.001, f'Expected ~1.0, got {sim}'
         # Orthogonal embeddings should give ~0.0
         emb2 = np.zeros_like(emb)
         emb2[0] = 1.0
         emb3 = np.zeros_like(emb)
         emb3[1] = 1.0
         sim2 = compute_identity_similarity(emb2, emb3)
         assert abs(sim2) < 0.001, f'Expected ~0.0, got {sim2}'
         print('Identity similarity normalization correct')
         "
      2. Assert: prints "Identity similarity normalization correct"
    Expected Result: Raw cosine clamped [0,1], not (x+1)/2
    Evidence: Command output

  Scenario: Orchestrator SwapResult has all fields
    Tool: Bash
    Steps:
      1. python -c "
         from factory.orchestrator import SwapResult
         import inspect
         fields = [f for f in SwapResult.__dataclass_fields__]
         required = ['source_frame', 'target_frame', 'result_frame', 'source_embedding', 'result_embedding', 'elapsed_seconds', 'peak_vram_mb']
         for r in required:
           assert r in fields, f'Missing field: {r}'
         print(f'SwapResult has {len(fields)} fields, all required present')
         "
      2. Assert: all required fields present
    Expected Result: SwapResult dataclass matches spec
    Evidence: Command output
  ```

  **Commit**: YES
  - Message: `feat(factory): add headless face-swap orchestrator with state isolation`
  - Files: `factory/orchestrator.py`, `factory/state_isolator.py`, `factory/identity.py`

---

- [x] 4. Metric Gates

  **What to do**:
  - Create `factory/gates/__init__.py` with exports
  - Create `factory/gates/metrics.py`:
    - `MetricGate` class that wraps `QualityChecker` methods + pyiqa LPIPS
    - Supported metrics: `ssim`, `psnr`, `identity_similarity`, `blur_score`, `artifact_score`, `lpips`, `overall_score`
    - `evaluate(source_frame, target_frame, result_frame, source_embedding, result_embedding, metric_assertion: MetricAssertion) -> GateResult`
    - `GateResult` dataclass: `metric_name`, `expected_operator`, `expected_value`, `actual_value`, `passed` (bool)
    - For LPIPS: initialize `pyiqa.create_metric('lpips')` lazily, compute between target and result frames
    - For identity metrics: use `factory.identity.compute_identity_similarity` (raw cosine), NOT `QualityChecker.compute_identity_similarity`
    - For SSIM/PSNR/blur/artifact: delegate to `QualityChecker` methods
    - `evaluate_all(source, target, result, src_emb, res_emb, assertions: List[MetricAssertion]) -> List[GateResult]`
  - Create `factory/gates/regression.py`:
    - `RegressionGate` class
    - `compare_to_golden(output_path, golden_path, tolerance: float = 0.05) -> RegressionResult`
    - Computes SSIM between output and golden, plus LPIPS distance
    - `RegressionResult` dataclass: `ssim_to_golden`, `lpips_to_golden`, `within_tolerance` (bool)

  **Must NOT do**:
  - Do not use `QualityChecker.compute_identity_similarity` for identity gates — use `factory.identity`
  - Do not create new SSIM/PSNR implementations — delegate to existing `QualityChecker`
  - Do not make LPIPS required for basic metric gates — lazy-load, fail gracefully if pyiqa not installed

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration work wrapping existing modules with new interface
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 5)
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 2, 3

  **References**:

  **Pattern References**:
  - `watserface/studio/quality_checker.py:30-159` — QualityChecker class with SSIM, PSNR, blur, artifact computation
  - `watserface/studio/quality_checker.py:10-27` — QualityMetrics dataclass pattern
  - `factory/identity.py` (Task 3) — canonical identity similarity

  **API/Type References**:
  - `factory/scenarios/schema.py:MetricAssertion` (Task 2) — assertion model to evaluate against
  - `watserface/types.py:VisionFrame` — image type

  **External References**:
  - pyiqa docs: https://iqa-pytorch.readthedocs.io/ — `create_metric('lpips')` API

  **WHY Each Reference Matters**:
  - `QualityChecker`: Delegate SSIM/PSNR/blur/artifact computation — don't reimplement
  - `MetricAssertion`: The schema defines what to evaluate (metric, operator, value)
  - `factory/identity.py`: Canonical identity similarity — the gate MUST use this, not QualityChecker's version

  **Acceptance Criteria**:

  ```
  Scenario: SSIM gate passes for identical images
    Tool: Bash
    Steps:
      1. python -c "
         import numpy as np
         from factory.gates.metrics import MetricGate
         from factory.scenarios.schema import MetricAssertion
         img = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
         assertion = MetricAssertion(metric='ssim', operator='>=', value=0.99)
         gate = MetricGate()
         result = gate.evaluate(img, img, img, None, None, assertion)
         assert result.passed, f'SSIM={result.actual_value}, expected >= 0.99'
         print(f'SSIM identical: {result.actual_value:.4f} - PASSED')
         "
      2. Assert: SSIM >= 0.99 for identical images
    Expected Result: Gate passes
    Evidence: Command output

  Scenario: SSIM gate fails for random images
    Tool: Bash
    Steps:
      1. python -c "
         import numpy as np
         from factory.gates.metrics import MetricGate
         from factory.scenarios.schema import MetricAssertion
         img1 = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
         img2 = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
         assertion = MetricAssertion(metric='ssim', operator='>=', value=0.9)
         gate = MetricGate()
         result = gate.evaluate(img1, img1, img2, None, None, assertion)
         assert not result.passed, f'Should fail, got SSIM={result.actual_value}'
         print(f'SSIM random: {result.actual_value:.4f} - FAILED (expected)')
         "
      2. Assert: Gate fails for dissimilar images
    Expected Result: Gate correctly detects quality failure
    Evidence: Command output

  Scenario: LPIPS metric computes without error
    Tool: Bash
    Steps:
      1. python -c "
         import numpy as np
         from factory.gates.metrics import MetricGate
         from factory.scenarios.schema import MetricAssertion
         img = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
         assertion = MetricAssertion(metric='lpips', operator='<=', value=0.5)
         gate = MetricGate()
         result = gate.evaluate(img, img, img, None, None, assertion)
         print(f'LPIPS identical: {result.actual_value:.4f} - passed={result.passed}')
         "
      2. Assert: LPIPS computes, returns value near 0 for identical images
    Expected Result: LPIPS metric functional via pyiqa
    Evidence: Command output

  Scenario: All operator types work
    Tool: Bash
    Steps:
      1. python -c "
         from factory.gates.metrics import MetricGate
         from factory.scenarios.schema import MetricAssertion
         import numpy as np
         img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
         gate = MetricGate()
         for op in ['>=', '<=', '>', '<', '==', '!=']:
           a = MetricAssertion(metric='blur_score', operator=op, value=0.5)
           r = gate.evaluate(img, img, img, None, None, a)
           print(f'  {op} 0.5: actual={r.actual_value:.3f} passed={r.passed}')
         print('All operators functional')
         "
      2. Assert: all 6 operators produce results without error
    Expected Result: Operator evaluation logic complete
    Evidence: Command output
  ```

  **Commit**: YES
  - Message: `feat(factory): add metric gates with SSIM, PSNR, LPIPS, identity support`
  - Files: `factory/gates/__init__.py`, `factory/gates/metrics.py`, `factory/gates/regression.py`

---

- [x] 5. Performance Gates

  **What to do**:
  - Create `factory/gates/performance.py`:
    - `PerformanceTracker` context manager:
      - On entry: record `time.perf_counter()`, call `torch.cuda.reset_peak_memory_stats()` if CUDA available
      - On exit: record elapsed time, read `torch.cuda.max_memory_allocated()` if CUDA
    - `PerformanceResult` dataclass: `elapsed_seconds`, `peak_vram_mb`, `cache_entries` (from face_store if accessible)
    - `evaluate_performance(result: PerformanceResult, assertions: Dict[str, float]) -> List[GateResult]`
    - Supported assertion keys: `processing_time_seconds`, `peak_vram_mb`, `cache_entries_max`, `frames_processed_ratio`
    - Return `GateResult` (same as metrics) for each assertion

  **Must NOT do**:
  - Do not add CPU fallback logic — GPU required per decision
  - Do not import torch at module level — lazy import for environments without CUDA

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Relatively straightforward wrapper around torch CUDA API
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 4)
  - **Blocks**: Task 9
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `watserface/benchmarker.py` — existing benchmarking patterns
  - `watserface/face_store.py` — cache interface for cache_entries tracking

  **External References**:
  - PyTorch CUDA memory: `torch.cuda.max_memory_allocated()`, `torch.cuda.reset_peak_memory_stats()`

  **Acceptance Criteria**:

  ```
  Scenario: Performance tracker measures elapsed time
    Tool: Bash
    Steps:
      1. python -c "
         import time
         from factory.gates.performance import PerformanceTracker
         with PerformanceTracker() as pt:
           time.sleep(0.1)
         result = pt.result
         assert result.elapsed_seconds >= 0.09, f'Elapsed {result.elapsed_seconds}s, expected >= 0.09'
         print(f'Elapsed: {result.elapsed_seconds:.3f}s - OK')
         "
      2. Assert: elapsed time >= 0.09 seconds
    Expected Result: Timer works
    Evidence: Command output

  Scenario: Performance assertions evaluate correctly
    Tool: Bash
    Steps:
      1. python -c "
         from factory.gates.performance import PerformanceResult, evaluate_performance
         result = PerformanceResult(elapsed_seconds=5.0, peak_vram_mb=8000, cache_entries=50)
         gate_results = evaluate_performance(result, {'processing_time_seconds': 10.0, 'peak_vram_mb': 14336})
         for gr in gate_results:
           print(f'  {gr.metric_name}: {gr.actual_value} {gr.expected_operator} {gr.expected_value} = {gr.passed}')
         assert all(gr.passed for gr in gate_results)
         print('Performance assertions passed')
         "
      2. Assert: all gates pass for values within bounds
    Expected Result: Performance gate evaluation works
    Evidence: Command output
  ```

  **Commit**: YES (groups with Task 4)
  - Message: `feat(factory): add performance gates with VRAM and timing tracking`
  - Files: `factory/gates/performance.py`

---

- [x] 6. LLM-as-Judge Harness

  **What to do**:
  - Create `factory/judges/__init__.py`
  - Create `factory/judges/prompts.py`:
    - `FACE_SWAP_EVALUATION_PROMPT` — the structured prompt from user's spec
    - 5 dimensions: identity_preservation, boundary_blending, lighting_consistency, expression_naturalness, uncanny_valley
    - Each dimension scored 1-10
    - Response format: JSON only
  - Create `factory/judges/vision_judge.py`:
    - `JudgeResult` dataclass: dimension scores (Dict[str, int]), notes (str), raw_response (str)
    - `VisionJudge` class:
      - `__init__(model: str = "claude-sonnet-4-20250514")`: stores model name
      - `evaluate(source_path: str, output_path: str) -> JudgeResult`:
        - Read images, encode as base64
        - Call Anthropic API (`anthropic.Anthropic()` client)
        - Send system prompt + user message with two images
        - Parse JSON response
        - Handle retries (max 2) for malformed JSON
        - Return typed `JudgeResult`
      - If `ANTHROPIC_API_KEY` not set: return `JudgeResult` with `skipped=True`, log warning, do NOT raise
  - Create `factory/judges/aggregator.py`:
    - `AggregatedJudgment` dataclass: medians (Dict[str, float]), means (Dict[str, float]), stds (Dict[str, float]), passed (Dict[str, bool]), unreliable_dimensions (List[str]), all_results (List[JudgeResult])
    - `aggregate_judgments(results: List[JudgeResult], thresholds: Dict[str, float]) -> AggregatedJudgment`:
      - Compute median, mean, std per dimension
      - Flag dimensions with std > 2.0 as "unreliable"
      - Compare median against threshold for pass/fail
    - `run_aggregated_judgment(judge: VisionJudge, source_path: str, output_path: str, n_samples: int = 3, thresholds: Dict[str, float] = {}) -> AggregatedJudgment`:
      - Run judge N times, aggregate results

  **Must NOT do**:
  - Do not make LLM judge a hard gate — always advisory
  - Do not crash when ANTHROPIC_API_KEY is missing — graceful skip with warning
  - Do not import anthropic at module level — lazy import with ImportError handling

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API integration with structured prompting, retry logic, statistical aggregation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1) — no dependencies
  - **Blocks**: Task 9
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `watserface/training/validators/quality.py:55-87` — graceful initialization pattern with try/except and fallback

  **External References**:
  - Anthropic Python SDK: `anthropic.Anthropic().messages.create()` with image content blocks
  - Base64 image encoding: `base64.b64encode(open(path, 'rb').read()).decode('utf-8')`

  **WHY Each Reference Matters**:
  - `QualityValidator` initialization pattern: Shows how to gracefully handle missing deps (InsightFace not available)
  - Anthropic SDK: Needed for the actual API call — image content blocks use `{"type": "image", "source": {"type": "base64", ...}}`

  **Acceptance Criteria**:

  ```
  Scenario: LLM judge degrades gracefully without API key
    Tool: Bash
    Steps:
      1. ANTHROPIC_API_KEY="" python -c "
         from factory.judges.vision_judge import VisionJudge
         judge = VisionJudge()
         result = judge.evaluate('nonexistent.png', 'nonexistent.png')
         assert result.skipped == True
         print('Judge skipped gracefully without API key')
         "
      2. Assert: no crash, skipped=True
    Expected Result: Graceful degradation
    Evidence: Command output

  Scenario: Aggregator computes correct statistics
    Tool: Bash
    Steps:
      1. python -c "
         from factory.judges.aggregator import aggregate_judgments, AggregatedJudgment
         from factory.judges.vision_judge import JudgeResult
         # Simulate 3 judge results
         results = [
           JudgeResult(scores={'identity': 8, 'boundary': 7}, notes='', raw_response='', skipped=False),
           JudgeResult(scores={'identity': 9, 'boundary': 6}, notes='', raw_response='', skipped=False),
           JudgeResult(scores={'identity': 8, 'boundary': 7}, notes='', raw_response='', skipped=False),
         ]
         agg = aggregate_judgments(results, {'identity': 7.0, 'boundary': 6.0})
         assert agg.medians['identity'] == 8.0
         assert agg.passed['identity'] == True
         assert agg.passed['boundary'] == True
         print(f'Medians: {agg.medians}')
         print(f'Stds: {dict((k, f\"{v:.2f}\") for k, v in agg.stds.items())}')
         print('Aggregation correct')
         "
      2. Assert: median identity = 8.0, both pass
    Expected Result: Statistical aggregation works correctly
    Evidence: Command output

  Scenario: Prompt template has all 5 dimensions
    Tool: Bash
    Steps:
      1. python -c "
         from factory.judges.prompts import FACE_SWAP_EVALUATION_PROMPT
         dims = ['identity_preservation', 'boundary_blending', 'lighting_consistency',
                 'expression_naturalness', 'uncanny_valley']
         for d in dims:
           assert d in FACE_SWAP_EVALUATION_PROMPT, f'Missing dimension: {d}'
         print(f'All {len(dims)} dimensions present in prompt')
         "
      2. Assert: all 5 dimensions in prompt template
    Expected Result: Prompt is complete
    Evidence: Command output
  ```

  **Commit**: YES
  - Message: `feat(factory): add LLM-as-judge harness with Anthropic vision API`
  - Files: `factory/judges/__init__.py`, `factory/judges/prompts.py`, `factory/judges/vision_judge.py`, `factory/judges/aggregator.py`

---

- [x] 7. Golden Reference Registry

  **What to do**:
  - Create `factory/golden/__init__.py`
  - Create `factory/golden/registry.py`:
    - `GoldenEntry` dataclass: `scenario_name`, `image_path`, `registered_at` (ISO datetime), `judge_scores` (Optional[Dict[str, float]]), `metric_scores` (Optional[Dict[str, float]])
    - `GoldenRegistry` class:
      - `__init__(golden_dir: Path)`: loads manifest from `{golden_dir}/manifest.json` if exists
      - `register(scenario_name: str, image_path: Path, judge_scores=None, metric_scores=None)`: copies image to golden dir, adds entry to manifest, saves manifest
      - `get(scenario_name: str) -> Optional[GoldenEntry]`: retrieve entry
      - `list() -> List[GoldenEntry]`: all registered entries
      - `remove(scenario_name: str)`: remove entry and image
      - `save_manifest()` / `load_manifest()`: JSON serialization
  - Create `factory/golden/comparator.py`:
    - `GoldenComparator` class:
      - `compare(output_path: Path, golden_entry: GoldenEntry, tolerance: float = 0.05) -> ComparisonResult`
      - `ComparisonResult` dataclass: `ssim_to_golden`, `lpips_to_golden`, `within_tolerance`, `metric_deltas` (Dict[str, float])
      - Computes SSIM and LPIPS between output and golden reference
      - If golden has metric_scores: compute deltas (new - baseline)
      - `within_tolerance` = all deltas <= tolerance

  **Must NOT do**:
  - Do not store full images in manifest.json — only paths
  - Do not auto-regenerate goldens — explicit command only

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Data management with JSON serialization, image copying, comparison logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 2, 3)
  - **Blocks**: Task 9
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `eval/compare_results.py` — JSON-based result comparison and reporting pattern
  - `watserface/studio/quality_checker.py:210-226` — difference heatmap generation (useful for visual diffs)

  **Acceptance Criteria**:

  ```
  Scenario: Register and retrieve golden reference
    Tool: Bash
    Steps:
      1. python -c "
         import tempfile, os
         import numpy as np, cv2
         from pathlib import Path
         from factory.golden.registry import GoldenRegistry
         with tempfile.TemporaryDirectory() as tmpdir:
           golden_dir = Path(tmpdir) / 'golden'
           golden_dir.mkdir()
           # Create test image
           img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
           img_path = Path(tmpdir) / 'test.png'
           cv2.imwrite(str(img_path), img)
           # Register
           registry = GoldenRegistry(golden_dir)
           registry.register('test_scenario', img_path, metric_scores={'ssim': 0.95})
           # Retrieve
           entry = registry.get('test_scenario')
           assert entry is not None
           assert entry.scenario_name == 'test_scenario'
           assert entry.metric_scores['ssim'] == 0.95
           # List
           entries = registry.list()
           assert len(entries) == 1
           # Manifest persists
           registry2 = GoldenRegistry(golden_dir)
           assert registry2.get('test_scenario') is not None
           print('Golden registry round-trip works')
         "
      2. Assert: register, get, list, persist all work
    Expected Result: Full CRUD + persistence
    Evidence: Command output

  Scenario: Comparator detects identical images
    Tool: Bash
    Steps:
      1. python -c "
         import tempfile, numpy as np, cv2
         from pathlib import Path
         from factory.golden.registry import GoldenRegistry, GoldenEntry
         from factory.golden.comparator import GoldenComparator
         with tempfile.TemporaryDirectory() as tmpdir:
           img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
           golden_path = Path(tmpdir) / 'golden.png'
           output_path = Path(tmpdir) / 'output.png'
           cv2.imwrite(str(golden_path), img)
           cv2.imwrite(str(output_path), img)
           entry = GoldenEntry(scenario_name='test', image_path=str(golden_path),
                               registered_at='2026-01-01T00:00:00', metric_scores={'ssim': 1.0})
           comp = GoldenComparator()
           result = comp.compare(output_path, entry)
           assert result.within_tolerance
           assert result.ssim_to_golden > 0.99
           print(f'SSIM to golden: {result.ssim_to_golden:.4f} - within tolerance')
         "
      2. Assert: identical images pass comparison
    Expected Result: Comparison detects no regression
    Evidence: Command output
  ```

  **Commit**: YES
  - Message: `feat(factory): add golden reference registry and comparator`
  - Files: `factory/golden/__init__.py`, `factory/golden/registry.py`, `factory/golden/comparator.py`

---

- [x] 8. Scenario YAML Definitions

  **What to do**:
  - Create the following YAML scenario files in `factory/scenarios/definitions/`:
    1. `swap_identity_preservation.yaml` — basic face swap with Balanced preset, identity_similarity >= 0.65, ssim >= 0.70, blur_score threshold, artifact_score threshold, LLM judge enabled with 5 dimensions
    2. `swap_occlusion_handling.yaml` — swap with partially occluded target (glasses/hand), lower thresholds
    3. `swap_preset_differentiation.yaml` — comparative scenario: Quality vs Fast preset on same input, Quality must score higher
    4. `video_memory_stability.yaml` — performance scenario: process N frames, track VRAM, ensure no OOM (peak_vram_mb <= 14336)
    5. `video_temporal_consistency.yaml` — frame-to-frame identity stability (max_frame_similarity_drop <= 0.15)
    6. `training_checkpoint_resume.yaml` — regression scenario (STUB: type=regression with note that it's not yet executable)
    7. `user_casual_balanced_swap.yaml` — user story: casual user, Balanced preset, overall_score >= 0.70
    8. `user_quality_vs_fast_tradeoff.yaml` — user story: comparative, Quality measurably better than Fast
    9. `user_video_no_oom.yaml` — user story: 30-second video without OOM on T4

  - All scenario YAMLs must use metrics that exist in the MetricGate (ssim, psnr, identity_similarity, blur_score, artifact_score, lpips, overall_score)
  - All identity_similarity thresholds must be documented as "raw cosine clamped [0,1]"
  - Comparative scenarios must use `type: comparative` with clear documentation that the runner processes both presets and compares deltas
  - `training_checkpoint_resume.yaml` must have `type: regression` with a note in description: "This scenario type is not yet executable. Requires Phase 4 training integration."

  **Must NOT do**:
  - Do not reference fixture files that can't exist (use relative paths from factory/fixtures/)
  - Do not set unrealistically high thresholds — use research-backed defaults
  - Do not create scenarios that require specific trained LoRA models

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding metric meanings and reasonable thresholds
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Task 9)
  - **Blocks**: Task 9
  - **Blocked By**: Task 2 (schema must exist first)

  **References**:

  **Pattern References**:
  - `factory/scenarios/schema.py` (Task 2) — Pydantic schema that YAML must conform to
  - User's spec in this prompt — exact YAML examples for several scenarios

  **Documentation References**:
  - Research findings: ArcFace > 0.6 for identity, SSIM > 0.7 for structural, LPIPS < 0.3 for perceptual

  **Acceptance Criteria**:

  ```
  Scenario: All YAML files parse without error
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.loader import load_scenarios
         from pathlib import Path
         scenarios = load_scenarios(Path('factory/scenarios/definitions'))
         print(f'Loaded {len(scenarios)} scenarios:')
         for s in scenarios:
           print(f'  [{s.priority.value:>8}] {s.type.value:>16} | {s.name}')
         assert len(scenarios) >= 9
         print('All scenarios valid')
         "
      2. Assert: >= 9 scenarios loaded, no validation errors
    Expected Result: All YAML conforms to Pydantic schema
    Evidence: Command output with scenario list

  Scenario: Comparative scenarios have correct type
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.loader import load_scenarios
         from factory.scenarios.schema import ScenarioType
         from pathlib import Path
         scenarios = load_scenarios(Path('factory/scenarios/definitions'))
         comparative = [s for s in scenarios if s.type == ScenarioType.comparative]
         print(f'Found {len(comparative)} comparative scenarios')
         assert len(comparative) >= 2
         print('Comparative scenario typing correct')
         "
      2. Assert: at least 2 comparative scenarios found
    Expected Result: Type system distinguishes scenario types
    Evidence: Command output
  ```

  **Commit**: YES (groups with Task 9)
  - Message: `feat(factory): add scenario YAML definitions including user stories`
  - Files: `factory/scenarios/definitions/*.yaml` (9 files)

---

- [x] 9. CLI Runner + Pytest Integration

  **What to do**:
  - Create `factory/runner.py`:
    - CLI entry point via `python -m factory.runner`
    - Args:
      - `scenarios`: glob pattern or specific YAML path(s)
      - `--priority`: minimum priority filter (critical, high, medium, low)
      - `--llm-judge`: opt-IN to LLM judge evaluation (default: OFF)
      - `--output`: results directory (default: `factory/results/`)
      - `--output-json`: write single JSON results file
      - `--skip-types`: skip scenario types (e.g., `--skip-types regression comparative`)
    - Execution flow:
      1. Load scenarios via `factory.scenarios.loader`
      2. Validate fixtures exist (warn on missing, skip scenario)
      3. For each scenario:
         a. If `visual_quality`: run single swap via orchestrator, evaluate all metric gates, optionally run LLM judge
         b. If `performance`: run swap wrapped in PerformanceTracker, evaluate performance assertions
         c. If `comparative`: run swap twice (once per preset) via StateIsolator, compute deltas, evaluate delta assertions
         d. If `regression`: log "Not yet implemented" and skip with warning
      4. If golden_ref specified: run golden comparison
      5. Collect all GateResults into `ScenarioResult` dataclass
      6. Write JSON results + print human-readable summary
    - `ScenarioResult` dataclass: `scenario_name`, `scenario_type`, `passed` (bool), `metric_results` (List[GateResult]), `performance_result` (Optional[PerformanceResult]), `judge_result` (Optional[AggregatedJudgment]), `golden_result` (Optional[ComparisonResult]), `skipped` (bool), `skip_reason` (Optional[str])
    - `FactoryReport` dataclass: `scenarios_run`, `scenarios_passed`, `scenarios_failed`, `scenarios_skipped`, `results` (List[ScenarioResult])
    - Human-readable summary format (like `eval/compare_results.py` output style)
  - Create `factory/__main__.py` to enable `python -m factory`
  - Create `factory/test_scenarios.py`:
    - pytest parametrized test that discovers all YAML files in `factory/scenarios/definitions/`
    - Uses `@pytest.mark.parametrize` with YAML file paths
    - Each test: loads scenario, runs via runner, asserts `passed`
    - Custom marker `@pytest.mark.llm_judge` for tests that require API key
    - Custom marker `@pytest.mark.gpu` for tests requiring GPU
    - Respects `--skip-llm` pytest CLI flag via `conftest.py`
  - Create `factory/conftest.py`:
    - Add `--skip-llm` option to pytest
    - Add `--skip-types` option to pytest
    - Register custom markers
  - Update `pytest.ini` to include `factory/` in test paths and register markers

  **Must NOT do**:
  - Do not make LLM judge default-on in pytest — require explicit opt-in
  - Do not run regression-type scenarios — skip with clear message
  - Do not fail the entire run if one scenario fails — collect and report all

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex integration of all previous components, CLI design, pytest configuration, result aggregation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 4, 5, 6, 7, 8

  **References**:

  **Pattern References**:
  - `eval/compare_results.py` — CLI argument parsing, human-readable report output format
  - `eval/eval_batch.py` — batch processing pattern with JSON output
  - `watserface/args.py` — argparse pattern used in project
  - `pytest.ini` — existing pytest configuration (markers: slow, integration, unit; testpaths: tests/)

  **API/Type References**:
  - All factory modules from Tasks 2-8 (schema, orchestrator, gates, judges, golden)

  **WHY Each Reference Matters**:
  - `eval/compare_results.py`: Sets the standard for CLI output formatting (the `=== COMPARISON ===` style)
  - `pytest.ini`: Must add factory test paths and markers without breaking existing test configuration
  - All factory modules: Runner orchestrates everything — it's the integration point

  **Acceptance Criteria**:

  ```
  Scenario: CLI shows help
    Tool: Bash
    Steps:
      1. python -m factory.runner --help
      2. Assert: shows usage with --scenarios, --priority, --llm-judge, --output, --skip-types args
    Expected Result: CLI interface complete
    Evidence: Help output captured

  Scenario: Runner executes a visual_quality scenario
    Tool: Bash
    Preconditions: At least one visual_quality YAML exists with synthetic/available fixtures
    Steps:
      1. python -m factory.runner factory/scenarios/definitions/swap_identity_preservation.yaml --output-json /tmp/factory_result.json
      2. python -c "
         import json
         with open('/tmp/factory_result.json') as f:
           r = json.load(f)
         assert 'scenarios_run' in r
         assert 'results' in r
         for res in r['results']:
           assert 'scenario_name' in res
           assert 'passed' in res
           assert 'metric_results' in res
         print(f'Results: {r[\"scenarios_run\"]} run, {r[\"scenarios_passed\"]} passed')
         "
      3. Assert: JSON output has expected schema
    Expected Result: End-to-end scenario execution with structured output
    Evidence: JSON file contents

  Scenario: pytest discovers and parametrizes YAML scenarios
    Tool: Bash
    Steps:
      1. pytest factory/test_scenarios.py --collect-only 2>&1
      2. Assert: output shows parametrized test names derived from YAML files
      3. Assert: >= 9 test cases collected
    Expected Result: Test discovery works
    Evidence: pytest collection output

  Scenario: Regression scenarios are skipped with warning
    Tool: Bash
    Steps:
      1. python -m factory.runner factory/scenarios/definitions/training_checkpoint_resume.yaml --output-json /tmp/regression_result.json 2>&1
      2. Assert: output contains "not yet implemented" or "skipped"
      3. python -c "
         import json
         with open('/tmp/regression_result.json') as f:
           r = json.load(f)
         assert r['scenarios_skipped'] >= 1
         print('Regression scenario correctly skipped')
         "
    Expected Result: Regression type handled gracefully
    Evidence: Skip message and JSON output

  Scenario: --skip-types flag works
    Tool: Bash
    Steps:
      1. python -m factory.runner factory/scenarios/definitions/ --skip-types comparative regression --output-json /tmp/skip_result.json
      2. python -c "
         import json
         with open('/tmp/skip_result.json') as f:
           r = json.load(f)
         for res in r['results']:
           assert res['scenario_type'] not in ['comparative', 'regression'] or res['skipped']
         print('Skip types filter works')
         "
    Expected Result: Specified types skipped
    Evidence: JSON output
  ```

  **Commit**: YES
  - Message: `feat(factory): add CLI runner, pytest integration, and scenario execution engine`
  - Files: `factory/runner.py`, `factory/__main__.py`, `factory/test_scenarios.py`, `factory/conftest.py`, `pytest.ini` (update)

---

- [x] 10. End-to-End Validation + README

  **What to do**:
  - Create `factory/README.md` documenting:
    - What the factory is and why it exists (reference StrongDM model)
    - Quick start: `python -m factory.runner factory/scenarios/definitions/ --priority critical`
    - How to write new scenarios (YAML format, available metrics, assertion syntax)
    - How to populate fixtures (link to fixtures/README.md)
    - How to register golden references
    - How to enable LLM judge (API key setup, --llm-judge flag)
    - Architecture overview: scenarios → gates → judges → golden → results
    - Available metrics with normalization notes (especially identity_similarity = raw cosine [0, 1])
  - Run full end-to-end validation:
    - Verify all scenario YAMLs load without error
    - Run at least one visual_quality scenario end-to-end (may need to use synthetic images if fixtures aren't populated)
    - Verify pytest collection discovers all scenarios
    - Verify LLM judge graceful degradation
    - Verify golden registry round-trip
  - Tag commit as `factory-v0.1.0`

  **Must NOT do**:
  - Do not create documentation beyond README.md (no separate docs files)
  - Do not auto-populate fixtures with real face images

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: End-to-end integration validation requires running the full pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task)
  - **Blocks**: None (final)
  - **Blocked By**: Task 9

  **References**:

  **Pattern References**:
  - `eval/README.md` — example of eval-adjacent documentation (setup, usage, examples)
  - `README.md` (project root) — overall project documentation style

  **Acceptance Criteria**:

  ```
  Scenario: Full factory import succeeds
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.schema import Scenario, MetricAssertion, LLMJudgeConfig
         from factory.scenarios.loader import load_scenarios
         from factory.gates.metrics import MetricGate
         from factory.gates.performance import PerformanceTracker
         from factory.judges.vision_judge import VisionJudge
         from factory.judges.aggregator import aggregate_judgments
         from factory.golden.registry import GoldenRegistry
         from factory.golden.comparator import GoldenComparator
         from factory.orchestrator import SwapResult
         from factory.state_isolator import StateIsolator
         from factory.identity import compute_identity_similarity
         print('All factory modules import successfully')
         "
      2. Assert: prints success message, no import errors
    Expected Result: Complete package works
    Evidence: Command output

  Scenario: All YAML scenarios are schema-valid
    Tool: Bash
    Steps:
      1. python -c "
         from factory.scenarios.loader import load_scenarios
         from pathlib import Path
         scenarios = load_scenarios(Path('factory/scenarios/definitions'))
         print(f'Loaded {len(scenarios)} scenarios - all valid')
         types = {}
         for s in scenarios:
           types[s.type.value] = types.get(s.type.value, 0) + 1
         for t, c in sorted(types.items()):
           print(f'  {t}: {c}')
         assert len(scenarios) >= 9
         "
      2. Assert: >= 9 scenarios, multiple types represented
    Expected Result: Full scenario coverage
    Evidence: Scenario type breakdown

  Scenario: pytest runs factory tests
    Tool: Bash
    Steps:
      1. pytest factory/ --collect-only -q 2>&1
      2. Assert: shows collected test count >= 10
      3. Assert: exit code 0
    Expected Result: Test suite discoverable
    Evidence: pytest output

  Scenario: Git tag created
    Tool: Bash
    Steps:
      1. git tag -l 'factory-v0.1.0'
      2. Assert: tag exists
    Expected Result: Version tagged
    Evidence: Tag output
  ```

  **Commit**: YES
  - Message: `feat(factory): add documentation and validate end-to-end`
  - Files: `factory/README.md`
  - Pre-commit: `python -c "from factory.scenarios.loader import load_scenarios; from pathlib import Path; s = load_scenarios(Path('factory/scenarios/definitions')); assert len(s) >= 9; print(f'{len(s)} scenarios valid')"`
  - Post-commit: `git tag factory-v0.1.0`

---

## Commit Strategy

| After Task | Message | Key Files | Verification |
|------------|---------|-----------|--------------|
| 1 | `feat(factory): scaffold factory directory and add dependencies` | requirements.txt, factory/__init__.py | `python -c "import factory"` |
| 2 | `feat(factory): add Pydantic scenario schema and YAML loader` | factory/scenarios/ | `python -c "from factory.scenarios.schema import Scenario"` |
| 3 | `feat(factory): add headless face-swap orchestrator with state isolation` | factory/orchestrator.py, factory/state_isolator.py, factory/identity.py | State isolation test |
| 4+5 | `feat(factory): add metric and performance gates` | factory/gates/ | Metric gate tests |
| 6 | `feat(factory): add LLM-as-judge harness with Anthropic vision API` | factory/judges/ | Graceful degradation test |
| 7 | `feat(factory): add golden reference registry and comparator` | factory/golden/ | Round-trip test |
| 8+9 | `feat(factory): add CLI runner, pytest integration, and scenario definitions` | factory/runner.py, factory/scenarios/definitions/ | `python -m factory.runner --help` |
| 10 | `feat(factory): add documentation and validate end-to-end` | factory/README.md | Tag `factory-v0.1.0` |

---

## Success Criteria

### Verification Commands
```bash
# Package imports
python -c "import factory; print(factory.__version__)"
# Expected: 0.1.0

# Schema validation
python -c "from factory.scenarios.loader import load_scenarios; from pathlib import Path; s = load_scenarios(Path('factory/scenarios/definitions')); print(f'{len(s)} scenarios loaded')"
# Expected: >= 9 scenarios loaded

# CLI entry point
python -m factory.runner --help
# Expected: Shows usage

# Pytest discovery
pytest factory/ --collect-only -q
# Expected: >= 10 tests collected

# LLM judge degradation
ANTHROPIC_API_KEY="" python -c "from factory.judges.vision_judge import VisionJudge; j = VisionJudge(); r = j.evaluate('x', 'y'); print(f'skipped={r.skipped}')"
# Expected: skipped=True
```

### Final Checklist
- [x] All 10 TODOs completed
- [x] All scenario YAMLs parse without error
- [x] CLI runner works end-to-end
- [x] pytest discovers all scenarios
- [x] LLM judge degrades gracefully without API key
- [x] Golden registry register/compare round-trip works
- [x] Identity similarity uses raw cosine [0, 1] everywhere
- [x] No imports from watserface.uis or gradio in factory/
- [x] No binary fixtures committed without LFS
- [x] Git tagged factory-v0.1.0
