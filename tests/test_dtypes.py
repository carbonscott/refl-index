"""Tests for refl_index.dtypes."""

import numpy as np
import pytest

from refl_index.dtypes import (
    DIALS_TYPES,
    element_size,
    numpy_dtype,
    numpy_shape,
)


def test_all_seven_types_present():
    expected = {
        "double", "int", "bool", "std::size_t",
        "int6", "vec3<double>", "cctbx::miller::index<>",
    }
    assert set(DIALS_TYPES.keys()) == expected


def test_element_sizes():
    assert element_size("double") == 8
    assert element_size("int") == 4
    assert element_size("bool") == 1
    assert element_size("std::size_t") == 8
    assert element_size("int6") == 24
    assert element_size("vec3<double>") == 24
    assert element_size("cctbx::miller::index<>") == 12


def test_numpy_dtypes_are_valid():
    for type_str in DIALS_TYPES:
        dt = numpy_dtype(type_str)
        # Should be a valid numpy dtype
        np.dtype(dt)


def test_numpy_shape_scalar_types():
    assert numpy_shape("double", 100) == (100,)
    assert numpy_shape("int", 50) == (50,)
    assert numpy_shape("bool", 10) == (10,)
    assert numpy_shape("std::size_t", 5) == (5,)


def test_numpy_shape_multi_element_types():
    assert numpy_shape("vec3<double>", 100) == (100, 3)
    assert numpy_shape("int6", 100) == (100, 6)
    assert numpy_shape("cctbx::miller::index<>", 100) == (100, 3)


def test_numpy_shape_zero_rows():
    assert numpy_shape("double", 0) == (0,)
    assert numpy_shape("vec3<double>", 0) == (0, 3)


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="Unknown DIALS type"):
        element_size("float")
    with pytest.raises(ValueError, match="Unknown DIALS type"):
        numpy_dtype("uint32")
    with pytest.raises(ValueError, match="Unknown DIALS type"):
        numpy_shape("complex", 10)
