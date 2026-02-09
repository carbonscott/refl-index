"""refl-index: Sidecar index for DIALS .refl msgpack files."""

from .dtypes import DIALS_TYPES
from .indexer import ColumnInfo, ReflIndex

__all__ = ["ReflIndex", "ColumnInfo", "DIALS_TYPES"]

# ReflReader is imported lazily since it requires numpy
def __getattr__(name):
    if name == "ReflReader":
        from .reader import ReflReader
        return ReflReader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
