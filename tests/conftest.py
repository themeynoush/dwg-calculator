import shutil
import subprocess
from pathlib import Path

import ezdxf
import pytest

HAS_LIBREDWG = shutil.which("dwg2dxf") is not None and shutil.which("dxf2dwg") is not None
needs_libredwg = pytest.mark.skipif(not HAS_LIBREDWG, reason="LibreDWG not installed")

CUBE = [  # 6 quads of a unit cube → 12 triangles
    [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
    [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],
    [(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)],
    [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
]


def make_doc(cube: bool = True, line: bool = True, insert: bool = False, text: bool = False):
    doc = ezdxf.new()
    msp = doc.modelspace()
    if cube:
        for quad in CUBE:
            msp.add_3dface(quad)
    if line:
        msp.add_line((0, 0, 0), (2, 2, 2))
    if insert:
        block = doc.blocks.new("POST")
        block.add_line((0, 0, 0), (0, 0, 3))
        msp.add_blockref("POST", (5, 5, 0))
    if text:
        msp.add_text("hello")
    return doc


@pytest.fixture
def dxf_path(tmp_path: Path) -> Path:
    path = tmp_path / "cube.dxf"
    make_doc().saveas(path)
    return path


@pytest.fixture
def dwg_path(tmp_path: Path, dxf_path: Path) -> Path:
    """A real DWG produced by LibreDWG from the cube DXF."""
    if not HAS_LIBREDWG:
        pytest.skip("LibreDWG not installed")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    dwg = uploads / "cube.dwg"
    subprocess.run(["dxf2dwg", "-y", "-o", str(dwg), str(dxf_path)], capture_output=True)
    assert dwg.exists()
    return dwg
