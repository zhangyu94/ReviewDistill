from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import dotenv_values

from reviewdistill.paths import (
    find_project_root,
    home_config_path,
    project_config_path,
    project_env_path,
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


def api_key_from_dotenv(root: Path, provider: str | None) -> str | None:
    if not provider:
        return None
    env_name = PROVIDER_ENV_KEYS.get(provider.lower())
    if not env_name:
        return None
    return load_dotenv_values(project_env_path(root)).get(env_name)


def with_project_dotenv(config: HomeConfig, root: Path) -> HomeConfig:
    key = api_key_from_dotenv(root, config.llm_provider)
    if not key:
        return config
    return HomeConfig(
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        llm_api_key=key,
    )


def ensure_env_gitignore(root: Path) -> None:
    path = root / ".reviewdistill" / ".gitignore"
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


ENV_EXAMPLE = """\
# Copy this file to .env and fill in the key that matches llm.provider in config.yaml.
# Do not commit .env.
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
"""

PROJECT_README = """\
# ReviewDistill

This directory is created by `reviewdistill init`. Commit it with the paper, except `.env`.

## `config.yaml`

`init` writes `project` and `comments`. Add an `llm` block so the workbench can call an API.

```yaml
project:
  id: <assigned by init; do not change>
  name: paper-01
comments:
  latex_commands:
    - myremark
llm:
  provider: deepseek          # openai | anthropic | deepseek
  model: deepseek-chat        # optional; each provider has a default
```

Do not put the API key in `config.yaml`. Put it in `.env` instead.

| `provider` | `.env` variable | typical `model` |
| --- | --- | --- |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |

## API key

1. Copy `.env.example` to `.env`.
2. Set the variable that matches `llm.provider`, for example:

```
DEEPSEEK_API_KEY=sk-...
```

3. A process environment variable of the same name wins if both are set.

## Files

- `config.yaml` — committed project and LLM settings (format above).
- `.env` — API key (gitignored).
- `.env.example` — template for `.env`.
- `.gitignore` — ignores `.env`.

Then run `reviewdistill extract` (or `extract --watch`) and `reviewdistill serve`.
"""


def ensure_project_scaffold(root: Path) -> None:
    ensure_env_gitignore(root)
    base = root / ".reviewdistill"
    base.mkdir(parents=True, exist_ok=True)
    (base / ".env.example").write_text(ENV_EXAMPLE)
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


def load_llm_config(*, start: Path | None = None) -> HomeConfig:
    """LLM settings: project `.reviewdistill/config.yaml` overlays home config."""
    home = load_home_config()
    root = find_project_root(start)
    if root is None:
        return home
    path = project_config_path(root)
    if not path.is_file():
        return home
    data = yaml.safe_load(path.read_text()) or {}
    llm = data.get("llm") or {}
    if llm:
        home = HomeConfig(
            llm_provider=llm.get("provider", home.llm_provider),
            llm_model=llm["model"] if llm.get("model") is not None else home.llm_model,
            llm_api_key=home.llm_api_key,
        )
    return with_project_dotenv(home, root)


def llm_config_from_project_root(root: Path) -> HomeConfig | None:
    path = project_config_path(root)
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    llm = data.get("llm") or {}
    if not llm:
        return None
    return with_project_dotenv(
        HomeConfig(
            llm_provider=llm.get("provider"),
            llm_model=llm.get("model"),
        ),
        root,
    )


def load_llm_config_from_registered_projects() -> HomeConfig | None:
    from reviewdistill.db.models import Project
    from reviewdistill.db.session import get_session, init_db

    init_db()
    roots: list[Path] = []
    with get_session() as session:
        for project in session.find(Project):
            roots.append(Path(project.root_path))
    found: list[HomeConfig] = []
    for root in sorted(roots, key=lambda path: str(path)):
        cfg = llm_config_from_project_root(root)
        if cfg and cfg.llm_provider and cfg.llm_provider.lower() != "mock":
            found.append(cfg)
    with_keys = [cfg for cfg in found if cfg.llm_api_key]
    if len(with_keys) == 1:
        return with_keys[0]
    if len(found) == 1:
        return found[0]
    return None


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
    path = project_config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if path.is_file():
        existing = yaml.safe_load(path.read_text()) or {}
    payload = {
        "project": {"id": config.id, "name": config.name},
        "comments": {"latex_commands": config.latex_commands},
    }
    if existing.get("llm"):
        llm = dict(existing["llm"])
        llm.pop("api_key", None)
        payload["llm"] = llm
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


def write_project_llm(root: Path, *, provider: str, model: str) -> None:
    """Write ``llm.provider`` / ``llm.model``. Keys live in ``.env``, not YAML."""
    path = project_config_path(root)
    data = yaml.safe_load(path.read_text()) or {} if path.is_file() else {}
    llm = dict(data.get("llm") or {})
    llm.pop("api_key", None)
    llm["provider"] = provider
    llm["model"] = model
    data["llm"] = llm
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def paper_key_set(root: Path, provider: str | None) -> bool:
    if not provider:
        return False
    return bool(api_key_from_dotenv(root, provider))


def list_registered_project_rows() -> list[dict]:
    from reviewdistill.db.models import Project
    from reviewdistill.db.session import get_session, init_db

    init_db()
    rows = []
    with get_session() as session:
        for project in session.find(Project):
            rows.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "root_path": project.root_path,
                }
            )
    return rows


def default_registered_project_id(*, cwd: Path | None = None) -> str | None:
    root = find_project_root(cwd)
    if root is None:
        return None
    resolved = root.resolve()
    for row in list_registered_project_rows():
        if Path(row["root_path"]).resolve() == resolved:
            return row["id"]
    return None


def llm_selected_payload(project_id: str) -> dict | None:
    from reviewdistill.db.models import Project
    from reviewdistill.db.session import get_session, init_db

    init_db()
    with get_session() as session:
        project = session.get(Project, project_id)
    if project is None:
        return None
    root = Path(project.root_path)
    cfg = llm_config_from_project_root(root)
    provider = cfg.llm_provider if cfg else None
    model = cfg.llm_model if cfg else None
    if provider and provider.lower() == "mock":
        provider = None
        model = None
    return {
        "project_id": project.id,
        "provider": provider,
        "model": model,
        "key_set": paper_key_set(root, provider),
    }
