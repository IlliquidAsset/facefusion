# Quality Iteration Loop Workflow

## Trigger Command
**`/ralph-loop`** or **`ralph-loop`** in conversation

## Purpose
Autonomous quality iteration loop that reads factory metrics, diagnoses issues, adjusts code/parameters, pushes to RunPod GPU, re-runs scenarios, and iterates until quality passes or progress stalls — completely hands-off.

## Prerequisites

Before running this workflow, ensure:
1. ✅ Fixture images exist in `factory/fixtures/`
2. ✅ REFace cloned to `vendors/REFace/` with checkpoint
3. ✅ RunPod pod running with SSH access
4. ✅ Environment variables set (or pass explicitly):
   - `RUNPOD_HOST` (default: 6j5e16kr33f7fr-64410bf1@ssh.runpod.io)
   - `RUNPOD_KEY` (default: ~/.ssh/id_ed25519)
   - `RUNPOD_WORKSPACE` (default: /workspace/watserface)

## Workflow

### Phase 0: Pre-Flight Checks

Verify the iteration controller can initialize:

```python
from factory.iteration_controller import IterationController
from factory.remote import RemoteExecutor

# Will use environment variables if args not provided
executor = RemoteExecutor()
controller = IterationController(
    executor,
    scenarios=[
        'factory/scenarios/definitions/swap_identity_preservation.yaml',
        'factory/scenarios/definitions/swap_occlusion_handling.yaml',
        'factory/scenarios/definitions/user_casual_balanced_swap.yaml'
    ],
    max_iterations=20,
    budget_cap=10.0
)
print(f"Controller ready: max_iter={controller.max_iterations}, budget=${controller.budget_cap}")
```

### Phase 1: Baseline Iteration (Iteration 0)

Run first iteration to establish baseline metrics:

```python
# Iteration 0: No changes, just establish baseline
result = controller.run_iteration(changes_description="Baseline - no changes")
print(f"Baseline identity_similarity: {result.metrics_summary.get('identity_similarity', 0):.4f}")
print(f"Status: {result.status}")
print(f"Cost so far: ${result.cost_so_far:.2f}")

# Check for immediate escalation
escalation = controller.check_escalation(controller.history)
if escalation:
    print(f"ESCALATION: {escalation.type} - {escalation.message}")
    # Handle escalation (see Phase 4)
```

### Phase 2: Autonomous Iteration Loop

While no escalation triggers, continue iterating:

```python
while True:
    # 1. Diagnose previous results
    last_result = controller.history[-1]
    diagnosis = controller.diagnose(last_result.factory_report)
    
    if diagnosis['failures']:
        print(f"\n=== Diagnosis ===")
        for failure in diagnosis['failures']:
            print(f"  {failure['metric']}: {failure['actual']:.4f} vs {failure['expected']:.4f} (gap: {failure['gap']:.4f})")
        for suggestion in diagnosis['suggestions']:
            print(f"  Suggestion: {suggestion}")
    
    # 2. Decide what to change (autonomous adjustment)
    # Based on diagnosis, modify code to improve metrics
    # ONLY modify: reface_bridge.py, preprocessing, postprocessing
    # NEVER modify: scenarios/, gates/, judges/, identity.py, runner.py
    changes = decide_changes(diagnosis)  # See adjustment strategies below
    
    # 3. Apply changes
    apply_code_changes(changes)
    
    # 4. Run next iteration
    result = controller.run_iteration(changes_description=changes['description'])
    
    print(f"\n=== Iteration {result.iteration_number} ===")
    print(f"Identity: {result.metrics_summary.get('identity_similarity', 0):.4f}")
    print(f"Status: {result.status}")
    print(f"Cost: ${result.cost_so_far:.2f}")
    print(f"Commit: {result.git_commit_hash}")
    
    # 5. Check escalation rules
    escalation = controller.check_escalation(controller.history)
    if escalation:
        print(f"\n*** ESCALATION TRIGGERED: {escalation.type} ***")
        print(f"Message: {escalation.message}")
        break
```

### Phase 3: Autonomous Adjustment Strategies

Based on diagnosis, the agent may adjust:

#### Identity Similarity Too Low
```python
# Strategy: Increase DDIM steps for better quality
# File: factory/reface_bridge.py
# Change: Increase default ddim_steps from 10 to 25

# Strategy: Adjust face alignment
# File: factory/reface_bridge.py  
# Change: Modify alignment coefficients or cropping

# Strategy: Add preprocessing alignment
# Create: factory/preprocessing/face_aligner.py
# Wire into reface_bridge before swap()
```

#### Boundary/Blending Issues
```python
# Strategy: Add post-processing blur/feather
# File: factory/reface_bridge.py
# Change: Apply Gaussian blur to mask boundaries

# Strategy: Color correction
# Create: factory/postprocessing/color_match.py
# Match histograms between source and target
```

#### Quality/Artifacts
```python
# Strategy: Adjust REFace scale parameter
# File: factory/reface_bridge.py
# Change: scale from 3.5 to 2.5 (less aggressive)

# Strategy: Add upscaling
# Create: factory/postprocessing/upscaler.py
# Use Real-ESRGAN or similar
```

#### Performance Too Slow
```python
# Strategy: Reduce DDIM steps
# File: factory/reface_bridge.py
# Change: ddim_steps from 50 to 10

# Strategy: Enable batch processing
# Use swap_batch() instead of sequential swap()
```

### Phase 4: Escalation Handling

When escalation triggers, handle according to type:

```python
def handle_escalation(escalation, controller):
    if escalation.type == "success":
        print("✅ All scenarios pass! Quality targets achieved.")
        print(f"Best iteration: {controller.track_best()}")
        return "COMPLETE"
    
    elif escalation.type == "plateau":
        print("⚠️ Metrics plateaued - no improvement for 3 iterations")
        print(f"Best achieved: {controller.best_metric_value:.4f}")
        print("Recommend: Human review of current approach")
        return "PLATEAU"
    
    elif escalation.type == "regression":
        print("🔄 Metrics regressed - rolling back to best iteration")
        controller.rollback_to_best()
        print(f"Rolled back to iteration {controller.best_iteration}")
        return "ROLLBACK"
    
    elif escalation.type == "max_iterations":
        print("🔢 Max iterations (20) reached")
        print(f"Best results at iteration {controller.best_iteration}")
        return "MAX_ITER"
    
    elif escalation.type == "budget":
        print("💰 Budget cap ($10) approaching")
        print(f"Current spend: ${controller.history[-1].cost_so_far:.2f}")
        return "BUDGET"
    
    elif escalation.type == "crash":
        print("💥 Factory crash detected")
        print("Recommend: Inspect logs, fix issue, retry")
        return "CRASH"
    
    return "UNKNOWN"
```

## Guardrails (MUST NOT Violate)

- ❌ **NEVER** modify `factory/scenarios/definitions/*.yaml` — these are sacred user quality standards
- ❌ **NEVER** modify `factory/gates/`, `factory/judges/`, `factory/identity.py`, `factory/runner.py` — trusted infrastructure
- ❌ **NEVER** modify REFace model architecture in `vendors/REFace/`
- ❌ **NEVER** train models or fine-tune weights
- ❌ **NEVER** exceed 20 iterations without human escalation
- ❌ **NEVER** exceed $10 RunPod spend
- ❌ **NEVER** skip git commits between iterations
- ❌ **NEVER** run video scenarios (image-only for v1)

## Safety Boundaries (MAY Modify)

- ✅ **MAY** modify `factory/reface_bridge.py` — primary adjustment target
- ✅ **MAY** modify `factory/orchestrator.py` — swap execution logic
- ✅ **MAY** create preprocessing modules in `factory/preprocessing/`
- ✅ **MAY** create postprocessing modules in `factory/postprocessing/`
- ✅ **MAY** adjust REFace inference parameters (ddim_steps, scale, sampler)
- ✅ **MAY** add new factory scenarios for targeted testing

## Target Scenarios

Image-only scenarios for v1:
1. `swap_identity_preservation.yaml` — Core quality test (identity_similarity >= 0.65)
2. `swap_occlusion_handling.yaml` — Occlusion robustness
3. `user_casual_balanced_swap.yaml` — User story: balanced preset

## Success Metrics

Loop succeeds when:
- ✅ All targeted scenarios PASS
- ✅ identity_similarity >= 0.65 on swap_identity_preservation
- ✅ Each iteration has traceable git commit
- ✅ Total cost <= $10
- ✅ No sacred files modified

## Output Artifacts

During execution, the loop produces:

1. **factory/iteration_log.json** — JSONL file with all iterations
2. **Git commits** — One per iteration with pattern `iteration-N: identity=X.XXXX`
3. **Metrics progression** — Tracked in log for trend analysis
4. **Final report** — Console output with escalation reason and best iteration

## Example Session

```
=== Starting Autonomous Quality Loop ===
Max iterations: 20
Budget cap: $10.00
Target scenarios: 3

=== Iteration 1 ===
Identity: 0.4231
Status: failed
Cost: $0.12
Commit: a1b2c3d
Diagnosis: Low identity similarity — suggest increasing DDIM steps

[Adjusting: ddim_steps 10 → 25]

=== Iteration 2 ===
Identity: 0.5876
Status: failed
Cost: $0.28
Commit: e4f5g6h
Diagnosis: Improved but still below threshold — suggest face alignment

[Adjusting: Adding face alignment preprocessing]

=== Iteration 3 ===
Identity: 0.6712
Status: passed
Cost: $0.45
Commit: i7j8k9l

*** ESCALATION TRIGGERED: success ***
Message: All factory scenarios pass. Quality targets achieved.
Best iteration: 3
Total cost: $0.45
```

## Recovery Procedures

### If Loop Crashes Mid-Iteration

```python
# Resume from log
import json

log_path = Path("factory/iteration_log.json")
if log_path.exists():
    with open(log_path) as f:
        lines = [json.loads(l) for l in f if l.strip()]
    last_iter = lines[-1]["iteration_number"]
    print(f"Resuming from iteration {last_iter + 1}")
    controller.iteration_count = last_iter
    controller.history = lines
```

### If SSH Connection Fails

1. Verify `RUNPOD_HOST` and `RUNPOD_KEY` environment variables
2. Test: `ssh -i $RUNPOD_KEY $RUNPOD_HOST "echo 'Connected'"`
3. If RunPod pod stopped, start new pod and update `RUNPOD_HOST`

### If REFace Server Won't Start

1. Check GPU availability on RunPod: `nvidia-smi`
2. Check REFace dependencies installed
3. Check checkpoint exists: `ls -lh vendors/REFace/models/REFace/checkpoints/`
4. Review logs in iteration output for specific errors

## Integration with Prometheus

After loop completes (success or escalation), Prometheus reviews:

1. **iteration_log.json** — Full metrics history
2. **Git history** — `git log --oneline --grep="iteration-"`
3. **Cost report** — Total RunPod spend
4. **What changed** — Diff between first and last iteration

Prometheus decides:
- ✅ **SUCCESS**: Accept results, proceed to next milestone
- ⚠️ **PLATEAU**: Human review, maybe adjust target scenarios
- 🔄 **RETRY**: Different approach suggested, restart loop
- 🛑 **ESCALATE**: Fundamental issue, need architectural change
