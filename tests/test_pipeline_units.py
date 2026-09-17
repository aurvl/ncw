import numpy as np
import pandas as pd
import shapely

from gcw.biome_shares import _wkb_polygons, shares_from_gez
from gcw.forest_uptake_pan import area_by_biome
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
