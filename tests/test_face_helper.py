import numpy

from watserface.face_helper import _TRIANGULATION_CACHE, create_normal_map


def test_create_normal_map_caching() -> None:
	# Clear cache
	_TRIANGULATION_CACHE.clear()

	# Create dummy landmarks (478 points)
	# Use a grid to ensure validity check passes (max edge < 0.5 span)
	# A grid of 22x22 is 484 points. We can take first 478.
	y, x = numpy.mgrid[0:1:22j, 0:1:22j]
	points = numpy.stack([x.ravel(), y.ravel()], axis=-1)
	points = points[:478]
	# Add Z coordinate
	points = numpy.hstack([points, numpy.zeros((478, 1))])

	landmarks = points.astype(numpy.float32) * 512
	size = (512, 512)

	# First call
	assert len(_TRIANGULATION_CACHE) == 0
	create_normal_map(landmarks, size)

	# Should be cached
	assert 478 in _TRIANGULATION_CACHE
	simplices = _TRIANGULATION_CACHE[478]
	assert simplices is not None

	# Second call
	create_normal_map(landmarks, size)
	# Cache should stay same
	assert _TRIANGULATION_CACHE[478] is simplices
