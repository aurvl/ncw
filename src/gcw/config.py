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
SUBTROPICAL_RATE_CSV = REFERENCE / "subtropical_rate.csv"

# --- Physical constants ----------------------------------------------------
CARBON_TO_CO2 = 44.0 / 12.0

# --- Monte Carlo (C8) --------------------------------------------------------
# B and the GSCC draws are taken from BCW so that GCW and BCW share the same worlds.
SEED = 20260916

# --- Route B: Pan area x rate (C1, C3, C4, C9) ------------------------------
PAN_PERIOD = "2010–2019"  # decade of Pan et al. (2024) Table 1 (C4)
AREA_YEAR = "2025"  # FRA 2025 reporting year used for areas, as in the current supplement
BIOMES = ["tropical", "subtropical", "temperate", "boreal"]
FOREST_TYPES = ["nrf", "planted"]
# Pan Table 1 row feeding each (biome, forest type); subtropical comes from SUBTROPICAL_RATE_CSV (C3).
# Tropical NRF -> intact and planted -> regrowth reproduces the current supplement (C9, open).
PAN_ROW_FOR = {
    ("tropical", "nrf"): "Tropical intact forest",
    ("tropical", "planted"): "Tropical regrowth forest",
    ("temperate", "nrf"): "Temperate forest",
    ("temperate", "planted"): "Temperate forest",
    ("boreal", "nrf"): "Boreal forest",
    ("boreal", "planted"): "Boreal forest",
}
# Pan rates apply to a whole biome except in the tropics, where NRF and planted areas are separated.
BIOMES_WITH_TYPE_SPLIT = {"tropical"}

# --- Biome shares (C2) -------------------------------------------------------
# First digit of the FAO GEZ 2010 code -> biome. Polar forest pixels are assigned to boreal.
GEZ_DOMAIN_TO_BIOME = {1: "tropical", 2: "subtropical", 3: "temperate", 4: "boreal", 5: "boreal"}
RASTER_STRIPE_ROWS = 400  # rows processed at once; keeps memory low

# --- Route A: FAOSTAT net flux (C1, C4) ---------------------------------------
FAOSTAT_ITEM = "Forestland"
FAOSTAT_ELEMENT = "Net emissions/removals (CO2) (Forest land)"
FAOSTAT_SOURCE = "FAO TIER 1"
FAOSTAT_PERIOD = (2015, 2024)
