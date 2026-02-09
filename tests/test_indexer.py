"""Tests for refl_index.indexer."""

import json
from pathlib import Path

import numpy as np
import pytest

from refl_index.dtypes import element_size
from refl_index.indexer import ReflIndex


class TestBuild:
    def test_basic_build(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        assert index.nrows == 100
        assert index.num_identifiers == 3
        assert len(index.columns) == 7

    def test_column_names(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        expected_names = set(col_arrays.keys())
        assert set(index.column_names) == expected_names

    def test_column_info_types(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        assert index["intensity.sum.value"].type_str == "double"
        assert index["flags"].type_str == "int"
        assert index["is_strong"].type_str == "bool"
        assert index["imageset_id"].type_str == "std::size_t"
        assert index["bbox"].type_str == "int6"
        assert index["xyzcal.px"].type_str == "vec3<double>"
        assert index["miller_index"].type_str == "cctbx::miller::index<>"

    def test_column_counts(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        for col in index.columns:
            assert col.count == 100

    def test_column_elem_sizes(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        for col in index.columns:
            assert col.elem_size == element_size(col.type_str)

    def test_blob_sizes(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        for col in index.columns:
            assert col.blob_size == col.elem_size * col.count

    def test_offsets_point_to_correct_data(self, synthetic_refl):
        """Verify that recorded offsets allow reading back the original data."""
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)

        with open(path, "rb") as f:
            for col in index.columns:
                f.seek(col.blob_offset)
                raw = f.read(col.blob_size)
                assert len(raw) == col.blob_size

                # Compare against the original numpy data
                arr = col_arrays[col.name]
                assert raw == arr.tobytes()

    def test_file_size(self, synthetic_refl):
        path, col_arrays = synthetic_refl
        index = ReflIndex.build(path)
        assert index.file_size == path.stat().st_size

    def test_contains(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        assert "intensity.sum.value" in index
        assert "nonexistent" not in index


class TestSaveLoad:
    def test_roundtrip(self, synthetic_refl, tmp_path):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)

        idx_path = tmp_path / "test.refl.idx"
        index.save(idx_path)

        loaded = ReflIndex.load(idx_path)

        assert loaded.refl_path == index.refl_path
        assert loaded.file_size == index.file_size
        assert loaded.nrows == index.nrows
        assert loaded.num_identifiers == index.num_identifiers
        assert len(loaded.columns) == len(index.columns)

        for orig, loaded_col in zip(index.columns, loaded.columns):
            assert loaded_col.name == orig.name
            assert loaded_col.type_str == orig.type_str
            assert loaded_col.elem_size == orig.elem_size
            assert loaded_col.count == orig.count
            assert loaded_col.blob_offset == orig.blob_offset
            assert loaded_col.blob_size == orig.blob_size

    def test_default_save_path(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        saved = index.save()
        assert saved == Path(str(path) + ".idx")
        assert saved.exists()

    def test_json_format(self, synthetic_refl, tmp_path):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)

        idx_path = tmp_path / "test.refl.idx"
        index.save(idx_path)

        with open(idx_path) as f:
            doc = json.load(f)

        assert doc["version"] == 1
        assert doc["nrows"] == 100
        assert doc["num_identifiers"] == 3
        assert doc["num_columns"] == 7
        assert "string_tables" in doc
        assert "columns" in doc
        # Each column is a compact array
        for entry in doc["columns"]:
            assert len(entry) == 6  # [name, type_idx, elem_size, count, offset, blob_size]


class TestValidate:
    def test_validate_pass(self, synthetic_refl):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        assert index.validate() is True

    def test_validate_missing_file(self, synthetic_refl, tmp_path):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)
        assert index.validate(tmp_path / "nonexistent.refl") is False

    def test_validate_wrong_size(self, synthetic_refl, tmp_path):
        path, _ = synthetic_refl
        index = ReflIndex.build(path)

        # Create a file with different size
        fake = tmp_path / "wrong_size.refl"
        fake.write_bytes(b"x" * 10)
        assert index.validate(fake) is False
