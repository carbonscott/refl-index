"""Tests for refl_index.reader."""

import numpy as np
import pytest

from refl_index.indexer import ReflIndex
from refl_index.reader import ReflReader


class TestReadColumn:
    def test_read_double(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("intensity.sum.value")
        np.testing.assert_array_equal(arr, col_arrays["intensity.sum.value"])
        assert arr.dtype == np.dtype("<f8")
        assert arr.shape == (100,)

    def test_read_int(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("flags")
        np.testing.assert_array_equal(arr, col_arrays["flags"])
        assert arr.dtype == np.dtype("<i4")
        assert arr.shape == (100,)

    def test_read_bool(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("is_strong")
        np.testing.assert_array_equal(arr, col_arrays["is_strong"])
        assert arr.dtype == np.dtype("?")
        assert arr.shape == (100,)

    def test_read_size_t(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("imageset_id")
        np.testing.assert_array_equal(arr, col_arrays["imageset_id"])
        assert arr.dtype == np.dtype("<u8")

    def test_read_miller_index(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("miller_index")
        np.testing.assert_array_equal(arr, col_arrays["miller_index"])
        assert arr.dtype == np.dtype("<i4")
        assert arr.shape == (100, 3)

    def test_read_vec3(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("xyzcal.px")
        np.testing.assert_array_equal(arr, col_arrays["xyzcal.px"])
        assert arr.dtype == np.dtype("<f8")
        assert arr.shape == (100, 3)

    def test_read_int6(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("bbox")
        np.testing.assert_array_equal(arr, col_arrays["bbox"])
        assert arr.dtype == np.dtype("<i4")
        assert arr.shape == (100, 6)


class TestRowSlicing:
    def test_start_stop(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("intensity.sum.value", start=10, stop=20)
        expected = col_arrays["intensity.sum.value"][10:20]
        np.testing.assert_array_equal(arr, expected)
        assert arr.shape == (10,)

    def test_start_only(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("intensity.sum.value", start=90)
        expected = col_arrays["intensity.sum.value"][90:]
        np.testing.assert_array_equal(arr, expected)
        assert arr.shape == (10,)

    def test_single_row(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("intensity.sum.value", start=42, stop=43)
        expected = col_arrays["intensity.sum.value"][42:43]
        np.testing.assert_array_equal(arr, expected)

    def test_zero_rows(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("intensity.sum.value", start=50, stop=50)
        assert arr.shape == (0,)

    def test_slicing_multi_element(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        arr = reader.read_column("miller_index", start=5, stop=15)
        expected = col_arrays["miller_index"][5:15]
        np.testing.assert_array_equal(arr, expected)
        assert arr.shape == (10, 3)


class TestReadColumns:
    def test_read_multiple(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        result = reader.read_columns(["intensity.sum.value", "flags"])
        assert set(result.keys()) == {"intensity.sum.value", "flags"}
        np.testing.assert_array_equal(result["intensity.sum.value"], col_arrays["intensity.sum.value"])
        np.testing.assert_array_equal(result["flags"], col_arrays["flags"])

    def test_read_columns_with_slice(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        result = reader.read_columns(["intensity.sum.value", "miller_index"], start=0, stop=10)
        assert result["intensity.sum.value"].shape == (10,)
        assert result["miller_index"].shape == (10, 3)


class TestReadColumnRaw:
    def test_raw_bytes(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        raw = reader.read_column_raw("intensity.sum.value")
        expected = col_arrays["intensity.sum.value"].tobytes()
        assert raw == expected

    def test_raw_slice(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        raw = reader.read_column_raw("intensity.sum.value", start=10, stop=20)
        expected = col_arrays["intensity.sum.value"][10:20].tobytes()
        assert raw == expected


class TestErrors:
    def test_missing_column(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        with pytest.raises(KeyError, match="nonexistent"):
            reader.read_column("nonexistent")

    def test_out_of_range(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        with pytest.raises(IndexError, match="exceeds row count"):
            reader.read_column("intensity.sum.value", stop=200)

    def test_negative_start(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        with pytest.raises(ValueError, match="non-negative"):
            reader.read_column("intensity.sum.value", start=-1)

    def test_start_greater_than_stop(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        reader = ReflReader(index)

        with pytest.raises(ValueError, match="must be <= stop"):
            reader.read_column("intensity.sum.value", start=50, stop=10)
