import pytest

from reviewdistill.config import HomeConfig, write_home_config
from reviewdistill.llm.base import get_provider, privacy_warning, resolve_api_key
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.llm.provider import LiteLLMProvider, litellm_model_id


def test_mock_provider_returns_scripted_json():
    provider = MockLLMProvider(scripted_response='{"recommendation":"new"}')
    assert provider.generate("hello") == '{"recommendation":"new"}'


def test_factory_default_requires_config(rd_home, monkeypatch):
    monkeypatch.delenv("REVIEWDISTILL_LLM_PROVIDER", raising=False)
    with pytest.raises(RuntimeError, match="No LLM provider"):
        get_provider()


def test_factory_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("REVIEWDISTILL_LLM_PROVIDER", "nope")
    with pytest.raises(RuntimeError, match="Unknown LLM provider"):
        get_provider()


def test_privacy_warning_for_external_provider():
    message = privacy_warning(provider_name="openai", comment_count=3)
    assert "openai" in message.lower()
    assert "3" in message
    assert "manuscript" in message.lower()


def test_litellm_model_id_prefixes_provider():
    assert litellm_model_id("deepseek", None) == "deepseek/deepseek-chat"
    assert litellm_model_id("openai", "gpt-4o-mini") == "openai/gpt-4o-mini"
    assert litellm_model_id("anthropic", None) == "anthropic/claude-sonnet-4-20250514"
    assert litellm_model_id("openai", "openai/gpt-4o") == "openai/gpt-4o"


def test_factory_selects_deepseek(rd_home, monkeypatch):
    monkeypatch.setenv("REVIEWDISTILL_LLM_PROVIDER", "deepseek")
    provider = get_provider()
    assert isinstance(provider, LiteLLMProvider)
    assert provider.name == "deepseek"
    assert provider.model == "deepseek-chat"


def test_deepseek_requires_api_key(rd_home, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    provider = LiteLLMProvider(name="deepseek", model="deepseek-chat")
    with pytest.raises(RuntimeError, match="api key"):
        provider.generate("hello")


def test_litellm_generate_requests_json_object(rd_home, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    captured: dict = {}

    class _Message:
        content = '{"recommendation":"new"}'

    class _Choice:
        message = _Message()

    class _Response:
        def __init__(self):
            self.choices = [_Choice()]

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _Response()

    import litellm

    monkeypatch.setattr(litellm, "completion", fake_completion)
    out = LiteLLMProvider(name="deepseek", model="deepseek-chat").generate("hello")
    assert out == '{"recommendation":"new"}'
    assert captured["model"] == "deepseek/deepseek-chat"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["api_key"] == "sk-test"
    assert captured["temperature"] == 0
    assert captured["num_retries"] == 3


def test_litellm_errors_become_runtime_error(rd_home, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class Boom(Exception):
        pass

    def boom(**kwargs):
        raise Boom("upstream down")

    import litellm

    monkeypatch.setattr(litellm, "completion", boom)
    provider = LiteLLMProvider(name="openai", model="gpt-4o-mini")
    with pytest.raises(RuntimeError, match="LLM request failed") as caught:
        provider.generate("hello")
    assert "upstream down" not in str(caught.value)


def test_resolve_api_key_ignores_yaml_api_key(rd_home, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from reviewdistill.paths import home_config_path

    home_config_path().write_text("llm:\n  provider: deepseek\n  api_key: sk-from-yaml\n")
    assert resolve_api_key("deepseek") is None


def test_factory_uses_home_provider_and_dotenv(rd_home, monkeypatch):
    monkeypatch.delenv("REVIEWDISTILL_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    write_home_config(HomeConfig(llm_provider="deepseek", llm_model="deepseek-chat"))
    from reviewdistill.paths import home_env_path

    home_env_path().write_text("DEEPSEEK_API_KEY=sk-from-home\n")
    provider = get_provider()
    assert isinstance(provider, LiteLLMProvider)
    assert resolve_api_key("deepseek") == "sk-from-home"


def test_factory_ignores_paper_llm(rd_home, tmp_path, monkeypatch):
    monkeypatch.delenv("REVIEWDISTILL_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    write_home_config(HomeConfig())
    repo = tmp_path / "paper"
    repo.mkdir()
    (repo / ".reviewdistill").mkdir()
    (repo / ".reviewdistill" / "config.yaml").write_text(
        "project:\n  id: p\n  name: paper\n"
        "comments:\n  latex_commands: [myremark]\n"
        "llm:\n  provider: deepseek\n  model: deepseek-chat\n"
    )
    (repo / ".reviewdistill" / ".env").write_text("DEEPSEEK_API_KEY=sk-from-paper\n")
    monkeypatch.chdir(repo)
    with pytest.raises(RuntimeError, match="No LLM provider"):
        get_provider()


def test_resolve_api_key_prefers_process_env_over_home_dotenv(rd_home, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-process")
    write_home_config(HomeConfig(llm_provider="deepseek"))
    from reviewdistill.paths import home_env_path

    home_env_path().write_text("DEEPSEEK_API_KEY=sk-from-home\n")
    assert resolve_api_key("deepseek") == "sk-from-process"


def test_resolve_api_key_uses_effective_provider_dotenv(rd_home, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("REVIEWDISTILL_LLM_PROVIDER", "openai")
    write_home_config(HomeConfig(llm_provider="deepseek", llm_model="deepseek-chat"))
    from reviewdistill.paths import home_env_path

    home_env_path().write_text("DEEPSEEK_API_KEY=sk-deepseek\nOPENAI_API_KEY=sk-openai\n")
    assert get_provider().name == "openai"
    assert resolve_api_key("openai") == "sk-openai"
