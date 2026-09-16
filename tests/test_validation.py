import pytest

from reviewdistill.cli.init import init_project
from reviewdistill.labeling.coder import unlabeled_for_ai
from reviewdistill.labeling.validation import (
    DELETE_UNCHANGED,
    VERIFY_FILE_MISSING,
    VERIFY_MANUSCRIPT_CHANGED,
    accept_assignment,
    change_assignment,
    disappearance_guess,
    delete_comment,
    inbox_items,
    verify_comment,
)
from reviewdistill.context.manuscript import extract_context
from reviewdistill.db.models import Assignment, LabelExample, Label, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.errors import BadInput, Conflict, NotFound
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.history import list_history, undo
from reviewdistill.taxonomy.operations import (
    accepted_counts_by_label,
    create_label,
    deactivate_label,
    list_active_labels,
    list_examples,
    list_working_observations,
    remove_label,
)


def _seed_proposed(tmp_path, response: dict) -> str:
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Why did we choose this method?}\n")
    extract_project(repo)
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        session.add(
            Assignment(
                id="seed-proposed",
                comment_id=comment.id,
                label_id=response.get("label_id"),
                coder_type="ai",
                status="proposed",
                proposed_label_name=response.get("label_name"),
                proposed_label_definition=response.get("definition"),
                proposed_parent_id=response.get("parent_id"),
                confidence=response.get("confidence"),
                rationale=response.get("rationale"),
            )
        )
        session.commit()
        return comment.id


def test_accept_existing_marks_assignment_and_adds_example(db, tmp_path):
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    with get_session() as session:
        comment = session.get(ProofreadingComment, comment_id)
        comment.raw_text = "Why did we choose this method?"
        comment.context_text = "Peak picking follows the energy rule in the supplement."
        session.commit()
    result = accept_assignment(comment_id)
    assert result.label_id == label.id
    assert inbox_items() == []
    examples = list_examples(label.id)
    assert examples[0].source_comment_id == comment_id
    with get_session() as session:
        coding = session.first(Assignment)
        assert coding.status == "accepted"
        assert coding.coder_type == "ai"
        stored = session.first(LabelExample)
        assert stored.text == "Peak picking follows the energy rule in the supplement."


def test_remove_drops_proposed_for_that_type(db, tmp_path):
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    remove_label(label.id)
    items = inbox_items()
    assert [item.comment.id for item in items] == [comment_id]
    assert items[0].labeled is False
    with get_session() as session:
        assert session.find(Assignment, comment_id=comment_id) == []
        assert session.find(LabelExample) == []
    with pytest.raises(BadInput, match="No proposed assignment"):
        accept_assignment(comment_id)


def test_remove_undo_restores_proposed_so_accept_works(db, tmp_path):
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    remove_label(label.id)
    undo()
    result = accept_assignment(comment_id)
    assert result.label_id == label.id
    assert inbox_items() == []


def test_deactivate_drops_proposed_for_that_type(db, tmp_path):
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    deactivate_label(label.id)
    items = inbox_items()
    assert [item.comment.id for item in items] == [comment_id]
    assert items[0].labeled is False
    with pytest.raises(BadInput, match="No proposed assignment"):
        accept_assignment(comment_id)


def test_accept_rejects_an_inactive_type(db, tmp_path):
    label = create_label(
        name="Missing methodological justification",
        definition="A design choice is unexplained.",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.84,
            "rationale": "Asks why the method was chosen.",
        },
    )
    with get_session() as session:
        row = session.get(Label, label.id)
        row.status = "inactive"
        session.add(row)
        session.commit()
    with pytest.raises(NotFound, match="Unknown label"):
        accept_assignment(comment_id)
    with get_session() as session:
        coding = session.first(Assignment, comment_id=comment_id)
        assert coding.status == "proposed"
        assert session.find(LabelExample) == []


def test_accept_new_creates_issue_type(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "label_name": "Missing methodological justification",
            "parent_id": None,
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    result = accept_assignment(comment_id)
    with get_session() as session:
        label = session.get(Label, result.label_id)
        assert label is not None
        assert label.name == "Missing methodological justification"
        assert label.status == "active"


def test_unknown_proposed_parent_id_becomes_root(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "label_name": "Missing methodological justification",
            "parent_id": "not-a-type",
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    with get_session() as session:
        coding = session.first(Assignment)
        assert coding.proposed_parent_id == "not-a-type"
    result = accept_assignment(comment_id)
    with get_session() as session:
        label = session.get(Label, result.label_id)
        assert label.parent_id is None


def test_existing_proposed_parent_id_is_kept(db, tmp_path):
    parent = create_label(name="Parent", definition="")
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "label_name": "Missing methodological justification",
            "parent_id": parent.id,
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    with get_session() as session:
        coding = session.first(Assignment)
        assert coding.proposed_parent_id == parent.id
    result = accept_assignment(comment_id)
    with get_session() as session:
        label = session.get(Label, result.label_id)
        assert label.parent_id == parent.id


def test_accept_new_type_under_leaf_moves_existing_labels_onto_ungrouped(db, tmp_path):
    parent = create_label(name="Parent", definition="")
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-kept",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="Already labeled.",
                status="active",
            )
        )
        session.add(
            Assignment(
                id="k-kept",
                comment_id="c-kept",
                label_id=parent.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "label_name": "Missing methodological justification",
            "parent_id": parent.id,
            "definition": "A design choice is unexplained.",
            "confidence": 0.78,
            "rationale": "Unexplained design decision.",
        },
    )
    result = accept_assignment(comment_id)
    with get_session() as session:
        label = session.get(Label, result.label_id)
        assert label.parent_id == parent.id
        kids = [row for row in session.find(Label, status="active") if row.parent_id == parent.id]
        ungrouped = next(row for row in kids if row.name == "ungrouped")
        kept = session.first(Assignment, comment_id="c-kept", status="accepted")
        assert kept.label_id == ungrouped.id
        assert label.id != ungrouped.id


def test_accept_new_issue_commits_once(db, tmp_path, monkeypatch):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "METHJUST",
            "label_name": "Missing methodological justification",
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
    accept_assignment(comment_id)
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


def test_accept_new_reuses_existing_label(db, tmp_path):
    existing = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "OVERCLAIM",
            "label_name": "Overclaiming",
            "parent_id": None,
            "definition": "A claim exceeds the evidence.",
            "confidence": 0.9,
            "rationale": "duplicate proposal",
        },
    )
    result = accept_assignment(comment_id)
    assert result.label_id == existing.id
    assert [label.name for label in list_active_labels()] == ["Overclaiming"]


def test_change_creates_human_assignment(db, tmp_path):
    chosen = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    other = create_label(
        name="Weak evidence",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": other.id,
            "confidence": 0.4,
            "rationale": "wrong guess",
        },
    )
    change_assignment(comment_id, label_id=chosen.id)
    assert inbox_items() == []
    with get_session() as session:
        rows = session.find(Assignment, comment_id=comment_id)
        statuses = {row.coder_type: row.status for row in rows}
        assert statuses["ai"] == "modified"
        assert statuses["human"] == "accepted"
        human = next(row for row in rows if row.coder_type == "human")
        assert human.label_id == chosen.id


def test_change_reassigns_from_one_type_to_another(db, tmp_path):
    first = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    second = create_label(
        name="Weak evidence",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": first.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_assignment(comment_id)
    assert [row.id for row in list_working_observations(first.id)] == [comment_id]
    assert list_working_observations(second.id) == []
    assert [row.source_comment_id for row in list_examples(first.id)] == [comment_id]

    change_assignment(comment_id, label_id=second.id)

    assert list_working_observations(first.id) == []
    assert [row.id for row in list_working_observations(second.id)] == [comment_id]
    assert accepted_counts_by_label().get(first.id, 0) == 0
    assert accepted_counts_by_label()[second.id] == 1
    assert list_examples(first.id) == []
    assert [row.source_comment_id for row in list_examples(second.id)] == [comment_id]
    with get_session() as session:
        accepted = [
            row for row in session.find(Assignment, comment_id=comment_id) if row.status == "accepted"
        ]
        assert len(accepted) == 1
        assert accepted[0].label_id == second.id
        assert session.find(LabelExample, label_id=first.id, source_comment_id=comment_id) == []


def test_change_rejects_an_inactive_type(db, tmp_path):
    from reviewdistill.taxonomy.operations import deactivate_label

    active = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    inactive = create_label(
        name="Weak evidence",
        definition="evidence is thin",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": active.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_assignment(comment_id)
    deactivate_label(inactive.id)
    with pytest.raises(ValueError, match="Unknown label"):
        change_assignment(comment_id, label_id=inactive.id)


def test_change_rejects_the_current_type(db, tmp_path):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_assignment(comment_id)
    with get_session() as session:
        before = [
            (row.id, row.status, row.label_id, row.coder_type)
            for row in session.find(Assignment, comment_id=comment_id)
        ]
    with pytest.raises(ValueError, match="already labeled"):
        change_assignment(comment_id, label_id=label.id)
    with get_session() as session:
        after = [
            (row.id, row.status, row.label_id, row.coder_type)
            for row in session.find(Assignment, comment_id=comment_id)
        ]
    assert after == before
    accepted = [row for row in after if row[1] == "accepted"]
    assert len(accepted) == 1


def test_change_rejects_a_type_that_has_children(db, tmp_path):
    parent = create_label(name="Parent", definition="")
    create_label(name="Child", definition="", parent_id=parent.id)
    leaf = create_label(name="Leaf", definition="")
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": leaf.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_assignment(comment_id)
    with pytest.raises(ValueError, match="leaf"):
        change_assignment(comment_id, label_id=parent.id)


def test_labeled_absent_unreviewed_stays_in_unlabeled_inbox(db, tmp_path):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_assignment(comment_id)
    assert inbox_items() == []
    (tmp_path / "paper" / "main.tex").write_text("no comments\n")
    extract_project(tmp_path / "paper")
    items = inbox_items()
    assert len(items) == 1
    assert items[0].comment.id == comment_id
    assert items[0].comment.status == "pending_disappeared"
    assert items[0].comment.verified is False
    assert items[0].labeled is True
    assert items[0].label is not None
    assert items[0].label.id == label.id
    assert items[0].label.name == "Overclaiming"
    assert items[0].label.name == "Overclaiming"
    assert list_working_observations(label.id) == []


def test_verify_labeled_absent_moves_off_unlabeled_onto_type(db, tmp_path):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "existing",
            "label_id": label.id,
            "confidence": 0.9,
            "rationale": "too strong",
        },
    )
    accept_assignment(comment_id)
    (tmp_path / "paper" / "main.tex").write_text("no comments\n")
    extract_project(tmp_path / "paper")
    verify_comment(comment_id)
    assert inbox_items() == []
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id).verified
    assert [row.id for row in list_working_observations(label.id)] == [comment_id]


def test_not_accepting_leaves_comment_unlabeled(db, tmp_path):
    comment_id = _seed_proposed(
        tmp_path,
        {
            "recommendation": "new",
            "issue_code": "X",
            "label_name": "Nope",
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
    assert len(unlabeled_for_ai()) == 1
    assert len(inbox_items()) == 1


def test_deleted_comment_is_gone(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Drop me.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        comment_id = row.id
    delete_comment(comment_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id) is None
    assert unlabeled_for_ai() == []
    assert inbox_items() == []
    with pytest.raises(NotFound, match="Unknown comment"):
        delete_comment(comment_id)


def test_delete_removes_assignments_and_sourced_examples(db, tmp_path):
    from reviewdistill.taxonomy.operations import add_example

    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Too strong.}\n")
    extract_project(repo)
    label = create_label(name="Overclaiming", definition="too strong")
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    change_assignment(comment_id, label_id=label.id)
    add_example(label.id, text="Too strong.", source_comment_id=comment_id)
    delete_comment(comment_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id) is None
        assert session.find(Assignment, comment_id=comment_id) == []
        assert session.find(LabelExample, source_comment_id=comment_id) == []
    assert list_examples(label.id) == []


def test_verify_toggles_off_and_undo_restores_verified(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Keep me.}\n")
    extract_project(repo)
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    verify_comment(comment_id)
    verify_comment(comment_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id).verified is False
    assert list_history()["events"][0]["event_type"] == "unverify"
    undo()
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id).verified


def test_delete_refuses_verified_comment(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Keep me.}\n")
    extract_project(repo)
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    verify_comment(comment_id)
    with pytest.raises(Conflict, match="Unverify before deleting"):
        delete_comment(comment_id)
    with get_session() as session:
        assert session.get(ProofreadingComment, comment_id) is not None
        assert session.get(ProofreadingComment, comment_id).verified


def test_verify_then_delete_absent_comment(db, tmp_path):
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
    with pytest.raises(Conflict, match="Unverify before deleting"):
        delete_comment(gone.comment.id)
    verify_comment(gone.comment.id)
    delete_comment(gone.comment.id)
    with get_session() as session:
        assert session.get(ProofreadingComment, gone.comment.id) is None


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
        status="pending_disappeared",
    )
    assert disappearance_guess(comment, source=None) == VERIFY_FILE_MISSING
    assert disappearance_guess(comment, source=unchanged) == DELETE_UNCHANGED
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
        context_text=prose,
        status="pending_disappeared",
    )
    assert disappearance_guess(comment, source=source) == DELETE_UNCHANGED




def test_accept_uses_newest_proposed_assignment_not_lexicographic_id(db):
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
                status="active",
            )
        )
        session.add(
            Assignment(
                id="aaa-older-id",
                comment_id="c1",
                coder_type="ai",
                status="proposed",
                proposed_label_name="Old",
                proposed_label_definition="older proposal",
                created_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        session.add(
            Assignment(
                id="zzz-newer-id",
                comment_id="c1",
                coder_type="ai",
                status="proposed",
                proposed_label_name="New",
                proposed_label_definition="newer proposal",
                created_at=datetime(2024, 6, 1, tzinfo=UTC),
            )
        )
        session.commit()
    items = inbox_items()
    assert len(items) == 1
    assert items[0].assignment is not None
    assert items[0].assignment.id == "zzz-newer-id"
    accepted = accept_assignment("c1")
    assert accepted.id == "zzz-newer-id"
    assert accepted.status == "accepted"


def test_inbox_and_unlabeled_order_by_created_at_not_id(db):
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
                status="active",
                created_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    assert [row.id for row in unlabeled_for_ai()] == ["zzz-older", "aaa-newer"]
    assert [item.comment.id for item in inbox_items()] == ["zzz-older", "aaa-newer"]
