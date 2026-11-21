from fastapi.testclient import TestClient

from src import server


def test_routes(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(server.pipeline, "run_pipeline", lambda *a: calls.append(a))
    out = tmp_path / "out"
    client = TestClient(server.create_app(tmp_path / "up", out))

    assert "DWG" in client.get("/").text
    assert client.get("/api/catalog").json() == {"models": [], "errors": {}}
    (out / "catalog.json").write_text('{"models": [{"name": "a"}], "errors": {}}')
    (out / "a.glb").write_bytes(b"glb")
    assert client.post("/api/refresh").json()["models"] == [{"name": "a"}]
    assert len(calls) == 1
    assert client.get("/models/a.glb?v=1").content == b"glb"
