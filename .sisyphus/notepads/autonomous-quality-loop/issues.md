# Issues - Autonomous Quality Loop

## 2026-02-11 - Task 5

- No functional blockers in implementation.
- `lsp_diagnostics` for `factory/iteration_controller.py` is clean.
- JSON-file LSP diagnostics require Biome in this environment; JSON validity was verified with `json.load` instead.
- Biome was installed locally and `lsp_diagnostics` for `factory/escalation_rules.json` is now clean.

## 2026-02-11 - CRITICAL BLOCKER: SSH to RunPod

**Status**: UNRESOLVED after 10+ attempts across 8 sessions

**Symptom**: `Permission denied (publickey)` on every SSH attempt to `6j5e16kr33f7fr-64410bf1@ssh.runpod.io`

**Keys tested (ALL rejected)**:
1. `/Users/kendrick/Documents/dev/id_rsa` (RSA 2048-bit, user's original key)
2. `~/.ssh/lightning_rsa` (pre-existing key)
3. `~/.ssh/id_ed25519` (freshly generated ed25519, RunPod's recommended type)
4. All keys simultaneously

**What works**: Pod IS reachable (TCP connection established, server host key received, auth negotiation begins). Key IS offered. Server REJECTS it.

**What we've asked the user to do**:
1. ✅ Confirmed which key was uploaded to RunPod
2. ✅ Asked to re-paste key in RunPod User Settings
3. ✅ Generated fresh ed25519 key and asked to add it
4. ✅ Asked to stop and restart pod (keys injected at boot)
5. ✅ Asked to check Connect dialog for current SSH command
6. ❓ Asked to check for "SSH over exposed TCP" (direct IP:port) option
7. ❓ Asked to run `cat ~/.ssh/authorized_keys` in RunPod web terminal

**Most likely root cause**: The key is not being saved/injected by RunPod. Either:
- The save button in RunPod settings isn't being clicked/isn't working
- The pod isn't being fully stopped and restarted after saving
- RunPod has a bug with this specific pod/account
- The pod template doesn't support SSH key injection

**Impact**: ALL 11 remaining tasks in autonomous-quality-loop.md are blocked. No workaround exists — GPU execution requires SSH.

**Resolution path**: User must verify via RunPod Web Terminal that `~/.ssh/authorized_keys` contains the public key. If it doesn't, manually add it via web terminal.

**Fastest fix — run this in RunPod Web Terminal**:
```bash
mkdir -p ~/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBSDc8LJkLogjbZ0aSDJ/Gh9WvVOB4ittR4rH/cKTUuD watserface-runpod' > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo "DONE"
```

**Infrastructure readiness**: All code is ready. `factory/remote.py` defaults to `~/.ssh/id_ed25519`. Scripts default to same key. The moment SSH works, Task 6 can begin immediately.

**Session 8-11 update (2026-02-11)**: Retried SSH 15+ times total across sessions. User confirmed RunPod settings has OLD RSA key, not the new ed25519 key. User has not yet performed a pod stop/restart or Web Terminal key injection. Boulder paused pending user action.

**To resume**: User must either (a) inject key via Web Terminal, (b) stop+start the pod after updating key in settings, or (c) create a new pod. Then say "SSH is fixed" to resume the boulder.
