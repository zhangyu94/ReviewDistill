"""Batch runner for the skill-spotting experiment.

``--source store`` (default) reads gold from the local ReviewDistill store.
``--source fixture`` uses ``fixtures/`` only and must not open the store.
See README.md in this folder.

Not a product CLI. Live calls spend tokens and send passages off-box.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib import (
    BASELINE_CONDITION,
    SKILL_CONDITION,
    EvalItem,
    FixtureError,
    GoldComment,
    aggregate_condition,
    append_cache,
    cache_key,
    distractor_item,
    gold_item,
    load_cache,
    load_fixture_pack,
    load_gold,
    load_types,
    parse_types_result,
    prompt_for,
    resolve_folds,
    sample_distractors,
    skill_markdown,
    skill_markdown_from_labels,
    unused_paragraphs,
)

from reviewdistill.db.models import Project, ProofreadingComment, in_working_set
from reviewdistill.db.session import get_session, init_db
from reviewdistill.llm.base import get_provider, privacy_warning


def _runs_dir() -> Path:
    return ROOT / "runs"


def _occupied_and_commands(project_id: str) -> tuple[dict[str, set[int]], set[str]]:
    """Lines already covered by working-set comments, plus proofreading command names.

    Used to keep distractor paragraphs away from labeled spots and to strip
    leftover ``\\command{...}`` markup from sampled blocks.
    """
    occupied: dict[str, set[int]] = defaultdict(set)
    commands: set[str] = set()
    init_db()
    with get_session() as session:
        for comment in session.find(ProofreadingComment, project_id=project_id):
            if not in_working_set(comment):
                continue
            occupied[comment.file_path].add(comment.line_number)
            if comment.source_command:
                commands.add(comment.source_command)
    return occupied, commands


def _project_root(project_id: str) -> Path | None:
    """Checkout path for unused-paragraph sampling. None if the .tex tree is gone."""
    init_db()
    with get_session() as session:
        row = session.get(Project, project_id)
    if row is None or not row.root_path:
        return None
    path = Path(row.root_path)
    return path if path.is_dir() else None


def build_items(
    gold: list[GoldComment],
    folds,
    rng,
    *,
    root_of,
    occupied_of,
) -> tuple[list[EvalItem], dict]:
    """Gold passages for each fold, plus about one unused paragraph per gold item.

    ``root_of(project_id)`` returns a Path or None.
    ``occupied_of(project_id)`` returns ``(occupied_lines_by_relpath, command_names)``.
    Distractors are skipped when the root is missing or every paragraph is occupied.
    """
    by_id = {item.comment_id: item for item in gold}
    items: list[EvalItem] = []
    meta_folds = []
    for fold in folds:
        gold_rows = [by_id[cid] for cid in fold.test_comment_ids if cid in by_id]
        for row in gold_rows:
            items.append(gold_item(fold, row))
        distractor_n = 0
        skipped = None
        for project_id in sorted(fold.test_project_ids):
            n_gold = sum(1 for row in gold_rows if row.project_id == project_id)
            root = root_of(project_id)
            if root is None:
                skipped = skipped or "missing-tex-root"
                continue
            occupied, commands = occupied_of(project_id)
            candidates = unused_paragraphs(
                root=root, occupied=occupied, commands=commands
            )
            picked = sample_distractors(candidates, n_gold, rng)
            if not picked and n_gold:
                skipped = skipped or "no-unused-paragraphs"
            for index, passage in enumerate(picked):
                items.append(distractor_item(fold, project_id, index, passage))
            distractor_n += len(picked)
        meta_folds.append(
            {
                "id": fold.id,
                "n_gold": len(gold_rows),
                "n_distractors": distractor_n,
                "distractor_skip": skipped,
            }
        )
    return items, {"folds": meta_folds}


def metrics_payload(items: list[EvalItem], predictions: list[dict], types) -> dict:
    """Headline exact + hierarchical + per-type scores, one block per condition."""
    by_item = {item.id: item for item in items}
    out = {}
    for condition in (BASELINE_CONDITION, SKILL_CONDITION):
        pairs = []
        for row in predictions:
            if row["condition"] != condition:
                continue
            item = by_item[row["item_id"]]
            pairs.append((set(item.gold_names), set(row["predicted"])))
        rolled = aggregate_condition(pairs, types)
        out[condition] = {
            "exact": rolled.exact,
            "hierarchical_recall": rolled.hierarchical_recall,
            "per_type": rolled.per_type,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Score current exported SKILL.md vs a names-only baseline on held-out "
            "passages. Developer experiment; not reviewdistill eval."
        )
    )
    parser.add_argument(
        "--holdout",
        choices=("auto", "paper", "comment"),
        default="auto",
        help=(
            "How to hold out gold so test-comment examples never enter SKILL.md. "
            "auto: leave-one-paper-out if two labeled projects exist, else leave-one-comment-out"
        ),
    )
    parser.add_argument(
        "--comment-fraction",
        type=float,
        default=None,
        help="With comment holdout, test this random fraction instead of true leave-one-out",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None, help="Run directory (default: runs/<utc>)")
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Existing run directory; reuse its cache.jsonl and write into it",
    )
    parser.add_argument(
        "--source",
        choices=("store", "fixture"),
        default="store",
        help="store: live working-set gold. fixture: experiments/skill-eval/fixtures/",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=None,
        help="Fixture pack directory (default: experiments/skill-eval/fixtures)",
    )
    args = parser.parse_args(argv)

    fixture_dir = args.fixture_dir or (ROOT / "fixtures")
    pack = None
    if args.source == "fixture":
        try:
            pack = load_fixture_pack(fixture_dir)
        except FixtureError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        gold = pack.gold
        types = pack.types

        def root_of(project_id: str):
            return pack.roots.get(project_id)

        def occupied_of(project_id: str):
            # Gold is gold.jsonl, not TeX macros; nothing to strip from distractors.
            return pack.occupied.get(project_id, {}), set()

    else:
        gold = load_gold()
        types = load_types()
        root_of = _project_root
        occupied_of = _occupied_and_commands

    if not gold:
        print("No gold comments (working-set + accepted active type).", file=sys.stderr)
        return 1
    try:
        provider = get_provider()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    mode, folds = resolve_folds(
        gold,
        holdout=args.holdout,
        comment_fraction=args.comment_fraction,
        rng=rng,
    )
    if args.comment_fraction is not None and mode != "comment":
        print("--comment-fraction requires comment holdout (pass --holdout comment).", file=sys.stderr)
        return 1

    items, fold_meta = build_items(gold, folds, rng, root_of=root_of, occupied_of=occupied_of)

    def holdout_passages(fold) -> set[str]:
        ids = set(fold.test_comment_ids)
        return {item.passage for item in gold if item.comment_id in ids and item.passage}

    if args.source == "fixture":
        skills = {
            fold.id: skill_markdown_from_labels(
                pack.labels,
                set(fold.test_comment_ids),
                holdout_passages=holdout_passages(fold),
            )
            for fold in folds
        }
    else:
        skills = {
            fold.id: skill_markdown(
                set(fold.test_comment_ids),
                holdout_passages=holdout_passages(fold),
            )
            for fold in folds
        }

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.resume or args.out or (_runs_dir() / stamp)
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / "cache.jsonl"
    cache = load_cache(cache_path)

    warning = privacy_warning(provider_name=provider.name, comment_count=len(items))
    print(warning, file=sys.stderr)

    predictions: list[dict] = []
    for item in items:
        for condition in (BASELINE_CONDITION, SKILL_CONDITION):
            skill_md = skills[item.fold]
            prompt = prompt_for(condition, skill_md, item.passage)
            key = cache_key(condition, item.id, prompt)
            hit = key in cache
            if hit:
                raw = cache[key]
            else:
                raw = provider.generate(prompt)
                cache[key] = raw
                append_cache(cache_path, key, prompt, raw)
            names, parse_error = parse_types_result(raw)
            predicted = sorted(names)
            predictions.append(
                {
                    "item_id": item.id,
                    "condition": condition,
                    "predicted": predicted,
                    "parse_error": parse_error,
                    "raw": raw,
                    "cache_hit": hit,
                }
            )

    metrics = metrics_payload(items, predictions, types)
    meta = {
        "source": args.source,
        "holdout": mode,
        "comment_fraction": args.comment_fraction,
        "seed": args.seed,
        "provider": provider.name,
        "model": getattr(provider, "model", None),
        "n_gold_comments": len(gold),
        "n_items": len(items),
        "privacy_warning": warning,
        **fold_meta,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    with (out / "items.jsonl").open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(
                json.dumps(
                    {
                        "id": item.id,
                        "fold": item.fold,
                        "project_id": item.project_id,
                        "comment_id": item.comment_id,
                        "passage": item.passage,
                        "gold_names": item.gold_names,
                        "is_distractor": item.is_distractor,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    with (out / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Wrote {out}")
    print(json.dumps({k: v["exact"] for k, v in metrics.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
