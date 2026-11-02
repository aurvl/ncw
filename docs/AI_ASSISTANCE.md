# AI assistance and research provenance

**Working disclosure record, 2 November 2026.** This document describes how generative AI assisted the research code, results preparation, and public web explorer. It does not replace the article's Methods, a journal-specific AI declaration, the executable pipeline, or author review of the final manuscript.

## Responsibilities and scope

The human researchers defined the research questions and accounting scope, selected data and methods, decided which results to report, interpreted the findings, and retain responsibility for the manuscript. Codex assisted with source existence checks, code and notebook changes, data processing, numerical and document audits, tables, figures and explanations. The first version of the interactive web explorer was developed with Claude; later site work included Codex-assisted data presentation.

This document was reconstructed from dated local AI-use records, project decision records, repository history, current code, and saved outputs.

## How AI was used

| Workstream | Researcher direction and AI assistance | Versioned evidence and checks |
| --- | --- | --- |
| Forest account | The researchers specified annual additions to living forest biomass as the account's physical scope. Codex compared existing definitions, helped implement Gibbs/GFW gross-removal rates across four climate domains, and checked mangrove exclusion from the rate calculation. | [Pipeline](PIPELINE.md), [source register](DATA_SOURCES.md), `code/src/gcw/`, `code/scripts/rebuild_gibbs_gfw_pipeline.py`, and generated forest-account tables. |
| Mangrove overlap and BCW | Following the researchers' selected area hierarchy and accounting rule, Codex audited FRA reports, implemented documented Forest/OWL treatment, updated the mangrove component of BCW, and checked reported zero against missing values. | [Pipeline, sections 2 and 4](PIPELINE.md), `data/derived/fra_mangrove_forest_overlap_2025.csv`, `data/derived/bcw_mangrove_gmw_area_replacement.csv`, and `code/src/gcw/ncw.py`. |
| Forest-capacity loss and restoration scenario | The researchers specified a separate deforestation-capacity measure and requested reconstruction of the Busch et al. cell inputs. Codex implemented the calculations, processed the available country source files, and joined the reconstructed costs to positive FRA-loss targets. | [Pipeline, sections 7 and 9](PIPELINE.md), `code/scripts/rebuild_deforestation_capacity.py`, `code/scripts/rebuild_busch_pipeline.py`, and generated coverage and cost tables. |
| Spatial and finance analyses | Researcher implemented spatial econometric models and defined analysed relationships. Codex implemented models in code and the illustrative 2% GCW allocation specified by the researcher. The researcher then selected the minimum-BIC models under Queen contiguity for manuscript reporting and supplied the intended Figure 5 comparison. | `code/notebooks/06_climate_finance.ipynb`, `code/notebooks/07_spatial_econometrics.qmd`, `code/notebooks/08_paper_figures.ipynb`, and `results/tables/manuscript/`. |
| Manuscript and supplementary material | Codex checked values against saved outputs, updated tables, figures, captions, and prepared inventories files in research results and limits.  | The repository supplies the underlying code, figures, tables, and bilingual pipeline documentation. Scientific claims and tracked edits require author approval. |
| Web explorer | Claude assisted with the creation of the interactive site. Codex assisted with selected later display and discoverability tasks, including sitemap and Search Console setup. | `web/`, [web README](../web/README.md), and repository history. Search Console submission is not evidence of search indexing. |

AI-assisted code was run and checked in several stages. Recorded checks include source-file counts and hashes, pipeline validation outputs, saved-draw reconciliation, selected independent recalculations, notebook execution, figure inspection, and Word revision/layout inspection. Some runs reused prepared `data/derived/` products; a standard `main.py` run is not the same as re-downloading and processing all heavy raw sources. The relevant command and input boundary for each stage are documented in the [repository README](../README.md) and the [pipeline](PIPELINE.md). A completed technical check does not by itself validate an ecological assumption or a scientific interpretation.

## Prompt and decision trace

The exact wording of every historical prompt is not recoverable from the retained project logs, so none is presented here as a quotation. For material tasks, the logs preserve the **researcher request, AI action, output, checks, and unresolved decisions**. Examples of recorded instructions, paraphrased here, are:

1. Recalculate GCW for the researcher-defined forest-biomass service and compare candidate source definitions.
2. Apply the selected mangrove-area hierarchy, distinguish reported zeros from missing data, and document which FRA mangrove areas are demonstrably in Forest rather than OWL.
3. Process all available Busch country input files before matching their modeled restoration supply to FRA-loss targets.
4. Report the selected Queen-contiguity model with minimum BIC and place revised tables and figures at their existing narrative locations in the tracked manuscript.
5. Build the researcher-specified three-panel Figure 5 and verify its legibility before versioning.

These entries document **instructions and execution**, not AI ownership of the underlying scientific choices.
