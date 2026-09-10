import subprocess
from pathlib import Path

from reviewdistill.gitinfo import GitMetadata, context_permalink, read_git_metadata


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_read_git_metadata_from_repo(tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")
    (repo / "main.tex").write_text("hi\n")
    _git(repo, "add", "main.tex")
    _git(repo, "commit", "-m", "init")
    meta = read_git_metadata(repo)
    assert isinstance(meta, GitMetadata)
    assert meta.repository == str(repo.resolve())
    assert len(meta.commit_hash) >= 7
    assert meta.remote_url is None


def test_read_git_metadata_includes_origin_url(tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")
    (repo / "main.tex").write_text("hi\n")
    _git(repo, "add", "main.tex")
    _git(repo, "commit", "-m", "init")
    _git(repo, "remote", "add", "origin", "https://github.com/example/paper.git")
    meta = read_git_metadata(repo)
    assert meta.remote_url == "https://github.com/example/paper.git"


def test_read_git_metadata_outside_repo(tmp_path: Path):
    meta = read_git_metadata(tmp_path)
    assert meta.repository is None
    assert meta.commit_hash is None
    assert meta.remote_url is None


def test_context_permalink_from_https_and_ssh_remotes():
    https = context_permalink(
        "https://github.com/example/paper.git",
        "abc1234",
        "src/main.tex",
        12,
    )
    assert https == "https://github.com/example/paper/blob/abc1234/src/main.tex#L12"
    ssh = context_permalink(
        "git@github.com:example/paper.git",
        "abc1234",
        "src/main.tex",
        12,
    )
    assert ssh == "https://github.com/example/paper/blob/abc1234/src/main.tex#L12"


def test_context_permalink_encodes_file_path():
    url = context_permalink(
        "https://github.com/example/paper.git",
        "abc1234",
        "sections/My File.tex",
        3,
    )
    assert url == "https://github.com/example/paper/blob/abc1234/sections/My%20File.tex#L3"


def test_context_permalink_strips_embedded_credentials():
    url = context_permalink(
        "https://user:ghp_secret@github.com/example/paper.git",
        "abc1234",
        "main.tex",
        1,
    )
    assert url == "https://github.com/example/paper/blob/abc1234/main.tex#L1"
    token_only = context_permalink(
        "https://ghp_secret@github.com/example/paper.git",
        "abc1234",
        "main.tex",
        1,
    )
    assert token_only == "https://github.com/example/paper/blob/abc1234/main.tex#L1"
    ssh_token = context_permalink(
        "ssh://user:ghp_secret@github.com/example/paper.git",
        "abc1234",
        "main.tex",
        1,
    )
    assert ssh_token is None or "ghp_secret" not in ssh_token


def test_sanitize_remote_url_keeps_git_username_without_password():
    from reviewdistill.gitinfo import sanitize_remote_url

    overleaf = "https://git@git.overleaf.com/aaaaaaaaaaaaaaaaaaaaaaaa"
    assert sanitize_remote_url(overleaf) == overleaf
    ssh_git = "ssh://git@github.com/example/paper.git"
    assert sanitize_remote_url(ssh_git) == ssh_git
    dirty_ssh = sanitize_remote_url("ssh://user:ghp_secret@github.com/example/paper.git")
    assert dirty_ssh == "ssh://github.com/example/paper.git"
    assert "ghp_secret" not in dirty_ssh


def test_read_git_metadata_strips_origin_credentials(tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")
    (repo / "main.tex").write_text("hi\n")
    _git(repo, "add", "main.tex")
    _git(repo, "commit", "-m", "init")
    _git(repo, "remote", "add", "origin", "https://user:ghp_secret@github.com/example/paper.git")
    meta = read_git_metadata(repo)
    assert meta.remote_url == "https://github.com/example/paper.git"
    assert "ghp_secret" not in (meta.remote_url or "")


def test_context_permalink_rejects_javascript_and_lookalike_hosts():
    assert context_permalink("javascript:alert(1)", "abc", "main.tex", 1) is None
    assert context_permalink("data:text/html,hi", "abc", "main.tex", 1) is None
    evil = context_permalink(
        "https://evilgithub.com/example/paper.git",
        "abc1234",
        "main.tex",
        1,
    )
    assert evil is None or "evilgithub.com/blob/" not in evil
    if evil:
        assert evil.startswith("https://evilgithub.com")
        assert "/blob/" not in evil
    gitlab_evil = context_permalink(
        "https://gitlab.evil.com/example/paper.git",
        "abc1234",
        "main.tex",
        1,
    )
    assert gitlab_evil is not None
    assert "/-/blob/" not in gitlab_evil
    gitlab = context_permalink(
        "https://gitlab.com/example/paper.git",
        "abc1234",
        "main.tex",
        1,
    )
    assert gitlab == "https://gitlab.com/example/paper/-/blob/abc1234/main.tex#L1"


def test_context_permalink_missing_remote_or_commit():
    assert context_permalink(None, "abc", "main.tex", 1) is None
    assert context_permalink("https://github.com/example/paper.git", None, "main.tex", 1) is None
