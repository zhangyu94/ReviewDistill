from reviewdistill.cli.init import init_project
from reviewdistill.config import (
    HomeConfig,
    ProjectConfig,
    default_llm_model,
    default_registered_project_id,
    llm_selected_payload,
    load_dotenv_values,
    load_home_config,
    load_llm_config,
    paper_key_set,
    upsert_env_var,
    write_home_config,
    write_project_config,
    write_project_llm,
)
from reviewdistill.paths import home_config_path, project_config_path, project_env_path


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


def test_load_llm_config_uses_project_yaml_over_home(rd_home, tmp_path, monkeypatch):
    write_home_config(HomeConfig(llm_provider="mock"))
    repo = tmp_path / "paper"
    repo.mkdir()
    monkeypatch.chdir(repo)
    write_project_config(
        repo,
        ProjectConfig(id="p", name="paper", latex_commands=["myremark"]),
    )
    path = repo / ".reviewdistill" / "config.yaml"
    path.write_text(
        path.read_text()
        + "llm:\n  provider: deepseek\n  model: deepseek-chat\n"
    )
    (repo / ".reviewdistill" / ".env").write_text("DEEPSEEK_API_KEY=sk-from-dotenv\n")
    config = load_llm_config()
    assert config.llm_provider == "deepseek"
    assert config.llm_model == "deepseek-chat"
    assert config.llm_api_key == "sk-from-dotenv"


def test_write_project_config_preserves_llm_block_without_api_key(rd_home, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    write_project_config(repo, ProjectConfig(id="p", name="paper"))
    path = repo / ".reviewdistill" / "config.yaml"
    path.write_text(
        path.read_text() + "llm:\n  provider: deepseek\n  api_key: sk-keep\n"
    )
    write_project_config(repo, ProjectConfig(id="p", name="renamed"))
    text = path.read_text()
    assert "provider: deepseek" in text
    assert "api_key" not in text
    assert "renamed" in text


def test_load_dotenv_values_parses_keys(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# comment\n"
        "export DEEPSEEK_API_KEY=sk-unquoted\n"
        "OPENAI_API_KEY=\"sk-quoted\"\n"
        "\n"
        "ANTHROPIC_API_KEY='sk-single'\n"
    )
    values = load_dotenv_values(path)
    assert values["DEEPSEEK_API_KEY"] == "sk-unquoted"
    assert values["OPENAI_API_KEY"] == "sk-quoted"
    assert values["ANTHROPIC_API_KEY"] == "sk-single"


def test_load_llm_config_reads_key_from_project_dotenv(rd_home, tmp_path, monkeypatch):
    repo = tmp_path / "paper"
    repo.mkdir()
    monkeypatch.chdir(repo)
    write_project_config(repo, ProjectConfig(id="p", name="paper", latex_commands=["myremark"]))
    path = repo / ".reviewdistill" / "config.yaml"
    path.write_text(path.read_text() + "llm:\n  provider: deepseek\n  model: deepseek-chat\n")
    (repo / ".reviewdistill" / ".env").write_text("DEEPSEEK_API_KEY=sk-from-dotenv\n")
    config = load_llm_config()
    assert config.llm_provider == "deepseek"
    assert config.llm_api_key == "sk-from-dotenv"


def test_default_llm_model_matches_known_providers():
    assert default_llm_model("deepseek") == "deepseek-chat"
    assert default_llm_model("openai") == "gpt-4o-mini"
    assert default_llm_model("anthropic") == "claude-sonnet-4-20250514"


def test_upsert_env_var_sets_one_key_and_keeps_others(tmp_path):
    path = tmp_path / ".env"
    path.write_text("DEEPSEEK_API_KEY=sk-old\nOPENAI_API_KEY=sk-keep\n")
    upsert_env_var(path, "DEEPSEEK_API_KEY", "sk-new")
    text = path.read_text()
    assert "DEEPSEEK_API_KEY=sk-new" in text
    assert "OPENAI_API_KEY=sk-keep" in text


def test_write_project_llm_sets_provider_and_strips_yaml_api_key(rd_home, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    write_project_config(repo, ProjectConfig(id="p", name="paper"))
    path = project_config_path(repo)
    path.write_text(path.read_text() + "llm:\n  provider: openai\n  api_key: sk-yaml\n")
    write_project_llm(repo, provider="deepseek", model="deepseek-chat")
    text = path.read_text()
    assert "provider: deepseek" in text
    assert "model: deepseek-chat" in text
    assert "api_key" not in text


def test_paper_key_set_reads_dotenv_not_process_env(rd_home, tmp_path, monkeypatch):
    repo = tmp_path / "paper"
    repo.mkdir()
    write_project_config(repo, ProjectConfig(id="p", name="paper"))
    write_project_llm(repo, provider="deepseek", model="deepseek-chat")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-process")
    assert paper_key_set(repo, "deepseek") is False
    project_env_path(repo).write_text("DEEPSEEK_API_KEY=sk-file\n")
    assert paper_key_set(repo, "deepseek") is True


def test_default_registered_project_id_uses_cwd_paper(db, tmp_path, monkeypatch):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    monkeypatch.chdir(repo)
    pid = default_registered_project_id()
    assert pid is not None
    row = llm_selected_payload(pid)
    assert row is not None
    assert row["provider"] is None
    assert row["key_set"] is False
    assert "api_key" not in row
