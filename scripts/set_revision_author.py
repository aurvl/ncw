"""Assign only Codex-authored tracked changes to the manuscript author."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
FILES = (
    ROOT / "Article-GCW.docx",
    ROOT / "Article_Green_Carbon.revised_2026-09-21.docx",
    ROOT / "Article_Green_Carbon.prompt-revision.docx",
)
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
AUTHOR = "Loua Aurel De Vince Vehi"

for path in FILES:
    if not path.exists():
        continue
    with ZipFile(path) as source:
        package = {item.filename: source.read(item.filename) for item in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    changed = 0
    for node in document.xpath(".//*[@w:author='Codex']", namespaces={"w": W}):
        node.set(f"{{{W}}}author", AUTHOR)
        changed += 1
    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = path.with_suffix(".author-update.docx")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as target:
        for name, payload in package.items():
            target.writestr(name, payload)
    temporary.replace(path)
    print(f"{path.name}: reassigned {changed} tracked changes to {AUTHOR}.")
