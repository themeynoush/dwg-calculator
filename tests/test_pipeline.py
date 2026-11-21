import json

from src.pipeline import run_pipeline
from tests.conftest import needs_libredwg


@needs_libredwg
def test_end_to_end(tmp_path, dwg_path):
    out = tmp_path / "out"
    (dwg_path.parent / "prices.csv").write_text("material,unit,unit_price,currency\n0,m2,10,EUR\n")
    catalog = run_pipeline(str(dwg_path.parent), str(out))
    assert [e.name for e in catalog] == ["cube"]
    # unit cube on layer "0" (metres): surface = L x W = 1 m² x 10 EUR
    [cube] = catalog[0].materials
    assert cube.layer == "0"
    assert (cube.length_m, cube.width_m, cube.height_m, cube.area_m2) == (1, 1, 1, 1)
    assert cube.price == 10 and cube.currency == "EUR"
    assert (out / "cube.glb").stat().st_size > 0
    assert json.loads((out / "catalog.json").read_text())["errors"] == {}
    # second run: nothing to reprocess, catalog still complete and still priced
    (dwg_path.parent / "prices.csv").write_text("material,unit,unit_price\n0,m2,20\n")
    again = run_pipeline(str(dwg_path.parent), str(out))
    assert [e.name for e in again] == ["cube"] and again[0].materials[0].price == 20
