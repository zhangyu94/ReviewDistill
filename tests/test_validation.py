import json

import pytest

from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import code_uncoded_comments, uncoded_comments
from reviewdistill.coding.validation import (
    DROP_UNCHANGED,
    VERIFY_FILE_MISSING,
    VERIFY_MANUSCRIPT_CHANGED,
    accept_coding,
    change_coding,
    disappearance_guess,
    drop_comment,
    inbox_items,
    verify_comment,
)
from reviewdistill.context.manuscript import extract_context
from reviewdistill.db.models import Coding, IssueExample, IssueType, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.errors import BadInput, NotFound
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.history import undo
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import (
    accepted_counts_by_issue_type,
    create_issue_type,
    deactivate_issue_type,
    list_active_issue_types,
    list_examples,
    list_working_observations,
    remove_issue_type,
)


def _seed_proposed(tmp_path, response: dict) -> str:
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why did we choose this method?}\n")
    extract_project(repo)
    code_uncoded_comments(provider=MockLLMProvider(scripted_response=json.dumps(response)))
    items = inbox_items()
    assert len(items) == 1
    return items[0].comment.id


def test_accept_existing_marks_coding_and_adds_example(db, tmp_path):
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    result = accept_coding(comment_id)
    assert result.issue_type_id == issue.id
    assert inbox_items() == []
    examples = list_examples(issue.id)
    assert examples[0].source_comment_id == comment_id
    with get_session() as session:
        coding = session.first(Coding)
        assert coding.status == "accepted"
        assert coding.coder_type == "ai"


def test_remove_drops_proposed_for_that_type(db, tmp_path):
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    remove_issue_type(issue.id)
    items = inbox_items()
    assert [item.comment.id for item in items] == [comment_id]
    assert items[0].labeled is False
    with get_session() as session:
        assert session.find(Coding, comment_id=comment_id) == []
        assert session.find(IssueExample) == []
    with pytest.raises(BadInput, match="No proposed coding"):
        accept_coding(comment_id)


def test_remove_undo_restores_proposed_so_accept_works(db, tmp_path):
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    remove_issue_type(issue.id)
    undo()
    result = accept_coding(comment_id)
    assert result.issue_type_id == issue.id
    assert inbox_items() == []


def test_deactivate_drops_proposed_for_that_type(db, tmp_path):
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    deactivate_issue_type(issue.id)
    items = inbox_items()
    assert [item.comment.id for item in items] == [comment_id]
    assert items[0].labeled is False
    with pytest.raises(BadInput, match="No proposed coding"):
        accept_coding(comment_id)


def test_accept_rejects_an_inactive_type(db, tmp_path):
    issue = create_issue_type(
        code="METHJUST",
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    with get_session() as session:
        row = session.get(IssueType, issue.id)
        row.status = "inactive"
        session.add(row)
        session.commit()
    with pytest.raises(NotFound, match="Unknown issue type"):
        accept_coding(comment_id)
    with get_session() as session:
        coding = session.first(Coding, comment_id=comment_id)
        assert coding.status == "proposed"
        assert session.find(IssueExample) == []


def test_accept_new_creates_issue_type(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "issue_name": "Missing methodological justification",
            "parent_id": None,
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    result = accept_coding(comment_id)
    with get_session() as session:
        issue = session.get(IssueType, result.issue_type_id)
        assert issue is not None
        assert issue.name == "Missing methodological justification"
        assert issue.status == "active"


def test_unknown_proposed_parent_id_becomes_root(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "issue_name": "Missing methodological justification",
            "parent_id": "not-a-type",
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    with get_session() as session:
        coding = session.first(Coding)
        assert coding.proposed_parent_id is None
    result = accept_coding(comment_id)
    with get_session() as session:
        issue = session.get(IssueType, result.issue_type_id)
        assert issue.parent_id is None


def test_existing_proposed_parent_id_is_kept(db, tmp_path):
    parent = create_issue_type(code="P", name="Parent", definition="")
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "issue_name": "Missing methodological justification",
            "parent_id": parent.id,
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    with get_session() as session:
        coding = session.first(Coding)
        assert coding.proposed_parent_id == parent.id
    result = accept_coding(comment_id)
    with get_session() as session:
        issue = session.get(IssueType, result.issue_type_id)
        assert issue.parent_id == parent.id


def test_accept_new_issue_commits_once(db, tmp_path, monkeypatch):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "issue_name": "Missing methodological justification",
            "parent_id": None,
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    from reviewdistill.db.session import StoreSession

    commits = {"n": 0}
    original = StoreSession.commit

    def counting(self):
        commits["n"] += 1
        return original(self)

    monkeypatch.setattr(StoreSession, "commit", counting)
    accept_coding(comment_id)
    assert commits["n"] == 1


def test_verify_comment_commits_once(db, tmp_path, monkeypatch):
    from reviewdistill.db.session import StoreSession

    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Too strong.}\n")
    extract_project(repo)
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    commits = {"n": 0}
    original = StoreSession.commit

    def counting(self):
        commits["n"] += 1
        return original(self)

    monkeypatch.setattr(StoreSession, "commit", counting)
    verify_comment(comment_id)
    assert commits["n"] == 1


def test_accept_new_reuses_existing_code(db, tmp_path):
    existing = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "OVERCLAIM",
            "issue_name": "Overclaiming",
            "parent_id": None,
            "definition": "A claim exceeds the evidence.",
            "confidence": 0.9,
            "rationale": "duplicate proposal",
        },
    )
    result = accept_coding(comment_id)
    assert result.issue_type_id == existing.id
    assert [issue.code for issue in list_active_issue_types()] == ["OVERCLAIM"]


def test_change_creates_human_coding(db, tmp_path):
    chosen = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    other = create_issue_type(
        code="WEAK",
        name="Weak evidence",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": other.id,
            "confidence": 0.4,
            "rationale": "wrong guess",
        },
    )
    change_coding(comment_id, issue_type_id=chosen.id)
    assert inbox_items() == []
    with get_session() as session:
        rows = session.find(Coding, comment_id=comment_id)
        statuses = {row.coder_type: row.status for row in rows}
        assert statuses["ai"] == "modified"
        assert statuses["human"] == "accepted"
        human = next(row for row in rows if row.coder_type == "human")
        assert human.issue_type_id == chosen.id


def test_change_reassigns_from_one_type_to_another(db, tmp_path):
    first = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    second = create_issue_type(
        code="WEAK",
        name="Weak evidence",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": first.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_coding(comment_id)
    assert [row.id for row in list_working_observations(first.id)] == [comment_id]
    assert list_working_observations(second.id) == []
    assert [row.source_comment_id for row in list_examples(first.id)] == [comment_id]

    change_coding(comment_id, issue_type_id=second.id)

    assert list_working_observations(first.id) == []
    assert [row.id for row in list_working_observations(second.id)] == [comment_id]
    assert accepted_counts_by_issue_type().get(first.id, 0) == 0
    assert accepted_counts_by_issue_type()[second.id] == 1
    assert list_examples(first.id) == []
    assert [row.source_comment_id for row in list_examples(second.id)] == [comment_id]
    with get_session() as session:
        accepted = [
            row for row in session.find(Coding, comment_id=comment_id) if row.status == "accepted"
        ]
        assert len(accepted) == 1
        assert accepted[0].issue_type_id == second.id
        assert session.find(IssueExample, issue_type_id=first.id, source_comment_id=comment_id) == []


def test_change_rejects_an_inactive_type(db, tmp_path):
    from reviewdistill.taxonomy.operations import deactivate_issue_type

    active = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    inactive = create_issue_type(
        code="WEAK",
        name="Weak evidence",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": active.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_coding(comment_id)
    deactivate_issue_type(inactive.id)
    with pytest.raises(ValueError, match="Unknown issue type"):
        change_coding(comment_id, issue_type_id=inactive.id)


def test_change_rejects_the_current_type(db, tmp_path):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_coding(comment_id)
    with get_session() as session:
        before = [
            (row.id, row.status, row.issue_type_id, row.coder_type)
            for row in session.find(Coding, comment_id=comment_id)
        ]
    with pytest.raises(ValueError, match="already labeled"):
        change_coding(comment_id, issue_type_id=issue.id)
    with get_session() as session:
        after = [
            (row.id, row.status, row.issue_type_id, row.coder_type)
            for row in session.find(Coding, comment_id=comment_id)
        ]
    assert after == before
    accepted = [row for row in after if row[1] == "accepted"]
    assert len(accepted) == 1


def test_labeled_absent_unreviewed_stays_in_unlabeled_inbox(db, tmp_path):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_coding(comment_id)
    assert inbox_items() == []
    (tmp_path / "paper" / "main.tex").write_text("no comments\n")
    extract_project(tmp_path / "paper")
    items = inbox_items()
    assert len(items) == 1
    assert items[0].comment.id == comment_id
    assert items[0].comment.status == "pending_disappeared"
    assert items[0].comment.quality == "unreviewed"
    assert items[0].labeled is True
    assert items[0].issue is not None
    assert items[0].issue.id == issue.id
    assert items[0].issue.code == "OVERCLAIM"
    assert items[0].issue.name == "Overclaiming"
    assert list_working_observations(issue.id) == []


def test_verify_labeled_absent_moves_off_unlabeled_onto_type(db, tmp_path):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "issue_type_id": issue.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_coding(comment_id)
    (tmp_path / "paper" / "main.tex").write_text("no comments\n")
    extract_project(tmp_path / "paper")
    verify_comment(comment_id)
    assert inbox_items() == []
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id).quality == "verified"
    assert [row.id for row in list_working_observations(issue.id)] == [comment_id]


def test_not_accepting_leaves_comment_unlabeled(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "X",
            "issue_name": "Nope",
            "parent_id": None,
            "definition": "nope",
            "confidence": 0.2,
            "rationale": "weak",
        },
    )
    assert [item.comment.id for item in inbox_items()] == [comment_id]


def test_verified_absent_comment_stays_in_working_set(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Still useful.}\n")
    extract_project(repo)
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        verify_comment(row.id)
    assert len(uncoded_comments()) == 1
    assert len(inbox_items()) == 1


def test_dropped_comment_is_not_unlabeled(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Drop me.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        drop_comment(row.id)
    assert uncoded_comments() == []
    assert inbox_items() == []


def test_verify_and_drop_quality(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{A.}\n\\myremark{B.}\n")
    extract_project(repo)
    (repo / "main.tex").write_text("\\myremark{A.}\n")
    extract_project(repo)
    items = inbox_items()
    gone = next(item for item in items if item.comment.status == "pending_disappeared")
    verify_comment(gone.comment.id)
    with get_session() as session:
        assert session.get(ProofreadingComment, gone.comment.id).quality == "verified"
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    drop_comment(gone.comment.id)
    with get_session() as session:
        assert session.get(ProofreadingComment, gone.comment.id).quality == "dropped"


def test_disappearance_guess_labels():
    unchanged = "The results demonstrate that X.\n"
    comment = ProofreadingComment(
        id="g",
        project_id="p",
        source_type="latex_command",
        source_command="myremark",
        file_path="main.tex",
        line_number=1,
        raw_text="Too strong.",
        context_text=extract_context(unchanged, 1).context_text,
        fingerprint="x",
        status="pending_disappeared",
    )
    assert disappearance_guess(comment, source=None) == VERIFY_FILE_MISSING
    assert disappearance_guess(comment, source=unchanged) == DROP_UNCHANGED
    changed = "Intro\n\nThe experiment only suggests Y.\n"
    comment.line_number = 3
    assert disappearance_guess(comment, source=changed) == VERIFY_MANUSCRIPT_CHANGED


def test_disappearance_guess_compares_full_prose_not_first_line():
    source = (
        "\\section{Results}\n"
        "\\subsection{Accuracy}\n"
        "Model A achieved higher accuracy than Model B.\n"
        "Therefore, Model A is more suitable.\n"
    )
    prose = extract_context(source, line_number=4).context_text
    comment = ProofreadingComment(
        id="g2",
        project_id="p",
        source_type="latex_command",
        source_command="myremark",
        file_path="main.tex",
        line_number=4,
        raw_text="Too strong.",
        context_text=prose + "\nCitations: skip | Refs: fig:1",
        fingerprint="x",
        status="pending_disappeared",
    )
    assert disappearance_guess(comment, source=source) == DROP_UNCHANGED


def test_verify_and_drop_work_while_present(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Still here.}\n")
    extract_project(repo)
    with get_session() as session:
        active_id = session.first(ProofreadingComment).id
    verify_comment(active_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, active_id).quality == "verified"
        assert session.get(ProofreadingComment, active_id).status == "active"
    drop_comment(active_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, active_id).quality == "dropped"
        assert session.get(ProofreadingComment, active_id).status == "active"


def test_accept_uses_newest_proposed_coding_not_lexicographic_id(db):
    from datetime import UTC, datetime

    from reviewdistill.db.models import Project

    with get_session() as session:
        session.add(Project(id="p1", name="paper", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Why this method?",
                fingerprint="fp",
                status="active",
            )
        )
        session.add(
            Coding(
                id="aaa-older-id",
                comment_id="c1",
                coder_type="ai",
                status="proposed",
                proposed_issue_name="Old",
                proposed_issue_code="OLD",
                proposed_issue_definition="older proposal",
                created_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        session.add(
            Coding(
                id="zzz-newer-id",
                comment_id="c1",
                coder_type="ai",
                status="proposed",
                proposed_issue_name="New",
                proposed_issue_code="NEWISSUE",
                proposed_issue_definition="newer proposal",
                created_at=datetime(2024, 6, 1, tzinfo=UTC),
            )
        )
        session.commit()
    items = inbox_items()
    assert len(items) == 1
    assert items[0].coding is not None
    assert items[0].coding.id == "zzz-newer-id"
    accepted = accept_coding("c1")
    assert accepted.id == "zzz-newer-id"
    assert accepted.status == "accepted"


def test_inbox_and_uncoded_order_by_created_at_not_id(db):
    from datetime import UTC, datetime

    from reviewdistill.db.models import Project

    with get_session() as session:
        session.add(Project(id="p1", name="paper", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="aaa-newer",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=2,
                raw_text="newer comment",
                fingerprint="fp-new",
                status="active",
                created_at=datetime(2024, 6, 1, tzinfo=UTC),
            )
        )
        session.add(
            ProofreadingComment(
                id="zzz-older",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="older comment",
                fingerprint="fp-old",
                status="active",
                created_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    assert [row.id for row in uncoded_comments()] == ["zzz-older", "aaa-newer"]
    assert [item.comment.id for item in inbox_items()] == ["zzz-older", "aaa-newer"]
