"""Golden reference comparator for measuring output quality against baselines."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

from .registry import GoldenEntry

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
	"""Result of comparing an output image against a golden reference."""

	ssim_to_golden: float
	lpips_to_golden: Optional[float] = None
	within_tolerance: bool = False
	metric_deltas: Dict[str, float] = field(default_factory=dict)


class GoldenComparator:
	"""Compares pipeline outputs against golden reference images."""

	def compare(
		self,
		output_path: Path,
		golden_entry: GoldenEntry,
		tolerance: float = 0.05,
		new_metric_scores: Optional[Dict[str, float]] = None,
	) -> ComparisonResult:
		"""Compare an output image against a golden reference.

		Args:
			output_path: Path to the output image to evaluate.
			golden_entry: The golden reference entry to compare against.
			tolerance: SSIM tolerance. within_tolerance is True when
				ssim_to_golden >= (1.0 - tolerance).
			new_metric_scores: Optional new metric scores to compute deltas against
				the golden entry's stored metric_scores.

		Returns:
			ComparisonResult with SSIM, optional LPIPS, tolerance check, and metric deltas.
		"""
		output_img = cv2.imread(str(output_path))
		golden_img = cv2.imread(str(golden_entry.image_path))

		if output_img is None:
			raise FileNotFoundError(f'Could not read output image: {output_path}')
		if golden_img is None:
			raise FileNotFoundError(f'Could not read golden image: {golden_entry.image_path}')

		# Resize to match if dimensions differ
		if output_img.shape != golden_img.shape:
			golden_img = cv2.resize(golden_img, (output_img.shape[1], output_img.shape[0]))

		# SSIM
		ssim_val = self._compute_ssim(output_img, golden_img)

		# LPIPS (optional)
		lpips_val = self._compute_lpips(output_img, golden_img)

		# Metric deltas
		metric_deltas: Dict[str, float] = {}
		if golden_entry.metric_scores:
			scores = new_metric_scores or {}
			for key, baseline in golden_entry.metric_scores.items():
				new_val = scores.get(key, baseline)
				metric_deltas[key] = new_val - baseline

		within_tolerance = ssim_val >= (1.0 - tolerance)

		return ComparisonResult(
			ssim_to_golden=ssim_val,
			lpips_to_golden=lpips_val,
			within_tolerance=within_tolerance,
			metric_deltas=metric_deltas,
		)

	@staticmethod
	def _compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
		"""Compute SSIM between two BGR images."""
		gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
		gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
		try:
			from skimage.metrics import structural_similarity

			return float(structural_similarity(gray1, gray2))
		except ImportError:
			logger.warning('skimage not available, using cv2-based SSIM approximation')
			return GoldenComparator._cv2_ssim_approx(gray1, gray2)

	@staticmethod
	def _cv2_ssim_approx(gray1: np.ndarray, gray2: np.ndarray) -> float:
		"""Simple SSIM approximation using cv2 when skimage is unavailable."""
		c1 = 6.5025  # (0.01 * 255) ** 2
		c2 = 58.5225  # (0.03 * 255) ** 2

		g1 = gray1.astype(np.float64)
		g2 = gray2.astype(np.float64)

		mu1 = cv2.GaussianBlur(g1, (11, 11), 1.5)
		mu2 = cv2.GaussianBlur(g2, (11, 11), 1.5)

		mu1_sq = mu1 * mu1
		mu2_sq = mu2 * mu2
		mu1_mu2 = mu1 * mu2

		sigma1_sq = cv2.GaussianBlur(g1 * g1, (11, 11), 1.5) - mu1_sq
		sigma2_sq = cv2.GaussianBlur(g2 * g2, (11, 11), 1.5) - mu2_sq
		sigma12 = cv2.GaussianBlur(g1 * g2, (11, 11), 1.5) - mu1_mu2

		numerator = (2 * mu1_mu2 + c1) * (2 * sigma12 + c2)
		denominator = (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)

		ssim_map = numerator / denominator
		return float(ssim_map.mean())

	@staticmethod
	def _compute_lpips(img1: np.ndarray, img2: np.ndarray) -> Optional[float]:
		"""Compute LPIPS between two BGR images. Returns None if pyiqa unavailable."""
		try:
			import pyiqa
			import torch

			def _bgr_to_tensor(img: np.ndarray) -> 'torch.Tensor':
				rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
				tensor = torch.from_numpy(rgb).float() / 255.0
				tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # NCHW
				return tensor

			t1 = _bgr_to_tensor(img1)
			t2 = _bgr_to_tensor(img2)

			lpips_metric = pyiqa.create_metric('lpips')
			return float(lpips_metric(t1, t2))
		except (ImportError, Exception) as exc:
			logger.debug('LPIPS computation unavailable: %s', exc)
			return None
