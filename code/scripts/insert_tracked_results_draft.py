"""Insert the R1-R4 manuscript draft as true tracked additions in the Word file.

The script intentionally does not delete the legacy results. It preserves all
existing comments and redlines for review, then inserts the proposed Results
section and its four figures before the legacy results.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
FIGURES = ROOT / "repo" / "results" / "figures" / "manuscript"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
NS = {"w": W_NS, "r": R_NS, "wp": WP_NS, "a": A_NS, "pic": PIC_NS, "pr": PR_NS, "ct": CT_NS}
EMU_PER_INCH = 914400
TARGET_WIDTH_EMU = int(6.25 * EMU_PER_INCH)


def w(name: str) -> str:
    """Return a WordprocessingML qualified name."""
    return f"{{{W_NS}}}{name}"


def next_numeric_id(root: etree._Element) -> int:
    """Find an unused Word revision identifier."""
    ids = []
    for element in root.xpath(".//*[@w:id]", namespaces=NS):
        try:
            ids.append(int(element.get(w("id"))))
        except (TypeError, ValueError):
            continue
    return max(ids, default=0) + 1


def paragraph_text(paragraph: etree._Element) -> str:
    """Return visible plain text from a paragraph."""
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def find_paragraph(body: etree._Element, text: str) -> etree._Element:
    """Find one direct body paragraph by its plain text."""
    matches = [paragraph for paragraph in body.findall("w:p", namespaces=NS) if paragraph_text(paragraph).strip() == text]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph with text {text!r}; found {len(matches)}.")
    return matches[0]


def find_paragraph_containing(body: etree._Element, text: str) -> etree._Element:
    """Find one direct body paragraph that contains a stable text fragment."""
    matches = [paragraph for paragraph in body.findall("w:p", namespaces=NS) if text in paragraph_text(paragraph)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph containing {text!r}; found {len(matches)}.")
    return matches[0]


def paragraph_properties(paragraph: etree._Element) -> etree._Element | None:
    """Copy paragraph properties to preserve the manuscript style hierarchy."""
    properties = paragraph.find("w:pPr", namespaces=NS)
    return deepcopy(properties) if properties is not None else None


def make_tracked_paragraph(
    text: str,
    properties: etree._Element | None,
    change_id: int,
    author: str,
    date: str,
) -> etree._Element:
    """Create a paragraph whose text is a real Word tracked insertion."""
    paragraph = etree.Element(w("p"))
    if properties is not None:
        paragraph.append(deepcopy(properties))
    insertion = etree.SubElement(paragraph, w("ins"))
    insertion.set(w("id"), str(change_id))
    insertion.set(w("author"), author)
    insertion.set(w("date"), date)
    run = etree.SubElement(insertion, w("r"))
    text_node = etree.SubElement(run, w("t"))
    if text[:1].isspace() or text[-1:].isspace() or "  " in text:
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    return paragraph


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read PNG dimensions without an imaging dependency."""
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def create_image_relationships(rels_root: etree._Element, images: list[Path]) -> list[str]:
    """Add image relationships and return their relationship identifiers."""
    existing_ids = {relationship.get("Id") for relationship in rels_root.findall("pr:Relationship", namespaces=NS)}
    sequence = 1
    relationship_ids = []
    for image in images:
        while f"rId{sequence}" in existing_ids:
            sequence += 1
        relationship_id = f"rId{sequence}"
        relationship = etree.SubElement(rels_root, f"{{{PR_NS}}}Relationship")
        relationship.set("Id", relationship_id)
        relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
        relationship.set("Target", f"media/{image.name}")
        relationship_ids.append(relationship_id)
        existing_ids.add(relationship_id)
        sequence += 1
    return relationship_ids


def make_tracked_figure_paragraph(
    template_drawing: etree._Element,
    image_path: Path,
    relationship_id: str,
    change_id: int,
    drawing_id: int,
    author: str,
    date: str,
) -> etree._Element:
    """Create a tracked insertion that embeds one manuscript figure."""
    drawing = deepcopy(template_drawing)
    width_px, height_px = png_dimensions(image_path)
    height_emu = round(TARGET_WIDTH_EMU * height_px / width_px)
    for extent in drawing.xpath(".//wp:extent", namespaces=NS):
        extent.set("cx", str(TARGET_WIDTH_EMU))
        extent.set("cy", str(height_emu))
    for extent in drawing.xpath(".//a:xfrm/a:ext", namespaces=NS):
        extent.set("cx", str(TARGET_WIDTH_EMU))
        extent.set("cy", str(height_emu))
    for doc_pr in drawing.xpath(".//wp:docPr", namespaces=NS):
        doc_pr.set("id", str(drawing_id))
        doc_pr.set("name", image_path.stem)
    for blip in drawing.xpath(".//a:blip", namespaces=NS):
        blip.set(f"{{{R_NS}}}embed", relationship_id)
    paragraph = etree.Element(w("p"))
    insertion = etree.SubElement(paragraph, w("ins"))
    insertion.set(w("id"), str(change_id))
    insertion.set(w("author"), author)
    insertion.set(w("date"), date)
    run = etree.SubElement(insertion, w("r"))
    run.append(drawing)
    return paragraph


def enable_track_revisions(settings_root: etree._Element) -> None:
    """Ensure Word continues to track subsequent manual edits."""
    if settings_root.find("w:trackRevisions", namespaces=NS) is None:
        settings_root.insert(0, etree.Element(w("trackRevisions")))


def ensure_png_content_type(content_types_root: etree._Element) -> None:
    """Ensure that the package declares PNG images."""
    defaults = content_types_root.findall("ct:Default", namespaces=NS)
    if not any(item.get("Extension") == "png" for item in defaults):
        item = etree.SubElement(content_types_root, f"{{{CT_NS}}}Default")
        item.set("Extension", "png")
        item.set("ContentType", "image/png")


def build_content(
    heading_1: etree._Element | None,
    heading_2: etree._Element | None,
    body_style: etree._Element | None,
    template_drawing: etree._Element,
    relationship_ids: list[str],
    images: list[Path],
    change_id: int,
    drawing_id: int,
    author: str,
    date: str,
) -> tuple[list[etree._Element], int]:
    """Create the four-part Results draft and the four corresponding figures."""
    blocks: list[tuple[str, etree._Element | None]] = [
        ("Results", heading_1),
        ("Forest carbon sinks make a large but uneven contribution to national carbon wealth", heading_2),
        (
            "Forests generated Green Carbon Wealth of US$8.16 trillion per year in 2015 prices "
            "(5th-95th percentile: US$3.15-15.49 trillion). Blue Carbon Wealth added US$2.33 trillion per year. "
            "Natural Carbon Wealth therefore reached US$10.49 trillion per year, of which forests accounted for 77.8%.",
            body_style,
        ),
        (
            "Tropical forests accounted for 78.6% of global uptake. Temperate and boreal forests accounted for 13.4% "
            "and 8.0%, respectively. Developing economies supplied 51.4% of global GCW, developed economies 27.7%, "
            "least developed countries 18.1%, and small island developing states 2.8%.",
            body_style,
        ),
        (
            "GCW equalled 8.9% of global GDP. Median GCW equalled 2.7% of GDP in developed economies and 75.1% in least developed countries. "
            "GCW and GDP were only moderately correlated (Spearman rho = 0.55). The Gini coefficient was 0.856 and the ten largest contributors supplied 57.4% of global GCW. "
            "The distribution differed across country groups (Kruskal-Wallis H = 48.1, p = 2 x 10^-10).",
            body_style,
        ),
        ("Blue carbon changes national sink profiles and net balances", heading_2),
        (
            "Blue carbon changed the composition of national carbon wealth. Small island developing states were predominantly blue: "
            "33 units had a blue-dominant profile and 10 had a green-dominant profile. Least developed countries showed the reverse pattern, "
            "with 15 green-dominant units and one blue-dominant unit.",
            body_style,
        ),
        (
            "The share of accounting units with a net sink increased from 37% with forests alone to 52% after the ocean component was added. "
            "The ten largest emitters accounted for 74% of global CO2 emissions, whereas the ten largest sinks accounted for 39% of the accounted sequestration. "
            "Only the Russian Federation and Indonesia appeared in both sets.",
            body_style,
        ),
        (
            "At the current debt-stress threshold, 24 of 34 least developed countries were net sinks with low debt stress and six were net sinks with high debt stress. "
            "No developed economy was a net sink with low debt stress. The detailed debt-carbon quadrants are reported in the Supplementary Material.",
            body_style,
        ),
        ("Deforestation erodes a persistent forest sink service", heading_2),
        (
            "Reported deforestation averaged 9.70 million ha per year over 2010-2019. It removed 45.9 MtCO2 per year of sequestration capacity, "
            "which corresponded to US$25.7 billion per year of Green Carbon Wealth. Among reporting units, this loss equalled 0.40% of GCW each year.",
            body_style,
        ),
        (
            "A constant loss at this rate would remove 4.0% of the current service within ten years. At a 2% discount rate, the capitalized value of one permanent annual loss was US$1.28 trillion. "
            "Developing economies accounted for 58.5% of the reported value loss and least developed countries for 34.7%.",
            body_style,
        ),
        (
            "Service magnitude and erosion intensity were not correlated (Spearman rho = -0.09, p > 0.05). The estimates cover 139 of 236 accounting units and 79% of global GCW. "
            "Missing FRA reports do not indicate zero deforestation. The FRA rate declined from 15.8 million ha per year in the 1990s to 8.5 million ha per year in the latest period.",
            body_style,
        ),
        ("Compensation costs and burdens diverge across countries", heading_2),
        (
            "The welfare value of lost capacity and the cost of replacement measure different quantities. At illustrative prices of US$50, US$150, and US$400 per tCO2, "
            "annual compensation costs were US$2.29, US$6.88, and US$18.36 billion. These amounts equalled 0.09, 0.27, and 0.71 of the annual welfare value lost.",
            body_style,
        ),
        (
            "Under domestic compensation at US$150 per tCO2, least developed countries paid US$2.39 billion per year. "
            "Under a shared effort proportional to GDP, their contribution fell to US$0.11 billion per year. The domestic burden reached 1.44% of GDP in the Central African Republic, "
            "1.21% in Somalia, and 0.95% in Mozambique.",
            body_style,
        ),
        (
            "A 5% decline in Blue Carbon Wealth corresponded to 208 MtCO2 per year and US$116 billion per year of welfare value. "
            "A 10% decline corresponded to 416 MtCO2 per year and US$233 billion per year. These ocean estimates are scenarios, not observed losses. "
            "The compensation prices remain illustrative until the final AR6 scenario, price year, and conversion to 2015 US dollars are selected.",
            body_style,
        ),
    ]
    output: list[etree._Element] = []
    figure_after = {4: 0, 8: 1, 12: 2, 16: 3}
    captions = [
        "Figure 1. Forest carbon wealth, economic size, and concentration.",
        "Figure 2. Blue carbon composition and national carbon balances.",
        "Figure 3. Service magnitude and erosion intensity.",
        "Figure 4. Who loses the sink and who pays for compensation.",
    ]
    for index, (text, properties) in enumerate(blocks):
        output.append(make_tracked_paragraph(text, properties, change_id, author, date))
        change_id += 1
        if index in figure_after:
            figure_index = figure_after[index]
            output.append(
                make_tracked_figure_paragraph(
                    template_drawing,
                    images[figure_index],
                    relationship_ids[figure_index],
                    change_id,
                    drawing_id,
                    author,
                    date,
                )
            )
            change_id += 1
            drawing_id += 1
            output.append(make_tracked_paragraph(captions[figure_index], body_style, change_id, author, date))
            change_id += 1
    return output, change_id


def main() -> None:
    """Patch the review copy while retaining all pre-existing XML parts."""
    images = [
        FIGURES / "Figure1_forest_service_and_concentration.png",
        FIGURES / "Figure2_blue_carbon_and_net_balance.png",
        FIGURES / "Figure3_erosion_of_forest_service.png",
        FIGURES / "Figure4_compensation_burden.png",
    ]
    if not ARTICLE.exists() or any(not image.exists() for image in images):
        raise FileNotFoundError("The manuscript or one of the four manuscript figures is missing.")
    author = "Codex"
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    workdir = ROOT / ".tmp" / "bnc2_results_work"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    unpacked = workdir / "unpacked"
    try:
        with zipfile.ZipFile(ARTICLE) as archive:
            archive.extractall(unpacked)
        document_path = unpacked / "word" / "document.xml"
        document_tree = etree.parse(str(document_path))
        document_root = document_tree.getroot()
        body = document_root.find("w:body", namespaces=NS)
        if body is None:
            raise RuntimeError("The manuscript has no document body.")
        insertion_point = find_paragraph(body, "Global distribution of forest areas")
        heading_1 = paragraph_properties(find_paragraph(body, "Introduction"))
        heading_2 = paragraph_properties(insertion_point)
        body_style = paragraph_properties(find_paragraph_containing(body, "Across economic groups, developed economies hold the largest extent of forest area"))
        template_drawing = document_root.find(".//w:drawing", namespaces=NS)
        if template_drawing is None:
            raise RuntimeError("The manuscript has no existing inline drawing to use as an image template.")
        relationship_path = unpacked / "word" / "_rels" / "document.xml.rels"
        relationship_tree = etree.parse(str(relationship_path))
        relationship_ids = create_image_relationships(relationship_tree.getroot(), images)
        relationship_tree.write(str(relationship_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        for image in images:
            shutil.copyfile(image, unpacked / "word" / "media" / image.name)
        content_types_path = unpacked / "[Content_Types].xml"
        content_types_tree = etree.parse(str(content_types_path))
        ensure_png_content_type(content_types_tree.getroot())
        content_types_tree.write(str(content_types_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        settings_path = unpacked / "word" / "settings.xml"
        settings_tree = etree.parse(str(settings_path))
        enable_track_revisions(settings_tree.getroot())
        settings_tree.write(str(settings_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        drawing_ids = [int(value) for value in document_root.xpath(".//wp:docPr/@id", namespaces=NS) if value.isdigit()]
        new_content, _ = build_content(
            heading_1,
            heading_2,
            body_style,
            template_drawing,
            relationship_ids,
            images,
            next_numeric_id(document_root),
            max(drawing_ids, default=0) + 1,
            author,
            date,
        )
        position = body.index(insertion_point)
        for offset, paragraph in enumerate(new_content):
            body.insert(position + offset, paragraph)
        document_tree.write(str(document_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        temporary_docx = workdir / ARTICLE.name
        with zipfile.ZipFile(temporary_docx, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file in unpacked.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(unpacked).as_posix())
        shutil.copyfile(temporary_docx, ARTICLE)
        print(f"Inserted {len(new_content)} tracked paragraphs into {ARTICLE}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
