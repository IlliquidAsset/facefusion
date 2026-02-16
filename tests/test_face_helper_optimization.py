import numpy
import pytest
from watserface.face_helper import create_normal_map, _TRIANGULATION_CACHE

def generate_grid_points(n_points=478, size=(512, 512)):
    # Create a regular grid to ensure Delaunay triangles are small (like a face mesh)
    side = int(numpy.ceil(numpy.sqrt(n_points)))
    x = numpy.linspace(0, size[0], side)
    y = numpy.linspace(0, size[1], side)
    xv, yv = numpy.meshgrid(x, y)
    points = numpy.stack([xv.flatten(), yv.flatten(), numpy.zeros_like(xv.flatten())], axis=1)
    points = points[:n_points].astype(numpy.float32)
    return points

def test_create_normal_map_caching():
    # Clear cache to start fresh
    _TRIANGULATION_CACHE.clear()

    # Mock data 1: Regular grid (simulating a valid face mesh structure)
    size = (512, 512)
    points1 = generate_grid_points(478, size)

    # First call: Should compute and cache
    res1 = create_normal_map(points1, size)
    assert res1.shape == (512, 512, 3)
    assert 478 in _TRIANGULATION_CACHE
    assert len(_TRIANGULATION_CACHE[478]) == 1
    simplices1 = _TRIANGULATION_CACHE[478][0]

    # Second call (same points): Should hit cache (same object)
    res2 = create_normal_map(points1, size)
    assert len(_TRIANGULATION_CACHE[478]) == 1
    assert _TRIANGULATION_CACHE[478][0] is simplices1

    # Mock data 2: Random points (simulating a completely different/distorted distribution)
    # Random points often have large gaps, causing large Delaunay edges,
    # which should fail the "0.5 * span" validity check when applied to a grid topology.
    # Wait, if we pass random points, we check if EXISTING cache (grid topology) fits random points.
    # Grid topology on random points -> VERY long edges. Should fail.
    numpy.random.seed(42)
    points2 = numpy.random.rand(478, 3).astype(numpy.float32) * 512

    # Third call: Should miss cache (validity check), compute new, and add to cache
    res3 = create_normal_map(points2, size)

    # Cache should now have 2 entries
    # The new entry (for random points) might or might not pass its OWN validity check?
    # No, we compute Delaunay on points2. The result is cached.
    # Does the self-check pass?
    # As seen in debug, random points might create large edges in their OWN Delaunay.
    # But `create_normal_map` logic:
    # 1. Check candidates. If one works, use it.
    # 2. If none work, compute new, insert to cache.
    # It doesn't check if the NEW one satisfies the heuristic (it assumes Delaunay is optimal).
    # The heuristic is only for REUSE.

    assert len(_TRIANGULATION_CACHE[478]) == 2
    simplices2 = _TRIANGULATION_CACHE[478][0]
    assert simplices2 is not simplices1

    # Fourth call: Go back to points1. Should find simplices1 in cache list.
    res4 = create_normal_map(points1, size)

    # Should maintain size 2
    assert len(_TRIANGULATION_CACHE[478]) == 2
    # Should bring simplices1 to front (LRU)
    assert _TRIANGULATION_CACHE[478][0] is simplices1

    # Validate result is not empty
    assert numpy.any(res4 > 0)

def test_create_normal_map_cache_limit():
    _TRIANGULATION_CACHE.clear()
    size = (512, 512)

    # Create 4 different sets of grid points (shifted)
    # Use grid to ensures they are "valid" faces if we were to check
    # But here we want them to be different enough to cause cache misses.
    # Grid vs Grid shifted? Topology might be compatible actually (just stretched).
    # We need incompatible topologies.
    # Use random points to force incompatibility.

    points_list = []
    for i in range(4):
        # Use different seeds
        numpy.random.seed(i)
        p = numpy.random.rand(478, 3).astype(numpy.float32) * 512
        points_list.append(p)
        create_normal_map(p, size)

    # Limit is 3. So size should be 3.
    assert len(_TRIANGULATION_CACHE[478]) == 3
