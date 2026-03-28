import unittest
from unittest.mock import MagicMock, patch
import watserface.video_manager

class TestVideoManagerLeak(unittest.TestCase):
    def setUp(self):
        # Clear the pool before each test
        watserface.video_manager.VIDEO_POOL_SET.clear()

    def test_video_pool_bounded_behavior(self):
        # Mock cv2.VideoCapture
        with patch('cv2.VideoCapture') as mock_capture_cls:
            # Use side_effect to return a NEW MagicMock for each call
            # This ensures we can track calls on individual instances
            mock_capture_cls.side_effect = lambda x: MagicMock()

            # We want to verify if the pool is bounded to 64
            max_size = 64
            num_items = 70

            # Add more items than the expected bound
            captures = []
            for i in range(num_items):
                path = f"video_{i}.mp4"
                # This calls get_video_capture, which adds to pool if not present
                cap = watserface.video_manager.get_video_capture(path)
                captures.append(cap)

            # Check current size
            current_size = len(watserface.video_manager.VIDEO_POOL_SET)
            print(f"Current pool size: {current_size}")

            # In the buggy version, size should be 70. In fixed version, 64.
            if current_size > max_size:
                print("FAIL: Pool size grew unbounded!")
            else:
                print("PASS: Pool size is bounded.")

            # Check if release() was called on evicted items
            # Items 0 to (num_items - max_size - 1) should have been evicted and released.
            # Items (num_items - max_size) to (num_items - 1) should still be in pool and NOT released.

            evicted_count = num_items - max_size
            release_call_count = 0

            for i in range(num_items):
                 if captures[i].release.called:
                     release_call_count += 1
                     # Verify only the first 'evicted_count' items are released
                     if i >= evicted_count:
                         print(f"WARN: Item {i} (should stay in pool) was released!")

            print(f"Release call count: {release_call_count}")

            # Assertion for final verification
            self.assertLessEqual(current_size, max_size, "Video pool is unbounded")
            self.assertEqual(release_call_count, evicted_count, "Incorrect number of items released")

            # Verify specifically that the OLDEST items were released (FIFO eviction for simple setitem overflow)
            # Since we didn't access them again, they remained at the start of the OrderedDict.
            for i in range(evicted_count):
                self.assertTrue(captures[i].release.called, f"Evicted item {i} was not released")
            for i in range(evicted_count, num_items):
                self.assertFalse(captures[i].release.called, f"Active item {i} was released")

    def test_lru_behavior(self):
        with patch('cv2.VideoCapture') as mock_capture_cls:
            mock_capture_cls.side_effect = lambda x: MagicMock()

            # Max size 3 for easy testing
            original_pool = watserface.video_manager.VIDEO_POOL_SET
            watserface.video_manager.VIDEO_POOL_SET = watserface.video_manager.BoundedVideoPool(maxsize=3)
            try:
                # Add 3 items
                cap0 = watserface.video_manager.get_video_capture("v0")
                cap1 = watserface.video_manager.get_video_capture("v1")
                cap2 = watserface.video_manager.get_video_capture("v2")

                # Pool order: v0, v1, v2 (newest)

                # Access v0 via __getitem__ (should move to end)
                _ = watserface.video_manager.VIDEO_POOL_SET["v0"]

                # Pool order: v1, v2, v0

                # Add v3. Should evict v1 (LRU).
                cap3 = watserface.video_manager.get_video_capture("v3")

                # Check v1 released
                self.assertTrue(cap1.release.called, "Item v1 should have been evicted")
                self.assertFalse(cap0.release.called, "Item v0 should NOT have been evicted (was accessed)")
                self.assertFalse(cap2.release.called, "Item v2 should NOT have been evicted")

                # Access v2 using get_video_capture (which calls .get())
                _ = watserface.video_manager.get_video_capture("v2")
                # Pool order: v0, v3, v2

                # Add v4. Should evict v0.
                cap4 = watserface.video_manager.get_video_capture("v4")

                self.assertTrue(cap0.release.called, "Item v0 should have been evicted")
                self.assertFalse(cap3.release.called, "Item v3 should NOT have been evicted")

            finally:
                watserface.video_manager.VIDEO_POOL_SET = original_pool

if __name__ == '__main__':
    unittest.main()
