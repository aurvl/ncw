import numpy as np
import pandas as pd
import shapely
import rasterio
from rasterio.transform import from_origin

from gcw.biome_shares import _wkb_polygons, shares_from_gez
from gcw.forest_uptake_pan import area_by_biome
from gcw.gfw_rates import aggregate_tile, annual_rate_tc_ha_yr, combine_tile_summaries, _weighted_moments
from gcw.forest_uptake_gfw import area_by_biome as gfw_area_by_biome, sensitivity_uptake, uptake_for_rates
from gcw.gcw import build_gcw
from gcw.pan_rates import _mean_sd, build_rates, pan_areas, rate_checks, read_pan_table1
from gcw.validation import sum_draws, summarise_draws


def test_wkb_parts_match_shapely_area() -> None:
    geometry = shapely.MultiPolygon([shapely.box(0, 0, 2, 2).difference(shapely.box(0.5, 0.5, 1, 1)), shapely.box(5, 5, 6, 7)])
    parts = list(_wkb_polygons(shapely.to_wkb(geometry, byte_order=1)))
    assert len(parts) == 2
    assert np.isclose(sum(shapely.Polygon(e, h).area for e, h in parts), geometry.area)


def test_pan_cell_parsing() -> None:
    assert _mean_sd("0.88 ± 0.24") == (0.88, 0.24)
    assert _mean_sd("−2.13 ± 0.56") == (-2.13, 0.56)


def test_gfw_cumulative_co2_converts_to_annual_carbon_rate() -> None:
    # Synthetic 23-year cumulative value equivalent to 1 tC/ha/yr.
    assert np.isclose(annual_rate_tc_ha_yr(23 * 44 / 12), 1.0)


def test_gfw_tile_summaries_combine_by_area_weight() -> None:
    first = pd.DataFrame({
        "biome": ["tropical", "subtropical", "temperate", "boreal"],
        "rate_tc_ha_yr_mean": [1.0, 2.0, 3.0, 4.0],
        "rate_tc_ha_yr_spatial_sd": [0.0, 0.0, 0.0, 0.0],
        "area_weight_sum": [1.0, 1.0, 1.0, 1.0],
        "pixel_count": [1, 1, 1, 1],
    })
    second = first.copy()
    second["rate_tc_ha_yr_mean"] *= 3
    second["area_weight_sum"] = 3.0
    result = combine_tile_summaries([first, second]).set_index("biome")
    assert np.isclose(result.loc["tropical", "rate_tc_ha_yr_mean"], 2.5)
    assert np.isclose(result.loc["boreal", "rate_tc_ha_yr_mean"], 10.0)


def test_gfw_pixel_mean_weights_geographic_cell_area_by_latitude() -> None:
    rates = np.array([[0.0], [2.0]])
    biome = np.array([[1], [1]], dtype=np.uint8)
    mean, _, _, _ = _weighted_moments(rates, biome, np.array([0.0, 60.0]))[1]
    assert np.isclose(mean, 2.0 / 3.0)


def test_gfw_raster_tile_aggregates_synthetic_biome_pixels(tmp_path) -> None:
    raster_path = tmp_path / "synthetic.tif"
    with rasterio.open(
        raster_path, "w", driver="GTiff", height=2, width=2, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(0, 2, 1, 1), nodata=-9999,
    ) as raster:
        raster.write(np.full((2, 2), 23 * 44 / 12, dtype="float32"), 1)
    gez_path = tmp_path / "gez.geojson"
    gez_path.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"gez_code":11},'
        '"geometry":{"type":"Polygon","coordinates":[[[0,0],[2,0],[2,2],[0,2],[0,0]]]}}]}',
        encoding="utf-8",
    )

    result = aggregate_tile(raster_path, str(gez_path), stripe_rows=1).set_index("biome")
    assert np.isclose(result.loc["tropical", "rate_tc_ha_yr_mean"], 1.0)
    assert result.loc["tropical", "pixel_count"] == 4


def test_gfw_country_area_uses_four_biomes_and_subtracts_mangroves_from_tropical() -> None:
    forest = pd.DataFrame({"iso3": ["AAA"], "year": ["2025"], "forest": [100.0], "mangroves": [5.0]})
    shares = pd.DataFrame({
        "iso3": ["AAA"] * 4,
        "biome": ["tropical", "subtropical", "temperate", "boreal"],
        "share": [0.4, 0.3, 0.2, 0.1],
        "source": ["synthetic"] * 4,
    })
    rates = pd.DataFrame({
        "biome": ["tropical", "subtropical", "temperate", "boreal"],
        "rate_tc_ha_yr_mean": [1.0, 2.0, 3.0, 4.0],
        "rate_tc_ha_yr_spatial_sd": [0.1, 0.2, 0.3, 0.4],
    })
    areas = gfw_area_by_biome(forest, shares)
    main = areas.query("variant == 'excl_mangroves'").set_index("biome")["area_ha"]
    assert np.isclose(main["tropical"], 35.0)
    assert np.isclose(main["subtropical"], 30.0)
    countries, uptake = uptake_for_rates(areas, rates, "excl_mangroves")
    expected_tc = 35 * 1 + 30 * 2 + 20 * 3 + 10 * 4
    assert countries == ["AAA"]
    assert np.isclose(uptake[0], expected_tc * 44 / 12)
    scenarios = sensitivity_uptake(areas, rates).set_index("scenario")
    assert scenarios.loc["spatial_sd_low", "uptake_tco2_yr"] < scenarios.loc["central", "uptake_tco2_yr"]
    assert scenarios.loc["spatial_sd_high", "uptake_tco2_yr"] > scenarios.loc["central", "uptake_tco2_yr"]


def test_gcw_keeps_spatial_sensitivity_separate_from_draw_uncertainty() -> None:
    forest = {
        "iso3": ["AAA"],
        "excl_mangroves": np.array([[10.0, 10.0]]),
        "incl_mangroves": np.array([[12.0, 12.0]]),
        "spatial_sd_low": np.array([[8.0, 8.0]]),
        "spatial_sd_high": np.array([[12.0, 12.0]]),
    }
    territories = pd.DataFrame({
        "iso3": ["AAA"], "name": ["Test"], "continent": ["X"], "fra_region": ["X"],
        "groups": ["X"], "population": [1.0], "gdp": [1.0],
    })
    faostat = pd.DataFrame({"iso3": ["AAA"], "net_uptake_tco2_yr": [1.0], "interannual_sd": [0.0], "n_years": [1]})
    table, draws = build_gcw(territories, forest, faostat, np.array([100.0, 200.0]))
    row = table.set_index("iso3").loc["AAA"]
    assert row["gcw_usd2015_yr_mean"] == 1500.0
    assert row["gcw_spatial_sd_low_usd2015_yr_mean"] == 1200.0
    assert row["gcw_spatial_sd_high_usd2015_yr_mean"] == 1800.0
    assert np.isclose(draws["gcw_usd2015_yr"].std(), 500.0)


def test_pan_rates_reproduce_fluxes_and_published_rates() -> None:
    flux, areas = read_pan_table1(), pan_areas()
    rates = build_rates(flux, areas)
    assert list(rates["pan_biome"]) == ["tropical", "temperate", "boreal"]
    assert rate_checks(flux, areas, rates)["ok"].all()


def test_subtropical_joins_tropical_and_mangroves_leave_it() -> None:
    shares = pd.DataFrame({"iso3": ["AAA"] * 3, "biome": ["tropical", "subtropical", "temperate"],
                           "share": [0.5, 0.3, 0.2], "source": "gez_forest_mask"})
    areas = pd.DataFrame({"iso3": ["AAA"], "year": ["2025"], "forest": [100.0], "mangroves": [10.0]})
    result = area_by_biome(areas, shares).set_index(["variant", "pan_biome"])["area_ha"]
    assert np.isclose(result[("incl_mangroves", "tropical")], 80.0)
    assert np.isclose(result[("excl_mangroves", "tropical")], 70.0)
    assert np.isclose(result[("excl_mangroves", "temperate")], 20.0)


def test_draw_sums_keep_correlation() -> None:
    common = np.array([1.0, 3.0])
    _, summed = sum_draws(np.vstack([common, common]), pd.Series(["world", "world"]))
    assert np.isclose(summarise_draws(summed, "x").iloc[0]["x_sd"], 2 * np.std(common, ddof=1))


def test_gez_shares_are_forest_weighted() -> None:
    table = pd.DataFrame({"iso3": ["AAA", "AAA"], "gez_code": [11, 31], "biome": ["tropical", "temperate"],
                          "forest_km2": [30.0, 10.0], "land_km2": [10.0, 90.0]})
    assert np.isclose(shares_from_gez(table).set_index("biome")["share"]["tropical"], 0.75)
