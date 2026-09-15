from __future__ import annotations

import os
from typing import Protocol

from reviewdistill.config import PROVIDER_ENV_KEYS, HomeConfig, api_key_from_dotenv, load_llm_config
from reviewdistill.paths import home_env_path


class LLMProvider(Protocol):
    name: str

    def generate(self, prompt: str) -> str:
        ...


_ENV_KEYS = PROVIDER_ENV_KEYS


def effective_llm_config() -> HomeConfig:
    """Home files only. Process-env provider/model overrides live in ``get_provider``."""
    return load_llm_config()


def resolve_api_key(provider_name: str) -> str | None:
    env_name = _ENV_KEYS.get(provider_name)
    if env_name:
        value = os.environ.get(env_name)
        if value:
            return value
    return api_key_from_dotenv(home_env_path(), provider_name)


def require_api_key(provider_name: str) -> str:
    key = resolve_api_key(provider_name)
    if key:
        return key
    env_name = _ENV_KEYS.get(provider_name, "the provider environment variable")
    raise RuntimeError(
        f"No api key configured for {provider_name}. "
        f"Set {env_name} in the process environment or the ReviewDistill folder's .env."
    )


def privacy_warning(*, provider_name: str, comment_count: int) -> str:
    return (
        f"Sending {comment_count} review comment(s) plus nearby manuscript context "
        f"and candidate label definitions to external LLM provider '{provider_name}'. "
        "The rest of the repository is not sent."
    )


def get_provider() -> LLMProvider:
    """``REVIEWDISTILL_LLM_PROVIDER`` / ``_MODEL`` override home YAML. No paper scan."""
    env_name = os.environ.get("REVIEWDISTILL_LLM_PROVIDER")
    config = effective_llm_config()
    name = (env_name or config.llm_provider or "").lower()
    if not name:
        raise RuntimeError(
            "No LLM provider configured. Set llm.provider in the ReviewDistill "
            "folder's config.yaml (Settings → Assistant), and put the API key in that folder's .env."
        )
    model = os.environ.get("REVIEWDISTILL_LLM_MODEL") or config.llm_model
    if name == "mock":
        from reviewdistill.llm.mock import MockLLMProvider

        return MockLLMProvider()
    if name in {"openai", "anthropic", "deepseek"}:
        from reviewdistill.llm.provider import DEFAULT_MODELS, LiteLLMProvider

        return LiteLLMProvider(name=name, model=model or DEFAULT_MODELS[name])
    raise RuntimeError(f"Unknown LLM provider: {name}")
