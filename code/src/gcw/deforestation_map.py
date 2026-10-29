"""Allocate FRA-reported deforestation across biomes using UMD loss locations.

FRA supplies the accounting-unit total annual loss rate. UMD Hansen GFC v1.13
supplies the spatial pattern used only to distribute that total among biomes.
Only 10 x 10 degree lossyear tiles intersecting the target land/ecozone polygons
are downloaded. The downloaded rasters are local inputs, not repository data.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import pyogrio
import rasterio
import requests
import shapely
from rasterio.features import rasterize
from rasterio.windows import Window

from .config import (
    BOUNDARIES_SHP,
    GEZ_DOMAIN_TO_BIOME,
    GEZ_SHP,
    RASTER_CODE_ALIASES,
    RAW,
)

UMD_VERSION = "GFC-2025-v1.13"
UMD_LOSSYEAR_LIST_URL = (
    "https://storage.googleapis.com/earthenginepartners-hansen/"
    "GFC-2025-v1.13/lossyear.txt"
)
UMD_TILE_CACHE = RAW / "environmental" / "forest" / "umd_gfc_2025" / "lossyear_tiles"
UMD_PERIOD_YEARS = {
    "2010-2015": (2010, 2015),
    "2015-2020": (2015, 2020),
    "2020-2025": (2020, 2025),
}
COUNTRY_POLYGON_TYPES = {"Union EEZ and country", "Landlocked country"}
EARTH_RADIUS_M = 6_371_008.8
STRIPE_ROWS = 256
TILE_PATTERN = re.compile(r"_lossyear_(\d{2})([NS])_(\d{3})([EW])\.tif$")


def _tile_bounds(url: str) -> tuple[float, float, float, float]:
    """Return the 10 x 10 degree bounds encoded by a UMD granule filename."""
    match = TILE_PATTERN.search(urlparse(url).path)
    if not match:
        raise ValueError(f"Unrecognised UMD lossyear tile URL: {url}")
    lat_value, lat_hemi, lon_value, lon_hemi = match.groups()
    north = float(lat_value) * (1 if lat_hemi == "N" else -1)
    west = float(lon_value) * (1 if lon_hemi == "E" else -1)
    return west, north - 10.0, west + 10.0, north


def _read_wkb_rows(path: str | Path, columns: list[str], bounds=None):
    """Yield shapefile attributes and geometries without loading a GeoDataFrame."""
    _, _, geometries, values = pyogrio.raw.read(path, columns=columns, bbox=bounds)
    if geometries is None or values is None:
        return
    for geometry, row in zip(geometries, zip(*values)):
        if geometry is None:
            continue
        yield dict(zip(columns, row)), shapely.from_wkb(geometry)


def _target_country_geometries(target_units: set[str]):
    """Read land/EEZ account polygons and map boundary aliases to FRA codes."""
    grouped: dict[str, list[object]] = {}
    fields = ["POL_TYPE", "ISO_TER1", "ISO_SOV1"]
    for properties, geometry in _read_wkb_rows(BOUNDARIES_SHP, fields):
        if properties["POL_TYPE"] not in COUNTRY_POLYGON_TYPES:
            continue
        code = properties["ISO_TER1"] or properties["ISO_SOV1"]
        if not code:
            continue
        code = RASTER_CODE_ALIASES.get(str(code), str(code))
        if code in target_units:
            if not shapely.is_valid(geometry):
                raise ValueError(f"Invalid accounting polygon for {code} in {BOUNDARIES_SHP}")
            grouped.setdefault(code, []).append(geometry)
    return grouped


def _overlay_shapes_for_tile(
    bounds: tuple[float, float, float, float],
    country_geometries: dict[str, list[object]],
    unit_index: dict[str, int],
) -> list[tuple[object, int]]:
    """Intersect target accounting polygons with GEZ biome polygons in a tile."""
    tile = shapely.box(*bounds)
    countries: list[tuple[str, object]] = []
    for iso3, geometries in country_geometries.items():
        for geometry in geometries:
            if shapely.intersects(geometry, tile):
                clipped = shapely.intersection(geometry, tile)
                if not shapely.is_empty(clipped):
                    countries.append((iso3, clipped))
    if not countries:
        return []

    output: list[tuple[object, int]] = []
    for properties, gez_geometry in _read_wkb_rows(GEZ_SHP, ["gez_code"], bounds):
        raw_code = properties["gez_code"]
        if raw_code is None or pd.isna(raw_code):
            continue
        gez_code = int(raw_code)
        if GEZ_DOMAIN_TO_BIOME.get(gez_code // 10) is None:
            continue
        if not shapely.is_valid(gez_geometry):
            raise ValueError(f"Invalid GEZ polygon code {gez_code} in {GEZ_SHP}")
        if not shapely.intersects(gez_geometry, tile):
            continue
        gez_clipped = shapely.intersection(gez_geometry, tile)
        for iso3, country_clipped in countries:
            if not shapely.intersects(country_clipped, gez_clipped):
                continue
            overlap = shapely.intersection(country_clipped, gez_clipped)
            if shapely.is_empty(overlap):
                continue
            # unit_index * 100 + GEZ code identifies one unit-by-biome-zone pair.
            output.append((overlap, unit_index[iso3] * 100 + gez_code))
    return output


def _download(url: str, destination: Path) -> None:
    """Stream one public raster granule to the local cache if not present."""
    if destination.is_file() and destination.stat().st_size > 0:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        with temporary.open("wb") as stream:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    stream.write(block)
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise IOError(f"UMD download produced an empty file: {url}")
    temporary.replace(destination)


def _lossyear_urls(cache_dir: Path) -> list[str]:
    """Download the small official index of UMD lossyear granule URLs."""
    index_path = cache_dir / "lossyear.txt"
    if not index_path.is_file():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(UMD_LOSSYEAR_LIST_URL, timeout=(30, 120))
        response.raise_for_status()
        index_path.write_text(response.text, encoding="utf-8")
    urls = [line.strip() for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not urls:
        raise ValueError(f"The UMD granule list is empty: {index_path}")
    return urls


def _row_pixel_area_ha(transform, first_row: int, row_count: int) -> np.ndarray:
    """Spherical ground area of one geographic-grid pixel, by raster row."""
    rows = np.arange(first_row, first_row + row_count, dtype="float64")
    north = transform.f + rows * transform.e
    south = north + transform.e
    dlon = np.deg2rad(abs(transform.a))
    area_m2 = EARTH_RADIUS_M**2 * dlon * (
        np.sin(np.deg2rad(north)) - np.sin(np.deg2rad(south))
    )
    return area_m2 / 10_000.0


def _aggregate_tile(
    path: Path,
    shapes: list[tuple[object, int]],
    periods: set[str],
    number_of_units: int,
) -> dict[str, np.ndarray]:
    """Sum mapped tree-cover-loss pixel area by unit and GEZ code, in stripes."""
    n_keys = (number_of_units + 1) * 100
    totals = {period: np.zeros(n_keys, dtype="float64") for period in periods}
    with rasterio.open(path) as source:
        if source.crs is None or source.crs.to_epsg() != 4326:
            raise ValueError(f"Expected EPSG:4326 UMD raster, received {source.crs}: {path}")
        if source.count != 1 or source.dtypes[0] != "uint8":
            raise ValueError(f"Expected one uint8 lossyear band: {path}")
        for first_row in range(0, source.height, STRIPE_ROWS):
            row_count = min(STRIPE_ROWS, source.height - first_row)
            window = Window(0, first_row, source.width, row_count)
            transform = source.window_transform(window)
            code_grid = rasterize(
                shapes,
                out_shape=(row_count, source.width),
                transform=transform,
                fill=0,
                dtype="uint16",
                all_touched=False,
            )
            lossyear = source.read(1, window=window)
            valid = code_grid > 0
            if not valid.any():
                continue
            pixel_area = np.broadcast_to(
                _row_pixel_area_ha(source.transform, first_row, row_count)[:, None],
                lossyear.shape,
            )
            for period in periods:
                start, end = UMD_PERIOD_YEARS[period]
                first_code = start - 2000 + 1
                last_code = end - 2000
                selected = valid & (lossyear >= first_code) & (lossyear <= last_code)
                if selected.any():
                    totals[period] += np.bincount(
                        code_grid[selected].astype("int64"),
                        weights=pixel_area[selected],
                        minlength=n_keys,
                    )
    return totals


def build_loss_biome_areas(
    selected_period_by_unit: pd.Series,
    cache_dir: Path = UMD_TILE_CACHE,
) -> tuple[pd.DataFrame, list[str]]:
    """Build UMD event-area totals for the selected periods and target units.

    The returned area is a map-derived spatial indicator, not the FRA area total.
    It is used downstream only to form within-unit biome shares.
    """
    target_period = selected_period_by_unit.dropna().astype(str)
    if target_period.empty:
        return pd.DataFrame(columns=["iso3", "period", "biome", "mapped_loss_area_ha"]), []
    invalid = sorted(set(target_period) - set(UMD_PERIOD_YEARS))
    if invalid:
        raise ValueError(f"Unsupported FRA periods for UMD allocation: {invalid}")

    units = sorted(target_period.index.astype(str).unique())
    target_units = set(units)
    unit_index = {iso3: index for index, iso3 in enumerate(units, start=1)}
    country_geometries = _target_country_geometries(target_units)
    missing_units = sorted(target_units - set(country_geometries))
    if missing_units:
        raise ValueError(f"No matching accounting polygons for FRA units: {missing_units}")
    periods = set(target_period.unique())
    totals = {period: np.zeros((len(units) + 1) * 100, dtype="float64") for period in periods}
    downloaded_tiles: list[str] = []

    for url in _lossyear_urls(cache_dir):
        bounds = _tile_bounds(url)
        shapes = _overlay_shapes_for_tile(bounds, country_geometries, unit_index)
        if not shapes:
            continue
        filename = Path(urlparse(url).path).name
        local_path = cache_dir / filename
        _download(url, local_path)
        tile_totals = _aggregate_tile(local_path, shapes, periods, len(units))
        for period in periods:
            totals[period] += tile_totals[period]
        downloaded_tiles.append(filename)

    rows = []
    for period, values in totals.items():
        for iso3, unit_id in unit_index.items():
            for gez_code in range(1, 100):
                area = values[unit_id * 100 + gez_code]
                biome = GEZ_DOMAIN_TO_BIOME.get(gez_code // 10)
                if biome is not None and area > 0:
                    rows.append({
                        "iso3": iso3,
                        "period": period,
                        "biome": biome,
                        "mapped_loss_area_ha": float(area),
                    })
    result = pd.DataFrame(rows, columns=["iso3", "period", "biome", "mapped_loss_area_ha"])
    if not result.empty:
        result = result.groupby(["iso3", "period", "biome"], as_index=False)["mapped_loss_area_ha"].sum()
    return result, downloaded_tiles
