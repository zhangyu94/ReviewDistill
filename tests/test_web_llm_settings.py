from fastapi.testclient import TestClient

from reviewdistill.config import home_key_set, write_home_llm
from reviewdistill.paths import home_config_path, home_env_path
from reviewdistill.web.app import create_app


def test_llm_settings_get_returns_key_for_settings(db, rd_home):
    write_home_llm(provider="deepseek", model="deepseek-chat")
    home_env_path().write_text("DEEPSEEK_API_KEY=sk-secret\n")
    body = TestClient(create_app()).get("/api/llm-settings").json()
    assert body == {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "key_set": True,
        "api_key": "sk-secret",
    }
    assert "projects" not in body
    yaml_text = home_config_path().read_text()
    assert "api_key" not in yaml_text


def test_llm_settings_get_empty_home(db, rd_home):
    body = TestClient(create_app()).get("/api/llm-settings").json()
    assert body == {"provider": None, "model": None, "key_set": False, "api_key": None}


def test_llm_settings_get_ignores_process_env_provider(db, rd_home, monkeypatch):
    monkeypatch.setenv("REVIEWDISTILL_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REVIEWDISTILL_LLM_MODEL", "deepseek-chat")
    body = TestClient(create_app()).get("/api/llm-settings").json()
    assert body == {"provider": None, "model": None, "key_set": False, "api_key": None}


def test_llm_settings_get_key_from_home_env_not_process(db, rd_home, monkeypatch):
    write_home_llm(provider="deepseek", model="deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-process")
    body = TestClient(create_app()).get("/api/llm-settings").json()
    assert body == {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "key_set": False,
        "api_key": None,
    }


def test_llm_settings_post_writes_home_yaml_and_env(db, rd_home):
    client = TestClient(create_app())
    response = client.post(
        "/api/llm-settings",
        json={"provider": "deepseek", "model": "deepseek-chat", "api_key": "sk-from-ui"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "key_set": True}
    yaml_text = home_config_path().read_text()
    assert "provider: deepseek" in yaml_text
    assert "api_key" not in yaml_text
    assert "sk-from-ui" in home_env_path().read_text()
    gitignore = (rd_home / ".gitignore").read_text()
    assert ".env" in gitignore
    assert home_key_set("deepseek") is True


def test_llm_settings_post_blank_key_keeps_existing(db, rd_home):
    write_home_llm(provider="deepseek", model="deepseek-chat")
    home_env_path().write_text("DEEPSEEK_API_KEY=sk-keep\n")
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"provider": "deepseek", "model": "deepseek-chat", "api_key": ""},
    )
    assert response.status_code == 200
    assert "sk-keep" in home_env_path().read_text()


def test_llm_settings_post_new_provider_without_key_is_400(db, rd_home):
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"provider": "openai", "model": "gpt-4o-mini"},
    )
    assert response.status_code == 400


def test_llm_settings_post_unknown_provider_is_400(db, rd_home):
    response = TestClient(create_app()).post(
        "/api/llm-settings",
        json={"provider": "mock", "model": "x", "api_key": "sk"},
    )
    assert response.status_code == 400
