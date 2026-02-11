#!/bin/bash
# Remote Factory Execution Script
#
# Executes the WatserFace factory on a remote RunPod instance via SSH.
# Pulls latest code, runs a scenario, and returns results as JSON.
#
# Usage:
#   bash scripts/run_remote_factory.sh \
#     --host <runpod-user@ssh.runpod.io> \
#     --key ~/.ssh/id_ed25519 \
#     --scenario factory/scenarios/definitions/swap_identity_preservation.yaml \
#     --output /tmp/remote_result.json
#
# Or with environment variables:
#   export RUNPOD_HOST="6j5e16kr33f7fr-64410bf1@ssh.runpod.io"
#   export RUNPOD_KEY="~/.ssh/id_ed25519"
#   bash scripts/run_remote_factory.sh \
#     --scenario factory/scenarios/definitions/swap_identity_preservation.yaml \
#     --output /tmp/remote_result.json

set -e

# Configuration
RUNPOD_HOST="${RUNPOD_HOST:-}"
RUNPOD_KEY="${RUNPOD_KEY:-~/.ssh/id_ed25519}"
RUNPOD_REPO_DIR="/workspace/watserface"
SCENARIO_PATH=""
OUTPUT_FILE=""
VERBOSE=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Usage: bash run_remote_factory.sh [OPTIONS]

Options:
  --host HOST              RunPod SSH host (user@ssh.runpod.io)
                          Default: \$RUNPOD_HOST env var
  --key KEY               Path to SSH private key
                          Default: ~/.ssh/id_ed25519
  --scenario PATH         Path to factory scenario YAML file
                          Required
  --output FILE           Output file for JSON results
                          Default: stdout
  --verbose               Enable verbose output
  --help                  Show this help message

Environment Variables:
  RUNPOD_HOST            RunPod SSH connection string
  RUNPOD_KEY             Path to SSH private key

Examples:
  # Run with environment variables
  export RUNPOD_HOST="6j5e16kr33f7fr-64410bf1@ssh.runpod.io"
  bash run_remote_factory.sh --scenario factory/scenarios/definitions/swap_identity_preservation.yaml

  # Run with explicit arguments
  bash run_remote_factory.sh \\
    --host 6j5e16kr33f7fr-64410bf1@ssh.runpod.io \\
    --key ~/.ssh/id_ed25519 \\
    --scenario factory/scenarios/definitions/swap_identity_preservation.yaml \\
    --output /tmp/result.json
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            RUNPOD_HOST="$2"
            shift 2
            ;;
        --key)
            RUNPOD_KEY="$2"
            shift 2
            ;;
        --scenario)
            SCENARIO_PATH="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validation
if [ -z "$RUNPOD_HOST" ]; then
    log_error "RunPod host not specified. Use --host or set RUNPOD_HOST env var"
    usage
fi

if [ -z "$SCENARIO_PATH" ]; then
    log_error "Scenario path required (--scenario)"
    usage
fi

# Expand key path
RUNPOD_KEY="${RUNPOD_KEY/#\~/$HOME}"

# Verify key exists
if [ ! -f "$RUNPOD_KEY" ]; then
    log_error "SSH key not found: $RUNPOD_KEY"
    exit 1
fi

log_info "Connecting to RunPod: $RUNPOD_HOST"
log_info "Scenario: $SCENARIO_PATH"

# Build SSH command
SSH_CMD="ssh -i $RUNPOD_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# Test connection
if [ $VERBOSE -eq 1 ]; then
    log_info "Testing SSH connection..."
fi

if ! $SSH_CMD "$RUNPOD_HOST" "echo 'SSH connection OK'" > /dev/null 2>&1; then
    log_error "Failed to connect to RunPod. Check host and key."
    exit 1
fi

log_info "SSH connection successful"

# Remote execution script
REMOTE_SCRIPT=$(cat << 'REMOTE_EOF'
#!/bin/bash
set -e

REPO_DIR="$1"
SCENARIO_PATH="$2"

cd "$REPO_DIR"

# Pull latest code
echo "[INFO] Pulling latest code..."
git pull origin main 2>&1 || git pull origin master 2>&1 || true

# Run factory scenario
echo "[INFO] Running factory scenario: $SCENARIO_PATH"
python -m factory.runner "$SCENARIO_PATH" --output-json /tmp/factory_result.json

# Output result
cat /tmp/factory_result.json
REMOTE_EOF
)

# Execute on remote
log_info "Executing factory on remote..."

if [ -n "$OUTPUT_FILE" ]; then
    # Save to file
    $SSH_CMD "$RUNPOD_HOST" bash -s "$RUNPOD_REPO_DIR" "$SCENARIO_PATH" << 'REMOTE_EOF' > "$OUTPUT_FILE"
#!/bin/bash
set -e

REPO_DIR="$1"
SCENARIO_PATH="$2"

cd "$REPO_DIR"

# Pull latest code
echo "[INFO] Pulling latest code..." >&2
git pull origin main 2>&1 || git pull origin master 2>&1 || true

# Run factory scenario
echo "[INFO] Running factory scenario: $SCENARIO_PATH" >&2
python -m factory.runner "$SCENARIO_PATH" --output-json /tmp/factory_result.json

# Output result
cat /tmp/factory_result.json
REMOTE_EOF
    
    log_info "Results saved to: $OUTPUT_FILE"
    
    # Parse and display summary
    if command -v python3 &> /dev/null; then
        python3 << PYTHON_EOF
import json
try:
    with open('$OUTPUT_FILE') as f:
        result = json.load(f)
    print("[INFO] Factory execution summary:")
    print(f"  Scenarios run: {result.get('scenarios_run', 0)}")
    print(f"  Scenarios passed: {result.get('scenarios_passed', 0)}")
    print(f"  Scenarios failed: {result.get('scenarios_failed', 0)}")
    print(f"  Scenarios skipped: {result.get('scenarios_skipped', 0)}")
except Exception as e:
    print(f"[WARN] Could not parse results: {e}")
PYTHON_EOF
    fi
else
    # Output to stdout
    $SSH_CMD "$RUNPOD_HOST" bash -s "$RUNPOD_REPO_DIR" "$SCENARIO_PATH" << 'REMOTE_EOF'
#!/bin/bash
set -e

REPO_DIR="$1"
SCENARIO_PATH="$2"

cd "$REPO_DIR"

# Pull latest code
echo "[INFO] Pulling latest code..." >&2
git pull origin main 2>&1 || git pull origin master 2>&1 || true

# Run factory scenario
echo "[INFO] Running factory scenario: $SCENARIO_PATH" >&2
python -m factory.runner "$SCENARIO_PATH" --output-json /tmp/factory_result.json

# Output result
cat /tmp/factory_result.json
REMOTE_EOF
fi

log_info "Remote factory execution complete"
