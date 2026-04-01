from unittest.mock import Mock, patch

from watserface import video_manager


def test_video_pool_bounded() -> None:
    video_manager.clear_video_pool()
    with patch("cv2.VideoCapture") as mock_capture:
        # Configure mock to have a release method
        mock_instance = Mock()
        mock_capture.return_value = mock_instance

        for i in range(100):
            video_manager.get_video_capture(f"test_{i}.mp4")

        assert len(video_manager.VIDEO_POOL_SET) == 64
        # Verify that release was called (100 - 64 = 36 times)
        assert mock_instance.release.call_count == 36
