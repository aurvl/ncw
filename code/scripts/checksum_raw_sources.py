"""Write a SHA-256 inventory of every file under data/raw/."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory raw source files with size and SHA-256 checksum.")
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/metadata/raw_checksums.csv"))
    args = parser.parse_args()

    rows = [
        {
            "source_dir": path.relative_to(args.raw).parts[0],
            "file": path.relative_to(args.raw).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(args.raw.rglob("*"))
        if path.is_file() and path.name != "README.md"
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"{len(rows)} files written to {args.output}")


if __name__ == "__main__":
    main()
