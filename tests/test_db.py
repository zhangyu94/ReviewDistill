from reviewdistill.db.models import ProofreadingComment, Project, WORKING_COMMENT_STATUSES
from reviewdistill.db.session import get_session, init_db


def test_init_db_creates_and_round_trips_project(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        session.commit()

    with get_session() as session:
        project = session.get(Project, "p1")
        assert project is not None
        assert project.name == "paper-01"


def test_comment_raw_text_persists(rd_home):
    init_db()
    with get_session() as session:
        session.add(Project(id="p1", name="paper-01", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=10,
                raw_text='I think "demonstrate" is too strong.',
                context_text="The results demonstrate that...",
                section="4.2 Results",
                git_commit="abc123",
                fingerprint="deadbeef",
                status="active",
            )
        )
        session.commit()

    with get_session() as session:
        comment = session.get(ProofreadingComment, "c1")
        assert comment.raw_text == 'I think "demonstrate" is too strong.'
        assert comment.status == "active"


def test_init_db_migrates_legacy_comment_statuses(db):
    with get_session() as session:
        session.add(
            ProofreadingComment(
                id="old-del",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="gone",
                fingerprint="a",
                status="deleted",
            )
        )
        session.add(
            ProofreadingComment(
                id="old-mod",
                project_id="p",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=2,
                raw_text="old wording",
                fingerprint="b",
                status="modified",
            )
        )
        session.commit()
    init_db()
    with get_session() as session:
        deleted = session.get(ProofreadingComment, "old-del")
        modified = session.get(ProofreadingComment, "old-mod")
        assert deleted.status == "pending_disappeared"
        assert modified.status == "superseded"
        assert deleted.status not in WORKING_COMMENT_STATUSES
        assert modified.status not in WORKING_COMMENT_STATUSES


def test_sqlite_enables_wal(db):
    from reviewdistill.db.session import get_engine

    with get_engine().connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
    assert str(mode).lower() == "wal"
