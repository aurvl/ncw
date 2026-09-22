"""Surgically repair the Introduction narrative and Methods redlines.

The script changes only Article-GCW.docx. Existing comments remain untouched.
New Methods paragraphs stay tracked as paragraph insertions, while their text
is stored as ordinary active runs so Word always displays it.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "Article-GCW.docx"
AUTHOR = "Loua Aurel De Vince Vehi"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def active_text(node: etree._Element) -> str:
    return "".join(node.xpath(".//w:t/text()", namespaces=NS)).strip()


def next_id(root: etree._Element) -> int:
    values: list[int] = []
    for value in root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            values.append(int(value))
        except ValueError:
            pass
    return max(values, default=0) + 1


def find_active(body: etree._Element, prefix: str) -> etree._Element:
    for paragraph in body.findall("w:p", namespaces=NS):
        if active_text(paragraph).startswith(prefix):
            return paragraph
    raise RuntimeError(f"Active paragraph not found: {prefix}")


def make_deletion_from_run(run: etree._Element, change_id: int, stamp: str) -> etree._Element:
    copied = deepcopy(run)
    for text in copied.xpath(".//w:t", namespaces=NS):
        text.tag = w("delText")
    deletion = etree.Element(w("del"))
    deletion.set(w("id"), str(change_id))
    deletion.set(w("author"), AUTHOR)
    deletion.set(w("date"), stamp)
    deletion.append(copied)
    return deletion


def delete_active_content(paragraph: etree._Element, change_id: int, stamp: str) -> int:
    """Delete only active direct content and preserve comments and prior deletions."""
    for child in list(paragraph):
        if child.tag == w("r"):
            if child.find("w:commentReference", namespaces=NS) is not None:
                continue
            paragraph.replace(child, make_deletion_from_run(child, change_id, stamp))
            change_id += 1
        elif child.tag == w("ins"):
            at = paragraph.index(child)
            replacements: list[etree._Element] = []
            for run in child.findall("w:r", namespaces=NS):
                if run.find("w:commentReference", namespaces=NS) is None:
                    replacements.append(make_deletion_from_run(run, change_id, stamp))
                    change_id += 1
            paragraph.remove(child)
            for offset, replacement in enumerate(replacements):
                paragraph.insert(at + offset, replacement)
    return change_id


def append_run_insertion(
    paragraph: etree._Element, content: str, change_id: int, stamp: str
) -> None:
    insertion = etree.SubElement(paragraph, w("ins"))
    insertion.set(w("id"), str(change_id))
    insertion.set(w("author"), AUTHOR)
    insertion.set(w("date"), stamp)
    run = etree.SubElement(insertion, w("r"))
    text = etree.SubElement(run, w("t"))
    text.text = content


def ensure_paragraph_marker_insertion(
    paragraph: etree._Element, change_id: int, stamp: str
) -> None:
    ppr = paragraph.find("w:pPr", namespaces=NS)
    if ppr is None:
        ppr = etree.Element(w("pPr"))
        paragraph.insert(0, ppr)
    rpr = ppr.find("w:rPr", namespaces=NS)
    if rpr is None:
        rpr = etree.SubElement(ppr, w("rPr"))
    marker = etree.SubElement(rpr, w("ins"))
    marker.set(w("id"), str(change_id))
    marker.set(w("author"), AUTHOR)
    marker.set(w("date"), stamp)


def expose_inserted_paragraph(
    paragraph: etree._Element, change_id: int, stamp: str
) -> int:
    """Use direct active runs plus a tracked paragraph-mark insertion."""
    converted = False
    for child in list(paragraph):
        if child.tag != w("ins") or child.get(w("author")) != AUTHOR:
            continue
        position = paragraph.index(child)
        runs = [deepcopy(run) for run in child.findall("w:r", namespaces=NS)]
        paragraph.remove(child)
        for offset, run in enumerate(runs):
            paragraph.insert(position + offset, run)
        converted = converted or bool(runs)
    if converted:
        ensure_paragraph_marker_insertion(paragraph, change_id, stamp)
        change_id += 1
    return change_id


def new_visible_tracked_paragraph(
    style: str, content: str, change_id: int, stamp: str
) -> etree._Element:
    paragraph = etree.Element(w("p"))
    ppr = etree.SubElement(paragraph, w("pPr"))
    pstyle = etree.SubElement(ppr, w("pStyle"))
    pstyle.set(w("val"), style)
    rpr = etree.SubElement(ppr, w("rPr"))
    marker = etree.SubElement(rpr, w("ins"))
    marker.set(w("id"), str(change_id))
    marker.set(w("author"), AUTHOR)
    marker.set(w("date"), stamp)
    run = etree.SubElement(paragraph, w("r"))
    text = etree.SubElement(run, w("t"))
    text.text = content
    return paragraph


def main() -> None:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with ZipFile(ARTICLE) as source:
        package = {item.filename: source.read(item.filename) for item in source.infolist()}
    root = etree.fromstring(package["word/document.xml"])
    body = root.find("w:body", namespaces=NS)
    if body is None:
        raise RuntimeError("Document body is missing")
    change_id = next_id(root)

    replacements = {
        "Conventional national accounts record exchange values": (
            "Conventional national accounts record exchange values generated by transactions, "
            "whereas climate regulation by forests produces no exchange at the place where the "
            "service is supplied. This helps explain why it remains largely absent from standard "
            "measures of national production and wealth. The System of Environmental-Economic "
            "Accounting Ecosystem Accounting provides a framework for recording ecosystem services "
            "alongside conventional accounts (United Nations et al., 2021). Recent applications show "
            "that non-market carbon sinks can be expressed as annual contributions to inclusive "
            "wealth, but the result depends on the physical boundary of the sink and the valuation "
            "convention (Bertram et al., 2021; Hilmi et al., 2026; Thaller et al., 2026)."
        ),
        "The Social Cost of Carbon (SCC) provides": (
            "Monetary valuation can place forest and ocean climate regulation on a common welfare "
            "basis. The social cost of carbon measures the marginal damages associated with an "
            "additional tonne of emissions and can therefore provide a shadow value for an equivalent "
            "tonne removed from the atmosphere (Ricke et al., 2018). Estimates remain sensitive to "
            "damage functions, socioeconomic scenarios and discounting. A common valuation basis is "
            "therefore necessary for comparing forest and ocean uptake, while the selected distribution "
            "and its uncertainty belong to the Methods."
        ),
        "The published Blue Carbon Wealth account values": (
            "Blue carbon studies have shown that coastal and oceanic uptake can be valued as an annual "
            "contribution to national inclusive wealth (Bertram et al., 2021; Hilmi et al., 2026). "
            "This work provides a relevant benchmark for a forest account because it defines territorial "
            "units, monetary conventions and a flow-based interpretation. Forest and ocean uptake remain "
            "physically distinct processes, and their combination requires removal of the mangrove overlap."
        ),
    }
    for prefix, replacement in replacements.items():
        target = find_active(body, prefix)
        change_id = delete_active_content(target, change_id, stamp)
        append_run_insertion(target, replacement, change_id, stamp)
        change_id += 1

    methods_heading = find_active(body, "Methods")
    first_new_method = find_active(body, "Accounting framework and estimand")
    first_result = find_active(body, "Forest carbon sinks make a large but uneven contribution")

    # Remove the obsolete active subheading that precedes the approved Methods.
    obsolete = find_active(body, "Accounting framework")
    if obsolete is not first_new_method:
        change_id = delete_active_content(obsolete, change_id, stamp)

    paragraphs = body.findall("w:p", namespaces=NS)
    method_start = paragraphs.index(methods_heading)
    method_end = paragraphs.index(first_result)
    for paragraph in paragraphs[method_start:method_end]:
        if paragraph is obsolete:
            continue
        if active_text(paragraph) == "---":
            change_id = delete_active_content(paragraph, change_id, stamp)
            continue
        change_id = expose_inserted_paragraph(paragraph, change_id, stamp)

    # Restore a visible tracked Results heading at the actual section boundary.
    if not any(
        active_text(paragraph) == "Results"
        for paragraph in body.findall("w:p", namespaces=NS)
    ):
        results_heading = new_visible_tracked_paragraph("Heading1", "Results", change_id, stamp)
        body.insert(body.index(first_result), results_heading)
        change_id += 1

    package["word/document.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = ARTICLE.with_suffix(".repairing.docx")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as target:
        for name, payload in package.items():
            target.writestr(name, payload)
    temporary.replace(ARTICLE)
    print(f"Repaired Introduction and Methods visibility through change id {change_id}.")


if __name__ == "__main__":
    main()
