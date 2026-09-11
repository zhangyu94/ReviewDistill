from __future__ import annotations

import typer

from reviewdistill.coding.clustering import cluster_texts
from reviewdistill.db.models import WORKING_COMMENT_STATUSES, ProofreadingComment
from reviewdistill.db.session import get_session, init_db


def run_cluster() -> None:
    init_db()
    with get_session() as session:
        comments = session.find(
            ProofreadingComment, status=WORKING_COMMENT_STATUSES, order_by="created_at"
        )
    clusters = cluster_texts(comments)
    if not clusters:
        typer.echo("No recurring clusters found.")
        return
    for index, group in enumerate(clusters, start=1):
        typer.echo(f"Cluster {index} ({len(group)} comments)")
        for comment in group:
            typer.echo(f"  - {comment.raw_text}")
