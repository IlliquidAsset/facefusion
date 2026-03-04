
import numpy
import pytest
from watserface.face_helper import create_tps_grid

def test_create_tps_grid_caching():
    target_width = 512
    target_height = 512

    # First call
    grid1 = create_tps_grid(target_width, target_height)

    # Second call
    grid2 = create_tps_grid(target_width, target_height)

    # Check if they are the same object (caching working)
    assert grid1 is grid2

    # Check shape
    assert grid1.shape == (target_width * target_height, 2)

    # Check content roughly
    assert numpy.all(grid1 >= 0)
    assert numpy.all(grid1 <= 1)

    # Check read-only
    with pytest.raises(ValueError):
        grid1[0, 0] = 99.0

def test_create_tps_grid_different_size():
    grid1 = create_tps_grid(100, 100)
    grid2 = create_tps_grid(200, 200)

    assert grid1 is not grid2
    assert grid1.shape == (100 * 100, 2)
    assert grid2.shape == (200 * 200, 2)
