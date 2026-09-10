from pathlib import Path

from reviewdistill.web.static_assets import resolve_serve_static_dir


def test_explicit_dir_with_index(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html>ok</html>")
    assert resolve_serve_static_dir(explicit=tmp_path) == tmp_path.resolve()


def test_explicit_dir_without_index_does_not_fall_through(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    repo = tmp_path / "repo"
    dist = repo / "studio" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>monorepo</html>")
    assert resolve_serve_static_dir(explicit=empty, repo_root=repo) is None


def test_monorepo_studio_dist(tmp_path: Path):
    dist = tmp_path / "studio" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>monorepo</html>")
    assert resolve_serve_static_dir(repo_root=tmp_path) == dist.resolve()
