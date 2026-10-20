"""Build the conservative FRA mangrove overlap table from 2025 country reports.

Only exact national-class area matches explicitly assigned 100% to FRA Forest are
removed from GCW. An explicit 100% Other wooded land case is retained as zero
forest overlap. All other cases remain unresolved and are not automatically
subtracted from FRA forest area.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "results/validation/fra_2025_mangrove_report_audit.csv"
OUTPUT = ROOT / "data/derived/fra_mangrove_forest_overlap_2025.csv"

# In each case below, the FRA 2025 country report contains the same national
# mangrove area as the FRA bulk table and assigns that class to Forest.
FOREST_100 = {
    "BHS": "Report crosswalk: Mangroves 141.96 kha; 100% Forest, 0% OWL.",
    "KEN": "Report crosswalk: Mangroves 61.27 kha; 100% Forest, 0% OWL.",
    "KIR": "Report crosswalk: Mangrove 1.07 kha; 100% Forest, 0% OWL; FRA source marked desk study.",
    "PNG": "Report crosswalk: Mangrove 285.97 kha; 100% Forest, 0% OWL.",
    "VCT": "Report crosswalk: Mangrove 0.04 kha; 100% Forest, 0% OWL.",
    "WSM": "Report crosswalk: Mangrove Forest 0.35 kha; 100% Forest, 0% OWL.",
    "SGP": "Report crosswalk: Mangrove Forest 0.84 kha; 100% Forest, 0% OWL.",
    "TLS": "Report crosswalk: Mangroves forest 2.13 kha; 100% Forest, 0% OWL.",
    "TON": "Report crosswalk: Mangroves and wetland 1.77 kha; 100% Forest, 0% OWL.",
}
OWL_100 = {
    "LCA": "Report crosswalk: Mangrove 0.22 kha; 0% Forest, 100% Other wooded land.",
}
AMBIGUOUS = {
    "PAK": "FRA report gives 164.53 kha for 2025 and says the mangrove category includes Forest and OWL; earlier class mapping does not quantify the 2025 split.",
    "SHN": "FRA report reclassifies 2.00 kha as Forest but says it may include OWL; 1980/2008 data are reused for all reporting years.",
    "TCA": "FRA report says 23.60 kha is mainly shrubby mangrove in OWL, but does not quantify the Forest subset.",
}


def main() -> None:
    audit = pd.read_csv(AUDIT)
    rows = []
    for _, row in audit.iterrows():
        iso = str(row["iso3"])
        area = float(row["fra_mangroves_ha"])
        note = str(row.get("explicit_classification_excerpts", "") or "")
        if iso in FOREST_100:
            status, fraction, amount, evidence = "documented_all_forest", 1.0, area, FOREST_100[iso]
        elif iso in OWL_100:
            status, fraction, amount, evidence = "documented_all_other_wooded_land", 0.0, 0.0, OWL_100[iso]
        elif iso in AMBIGUOUS:
            status, fraction, amount, evidence = "unresolved_split", None, 0.0, AMBIGUOUS[iso]
        else:
            status, fraction, amount, evidence = "no_exact_forest_split_verified", None, 0.0, "No matching exact national Forest/OWL area split was verified in the report audit."
        rows.append(
            {
                "iso3": iso,
                "fra_mangroves_2025_ha": area,
                "documented_forest_fraction": fraction,
                "documented_forest_mangrove_area_ha": amount,
                "overlap_status": status,
                "desk_study": row["Desk study"],
                "fra_report_handle": row.get("report_handle", ""),
                "fra_report_url": f"https://openknowledge.fao.org/handle/20.500.14283/{str(row.get('report_handle', '')).lower()}",
                "evidence_note": evidence,
                "report_excerpt": note[:1200],
            }
        )
    result = pd.DataFrame(rows).sort_values("iso3")
    if result["iso3"].duplicated().any():
        raise ValueError("FRA mangrove overlap audit has duplicate country rows")
    if (result["documented_forest_mangrove_area_ha"] > result["fra_mangroves_2025_ha"] + 1e-6).any():
        raise ValueError("Documented forest subset cannot exceed FRA mangrove category area")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(result)} country rows; documented Forest overlap: "
          f"{result['documented_forest_mangrove_area_ha'].sum():,.0f} ha")
    print(result["overlap_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
