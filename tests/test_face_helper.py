
import unittest
import numpy
from watserface.face_helper import create_normal_map, _TRIANGULATION_CACHE

class TestFaceHelper(unittest.TestCase):
    def setUp(self):
        _TRIANGULATION_CACHE.clear()

    def test_create_normal_map_caching(self):
        # Create grid landmarks
        w = 22
        h = 22
        x = numpy.linspace(0, 1, w)
        y = numpy.linspace(0, 1, h)
        xv, yv = numpy.meshgrid(x, y)
        points_2d = numpy.stack([xv.ravel(), yv.ravel()], axis=-1)[:478]
        points_z = numpy.zeros((478, 1))
        landmarks = numpy.hstack([points_2d, points_z]).astype(numpy.float64)
        size = (128, 128)

        # First call
        result1 = create_normal_map(landmarks, size)
        self.assertEqual(result1.shape, (128, 128, 3))
        self.assertTrue(numpy.any(result1))
        self.assertIn(478, _TRIANGULATION_CACHE)

        # Capture the cached value
        cached_simplices = _TRIANGULATION_CACHE[478]

        # Second call
        result2 = create_normal_map(landmarks, size)

        # Verify result is same
        numpy.testing.assert_array_equal(result1, result2)

        # Verify cache is still the same object
        self.assertIs(_TRIANGULATION_CACHE[478], cached_simplices)

    def test_create_normal_map_invalid_topology(self):
        # Create landmarks that are very spread out / bad topology for validity check
        # "max edge length < 0.5 * span"
        # We can force a fail by having two clusters very far apart.

        # Cluster 1
        c1 = numpy.random.rand(239, 2) * 0.1
        # Cluster 2 far away
        c2 = numpy.random.rand(239, 2) * 0.1 + [10, 10]

        points_2d = numpy.vstack([c1, c2])
        points_z = numpy.zeros((478, 1))
        landmarks = numpy.hstack([points_2d, points_z]).astype(numpy.float64)

        # Span is ~10.
        # Delaunay will bridge the gap. Edge length ~14.
        # 14 > 0.5 * 10 (5). Should fail caching.

        _TRIANGULATION_CACHE.clear()
        create_normal_map(landmarks, (128, 128))

        self.assertNotIn(478, _TRIANGULATION_CACHE)

if __name__ == '__main__':
    unittest.main()
