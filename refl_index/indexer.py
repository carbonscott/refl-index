"""ReflIndex: build, save, and load sidecar index for DIALS .refl files."""

import json
import os
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import msgpack

from .dtypes import DIALS_TYPES, element_size

# Chunk size for draining binary blobs during indexing
_DRAIN_CHUNK = 1 * 1024 * 1024  # 1 MB


@dataclass
class ColumnInfo:
    """Metadata for one column in a .refl file."""
    name: str
    type_str: str
    elem_size: int
    count: int
    blob_offset: int  # byte offset where raw data starts (after msgpack bin header)
    blob_size: int    # total bytes of raw data


class ReflIndex:
    """Sidecar index for a DIALS .refl msgpack file.

    Stores byte offsets of each column's binary blob, enabling O(1)
    random access to any column or row range via file.seek().
    """

    def __init__(
        self,
        refl_path: str,
        file_size: int,
        nrows: int,
        num_identifiers: int,
        columns: list[ColumnInfo],
    ):
        self.refl_path = str(refl_path)
        self.file_size = file_size
        self.nrows = nrows
        self.num_identifiers = num_identifiers
        self.columns = columns
        self._column_map = {c.name: c for c in columns}

    def __getitem__(self, name: str) -> ColumnInfo:
        return self._column_map[name]

    def __contains__(self, name: str) -> bool:
        return name in self._column_map

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @classmethod
    def build(cls, refl_path: str | Path) -> "ReflIndex":
        """Build an index by scanning a .refl file.

        Parses the msgpack structure to record byte offsets of each
        column's binary blob. Binary blobs are drained in chunks to
        avoid buffering hundreds of MB.
        """
        refl_path = Path(refl_path)
        file_size = refl_path.stat().st_size

        with open(refl_path, "rb") as f:
            unpacker = msgpack.Unpacker(
                f,
                raw=True,
                strict_map_key=False,
                max_bin_len=2**31 - 1,
                max_buffer_size=2**31 - 1,
                max_str_len=2**31 - 1,
            )

            # Outer array: [magic, version, data_map]
            outer_len = unpacker.read_array_header()
            if outer_len != 3:
                raise ValueError(f"Expected outer array of length 3, got {outer_len}")

            magic = unpacker.unpack()
            if magic != b"dials::af::reflection_table":
                raise ValueError(f"Not a DIALS .refl file (magic: {magic!r})")

            version = unpacker.unpack()

            # Main map: {"identifiers": ..., "nrows": ..., "data": ...}
            main_map_len = unpacker.read_map_header()

            nrows = 0
            num_identifiers = 0
            columns = []

            for _ in range(main_map_len):
                key = unpacker.unpack()
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                if key == "nrows":
                    nrows = unpacker.unpack()

                elif key == "identifiers":
                    # Skip all identifier entries without constructing them
                    num_identifiers = unpacker.read_map_header()
                    for _id in range(num_identifiers):
                        unpacker.skip()  # key (int)
                        unpacker.skip()  # value (uuid string)

                elif key == "data":
                    num_data_cols = unpacker.read_map_header()
                    for _col in range(num_data_cols):
                        col_name = unpacker.unpack()
                        if isinstance(col_name, bytes):
                            col_name = col_name.decode("utf-8")

                        # Each column value is: [type_str, [count, raw_binary_blob]]
                        unpacker.read_array_header()  # outer array (2)
                        type_str = unpacker.unpack()
                        if isinstance(type_str, bytes):
                            type_str = type_str.decode("utf-8")

                        unpacker.read_array_header()  # inner array (2)
                        count = unpacker.unpack()

                        # Now we need to read the binary blob header manually
                        # to get the offset without buffering the entire blob.
                        # The next item is a msgpack bin (0xC4/C5/C6).
                        #
                        # We use read_bytes(1) to get the bin marker, then
                        # read the length bytes to determine blob size.
                        # After that, tell() gives us the blob data offset.

                        marker_byte = unpacker.read_bytes(1)
                        marker = marker_byte[0]

                        if marker == 0xC4:
                            # bin8: 1 byte length
                            length_bytes = unpacker.read_bytes(1)
                            blob_size = length_bytes[0]
                        elif marker == 0xC5:
                            # bin16: 2 byte length (big-endian)
                            length_bytes = unpacker.read_bytes(2)
                            blob_size = struct.unpack(">H", length_bytes)[0]
                        elif marker == 0xC6:
                            # bin32: 4 byte length (big-endian)
                            length_bytes = unpacker.read_bytes(4)
                            blob_size = struct.unpack(">I", length_bytes)[0]
                        else:
                            raise ValueError(
                                f"Expected bin marker for column {col_name!r}, "
                                f"got 0x{marker:02x}"
                            )

                        blob_offset = unpacker.tell()

                        # Verify size matches expectations
                        if type_str in DIALS_TYPES:
                            expected_size = element_size(type_str) * count
                            if blob_size != expected_size:
                                raise ValueError(
                                    f"Column {col_name!r}: blob_size={blob_size} != "
                                    f"element_size({element_size(type_str)}) * count({count}) = {expected_size}"
                                )

                        # Drain the blob in chunks to avoid buffering it all
                        remaining = blob_size
                        while remaining > 0:
                            chunk = min(_DRAIN_CHUNK, remaining)
                            unpacker.read_bytes(chunk)
                            remaining -= chunk

                        elem_sz = element_size(type_str) if type_str in DIALS_TYPES else 0
                        columns.append(ColumnInfo(
                            name=col_name,
                            type_str=type_str,
                            elem_size=elem_sz,
                            count=count,
                            blob_offset=blob_offset,
                            blob_size=blob_size,
                        ))

                else:
                    # Unknown key — skip its value
                    unpacker.skip()

        return cls(
            refl_path=str(refl_path),
            file_size=file_size,
            nrows=nrows,
            num_identifiers=num_identifiers,
            columns=columns,
        )

    def save(self, path: str | Path | None = None) -> Path:
        """Save index as a JSON sidecar file.

        Defaults to ``<refl_path>.idx``.
        """
        if path is None:
            path = Path(self.refl_path + ".idx")
        else:
            path = Path(path)

        # String table for type_str deduplication
        type_strs = sorted(set(c.type_str for c in self.columns))
        type_str_to_idx = {t: i for i, t in enumerate(type_strs)}

        # Columns as compact arrays
        col_entries = []
        for c in self.columns:
            col_entries.append([
                c.name,
                type_str_to_idx[c.type_str],
                c.elem_size,
                c.count,
                c.blob_offset,
                c.blob_size,
            ])

        doc = {
            "version": 1,
            "refl_path": self.refl_path,
            "file_size": self.file_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "nrows": self.nrows,
            "num_identifiers": self.num_identifiers,
            "num_columns": len(self.columns),
            "string_tables": {"type_strs": type_strs},
            "columns": col_entries,
        }

        with open(path, "w") as f:
            json.dump(doc, f, indent=2)

        return path

    @classmethod
    def load(cls, path: str | Path) -> "ReflIndex":
        """Load an index from a JSON sidecar file."""
        path = Path(path)
        with open(path) as f:
            doc = json.load(f)

        if doc.get("version") != 1:
            raise ValueError(f"Unsupported index version: {doc.get('version')}")

        type_strs = doc["string_tables"]["type_strs"]

        columns = []
        for entry in doc["columns"]:
            name, type_idx, elem_sz, count, blob_offset, blob_size = entry
            columns.append(ColumnInfo(
                name=name,
                type_str=type_strs[type_idx],
                elem_size=elem_sz,
                count=count,
                blob_offset=blob_offset,
                blob_size=blob_size,
            ))

        return cls(
            refl_path=doc["refl_path"],
            file_size=doc["file_size"],
            nrows=doc["nrows"],
            num_identifiers=doc["num_identifiers"],
            columns=columns,
        )

    def validate(self, refl_path: str | Path | None = None) -> bool:
        """Check that the indexed .refl file exists and matches expected size."""
        path = Path(refl_path) if refl_path else Path(self.refl_path)
        if not path.exists():
            return False
        return path.stat().st_size == self.file_size
