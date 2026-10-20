"""Historical Word sync for the superseded 2026-10-15 Results draft.

This script contains obsolete result text and images. Do not use it to update
the current PAPER.docx; current figure/table outputs are built by
``build_manuscript_artifacts.py`` and manuscript synchronization is a later,
separate task after spatial-model selection.

The script edits the existing DOCX package directly so that comments, section
properties, relationships, and the existing review history outside the touched
paragraphs remain intact. Text replacements are recorded as Word revisions by
Loua Aurel De Vince Vehi.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from lxml import etree
from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
PAPER = ROOT / "BNC2 paper" / "NEXT" / "PAPER.docx"
FIGURES = ROOT / "BNC2 paper" / "repo" / "results" / "archive" / "legacy_manuscript_2026-10-19" / "figures"
AUTHOR = "Loua Aurel De Vince Vehi"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = f"{{{W_NS}}}"
R = f"{{{R_NS}}}"
WP = f"{{{WP_NS}}}"
A = f"{{{A_NS}}}"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def visible_text(node: etree._Element) -> str:
    """Return text visible in the accepted current document, omitting deletions."""
    out: list[str] = []

    def visit(el: etree._Element, inside_deletion: bool = False) -> None:
        deleted = inside_deletion or el.tag == W + "del"
        if el.tag == W + "t" and not deleted:
            out.append(el.text or "")
        for child in el:
            visit(child, deleted)

    visit(node)
    return "".join(out)


def text_from_runs(node: etree._Element, tag: str) -> str:
    return "".join((item.text or "") for item in node.iter(W + tag))


class PaperEditor:
    def __init__(self, document: etree._Element):
        self.document = document
        self.body = document.find(W + "body")
        if self.body is None:
            raise RuntimeError("DOCX body not found")
        ids = []
        for el in document.iter():
            if el.tag in (W + "ins", W + "del", W + "moveFrom", W + "moveTo"):
                raw = el.get(W + "id")
                if raw and raw.isdigit():
                    ids.append(int(raw))
        self.next_revision_id = max(ids, default=0) + 1
        self.date = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self.changed: list[str] = []

    def paragraph(self, predicate) -> etree._Element:
        matches = [el for el in self.body if el.tag == W + "p" and predicate(visible_text(el))]
        if len(matches) != 1:
            examples = [visible_text(x)[:100] for x in matches[:4]]
            raise RuntimeError(f"Expected one paragraph; got {len(matches)} ({examples})")
        return matches[0]

    def _revision(self, tag: str, content: str, rpr: etree._Element | None) -> etree._Element | None:
        if not content:
            return None
        rev = etree.Element(W + tag)
        rev.set(W + "id", str(self.next_revision_id))
        self.next_revision_id += 1
        rev.set(W + "author", AUTHOR)
        rev.set(W + "date", self.date)
        run = etree.SubElement(rev, W + "r")
        if rpr is not None:
            run.append(deepcopy(rpr))
        txt_tag = W + ("delText" if tag == "del" else "t")
        txt = etree.SubElement(run, txt_tag)
        txt.set(f"{{{XML_NS}}}space", "preserve")
        txt.text = content
        return rev

    def replace(self, paragraph: etree._Element, new_text: str, *, anchors: list[tuple[str, str]] | None = None, label: str) -> None:
        old_text = visible_text(paragraph)
        if old_text == new_text and not anchors:
            return
        rpr = next((deepcopy(r) for r in paragraph.iter(W + "rPr")), None)
        ppr = paragraph.find(W + "pPr")
        comments: dict[tuple[str, str], etree._Element] = {}
        for kind in ("commentRangeStart", "commentRangeEnd"):
            for marker in paragraph.iter(W + kind):
                comments[(kind, marker.get(W + "id", ""))] = deepcopy(marker)
        for child in list(paragraph):
            if child is not ppr:
                paragraph.remove(child)
        if ppr is not None:
            paragraph.insert(0, ppr)
        deletion = self._revision("del", old_text, rpr)
        if deletion is not None:
            paragraph.append(deletion)
        if not new_text:
            self.changed.append(label)
            return

        cursor = 0
        for cid, phrase in anchors or []:
            start = new_text.find(phrase, cursor)
            if start < 0:
                raise RuntimeError(f"Comment anchor phrase not found for {label}: {phrase}")
            before = self._revision("ins", new_text[cursor:start], rpr)
            if before is not None:
                paragraph.append(before)
            start_marker = comments.get(("commentRangeStart", cid))
            end_marker = comments.get(("commentRangeEnd", cid))
            if start_marker is None or end_marker is None:
                raise RuntimeError(f"Comment marker {cid} not found for {label}")
            paragraph.append(start_marker)
            selected = self._revision("ins", phrase, rpr)
            if selected is not None:
                paragraph.append(selected)
            paragraph.append(end_marker)
            cursor = start + len(phrase)
        after = self._revision("ins", new_text[cursor:], rpr)
        if after is not None:
            paragraph.append(after)
        self.changed.append(label)

    def replace_paragraph(self, starts: str, new_text: str, *, label: str, anchors=None) -> None:
        p = self.paragraph(lambda s: s.startswith(starts))
        self.replace(p, new_text, anchors=anchors, label=label)

    def delete_paragraph(self, starts: str, *, label: str) -> None:
        p = self.paragraph(lambda s: s.startswith(starts))
        self.replace(p, "", label=label)

    def find_table(self, first_cell: str, second_cell: str | None = None) -> etree._Element:
        found = []
        for table in self.body.iter(W + "tbl"):
            first_row = table.find(W + "tr")
            if first_row is None:
                continue
            first = first_row.find(W + "tc")
            if first is None or visible_text(first).strip() != first_cell:
                continue
            if second_cell is not None:
                cells = first_row.findall(W + "tc")
                if len(cells) < 2 or visible_text(cells[1]).strip() != second_cell:
                    continue
            found.append(table)
        if len(found) != 1:
            raise RuntimeError(f"Expected one table beginning with {first_cell!r}; found {len(found)}")
        return found[0]

    def update_table(self, first_cell: str, rows: dict[str, list[str]], *, second_cell: str | None = None, header_updates: dict[str, str] | None = None, label: str) -> None:
        table = self.find_table(first_cell, second_cell)
        for ri, row in enumerate(table.findall(W + "tr")):
            cells = row.findall(W + "tc")
            if not cells:
                continue
            key = visible_text(cells[0]).strip()
            if ri == 0 and header_updates:
                for cell in cells:
                    old = visible_text(cell).strip()
                    if old in header_updates:
                        self.replace(cell.find(W + "p"), header_updates[old], label=f"{label} header {old}")
            if key not in rows:
                continue
            vals = rows[key]
            if len(vals) != len(cells) - 1:
                raise RuntimeError(f"Table {label}: row {key!r} has {len(cells)} cells, expected {len(vals)+1}")
            for ci, value in enumerate(vals, 1):
                p = cells[ci].find(W + "p")
                if p is None:
                    raise RuntimeError(f"Table {label}: no paragraph for {key!r} cell {ci}")
                self.replace(p, value, label=f"{label} {key} cell {ci}")
        self.changed.append(label)


def update_images(package: dict[str, bytes], document: etree._Element) -> None:
    relationships = etree.fromstring(package["word/_rels/document.xml.rels"])
    rel_targets = {
        rel.get("Id"): rel.get("Target")
        for rel in relationships.findall(f"{{{REL_NS}}}Relationship")
    }
    image_map = {
        "Figure1_forest_service_and_concentration.png": (
            "Figure 1",
            "Two panels: annual GCW against GDP for accounting units, and Lorenz curves for GCW and BCW with Gini coefficients.",
        ),
        "Figure2_blue_carbon_and_net_balance.png": (
            "Figure 2",
            "Two panels: forest and blue carbon wealth by country group; emissions and accounted annual carbon flows for selected accounting units.",
        ),
        "Figure3_erosion_of_forest_service.png": (
            "Figure 3",
            "Scatter plot of annual forest-addition capacity no longer supplied as a share of GCW against GCW for 105 reporting units; median lines and eight labels.",
        ),
        "Figure4_compensation_burden.png": (
            "Figure 4",
            "Grouped horizontal bars compare domestic replacement cost and GDP-proportional shared effort by group under the illustrative 150 US dollars per tonne case.",
        ),
    }
    r_to_file: dict[str, str] = {}
    for rid, target in rel_targets.items():
        if target and target.startswith("media/"):
            r_to_file[rid] = "word/" + target
    for filename, (title, description) in image_map.items():
        source = FIGURES / filename
        target_path = next((v for v in r_to_file.values() if Path(v).name == filename or Path(v).stem == Path(filename).stem), None)
        if target_path is None:
            # The document uses image1.png...image4.png rather than descriptive filenames.
            index = int(re.search(r"Figure(\d+)", filename).group(1))
            target_path = f"word/media/image{index}.png"
        if target_path not in package:
            raise RuntimeError(f"Image relationship target missing: {target_path}")
        package[target_path] = source.read_bytes()
        with Image.open(source) as im:
            px_w, px_h = im.size
        rel_ids = {rid for rid, target in r_to_file.items() if target == target_path}
        for blip in document.iter(A + "blip"):
            rid = blip.get(R + "embed")
            if rid not in rel_ids:
                continue
            drawing = blip
            while drawing is not None and drawing.tag not in (WP + "inline", WP + "anchor"):
                drawing = drawing.getparent()
            if drawing is None:
                continue
            ext = drawing.find(WP + "extent")
            if ext is None:
                continue
            cx = int(ext.get("cx"))
            cy = round(cx * px_h / px_w)
            ext.set("cy", str(cy))
            for aext in drawing.iter(A + "ext"):
                if aext.get("cx") is not None:
                    aext.set("cx", str(cx))
                    aext.set("cy", str(cy))
            for prop in drawing.iter(WP + "docPr"):
                prop.set("title", title)
                prop.set("descr", description)


def main() -> None:
    if not PAPER.is_file():
        raise FileNotFoundError(PAPER)
    backup = ROOT / "BNC2 paper" / "repo" / "results" / "validation" / "PAPER_before_results_sync.docx"
    if not backup.is_file():
        raise FileNotFoundError(f"Expected pre-edit backup: {backup}")
    with zipfile.ZipFile(PAPER, "r") as z:
        package = {name: z.read(name) for name in z.namelist()}
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    document = etree.fromstring(package["word/document.xml"], parser)
    editor = PaperEditor(document)

    # Requested citation addition and abstract synchronisation.
    introduction_paragraph = "Conventional economic accounts primarily record exchange values, leaving many non-market ecosystem services insufficiently represented. The System of Environmental-Economic Accounting-Ecosystem Accounting (SEEA-EA) provides a framework for recording ecosystem services using exchange-value conventions (United Nations et al., 2021). Inclusive wealth accounting instead assesses the economic value of natural assets according to their contribution to societal well-being (Bertram et al., 2021). Recent research has applied this approach to marine carbon sequestration and storage, demonstrating how these services can be expressed as contributions to inclusive wealth (Bertram et al., 2021; Berzaghi et al., 2025; Hilmi et al., 2026)."
    editor.replace_paragraph(
        "Conventional economic accounts primarily record exchange values",
        introduction_paragraph,
        label="Introduction citation Berzaghi 2025",
        anchors=[("134", introduction_paragraph)],
    )
    editor.replace_paragraph(
        "Forests and oceans remove carbon dioxide, but their contributions",
        "Forests and marine ecosystems contribute to climate regulation, yet their annual contributions to national wealth and the distributional consequences of their loss remain incompletely quantified. Here we estimate the annual welfare value assigned to gross carbon additions to living forest biomass for 236 forest units within a harmonized framework of 266 countries and territories. We combine this estimate with published marine carbon values and national emissions, economic, and deforestation data. The forest account estimates 14.68 GtCO₂ per year of gross additions to living biomass and GCW of US$8.22 [3.21-14.92] trillion per year in constant 2015 dollars, 77.9% of combined forest and marine value. Tropical, subtropical, temperate, and boreal forests contribute 44.5%, 15.9%, 22.0%, and 17.5% of estimated forest additions, respectively. Forest value is particularly large relative to recorded economic output in least developed countries. Adding marine flows raises the share of accounting units with positive annual balances against fossil-fuel and industrial CO₂ emissions from 37% to 54%. Reported deforestation across 139 units removes 34.83 MtCO₂ per year of modeled annual forest-addition capacity, valued at US$19.49 billion per year. Illustrative abatement prices imply replacement costs of US$1.74-13.93 billion per year; domestic allocation produces the highest relative burdens in least developed countries. These results distinguish annual ecosystem-service values, lost capacity, and hypothetical mitigation costs.",
        label="Abstract result synchronisation",
        anchors=[
            ("44", "annual welfare value assigned to gross carbon additions to living forest biomass"),
            ("47", "44.5%"),
            ("48", "15.9%"),
            ("55", "Reported deforestation across 139 units"),
            ("57", "replacement costs"),
        ],
    )

    # Main Results text, with reviewer comment ranges retained on their revised referents.
    editor.replace_paragraph("Contribution of forest carbon sinks to national carbon", "Forest carbon wealth and its national distribution", label="Results heading 1", anchors=[("151", "Forest carbon wealth and its national distribution")])
    editor.replace_paragraph(
        "Forests removed 14.58 GtCO₂ per year",
        "The country account estimates 14.68 GtCO₂ per year of gross carbon additions to living forest biomass, equivalent to 4.00 GtC per year. This flow is assigned GCW of US$8.22 [3.21-14.92] trillion per year. The published marine account contributes BCW of US$2.33 [0.91-4.30] trillion, bringing NCW to US$10.55 [4.15-19.12] trillion per year. Forests account for 77.9% of the mean combined value (Table 1). These annual values represent the welfare value assigned to the modeled flows; they are not estimates of carbon stocks, national income, or financing entitlements.",
        label="Results global account",
    )
    editor.update_table(
        "Component",
        {
            "Green carbon wealth": ["8.22", "3.21-14.92", "77.9"],
            "Blue carbon wealth": ["2.33", "0.91-4.30", "22.1"],
            "Natural carbon wealth": ["10.55", "4.15-19.12", "100.0"],
        },
        second_cell="Mean (trillion 2015 US$/year)",
        label="Table 1 values",
    )
    editor.replace_paragraph(
        "Tropical forests supplied 78.6% of global forest uptake",
        "The forest account uses four biome-specific rates estimated from Gibbs/GFW pixels after excluding pixels classified as mangroves by the source model: 0.934 tC ha⁻¹ yr⁻¹ for tropical, 1.371 for subtropical, 1.430 for temperate, and 0.619 for boreal forests. Applied to the allocated forest areas used in the country calculation-1,908.3, 464.8, 616.4, and 1,135.2 Mha, respectively-these rates yield 44.5%, 15.9%, 22.0%, and 17.5% of estimated global living-biomass additions (Supplementary Section S3). The resulting shares combine modeled average rates with allocated forest areas; they are not direct observations of each country's annual forest growth.",
        label="Results four-biome decomposition",
    )
    editor.replace_paragraph(
        "Forest area did not translate proportionally into uptake value across economic groups",
        "The estimated forest value was distributed across all four economic groups. Developed economies supplied US$3.60 trillion per year of GCW (43.9% of the total), developing economies US$3.40 trillion (41.4%), least developed countries (LDCs) US$1.05 trillion (12.8%), and Small Island Developing States (SIDS) US$0.16 trillion (2.0%) (Table 2). Median GCW-to-GDP ratios were 4.0% in developed economies, 8.7% in developing economies, 53.3% in LDCs, and 4.4% in SIDS. These ratios describe the estimated annual service value relative to the scale of recorded economic output; they are not shares of GDP produced by forests or income transferred to countries. Group distributions differed significantly (Kruskal-Wallis H = 38.2, p = 2.53 × 10⁻⁸; Supplementary Section S6).",
        label="Results group wealth and ratio explanation",
        anchors=[("153", "53.3% in LDCs")],
    )
    editor.replace_paragraph(
        "GCW was also concentrated within groups",
        "GCW was highly concentrated across accounting units. The Russian Federation had the largest estimated value (US$1.21 trillion per year), followed by Brazil (US$0.94 trillion) and the United States (US$0.82 trillion). The ten largest units accounted for 64.1% of global GCW, and the Gini coefficient was 0.866. Figure 1a shows the relationship between GCW and GDP; their rank correlation was positive (Spearman ρ = 0.60, p = 1.6 × 10⁻²⁰, n = 198). Figure 1b shows stronger concentration in GCW (Gini 0.87) than in BCW (Gini 0.76). These national and territorial units are spatial attribution units for the estimated flows.",
        label="Results concentration and GDP association",
    )
    editor.replace_paragraph("Table 2. Country-group profiles of GCW and sink composition", "Table 2. Country-group profiles of GCW and green-blue composition.", label="Table 2 caption")
    editor.update_table(
        "Group",
        {
            "Developed economies": ["3.60", "43.9", "4.0", "22", "9"],
            "Developing economies": ["3.40", "41.4", "8.7", "29", "17"],
            "LDCs": ["1.05", "12.8", "53.3", "12", "3"],
            "SIDS": ["0.16", "2.0", "4.4", "8", "38"],
        },
        second_cell="GCW (trillion 2015 US$/year)",
        label="Table 2 values",
    )
    editor.replace_paragraph("Figure 1 | Forest carbon uptake dominates", "Figure 1 | Annual forest value varies with economic size and is concentrated across units.", label="Figure 1 caption title")
    editor.replace_paragraph("a. Annual Green Carbon Wealth (GCW)", "a. Annual GCW and GDP per accounting unit in constant 2015 US dollars; both axes use logarithmic scales and colours identify country groups.", label="Figure 1 panel a caption")
    editor.replace_paragraph("b. Global annual value of forest", "b. Lorenz curves of GCW and BCW across accounting units; Gini coefficients are reported in the legend. Monetary values are in constant 2015 US dollars.", label="Figure 1 panel b caption")
    editor.delete_paragraph("c. Lorenz curves of GCW and BCW", label="Remove obsolete Figure 1 panel c caption")

    editor.replace_paragraph("Extension to include Blue Carbon", "Marine carbon wealth and national accounting balances", label="Results heading 2")
    editor.replace_paragraph(
        "Adding BCW changed the composition of national carbon wealth",
        "Adding the published marine account changed the composition of national carbon wealth among 175 of 242 units for which both components supported classification. Under the two-thirds dominance threshold, 71 units were green-dominant, 67 blue-dominant, and 37 mixed. SIDS had 38 blue-dominant and 8 green-dominant units, whereas LDCs had 12 green-dominant and 3 blue-dominant units; developed economies had 22 and 9, and developing economies 29 and 17, respectively (Table 2; Figure 2a). The composition reflects the geography of forest areas and marine accounting values; the two physical flows are not interchangeable.",
        label="Results group composition",
    )
    editor.replace_paragraph(
        "The ocean component also changed national net balances",
        "The marine component also changed national annual accounting balances. Among 210 accounting units with emissions and flow estimates, the share classified as net sinks under the accounted CO₂ boundary rose from 37% with forests alone to 54% with forests and marine flows. The ten largest emitting units accounted for 74% of global emissions; the ten largest flow-attribution units outside that emitter group accounted for 35% of global accounted removals (Figure 2b). These are territorial attribution results, not a claim that governments or territories are the ecological agents producing every flow. A positive annual balance under the selected boundary does not establish a trajectory compatible with climate neutrality.",
        label="Results annual balances and flow concentration",
        anchors=[("156", "accounting units"), ("157", "net sinks under the accounted CO₂ boundary"), ("158", "A positive annual balance under the selected boundary does not establish a trajectory compatible with climate neutrality.")],
    )
    editor.replace_paragraph(
        "NCW remains a lower bound for 61 forest units",
        "NCW remains a lower bound for 61 forest units without a known marine component. This coverage constraint does not affect the forest account, but it limits comparisons of the combined profile. The next analysis examines the annual forest-addition capacity associated with reported deforestation, rather than treating conversion as an observed release of the carbon already stored in forests.",
        label="Results marine coverage limitation",
    )
    editor.replace_paragraph("Figure 2. Ocean uptake changes national carbon profiles", "Figure 2 | Marine flows alter country-group wealth and national accounting balances.", label="Figure 2 caption title")
    editor.replace_paragraph("a. Share of Natural Carbon Wealth supplied by forests", "a. Annual GCW and BCW by country group, in trillion constant 2015 US dollars per year.", label="Figure 2 panel a caption")
    editor.replace_paragraph("b. Net carbon balance with forests only", "b. 2023 fossil-fuel and industrial CO₂ emissions and accounted annual forest and marine flows for the ten largest emitting units (left of divider) and ten largest flow-attribution units outside that set (right); bars show shares of global annual fluxes. The forest component is gross addition to living biomass and the marine component is the published accounted blue-carbon flow.", label="Figure 2 panel b caption")
    editor.delete_paragraph("c. The ten largest emitters", label="Remove obsolete Figure 2 panel c caption")

    editor.replace_paragraph("Deforestation effects", "Deforestation and lost annual forest-addition capacity", label="Results heading 3")
    editor.replace_paragraph(
        "Reported deforestation averaged 9.70 Mha per year",
        "FRA-reported deforestation averaged 9.70 Mha per year over 2010-2019. Across reporting units, converted area corresponded to 34.83 MtCO₂ per year of modeled annual forest-addition capacity no longer supplied, valued at US$19.49 billion per year (Table 3). The estimated annual value loss was 0.30% of the GCW reported for those units. Brazil had the largest estimated annual value loss (US$4.41 billion), followed by India (US$1.34 billion), the Democratic Republic of the Congo (US$1.24 billion), Australia (US$1.05 billion), and Indonesia (US$1.04 billion; Supplementary country-level erosion table). This is foregone future addition capacity after conversion, not an estimate of emissions from carbon already stored in vegetation or soils. The estimates cover 139 of 236 forest units, representing 79% of global GCW.",
        label="Results deforestation totals and coverage",
        anchors=[("161", "FRA-reported deforestation averaged 9.70 Mha per year over 2010-2019. Across reporting units, converted area corresponded to 34.83 MtCO₂ per year of modeled annual forest-addition capacity no longer supplied, valued at US$19.49 billion per year (Table 3). The estimated annual value loss was 0.30% of the GCW reported for those units. Brazil had the largest estimated annual value loss (US$4.41 billion), followed by India (US$1.34 billion), the Democratic Republic of the Congo (US$1.24 billion), Australia (US$1.05 billion), and Indonesia (US$1.04 billion; Supplementary country-level erosion table). This is foregone future addition capacity after conversion, not an estimate of emissions from carbon already stored in vegetation or soils. The estimates cover 139 of 236 forest units, representing 79% of global GCW.")],
    )
    editor.replace_paragraph("Table 3. Annual loss of forest sink service", "Table 3. Annual loss of modeled forest living-biomass addition capacity, 2010-2019.", label="Table 3 caption")
    editor.update_table(
        "Group",
        {
            "Developed economies": ["45", "0.69", "2.85", "1.59"],
            "Developing economies": ["51", "5.63", "20.39", "11.41"],
            "LDCs": ["24", "3.29", "11.28", "6.31"],
            "SIDS": ["17", "0.09", "0.31", "0.17"],
        },
        second_cell="Reporting units",
        label="Table 3 values",
    )
    editor.replace_paragraph(
        "The annual percentage is small relative to the service",
        "If the reported annual deforestation rate continued and converted areas remained outside forest, the modeled loss of annual addition capacity would accumulate to 2.37% of the current global forest-flow estimate after ten years. Capitalizing the current annual value loss as a permanent stream at a 2% real discount rate gives an illustrative value of US$0.975 trillion. Developing economies accounted for 58.5% of the reported annual value loss and LDCs for 32.4%, compared with 8.2% in developed economies and 0.9% in SIDS (Table 3). The ten-year calculation assumes no regrowth or change in biome rates, and the capitalized value is not an observed asset price. Group shares apply only to reporting units.",
        label="Results cumulative erosion and group incidence",
    )
    editor.replace_paragraph(
        "The magnitude of the current service did not predict erosion intensity",
        "Across 105 units with positive reported deforestation and positive GCW, GCW and annual erosion intensity had a weak negative rank association (Spearman ρ = −0.22, p = 0.022). Figure 3 plots annual gross-addition capacity no longer supplied as a percentage of GCW against GCW; median lines divide the units into 32 high-GCW/low-erosion, 21 high/high, 32 low/high, and 20 low/low profiles. The association is descriptive and does not establish that current service value causes or predicts deforestation. The figure excludes 34 reporting units with zero deforestation and 97 units with missing deforestation reports.",
        label="Results erosion intensity association",
    )
    editor.replace_paragraph(
        "Reported global deforestation nearly halved",
        "Reported global deforestation nearly halved from 15.8 Mha per year in the 1990s to 8.5 Mha per year in 2020-2025 (Supplementary Table S3). This trend concerns reported area, while the modeled 34.83 MtCO₂ per year of lost forest-addition capacity is calculated for the separate 2010-2019 reference period. Earlier regional losses reached 3.3-3.6 Mha per year in Africa and 7.3 Mha per year in South America during the 1990s. At country level, only Indonesia (p = 0.027) and Paraguay (p = 0.050) showed a significant decline; the decline in Brazil was not significant. The global trend indicates slower reported area loss, not a reversal of accumulated capacity loss. Five reporting intervals and incomplete country coverage limit the strength of the inference.",
        label="Results deforestation time trend",
    )
    editor.replace_paragraph("Figure 3. Deforestation persistently erodes", "Figure 3 | Annual forest-addition capacity loss varies across reporting units.", label="Figure 3 caption title")
    editor.replace_paragraph("a. Annual loss of forest uptake capacity", "Each point shows annual gross-addition capacity no longer supplied as a percentage of GCW against GCW for 105 units with positive reported deforestation. Both axes are logarithmic; dashed lines mark the medians, and labels identify the eight units with the largest absolute estimated value losses.", label="Figure 3 caption")
    editor.delete_paragraph("b. GCW against annual erosion intensity", label="Remove obsolete Figure 3 panel b caption")
    editor.delete_paragraph("c. Reported global deforestation by FRA interval", label="Remove obsolete Figure 3 panel c caption")

    editor.replace_paragraph("Compensation costs and burdens divergences", "Illustrative replacement costs and burden allocation", label="Results heading 4", anchors=[("164", "Illustrative replacement costs")])
    editor.replace_paragraph(
        "The welfare value of lost capacity and the cost of replacing that capacity",
        "The welfare value of lost capacity and the cost of replacing that capacity use different prices for the same annual tonne. The GSCC values avoided climate damages, whereas an abatement price approximates the cost of additional mitigation. Across 139 reporting forest units, illustrative prices of US$50, US$150, and US$400 per tCO₂ imply annual replacement costs of US$1.74, US$5.22, and US$13.93 billion, respectively (Table 4). These amounts equal 0.09, 0.27, and 0.71 of the annual welfare value lost. The prices are illustrative scenario inputs; the ratios do not establish that replacement would be cheaper under every technology, location, or policy constraint.",
        label="Results replacement cost scenarios",
    )
    editor.replace_paragraph("Table 4. Illustrative annual compensation costs", "Table 4. Illustrative annual replacement costs under alternative abatement prices.", label="Table 4 caption")
    editor.update_table(
        "Illustrative price (2015 US$/tCO₂)",
        {
            "50": ["1.74", "0.09"],
            "150": ["5.22", "0.27"],
            "400": ["13.93", "0.71"],
        },
        header_updates={
            "Annual compensation (billion 2015 US$)": "Annual cost (billion 2015 US$)",
            "Compensation/welfare-loss ratio": "Cost/lost-value ratio",
        },
        label="Table 4 values",
    )
    editor.replace_paragraph(
        "The allocation rule changed who carried this cost",
        "The allocation rule changed which groups bear the modeled replacement cost. At US$150 per tCO₂, LDCs would face US$1.69 billion per year under domestic allocation and US$0.08 billion under an allocation proportional to GDP. Developed economies would face US$0.43 billion domestically and US$2.16 billion under the shared-effort rule. Under domestic allocation, the burden reached 1.02% of GDP in the Central African Republic, 0.85% in Somalia, and 0.67% in Mozambique. Figure 4 compares group totals under the two rules. These are burden-sharing scenarios for the 139 reporting units, not forecasts of a carbon market or statements of legal responsibility.",
        label="Results replacement cost allocation",
    )
    editor.replace_paragraph(
        "The ocean scenarios show that a wider erosion of natural sinks",
        "A 5% decline in the published annual BCW flow corresponds to 208 MtCO₂ per year, about 6.0 times the modeled forest-addition capacity loss associated with reported deforestation, and to US$116.5 billion per year at the common valuation. A 10% decline corresponds to 416 MtCO₂ and US$233.1 billion per year. These are sensitivity scenarios based on the published marine account, not observed ocean losses (Table 1; comparison with Table 3).",
        label="Results marine decline sensitivity",
    )
    editor.replace_paragraph("Figure 4. Under domestic allocation", "Figure 4 | Illustrative replacement costs differ across country groups under alternative allocation rules.", label="Figure 4 caption title")
    editor.replace_paragraph("a. Annual cost of replacing the forest uptake capacity", "At an illustrative abatement price of US$150 per tCO₂, bars compare annual replacement costs by group under domestic allocation and GDP-proportional shared effort (billion constant 2015 US dollars per year).", label="Figure 4 caption")
    editor.delete_paragraph("b. Domestic replacement cost as a share of GDP", label="Remove obsolete Figure 4 panel b caption")
    editor.delete_paragraph("c. Annual forest capacity lost", label="Remove obsolete Figure 4 panel c caption")

    # Discussion values and statements tied to the replaced results.
    editor.replace_paragraph(
        "Forest and ocean carbon sinks underpin a large annual climate-regulation service",
        "Forest and marine carbon flows underpin a large annual climate-regulation service, but their estimated welfare values and spatial attribution are unevenly distributed. GCW reached US$8.22 [3.21-14.92] trillion per year and accounted for 77.9% of NCW after combination with the published marine account. This result extends the national accounting comparison to forests while keeping the unit of analysis an annual welfare contribution rather than a stock value or revenue stream.",
        label="Discussion global summary",
    )
    editor.replace_paragraph(
        "The combined account reveals patterns that a forest or ocean account",
        "The combined account reveals patterns that a forest or marine account alone cannot show. Tropical, subtropical, temperate, and boreal forests supplied 44.5%, 15.9%, 22.0%, and 17.5% of estimated gross living-biomass additions. Marine flows changed the composition of carbon wealth most strongly in SIDS. Adding BCW raised the share of accounting units with positive annual balances against fossil-fuel and industrial emissions from 37% to 54%; this boundary-based classification does not establish climate neutrality. The population-weighted mean NCW was US$1,303 per person, while the unweighted mean across units with data was US$19,858. Per-capita figures remain in the Supplementary Material because they describe demographic scale; GCW relative to GDP is used in the main text to describe the service value relative to economic output.",
        label="Discussion group and balance summary",
    )
    editor.replace_paragraph(
        "The erosion result adds a temporal dimension to the account",
        "The erosion result adds a temporal dimension to the account. Reported deforestation corresponded to US$19.49 billion per year of lost annual forest-addition capacity across 139 reporting units, representing 79% of global GCW. The annual value loss was 0.30% of reported-unit GCW. Under a constant-rate, no-regrowth scenario, ten-year accumulated lost capacity would equal 2.37% of the current global forest-flow estimate. Erosion value was concentrated in developing economies and LDCs. Across 105 positive-reporting units, GCW had a weak negative association with erosion intensity (Spearman ρ = −0.22, p = 0.022); this does not establish causation. Protection priorities therefore cannot be inferred from current service magnitude alone.",
        label="Discussion erosion summary",
    )
    editor.replace_paragraph(
        "The compensation scenarios make the distributional issue explicit",
        "The replacement-cost scenarios make the distributional issue explicit. At US$150 per tCO₂, LDCs would face US$1.69 billion per year under domestic allocation and US$0.08 billion under allocation proportional to GDP. This contrast reflects how alternative rules distribute a hypothetical additional-abatement cost; it does not establish a payment obligation or an entitlement to climate finance.",
        label="Discussion allocation summary",
    )
    editor.replace_paragraph(
        "The forest and blue accounts require several harmonizations",
        "The forest and marine accounts rely on different spatial products, definitions, and reference periods. Our four FAO GEZ mean rates are estimated from Gibbs/GFW gross-removal pixels for 2001-2023, with source-model mangrove pixels excluded, and applied to FRA forest areas for 2025. These rates estimate gross additions to living above- and below-ground biomass; they do not represent a net balance of the whole forest ecosystem or the duration for which each added tonne remains in living biomass. Socio-economic variables refer to 2023 or the nearest compatible year, while reported deforestation is averaged over 2010-2019. The resulting country comparisons therefore combine non-contemporaneous inputs and spatial classifications that are not perfectly aligned.",
        label="Discussion harmonisation and forest-rate limits",
    )
    editor.replace_paragraph(
        "Erosion estimates cover 139 of 236 forest units",
        "Erosion estimates cover 139 of 236 forest units and 79% of global GCW. Missing deforestation reports are treated as missing rather than zero. For 61 units without a known marine component, NCW is a lower bound. Forest-area and biome-rate uncertainty are not propagated into the main monetary intervals, which reflect GSCC draws and the published marine valuation uncertainty. The erosion measure includes reported deforestation only; it excludes degradation, fire, recovery dynamics, and sink saturation. Climate stress and disturbance can weaken forest uptake beyond area conversion (Green and Keenan, 2022).",
        label="Discussion coverage and uncertainty limits",
    )
    editor.replace_paragraph(
        "The compensation prices of US$50",
        "The replacement-cost results use illustrative abatement prices of US$50, US$150, and US$400 per tCO₂; they are not country-specific marginal-abatement-cost estimates. Ocean declines are sensitivity scenarios, not observed losses. The account also excludes other terrestrial ecosystems, including grasslands and savannas, which regulate climate.",
        label="Discussion scenario limits",
    )
    editor.replace_paragraph(
        "Welfare value, additional mitigation and climate finance must remain distinct",
        "Welfare value, additional mitigation, and climate finance must remain distinct. The GSCC represents avoided marginal climate damages, while the replacement-cost scenarios use illustrative abatement prices. Neither establishes an amount of climate finance owed to a country. Nature-based finance also requires attention to permanence, additionality, leakage, monitoring, rights, and governance, as Chausson et al. (2023) emphasize. The REDD+ framework and standards such as Verra and ART-TREES address these issues through different institutional rules. The account can identify where climate-regulation benefits are generated; it does not by itself establish a credit or finance entitlement.",
        label="Discussion climate-finance distinction",
        anchors=[("167", "The account can identify where climate-regulation benefits are generated; it does not by itself establish a credit or finance entitlement.")],
    )
    editor.replace_paragraph(
        "Forest carbon sinks provide a large annual service",
        "Forest and marine carbon flows represent a large annual climate-regulation service, with forest value concentrated across accounting units and forest capacity loss concentrated in poorer country groups. Marine flows change national accounting profiles, while reported deforestation reduces the annual forest-addition capacity associated with converted areas. Illustrative replacement costs depend on the chosen price and allocation rule; domestic allocation places the largest relative burdens on LDCs. These accounts make the patterns visible while keeping ecosystem-service value, lost annual capacity, mitigation costs, and climate finance distinct.",
        label="Discussion conclusion",
    )

    # Keep terminology consistent in the Methods headings and short references.
    editor.replace_paragraph("Compensation scenarios", "Replacement-cost scenarios", label="Methods replacement-cost heading")
    editor.replace_paragraph(
        "Two allocation rules bound the distribution of the resulting bill",
        "Two allocation rules bound the distribution of the resulting replacement cost. Under domestic allocation, each country covers the loss occurring on its own territory. Under shared effort, the global cost is distributed in proportion to GDP. Neither rule is a least-cost equilibrium: a genuine market outcome would require national marginal-abatement-cost curves, which are identified as an extension rather than used here.",
        label="Methods replacement-cost allocation wording",
    )

    update_images(package, document)
    package["word/document.xml"] = etree.tostring(document, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = PAPER.with_suffix(".results-sync.tmp.docx")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in package.items():
            z.writestr(name, data)
    # Verify the archive before replacing the manuscript.
    with zipfile.ZipFile(tmp, "r") as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"DOCX package verification failed at {bad}")
        check = etree.fromstring(z.read("word/document.xml"), parser)
        final_text = "\n".join(visible_text(p) for p in check.iter(W + "p"))
        for required in ["Berzaghi et al., 2025", "14.68 GtCO₂", "34.83 MtCO₂", "US$19.49 billion", "54%", "64.1%"]:
            if required not in final_text:
                raise RuntimeError(f"Post-edit content check failed: {required}")
        obsolete = ["14.58 GtCO₂", "US$8.16", "78.6%", "US$25.7", "45.9 MtCO₂", "US$6.88", "US$18.36", "37% to 52%"]
        still_visible = [value for value in obsolete if value in final_text]
        if still_visible:
            raise RuntimeError(f"Obsolete Results values remain visible: {still_visible}")
        comments = etree.fromstring(z.read("word/comments.xml"))
        comment_ids = {c.get(W + "id") for c in comments.iter(W + "comment")}
        start_ids = {c.get(W + "id") for c in check.iter(W + "commentRangeStart")}
        end_ids = {c.get(W + "id") for c in check.iter(W + "commentRangeEnd")}
        if comment_ids - start_ids or comment_ids - end_ids:
            raise RuntimeError(f"Comment range markers lost: starts={sorted(comment_ids-start_ids)}, ends={sorted(comment_ids-end_ids)}")
        for cid in ["44", "47", "48", "55", "57", "134", "151", "153", "156", "157", "158", "161", "164", "167"]:
            if not any(c.get(W + "id") == cid for c in comments.iter(W + "comment")):
                raise RuntimeError(f"Comment {cid} was lost")
    shutil.move(str(tmp), str(PAPER))
    print(f"Updated: {PAPER}")
    print(f"Track changes inserted by: {AUTHOR}")
    print(f"Changes applied: {len(editor.changed)} entries")
    for item in editor.changed:
        print(f"- {item}")


if __name__ == "__main__":
    main()
