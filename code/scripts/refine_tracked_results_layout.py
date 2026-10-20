"""Refine the tracked Results replacement in the manuscript review copy.

This is deliberately an OOXML-level edit.  It keeps the existing comment
anchors and redlines intact, marks legacy Results runs as tracked deletions,
adds the four manuscript tables at their first textual call-out, and keeps
all new material as tracked additions.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import os
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def text_of(paragraph: etree._Element) -> str:
    return "".join(node.text or "" for node in paragraph.xpath(".//w:t", namespaces=NS))


def direct_paragraphs(body: etree._Element) -> list[etree._Element]:
    return body.findall("w:p", namespaces=NS)


def one_paragraph_containing(body: etree._Element, fragment: str) -> etree._Element:
    matches = [p for p in direct_paragraphs(body) if fragment in text_of(p)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one paragraph containing {fragment!r}; found {len(matches)}.")
    return matches[0]


def next_change_id(document_root: etree._Element) -> int:
    values: list[int] = []
    for value in document_root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            values.append(int(value))
        except ValueError:
            continue
    return max(values, default=0) + 1


def revision_attributes(element: etree._Element, change_id: int, date: str) -> None:
    element.set(w("id"), str(change_id))
    element.set(w("author"), "Codex")
    element.set(w("date"), date)


def enable_track_revisions(settings_root: etree._Element) -> None:
    if settings_root.find("w:trackRevisions", namespaces=NS) is None:
        settings_root.insert(0, etree.Element(w("trackRevisions")))


def mark_legacy_results_as_deleted(
    body: etree._Element, change_id: int, date: str
) -> int:
    """Turn only ordinary legacy runs into tracked deletions.

    Existing `w:ins`, `w:del`, comment-range markers, and comment-reference
    runs are left untouched so that the previous review history remains
    auditable.  Ordinary drawing runs are therefore deleted, which replaces
    the five old figures without removing their package data or comments.
    """
    start = one_paragraph_containing(body, "Global distribution of forest areas")
    end = one_paragraph_containing(body, "Figure 5 | Natural Carbon Wealth overview")
    children = list(body)
    first, last = children.index(start), children.index(end)
    if last < first:
        raise RuntimeError("The legacy Results range is reversed.")
    for paragraph in children[first : last + 1]:
        if paragraph.tag != w("p"):
            continue
        for child in list(paragraph):
            if child.tag != w("r"):
                continue
            if child.find("w:commentReference", namespaces=NS) is not None:
                continue
            deleted_run = deepcopy(child)
            for node in deleted_run.findall(".//w:t", namespaces=NS):
                node.tag = w("delText")
            deletion = etree.Element(w("del"))
            revision_attributes(deletion, change_id, date)
            deletion.append(deleted_run)
            paragraph.replace(child, deletion)
            change_id += 1
    return change_id


def bold_caption(paragraph: etree._Element) -> None:
    """Apply bold styling to the full caption, including the figure number."""
    for run in paragraph.xpath(".//w:r", namespaces=NS):
        properties = run.find("w:rPr", namespaces=NS)
        if properties is None:
            properties = etree.Element(w("rPr"))
            run.insert(0, properties)
        if properties.find("w:b", namespaces=NS) is None:
            properties.append(etree.Element(w("b")))


def replace_suffix(body: etree._Element, starts_with: str, old: str, new: str) -> None:
    paragraph = one_paragraph_containing(body, starts_with)
    text_nodes = paragraph.xpath(".//w:t", namespaces=NS)
    current = "".join(node.text or "" for node in text_nodes)
    if not current.endswith(old):
        raise RuntimeError(f"Unexpected paragraph ending for {starts_with!r}: {current[-100:]!r}")
    text_nodes[-1].text = (text_nodes[-1].text or "")[: -len(old)] + new


def make_caption(text: str, change_id: int, date: str) -> etree._Element:
    paragraph = etree.Element(w("p"))
    paragraph_properties = etree.SubElement(paragraph, w("pPr"))
    etree.SubElement(paragraph_properties, w("jc")).set(w("val"), "center")
    insertion = etree.SubElement(paragraph, w("ins"))
    revision_attributes(insertion, change_id, date)
    run = etree.SubElement(insertion, w("r"))
    run_properties = etree.SubElement(run, w("rPr"))
    etree.SubElement(run_properties, w("b"))
    etree.SubElement(run, w("t")).text = text
    return paragraph


def set_cell_margins(cell_properties: etree._Element) -> None:
    margins = etree.SubElement(cell_properties, w("tcMar"))
    for side in ("top", "left", "bottom", "right"):
        item = etree.SubElement(margins, w(side))
        item.set(w("w"), "70")
        item.set(w("type"), "dxa")


def make_cell(text: str, width: int, header: bool) -> etree._Element:
    cell = etree.Element(w("tc"))
    properties = etree.SubElement(cell, w("tcPr"))
    width_element = etree.SubElement(properties, w("tcW"))
    width_element.set(w("w"), str(width))
    width_element.set(w("type"), "dxa")
    set_cell_margins(properties)
    if header:
        shade = etree.SubElement(properties, w("shd"))
        shade.set(w("val"), "clear")
        shade.set(w("fill"), "404040")
    paragraph = etree.SubElement(cell, w("p"))
    paragraph_properties = etree.SubElement(paragraph, w("pPr"))
    etree.SubElement(paragraph_properties, w("jc")).set(w("val"), "center" if header else "left")
    run = etree.SubElement(paragraph, w("r"))
    run_properties = etree.SubElement(run, w("rPr"))
    if header:
        etree.SubElement(run_properties, w("b"))
        colour = etree.SubElement(run_properties, w("color"))
        colour.set(w("val"), "FFFFFF")
    etree.SubElement(run, w("t")).text = text
    return cell


def make_tracked_table(
    headers: list[str], rows: list[list[str]], widths: list[int], change_id: int, date: str
) -> tuple[etree._Element, int]:
    table = etree.Element(w("tbl"))
    table_properties = etree.SubElement(table, w("tblPr"))
    style = etree.SubElement(table_properties, w("tblStyle"))
    style.set(w("val"), "TableGrid")
    table_width = etree.SubElement(table_properties, w("tblW"))
    table_width.set(w("w"), str(sum(widths)))
    table_width.set(w("type"), "dxa")
    layout = etree.SubElement(table_properties, w("tblLayout"))
    layout.set(w("type"), "fixed")
    grid = etree.SubElement(table, w("tblGrid"))
    for width in widths:
        etree.SubElement(grid, w("gridCol")).set(w("w"), str(width))
    for row_index, values in enumerate([headers, *rows]):
        row = etree.SubElement(table, w("tr"))
        row_properties = etree.SubElement(row, w("trPr"))
        insertion = etree.SubElement(row_properties, w("ins"))
        revision_attributes(insertion, change_id, date)
        change_id += 1
        for value, width in zip(values, widths, strict=True):
            row.append(make_cell(value, width, header=row_index == 0))
    return table, change_id


def insert_table_after(
    body: etree._Element,
    reference_fragment: str,
    caption_text: str,
    headers: list[str],
    rows: list[list[str]],
    widths: list[int],
    change_id: int,
    date: str,
) -> int:
    reference = one_paragraph_containing(body, reference_fragment)
    position = body.index(reference) + 1
    caption = make_caption(caption_text, change_id, date)
    change_id += 1
    table, change_id = make_tracked_table(headers, rows, widths, change_id, date)
    body.insert(position, caption)
    body.insert(position + 1, table)
    return change_id


def main() -> None:
    if not ARTICLE.exists():
        raise FileNotFoundError(ARTICLE)
    date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with zipfile.ZipFile(ARTICLE, "r") as source:
        package = {info.filename: source.read(info.filename) for info in source.infolist()}
    document_tree = etree.fromstring(package["word/document.xml"])
    body = document_tree.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("The document has no body.")
    settings_tree = etree.fromstring(package["word/settings.xml"])
    enable_track_revisions(settings_tree)
    change_id = next_change_id(document_tree)

    # These call-outs turn the figures and tables into interpreted evidence,
    # rather than standalone graphics.
    replace_suffix(
        body,
        "Forests generated Green Carbon Wealth",
        "Natural Carbon Wealth therefore reached US$10.49 trillion per year, of which forests accounted for 77.8%.",
        "Natural Carbon Wealth therefore reached US$10.49 trillion per year, of which forests accounted for 77.8% (Table 1).",
    )
    replace_suffix(
        body,
        "GCW equalled 8.9% of global GDP.",
        "The distribution differed across country groups (Kruskal-Wallis H = 48.1, p = 2 x 10^-10).",
        "The distribution differed across country groups (Kruskal-Wallis H = 48.1, p = 2 x 10^-10). Figure 1 shows the separation between ecological endowment and economic size, and Table 2 summarises country-group profiles.",
    )
    replace_suffix(
        body,
        "Blue carbon changed the composition",
        "with 15 green-dominant units and one blue-dominant unit.",
        "with 15 green-dominant units and one blue-dominant unit. Figure 2 shows this contrast, which Table 2 quantifies across country groups.",
    )
    replace_suffix(
        body,
        "Reported deforestation averaged 9.70 million ha",
        "Among reporting units, this loss equalled 0.40% of GCW each year.",
        "Among reporting units, this loss equalled 0.40% of GCW each year (Table 3).",
    )
    replace_suffix(
        body,
        "Service magnitude and erosion intensity were not correlated",
        "The FRA rate declined from 15.8 million ha per year in the 1990s to 8.5 million ha per year in the latest period.",
        "The FRA rate declined from 15.8 million ha per year in the 1990s to 8.5 million ha per year in the latest period. Figure 3 shows that a large service does not imply a high erosion intensity.",
    )
    replace_suffix(
        body,
        "The welfare value of lost capacity and the cost of replacement",
        "These amounts equalled 0.09, 0.27, and 0.71 of the annual welfare value lost.",
        "These amounts equalled 0.09, 0.27, and 0.71 of the annual welfare value lost (Table 4).",
    )
    replace_suffix(
        body,
        "Under domestic compensation at US$150 per tCO2",
        "1.21% in Somalia, and 0.95% in Mozambique.",
        "1.21% in Somalia, and 0.95% in Mozambique. Figure 4 shows why a domestic allocation concentrates the burden in countries with low GDP.",
    )

    for number in range(1, 5):
        bold_caption(one_paragraph_containing(body, f"Figure {number}."))

    change_id = insert_table_after(
        body,
        "Forests generated Green Carbon Wealth",
        "Table 1. Global annual Green, Blue, and Natural Carbon Wealth in 2015 US dollars.",
        ["Component", "Mean (trillion 2015 US$/year)", "5th-95th percentile", "Share of NCW (%)"],
        [
            ["Green carbon wealth", "8.16", "3.15-15.49", "77.8"],
            ["Blue carbon wealth", "2.33", "0.91-4.30", "22.2"],
            ["Natural carbon wealth", "10.49", "4.07-19.66", "100.0"],
        ],
        [2700, 2500, 2200, 1600],
        change_id,
        date,
    )
    change_id = insert_table_after(
        body,
        "GCW equalled 8.9% of global GDP.",
        "Table 2. Country-group profiles of Green Carbon Wealth and sink composition.",
        ["Group", "GCW (trillion 2015 US$/year)", "World share (%)", "Median GCW/GDP (%)", "Green dominant", "Blue dominant"],
        [
            ["Developed economies", "2.26", "27.7", "2.7", "21", "11"],
            ["Developing economies", "4.19", "51.4", "10.5", "30", "16"],
            ["LDCs", "1.47", "18.1", "75.1", "15", "1"],
            ["SIDS", "0.23", "2.8", "6.2", "10", "33"],
        ],
        [2000, 2000, 1200, 1600, 1200, 1200],
        change_id,
        date,
    )
    change_id = insert_table_after(
        body,
        "Reported deforestation averaged 9.70 million ha",
        "Table 3. Annual loss of forest sink service, 2010-2019, among FRA-reporting units.",
        ["Group", "Reporting units", "Deforestation (Mha/year)", "Lost capacity (MtCO₂/year)", "Lost GCW (billion 2015 US$/year)"],
        [
            ["Developed economies", "45", "0.69", "2.68", "1.50"],
            ["Developing economies", "51", "5.63", "26.84", "15.03"],
            ["LDCs", "24", "3.29", "15.94", "8.93"],
            ["SIDS", "17", "0.09", "0.44", "0.24"],
        ],
        [2200, 1400, 2000, 2100, 2300],
        change_id,
        date,
    )
    change_id = insert_table_after(
        body,
        "The welfare value of lost capacity and the cost of replacement",
        "Table 4. Illustrative annual compensation costs under alternative abatement prices.",
        ["Illustrative price (2015 US$/tCO₂)", "Annual compensation (billion 2015 US$)", "Compensation/welfare-loss ratio"],
        [["50", "2.29", "0.09"], ["150", "6.88", "0.27"], ["400", "18.36", "0.71"]],
        [3100, 3300, 2600],
        change_id,
        date,
    )

    # This pass happens after all new insertions are located, so it only
    # suppresses the legacy Results sequence.
    mark_legacy_results_as_deleted(body, change_id, date)

    package["word/document.xml"] = etree.tostring(
        document_tree, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    package["word/settings.xml"] = etree.tostring(
        settings_tree, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_name("Article_Green_Carbon.revised.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, ARTICLE)
    print(f"Refined tracked Results layout in {ARTICLE}")


if __name__ == "__main__":
    main()
