"""Restore the existing Introduction and update only the commented SCC passage.

The earlier full-introduction replacement is withdrawn because it displaced the
user's reviewed text.  The original Introduction is restored, while the SCC
passage remains a visible deletion and the BCW-consistent formulation is added
immediately after it as a normal Word insertion.
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
NEW_SCC_TEXT = (
    "The Global Social Cost of Carbon (GSCC) provides a welfare-based measure of avoided marginal "
    "climate damages. To maintain direct comparability with BCW, annual removal is valued using the final "
    "mean structure-adjusted GSCC estimated by Hilmi et al. (2026), US$559.6 ± 268.6 per tCO2 in constant "
    "2015 prices, with a 5th–95th percentile interval of US$218.5–1,015.9 per tCO2. Applied to global forest "
    "carbon uptake, this valuation represents annual avoided damages rather than a market price or financing "
    "entitlement. Such values are rarely incorporated into macroeconomic indicators, and uncertainty in carbon "
    "data and valuation assumptions remains important."
)


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def visible_text(element: etree._Element) -> str:
    return "".join(node.text or "" for node in element.xpath(".//w:t", namespaces=NS))


def all_text(element: etree._Element) -> str:
    return "".join(node.text or "" for node in element.xpath(".//w:t | .//w:delText", namespaces=NS))


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


def restore_coded_deletion(paragraph: etree._Element, deletion: etree._Element) -> None:
    """Restore a Codex-only text deletion, retaining every user revision."""
    restored_children = []
    for child in list(deletion):
        restored = deepcopy(child)
        for text in restored.findall(".//w:delText", namespaces=NS):
            text.tag = w("t")
        restored_children.append(restored)
    position = paragraph.index(deletion)
    paragraph.remove(deletion)
    for offset, child in enumerate(restored_children):
        paragraph.insert(position + offset, child)


def deletion_from_insertion(insertion: etree._Element, change_id: int, date: str) -> etree._Element:
    deletion = etree.Element(w("del"))
    revision_attributes(deletion, change_id, date)
    for child in list(insertion):
        copied = deepcopy(child)
        for text in copied.findall(".//w:t", namespaces=NS):
            text.tag = w("delText")
        deletion.append(copied)
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
    paragraphs = body.findall("w:p", namespaces=NS)
    intro = next(paragraph for paragraph in paragraphs if visible_text(paragraph).strip() == "Introduction")
    first_results = next(
        paragraph for paragraph in paragraphs[paragraphs.index(intro) + 1 :] if visible_text(paragraph).strip() == "Results"
    )
    intro_paragraphs = paragraphs[paragraphs.index(intro) + 1 : paragraphs.index(first_results)]
    target = next(
        paragraph for paragraph in intro_paragraphs if "The Social Cost of Carbon (SCC)" in all_text(paragraph)
    )

    # Restore the original reviewed introduction, except for the outdated SCC paragraph.
    for paragraph in intro_paragraphs:
        for deletion in list(paragraph.findall("w:del", namespaces=NS)):
            if deletion.get(w("author")) != "Codex":
                continue
            if paragraph is target:
                comment_start = next(
                    element for element in paragraph if element.tag == w("commentRangeStart") and element.get(w("id")) == "356"
                )
                if paragraph.index(deletion) >= paragraph.index(comment_start):
                    continue
            restore_coded_deletion(paragraph, deletion)

    # The two historical US$ insertions belong to the superseded SCC sentence.
    change_id = next_change_id(document)
    for insertion in list(target.findall("w:ins", namespaces=NS)):
        target.replace(insertion, deletion_from_insertion(insertion, change_id, date))
        change_id += 1

    if NEW_SCC_TEXT not in "".join(document.xpath(".//w:t/text()", namespaces=NS)):
        new_paragraph = inserted_paragraph(
            NEW_SCC_TEXT, target.find("w:pPr", namespaces=NS), change_id, date
        )
        body.insert(body.index(target) + 1, new_paragraph)

    # Withdraw the misplaced replacement Introduction and the orphaned old Results heading.
    first_results = next(
        paragraph for paragraph in body.findall("w:p", namespaces=NS) if paragraph is first_results
    )
    methods = next(
        paragraph
        for paragraph in body.findall("w:p", namespaces=NS)[body.findall("w:p", namespaces=NS).index(first_results) + 1 :]
        if visible_text(paragraph).strip() == "Methods"
    )
    to_remove = list(body)[body.index(first_results) : body.index(methods)]
    for element in to_remove:
        body.remove(element)

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.intro-restored.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:
        for name, data in package.items():
            target_zip.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print("Restored the original Introduction and inserted the BCW SCC update in place.")


if __name__ == "__main__":
    main()
