"""Mark replaced abstract and legacy Results paragraphs as deleted revisions.

Some old paragraphs contain historical inserted fragments.  A paragraph-mark
deletion keeps those historical revisions in the XML but ensures that Word
hides the complete old paragraph in the revised text.
"""

from __future__ import annotations

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


def all_text(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t | .//w:delText", namespaces=NS))


def find_one(body: etree._Element, fragment: str) -> etree._Element:
    matches = [p for p in body.findall("w:p", namespaces=NS) if fragment in all_text(p)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph with {fragment!r}; found {len(matches)}.")
    return matches[0]


def next_change_id(root: etree._Element) -> int:
    values: list[int] = []
    for value in root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            values.append(int(value))
        except ValueError:
            continue
    return max(values, default=0) + 1


def mark_paragraph_deleted(paragraph: etree._Element, change_id: int, date: str) -> int:
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
    deletion.set(w("id"), str(change_id))
    deletion.set(w("author"), "Codex")
    deletion.set(w("date"), date)
    return change_id + 1


def main() -> None:
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    body = document.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("The document has no body.")
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    change_id = next_change_id(document)
    children = list(body)

    # Delete the three old abstract paragraphs as whole paragraphs.  New text
    # has a Codex insertion, while each replaced paragraph already contains a
    # run-level deletion from the prior pass.
    abstract = find_one(body, "Abstract")
    acronyms = find_one(body, "Acronyms")
    first, last = children.index(abstract), children.index(acronyms)
    abstract_old = [
        p
        for p in children[first + 1 : last]
        if p.tag == w("p")
        and p.find(".//w:del", namespaces=NS) is not None
        and p.find(".//w:ins[@w:author='Codex']", namespaces=NS) is None
    ]
    if len(abstract_old) != 3:
        raise RuntimeError(f"Expected three replaced abstract paragraphs; found {len(abstract_old)}.")
    for paragraph in abstract_old:
        change_id = mark_paragraph_deleted(paragraph, change_id, date)

    # The full legacy Results sequence is deleted at paragraph level.  Its
    # prior comments, tracked insertions, and run-level deletion history stay
    # in the file but do not reappear in the replacement Results section.
    results_start = find_one(body, "Global distribution of forest areas")
    results_end = find_one(body, "Figure 5 | Natural Carbon Wealth overview")
    first, last = children.index(results_start), children.index(results_end)
    if last < first:
        raise RuntimeError("The legacy Results sequence is reversed.")
    count = 0
    for paragraph in children[first : last + 1]:
        if paragraph.tag == w("p"):
            change_id = mark_paragraph_deleted(paragraph, change_id, date)
            count += 1
    package["word/document.xml"] = etree.tostring(document, xml_declaration=True, encoding="UTF-8", standalone=True)
    temporary = ARTICLE.with_name("Article_Green_Carbon.paragraph-revisions.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Marked {len(abstract_old)} abstract and {count} legacy Results paragraphs as tracked deletions.")


if __name__ == "__main__":
    main()
