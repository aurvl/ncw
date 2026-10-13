# Data sources, licences and citations

Raw files in `data_source/raw/` are stored exactly as downloaded (git attribute `-text`). `data_source/metadata/source_registry.csv` records URL, version, access date and licence; `data_source/metadata/raw_checksums.csv` records SHA-256 checksums (`python scripts/checksum_raw_sources.py`).

| Folder | Source | Used for | Licence | Cite |
|---|---|---|---|---|
| `fra/` | FAO, Global Forest Resources Assessment 2025, bulk download (world) | Forest, mangrove, NRF, planted and primary areas; climatic-domain shares; M49 codes | CC BY 4.0 | FAO (2025). *Global Forest Resources Assessment 2025*. Rome. |
| `faostat/` | FAOSTAT, *Emissions from forests* (Global, National – Annual), bulk file dated 2026-07-06 | Route A net forest flux | CC BY 4.0 | FAO (2026). FAOSTAT: Emissions from forests. |
| `gez/` | FAO, Global Ecological Zones, second edition (2010) | Biome of each forest pixel | CC BY 4.0 | FAO (2012). *Global ecological zones for FAO forest reporting: 2010 update*. |
| `boundaries/` | Flanders Marine Institute, Union of world country boundaries and EEZ v4 (2024-10), as used by BCW | Country polygons | CC BY 4.0 (see `LICENSE_EEZ_LAND_v4.txt`; not for legal use) | Flanders Marine Institute (2024). Union of the ESRI Country shapefile and the Exclusive Economic Zones (version 4). marineregions.org |
| `boundaries/ne_50m_admin_0_countries.zip` | Natural Earth 1:50m Admin 0 countries | Land polygons for figure maps (notebook 03) | Public domain | Made with Natural Earth. naturalearthdata.com |
| `forest_mask/` | European Commission JRC, Global Forest Cover 2020 V4, internal overview ×256 (~2.3 km) of the single COG | Forest mask for biome shares | Free of charge, without restriction of use (Copernicus); citation required | Bourgoin, C. et al. (2025). Global map of forest cover 2020. European Commission, Joint Research Centre. http://data.europa.eu/89h/8c561543-31df-4e1b-9994-e529afecaf54 |
| `gfw_gibbs_2025/gross_removals/` | Gibbs et al. (2025), published 2001-2023 gross-removals GeoTIFF tiles | Gross additions to above- and below-ground living forest biomass, aggregated into four FAO GEZ biomes | CC0 1.0 | Gibbs, D. A. et al. (2025). Revised and updated geospatial monitoring of 21st century forest carbon fluxes. *Earth System Science Data*, 17, 1217-1242. https://doi.org/10.5194/essd-17-1217-2025; data: https://doi.org/10.7910/DVN/V2ISRH; [WRI model documentation](https://github.com/wri/carbon-budget) |
| `pan/` | Pan et al. (2024), Table 1 (HTML) and Extended Data Tables 1 and 3 (images) | Biome fluxes, biome areas, published rates per area | © Springer Nature; numerical values cited as facts | Pan, Y. et al. (2024). The enduring world forest carbon sink. *Nature* 631, 563–569. https://doi.org/10.1038/s41586-024-07602-x |
| `bcw/` | BCW release, commit 29ede5b (`output/country_level_bcw.csv`, `output/draws.npz`) | BCW values and draws, GSCC draws, population, GDP, groups | CC BY 4.0 (`LICENSE-CC-BY-4.0`) | See `bcw/CITATION.cff` |

## Derived Gibbs/GFW rates

Place the 272 GeoTIFF tiles from the published 2001-2023 gross-removals dataset in `data_source/raw/gfw_gibbs_2025/gross_removals/`. The compressed source set is approximately 37 GB. The selected 30 m gross-removal layer is positive by the WRI sign convention and stores cumulative Mg CO2/ha values over the model period. The pipeline converts each value to a 23-year mean annual tC/ha/yr rate, weights pixels by geographic cell area, and averages them within the four FAO GEZ biomes. Spatial dispersion is reported as a deterministic mean ± one spatial standard deviation sensitivity, not as probabilistic uncertainty. The newer 2001-2025 model release is not substituted for the 2001-2023 publication dataset.

## Transcribed values

`data_source/reference/pan_biome_areas.csv` holds values transcribed from Pan et al. (2024) Extended Data Tables 1 and 3. They support comparison with the previous calculation; they are no longer inputs to the main rate pipeline.

## Controlled references

| File | Content |
|---|---|
| `reference/pan_biome_areas.csv` | Pan biome areas and published rates (transcribed) |
| `reference/territory_crosswalk.csv` | BCW territory → accounting unit, with decision, author and date (C12) |

The Gibbs/GFW raster processing writes `summary/gfw_gibbs_biome_rates.csv` and per-tile audit rows to `summary/gfw_gibbs_tile_rates.csv`.

## Not available

The Pan et al. (2024) replication spreadsheets (US Forest Service archive RDS-2023-0051) could not be downloaded (access blocked); their tables are retained only for comparison with the previous calculation. The published Gibbs/GFW raster tiles have not been staged locally yet, so no country or global rates have been recomputed.
