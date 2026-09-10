from pathlib import Path

from sqlmodel import select
from watchfiles import Change

from reviewdistill.cli.extract import run_extract
from reviewdistill.cli.init import init_project
from reviewdistill.db.models import ProofreadingComment
from reviewdistill.db.session import get_session


def test_run_extract_watch_extracts_on_tex_event(db, tmp_path: Path):
    repo = tmp_path / "paper"
    repo.mkdir()
    init_project(name="paper-01", commands=["myremark"], cwd=repo)
    (repo / "main.tex").write_text("\\myremark{From watch.}\n")

    def fake_watch(*args, **kwargs):
        yield {(Change.modified, str(repo / "main.tex"))}
        raise KeyboardInterrupt()

    run_extract(cwd=repo, watch=True, watcher=fake_watch)
    with get_session() as session:
        rows = list(session.exec(select(ProofreadingComment)))
        assert len(rows) == 1
        assert rows[0].raw_text == "From watch."
