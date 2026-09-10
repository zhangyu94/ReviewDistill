"""Locate the Studio SPA for `reviewdistill serve`."""

from __future__ import annotations

from pathlib import Path

_PACKAGED_STATIC = Path(__file__).resolve().parent / "static"


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def packaged_static_dir() -> Path | None:
    index = _PACKAGED_STATIC / "index.html"
    if index.is_file():
        return _PACKAGED_STATIC
    return None


def resolve_serve_static_dir(
    *,
    explicit: Path | None = None,
    repo_root: Path | None = None,
) -> Path | None:
    """Order: explicit (no fall-through) → studio/dist → packaged static."""
    if explicit is not None:
        root = explicit.resolve()
        if (root / "index.html").is_file():
            return root
        return None
    root = (repo_root if repo_root is not None else default_repo_root()).resolve()
    monorepo = root / "studio" / "dist"
    if (monorepo / "index.html").is_file():
        return monorepo
    return packaged_static_dir()
