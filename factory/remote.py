"""SSH remote execution bridge for factory on RunPod."""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FactoryReport:
    """Simplified FactoryReport for remote results."""
    scenarios_run: int
    scenarios_passed: int
    scenarios_failed: int
    scenarios_skipped: int
    results: list[dict]
    elapsed_seconds: float


class RemoteExecutor:
    """Execute factory scenarios on remote GPU via SSH."""
    
    def __init__(
        self,
        host: str,
        port: int = 22,
        user: str = "root",
        key_path: str = "~/.ssh/id_ed25519",
        workspace: str = "/workspace/watserface"
    ):
        self.host = host
        self.port = port
        self.user = user
        self.key_path = str(Path(key_path).expanduser())
        self.workspace = workspace
    
    def _run_ssh(self, command: str, timeout: int = 300) -> tuple[str, str, int]:
        """Run command on remote via SSH. Returns (stdout, stderr, exit_code)."""
        ssh_cmd = [
            "ssh",
            "-i", self.key_path,
            "-p", str(self.port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"{self.user}@{self.host}",
            command
        ]
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    
    def sync_code(self) -> bool:
        """Sync local code to remote via git push + pull."""
        # Push local changes
        subprocess.run(["git", "push"], check=False)
        # Pull on remote
        stdout, stderr, code = self._run_ssh(
            f"cd {self.workspace} && git pull"
        )
        return code == 0
    
    def run_factory(
        self,
        scenario_path: str,
        output_json: str = "/tmp/factory_result.json",
        ddim_steps: int = 50
    ) -> FactoryReport:
        """Run factory scenario on remote."""
        cmd = (
            f"cd {self.workspace} && "
            f"python -m factory.runner {scenario_path} "
            f"--output-json {output_json} "
            f"2>&1"
        )
        stdout, stderr, code = self._run_ssh(cmd, timeout=600)
        
        if code != 0:
            raise RuntimeError(f"Factory failed: {stderr}")
        
        # Get results
        stdout, stderr, code = self._run_ssh(f"cat {output_json}")
        if code != 0:
            raise RuntimeError(f"Could not read results: {stderr}")
        
        data = json.loads(stdout)
        return FactoryReport(
            scenarios_run=data.get("scenarios_run", 0),
            scenarios_passed=data.get("scenarios_passed", 0),
            scenarios_failed=data.get("scenarios_failed", 0),
            scenarios_skipped=data.get("scenarios_skipped", 0),
            results=data.get("results", []),
            elapsed_seconds=data.get("elapsed_seconds", 0.0)
        )
    
    def run_all_scenarios(self, priority: str = "critical", ddim_steps: int = 50) -> FactoryReport:
        """Run all scenarios at specified priority."""
        import os
        scenarios_dir = os.path.join(self.workspace, "factory/scenarios/definitions")
        cmd = (
            f"cd {self.workspace} && "
            f"python -m factory.runner {scenarios_dir} "
            f"--priority {priority} "
            f"--output-json /tmp/factory_all_results.json"
        )
        stdout, stderr, code = self._run_ssh(cmd, timeout=1200)
        
        if code != 0:
            raise RuntimeError(f"Factory batch failed: {stderr}")
        
        stdout, stderr, code = self._run_ssh("cat /tmp/factory_all_results.json")
        if code != 0:
            raise RuntimeError(f"Could not read batch results: {stderr}")
        
        data = json.loads(stdout)
        return FactoryReport(
            scenarios_run=data.get("scenarios_run", 0),
            scenarios_passed=data.get("scenarios_passed", 0),
            scenarios_failed=data.get("scenarios_failed", 0),
            scenarios_skipped=data.get("scenarios_skipped", 0),
            results=data.get("results", []),
            elapsed_seconds=data.get("elapsed_seconds", 0.0)
        )
    
    def get_gpu_info(self) -> dict:
        """Get GPU info from remote."""
        stdout, _, code = self._run_ssh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader")
        if code != 0:
            return {"name": "unknown", "vram_total_mb": 0, "driver_version": "unknown"}
        
        parts = [p.strip() for p in stdout.strip().split(",")]
        return {
            "name": parts[0] if len(parts) > 0 else "unknown",
            "vram_total_mb": parts[1].replace(" MiB", "").replace(" MB", "") if len(parts) > 1 else 0,
            "driver_version": parts[2] if len(parts) > 2 else "unknown"
        }
    
    def estimate_cost(self, start_time: float, rate_per_hour: float = 0.79) -> float:
        """Estimate RunPod cost. A40 rate is ~$0.79/hour."""
        elapsed_hours = (time.time() - start_time) / 3600
        return elapsed_hours * rate_per_hour
