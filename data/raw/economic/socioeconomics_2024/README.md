# 2024 socioeconomic source extracts

The GCB workbook and 2024 WDI files were retrieved on 2026-10-20; the 2023 and 2022 WDI fallback files were retrieved on 2026-10-28. These public-source files support a separate analysis with 2024 as its reference year. They do not overwrite the 2023 socioeconomic values embedded in the existing BCW reference tables.

## Files

- `national_fossil_carbon_emissions_GCB2025.xlsx` - official Global Carbon Budget 2025 national fossil carbon emissions workbook, `Territorial Emissions` sheet. Values are MtC/year; its note specifies 3.664 MtCO2 per MtC. The national series includes fossil-fuel combustion/oxidation and cement production and excludes land-use change. The workbook includes 2023 and 2024 country/territory rows and aggregate rows.
- `wb_population_2024.json`, `wb_population_2023.json`, `wb_population_2022.json` - World Bank WDI API `SP.POP.TOTL` for each year.
- `wb_gdp_constant_2015_2024.json`, `wb_gdp_constant_2015_2023.json`, `wb_gdp_constant_2015_2022.json` - World Bank WDI API `NY.GDP.MKTP.KD` for each year, constant 2015 US dollars.

The World Bank API payloads record `lastupdated` as 2026-10-08. Population is a midyear estimate with source inputs including UN WPP, national statistical offices and Eurostat. WPP 2024's published time split is estimates for 1950-2023 and projections for 2024-2100, so the 2024 population series is not described as a fully observed count. GDP coverage and status vary by economy. For population and GDP independently, the analysis selects the latest non-missing value from 2024, then 2023, then 2022; the selected source year is kept for each unit.

## Sources and attribution

- Global Carbon Project, [The Latest GCB Data (2025)](https://globalcarbonbudget.org/datahub/the-latest-gcb-data-2025/). The GCB page requests citation of Friedlingstein et al. (2025) and notes that co-authorship may need to be considered when data are essential to a study or an important result depends on them.
- World Bank, [Population, total (SP.POP.TOTL)](https://data.worldbank.org/indicator/SP.POP.TOTL), CC BY 4.0.
- World Bank, [GDP (constant 2015 US$) (NY.GDP.MKTP.KD)](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD), CC BY 4.0.

Extraction and ISO3 crosswalk: `code/scripts/build_socioeconomic_2024.py`. The derived unit-level table is `data/derived/socioeconomic_2024_by_unit.csv`; coverage and cross-source checks are in `results/validation/socioeconomic_2024_coverage_audit.json` and the adjacent CSV audit files.
