from pathlib import Path

import pytest

from client_build import (
    ClientBuildError,
    build_client_assets,
    copy_dist_to_packaged,
    should_build_client,
)


def test_skip_env_disables_build(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SKIP_CLIENT_BUILD", "1")
    assert should_build_client(tmp_path) is False
    build_client_assets(tmp_path)  # no error without client or pnpm


def test_missing_client_sources_skips(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SKIP_CLIENT_BUILD", raising=False)
    assert should_build_client(tmp_path) is False
    build_client_assets(tmp_path)


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
    monkeypatch.delenv("SKIP_CLIENT_BUILD", raising=False)
    monkeypatch.setattr("client_build.shutil.which", lambda _: None)
    (tmp_path / "client").mkdir()
    (tmp_path / "client" / "package.json").write_text("{}")
    with pytest.raises(ClientBuildError, match="SKIP_CLIENT_BUILD"):
        build_client_assets(tmp_path)
