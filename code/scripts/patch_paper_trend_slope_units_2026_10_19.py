"""Clarify the Theil-Sen trend-slope units in the tracked Results paragraph."""

from __future__ import annotations

from pathlib import Path
import shutil
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT.parent / "NEXT" / "PAPER.docx"
BACKUP = ROOT / "results" / "validation" / "PAPER_before_trend_slope_unit_fix_2026-10-19.docx"
TEMP = PAPER.with_name(PAPER.stem + ".trend-slope-unit-refresh.tmp.docx")
OLD = "The Theil-Sen slope was −271.77 kha per year of trend (approximate non-parametric interval −460.07 to −80.06);"
NEW = "The Theil-Sen slope was −0.272 Mha yr⁻² (approximate 95% non-parametric interval −0.460 to −0.080 Mha yr⁻²);"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def main() -> None:
    if BACKUP.exists():
        raise FileExistsError(f"Refusing to overwrite backup: {BACKUP}")
    shutil.copy2(PAPER, BACKUP)

    with zipfile.ZipFile(PAPER, "r") as source:
        package = {name: source.read(name) for name in source.namelist()}
    document_xml = package["word/document.xml"]
    old_bytes, new_bytes = OLD.encode("utf-8"), NEW.encode("utf-8")
    if document_xml.count(old_bytes) != 1:
        raise RuntimeError("Expected to find the old slope wording exactly once in PAPER.docx")
    package["word/document.xml"] = document_xml.replace(old_bytes, new_bytes, 1)

    with zipfile.ZipFile(TEMP, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, content in package.items():
            target.writestr(name, content)

    with zipfile.ZipFile(TEMP, "r") as checked:
        corrupt_member = checked.testzip()
        if corrupt_member:
            raise RuntimeError(f"Corrupt DOCX member: {corrupt_member}")
        root = ET.fromstring(checked.read("word/document.xml"))
        text = "\n".join("".join(node.text or "" for node in p.iter(W + "t")) for p in root.iter(W + "p"))
        if NEW not in text or OLD in text:
            raise RuntimeError("Slope wording verification failed")

        comments = ET.fromstring(checked.read("word/comments.xml"))
        comment_ids = {node.get(W + "id") for node in comments.iter(W + "comment")}
        start_ids = {node.get(W + "id") for node in root.iter(W + "commentRangeStart")}
        end_ids = {node.get(W + "id") for node in root.iter(W + "commentRangeEnd")}
        if not comment_ids <= start_ids or not comment_ids <= end_ids:
            raise RuntimeError("A Word comment lost its start or end range")

        with zipfile.ZipFile(BACKUP, "r") as original:
            old_media = {name: original.read(name) for name in original.namelist() if name.startswith("word/media/")}
        new_media = {name: checked.read(name) for name in checked.namelist() if name.startswith("word/media/")}
        if old_media != new_media:
            raise RuntimeError("Embedded manuscript images changed")

    TEMP.replace(PAPER)
    print(f"Updated {PAPER}")
    print(f"Backup {BACKUP}")
    print(f"Preserved {len(comment_ids)} comment ranges and {len(new_media)} embedded images")


if __name__ == "__main__":
    main()
