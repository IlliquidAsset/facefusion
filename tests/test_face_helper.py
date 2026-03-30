
import numpy
import scipy.spatial
from unittest.mock import patch
import watserface.face_helper
from watserface.face_helper import create_normal_map

def setup_function():
    # Clear the cache before each test
    watserface.face_helper._TRIANGULATION_CACHE.clear()

def test_create_normal_map_caching():
    # Create valid synthetic landmarks (grid)
    rows = 22
    cols = 22
    points = []
    for y in range(rows):
        for x in range(cols):
            points.append([float(x * 10), float(y * 10), 0.0])

    # Pad to 478
    while len(points) < 478:
        points.append([0.0, 0.0, 0.0])

    landmarks = numpy.array(points[:478], dtype=numpy.float32)
    size = (512, 512)

    with patch('scipy.spatial.Delaunay', side_effect=scipy.spatial.Delaunay) as mock_delaunay:
        # First call - should trigger Delaunay
        result1 = create_normal_map(landmarks, size)
        assert mock_delaunay.call_count == 1
        assert numpy.any(result1)

        # Second call - should use cache
        create_normal_map(landmarks, size)
        assert mock_delaunay.call_count == 1

def test_create_normal_map_invalid_topology():
    # Create invalid synthetic landmarks
    rows = 22
    cols = 22
    points = []
    for y in range(rows):
        for x in range(cols):
            points.append([float(x * 10), float(y * 10), 0.0])

    # Distort one point to be extremely far
    points[0] = [10000.0, 10000.0, 0.0]

    while len(points) < 478:
        points.append([0.0, 0.0, 0.0])

    landmarks = numpy.array(points[:478], dtype=numpy.float32)
    size = (512, 512)

    with patch('scipy.spatial.Delaunay', side_effect=scipy.spatial.Delaunay) as mock_delaunay:
        # First call - invalid, should NOT cache
        create_normal_map(landmarks, size)
        assert mock_delaunay.call_count == 1

        # Second call - invalid, should trigger Delaunay again
        create_normal_map(landmarks, size)
        assert mock_delaunay.call_count == 2
