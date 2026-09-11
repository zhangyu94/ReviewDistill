from fastapi.testclient import TestClient

from reviewdistill.paths import data_location
from reviewdistill.web.app import create_app


def test_paths_api_returns_home_and_comments(db):
    body = TestClient(create_app()).get("/api/paths").json()
    assert body == data_location()
    assert "home_env" not in body
    assert body["comments"].endswith("comments.jsonl")
