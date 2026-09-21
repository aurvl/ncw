"""Align the manuscript core with the four-part GCW/NCW study.

The patch works at OOXML level to preserve all existing comments and tracked
revisions.  It replaces the legacy Introduction and Discussion as paragraph
deletions, inserts a concise Methods section and updates the existing tracked
Results additions in place so that their figures and tables remain located at
their first textual call-out.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import os
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def visible_text(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def all_text(paragraph: etree._Element) -> str:
    return "".join(
        node.text or "" for node in paragraph.xpath(".//w:t | .//w:delText", namespaces=NS)
    )


def direct_paragraphs(body: etree._Element) -> list[etree._Element]:
    return body.findall("w:p", namespaces=NS)


def one_exact(body: etree._Element, text: str, *, include_deleted: bool = False) -> etree._Element:
    getter = all_text if include_deleted else visible_text
    matches = [p for p in direct_paragraphs(body) if getter(p).strip() == text]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph {text!r}; found {len(matches)}.")
    return matches[0]


def one_starts(body: etree._Element, prefix: str) -> etree._Element:
    matches = [p for p in direct_paragraphs(body) if visible_text(p).startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one visible paragraph beginning {prefix!r}; found {len(matches)}.")
    return matches[0]


def next_change_id(root: etree._Element) -> int:
    ids: list[int] = []
    for value in root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return max(ids, default=0) + 1


def add_revision_attributes(element: etree._Element, change_id: int, date: str) -> None:
    element.set(w("id"), str(change_id))
    element.set(w("author"), "Codex")
    element.set(w("date"), date)


def mark_paragraph_deleted(paragraph: etree._Element, change_id: int, date: str) -> int:
    """Add a paragraph-mark deletion without disturbing runs or comments."""
    properties = paragraph.find("w:pPr", namespaces=NS)
    if properties is None:
        properties = etree.Element(w("pPr"))
        paragraph.insert(0, properties)
    run_properties = properties.find("w:rPr", namespaces=NS)
    if run_properties is None:
        run_properties = etree.SubElement(properties, w("rPr"))
    if run_properties.find("w:del", namespaces=NS) is not None:
        return change_id
    deletion = etree.SubElement(run_properties, w("del"))
    add_revision_attributes(deletion, change_id, date)
    return change_id + 1


def make_inserted_paragraph(
    text: str, properties: etree._Element | None, change_id: int, date: str
) -> etree._Element:
    paragraph = etree.Element(w("p"))
    if properties is not None:
        paragraph.append(deepcopy(properties))
    insertion = etree.SubElement(paragraph, w("ins"))
    add_revision_attributes(insertion, change_id, date)
    run = etree.SubElement(insertion, w("r"))
    text_node = etree.SubElement(run, w("t"))
    if text.startswith(" ") or text.endswith(" "):
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    return paragraph


def insert_before(
    body: etree._Element,
    reference: etree._Element,
    blocks: list[tuple[str, etree._Element | None]],
    change_id: int,
    date: str,
) -> int:
    position = body.index(reference)
    for offset, (text, properties) in enumerate(blocks):
        body.insert(position + offset, make_inserted_paragraph(text, properties, change_id, date))
        change_id += 1
    return change_id


def update_tracked_result_paragraph(body: etree._Element, prefix: str, replacement: str) -> None:
    paragraph = one_starts(body, prefix)
    nodes = paragraph.xpath(".//w:ins[@w:author='Codex']//w:t", namespaces=NS)
    if not nodes:
        raise RuntimeError(f"The Results paragraph {prefix!r} is not a Codex tracked insertion.")
    nodes[0].text = replacement
    for node in nodes[1:]:
        node.text = ""


def mark_section_paragraphs_deleted(
    body: etree._Element,
    heading: etree._Element,
    end: etree._Element,
    change_id: int,
    date: str,
) -> int:
    children = list(body)
    first, last = children.index(heading), children.index(end)
    if last <= first:
        raise RuntimeError("Section bounds are invalid.")
    for paragraph in children[first + 1 : last]:
        if paragraph.tag == w("p") and all_text(paragraph).strip():
            change_id = mark_paragraph_deleted(paragraph, change_id, date)
    return change_id


def enable_track_revisions(settings: etree._Element) -> None:
    if settings.find("w:trackRevisions", namespaces=NS) is None:
        settings.insert(0, etree.Element(w("trackRevisions")))


INTRODUCTION = [
    "Climate mitigation depends on biophysical processes that do not appear in standard measures of national output or wealth. Natural-capital accounting offers a way to make these contributions visible by linking ecosystem functions to human welfare (Brondizio et al., 2019). Forests and the ocean remove CO2 from the atmosphere each year, but the national distribution, persistence, and economic implications of these services remain difficult to compare on a common basis.",
    "Forests are a major part of the global carbon sink, yet their contribution is heterogeneous across biomes and is exposed to deforestation, disturbance, and climate stress (Pan et al., 2024; FAO, 2025). Blue Carbon Wealth (BCW) has already shown that annual coastal and open-ocean carbon removal can be expressed as a welfare-relevant natural-capital contribution at the country level (Bertram et al., 2021; Hilmi et al., 2026). An analogous forest account must distinguish an annual removal flow from a carbon stock, and it must avoid treating an ecosystem-service value as observed income, a market price, or a claim on climate finance.",
    "Recent studies clarify why these distinctions matter. Thaller et al. (2026) value land-sink contributions to inclusive wealth with country social costs of carbon. Favero and Austin (2026) estimate future, policy-induced forest mitigation and its marginal cost under alternative carbon-price paths. Rickels et al. (2024) show how a weaker ocean sink can increase the cost of meeting climate targets. These studies address related but distinct objects: a service provided by a reference-period sink, additional mitigation relative to a baseline, and the policy cost of a weakened sink.",
    "This study links these objects descriptively at the national level. It first estimates the annual welfare contribution of forest uptake as Green Carbon Wealth (GCW) and combines it with BCW to form Natural Carbon Wealth (NCW). It then quantifies the annual forest service capacity lost through reported deforestation and compares that welfare loss with linear, illustrative carbon-price proxies for additional abatement. The final comparison also asks how the burden changes when the country that loses a sink pays itself or when the aggregate bill is shared in proportion to GDP.",
    "Our purpose is not to claim the first valuation of a terrestrial sink, nor to infer a tradable entitlement from natural-carbon wealth. Instead, we provide a harmonised account of four connected facts: the magnitude and distribution of forest service, the change introduced by the ocean component, the erosion of the forest service, and the distributional implications of compensating for that erosion. This framework makes clear which results are measured, which are scenarios, and which policy interpretations remain conditional on future choices about abatement technology and burden sharing.",
]


METHODS = [
    ("Methods", "h1"),
    ("Accounting framework", "h2"),
    (
        "Green Carbon Wealth is the annual welfare value of forest CO2 uptake. For each accounting unit, annual uptake in tonnes of CO2 is multiplied by the Global Social Cost of Carbon (GSCC) in constant 2015 US dollars per tonne of CO2. Natural Carbon Wealth equals GCW plus BCW after removing the overlap for mangroves. These indicators describe annual climate-regulation services. They are neither carbon-stock values, observed national income, market prices, finance needs, nor estimates of additional mitigation.",
        "body",
    ),
    ("Forest uptake and harmonisation", "h2"),
    (
        "The forest account uses FRA 2025 forest area, country-level biome shares, and the 2010-2019 forest fluxes reported by Pan et al. (2024). Tropical and subtropical forest shares are combined because Pan et al. report a single tropical rate. The resulting mean uptake rates are 1.32 tC ha^-1 year^-1 for tropical forests, 0.87 for temperate forests, and 0.28 for boreal forests. Mangrove area is removed from the forest component when it is already represented by the BCW account, which prevents double counting.",
        "body",
    ),
    (
        "Accounting units follow the FRA country and territory scheme. BCW components are mapped onto these units, and their sub-territories are regrouped where necessary. Population, GDP, and fossil-and-industry CO2 emissions use the 2023 socio-economic reference year. The ecological forest flux therefore represents 2010-2019, the forest-area account uses FRA 2025, and the socio-economic comparisons use 2023. This timing mismatch is retained for consistency with the BCW account and is treated as a limitation.",
        "body",
    ),
    ("Uncertainty and descriptive statistics", "h2"),
    (
        "Uncertainty in GCW and NCW is propagated with 20,000 Monte Carlo draws. Biome uptake rates follow truncated normal distributions, and the same GSCC draws are used for the green and blue accounts. Global and group totals are summed draw by draw before their means and 5th-95th percentiles are calculated. We report absolute values, ratios to GDP, country-group summaries, a Gini coefficient, and Spearman correlations. Group differences in the GCW-to-GDP ratio are assessed with a Kruskal-Wallis test.",
        "body",
    ),
    ("Net balances, erosion, and compensation scenarios", "h2"),
    (
        "A net sink has annual accounted sequestration greater than 2023 fossil-and-industry CO2 emissions; emissions from land-use change are excluded from this comparison. We report the forest-only and forest-plus-ocean classifications. The debt quadrant shown in preliminary analyses is not retained in the main text because a debt-stress threshold has not yet been fixed to the BCW definition.",
        "body",
    ),
    (
        "Forest-service erosion is estimated from reported annual deforestation for 2010-2019. Deforested area is multiplied by the biome-specific uptake rate and then by the GSCC. The reporting analysis is restricted to the 139 units with valid FRA deforestation information; a missing report is never coded as zero. We assess the global deforestation series with a Theil-Sen slope and a Mann-Kendall test.",
        "body",
    ),
    (
        "Compensation is a scenario analysis, not a model of a carbon market. We multiply lost annual capacity by three illustrative 2015 US dollar prices per tonne of CO2 (50, 150, and 400). These prices are linear proxies for the cost of additional abatement and remain distinct from the GSCC, which values avoided welfare damages. We compare a domestic allocation, where each country covers its own loss, with a GDP-shared allocation of the aggregate bill. The latter is a burden-sharing rule, not a least-cost market equilibrium.",
        "body",
    ),
]


DISCUSSION = [
    "This study shows that forest carbon uptake is a large annual climate-regulation service. GCW averaged US$8.16 trillion per year, while the forest component represented 77.8% of the combined US$10.49 trillion NCW account. These figures do not value stored forest carbon and do not measure a cash flow available to governments. They express the welfare value of annual CO2 removal under a common GSCC, which is the appropriate interpretation for a flow account.",
    "The service is concentrated because tropical forests combine the largest forest area with the highest biome-specific uptake rate. They supply 78.6% of global uptake. The economic interpretation differs from a ranking of GDP: the Gini coefficient of 0.856 means that a small number of countries provide most of the quantified service, whereas the modest GCW-GDP correlation shows that ecological endowment and economic size are different dimensions. The high GCW-to-GDP ratios in least developed countries reflect a small GDP denominator as well as forest endowment. They identify a large unpriced service relative to measured output, not a transferable income stream.",
    "Adding BCW changes national profiles without eliminating this geographic separation. The ocean component shifts many small island economies toward blue-dominant accounts and raises the share of units classified as net sinks from 37% to 52%. Yet the leading emitters and the leading sinks remain largely distinct. Natural carbon wealth therefore cannot be read as an offset for current emissions. It is an accounting measure that makes visible who supplies annual removal and how that supply relates to, but does not cancel, national emissions.",
    "The erosion results add a temporal dimension that a static wealth account cannot provide. Reported deforestation removes US$25.7 billion per year of annual GCW capacity, with a 5th-95th percentile interval of US$9.79-49.58 billion. The annual fraction is small relative to the service, but it is persistent: a permanent loss at the observed rate reaches 4.0% over a decade and has a capitalised value of US$1.28 trillion at a 2% discount rate. The service-to-erosion correlation is close to zero. Protecting only the largest current sinks would therefore miss countries where a modest service is eroding rapidly.",
    "The deforestation trend needs a careful reading. The global reported rate fell from 15.8 million ha per year in the 1990s to 8.5 million ha per year in the latest period. The Theil-Sen estimate is -272 thousand ha per year per year, and the Mann-Kendall test gives p = 0.03. This evidence does not support a claim that global reported deforestation is accelerating. It also does not imply that the annual service loss is negligible, because avoided future uptake is lost wherever conversion occurs. The erosion estimates cover only 139 of 236 accounting units and 79% of global GCW; the United States, Peru, Bolivia, and Myanmar are among the non-reporting units. Missing data must not be interpreted as zero loss.",
    "The compensation scenarios distinguish two prices for the same lost tonne. The GSCC measures the welfare damages avoided when the tonne is removed. The illustrative carbon price represents a proxy for the cost of generating additional abatement to replace it. Within the three price cases, the proxy cost is 0.09-0.71 of the annual welfare value lost. This comparison does not prove that compensation is inexpensive in practice. It shows only that a linear price proxy below the selected welfare valuation produces a lower accounting amount.",
    "Who pays is separate from who loses the forest service. Under domestic allocation, countries with reported deforestation also bear the full replacement bill, even when their GDP is small. This mechanism explains the high burden in the Central African Republic, Somalia, and Mozambique and the large reduction in the LDC bill under GDP sharing. These estimates compare allocation rules. They do not model national marginal abatement costs, international permit trade, feasibility, or the institutional design of a transfer. A full least-cost analysis would require validated marginal-cost curves or an economic model such as the framework used by Rickels et al. (2024).",
    "The study is positioned alongside, rather than ahead of, recent work. Thaller et al. (2026) value terrestrial sink contributions with country social costs of carbon. Favero and Austin (2026) estimate policy-induced forest mitigation relative to a future baseline. Rickels et al. (2024) combine ocean-sink valuation with abatement-cost analysis. Our contribution is to place a harmonised forest service, published BCW, observed forest-service erosion, and transparent allocation scenarios in one country-level account. The four components remain conceptually distinct, and this distinction limits overinterpretation.",
    "Several limitations matter for interpretation. Country uptake uses biome-average rates and a spatial allocation of forest area. It does not represent within-country forest condition, management, disturbance, or the full uncertainty of future climate responses. The forest and socio-economic data refer to different years. The loss draws are not a full joint uncertainty model with the GCW and BCW draws. Ocean weakening is represented only by 5% and 10% scenarios, not observed country-level losses. Finally, the compensation price cases are illustrative until a final AR6 scenario, price year, and conversion protocol are specified.",
    "Forest and ocean carbon sinks thus enter the account as a valuable but unevenly supplied annual service. Its erosion is concentrated in countries whose measured economies often provide limited capacity to absorb the associated burden. A useful policy response cannot follow from the value estimate alone. It requires clearer physical monitoring, explicit additionality and permanence rules, and a defensible rule for sharing the costs of maintaining a global climate-regulation service.",
]


REFERENCES = {
    "Favero": "Favero, A., & Austin, K. G. (2026). Charting our forest future: national supply curves for forest-based CO2 mitigation. npj Climate Action, 5, 6. https://doi.org/10.1038/s44168-026-00335-9",
    "Hilmi": "Hilmi, N., De Vince Vehi, L. A., Treskova, M., Sabourault, C., & Levin, L. (2026). Global assessment shows blue carbon wealth dominated by ocean processes and unevenly distributed across countries. Communications Sustainability, 1, 114. https://doi.org/10.1038/s44458-026-00117-8",
    "Rickels": "Rickels, W., Meier, F., Peterson, S., Ruhland, S., Thube, S., Karstensen, J., Posern, C., Wolff, C., Vafeidis, A. T., Grasse, P., & Quaas, M. (2024). The ocean carbon sink enhances countries' inclusive wealth and reduces the cost of national climate policies. Communications Earth & Environment, 5, 513. https://doi.org/10.1038/s43247-024-01674-3",
    "Thaller": "Thaller, L., Harding, A., Saldivia Gonzatti, I., Schwingshackl, C., O'Sullivan, M., Pongratz, J., & Rickels, W. (2026). Country social cost of carbon estimates and their application to assess the natural land sink. Kiel Working Paper No. 2316, Kiel Institute for the World Economy.",
}


def main() -> None:
    if not ARTICLE.exists():
        raise FileNotFoundError(ARTICLE)
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    settings = etree.fromstring(package["word/settings.xml"])
    enable_track_revisions(settings)
    body = document.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("The document has no body.")
    change_id = next_change_id(document)

    introduction_heading = one_exact(body, "Introduction")
    result_headings = [p for p in direct_paragraphs(body) if visible_text(p).strip() == "Results"]
    if len(result_headings) != 2:
        raise RuntimeError(f"Expected the two pre-existing Results headings; found {len(result_headings)}.")
    # The first duplicate lies between the legacy Introduction and the actual
    # Results block.  Deleting it with the old Introduction removes the stray
    # heading while retaining the second heading as the new Results anchor.
    results_heading = result_headings[-1]
    first_intro = one_starts(body, "The accelerating impacts of climate change")
    body_properties = deepcopy(first_intro.find("w:pPr", namespaces=NS))
    heading_1_properties = deepcopy(results_heading.find("w:pPr", namespaces=NS))
    result_subheading = one_exact(body, "Forest carbon sinks make a large but uneven contribution to national carbon wealth")
    heading_2_properties = deepcopy(result_subheading.find("w:pPr", namespaces=NS))

    # The old introduction remains available as a paragraph-level deletion.
    change_id = mark_section_paragraphs_deleted(
        body, introduction_heading, results_heading, change_id, date
    )
    intro_blocks = [(paragraph, body_properties) for paragraph in INTRODUCTION]
    method_blocks: list[tuple[str, etree._Element | None]] = []
    for text, kind in METHODS:
        properties = {"h1": heading_1_properties, "h2": heading_2_properties, "body": body_properties}[kind]
        method_blocks.append((text, properties))
    change_id = insert_before(body, results_heading, [*intro_blocks, *method_blocks], change_id, date)

    # Retain figures and tables in their existing locations.  The paragraph
    # text is expanded in its existing tracked insertion so the visual objects
    # remain at the first reference in the Results.
    update_tracked_result_paragraph(
        body,
        "Forests generated Green Carbon Wealth",
        "Forests generated Green Carbon Wealth (GCW) of US$8.16 trillion per year in 2015 prices (5th-95th percentile: US$3.15-15.49 trillion). Blue Carbon Wealth added US$2.33 trillion per year, so Natural Carbon Wealth reached US$10.49 trillion per year and forests accounted for 77.8% of the combined account (Table 1). These are annual welfare values of CO2 uptake. They do not value stored forest carbon or a cash flow available to the countries where forests occur.",
    )
    update_tracked_result_paragraph(
        body,
        "Tropical forests accounted for 78.6%",
        "Tropical forests accounted for 78.6% of global uptake, compared with 13.4% for temperate forests and 8.0% for boreal forests. This dominance follows directly from the accounting mechanism: tropical forests combine the largest estimated area (2,373 million ha) with the highest biome-average uptake rate (1.32 tC ha^-1 year^-1), compared with 0.87 in temperate forests and 0.28 in boreal forests. The result therefore reflects both extent and per-hectare uptake, rather than area alone.",
    )
    update_tracked_result_paragraph(
        body,
        "GCW equalled 8.9% of global GDP.",
        "Developing economies supplied 51.4% of global GCW, developed economies 27.7%, least developed countries 18.1%, and small island developing states 2.8%. GCW equalled 8.9% of global GDP, but the median ratio was 75.1% in least developed countries and 2.7% in developed economies. This contrast reflects the GDP denominator as well as forest endowment: a similar physical service represents a much larger share of recorded output where measured economies are small. GCW and GDP were only moderately associated (Spearman correlation = 0.55). The distribution also differed across country groups (Kruskal-Wallis H = 48.1, p = 2 x 10^-10). Figure 1 and Table 2 show that a Gini coefficient of 0.856 leaves policy based on GCW concentrated in a small number of countries: the ten largest contributors supplied 57.4% of the global total.",
    )
    update_tracked_result_paragraph(
        body,
        "Blue carbon changed the composition",
        "Blue carbon changed the composition of national carbon wealth, but not in the same way across groups. Small island developing states were predominantly blue, with 33 blue-dominant and 10 green-dominant accounting units. Least developed countries showed the reverse pattern, with 15 green-dominant and one blue-dominant unit. Figure 2 makes this contrast visible, and Table 2 shows that the blue component changes the composition of the account most strongly in island economies rather than in the forest-rich least developed countries.",
    )
    update_tracked_result_paragraph(
        body,
        "The share of accounting units with a net sink",
        "Adding the ocean component changed national net balances. The share of accounting units classified as net sinks rose from 37% with forests alone to 52% with forests and the ocean. The change is consequential for national profiles, but it does not erase the separation between those that emit and those that sequester. The ten largest emitters accounted for 74% of global CO2 emissions, whereas the ten largest sinks accounted for 39% of accounted sequestration. Only the Russian Federation and Indonesia appeared in both groups. Natural carbon wealth therefore complements, rather than offsets, an emissions account.",
    )
    debt_paragraph = one_starts(body, "At the current debt-stress threshold")
    change_id = mark_paragraph_deleted(debt_paragraph, change_id, date)
    update_tracked_result_paragraph(
        body,
        "Reported deforestation averaged 9.70 million ha",
        "Reported deforestation averaged 9.70 million ha per year over 2010-2019. It removed an estimated 45.9 MtCO2 per year of future sequestration capacity, equivalent to US$25.7 billion per year of GCW (5th-95th percentile: US$9.79-49.58 billion) and 0.40% of GCW among reporting units each year (Table 3). This is an annual service-capacity loss: once forest is converted, the uptake that it would have provided is no longer available in subsequent years.",
    )
    update_tracked_result_paragraph(
        body,
        "A constant loss at this rate would remove 4.0%",
        "The annual percentage is small relative to the global service, but the loss is cumulative and persistent. A constant loss at this rate would remove 4.0% of the current service within ten years. At a 2% discount rate, the capitalised value of one permanent annual loss was US$1.28 trillion. Developing economies accounted for 58.5% of the reported value loss and least developed countries for 34.7%, so erosion is concentrated in groups for which the service also carries a high weight relative to GDP.",
    )
    update_tracked_result_paragraph(
        body,
        "Service magnitude and erosion intensity were not correlated",
        "Service magnitude and erosion intensity were not correlated (Spearman correlation = -0.09, p > 0.05). Figure 3 shows why the size of a current sink is not a reliable guide to erosion risk: countries that provide a large service are not systematically the countries with the most rapid proportional loss. Reported deforestation declined from 15.8 million ha per year in the 1990s to 8.5 million ha per year in the latest period. The global Theil-Sen slope was -272 thousand ha per year per year and the Mann-Kendall test gave p = 0.03. This evidence does not support acceleration, but it does not remove the cumulative effect of continued loss. The estimates cover 139 of 236 accounting units and 79% of global GCW; missing FRA reports do not indicate zero deforestation.",
    )
    update_tracked_result_paragraph(
        body,
        "The welfare value of lost capacity and the cost of replacement",
        "The welfare value of lost capacity and the cost of additional abatement are different quantities. The GSCC values the avoided climate damages from one tonne of removal, whereas an abatement price is a proxy for the cost of replacing that tonne. At illustrative prices of US$50, US$150, and US$400 per tCO2, annual compensation costs were US$2.29, US$6.88, and US$18.36 billion. These amounts were 0.09, 0.27, and 0.71 of the annual welfare value lost (Table 4). The ratio below one is a property of the selected price cases; it is not evidence that real-world compensation is always cheaper than the damage avoided.",
    )
    update_tracked_result_paragraph(
        body,
        "Under domestic compensation at US$150 per tCO2",
        "Who loses a forest service is not necessarily who can afford to pay for its replacement. Under domestic compensation at US$150 per tCO2, least developed countries paid US$2.39 billion per year. Under a shared allocation proportional to GDP, their contribution fell to US$0.11 billion per year. The domestic burden reached 1.44% of GDP in the Central African Republic, 1.21% in Somalia, and 0.95% in Mozambique. Figure 4 shows the mechanism: erosion occurs where forests are lost, while GDP capacity is concentrated elsewhere. These are allocation rules, not estimates of a functioning international carbon market.",
    )
    update_tracked_result_paragraph(
        body,
        "A 5% decline in Blue Carbon Wealth",
        "The ocean component shows the scale of a potential wider loss. A 5% decline in Blue Carbon Wealth corresponded to 208 MtCO2 per year, 4.5 times the observed annual forest-capacity loss, and US$116 billion per year of welfare value. A 10% decline corresponded to 416 MtCO2 per year and US$233 billion per year. These are sensitivity scenarios rather than observed ocean losses. The compensation prices also remain illustrative until the final AR6 scenario, price year, and conversion to 2015 US dollars are selected.",
    )

    # Replace the legacy discussion while retaining it as tracked material.
    discussion_heading = one_exact(body, "Discussion and limitations")
    references_heading = one_exact(body, "References")
    change_id = mark_section_paragraphs_deleted(
        body, discussion_heading, references_heading, change_id, date
    )
    discussion_blocks = [(paragraph, body_properties) for paragraph in DISCUSSION]
    change_id = insert_before(body, references_heading, discussion_blocks, change_id, date)

    # Update the published BCW reference and add the three sources that frame
    # the revised contribution.  Each old reference remains as a deletion.
    hilmi_old = one_starts(body, "Hilmi Nathalie")
    ref_properties = deepcopy(hilmi_old.find("w:pPr", namespaces=NS))
    change_id = mark_paragraph_deleted(hilmi_old, change_id, date)
    change_id = insert_before(body, hilmi_old, [(REFERENCES["Hilmi"], ref_properties)], change_id, date)
    fao_2020 = one_starts(body, "Food and Agriculture Organization of the United Nations. (2020)")
    change_id = insert_before(body, fao_2020, [(REFERENCES["Favero"], ref_properties)], change_id, date)
    ricke = one_starts(body, "Ricke, K.")
    change_id = insert_before(body, ricke, [(REFERENCES["Rickels"], ref_properties)], change_id, date)
    trumbore = one_starts(body, "Trumbore, S. E.")
    change_id = insert_before(body, trumbore, [(REFERENCES["Thaller"], ref_properties)], change_id, date)

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    package["word/settings.xml"] = etree.tostring(
        settings, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.core-revised.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Rewrote Introduction, Methods, Results, Discussion, and references in {ARTICLE}")


if __name__ == "__main__":
    main()
