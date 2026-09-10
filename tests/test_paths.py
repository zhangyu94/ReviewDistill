from reviewdistill.paths import db_path, find_project_root, home_dir


def test_home_dir_uses_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("REVIEWDISTILL_HOME", str(tmp_path / "rd"))
    assert home_dir() == tmp_path / "rd"
    assert db_path() == tmp_path / "rd" / "reviewdistill.db"


def test_find_project_root_walks_up(tmp_path):
    repo = tmp_path / "paper"
    nested = repo / "src" / "tex"
    nested.mkdir(parents=True)
    (repo / ".reviewdistill").mkdir()
    (repo / ".reviewdistill" / "config.yaml").write_text("project:\n  name: demo\n")
    assert find_project_root(nested) == repo


def test_find_project_root_missing_returns_none(tmp_path):
    assert find_project_root(tmp_path) is None
