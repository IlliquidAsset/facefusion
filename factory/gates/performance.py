"""Performance tracking and evaluation for factory gates."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PerformanceResult:
	"""Result of performance tracking."""
	elapsed_seconds: float
	peak_vram_mb: float
	cache_entries: int = 0


class PerformanceTracker:
	"""Context manager for tracking performance metrics."""

	def __init__(self) -> None:
		"""Initialize the performance tracker."""
		self._result: Optional[PerformanceResult] = None
		self._start_time: Optional[float] = None

	def __enter__(self) -> "PerformanceTracker":
		"""Enter the context manager."""
		self._start_time = time.perf_counter()

		# Reset CUDA peak memory stats if available
		try:
			import torch
			if torch.cuda.is_available():
				torch.cuda.reset_peak_memory_stats()
		except ImportError:
			pass

		return self

	def __exit__(self, *exc) -> None:
		"""Exit the context manager and compute performance metrics."""
		# Compute elapsed time
		elapsed_seconds = time.perf_counter() - self._start_time

		# Read peak VRAM
		peak_vram_mb = 0.0
		try:
			import torch
			if torch.cuda.is_available():
				peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
		except ImportError:
			pass

		# Read cache entries
		cache_entries = 0
		try:
			from watserface import face_store
			static_faces = face_store.get_face_store().get('static_faces')
			if static_faces:
				cache_entries = len(static_faces)
		except Exception:
			pass

		# Store result
		self._result = PerformanceResult(
			elapsed_seconds=elapsed_seconds,
			peak_vram_mb=peak_vram_mb,
			cache_entries=cache_entries
		)

	@property
	def result(self) -> Optional[PerformanceResult]:
		"""Get the performance result (None if still inside context)."""
		return self._result


def evaluate_performance(
	result: PerformanceResult,
	assertions: Dict[str, float]
) -> List:
	"""Evaluate performance against assertions.

	Args:
		result: PerformanceResult from PerformanceTracker
		assertions: Dict mapping metric names to thresholds

	Returns:
		List of GateResult objects
	"""
	from factory.gates.metrics import GateResult

	gate_results = []

	# Map assertion keys to performance metrics
	metric_mapping = {
		'processing_time_seconds': ('elapsed_seconds', result.elapsed_seconds),
		'peak_vram_mb': ('peak_vram_mb', result.peak_vram_mb),
		'cache_entries_max': ('cache_entries', result.cache_entries),
	}

	for metric_name, threshold in assertions.items():
		if metric_name in metric_mapping:
			_, actual_value = metric_mapping[metric_name]
			gate_result = GateResult(
				metric_name=metric_name,
				actual_value=actual_value,
				expected_operator='<=',
				expected_value=threshold,
				passed=actual_value <= threshold
			)
			gate_results.append(gate_result)

	return gate_results
