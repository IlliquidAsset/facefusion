"""Tests for lip identity texture blend (Task 10).

TDD: Tests written FIRST before implementation.
Validates that blend_lip_identity() blends source identity color
onto target lip texture while preserving edge structure (deformation).
"""

import numpy
import cv2
import pytest
import os


class TestBlendLipIdentityExists:
	"""Verify function exists and has correct signature."""

	def test_import(self):
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		assert callable(blend_lip_identity)

	def test_signature(self):
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		import inspect
		sig = inspect.signature(blend_lip_identity)
		params = list(sig.parameters.keys())
		assert 'swapped_image' in params
		assert 'target_image' in params
		assert 'lip_landmarks' in params

	def test_has_padding_parameter(self):
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		import inspect
		sig = inspect.signature(blend_lip_identity)
		assert 'padding' in sig.parameters
		assert sig.parameters['padding'].default == 15

	def test_toggleable_parameter(self):
		"""Must have apply_lip_blend parameter for toggling."""
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		import inspect
		sig = inspect.signature(blend_lip_identity)
		assert 'apply_lip_blend' in sig.parameters
		assert sig.parameters['apply_lip_blend'].default == False


class TestBlendLipIdentityToggle:
	"""Verify toggling behavior."""

	@pytest.fixture
	def synthetic_data(self):
		"""Create synthetic swapped/target images with distinct lip colors."""
		# Target: blue lips on gray face (represents deformed lip texture)
		target = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(target, (128, 140), (40, 20), 0, 0, 360, (200, 100, 80), -1)
		# Add edge detail (creases) to target lips
		cv2.line(target, (95, 140), (161, 140), (150, 70, 50), 1)
		cv2.line(target, (100, 135), (156, 135), (160, 80, 60), 1)

		# Swapped: red lips on gray face (represents source identity color)
		swapped = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(swapped, (128, 140), (40, 20), 0, 0, 360, (80, 100, 220), -1)

		# Lip landmarks forming an ellipse around the lip area
		angles = numpy.linspace(0, 2 * numpy.pi, 20, endpoint=False)
		lip_landmarks = numpy.column_stack([
			128 + 35 * numpy.cos(angles),
			140 + 15 * numpy.sin(angles)
		]).astype(numpy.float64)

		return swapped, target, lip_landmarks

	def test_disabled_returns_swapped_unchanged(self, synthetic_data):
		"""When apply_lip_blend=False, output equals swapped input."""
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		swapped, target, landmarks = synthetic_data
		result = blend_lip_identity(swapped, target, landmarks, apply_lip_blend=False)
		numpy.testing.assert_array_equal(result, swapped)

	def test_enabled_modifies_lip_region(self, synthetic_data):
		"""When apply_lip_blend=True, lip region pixels change."""
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		swapped, target, landmarks = synthetic_data
		result = blend_lip_identity(swapped, target, landmarks, apply_lip_blend=True)
		# Lip region should differ from swapped
		y_min, y_max = 120, 160
		x_min, x_max = 88, 168
		lip_diff = numpy.abs(result[y_min:y_max, x_min:x_max].astype(float) - swapped[y_min:y_max, x_min:x_max].astype(float))
		assert lip_diff.mean() > 5.0, "Lip region should be modified when blend is enabled"


class TestBlendLipIdentityColorShift:
	"""Verify color shifts toward source identity but doesn't fully replace."""

	@pytest.fixture
	def color_data(self):
		"""Target has blue lips, swapped has red lips."""
		target = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		# Blue-ish lips on target
		cv2.ellipse(target, (128, 140), (40, 20), 0, 0, 360, (220, 120, 80), -1)
		# Add creases
		for y_off in [-3, 0, 3]:
			cv2.line(target, (95, 140 + y_off), (161, 140 + y_off), (180, 90, 60), 1)

		# Red-ish lips on swapped (source identity)
		swapped = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(swapped, (128, 140), (40, 20), 0, 0, 360, (80, 100, 230), -1)

		angles = numpy.linspace(0, 2 * numpy.pi, 20, endpoint=False)
		lip_landmarks = numpy.column_stack([
			128 + 35 * numpy.cos(angles),
			140 + 15 * numpy.sin(angles)
		]).astype(numpy.float64)

		return swapped, target, lip_landmarks

	def test_color_shifts_toward_source(self, color_data):
		"""Result lip color should be between target and swapped (partial blend)."""
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		swapped, target, landmarks = color_data
		result = blend_lip_identity(swapped, target, landmarks, apply_lip_blend=True)

		# Sample lip center pixel
		center_result = result[140, 128].astype(float)
		center_target = target[140, 128].astype(float)
		center_swapped = swapped[140, 128].astype(float)

		# Result should be closer to swapped than target at center (high alpha)
		dist_to_swapped = numpy.linalg.norm(center_result - center_swapped)
		dist_to_target = numpy.linalg.norm(center_result - center_target)
		assert dist_to_swapped < dist_to_target, \
			f"Center should be closer to swapped (source identity). dist_swap={dist_to_swapped:.1f}, dist_target={dist_to_target:.1f}"

	def test_not_full_replacement(self, color_data):
		"""Result should NOT be identical to swapped (must retain some target)."""
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		swapped, target, landmarks = color_data
		result = blend_lip_identity(swapped, target, landmarks, apply_lip_blend=True)

		# Lip region should differ from pure swapped
		y_min, y_max = 125, 155
		x_min, x_max = 95, 161
		lip_result = result[y_min:y_max, x_min:x_max].astype(float)
		lip_swapped = swapped[y_min:y_max, x_min:x_max].astype(float)
		diff = numpy.abs(lip_result - lip_swapped).mean()
		assert diff > 3.0, f"Result should not fully replace target lips. Mean diff={diff:.2f}"


class TestBlendLipIdentityEdgePreservation:
	"""Verify target edge structure (deformation) is preserved."""

	@pytest.fixture
	def edge_data(self):
		"""Target with strong edge detail in lip region."""
		target = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(target, (128, 140), (40, 20), 0, 0, 360, (200, 120, 90), -1)
		# Strong creases/wrinkles
		for i in range(5):
			y = 132 + i * 4
			cv2.line(target, (100, y), (156, y), (140, 70, 50), 1)
		# Vertical crease
		cv2.line(target, (128, 125), (128, 155), (150, 80, 55), 1)

		swapped = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(swapped, (128, 140), (40, 20), 0, 0, 360, (90, 110, 210), -1)

		angles = numpy.linspace(0, 2 * numpy.pi, 20, endpoint=False)
		lip_landmarks = numpy.column_stack([
			128 + 35 * numpy.cos(angles),
			140 + 15 * numpy.sin(angles)
		]).astype(numpy.float64)

		return swapped, target, lip_landmarks

	def test_edge_ssim_above_threshold(self, edge_data):
		"""SSIM of edge structure between target and result should be >0.8."""
		from watserface.processors.modules.transparency_handler import blend_lip_identity

		swapped, target, landmarks = edge_data
		result = blend_lip_identity(swapped, target, landmarks, apply_lip_blend=True)

		# Extract lip ROI
		y_min, y_max = 120, 160
		x_min, x_max = 88, 168

		target_roi = cv2.cvtColor(target[y_min:y_max, x_min:x_max], cv2.COLOR_BGR2GRAY)
		result_roi = cv2.cvtColor(result[y_min:y_max, x_min:x_max], cv2.COLOR_BGR2GRAY)

		# Canny edges
		target_edges = cv2.Canny(target_roi, 50, 150).astype(numpy.float32)
		result_edges = cv2.Canny(result_roi, 50, 150).astype(numpy.float32)

		# Compute SSIM manually (avoid skimage dependency)
		ssim = _compute_ssim(target_edges, result_edges)
		assert ssim > 0.8, f"Edge structure SSIM={ssim:.3f}, expected >0.8"


class TestBlendLipIdentityNonLipUnchanged:
	"""Verify pixels outside lip region are NOT modified."""

	def test_non_lip_pixels_unchanged(self):
		from watserface.processors.modules.transparency_handler import blend_lip_identity

		target = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(target, (128, 140), (40, 20), 0, 0, 360, (200, 120, 90), -1)

		swapped = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		cv2.ellipse(swapped, (128, 140), (40, 20), 0, 0, 360, (90, 110, 210), -1)

		angles = numpy.linspace(0, 2 * numpy.pi, 20, endpoint=False)
		lip_landmarks = numpy.column_stack([
			128 + 35 * numpy.cos(angles),
			140 + 15 * numpy.sin(angles)
		]).astype(numpy.float64)

		result = blend_lip_identity(swapped, target, lip_landmarks, apply_lip_blend=True)

		# Check corners (far from lips) - should equal swapped
		numpy.testing.assert_array_equal(result[0:20, 0:20], swapped[0:20, 0:20])
		numpy.testing.assert_array_equal(result[0:20, 236:256], swapped[0:20, 236:256])
		numpy.testing.assert_array_equal(result[236:256, 0:20], swapped[236:256, 0:20])


class TestBlendLipIdentityReturnType:
	"""Verify output type and shape."""

	def test_output_shape_matches_input(self):
		from watserface.processors.modules.transparency_handler import blend_lip_identity
		target = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		swapped = numpy.full((256, 256, 3), 180, dtype=numpy.uint8)
		landmarks = numpy.array([[120, 135], [128, 130], [136, 135],
		                          [136, 145], [128, 150], [120, 145]], dtype=numpy.float64)
		result = blend_lip_identity(swapped, target, landmarks, apply_lip_blend=True)
		assert result.shape == swapped.shape
		assert result.dtype == numpy.uint8


def _compute_ssim(img1: numpy.ndarray, img2: numpy.ndarray) -> float:
	"""Simple SSIM computation without skimage dependency."""
	C1 = (0.01 * 255) ** 2
	C2 = (0.03 * 255) ** 2

	img1 = img1.astype(numpy.float64)
	img2 = img2.astype(numpy.float64)

	mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
	mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

	mu1_sq = mu1 ** 2
	mu2_sq = mu2 ** 2
	mu1_mu2 = mu1 * mu2

	sigma1_sq = cv2.GaussianBlur(img1 ** 2, (11, 11), 1.5) - mu1_sq
	sigma2_sq = cv2.GaussianBlur(img2 ** 2, (11, 11), 1.5) - mu2_sq
	sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

	ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
	           ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

	return float(ssim_map.mean())
