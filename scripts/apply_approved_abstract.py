"""Insert the author-approved abstract as a Word tracked revision.

The preceding draft abstract remains visible as a tracked deletion.  No
comments, reviewer changes, or prior redlines are accepted or removed.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def paragraph_text(paragraph: etree._Element) -> str:
    return "".join(
        node.text or ""
        for node in paragraph.xpath(".//w:t | .//w:delText", namespaces=NS)
    )


def revision_attributes(element: etree._Element, change_id: int, date: str) -> None:
    element.set(w("id"), str(change_id))
    element.set(w("author"), "Codex")
    element.set(w("date"), date)


def next_change_id(document: etree._Element) -> int:
    ids = []
    for value in document.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return max(ids, default=0) + 1


def mark_insertion_deleted(paragraph: etree._Element, change_id: int, date: str) -> None:
    """Replace the previous draft insertion with a normal tracked deletion."""
    for insertion in list(paragraph.findall("w:ins", namespaces=NS)):
        deletion = etree.Element(w("del"))
        revision_attributes(deletion, change_id, date)
        for child in list(insertion):
            replacement = deepcopy(child)
            for text in replacement.findall(".//w:t", namespaces=NS):
                text.tag = w("delText")
            deletion.append(replacement)
        paragraph.replace(insertion, deletion)


def make_inserted_paragraph(
    text: str,
    properties: etree._Element | None,
    change_id: int,
    date: str,
) -> etree._Element:
    paragraph = etree.Element(w("p"))
    if properties is not None:
        paragraph.append(deepcopy(properties))
    insertion = etree.SubElement(paragraph, w("ins"))
    revision_attributes(insertion, change_id, date)
    run = etree.SubElement(insertion, w("r"))
    text_node = etree.SubElement(run, w("t"))
    text_node.text = text
    return paragraph


def main() -> None:
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}

    document = etree.fromstring(package["word/document.xml"])
    body = document.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("The document has no body.")
    paragraphs = body.findall("w:p", namespaces=NS)
    abstract_index = next(
        i for i, paragraph in enumerate(paragraphs) if paragraph_text(paragraph).strip() == "Abstract"
    )
    acronyms_index = next(
        i for i, paragraph in enumerate(paragraphs) if paragraph_text(paragraph).strip() == "Acronyms"
    )
    prior_draft = [
        paragraph
        for paragraph in paragraphs[abstract_index + 1 : acronyms_index]
        if paragraph.find("w:ins", namespaces=NS) is not None
        and "Forest carbon uptake is a major climate-regulation service" in paragraph_text(paragraph)
        or paragraph.find("w:ins", namespaces=NS) is not None
        and "GCW reached US$8.16 trillion" in paragraph_text(paragraph)
        or paragraph.find("w:ins", namespaces=NS) is not None
        and "Reported deforestation across 139 reporting units" in paragraph_text(paragraph)
    ]
    if len(prior_draft) != 3:
        raise RuntimeError(f"Expected three prior draft paragraphs; found {len(prior_draft)}.")

    change_id = next_change_id(document)
    for paragraph in prior_draft:
        mark_insertion_deleted(paragraph, change_id, date)
        change_id += 1

    properties = prior_draft[0].find("w:pPr", namespaces=NS)
    approved_abstract = (
        "Forests and oceans remove carbon dioxide, but their contributions to national wealth and "
        "consequences of loss are poorly quantified. Here we estimate annual forest uptake value for "
        "236 countries and territories from forest observations, uptake rates, and a carbon value for "
        "avoided climate damages. We combine estimates with published ocean values and national "
        "emissions, economic, and deforestation data. Forest uptake was worth 8.16 trillion 2015 United "
        "States dollars annually and represented 78% of the combined forest and ocean value. Tropical "
        "forests provided 79% of forest uptake. Forest value represented a much larger share of economic "
        "output in least developed countries than in developed economies. Ocean uptake increased the share "
        "of countries that remove more carbon dioxide than they release from 37% to 52%. Reported "
        "deforestation removed annual uptake capacity worth 25.7 billion 2015 United States dollars. These "
        "results identify unequal providers of climate regulation and unequal exposure to its loss."
    )
    position = body.index(prior_draft[-1]) + 1
    body.insert(position, make_inserted_paragraph(approved_abstract, properties, change_id, date))

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.abstract-approved.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print("Inserted the approved abstract as a tracked revision.")


if __name__ == "__main__":
    main()
