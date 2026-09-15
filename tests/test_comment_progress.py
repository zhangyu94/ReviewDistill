from reviewdistill.db.models import ProofreadingComment
from reviewdistill.views import comment_progress


def _comment(**kwargs) -> ProofreadingComment:
    row = {
        "id": "c1",
        "project_id": "p",
        "source_type": "latex_command",
        "source_command": "myremark",
        "file_path": "main.tex",
        "line_number": 1,
        "raw_text": "text",
        "status": "active",
        "verified": False,
    }
    row.update(kwargs)
    return ProofreadingComment(**row)


def test_empty_store_is_zeros():
    counts = comment_progress([], set())
    assert counts == {
        "working_set": 0,
        "unlabeled": 0,
        "labeled": 0,
        "unreviewed": 0,
        "verified": 0,
    }
    assert "absent" not in counts
    assert "dropped" not in counts


def test_working_set_split_and_quality_partition():
    live = _comment(id="live")
    labeled = _comment(id="lab")
    gone = _comment(id="gone", status="pending_disappeared")
    counts = comment_progress([live, labeled, gone], {"lab"})
    assert counts["working_set"] == 2
    assert counts["unlabeled"] == 1
    assert counts["labeled"] == 1
    assert counts["unreviewed"] == 3
    assert counts["verified"] == 0
    assert "dropped" not in counts
    assert counts["unlabeled"] + counts["labeled"] == counts["working_set"]
    assert counts["unreviewed"] + counts["verified"] == 3


def test_left_manuscript_unreviewed_is_outside_working_set():
    gone = _comment(
        id="abs",
        status="pending_disappeared",
    )
    counts = comment_progress([gone], set())
    assert "absent" not in counts
    assert counts["unreviewed"] == 1
    assert counts["working_set"] == 0
    assert counts["unlabeled"] == 0


def test_left_manuscript_verified_stays_in_working_set():
    gone = _comment(
        id="av",
        status="pending_disappeared",
        verified=True,
    )
    counts = comment_progress([gone], set())
    assert "absent" not in counts
    assert counts["verified"] == 1
    assert counts["working_set"] == 1
    assert counts["unlabeled"] == 1
    assert counts["labeled"] == 0
