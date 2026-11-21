"""Extract node: turn DXF entities into triangles and line segments.

ezdxf's `disassemble` module expands block references (INSERT) recursively and
converts entities into meshes (MESH, POLYFACE, POLYMESH) or polyline
approximations (LINE, ARC, CIRCLE, SPLINE, ...). 3DFACE is handled directly:
ezdxf would only return its outline, but it is a filled surface.
ACIS bodies (3DSOLID, REGION, BODY) are encrypted and cannot be tessellated.

Each triangle remembers its CAD layer: drawings use one layer per material
(marble, mirror, wallpaper...), so the layer colour becomes the material colour.
"""
import logging

from ezdxf import colors, disassemble
from ezdxf.entities import Face3d

from src.state import Geometry, PipelineState

logger = logging.getLogger(__name__)

# Text is rendered as outline paths by ezdxf — noisy in 3D, so skip it.
SKIPPED_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "HATCH", "VIEWPORT"}
UNSUPPORTED_TYPES = {"3DSOLID", "REGION", "BODY", "SURFACE"}


def _resolve_color(entity, doc) -> tuple[str, tuple[int, int, int]]:
    """Layer name and RGB of an entity (true colour > ACI > layer colour)."""
    layer = entity.dxf.get("layer", "0")
    if entity.dxf.hasattr("true_color"):
        return layer, colors.int2rgb(entity.dxf.true_color)
    aci = entity.dxf.get("color", colors.BYLAYER)
    if aci in (colors.BYLAYER, colors.BYBLOCK) and doc is not None and layer in doc.layers:
        aci = abs(doc.layers.get(layer).color)   # negative = layer switched off
    if not 1 <= aci <= 255:
        aci = 7
    return layer, colors.aci2rgb(aci)


class _Builder:
    def __init__(self, doc=None) -> None:
        self.geometry = Geometry()
        self.doc = doc
        self.layer = "0"

    def use(self, entity) -> None:
        """Make the next faces belong to the layer of `entity`."""
        self.layer, rgb = _resolve_color(entity, self.doc)
        self.geometry.layer_colors.setdefault(self.layer, (rgb[0], rgb[1], rgb[2]))

    def _add_triangle(self, a: int, b: int, c: int) -> None:
        self.geometry.faces.append((a, b, c))
        self.geometry.face_layers.append(self.layer)

    def _add_vertices(self, vertices) -> int:
        offset = len(self.geometry.vertices)
        self.geometry.vertices.extend((v.x, v.y, v.z) for v in vertices)
        return offset

    def add_mesh(self, mesh) -> None:
        offset = self._add_vertices(mesh.vertices)
        for face in mesh.faces:
            # fan triangulation: fine for the convex quads/polygons used in CAD meshes
            for i in range(1, len(face) - 1):
                self._add_triangle(offset + face[0], offset + face[i], offset + face[i + 1])

    def add_face(self, vertices) -> None:
        points = list(vertices)
        if len(points) == 4 and points[2].isclose(points[3]):
            points = points[:3]    # a 3DFACE with 4th vertex == 3rd is a triangle
        offset = self._add_vertices(points)
        for i in range(1, len(points) - 1):
            self._add_triangle(offset, offset + i, offset + i + 1)

    def add_polyline(self, vertices) -> None:
        points = list(vertices)
        if len(points) < 2:
            return
        offset = self._add_vertices(points)
        self.geometry.segments.extend((offset + i, offset + i + 1) for i in range(len(points) - 1))


def _extract(doc) -> tuple[Geometry, set[str]]:
    builder, unsupported = _Builder(doc), set()
    entities = []
    for e in disassemble.recursive_decompose(doc.modelspace()):
        kind = e.dxftype()
        if kind in UNSUPPORTED_TYPES:
            unsupported.add(kind)
        elif isinstance(e, Face3d):
            builder.use(e)
            builder.add_face(e.wcs_vertices())
        elif kind not in SKIPPED_TYPES:
            entities.append(e)

    for primitive in disassemble.to_primitives(entities):
        if primitive.is_empty:
            continue
        if primitive.mesh is not None:
            builder.use(primitive.entity)
            builder.add_mesh(primitive.mesh)
        else:
            builder.add_polyline(primitive.vertices())
    return builder.geometry, unsupported


def extract_geometry(state: PipelineState) -> dict:
    geometries, errors = {}, dict(state.errors)
    for name, doc in state.documents.items():
        geometry, unsupported = _extract(doc)
        if unsupported:
            logger.warning("%s: unsupported entities ignored: %s", name, sorted(unsupported))
        if geometry.is_empty:
            errors[name] = "extract: no displayable geometry"
            logger.warning("Skipping %s: no displayable geometry", name)
            continue
        logger.info("%s: %d triangles, %d segments",
                    name, len(geometry.faces), len(geometry.segments))
        geometries[name] = geometry
    return {"geometries": geometries, "errors": errors}
