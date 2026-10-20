"""Download the WRI v1.3.2 forest-type tiles matching the Gibbs raster grid.

Forest-type code 6 identifies pixels assigned mangrove removal factors in the
published model. This downloads only source-version model outputs, not GMW 2025.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time

import requests


BASE_URL = (
    "https://gfw2-data.s3.amazonaws.com/climate/carbon_model/"
    "removal_forest_type/standard/20240308/"
)
FOREST_TYPE_SUFFIX = "_removal_forest_type.tif"
EXPECTED_TILES = 272
CHUNK_SIZE = 8 * 1024 * 1024


def forest_type_name(removals_name: str) -> str:
    """Map one published removals tile to its same-grid forest-type tile."""
    if "_gross_removals" not in removals_name:
        raise ValueError(f"Not a Gibbs gross-removals tile: {removals_name}")
    return removals_name.split("_gross_removals", 1)[0] + FOREST_TYPE_SUFFIX


def download_one(removals_name: str, destination: Path) -> dict[str, object]:
    name = forest_type_name(removals_name)
    url = BASE_URL + name
    target = destination / name
    for attempt in range(1, 5):
        partial = destination / f"{name}.part"
        try:
            metadata = requests.head(url, timeout=60)
            metadata.raise_for_status()
            size = int(metadata.headers["Content-Length"])
            etag = metadata.headers.get("ETag", "").strip('"')
            if target.exists() and target.stat().st_size == size:
                digest = hashlib.md5(usedforsecurity=False)
                sha256 = hashlib.sha256()
                with target.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                        digest.update(chunk)
                        sha256.update(chunk)
                if not etag or "-" in etag or digest.hexdigest() == etag:
                    return {
                        "filename": name, "url": url, "size": size,
                        "etag": etag, "sha256": sha256.hexdigest(), "status": "verified-existing",
                    }
            md5 = hashlib.md5(usedforsecurity=False)
            sha256 = hashlib.sha256()
            received = 0
            with requests.get(url, stream=True, timeout=180) as response:
                response.raise_for_status()
                with partial.open("wb") as stream:
                    for chunk in response.iter_content(CHUNK_SIZE):
                        if chunk:
                            stream.write(chunk)
                            md5.update(chunk)
                            sha256.update(chunk)
                            received += len(chunk)
            if received != size:
                raise IOError(f"Size mismatch for {name}: {received} != {size}")
            if etag and "-" not in etag and md5.hexdigest() != etag:
                raise IOError(f"ETag MD5 mismatch for {name}")
            partial.replace(target)
            return {
                "filename": name, "url": url, "size": size,
                "etag": etag, "sha256": sha256.hexdigest(), "status": "downloaded",
            }
        except (OSError, requests.RequestException) as exc:
            partial.unlink(missing_ok=True)
            if attempt == 4:
                raise RuntimeError(f"Failed to download {name}: {exc}") from exc
            time.sleep(min(2**attempt, 20))
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--removals-manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    catalog = json.loads(args.removals_manifest.read_text(encoding="utf-8"))
    names = [str(item["filename"]) for item in catalog]
    if len(names) != EXPECTED_TILES or len(set(names)) != EXPECTED_TILES:
        raise RuntimeError(f"Expected {EXPECTED_TILES} unique gross-removals tiles, found {len(names)}")
    args.destination.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download_one, name, args.destination): name for name in names}
        for future in as_completed(futures):
            item = future.result()
            results.append(item)
            print(f"[{len(results)}/{len(names)}] {item['status']}: {item['filename']}", flush=True)
    results.sort(key=lambda item: str(item["filename"]))
    (args.destination.parent / "gfw_forest_type_manifest.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(f"Verified {len(results)} forest-type tiles; total {sum(int(item['size']) for item in results) / 1e9:.2f} GB", flush=True)


if __name__ == "__main__":
    main()
