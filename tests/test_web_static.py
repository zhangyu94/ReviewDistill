from fastapi.testclient import TestClient

from reviewdistill.web.app import create_app


def test_spa_fallback_serves_index(tmp_path, db):
    (tmp_path / "index.html").write_text("<html>studio-index</html>")
    (tmp_path / "asset.txt").write_text("asset-body")
    client = TestClient(create_app(static_dir=tmp_path))
    missing = client.get("/missing-spa-path")
    assert missing.status_code == 200
    assert "studio-index" in missing.text
    asset = client.get("/asset.txt")
    assert asset.status_code == 200
    assert asset.text == "asset-body"


def test_missing_index_is_503_on_unknown_path(tmp_path, db):
    empty = tmp_path / "empty"
    empty.mkdir()
    client = TestClient(create_app(static_dir=empty))
    response = client.get("/missing-spa-path")
    assert response.status_code == 503
    assert "pip install -e" in response.json()["detail"]


def test_root_is_spa_when_index_exists(tmp_path, db):
    (tmp_path / "index.html").write_text("<html>studio-index</html>")
    client = TestClient(create_app(static_dir=tmp_path))
    response = client.get("/")
    assert response.status_code == 200
    assert "studio-index" in response.text
    api = client.get("/api/inbox")
    assert api.status_code == 200
    assert api.headers["content-type"].startswith("application/json")
