"""Golden reference registry for managing baseline images and scores."""

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GoldenEntry:
	"""A single golden reference entry."""

	scenario_name: str
	image_path: str
	registered_at: str
	judge_scores: Optional[Dict[str, float]] = None
	metric_scores: Optional[Dict[str, float]] = None


class GoldenRegistry:
	"""Registry for golden reference images and their associated scores."""

	def __init__(self, golden_dir: Path) -> None:
		self._golden_dir = Path(golden_dir)
		self._entries: Dict[str, GoldenEntry] = {}
		self._manifest_path = self._golden_dir / 'manifest.json'
		if self._manifest_path.exists():
			self._load_manifest()

	def register(
		self,
		scenario_name: str,
		image_path: Path,
		judge_scores: Optional[Dict[str, float]] = None,
		metric_scores: Optional[Dict[str, float]] = None,
	) -> GoldenEntry:
		"""Register a new golden reference image.

		Copies the image into golden_dir and creates a manifest entry.
		"""
		image_path = Path(image_path)
		self._golden_dir.mkdir(parents=True, exist_ok=True)
		dest = self._golden_dir / image_path.name
		shutil.copy2(str(image_path), str(dest))
		relative_path = dest.relative_to(self._golden_dir)
		entry = GoldenEntry(
			scenario_name=scenario_name,
			image_path=str(relative_path),
			registered_at=datetime.now(timezone.utc).isoformat(),
			judge_scores=judge_scores,
			metric_scores=metric_scores,
		)
		self._entries[scenario_name] = entry
		self._save_manifest()
		return entry

	def get(self, scenario_name: str) -> Optional[GoldenEntry]:
		"""Get a golden entry by scenario name, or None if not found."""
		return self._entries.get(scenario_name)

	def list(self) -> List[GoldenEntry]:
		"""Return all entries sorted by scenario_name."""
		return sorted(self._entries.values(), key=lambda e: e.scenario_name)

	def remove(self, scenario_name: str) -> bool:
		"""Remove a golden entry and its image file.

		Returns True if the entry existed, False otherwise.
		"""
		entry = self._entries.pop(scenario_name, None)
		if entry is None:
			return False
		image_file = self._golden_dir / entry.image_path
		if image_file.exists():
			image_file.unlink()
		self._save_manifest()
		return True

	def _save_manifest(self) -> None:
		"""Persist all entries to manifest.json."""
		data = {name: asdict(entry) for name, entry in self._entries.items()}
		self._golden_dir.mkdir(parents=True, exist_ok=True)
		with open(self._manifest_path, 'w') as f:
			json.dump(data, f, indent=2)

	# Public alias expected by spec
	save_manifest = _save_manifest

	def _load_manifest(self) -> None:
		"""Load entries from manifest.json. Handles corrupt files gracefully."""
		try:
			with open(self._manifest_path) as f:
				data = json.load(f)
			for name, entry_dict in data.items():
				self._entries[name] = GoldenEntry(**entry_dict)
		except (json.JSONDecodeError, TypeError, KeyError) as exc:
			logger.warning('Failed to load manifest %s: %s', self._manifest_path, exc)
			self._entries = {}

	# Public alias expected by spec
	load_manifest = _load_manifest
