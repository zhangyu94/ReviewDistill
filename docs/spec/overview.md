# Overview

ReviewDistill is a local-first tool that turns informal LaTeX proofreading comments into an evolving label taxonomy and a reusable agent skill.

You proofread with whatever comment macros you already use. ReviewDistill extracts those remarks with the manuscript sentence they sit in, and you group recurring ones into labels. Over papers, that taxonomy is the reviewer’s practice, not a one-shot clustering of a single file.

A shipped label has:

* a parent (`parent_id`)
* a definition
* examples
* `detection_guidance` (retrieval only; not shown in Label Details)

Later: severity or importance, relationships to other labels, rules an agent can apply.

Classification uses one family with three roles:

| Role | Meaning | Word |
|---|---|---|
| Collection | the scheme / tree | **taxonomy** |
| Category | an abstract class in that scheme | **label** |
| Assignment | a comment classified with a category | **labeled** / **unlabeled**; a **label assignment** |

The tree header is **Label Taxonomy**, not **Labels** (that would read as a bag of assignments). Use **taxonomy** only for the scheme: dump filenames `review-taxonomy.yaml` / `.json`, package `reviewdistill/taxonomy/`, client `taxonomyTree.ts`. Product copy, HTTP, JSON, and store files use **label**, not **type** / **issue type**. The History undo log is `history.jsonl`.

Keep these names: `Assignment` rows (`assignments.jsonl`), parking name **ungrouped**, inbox **Unlabeled**, **Label with AI**, Verify / unreviewed / to distill. YAML/JSON export wraps the list in `labels`. Skill-eval still scores `{"types": [...]}`.

## Core concept

```
Natural expert review
        │
        ▼
Informal review comments
        │
        ▼
Comment extraction
        │
        ▼
Contextualized observations
        │
        ▼
AI-assisted qualitative coding
        │
        ▼
Recurring labels
        │
        ▼
Evolving review taxonomy
        │
        ▼
Definitions + examples
        │
        ▼
Reusable review knowledge
        │
        ├──────────────► Coding-agent review skill
        │
        └──────────────► Future AI-assisted coding
```

The taxonomy grows with each paper. Each session can reinforce a label, add an example, introduce a new issue, split or merge labels, or refine a definition.

## Goals

1. Let the reviewer keep their existing proofreading workflow.
2. Collect comments from the manuscript.
3. Preserve original comment text and manuscript context.
4. Use AI to code comments into recurring labels.
5. Keep an evolving taxonomy.
6. Let the reviewer validate, change, merge, and split labels quickly.
7. Accumulate examples for each label.
8. Export that knowledge as a skill a coding agent can use.

Also in scope: History of taxonomy change, Git commit on each extract, several papers in one store, several LaTeX comment commands, a comment model that is not tied to LaTeX. Connecting comments to later author revisions is future work.

## Non-goals

Do not build:

* a LaTeX editor or Overleaf replacement
* an autonomous paper reviewer
* automatic edits to manuscript text
* a cloud collaborative review platform
* multi-user permissions
* a general annotation platform
* a required vector database
* a multi-agent architecture

The product is the distillation loop.

## Stack

* Python, Typer CLI, FastAPI, JSONL in the home folder
* Vue 3 + TypeScript SPA in `client/`
* `reviewdistill ui` serves the built SPA (no Node at runtime)

```
reviewdistill/
├── cli/          init, extract, export, ui
├── extraction/   LaTeX comments + incremental match
├── labeling/     AI propose, retrieve, validate
├── taxonomy/     labels, merge/split, export
├── context/      manuscript neighborhood
├── llm/          provider interface
├── db/           JSONL models and session
└── web/          FastAPI `/api` + packaged client static
```

## Success

The loop works when a reviewer can:

1. Init a paper and configure its comment commands.
2. Proofread as usual.
3. Run `reviewdistill extract`.
4. Open `reviewdistill ui`, assign leaves, optionally **Label with AI**, **Verify** or **Delete**.
5. Repeat on a second paper with the same taxonomy.
6. Export `SKILL.md` and use it with a coding agent.

## Future research

Room to grow: discovering unlabeled patterns, splitting labels that have become too broad, reviewer-specific models, linking comments to author revisions, agentic review of a new manuscript, confidence about which issues an AI can flag, comparing taxonomies across reviewers.

The process is qualitative analysis (open coding → categories → definitions → examples) in a loop: expert reviews feed comments, coding updates the taxonomy, and the next paper uses that knowledge.
