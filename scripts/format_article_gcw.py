"""Audit and apply form-only consistency fixes to Article-GCW.docx.

The script works directly on OOXML so existing comments and tracked revisions are
preserved. Text replacements are represented as new tracked deletions/insertions
under the manuscript author's name. Formatting and reference ordering do not
alter the wording of references or captions.
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}
W = f"{{{W_NS}}}"
AUTHOR = "Loua Aurel De Vince Vehi"

sys.stdout.reconfigure(encoding="utf-8")


REPLACEMENTS: list[tuple[int, str, str]] = [
    (25, "The Intergovernmental Panel on Climate Change Special Report", "The Intergovernmental Panel on Climate Change (IPCC) Special Report"),
    (25, "if it continued at the then-current rate.", "if it continued at the then-current rate (IPCC, 2022)."),
    (27, "UNEP and IUCN, 2021", "United Nations Environment Programme and International Union for Conservation of Nature, 2021"),
    (30, "200 Mha (millions hectares)", "200 million hectares (Mha)"),
    (30, "(FAO, 2025)", "(Food and Agriculture Organization of the United Nations, 2025)"),
    (40, "a common distribution of the Global Social Cost of Carbon (GSCC)", "a common GSCC distribution"),
    (48, "Green Carbon Wealth", "GCW"),
    (48, "Blue Carbon Wealth", "BCW"),
    (48, "Natural Carbon Wealth", "NCW"),
    (51, "Global annual Green, Blue, and Natural Carbon Wealth", "Global annual GCW, BCW and NCW"),
    (55, "developing and least developed countries contained", "developing and least developed countries (LDCs) contained"),
    (55, "US$4.19 trillion of Green Carbon Wealth", "US$4.19 trillion of GCW"),
    (55, "least developed countries US$1.47", "LDCs US$1.47"),
    (55, "small island developing states US$0.23", "small island developing states (SIDS) US$0.23"),
    (55, "Green Carbon Wealth equalled", "GCW equalled"),
    (55, "world gross domestic product", "world gross domestic product (GDP)"),
    (55, "75.1% in least developed countries", "75.1% in LDCs"),
    (55, "6.2% in small island developing states", "6.2% in SIDS"),
    (58, "relationship between Green Carbon Wealth and economic size", "relationship between GCW and economic size"),
    (58, "ecological endowment and gross domestic product", "ecological endowment and GDP"),
    (60, "Country-group profiles of Green Carbon Wealth", "Country-group profiles of GCW"),
    (66, "Adding Blue Carbon Wealth", "Adding BCW"),
    (66, "Small island developing states included", "SIDS included"),
    (66, "whereas least developed countries included", "whereas LDCs included"),
    (66, "Large exclusive economic zones", "Large exclusive economic zones (EEZs)"),
    (69, "Natural Carbon Wealth remains", "NCW remains"),
    (75, "of Green Carbon Wealth", "of GCW"),
    (79, "least developed countries for", "LDCs for"),
    (79, "small island developing states", "SIDS"),
    (79, "for which Green Carbon Wealth also represents", "for which GCW also represents"),
    (87, "The Global Social Cost of Carbon values", "The GSCC values"),
    (91, "proportional to gross domestic product", "proportional to GDP"),
    (91, "of gross domestic product in", "of GDP in"),
    (143, "SEEA-EA", "SEEA EA"),
    (143, "(United Nations, 2025)", "(United Nations et al., 2021)"),
    (145, "Berzaghi et al. 2025", "Berzaghi et al., 2025"),
    (161, "small island developing states", "SIDS"),
    (162, "global Green Carbon Wealth", "global GCW"),
    (162, "least developed countries", "LDCs"),
    (163, "least developed countries", "LDCs"),
    (166, "Standards such as Verra and ART-TREES, and the Reducing Emissions from Deforestation and Forest Degradation framework, address these issues through different institutional rules.", "The Reducing Emissions from Deforestation and Forest Degradation (REDD+) framework and standards such as Verra and the Architecture for REDD+ Transactions and its REDD+ Environmental Excellence Standard (ART-TREES) address these issues through different institutional rules."),
    (167, "System of Environmental-Economic Accounting Ecosystem Accounting", "SEEA EA"),
    (169, "Global Forest Resources Assessment 2025", "Food and Agriculture Organization of the United Nations (FAO) Global Forest Resources Assessment 2025 (FRA 2025)"),
    (171, "Intergovernmental Panel on Climate Change price scenarios", "IPCC price scenarios"),
    (220, "The social cost of carbon already discounts", "The SCC already discounts"),
    (223, "the FAO Global Forest Resources Assessment (FRA)", "the FRA"),
    (224, "Hong Kong SAR and Macao SAR", "Hong Kong Special Administrative Region (SAR) and Macao SAR"),
    (226, "Green Carbon Wealth measures", "GCW measures"),
    (227, "JRC Global Forest Cover 2020", "Joint Research Centre (JRC) Global Forest Cover 2020"),
    (238, "country-level social cost of carbon database", "country-level SCC database"),
    (258, "FAOSTAT", "Food and Agriculture Organization of the United Nations statistical database (FAOSTAT)"),
    (263, "their URL", "their uniform resource locator (URL)"),
    (263, "SHA-256 checksum", "Secure Hash Algorithm 256-bit (SHA-256) checksum"),
    (263, "a CC BY 4.0 licence", "a Creative Commons Attribution 4.0 (CC BY 4.0) licence"),
    (264, "Use of generative AI", "Use of generative artificial intelligence (AI)"),
]


REFERENCE_ORDER: list[tuple[str, str]] = [
    ("Intergovernmental Panel on Climate Change.", "(2022)"),
    ("Griscom,", "(2017)"),
    ("United Nations Environment Programme,", "(2021)"),
    ("Pan,", "(2011)"),
    ("Pan,", "(2024)"),
    ("Food and Agriculture Organization of the United Nations.", "(2025)"),
    ("United Nations, European Union,", "(2021)"),
    ("Bertram,", "(2021)"),
    ("Hilmi,", "(2026)"),
    ("Thaller,", "(2026)"),
    ("Ricke,", "(2018)"),
    ("Favero,", "(2026)"),
    ("Rickels,", "(2024)"),
    ("Berzaghi,", "(2025)"),
    ("Chausson,", "(2023)"),
    ("Green,", "(2022)"),
    ("Ontl,", "(2012)"),
    ("Lal,", "(2008)"),
    ("Keller,", "(2024)"),
    ("Trumbore,", "(1997)"),
    ("Brett,", "(2002)"),
]

POST_REPLACEMENTS: list[tuple[int, str, str]] = [
    (75, "The loss equalled 0.40% of the Green Carbon Wealth of reporting units", "The loss equalled 0.40% of the GCW of reporting units"),
    (75, "79% of global Green Carbon Wealth", "79% of global GCW"),
    (91, "least developed countries would pay", "LDCs would pay"),
]

INTRO_PARAGRAPHS: dict[int, str] = {
    25: "Climate change increases the need to represent natural systems in economic decision making. The Intergovernmental Panel on Climate Change (IPCC) Special Report on Global Warming of 1.5°C showed that continued warming creates substantial risks for ecosystems and human societies (IPCC, 2022). Natural capital accounting can make the contribution of ecosystems to human welfare more visible. Yet major climate-regulation services remain outside conventional national accounts because no market transaction occurs where these services are supplied.",
    27: "Nature-based solutions could provide up to about 10 GtCO₂ of mitigation per year, and forests account for a substantial share of this potential (Griscom et al., 2017; United Nations Environment Programme and International Union for Conservation of Nature, 2021). Forests currently remove about 3.5–4.0 gigatonnes of carbon from the atmosphere each year (Pan et al., 2011; Pan et al., 2024). This sink is spatially heterogeneous and changes through time. Uptake has declined in boreal and intact tropical forests, whereas some temperate and regrowing tropical forests have strengthened their uptake.",
    30: "Forest carbon stocks and annual forest sinks are distinct accounting objects. Forests stored about 714 gigatonnes of carbon in 2025, while more than 200 million hectares of forest have been lost since 1990 (Food and Agriculture Organization of the United Nations, 2025). Stocks describe the carbon held in biomass, dead wood, litter and soils. Annual sinks describe the net transfer of carbon dioxide from the atmosphere into these pools. The present study values this annual climate-regulation service rather than the underlying carbon stock. Its magnitude cannot be inferred from forest area alone. It also depends on forest composition, biome-specific uptake rates and the loss of future removal capacity caused by deforestation.",
    32: "Conventional national accounts record exchange values generated through transactions. Forest carbon uptake generates no such exchange where the service is supplied. The System of Environmental-Economic Accounting Ecosystem Accounting (SEEA EA) provides a framework for recording ecosystem services alongside conventional accounts (United Nations et al., 2021). Recent applications show that non-market carbon sinks can be expressed as annual contributions to inclusive wealth. However, the resulting estimates depend on the physical boundary of the sink, the treatment of uncertainty and the monetary valuation convention (Bertram et al., 2021; Hilmi et al., 2026; Thaller et al., 2026).",
    33: "Monetary valuation can place forest and ocean climate regulation on a common welfare basis. The Social Cost of Carbon (SCC) measures the marginal damages associated with an additional tonne of emissions and can therefore provide an economic value for an equivalent tonne removed from the atmosphere (Ricke et al., 2018). Estimates remain sensitive to damage functions, socioeconomic scenarios and discounting. Hilmi et al. (2026) derived a structure-adjusted Global Social Cost of Carbon (GSCC) of US$559.6 per tCO₂, with a 5th–95th percentile interval of US$218.5–1,015.9 in constant 2015 prices. A common distribution is necessary if forest and ocean uptake are to be compared within the same welfare framework.",
    35: "A forest-only account nevertheless provides an incomplete representation of nature-based atmospheric carbon dioxide removal. Coastal ecosystems and the oceanic biological carbon pump also contribute to national carbon wealth. The published Blue Carbon Wealth (BCW) account values these services as annual contributions to inclusive wealth (Bertram et al., 2021; Hilmi et al., 2026). Forest and ocean uptake remain physically distinct, but their combination raises two accounting requirements. Both components must use consistent territorial and monetary conventions, and the mangrove contribution must be counted only once. A combined account can also support a net carbon balance that compares accounted annual uptake with fossil-fuel and industrial emissions under a common boundary.",
    37: "Existing studies address separate parts of this accounting problem. Bertram et al. (2021) and Hilmi et al. (2026) establish a national account for coastal and oceanic uptake. Thaller et al. (2026) value natural land sinks across countries. Favero and Austin (2026) estimate the potential for additional forest mitigation relative to a policy baseline. Rickels et al. (2024) examine the policy consequences of a weakening ocean sink. These measures answer different questions. The value of a current sink is not the same as its potential for additional mitigation, and neither measure captures the annual erosion of removal capacity caused by deforestation.",
    40: "These strands of research therefore point to an integration problem rather than simply to a missing global estimate. A national account of nature-based carbon wealth must distinguish annual uptake from stored carbon, represent differences in forest composition and apply a common welfare valuation to terrestrial and oceanic uptake. It must also prevent double counting and measure changes in the capacity that supports the annual service. Once a loss of capacity is quantified, its illustrative replacement cost can be estimated. The distribution of that cost then depends on the selected allocation rule and need not coincide with the location of the ecological loss.",
    41: "Here we develop a harmonised country-level framework for the annual forest- and ocean-based uptake of atmospheric carbon dioxide. We define Green Carbon Wealth (GCW) as the annual welfare value of net atmospheric carbon dioxide removal provided by forests. Forest area is allocated among tropical, temperate and boreal biomes for each accounting unit. These areas are combined with biome-specific uptake rates derived from the decadal forest-sink estimates of Pan et al. (2024). The resulting annual removal flows are valued with the GSCC distribution used in the published blue carbon account. Natural Carbon Wealth (NCW) combines GCW with BCW after the mangrove component has been removed from the forest estimate.",
    42: "GCW and NCW are annual measures of the welfare value of climate-regulation services. They are not estimates of carbon stocks, market prices, national income, fiscal transfers or financing entitlements. The replacement calculations also remain analytical scenarios. They estimate the resources required to replace lost annual removal capacity under selected abatement prices and do not establish compensation rights or legal responsibility. We address three related questions. First, what is the annual value and geographic distribution of forest-based atmospheric carbon dioxide uptake, and how does the inclusion of BCW affect national carbon wealth and net carbon balances? Second, how much annual forest removal capacity is lost through reported deforestation? Third, how do illustrative replacement costs vary across abatement-price assumptions and between domestic allocation and allocation proportional to gross domestic product (GDP)?",
    43: "The contribution of this study lies in connecting three dimensions that are usually examined separately. We integrate forest and ocean carbon-removal services within a common country-level account. We quantify the persistent erosion of annual forest removal capacity. We then examine how alternative allocation rules distribute the illustrative replacement burden. The central proposition is that service provision, service erosion and capacity to finance replacement are distinct objects that must be analysed together without being conflated.",
}

INTERVAL_REPLACEMENTS: list[tuple[int, str, str]] = [
    (
        33,
        "Hilmi et al. (2026) derived a structure-adjusted Global Social Cost of Carbon (GSCC) of US$559.6 per tCO₂, with a 5th–95th percentile interval of US$218.5–1,015.9 in constant 2015 prices.",
        "Hilmi et al. (2026) derived a structure-adjusted Global Social Cost of Carbon (GSCC) of US$559.6 [218.5–1,015.9] per tCO₂ in constant 2015 prices, where brackets denote the 5th–95th percentile interval.",
    ),
    (
        48,
        "US$8.16 [3.15–15.49] (5th–95th percentile) trillion per year",
        "US$8.16 [3.15–15.49] trillion per year",
    ),
    (
        75,
        "US$25.7 billion per year of GCW, with a 5th–95th percentile interval of US$9.79–49.58 billion",
        "US$25.7 [9.79–49.58] billion per year of GCW",
    ),
    (
        235,
        "The adjusted distribution has a mean of 559.6, a median of 506.7 and a standard deviation of 268.6 constant 2015 US dollars per tonne of CO₂, with a 5th–95th percentile range of 218.5–1,015.9.",
        "The adjusted distribution has a mean of 559.6 [218.5–1,015.9] constant 2015 US dollars per tonne of CO₂. Its median is 506.7 and its standard deviation is 268.6.",
    ),
    (
        250,
        "We report means, medians, standard deviations and 5th–95th percentile intervals of the draws.",
        "We report each estimate as mean [5th–95th percentile] unit. Medians and standard deviations are also provided.",
    ),
]


def active_text(element: etree._Element) -> str:
    """Return visible text, excluding tracked deletions and move-from content."""
    pieces: list[str] = []
    for node in element.xpath(".//w:t", namespaces=NS):
        if node.xpath("ancestor::w:del or ancestor::w:moveFrom", namespaces=NS):
            continue
        pieces.append(node.text or "")
    return "".join(pieces)


def paragraph_style(paragraph: etree._Element) -> str:
    values = paragraph.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return values[0] if values else ""


def body_paragraphs(document: etree._Element) -> list[etree._Element]:
    return document.xpath(".//w:body/w:p", namespaces=NS)


def section_ranges(paragraphs: list[etree._Element]) -> dict[str, tuple[int, int]]:
    headings: list[tuple[int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        if paragraph_style(paragraph) == "Heading1":
            headings.append((index, active_text(paragraph).strip()))
    ranges: dict[str, tuple[int, int]] = {}
    for pos, (start, title) in enumerate(headings):
        end = headings[pos + 1][0] if pos + 1 < len(headings) else len(paragraphs)
        ranges[title] = (start, end)
    return ranges


def audit(document: etree._Element, show: str = "") -> None:
    paragraphs = body_paragraphs(document)
    ranges = section_ranges(paragraphs)
    print("SECTIONS")
    for title, bounds in ranges.items():
        print(f"  {bounds[0]:03d}-{bounds[1] - 1:03d} {title}")

    acronym_re = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z]{2,}(?:-[A-Z]{2,})?|[A-Z]{2,}[a-z]s)(?![A-Za-z0-9])")
    occurrences: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for index, paragraph in enumerate(paragraphs):
        text = active_text(paragraph).strip()
        for token in acronym_re.findall(text):
            occurrences[token].append((index, text))
    print("\nACRONYM OCCURRENCES")
    for token in sorted(occurrences):
        print(f"  {token}: " + ", ".join(str(index) for index, _ in occurrences[token]))
        first_index, first_text = occurrences[token][0]
        print(f"    first {first_index:03d}: {first_text[:260]}")

    full_forms = [
        "Intergovernmental Panel on Climate Change",
        "Nature-based Solutions",
        "United Nations Environment Programme",
        "International Union for Conservation of Nature",
        "Food and Agriculture Organization of the United Nations",
        "System of Environmental-Economic Accounting Ecosystem Accounting",
        "Social Cost of Carbon",
        "social cost of carbon",
        "Global Social Cost of Carbon",
        "Green Carbon Wealth",
        "Blue Carbon Wealth",
        "Natural Carbon Wealth",
        "gross domestic product",
        "least developed countries",
        "small island developing states",
        "Global Forest Resources Assessment",
        "Joint Research Centre",
        "exclusive economic zone",
        "artificial intelligence",
    ]
    print("\nFULL-FORM OCCURRENCES")
    for phrase in full_forms:
        hits = [index for index, paragraph in enumerate(paragraphs) if phrase in active_text(paragraph)]
        if hits:
            print(f"  {phrase}: " + ", ".join(map(str, hits)))

    print("\nFIGURE CAPTIONS")
    for index, paragraph in enumerate(paragraphs):
        text = active_text(paragraph).strip()
        if re.match(r"^Figure\s+\d+\.", text):
            fonts = sorted(set(paragraph.xpath(".//w:rFonts/@w:ascii | .//w:rFonts/@w:hAnsi", namespaces=NS)))
            print(f"  {index:03d} fonts={fonts or ['<inherited>']} {text[:240]}")

    ref_range = ranges.get("References")
    if not ref_range:
        raise RuntimeError("References section was not found.")
    print("\nREFERENCES")
    for index in range(ref_range[0] + 1, ref_range[1]):
        text = active_text(paragraphs[index]).strip()
        if text:
            print(f"  {index:03d} {text[:220]}")

    if show:
        selected: set[int] = set()
        for part in show.split(","):
            if "-" in part:
                start, end = (int(value) for value in part.split("-", 1))
                selected.update(range(start, end + 1))
            else:
                selected.add(int(part))
        print("\nSELECTED ACTIVE PARAGRAPHS")
        for index in sorted(selected):
            if 0 <= index < len(paragraphs):
                text = active_text(paragraphs[index]).strip()
                if text:
                    print(f"  {index:03d} {text}")


def load_package(path: Path) -> tuple[dict[str, bytes], etree._Element]:
    with zipfile.ZipFile(path, "r") as source:
        package = {item.filename: source.read(item.filename) for item in source.infolist()}
    return package, etree.fromstring(package["word/document.xml"])


def nearest_ancestor(node: etree._Element, local_name: str) -> etree._Element | None:
    parent = node.getparent()
    while parent is not None:
        if etree.QName(parent).localname == local_name:
            return parent
        parent = parent.getparent()
    return None


def text_run(text: str, template_run: etree._Element | None, deleted: bool = False) -> etree._Element:
    run = etree.Element(W + "r")
    if template_run is not None:
        rpr = template_run.find(W + "rPr")
        if rpr is not None:
            run.append(copy.deepcopy(rpr))
    node = etree.SubElement(run, W + ("delText" if deleted else "t"))
    if text.startswith(" ") or text.endswith(" ") or "  " in text:
        node.set(f"{{{XML_NS}}}space", "preserve")
    node.text = text
    return run


class RevisionIds:
    def __init__(self, document: etree._Element) -> None:
        values: list[int] = []
        for value in document.xpath(".//*[@w:id]/@w:id", namespaces=NS):
            try:
                values.append(int(value))
            except ValueError:
                pass
        self.current = max(values, default=0)

    def next(self) -> str:
        self.current += 1
        return str(self.current)


def revision_wrapper(kind: str, revision_ids: RevisionIds) -> etree._Element:
    wrapper = etree.Element(W + kind)
    wrapper.set(W + "id", revision_ids.next())
    wrapper.set(W + "author", AUTHOR)
    wrapper.set(W + "date", datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    return wrapper


def active_text_nodes(paragraph: etree._Element) -> list[etree._Element]:
    nodes: list[etree._Element] = []
    for node in paragraph.xpath(".//w:t", namespaces=NS):
        if node.xpath("ancestor::w:del or ancestor::w:moveFrom", namespaces=NS):
            continue
        nodes.append(node)
    return nodes


def replace_active_substring(
    paragraph: etree._Element,
    old: str,
    new: str,
    revision_ids: RevisionIds,
) -> str:
    nodes = active_text_nodes(paragraph)
    joined = "".join(node.text or "" for node in nodes)
    if joined.count(old) != 1:
        raise RuntimeError(f"Expected exactly one active match for {old!r}; found {joined.count(old)} in {joined!r}")
    start = joined.index(old)
    end = start + len(old)
    offsets: list[tuple[etree._Element, int, int]] = []
    cursor = 0
    for node in nodes:
        next_cursor = cursor + len(node.text or "")
        offsets.append((node, cursor, next_cursor))
        cursor = next_cursor
    touched = [(node, left, right) for node, left, right in offsets if right > start and left < end]
    if not touched:
        raise RuntimeError(f"Could not map active match for {old!r}")

    insertion_ancestors = [nearest_ancestor(node, "ins") for node, _, _ in touched]
    if all(
        ancestor is not None and ancestor.get(W + "author") == AUTHOR
        for ancestor in insertion_ancestors
    ):
        first_node, first_left, _ = touched[0]
        last_node, last_left, _ = touched[-1]
        first_text = first_node.text or ""
        last_text = last_node.text or ""
        prefix = first_text[: start - first_left]
        suffix = last_text[end - last_left :]
        first_node.text = prefix + new + suffix
        for node, _, _ in touched[1:]:
            node.text = ""
        return "updated-existing-insertion"

    if len(touched) != 1:
        raise RuntimeError(f"Untracked replacement spans {len(touched)} text nodes for {old!r}")
    node, left, _ = touched[0]
    run = node.getparent()
    if etree.QName(run).localname != "r" or len(run.xpath("./w:t", namespaces=NS)) != 1:
        raise RuntimeError(f"Unsupported untracked run structure for {old!r}")
    parent = run.getparent()
    position = parent.index(run)
    run_text = node.text or ""
    local_start = start - left
    local_end = end - left
    prefix = run_text[:local_start]
    suffix = run_text[local_end:]
    additions: list[etree._Element] = []
    if prefix:
        additions.append(text_run(prefix, run))
    deletion = revision_wrapper("del", revision_ids)
    deletion.append(text_run(old, run, deleted=True))
    additions.append(deletion)
    insertion = revision_wrapper("ins", revision_ids)
    insertion.append(text_run(new, run))
    additions.append(insertion)
    if suffix:
        additions.append(text_run(suffix, run))
    parent.remove(run)
    for offset, addition in enumerate(additions):
        parent.insert(position + offset, addition)
    return "new-tracked-replacement"


def set_run_font(run: etree._Element, font_name: str) -> None:
    rpr = run.find(W + "rPr")
    if rpr is None:
        rpr = etree.Element(W + "rPr")
        run.insert(0, rpr)
    fonts = rpr.find(W + "rFonts")
    if fonts is None:
        fonts = etree.Element(W + "rFonts")
        rpr.insert(0, fonts)
    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(W + attribute, font_name)


def format_figure_captions(paragraphs: list[etree._Element]) -> list[int]:
    changed: list[int] = []
    for index, paragraph in enumerate(paragraphs):
        if not re.match(r"^Figure\s+\d+\.", active_text(paragraph).strip()):
            continue
        for run in paragraph.xpath(".//w:r", namespaces=NS):
            if run.xpath("ancestor::w:del or ancestor::w:moveFrom", namespaces=NS):
                continue
            set_run_font(run, "Arial")
        changed.append(index)
    return changed


def format_all_captions(paragraphs: list[etree._Element]) -> list[int]:
    changed: list[int] = []
    for index, paragraph in enumerate(paragraphs):
        text = active_text(paragraph).strip()
        if not re.match(r"^(?:Figure|Table)\s+\d+\.", text):
            continue
        for run in paragraph.xpath(".//w:r", namespaces=NS):
            if run.xpath("ancestor::w:del or ancestor::w:moveFrom", namespaces=NS):
                continue
            set_run_font(run, "Arial")
        changed.append(index)
    return changed


def reorder_references(document: etree._Element) -> tuple[list[str], list[str]]:
    paragraphs = body_paragraphs(document)
    ranges = section_ranges(paragraphs)
    start, end = ranges["References"]
    slots = [paragraphs[index] for index in range(start + 1, end) if active_text(paragraphs[index]).strip()]
    original = [active_text(paragraph).strip() for paragraph in slots]
    selected: list[etree._Element] = []
    used: set[int] = set()
    for prefix, year in REFERENCE_ORDER:
        matches = [
            index
            for index, text in enumerate(original)
            if index not in used and text.startswith(prefix) and year in text
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Reference key {(prefix, year)!r} matched {len(matches)} entries")
        used.add(matches[0])
        selected.append(slots[matches[0]])
    selected.extend(paragraph for index, paragraph in enumerate(slots) if index not in used)

    parents_and_positions = [(paragraph.getparent(), paragraph.getparent().index(paragraph)) for paragraph in slots]
    for paragraph in slots:
        paragraph.getparent().remove(paragraph)
    for (parent, position), paragraph in zip(parents_and_positions, selected):
        parent.insert(position, paragraph)
    return original, [active_text(paragraph).strip() for paragraph in selected]


def ensure_track_revisions(package: dict[str, bytes]) -> None:
    settings = etree.fromstring(package["word/settings.xml"])
    if not settings.xpath("./w:trackRevisions", namespaces=NS):
        settings.insert(0, etree.Element(W + "trackRevisions"))
    package["word/settings.xml"] = etree.tostring(
        settings, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def new_run(text: str, bold: bool = False) -> etree._Element:
    run = etree.Element(W + "r")
    rpr = etree.SubElement(run, W + "rPr")
    fonts = etree.SubElement(rpr, W + "rFonts")
    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(W + attribute, "Arial")
    if bold:
        etree.SubElement(rpr, W + "b")
    node = etree.SubElement(run, W + "t")
    if text.startswith(" ") or text.endswith(" "):
        node.set(f"{{{XML_NS}}}space", "preserve")
    node.text = text
    return run


def new_tracked_paragraph(
    text: str,
    revision_ids: RevisionIds,
    *,
    style: str | None = None,
    bold_prefix: str | None = None,
) -> etree._Element:
    paragraph = etree.Element(W + "p")
    if style:
        ppr = etree.SubElement(paragraph, W + "pPr")
        pstyle = etree.SubElement(ppr, W + "pStyle")
        pstyle.set(W + "val", style)
    insertion = revision_wrapper("ins", revision_ids)
    if bold_prefix and text.startswith(bold_prefix):
        insertion.append(new_run(bold_prefix, bold=True))
        insertion.append(new_run(text[len(bold_prefix) :]))
    else:
        insertion.append(new_run(text))
    paragraph.append(insertion)
    return paragraph


def set_cell_text(cell: etree._Element, text: str, bold: bool = False) -> None:
    paragraph = etree.SubElement(cell, W + "p")
    paragraph.append(new_run(text, bold=bold))


def new_supplementary_trend_table(revision_ids: RevisionIds) -> etree._Element:
    table = etree.Element(W + "tbl")
    properties = etree.SubElement(table, W + "tblPr")
    style = etree.SubElement(properties, W + "tblStyle")
    style.set(W + "val", "TableGrid")
    width = etree.SubElement(properties, W + "tblW")
    width.set(W + "w", "0")
    width.set(W + "type", "auto")
    look = etree.SubElement(properties, W + "tblLook")
    look.set(W + "val", "04A0")
    grid = etree.SubElement(table, W + "tblGrid")
    for width_value in (3000, 1800, 3600):
        column = etree.SubElement(grid, W + "gridCol")
        column.set(W + "w", str(width_value))

    rows = [
        ("FRA interval", "Midpoint year", "Reported deforestation (Mha yr⁻¹)"),
        ("1990–2000", "1995", "15.819"),
        ("2000–2010", "2005", "13.329"),
        ("2010–2015", "2012.5", "9.878"),
        ("2015–2020", "2017.5", "9.478"),
        ("2020–2025", "2022.5", "8.484"),
    ]
    for row_index, values in enumerate(rows):
        row = etree.SubElement(table, W + "tr")
        row_properties = etree.SubElement(row, W + "trPr")
        row_properties.append(revision_wrapper("ins", revision_ids))
        if row_index == 0:
            header = etree.SubElement(row_properties, W + "tblHeader")
            header.set(W + "val", "true")
        for value in values:
            cell = etree.SubElement(row, W + "tc")
            cell_properties = etree.SubElement(cell, W + "tcPr")
            if row_index == 0:
                shading = etree.SubElement(cell_properties, W + "shd")
                shading.set(W + "val", "clear")
                shading.set(W + "fill", "D9D9D9")
            set_cell_text(cell, value, bold=row_index == 0)
    return table


def add_supplementary_trend_table(path: Path, package: dict[str, bytes], document: etree._Element) -> None:
    if path.name != "Supplementary Material.docx":
        raise RuntimeError("This operation may only modify Supplementary Material.docx")
    if "Supplementary Table S3." in active_text(document):
        raise RuntimeError("Supplementary Table S3 already exists")
    paragraphs = body_paragraphs(document)
    targets = [
        paragraph
        for paragraph in paragraphs
        if active_text(paragraph).strip() == "S8 Compensation scenarios"
    ]
    if len(targets) != 1:
        raise RuntimeError(f"Expected one S8 heading, found {len(targets)}")
    revision_ids = RevisionIds(document)
    target = targets[0]
    body = target.getparent()
    position = body.index(target)
    elements = [
        new_tracked_paragraph(
            "Supplementary Table S3. Reported global deforestation across FRA intervals.",
            revision_ids,
            bold_prefix="Supplementary Table S3.",
        ),
        new_supplementary_trend_table(revision_ids),
        new_tracked_paragraph(
            "Note. Values are sums across the 139 units that report deforestation. The Theil–Sen estimate is −0.272 Mha yr⁻², with a 95% confidence interval of −0.460 to −0.080 Mha yr⁻². The Mann–Kendall test gives p = 0.03. The series has five reporting intervals, so the trend is descriptive.",
            revision_ids,
            bold_prefix="Note.",
        ),
    ]
    for offset, element in enumerate(elements):
        body.insert(position + offset, element)
    ensure_track_revisions(package)
    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = path.with_name(path.stem + ".editing.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target_archive:
        for name, data in package.items():
            target_archive.writestr(name, data)
    os.replace(temporary, path)
    print("Inserted Supplementary Table S3 and its trend-statistics note.")


def apply_changes(path: Path, package: dict[str, bytes], document: etree._Element) -> None:
    paragraphs = body_paragraphs(document)
    revision_ids = RevisionIds(document)
    modes: defaultdict[str, int] = defaultdict(int)
    for index, old, new in REPLACEMENTS:
        modes[replace_active_substring(paragraphs[index], old, new, revision_ids)] += 1
    caption_indices = format_figure_captions(paragraphs)
    original_refs, ordered_refs = reorder_references(document)
    ensure_track_revisions(package)
    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    temporary = path.with_name(path.stem + ".editing.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, path)
    print(f"Applied {len(REPLACEMENTS)} acronym/citation-form replacements: {dict(modes)}")
    print(f"Arial applied to active figure captions at paragraphs: {caption_indices}")
    print(f"Reordered {len(ordered_refs)} references; first five were:")
    for reference in ordered_refs[:5]:
        print(f"  {reference[:160]}")


def postprocess(path: Path, package: dict[str, bytes], document: etree._Element) -> None:
    paragraphs = body_paragraphs(document)
    revision_ids = RevisionIds(document)
    for index, old, new in POST_REPLACEMENTS:
        replace_active_substring(paragraphs[index], old, new, revision_ids)

    ranges = section_ranges(paragraphs)
    start, end = ranges["References"]
    removed = 0
    for paragraph in list(paragraphs[start + 1 : end]):
        if not active_text(paragraph).strip() and len(paragraph.xpath(".//w:commentRangeStart | .//w:commentRangeEnd | .//w:commentReference", namespaces=NS)) == 0:
            paragraph.getparent().remove(paragraph)
            removed += 1

    ensure_track_revisions(package)
    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = path.with_name(path.stem + ".editing.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, path)
    print(f"Applied {len(POST_REPLACEMENTS)} final acronym replacements and removed {removed} empty reference paragraphs.")


def apply_validated_intro(path: Path, package: dict[str, bytes], document: etree._Element) -> None:
    paragraphs = body_paragraphs(document)
    for index, replacement in INTRO_PARAGRAPHS.items():
        nodes = active_text_nodes(paragraphs[index])
        if not nodes:
            raise RuntimeError(f"Introduction paragraph {index} has no active text nodes")
        insertions = [nearest_ancestor(node, "ins") for node in nodes]
        if not all(item is not None and item.get(W + "author") == AUTHOR for item in insertions):
            raise RuntimeError(f"Introduction paragraph {index} is not entirely tracked under {AUTHOR}")
        nodes[0].text = replacement
        if replacement.startswith(" ") or replacement.endswith(" "):
            nodes[0].set(f"{{{XML_NS}}}space", "preserve")
        for node in nodes[1:]:
            node.text = ""

    revision_ids = RevisionIds(document)
    replace_active_substring(
        paragraphs[55],
        "world gross domestic product (GDP)",
        "world GDP",
        revision_ids,
    )
    ensure_track_revisions(package)
    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = path.with_name(path.stem + ".editing.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, path)
    print(f"Replaced {len(INTRO_PARAGRAPHS)} active introduction paragraphs and moved the GDP definition to paragraph 42.")


def apply_caption_and_interval_format(path: Path, package: dict[str, bytes], document: etree._Element) -> None:
    paragraphs = body_paragraphs(document)
    revision_ids = RevisionIds(document)
    for index, old, new in INTERVAL_REPLACEMENTS:
        replace_active_substring(paragraphs[index], old, new, revision_ids)
    caption_indices = format_all_captions(paragraphs)
    ensure_track_revisions(package)
    package["word/document.xml"] = etree.tostring(
        document, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    temporary = path.with_name(path.stem + ".editing.docx")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in package.items():
            target.writestr(name, data)
    os.replace(temporary, path)
    print(f"Applied {len(INTERVAL_REPLACEMENTS)} interval-format replacements.")
    print(f"Arial applied to active table and figure captions at paragraphs: {caption_indices}")


def validate(package: dict[str, bytes], document: etree._Element) -> None:
    settings = etree.fromstring(package["word/settings.xml"])
    assert settings.xpath("./w:trackRevisions", namespaces=NS), "Track revisions is not enabled"
    authors: defaultdict[str, int] = defaultdict(int)
    for revision in document.xpath(".//w:ins | .//w:del", namespaces=NS):
        authors[revision.get(W + "author", "<missing>")] += 1

    comment_ids: set[str] = set()
    if "word/comments.xml" in package:
        comments = etree.fromstring(package["word/comments.xml"])
        comment_ids = set(comments.xpath(".//w:comment/@w:id", namespaces=NS))
    starts = set(document.xpath(".//w:commentRangeStart/@w:id", namespaces=NS))
    ends = set(document.xpath(".//w:commentRangeEnd/@w:id", namespaces=NS))
    refs = set(document.xpath(".//w:commentReference/@w:id", namespaces=NS))
    assert starts <= comment_ids and ends <= comment_ids and refs <= comment_ids, "Orphaned comment anchor"

    paragraphs = body_paragraphs(document)
    captions = []
    for index, paragraph in enumerate(paragraphs):
        if re.match(r"^(?:Figure|Table)\s+\d+\.", active_text(paragraph).strip()):
            fonts = set(paragraph.xpath(".//w:r[not(ancestor::w:del)]/w:rPr/w:rFonts/@w:ascii", namespaces=NS))
            assert fonts == {"Arial"}, f"Figure caption {index} is not uniformly Arial: {fonts}"
            captions.append(index)

    ranges = section_ranges(paragraphs)
    start, end = ranges["References"]
    blank_refs = [index for index in range(start + 1, end) if not active_text(paragraphs[index]).strip()]
    assert not blank_refs, f"Blank paragraphs remain in references: {blank_refs}"

    checks = {
        "Global Social Cost of Carbon": [33],
        "System of Environmental-Economic Accounting Ecosystem Accounting": [32],
        "Green Carbon Wealth": [41],
        "Blue Carbon Wealth": [35],
        "Natural Carbon Wealth": [41],
        "gross domestic product": [42],
        "small island developing states": [55],
    }
    for phrase, allowed in checks.items():
        hits = [
            index
            for index, paragraph in enumerate(paragraphs)
            if index < start and phrase.lower() in active_text(paragraph).lower()
        ]
        assert hits == allowed, f"Unexpected active occurrences for {phrase!r}: {hits}"

    print(f"trackRevisions=on; revision authors={dict(authors)}")
    print(f"comments={len(comment_ids)}; starts={len(starts)}; ends={len(ends)}; references={len(refs)}")
    print(f"Arial table/figure captions={captions}; reference blanks=0")
    print("Acronym full-form occurrence checks passed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--postprocess", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--apply-intro", action="store_true")
    parser.add_argument("--format-captions-intervals", action="store_true")
    parser.add_argument("--add-supplementary-trend-table", action="store_true")
    parser.add_argument("--show", default="")
    args = parser.parse_args()
    package, document = load_package(args.document)
    if args.add_supplementary_trend_table:
        add_supplementary_trend_table(args.document, package, document)
        return
    if args.format_captions_intervals:
        apply_caption_and_interval_format(args.document, package, document)
        return
    if args.apply_intro:
        apply_validated_intro(args.document, package, document)
        return
    if args.validate:
        validate(package, document)
        return
    if args.postprocess:
        postprocess(args.document, package, document)
        return
    if not args.apply:
        audit(document, args.show)
        return
    apply_changes(args.document, package, document)


if __name__ == "__main__":
    main()
