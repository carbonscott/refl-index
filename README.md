# refl-index

Fast, selective access to DIALS `.refl` msgpack files. Builds a lightweight
sidecar index (~3 KB) that records byte offsets of each column's binary blob,
then uses `file.seek()` to read any column or row range without parsing the
entire file.

## Setup

First-time setup (creates `.venv` and installs dependencies):

```bash
cd /path/to/refl-index
uv sync --extra numpy
```

Omit `--extra numpy` if you only need indexing (no data reading).

Then, to use `refl-index` from any directory, source the environment file:

```bash
source /path/to/refl-index/env.sh
```

This sets `UV_CACHE_DIR` for SDF and defines a `refl-index` shell function so
the CLI works from anywhere.

## CLI Usage

### Build an index

```bash
$ refl-index build /path/to/reflections.refl
Building index for /path/to/reflections.refl ...
Saved index to /path/to/reflections.refl.idx
  rows:        20,380,600
  identifiers: 53,392
  columns:     28
  file size:   6,707,407,141 bytes
```

### Inspect an index

```bash
$ refl-index info reflections.refl.idx
Index: reflections.refl.idx
  refl_path:   /path/to/reflections.refl
  file_size:   6,707,407,141
  nrows:       20,380,600
  identifiers: 53,392
  columns:     28

Column                                   Type                      ElemSize        Count          Offset        BlobSize
------------------------------------------------------------------------------------------------------------------------
intensity.sum.value                      double                           8   20,380,600   1,897,584,936   163,044,800
miller_index                             cctbx::miller::index<>          12   20,380,600   2,223,674,626   244,567,200
...
```

### Read column data

```bash
# First 5 rows of a specific column
$ refl-index read reflections.refl.idx -c intensity.sum.value --head 5

# Multiple columns, row range
$ refl-index read reflections.refl.idx -c intensity.sum.value miller_index --start 100 --stop 110
```

## Python Usage

### Build and save an index

```python
from refl_index import ReflIndex

index = ReflIndex.build("reflections.refl")
index.save()  # writes reflections.refl.idx
```

### Load an index and read data

```python
from refl_index import ReflIndex, ReflReader

index = ReflIndex.load("reflections.refl.idx")
reader = ReflReader(index)

# Read an entire column as a numpy array
intensities = reader.read_column("intensity.sum.value")

# Read a row slice
first_100 = reader.read_column("miller_index", stop=100)

# Read multiple columns at once
data = reader.read_columns(["intensity.sum.value", "miller_index"], start=0, stop=1000)

# Read raw bytes (no numpy needed)
raw = reader.read_column_raw("flags", start=10, stop=20)
```

### Inspect index metadata

```python
index = ReflIndex.load("reflections.refl.idx")

print(index.nrows)           # 20380600
print(index.column_names)    # ['background.dispersion', 'background.mean', ...]
print(index["miller_index"]) # ColumnInfo(name='miller_index', type_str='cctbx::miller::index<>', ...)
```

## How It Works

A DIALS `.refl` file stores each column as a contiguous binary blob of
fixed-size elements (e.g., `double` = 8 bytes, `vec3<double>` = 24 bytes)
inside a msgpack container. Normally, reading any column requires parsing the
entire file sequentially.

`refl-index` solves this in two steps:

1. **Build** — scan the msgpack structure once to record the byte offset and
   size of each column's blob. This takes ~1 second even for a 6.3 GB file.
   The result is saved as a small JSON sidecar (`.refl.idx`).

2. **Read** — use `file.seek()` to jump directly to any column's blob, then
   read exactly the bytes needed. Reading 5 rows from a 6.3 GB file takes
   ~14 ms.

For details on the `.refl` file format, see
[docs/refl-file-format.md](docs/refl-file-format.md).

## Running Tests

```bash
uv run pytest tests/ -v
```
