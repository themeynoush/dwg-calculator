import json

from src.nodes.build_catalog import build_catalog
from src.state import PipelineState


def test_catalog_lists_only_converted_dwgs(tmp_path):
    up, out = tmp_path / "up", tmp_path / "out"
    up.mkdir()
    out.mkdir()
    for name in ["b.dwg", "a.DWG", "failed.dwg", "readme.txt"]:
        (up / name).write_bytes(b"12345")
    for name in ["a.glb", "b.glb"]:
        (out / name).write_bytes(b"x")
    state = PipelineState(uploads_dir=str(up), output_dir=str(out),
                          errors={"failed": "parse: boom"})
    catalog = build_catalog(state)["catalog"]
    assert [e.name for e in catalog] == ["a", "b"]
    assert catalog[0].model_url.startswith("/models/a.glb?v=")
    assert catalog[0].size_bytes == 5
    data = json.loads((out / "catalog.json").read_text())
    assert len(data["models"]) == 2 and data["errors"] == {"failed": "parse: boom"}
