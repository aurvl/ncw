"""Restore the reviewed Discussion and withdraw its wholesale replacement draft."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def visible_text(element: etree._Element) -> str:
    return "".join(node.text or "" for node in element.xpath(".//w:t", namespaces=NS))


def restore_coded_deletion(paragraph: etree._Element, deletion: etree._Element) -> None:
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


def is_wholesale_coded_insertion(paragraph: etree._Element) -> bool:
    active_children = [
        child for child in paragraph if child.tag in {w("r"), w("ins")}
    ]
    return (
        len(active_children) == 1
        and active_children[0].tag == w("ins")
        and active_children[0].get(w("author")) == "Codex"
    )


def main() -> None:
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    body = document.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("The document has no body.")
    paragraphs = body.findall("w:p", namespaces=NS)
    heading = next(
        paragraph for paragraph in paragraphs if visible_text(paragraph).strip() == "Discussion and limitations"
    )
    references = next(
        paragraph
        for paragraph in paragraphs[paragraphs.index(heading) + 1 :]
        if visible_text(paragraph).strip() == "References"
    )
    discussion = paragraphs[paragraphs.index(heading) + 1 : paragraphs.index(references)]

    removed_drafts = 0
    for paragraph in list(discussion):
        if is_wholesale_coded_insertion(paragraph):
            body.remove(paragraph)
            removed_drafts += 1

    # Two paragraphs had already passed through a second redline operation and
    # therefore no longer retained their enclosing Codex insertion wrapper.
    # They are still part of the withdrawn wholesale discussion draft.
    residual_starts = (
        "The service is concentrated because tropical forests combine",
        "The erosion results add a temporal dimension",
    )
    for paragraph in list(body.findall("w:p", namespaces=NS)):
        if visible_text(paragraph).startswith(residual_starts):
            body.remove(paragraph)
            removed_drafts += 1

    restored_deletions = 0
    for paragraph in body.findall("w:p", namespaces=NS):
        if paragraph is heading or paragraph is references:
            continue
        current = body.findall("w:p", namespaces=NS)
        if not (current.index(heading) < current.index(paragraph) < current.index(references)):
            continue
        for deletion in list(paragraph.findall("w:del", namespaces=NS)):
            if deletion.get(w("author")) == "Codex":
                restore_coded_deletion(paragraph, deletion)
                restored_deletions += 1

    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.discussion-restored.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Restored {restored_deletions} discussion deletions and withdrew {removed_drafts} replacement paragraphs.")


if __name__ == "__main__":
    main()
