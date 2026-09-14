from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import dotenv_values

from reviewdistill.paths import (
    home_config_path,
    home_env_path,
    project_config_path,
)

PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

LLM_SETTINGS_PROVIDERS = ("deepseek", "openai", "anthropic")

_DEFAULT_LLM_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "deepseek": "deepseek-chat",
}


def default_llm_model(provider: str) -> str:
    return _DEFAULT_LLM_MODELS[provider.lower()]


@dataclass
class HomeConfig:
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


def load_dotenv_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for key, value in dotenv_values(path).items():
        if key and value is not None:
            values[key] = value
    return values


def api_key_from_dotenv(env_path: Path, provider: str | None) -> str | None:
    if not provider:
        return None
    env_name = PROVIDER_ENV_KEYS.get(provider.lower())
    if not env_name:
        return None
    return load_dotenv_values(env_path).get(env_name)


def with_home_dotenv(config: HomeConfig) -> HomeConfig:
    key = api_key_from_dotenv(home_env_path(), config.llm_provider)
    if not key:
        return config
    return HomeConfig(
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        llm_api_key=key,
    )


def ensure_env_gitignore(directory: Path) -> None:
    path = directory / ".gitignore"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        text = path.read_text()
        if ".env" in text.splitlines() or text.strip() == ".env":
            return
        if text and not text.endswith("\n"):
            text += "\n"
        path.write_text(text + ".env\n")
        return
    path.write_text(".env\n")


PROJECT_README = """\
# ReviewDistill

This directory is created by `reviewdistill init`. Commit it with the paper.

## `config.yaml`

```yaml
project:
  id: <assigned by init; do not change>
  name: paper-01
comments:
  latex_commands:
    - myremark
```

Comment commands are per paper. The LLM assistant (provider, model, API key) is configured in header **Settings → Assistant** and stored in the ReviewDistill folder on this computer, not here.

Then run `reviewdistill extract` (or `extract --watch`) and `reviewdistill serve`.
"""


def ensure_project_scaffold(root: Path) -> None:
    base = root / ".reviewdistill"
    base.mkdir(parents=True, exist_ok=True)
    ensure_env_gitignore(base)
    (base / "README.md").write_text(PROJECT_README)


@dataclass
class ProjectConfig:
    id: str
    name: str
    latex_commands: list[str] = field(default_factory=lambda: ["myremark"])


def load_home_config() -> HomeConfig:
    path = home_config_path()
    if not path.is_file():
        return HomeConfig()
    data = yaml.safe_load(path.read_text()) or {}
    llm = data.get("llm") or {}
    return HomeConfig(
        llm_provider=llm.get("provider"),
        llm_model=llm.get("model"),
    )


def load_llm_config() -> HomeConfig:
    """Home YAML plus home ``.env``. Paper ``llm:`` / ``.env`` are ignored."""
    return with_home_dotenv(load_home_config())


def write_home_llm(*, provider: str, model: str) -> None:
    write_home_config(HomeConfig(llm_provider=provider, llm_model=model))


def home_key_set(provider: str | None) -> bool:
    if not provider:
        return False
    return bool(api_key_from_dotenv(home_env_path(), provider))


def write_home_config(config: HomeConfig) -> None:
    path = home_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    llm: dict[str, str | None] = {
        "provider": config.llm_provider,
        "model": config.llm_model,
    }
    path.write_text(yaml.safe_dump({"llm": llm}, sort_keys=False))


def load_project_config(root: Path) -> ProjectConfig:
    data = yaml.safe_load(project_config_path(root).read_text()) or {}
    project = data.get("project") or {}
    comments = data.get("comments") or {}
    commands = comments.get("latex_commands") or ["myremark"]
    return ProjectConfig(
        id=project["id"],
        name=project["name"],
        latex_commands=list(commands),
    )


def write_project_config(root: Path, config: ProjectConfig) -> None:
    """Paper YAML is ``project`` plus latex commands. Does not write ``llm:``."""
    path = project_config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project": {"id": config.id, "name": config.name},
        "comments": {"latex_commands": config.latex_commands},
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def upsert_env_var(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text().splitlines() if path.is_file() else []
    out: list[str] = []
    replaced = False
    for line in lines:
        raw = line.removeprefix("export ")
        if raw.startswith(f"{key}="):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n")


