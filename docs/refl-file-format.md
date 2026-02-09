# DIALS `.refl` File Format Specification

## Overview

DIALS (Diffraction Integration for Advanced Light Sources) `.refl` files store
reflection tables used in macromolecular crystallography data processing. Each
file contains a table of measured Bragg reflections with columns for
intensities, Miller indices, detector coordinates, and other metadata.

The files are serialized using [MessagePack](https://msgpack.org/) (msgpack), a
binary serialization format. The reflection data columns are stored as
contiguous binary blobs of fixed-size elements, making the format suitable for
memory-mapped or seek-based random access once byte offsets are known.

### Scale (Sample Observations)

The following numbers come from two specific files from the MFXl1008021
experiment at LCLS and are **not** inherent limits of the format. Real `.refl`
files can be much smaller (e.g., a single-image integration with a few dozen
reflections) or much larger (e.g., a combined dataset from a larger experiment).
The number of columns also varies depending on the processing stage.

| Property | Individual file (sample) | Combined file (sample) |
|---|---|---|
| Rows (reflections) | ~1,300 | ~20,380,600 |
| Columns | 28 | 28 |
| Experiment identifiers | 7 | 53,392 |
| File size | 429 KB | 6.3 GB |

## Top-Level Structure

A `.refl` file is a single msgpack-encoded object with the following structure:

```
array(3) [
  [0]  bytes    "dials::af::reflection_table"   # magic identifier
  [1]  int      1                                # format version
  [2]  map(3)   {                                # payload
         "identifiers": map { int → string },
         "nrows":       int,
         "data":        map { string → column_value }
       }
]
```

### Element [0]: Magic Identifier

A byte string (msgpack raw/str) containing the ASCII text
`dials::af::reflection_table`. This identifies the file as a DIALS reflection
table. Any reader should verify this magic before proceeding.

### Element [1]: Format Version

An integer, currently always `1`.

### Element [2]: Payload Map

A msgpack map with exactly three keys, always in this order:

1. `"identifiers"` — experiment identifier mapping
2. `"nrows"` — row count
3. `"data"` — column data

## Payload Fields

### `identifiers`

A msgpack map from integer keys to UUID strings. Each entry maps a sequential
integer ID (0, 1, 2, ...) to a UUID-4 string identifying the experiment that
produced those reflections.

```
identifiers: map {
  0 → "f571b10d-948c-7ba2-87c6-2ba27fb7dea9",
  1 → "540b41a0-ab28-4847-cfeb-0d965f255636",
  2 → "50ffdad8-e4a1-9f32-613c-af2110accb2b",
  ...
}
```

- Each UUID is a 36-character string (standard 8-4-4-4-12 hex format).
- Small files may have a handful of entries; combined files can have 53,000+.
- The `id` column in the data section references these integer keys.

### `nrows`

An integer giving the total number of rows (reflections) in every data column.
All columns have exactly this many rows.

### `data`

A msgpack map from column name (string) to column value. Each column value has
the structure:

```
column_value = array(2) [
  [0]  string   type_str,                # DIALS type identifier
  [1]  array(2) [
         [0]  int    count,              # number of rows (== nrows)
         [1]  bin    raw_binary_blob     # contiguous array of elements
       ]
]
```

The `count` field always equals the top-level `nrows`. The binary blob contains
`count` elements packed contiguously with no padding or alignment gaps.

## Column Types

DIALS uses 7 column types. Each type has a fixed byte size per element, and the
blob contains elements in **little-endian** byte order (matching x86 hardware).

| Type String | Bytes/Elem | NumPy dtype | Shape per row | Description |
|---|---|---|---|---|
| `double` | 8 | `<f8` | scalar | IEEE 754 64-bit float |
| `int` | 4 | `<i4` | scalar | 32-bit signed integer |
| `bool` | 1 | `?` | scalar | 1 byte, 0=false 1=true |
| `std::size_t` | 8 | `<u8` | scalar | 64-bit unsigned integer |
| `int6` | 24 | `<i4` | (6,) | 6 × 32-bit signed int |
| `vec3<double>` | 24 | `<f8` | (3,) | 3 × 64-bit float |
| `cctbx::miller::index<>` | 12 | `<i4` | (3,) | 3 × 32-bit signed int |

### Multi-Element Types

For multi-element types, the sub-elements of a single row are stored
contiguously. For example, a `vec3<double>` row stores three doubles (x, y, z)
in 24 consecutive bytes:

```
Row 0: [x0 (8B)] [y0 (8B)] [z0 (8B)]
Row 1: [x1 (8B)] [y1 (8B)] [z1 (8B)]
...
```

This means a blob of N rows of `vec3<double>` can be read as a NumPy array of
shape `(N, 3)` with dtype `<f8`.

### Type–Column Assignments (Observed)

The following 28 columns were observed in post-integration `.refl` files from
the sample dataset. Different DIALS processing stages produce different subsets
of columns; earlier stages (e.g., spot-finding) may have fewer columns, and
other workflows may introduce additional ones. This list is not exhaustive.

| Column Name | Type | Description |
|---|---|---|
| `background.dispersion` | `double` | Background pixel intensity dispersion |
| `background.mean` | `double` | Mean background intensity |
| `background.mse` | `double` | Background mean squared error |
| `background.sum.value` | `double` | Summed background intensity |
| `background.sum.variance` | `double` | Variance of summed background |
| `bbox` | `int6` | Shoebox bounding box (x0, x1, y0, y1, z0, z1) |
| `d` | `double` | Resolution (d-spacing) in Angstroms |
| `delpsical.rad` | `double` | Predicted minus observed rotation in radians |
| `entering` | `bool` | Whether reflection is entering the Ewald sphere |
| `flags` | `std::size_t` | Bitfield of reflection status flags |
| `id` | `int` | Experiment identifier (indexes into `identifiers`) |
| `intensity.sum.value` | `double` | Summed intensity |
| `intensity.sum.variance` | `double` | Variance of summed intensity |
| `miller_index` | `cctbx::miller::index<>` | Miller indices (h, k, l) |
| `num_pixels.background` | `int` | Number of background pixels |
| `num_pixels.background_used` | `int` | Number of background pixels used |
| `num_pixels.foreground` | `int` | Number of foreground pixels |
| `num_pixels.valid` | `int` | Number of valid pixels |
| `panel` | `std::size_t` | Detector panel index |
| `partial_id` | `std::size_t` | Partial reflection identifier |
| `partiality` | `double` | Reflection partiality (0–1) |
| `s1` | `vec3<double>` | Scattered beam direction vector |
| `xyzcal.mm` | `vec3<double>` | Calculated position in mm + rotation angle |
| `xyzcal.px` | `vec3<double>` | Calculated position in pixels + image number |
| `xyzobs.mm.value` | `vec3<double>` | Observed position in mm + rotation angle |
| `xyzobs.mm.variance` | `vec3<double>` | Variance of observed position (mm) |
| `xyzobs.px.value` | `vec3<double>` | Observed position in pixels + image number |
| `xyzobs.px.variance` | `vec3<double>` | Variance of observed position (pixels) |

See the [DIALS documentation](https://dials.github.io/) for the full set of
possible columns across different processing stages.

## Byte-Level Encoding

This section documents the exact msgpack encoding observed in real `.refl`
files. Understanding this is necessary for building fast parsers that avoid
buffering multi-hundred-megabyte blobs.

### Outer Array

```
Offset  Bytes     Meaning
------  --------  -------------------------------------------
0x0000  93        fixarray(3) — outer array of 3 elements
```

The outer array always has exactly 3 elements, so it always fits in the
compact fixarray encoding (single byte, 0x90 | length).

### Magic String

```
0x0001  BB        fixstr(27) — 0xA0 | 27
0x0002  (27B)     "dials::af::reflection_table"
```

Encoded as a fixstr since 27 ≤ 31.

### Version

```
0x001D  01        positive fixint(1)
```

### Payload Map

```
0x001E  83        fixmap(3)
```

Always 3 keys, so fits in fixmap.

### Identifiers Key + Value

```
0x001F  AB        fixstr(11) — key "identifiers"
0x0020  (11B)     "identifiers"
```

The identifiers map header depends on the number of entries:

| Entries | Encoding | Bytes |
|---|---|---|
| ≤ 15 | fixmap | 1 byte: `0x80 \| n` |
| ≤ 65,535 | map16 | 3 bytes: `0xDE` + 2B big-endian length |
| > 65,535 | map32 | 5 bytes: `0xDF` + 4B big-endian length |

Examples observed:

```
Small file (7 entries):   87              fixmap(7)
Large file (53,392):      DE D0 90        map16(53392)
```

Each identifier entry:

```
<int_key>  <str8(36)>
```

The integer key uses the smallest msgpack integer encoding that fits:
- Keys 0–127: positive fixint (1 byte)
- Keys 128–255: uint8 (2 bytes: `0xCC` + 1B)
- Keys 256–65535: uint16 (3 bytes: `0xCD` + 2B big-endian)

The UUID string is always 36 characters, encoded as str8:

```
D9 24 <36 bytes of UUID text>
```

(`0xD9` = str8 header, `0x24` = 36)

### `nrows` Key + Value

```
A5           fixstr(5)
"nrows"
<integer>    smallest msgpack int encoding
```

| nrows value | Encoding |
|---|---|
| 1,300 | `CD 05 14` — uint16 |
| 20,380,600 | `CE 01 36 FB B8` — uint32 |

### `data` Key + Value

```
A4           fixstr(4)
"data"
DE 00 1C     map16(28) — 28 columns in these sample files
```

### Column Entries

Each column entry in the data map:

```
<column_name_str>           # fixstr or str8
92                          # fixarray(2) — outer [type_str, inner]
  <type_str>                # fixstr or str8
  92                        # fixarray(2) — inner [count, blob]
    <count_int>             # uint16 or uint32
    <bin_header> <raw_data> # binary blob
```

#### Column Name Encoding

Column names use fixstr when length ≤ 31, or str8 otherwise:

```
"d"                       (1 char)  → A1 64
"background.dispersion"   (21 chars) → B5 + 21 bytes
"intensity.sum.variance"  (22 chars) → B6 + 22 bytes
```

#### Type String Encoding

Always a fixstr:

```
"double"                  (6 chars)  → A6 + 6 bytes
"int"                     (3 chars)  → A3 + 3 bytes
"bool"                    (4 chars)  → A4 + 4 bytes
"std::size_t"             (11 chars) → AB + 11 bytes
"int6"                    (4 chars)  → A4 + 4 bytes
"vec3<double>"            (12 chars) → AC + 12 bytes
"cctbx::miller::index<>"  (22 chars) → B6 + 22 bytes
```

#### Binary Blob Header

The blob uses the standard msgpack bin format. The header variant depends on
blob size:

| Blob size range | Header | Total header bytes |
|---|---|---|
| 0 – 255 | `C4 XX` | 2 |
| 256 – 65,535 | `C5 XX XX` | 3 |
| 65,536 – 4,294,967,295 | `C6 XX XX XX XX` | 5 |

Length bytes are big-endian.

In the sample small file (nrows=1,300): all blobs range from 1,300 to 31,200
bytes, so all use **bin16** (`0xC5`).

In the sample combined file (nrows=20,380,600): all blobs range from
20,380,600 to 489,134,400 bytes (~466 MB), so all use **bin32** (`0xC6`).

Which variant appears depends entirely on blob size, which is
`nrows × elem_size`.

The blob data immediately follows the header with no padding. After the last
byte of a column's blob, the next column's name string begins immediately.

#### Example: First Column of Small File

```
Offset  Hex              Meaning
------  ---------------  ----------------------------------------
0x014E  B5               fixstr(21)
0x014F  (21 bytes)       "background.dispersion"
0x0164  92               fixarray(2) — outer
0x0165  A6               fixstr(6)
0x0166  (6 bytes)        "double"
0x016C  92               fixarray(2) — inner
0x016D  CD 05 14         uint16(1300) — count
0x0170  C5               bin16
0x0171  28 A0            blob_size = 10,400 (= 1300 × 8)
0x0173  (10,400 bytes)   raw blob data starts here
        ├── bytes 0–7:   00 00 00 60 6E B8 CF 3F
        │                → IEEE 754 LE double = 0.24781589...
        ├── bytes 8–15:  next double value
        ...
        └── bytes 10,392–10,399: last double value
```

#### Example: First Column of Large File

```
Offset      Hex                    Meaning
----------  ---------------------  ----------------------------------------
2,188,753   B5                     fixstr(21)
2,188,754   (21 bytes)             "background.dispersion"
2,188,775   92                     fixarray(2) — outer
2,188,776   A6                     fixstr(6)
2,188,777   (6 bytes)              "double"
2,188,783   92                     fixarray(2) — inner
2,188,784   CE 01 36 FB B8         uint32(20,380,600) — count
2,188,789   C6                     bin32
2,188,790   09 B7 DD C0            blob_size = 163,044,800 (= 20,380,600 × 8)
2,188,794   (163,044,800 bytes)    raw blob data starts here
```

## File Layout Diagram

```
┌──────────────────────────────────────────────┐
│ fixarray(3) header                      [1B] │
├──────────────────────────────────────────────┤
│ Magic: "dials::af::reflection_table"   [28B] │
├──────────────────────────────────────────────┤
│ Version: 1                              [1B] │
├──────────────────────────────────────────────┤
│ fixmap(3) header                        [1B] │
├──────────────────────────────────────────────┤
│ "identifiers" key                      [12B] │
│ identifiers map header              [1–5B]   │
│ ┌──────────────────────────────────────────┐ │
│ │ id₀ → UUID₀  (1–3B + 38B)               │ │
│ │ id₁ → UUID₁                             │ │
│ │ ...                                      │ │
│ │ idₙ → UUIDₙ                             │ │
│ └──────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│ "nrows" key + integer value          [6–10B] │
├──────────────────────────────────────────────┤
│ "data" key + map header              [5–7B]  │
│ ┌──────────────────────────────────────────┐ │
│ │ Column 0: name + type + count + blob     │ │
│ │  ┌────────────────────────────────────┐  │ │
│ │  │ column_name (fixstr/str8)         │  │ │
│ │  │ fixarray(2)                       │  │ │
│ │  │  type_str (fixstr)               │  │ │
│ │  │  fixarray(2)                     │  │ │
│ │  │   count (uint16/uint32)          │  │ │
│ │  │   bin header (C4/C5/C6 + len)    │  │ │
│ │  │   ┌────────────────────────────┐ │  │ │
│ │  │   │ raw data                   │ │  │ │
│ │  │   │ (count × elem_size bytes)  │ │  │ │
│ │  │   │ LITTLE-ENDIAN              │ │  │ │
│ │  │   └────────────────────────────┘ │  │ │
│ │  └────────────────────────────────────┘  │ │
│ │ Column 1: ...                            │ │
│ │ ...                                      │ │
│ │ Column 27: ...                           │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
                                          EOF ◄── last blob ends exactly at EOF
```

## Random Access via Byte Offsets

Because each column's blob is a contiguous array of fixed-size elements, random
access to any column or row range is possible via `file.seek()`:

**Read column `C` starting at row `R_start` through `R_stop`:**

```python
offset = blob_offset[C] + R_start * elem_size[C]
nbytes = (R_stop - R_start) * elem_size[C]

f.seek(offset)
raw = f.read(nbytes)
array = numpy.frombuffer(raw, dtype=numpy_dtype[C]).reshape(shape)
```

This enables reading a single column from a 6.3 GB file in milliseconds,
compared to minutes for parsing the entire file sequentially.

**Prerequisites:**

- You must know the `blob_offset` for each column (byte position where its
  raw data starts, after the msgpack bin header).
- You must know the `elem_size` for the column's type.

These offsets can be computed by a single sequential scan of the file that
parses only the msgpack structure headers (not the blob contents). This is
what the `refl-index` tool does, storing the results in a lightweight JSON
sidecar file.

## Size Budget (Sample Combined File)

The following breakdown is from the 6.3 GB sample combined file (20.4M rows,
28 columns, 53K identifiers). Actual sizes scale linearly with row count and
depend on which columns are present.

| Component | Size | % of file |
|---|---|---|
| Identifiers (53,392 entries) | ~2.1 MB | 0.03% |
| Msgpack structure overhead | ~2 KB | ~0% |
| Column blobs (28 columns) | ~6.25 GB | 99.97% |
| **Total** | **6.25 GB** | |

In general, the binary blobs dominate file size. The msgpack framing overhead
is negligible. Identifier overhead scales with experiment count (roughly 39
bytes per entry).

Breakdown by column type for this sample:

| Type | Columns | Blob size each | Subtotal |
|---|---|---|---|
| `double` (×13) | 20.4M rows | 163 MB | 2.12 GB |
| `vec3<double>` (×7) | 20.4M rows | 467 MB | 3.27 GB |
| `std::size_t` (×3) | 20.4M rows | 163 MB | 0.49 GB |
| `int` (×3) | 20.4M rows | 81.5 MB | 0.24 GB |
| `int6` (×1) | 20.4M rows | 467 MB | 0.47 GB |
| `cctbx::miller::index<>` (×1) | 20.4M rows | 245 MB | 0.24 GB |
| `bool` (×1) | 20.4M rows | 20.4 MB | 0.02 GB |

## Endianness

All numeric data in the binary blobs is stored in **little-endian** byte order.
This matches the native byte order of x86/x86-64 processors used at LCLS and
most modern hardware. The msgpack structure headers (array lengths, map
lengths, bin sizes) use **big-endian** per the msgpack specification.

Example — first value of `background.dispersion` column:

```
Bytes (file order):  00 00 00 60 6E B8 CF 3F
IEEE 754 LE double:  0.24781589210033417
```

## Compatibility Notes

- **DIALS source**: The format is defined by `dials::af::reflection_table`
  in the DIALS C++ codebase, serialized via the `dials.array_family` msgpack
  interface.
- **msgpack version**: The file uses standard msgpack types only (no ext
  types). Any msgpack library that supports the bin format family (introduced
  in msgpack spec revision 2013-09) can parse these files.
- **Max blob size**: The largest individual blob observed is ~467 MB (bin32
  can hold up to ~4 GB). Files with more than ~536 million rows of
  `vec3<double>` would exceed the bin32 limit.
- **Key ordering**: While msgpack maps are officially unordered, DIALS always
  writes the payload keys in the order `identifiers`, `nrows`, `data`, and
  data columns in alphabetical order. Readers should not depend on this.

## Reference Files

The sample files used to produce the byte-level analysis in this document:

| Description | Path | Size |
|---|---|---|
| Small individual file | `.../mfxl1008021/.../t002_rg019_chunk000_reintegrated_000000.refl` | 429 KB |
| Combined file | `.../mfxl1008021/.../combined_reflection_data/apo.refl` | 6.3 GB |

Full paths on LCLS SDF:
- Small: `/sdf/data/lcls/ds/mfx/mfxl1008021/results/common/results/r0043/002_rg019/task009/combine_experiments_t002/intermediates/t002_rg019_chunk000_reintegrated_000000.refl`
- Combined: `/sdf/data/lcls/ds/mfx/mfxl1008021/results/common/results/abismal/combined_reflection_data/apo.refl`
