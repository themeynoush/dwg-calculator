import json

from src.pipeline import run_pipeline
from tests.conftest import needs_libredwg


@needs_libredwg
def test_end_to_end(tmp_path, dwg_path):
    out = tmp_path / "out"
    catalog = run_pipeline(str(dwg_path.parent), str(out))
    assert [e.name for e in catalog] == ["cube"]
    assert (out / "cube.glb").stat().st_size > 0
    assert json.loads((out / "catalog.json").read_text())["errors"] == {}
    # second run: nothing to reprocess, catalog still complete
    assert [e.name for e in run_pipeline(str(dwg_path.parent), str(out))] == ["cube"]
