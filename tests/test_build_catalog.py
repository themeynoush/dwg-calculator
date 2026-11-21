import json

from src.nodes.build_catalog import build_catalog
from src.state import MaterialCost, PipelineState


def test_catalog_lists_only_converted_dwgs(tmp_path):
    up, out = tmp_path / "up", tmp_path / "out"
    up.mkdir()
    out.mkdir()
    for name in ["b.dwg", "a.DWG", "failed.dwg", "readme.txt"]:
        (up / name).write_bytes(b"12345")
    for name in ["a.glb", "b.glb"]:
        (out / name).write_bytes(b"x")
    oak = MaterialCost(layer="OAK", length_m=2, width_m=2, height_m=0, area_m2=4, unit="m2",
                       unit_price=10, price=40)
    state = PipelineState(uploads_dir=str(up), output_dir=str(out),
                          errors={"failed": "parse: boom"}, costs={"a": [oak]})
    catalog = build_catalog(state)["catalog"]
    assert [e.name for e in catalog] == ["a", "b"]
    assert catalog[0].model_url.startswith("/models/a.glb?v=")
    assert catalog[0].size_bytes == 5
    assert catalog[0].materials == [oak] and catalog[1].materials == []
    data = json.loads((out / "catalog.json").read_text())
    assert len(data["models"]) == 2 and data["errors"] == {"failed": "parse: boom"}
    assert data["models"][0]["materials"][0]["price"] == 40
