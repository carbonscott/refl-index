"""DIALS reflection type → (element_size, numpy_dtype, description) mapping."""

# Each entry: (bytes_per_element, numpy_dtype_string, description)
DIALS_TYPES = {
    "double":                (8,  "<f8", "64-bit float"),
    "int":                   (4,  "<i4", "32-bit signed int"),
    "bool":                  (1,  "?",   "boolean"),
    "std::size_t":           (8,  "<u8", "64-bit unsigned int"),
    "int6":                  (24, "<i4", "6 x 32-bit int (e.g. shoebox bounding box)"),
    "vec3<double>":          (24, "<f8", "3 x 64-bit float"),
    "cctbx::miller::index<>": (12, "<i4", "3 x 32-bit int (Miller index)"),
}

# Number of sub-elements per row for multi-element types
_MULTI_ELEMENT_COUNTS = {
    "int6": 6,
    "vec3<double>": 3,
    "cctbx::miller::index<>": 3,
}


def element_size(type_str: str) -> int:
    """Return byte size of one row for a DIALS type string."""
    if type_str not in DIALS_TYPES:
        raise ValueError(f"Unknown DIALS type: {type_str!r}")
    return DIALS_TYPES[type_str][0]


def numpy_dtype(type_str: str) -> str:
    """Return numpy dtype string for a DIALS type string."""
    if type_str not in DIALS_TYPES:
        raise ValueError(f"Unknown DIALS type: {type_str!r}")
    return DIALS_TYPES[type_str][1]


def numpy_shape(type_str: str, nrows: int) -> tuple:
    """Return the numpy array shape for a column with nrows rows.

    Multi-element types (vec3, int6, miller) return 2D shapes like (nrows, 3).
    """
    if type_str not in DIALS_TYPES:
        raise ValueError(f"Unknown DIALS type: {type_str!r}")
    sub = _MULTI_ELEMENT_COUNTS.get(type_str)
    if sub is not None:
        return (nrows, sub)
    return (nrows,)
