from fastapi.testclient import TestClient

from reviewdistill.db.models import Assignment, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import (
    add_example,
    create_label,
    deactivate_label,
    merge_labels,
    rename_label,
)
from reviewdistill.web.app import create_app


def _add_comment(comment_id: str, text: str, *, label_id: str | None = None):
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id=comment_id,
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text=text,
                status="active",
            )
        )
        if label_id:
            session.add(
                Assignment(
                    id=f"k-{comment_id}",
                    comment_id=comment_id,
                    label_id=label_id,
                    coder_type="human",
                    status="accepted",
                )
            )
        session.commit()


def test_taxonomy_returns_forest(db):
    parent = create_label(name="Parent", definition="")
    create_label(name="Child", definition="", parent_id=parent.id)
    client = TestClient(create_app())
    response = client.get("/api/labels")
    assert response.status_code == 200
    forest = response.json()["forest"]
    assert forest[0]["name"] == "Parent"
    assert forest[0]["children"][0]["name"] == "Child"


def test_issue_detail_shows_definition_examples_and_observations(db):
    label = create_label(
        name="Overclaiming",
        definition="A claim is stronger than the evidence supports.",
    )
    add_example(label.id, text="demonstrate → suggest")
    client = TestClient(create_app())
    response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    body = response.json()
    assert "A claim is stronger" in body["definition"]
    assert any("demonstrate" in row["text"] for row in body["examples"])
    assert body["comments"] == []
    assert "notes" not in body


def test_deactivate_is_not_an_http_route(db):
    label = create_label(name="Overclaiming", definition="too strong")
    client = TestClient(create_app())
    response = client.post(f"/api/labels/{label.id}/deactivate")
    assert response.status_code in {404, 405}


def test_issue_detail_404s_for_inactive_types(db):
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    deactivate_label(label.id)
    client = TestClient(create_app())
    response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 404
    assert "Unknown label" in response.json()["detail"]


def test_issue_comments_include_manuscript_context(db):
    label = create_label(
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
                status="active",
            )
        )
        session.add(
            Assignment(
                id="coding-ctx",
                comment_id="c-ctx",
                label_id=label.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    client = TestClient(create_app())
    comment = client.get(f"/api/labels/{label.id}").json()["comments"][0]
    assert comment["id"] == "c-ctx"
    assert comment["raw_text"] == "too strong here"
    assert comment["context_text"].startswith("The results prove X.")
    assert comment["file_path"] == "sections/results.tex"
    assert comment["line_number"] == 42
    assert comment["section"] == "Results"
    assert comment["source_command"] == "myremark"
    assert "project_name" in comment


def test_history_lists_rename_and_merge(db):
    a = create_label(name="Unsupported claim", definition="a")
    b = create_label(name="Overly strong claim", definition="b")
    target = create_label(name="Overclaiming", definition="c")
    rename_label(a.id, name="Unsupported claim (old)")
    merge_labels(source_ids=[a.id, b.id], target_id=target.id)
    client = TestClient(create_app())
    response = client.get("/api/history")
    assert response.status_code == 200
    types = [event["event_type"] for event in response.json()["events"]]
    assert "add" in types
    assert "rename" in types
    assert "merge" in types
    assert types[0] == "merge"
    assert isinstance(response.json()["events"][0]["payload"], dict)
    first = response.json()["events"][0]
    assert first["details"]["explanation"] == (
        "Merged Unsupported claim (old), Overly strong claim into Overclaiming."
    )


def test_merged_source_observations_appear_on_target_detail(db):
    source = create_label(name="Type A", definition="a")
    target = create_label(name="Type B", definition="b")
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
                status="active",
            )
        )
        session.add(
            Assignment(
                id="coding-a",
                comment_id="c-a",
                label_id=source.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    merge_labels(source_ids=[source.id], target_id=target.id)
    client = TestClient(create_app())
    body = client.get(f"/api/labels/{target.id}").json()
    assert any(row["raw_text"] == "observation from A" for row in body["comments"])


def test_taxonomy_omits_comments_not_to_distill(db):
    label = create_label(
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
                status="pending_disappeared",
            )
        )
        session.add(
            Assignment(
                id="coding-live",
                comment_id="c-live",
                label_id=label.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.add(
            Assignment(
                id="coding-dropped",
                comment_id="c-dropped",
                label_id=label.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    client = TestClient(create_app())
    listed = client.get("/api/labels").json()
    row = next(item for item in listed["forest"] if item["id"] == label.id)
    assert row["count"] == 1
    detail = client.get(f"/api/labels/{label.id}").json()
    assert [comment["id"] for comment in detail["comments"]] == ["c-live"]
    assert all(comment["raw_text"] != "too strong dropped" for comment in detail["comments"])


def test_rename_post_json(db):
    label = create_label(name="Overclaiming", definition="x")
    client = TestClient(create_app())
    response = client.post(
        f"/api/labels/{label.id}/rename",
        json={"name": "Overclaiming (renamed)"},
    )
    assert response.status_code == 200
    assert client.get(f"/api/labels/{label.id}").json()["name"] == "Overclaiming (renamed)"


def test_edit_post_json_has_no_notes(db):
    label = create_label(name="Overclaiming", definition="old")
    client = TestClient(create_app())
    response = client.post(
        f"/api/labels/{label.id}/edit",
        json={"definition": "A claim exceeds the evidence."},
    )
    assert response.status_code == 200
    body = client.get(f"/api/labels/{label.id}").json()
    assert body["definition"] == "A claim exceeds the evidence."
    assert "notes" not in body
    edit = next(
        event for event in client.get("/api/history").json()["events"] if event["event_type"] == "edit"
    )
    assert "notes" not in edit["payload"]["before"]
    assert "notes" not in edit["payload"]["after"]


def test_move_post_nests_under_parent(db):
    parent = create_label(name="Parent", definition="p")
    label = create_label(
        name="Overclaiming",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.post(
        f"/api/labels/{label.id}/move",
        json={"parent_id": parent.id, "position": 0},
    )
    assert response.status_code == 200
    body = client.get(f"/api/labels/{label.id}").json()
    assert body["parent_id"] == parent.id
    assert body["definition"] == "too strong"


def test_create_flatten_remove_http(db):
    client = TestClient(create_app())
    created = client.post("/api/labels", json={"parent_id": None})
    assert created.status_code == 200
    parent_id = created.json()["id"]
    child = client.post("/api/labels", json={"parent_id": parent_id})
    assert child.status_code == 200
    flattened = client.post(f"/api/labels/{parent_id}/flatten")
    assert flattened.status_code == 200
    removed = client.post(f"/api/labels/{parent_id}/remove")
    assert removed.status_code == 200
    assert client.get("/api/labels").json()["forest"] == []


def test_issue_comments_and_count_are_subtree(db):
    parent = create_label(name="Parent", definition="")
    child = create_label(name="Child", definition="", parent_id=parent.id)
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
                status="active",
            )
        )
        session.add(
            Assignment(
                id="coding-child",
                comment_id="c-child",
                label_id=child.id,
                coder_type="human",
                status="accepted",
            )
        )
        session.commit()
    client = TestClient(create_app())
    listed = client.get("/api/labels").json()
    row = next(item for item in listed["forest"] if item["id"] == parent.id)
    assert row["count"] == 1
    assert row["children"][0]["count"] == 1
    detail = client.get(f"/api/labels/{parent.id}").json()
    assert [comment["id"] for comment in detail["comments"]] == ["c-child"]
    assert detail["comments"][0]["label"] == {
        "id": child.id,
        "name": "Child",
        "parent_id": parent.id,
    }


def test_move_unknown_issue_is_404(db):
    client = TestClient(create_app())
    response = client.post("/api/labels/missing/move", json={"parent_id": None, "position": 0})
    assert response.status_code == 404


def test_inactive_issue_mutations_are_404(db):
    label = create_label(name="Leaf", definition="")
    other = create_label(name="Target", definition="")
    deactivate_label(label.id)
    client = TestClient(create_app())
    assert client.post(f"/api/labels/{label.id}/flatten").status_code == 404
    assert client.post(f"/api/labels/{label.id}/remove").status_code == 404
    assert (
        client.post(f"/api/labels/{label.id}/move", json={"parent_id": None, "position": 0}).status_code
        == 404
    )
    assert (
        client.post(f"/api/labels/{label.id}/split").status_code
        == 404
    )
    assert (
        client.post("/api/labels/merge", json={"source_ids": [label.id], "target_id": other.id}).status_code
        == 404
    )
    deactivate_label(other.id)
    live = create_label(name="Source", definition="")
    assert (
        client.post("/api/labels/merge", json={"source_ids": [live.id], "target_id": other.id}).status_code
        == 404
    )


def test_export_get_markdown(db):
    create_label(
        name="Overclaiming",
        definition="too strong",
    )
    client = TestClient(create_app())
    response = client.get("/api/labels/export", params={"format": "md"})
    assert response.status_code == 200
    assert "Overclaiming" in response.text


def test_export_get_selected_ids_only(db):
    parent = create_label(name="Parent", definition="p")
    child = create_label(name="Child", definition="c", parent_id=parent.id)
    client = TestClient(create_app())
    response = client.get("/api/labels/export", params=[("format", "md"), ("id", child.id)])
    assert response.status_code == 200
    assert "Child" in response.text
    assert "Parent" in response.text
    assert "## Parent" not in response.text


def test_export_unknown_format_is_400(db):
    client = TestClient(create_app())
    response = client.get("/api/labels/export", params={"format": "xlsx"})
    assert response.status_code == 400


def test_post_split_leaf_creates_children(db, monkeypatch):
    source = create_label(name="Overclaiming", definition="too strong")
    _add_comment("c1", "Too strong.", label_id=source.id)
    _add_comment("c2", "Hedge this.", label_id=source.id)
    monkeypatch.setenv("REVIEWDISTILL_LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "reviewdistill.llm.base.get_provider",
        lambda: MockLLMProvider(
            '{"labels":[{"name":"Evidence","definition":"a"},{"name":"Wording","definition":"b"}],'
            '"assignments":[{"comment_id":"c1","label_index":0},{"comment_id":"c2","label_index":1}]}'
        ),
    )
    client = TestClient(create_app())
    response = client.post(f"/api/labels/{source.id}/split")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "privacy_warning" in response.json()
    assert response.json()["labeled"] == 2
    assert response.json()["label_names"] == ["Evidence", "Wording"]
    listed = client.get("/api/labels").json()
    node = next(item for item in listed["forest"] if item["id"] == source.id)
    assert {child["name"] for child in node["children"]} == {"Evidence", "Wording"}
    assert all(child["count"] > 0 for child in node["children"])


def test_post_split_forest_creates_roots(db, monkeypatch):
    _add_comment("c1", "Too strong.")
    _add_comment("c2", "Hedge this.")
    monkeypatch.setenv("REVIEWDISTILL_LLM_PROVIDER", "mock")
    monkeypatch.setattr(
        "reviewdistill.llm.base.get_provider",
        lambda: MockLLMProvider(
            '{"labels":[{"name":"Evidence","definition":"a"},{"name":"Wording","definition":"b"}],'
            '"assignments":[{"comment_id":"c1","label_index":0},{"comment_id":"c2","label_index":1}]}'
        ),
    )
    client = TestClient(create_app())
    response = client.post("/api/labels/split")
    assert response.status_code == 200
    assert "privacy_warning" in response.json()
    assert response.json()["labeled"] == 2
    assert response.json()["label_names"] == ["Evidence", "Wording"]
    listed = client.get("/api/labels").json()
    assert {node["name"] for node in listed["forest"]} == {"Evidence", "Wording"}
    assert all(node["count"] > 0 for node in listed["forest"])
    inbox = client.get("/api/inbox").json()
    assert inbox["unlabeled_count"] == 0
    assert all(item["labeled"] is True for item in inbox["working_items"])


def test_post_split_forest_rejects_existing_taxonomy(db):
    create_label(name="Already", definition="x")
    client = TestClient(create_app())
    response = client.post("/api/labels/split")
    assert response.status_code == 400


def test_recycle_returns_new_id(db):
    create_label(name="Existing", definition="")
    _add_comment("c1", "too strong")
    _add_comment("c2", "hedge this")
    client = TestClient(create_app())
    response = client.post("/api/labels/recycle")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["id"]
    forest = client.get("/api/labels").json()["forest"]
    names = [row["name"] for row in forest]
    assert "ungrouped" in names
    assert body["id"] in {row["id"] for row in forest}


def test_recycle_400_when_forest_empty(db):
    _add_comment("c1", "too strong")
    _add_comment("c2", "hedge this")
    client = TestClient(create_app())
    response = client.post("/api/labels/recycle")
    assert response.status_code == 400
    assert "until a taxonomy exists" in response.json()["detail"]
