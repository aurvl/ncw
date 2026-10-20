"""Apply the approved manuscript-revision brief as visible Word redlines.

This script preserves existing comments and revisions.  It never accepts or
rejects an existing change: superseded paragraphs are represented as ordinary
Word deletions and revised paragraphs are added immediately after them as Word
insertions.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import os
import re

from lxml import etree


ROOT = Path(__file__).resolve().parents[3]
ARTICLE = ROOT / "Article_Green_Carbon.docx"
METHODS_SOURCE = ROOT / "METHODS_REWRITE.md"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def w(name: str) -> str:
    return f"{{{W_NS}}}{name}"


def text(node: etree._Element) -> str:
    return "".join(node.xpath(".//w:t/text()", namespaces=NS))


def all_text(node: etree._Element) -> str:
    return "".join(node.xpath(".//w:t/text() | .//w:delText/text()", namespaces=NS))


def next_id(root: etree._Element) -> int:
    found = []
    for value in root.xpath(".//*[@w:id]/@w:id", namespaces=NS):
        try:
            found.append(int(value))
        except ValueError:
            pass
    return max(found, default=0) + 1


def deleted_run(run: etree._Element, change_id: int, stamp: str) -> etree._Element:
    copied = deepcopy(run)
    for node in copied.findall(".//w:t", namespaces=NS):
        node.tag = w("delText")
    deletion = etree.Element(w("del"))
    deletion.set(w("id"), str(change_id))
    deletion.set(w("author"), "Codex")
    deletion.set(w("date"), stamp)
    deletion.append(copied)
    return deletion


def delete_visible_runs(paragraph: etree._Element, change_id: int, stamp: str) -> int:
    """Turn direct active runs into visible Word deletions without touching comments."""
    for child in list(paragraph):
        if child.tag == w("r"):
            if child.find("w:commentReference", namespaces=NS) is not None:
                continue
            paragraph.replace(child, deleted_run(child, change_id, stamp))
            change_id += 1
        elif child.tag == w("ins"):
            # A prior insertion is kept as visible history, but the current
            # revision explicitly deletes the superseded wording.  Nested
            # revisions are avoided because Word does not support them.
            at = paragraph.index(child)
            converted = []
            for run in child.findall("w:r", namespaces=NS):
                if run.find("w:commentReference", namespaces=NS) is None:
                    converted.append(deleted_run(run, change_id, stamp))
                    change_id += 1
            paragraph.remove(child)
            for offset, item in enumerate(converted):
                paragraph.insert(at + offset, item)
    return change_id


def paragraph(style: str | None, content: str, change_id: int, stamp: str, caption=False) -> etree._Element:
    p = etree.Element(w("p"))
    if style:
        ppr = etree.SubElement(p, w("pPr"))
        ps = etree.SubElement(ppr, w("pStyle"))
        ps.set(w("val"), style)
    ins = etree.SubElement(p, w("ins"))
    ins.set(w("id"), str(change_id))
    ins.set(w("author"), "Codex")
    ins.set(w("date"), stamp)
    if caption:
        lead, tail = content.split(" ", 1)
        r1 = etree.SubElement(ins, w("r"))
        rpr = etree.SubElement(r1, w("rPr"))
        etree.SubElement(rpr, w("b"))
        t1 = etree.SubElement(r1, w("t")); t1.text = lead
        r2 = etree.SubElement(ins, w("r"))
        t2 = etree.SubElement(r2, w("t")); t2.text = " " + tail
    else:
        r = etree.SubElement(ins, w("r"))
        t = etree.SubElement(r, w("t"))
        if content.startswith(" ") or content.endswith(" "):
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = content
    return p


def insert_after(body: etree._Element, anchor: etree._Element, additions: list[etree._Element]) -> None:
    at = body.index(anchor) + 1
    for item in additions:
        body.insert(at, item)
        at += 1


def find_paragraph(body: etree._Element, prefix: str) -> etree._Element:
    for p in body.findall("w:p", namespaces=NS):
        if all_text(p).strip().startswith(prefix):
            return p
    raise RuntimeError(f"Could not find paragraph beginning {prefix!r}")


def markdown_methods() -> list[tuple[str | None, str]]:
    raw = METHODS_SOURCE.read_text(encoding="utf-8")
    match = re.search(r"^## Methods\s*$", raw, flags=re.MULTILINE)
    if match is None:
        raise RuntimeError("Approved Methods heading was not found.")
    payload = raw[match.end() :].split("\n## Ce que cette version corrige", 1)[0]
    blocks = [b.strip() for b in re.split(r"\n\s*\n", payload) if b.strip()]
    result: list[tuple[str | None, str]] = []
    for block in blocks:
        if block.startswith("### "):
            result.append(("Heading2", block[4:].strip()))
            continue
        if block.startswith("$$"):
            formula = block.replace("$$", "").strip()
            formula = formula.replace("\\times", "×").replace("\\frac{44}{12}", "44/12")
            formula = formula.replace("_i", "ᵢ").replace("_b", "ᵦ")
            result.append((None, formula))
            continue
        clean = re.sub(r"\*\*(.*?)\*\*", r"\1", block)
        clean = clean.replace("$", "")
        clean = re.sub(r"\s+", " ", clean)
        result.append((None, clean))
    return result


INTRO = {
    "The accelerating impacts": "Climate change increases the need to represent natural systems in economic decision making. The Intergovernmental Panel on Climate Change Special Report on Global Warming of 1.5°C assessed that global warming was likely to reach 1.5°C between 2030 and 2052 if it continued at the then-current rate. Natural capital accounting links ecological functions to measures of wealth, yet major climate-regulation services remain outside conventional national accounts. This omission matters because climate stability depends on biophysical processes that have no market transaction at the point where the service is supplied.",
    "Nature based solutions": "Nature-based solutions can provide mitigation potential of up to about 10 GtCO₂ per year, and forests account for a large share of that potential (Griscom et al., 2017; United Nations Environment Programme and International Union for Conservation of Nature, 2021). Forests therefore link climate mitigation, biodiversity and land stewardship. The physical basis of the forest account, including carbon pools and residence times, is specified in Methods so that the valuation follows a defined annual uptake flow rather than a general statement about forest carbon.",
    "At the global scale": "Forests remove about 3.5 to 4.0 GtC from the atmosphere each year (Pan et al., 2011; Pan et al., 2024). This sink is heterogeneous and dynamic. Uptake has declined in boreal and intact tropical forests, even as temperate and regrowing tropical forests have strengthened in some regions. Global forests also held about 714 GtC in 2025, while more than 200 Mha of forest area has been lost since 1990 (Food and Agriculture Organization of the United Nations, 2025). The annual service is therefore large but vulnerable to a persistent reduction in forest area.",
    "Despite their central role": "Conventional national accounts record exchange values generated by transactions. Climate regulation by forests does not generate such a transaction at the place where the service is supplied, which helps explain its absence from standard measures of national production and wealth. The System of Environmental-Economic Accounting Ecosystem Accounting provides a framework for recording ecosystem services alongside conventional accounts. We value annual uptake with the Global Social Cost of Carbon distribution used in the published blue carbon account. Its mean is US$559.6 per tCO₂ in constant 2015 prices, its median is US$506.7, and its 5th-95th percentile interval is US$218.5-1,015.9 per tCO₂. Methods describes the distribution and its derivation from Ricke et al. (2018).",
    "Recent studies have demonstrated": "The published Blue Carbon Wealth account values annual coastal and oceanic carbon uptake under the same welfare-based price framework (Hilmi et al., 2026). We retain that framework, monetary year, territorial harmonisation and flow interpretation. Green Carbon Wealth measures the corresponding annual forest contribution, and Natural Carbon Wealth combines Green Carbon Wealth and Blue Carbon Wealth after removal of the mangrove overlap. These measures are annual welfare values, not national income, financial claims or estimates of additional mitigation.",
    "Incorporating green natural capital": "Recent work has valued natural land-sink contributions at country level (Thaller et al., 2026), estimated national supply curves for additional forest mitigation (Favero and Austin, 2026), and quantified the policy implications of a weakening ocean sink (Rickels et al., 2024). These studies address distinct questions. No account connects the annual value of the forest and ocean service, the observed erosion of forest capacity, and the distribution of illustrative compensation costs within one harmonised country-level framework.",
    "How large is the global economic value": "Here we build a harmonised account of annual forest and ocean carbon uptake for countries and territories. We ask three linked questions. First, how large is the annual forest service, and how does adding ocean uptake change national carbon wealth and net balances? Second, how much of the forest service is removed each year by reported deforestation? Third, what would it cost to replace that capacity under illustrative abatement prices, and how would domestic and shared allocation rules distribute the burden? Our contribution lies in cross-domain integration, erosion measurement and distributional analysis, rather than in the first valuation of land carbon sinks.",
}


DISCUSSION = [
    (None, "Forest and ocean carbon sinks underpin a large annual climate-regulation service, but the service is unevenly distributed. Green Carbon Wealth reached US$8.16 trillion per year in constant 2015 prices, with a 5th-95th percentile interval of US$3.15-15.49 trillion. It accounted for 77.8% of Natural Carbon Wealth after combination with the published blue account. This result extends the common accounting framework of Hilmi et al. (2026) to forests and keeps the unit of analysis an annual welfare contribution rather than a stock value or revenue stream."),
    (None, "The combined account reveals patterns that a forest or ocean account alone cannot show. Tropical forests supplied 78.6% of forest uptake, whereas ocean processes changed the composition of carbon wealth most strongly in small island developing states. Adding Blue Carbon Wealth increased the share of countries classified as net sinks from 37% to 52%. A net-sink classification does not establish a pathway compatible with climate neutrality. It only compares accounted uptake with fossil-fuel and industrial emissions for the stated reference year."),
    (None, "The erosion result adds a temporal dimension to the account. Reported deforestation removed annual uptake capacity worth US$25.7 billion per year, with a 5th-95th percentile interval of US$9.79-49.58 billion, across 139 reporting units that account for 79% of global Green Carbon Wealth. The annual fraction was 0.40%, but the lost capacity does not return automatically after conversion. At the current rate, the cumulative loss reaches 4.0% over ten years. Erosion was concentrated in developing economies and least developed countries, yet its intensity was not correlated with the size of the current service. Protection priorities cannot therefore be inferred from sink magnitude alone."),
    (None, "The compensation scenarios make the distributional issue explicit. The country that loses a sink is not necessarily the country with the fiscal capacity to replace it. At US$150 per tCO₂, least developed countries would pay US$2.39 billion per year under domestic allocation and US$0.11 billion under allocation proportional to GDP. This contrast reflects a structural gap between the location of global ecosystem benefits and national fiscal capacity. The scenarios do not establish a payment obligation. They show how alternative allocation rules expose that gap."),
    (None, "Our estimates should not be read as a disagreement with Thaller et al. (2026). Their land-sink account uses different flux boundaries, a different carbon-price distribution, a different monetary year and different summary statistics. Each choice changes the estimand. The comparison instead shows why a value for annual climate regulation must identify the physical flow, the damage function and the accounting boundary before country rankings are interpreted."),
    (None, "A large current sink also does not imply a large low-cost potential for additional mitigation. Favero and Austin (2026) estimate policy-induced mitigation relative to a baseline, whereas Green Carbon Wealth values uptake in the reference period. Additional mitigation depends on land availability, baselines, implementation speed and marginal abatement costs. The two measures are complementary, but they answer different policy questions."),
    (None, "Welfare value, additional mitigation and climate finance must remain distinct. The Global Social Cost of Carbon represents avoided marginal climate damages. The compensation prices are illustrative proxies for replacement effort. Neither measure fixes the amount of climate finance owed to a country. Nature-based finance also requires attention to permanence, additionality, leakage, monitoring, rights and governance, as Chausson et al. (2023) emphasise. Standards such as Verra and ART-TREES, and the Reducing Emissions from Deforestation and Forest Degradation framework, address these issues through different institutional rules. Carbon wealth can identify where climate-regulation benefits are generated; it cannot itself create a credit or a finance entitlement."),
    (None, "The account aligns with the System of Environmental-Economic Accounting Ecosystem Accounting by making a non-market ecosystem service visible in a coherent national framework. Its role is descriptive and comparative. It complements broader measures of inclusive wealth and policy analysis, but it does not replace physical forest monitoring, marginal abatement cost analysis or negotiated finance arrangements."),
    ("Heading1", "Limitations"),
    (None, "The forest and blue accounts require several harmonisations. Forest areas from the Global Forest Resources Assessment 2025 are about 8% larger than those underlying Pan et al. (2024), and the ecological-zone allocation classifies some Chinese, United States and Australian subtropical forests as tropical when Pan et al. classify them as temperate. Together these differences raise the global sink by about 13%. The tropical source flux is a gross sink, whereas the temperate and boreal source fluxes are net stock changes. The study also combines fluxes for 2010-2019, forest areas for 2025 and socio-economic variables for 2023."),
    (None, "Erosion estimates cover 139 of 236 forest units and 79% of global Green Carbon Wealth. Missing deforestation reports are treated as missing rather than zero. For 61 units without a known blue component, Natural Carbon Wealth is a lower bound. Forest-area uncertainty is not propagated, and erosion draws are independent of Green Carbon Wealth draws. The erosion measure includes reported deforestation only. It excludes degradation, fire, forest recovery dynamics and sink saturation. Evidence from the Amazon and other forests indicates that climate stress and disturbance can weaken uptake beyond area conversion (Green and Keenan, 2022)."),
    (None, "The compensation prices of US$50, US$150 and US$400 per tCO₂ are illustrative until a final set of Intergovernmental Panel on Climate Change price scenarios is specified and converted to constant 2015 prices. Ocean declines are sensitivity scenarios, not observed losses. Finally, the account excludes other terrestrial ecosystems, including grasslands and savannas, which also regulate climate."),
    ("Heading1", "Conclusion"),
    (None, "Forest carbon sinks provide a large annual service that is concentrated in tropical countries and economically important relative to output in many least developed countries. Ocean uptake changes national sink profiles, whereas reported deforestation persistently erodes the forest service. Replacement costs remain lower than the selected welfare value of the loss, but a domestic allocation places the highest relative burdens where fiscal capacity is weakest. Harmonised carbon-wealth accounts can make these patterns visible while preserving the distinction between ecosystem-service value, mitigation potential and climate finance."),
]


def main() -> None:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with ZipFile(ARTICLE) as source:
        package = {item.filename: source.read(item.filename) for item in source.infolist()}
    root = etree.fromstring(package["word/document.xml"])
    body = root.find("w:body", namespaces=NS)
    assert body is not None
    cid = next_id(root)

    # Introduction: retain each reviewed paragraph in place as a visible deletion,
    # and place the new paragraph directly after it.
    for prefix, replacement in INTRO.items():
        old = find_paragraph(body, prefix)
        cid = delete_visible_runs(old, cid, stamp)
        insert_after(body, old, [paragraph(None, replacement, cid, stamp)])
        cid += 1
    moved = find_paragraph(body, "Carbon sequestration is the transfer")
    cid = delete_visible_runs(moved, cid, stamp)

    # Methods: the brief requires the complete approved replacement.
    methods = find_paragraph(body, "Methods")
    results = find_paragraph(body, "Results")
    old_methods = body.findall("w:p", namespaces=NS)[body.index(methods) + 1 : body.index(results)]
    for old in old_methods:
        cid = delete_visible_runs(old, cid, stamp)
    additions = [paragraph(style, content, cid + offset, stamp) for offset, (style, content) in enumerate(markdown_methods())]
    cid += len(additions)
    # Preserve the coauthor-requested definition and citations in its new Methods location.
    definition = "Carbon sequestration is the transfer of atmospheric CO₂ into long-lived pools in vegetation and soils through photosynthesis (Ontl and Schulte, 2012; Lal, 2008). Carbon residence times range from years in leaves to centuries in woody biomass and mineral-associated soil carbon, but fire, harvest and other disturbances can shorten them (Keller et al., 2024; Trumbore, 1997)."
    additions.insert(8, paragraph(None, definition, cid, stamp)); cid += 1
    insert_after(body, old_methods[-1], additions)

    # Strengthen Results where the original draft was still purely descriptive.
    result_replacements = {
        "Forests generated Green Carbon Wealth": "Forests generated Green Carbon Wealth of US$8.16 trillion per year in constant 2015 prices, with a 5th-95th percentile interval of US$3.15-15.49 trillion. Blue Carbon Wealth added US$2.33 trillion, with an interval of US$0.91-4.30 trillion, so Natural Carbon Wealth reached US$10.49 trillion per year, with an interval of US$4.07-19.66 trillion. Forests supplied 77.8% of the combined account (Table 1). These values represent annual avoided climate damages associated with uptake. They do not value stored forest carbon or a cash flow available to the countries where forests occur.",
        "Tropical forests accounted": "Tropical forests accounted for 78.6% of global uptake, compared with 13.4% for temperate forests and 8.0% for boreal forests. The pattern follows the area-by-rate construction of the account. Tropical forests combine 2,373 Mha with a mean uptake rate of 1.32 ± 0.21 tC ha⁻¹ yr⁻¹, against 616 Mha and 0.87 ± 0.06 in temperate forests and 1,135 Mha and 0.28 ± 0.04 in boreal forests. Tropical dominance therefore reflects both forest extent and the rate supplied by the source data. The national allocation remains sensitive to the forest-area and biome correspondence described in Limitations.",
        "Developing economies supplied": "Developing economies supplied US$4.19 trillion of Green Carbon Wealth, or 51.4% of the global total. Developed economies supplied US$2.26 trillion, or 27.7%, least developed countries supplied US$1.47 trillion, or 18.1%, and small island developing states supplied US$0.23 trillion, or 2.8%. Green Carbon Wealth equalled 8.9% of global gross domestic product, but the median ratio was 75.1% in least developed countries and 2.7% in developed economies. The gap reflects the denominator as much as the numerator. Tropical forest endowment combines with small measured economies, so the same physical service represents a far larger share of recorded output. Green Carbon Wealth and gross domestic product were only moderately correlated (Spearman rho = 0.55), while the group differences were substantial (Kruskal-Wallis H = 48.1, p = 2 × 10⁻¹⁰). The Gini coefficient of 0.856 and the 57.4% share held by the ten largest contributors show that a policy organised around this service concerns a limited group of countries. These ratios indicate the scale of an unpriced service relative to output, not transferable income.",
        "Blue carbon changed the composition": "Blue Carbon Wealth changed the composition of national carbon wealth, but not in the same way across groups. Among the 175 units with a complete composition classification, small island developing states included 33 blue-dominant and 10 green-dominant units. Least developed countries showed the reverse pattern, with 15 green-dominant and one blue-dominant unit. Large exclusive economic zones and low population help explain why the ocean component is prominent in island territories. The composition threshold is descriptive. It does not indicate that one process can substitute for the other.",
        "Adding the ocean component": "Adding the ocean component increased the share of net-sink units from 37% to 52% among 210 units with emissions and sequestration data. The biological carbon pump covers large maritime areas, so it changes the balance particularly for countries with extensive coasts and relatively low emissions. A net-sink classification does not establish a trajectory compatible with climate neutrality. It only compares accounted uptake with fossil-fuel and industrial emissions in 2023. The ten largest emitters accounted for 74% of global emissions, while the ten largest sinks accounted for 39% of accounted sequestration. Only the Russian Federation and Indonesia appeared in both groups. Sink provision and emissions remain geographically distinct.",
        "Reported deforestation averaged": "Reported deforestation averaged 9.70 Mha per year over 2010-2019. It removed 45.9 MtCO₂ per year of future sequestration capacity, equivalent to US$25.7 billion per year of Green Carbon Wealth, with a 5th-95th percentile interval of US$9.79-49.58 billion. This is 0.40% of Green Carbon Wealth among reporting units each year (Table 3). The measure captures a loss of annual capacity, not a release of stored carbon. Once land is converted, the uptake that it would have supplied no longer recurs in subsequent years. The result covers 139 of 236 units, which represent 79% of global Green Carbon Wealth.",
        "Service magnitude and erosion intensity": "Service magnitude and erosion intensity were not correlated (Spearman rho = −0.09, p = 0.36). Countries that provide a large service are therefore not systematically the countries with the most rapid proportional erosion. This lack of association is policy-relevant because sink magnitude alone cannot identify the places where retention of capacity is most urgent. Reported deforestation declined from 15.8 Mha per year in the 1990s to 8.5 Mha per year in the latest period. The Theil-Sen slope was −272 kha per year per year and the Mann-Kendall test gave p = 0.03. Africa lost 3.3-3.6 Mha per year and South America lost up to 7.3 Mha per year during the 1990s. The decline does not remove the cumulative and irreversible effect of continued conversion. Missing FRA reports remain missing rather than zero.",
    }
    for prefix, replacement in result_replacements.items():
        old = find_paragraph(body, prefix)
        cid = delete_visible_runs(old, cid, stamp)
        insert_after(body, old, [paragraph(None, replacement, cid, stamp)])
        cid += 1

    # Bold caption labels, requested in the prior review, while retaining old captions visibly.
    for label in ("Table 1.", "Table 2.", "Table 3.", "Table 4.", "Figure 1.", "Figure 2.", "Figure 3.", "Figure 4."):
        old = find_paragraph(body, label)
        content = text(old).strip()
        cid = delete_visible_runs(old, cid, stamp)
        insert_after(body, old, [paragraph(None, content, cid, stamp, caption=True)])
        cid += 1

    # Discussion and limitations: full replacement required by the brief, but each
    # original paragraph remains visible as a local tracked deletion.
    heading = find_paragraph(body, "Discussion and limitations")
    refs = find_paragraph(body, "References")
    old_discussion = body.findall("w:p", namespaces=NS)[body.index(heading) : body.index(refs)]
    for old in old_discussion:
        cid = delete_visible_runs(old, cid, stamp)
    additions = [paragraph(style, content, cid + offset, stamp) for offset, (style, content) in enumerate(DISCUSSION)]
    cid += len(additions)
    insert_after(body, old_discussion[-1], additions)

    # Correct the SEEA entry and add the finance-comparison reference without
    # removing other coauthor-provided bibliography items.
    seea = find_paragraph(body, "United Nations. (2025). System")
    cid = delete_visible_runs(seea, cid, stamp)
    insert_after(body, seea, [paragraph("ListParagraph", "United Nations, European Union, Food and Agriculture Organization of the United Nations, International Monetary Fund, Organisation for Economic Co-operation and Development, and World Bank. (2021). System of Environmental-Economic Accounting Ecosystem Accounting. United Nations.", cid, stamp)])
    cid += 1
    references = find_paragraph(body, "References")
    insert_after(body, references, [paragraph("ListParagraph", "Austin, K. G. et al. (2025). Targeting climate finance for global forests. Nature Communications, 16, 6443. https://doi.org/10.1038/s41467-025-61657-6", cid, stamp)])
    cid += 1

    # Some legacy revisions place their text in ordinary runs outside the
    # original discussion range.  The brief explicitly retires these values.
    for old in body.findall("w:p", namespaces=NS):
        if any(value in text(old) for value in ("573.8", "8.1 trillion", "3.86")):
            cid = delete_visible_runs(old, cid, stamp)

    package["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    output = ARTICLE.with_name("Article_Green_Carbon.revised_2026-09-21.docx")
    with ZipFile(output, "w", ZIP_DEFLATED) as target:
        for name, payload in package.items():
            target.writestr(name, payload)
    print(f"Applied prompt revision with tracked insertions to {output.name}. Last change id {cid}.")


if __name__ == "__main__":
    main()
