"""Fixtures for creating synthetic .refl files."""

import struct
from pathlib import Path

import msgpack
import numpy as np
import pytest


def make_synthetic_refl(
    path: Path,
    nrows: int = 100,
    columns: dict | None = None,
    num_identifiers: int = 3,
) -> dict:
    """Create a synthetic .refl file and return the packed column data for verification.

    Args:
        path: Output file path.
        nrows: Number of rows per column.
        columns: Dict of {name: type_str}. If None, uses a default set.
        num_identifiers: Number of identifier entries.

    Returns:
        Dict mapping column name → numpy array of the packed data.
    """
    if columns is None:
        columns = {
            "intensity.sum.value": "double",
            "flags": "int",
            "is_strong": "bool",
            "imageset_id": "std::size_t",
            "bbox": "int6",
            "xyzcal.px": "vec3<double>",
            "miller_index": "cctbx::miller::index<>",
        }

    rng = np.random.default_rng(42)

    # Type → (numpy_dtype, elem_size, sub_elements)
    type_info = {
        "double":                ("<f8", 8,  1),
        "int":                   ("<i4", 4,  1),
        "bool":                  ("?",   1,  1),
        "std::size_t":           ("<u8", 8,  1),
        "int6":                  ("<i4", 24, 6),
        "vec3<double>":          ("<f8", 24, 3),
        "cctbx::miller::index<>": ("<i4", 12, 3),
    }

    # Generate data for each column
    col_arrays = {}
    for col_name, type_str in columns.items():
        dtype_str, elem_size, sub_elems = type_info[type_str]
        if type_str == "bool":
            arr = rng.choice([True, False], size=nrows).astype("?")
        elif type_str == "double":
            arr = rng.standard_normal(nrows).astype("<f8")
        elif type_str == "vec3<double>":
            arr = rng.standard_normal((nrows, 3)).astype("<f8")
        elif type_str in ("int", "cctbx::miller::index<>"):
            shape = (nrows, sub_elems) if sub_elems > 1 else (nrows,)
            arr = rng.integers(-100, 100, size=shape, dtype="<i4")
        elif type_str == "int6":
            arr = rng.integers(-100, 100, size=(nrows, 6), dtype="<i4")
        elif type_str == "std::size_t":
            arr = rng.integers(0, 1000, size=nrows, dtype="<u8")
        else:
            raise ValueError(f"Unknown type: {type_str}")
        col_arrays[col_name] = arr

    # Pack using msgpack
    packer = msgpack.Packer()

    with open(path, "wb") as f:
        # Outer array of 3
        f.write(packer.pack_array_header(3))
        # Magic
        f.write(packer.pack(b"dials::af::reflection_table"))
        # Version
        f.write(packer.pack(1))
        # Main map
        f.write(packer.pack_map_header(3))

        # identifiers
        f.write(packer.pack("identifiers"))
        f.write(packer.pack_map_header(num_identifiers))
        for i in range(num_identifiers):
            f.write(packer.pack(i))
            f.write(packer.pack(f"uuid-{i:04d}"))

        # nrows
        f.write(packer.pack("nrows"))
        f.write(packer.pack(nrows))

        # data
        f.write(packer.pack("data"))
        f.write(packer.pack_map_header(len(columns)))

        for col_name, type_str in columns.items():
            arr = col_arrays[col_name]
            raw_bytes = arr.tobytes()

            f.write(packer.pack(col_name))
            # [type_str, [count, raw_blob]]
            f.write(packer.pack_array_header(2))
            f.write(packer.pack(type_str))
            f.write(packer.pack_array_header(2))
            f.write(packer.pack(nrows))
            # Pack raw blob as bin
            f.write(packer.pack(raw_bytes))

    return col_arrays


@pytest.fixture
def synthetic_refl(tmp_path):
    """Create a synthetic .refl file and return (path, col_arrays)."""
    path = tmp_path / "test.refl"
    col_arrays = make_synthetic_refl(path)
    return path, col_arrays


@pytest.fixture
def synthetic_refl_small(tmp_path):
    """Create a small synthetic .refl file with just 10 rows."""
    path = tmp_path / "small.refl"
    col_arrays = make_synthetic_refl(path, nrows=10)
    return path, col_arrays
