"""Paths, constants and documented modelling parameters of the GCW pipeline.

Every subjective parameter below refers to an entry of MYCHOICES.md (C#).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- Directories -----------------------------------------------------------
DATA = ROOT / "data_source"
RAW = DATA / "raw"
REFERENCE = DATA / "reference"
SUMMARY = DATA / "summary"
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
VALIDATION = OUTPUT / "validation"

# --- Raw inputs ------------------------------------------------------------
FRA_ZIP = RAW / "fra" / "fra2025_bulk_WO.zip"
FRA_VARIABLE = "FRA_Years_variables/{name}_2026-09-16.csv"
FAOSTAT_FOREST_ZIP = RAW / "faostat" / "Emissions_Land_Use_Forests_E_All_Data_(Normalized).zip"
FAOSTAT_FOREST_CSV = "Emissions_Land_Use_Forests_E_All_Data_(Normalized).csv"
PAN_TABLE1_HTML = RAW / "pan" / "nature_extended_data_tables" / "Table1_main.html"
GEZ_SHP = "/vsizip/" + (RAW / "gez" / "gez2010.zip").as_posix() + "/gez_2010_wgs84.shp"
BOUNDARIES_SHP = RAW / "boundaries" / "EEZ_land_union_v4_202410.shp"
FOREST_MASK_TIF = RAW / "forest_mask" / "JRC_GFC2020_V4_overview_x256.tif"
BCW_COUNTRY_CSV = RAW / "bcw" / "output" / "country_level_bcw.csv"
BCW_DRAWS_NPZ = RAW / "bcw" / "output" / "draws.npz"
PAN_BIOME_AREAS_CSV = REFERENCE / "pan_biome_areas.csv"
TERRITORY_CROSSWALK_CSV = REFERENCE / "territory_crosswalk.csv"

# --- Accounting units (C12) --------------------------------------------------
# FAO/FRA "China" (M49 159) includes Taiwan, Hong Kong SAR and Macao SAR.
UNIT_NAME_OVERRIDES = {"CHN": "China (incl. Taiwan, Hong Kong SAR and Macao SAR)"}
# Boundary polygons whose land belongs to another FRA unit when computing biome shares.
RASTER_CODE_ALIASES = {"TWN": "CHN", "HKG": "CHN", "MAC": "CHN"}

# --- Physical constants ----------------------------------------------------
CARBON_TO_CO2 = 44.0 / 12.0

# --- Monte Carlo (C8) --------------------------------------------------------
# B and the GSCC draws are taken from BCW so that GCW and BCW share the same worlds.
SEED = 20260916

# --- Route B: harmonised biomes x Pan rates (C1, C4, C17) ----------------------
PAN_PERIOD = "2010–2019"  # decade of Pan et al. (2024) Table 1 (C4)
AREA_YEAR = "2025"  # FRA 2025 reporting year used for country forest areas
# Pan biome -> Pan Table 1 row giving its flux (the tropical row aggregates intact and regrowth, C17).
PAN_BIOME_ROWS = {"tropical": "All tropical forests", "temperate": "Temperate forest", "boreal": "Boreal forest"}
# Pan biome -> GEZ biomes it contains: Pan includes subtropical forests in its tropical set (C17).
PAN_BIOME_MEMBERS = {"tropical": ["tropical", "subtropical"], "temperate": ["temperate"], "boreal": ["boreal"]}
# Pan areas used as rate denominators: mean of the 2010 and 2020 areas of the flux decade (C17).
PAN_AREA_YEARS = ["area_2010_mha", "area_2020_mha"]

# --- Biome shares (C2) -------------------------------------------------------
BIOMES = ["tropical", "subtropical", "temperate", "boreal"]
# First digit of the FAO GEZ 2010 code -> biome. Polar forest pixels are assigned to boreal.
GEZ_DOMAIN_TO_BIOME = {1: "tropical", 2: "subtropical", 3: "temperate", 4: "boreal", 5: "boreal"}
RASTER_STRIPE_ROWS = 400  # rows processed at once; keeps memory low

# --- Route A: FAOSTAT net flux (C1, C4) ---------------------------------------
FAOSTAT_ITEM = "Forestland"
FAOSTAT_ELEMENT = "Net emissions/removals (CO2) (Forest land)"
FAOSTAT_SOURCE = "FAO TIER 1"
FAOSTAT_PERIOD = (2015, 2024)
