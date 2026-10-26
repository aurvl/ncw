import numpy as np
import pandas as pd
import shapely
import rasterio
from rasterio.transform import from_origin

from gcw.biome_shares import _wkb_polygons, select_shares, select_shares_map_first, shares_from_gez
from gcw.forest_uptake_pan import area_by_biome
from gcw.gfw_rates import aggregate_tile, annual_rate_tc_ha_yr, combine_tile_summaries, _weighted_moments
from gcw.forest_uptake_gfw import area_by_biome as gfw_area_by_biome, sensitivity_uptake, uptake_for_rates
from gcw.gcw import build_gcw
from gcw.ncw import combine_complete_accounts, forest_share_for_composition
from gcw.pan_rates import _mean_sd, build_rates, pan_areas, rate_checks, read_pan_table1
from gcw.territories import _complete_economic_groups, _valid_iso3
from gcw.validation import sum_draws, summarise_draws


def test_economic_group_fallback_preserves_source_units() -> None:
    territories = pd.DataFrame({
        "iso3": ["MUS", "IO", "REU", "VAT", "XXX"],
        "groups": ["SIDS", None, None, None, None],
        "sovereign": ["Republic of Mauritius", "Republic of Mauritius", "France", None, "Unknown"],
    })
    bcw = pd.DataFrame({
        "country_name": ["Republic of Mauritius", "France"],
        "Groups": ["SIDS", "Developed economies"],
    })
    overrides = pd.DataFrame({"iso3": ["REU", "VAT"], "groups": ["Developed economies"] * 2})
    result = _complete_economic_groups(territories, bcw, overrides).set_index("iso3")
    assert result.loc["MUS", "group_source"] == "published_unit"
    assert result.loc["IO", "groups"] == "SIDS"
    assert result.loc["IO", "group_source"] == "sovereign_fallback"
    assert result.loc["REU", "groups"] == "Developed economies"
    assert result.loc["VAT", "group_source"] == "researcher_convention"
    assert pd.isna(result.loc["XXX", "groups"])


def test_accounting_unit_code_is_not_assumed_to_be_iso3() -> None:
    assert _valid_iso3("MUS") == "MUS"
    assert _valid_iso3("IO") is None
    assert _valid_iso3("SD") is None
    assert _valid_iso3("BCW-JR") is None


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
        "area_ha": [1.0, 1.0, 1.0, 1.0],
        "pixel_count": [1, 1, 1, 1],
        "negative_source_pixel_count": [0, 0, 0, 0],
    })
    second = first.copy()
    second["rate_tc_ha_yr_mean"] *= 3
    second["area_ha"] = 3.0
    result = combine_tile_summaries([first, second]).set_index("biome")
    assert np.isclose(result.loc["tropical", "rate_tc_ha_yr_mean"], 2.5)
    assert np.isclose(result.loc["boreal", "rate_tc_ha_yr_mean"], 10.0)


def test_gfw_pixel_mean_weights_exact_spherical_cell_area_by_latitude() -> None:
    rates = np.array([[0.0], [2.0]])
    biome = np.array([[1], [1]], dtype=np.uint8)
    north = np.array([2.0, 1.0])
    south = np.array([1.0, 0.0])
    areas = np.sin(np.deg2rad(north)) - np.sin(np.deg2rad(south))
    mean, _, total_area, _ = _weighted_moments(rates, biome, areas)[1]
    assert np.isclose(mean, 2.0 * areas[1] / areas.sum())
    assert np.isclose(total_area, areas.sum())


def test_gfw_raster_tile_aggregates_synthetic_biome_pixels(tmp_path) -> None:
    raster_path = tmp_path / "synthetic.tif"
    with rasterio.open(
        raster_path, "w", driver="GTiff", height=2, width=2, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(0, 2, 1, 1), nodata=-9999,
    ) as raster:
        raster.write(np.array([[23 * 44 / 12, 23 * 44 / 12],
                               [23 * 44 / 12, -23 * 44 / 12]], dtype="float32"), 1)
    gez_path = tmp_path / "gez.geojson"
    gez_path.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"gez_code":11},'
        '"geometry":{"type":"Polygon","coordinates":[[[0,0],[2,0],[2,2],[0,2],[0,0]]]}}]}',
        encoding="utf-8",
    )

    result = aggregate_tile(raster_path, str(gez_path), stripe_rows=1).set_index("biome")
    result_two_rows = aggregate_tile(raster_path, str(gez_path), stripe_rows=2).set_index("biome")
    row_area = np.sin(np.deg2rad([2.0, 1.0])) - np.sin(np.deg2rad([1.0, 0.0]))
    expected_mean = row_area[0] / row_area.sum()
    assert np.isclose(result.loc["tropical", "rate_tc_ha_yr_mean"], expected_mean)
    expected_area_ha = (
        2 * (np.pi / 180.0) * 6_371_008.8**2 * row_area.sum() / 10_000.0
    )
    assert np.isclose(result.loc["tropical", "area_ha"], expected_area_ha)
    assert result.loc["tropical", "pixel_count"] == 4
    assert result.loc["tropical", "negative_source_pixel_count"] == 1
    assert result.loc["tropical", "pixel_count"] == result_two_rows.loc["tropical", "pixel_count"]


def test_gfw_source_forest_type_excludes_mangrove_pixels(tmp_path) -> None:
    transform = from_origin(0, 2, 1, 1)
    raster_path = tmp_path / "gross.tif"
    with rasterio.open(
        raster_path, "w", driver="GTiff", height=2, width=2, count=1,
        dtype="float32", crs="EPSG:4326", transform=transform, nodata=-9999,
    ) as raster:
        raster.write(np.array([[23 * 44 / 12, 10 * 23 * 44 / 12],
                               [23 * 44 / 12, 23 * 44 / 12]], dtype="float32"), 1)
    forest_type_path = tmp_path / "types.tif"
    with rasterio.open(
        forest_type_path, "w", driver="GTiff", height=2, width=2, count=1,
        dtype="uint8", crs="EPSG:4326", transform=transform, nodata=0,
    ) as raster:
        raster.write(np.array([[1, 6], [1, 1]], dtype="uint8"), 1)
    gez_path = tmp_path / "gez.geojson"
    gez_path.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"gez_code":11},'
        '"geometry":{"type":"Polygon","coordinates":[[[0,0],[2,0],[2,2],[0,2],[0,0]]]}}]}',
        encoding="utf-8",
    )
    old = aggregate_tile(raster_path, str(gez_path), stripe_rows=1).set_index("biome")
    clean = aggregate_tile(
        raster_path, str(gez_path), stripe_rows=1, forest_type_path=forest_type_path
    ).set_index("biome")
    assert old.loc["tropical", "pixel_count"] == 4
    assert clean.loc["tropical", "pixel_count"] == 3
    assert clean.loc["tropical", "excluded_mangrove_pixel_count"] == 1
    assert np.isclose(clean.loc["tropical", "rate_tc_ha_yr_mean"], 1.0)
    assert old.loc["tropical", "rate_tc_ha_yr_mean"] > 1.0
    assert clean.loc["tropical", "excluded_mangrove_area_ha"] > 0


def test_gfw_all_mangrove_tile_keeps_zero_weight_audit_row(tmp_path) -> None:
    transform = from_origin(0, 1, 1, 1)
    raster_path = tmp_path / "gross.tif"
    with rasterio.open(
        raster_path, "w", driver="GTiff", height=1, width=1, count=1,
        dtype="float32", crs="EPSG:4326", transform=transform, nodata=-9999,
    ) as raster:
        raster.write(np.array([[23 * 44 / 12]], dtype="float32"), 1)
    forest_type_path = tmp_path / "types.tif"
    with rasterio.open(
        forest_type_path, "w", driver="GTiff", height=1, width=1, count=1,
        dtype="uint8", crs="EPSG:4326", transform=transform, nodata=0,
    ) as raster:
        raster.write(np.array([[6]], dtype="uint8"), 1)
    gez_path = tmp_path / "gez.geojson"
    gez_path.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"gez_code":11},'
        '"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}]}',
        encoding="utf-8",
    )
    row = aggregate_tile(
        raster_path, str(gez_path), stripe_rows=1, forest_type_path=forest_type_path
    ).set_index("biome").loc["tropical"]
    assert row.pixel_count == 0
    assert row.area_ha == 0
    assert row.excluded_mangrove_pixel_count == 1
    assert row.excluded_mangrove_area_ha > 0


def test_gfw_country_area_removes_only_report_documented_overlap_from_tropical() -> None:
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
    overlap = pd.DataFrame({"iso3": ["AAA"], "documented_forest_mangrove_area_ha": [5.0]})
    areas = gfw_area_by_biome(forest, shares, overlap_evidence=overlap)
    main = areas.query("variant == 'documented_overlap_removed'").set_index("biome")["area_ha"]
    assert np.isclose(main["tropical"], 35.0)
    assert np.isclose(main["subtropical"], 30.0)
    countries, uptake = uptake_for_rates(areas, rates, "documented_overlap_removed")
    expected_tc = 35 * 1 + 30 * 2 + 20 * 3 + 10 * 4
    assert countries == ["AAA"]
    assert np.isclose(uptake[0], expected_tc * 44 / 12)
    scenarios = sensitivity_uptake(areas, rates).set_index("scenario")
    assert scenarios.loc["spatial_sd_low", "uptake_tco2_yr"] < scenarios.loc["central", "uptake_tco2_yr"]
    assert scenarios.loc["spatial_sd_high", "uptake_tco2_yr"] > scenarios.loc["central", "uptake_tco2_yr"]


def test_biome_selection_prefers_fra_and_fills_missing_units_from_gez() -> None:
    fra = pd.DataFrame({
        "iso3": ["AAA", "AAA"],
        "biome": ["tropical", "temperate"],
        "share": [0.75, 0.25],
        "source": ["fra_reported", "fra_reported"],
    })
    gez = pd.DataFrame({
        "iso3": ["AAA", "AAA", "BBB", "BBB"],
        "biome": ["tropical", "temperate", "tropical", "boreal"],
        "share": [0.50, 0.50, 0.60, 0.40],
        "source": ["gez_forest_mask"] * 4,
    })
    selected = select_shares(gez, fra).set_index(["iso3", "biome"])
    assert selected.loc[("AAA", "tropical"), "source"] == "fra_reported"
    assert np.isclose(selected.loc[("AAA", "tropical"), "share"], 0.75)
    assert set(selected.loc["BBB", "source"]) == {"gez_forest_mask"}
    map_first = select_shares_map_first(gez, fra).set_index(["iso3", "biome"])
    assert map_first.loc[("AAA", "tropical"), "source"] == "gez_forest_mask"
    assert np.isclose(map_first.loc[("AAA", "tropical"), "share"], 0.50)


def test_gfw_country_area_applies_fractional_documented_overlap() -> None:
    forest = pd.DataFrame({"iso3": ["AAA"], "year": ["2025"], "forest": [100.0], "mangroves": [10.0]})
    shares = pd.DataFrame({
        "iso3": ["AAA"] * 4,
        "biome": ["tropical", "subtropical", "temperate", "boreal"],
        "share": [0.4, 0.3, 0.2, 0.1],
        "source": ["fra_reported"] * 4,
    })
    overlap = pd.DataFrame({
        "iso3": ["AAA"],
        "documented_forest_fraction": [0.8],
        "documented_forest_mangrove_area_ha": [8.0],
        "documented_other_wooded_land_area_ha": [0.0],
        "documented_remaining_land_area_ha": [0.0],
        "unresolved_mangrove_area_ha": [2.0],
        "fra_mangroves_2025_ha": [10.0],
        "overlap_status": ["documented_fractional_forest"],
    })
    areas = gfw_area_by_biome(forest, shares, overlap_evidence=overlap)
    main = areas.query("variant == 'documented_overlap_removed'").set_index("biome")
    assert np.isclose(main.loc["tropical", "area_ha"], 32.0)
    assert np.isclose(main["unresolved_fra_mangrove_category_ha"].iloc[0], 2.0)


def test_gfw_country_area_keeps_documented_remaining_land_out_of_unknown() -> None:
    forest = pd.DataFrame({"iso3": ["AAA"], "year": ["2025"], "forest": [100.0], "mangroves": [10.0]})
    shares = pd.DataFrame({
        "iso3": ["AAA"] * 4,
        "biome": ["tropical", "subtropical", "temperate", "boreal"],
        "share": [0.4, 0.3, 0.2, 0.1],
        "source": ["fra_reported"] * 4,
    })
    overlap = pd.DataFrame({
        "iso3": ["AAA"],
        "documented_forest_mangrove_area_ha": [4.8],
        "documented_other_wooded_land_area_ha": [4.55],
        "documented_remaining_land_area_ha": [0.65],
        "unresolved_mangrove_area_ha": [0.0],
    })
    areas = gfw_area_by_biome(forest, shares, overlap_evidence=overlap)
    main = areas.query("variant == 'documented_overlap_removed'")
    assert np.isclose(main["unresolved_fra_mangrove_category_ha"].iloc[0], 0.0)
    assert np.isclose(main["documented_remaining_land_area_ha"].iloc[0], 0.65)


def test_gcw_keeps_spatial_sensitivity_separate_from_draw_uncertainty() -> None:
    forest = {
        "iso3": ["AAA"],
        "documented_overlap_removed": np.array([[10.0, 10.0]]),
        "no_overlap_removed": np.array([[12.0, 12.0]]),
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


def test_missing_bcw_stays_missing_and_bcw_only_has_zero_forest_share() -> None:
    gcw = np.array([[10.0, 12.0], [np.nan, np.nan], [5.0, 5.0]])
    bcw = np.array([[2.0, 2.0], [7.0, 7.0], [np.nan, np.nan]])
    ncw, has_gcw, has_bcw, complete = combine_complete_accounts(gcw, bcw)
    share = forest_share_for_composition(
        np.array([11.0, np.nan, 5.0]),
        np.array([13.0, np.nan, np.nan]),
        has_gcw,
        has_bcw,
    )

    assert np.allclose(ncw[0], [12.0, 14.0])
    assert np.isnan(ncw[1:]).all()
    assert complete.tolist() == [True, False, False]
    assert has_gcw.tolist() == [True, False, True]
    assert has_bcw.tolist() == [True, True, False]
    assert np.isclose(share[0], 11.0 / 13.0)
    assert share[1] == 0.0  # BCW is present, so the forest share is in the 0-20% bin.
    assert np.isnan(share[2])  # BCW is missing, so there is no composition value.


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
