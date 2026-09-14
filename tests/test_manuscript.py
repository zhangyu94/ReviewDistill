from pathlib import Path

from reviewdistill.manuscript import comment_source_file


def test_comment_source_file_returns_existing_file(tmp_path: Path):
    root = tmp_path / "paper"
    tex = root / "sections" / "intro.tex"
    tex.parent.mkdir(parents=True)
    tex.write_text("% hi\n")
    assert comment_source_file(str(root), "sections/intro.tex") == tex.resolve()


def test_comment_source_file_allows_dotdot_that_stays_under_root(tmp_path: Path):
    root = tmp_path / "paper"
    tex = root / "main.tex"
    root.mkdir()
    tex.write_text("% hi\n")
    assert comment_source_file(str(root), "sections/../main.tex") == tex.resolve()


def test_comment_source_file_missing_file_is_none(tmp_path: Path):
    root = tmp_path / "paper"
    root.mkdir()
    assert comment_source_file(str(root), "gone.tex") is None


def test_comment_source_file_missing_root_is_none(tmp_path: Path):
    assert comment_source_file(str(tmp_path / "gone"), "main.tex") is None


def test_comment_source_file_directory_is_none(tmp_path: Path):
    root = tmp_path / "paper"
    nested = root / "sections"
    nested.mkdir(parents=True)
    assert comment_source_file(str(root), "sections") is None


def test_comment_source_file_escape_is_none(tmp_path: Path):
    root = tmp_path / "paper"
    root.mkdir()
    secret = tmp_path / "secret.tex"
    secret.write_text("nope\n")
    assert comment_source_file(str(root), "../secret.tex") is None


def test_comment_source_file_absolute_path_is_none(tmp_path: Path):
    root = tmp_path / "paper"
    root.mkdir()
    secret = tmp_path / "secret.tex"
    secret.write_text("nope\n")
    assert comment_source_file(str(root), str(secret)) is None


def test_comment_source_file_symlink_escape_is_none(tmp_path: Path):
    root = tmp_path / "paper"
    root.mkdir()
    secret = tmp_path / "secret.tex"
    secret.write_text("nope\n")
    (root / "leak.tex").symlink_to(secret)
    assert comment_source_file(str(root), "leak.tex") is None
