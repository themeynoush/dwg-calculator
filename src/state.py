"""Typed data models: every node reads/writes this state."""
from typing import Any

from pydantic import BaseModel, ConfigDict


class DwgFile(BaseModel):
    """A DWG file discovered in the uploads folder."""
    name: str          # stem, used as the model id ("house" for house.dwg)
    path: str


class Geometry(BaseModel):
    """Raw 3D geometry extracted from one drawing (DXF coordinates, Z-up)."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []          # triangles, indices into vertices
    segments: list[tuple[int, int]] = []            # line segments, indices into vertices
    face_layers: list[str] = []                     # CAD layer (= material) of each triangle
    layer_colors: dict[str, tuple[int, int, int]] = {}  # layer name: RGB 0-255

    @property
    def is_empty(self) -> bool:
        return not self.faces and not self.segments


class CatalogEntry(BaseModel):
    """One item of the sidebar menu."""
    name: str
    model_url: str     # URL of the .glb served to the browser
    source: str        # original .dwg file name
    size_bytes: int


class PipelineState(BaseModel):
    """What flows through the LangGraph nodes."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uploads_dir: str
    output_dir: str
    force: bool = False                      # reprocess files even if a .glb is up to date
    pending: list[DwgFile] = []              # scan → files needing processing
    dxf_paths: dict[str, str] = {}           # convert → name: path to .dxf
    documents: dict[str, Any] = {}           # parse → name: ezdxf Drawing
    geometries: dict[str, Geometry] = {}     # extract_geometry → name: Geometry
    exported: list[str] = []                 # export_gltf → names written as .glb
    errors: dict[str, str] = {}              # name: reason the file was skipped
    catalog: list[CatalogEntry] = []         # build_catalog → sidebar entries
