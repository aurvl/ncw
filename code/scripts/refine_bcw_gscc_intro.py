"""Replace the preliminary GSCC sentence with BCW uncertainty and article-style punctuation."""

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
ANCHOR = "The Global Social Cost of Carbon (GSCC) provides a welfare-based measure"
REPLACEMENT = (
    "The Global Social Cost of Carbon (GSCC) provides a welfare-based measure of avoided marginal "
    "climate damages. To maintain direct comparability with BCW, annual removal is valued using the final "
    "mean structure-adjusted GSCC estimated by Hilmi et al. (2026), US$559.6 ± 268.6 per tCO2 in "
    "constant 2015 prices, with a 5th-95th percentile interval of US$218.5-1,015.9 per tCO2."
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


def revision_attributes(element: etree._Element, change_id: int, date: str) -> None:
    element.set(w("id"), str(change_id))
    element.set(w("author"), "Codex")
    element.set(w("date"), date)


def deletion_from_insertion(insertion: etree._Element, change_id: int, date: str) -> etree._Element:
    deletion = etree.Element(w("del"))
    revision_attributes(deletion, change_id, date)
    for child in list(insertion):
        replacement = deepcopy(child)
        for text in replacement.findall(".//w:t", namespaces=NS):
            text.tag = w("delText")
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
    matches = [p for p in body.findall("w:p", namespaces=NS) if visible_text(p).startswith(ANCHOR)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one active GSCC paragraph; found {len(matches)}.")
    previous = matches[0]
    old_insertion = previous.find("w:ins", namespaces=NS)
    if old_insertion is None:
        raise RuntimeError("The preliminary GSCC paragraph is not a tracked insertion.")
    change_id = next_change_id(document)
    previous.replace(old_insertion, deletion_from_insertion(old_insertion, change_id, date))
    new_paragraph = inserted_paragraph(
        REPLACEMENT, previous.find("w:pPr", namespaces=NS), change_id + 1, date
    )
    body.insert(body.index(previous) + 1, new_paragraph)

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.intro-gscc-refined.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print("Refined the BCW-consistent GSCC statement as a tracked revision.")


if __name__ == "__main__":
    main()
