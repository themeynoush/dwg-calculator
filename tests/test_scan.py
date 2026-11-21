import os

from src.nodes.scan import scan
from src.state import PipelineState


def _state(tmp_path, force=False):
    return PipelineState(uploads_dir=str(tmp_path / "up"), output_dir=str(tmp_path / "out"),
                         force=force)


def test_scan_finds_dwg_case_insensitive_and_ignores_others(tmp_path):
    up = tmp_path / "up"
    up.mkdir()
    for name in ["a.dwg", "B.DWG", "notes.txt", "c.dxf"]:
        (up / name).write_bytes(b"x")
    names = [f.name for f in scan(_state(tmp_path))["pending"]]
    assert names == ["B", "a"]


def test_scan_creates_missing_uploads_folder(tmp_path):
    assert scan(_state(tmp_path))["pending"] == []
    assert (tmp_path / "up").is_dir()


def test_scan_skips_up_to_date_unless_forced(tmp_path):
    (tmp_path / "up").mkdir()
    (tmp_path / "out").mkdir()
    dwg = tmp_path / "up" / "a.dwg"
    dwg.write_bytes(b"x")
    glb = tmp_path / "out" / "a.glb"
    glb.write_bytes(b"x")
    os.utime(dwg, (1000, 1000))
    assert len(scan(_state(tmp_path))["pending"]) == 1    # no take-off yet → measure it
    takeoff = tmp_path / "out" / "a.takeoff.json"
    takeoff.write_text('[{"layer": "OAK", "length_m": 1, "height_m": 0, "area_m2": 1}]')
    assert len(scan(_state(tmp_path))["pending"]) == 1    # older format (no width) → redo
    takeoff.write_text("[]")
    assert scan(_state(tmp_path))["pending"] == []
    assert len(scan(_state(tmp_path, force=True))["pending"]) == 1
    os.utime(dwg, (glb.stat().st_mtime + 10,) * 2)   # DWG edited after export
    assert len(scan(_state(tmp_path))["pending"]) == 1
