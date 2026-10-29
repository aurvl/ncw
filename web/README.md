# Natural Carbon Wealth explorer

Interactive web page for the study's results: a globe coloured by Natural Carbon Wealth (NCW) and its
green (GCW) and blue (BCW) components, with a full account card for every country or territory.
English and French, light and dark themes.

The site is static. It shows only repository outputs; no external data are loaded at runtime.

## Run

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm run build      # static site in web/dist/
npm run preview    # serve the built site
```

## Refresh the data

The JSON and GeoJSON files in `public/data/` are generated from the repository outputs. Rebuild them after
the accounts change:

```bash
python web/scripts/build_web_data.py   # from the repository root
```

| Output | Source |
|---|---|
| `units.json` | `results/validation/country_level_results_master.csv`, plus `gcw_gdp_2024_pct` from `results/tables/manuscript/Supplementary_country_level_accounts_2024.csv` |
| `global.json` | `results/tables/manuscript/Table1_global_carbon_wealth.csv` (the script checks that unit-level GCW sums to it) |
| `aggregates.json` | Sums of unit means by region and by economic group; checked against `Supplementary_region_profiles_2024.csv`, Table 2 and `Supplementary_Figure4_finance_allocations_by_group.csv`; medians and green/mixed/blue counts copied from those tables |
| `land.geojson` | `data/raw/geospatial/boundaries/ne_10m_admin_0_map_units.zip`, simplified |
| `eez.geojson` | `data/raw/geospatial/boundaries/EEZ_land_union_v4_202410.shp`, simplified |

Values are copied as stored and only scaled for display, with one researcher rule: NCW = GCW + BCW, a missing
component counting as zero. For the 68 units with a single account, NCW (mean and P05/P95) therefore equals that
account, and the card says which component is missing. With this rule, unit-level NCW sums to the additive global
NCW of Table 1 (checked by the script). The master table itself keeps NCW complete-case.

Other missing values stay "No data" and are never shown as zero; reported zeros use the red hatching of the paper figures.

## Publish with GitHub Pages

`.github/workflows/pages.yml` builds `web/` and deploys `web/dist`. Enable it once in the repository settings:
**Settings → Pages → Build and deployment → Source: GitHub Actions**. The workflow then runs on every push to `main`
that touches `web/`, or manually from the Actions tab. The site is served at `https://aurvl.github.io/ncw/`.

## Structure

```text
web/
├── scripts/build_web_data.py   data export from repository outputs
├── public/data/                generated data and boundaries
└── src/
    ├── App.tsx                 page state (landing / explorer), theme, selection
    ├── pages/Landing.tsx       title, authors, short description, global totals
    ├── components/             Globe (MapLibre), CountryPanel, Legend, LayerSwitch, Search, ...
    ├── lib/                    data loading, layer classes, panel fields, number formatting
    ├── i18n/                   en.json, fr.json
    └── styles/                 tokens.css (themes), app.css
```

## Stack

Vite, React and TypeScript; MapLibre GL JS (globe projection, no tile server); Motion for animations;
i18next for languages; Inter and Source Serif 4, self-hosted.

## Editorial note

The landing description, the French translations of the README methods text and the field labels are drafts
to be reviewed by the authors. Country names come from the source table and are shown in English in both languages.
