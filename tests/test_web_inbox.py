import json

import pytest
from fastapi.testclient import TestClient
from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import code_uncoded_comments
from reviewdistill.coding.validation import accept_coding, inbox_items
from reviewdistill.config import HomeConfig, write_home_config
from reviewdistill.db.models import Coding, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import create_issue_type
from reviewdistill.web.app import create_app


def _seed(tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{This seems too strong given the experiment.}\n")
    extract_project(repo)
    issue = create_issue_type(
        name="Overclaiming",
        definition="too strong",
    )
    code_uncoded_comments(
        provider=MockLLMProvider(
            scripted_response=json.dumps(
                {
                    "recommendation": "existing",
                    "issue_type_id": issue.id,
                    "confidence": 0.91,
                    "rationale": "Objects to claim strength.",
                }
            )
        )
    )
    return issue


def _count_store_loads(monkeypatch):
    from reviewdistill.db.session import StoreSession

    counts = {"n": 0}
    original = StoreSession._load

    def wrapped(self):
        counts["n"] += 1
        return original(self)

    monkeypatch.setattr(StoreSession, "_load", wrapped)
    return counts


def test_inbox_lists_proposed_comments(db, tmp_path):
    _seed(tmp_path)
    item = inbox_items()[0]
    comment = item.comment
    client = TestClient(create_app())
    response = client.get("/api/inbox")
    assert response.status_code == 200
    body = response.json()
    assert body["unlabeled_count"] == 1
    progress = body["progress"]
    assert progress["working_set"] == 1
    assert progress["unlabeled"] == 1
    assert progress["labeled"] == 0
    assert progress["unreviewed"] == 1
    assert progress["verified"] == 0
    assert progress["dropped"] == 0
    assert "absent" not in progress
    assert progress["unlabeled"] + progress["labeled"] == progress["working_set"]
    assert body["items"][0]["comment"]["id"] == comment.id
    assert body["items"][0]["comment"]["raw_text"] == comment.raw_text
    assert body["items"][0]["comment"]["file_path"] == comment.file_path
    assert body["items"][0]["comment"]["line_number"] == comment.line_number
    assert body["items"][0]["comment"]["source_command"] == comment.source_command
    assert body["items"][0]["comment"]["source_type"] == comment.source_type
    assert body["items"][0]["comment"]["status"] == comment.status
    assert body["items"][0]["comment"]["quality"] == "unreviewed"
    assert body["items"][0]["in_manuscript"] is True
    assert body["items"][0]["comment"]["fingerprint"] == comment.fingerprint
    assert body["items"][0]["project_name"] == "paper-01"
    assert body["items"][0]["guess"] is None
    assert body["items"][0]["coding"]["kind"] == "existing"
    assert body["items"][0]["coding"]["confidence"] == 0.91
    assert body["items"][0]["labeled"] is False
    assert body["items"][0]["issue"] is None
    assert "working_items" in body
    assert body["items"][0]["in_working_set"] is True
    working_ids = {row["comment"]["id"] for row in body["working_items"]}
    assert comment.id in working_ids
    assert any(row["name"] == "Overclaiming" for row in body["issues"])
    assert "view" not in body


def test_inbox_working_items_include_labeled_working_set(db, tmp_path):
    issue = _seed(tmp_path)
    comment_id = inbox_items()[0].comment.id
    accept_coding(comment_id)
    client = TestClient(create_app())
    body = client.get("/api/inbox").json()
    assert body["unlabeled_count"] == 0
    assert body["items"] == []
    assert {row["comment"]["id"] for row in body["working_items"]} == {comment_id}
    row = body["working_items"][0]
    assert row["labeled"] is True
    assert row["in_working_set"] is True
    assert row["issue"]["id"] == issue.id


def test_accept_post_leaves_inbox(db, tmp_path):
    _seed(tmp_path)
    item = inbox_items()[0]
    client = TestClient(create_app())
    response = client.post(f"/api/inbox/{item.comment.id}/accept")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    body = client.get("/api/inbox").json()
    assert body["unlabeled_count"] == 0


def test_inbox_treats_label_on_inactive_type_as_unlabeled(db, tmp_path):
    from reviewdistill.db.models import ISSUE_INACTIVE, IssueType

    issue = _seed(tmp_path)
    comment_id = inbox_items()[0].comment.id
    accept_coding(comment_id)
    client = TestClient(create_app())
    assert client.get("/api/inbox").json()["unlabeled_count"] == 0
    with get_session() as session:
        row = session.get(IssueType, issue.id)
        row.status = ISSUE_INACTIVE
        session.add(row)
        session.commit()
    body = client.get("/api/inbox").json()
    assert body["unlabeled_count"] == 1
    assert body["pending_code_count"] == 1
    assert body["items"][0]["comment"]["id"] == comment_id
    assert body["items"][0]["labeled"] is False
    assert body["items"][0]["issue"] is None
    progress = body["progress"]
    assert progress["working_set"] == 1
    assert progress["unlabeled"] == 1
    assert progress["labeled"] == 0


def test_inbox_json_marks_labeled_absent_unreviewed(db, tmp_path):
    issue = _seed(tmp_path)
    comment_id = inbox_items()[0].comment.id
    accept_coding(comment_id)
    (tmp_path / "paper" / "main.tex").write_text("no comments\n")
    extract_project(tmp_path / "paper")
    client = TestClient(create_app())
    body = client.get("/api/inbox").json()
    assert body["unlabeled_count"] == 1
    progress = body["progress"]
    assert progress["unlabeled"] == 0
    assert body["unlabeled_count"] != progress["unlabeled"]
    assert "absent" not in progress
    assert progress["working_set"] == 0
    item = body["items"][0]
    assert item["comment"]["id"] == comment_id
    assert item["comment"]["status"] == "pending_disappeared"
    assert item["comment"]["quality"] == "unreviewed"
    assert item["in_manuscript"] is False
    assert item["labeled"] is True
    assert item["issue"]["id"] == issue.id
    assert item["issue"]["name"] == "Overclaiming"
    assert item["issue"]["name"] == "Overclaiming"


def test_absent_comment_verify_post(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Gone soon.}\n")
    extract_project(repo)
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    item = inbox_items()[0]
    client = TestClient(create_app())
    response = client.get("/api/inbox")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["comment"]["raw_text"] == "Gone soon."
    assert body["items"][0]["in_manuscript"] is False
    assert body["items"][0]["guess"]
    assert body["items"][0]["coding"] is None
    verified = client.post(f"/api/inbox/{item.comment.id}/verify")
    assert verified.status_code == 200
    with get_session() as session:
        assert session.get(ProofreadingComment, item.comment.id).quality == "verified"
    unlabeled = client.get("/api/inbox").json()
    assert unlabeled["unlabeled_count"] == 1


def test_inbox_rejects_unknown_quality(db, tmp_path, rd_home):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Too strong.}\n")
    extract_project(repo)
    with get_session() as session:
        comment_id = session.first(ProofreadingComment).id
    issue = create_issue_type(
        name="Overclaiming",
        definition="too strong",
    )
    path = rd_home / "comments.jsonl"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"unreviewed"', '"kept"', 1), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown comment quality"):
        inbox_items()
    client = TestClient(create_app(), raise_server_exceptions=False)
    requests = [
        ("GET", "/api/inbox"),
        ("GET", "/api/taxonomy"),
        ("GET", f"/api/taxonomy/{issue.id}"),
        ("GET", "/api/taxonomy/export"),
        ("GET", "/api/history"),
        ("POST", f"/api/inbox/{comment_id}/verify"),
    ]
    for method, url in requests:
        response = client.request(method, url)
        assert response.status_code == 500, url
        assert "Unknown comment quality" in response.json()["detail"]


def test_verify_unknown_comment_is_404(db):
    client = TestClient(create_app())
    response = client.post("/api/inbox/missing/verify")
    assert response.status_code == 404
    assert "Unknown comment" in response.json()["detail"]


def test_drop_post_excludes_from_unlabeled(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Pull this.}\n")
    extract_project(repo)
    (repo / "main.tex").write_text("no comments\n")
    extract_project(repo)
    item = inbox_items()[0]
    client = TestClient(create_app())
    client.post(f"/api/inbox/{item.comment.id}/drop")
    unlabeled = client.get("/api/inbox").json()
    assert unlabeled["unlabeled_count"] == 0


def test_inbox_unknown_llm_provider_is_null_not_500(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Needs a real suggestion.}\n")
    extract_project(repo)
    write_home_config(HomeConfig(llm_provider="nope"))
    client = TestClient(create_app())
    response = client.get("/api/inbox")
    assert response.status_code == 200
    body = response.json()
    assert body["llm_provider"] is None
    assert body["unlabeled_count"] == 1


def test_inbox_hides_mock_proposal_and_counts_it_as_pending(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Needs a real suggestion.}\n")
    extract_project(repo)
    comment_id = inbox_items()[0].comment.id
    with get_session() as session:
        session.add(
            Coding(
                id="mock-proposed",
                comment_id=comment_id,
                coder_type="ai",
                status="proposed",
                proposed_issue_name="Mock issue",
                rationale="Mock provider used in tests.",
                confidence=0.5,
            )
        )
        session.commit()
    client = TestClient(create_app())
    body = client.get("/api/inbox").json()
    assert body["items"][0]["coding"] is None
    assert body["pending_code_count"] == 1
    assert body["llm_provider"] is None


def test_post_inbox_code_without_provider_is_400(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Needs a provider.}\n")
    extract_project(repo)
    client = TestClient(create_app())
    response = client.post("/api/inbox/code")
    assert response.status_code == 400
    assert "LLM" in response.json()["detail"]


def test_post_inbox_code_proposes_all_uncoded(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text(
        "\\myremark{This seems too strong given the experiment.}\n"
        "\\myremark{Why this method?}\n"
    )
    extract_project(repo)
    write_home_config(HomeConfig(llm_provider="mock"))
    client = TestClient(create_app())
    listed = client.get("/api/inbox").json()
    assert listed["pending_code_count"] == 2
    assert listed["llm_provider"] == "mock"
    assert "privacy_warning" not in listed
    assert all(item["coding"] is None for item in listed["items"])
    response = client.post("/api/inbox/code")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["coded"] == 2
    assert body["failed"] == 0
    after = client.get("/api/inbox").json()
    assert after["pending_code_count"] == 0
    assert after["unlabeled_count"] == 2
    assert all(item["coding"] is not None for item in after["items"])
    again = client.post("/api/inbox/code")
    assert again.json()["coded"] == 0


def test_post_inbox_code_http_error_is_400(db, tmp_path, monkeypatch):
    import httpx

    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Needs coding.}\n")
    extract_project(repo)

    class _Down:
        name = "openai"

        def generate(self, prompt: str) -> str:
            raise httpx.HTTPStatusError(
                "bad",
                request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
                response=httpx.Response(503, request=httpx.Request("POST", "https://example.com")),
            )

    monkeypatch.setattr("reviewdistill.coding.coder.get_provider", lambda: _Down())
    client = TestClient(create_app())
    response = client.post("/api/inbox/code")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail == "LLM request failed"
    assert "openai.com" not in detail
    assert "sk-" not in detail


def test_inbox_json_strips_credentials_from_stored_git_url(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Too strong.}\n")
    extract_project(repo)
    with get_session() as session:
        row = session.first(ProofreadingComment)
        row.git_url = "https://user:ghp_secret@github.com/example/paper.git"
        session.add(row)
        session.commit()
    client = TestClient(create_app())
    body = client.get("/api/inbox").json()
    git_url = body["items"][0]["comment"]["git_url"]
    assert git_url == "https://github.com/example/paper.git"
    assert "ghp_secret" not in git_url


def test_get_inbox_loads_store_once(db, tmp_path, monkeypatch):
    _seed(tmp_path)
    loads = _count_store_loads(monkeypatch)
    client = TestClient(create_app())
    response = client.get("/api/inbox")
    assert response.status_code == 200
    assert loads["n"] == 1
