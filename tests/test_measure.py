import json

import ezdxf
import pytest
from ezdxf import units

from src.nodes.extract_geometry import extract_geometry
from src.nodes.measure import measure, read_takeoff, to_metres
from src.state import PipelineState
from tests.conftest import CUBE


def _measure(tmp_path, doc):
    state = PipelineState(uploads_dir=".", output_dir=str(tmp_path), documents={"d": doc})
    state.geometries = extract_geometry(state)["geometries"]
    return {q.layer: q for q in measure(state)["quantities"]["d"]}


def _lwh_area(q):
    return q.length_m, q.width_m, q.height_m, q.area_m2


def test_unit_conversion():
    assert to_metres(units.MM) == pytest.approx(0.001)
    assert to_metres(units.M) == 1
    assert to_metres(0) == 1          # unitless drawings are read as metres


def test_lwh_from_bounding_box_and_surface_is_l_times_w(tmp_path):
    doc = ezdxf.new(units=units.MM)
    msp = doc.modelspace()
    # floor: 3 m (along y) x 2 m (along x), flat → L is the longer side whatever the axis
    msp.add_3dface([(0, 0, 0), (2000, 0, 0), (2000, 3000, 0), (0, 3000, 0)],
                   dxfattribs={"layer": "FLOOR"})
    # wall panel 4 m long, 0.1 m thick, 2.5 m high: H is shown but not in the surface
    for quad in CUBE:
        msp.add_3dface([(x * 4000, y * 100, z * 2500) for x, y, z in quad],
                       dxfattribs={"layer": "PANEL"})
    q = _measure(tmp_path, doc)
    assert _lwh_area(q["FLOOR"]) == (3, 2, 0, 6)
    assert _lwh_area(q["PANEL"]) == (4, 0.1, 2.5, 0.4)


def test_pieces_on_one_layer_share_one_bounding_box(tmp_path):
    doc = ezdxf.new(units=units.M)
    msp = doc.modelspace()
    for x0 in (0, 9):   # two 1 m tiles, 10 m apart end to end
        msp.add_3dface([(x0, 0, 0), (x0 + 1, 0, 0), (x0 + 1, 1, 0), (x0, 1, 0)],
                       dxfattribs={"layer": "TILE"})
    assert _lwh_area(_measure(tmp_path, doc)["TILE"]) == (10, 1, 0, 10)


def test_take_off_is_written_and_read_back(tmp_path):
    doc = ezdxf.new(units=units.M)
    for quad in CUBE:
        doc.modelspace().add_3dface(quad, dxfattribs={"layer": "WALL"})
    _measure(tmp_path, doc)
    path = tmp_path / "d.takeoff.json"
    assert json.loads(path.read_text()) == [
        {"layer": "WALL", "length_m": 1, "width_m": 1, "height_m": 1, "area_m2": 1}]
    assert read_takeoff(path)[0].area_m2 == 1
    path.write_text('[{"layer": "WALL", "length_m": 1}]')     # older / broken format
    assert read_takeoff(path) is None
