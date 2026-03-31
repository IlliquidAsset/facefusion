import numpy
import pytest
from watserface.face_helper import create_normal_map, _TRIANGULATION_CACHE

def test_create_normal_map_caching() -> None:
    # Clear cache initially
    _TRIANGULATION_CACHE.clear()

    # 1. Create a regular grid of points (478 points)
    # 22x22 = 484. We take first 478.
    x = numpy.linspace(100, 400, 22)
    y = numpy.linspace(100, 400, 22)
    xv, yv = numpy.meshgrid(x, y)
    points_2d = numpy.stack([xv.flatten(), yv.flatten()], axis=1)[:478]
    points_z = numpy.zeros((478, 1)) # Flat face
    landmarks = numpy.hstack([points_2d, points_z])

    size = (512, 512)

    # 2. First call: should compute and cache
    normal_map_1 = create_normal_map(landmarks, size)

    assert normal_map_1.shape == (512, 512, 3)
    assert numpy.any(normal_map_1 > 0) # Should have content

    # Check if cached
    assert len(landmarks) in _TRIANGULATION_CACHE
    cached_simplices = _TRIANGULATION_CACHE[len(landmarks)]
    assert isinstance(cached_simplices, numpy.ndarray)

    # 3. Second call: should use cache
    normal_map_2 = create_normal_map(landmarks, size)

    assert numpy.array_equal(normal_map_1, normal_map_2)
