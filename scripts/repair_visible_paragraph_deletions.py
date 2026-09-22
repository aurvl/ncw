"""Convert Codex paragraph-deletion markers into visible Word run deletions.

Earlier edits used a paragraph-property deletion, which Word rendered only as a
revision bar.  This repair leaves reviewer comments and user-authored revision
metadata intact while replacing those Codex-only markers with normal ``w:del``
runs that Word displays as struck-through deleted text.
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


def next_change_id(document: etree._Element) -> int:
    values = []
    for value in document.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            values.append(int(value))
        except ValueError:
            continue
    return max(values, default=0) + 1


def make_deletion(run: etree._Element, change_id: int, date: str) -> etree._Element:
    deleted_run = deepcopy(run)
    for text in deleted_run.findall(".//w:t", namespaces=NS):
        text.tag = w("delText")
    deletion = etree.Element(w("del"))
    deletion.set(w("id"), str(change_id))
    deletion.set(w("author"), "Codex")
    deletion.set(w("date"), date)
    deletion.append(deleted_run)
    return deletion


def main() -> None:
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    change_id = next_change_id(document)
    repaired_paragraphs = 0
    repaired_runs = 0

    for paragraph in document.xpath("/w:document/w:body/w:p", namespaces=NS):
        paragraph_deletions = paragraph.xpath("./w:pPr/w:rPr/w:del[@w:author='Codex']", namespaces=NS)
        if not paragraph_deletions:
            continue

        for child in list(paragraph):
            if child.tag != w("r"):
                continue
            if child.find("w:commentReference", namespaces=NS) is not None:
                continue
            paragraph.replace(child, make_deletion(child, change_id, date))
            change_id += 1
            repaired_runs += 1

        for marker in paragraph_deletions:
            marker.getparent().remove(marker)
        repaired_paragraphs += 1

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.visible-deletions.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Repaired {repaired_paragraphs} paragraph deletions as {repaired_runs} visible run deletions.")


if __name__ == "__main__":
    main()
