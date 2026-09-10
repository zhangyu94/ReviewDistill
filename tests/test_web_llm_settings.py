from fastapi.testclient import TestClient

from reviewdistill.cli.init import init_project
from reviewdistill.config import paper_key_set, write_project_llm
from reviewdistill.paths import project_config_path, project_env_path
from reviewdistill.web.app import create_app


def test_llm_settings_get_lists_paper_and_omits_secret(db, tmp_path, monkeypatch):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    write_project_llm(repo, provider="deepseek", model="deepseek-chat")
    project_env_path(repo).write_text("DEEPSEEK_API_KEY=sk-secret\n")
    monkeypatch.chdir(repo)
    body = TestClient(create_app()).get("/api/llm-settings").json()
    assert body["default_project_id"]
    assert body["projects"][0]["name"] == "paper-01"
    assert body["selected"]["provider"] == "deepseek"
    assert body["selected"]["key_set"] is True
    dumped = str(body)
    assert "sk-secret" not in dumped
    assert "api_key" not in dumped


def test_llm_settings_get_by_project_id(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    client = TestClient(create_app())
    listed = client.get("/api/llm-settings").json()
    pid = listed["projects"][0]["id"]
    body = client.get("/api/llm-settings", params={"project_id": pid}).json()
    assert body["selected"]["project_id"] == pid
    assert body["selected"]["provider"] is None


def test_llm_settings_get_unknown_project_is_404(db):
    client = TestClient(create_app())
    response = client.get("/api/llm-settings", params={"project_id": "missing"})
    assert response.status_code == 404


def test_llm_settings_post_writes_yaml_and_env(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    pid = TestClient(create_app()).get("/api/llm-settings").json()["projects"][0]["id"]
    client = TestClient(create_app())
    response = client.post(
        "/api/llm-settings",
        json={
            "project_id": pid,
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "sk-from-ui",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "key_set": True}
    assert "sk-from-ui" not in str(response.json())
    yaml_text = project_config_path(repo).read_text()
    assert "provider: deepseek" in yaml_text
    assert "api_key" not in yaml_text
    assert "sk-from-ui" in project_env_path(repo).read_text()
    gitignore = (repo / ".reviewdistill" / ".gitignore").read_text()
    assert ".env" in gitignore
    assert paper_key_set(repo, "deepseek") is True


def test_llm_settings_post_blank_key_keeps_existing(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    write_project_llm(repo, provider="deepseek", model="deepseek-chat")
    project_env_path(repo).write_text("DEEPSEEK_API_KEY=sk-keep\n")
    pid = TestClient(create_app()).get("/api/llm-settings").json()["projects"][0]["id"]
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"project_id": pid, "provider": "deepseek", "model": "deepseek-chat", "api_key": ""},
    )
    assert response.status_code == 200
    assert "sk-keep" in project_env_path(repo).read_text()


def test_llm_settings_post_new_provider_without_key_is_400(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    pid = TestClient(create_app()).get("/api/llm-settings").json()["projects"][0]["id"]
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"project_id": pid, "provider": "openai", "model": "gpt-4o-mini"},
    )
    assert response.status_code == 400


def test_llm_settings_post_unknown_provider_is_400(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    pid = TestClient(create_app()).get("/api/llm-settings").json()["projects"][0]["id"]
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"project_id": pid, "provider": "mock", "model": "x", "api_key": "sk"},
    )
    assert response.status_code == 400


def test_llm_settings_post_unknown_project_is_404(db):
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"project_id": "missing", "provider": "deepseek", "model": "deepseek-chat", "api_key": "sk"},
    )
    assert response.status_code == 404
