import json

import httpx
import pytest
from reviewdistill.cli.init import init_project
from reviewdistill.coding.coder import build_prompt, code_uncoded_comments, parse_model_output
from reviewdistill.db.models import Coding, ProofreadingComment
from reviewdistill.db.session import get_session
from reviewdistill.extraction.incremental import extract_project
from reviewdistill.llm.mock import MockLLMProvider
from reviewdistill.taxonomy.operations import add_example, create_issue_type


def test_parse_existing_and_new_recommendations():
    existing = parse_model_output(
        json.dumps(
            {
                "recommendation": "existing",
                "issue_type_id": "iss-1",
                "confidence": 0.91,
                "rationale": "Objects to demonstrate.",
                "suggested_evidence": "demonstrate → suggest",
            }
        )
    )
    assert existing.recommendation == "existing"
    assert existing.issue_type_id == "iss-1"
    assert existing.confidence == 0.91

    new = parse_model_output(
        json.dumps(
            {
                "recommendation": "new",
                "issue_code": "METHJUST",
                "issue_name": "Missing methodological justification",
                "category": "Methodology",
                "definition": "A design decision is unexplained.",
                "confidence": 0.78,
                "rationale": "Asks why the design was necessary.",
            }
        )
    )
    assert new.recommendation == "new"
    assert new.issue_name.startswith("Missing")


def test_parse_model_output_reads_first_json_object():
    proposal = parse_model_output(
        '{"recommendation":"new","issue_name":"X"} leftover {not json}'
    )
    assert proposal.recommendation == "new"
    assert proposal.issue_name == "X"


def test_build_prompt_separates_observation_from_interpretation():
    issue = type(
        "I",
        (),
        {
            "id": "iss-1",
            "code": "OVERCLAIM",
            "name": "Overclaiming",
            "category": "Argumentation",
            "definition": "too strong",
        },
    )()
    prompt = build_prompt(
        raw_text='I think "demonstrate" is too strong.',
        context_text="The experiment only shows a correlation.",
        section="Results",
        candidates=[issue],
    )
    assert "Reviewer observation:" in prompt
    assert "do not modify the taxonomy" in prompt.lower()
    assert "Overclaiming" in prompt
    assert "demonstrate" in prompt


def test_code_uncoded_comments_writes_proposed_coding(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text('\\myremark{I think "demonstrate" is too strong here.}\n')
    extract_project(repo)
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="A claim is stronger than the evidence supports.",
    )
    provider = MockLLMProvider(
        scripted_response=json.dumps(
            {
                "recommendation": "existing",
                "issue_type_id": issue.id,
                "confidence": 0.91,
                "rationale": "The reviewer objects to demonstrate.",
                "suggested_evidence": "demonstrate → suggest",
            }
        )
    )
    summary = code_uncoded_comments(provider=provider)
    assert summary.coded == 1
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        coding = session.first(Coding)
        assert comment.raw_text.startswith("I think")
        assert coding.comment_id == comment.id
        assert coding.coder_type == "ai"
        assert coding.status == "proposed"
        assert coding.issue_type_id == issue.id
        assert coding.confidence == 0.91


def test_code_skips_already_resolved_comments(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Too strong.}\n")
    extract_project(repo)
    provider = MockLLMProvider()
    first = code_uncoded_comments(provider=provider)
    second = code_uncoded_comments(provider=provider)
    assert first.coded == 1
    assert second.coded == 0


def test_code_replaces_placeholder_mock_proposal(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Needs a real suggestion.}\n")
    extract_project(repo)
    comment_id = None
    with get_session() as session:
        comment = session.first(ProofreadingComment)
        comment_id = comment.id
        session.add(
            Coding(
                id="mock-proposed",
                comment_id=comment.id,
                coder_type="ai",
                status="proposed",
                proposed_issue_name="Mock issue",
                rationale="Mock provider used in tests.",
                confidence=0.5,
            )
        )
        session.commit()

    class _Stub:
        name = "openai"

        def generate(self, prompt: str) -> str:
            return json.dumps(
                {
                    "recommendation": "new",
                    "issue_name": "Unclear thesis",
                    "issue_code": "UNCLEAR",
                    "category": "Writing",
                    "definition": "The paragraph thesis is not clear.",
                    "confidence": 0.8,
                    "rationale": "The reviewer asks for a clearer thesis.",
                }
            )

    summary = code_uncoded_comments(provider=_Stub())
    assert summary.coded == 1
    with get_session() as session:
        rows = session.find(Coding, comment_id=comment_id)
        assert session.get(Coding, "mock-proposed") is None
        assert len(rows) == 1
        assert rows[0].proposed_issue_name == "Unclear thesis"


def test_unknown_issue_type_id_does_not_fall_back_to_top_candidate(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text('\\myremark{I think "demonstrate" is too strong here.}\n')
    extract_project(repo)
    issue = create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="A claim is stronger than the evidence supports.",
    )
    add_example(issue.id, text='I think "demonstrate" is too strong here.')
    provider = MockLLMProvider(
        scripted_response=json.dumps(
            {
                "recommendation": "existing",
                "issue_type_id": "not-a-real-issue",
                "issue_name": "Overclaiming (proposed)",
                "issue_code": "OVERCLAIM2",
                "category": "Argumentation",
                "definition": "A claim exceeds the evidence.",
                "confidence": 0.91,
                "rationale": "Hallucinated id.",
            }
        )
    )
    code_uncoded_comments(provider=provider)
    with get_session() as session:
        coding = session.first(Coding)
        assert coding.issue_type_id is None
        assert coding.proposed_issue_name == "Overclaiming (proposed)"
        assert coding.issue_type_id != issue.id


def test_code_continues_after_one_unparseable_response(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{First comment.}\n\\myremark{Second comment.}\n")
    extract_project(repo)
    responses = iter(["not json", json.dumps({"recommendation": "new", "issue_name": "Second"})])

    class _Stub:
        name = "openai"

        def generate(self, prompt: str) -> str:
            return next(responses)

    summary = code_uncoded_comments(provider=_Stub())
    assert summary.coded == 1
    assert summary.skipped >= 1
    with get_session() as session:
        names = {row.proposed_issue_name for row in session.find(Coding)}
        assert "Second" in names


def test_code_uncoded_comments_ranks_all_comments_without_reloading_store(db, tmp_path, monkeypatch):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{First comment.}\n\\myremark{Second comment.}\n")
    extract_project(repo)
    create_issue_type(
        code="OVERCLAIM",
        name="Overclaiming",
        category="Argumentation",
        definition="A claim is stronger than the evidence supports.",
    )
    from reviewdistill.coding import coder as coder_mod
    from reviewdistill.coding.retrieval import retrieve_candidates
    from reviewdistill.db.session import StoreSession

    loads = {"n": 0}
    original_load = StoreSession._load
    original_retrieve = retrieve_candidates
    retrieve_loads: list[int] = []

    def counting_load(self):
        loads["n"] += 1
        return original_load(self)

    def counting_retrieve(comment, limit=5):
        before = loads["n"]
        result = original_retrieve(comment, limit=limit)
        retrieve_loads.append(loads["n"] - before)
        return result

    monkeypatch.setattr(StoreSession, "_load", counting_load)
    monkeypatch.setattr(coder_mod, "retrieve_candidates", counting_retrieve)
    summary = code_uncoded_comments(provider=MockLLMProvider())
    assert summary.coded == 2
    assert retrieve_loads
    assert retrieve_loads[0] <= 1
    assert retrieve_loads[1:] == [0] * (len(retrieve_loads) - 1)


def test_code_aborts_provider_http_error(db, tmp_path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{Needs a provider.}\n")
    extract_project(repo)

    class _Down:
        name = "openai"

        def generate(self, prompt: str) -> str:
            raise httpx.HTTPStatusError(
                "bad",
                request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
                response=httpx.Response(503, request=httpx.Request("POST", "https://example.com")),
            )

    with pytest.raises(httpx.HTTPError):
        code_uncoded_comments(provider=_Down())
