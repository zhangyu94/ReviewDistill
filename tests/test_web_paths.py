from fastapi.testclient import TestClient

from reviewdistill.web.app import create_app


def test_paths_api_returns_home_and_comments(db):
    body = TestClient(create_app()).get("/api/paths").json()
    assert "home_env" not in body
    assert body["comments"].endswith("comments.jsonl")
    assert body["file_url"].startswith("file://")


def test_paths_api_post_uses_new_home(db, tmp_path):
    dest = tmp_path / "other-home"
    client = TestClient(create_app())
    response = client.post("/api/paths", json={"home": str(dest)})
    assert response.status_code == 200
    body = response.json()
    assert body["home"] == str(dest.resolve())
    assert dest.is_dir()
    assert client.get("/api/paths").json()["home"] == str(dest.resolve())


def test_paths_api_post_blank_is_400(db):
    before = TestClient(create_app()).get("/api/paths").json()["home"]
    response = TestClient(create_app()).post("/api/paths", json={"home": "  "})
    assert response.status_code == 400
    assert TestClient(create_app()).get("/api/paths").json()["home"] == before


def test_paths_api_post_file_is_400(db, tmp_path):
    target = tmp_path / "not-a-folder"
    target.write_text("x")
    response = TestClient(create_app()).post("/api/paths", json={"home": str(target)})
    assert response.status_code == 400
    assert "not a folder" in response.json()["detail"]


def test_paths_api_open_opens_home(db, monkeypatch):
    opened: list[bool] = []
    monkeypatch.setattr(
        "reviewdistill.web.api.open_data_folder",
        lambda: opened.append(True),
    )
    response = TestClient(create_app()).post("/api/paths/open")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert opened == [True]


def test_paths_api_choose_returns_picked_folder(db, tmp_path, monkeypatch):
    picked = tmp_path / "picked"
    picked.mkdir()
    monkeypatch.setattr(
        "reviewdistill.web.api.choose_data_folder",
        lambda: picked,
    )
    response = TestClient(create_app()).post("/api/paths/choose")
    assert response.status_code == 200
    assert response.json() == {"home": str(picked)}


def test_paths_api_choose_cancel_keeps_null(db, monkeypatch):
    monkeypatch.setattr("reviewdistill.web.api.choose_data_folder", lambda: None)
    response = TestClient(create_app()).post("/api/paths/choose")
    assert response.status_code == 200
    assert response.json() == {"home": None}


def test_paths_api_choose_does_not_switch_home(db, tmp_path, monkeypatch):
    before = TestClient(create_app()).get("/api/paths").json()["home"]
    picked = tmp_path / "picked"
    picked.mkdir()
    monkeypatch.setattr("reviewdistill.web.api.choose_data_folder", lambda: picked)
    TestClient(create_app()).post("/api/paths/choose")
    assert TestClient(create_app()).get("/api/paths").json()["home"] == before
