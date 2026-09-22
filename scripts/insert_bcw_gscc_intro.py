"""Insert the BCW-consistent carbon-value statement into the Introduction."""

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
ANCHOR = "Forests are a major part of the global carbon sink"
INSERTION = (
    "The Global Social Cost of Carbon (GSCC) provides a welfare-based measure of avoided marginal "
    "climate damages. To maintain direct comparability with BCW, annual removal is valued at the final "
    "mean structure-adjusted GSCC used by Hilmi et al. (2026): 559.6 constant 2015 US dollars per tonne "
    "of carbon dioxide."
)


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def visible_text(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def next_change_id(document: etree._Element) -> int:
    ids = []
    for value in document.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return max(ids, default=0) + 1


def make_inserted_paragraph(
    text: str, properties: etree._Element | None, change_id: int, date: str
) -> etree._Element:
    paragraph = etree.Element(w("p"))
    if properties is not None:
        paragraph.append(deepcopy(properties))
    insertion = etree.SubElement(paragraph, w("ins"))
    insertion.set(w("id"), str(change_id))
    insertion.set(w("author"), "Codex")
    insertion.set(w("date"), date)
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
    if INSERTION in "".join(document.xpath(".//w:t/text()", namespaces=NS)):
        raise RuntimeError("The BCW-consistent GSCC statement is already present.")
    anchors = [
        paragraph
        for paragraph in body.findall("w:p", namespaces=NS)
        if visible_text(paragraph).startswith(ANCHOR)
    ]
    if len(anchors) != 1:
        raise RuntimeError(f"Expected one Introduction anchor; found {len(anchors)}.")
    anchor = anchors[0]
    properties = anchor.find("w:pPr", namespaces=NS)
    paragraph = make_inserted_paragraph(INSERTION, properties, next_change_id(document), date)
    body.insert(body.index(anchor) + 1, paragraph)

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.intro-gscc.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print("Inserted the BCW-consistent GSCC statement as a tracked revision.")


if __name__ == "__main__":
    main()
