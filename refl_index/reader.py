"""ReflReader: seek-based column access returning numpy arrays."""

from pathlib import Path

from .dtypes import numpy_dtype, numpy_shape
from .indexer import ColumnInfo, ReflIndex


class ReflReader:
    """Read columns from a .refl file using a pre-built index.

    Uses file.seek() to jump directly to the requested column's binary
    blob, avoiding full-file parsing. Requires numpy.
    """

    def __init__(self, index: ReflIndex, refl_path: str | Path | None = None):
        try:
            import numpy as np
            self._np = np
        except ImportError:
            raise ImportError("numpy is required for ReflReader. Install with: pip install refl-index[numpy]")

        self._index = index
        self._refl_path = Path(refl_path) if refl_path else Path(index.refl_path)

    def read_column(
        self,
        name: str,
        start: int = 0,
        stop: int | None = None,
    ):
        """Read a column (or row slice) as a numpy array.

        Args:
            name: Column name.
            start: First row to read (default 0).
            stop: One past the last row (default: all rows).

        Returns:
            numpy.ndarray with appropriate dtype and shape.
        """
        np = self._np
        col = self._get_column(name)

        if stop is None:
            stop = col.count
        self._validate_range(col, start, stop)

        nrows = stop - start
        if nrows == 0:
            dtype = numpy_dtype(col.type_str)
            shape = numpy_shape(col.type_str, 0)
            return np.empty(shape, dtype=dtype)

        byte_offset = col.blob_offset + start * col.elem_size
        byte_count = nrows * col.elem_size

        with open(self._refl_path, "rb") as f:
            f.seek(byte_offset)
            raw = f.read(byte_count)

        if len(raw) != byte_count:
            raise IOError(
                f"Short read for column {name!r}: expected {byte_count} bytes, got {len(raw)}"
            )

        dtype = numpy_dtype(col.type_str)
        arr = np.frombuffer(raw, dtype=dtype)
        shape = numpy_shape(col.type_str, nrows)
        return arr.reshape(shape)

    def read_columns(
        self,
        names: list[str],
        start: int = 0,
        stop: int | None = None,
    ) -> dict:
        """Read multiple columns as a dict of numpy arrays."""
        return {name: self.read_column(name, start, stop) for name in names}

    def read_column_raw(
        self,
        name: str,
        start: int = 0,
        stop: int | None = None,
    ) -> bytes:
        """Read raw bytes for a column (or row slice), without numpy."""
        col = self._get_column(name)

        if stop is None:
            stop = col.count
        self._validate_range(col, start, stop)

        nrows = stop - start
        if nrows == 0:
            return b""

        byte_offset = col.blob_offset + start * col.elem_size
        byte_count = nrows * col.elem_size

        with open(self._refl_path, "rb") as f:
            f.seek(byte_offset)
            raw = f.read(byte_count)

        if len(raw) != byte_count:
            raise IOError(
                f"Short read for column {name!r}: expected {byte_count} bytes, got {len(raw)}"
            )
        return raw

    def _get_column(self, name: str) -> ColumnInfo:
        if name not in self._index:
            available = ", ".join(self._index.column_names)
            raise KeyError(f"Column {name!r} not found. Available: {available}")
        return self._index[name]

    @staticmethod
    def _validate_range(col: ColumnInfo, start: int, stop: int):
        if start < 0 or stop < 0:
            raise ValueError(f"start and stop must be non-negative (got start={start}, stop={stop})")
        if start > stop:
            raise ValueError(f"start ({start}) must be <= stop ({stop})")
        if stop > col.count:
            raise IndexError(
                f"stop ({stop}) exceeds row count ({col.count}) for column {col.name!r}"
            )
