from collections import OrderedDict
from unittest.mock import Mock, patch

import pytest
import watserface.video_manager
from watserface.video_manager import BoundedVideoPool, get_video_capture, clear_video_pool

@pytest.fixture
def mock_video_capture():
    with patch('cv2.VideoCapture') as mock:
        yield mock


def test_bounded_video_pool_eviction(mock_video_capture):
    pool = BoundedVideoPool(maxsize=3)
    captures = []

    # Add 3 items
    for i in range(3):
        mock_cap = Mock()
        captures.append(mock_cap)
        pool[f'video_{i}'] = mock_cap

    assert len(pool) == 3

    # Add 4th item, should evict video_0
    mock_cap_3 = Mock()
    pool['video_3'] = mock_cap_3

    assert len(pool) == 3
    assert 'video_0' not in pool
    assert 'video_3' in pool
    captures[0].release.assert_called_once()
    captures[1].release.assert_not_called()


def test_bounded_video_pool_lru_get(mock_video_capture):
    pool = BoundedVideoPool(maxsize=3)

    for i in range(3):
        pool[f'video_{i}'] = Mock()

    # Access video_0 using .get(), making it most recently used
    _ = pool.get('video_0')

    # Add video_3, should evict video_1 (LRU), not video_0
    pool['video_3'] = Mock()

    assert 'video_1' not in pool
    assert 'video_0' in pool


def test_bounded_video_pool_lru_getitem(mock_video_capture):
    pool = BoundedVideoPool(maxsize=3)

    for i in range(3):
        pool[f'video_{i}'] = Mock()

    # Access video_0 using [], making it most recently used
    _ = pool['video_0']

    # Add video_3, should evict video_1 (LRU), not video_0
    pool['video_3'] = Mock()

    assert 'video_1' not in pool
    assert 'video_0' in pool


def test_get_video_capture_integration(mock_video_capture):
    # This tests the integration with the module-level VIDEO_POOL_SET
    # We patch VIDEO_POOL_SET with a BoundedVideoPool instance
    pool = BoundedVideoPool(maxsize=2)

    with patch('watserface.video_manager.VIDEO_POOL_SET', pool):
        cap1 = get_video_capture('video1')
        cap2 = get_video_capture('video2')

        assert cap1 is not None
        assert cap2 is not None
        assert len(pool) == 2

        # Access cap1 again to make it recently used
        _ = get_video_capture('video1')

        # Add 3rd, should evict video2 (since video1 was just used)
        cap3 = get_video_capture('video3')

        assert len(pool) == 2
        assert 'video1' in pool
        assert 'video3' in pool
        assert 'video2' not in pool

        # Verify release was called on the evicted capture (cap2 mock)
        cap2.release.assert_called_once()


def test_clear_video_pool_integration(mock_video_capture):
    pool = BoundedVideoPool(maxsize=3)
    mock_cap = Mock()
    pool['video'] = mock_cap

    with patch('watserface.video_manager.VIDEO_POOL_SET', pool):
        # Call the actual function
        clear_video_pool()

        mock_cap.release.assert_called_once()
        assert len(pool) == 0
