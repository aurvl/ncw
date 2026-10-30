"""Download (with resume) and verify the public Busch cell-level input archive.

The 12.4 GB archive is raw source data: it is stored under data/raw/economic/busch_2024/
and excluded from Git.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests


URL = "https://zenodo.org/records/19239386/files/08_input_dtas.zip?download=1"
TARGET = Path(__file__).resolve().parents[2] / "data/raw/economic/busch_2024/08_input_dtas.zip"
EXPECTED_SIZE = 12_384_216_498
EXPECTED_MD5 = "0fb5708381b11a9d173219f55bca5e81"


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    downloaded = TARGET.stat().st_size if TARGET.exists() else 0
    if downloaded > EXPECTED_SIZE:
        raise RuntimeError(f"Unexpected archive size before download: {downloaded} bytes")

    if downloaded < EXPECTED_SIZE:
        with requests.get(
            URL,
            headers={"Range": f"bytes={downloaded}-"},
            stream=True,
            timeout=(20, 120),
        ) as response:
            response.raise_for_status()
            if downloaded and response.status_code != 206:
                raise RuntimeError("Zenodo did not honor the resume range; partial file was preserved")
            started = time.monotonic()
            last_report = started
            mode = "ab" if downloaded else "wb"
            with TARGET.open(mode) as output:
                for block in response.iter_content(chunk_size=4 * 1024 * 1024):
                    if block:
                        output.write(block)
                        downloaded += len(block)
                    now = time.monotonic()
                    if now - last_report >= 15:
                        print(
                            f"downloaded {downloaded / 1e9:.3f}/{EXPECTED_SIZE / 1e9:.3f} GB",
                            flush=True,
                        )
                        last_report = now
            print(f"download seconds: {time.monotonic() - started:.1f}", flush=True)

    actual_size = TARGET.stat().st_size
    if actual_size != EXPECTED_SIZE:
        raise RuntimeError(f"Unexpected archive size: {actual_size}; expected {EXPECTED_SIZE} bytes")
    actual_md5 = file_md5(TARGET)
    if actual_md5 != EXPECTED_MD5:
        TARGET.unlink(missing_ok=True)
        raise RuntimeError(f"Archive MD5 mismatch: received {actual_md5}; invalid file removed")
    print(f"verified {TARGET} MD5 {actual_md5}", flush=True)


if __name__ == "__main__":
    main()
