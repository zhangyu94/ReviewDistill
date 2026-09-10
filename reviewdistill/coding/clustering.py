from __future__ import annotations

from reviewdistill.coding.retrieval import _overlap, _tokens
from reviewdistill.db.models import ProofreadingComment


def cluster_texts(
    comments: list[ProofreadingComment], min_size: int = 2
) -> list[list[ProofreadingComment]]:
    remaining = list(comments)
    clusters: list[list[ProofreadingComment]] = []
    while remaining:
        seed = remaining.pop(0)
        seed_tokens = _tokens(seed.raw_text)
        group = [seed]
        kept: list[ProofreadingComment] = []
        for other in remaining:
            if _overlap(seed_tokens, _tokens(other.raw_text)) >= 0.1:
                group.append(other)
            else:
                kept.append(other)
        remaining = kept
        if len(group) >= min_size:
            clusters.append(group)
    return clusters
