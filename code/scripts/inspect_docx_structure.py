import sys
from zipfile import ZipFile
from lxml import etree

sys.stdout.reconfigure(encoding="utf-8")
PATH = sys.argv[1] if len(sys.argv) > 1 else "Article_Green_Carbon.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

with ZipFile(PATH) as archive:
    root = etree.fromstring(archive.read("word/document.xml"))

for index, paragraph in enumerate(root.xpath(".//w:body/w:p", namespaces=NS)):
    text = "".join(paragraph.xpath(".//w:t/text()", namespaces=NS)).strip()
    if text:
        styles = paragraph.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
        style = styles[0] if styles else ""
        print(f"{index:03d} [{style}] {text[:300]}")
