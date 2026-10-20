"""Remove colon-led prose constructions from active manuscript paragraphs.

References, URLs and table/figure material are deliberately out of scope.  Each
replacement is inserted as a new tracked paragraph while the prior active text
is retained as a tracked deletion.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}

REPLACEMENTS = {
    "Recent studies clarify why these distinctions matter.": (
        "Recent studies clarify why these distinctions matter. Thaller et al. (2026) value land-sink "
        "contributions to inclusive wealth with country social costs of carbon. Favero and Austin (2026) "
        "estimate future, policy-induced forest mitigation and its marginal cost under alternative carbon-price "
        "paths. Rickels et al. (2024) show how a weaker ocean sink can increase the cost of meeting climate "
        "targets. These studies address related but distinct objects. They include a service provided by a "
        "reference-period sink, additional mitigation relative to a baseline, and the policy cost of a weakened sink."
    ),
    "Our purpose is not to claim the first valuation": (
        "Our purpose is not to claim the first valuation of a terrestrial sink, nor to infer a tradable entitlement "
        "from natural-carbon wealth. Instead, we provide a harmonised account of four connected facts. These are "
        "the magnitude and distribution of forest service, the change introduced by the ocean component, the erosion "
        "of the forest service, and the distributional implications of compensating for that erosion. This framework "
        "makes clear which results are measured, which are scenarios, and which policy interpretations remain "
        "conditional on future choices about abatement technology and burden sharing."
    ),
    "Forests generated Green Carbon Wealth (GCW)": (
        "Forests generated Green Carbon Wealth (GCW) of US$8.16 trillion per year in constant 2015 prices, with a "
        "5th-95th percentile interval of US$3.15-15.49 trillion. Blue Carbon Wealth added US$2.33 trillion per "
        "year, so Natural Carbon Wealth reached US$10.49 trillion per year and forests accounted for 77.8% of the "
        "combined account (Table 1). These are annual welfare values of CO2 uptake. They do not value stored forest "
        "carbon or a cash flow available to the countries where forests occur."
    ),
    "Tropical forests accounted for 78.6%": (
        "Tropical forests accounted for 78.6% of global uptake, compared with 13.4% for temperate forests and 8.0% "
        "for boreal forests. This dominance follows directly from the accounting mechanism. Tropical forests combine "
        "the largest estimated area (2,373 million ha) with the highest biome-average uptake rate (1.32 tC ha^-1 "
        "year^-1), compared with 0.87 in temperate forests and 0.28 in boreal forests. The result therefore reflects "
        "both extent and per-hectare uptake, rather than area alone."
    ),
    "Developing economies supplied 51.4%": (
        "Developing economies supplied 51.4% of global GCW, developed economies 27.7%, least developed countries "
        "18.1%, and small island developing states 2.8%. GCW equalled 8.9% of global GDP, but the median ratio was "
        "75.1% in least developed countries and 2.7% in developed economies. This contrast reflects the GDP "
        "denominator as well as forest endowment. A similar physical service represents a much larger share of recorded "
        "output where measured economies are small. GCW and GDP were only moderately associated (Spearman correlation "
        "= 0.55). The distribution also differed across country groups (Kruskal-Wallis H = 48.1, p = 2 × 10−10). "
        "Figure 1 and Table 2 show that a Gini coefficient of 0.856 leaves policy based on GCW concentrated in a small "
        "number of countries. The ten largest contributors supplied 57.4% of the global total."
    ),
    "Reported deforestation averaged 9.70 million ha": (
        "Reported deforestation averaged 9.70 million ha per year over 2010-2019. It removed an estimated 45.9 MtCO2 "
        "per year of future sequestration capacity, equivalent to US$25.7 billion per year of GCW, with a 5th-95th "
        "percentile interval of US$9.79-49.58 billion, and 0.40% of GCW among reporting units each year (Table 3). "
        "This is an annual service-capacity loss. Once forest is converted, the uptake that it would have provided is "
        "no longer available in subsequent years."
    ),
    "Service magnitude and erosion intensity": (
        "Service magnitude and erosion intensity were not correlated (Spearman correlation = -0.09, p > 0.05). "
        "Figure 3 shows why the size of a current sink is not a reliable guide to erosion risk. Countries that provide "
        "a large service are not systematically the countries with the most rapid proportional loss. Reported "
        "deforestation declined from 15.8 million ha per year in the 1990s to 8.5 million ha per year in the latest "
        "period. The global Theil-Sen slope was -272 thousand ha per year per year and the Mann-Kendall test gave p = "
        "0.03. This evidence does not support acceleration, but it does not remove the cumulative effect of continued "
        "loss. The estimates cover 139 of 236 accounting units and 79% of global GCW; missing FRA reports do not indicate "
        "zero deforestation."
    ),
    "Who loses a forest service is not necessarily": (
        "Who loses a forest service is not necessarily who can afford to pay for its replacement. Under domestic "
        "compensation at US$150 per tCO2, least developed countries paid US$2.39 billion per year. Under a shared "
        "allocation proportional to GDP, their contribution fell to US$0.11 billion per year. The domestic burden reached "
        "1.44% of GDP in the Central African Republic, 1.21% in Somalia, and 0.95% in Mozambique. Figure 4 shows the "
        "mechanism. Erosion occurs where forests are lost, while GDP capacity is concentrated elsewhere. These are "
        "allocation rules, not estimates of a functioning international carbon market."
    ),
    "Our results reveal strong spatial and economic asymmetries.": (
        "Our results reveal strong spatial and economic asymmetries. Developing economies and LDCs account for a "
        "substantial share of global carbon uptake, largely driven by tropical forests (Pan et al., 2011; Pan et al., "
        "2024). For example, countries such as Brazil and the Democratic Republic of Congo emerge as major contributors "
        "in absolute terms, while smaller forest rich countries such as Guyana or Gabon exhibit high values relative to "
        "population and GDP. This contrast highlights a key insight. Ecosystem-based climate services are not aligned "
        "with economic size, creating a structural imbalance between global benefits and national fiscal capacity."
    ),
    "The service is concentrated because tropical forests": (
        "The service is concentrated because tropical forests combine the largest forest area with the highest "
        "biome-specific uptake rate. They supply 78.6% of global uptake. The economic interpretation differs from a "
        "ranking of GDP. The Gini coefficient of 0.856 means that a small number of countries provide most of the "
        "quantified service, whereas the modest GCW-GDP correlation shows that ecological endowment and economic size "
        "are different dimensions. The high GCW-to-GDP ratios in least developed countries reflect a small GDP denominator "
        "as well as forest endowment. They identify a large unpriced service relative to measured output, not a "
        "transferable income stream."
    ),
    "The erosion results add a temporal dimension": (
        "The erosion results add a temporal dimension that a static wealth account cannot provide. Reported deforestation "
        "removes US$25.7 billion per year of annual GCW capacity, with a 5th-95th percentile interval of US$9.79-49.58 "
        "billion. The annual fraction is small relative to the service, but it is persistent. A permanent loss at the "
        "observed rate reaches 4.0% over a decade and has a capitalised value of US$1.28 trillion at a 2% discount rate. "
        "The service-to-erosion correlation is close to zero. Protecting only the largest current sinks would therefore "
        "miss countries where a modest service is eroding rapidly."
    ),
}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def visible_text(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def next_change_id(document: etree._Element) -> int:
    values = []
    for value in document.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            values.append(int(value))
        except ValueError:
            continue
    return max(values, default=0) + 1


def revision_attributes(element: etree._Element, change_id: int, date: str) -> None:
    element.set(w("id"), str(change_id))
    element.set(w("author"), "Codex")
    element.set(w("date"), date)


def deletion_from_active_child(child: etree._Element, change_id: int, date: str) -> etree._Element:
    deletion = etree.Element(w("del"))
    revision_attributes(deletion, change_id, date)
    children = list(child) if child.tag == w("ins") else [child]
    for source in children:
        replacement = deepcopy(source)
        for descendant in replacement.iter():
            if descendant.tag == w("t"):
                descendant.tag = w("delText")
        deletion.append(replacement)
    return deletion


def inserted_paragraph(text: str, properties: etree._Element | None, change_id: int, date: str) -> etree._Element:
    paragraph = etree.Element(w("p"))
    if properties is not None:
        paragraph.append(deepcopy(properties))
    insertion = etree.SubElement(paragraph, w("ins"))
    revision_attributes(insertion, change_id, date)
    run = etree.SubElement(insertion, w("r"))
    etree.SubElement(run, w("t")).text = text
    return paragraph


def main() -> None:
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    body = document.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("The document has no body.")
    change_id = next_change_id(document)

    for anchor, replacement in REPLACEMENTS.items():
        matches = [
            paragraph
            for paragraph in body.findall("w:p", namespaces=NS)
            if visible_text(paragraph).startswith(anchor)
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one paragraph beginning {anchor!r}; found {len(matches)}.")
        paragraph = matches[0]
        if paragraph.xpath(".//w:commentReference", namespaces=NS):
            if anchor != "Our results reveal strong spatial and economic asymmetries.":
                raise RuntimeError(f"Refusing to rewrite comment-anchored paragraph {anchor!r}.")
            run = next(
                run
                for run in paragraph.findall("w:r", namespaces=NS)
                if "This contrast highlights a key insight:" in visible_text(run)
            )
            replacement_run = deepcopy(run)
            for text_node in replacement_run.findall(".//w:t", namespaces=NS):
                text_node.text = (text_node.text or "").replace(
                    "This contrast highlights a key insight:",
                    "This contrast highlights a key insight.",
                )
            deletion = deletion_from_active_child(run, change_id, date)
            paragraph.replace(run, deletion)
            insertion = etree.Element(w("ins"))
            revision_attributes(insertion, change_id + 1, date)
            insertion.append(replacement_run)
            paragraph.insert(paragraph.index(deletion) + 1, insertion)
            change_id += 2
            continue
        for child in list(paragraph):
            if child.tag not in {w("r"), w("ins")}:
                continue
            deletion = deletion_from_active_child(child, change_id, date)
            paragraph.replace(child, deletion)
            change_id += 1
        new_paragraph = inserted_paragraph(
            replacement, paragraph.find("w:pPr", namespaces=NS), change_id, date
        )
        body.insert(body.index(paragraph) + 1, new_paragraph)
        change_id += 1

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.colons-refined.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Rewrote {len(REPLACEMENTS)} prose paragraphs as tracked revisions.")


if __name__ == "__main__":
    main()
