# refl-index

Sidecar index for DIALS .refl msgpack files. Enables O(1) random access to any column or row range.

## Dev Setup

```bash
UV_CACHE_DIR=/sdf/data/lcls/ds/prj/prjdat21/results/cwang31/.UV_CACHE uv pip install -e ".[numpy]"
```

## Running Tests

```bash
UV_CACHE_DIR=/sdf/data/lcls/ds/prj/prjdat21/results/cwang31/.UV_CACHE uv run pytest tests/ -v
```

## Test Data

- Small individual .refl: `/sdf/data/lcls/ds/mfx/mfxl1008021/results/common/results/r0043/002_rg019/task009/combine_experiments_t002/intermediates/t002_rg019_chunk000_reintegrated_000000.refl`
- Combined 6.3GB .refl: `/sdf/data/lcls/ds/mfx/mfxl1008021/results/common/results/abismal/combined_reflection_data/apo.refl`

## Architecture

- `dtypes.py`: DIALS type → numpy dtype mapping
- `indexer.py`: Build/save/load sidecar index (no numpy dependency)
- `reader.py`: Seek-based column reader (requires numpy)
- `cli.py`: `refl-index build|info|read`

## Notes

- Little-endian assumed (matches LCLS x86 machines)
- Binary blobs drained in 1MB chunks during indexing to avoid buffering
- Identifiers not stored in index (53K entries would bloat it)
