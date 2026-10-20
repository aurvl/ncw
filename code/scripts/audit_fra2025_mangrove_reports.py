"""Search public FRA 2025 country reports for mangrove/forest classification evidence.

The bulk FRA table reports mangroves as a national category but does not partition
that area between Forest and Other wooded land. This audit retrieves the public
country-report OCR text and preserves short, linked excerpts for manual verification.
It does not infer a forest subset automatically from keyword co-occurrence.
"""

from __future__ import annotations

import csv
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
FRA_ZIP = ROOT / "data/raw/environmental/forest/fra/fra2025_bulk_WO.zip"
OUT = ROOT / "results/validation/fra_2025_mangrove_report_audit.csv"
REPORTS_URL = "https://www.fao.org/forest-resources-assessment/fra-2025-country-reports/"
API = "https://openknowledge.fao.org/server/api"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"}


class ReportLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            href = urljoin(REPORTS_URL, self._href)
            if "20.500.14283/" in href:
                self.links.append({"name": " ".join("".join(self._text).split()), "url": href})
            self._href = None
            self._text = []


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def get(session: requests.Session, url: str) -> requests.Response:
    last: Exception | None = None
    for attempt in range(4):
        try:
            response = session.get(url, timeout=(15, 90), headers=HEADERS)
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001 - retry public API/network failures
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}: {last}")


def extract_text_url(session: requests.Session, report_url: str) -> tuple[str, str, str]:
    handle = urlparse(report_url).path.rstrip("/").split("/")[-1]
    pid_url = f"{API}/pid/find?id={quote('20.500.14283/' + handle, safe='')}"
    item = get(session, pid_url).json()
    item_id = item["id"]
    bundles_response = get(session, f"{API}/core/items/{item_id}/bundles").json()
    bundles = bundles_response.get("_embedded", {}).get("bundles", [])
    text_bundle = next((bundle for bundle in bundles if bundle.get("name", "").upper() == "TEXT"), None)
    if text_bundle is None:
        raise RuntimeError("No OCR TEXT bundle")
    bitstreams_response = get(session, text_bundle["_links"]["bitstreams"]["href"]).json()
    bitstreams = bitstreams_response.get("_embedded", {}).get("bitstreams", [])
    if not bitstreams:
        raise RuntimeError("Empty OCR TEXT bundle")
    bitstream = next(
        (entry for entry in bitstreams if entry.get("name", "").lower().endswith(".txt")),
        bitstreams[0],
    )
    content_url = bitstream.get("_links", {}).get("content", {}).get("href")
    if not content_url:
        raise RuntimeError("OCR text content URL unavailable")
    return item.get("name", ""), handle, content_url


KEY_RE = re.compile(r"mangrove|manguez|manglar|manglier|mangle|mangrove|mangal|mangrov", re.IGNORECASE)
CLASS_RE = re.compile(
    r"other\s+wooded\s+land|forest\s+area|classified\s+as\s+forest|included\s+in\s+forest|"
    r"not\s+included\s+in\s+forest|forest\s+category|forest\s+type|1c\s*mangrove|1c\s*extent",
    re.IGNORECASE,
)


def make_excerpts(text: str, max_items: int = 8) -> tuple[str, str, int]:
    text = text.replace("\x00", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    hits: list[str] = []
    for index, line in enumerate(lines):
        if not KEY_RE.search(line):
            continue
        start, end = max(index - 1, 0), min(index + 2, len(lines))
        frag = " | ".join(lines[start:end])
        if CLASS_RE.search(frag) or re.search(r"1c|classification|definition|source", frag, re.I):
            if frag not in hits:
                hits.append(frag[:1200])
        if len(hits) >= max_items:
            break
    # Keep a broader first-occurrence excerpt if classification terms were not found.
    if not hits:
        for index, line in enumerate(lines):
            if KEY_RE.search(line):
                hits.append(" | ".join(lines[max(index - 1, 0):min(index + 2, len(lines))])[:1200])
                if len(hits) == 3:
                    break
    explicit = [frag for frag in hits if CLASS_RE.search(frag)]
    return "\n---\n".join(hits), "\n---\n".join(explicit), len(list(KEY_RE.finditer(text)))


def forest_owl_table_evidence(text: str) -> str:
    """Extract national-class crosswalk snippets that allocate classes to FRA Forest/OWL."""
    lines = [line.strip() for line in text.replace("\x00", " ").replace("\r", "\n").splitlines() if line.strip()]
    snippets: list[str] = []
    for start in range(len(lines)):
        header = " ".join(lines[start : min(start + 3, len(lines))])
        if not (
            re.search(r"class area", header, re.I)
            and re.search(r"forest", header, re.I)
            and re.search(r"other\s+wooded", header, re.I)
        ):
            continue
        end = min(start + 60, len(lines))
        for index in range(start + 1, end):
            if re.search(r"\bmangrove", lines[index], re.I):
                snippets.append(" | ".join(lines[max(start, index - 2) : min(end, index + 5)])[:1600])
        if len(snippets) >= 12:
            break
    if not snippets:
        for match in re.finditer(r"(?is)(class area.{0,700}?mangrove.{0,900})", text):
            snippets.append(" ".join(match.group(1).split())[:1600])
            if len(snippets) >= 12:
                break
    return "\n---\n".join(dict.fromkeys(snippets))


def main() -> None:
    with zipfile_open(FRA_ZIP) as archive:
        name = next(path for path in archive.namelist() if "1c_mangroves_" in path)
        mangroves = pd.read_csv(archive.open(name))
    records = mangroves.loc[
        mangroves["2025"].fillna(0).gt(0),
        ["iso3", "name", "2025", "Desk study"],
    ].copy()
    records["fra_mangroves_ha"] = records["2025"] * 1000.0
    records = records.drop(columns="2025")

    session = requests.Session()
    page = get(session, REPORTS_URL).text
    parser = ReportLinkParser()
    parser.feed(page)
    by_name: dict[str, dict[str, str]] = {}
    for entry in parser.links:
        key = norm(entry["name"])
        if key and key not in by_name:
            by_name[key] = entry
    def fetch_one(row: dict[str, object]) -> dict[str, str]:
        country = str(row["name"])
        key = norm(country)
        entry = by_name.get(key)
        if entry is None:
            return {"iso3": str(row["iso3"]), "report_status": "no matching FRA report link found"}
        local = requests.Session()
        try:
            title, handle, text_url = extract_text_url(local, entry["url"])
            text = get(local, text_url).content.decode("utf-8", errors="replace")
            excerpts, explicit, count = make_excerpts(text)
            return {
                "iso3": str(row["iso3"]), "report_name": entry["name"], "report_handle": handle,
                "report_title": title, "report_text_url": text_url, "report_status": f"text retrieved; {count} keyword hits",
                "excerpts": excerpts, "explicit_classification_excerpts": explicit,
                "forest_owl_table_evidence": forest_owl_table_evidence(text),
            }
        except Exception as exc:  # noqa: BLE001 - retain per-report errors for audit
            return {
                "iso3": str(row["iso3"]), "report_name": entry["name"],
                "report_handle": urlparse(entry["url"]).path.rstrip("/").split("/")[-1],
                "report_status": f"retrieval error: {type(exc).__name__}: {exc}",
            }

    results: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_one, row) for row in records.to_dict("records")]
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 10 == 0 or index == len(futures):
                print(f"Processed public FRA 2025 reports: {index}/{len(futures)}", flush=True)
    report_data = pd.DataFrame(results)
    output = records.merge(report_data, on="iso3", how="left")
    output.to_csv(OUT, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"Wrote {len(output)} mangrove-positive country rows to {OUT}")
    print(output["report_status"].fillna("no report result").value_counts().to_string())


class zipfile_open:
    """Tiny context wrapper to keep the stdlib zipfile import local to this script."""

    def __init__(self, path: Path) -> None:
        import zipfile

        self.archive = zipfile.ZipFile(path)

    def __enter__(self):
        return self.archive

    def __exit__(self, exc_type, exc, tb):
        self.archive.close()


if __name__ == "__main__":
    main()
