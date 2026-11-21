import pytest

from src.nodes import convert as convert_module
from src.nodes.convert import convert
from src.state import DwgFile, PipelineState
from tests.conftest import needs_libredwg


def _state(tmp_path, files):
    return PipelineState(uploads_dir=str(tmp_path), output_dir=str(tmp_path / "out"),
                         pending=files)


def test_convert_missing_binary_gives_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(convert_module.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="brew install libredwg"):
        convert(_state(tmp_path, [DwgFile(name="a", path="a.dwg")]))


def test_convert_nothing_pending_needs_no_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(convert_module.shutil, "which", lambda _: None)
    assert convert(_state(tmp_path, []))["dxf_paths"] == {}


@needs_libredwg
def test_convert_real_dwg(tmp_path, dwg_path):
    result = convert(_state(tmp_path, [DwgFile(name="cube", path=str(dwg_path))]))
    assert result["errors"] == {}
    assert result["dxf_paths"]["cube"].endswith("cube.dxf")


@needs_libredwg
def test_convert_corrupt_file_is_skipped(tmp_path):
    bad = tmp_path / "bad.dwg"
    bad.write_bytes(b"not a dwg at all")
    result = convert(_state(tmp_path, [DwgFile(name="bad", path=str(bad))]))
    assert result["dxf_paths"] == {}
    assert "bad" in result["errors"]
