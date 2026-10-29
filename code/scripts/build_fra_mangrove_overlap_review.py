"""Build a country-by-country review table for FRA mangrove classification evidence.

The report audit stores public FRA country-report excerpts. This script parses every
retained Forest/Other wooded land crosswalk row, compares its area with the FRA 2025
bulk mangrove value, and records whether the row was used in the main overlap table.
It is a screening aid: the explicit country decisions remain documented in
``build_fra_mangrove_forest_overlap.py`` and require scientific review before reuse.
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
REPORT_AUDIT = ROOT / "results/validation/fra_2025_mangrove_report_audit.csv"
OVERLAP = ROOT / "data/derived/fra_mangrove_forest_overlap_2025.csv"
OUTPUT = ROOT / "results/validation/fra_mangrove_overlap_review.csv"
SUMMARY = ROOT / "results/validation/fra_mangrove_overlap_review.md"

MANGROVE_RE = re.compile(r"mangrove|manguez|manglar|mangal", re.IGNORECASE)
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/plain"}
ROW_RE = re.compile(
    r"(?P<label>mangrove[^|\n]{0,100}?)\s+"
    r"(?P<area>[0-9][0-9\s,\u00a0�.]*?)\s+"
    r"(?P<forest>[0-9]+(?:[.,][0-9]+)?)\s*%\s+"
    r"(?P<owl>[0-9]+(?:[.,][0-9]+)?)\s*%\s+"
    r"(?P<remaining>[0-9]+(?:[.,][0-9]+)?)\s*%",
    re.IGNORECASE,
)


def parse_number(value: str) -> float | None:
    """Parse OCR numbers with spaces, replacement separators or decimal commas."""
    cleaned = value.replace("\u00a0", "").replace("�", "").replace(" ", "")
    if "," in cleaned and "." not in cleaned and cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_rows(evidence: str) -> list[dict[str, float | str]]:
    """Extract mangrove rows with Forest/OWL/remaining percentages from excerpts."""
    rows: list[dict[str, float | str]] = []
    for segment in str(evidence).split("|"):
        if not MANGROVE_RE.search(segment):
            continue
        match = ROW_RE.search(segment)
        if match is None:
            continue
        area = parse_number(match.group("area"))
        if area is None:
            continue
        rows.append(
            {
                "class_name": " ".join(match.group("label").split()),
                "report_area_kha": area,
                "forest_fraction": parse_number(match.group("forest")) / 100.0,
                "owl_fraction": parse_number(match.group("owl")) / 100.0,
                "remaining_fraction": parse_number(match.group("remaining")) / 100.0,
            }
        )
    unique: list[dict[str, float | str]] = []
    for row in rows:
        if row not in unique:
            unique.append(row)
    return unique


def candidate_summary(rows: list[dict[str, float | str]], fra_area_kha: float) -> tuple[str, float | None, float | None]:
    """Return compact candidate text plus the closest area and ratio."""
    if not rows:
        return "", None, None
    ranked = sorted(rows, key=lambda row: abs(float(row["report_area_kha"]) - fra_area_kha))
    best = ranked[0]
    best_area = float(best["report_area_kha"])
    summary = "; ".join(
        f"{row['class_name']}={float(row['report_area_kha']):g} kha "
        f"(F={float(row['forest_fraction']):.3g}, OWL={float(row['owl_fraction']):.3g}, "
        f"remaining={float(row['remaining_fraction']):.3g})"
        for row in ranked[:5]
    )
    return summary, best_area, best_area / fra_area_kha if fra_area_kha else None


def fetch_report(row: pd.Series) -> tuple[str, str]:
    """Fetch one public OCR report, returning an empty string after retries."""
    url = str(row.get("report_text_url", ""))
    if not url:
        return str(row["iso3"]), ""
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=(15, 90))
            response.raise_for_status()
            return str(row["iso3"]), response.content.decode("utf-8", errors="replace")
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1.0 + attempt)
    return str(row["iso3"]), ""


def main() -> None:
    """Write the complete country-level screening table and a short audit summary."""
    audit = pd.read_csv(REPORT_AUDIT).fillna("")
    overlap = pd.read_csv(OVERLAP).drop_duplicates("iso3")
    with ThreadPoolExecutor(max_workers=12) as pool:
        report_text = dict(pool.map(fetch_report, [row for _, row in audit.iterrows()]))
    rows = []
    for _, source in audit.iterrows():
        iso3 = str(source["iso3"])
        fra_area_kha = float(source["fra_mangroves_ha"]) / 1000.0
        evidence = report_text.get(iso3, "") or str(source.get("forest_owl_table_evidence", ""))
        candidates = extract_rows(evidence)
        summary, best_area, best_ratio = candidate_summary(candidates, fra_area_kha)
        status = str(overlap.loc[overlap["iso3"].eq(iso3), "overlap_status"].iloc[0])
        direct_text = report_text.get(iso3, "") or " ".join(
            str(source.get(column, "")) for column in ("explicit_classification_excerpts", "excerpts")
        )
        direct_signal = ""
        if re.search(r"included in the forest|all mangrove.*forest|mangrove forest are forest|forest:\s*mangrove", direct_text, re.I):
            direct_signal = "direct Forest-inclusion statement"
        if "documented" in status:
            outcome = "applied_in_main"
        elif best_ratio is not None and 0.95 <= best_ratio <= 1.05:
            outcome = "candidate_not_applied_review"
        elif candidates or direct_signal:
            outcome = "classification_evidence_not_comparable"
        else:
            outcome = "no_quantified_crosswalk_retained"
        rows.append(
            {
                "iso3": iso3,
                "name": source["name"],
                "fra_mangroves_2025_ha": float(source["fra_mangroves_ha"]),
                "report_classification_rows": len(candidates),
                "closest_report_area_kha": best_area,
                "closest_area_ratio_to_fra_2025": best_ratio,
                "classification_candidates": summary,
                "direct_signal": direct_signal,
                "report_text_retrieved": bool(report_text.get(iso3)),
                "main_overlap_status": status,
                "audit_outcome": outcome,
                "fra_report_url": f"https://openknowledge.fao.org/handle/20.500.14283/{str(source.get('report_handle', '')).lower()}",
            }
        )
    result = pd.DataFrame(rows).sort_values("iso3")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False, lineterminator="\n")
    counts = result["audit_outcome"].value_counts().to_dict()
    applied = result.loc[result["audit_outcome"].eq("applied_in_main")]
    review = result.loc[result["audit_outcome"].eq("candidate_not_applied_review")]
    report = [
        "# FRA 2025 mangrove Forest/OWL report review",
        "",
        f"The public FRA 2025 report audit covers {len(result)} mangrove-positive units. "
        "This table parses every retained national-class Forest/OWL crosswalk excerpt, "
        "rather than stopping at the first few report snippets.",
        "",
        "## Screening counts",
        "",
        *[f"- `{key}`: {value}" for key, value in sorted(counts.items())],
        "",
        "## Units applied in the main overlap table",
        "",
        ", ".join(applied["iso3"].tolist()) or "None",
        "",
        "## Near-area candidates not applied",
        "",
    ]
    if review.empty:
        report.append("None.")
    else:
        report.extend(
            f"- **{row.iso3} ({row['name']})**: closest report/FRA area ratio "
            f"{row.closest_area_ratio_to_fra_2025:.3f}; {row.classification_candidates}"
            for _, row in review.iterrows()
        )
    SUMMARY.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote {len(result)} country rows to {OUTPUT}")
    print(result["audit_outcome"].value_counts().to_string())


if __name__ == "__main__":
    main()
