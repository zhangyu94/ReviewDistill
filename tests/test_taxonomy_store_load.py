import json

import pytest

from reviewdistill.db.models import Coding, Label
from reviewdistill.db.session import get_session, init_db, reset_engine
from reviewdistill.errors import CorruptStore
from reviewdistill.taxonomy.operations import rename_label


def test_store_does_not_rewrite_category_rows(rd_home):
    reset_engine()
    path = rd_home / "labels.jsonl"
    row = {
        "id": "t1",
        "name": "Alpha",
        "category": "Argumentation",
        "definition": "a",
        "status": "active",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    init_db()
    with get_session() as session:
        loaded = session.get(Label, "t1")
        assert loaded is not None
        assert loaded.parent_id is None
        assert loaded.position == 0
    saved = path.read_text(encoding="utf-8")
    assert "category" in saved
    assert "parent_id" not in saved


def test_store_loads_issue_type_with_leftover_notes_and_drops_them_on_rewrite(rd_home):
    reset_engine()
    path = rd_home / "labels.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "t1",
                "name": "Alpha",
                "definition": "a",
                "notes": "Watch epistemic verbs.",
                "status": "active",
                "parent_id": None,
                "position": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with get_session() as session:
        loaded = session.get(Label, "t1")
        assert loaded is not None
        assert loaded.definition == "a"
        assert "notes" not in loaded.model_dump()
    rename_label("t1", name="Alpha")
    saved = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "notes" not in saved
    assert saved["name"] == "Alpha"


def test_store_does_not_rewrite_proposed_issue_category(rd_home):
    reset_engine()
    (rd_home / "codings.jsonl").write_text(
        json.dumps(
            {
                "id": "c1",
                "comment_id": "x",
                "coder_type": "ai",
                "status": "proposed",
                "proposed_issue_category": "Argumentation",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with get_session() as session:
        loaded = session.get(Coding, "c1")
        assert loaded is not None
        assert loaded.proposed_parent_id is None
    saved = (rd_home / "codings.jsonl").read_text(encoding="utf-8")
    assert "proposed_issue_category" in saved
    assert "proposed_parent_id" not in saved


def test_invalid_active_parent_fails_fast(rd_home):
    reset_engine()
    path = rd_home / "labels.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "t1",
                "name": "A",
                "parent_id": "missing",
                "position": 0,
                "definition": "",
                "status": "active",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with pytest.raises(CorruptStore), get_session():
        pass


def test_self_parent_fails_fast(rd_home):
    reset_engine()
    path = rd_home / "labels.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "t1",
                "name": "A",
                "parent_id": "t1",
                "position": 0,
                "definition": "",
                "status": "active",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with pytest.raises(CorruptStore), get_session():
        pass


def test_parent_cycle_fails_fast(rd_home):
    reset_engine()
    path = rd_home / "labels.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "t1",
                        "name": "A",
                        "parent_id": "t2",
                        "position": 0,
                        "definition": "",
                        "status": "active",
                    }
                ),
                json.dumps(
                    {
                        "id": "t2",
                        "name": "B",
                        "parent_id": "t1",
                        "position": 0,
                        "definition": "",
                        "status": "active",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with pytest.raises(CorruptStore), get_session():
        pass


def test_inactive_parent_of_active_type_fails_fast(rd_home):
    reset_engine()
    path = rd_home / "labels.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "p1",
                        "name": "Parent",
                        "parent_id": None,
                        "position": 0,
                        "definition": "",
                        "status": "inactive",
                    }
                ),
                json.dumps(
                    {
                        "id": "c1",
                        "name": "Child",
                        "parent_id": "p1",
                        "position": 0,
                        "definition": "",
                        "status": "active",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    init_db()
    with pytest.raises(CorruptStore), get_session():
        pass
