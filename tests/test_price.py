import json

import pytest

from src.nodes.price import PriceListError, price, read_prices


def _setup(tmp_path, csv_text=None):
    up, out = tmp_path / "up", tmp_path / "out"
    up.mkdir()
    out.mkdir()
    if csv_text is not None:
        (up / "prices.csv").write_text(csv_text)
    takeoff = [{"layer": "Floor-Oak", "length_m": 5, "width_m": 4, "height_m": 0, "area_m2": 20},
               {"layer": "BRASS", "length_m": 8, "width_m": 0.1, "height_m": 0.1, "area_m2": 0.8},
               {"layer": "UNLISTED", "length_m": 1, "width_m": 1, "height_m": 1, "area_m2": 1}]
    (out / "shop.takeoff.json").write_text(json.dumps(takeoff))
    from src.state import PipelineState
    return PipelineState(uploads_dir=str(up), output_dir=str(out))


def test_prices_by_area_and_by_length_case_insensitive(tmp_path):
    state = _setup(tmp_path, "material,unit,unit_price,currency\n"
                             "FLOOR-OAK,m2,120,EUR\nbrass,m,95.5,EUR\n")
    costs = {c.layer: c for c in price(state)["costs"]["shop"]}
    assert costs["Floor-Oak"].price == 2400 and costs["Floor-Oak"].unit == "m2"
    assert costs["BRASS"].price == 764 and costs["BRASS"].currency == "EUR"
    assert costs["UNLISTED"].price is None and costs["UNLISTED"].area_m2 == 1


def test_missing_price_list_leaves_quantities_unpriced(tmp_path):
    result = price(_setup(tmp_path))
    assert all(c.price is None for c in result["costs"]["shop"])
    assert result["errors"] == {}


def test_bad_price_list_is_reported_not_fatal(tmp_path):
    result = price(_setup(tmp_path, "material,unit,unit_price\nOAK,m2,cheap\n"))
    assert "prices.csv" in result["errors"]
    assert all(c.price is None for c in result["costs"]["shop"])


def test_unit_defaults_to_m2_and_unknown_unit_is_rejected(tmp_path):
    path = tmp_path / "p.csv"
    path.write_text("material,unit_price\nOAK,10\n")
    assert read_prices(path) == {"OAK": ("m2", 10.0, None)}
    path.write_text("material,unit,unit_price\nOAK,kg,10\n")
    with pytest.raises(PriceListError, match="unknown unit"):
        read_prices(path)
