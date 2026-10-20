import sys
from zipfile import ZipFile

from lxml import etree

sys.stdout.reconfigure(encoding="utf-8")
path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
stop = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}

with ZipFile(path) as archive:
    root = etree.fromstring(archive.read("word/document.xml"))

paragraphs = root.xpath("/w:document/w:body/w:p", namespaces=NS)
for index, p in enumerate(paragraphs[start:stop], start):
    active = "".join(p.xpath(".//w:t/text()", namespaces=NS)).strip()
    deleted = "".join(p.xpath(".//w:delText/text()", namespaces=NS)).strip()
    style = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    children = []
    for child in p:
        local = etree.QName(child).localname
        author = child.get(f"{{{W}}}author")
        children.append(local + (f"({author})" if author else ""))
    print(f"{index:03d} [{style[0] if style else ''}] children={children}")
    if active:
        print("  ACTIVE:", active[:350])
    if deleted:
        print("  DELETED:", deleted[:350])
