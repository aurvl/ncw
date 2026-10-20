"""Download and checksum the 2001-2023 Gibbs/GFW gross-removals tiles.

Usage from the repository root:
    python code/scripts/download_gfw_dataverse.py --destination data/raw/environmental/forest/gfw_gibbs_2025/gross_removals

The script reads the public Harvard Dataverse file catalogue, downloads each
matching GeoTIFF concurrently, verifies its published MD5 and byte size, and
renames only verified files into place. Failed downloads leave no partial tile.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from threading import Lock


DATASET_DOI = "doi:10.7910/DVN/V2ISRH"
DATASET_API = "https://dataverse.harvard.edu/api/datasets/:persistentId/"
FILE_API = "https://dataverse.harvard.edu/api/access/datafile/{file_id}"
FILENAME_SUFFIX = "gross_removals_AGCO2_BGCO2_Mg_ha_all_forest_types_forest_extent_2001_23.tif"
EXPECTED_FILES = 272
CHUNK_SIZE = 8 * 1024 * 1024
MAX_ATTEMPTS = 4


def get_catalog() -> list[dict[str, object]]:
    url = f"{DATASET_API}?persistentId={DATASET_DOI}"
    request = urllib.request.Request(url, headers={"User-Agent": "BNC2-GFW-data-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)

    files = []
    for entry in payload["data"]["latestVersion"]["files"]:
        item = entry["dataFile"]
        name = item["filename"]
        if name.endswith(FILENAME_SUFFIX):
            files.append(
                {
                    "id": int(item["id"]),
                    "filename": name,
                    "size": int(item["filesize"]),
                    "md5": item["md5"].lower(),
                    "url": FILE_API.format(file_id=item["id"]),
                }
            )

    files.sort(key=lambda item: str(item["filename"]))
    if len(files) != EXPECTED_FILES:
        raise RuntimeError(f"Expected {EXPECTED_FILES} matching GeoTIFFs; found {len(files)}")
    return files


def file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        while block := stream.read(CHUNK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def download_one(item: dict[str, object], destination: Path) -> tuple[str, int]:
    name = str(item["filename"])
    target = destination / name
    expected_size = int(item["size"])
    expected_md5 = str(item["md5"])
    if target.is_file() and target.stat().st_size == expected_size:
        if file_md5(target) == expected_md5:
            return "verified-existing", expected_size

    partial = target.with_name(target.name + ".part")
    request = urllib.request.Request(
        str(item["url"]), headers={"User-Agent": "BNC2-GFW-data-fetch/1.0"}
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        digest = hashlib.md5(usedforsecurity=False)
        received = 0
        try:
            with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as out:
                while block := response.read(CHUNK_SIZE):
                    out.write(block)
                    digest.update(block)
                    received += len(block)
            if received != expected_size:
                raise IOError(f"size mismatch: expected {expected_size}, got {received}")
            if digest.hexdigest() != expected_md5:
                raise IOError(f"MD5 mismatch for {name}")
            partial.replace(target)
            return "downloaded", received
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            partial.unlink(missing_ok=True)
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"Failed {name} after {attempt} attempts: {exc}") from exc
            time.sleep(min(2**attempt, 30))

    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, help="Download only the first N tiles (for a checksum test).")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    args.destination.mkdir(parents=True, exist_ok=True)
    catalog = get_catalog()
    manifest = args.destination.parent / "gfw_dataverse_manifest.json"
    manifest.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    selected = catalog[: args.limit] if args.limit else catalog
    if not selected:
        raise RuntimeError("No files selected")

    print(
        f"Dataverse {DATASET_DOI}: {len(catalog)} tiles, "
        f"{sum(int(item['size']) for item in catalog) / 1e9:.2f} GB; "
        f"downloading {len(selected)} with {args.workers} workers",
        flush=True,
    )
    lock = Lock()
    started = time.monotonic()
    completed = 0
    downloaded = 0
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(download_one, item, args.destination): item for item in selected}
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                status, size = future.result()
                with lock:
                    completed += 1
                    if status == "downloaded":
                        downloaded += size
                    elapsed = time.monotonic() - started
                    print(
                        f"[{completed}/{len(selected)}] {status}: {item['filename']} "
                        f"({size / 1e6:.1f} MB); {downloaded / 1e9:.2f} GB downloaded; "
                        f"{elapsed / 60:.1f} min",
                        flush=True,
                    )
            except Exception as exc:  # report all tile failures after the pool drains
                failures.append(f"{item['filename']}: {exc}")

    if failures:
        raise RuntimeError("Tile download failures:\n" + "\n".join(failures))
    elapsed = time.monotonic() - started
    print(
        f"Finished: {completed}/{len(selected)} files; {downloaded / 1e9:.2f} GB downloaded "
        f"and MD5-verified in {elapsed / 60:.1f} min.",
        flush=True,
    )


if __name__ == "__main__":
    main()
