"""Download, verify, and spatially assign the GMW 2025 mangrove layer.

The compressed source GeoPackage is stored in data/raw/ and is never committed.
The prepared area table remains in data/derived/; overlay and provenance
products are written under data/outputs/validation/.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
RECORD_ID = "21346457"
FILE_NAME = "gmw_v4112_2025_mng_ext_cntry_info_vec.gpkg.gz"
RECORD_API = f"https://zenodo.org/api/records/{RECORD_ID}"
DOWNLOAD_URL = f"https://zenodo.org/records/{RECORD_ID}/files/{FILE_NAME}?download=1"
RAW_DIR = ROOT / "data/raw/environmental/marine/gmw"
ARCHIVE = RAW_DIR / FILE_NAME
GEOPACKAGE = RAW_DIR / FILE_NAME.removesuffix(".gz")
AREA_TABLE = ROOT / "data/derived/gmw_2025_mangrove_area_by_unit.csv"
OVERLAY_SUMMARY = ROOT / "data/outputs/validation/gmw_2025_direct_overlay_summary.json"
PIPELINE_MANIFEST = ROOT / "data/outputs/validation/gmw_2025_pipeline_manifest.json"
CHUNK_SIZE = 8 * 1024 * 1024


def md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def source_metadata() -> tuple[int, str]:
    response = requests.get(RECORD_API, timeout=60)
    response.raise_for_status()
    matches = [item for item in response.json().get("files", []) if item.get("key") == FILE_NAME]
    if len(matches) != 1:
        raise RuntimeError(f"Zenodo record {RECORD_ID} does not contain exactly one {FILE_NAME}")
    item = matches[0]
    checksum = str(item.get("checksum", ""))
    if not checksum.startswith("md5:"):
        raise RuntimeError(f"Zenodo did not publish an MD5 checksum for {FILE_NAME}")
    return int(item["size"]), checksum.removeprefix("md5:").lower()


def download_archive(expected_size: int, expected_md5: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.is_file() and ARCHIVE.stat().st_size == expected_size and md5(ARCHIVE) == expected_md5:
        print(f"Verified existing GMW archive: {ARCHIVE.relative_to(ROOT)}", flush=True)
        return

    partial = ARCHIVE.with_suffix(ARCHIVE.suffix + ".part")
    for attempt in range(1, 5):
        offset = partial.stat().st_size if partial.is_file() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with requests.get(DOWNLOAD_URL, headers=headers, stream=True, timeout=(30, 180)) as response:
                response.raise_for_status()
                append = offset > 0 and response.status_code == 206
                if offset and not append:
                    offset = 0
                mode = "ab" if append else "wb"
                received = offset
                started = time.monotonic()
                with partial.open(mode) as output:
                    for block in response.iter_content(CHUNK_SIZE):
                        if block:
                            output.write(block)
                            received += len(block)
                            if received % (512 * 1024 * 1024) < len(block):
                                print(f"GMW archive downloaded: {received / 1e9:.2f} GB", flush=True)
                print(f"GMW download elapsed: {(time.monotonic() - started) / 60:.1f} min", flush=True)
            if partial.stat().st_size != expected_size:
                raise IOError(f"Size mismatch: received {partial.stat().st_size}, expected {expected_size}")
            if md5(partial) != expected_md5:
                partial.unlink(missing_ok=True)
                raise IOError("MD5 mismatch; partial archive removed")
            partial.replace(ARCHIVE)
            return
        except (OSError, requests.RequestException) as exc:
            if attempt == 4:
                raise RuntimeError(f"GMW archive download failed after {attempt} attempts: {exc}") from exc
            time.sleep(min(2**attempt, 30))


def extract_geopackage() -> None:
    if GEOPACKAGE.is_file() and GEOPACKAGE.stat().st_size > 0:
        return
    temporary = GEOPACKAGE.with_suffix(GEOPACKAGE.suffix + ".part")
    temporary.unlink(missing_ok=True)
    with gzip.open(ARCHIVE, "rb") as compressed, temporary.open("wb") as output:
        for block in iter(lambda: compressed.read(CHUNK_SIZE), b""):
            output.write(block)
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise RuntimeError("GMW GeoPackage extraction produced an empty file")
    temporary.replace(GEOPACKAGE)


def run_script(name: str) -> None:
    script = ROOT / "code/scripts" / name
    print(f"== {name} ==", flush=True)
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    expected_size, expected_md5 = source_metadata()
    download_archive(expected_size, expected_md5)
    extract_geopackage()
    run_script("overlay_gmw_2025_direct_eez.py")
    run_script("build_gmw_2025_direct_area_table.py")
    if not AREA_TABLE.is_file() or not OVERLAY_SUMMARY.is_file():
        raise FileNotFoundError("GMW overlay did not produce its expected area table and summary")
    manifest = {
        "pipeline": "GMW 2025 polygon-to-EEZ area assignment",
        "zenodo_record": RECORD_ID,
        "source_file": FILE_NAME,
        "source_size_bytes": expected_size,
        "source_md5": expected_md5,
        "source_archive_sha256": sha256(ARCHIVE),
        "area_table_sha256": sha256(AREA_TABLE),
        "overlay_summary_sha256": sha256(OVERLAY_SUMMARY),
        "completed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    PIPELINE_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
