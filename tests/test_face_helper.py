
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import scipy.spatial
import cv2
import sys

# Mock imports if needed, but face_helper depends on opencv and numpy which are installed
# We need to make sure watserface can be imported
sys.path.append('.')

from watserface.face_helper import create_normal_map

class TestFaceHelper(unittest.TestCase):
    def setUp(self):
        # Reset cache if exposed, otherwise we might need to reload module
        # But for now, let's assume we can access it or it's empty initially
        pass

    def test_create_normal_map_caching(self):
        # We need to access the cache dictionary to clear it
        import watserface.face_helper
        if hasattr(watserface.face_helper, '_TRIANGULATION_CACHE'):
            watserface.face_helper._TRIANGULATION_CACHE.clear()

        # Create synthetic landmarks (grid)
        # 478 points
        # We need a grid that is roughly square to avoid long skinny triangles
        # sqrt(478) ~ 21.8
        y, x = np.mgrid[0:22, 0:22] # 22x22 = 484
        grid = np.stack((x.ravel(), y.ravel()), axis=1).astype(np.float32)
        landmarks = np.zeros((478, 3), dtype=np.float32)
        landmarks[:, :2] = grid[:478] * 10 # Scale to 220x220
        landmarks[:, 2] = np.random.rand(478) # Random Z

        size = (512, 512)

        # We patch scipy.spatial.Delaunay to count calls
        with patch('scipy.spatial.Delaunay', side_effect=scipy.spatial.Delaunay) as mock_delaunay:
            # First call
            result1 = create_normal_map(landmarks, size)

            # Assert result is valid (not empty)
            self.assertTrue(np.any(result1), "Result should not be empty")
            self.assertEqual(result1.shape, (512, 512, 3))

            # Assert Delaunay was called
            # Note: create_normal_map calls Delaunay internally
            # If not cached, call_count should be 1
            # If implementation doesn't cache yet, this test will fail on the assertion below if we expect caching
            # But we are WRITING the test to verify the optimization.

            # Second call
            result2 = create_normal_map(landmarks, size)

            # If cached, call_count should remain the same (1)
            # If not cached, it will be 2

            # Assert cache is working (call count should be 1)
            self.assertEqual(mock_delaunay.call_count, 1, "Delaunay should be called only once due to caching")

if __name__ == '__main__':
    unittest.main()
