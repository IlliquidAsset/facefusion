# Architectural Decisions - Autonomous Quality Loop

## Decisions Made

### 1. REFace Integration Strategy
**Decision**: Use subprocess invocation via folder I/O rather than direct Python API
**Rationale**: 
- REFace's `one_inference.py` expects folder inputs/outputs
- Direct import would require significant refactoring of REFace's internal pipeline
- Subprocess is cleaner separation and easier to debug
- Performance acceptable for factory validation (not real-time)

### 2. Model Loading Pattern
**Decision**: Lazy initialization with singleton pattern
**Rationale**:
- Following existing pattern in `eval/utils.py`
- First call loads model (~30-60s), subsequent calls are fast
- Bridge class manages state and cleanup

### 3. Remote Execution Architecture
**Decision**: Git-based sync + SSH command execution
**Rationale**:
- Simple and reliable
- No complex deployment pipelines
- Rollback via git history
- Already have scripts for this pattern

### 4. Escalation Rules Format
**Decision**: JSON file with machine-parseable conditions
**Rationale**:
- Easy to read and modify
- Can be loaded by both Python and shell scripts
- Clear separation of concerns

## Open Questions

1. **MPS Support**: Can REFace run on M4 MPS or is CUDA required?
2. **SSH Key Location**: Where is the actual SSH key for RunPod?
3. **Iteration Speed**: How long does one factory iteration take on A40?

## Blockers

1. SSH key `~/.ssh/id_ed25519` does not exist - need to locate correct key

## 2026-02-11 - Task 5 decisions

### 5. Iteration execution scope
**Decision**: Run all configured scenarios sequentially and aggregate them into one `FactoryReport`
**Rationale**:
- Matches the task requirement that the controller receives a scenario list
- Keeps `RemoteExecutor` unchanged while still supporting multi-scenario loops
- Produces one iteration-level pass/fail state and one metrics summary for escalation checks

### 6. Rule source of truth
**Decision**: Load escalation behavior from `factory/escalation_rules.json` at controller init
**Rationale**:
- Keeps stop/rollback policy external and machine-editable
- Allows future policy changes without Python code edits

### 7. Regression rollback strategy
**Decision**: Roll back by reverting commits newer than `best_iteration` in reverse order
**Rationale**:
- Preserves git history and auditability
- Avoids destructive reset commands
