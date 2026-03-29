
import numpy
from watserface.face_helper import create_normal_map, _TRIANGULATION_CACHE

def test_create_normal_map_caching():
    # Clear cache
    _TRIANGULATION_CACHE.clear()

    # Create dummy landmarks (grid)
    rows, cols = 22, 22
    x = numpy.linspace(0, 512, cols)
    y = numpy.linspace(0, 512, rows)
    xv, yv = numpy.meshgrid(x, y)
    points = numpy.stack([xv.flatten(), yv.flatten(), numpy.zeros_like(xv.flatten())], axis=1)
    landmarks = points[:478].astype(numpy.float32)

    # First call - should populate cache
    normal_map1 = create_normal_map(landmarks, (512, 512))
    assert normal_map1.shape == (512, 512, 3)
    assert 'simplices' in _TRIANGULATION_CACHE

    # Capture the cached simplices
    cached_simplices = _TRIANGULATION_CACHE['simplices']

    # Second call - should use cache
    normal_map2 = create_normal_map(landmarks, (512, 512))
    assert numpy.array_equal(normal_map1, normal_map2)

    # Verify cache is preserved
    assert _TRIANGULATION_CACHE['simplices'] is cached_simplices

def test_create_normal_map_empty_input():
    landmarks = numpy.zeros((478, 2), dtype=numpy.float32) # Missing Z
    normal_map = create_normal_map(landmarks, (512, 512)) # type: ignore
    assert numpy.all(normal_map == 0)
