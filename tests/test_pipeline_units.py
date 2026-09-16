import numpy as np
import pandas as pd
import shapely

from gcw.biome_shares import _wkb_polygons, shares_from_gez
from gcw.pan_rates import _mean_sd
from gcw.validation import sum_draws, summarise_draws


def test_wkb_parts_match_shapely_area() -> None:
    geometry = shapely.MultiPolygon([shapely.box(0, 0, 2, 2).difference(shapely.box(0.5, 0.5, 1, 1)), shapely.box(5, 5, 6, 7)])
    parts = list(_wkb_polygons(shapely.to_wkb(geometry, byte_order=1)))
    assert len(parts) == 2
    assert np.isclose(sum(shapely.Polygon(e, h).area for e, h in parts), geometry.area)


def test_pan_cell_parsing() -> None:
    assert _mean_sd("0.88 ± 0.24") == (0.88, 0.24)
    assert _mean_sd("−2.13 ± 0.56") == (-2.13, 0.56)


def test_draw_sums_keep_correlation() -> None:
    common = np.array([1.0, 3.0])
    draws = np.vstack([common, common])
    _, summed = sum_draws(draws, pd.Series(["world", "world"]))
    stats = summarise_draws(summed, "x").iloc[0]
    assert np.isclose(stats["x_sd"], 2 * np.std(common, ddof=1))


def test_gez_shares_are_forest_weighted() -> None:
    table = pd.DataFrame(
        {"iso3": ["AAA", "AAA"], "gez_code": [11, 31], "biome": ["tropical", "temperate"],
         "forest_km2": [30.0, 10.0], "land_km2": [10.0, 90.0]}
    )
    shares = shares_from_gez(table).set_index("biome")["share"]
    assert np.isclose(shares["tropical"], 0.75)
