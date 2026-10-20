import sys
from zipfile import ZipFile
from lxml import etree

PATH = sys.argv[1] if len(sys.argv) > 1 else "Article_Green_Carbon.revised_2026-09-21.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

with ZipFile(PATH) as archive:
    document = etree.fromstring(archive.read("word/document.xml"))
    settings = etree.fromstring(archive.read("word/settings.xml"))
    comments = etree.fromstring(archive.read("word/comments.xml"))

active = "".join(document.xpath(".//w:t/text()", namespaces=NS))
print("track_settings", bool(settings.xpath(".//w:trackRevisions", namespaces=NS)))
print("active_words", len(active.split()))
print("comments", len(comments.xpath(".//w:comment", namespaces=NS)))
print("insertions", len(document.xpath(".//w:ins", namespaces=NS)))
print("deletions", len(document.xpath(".//w:del", namespaces=NS)))
print("codex_authors", len(document.xpath(".//*[@w:author='Codex']", namespaces=NS)))
print("aurel_authors", len(document.xpath(".//*[@w:author='Loua Aurel De Vince Vehi']", namespaces=NS)))
print("paragraph_insertions", len(document.xpath(".//w:pPr/w:rPr/w:ins", namespaces=NS)))
print("banned_active", [(value, value in active) for value in ("573.8", "8.1 trillion", "3.86", "417", "177 to 805", "in press", "xxx")])
for value in ("573.8", "8.1 trillion", "3.86"):
    for node in document.xpath(f".//w:t[contains(., '{value}')]", namespaces=NS):
        lineage = [etree.QName(item).localname for item in node.iterancestors()]
        print("residual", value, lineage[:5], node.text)
for p in document.xpath(".//w:p", namespaces=NS):
    styles = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    if styles and styles[0] == "Heading1":
        print("heading", "".join(p.xpath(".//w:t/text()", namespaces=NS)))
