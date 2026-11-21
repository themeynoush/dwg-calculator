# DWG 3D Viewer

Browse `.dwg` files and inspect them in 3D from your browser — no AutoCAD needed.
Drop files in `uploads/`, run one command, open `http://localhost:8000`: the left
menu shows a preview of each file; click one to rotate, zoom and pan it in 3D.

```
scan → convert → parse → extract_geometry → export_gltf → build_catalog
```

## Quick start

```bash
brew install libredwg          # once, provides dwg2dxf
uv sync
# put your .dwg files in uploads/
uv run python -m src.main      # then open http://localhost:8000
```

---

## How it was built — step by step

### Step 1 — Define the requirements
- Input: `.dwg` files dropped in an `uploads/` folder.
- Output: a local web page — left sidebar with a preview per file, 3D viewer in the centre.
- Constraint: the end user needs no CAD software, only a browser.
- Architecture: six single-responsibility nodes, one typed state, LangGraph
  (same pattern as `jean-infra-opt-ai`).

### Step 2 — Choose the tools
| Need | Choice | Why |
|---|---|---|
| Read DWG | **LibreDWG** (`dwg2dxf`) | DWG is closed; Python only reads DXF. Open source, `brew install` |
| Read DXF | **ezdxf** | Mature, has a recover mode and block expansion (`disassemble`) |
| 3D file for the browser | **glTF (.glb)** via **trimesh** | Browser-native 3D format, supports faces and lines |
| Orchestration | **LangGraph** + **Pydantic** | Explicit node chain with a typed contract |
| Web server | **FastAPI** + uvicorn | Serves page, catalog, models |
| Viewer | **three.js** (`GLTFLoader`, `OrbitControls`) | Rotate / zoom / pan in any browser |
| Quality | **pytest, ruff, mypy, GitHub Actions** | Same as the reference project |

### Step 3 — Set up the project
```bash
brew install libredwg
uv init --name dwg-viewer --python 3.12
uv add langgraph pydantic ezdxf numpy trimesh fastapi "uvicorn[standard]"
uv add --dev pytest ruff mypy httpx
```

### Step 4 — Define the shared state (`src/state.py`)
- `DwgFile` — a file found in `uploads/`.
- `Geometry` — vertices, triangles, line segments.
- `CatalogEntry` — one sidebar item (name, model URL, source file, size).
- `PipelineState` — what flows through the nodes; each node fills one field
  and adds to `errors` when a file must be skipped.

### Step 5 — Write the six nodes (`src/nodes/`)
| # | Node | Role |
|---|---|---|
| 1 | `scan` | List `*.dwg` (case-insensitive); skip files whose `.glb` is newer than the DWG |
| 2 | `convert` | DWG → DXF with `dwg2dxf`; clear error if LibreDWG is missing |
| 3 | `parse` | Load DXF with ezdxf in recover mode, after repairing LibreDWG quirks |
| 4 | `extract_geometry` | Expand blocks; 3D faces/meshes → triangles, lines/arcs/curves → segments |
| 5 | `export_gltf` | Centre, scale to unit size, Z-up → Y-up, write one `.glb` per file |
| 6 | `build_catalog` | Write `output/catalog.json` (models + per-file errors) for the sidebar |

Rule for every node: a bad file is **logged and skipped**, never fatal.

### Step 6 — Verify the riskiest part early
Before going further, checked with a throwaway script that:
- trimesh exports line segments (`Path3D`) to `.glb` and reads them back ✔
- LibreDWG can produce a real DWG from a DXF (`dxf2dwg`) — used for tests ✔

### Step 7 — Wire the graph (`src/graph.py`, `src/pipeline.py`)
- `build_graph()` chains the six nodes `START → … → END`.
- `run_pipeline(uploads_dir, output_dir, force)` runs it once and returns the catalog.

### Step 8 — Build the web server (`src/server.py`, `src/main.py`)
| Route | Purpose |
|---|---|
| `GET /` | The viewer page |
| `GET /api/catalog` | Content of `catalog.json` |
| `POST /api/refresh` | Re-run the pipeline (new uploads) |
| `GET /models/*.glb` | The 3D models |

`main.py` runs the pipeline at startup, then serves on port 8000 (`--port`, `--force`).

### Step 9 — Build the viewer (`static/index.html`)
- Single HTML file, three.js loaded from a CDN (no build step).
- **Sidebar**: Refresh button, one card per model, list of failed files with reasons.
- **Thumbnails**: rendered in the browser by one hidden WebGL renderer
  (isometric view → PNG), so the server needs no graphics stack.
- **Centre**: OrbitControls, lights, ground grid, camera auto-fitted to the model.
- Model URLs carry `?v=<mtime>` so a regenerated model is never served stale.

### Step 10 — Test each node (`tests/`)
Fixtures are generated with ezdxf (a cube of `3DFACE`s, a line, a block `INSERT`,
text), and turned into a real DWG with `dxf2dwg` when LibreDWG is installed.

| Test file | Checks |
|---|---|
| `test_scan` | finds `.dwg`/`.DWG`, ignores other files, incremental skip, `--force` |
| `test_convert` | missing binary message, real DWG conversion, corrupt file skipped |
| `test_parse` | valid DXF, garbage skipped, handle repair |
| `test_extract_geometry` | cube → 12 triangles, blocks expanded, text skipped, empty → error |
| `test_export_gltf` | centring, scaling, Z-up → Y-up, `.glb` reloads |
| `test_build_catalog` | only converted DWGs listed, errors written |
| `test_server` | all routes (pipeline mocked) |
| `test_pipeline` | full DWG → catalog run, then incremental re-run |

### Step 11 — Fix what the tests revealed
1. **LibreDWG writes handle `0`** on some entities (e.g. `ENDBLK`), which ezdxf
   rejects even in recover mode → `parse.sanitize()` drops those tags so ezdxf
   assigns fresh handles.
2. **3D faces came out as outlines**: ezdxf's `disassemble` returns only their
   border → `extract_geometry` triangulates `3DFACE` directly.

### Step 12 — Quality gates and CI
```bash
uv run ruff check .
uv run mypy src
uv run pytest -q
```
`.github/workflows/ci.yml` runs the same three on every push
(LibreDWG tests are skipped automatically when it is not installed).

### Step 13 — End-to-end check
Put a DWG in `uploads/`, start the app, then:
```bash
curl localhost:8000/api/catalog              # lists the model
curl -I localhost:8000/models/sample.glb     # 200 OK
```
Finally open `http://localhost:8000` and check the thumbnails and 3D interaction.

---

## Project layout
```
src/
  state.py            shared typed state
  graph.py            LangGraph wiring
  pipeline.py         run the graph once
  server.py           FastAPI routes
  main.py             entrypoint
  nodes/              the six nodes
static/index.html     the viewer
uploads/              your .dwg files
output/               generated .dxf, .glb, catalog.json (git-ignored)
tests/                one test file per node + server + end-to-end
```

## Limitations
- `3DSOLID` / `REGION` / `BODY` (ACIS solids) are encrypted in DWG and are not rendered;
  meshes, 3D faces, polyface meshes and wireframes are.
- Text, dimensions and hatches are skipped.
- The browser needs internet access to load three.js from the CDN.
