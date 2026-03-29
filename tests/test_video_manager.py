from unittest.mock import Mock, patch

# Ensure cv2 is mocked if not available, though we have opencv-python-headless
# But the key is to patch it inside video_manager

from watserface import video_manager


@patch("watserface.video_manager.cv2.VideoCapture")
def test_video_pool_bound_and_eviction(mock_video_capture):
    """
    Test that the video pool is bounded and releases resources upon eviction.
    """
    # Setup
    mock_captures = {}

    def create_mock_capture(path):
        m = Mock()
        m.path = path  # for debugging
        mock_captures[path] = m
        return m

    mock_video_capture.side_effect = create_mock_capture

    # Reset pool explicitly
    video_manager.clear_video_pool()
    # If VIDEO_POOL_SET is replaced by BoundedVideoPool, clear() works too.
    # But if it is a dict, clear() empties it.

    # We suspect the limit will be 64.
    limit = 64

    # Add items beyond limit
    for i in range(limit + 5):
        video_manager.get_video_capture(f"video_{i}.mp4")

    # Assertion 1: Pool should be bounded
    # Note: If this fails with the current code, it confirms the bug.
    assert (
        len(video_manager.VIDEO_POOL_SET) <= limit
    ), f"Pool size {len(video_manager.VIDEO_POOL_SET)} exceeded limit {limit}"

    # Assertion 2: Evicted items (video_0.mp4 to video_4.mp4) should be released
    for i in range(5):
        path = f"video_{i}.mp4"
        assert path not in video_manager.VIDEO_POOL_SET
        # The mock instance for this path should have had release() called
        mock_captures[path].release.assert_called_once()

    # Assertion 3: Recent items should be present and NOT released
    for i in range(5, limit + 5):
        path = f"video_{i}.mp4"
        assert path in video_manager.VIDEO_POOL_SET
        mock_captures[path].release.assert_not_called()


@patch("watserface.video_manager.cv2.VideoCapture")
def test_video_pool_lru_behavior(mock_video_capture):
    """
    Test that accessing an existing item moves it to the end (LRU).
    """
    video_manager.clear_video_pool()
    limit = 64

    # Fill pool up to limit
    for i in range(limit):
        video_manager.get_video_capture(f"video_{i}.mp4")

    # Access the first item (video_0) again, making it most recently used
    video_manager.get_video_capture("video_0.mp4")

    # Add one more item (video_64), which should trigger eviction
    # Since video_0 was just used, video_1 should be evicted instead of video_0
    video_manager.get_video_capture(f"video_{limit}.mp4")

    assert "video_0.mp4" in video_manager.VIDEO_POOL_SET
    assert "video_1.mp4" not in video_manager.VIDEO_POOL_SET
    assert f"video_{limit}.mp4" in video_manager.VIDEO_POOL_SET
