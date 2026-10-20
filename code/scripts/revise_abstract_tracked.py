"""Replace the manuscript abstract through Word tracked revisions.

The edit works directly on OOXML so existing reviewer comments and prior
redlines stay in place.  Old abstract runs become tracked deletions and the
new three-paragraph abstract is inserted as tracked text.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import os
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def text_of(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def direct_paragraphs(body: etree._Element) -> list[etree._Element]:
    return body.findall("w:p", namespaces=NS)


def one_exact(body: etree._Element, text: str) -> etree._Element:
    matches = [p for p in direct_paragraphs(body) if text_of(p).strip() == text]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph {text!r}; found {len(matches)}.")
    return matches[0]


def next_change_id(root: etree._Element) -> int:
    values: list[int] = []
    for value in root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            values.append(int(value))
        except ValueError:
            continue
    return max(values, default=0) + 1


def revision_attributes(element: etree._Element, change_id: int, date: str) -> None:
    element.set(w("id"), str(change_id))
    element.set(w("author"), "Codex")
    element.set(w("date"), date)


def make_tracked_paragraph(text: str, properties: etree._Element | None, change_id: int, date: str) -> etree._Element:
    paragraph = etree.Element(w("p"))
    if properties is not None:
        paragraph.append(deepcopy(properties))
    insertion = etree.SubElement(paragraph, w("ins"))
    revision_attributes(insertion, change_id, date)
    run = etree.SubElement(insertion, w("r"))
    text_node = etree.SubElement(run, w("t"))
    if text.startswith(" ") or text.endswith(" "):
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    return paragraph


def delete_ordinary_runs(paragraph: etree._Element, change_id: int, date: str) -> int:
    """Mark old abstract text as deleted but preserve review metadata."""
    for child in list(paragraph):
        if child.tag != w("r"):
            continue
        if child.find("w:commentReference", namespaces=NS) is not None:
            continue
        deleted_run = deepcopy(child)
        for text_node in deleted_run.findall(".//w:t", namespaces=NS):
            text_node.tag = w("delText")
        deletion = etree.Element(w("del"))
        revision_attributes(deletion, change_id, date)
        deletion.append(deleted_run)
        paragraph.replace(child, deletion)
        change_id += 1
    return change_id


def enable_track_revisions(settings: etree._Element) -> None:
    if settings.find("w:trackRevisions", namespaces=NS) is None:
        settings.insert(0, etree.Element(w("trackRevisions")))


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
    abstract_heading = one_exact(body, "Abstract")
    acronyms_heading = one_exact(body, "Acronyms")
    children = list(body)
    start, end = children.index(abstract_heading), children.index(acronyms_heading)
    old_abstract = [p for p in children[start + 1 : end] if p.tag == w("p") and text_of(p).strip()]
    if len(old_abstract) != 3:
        raise RuntimeError(f"Expected three old abstract paragraphs; found {len(old_abstract)}.")
    change_id = next_change_id(document)
    for paragraph in old_abstract:
        change_id = delete_ordinary_runs(paragraph, change_id, date)

    body_properties = old_abstract[0].find("w:pPr", namespaces=NS)
    replacement = [
        "Forest carbon uptake is a major climate-regulation service, yet standard wealth measures rarely represent it. We estimate annual Green Carbon Wealth (GCW) for 236 national accounting units from harmonised forest data and biome-specific uptake rates. We combine GCW with Blue Carbon Wealth (BCW) to describe Natural Carbon Wealth (NCW), national sink profiles, and net balances. We also quantify the erosion of forest service from reported deforestation and compare domestic and GDP-shared compensation allocations.",
        "GCW reached US$8.16 trillion per year in 2015 prices (5th-95th percentile: US$3.15-15.49 trillion), or 77.8% of NCW (US$10.49 trillion). Tropical forests supplied 78.6% of uptake and developing economies held 51.4% of global GCW. GCW equalled 8.9% of global GDP, but the group median reached 75.1% of GDP in least developed countries and 2.7% in developed economies. Adding BCW increased the share of accounting units with a net sink from 37% to 52%.",
        "Reported deforestation across 139 reporting units removed 45.9 MtCO₂ per year of sink capacity, equal to US$25.7 billion per year of GCW and 0.40% of the reported service each year. At illustrative abatement prices, annual replacement costs ranged from US$2.29 to US$18.36 billion. A GDP-shared allocation reduced the annual charge for least developed countries from US$2.39 billion under domestic compensation to US$0.11 billion. Forest and marine sinks therefore provide a large but concentrated global service. Their erosion exposes countries that depend on this service most, while an equitable response requires a burden-sharing rule that does not assign the whole cost to sink-hosting countries.",
    ]
    position = body.index(old_abstract[-1]) + 1
    for offset, paragraph_text in enumerate(replacement):
        body.insert(position + offset, make_tracked_paragraph(paragraph_text, body_properties, change_id, date))
        change_id += 1
    package["word/document.xml"] = etree.tostring(document, xml_declaration=True, encoding="UTF-8", standalone=True)
    package["word/settings.xml"] = etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True)
    temporary = ARTICLE.with_name("Article_Green_Carbon.abstract-revised.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Replaced abstract through tracked revisions in {ARTICLE}")


if __name__ == "__main__":
    main()
