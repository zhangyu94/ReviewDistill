from reviewdistill.coding.clustering import cluster_texts
from reviewdistill.db.models import ProofreadingComment


def test_cluster_groups_similar_comments():
    comments = [
        ProofreadingComment(
            id="1",
            project_id="p",
            source_type="latex_command",
            source_command="myremark",
            file_path="a.tex",
            line_number=1,
            raw_text="demonstrate is too strong here",
            fingerprint="1",
            status="active",
        ),
        ProofreadingComment(
            id="2",
            project_id="p",
            source_type="latex_command",
            source_command="myremark",
            file_path="b.tex",
            line_number=1,
            raw_text="the verb demonstrate overclaims the result",
            fingerprint="2",
            status="active",
        ),
        ProofreadingComment(
            id="3",
            project_id="p",
            source_type="latex_command",
            source_command="myremark",
            file_path="c.tex",
            line_number=1,
            raw_text="please define the acronym RNN on first use",
            fingerprint="3",
            status="active",
        ),
    ]
    clusters = cluster_texts(comments, min_size=2)
    assert len(clusters) == 1
    ids = {comment.id for comment in clusters[0]}
    assert ids == {"1", "2"}
