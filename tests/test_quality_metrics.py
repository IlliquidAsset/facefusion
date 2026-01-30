"""Tests for quality metrics validation - LPIPS, SSIM, temporal consistency, compositing."""
import pytest
import numpy
import cv2


class TestLPIPSComputation:
    """Test LPIPS metric computation."""
    
    def test_lpips_import(self):
        """LPIPS library should be importable."""
        import lpips
        assert lpips is not None
    
    def test_lpips_model_creation(self):
        """LPIPS model should initialize successfully."""
        import lpips
        model = lpips.LPIPS(net='alex')
        assert model is not None
    
    def test_lpips_identical_images_zero(self):
        """Identical images should have LPIPS ~0."""
        import lpips
        import torch
        model = lpips.LPIPS(net='alex')
        img = torch.randn(1, 3, 64, 64)
        dist = model(img, img)
        assert float(dist) < 0.01
    
    def test_lpips_different_images_nonzero(self):
        """Different images should have LPIPS > 0."""
        import lpips
        import torch
        model = lpips.LPIPS(net='alex')
        img1 = torch.randn(1, 3, 64, 64)
        img2 = torch.randn(1, 3, 64, 64)
        dist = model(img1, img2)
        assert float(dist) > 0.01
    
    def test_lpips_range_valid(self):
        """LPIPS should be in valid range."""
        import lpips
        import torch
        model = lpips.LPIPS(net='alex')
        img1 = torch.ones(1, 3, 64, 64)
        img2 = -torch.ones(1, 3, 64, 64)
        dist = model(img1, img2)
        assert 0 <= float(dist) <= 2.0
    
    def test_lpips_batch_processing(self):
        """LPIPS should handle batch inputs."""
        import lpips
        import torch
        model = lpips.LPIPS(net='alex')
        img1 = torch.randn(2, 3, 64, 64)
        img2 = torch.randn(2, 3, 64, 64)
        dist = model(img1, img2)
        assert dist.shape == (2, 1, 1, 1)
    
    def test_lpips_symmetry(self):
        """LPIPS(A, B) should equal LPIPS(B, A)."""
        import lpips
        import torch
        model = lpips.LPIPS(net='alex')
        img1 = torch.randn(1, 3, 64, 64)
        img2 = torch.randn(1, 3, 64, 64)
        dist_ab = float(model(img1, img2))
        dist_ba = float(model(img2, img1))
        assert abs(dist_ab - dist_ba) < 0.001


class TestSSIMComputation:
    """Test SSIM metric computation."""
    
    def test_ssim_identical_is_one(self):
        """Identical images should have SSIM = 1.0."""
        from skimage.metrics import structural_similarity
        img = numpy.random.randint(0, 255, (64, 64), dtype=numpy.uint8)
        ssim = structural_similarity(img, img, data_range=255)
        assert ssim == pytest.approx(1.0, abs=0.001)
    
    def test_ssim_different_is_less_than_one(self):
        """Different images should have SSIM < 1.0."""
        from skimage.metrics import structural_similarity
        img1 = numpy.random.randint(0, 255, (64, 64), dtype=numpy.uint8)
        img2 = numpy.random.randint(0, 255, (64, 64), dtype=numpy.uint8)
        ssim = structural_similarity(img1, img2, data_range=255)
        assert ssim < 1.0
    
    def test_ssim_range_valid(self):
        """SSIM should be in [-1, 1] range."""
        from skimage.metrics import structural_similarity
        img1 = numpy.zeros((64, 64), dtype=numpy.uint8)
        img2 = numpy.ones((64, 64), dtype=numpy.uint8) * 255
        ssim = structural_similarity(img1, img2, data_range=255)
        assert -1 <= ssim <= 1
    
    def test_ssim_symmetry(self):
        """SSIM(A, B) should equal SSIM(B, A)."""
        from skimage.metrics import structural_similarity
        img1 = numpy.random.randint(0, 255, (64, 64), dtype=numpy.uint8)
        img2 = numpy.random.randint(0, 255, (64, 64), dtype=numpy.uint8)
        ssim_ab = structural_similarity(img1, img2, data_range=255)
        ssim_ba = structural_similarity(img2, img1, data_range=255)
        assert abs(ssim_ab - ssim_ba) < 0.001
    
    def test_ssim_multichannel(self):
        """SSIM should work with multichannel images."""
        from skimage.metrics import structural_similarity
        img1 = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        img2 = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        ssim = structural_similarity(img1, img2, data_range=255, channel_axis=2)
        assert -1 <= ssim <= 1
    
    def test_ssim_slightly_different_images(self):
        """SSIM of slightly different images should be high."""
        from skimage.metrics import structural_similarity
        img = numpy.random.randint(0, 255, (64, 64), dtype=numpy.uint8)
        img_noisy = img.copy().astype(numpy.float32)
        img_noisy += numpy.random.normal(0, 5, img.shape)
        img_noisy = numpy.clip(img_noisy, 0, 255).astype(numpy.uint8)
        ssim = structural_similarity(img, img_noisy, data_range=255)
        assert ssim > 0.8


class TestTemporalConsistency:
    """Test temporal consistency measurement."""
    
    def test_identical_frames_high_score(self):
        """Identical frames should have high temporal consistency."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        frame = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        frames = [frame.copy() for _ in range(5)]
        score = handler.compute_temporal_consistency(frames)
        assert score > 0.99
    
    def test_varying_frames_lower_score(self):
        """Varying frames should have lower temporal consistency."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        frames = [numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8) for _ in range(5)]
        score = handler.compute_temporal_consistency(frames)
        assert score < 0.99
    
    def test_single_frame_returns_one(self):
        """Single frame should return consistency score of 1.0."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        frame = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        score = handler.compute_temporal_consistency([frame])
        assert score == 1.0
    
    def test_empty_frames_returns_one(self):
        """Empty frame list should return 1.0."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        score = handler.compute_temporal_consistency([])
        assert score == 1.0
    
    def test_gradually_changing_frames(self):
        """Gradually changing frames should have moderate consistency."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        frames = []
        for i in range(5):
            frame = numpy.full((64, 64, 3), 100 + i * 20, dtype=numpy.uint8)
            frames.append(frame)
        score = handler.compute_temporal_consistency(frames)
        assert 0.5 < score < 0.99
    
    def test_consistency_score_range(self):
        """Temporal consistency should be in [0, 1] range."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        frames = [numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8) for _ in range(10)]
        score = handler.compute_temporal_consistency(frames)
        assert 0 <= score <= 1


class TestCompositingQuality:
    """Test compositing quality and correctness."""
    
    def test_full_alpha_preserves_original(self):
        """Alpha = 1 everywhere should return original."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        dirty_swap = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        alpha = numpy.ones((64, 64), dtype=numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        numpy.testing.assert_array_equal(result, original)
    
    def test_zero_alpha_preserves_swap(self):
        """Alpha = 0 everywhere should return dirty swap."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        dirty_swap = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        alpha = numpy.zeros((64, 64), dtype=numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        numpy.testing.assert_array_equal(result, dirty_swap)
    
    def test_half_alpha_blends(self):
        """Alpha = 0.5 should average the two frames."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.full((64, 64, 3), 200, dtype=numpy.uint8)
        dirty_swap = numpy.full((64, 64, 3), 100, dtype=numpy.uint8)
        alpha = numpy.full((64, 64), 0.5, dtype=numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        expected = 150
        assert numpy.abs(result.astype(float).mean() - expected) < 1.0
    
    def test_composite_output_shape(self):
        """Composite output should match original shape."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        h, w = 100, 100
        original = numpy.zeros((h, w, 3), dtype=numpy.uint8)
        dirty_swap = numpy.ones((h, w, 3), dtype=numpy.uint8) * 255
        alpha = numpy.random.rand(h, w).astype(numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        assert result.shape == (h, w, 3)
    
    def test_composite_output_dtype(self):
        """Composite output should be uint8."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.zeros((64, 64, 3), dtype=numpy.uint8)
        dirty_swap = numpy.ones((64, 64, 3), dtype=numpy.uint8) * 255
        alpha = numpy.random.rand(64, 64).astype(numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        assert result.dtype == numpy.uint8
    
    def test_composite_clipping(self):
        """Composite should clip values to [0, 255]."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.full((64, 64, 3), 255, dtype=numpy.uint8)
        dirty_swap = numpy.full((64, 64, 3), 255, dtype=numpy.uint8)
        alpha = numpy.ones((64, 64), dtype=numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        assert result.min() >= 0
        assert result.max() <= 255
    
    def test_composite_with_mismatched_shapes(self):
        """Composite should handle mismatched input shapes."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.zeros((64, 64, 3), dtype=numpy.uint8)
        dirty_swap = numpy.ones((128, 128, 3), dtype=numpy.uint8) * 255
        alpha = numpy.random.rand(64, 64).astype(numpy.float32)
        result = handler._composite(original, dirty_swap, alpha)
        assert result.shape == (64, 64, 3)


class TestDepthAlpha:
    """Test depth-based alpha computation."""
    
    def test_depth_threshold_creates_binary_mask(self):
        """Depth threshold should create binary-like mask."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(depth_threshold=0.5, blur_strength=(1, 1))
        depth = numpy.array([[0.3, 0.7], [0.4, 0.8]], dtype=numpy.float32)
        alpha = handler._compute_alpha(depth)
        assert alpha.shape == (2, 2)
        assert alpha[0, 0] < 0.5  # 0.3 < 0.5
        assert alpha[0, 1] > 0.5  # 0.7 > 0.5
    
    def test_depth_alpha_range(self):
        """Alpha from depth should be in [0, 1]."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        depth = numpy.random.rand(64, 64).astype(numpy.float32)
        alpha = handler._compute_alpha(depth)
        assert alpha.min() >= 0
        assert alpha.max() <= 1
    
    def test_depth_alpha_shape(self):
        """Alpha shape should match depth shape."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        depth = numpy.random.rand(100, 100).astype(numpy.float32)
        alpha = handler._compute_alpha(depth)
        assert alpha.shape == (100, 100)
    
    def test_depth_normalized_to_0_1(self):
        """Depth values > 1 should be normalized."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(depth_threshold=0.5, blur_strength=(1, 1))
        depth = numpy.array([[100, 200], [150, 250]], dtype=numpy.float32)
        alpha = handler._compute_alpha(depth)
        assert alpha.shape == (2, 2)
        assert 0 <= alpha.min() <= 1
        assert 0 <= alpha.max() <= 1
    
    def test_depth_threshold_parameter(self):
        """Different thresholds should produce different alphas."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        depth = numpy.array([[0.5, 0.5], [0.5, 0.5]], dtype=numpy.float32)
        
        handler_low = TransparencyHandler(depth_threshold=0.3, blur_strength=(1, 1))
        alpha_low = handler_low._compute_alpha(depth)
        
        handler_high = TransparencyHandler(depth_threshold=0.7, blur_strength=(1, 1))
        alpha_high = handler_high._compute_alpha(depth)
        
        assert alpha_low.mean() > alpha_high.mean()


class TestProcessFrameIntegration:
    """Test full frame processing pipeline."""
    
    def test_process_frame_returns_correct_shape(self):
        """process_frame should return correct shape."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        h, w = 100, 100
        original = numpy.zeros((h, w, 3), dtype=numpy.uint8)
        dirty_swap = numpy.ones((h, w, 3), dtype=numpy.uint8) * 255
        depth_map = numpy.zeros((h, w), dtype=numpy.float32)
        result = handler.process_frame(original, dirty_swap, depth_map)
        assert result.shape == (h, w, 3)
        assert result.dtype == numpy.uint8
    
    def test_process_frame_compositing_formula(self):
        """process_frame should apply compositing formula correctly."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(depth_threshold=0.5, blur_strength=(1, 1))
        h, w = 10, 10
        original = numpy.zeros((h, w, 3), dtype=numpy.uint8)
        dirty_swap = numpy.ones((h, w, 3), dtype=numpy.uint8) * 200
        depth_map = numpy.zeros((h, w), dtype=numpy.float32)
        depth_map[:5, :] = 0.3
        depth_map[5:, :] = 0.7
        result = handler.process_frame(original, dirty_swap, depth_map)
        assert result[:3, :].mean() > 100
        assert result[7:, :].mean() < 100
    
    def test_process_frame_with_random_depth(self):
        """process_frame should handle random depth maps."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        original = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        dirty_swap = numpy.random.randint(0, 255, (64, 64, 3), dtype=numpy.uint8)
        depth_map = numpy.random.rand(64, 64).astype(numpy.float32)
        result = handler.process_frame(original, dirty_swap, depth_map)
        assert result.shape == (64, 64, 3)
        assert result.dtype == numpy.uint8


class TestVideoProcessing:
    """Test video processing with temporal coherence."""
    
    def test_process_video_returns_correct_length(self):
        """process_video should return same number of frames."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        num_frames = 10
        h, w = 50, 50
        frames = [numpy.zeros((h, w, 3), dtype=numpy.uint8) for _ in range(num_frames)]
        dirty_swaps = [numpy.ones((h, w, 3), dtype=numpy.uint8) * 255 for _ in range(num_frames)]
        depth_maps = [numpy.random.rand(h, w).astype(numpy.float32) for _ in range(num_frames)]
        results = handler.process_video(frames, dirty_swaps, depth_maps)
        assert len(results) == num_frames
    
    def test_process_video_validates_lengths(self):
        """process_video should validate input lengths."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        frames = [numpy.zeros((50, 50, 3), dtype=numpy.uint8) for _ in range(5)]
        dirty_swaps = [numpy.zeros((50, 50, 3), dtype=numpy.uint8) for _ in range(3)]
        depth_maps = [numpy.zeros((50, 50), dtype=numpy.float32) for _ in range(5)]
        with pytest.raises(ValueError):
            handler.process_video(frames, dirty_swaps, depth_maps)
    
    def test_process_video_handles_empty_input(self):
        """process_video should handle empty input."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        results = handler.process_video([], [], [])
        assert results == []
    
    def test_process_video_output_dtype(self):
        """process_video output should be uint8."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        num_frames = 5
        h, w = 50, 50
        frames = [numpy.zeros((h, w, 3), dtype=numpy.uint8) for _ in range(num_frames)]
        dirty_swaps = [numpy.ones((h, w, 3), dtype=numpy.uint8) * 255 for _ in range(num_frames)]
        depth_maps = [numpy.random.rand(h, w).astype(numpy.float32) for _ in range(num_frames)]
        results = handler.process_video(frames, dirty_swaps, depth_maps)
        for result in results:
            assert result.dtype == numpy.uint8


class TestTemporalSmoothing:
    """Test temporal smoothing functionality."""
    
    def test_temporal_smoothing_reduces_variance(self):
        """Temporal smoothing should reduce variance."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(temporal_window=5)
        alpha_maps = []
        for i in range(10):
            alpha = numpy.ones((20, 20), dtype=numpy.float32) * (0.3 + 0.4 * (i % 2))
            alpha_maps.append(alpha)
        original_variance = numpy.var([a.mean() for a in alpha_maps])
        smoothed = handler._apply_temporal_smoothing(alpha_maps)
        smoothed_variance = numpy.var([a.mean() for a in smoothed])
        assert smoothed_variance < original_variance
    
    def test_temporal_smoothing_preserves_length(self):
        """Temporal smoothing should preserve frame count."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(temporal_window=3)
        alpha_maps = [numpy.random.rand(20, 20).astype(numpy.float32) for _ in range(10)]
        smoothed = handler._apply_temporal_smoothing(alpha_maps)
        assert len(smoothed) == len(alpha_maps)
    
    def test_temporal_smoothing_single_frame(self):
        """Temporal smoothing should handle single frame."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(temporal_window=5)
        alpha_maps = [numpy.random.rand(20, 20).astype(numpy.float32)]
        smoothed = handler._apply_temporal_smoothing(alpha_maps)
        assert len(smoothed) == 1
        numpy.testing.assert_array_equal(smoothed[0], alpha_maps[0])


class TestHandlerInitialization:
    """Test TransparencyHandler initialization."""
    
    def test_initializes_with_defaults(self):
        """Handler should initialize with default parameters."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        assert handler.depth_threshold == 0.74
        assert handler.blur_strength == (5, 5)
        assert handler.temporal_window == 5
    
    def test_accepts_custom_parameters(self):
        """Handler should accept custom parameters."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler(
            depth_threshold=0.8,
            blur_strength=(7, 7),
            temporal_window=10
        )
        assert handler.depth_threshold == 0.8
        assert handler.blur_strength == (7, 7)
        assert handler.temporal_window == 10
    
    def test_alpha_mode_defaults_to_xseg(self):
        """Handler should default to xseg alpha mode."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        assert handler.alpha_mode == 'xseg'
    
    def test_xseg_threshold_default(self):
        """Handler should have default xseg threshold."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        assert handler.xseg_threshold == 0.5
    
    def test_alpha_blur_default(self):
        """Handler should have default alpha blur."""
        from watserface.processors.modules.transparency_handler import TransparencyHandler
        handler = TransparencyHandler()
        assert handler.alpha_blur == (15, 15)
