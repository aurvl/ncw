"""Refresh existing PAPER results with the current GMW/FRA/Gibbs outputs.

The edit is deliberately limited to the manuscript's existing claims, their
current values, and method sentences that describe the now-selected mangrove
accounting rule. Existing figures are kept byte-for-byte for the author's
later figure-update pass. Every replacement is recorded as a Word revision.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT.parent / "NEXT" / "PAPER.docx"
BACKUP = ROOT / "results" / "validation" / "PAPER_before_current_results_refresh.docx"
sys.path.insert(0, str(ROOT / "scripts"))
from sync_paper_results import PaperEditor, W, visible_text  # noqa: E402


def main() -> None:
    if not PAPER.is_file():
        raise FileNotFoundError(PAPER)
    if BACKUP.exists():
        raise FileExistsError(f"Refusing to overwrite existing backup: {BACKUP}")
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PAPER, BACKUP)

    with zipfile.ZipFile(PAPER, "r") as source:
        package = {name: source.read(name) for name in source.namelist()}
    original_images = {
        name: content
        for name, content in package.items()
        if name.startswith("word/media/")
    }
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    document = etree.fromstring(package["word/document.xml"], parser)
    editor = PaperEditor(document)

    # Abstract: value and flow totals, biome shares, balance classification,
    # and current deforestation-capacity value.
    editor.replace_paragraph(
        "Forests and marine ecosystems contribute to climate regulation, yet their annual contributions",
        "Forests and marine ecosystems contribute to climate regulation, yet their annual contributions to national wealth and the distributional consequences of their loss remain incompletely quantified. Here we estimate the annual welfare value assigned to gross carbon additions to living forest biomass for 236 forest units within a harmonized framework of 266 countries and territories. We combine this estimate with published marine carbon values and national emissions, economic, and deforestation data. The forest account estimates 14.73 GtCO₂ per year of gross additions to living biomass and GCW of US$8.24 [3.22-14.97] trillion per year in constant 2015 dollars. This represents 78.0% of the combined forest and marine value. Tropical, subtropical, temperate, and boreal forests contribute 44.7%, 15.9%, 21.9%, and 17.5% of estimated forest additions, respectively. Forest value is particularly large relative to recorded economic output in least developed countries. Adding marine flows raises the share of accounting units with positive annual balances against fossil-fuel and industrial CO₂ emissions from 38% to 54%. Reported deforestation across 139 units corresponds to 34.83 MtCO₂ per year of modeled annual forest-addition capacity no longer supplied, valued at US$19.49 billion per year. Illustrative replacement-cost scenarios using abatement prices of US$50-400 per tCO₂ imply costs of US$1.74-13.93 billion per year; domestic allocation produces the highest relative burdens in least developed countries. These results distinguish annual ecosystem-service values, lost capacity, and hypothetical mitigation costs.",
        label="Abstract current-result values",
        anchors=[
            ("44", "the annual welfare value assigned to gross carbon additions to living forest biomass"),
            ("47", "The forest account estimates 14.73 GtCO₂ per year of gross additions to living biomass and GCW of US$8.24 [3.22-14.97] trillion per year in constant 2015 dollars."),
            ("48", "This represents 78.0% of the combined forest and marine value."),
            ("55", "Reported deforestation across 139 units corresponds to 34.83 MtCO₂ per year of modeled annual forest-addition capacity no longer supplied, valued at US$19.49 billion per year."),
            ("57", "Illustrative replacement-cost scenarios using abatement prices of US$50-400 per tCO₂ imply costs of US$1.74-13.93 billion per year; domestic allocation produces the highest relative burdens in least developed countries."),
        ],
    )

    # Core Results values.
    editor.replace_paragraph(
        "The country account estimates 14.68 GtCO₂ per year",
        "The country account estimates 14.73 GtCO₂ per year of gross carbon additions to living forest biomass, equivalent to 4.02 GtC per year. This flow is assigned GCW of US$8.24 [3.22-14.97] trillion per year. The marine account, with its mangrove area updated using GMW 2025, contributes BCW of US$2.33 [0.91-4.30] trillion, bringing NCW to US$10.57 [4.16-19.17] trillion per year. Forests account for 78.0% of the mean combined value (Table 1). These annual values represent the welfare value assigned to the modeled flows; they are not estimates of carbon stocks, national income, or financing entitlements.",
        label="Results global account",
    )
    editor.update_table(
        "Component",
        {
            "Green carbon wealth": ["8.24", "3.22-14.97", "78.0"],
            "Blue carbon wealth": ["2.33", "0.91-4.30", "22.0"],
            "Natural carbon wealth": ["10.57", "4.16-19.17", "100.0"],
        },
        second_cell="Mean (trillion 2015 US$/year)",
        label="Table 1 current values",
    )
    editor.replace_paragraph(
        "The forest account uses four biome-specific rates",
        "The forest account uses four biome-specific rates estimated from Gibbs/GFW pixels after excluding pixels classified as mangroves by the source model: 0.934 tC ha⁻¹ yr⁻¹ for tropical, 1.371 for subtropical, 1.430 for temperate, and 0.619 for boreal forests. Applied to the allocated forest areas used in the country calculation-1,923.6, 464.8, 616.4, and 1,135.2 Mha, respectively-these rates yield 44.7%, 15.9%, 21.9%, and 17.5% of estimated global living-biomass additions (Supplementary Section S3). The resulting shares combine modeled average rates with allocated forest areas; they are not direct observations of each country's annual forest growth.",
        label="Results four-biome decomposition",
    )
    editor.replace_paragraph(
        "The estimated forest value was distributed across all four economic groups",
        "The estimated forest value was distributed across all four economic groups. Developed economies supplied US$3.61 trillion per year of GCW (43.7% of the total), developing economies US$3.42 trillion (41.5%), least developed countries (LDCs) US$1.05 trillion (12.8%), and Small Island Developing States (SIDS) US$0.16 trillion (2.0%) (Table 2). Median GCW-to-GDP ratios were 4.0% in developed economies, 8.7% in developing economies, 54.6% in LDCs, and 4.4% in SIDS. These ratios describe the estimated annual service value relative to the scale of recorded economic output; they are not shares of GDP produced by forests or income transferred to countries. Group distributions differed significantly (Kruskal-Wallis H = 36.84, p = 4.97 × 10⁻⁸; Supplementary Section S6).",
        label="Results group wealth and ratio explanation",
        anchors=[("153", "These ratios describe the estimated annual service value relative to the scale of recorded economic output; they are not shares of GDP produced by forests or income transferred to countries.")],
    )
    editor.replace_paragraph(
        "GCW was highly concentrated across accounting units",
        "GCW was highly concentrated across accounting units. The Russian Federation had the largest estimated value (US$1.21 trillion per year), followed by Brazil (US$0.94 trillion) and the United States (US$0.82 trillion). The ten largest units accounted for 64.1% of global GCW, and the Gini coefficient was 0.866. Figure 1a shows the relationship between GCW and GDP; their rank correlation was positive (Spearman ρ = 0.605, p = 2.17 × 10⁻²¹, n = 200). Figure 1b shows stronger concentration in GCW (Gini 0.866) than in BCW (Gini 0.763). These national and territorial units are spatial attribution units for the estimated flows.",
        label="Results concentration and GDP association",
    )
    editor.update_table(
        "Group",
        {
            "Developed economies": ["3.61", "43.7", "4.0", "22", "9"],
            "Developing economies": ["3.42", "41.5", "8.7", "30", "16"],
            "LDCs": ["1.05", "12.8", "54.6", "12", "3"],
            "SIDS": ["0.16", "2.0", "4.4", "8", "37"],
        },
        second_cell="GCW (trillion 2015 US$/year)",
        label="Table 2 current values",
    )

    editor.replace_paragraph(
        "Adding the published marine account changed the composition",
        "Adding the published marine account changed the composition of carbon wealth among the 242 units with at least one component available. Both components were available for 175 units: 72 were green-dominant, 65 blue-dominant, and 38 mixed under the two-thirds dominance threshold. SIDS had 37 blue-dominant and 8 green-dominant units, whereas LDCs had 12 and 3; developed economies had 22 and 9, and developing economies 30 and 16, respectively (Table 2; Figure 2a). The composition reflects the geography of forest areas and marine accounting values; the two physical flows are not interchangeable.",
        label="Results green-blue composition",
    )
    editor.replace_paragraph(
        "The marine component also changed national annual accounting balances",
        "The marine component also changed national annual accounting balances. Among 210 accounting units with emissions and flow estimates, the share classified as net sinks under the accounted CO₂ boundary rose from 38% with forests alone to 54% with forests and marine flows. The ten largest emitting units accounted for 71.9% of global emissions; the ten largest flow-attribution units outside that emitter group accounted for 32.3% of global accounted removals (Figure 2b). These are territorial attribution results, not a claim that governments or territories are the ecological agents producing every flow. A positive annual balance under the selected boundary does not establish a trajectory compatible with climate neutrality.",
        label="Results annual balances and flow concentration",
        anchors=[
            ("156", "accounting units"),
            ("157", "net sinks under the accounted CO₂ boundary"),
            ("158", "A positive annual balance under the selected boundary does not establish a trajectory compatible with climate neutrality."),
        ],
    )

    editor.replace_paragraph(
        "FRA-reported deforestation averaged 9.70 Mha per year",
        "FRA-reported deforestation averaged 9.70 Mha per year over 2010-2020. Across reporting units, converted area corresponded to 34.83 MtCO₂ per year of modeled annual forest-addition capacity no longer supplied, valued at US$19.49 billion per year (Table 3). The estimated annual value loss was 0.30% of the GCW reported for those units. Brazil had the largest estimated annual value loss (US$4.41 billion), followed by India (US$1.34 billion), the Democratic Republic of the Congo (US$1.24 billion), Australia (US$1.05 billion), and Indonesia (US$1.04 billion; Supplementary country-level erosion table). This is foregone future addition capacity after conversion, not an estimate of emissions from carbon already stored in vegetation or soils. The estimates cover 139 of 236 forest units, representing 78.7% of global GCW.",
        label="Results deforestation totals and coverage",
        anchors=[("161", "The estimates cover 139 of 236 forest units, representing 78.7% of global GCW.")],
    )
    editor.replace_paragraph(
        "Table 3. Annual loss of modeled forest living-biomass addition capacity, 2010-2019.",
        "Table 3. Annual loss of modeled forest living-biomass addition capacity, 2010-2020.",
        label="Table 3 current period",
    )
    editor.update_table(
        "Group",
        {
            "Developed economies": ["45", "0.69", "2.85", "1.59"],
            "Developing economies": ["51", "5.63", "20.39", "11.41"],
            "LDCs": ["24", "3.29", "11.28", "6.31"],
            "SIDS": ["17", "0.09", "0.31", "0.17"],
        },
        second_cell="Reporting units",
        label="Table 3 current group values",
    )
    editor.replace_paragraph(
        "If the reported annual deforestation rate continued",
        "If the reported annual deforestation rate continued and converted areas remained outside forest, the modeled loss of annual addition capacity would accumulate to 2.36% of the current global forest-flow estimate after ten years. Capitalizing the current annual value loss as a permanent stream at a 2% real discount rate gives an illustrative value of US$0.974 trillion. Developing economies accounted for 58.5% of the reported annual value loss and LDCs for 32.4%, compared with 8.2% in developed economies and 0.9% in SIDS (Table 3). The ten-year calculation assumes no regrowth or change in biome rates, and the capitalized value is not an observed asset price. Group shares apply only to reporting units.",
        label="Results cumulative erosion and group incidence",
    )
    editor.replace_paragraph(
        "Across 105 units with positive reported deforestation",
        "Across 105 units with positive reported deforestation and positive GCW, GCW and annual erosion intensity had a weak negative rank association (Spearman ρ = −0.218, p = 0.0257). Figure 3 plots annual gross-addition capacity no longer supplied as a percentage of GCW against GCW; its median lines divide the units into 33 high-GCW/low-erosion, 20 high/high, 33 low/high, and 19 low/low profiles. The association is descriptive and does not establish that current service value causes or predicts deforestation. The figure excludes 34 reporting units with zero deforestation and 97 units with missing deforestation reports.",
        label="Results erosion intensity association",
    )
    editor.replace_paragraph(
        "Reported global deforestation nearly halved",
        "Reported global deforestation totals declined across the five FRA intervals: 15.82 Mha per year in 1990-2000, 13.33 in 2000-2010, 9.88 in 2010-2015, 9.48 in 2015-2020, and 8.48 in 2020-2025. The Theil-Sen slope was −0.272 Mha yr⁻² (approximate 95% non-parametric interval −0.460 to −0.080 Mha yr⁻²); the Mann-Kendall statistic was S = −10 (p = 0.0275; see Supplementary Table S3). The five intervals differ in duration, and the reporting cohort can vary; this is an indicative trend in reported area, not evidence that the modeled annual forest-addition capacity loss has reversed. The modeled 34.83 MtCO₂ per year of lost capacity uses the separate 2010-2020 reference period.",
        label="Results global deforestation trend",
    )

    editor.replace_paragraph(
        "The welfare value of lost capacity and the cost of replacing that capacity use different prices",
        "The welfare value of lost capacity and the cost of replacing that capacity use different prices for the same annual tonne. The GSCC values avoided climate damages, whereas an abatement price approximates the cost of additional mitigation. Across 139 reporting forest units, illustrative prices of US$50, US$150, and US$400 per tCO₂ imply annual replacement costs of US$1.74, US$5.22, and US$13.93 billion, respectively (Table 4). These amounts equal 0.09, 0.27, and 0.71 of the annual welfare value lost. The prices are illustrative scenario inputs, not action-specific costs; the ratios do not establish that replacement would be cheaper under every technology, location, or policy constraint.",
        label="Results illustrative replacement costs",
    )
    editor.replace_paragraph(
        "The allocation rule changed which groups bear the modeled replacement cost.",
        "At US$150 per tCO₂, LDCs would face US$1.69 billion per year under domestic allocation and US$0.08 billion under an allocation proportional to GDP. Developed economies would face US$0.43 billion domestically and US$2.16 billion under the shared-effort rule. Under domestic allocation, the burden reached 1.02% of GDP in the Central African Republic, 0.85% in Somalia, and 0.67% in Mozambique. Figure 4 compares group totals under the two rules. These are burden-sharing scenarios for the 139 reporting units, not forecasts of a carbon market or statements of legal responsibility.",
        label="Results replacement-cost group allocation",
    )
    editor.replace_paragraph(
        "A 5% decline in the published annual BCW flow corresponds",
        "A 5% decline in the annual BCW flow corresponds to 208.5 MtCO₂ per year, about 6.0 times the modeled forest-addition capacity loss associated with reported deforestation, and to US$116.5 billion per year at the common valuation. A 10% decline corresponds to 416.9 MtCO₂ and US$233.0 billion per year. These are sensitivity scenarios applied to the BCW account with the selected mangrove-area hierarchy, not observed declines in marine carbon uptake (Table 1; comparison with Table 3).",
        label="Results marine decline sensitivity",
    )

    # Discussion repeats of the same results; no new claims are introduced.
    editor.replace_paragraph(
        "Forest and marine carbon flows underpin a large annual climate-regulation service",
        "Forest and marine carbon flows underpin a large annual climate-regulation service, but their estimated welfare values and spatial attribution are unevenly distributed. GCW reached US$8.24 [3.22-14.97] trillion per year and accounted for 78.0% of NCW after combination with the marine account whose mangrove area was updated using GMW 2025. This result extends the national accounting comparison to forests while keeping the unit of analysis an annual welfare contribution rather than a stock value or revenue stream.",
        label="Discussion global summary",
    )
    editor.replace_paragraph(
        "The combined account reveals patterns that a forest or marine account alone",
        "The combined account reveals patterns that a forest or marine account alone cannot show. Tropical, subtropical, temperate, and boreal forests supplied 44.7%, 15.9%, 21.9%, and 17.5% of estimated gross living-biomass additions. Marine flows changed the composition of carbon wealth most strongly in SIDS. Adding BCW raised the share of accounting units with positive annual balances against fossil-fuel and industrial emissions from 38% to 54%; this boundary-based classification does not establish climate neutrality. The population-weighted mean NCW was US$1,306 per person, while the unweighted mean across 232 units with data was US$19,866. Per-capita figures remain in the Supplementary Material because they describe demographic scale; GCW relative to GDP is used in the main text to describe the service value relative to economic output.",
        label="Discussion group and balance summary",
    )
    editor.replace_paragraph(
        "The erosion result adds a temporal dimension to the account",
        "The erosion result adds a temporal dimension to the account. Reported deforestation corresponded to US$19.49 billion per year of lost annual forest-addition capacity across 139 reporting units, representing 78.7% of global GCW. The annual value loss was 0.30% of reported-unit GCW. Under a constant-rate, no-regrowth scenario, ten-year accumulated lost capacity would equal 2.36% of the current global forest-flow estimate. Erosion value was concentrated in developing economies and LDCs. Across 105 positive-reporting units, GCW had a weak negative association with erosion intensity (Spearman ρ = −0.218, p = 0.0257); this does not establish causation. Protection priorities therefore cannot be inferred from current service magnitude alone.",
        label="Discussion erosion summary",
    )
    editor.replace_paragraph(
        "The replacement-cost scenarios make the distributional issue explicit",
        "The replacement-cost scenarios make the distributional issue explicit. At US$150 per tCO₂, LDCs would face US$1.69 billion per year under domestic allocation and US$0.08 billion under allocation proportional to GDP. This contrast reflects how alternative rules distribute a hypothetical additional-abatement cost; it does not establish a payment obligation or an entitlement to climate finance.",
        label="Discussion allocation summary",
    )
    editor.replace_paragraph(
        "The forest and marine accounts rely on different spatial products",
        "The forest and marine accounts rely on different spatial products, definitions, and reference periods. Our four FAO GEZ mean rates are estimated from Gibbs/GFW gross-removal pixels for 2001-2023, with source-model mangrove pixels excluded, and applied to FRA forest areas for 2025. For GCW, valid FRA-reported biome shares are used first and the GEZ/JRC map fills missing units. FRA mangrove area is subtracted only where national reports document a Forest share: exact 100% matches plus the quantified 80% Forest share for Mozambique; the remaining category-level overlap is unresolved. For BCW, the selected mangrove area follows GMW 2025, FRA 2025, GMW 2024, GMW 2023, then the area reported by Hilmi et al. (2026). The total BCW is calculated directly from the selected mangrove area, Hilmi-reported seagrass and saltmarsh areas, their rates, the reported BCP flux, and shared GSCC draws. The forest rates estimate gross additions to living above- and below-ground biomass; they do not represent a net balance of the whole forest ecosystem or the duration for which each added tonne remains in living biomass. Socio-economic variables refer to 2023 or the nearest compatible year, while reported deforestation is averaged over 2010-2020. The country comparisons therefore combine non-contemporaneous inputs and spatial classifications that are not perfectly aligned.",
        label="Discussion harmonisation and forest-rate limits",
    )
    editor.replace_paragraph(
        "Erosion estimates cover 139 of 236 forest units",
        "Erosion estimates cover 139 of 236 forest units and 78.7% of global GCW. Missing deforestation reports are treated as missing rather than zero. For 61 units without a known marine component, NCW is a lower bound. Forest-area, biome-rate, GMW mangrove-area, and biome-allocation uncertainty are not propagated into the main monetary intervals, which reflect GSCC draws and the uncertainty present in the published marine valuation. The erosion measure includes reported deforestation only; it excludes degradation, fire, recovery dynamics, and sink saturation. Climate stress and disturbance can weaken forest uptake beyond area conversion (Green and Keenan, 2022).",
        label="Discussion coverage and uncertainty limits",
    )

    # Update the methods that generated these results, not only their prose summary.
    editor.replace_paragraph(
        "We estimate an annual flow contribution to inclusive wealth.",
        "We estimate an annual flow contribution to inclusive wealth. Green Carbon Wealth (GCW) is the annual welfare value assigned to carbon added to above- and below-ground living forest biomass, using a global welfare-based shadow price of carbon. This is the gross-removal component of the Gibbs/GFW forest carbon model, not its net forest ecosystem balance. Blue Carbon Wealth (BCW) uses the published coastal and ocean account of Hilmi et al. (2026), with mangrove area updated from GMW 2025 while retaining the published mangrove burial rate and the other marine components. Natural Carbon Wealth (NCW) combines GCW and BCW under the stated FRA mangrove-area convention.",
        label="Methods accounting inputs",
    )
    editor.replace_paragraph(
        "The current national calculation deducts the FRA-reported mangrove category",
        "For GCW, we deduct mangrove hectares from FRA forest area only where a national report documents a Forest share: exact 100% Forest matches identify 2,082,920 ha in 12 units, 1,809,830 ha are covered by explicit stability assumptions, and Mozambique and Mayotte contribute 287,848 ha and 312 ha from their reported Forest shares. The main documented Forest overlap is 4,180,910 ha. The Mozambique, Mayotte and copied/forecast 2025 applications assume classification stability. The evidence table documents 72,477.75 ha as Other wooded land and 42.25 ha as Remaining land; neither is deducted from strict forest area. Where a comparable Forest/Other wooded land split is unavailable, the FRA mangrove category is not subtracted, leaving 11,613,440 ha with unknown classification and a possible residual overlap with the coastal mangrove component in BCW. The Gibbs/GFW rate derivation separately excludes pixels classified as mangroves by its source model.",
        label="Methods selective FRA mangrove accounting",
    )
    editor.replace_paragraph(
        "Deforestation permanently removes the uptake that the cleared area would have produced.",
        "We estimate the modeled annual living-biomass addition capacity associated with the area converted during the reference period, under the scenario that converted land remains outside forest. The reported deforestation area is multiplied by the unit's biome uptake rates and by the GSCC. The deforested area is distributed across biomes using the unit's forest biome shares, which approximates a process that is predominantly tropical; this assumption has no effect on single-biome units.",
        label="Methods deforestation capacity definition",
    )
    editor.replace_paragraph(
        "If a climate target is held fixed, capacity lost from the sink must be replaced",
        "Under the replacement scenario, a climate target is held fixed and modeled annual capacity no longer supplied by converted forest area is matched, by assumption, with additional abatement elsewhere. Lost annual capacity is multiplied by three illustrative prices of 50, 150 and 400 constant 2015 US$/tCO₂. These prices are placeholders for scenario comparison, not observed action costs or country-specific marginal-abatement-cost estimates. They are conceptually distinct from the GSCC, which values avoided damages rather than replacement effort.",
        label="Methods replacement-scenario assumption",
    )
    editor.replace_paragraph(
        "Three reference periods coexist.",
        "Three reference periods coexist. The Gibbs/GFW forest gross-removal rates average 2001-2023; FRA forest areas refer to 2025; population, GDP, emissions and debt refer to 2023 or the nearest available year compatible with the published blue carbon account. Reported deforestation is averaged over 2010-2020. This pairing supports comparative accounting but is not a contemporaneous measurement of every country's forest flow.",
        label="Methods deforestation period",
    )

    package["word/document.xml"] = etree.tostring(document, xml_declaration=True, encoding="UTF-8", standalone=True)
    temp = PAPER.with_suffix(".current-results-refresh.tmp.docx")
    with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, content in package.items():
            out.writestr(name, content)

    with zipfile.ZipFile(temp, "r") as check_zip:
        bad = check_zip.testzip()
        if bad:
            raise RuntimeError(f"DOCX ZIP integrity check failed: {bad}")
        checked = etree.fromstring(check_zip.read("word/document.xml"), parser)
        text = "\n".join(visible_text(p) for p in checked.iter(W + "p"))
        required = [
            "14.73 GtCO₂", "US$8.24 [3.22-14.97]", "US$10.57 [4.16-19.17]",
            "78.0%", "44.7%", "54.6%", "64.1%", "p = 2.17 × 10⁻²¹",
            "72 were green-dominant", "71.9% of global emissions", "32.3% of global accounted removals",
            "139 of 236 forest units, representing 78.7%", "2.36%", "US$0.974 trillion",
            "15.82 Mha per year in 1990-2000", "p = 0.0257", "208.5 MtCO₂",
            "GMW 2025", "4,180,910 ha", "287,848 ha from its reported 80% Forest share", "remains outside forest",
        ]
        missing = [item for item in required if item not in text]
        if missing:
            raise RuntimeError(f"Post-edit text checks failed: {missing}")
        obsolete = [
            "14.68 GtCO₂", "US$8.22 [3.21-14.92]", "US$10.55 [4.15-19.12]",
            "77.9%", "44.5%", "53.3%", "p = 1.6 × 10⁻²⁰", "71 units were green-dominant",
            "37% with forests alone", "74% of global emissions", "35% of global accounted removals",
            "2010-2019", "2.37%", "US$0.975 trillion", "p = 0.022",
            "208 MtCO₂ per year", "deducts the FRA-reported mangrove category",
            "Deforestation permanently removes the uptake",
        ]
        present = [item for item in obsolete if item in text]
        if present:
            raise RuntimeError(f"Obsolete visible text remains: {present}")
        comments = etree.fromstring(check_zip.read("word/comments.xml"))
        comment_ids = {c.get(W + "id") for c in comments.iter(W + "comment")}
        start_ids = {c.get(W + "id") for c in checked.iter(W + "commentRangeStart")}
        end_ids = {c.get(W + "id") for c in checked.iter(W + "commentRangeEnd")}
        if comment_ids - start_ids or comment_ids - end_ids:
            raise RuntimeError("A Word comment lost its range marker")
        new_images = {
            name: check_zip.read(name)
            for name in check_zip.namelist()
            if name.startswith("word/media/")
        }
        if new_images != original_images:
            raise RuntimeError("An embedded image changed during the text-only refresh")

    temp.replace(PAPER)
    print(f"Updated: {PAPER}")
    print(f"Backup: {BACKUP}")
    print(f"Track-change entries: {len(editor.changed)}")
    print("Embedded images: unchanged")
    for change in editor.changed:
        print(f"- {change}")


if __name__ == "__main__":
    main()
