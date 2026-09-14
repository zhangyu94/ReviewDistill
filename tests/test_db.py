import os
import subprocess
import sys
from pathlib import Path

import pytest

from reviewdistill.db.models import Project, ProofreadingComment, comment_quality
from reviewdistill.db.session import get_session, init_db


def test_init_db_creates_and_round_trips_project(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        session.commit()

    with get_session() as session:
        project = session.get(Project, "p1")
        assert project is not None
        assert project.name == "paper-01"
    assert (rd_home / "projects.jsonl").is_file()


def test_comment_raw_text_persists(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=10,
                raw_text='I think "demonstrate" is too strong.',
                context_text="The results demonstrate that...",
                section="4.2 Results",
                git_commit="abc123",
                fingerprint="deadbeef",
                status="active",
            )
        )
        session.commit()

    with get_session() as session:
        comment = session.get(ProofreadingComment, "c1")
        assert comment.raw_text == 'I think "demonstrate" is too strong.'
        assert comment.status == "active"
    line = (rd_home / "comments.jsonl").read_text(encoding="utf-8").strip()
    assert "demonstrate" in line


def test_unknown_quality_is_rejected():
    comment = ProofreadingComment(
        id="c-bad",
        project_id="p1",
        source_type="latex_command",
        source_command="myremark",
        file_path="main.tex",
        line_number=1,
        raw_text="Too strong.",
        fingerprint="fp",
        quality="kept",
    )
    with pytest.raises(ValueError, match="Unknown comment quality"):
        comment_quality(comment)


def test_add_rejects_unknown_quality(rd_home):
    init_db()
    with pytest.raises(ValueError, match="Unknown comment quality"):
        with get_session() as session:
            session.add(
                ProofreadingComment(
                    id="c-bad",
                    project_id="p1",
                    source_type="latex_command",
                    source_command="myremark",
                    file_path="main.tex",
                    line_number=1,
                    raw_text="Too strong.",
                    fingerprint="fp",
                    quality="kept",
                )
            )


def test_commit_rejects_unknown_quality(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        comment = ProofreadingComment(
            id="c-bad",
            project_id="p1",
            source_type="latex_command",
            source_command="myremark",
            file_path="main.tex",
            line_number=1,
            raw_text="Too strong.",
            fingerprint="fp",
            quality="unreviewed",
        )
        session.add(comment)
        session.commit()
        comment.quality = "kept"
        with pytest.raises(ValueError, match="Unknown comment quality"):
            session.commit()
    assert '"unreviewed"' in (rd_home / "comments.jsonl").read_text(encoding="utf-8")
    assert '"kept"' not in (rd_home / "comments.jsonl").read_text(encoding="utf-8")


def test_store_load_rejects_unknown_quality(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c-bad",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Too strong.",
                fingerprint="fp",
                quality="unreviewed",
            )
        )
        session.commit()
    path = rd_home / "comments.jsonl"
    text = path.read_text(encoding="utf-8")
    assert '"unreviewed"' in text
    path.write_text(text.replace('"unreviewed"', '"kept"', 1), encoding="utf-8")
    assert '"kept"' in path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown comment quality"):
        with get_session():
            pass
    with pytest.raises(ValueError, match="Unknown comment quality"):
        with get_session():
            pass


def _seed_project_and_comment(*, name: str, raw_text: str) -> None:
    with get_session() as session:
        session.add(Project(id="p1", name=name, root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text=raw_text,
                fingerprint="fp",
                status="active",
            )
        )
        session.commit()


def test_init_db_appends_lock_to_existing_gitignore(rd_home):
    gitignore = rd_home / ".gitignore"
    gitignore.write_text("*.bak\n", encoding="utf-8")
    init_db()
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert "*.bak" in lines
    assert ".lock" in lines


def test_init_db_writes_home_readme(rd_home):
    init_db()
    text = (rd_home / "README.md").read_text(encoding="utf-8")
    assert "paths move" in text
    assert "paths use" in text
    assert ".env" in text


def test_init_db_does_not_overwrite_home_readme(rd_home):
    path = rd_home / "README.md"
    path.write_text("user notes\n", encoding="utf-8")
    init_db()
    assert path.read_text(encoding="utf-8") == "user notes\n"


def test_load_removes_leftover_jsonl_tmp(rd_home):
    leftover = rd_home / "comments.jsonl.tmp"
    leftover.write_text("{}\n", encoding="utf-8")
    with get_session() as session:
        session.get(Project, "missing")
    assert not leftover.exists()


def test_nested_sessions_reuse_and_do_not_deadlock(rd_home, fake_user_home):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["HOME"] = str(fake_user_home)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    script = """
from reviewdistill.db.models import Project
from reviewdistill.db.session import get_session, init_db
init_db()
with get_session() as outer:
    outer.add(Project(id="nested", name="n", root_path="/tmp"))
    with get_session() as inner:
        assert inner is outer, "nested get_session must reuse the open session"
        assert inner.get(Project, "nested") is not None
        inner.commit()
with get_session() as session:
    assert session.get(Project, "nested") is not None
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_failed_commit_leaves_consistent_jsonl(rd_home, monkeypatch):
    _seed_project_and_comment(name="old", raw_text="old")
    original = Path.replace
    calls = {"n": 0}

    def boom(self, target):
        if str(self).endswith(".jsonl") or str(target).endswith(".jsonl"):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise OSError("crash mid-save")
        return original(self, target)

    monkeypatch.setattr(Path, "replace", boom)
    with pytest.raises(OSError, match="crash mid-save"), get_session() as session:
        session.get(Project, "p1").name = "new"
        session.get(ProofreadingComment, "c1").raw_text = "new"
        session.add(session.get(Project, "p1"))
        session.add(session.get(ProofreadingComment, "c1"))
        session.commit()
    monkeypatch.setattr(Path, "replace", original)
    with get_session() as session:
        names = (session.get(Project, "p1").name, session.get(ProofreadingComment, "c1").raw_text)
    assert names in {("old", "old"), ("new", "new")}


def test_retry_commit_crash_before_sentinel_stays_consistent(rd_home, monkeypatch):
    _seed_project_and_comment(name="old", raw_text="old")
    original_replace = Path.replace
    original_write = Path.write_text
    jsonl_replaces = {"n": 0}

    def boom_replace(self, target):
        if str(self).endswith(".jsonl") or str(target).endswith(".jsonl"):
            jsonl_replaces["n"] += 1
            if jsonl_replaces["n"] == 2:
                raise OSError("crash mid-replace")
        return original_replace(self, target)

    def boom_write(self, data, encoding=None, errors=None, newline=None):
        if self.name == "COMMIT":
            raise OSError("crash before sentinel")
        return original_write(self, data, encoding=encoding, errors=errors, newline=newline)

    with get_session() as session:
        session.get(Project, "p1").name = "new"
        session.get(ProofreadingComment, "c1").raw_text = "new"
        session.add(session.get(Project, "p1"))
        session.add(session.get(ProofreadingComment, "c1"))
        monkeypatch.setattr(Path, "replace", boom_replace)
        with pytest.raises(OSError, match="crash mid-replace"):
            session.commit()
        monkeypatch.setattr(Path, "replace", original_replace)
        monkeypatch.setattr(Path, "write_text", boom_write)
        with pytest.raises(OSError, match="crash before sentinel"):
            session.commit()
    monkeypatch.setattr(Path, "write_text", original_write)
    with get_session() as session:
        names = (session.get(Project, "p1").name, session.get(ProofreadingComment, "c1").raw_text)
    assert names in {("old", "old"), ("new", "new")}


def test_load_finishes_committed_staging_dir(rd_home):
    _seed_project_and_comment(name="old", raw_text="old")
    staging = rd_home / ".commit"
    staging.mkdir()
    (staging / "projects.jsonl").write_text(
        (rd_home / "projects.jsonl").read_text(encoding="utf-8").replace('"old"', '"new"'),
        encoding="utf-8",
    )
    (staging / "comments.jsonl").write_text(
        (rd_home / "comments.jsonl").read_text(encoding="utf-8").replace('"old"', '"new"'),
        encoding="utf-8",
    )
    (staging / "COMMIT").write_text("ok\n", encoding="utf-8")
    with get_session() as session:
        assert session.get(Project, "p1").name == "new"
        assert session.get(ProofreadingComment, "c1").raw_text == "new"
    assert not staging.exists()


def test_load_discards_incomplete_staging_dir(rd_home):
    _seed_project_and_comment(name="old", raw_text="old")
    staging = rd_home / ".commit"
    staging.mkdir()
    (staging / "projects.jsonl").write_text(
        (rd_home / "projects.jsonl").read_text(encoding="utf-8").replace('"old"', '"new"'),
        encoding="utf-8",
    )
    with get_session() as session:
        assert session.get(Project, "p1").name == "old"
    assert not staging.exists()


def test_two_processes_keep_both_commits(rd_home, fake_user_home):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["HOME"] = str(fake_user_home)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    script = """
from reviewdistill.db.models import Project
from reviewdistill.db.session import get_session, init_db
init_db()
with get_session() as session:
    session.add(Project(id={id!r}, name={id!r}, root_path="/tmp"))
    session.commit()
"""
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script.format(id=ident)],
            env=env,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for ident in ("proc-a", "proc-b")
    ]
    for proc in procs:
        assert proc.wait(timeout=15) == 0, proc.stderr.read()
    with get_session() as session:
        assert session.get(Project, "proc-a") is not None
        assert session.get(Project, "proc-b") is not None
