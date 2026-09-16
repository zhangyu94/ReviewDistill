import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from reviewdistill.db.models import (
    Assignment,
    Project,
    ProofreadingComment,
    TaxonomyEvent,
    normalize_comment_record,
)
from reviewdistill.db.session import FILES, get_session, init_db, reset_engine
from reviewdistill.errors import CorruptStore


def test_store_files_are_the_live_collections():
    assert set(FILES.values()) == {
        "projects.jsonl",
        "comments.jsonl",
        "assignments.jsonl",
        "labels.jsonl",
        "label_examples.jsonl",
        "history.jsonl",
    }


def test_load_ignores_taxonomy_events_jsonl(rd_home):
    reset_engine()
    (rd_home / "taxonomy_events.jsonl").write_text(
        json.dumps(
            {
                "id": "e1",
                "event_type": "add",
                "payload_json": "{}",
                "undone": False,
                "created_at": "2026-09-16T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with get_session() as session:
        assert session.get(TaxonomyEvent, "e1") is None
    history = rd_home / "history.jsonl"
    assert not history.is_file() or "e1" not in history.read_text(encoding="utf-8")
    assert (rd_home / "taxonomy_events.jsonl").is_file()


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


def test_comment_context_offset_persists(rd_home):
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
                raw_text="Too strong.",
                context_text="Hello.",
                context_offset=5,
                status="active",
            )
        )
        session.commit()

    with get_session() as session:
        comment = session.get(ProofreadingComment, "c1")
        assert comment.context_offset == 5
        assert comment.context_text == "Hello."


def _record(**extra):
    base = {
        "id": "c1",
        "project_id": "p1",
        "source_type": "latex_command",
        "source_command": "myremark",
        "file_path": "main.tex",
        "line_number": 1,
        "raw_text": "Too strong.",
        "status": "active",
    }
    base.update(extra)
    return base


def test_normalize_maps_quality_strings():
    assert normalize_comment_record(_record(quality="verified"))["verified"] is True
    assert normalize_comment_record(_record(quality="unreviewed"))["verified"] is False
    assert "quality" not in normalize_comment_record(_record(quality="unreviewed"))


def test_normalize_keeps_boolean_verified():
    out = normalize_comment_record(_record(verified=True, quality="unreviewed"))
    assert out["verified"] is True
    assert "quality" not in out


def test_normalize_purges_dropped_even_if_verified_present():
    assert normalize_comment_record(_record(quality="dropped", verified=True)) is None


def test_normalize_dropped_without_purge_is_not_verified():
    out = normalize_comment_record(_record(quality="dropped"), purge_dropped=False)
    assert out["verified"] is False
    assert "quality" not in out


def test_normalize_unknown_quality_fails():
    with pytest.raises(CorruptStore, match="Unknown comment quality"):
        normalize_comment_record(_record(quality="kept"))


def test_normalize_non_boolean_verified_fails():
    with pytest.raises(CorruptStore, match="Unknown comment verified"):
        normalize_comment_record(_record(verified="yes"))


def test_normalize_missing_both_defaults_false():
    assert normalize_comment_record(_record())["verified"] is False


def test_normalize_drops_stored_fingerprint():
    out = normalize_comment_record(_record(fingerprint="deadbeef"))
    assert "fingerprint" not in out


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
            )
        )
        session.commit()
    path = rd_home / "comments.jsonl"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("verified", None)
    data["quality"] = "kept"
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown comment quality"):
        with get_session():
            pass
    with pytest.raises(ValueError, match="Unknown comment quality"):
        with get_session():
            pass


def test_store_load_rejects_non_boolean_verified(rd_home):
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
            )
        )
        session.commit()
    path = rd_home / "comments.jsonl"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["verified"] = "yes"
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown comment verified"):
        with get_session():
            pass


def test_load_maps_quality_and_rewrites_jsonl(rd_home):
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
                line_number=1,
                raw_text="Too strong.",
            )
        )
        session.commit()
    path = rd_home / "comments.jsonl"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("verified", None)
    data["quality"] = "verified"
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    reset_engine()
    with get_session() as session:
        assert session.get(ProofreadingComment, "c1").verified is True
    text = path.read_text(encoding="utf-8")
    assert '"verified": true' in text
    assert "quality" not in text


def test_load_purges_dropped_comment_and_dependents(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c-drop",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Bad extract.",
            )
        )
        session.add(
            Assignment(
                id="k1",
                comment_id="c-drop",
                label_id=None,
                coder_type="human",
                status="proposed",
            )
        )
        session.commit()
    path = rd_home / "comments.jsonl"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("verified", None)
    data["quality"] = "dropped"
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    reset_engine()
    with get_session() as session:
        assert session.get(ProofreadingComment, "c-drop") is None
        assert session.get(Assignment, "k1") is None
    assert "dropped" not in (rd_home / "comments.jsonl").read_text(encoding="utf-8")


def test_load_drops_stored_fingerprint(rd_home):
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
                line_number=1,
                raw_text="Too strong.",
            )
        )
        session.commit()
    path = rd_home / "comments.jsonl"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["fingerprint"] = "deadbeef"
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    reset_engine()
    with get_session() as session:
        row = session.get(ProofreadingComment, "c1")
        assert row is not None
        assert not hasattr(row, "fingerprint") or "fingerprint" not in row.model_dump()
    assert "fingerprint" not in path.read_text(encoding="utf-8")


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
    assert "`projects.jsonl`" in text
    assert "`comments.jsonl`" in text
    assert "`labels.jsonl`" in text
    assert "`config.yaml`" in text
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
