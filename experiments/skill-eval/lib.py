"""Helpers for the skill-spotting experiment (see README.md in this folder).

The product exports SKILL.md but never tests whether an agent can use it to
name the author's labels. This module builds held-out eval items from the
local store, renders a skill that excludes test comments, and scores exact
type-name match vs a names-only baseline.

Nothing here is a CLI command or a pytest module.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

from reviewdistill.context.manuscript import _blocks, _is_structural_line
from reviewdistill.db.models import (
    ASSIGNMENT_ACCEPTED,
    LABEL_ACTIVE,
    Assignment,
    Label,
    ProofreadingComment,
    in_working_set,
)
from reviewdistill.db.session import get_session, init_db
from reviewdistill.taxonomy.export import _to_markdown
from reviewdistill.taxonomy.operations import (
    list_active_labels,
    list_examples,
)

# Condition ids written into predictions.jsonl / metrics.json.
SKILL_CONDITION = "skill"
BASELINE_CONDITION = "baseline"

# Eval protocol key is types (not product JSON). Values are label names.
JSON_INSTRUCTION = (
    'Return JSON {"types": ["..."]} using label names, or {"types": []} if none apply. '
    "No other keys."
)


def parse_types(text: str) -> set[str]:
    """Last JSON object in the reply with a ``types`` list of strings.

    Parse failure or no such object is predicted empty, same as a model that
    refuses to name anything. Use ``parse_types_result`` when the caller needs
    to distinguish a parse miss from ``{"types": []}``.
    """
    names, _parse_error = parse_types_result(text)
    return names


def parse_types_result(text: str) -> tuple[set[str], bool]:
    """``(names, parse_error)``. Last object with a ``types`` list wins."""
    decoder = json.JSONDecoder()
    last: set[str] | None = None
    idx = 0
    while True:
        start = text.find("{", idx)
        if start < 0:
            break
        try:
            data, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            idx = start + 1
            continue
        idx = start + max(end, 1)
        if not isinstance(data, dict):
            continue
        raw = data.get("types")
        if not isinstance(raw, list):
            continue
        names: set[str] = set()
        for item in raw:
            if isinstance(item, str) and item.strip():
                names.add(item.strip())
        last = names
    if last is None:
        return set(), True
    return last, False


def exact_counts(gold: set[str], predicted: set[str]) -> tuple[int, int, int]:
    """Set overlap on type *names*. Extra predicted names are FPs; misses are FNs."""
    tp = len(gold & predicted)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    return tp, fp, fn


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    """Micro P/R/F1. Undefined ratios become 0.0 (a real score, not missing data)."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    if precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


@dataclass(frozen=True)
class TypeRef:
    """Active taxonomy row. Scoring matches on ``name``, hierarchy walks ``parent_id``."""

    id: str
    name: str
    parent_id: str | None


def ancestor_names(types: list[TypeRef], type_id: str) -> set[str]:
    """Parent / grandparent names of ``type_id`` (not including itself)."""
    by_id = {row.id: row for row in types}
    names: set[str] = set()
    current = by_id.get(type_id)
    if current is None:
        return names
    parent_id = current.parent_id
    seen: set[str] = set()
    while parent_id and parent_id not in seen:
        seen.add(parent_id)
        parent = by_id.get(parent_id)
        if parent is None:
            break
        names.add(parent.name)
        parent_id = parent.parent_id
    return names


def name_to_id(types: list[TypeRef]) -> dict[str, str]:
    """Map displayed type name → id (for walking ancestors during hierarchical scoring)."""
    return {row.name: row.id for row in types}


def hierarchical_hits(gold: set[str], predicted: set[str], types: list[TypeRef]) -> set[str]:
    """Gold names counted as hit if predicted contains that name *or an ancestor*.

    Sibling / child / unrelated names do not count. Precision stays exact;
    this is only a secondary recall diagnostic.
    """
    ids = name_to_id(types)
    hits: set[str] = set()
    for name in gold:
        if name in predicted:
            hits.add(name)
            continue
        type_id = ids.get(name)
        if type_id is None:
            continue
        if ancestor_names(types, type_id) & predicted:
            hits.add(name)
    return hits


@dataclass
class ConditionMetrics:
    exact: dict[str, float]
    hierarchical_recall: float
    per_type: dict[str, dict]


def aggregate_condition(
    items: list[tuple[set[str], set[str]]],
    types: list[TypeRef],
) -> ConditionMetrics:
    """Roll gold/predicted pairs into headline exact P/R/F1 plus per-type confusion."""
    tp = fp = fn = 0
    gold_n = 0
    hier_n = 0
    per: dict[str, dict] = defaultdict(
        lambda: {
            "gold": 0,
            "exact": 0,
            "hierarchical_only": 0,
            "miss": 0,
            "wrong": Counter(),
        }
    )
    for gold, predicted in items:
        t, fpos, fneg = exact_counts(gold, predicted)
        tp += t
        fp += fpos
        fn += fneg
        hier = hierarchical_hits(gold, predicted, types)
        gold_n += len(gold)
        hier_n += len(hier)
        extras = predicted - gold
        for name in gold:
            row = per[name]
            row["gold"] += 1
            if name in predicted:
                row["exact"] += 1
            elif name in hier:
                row["hierarchical_only"] += 1
            else:
                row["miss"] += 1
            for extra in extras:
                row["wrong"][extra] += 1
    exact = prf(tp, fp, fn)
    hier_recall = hier_n / gold_n if gold_n else 0.0
    per_type = {}
    for name, row in per.items():
        per_type[name] = {
            "gold": row["gold"],
            "exact": row["exact"],
            "hierarchical_only": row["hierarchical_only"],
            "miss": row["miss"],
            "top_wrong": row["wrong"].most_common(5),
        }
    return ConditionMetrics(exact=exact, hierarchical_recall=hier_recall, per_type=per_type)


@dataclass(frozen=True)
class GoldComment:
    """One labeled comment. ``passage`` is stored context_text; never raw_text."""

    comment_id: str
    project_id: str
    passage: str
    gold_names: frozenset[str]
    file_path: str
    line_number: int
    source_command: str


@dataclass(frozen=True)
class Fold:
    """One holdout split. Skill markdown must drop examples whose source is in
    test_comment_ids, and examples whose text matches a held-out passage."""

    id: str
    test_comment_ids: frozenset[str]
    test_project_ids: frozenset[str]


class FixtureError(ValueError):
    """Bad fixture pack (missing file, bad line, unknown gold name)."""


def passage_at_line(path: Path, line_number: int) -> str:
    """Manuscript block containing 1-based ``line_number``. Fails if not a content block.

    Same unit distractors use (``_blocks``: blank lines split paragraphs).
    ``gold.jsonl`` stores the line, not the passage, so the ``.tex`` stays source of truth.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureError(f"Cannot read {path}: {exc}") from exc
    lines = text.splitlines()
    if line_number < 1 or line_number > len(lines):
        raise FixtureError(f"{path}: line {line_number} out of range")
    idx = line_number - 1
    for start, end in _blocks(lines):
        if start <= idx <= end:
            has_content = any(
                lines[i].strip() and not _is_structural_line(lines[i])
                for i in range(start, end + 1)
            )
            if not has_content:
                raise FixtureError(f"{path}:{line_number} is not a content block")
            return "\n".join(lines[start : end + 1]).strip()
    raise FixtureError(f"{path}:{line_number} is not inside a paragraph block")


def load_fixture_taxonomy(path: Path) -> list[dict]:
    """Load ``taxonomy.yaml``. Each label dict includes ``example_rows`` with optional ``source_item_id``."""
    if not path.is_file():
        raise FixtureError(f"Missing {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("labels"), list):
        raise FixtureError(f"{path}: expected a mapping with a labels list")
    by_id: dict[str, dict] = {}
    for raw in data["labels"]:
        if not isinstance(raw, dict):
            raise FixtureError(f"{path}: each label must be a mapping")
        label_id = raw.get("id")
        name = raw.get("name")
        definition = raw.get("definition")
        if not isinstance(label_id, str) or not label_id.strip():
            raise FixtureError(f"{path}: label id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise FixtureError(f"{path}: label name must be a non-empty string")
        if not isinstance(definition, str) or not definition.strip():
            raise FixtureError(f"{path}: label {name!r} needs a definition")
        parent_id = raw.get("parent_id")
        if parent_id is not None and not isinstance(parent_id, str):
            raise FixtureError(f"{path}: parent_id must be a string or null")
        example_rows = []
        for row in raw.get("examples") or []:
            if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                raise FixtureError(f"{path}: examples must be mappings with text")
            source = row.get("source_item_id")
            if source is not None and not isinstance(source, str):
                raise FixtureError(f"{path}: source_item_id must be a string or omitted")
            example_rows.append({"text": row["text"].strip(), "source_item_id": source})
        by_id[label_id] = {
            "id": label_id,
            "name": name.strip(),
            "parent_id": parent_id,
            "definition": " ".join(definition.split()),
            "example_rows": example_rows,
        }
    labels = []
    for label_id in by_id:
        row = by_id[label_id]
        parent_id = row["parent_id"]
        parent_name = by_id[parent_id]["name"] if parent_id and parent_id in by_id else None
        labels.append({**row, "parent_name": parent_name})
    return labels


def _normalized_passage(text: str) -> str:
    return " ".join(text.split())


def skill_markdown_from_labels(
    labels: list[dict],
    holdout_item_ids: set[str],
    holdout_passages: set[str] | None = None,
) -> str:
    """Product SKILL.md shape from in-memory labels.

    Drops examples whose ``source_item_id`` is in the test fold, and examples
    whose text matches a held-out passage (two comments can share a block).
    Examples with ``source_item_id`` omitted stay unless their text matches.
    A heading with no remaining examples still renders (same as Export).
    """
    blocked = {_normalized_passage(text) for text in holdout_passages or () if text}
    rendered = []
    for label in labels:
        examples = [
            row["text"]
            for row in label["example_rows"]
            if row["text"]
            and row.get("source_item_id") not in holdout_item_ids
            and _normalized_passage(row["text"]) not in blocked
        ]
        rendered.append(
            {
                "id": label["id"],
                "name": label["name"],
                "parent_id": label.get("parent_id"),
                "parent_name": label.get("parent_name"),
                "definition": label["definition"],
                "examples": examples,
            }
        )
    return _to_markdown(rendered)


def fixture_types(labels: list[dict]) -> list[TypeRef]:
    return [
        TypeRef(id=row["id"], name=row["name"], parent_id=row.get("parent_id"))
        for row in labels
    ]


@dataclass
class FixturePack:
    labels: list[dict]
    gold: list[GoldComment]
    types: list[TypeRef]
    roots: dict[str, Path]
    occupied: dict[str, dict[str, set[int]]]


def load_fixture_pack(root: Path) -> FixturePack:
    """Load ``fixtures/``: taxonomy, gold pointers, resolved passages. Does not open the store."""
    taxonomy_path = root / "taxonomy.yaml"
    gold_path = root / "gold.jsonl"
    papers = root / "papers"
    labels = load_fixture_taxonomy(taxonomy_path)
    names = {row["name"] for row in labels}
    if not gold_path.is_file():
        raise FixtureError(f"Missing {gold_path}")
    gold: list[GoldComment] = []
    occupied: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    roots: dict[str, Path] = {}
    seen_ids: set[str] = set()
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        item_id = row["id"]
        if item_id in seen_ids:
            raise FixtureError(f"Duplicate gold id {item_id}")
        seen_ids.add(item_id)
        paper_id = row["paper_id"]
        file_path = row["file_path"]
        line_number = row["line_number"]
        gold_names = row["gold_names"]
        if not isinstance(line_number, int):
            raise FixtureError(f"{item_id}: line_number must be an int")
        if not isinstance(gold_names, list) or not gold_names:
            raise FixtureError(f"{item_id}: gold_names must be a non-empty list")
        unknown = [name for name in gold_names if name not in names]
        if unknown:
            raise FixtureError(f"{item_id}: unknown gold name {unknown[0]!r}")
        paper_root = papers / paper_id
        tex = paper_root / file_path
        if not paper_root.is_dir():
            raise FixtureError(f"{item_id}: missing paper directory {paper_root}")
        passage = passage_at_line(tex, line_number)
        roots[paper_id] = paper_root
        occupied[paper_id][file_path].add(line_number)
        gold.append(
            GoldComment(
                comment_id=item_id,
                project_id=paper_id,
                passage=passage,
                gold_names=frozenset(gold_names),
                file_path=file_path,
                line_number=line_number,
                source_command="",
            )
        )
    if not gold:
        raise FixtureError(f"{gold_path} has no gold items")
    return FixturePack(
        labels=labels,
        gold=gold,
        types=fixture_types(labels),
        roots=dict(roots),
        occupied={pid: {fp: set(lines) for fp, lines in files.items()} for pid, files in occupied.items()},
    )


def load_types() -> list[TypeRef]:
    """Active taxonomy labels (the names Export puts in SKILL.md headings)."""
    init_db()
    with get_session() as session:
        rows = [
            TypeRef(id=row.id, name=row.name, parent_id=row.parent_id)
            for row in session.find(Label, status=LABEL_ACTIVE)
        ]
    return rows


def load_gold() -> list[GoldComment]:
    """Working-set comments with ≥1 accepted assignment on an active type.

    Passage is stored ``context_text``. ``raw_text`` is never loaded: it is
    the author's description of the issue and would leak the answer.
    """
    init_db()
    with get_session() as session:
        active = {row.id: row for row in session.find(Label, status=LABEL_ACTIVE)}
        by_comment: dict[str, set[str]] = defaultdict(set)
        for coding in session.find(Assignment, status=ASSIGNMENT_ACCEPTED):
            if not coding.label_id:
                continue
            label = active.get(coding.label_id)
            if label is None:
                continue
            by_comment[coding.comment_id].add(label.name)
        gold: list[GoldComment] = []
        for comment in session.find(ProofreadingComment):
            names = by_comment.get(comment.id)
            if not names or not in_working_set(comment):
                continue
            passage = comment.context_text
            gold.append(
                GoldComment(
                    comment_id=comment.id,
                    project_id=comment.project_id,
                    passage=passage,
                    gold_names=frozenset(names),
                    file_path=comment.file_path,
                    line_number=comment.line_number,
                    source_command=comment.source_command,
                )
            )
    return gold


def labeled_project_ids(gold: list[GoldComment]) -> set[str]:
    return {item.project_id for item in gold}


def default_holdout_mode(gold: list[GoldComment]) -> str:
    """Leave-one-paper-out when ≥2 labeled projects; else leave-one-comment-out."""
    return "paper" if len(labeled_project_ids(gold)) >= 2 else "comment"


def paper_folds(gold: list[GoldComment]) -> list[Fold]:
    """Each labeled project is the test set once; other projects train the skill."""
    by_project: dict[str, list[GoldComment]] = defaultdict(list)
    for item in gold:
        by_project[item.project_id].append(item)
    folds: list[Fold] = []
    for project_id, items in sorted(by_project.items()):
        folds.append(
            Fold(
                id=project_id,
                test_comment_ids=frozenset(item.comment_id for item in items),
                test_project_ids=frozenset({project_id}),
            )
        )
    return folds


def comment_folds(gold: list[GoldComment]) -> list[Fold]:
    """Each gold comment is the test set once (leave-one-comment-out)."""
    return [
        Fold(
            id=item.comment_id,
            test_comment_ids=frozenset({item.comment_id}),
            test_project_ids=frozenset({item.project_id}),
        )
        for item in gold
    ]


def comment_fraction_fold(
    gold: list[GoldComment],
    fraction: float,
    rng,
) -> list[Fold]:
    """Cheaper than full LOCO: one fold with a label-stratified random fraction held out."""
    by_type: dict[str, list[GoldComment]] = defaultdict(list)
    for item in gold:
        key = min(item.gold_names) if item.gold_names else ""
        by_type[key].append(item)
    chosen: list[GoldComment] = []
    for group in by_type.values():
        k = max(1, round(len(group) * fraction)) if group else 0
        k = min(len(group), max(0, k))
        if k:
            chosen.extend(rng.sample(group, k))
    ids = frozenset(item.comment_id for item in chosen)
    projects = frozenset(item.project_id for item in chosen)
    return [Fold(id="comment-fraction", test_comment_ids=ids, test_project_ids=projects)]


def resolve_folds(
    gold: list[GoldComment],
    *,
    holdout: str,
    comment_fraction: float | None,
    rng,
) -> tuple[str, list[Fold]]:
    """``holdout`` is ``auto`` / ``paper`` / ``comment``. Fraction only applies to comment mode."""
    mode = holdout if holdout != "auto" else default_holdout_mode(gold)
    if mode == "paper":
        return mode, paper_folds(gold)
    if comment_fraction is not None:
        return mode, comment_fraction_fold(gold, comment_fraction, rng)
    return mode, comment_folds(gold)


def skill_markdown(
    holdout_comment_ids: set[str],
    holdout_passages: set[str] | None = None,
) -> str:
    """Product SKILL.md shape, with examples from test comments stripped.

    Types stay the full active taxonomy (same names Export would use). A label
    with no remaining train examples still appears with definition and empty
    examples, matching today's export.
    Does not write the store.
    """
    init_db()
    active = list_active_labels()
    by_id = {label.id: label for label in active}
    labels = []
    for label in active:
        example_rows = [
            {"text": example.text, "source_item_id": example.source_comment_id}
            for example in list_examples(label.id)
        ]
        labels.append(
            {
                "id": label.id,
                "name": label.name,
                "parent_id": label.parent_id,
                "parent_name": (
                    by_id[label.parent_id].name
                    if label.parent_id and label.parent_id in by_id
                    else None
                ),
                "definition": label.definition,
                "example_rows": example_rows,
            }
        )
    return skill_markdown_from_labels(labels, holdout_comment_ids, holdout_passages)


def _tex_paths(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*.tex") if path.is_file())


def _block_occupied(start: int, end: int, occupied_lines: set[int]) -> bool:
    for line_number in occupied_lines:
        idx = line_number - 1
        if start <= idx <= end:
            return True
    return False


def unused_paragraphs(
    *,
    root: Path,
    occupied: dict[str, set[int]],
    commands: set[str],
) -> list[str]:
    """Manuscript paragraphs that do not overlap any working-set comment.

    Distractors: gold is empty. A skill that flags every paragraph pays in FP.
    Preamble / ``\\end{document}`` and other command-only blocks are skipped.
    """
    found: list[str] = []
    seen: set[str] = set()
    for path in _tex_paths(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        busy = occupied.get(rel, set()) | occupied.get(str(path), set())
        for start, end in _blocks(lines):
            if _block_occupied(start, end, busy):
                continue
            if not any(
                lines[i].strip() and not _is_structural_line(lines[i])
                for i in range(start, end + 1)
            ):
                continue
            chunk_lines = []
            for line in lines[start : end + 1]:
                if any(f"\\{command}{{" in line for command in commands):
                    continue
                chunk_lines.append(line.rstrip())
            chunk = "\n".join(chunk_lines).strip()
            if not chunk or chunk in seen or not is_prose_passage(chunk):
                continue
            seen.add(chunk)
            found.append(chunk)
    return found


def sample_distractors(
    candidates: list[str],
    n: int,
    rng,
) -> list[str]:
    """Up to ``n`` unused paragraphs (target: about one distractor per gold item)."""
    if n <= 0 or not candidates:
        return []
    k = min(n, len(candidates))
    return rng.sample(candidates, k)


def heading_names_from_skill(skill_md: str) -> list[str]:
    """``##`` label headings from exported skill markdown, not ``### Definition``."""
    names: list[str] = []
    for line in skill_md.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            names.append(line[3:].strip())
    return names


def is_prose_passage(text: str) -> bool:
    """True when a block still has sentence words after stripping TeX commands.

    Keeps distractors from being ``\\end{document}`` or a preamble line.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        without_cmd = re.sub(
            r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?",
            " ",
            stripped,
        )
        words = re.findall(r"[A-Za-z]{3,}", without_cmd)
        if len(words) >= 4:
            return True
    return False


def skill_prompt(skill_md: str, passage: str) -> str:
    """Skill condition: taxonomy first, then the passage, then JSON-only instruction."""
    return (
        f"{skill_md.rstrip()}\n\n"
        "Passage:\n"
        f"{passage}\n\n"
        "Flag labels from the skill that apply to this passage. "
        "Use only label names that appear as ## headings in the skill. "
        f"{JSON_INSTRUCTION}"
    )


def baseline_prompt(passage: str, skill_md: str) -> str:
    """Same heading names as the skill, without definitions or examples."""
    headings = "\n".join(f"## {name}" for name in heading_names_from_skill(skill_md))
    return (
        f"{headings}\n\n"
        "Flag writing issues in this passage. "
        "Use only label names that appear as ## headings above. "
        "Do not use other names.\n\n"
        f"Passage:\n{passage}\n\n"
        f"{JSON_INSTRUCTION}"
    )


def prompt_for(condition: str, skill_md: str | None, passage: str) -> str:
    """Dispatch skill vs names-only baseline. Same items, different prompt body."""
    if not skill_md:
        raise ValueError(f"{condition} condition requires skill markdown")
    if condition == SKILL_CONDITION:
        return skill_prompt(skill_md, passage)
    if condition == BASELINE_CONDITION:
        return baseline_prompt(passage, skill_md)
    raise ValueError(f"Unknown condition {condition}")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def cache_key(condition: str, item_id: str, prompt: str) -> str:
    """Token cache identity. A prompt-template change invalidates the hash."""
    return f"{condition}:{item_id}:{prompt_hash(prompt)}"


def load_cache(path: Path) -> dict[str, str]:
    """Load ``cache.jsonl`` as key → response. Missing file is an empty cache."""
    rows: dict[str, str] = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[row["key"]] = row["response"]
    return rows


def append_cache(path: Path, key: str, prompt: str, response: str) -> None:
    """Append one cached completion. Prompt text is stored so template edits change the hash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"key": key, "prompt": prompt, "response": response}, ensure_ascii=False)
            + "\n"
        )


@dataclass
class EvalItem:
    """One LLM call target: a gold passage or a distractor paragraph."""

    id: str
    fold: str
    project_id: str
    comment_id: str | None
    passage: str
    gold_names: list[str]
    is_distractor: bool


def gold_item(fold: Fold, comment: GoldComment) -> EvalItem:
    """Eval row for a held-out labeled comment (gold names copied through)."""
    return EvalItem(
        id=comment.comment_id,
        fold=fold.id,
        project_id=comment.project_id,
        comment_id=comment.comment_id,
        passage=comment.passage,
        gold_names=sorted(comment.gold_names),
        is_distractor=False,
    )


def distractor_item(fold: Fold, project_id: str, index: int, passage: str) -> EvalItem:
    """Eval row with empty gold. Any predicted name is a false positive."""
    return EvalItem(
        id=f"distractor:{fold.id}:{project_id}:{index}",
        fold=fold.id,
        project_id=project_id,
        comment_id=None,
        passage=passage,
        gold_names=[],
        is_distractor=True,
    )
