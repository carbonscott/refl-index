"""CLI: refl-index build|info|read"""

import argparse
import sys
from pathlib import Path

from .indexer import ReflIndex


def cmd_build(args):
    """Build a sidecar index for a .refl file."""
    refl_path = Path(args.file)
    if not refl_path.exists():
        print(f"Error: file not found: {refl_path}", file=sys.stderr)
        return 1

    print(f"Building index for {refl_path} ...")
    index = ReflIndex.build(refl_path)

    out_path = Path(args.output) if args.output else None
    saved = index.save(out_path)
    print(f"Saved index to {saved}")
    print(f"  rows:        {index.nrows:,}")
    print(f"  identifiers: {index.num_identifiers:,}")
    print(f"  columns:     {len(index.columns)}")
    print(f"  file size:   {index.file_size:,} bytes")
    return 0


def cmd_info(args):
    """Print column table from an index file."""
    idx_path = Path(args.index)
    if not idx_path.exists():
        print(f"Error: index file not found: {idx_path}", file=sys.stderr)
        return 1

    index = ReflIndex.load(idx_path)
    print(f"Index: {idx_path}")
    print(f"  refl_path:   {index.refl_path}")
    print(f"  file_size:   {index.file_size:,}")
    print(f"  nrows:       {index.nrows:,}")
    print(f"  identifiers: {index.num_identifiers:,}")
    print(f"  columns:     {len(index.columns)}")
    print()

    # Column table
    header = f"{'Column':<40} {'Type':<25} {'ElemSize':>8} {'Count':>12} {'Offset':>15} {'BlobSize':>15}"
    print(header)
    print("-" * len(header))
    for c in index.columns:
        print(f"{c.name:<40} {c.type_str:<25} {c.elem_size:>8} {c.count:>12,} {c.blob_offset:>15,} {c.blob_size:>15,}")
    return 0


def cmd_read(args):
    """Read and print column data from a .refl file using its index."""
    try:
        import numpy as np
    except ImportError:
        print("Error: numpy is required for the 'read' command. Install with: pip install refl-index[numpy]", file=sys.stderr)
        return 1

    from .reader import ReflReader

    idx_path = Path(args.index)
    if not idx_path.exists():
        print(f"Error: index file not found: {idx_path}", file=sys.stderr)
        return 1

    index = ReflIndex.load(idx_path)

    # Resolve .refl file path
    refl_path = Path(index.refl_path)
    if not refl_path.exists():
        # Try relative to the index file
        refl_path = idx_path.parent / refl_path.name
        if not refl_path.exists():
            print(f"Error: .refl file not found: {index.refl_path}", file=sys.stderr)
            return 1

    reader = ReflReader(index, refl_path)

    # Which columns to read
    col_names = args.columns if args.columns else index.column_names

    start = args.start or 0
    stop = args.stop
    head = args.head

    if stop is None and head is not None:
        stop = start + head

    for name in col_names:
        if name not in index:
            print(f"Warning: column {name!r} not found, skipping", file=sys.stderr)
            continue
        arr = reader.read_column(name, start=start, stop=stop)
        col_info = index[name]
        print(f"\n--- {name} ({col_info.type_str}, {col_info.count:,} rows) ---")
        print(arr)

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="refl-index",
        description="Sidecar index for DIALS .refl msgpack files",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Build index for a .refl file")
    p_build.add_argument("file", help="Path to .refl file")
    p_build.add_argument("-o", "--output", help="Output path for index (default: <file>.idx)")

    # info
    p_info = subparsers.add_parser("info", help="Print column info from an index file")
    p_info.add_argument("index", help="Path to .refl.idx file")

    # read
    p_read = subparsers.add_parser("read", help="Read column data using an index")
    p_read.add_argument("index", help="Path to .refl.idx file")
    p_read.add_argument("-c", "--columns", nargs="+", help="Column names to read (default: all)")
    p_read.add_argument("--start", type=int, help="First row to read")
    p_read.add_argument("--stop", type=int, help="One past last row to read")
    p_read.add_argument("--head", type=int, help="Number of rows to read from start")

    args = parser.parse_args()
    commands = {"build": cmd_build, "info": cmd_info, "read": cmd_read}
    sys.exit(commands[args.command](args))
