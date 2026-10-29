"""Build the FRA mangrove overlap table from 2025 country reports.

Exact national-class matches explicitly assigned 100% to FRA Forest are removed
from GCW. Quantitative Forest/Other wooded land splits are also applied when the
report provides a defensible classification basis for the FRA 2025 series. An
explicit 100% Other wooded land case remains zero forest overlap. Other cases stay
unresolved and are not automatically subtracted from FRA forest area.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "data/outputs/validation/fra_2025_mangrove_report_audit.csv"
OUTPUT = ROOT / "data/derived/fra_mangrove_forest_overlap_2025.csv"

# In each case below, the FRA 2025 country report contains the same national
# mangrove area as the FRA bulk table, to the report's published precision, and
# assigns that class to Forest.
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
    "BRA": "Report 2025 crosswalk: Manguezal 1,394.68 kha; 100% Forest, 0% OWL.",
    "GAB": "Report 2025 crosswalk: Mangrove 190.64 kha; 100% Forest, 0% OWL; FRA bulk value is 190.63 kha after rounding.",
    "MTQ": "Report 2025 crosswalk: Mangrove 2.21 kha; 100% Forest, 0% OWL.",
}

# These cases have an explicit Forest classification, but the report applies a
# stable classification to a 2025 value copied, forecast, or extrapolated from
# an earlier inventory. They are retained in the main estimate with that
# harmonisation assumption stated in the evidence note.
FOREST_100_STABLE = {
    "BGD": "Report crosswalk: 2015 Mangrove Plantation 55.10 kha and Mangrove Forest 402.18 kha are both 100% Forest; the report states that 2020 and 2025 are unchanged, giving 457.27 kha in 2025.",
    "BRN": "Report national class: Mangrove Forest; 18.42 kha is reported for 2025 and the report states that selective harvesting does not change its FRA forest category.",
    "FJI": "Report 2025 comment: mangrove area 47.25 kha is included in the forest area because it is detected as forest under the new forest-detection methodology.",
    "GHA": "Report crosswalk: Mangrove is 100% Forest in the latest mapped years; the 4.90 kha 2025 value is extrapolated from the national mangrove series under the same class.",
    "IND": "Report states that national and FRA classifications are the same; the Mangrove class is 100% Forest in the crosswalk and the 504.00 kha 2025 value is forecast from the same series.",
    "LKA": "Report reclassification table: Mangroves are 100% Forest, 0% OWL and 0% remaining land; the 2025 series reports 19.51 kha.",
    "PHL": "Report states that all mangrove areas are considered Forest; the 319.41 kha 2025 value is extrapolated from the national land-cover series.",
    "THA": "Report states that Thailand's forest area includes the mangrove area; the 2025 series reports 277.92 kha, repeated from the 2020 assessment.",
    "TZA": "Report biomass-area table identifies 158,405 ha as Forest: Mangrove; the FRA 2025 mangrove series reports 158.10 kha for 2015-2025.",
    "VUT": "Report reclassification: Mangrove Forest are Forest dominated with Mangrove species; the manual delineation used for the 2025 series reports 3.02 kha.",
    "WLF": "Report crosswalk: 0.03 kha of Mangrove is 100% Forest; the report repeats the 2018 data through 2025.",
}
OWL_100 = {
    "LCA": "Report crosswalk: Mangrove 0.22 kha; 0% Forest, 100% Other wooded land.",
}
AMBIGUOUS = {
    "PAK": "FRA report gives 164.53 kha for 2025 and says the mangrove category includes Forest and OWL; earlier class mapping does not quantify the 2025 split.",
    "SHN": "FRA report reclassifies 2.00 kha as Forest but says it may include OWL; 1980/2008 data are reused for all reporting years.",
    "TCA": "FRA report says 23.60 kha is mainly shrubby mangrove in OWL, but does not quantify the Forest subset.",
}

# Mozambique's FRA 2025 report gives a national Mangrove class of 297.89 kha
# with 80% Forest and 20% Other wooded land. FRA's 2025 mangrove series for
# Mozambique is generated from the same national inventory series and reports
# 359.81 kha for 2025. We apply the reported classification fraction to the
# 2025 category, while keeping the stability assumption explicit in the table.
FRACTIONAL_FOREST = {
    "MOZ": {
        "fraction": 0.8,
        "other_fraction": 0.2,
        "remaining_fraction": 0.0,
        "evidence": (
            "FRA 2025 report: 2018 national Mangrove class 297.89 kha, 80% Forest "
            "and 20% Other wooded land. The FRA 2025 mangrove series is derived "
            "from the same national inventory series and reports 359.81 kha for "
            "2025; apply the 80/20 split to 2025 under a classification-stability "
            "assumption."
        ),
    },
    "MYT": {
        "fraction": 0.48,
        "other_fraction": 0.455,
        "remaining_fraction": 0.065,
        "evidence": (
            "Report 2025 crosswalk: 0.65 kha of Mangrove is split into 48.0% "
            "Forest, 45.5% Other wooded land and 6.5% Remaining land."
        ),
    },
}


def main() -> None:
    audit = pd.read_csv(AUDIT)
    rows = []
    for _, row in audit.iterrows():
        iso = str(row["iso3"])
        area = float(row["fra_mangroves_ha"])
        note = str(row.get("explicit_classification_excerpts", "") or "")
        if not note or note.lower() == "nan":
            note = str(row.get("forest_owl_table_evidence", "") or "")
        if iso in FOREST_100:
            status, fraction, other_fraction, remaining_fraction, amount, other_amount, remaining_amount, unknown_amount, evidence = (
                "documented_all_forest", 1.0, 0.0, 0.0, area, 0.0, 0.0, 0.0, FOREST_100[iso]
            )
        elif iso in FOREST_100_STABLE:
            status, fraction, other_fraction, remaining_fraction, amount, other_amount, remaining_amount, unknown_amount, evidence = (
                "documented_all_forest_stability_assumption", 1.0, 0.0, 0.0, area, 0.0, 0.0, 0.0, FOREST_100_STABLE[iso]
            )
        elif iso in OWL_100:
            status, fraction, other_fraction, remaining_fraction, amount, other_amount, remaining_amount, unknown_amount, evidence = (
                "documented_all_other_wooded_land", 0.0, 1.0, 0.0, 0.0, area, 0.0, 0.0, OWL_100[iso]
            )
        elif iso in FRACTIONAL_FOREST:
            fraction = float(FRACTIONAL_FOREST[iso]["fraction"])
            other_fraction = float(FRACTIONAL_FOREST[iso]["other_fraction"])
            remaining_fraction = float(FRACTIONAL_FOREST[iso]["remaining_fraction"])
            status = "documented_fractional_forest"
            amount = area * fraction
            other_amount = area * other_fraction
            remaining_amount = area * remaining_fraction
            unknown_amount = area * max(0.0, 1.0 - fraction - other_fraction - remaining_fraction)
            evidence = FRACTIONAL_FOREST[iso]["evidence"]
        elif iso in AMBIGUOUS:
            status, fraction, other_fraction, remaining_fraction, amount, other_amount, remaining_amount, unknown_amount, evidence = (
                "unresolved_split", None, None, None, 0.0, 0.0, 0.0, area, AMBIGUOUS[iso]
            )
        else:
            status, fraction, other_fraction, remaining_fraction, amount, other_amount, remaining_amount, unknown_amount, evidence = (
                "no_exact_forest_split_verified", None, None, None, 0.0, 0.0, 0.0, area,
                "No matching exact national Forest/OWL area split was verified in the report audit.",
            )
        rows.append(
            {
                "iso3": iso,
                "fra_mangroves_2025_ha": area,
                "documented_forest_fraction": fraction,
                "documented_forest_mangrove_area_ha": amount,
                "documented_other_wooded_land_fraction": other_fraction,
                "documented_other_wooded_land_area_ha": other_amount,
                "documented_remaining_land_fraction": remaining_fraction,
                "documented_remaining_land_area_ha": remaining_amount,
                "unresolved_mangrove_area_ha": unknown_amount,
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
    if (
        result["documented_forest_mangrove_area_ha"]
        + result["documented_other_wooded_land_area_ha"]
        + result["documented_remaining_land_area_ha"]
        + result["unresolved_mangrove_area_ha"]
        - result["fra_mangroves_2025_ha"]
    ).abs().max() > 1e-6:
        raise ValueError("Forest, Other wooded land and unresolved parts must sum to the FRA mangrove category")
    for column in (
        "documented_forest_fraction",
        "documented_other_wooded_land_fraction",
        "documented_remaining_land_fraction",
    ):
        if ((result[column].notna()) & ~result[column].between(0, 1)).any():
            raise ValueError(f"{column} values must lie between 0 and 1")
    known_fraction = result["documented_forest_fraction"].notna() & result["documented_other_wooded_land_fraction"].notna()
    fraction_sum = (
        result["documented_forest_fraction"].fillna(0.0)
        + result["documented_other_wooded_land_fraction"].fillna(0.0)
        + result["documented_remaining_land_fraction"].fillna(0.0)
    )
    if (fraction_sum[known_fraction] > 1 + 1e-9).any():
        raise ValueError("Documented Forest, Other wooded land and remaining-land fractions cannot exceed 1")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(result)} country rows; documented Forest overlap: "
          f"{result['documented_forest_mangrove_area_ha'].sum():,.0f} ha")
    print(result["overlap_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
