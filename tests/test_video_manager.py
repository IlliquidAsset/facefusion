from unittest.mock import MagicMock, patch
from watserface import video_manager

def test_video_pool_memory_leak() -> None:
    # Clear the pool initially
    video_manager.VIDEO_POOL_SET.clear()

    captures = []

    # Side effect to return a new mock for each call and store it
    def create_capture(path):
        m = MagicMock()
        m.path = path
        captures.append(m)
        return m

    # Patch cv2.VideoCapture where it is used in video_manager
    with patch('watserface.video_manager.cv2.VideoCapture', side_effect=create_capture):
        # Add 100 items
        for i in range(100):
            video_manager.get_video_capture(f"video_{i}.mp4")

        # Check if pool size is bounded (should be <= 64)
        assert len(video_manager.VIDEO_POOL_SET) <= 64

        # Check if evicted items were released
        evicted_count = 100 - 64
        if evicted_count > 0:
            for i in range(evicted_count):
                captures[i].release.assert_called()
