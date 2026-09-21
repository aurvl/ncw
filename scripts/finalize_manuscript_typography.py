"""Apply the remaining statistical typography correction in tracked text."""

from __future__ import annotations

from pathlib import Path
import os
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def main() -> None:
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document = etree.fromstring(package["word/document.xml"])
    matches = document.xpath(".//w:ins[@w:author='Codex']//w:t[contains(., 'p = 2 x 10^-10')]", namespaces=NS)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one statistical-text match; found {len(matches)}.")
    matches[0].text = (matches[0].text or "").replace("p = 2 x 10^-10", "p = 2 × 10−10")
    package["word/document.xml"] = etree.tostring(document, xml_declaration=True, encoding="UTF-8", standalone=True)
    temporary = ARTICLE.with_name("Article_Green_Carbon.typography-revised.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print("Corrected the Kruskal-Wallis p-value typography.")


if __name__ == "__main__":
    main()
