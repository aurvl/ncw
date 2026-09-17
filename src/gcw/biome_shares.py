"""Q: Which share of each country's forest lies in each biome?

Outputs (data_source/summary/):
- gez_area_by_country.csv : forest and land km2 per country x GEZ zone
                            (GEZ 2010 x EEZ_land_union v4 x JRC GFC2020 forest mask)
- biome_shares_fra.csv    : shares reported by countries in FRA 2025 (control, C2)
- biome_shares.csv        : shares used by the pipeline, with their source

Polygons are burnt part by part and rasters read in stripes so that memory use stays low.
Intermediate rasters: data_source/summary/rasters/{countries,gez}.tif
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pyogrio.raw
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window
from shapely.geometry import Polygon

from .config import (
    BIOMES, BOUNDARIES_SHP, FOREST_MASK_TIF, GEZ_DOMAIN_TO_BIOME, GEZ_SHP, RASTER_CODE_ALIASES, RASTER_STRIPE_ROWS,
    SUMMARY,
)
from .validation import read_fra_variable, write_table

EARTH_RADIUS_KM = 6371.0088
COUNTRY_POLYGON_TYPES = {"Union EEZ and country", "Landlocked country"}


def _wkb_polygons(wkb: bytes):
    """Yield (exterior, holes) numpy rings from a 2D little-endian (Multi)Polygon WKB.

    Very large GEZ features cannot be converted to a single shapely object with the memory
    available, so they are split into polygon parts without copying the whole geometry.
    """
    buffer = memoryview(wkb)

    def read_polygon(offset: int):
        n_rings = int(np.frombuffer(buffer, "<u4", 1, offset)[0])
        offset += 4
        rings = []
        for _ in range(n_rings):
            n_points = int(np.frombuffer(buffer, "<u4", 1, offset)[0])
            offset += 4
            rings.append(np.frombuffer(buffer, "<f8", 2 * n_points, offset).reshape(-1, 2))
            offset += 16 * n_points
        return rings, offset

    geometry_type = int(np.frombuffer(buffer, "<u4", 1, 1)[0])
    if geometry_type == 3:
        rings, _ = read_polygon(5)
        yield rings[0], rings[1:]
    elif geometry_type == 6:
        n_parts = int(np.frombuffer(buffer, "<u4", 1, 5)[0])
        offset = 9
        for _ in range(n_parts):
            rings, offset = read_polygon(offset + 5)
            yield rings[0], rings[1:]
    else:
        raise ValueError(f"Unsupported WKB geometry type {geometry_type}")


def burn_vector(path: str, value_of, fields: list[str], out_path, template, dtype: str) -> None:
    """Rasterise polygons part by part onto the template grid, writing directly to disk."""
    profile = template.profile | {"dtype": dtype, "nodata": 0, "compress": "deflate", "tiled": True,
                                  "blockxsize": 512, "blockysize": 512}
    with rasterio.open(out_path, "w", **profile) as out:
        for row in range(0, template.height, RASTER_STRIPE_ROWS):
            n_rows = min(RASTER_STRIPE_ROWS, template.height - row)
            out.write(np.zeros((n_rows, template.width), dtype=dtype), 1, window=Window(0, row, template.width, n_rows))
    info = pyogrio.read_info(path)
    with rasterio.open(out_path, "r+") as out:
        for index in range(info["features"]):
            meta, _, geometry, values = pyogrio.raw.read(path, columns=fields, skip_features=index, max_features=1)
            value = value_of(dict(zip(meta["fields"], (v[0] for v in values))))  # fields come back in file order
            if not value or geometry[0] is None:
                continue
            for exterior, holes in _wkb_polygons(geometry[0]):
                west, south = exterior.min(axis=0)
                east, north = exterior.max(axis=0)
                # Integer pixel window covering the part, computed explicitly (Window rounding APIs differ across rasterio versions).
                col0 = max(int(np.floor((west - out.transform.c) / out.transform.a)), 0)
                row0 = max(int(np.floor((north - out.transform.f) / out.transform.e)), 0)
                col1 = min(int(np.ceil((east - out.transform.c) / out.transform.a)), out.width)
                row1 = min(int(np.ceil((south - out.transform.f) / out.transform.e)), out.height)
                if col1 - col0 < 1 or row1 - row0 < 1:
                    continue
                window = Window(col0, row0, col1 - col0, row1 - row0)
                burned = rasterize([(Polygon(exterior, holes), 1)], (int(window.height), int(window.width)),
                                   transform=out.window_transform(window), fill=0, dtype="uint8")
                if not burned.any():
                    continue
                current = out.read(1, window=window)
                current[burned == 1] = value
                out.write(current, 1, window=window)


def compute_gez_area_by_country() -> pd.DataFrame:
    fields = ["POL_TYPE", "ISO_TER1", "ISO_SOV1"]
    meta, _, _, values = pyogrio.raw.read(BOUNDARIES_SHP, columns=fields, read_geometry=False)
    records = [dict(zip(meta["fields"], row)) for row in zip(*values)]
    codes = sorted({code for record in records if (code := _country_code(record))})
    index_of = {code: i + 1 for i, code in enumerate(codes)}

    country_tif = SUMMARY / "rasters" / "countries.tif"
    gez_tif = SUMMARY / "rasters" / "gez.tif"
    country_tif.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(FOREST_MASK_TIF) as template:
        print("    burning country polygons")
        burn_vector(str(BOUNDARIES_SHP), lambda p: index_of.get(_country_code(p)), fields, country_tif, template, "uint16")
        print("    burning GEZ polygons")
        burn_vector(GEZ_SHP, lambda p: int(p["gez_code"]) if p["gez_code"] else None, ["gez_code"], gez_tif, template, "uint8")

    n_keys = (len(codes) + 1) * 100
    forest_km2 = np.zeros(n_keys)
    land_km2 = np.zeros(n_keys)
    with rasterio.open(FOREST_MASK_TIF) as mask, rasterio.open(country_tif) as country_src, rasterio.open(gez_tif) as gez_src:
        dlon, dlat = mask.transform.a, -mask.transform.e
        for row in range(0, mask.height, RASTER_STRIPE_ROWS):
            n_rows = min(RASTER_STRIPE_ROWS, mask.height - row)
            window = Window(0, row, mask.width, n_rows)
            country = country_src.read(1, window=window)
            gez = gez_src.read(1, window=window)
            forest = mask.read(1, window=window)
            north = mask.window_transform(window).f
            latitudes = north - (np.arange(n_rows) + 0.5) * dlat
            cell_km2 = (EARTH_RADIUS_KM**2) * np.radians(dlat) * np.radians(dlon) * np.cos(np.radians(latitudes))
            cell_area = np.broadcast_to(cell_km2[:, None], country.shape)
            keys = country.astype(np.int32) * 100 + gez
            valid = (country > 0) & (gez > 0)
            land_km2 += np.bincount(keys[valid], weights=cell_area[valid], minlength=n_keys)
            forested = valid & (forest == 1)
            forest_km2 += np.bincount(keys[forested], weights=cell_area[forested], minlength=n_keys)

    rows = []
    for code, i in index_of.items():
        for gez_code in range(1, 100):
            key = i * 100 + gez_code
            if land_km2[key] > 0:
                rows.append({"iso3": code, "gez_code": gez_code, "forest_km2": forest_km2[key], "land_km2": land_km2[key]})
    if not rows:
        raise RuntimeError("No country x GEZ overlap found: check the boundary and GEZ rasters.")
    table = pd.DataFrame(rows)
    table["biome"] = table["gez_code"].floordiv(10).map(GEZ_DOMAIN_TO_BIOME)  # water (90) -> NaN
    return table


def _country_code(properties: dict) -> str | None:
    """Sovereign-level ISO3 of a land polygon; disputed and joint areas are skipped."""
    if properties["POL_TYPE"] not in COUNTRY_POLYGON_TYPES:
        return None
    code = properties["ISO_TER1"] or properties["ISO_SOV1"]
    return RASTER_CODE_ALIASES.get(code, code)


def shares_from_gez(gez_area: pd.DataFrame) -> pd.DataFrame:
    """Forest-weighted biome shares; land-weighted when the coarse mask finds no forest."""
    zoned = gez_area.dropna(subset=["biome"])
    by_biome = zoned.groupby(["iso3", "biome"], as_index=False)[["forest_km2", "land_km2"]].sum()
    totals = by_biome.groupby("iso3")[["forest_km2", "land_km2"]].transform("sum")
    by_biome["share_forest"] = by_biome["forest_km2"] / totals["forest_km2"]
    by_biome["share_land"] = by_biome["land_km2"] / totals["land_km2"]
    has_forest = totals["forest_km2"] > 0
    by_biome["share"] = np.where(has_forest, by_biome["share_forest"], by_biome["share_land"])
    by_biome["source"] = np.where(has_forest, "gez_forest_mask", "gez_land")
    return by_biome[["iso3", "biome", "share", "source", "forest_km2", "land_km2"]]


def shares_from_fra() -> pd.DataFrame:
    fra = read_fra_variable("1a_forestArea")[["iso3", *BIOMES]]
    long = fra.melt(id_vars="iso3", value_vars=BIOMES, var_name="biome", value_name="percent")
    total = long.groupby("iso3")["percent"].transform("sum")
    long["share"] = long["percent"] / total
    long["source"] = "fra_reported"
    return long.loc[total > 0, ["iso3", "biome", "share", "source"]]


def select_shares(gez: pd.DataFrame, fra: pd.DataFrame) -> pd.DataFrame:
    """GEZ x forest mask first (C2); FRA shares for countries the rasters do not resolve."""
    selected = gez.loc[gez["source"] == "gez_forest_mask", ["iso3", "biome", "share", "source"]]
    missing = fra.loc[~fra["iso3"].isin(selected["iso3"])]
    remaining = gez.loc[~gez["iso3"].isin(selected["iso3"]) & ~gez["iso3"].isin(missing["iso3"]), ["iso3", "biome", "share", "source"]]
    shares = pd.concat([selected, missing, remaining], ignore_index=True)
    shares = shares.loc[shares["share"] > 0]
    return shares.sort_values(["iso3", "biome"]).reset_index(drop=True)


def run(recompute_rasters: bool = False) -> pd.DataFrame:
    gez_path = SUMMARY / "gez_area_by_country.csv"
    if recompute_rasters or not gez_path.exists():
        print("  rasterising GEZ x boundaries x forest mask (slow step)")
        write_table(compute_gez_area_by_country(), gez_path)
    gez = shares_from_gez(pd.read_csv(gez_path))
    fra = shares_from_fra()
    write_table(fra, SUMMARY / "biome_shares_fra.csv")
    shares = select_shares(gez, fra)
    write_table(shares, SUMMARY / "biome_shares.csv")
    return shares
