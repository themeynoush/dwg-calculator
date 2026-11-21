"""Parse node: load each DXF with ezdxf, recovering from minor corruption."""
import io
import logging
from pathlib import Path

import ezdxf
from ezdxf import recover

from src.state import PipelineState

logger = logging.getLogger(__name__)

HANDLE_CODES = {b"5", b"105"}


def sanitize(raw: bytes) -> bytes:
    """Drop handle tags with value 0 that LibreDWG emits (e.g. on ENDBLK).

    ezdxf rejects handle 0 even in recover mode; without the tag it assigns a
    fresh handle. DXF is a sequence of (group code, value) line pairs.
    """
    lines = raw.splitlines()
    out = []
    for i in range(0, len(lines) - 1, 2):
        code, value = lines[i].strip(), lines[i + 1].strip()
        if code in HANDLE_CODES and value == b"0":
            continue
        out += [lines[i], lines[i + 1]]
    out += lines[len(lines) - len(lines) % 2:]   # keep a trailing unpaired line
    return b"\n".join(out)


def parse(state: PipelineState) -> dict:
    """Invalid files are logged and skipped, not fatal."""
    documents, errors = {}, dict(state.errors)
    for name, path in state.dxf_paths.items():
        try:
            raw = sanitize(Path(path).read_bytes())
            doc, auditor = recover.read(io.BytesIO(raw))
        except (OSError, ValueError, ezdxf.DXFError) as exc:
            errors[name] = f"parse: {exc}"
            logger.warning("Skipping %s: invalid DXF (%s)", name, exc)
            continue
        if auditor.has_errors:
            logger.info("%s: %d DXF error(s) auto-fixed", name, len(auditor.errors))
        documents[name] = doc
    return {"documents": documents, "errors": errors}
