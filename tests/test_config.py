from reviewdistill.config import (
    HomeConfig,
    ProjectConfig,
    load_home_config,
    load_llm_config,
    upsert_env_var,
    write_home_config,
    write_project_config,
)
from reviewdistill.paths import home_config_path, home_env_path, project_config_path


def test_load_home_config_ignores_yaml_api_key(rd_home):
    home_config_path().write_text(
        "llm:\n  provider: deepseek\n  model: deepseek-chat\n  api_key: sk-from-yaml\n"
    )
    config = load_home_config()
    assert config.llm_provider == "deepseek"
    assert config.llm_model == "deepseek-chat"
    assert config.llm_api_key is None


def test_write_home_config_does_not_write_api_key(rd_home):
    write_home_config(
        HomeConfig(llm_provider="openai", llm_model="gpt-4o-mini", llm_api_key="sk-written")
    )
    config = load_home_config()
    assert config.llm_api_key is None
    assert "api_key" not in home_config_path().read_text()


def test_load_llm_config_reads_home_yaml_and_dotenv(rd_home):
    write_home_config(HomeConfig(llm_provider="deepseek", llm_model="deepseek-chat"))
    home_env_path().write_text("DEEPSEEK_API_KEY=sk-from-home\n")
    config = load_llm_config()
    assert config.llm_provider == "deepseek"
    assert config.llm_model == "deepseek-chat"
    assert config.llm_api_key == "sk-from-home"


def test_load_llm_config_ignores_paper_yaml_and_dotenv(rd_home, tmp_path, monkeypatch):
    write_home_config(HomeConfig(llm_provider="openai", llm_model="gpt-4o-mini"))
    home_env_path().write_text("OPENAI_API_KEY=sk-home\n")
    repo = tmp_path / "paper"
    repo.mkdir()
    monkeypatch.chdir(repo)
    write_project_config(repo, ProjectConfig(id="p", name="paper", latex_commands=["myremark"]))
    path = repo / ".reviewdistill" / "config.yaml"
    path.write_text(path.read_text() + "llm:\n  provider: deepseek\n  model: deepseek-chat\n")
    (repo / ".reviewdistill" / ".env").write_text("DEEPSEEK_API_KEY=sk-from-paper\n")
    config = load_llm_config()
    assert config.llm_provider == "openai"
    assert config.llm_model == "gpt-4o-mini"
    assert config.llm_api_key == "sk-home"


def test_write_project_config_drops_llm_block(rd_home, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    write_project_config(repo, ProjectConfig(id="p", name="paper"))
    path = project_config_path(repo)
    path.write_text(path.read_text() + "llm:\n  provider: deepseek\n  api_key: sk-keep\n")
    write_project_config(repo, ProjectConfig(id="p", name="renamed"))
    text = path.read_text()
    assert "llm:" not in text
    assert "renamed" in text


def test_upsert_env_var_sets_one_key_and_keeps_others(tmp_path):
    path = tmp_path / ".env"
    path.write_text("DEEPSEEK_API_KEY=sk-old\nOPENAI_API_KEY=sk-keep\n")
    upsert_env_var(path, "DEEPSEEK_API_KEY", "sk-new")
    text = path.read_text()
    assert "DEEPSEEK_API_KEY=sk-new" in text
    assert "OPENAI_API_KEY=sk-keep" in text


def test_write_home_llm_sets_provider_without_yaml_key(rd_home):
    from reviewdistill.config import write_home_llm

    write_home_llm(provider="deepseek", model="deepseek-chat")
    text = home_config_path().read_text()
    assert "provider: deepseek" in text
    assert "model: deepseek-chat" in text
    assert "api_key" not in text


def test_home_key_set_reads_home_dotenv_not_process_env(rd_home, monkeypatch):
    from reviewdistill.config import home_key_set, write_home_llm

    write_home_llm(provider="deepseek", model="deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-process")
    assert home_key_set("deepseek") is False
    home_env_path().write_text("DEEPSEEK_API_KEY=sk-file\n")
    assert home_key_set("deepseek") is True
