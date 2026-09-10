from pathlib import Path

import pytest

from studio_build import (
    StudioBuildError,
    build_studio_assets,
    copy_dist_to_packaged,
    should_build_studio,
)


def test_skip_env_disables_build(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SKIP_STUDIO_BUILD", "1")
    assert should_build_studio(tmp_path) is False
    build_studio_assets(tmp_path)  # no error without studio or pnpm


def test_missing_studio_sources_skips(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SKIP_STUDIO_BUILD", raising=False)
    assert should_build_studio(tmp_path) is False
    build_studio_assets(tmp_path)


def test_copy_replaces_assets_and_keeps_scaffold(tmp_path: Path):
    dist = tmp_path / "dist"
    dest = tmp_path / "static"
    dist.mkdir()
    (dist / "index.html").write_text("<html>new</html>")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("js")
    dest.mkdir()
    (dest / "README.md").write_text("keep-readme")
    (dest / ".gitignore").write_text("keep-ignore")
    (dest / "stale.js").write_text("old")
    copy_dist_to_packaged(dist, dest)
    assert (dest / "index.html").read_text() == "<html>new</html>"
    assert (dest / "assets" / "app.js").read_text() == "js"
    assert not (dest / "stale.js").exists()
    assert (dest / "README.md").read_text() == "keep-readme"
    assert (dest / ".gitignore").read_text() == "keep-ignore"


def test_missing_pnpm_explains_how_to_skip(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SKIP_STUDIO_BUILD", raising=False)
    monkeypatch.setattr("studio_build.shutil.which", lambda _: None)
    (tmp_path / "studio").mkdir()
    (tmp_path / "studio" / "package.json").write_text("{}")
    with pytest.raises(StudioBuildError, match="SKIP_STUDIO_BUILD"):
        build_studio_assets(tmp_path)
