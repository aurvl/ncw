"""Download (with resume) the public Busch et al. output archive, used only for audits.

The archive is raw source data: it is stored under data/raw/economic/busch_2024/ and excluded
from Git.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests


URL = "https://zenodo.org/records/19239386/files/09_output_dtas.zip?download=1"
TARGET = Path(__file__).resolve().parents[2] / "data/raw/economic/busch_2024/09_output_dtas.zip"
EXPECTED_SIZE = 2_942_216_015
EXPECTED_MD5 = "af26192c9349150071e4e4f40ba1f456"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    start = TARGET.stat().st_size if TARGET.exists() else 0
    if start < EXPECTED_SIZE:
        with requests.get(
            URL,
            headers={"Range": f"bytes={start}-"},
            stream=True,
            timeout=(20, 120),
        ) as response:
            response.raise_for_status()
            if start and response.status_code != 206:
                raise RuntimeError("Server did not honor resume range")
            t0 = time.monotonic()
            last_print = t0
            with TARGET.open("ab" if start else "wb") as output:
                for block in response.iter_content(chunk_size=4 * 1024 * 1024):
                    if block:
                        output.write(block)
                        start += len(block)
                    now = time.monotonic()
                    if now - last_print > 15:
                        print(f"downloaded {start / 1e9:.3f}/{EXPECTED_SIZE / 1e9:.3f} GB", flush=True)
                        last_print = now
            print(f"download seconds: {time.monotonic() - t0:.1f}", flush=True)
    if TARGET.stat().st_size != EXPECTED_SIZE:
        raise RuntimeError(f"Unexpected archive size: {TARGET.stat().st_size}")
    digest = hashlib.md5()
    with TARGET.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != EXPECTED_MD5:
        raise RuntimeError(f"Archive MD5 mismatch: {digest.hexdigest()}")
    print(f"verified {TARGET} MD5 {digest.hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
