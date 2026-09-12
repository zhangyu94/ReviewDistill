from fastapi.testclient import TestClient

from reviewdistill.db.models import Coding, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.taxonomy.operations import (
    add_example,
    create_issue_type,
    deactivate_issue_type,
    merge_issue_types,
    rename_issue_type,
)
from reviewdistill.web.app import create_app


def test_taxonomy_returns_forest(db):
    parent = create_issue_type(code="P", name="Parent", definition="")
    create_issue_type(code="C", name="Child", definition="", parent_id=parent.id)
    client = TestClient(create_app())
    response = client.get("/api/taxonomy")
    assert response.status_code == 200
    forest = response.json()["forest"]
    assert forest[0]["code"] == "P"
    assert forest[0]["children"][0]["code"] == "C"


def test_issue_detail_shows_definition_examples_and_observations(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="A claim is stronger than the evidence supports.",
    )
    add_example(issue.id, text="demonstrate → suggest")
    client = TestClient(create_app())
    response = client.get(f"/api/taxonomy/{issue.id}")
    assert response.status_code == 200
    body = response.json()
    assert "A claim is stronger" in body["definition"]
    assert any("demonstrate" in row["text"] for row in body["examples"])
    assert body["comments"] == []


def test_issue_detail_404s_for_inactive_types(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    deactivate_issue_type(issue.id)
    client = TestClient(create_app())
    response = client.get(f"/api/taxonomy/{issue.id}")
    assert response.status_code == 404
    assert "Unknown issue type" in response.json()["detail"]


def test_issue_comments_include_manuscript_context(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-ctx",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="sections/results.tex",
                line_number=42,
                raw_text="too strong here",
                context_text="The results prove X.\nlabel=fig:1",
                section="Results",
                fingerprint="fp-ctx",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-ctx",
                comment_id="c-ctx",
                issue_type_id=issue.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    client = TestClient(create_app())
    comment = client.get(f"/api/taxonomy/{issue.id}").json()["comments"][0]
    assert comment["id"] == "c-ctx"
    assert comment["raw_text"] == "too strong here"
    assert comment["context_text"].startswith("The results prove X.")
    assert comment["file_path"] == "sections/results.tex"
    assert comment["line_number"] == 42
    assert comment["section"] == "Results"
    assert comment["source_command"] == "myremark"
    assert "project_name" in comment


def test_history_lists_rename_and_merge(db):
    a = create_issue_type(code="U", name="Unsupported claim", definition="a")
    b = create_issue_type(code="S", name="Overly strong claim", definition="b")
    target = create_issue_type(code="O", name="Overclaiming", definition="c")
    rename_issue_type(a.id, name="Unsupported claim (old)")
    merge_issue_types(source_ids=[a.id, b.id], target_id=target.id)
    client = TestClient(create_app())
    response = client.get("/api/history")
    assert response.status_code == 200
    types = [event["event_type"] for event in response.json()["events"]]
    assert "add" in types
    assert "rename" in types
    assert "merge" in types
    assert types[0] == "merge"
    assert isinstance(response.json()["events"][0]["payload"], dict)


def test_merged_source_observations_appear_on_target_detail(db):
    source = create_issue_type(code="A", name="Type A", definition="a")
    target = create_issue_type(code="B", name="Type B", definition="b")
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-a",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="observation from A",
                fingerprint="fp-a",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-a",
                comment_id="c-a",
                issue_type_id=source.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    merge_issue_types(source_ids=[source.id], target_id=target.id)
    client = TestClient(create_app())
    body = client.get(f"/api/taxonomy/{target.id}").json()
    assert any(row["raw_text"] == "observation from A" for row in body["comments"])


def test_taxonomy_omits_dropped_observations_and_counts(db):
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-live",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="too strong live",
                fingerprint="fp-live",
                status="active",
            )
        )
        session.add(
            ProofreadingComment(
                id="c-dropped",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=2,
                raw_text="too strong dropped",
                fingerprint="fp-dropped",
                status="active",
                quality="dropped",
            )
        )
        session.add(
            Coding(
                id="coding-live",
                comment_id="c-live",
                issue_type_id=issue.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Coding(
                id="coding-dropped",
                comment_id="c-dropped",
                issue_type_id=issue.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    client = TestClient(create_app())
    listed = client.get("/api/taxonomy").json()
    row = next(item for item in listed["forest"] if item["id"] == issue.id)
    assert row["count"] == 1
    detail = client.get(f"/api/taxonomy/{issue.id}").json()
    assert [comment["id"] for comment in detail["comments"]] == ["c-live"]
    assert all(comment["raw_text"] != "too strong dropped" for comment in detail["comments"])


def test_rename_post_json(db):
    issue = create_issue_type(code="OVERCLAIM", name="Overclaiming", definition="x")
    client = TestClient(create_app())
    response = client.post(
        f"/api/taxonomy/{issue.id}/rename",
        json={"name": "Overclaiming (renamed)", "code": "OVERCLAIM"},
    )
    assert response.status_code == 200
    assert client.get(f"/api/taxonomy/{issue.id}").json()["name"] == "Overclaiming (renamed)"


def test_move_post_nests_under_parent(db):
    parent = create_issue_type(code="P", name="Parent", definition="p")
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.post(
        f"/api/taxonomy/{issue.id}/move",
        json={"parent_id": parent.id, "position": 0},
    )
    assert response.status_code == 200
    body = client.get(f"/api/taxonomy/{issue.id}").json()
    assert body["parent_id"] == parent.id
    assert body["definition"] == "too strong"


def test_create_flatten_remove_http(db):
    client = TestClient(create_app())
    created = client.post("/api/taxonomy", json={"parent_id": None})
    assert created.status_code == 200
    parent_id = created.json()["id"]
    child = client.post("/api/taxonomy", json={"parent_id": parent_id})
    assert child.status_code == 200
    flattened = client.post(f"/api/taxonomy/{parent_id}/flatten")
    assert flattened.status_code == 200
    removed = client.post(f"/api/taxonomy/{parent_id}/remove")
    assert removed.status_code == 200
    assert client.get("/api/taxonomy").json()["forest"] == []


def test_issue_comments_and_count_are_subtree(db):
    parent = create_issue_type(code="P", name="Parent", definition="")
    child = create_issue_type(code="C", name="Child", definition="", parent_id=parent.id)
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="c-child",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="child observation",
                fingerprint="fp-child",
                status="active",
            )
        )
        session.add(
            Coding(
                id="coding-child",
                comment_id="c-child",
                issue_type_id=child.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    client = TestClient(create_app())
    listed = client.get("/api/taxonomy").json()
    row = next(item for item in listed["forest"] if item["id"] == parent.id)
    assert row["count"] == 1
    assert row["children"][0]["count"] == 1
    detail = client.get(f"/api/taxonomy/{parent.id}").json()
    assert [comment["id"] for comment in detail["comments"]] == ["c-child"]
    assert detail["comments"][0]["issue"] == {
        "id": child.id,
        "code": "C",
        "name": "Child",
        "parent_id": parent.id,
    }


def test_move_unknown_issue_is_404(db):
    client = TestClient(create_app())
    response = client.post("/api/taxonomy/missing/move", json={"parent_id": None, "position": 0})
    assert response.status_code == 404


def test_inactive_issue_mutations_are_404(db):
    issue = create_issue_type(code="L", name="Leaf", definition="")
    other = create_issue_type(code="T", name="Target", definition="")
    deactivate_issue_type(issue.id)
    client = TestClient(create_app())
    assert client.post(f"/api/taxonomy/{issue.id}/flatten").status_code == 404
    assert client.post(f"/api/taxonomy/{issue.id}/remove").status_code == 404
    assert (
        client.post(f"/api/taxonomy/{issue.id}/move", json={"parent_id": None, "position": 0}).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/taxonomy/{issue.id}/split",
            json={
                "left": {"code": "L", "name": "Left", "definition": "l"},
                "right": {"code": "R", "name": "Right", "definition": "r"},
            },
        ).status_code
        == 404
    )
    assert (
        client.post("/api/taxonomy/merge", json={"source_ids": [issue.id], "target_id": other.id}).status_code
        == 404
    )
    deactivate_issue_type(other.id)
    live = create_issue_type(code="S", name="Source", definition="")
    assert (
        client.post("/api/taxonomy/merge", json={"source_ids": [live.id], "target_id": other.id}).status_code
        == 404
    )


def test_export_get_markdown(db):
    create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.get("/api/taxonomy/export", params={"format": "md"})
    assert response.status_code == 200
    assert "Scholarly Review Rubric" in response.text
    assert "Overclaiming" in response.text


def test_export_unknown_format_is_400(db):
    client = TestClient(create_app())
    response = client.get("/api/taxonomy/export", params={"format": "xlsx"})
    assert response.status_code == 400
