"""Update the keyword line with Word tracked changes."""

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
OLD_KEYWORDS = (
    "Green natural capital, carbon sequestration, carbon sink, green capital wealth, ecosystem services"
)
NEW_KEYWORDS = (
    "Natural capital, forest carbon sequestration, ocean carbon sequestration, deforestation, "
    "ecosystem services, climate burden sharing"
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


def main() -> None:
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    paragraphs = document.xpath("/w:document/w:body/w:p", namespaces=NS)
    matches = [paragraph for paragraph in paragraphs if visible_text(paragraph).strip() == OLD_KEYWORDS]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one active keyword line; found {len(matches)}.")
    paragraph = matches[0]
    change_id = next_change_id(document)

    for child in list(paragraph):
        if child.tag != w("r"):
            continue
        deleted_run = deepcopy(child)
        for text_node in deleted_run.findall(".//w:t", namespaces=NS):
            text_node.tag = w("delText")
        deletion = etree.Element(w("del"))
        revision_attributes(deletion, change_id, date)
        deletion.append(deleted_run)
        paragraph.replace(child, deletion)
        change_id += 1

    insertion = etree.SubElement(paragraph, w("ins"))
    revision_attributes(insertion, change_id, date)
    run = etree.SubElement(insertion, w("r"))
    etree.SubElement(run, w("t")).text = NEW_KEYWORDS

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.keywords-updated.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print("Updated keywords as tracked revisions.")


if __name__ == "__main__":
    main()
