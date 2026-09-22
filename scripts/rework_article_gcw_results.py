"""Rework the four Results blocks in Article-GCW.docx with true redlines."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "Article-GCW.docx"
AUTHOR = "Loua Aurel De Vince Vehi"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def active_text(node: etree._Element) -> str:
    return "".join(node.xpath(".//w:t/text()", namespaces=NS)).strip()


def next_id(root: etree._Element) -> int:
    ids: list[int] = []
    for value in root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            ids.append(int(value))
        except ValueError:
            pass
    return max(ids, default=0) + 1


def matches(body: etree._Element, prefix: str) -> list[etree._Element]:
    return [p for p in body.findall("w:p", namespaces=NS) if active_text(p).startswith(prefix)]


def find_one(body: etree._Element, prefix: str) -> etree._Element:
    found = matches(body, prefix)
    if not found:
        raise RuntimeError(f"Paragraph not found: {prefix}")
    return found[0]


def deletion_from_run(run: etree._Element, change_id: int, stamp: str) -> etree._Element:
    copied = deepcopy(run)
    for node in copied.xpath(".//w:t", namespaces=NS):
        node.tag = w("delText")
    deletion = etree.Element(w("del"))
    deletion.set(w("id"), str(change_id))
    deletion.set(w("author"), AUTHOR)
    deletion.set(w("date"), stamp)
    deletion.append(copied)
    return deletion


def delete_active(paragraph: etree._Element, change_id: int, stamp: str) -> int:
    """Delete active text while retaining comments and earlier deletions."""
    for child in list(paragraph):
        if child.tag == w("r"):
            if child.find("w:commentReference", namespaces=NS) is not None:
                continue
            paragraph.replace(child, deletion_from_run(child, change_id, stamp))
            change_id += 1
        elif child.tag == w("ins"):
            position = paragraph.index(child)
            converted: list[etree._Element] = []
            for run in child.findall("w:r", namespaces=NS):
                if run.find("w:commentReference", namespaces=NS) is None:
                    converted.append(deletion_from_run(run, change_id, stamp))
                    change_id += 1
            paragraph.remove(child)
            for offset, item in enumerate(converted):
                paragraph.insert(position + offset, item)
    return change_id


def append_insertion(
    paragraph: etree._Element,
    content: str,
    change_id: int,
    stamp: str,
    *,
    bold: bool = False,
    preserve_space: bool = False,
) -> None:
    insertion = etree.SubElement(paragraph, w("ins"))
    insertion.set(w("id"), str(change_id))
    insertion.set(w("author"), AUTHOR)
    insertion.set(w("date"), stamp)
    run = etree.SubElement(insertion, w("r"))
    if bold:
        rpr = etree.SubElement(run, w("rPr"))
        etree.SubElement(rpr, w("b"))
    text = etree.SubElement(run, w("t"))
    if preserve_space:
        text.set(f"{{{XML_NS}}}space", "preserve")
    text.text = content


def replace(paragraph: etree._Element, content: str, change_id: int, stamp: str) -> int:
    change_id = delete_active(paragraph, change_id, stamp)
    append_insertion(paragraph, content, change_id, stamp)
    return change_id + 1


def replace_caption(
    paragraph: etree._Element,
    label: str,
    title: str,
    change_id: int,
    stamp: str,
) -> int:
    change_id = delete_active(paragraph, change_id, stamp)
    append_insertion(paragraph, label, change_id, stamp, bold=True)
    change_id += 1
    append_insertion(paragraph, " " + title, change_id, stamp, preserve_space=True)
    return change_id + 1


R1_GLOBAL = (
    "Forests removed 14.58 GtCO₂ per year, equivalent to 3.98 GtC per year, and generated "
    "Green Carbon Wealth of US$8.16 trillion per year in constant 2015 prices. The 5th–95th "
    "percentile interval was US$3.15–15.49 trillion. Blue Carbon Wealth contributed a further "
    "US$2.33 trillion, with an interval of US$0.91–4.30 trillion, which raised Natural Carbon "
    "Wealth to US$10.49 trillion per year, with an interval of US$4.07–19.66 trillion. Forests "
    "therefore supplied 77.8% of the combined annual value (Table 1). These quantities value the "
    "climate damages avoided by annual uptake. They are not estimates of stored-carbon value, "
    "national income or funds available to provider countries."
)

R1_BIOMES = (
    "Tropical forests supplied 78.6% of global forest uptake, compared with 13.4% for temperate "
    "forests and 8.0% for boreal forests. This dominance follows from the product of forest area "
    "and the biome uptake rate. Tropical forests combine 2,373 Mha with a rate of 1.32 ± 0.21 "
    "tC ha⁻¹ yr⁻¹, whereas temperate forests combine 616 Mha with 0.87 ± 0.06 and boreal forests "
    "combine 1,135 Mha with 0.28 ± 0.04 tC ha⁻¹ yr⁻¹. The result therefore reflects both extent "
    "and the rate assigned from Pan et al. (2024), rather than forest area alone. National values "
    "remain sensitive to the correspondence between the forest-area and biome classifications."
)

R1_GROUPS = (
    "Developing economies supplied US$4.19 trillion of Green Carbon Wealth, or 51.4% of the global "
    "total. Developed economies supplied US$2.26 trillion, or 27.7%, least developed countries "
    "US$1.47 trillion, or 18.1%, and small island developing states US$0.23 trillion, or 2.8% "
    "(Table 2). The global value equalled 8.9% of world gross domestic product, but group medians "
    "were 2.7% in developed economies, 10.5% in developing economies, 75.1% in least developed "
    "countries and 6.2% in small island developing states. The contrast reflects the denominator "
    "as much as the service itself because tropical forest endowment is often combined with a small "
    "measured economy. The group distributions differed strongly (Kruskal–Wallis H = 48.1, "
    "p = 2 × 10⁻¹⁰), but the ratios remain comparisons with recorded output rather than transferable income."
)

R1_CONCENTRATION = (
    "Green Carbon Wealth was also concentrated within groups. Brazil supplied US$1.31 trillion per "
    "year, followed by the Russian Federation at US$589 billion and the United States at US$579 "
    "billion. The ten largest providers accounted for 57.4% of the global total, and the Gini "
    "coefficient reached 0.856. Figure 1 combines this concentration with the relationship between "
    "Green Carbon Wealth and economic size. Their rank correlation was only moderate (Spearman "
    "rho = 0.55), which shows that ecological endowment and gross domestic product capture different "
    "dimensions of national wealth. The country ranking inherits the spatial resolution and common "
    "biome rates of the accounting framework."
)

R2_COMPOSITION = (
    "Adding Blue Carbon Wealth changed the composition of national carbon wealth across the 175 of "
    "242 units for which both components supported classification. Small island developing states "
    "included 33 blue-dominant and 10 green-dominant units, whereas least developed countries "
    "included 15 green-dominant and one blue-dominant unit. Developed economies included 21 "
    "green-dominant and 11 blue-dominant units, and developing economies included 30 and 16, "
    "respectively. Large exclusive economic zones make the ocean component particularly important "
    "for island territories, while extensive tropical forests drive the least-developed-country "
    "profile. Figure 2 shows these contrasts under the two-thirds dominance threshold. The categories "
    "describe composition and do not imply that forest and ocean processes are interchangeable."
)

R2_BALANCE = (
    "The ocean component also changed national net balances. Among 210 units with emissions and "
    "sequestration data, the share classified as net sinks rose from 37% with forests alone to 52% "
    "with forests and the ocean. The biological carbon pump operates across large maritime areas, so "
    "it can exceed fossil-fuel and industrial emissions in coastal states with relatively low "
    "emissions. The reclassification did not remove the separation between emitters and providers. "
    "The ten largest emitters produced 74% of global emissions, whereas the ten largest sinks supplied "
    "39% of accounted sequestration. Only the Russian Federation and Indonesia appeared in both sets. "
    "A net-sink classification describes an annual balance under the selected boundary and does not "
    "establish a trajectory compatible with climate neutrality."
)

R2_TRANSITION = (
    "Natural Carbon Wealth remains a lower bound for 61 forest units without a known blue component. "
    "This coverage constraint does not affect the forest account, but it limits comparisons of the "
    "combined profile. More importantly, the annual balance does not indicate whether sink capacity "
    "is stable through time. The next analysis therefore turns to the forest component, for which "
    "reported deforestation provides an observed measure of annual erosion."
)

R3_LOSS = (
    "Reported deforestation averaged 9.70 Mha per year over 2010–2019. Brazil reported 2.27 Mha per "
    "year, followed by India at 0.67 Mha, the Democratic Republic of the Congo at 0.65 Mha, Indonesia "
    "at 0.54 Mha and Angola at 0.51 Mha. Across reporting units, this removed 45.9 MtCO₂ per year of "
    "future uptake capacity and US$25.7 billion per year of Green Carbon Wealth, with a 5th–95th "
    "percentile interval of US$9.79–49.58 billion (Table 3). The loss equalled 0.40% of the Green "
    "Carbon Wealth of reporting units each year. It measures foregone annual uptake after conversion, "
    "not the release of carbon already stored in vegetation and soils. The estimates cover 139 of 236 "
    "forest units and 79% of global Green Carbon Wealth."
)

R3_CUMULATIVE = (
    "The annual percentage is small relative to the service, but the loss persists in every subsequent "
    "year. At the same rate, cumulative erosion would remove 4.0% of current capacity over ten years. "
    "Capitalising one permanent annual loss at 2% gives an illustrative value of US$1.28 trillion. "
    "Developing economies accounted for 58.5% of the reported value loss and least developed countries "
    "for 34.7%, compared with 5.8% in developed economies and 1.0% in small island developing states. "
    "The geography of erosion therefore concentrates the loss in the groups for which Green Carbon "
    "Wealth also represents the largest share of measured output. These shares apply only to reporting "
    "units and must not be interpreted as complete group totals."
)

R3_TYPOLOGY = (
    "The magnitude of the current service did not predict erosion intensity (Spearman rho = −0.09, "
    "p = 0.36). Figure 3 separates 28 units with a large service and low erosion, 25 with a large "
    "service and high erosion, 28 with a small service and high erosion, and 24 with a small service "
    "and low erosion. The near-even distribution across these four profiles explains why protection "
    "priorities cannot be inferred from the size of a country's current sink. The typology is restricted "
    "to units with reported deforestation and uses relative thresholds for description rather than "
    "causal classification."
)

R3_TRENDS = (
    "Reported global deforestation declined from 15.8 Mha per year in the 1990s to 8.5 Mha per year "
    "in the latest period. The Theil–Sen slope was −272 kha per year per year, and the Mann–Kendall "
    "test gave p = 0.03. Earlier regional losses reached 3.3–3.6 Mha per year in Africa and 7.3 Mha "
    "per year in South America during the 1990s. At country level, only Indonesia (p = 0.027) and "
    "Paraguay (p = 0.050) showed a significant decline, while the decline in Brazil was not significant. "
    "The global trend therefore indicates slower reported loss, not an end to the cumulative erosion of "
    "sink capacity. Five reporting intervals and incomplete country coverage limit the strength of the inference."
)

R4_COST = (
    "The welfare value of lost capacity and the cost of replacing that capacity use two different prices "
    "for the same tonne. The Global Social Cost of Carbon values avoided climate damages, whereas the "
    "abatement price approximates replacement effort. Across the 139 reporting forest units, illustrative "
    "prices of US$50, US$150 and US$400 per tCO₂ produced annual costs of US$2.29, US$6.88 and "
    "US$18.36 billion (Table 4). These amounts equal 0.09, 0.27 and 0.71 of the annual welfare value "
    "lost. Ratios below one follow from the selected price cases and do not demonstrate that compensation "
    "would be cheaper under every technology, location or policy constraint."
)

R4_BURDEN = (
    "The allocation rule changed who carried this cost. At US$150 per tCO₂, least developed countries "
    "would pay US$2.39 billion per year if each country replaced the capacity lost on its own territory, "
    "but US$0.11 billion under an allocation proportional to gross domestic product. Developed economies "
    "would move in the opposite direction, from US$0.40 billion to US$2.84 billion. Under domestic "
    "allocation, the burden reached 1.44% of gross domestic product in the Central African Republic, "
    "1.21% in Somalia and 0.95% in Mozambique. Figure 4 contrasts the location of the loss with the "
    "distribution of payment capacity. The scenarios are burden-sharing illustrations for the 139 "
    "reporting units, not predictions of a carbon market or statements of legal responsibility."
)

R4_OCEAN = (
    "The ocean scenarios show that a wider erosion of natural sinks could change the scale of the problem. "
    "A 5% decline in accounted blue carbon sequestration would remove 208 MtCO₂ per year, 4.5 times the "
    "observed annual forest-capacity loss, and US$116 billion per year of welfare value. A 10% decline "
    "would remove 416 MtCO₂ per year and US$233 billion per year. These values apply the scenario to the "
    "published blue account and are not observed ocean losses. Together with the forest results, they show "
    "that a modest proportional weakening of a large recurring service can dominate the annual loss now "
    "measured from reported deforestation."
)


def main() -> None:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with ZipFile(ARTICLE) as source:
        package = {item.filename: source.read(item.filename) for item in source.infolist()}
    root = etree.fromstring(package["word/document.xml"])
    body = root.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("Document body is missing")
    change_id = next_id(root)

    grouped = matches(body, "Forests generated Green Carbon Wealth")
    change_id = replace(grouped[0], R1_GLOBAL, change_id, stamp)
    for duplicate in grouped[1:]:
        change_id = delete_active(duplicate, change_id, stamp)

    grouped = matches(body, "Tropical forests accounted")
    change_id = replace(grouped[0], R1_BIOMES, change_id, stamp)
    for duplicate in grouped[1:]:
        change_id = delete_active(duplicate, change_id, stamp)

    grouped = matches(body, "Developing economies supplied")
    change_id = replace(grouped[0], R1_GROUPS, change_id, stamp)
    change_id = replace(grouped[1], R1_CONCENTRATION, change_id, stamp)

    change_id = replace(find_one(body, "Blue Carbon Wealth changed"), R2_COMPOSITION, change_id, stamp)
    change_id = replace(find_one(body, "Adding the ocean component increased"), R2_BALANCE, change_id, stamp)
    change_id = replace(find_one(body, "At the current debt-stress threshold"), R2_TRANSITION, change_id, stamp)

    grouped = matches(body, "Reported deforestation averaged")
    change_id = replace(grouped[0], R3_LOSS, change_id, stamp)
    for duplicate in grouped[1:]:
        change_id = delete_active(duplicate, change_id, stamp)
    change_id = replace(find_one(body, "The annual percentage is small"), R3_CUMULATIVE, change_id, stamp)

    grouped = matches(body, "Service magnitude and erosion intensity")
    change_id = replace(grouped[0], R3_TYPOLOGY, change_id, stamp)
    change_id = replace(grouped[1], R3_TRENDS, change_id, stamp)

    change_id = replace(find_one(body, "The welfare value of lost capacity"), R4_COST, change_id, stamp)
    change_id = replace(find_one(body, "Who loses a forest service"), R4_BURDEN, change_id, stamp)
    change_id = replace(find_one(body, "The ocean component shows"), R4_OCEAN, change_id, stamp)

    captions = {
        "Table1.": ("Table 1.", "Global annual Green, Blue, and Natural Carbon Wealth in 2015 US dollars."),
        "Table2.": ("Table 2.", "Country-group profiles of Green Carbon Wealth and sink composition."),
        "Table3.": ("Table 3.", "Annual loss of forest sink service, 2010–2019, among reporting units."),
        "Table4.": ("Table 4.", "Illustrative annual compensation costs under alternative abatement prices."),
        "Figure1.": ("Figure 1.", "Forest carbon wealth, economic size, and concentration."),
        "Figure2.": ("Figure 2.", "Blue carbon composition and national carbon balances."),
        "Figure3.": ("Figure 3.", "Service magnitude and erosion intensity."),
        "Figure4.": ("Figure 4.", "Location of sink loss and allocation of compensation costs."),
    }
    for old_prefix, (label, title) in captions.items():
        change_id = replace_caption(find_one(body, old_prefix), label, title, change_id, stamp)

    figure_four = find_one(body, "Figure 4.")
    discussion = find_one(body, "Discussion and limitations")
    paragraphs = body.findall("w:p", namespaces=NS)
    residuals = {"US$", "distribution", "; Hilmi et al., 2026", "-"}
    for paragraph in paragraphs[paragraphs.index(figure_four) + 1 : paragraphs.index(discussion)]:
        if active_text(paragraph) in residuals:
            change_id = delete_active(paragraph, change_id, stamp)

    package["word/document.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_suffix(".editing.docx")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as target:
        for name, payload in package.items():
            target.writestr(name, payload)
    temporary.replace(ARTICLE)
    print(f"Results reworked through change id {change_id}.")


if __name__ == "__main__":
    main()
