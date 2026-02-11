# RunPod GPU Environment Setup Guide

## Overview

This document describes how to set up and use a RunPod A40 GPU instance for running the WatserFace factory with REFace inference.

**Pod Details:**
- **Host**: `ssh.runpod.io`
- **User**: `6j5e16kr33f7fr-64410bf1`
- **GPU**: NVIDIA A40 (48GB VRAM)
- **RAM**: 50GB system
- **CPUs**: 9 cores
- **SSH Key**: `~/.ssh/id_ed25519` (must be provided by user)

---

## Prerequisites

### Local Machine
1. **SSH Key**: You must have the SSH private key at `~/.ssh/id_ed25519`
   - If you don't have it, ask the user who provisioned the RunPod pod
   - The key should have permissions `600` (read/write for owner only)
   ```bash
   chmod 600 ~/.ssh/id_ed25519
   ```

2. **SSH Client**: Standard `ssh` and `scp` commands (included on macOS/Linux)

3. **Python 3.8+**: For parsing JSON results locally

### RunPod Pod
- Pod must be running and SSH enabled
- Standard Linux environment (Ubuntu 20.04 or later)
- ~50GB free disk space (for repo + models)

---

## Quick Start

### 1. Test SSH Connection

```bash
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io "echo 'Connected to RunPod'"
```

**Expected output:**
```
Connected to RunPod
```

If this fails:
- Check that `~/.ssh/id_ed25519` exists and is readable
- Verify the pod is running in the RunPod dashboard
- Ensure SSH is enabled on the pod

### 2. Set Up RunPod Environment

Copy the setup script to the pod and run it:

```bash
# Copy setup script to pod
scp -i ~/.ssh/id_ed25519 scripts/runpod_setup.sh \
  6j5e16kr33f7fr-64410bf1@ssh.runpod.io:/tmp/

# Run setup on pod
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io \
  "bash /tmp/runpod_setup.sh"
```

**What this does:**
1. Clones the WatserFace repository to `/workspace/watserface`
2. Installs system dependencies (git, curl, build tools)
3. Installs Python dependencies (PyYAML, Pydantic, PyIQA)
4. Installs InsightFace + ONNX Runtime GPU
5. Downloads InsightFace buffalo_l model (~300MB)
6. Sets up REFace (if `scripts/setup_reface.sh` exists)
7. Runs a smoke test to verify everything works

**Expected output:**
```
[INFO] RunPod Setup Starting...
[INFO] Cloning WatserFace repository
[INFO] Updating package manager
...
[INFO] RunPod setup complete!
[INFO] Repository location: /workspace/watserface
```

### 3. Run Factory Scenarios Remotely

Use the remote execution script to run factory scenarios on the pod:

```bash
# Set environment variables (optional but recommended)
export RUNPOD_HOST="6j5e16kr33f7fr-64410bf1@ssh.runpod.io"
export RUNPOD_KEY="~/.ssh/id_ed25519"

# Run a scenario
bash scripts/run_remote_factory.sh \
  --scenario factory/scenarios/definitions/swap_identity_preservation.yaml \
  --output /tmp/remote_result.json
```

**Expected output:**
```
[INFO] Connecting to RunPod: 6j5e16kr33f7fr-64410bf1@ssh.runpod.io
[INFO] Scenario: factory/scenarios/definitions/swap_identity_preservation.yaml
[INFO] SSH connection successful
[INFO] Executing factory on remote...
[INFO] Results saved to: /tmp/remote_result.json
[INFO] Factory execution summary:
  Scenarios run: 1
  Scenarios passed: 0
  Scenarios failed: 1
  Scenarios skipped: 0
```

### 4. Inspect Results

```bash
# View raw JSON
cat /tmp/remote_result.json | python3 -m json.tool

# Extract specific metrics
python3 << 'EOF'
import json
with open('/tmp/remote_result.json') as f:
    result = json.load(f)
    
for scenario_result in result['results']:
    print(f"Scenario: {scenario_result['scenario_name']}")
    print(f"  Passed: {scenario_result['passed']}")
    for metric in scenario_result['metric_results']:
        print(f"  {metric['metric_name']}: {metric['actual_value']:.4f}")
EOF
```

---

## Advanced Usage

### Environment Variables

You can configure the remote execution script using environment variables:

```bash
export RUNPOD_HOST="6j5e16kr33f7fr-64410bf1@ssh.runpod.io"
export RUNPOD_KEY="~/.ssh/id_ed25519"

# Now you can omit --host and --key from commands
bash scripts/run_remote_factory.sh --scenario <path> --output <file>
```

### Dry-Run Mode

Test the setup script without making changes:

```bash
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io \
  "bash /tmp/runpod_setup.sh --dry-run"
```

### Verbose Output

Enable verbose logging:

```bash
bash scripts/run_remote_factory.sh \
  --scenario factory/scenarios/definitions/swap_identity_preservation.yaml \
  --output /tmp/result.json \
  --verbose
```

### Manual SSH Access

For debugging or manual operations:

```bash
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io

# Once connected, you can:
cd /workspace/watserface
python -m factory.runner --help
nvidia-smi  # Check GPU status
```

---

## Troubleshooting

### SSH Connection Fails

**Error**: `Permission denied (publickey)`

**Solutions**:
1. Verify the key exists: `ls -la ~/.ssh/id_ed25519`
2. Check key permissions: `chmod 600 ~/.ssh/id_ed25519`
3. Verify the pod is running in RunPod dashboard
4. Try with verbose SSH: `ssh -v -i ~/.ssh/id_ed25519 ...`

### Setup Script Fails

**Error**: `apt-get: command not found`

**Solution**: The pod may not have a standard Linux environment. Contact RunPod support or try a different pod image.

**Error**: `git: command not found`

**Solution**: The setup script tries to install git. If it fails, the pod may be misconfigured. Try running setup again or restart the pod.

### Factory Execution Fails

**Error**: `python: command not found`

**Solution**: Python may not be in PATH. Try:
```bash
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io \
  "/usr/bin/python3 -m factory.runner --help"
```

**Error**: `ModuleNotFoundError: No module named 'factory'`

**Solution**: The repository may not have been cloned correctly. Re-run the setup script:
```bash
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io \
  "bash /tmp/runpod_setup.sh"
```

### GPU Not Detected

**Error**: `No GPU detected (CPU mode only)`

**Solution**: The pod may not have GPU drivers installed. Try:
```bash
ssh -i ~/.ssh/id_ed25519 6j5e16kr33f7fr-64410bf1@ssh.runpod.io \
  "nvidia-smi"
```

If `nvidia-smi` fails, the GPU drivers are not installed. Contact RunPod support.

---

## Security Notes

### SSH Key Management

⚠️ **IMPORTANT**: Never commit the SSH key to git!

- The key is stored locally at `~/.ssh/id_ed25519`
- It is NOT committed to the repository
- If the key is compromised, regenerate it in the RunPod dashboard

### Credential Storage

- SSH connection strings are passed via environment variables or command-line arguments
- They are NOT stored in git or configuration files
- Use environment variables for automation (CI/CD, scripts)

### Pod Lifecycle

- RunPod pods are **ephemeral** — they are destroyed when stopped
- Do NOT rely on persistent storage
- Always pull the latest code before running scenarios
- The setup script is idempotent — it's safe to run multiple times

---

## Integration with Autonomous Loop

The remote execution script is designed to work with the autonomous quality iteration loop:

1. **Local Development**: Test scenarios locally with `python -m factory.runner`
2. **Remote Validation**: Run on RunPod A40 for full-quality results
3. **Iteration Loop**: The loop automatically:
   - Pushes code changes to git
   - Runs `git pull` on the pod
   - Executes factory scenarios
   - Parses JSON results
   - Adjusts parameters based on metrics
   - Repeats until quality passes or plateau is detected

---

## Reference

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/runpod_setup.sh` | One-time setup of RunPod environment |
| `scripts/run_remote_factory.sh` | Execute factory scenarios on RunPod |

### Directories

| Path | Purpose |
|------|---------|
| `/workspace/watserface` | Repository root on RunPod |
| `/workspace/watserface/factory` | Factory module |
| `/workspace/watserface/vendors/REFace` | REFace inference engine |
| `~/.insightface/models` | InsightFace model cache |

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `RUNPOD_HOST` | SSH connection string | `6j5e16kr33f7fr-64410bf1@ssh.runpod.io` |
| `RUNPOD_KEY` | Path to SSH private key | `~/.ssh/id_ed25519` |

---

## Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review RunPod documentation: https://docs.runpod.io/
3. Check pod logs in RunPod dashboard
4. Contact the user who provisioned the pod

---

**Last Updated**: 2026-02-11
**Status**: Ready for use (pending SSH key provision)
