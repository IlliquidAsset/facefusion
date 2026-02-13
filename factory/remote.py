"""SSH Execution Bridge for remote factory execution on RunPod GPU.

Provides RemoteExecutor class for pushing code, running factory scenarios,
and retrieving results from remote RunPod instances.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from factory.runner import FactoryReport

logger = logging.getLogger(__name__)


class RemoteExecutor:
    """Execute factory scenarios on remote RunPod GPU via SSH.
    
    Handles code synchronization, remote factory execution, GPU info retrieval,
    and cost estimation for RunPod A40 instances.
    """

    def __init__(
        self,
        host: str,
        port: int = 22,
        user: str = 'root',
        key_path: str = '~/.ssh/id_ed25519',
        workspace: str = '/workspace/watserface',
    ):
        """Initialize RemoteExecutor with SSH configuration.
        
        Parameters
        ----------
        host : str
            RunPod SSH host (e.g., '6j5e16kr33f7fr-64410bf1@ssh.runpod.io')
        port : int
            SSH port (default: 22)
        user : str
            SSH user (default: 'root')
        key_path : str
            Path to SSH private key (default: '~/.ssh/id_ed25519')
        workspace : str
            Remote workspace directory (default: '/workspace/watserface')
        """
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.key_path: str = os.path.expanduser(key_path)
        self.workspace: str = workspace
        self._start_time: Optional[float] = None

        logger.info(
            'RemoteExecutor initialized: host=%s, workspace=%s, key=%s',
            self.host,
            self.workspace,
            self.key_path,
        )

    def sync_code(self) -> bool:
        """Push local code to remote via git.
        
        Steps:
        1. Run `git push` locally (assumes remote is configured)
        2. SSH to remote and run `git pull` in workspace
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        logger.info('Syncing code to remote...')

        try:
            # Step 1: Push local changes
            logger.debug('Running git push locally...')
            result = subprocess.run(
                ['git', 'push'],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning('git push failed: %s', result.stderr)
                # Continue anyway; remote may already be up-to-date

            # Step 2: Pull on remote
            logger.debug('Running git pull on remote...')
            stdout, stderr, exit_code = self._run_ssh_command(
                f'cd {self.workspace} && git pull origin main 2>&1 || git pull origin master 2>&1 || true',
                timeout=60,
            )
            if exit_code != 0:
                logger.warning('git pull on remote failed: %s', stderr)
                return False

            logger.info('Code sync successful')
            return True

        except subprocess.TimeoutExpired:
            logger.error('Code sync timed out')
            return False
        except Exception as exc:
            logger.error('Code sync failed: %s', exc)
            return False

    def run_factory(
        self,
        scenario_path: str,
        output_json: str = '/tmp/factory_result.json',
        ddim_steps: int = 50,
    ) -> FactoryReport:
        """Run factory scenario on remote.
        
        Steps:
        1. Build SSH command to run factory runner
        2. Capture stdout or SCP result back
        3. Parse JSON into FactoryReport dataclass
        
        Parameters
        ----------
        scenario_path : str
            Path to scenario YAML file (relative to workspace)
        output_json : str
            Remote path for JSON output (default: '/tmp/factory_result.json')
        ddim_steps : int
            DDIM steps for inference (default: 50)
        
        Returns
        -------
        FactoryReport
            Parsed factory report from remote execution
        
        Raises
        ------
        RuntimeError
            If remote execution fails or JSON parsing fails
        """
        logger.info('Running factory scenario on remote: %s', scenario_path)
        self._start_time = time.time()

        try:
            # Build remote command
            cmd = (
                f'cd {self.workspace} && '
                f'python -m factory.runner {scenario_path} '
                f'--output-json {output_json}'
            )

            # Execute on remote
            stdout, stderr, exit_code = self._run_ssh_command(cmd, timeout=600)

            if exit_code != 0:
                logger.error('Remote factory execution failed: %s', stderr)
                raise RuntimeError(f'Remote execution failed: {stderr}')

            # SCP result back
            logger.debug('Retrieving results from remote...')
            local_result = '/tmp/factory_result_local.json'
            scp_cmd = [
                'scp',
                '-i', self.key_path,
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                f'{self.host}:{output_json}',
                local_result,
            ]
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error('SCP failed: %s', result.stderr)
                raise RuntimeError(f'SCP failed: {result.stderr}')

            # Parse JSON
            logger.debug('Parsing factory report...')
            with open(local_result) as f:
                data = json.load(f)

            report = FactoryReport(
                scenarios_run=data.get('scenarios_run', 0),
                scenarios_passed=data.get('scenarios_passed', 0),
                scenarios_failed=data.get('scenarios_failed', 0),
                scenarios_skipped=data.get('scenarios_skipped', 0),
                results=data.get('results', []),
            )

            logger.info(
                'Factory execution complete: %d run, %d passed, %d failed, %d skipped',
                report.scenarios_run,
                report.scenarios_passed,
                report.scenarios_failed,
                report.scenarios_skipped,
            )
            return report

        except json.JSONDecodeError as exc:
            logger.error('Failed to parse factory report JSON: %s', exc)
            raise RuntimeError(f'JSON parse failed: {exc}')
        except Exception as exc:
            logger.error('Factory execution failed: %s', exc)
            raise

    def run_all_scenarios(
        self,
        priority: str = 'critical',
        ddim_steps: int = 50,
    ) -> FactoryReport:
        """Run all scenarios at specified priority on remote.
        
        Parameters
        ----------
        priority : str
            Minimum priority level ('critical', 'high', 'medium', 'low')
        ddim_steps : int
            DDIM steps for inference (default: 50)
        
        Returns
        -------
        FactoryReport
            Parsed factory report from remote execution
        """
        logger.info('Running all scenarios at priority: %s', priority)
        self._start_time = time.time()

        try:
            # Build remote command
            cmd = (
                f'cd {self.workspace} && '
                f'python -m factory.runner factory/scenarios/definitions/ '
                f'--priority {priority} '
                f'--output-json /tmp/factory_all_result.json'
            )

            # Execute on remote
            stdout, stderr, exit_code = self._run_ssh_command(cmd, timeout=1800)

            if exit_code != 0:
                logger.error('Remote factory execution failed: %s', stderr)
                raise RuntimeError(f'Remote execution failed: {stderr}')

            # SCP result back
            logger.debug('Retrieving results from remote...')
            local_result = '/tmp/factory_all_result_local.json'
            scp_cmd = [
                'scp',
                '-i', self.key_path,
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                f'{self.host}:/tmp/factory_all_result.json',
                local_result,
            ]
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error('SCP failed: %s', result.stderr)
                raise RuntimeError(f'SCP failed: {result.stderr}')

            # Parse JSON
            logger.debug('Parsing factory report...')
            with open(local_result) as f:
                data = json.load(f)

            report = FactoryReport(
                scenarios_run=data.get('scenarios_run', 0),
                scenarios_passed=data.get('scenarios_passed', 0),
                scenarios_failed=data.get('scenarios_failed', 0),
                scenarios_skipped=data.get('scenarios_skipped', 0),
                results=data.get('results', []),
            )

            logger.info(
                'All scenarios execution complete: %d run, %d passed, %d failed, %d skipped',
                report.scenarios_run,
                report.scenarios_passed,
                report.scenarios_failed,
                report.scenarios_skipped,
            )
            return report

        except json.JSONDecodeError as exc:
            logger.error('Failed to parse factory report JSON: %s', exc)
            raise RuntimeError(f'JSON parse failed: {exc}')
        except Exception as exc:
            logger.error('All scenarios execution failed: %s', exc)
            raise

    def get_gpu_info(self) -> dict[str, int | str]:
        """Check GPU on remote.
        
        Returns
        -------
        dict
            GPU information with keys:
            - 'name': GPU model name (str)
            - 'vram_total_mb': Total VRAM in MB (int)
            - 'driver_version': NVIDIA driver version (str)
        
        Raises
        ------
        RuntimeError
            If GPU query fails or nvidia-smi is not available
        """
        logger.info('Querying GPU info on remote...')

        try:
            cmd = (
                'nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits && '
                'nvidia-smi --query-gpu=driver_version --format=csv,noheader'
            )
            stdout, stderr, exit_code = self._run_ssh_command(cmd, timeout=30)

            if exit_code != 0:
                logger.error('GPU query failed: %s', stderr)
                raise RuntimeError(f'GPU query failed: {stderr}')

            lines = stdout.strip().split('\n')
            if len(lines) < 2:
                raise RuntimeError('Unexpected nvidia-smi output format')

            # Parse first line: "GPU_NAME, VRAM_MB"
            gpu_line = lines[0].split(',')
            gpu_name = gpu_line[0].strip()
            vram_mb = int(float(gpu_line[1].strip()))

            # Parse second line: driver version
            driver_version = lines[1].strip()

            result = {
                'name': gpu_name,
                'vram_total_mb': vram_mb,
                'driver_version': driver_version,
            }

            logger.info('GPU info: %s', result)
            return result

        except Exception as exc:
            logger.error('Failed to get GPU info: %s', exc)
            raise RuntimeError(f'GPU info query failed: {exc}')

    def estimate_cost(
        self,
        start_time: Optional[float] = None,
        gpu_rate_per_hour: float = 0.79,
    ) -> float:
        """Calculate RunPod cost based on elapsed time.
        
        A40 rate is approximately $0.79/hour.
        
        Parameters
        ----------
        start_time : float, optional
            Unix timestamp of start time. If None, uses self._start_time.
        gpu_rate_per_hour : float
            Hourly GPU rate in dollars (default: 0.79 for A40)
        
        Returns
        -------
        float
            Estimated cost in dollars
        
        Raises
        ------
        ValueError
            If no start time is available
        """
        if start_time is None:
            start_time = self._start_time

        if start_time is None:
            raise ValueError('No start time available. Call run_factory() first or provide start_time.')

        elapsed_seconds = time.time() - start_time
        elapsed_hours = elapsed_seconds / 3600.0
        cost = elapsed_hours * gpu_rate_per_hour

        logger.info(
            'Cost estimate: %.2f hours * $%.2f/hr = $%.4f',
            elapsed_hours,
            gpu_rate_per_hour,
            cost,
        )
        return cost

    def _run_ssh_command(
        self,
        command: str,
        timeout: int = 300,
    ) -> tuple[str, str, int]:
        """Internal: run command via SSH and return (stdout, stderr, exit_code).
        
        Parameters
        ----------
        command : str
            Shell command to execute on remote
        timeout : int
            Command timeout in seconds (default: 300)
        
        Returns
        -------
        tuple
            (stdout, stderr, exit_code)
        """
        logger.debug('SSH command: %s', command)

        try:
            ssh_cmd = [
                'ssh',
                '-i', self.key_path,
                '-p', str(self.port),
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=10',
                self.host,
                command,
            ]

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            logger.debug('SSH exit code: %d', result.returncode)
            if result.stderr:
                logger.debug('SSH stderr: %s', result.stderr)

            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            logger.error('SSH command timed out after %d seconds', timeout)
            raise RuntimeError(f'SSH command timed out: {command}')
        except FileNotFoundError:
            logger.error('SSH binary not found')
            raise RuntimeError('SSH binary not found. Ensure OpenSSH is installed.')
        except Exception as exc:
            logger.error('SSH command failed: %s', exc)
            raise RuntimeError(f'SSH command failed: {exc}')
