"""Golden reference images and data."""

from .comparator import ComparisonResult, GoldenComparator
from .registry import GoldenEntry, GoldenRegistry

__all__ = [
	'GoldenEntry',
	'GoldenRegistry',
	'GoldenComparator',
	'ComparisonResult',
]
