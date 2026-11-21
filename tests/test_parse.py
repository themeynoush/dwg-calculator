from src.nodes.parse import parse
from src.state import PipelineState


def test_parse_valid_and_invalid(tmp_path, dxf_path):
    garbage = tmp_path / "garbage.dxf"
    garbage.write_bytes(b"\x00\x01 garbage")
    state = PipelineState(uploads_dir=str(tmp_path), output_dir=str(tmp_path),
                          dxf_paths={"cube": str(dxf_path), "garbage": str(garbage)})
    result = parse(state)
    assert list(result["documents"]) == ["cube"]
    assert "garbage" in result["errors"]


def test_sanitize_drops_zero_handles_only():
    from src.nodes.parse import sanitize
    raw = b"  0\nENDBLK\n  5\n0\n  5\n1F\n 10\n0\n"
    assert sanitize(raw) == b"  0\nENDBLK\n  5\n1F\n 10\n0"
