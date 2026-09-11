import subprocess
from pathlib import Path

import pytest
from reviewdistill.cli.init import init_project
from reviewdistill.db.models import Coding, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.extraction.incremental import extract_project, fingerprint_for, similar_text


def _write_tex(repo: Path, body: str) -> None:
    (repo / "main.tex").write_text(body)


def test_similar_text_revision_example():
    assert similar_text("Too strong.", "Too strong given the experiment.") is True
    assert similar_text("too strong.", "Too strong given the experiment.") is True
    assert similar_text("Why?", "Why this method?") is True


def test_similar_text_replacement_example():
    assert similar_text("Too strong.", "This citation is missing.") is False


@pytest.mark.parametrize(
    "before, after",
    [
        ("Too strong.", "Too long."),
        ("Too strong.", "Too weak."),
        ("Why this method?", "Why this model?"),
        ("Missing citation.", "Missing comma."),
        ("ok", "This is ok here."),
        ("a", "This citation is missing."),
        ("Too.", "Too long."),
        ("method", "The method here is unclear."),
    ],
)
def test_similar_text_short_distinct_remarks_are_not_revisions(before: str, after: str):
    assert similar_text(before, after) is False


def test_similar_text_typo_is_a_revision():
    assert similar_text("Too strong.", "Too stong.") is True


def test_similar_text_single_word_prefix_expansion_is_a_revision():
    assert similar_text("Unclear.", "Unclear given the setup.") is True


def test_first_extract_inserts_comments(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, Path("tests/fixtures/paper-01/main.tex").read_text())

    summary = extract_project(repo)
    assert summary.added == 2
    assert summary.unchanged == 0

    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 2
        assert all(row.raw_text for row in rows)
        assert all(row.context_text for row in rows)
        assert all(row.section for row in rows)
        assert {row.fingerprint for row in rows} == {
            fingerprint_for("myremark", "I don't think this follows."),
            fingerprint_for(
                "myremark",
                "This paragraph does not explain why this design decision was necessary.",
            ),
        }


def test_second_extract_is_idempotent(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, Path("tests/fixtures/paper-01/main.tex").read_text())
    extract_project(repo)
    summary = extract_project(repo)
    assert summary.added == 0
    assert summary.unchanged == 2

    with get_session() as session:
        assert len(session.find(ProofreadingComment)) == 2


def test_similar_body_change_updates_same_row(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    extract_project(repo)
    with get_session() as session:
        original_id = session.first(ProofreadingComment).id
    _write_tex(repo, "\\myremark{Too strong given the experiment.}\n")
    summary = extract_project(repo)
    assert summary.revised == 1
    assert summary.added == 0
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 1
        assert rows[0].id == original_id
        assert rows[0].raw_text == "Too strong given the experiment."
        assert rows[0].status == "active"
        assert rows[0].supersedes_id is None


def test_revision_clears_verified_quality(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        row.quality = "verified"
        session.add(row)
        session.commit()
        original_id = row.id
    _write_tex(repo, "\\myremark{Too strong given the experiment.}\n")
    summary = extract_project(repo)
    assert summary.revised == 1
    with get_session() as session:
        row = session.first(ProofreadingComment)
        assert row.id == original_id
        assert row.quality == "unreviewed"


def test_dissimilar_body_change_is_disappeared_and_new(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    extract_project(repo)
    _write_tex(repo, "\\myremark{This citation is missing.}\n")
    summary = extract_project(repo)
    assert summary.disappeared == 1
    assert summary.added == 1
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 2
        old = next(row for row in rows if row.raw_text == "Too strong.")
        new = next(row for row in rows if row.raw_text == "This citation is missing.")
        assert old.status == "pending_disappeared"
        assert new.status == "active"
        assert new.id != old.id


def test_short_distinct_same_line_replacement_is_disappeared_and_new(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    extract_project(repo)
    with get_session() as session:
        old = session.first(ProofreadingComment)
        old_id = old.id
        session.add(
            Coding(
                id="coding-old",
                comment_id=old_id,
                coder_type="human",
                status="accepted",
                issue_type_id="issue-1",
            )
        )
        session.commit()
    _write_tex(repo, "\\myremark{Too long.}\n")
    summary = extract_project(repo)
    assert summary.revised == 0
    assert summary.disappeared == 1
    assert summary.added == 1
    with get_session() as session:
        old = session.get(ProofreadingComment, old_id)
        new = next(
            row
            for row in session.find(ProofreadingComment)
            if row.id != old_id
        )
        coding = session.get(Coding, "coding-old")
        assert old.status == "pending_disappeared"
        assert old.raw_text == "Too strong."
        assert new.status == "active"
        assert new.raw_text == "Too long."
        assert coding.comment_id == old_id


def test_pending_disappeared_reappears_same_id(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    extract_project(repo)
    with get_session() as session:
        original_id = session.first(ProofreadingComment).id
    _write_tex(repo, "no comments\n")
    extract_project(repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    summary = extract_project(repo)
    assert summary.resurrected == 1
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 1
        assert rows[0].id == original_id
        assert rows[0].status == "active"


def test_removed_comment_is_pending_disappeared(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Keep me.}\n\\myremark{Delete me.}\n")
    extract_project(repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    summary = extract_project(repo)
    assert summary.disappeared == 1
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 2
        gone = next(row for row in rows if row.raw_text == "Delete me.")
        assert gone.status == "pending_disappeared"


def test_gap_then_new_text_is_two_records(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    extract_project(repo)
    _write_tex(repo, "no comments\n")
    extract_project(repo)
    _write_tex(repo, "\\myremark{This citation is missing.}\n")
    extract_project(repo)
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 2
        old = next(row for row in rows if row.raw_text == "Too strong.")
        new = next(row for row in rows if row.raw_text == "This citation is missing.")
        assert old.status == "pending_disappeared"
        assert new.status == "active"


def test_unclosed_comment_does_not_enqueue_disappearance(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    extract_project(repo)
    _write_tex(repo, "\\myremark{Keep me.\n")
    summary = extract_project(repo)
    assert summary.skipped_unstable == 1
    assert summary.disappeared == 0
    with get_session() as session:
        row = session.first(ProofreadingComment)
        assert row.status == "active"
        assert row.raw_text == "Keep me."


def test_verified_reappears_same_id(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        row.status = "pending_disappeared"
        row.quality = "verified"
        session.add(row)
        session.commit()
        kept_id = row.id
    summary = extract_project(repo)
    assert summary.resurrected == 1
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 1
        assert rows[0].id == kept_id
        assert rows[0].status == "active"
        assert rows[0].quality == "verified"


def test_dropped_same_text_stays_same_id(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        row.quality = "dropped"
        session.add(row)
        session.commit()
        dropped_id = row.id
    extract_project(repo)
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 1
        assert rows[0].id == dropped_id
        assert rows[0].status == "active"
        assert rows[0].quality == "dropped"


def test_duplicate_texts_are_not_merged(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Same.}\n\\myremark{Same.}\n")
    extract_project(repo)
    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 2
        assert {row.raw_text for row in rows} == {"Same."}


def test_moved_comment_updates_location(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "line1\n\\myremark{Moved comment.}\n")
    extract_project(repo)
    (repo / "other.tex").write_text("\\myremark{Moved comment.}\n")
    (repo / "main.tex").write_text("no comments\n")
    summary = extract_project(repo)
    assert summary.moved == 1

    with get_session() as session:
        rows = session.find(ProofreadingComment)
        assert len(rows) == 1
        assert rows[0].file_path == "other.tex"
        assert rows[0].status == "active"
        assert rows[0].raw_text == "Moved comment."


def test_move_keeps_verified_quality(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "line1\n\\myremark{Moved comment.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        row.quality = "verified"
        session.add(row)
        session.commit()
        original_id = row.id
    (repo / "other.tex").write_text("\\myremark{Moved comment.}\n")
    (repo / "main.tex").write_text("no comments\n")
    summary = extract_project(repo)
    assert summary.moved == 1
    with get_session() as session:
        row = session.first(ProofreadingComment)
        assert row.id == original_id
        assert row.file_path == "other.tex"
        assert row.quality == "verified"


def test_extract_records_git_remote_url(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "main.tex"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/example/paper.git"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        assert row.git_url == "https://github.com/example/paper.git"
        assert row.git_commit
        assert len(row.git_commit) >= 7


def test_extract_strips_credentials_from_stored_git_url(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Too strong.}\n")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "main.tex"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://user:ghp_secret@github.com/example/paper.git"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        assert row.git_url == "https://github.com/example/paper.git"
        assert "ghp_secret" not in (row.git_url or "")


def test_extract_skips_ignored_directories(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    _write_tex(repo, "\\myremark{Keep me.}\n")
    nested = repo / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    (nested / "vendor.tex").write_text("\\myremark{Ignore me.}\n")
    extract_project(repo)
    with get_session() as session:
        texts = {row.raw_text for row in session.find(ProofreadingComment)}
        assert texts == {"Keep me."}
