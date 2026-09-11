ReviewDistill

AI-Assisted Continuous Distillation of Expert Review Practices

1. Overview

ReviewDistill is a local-first tool for continuously distilling an expert’s informal scholarly proofreading comments into a structured, evolving body of reusable review knowledge.

The user should be able to proofread papers naturally, using whatever commenting mechanism they already use. ReviewDistill then extracts those comments, associates them with manuscript context, and uses AI-assisted qualitative coding to identify recurring issues and patterns.

Over multiple papers and multiple review sessions, these observations are progressively distilled into an evolving taxonomy of review issues, including:

* issue categories
* definitions
* examples
* counterexamples
* severity or importance
* contextual cues
* relationships between issue types
* eventually, machine-detectable review rules

The resulting knowledge can be exported as a review rubric for coding agents such as Cursor.

2. Core Concept

The central workflow is:

Natural Expert Review
        │
        ▼
Informal Review Comments
        │
        ▼
Comment Extraction
        │
        ▼
Contextualized Observations
        │
        ▼
AI-Assisted Qualitative Coding
        │
        ▼
Recurring Patterns / Issue Types
        │
        ▼
Evolving Review Taxonomy
        │
        ▼
Operational Definitions + Examples
        │
        ▼
Reusable Review Knowledge
        │
        ├──────────────► Coding-agent review rubric
        │
        └──────────────► Future AI-assisted coding

The system should be incremental rather than a one-shot clustering tool.

Each new proofreading session should have the potential to:

1. reinforce an existing issue type;
2. provide new examples of an existing issue;
3. reveal a previously unseen issue;
4. suggest that an existing issue should be split;
5. suggest that multiple issues should be merged;
6. refine the definition or boundaries of an issue.

The taxonomy is therefore an evolving representation of the reviewer’s practice.

⸻

3. Goals

Primary goals

1. Allow the user to continue proofreading using their existing workflow.
2. Automatically collect review comments from the manuscript/repository.
3. Preserve the original comments and manuscript context.
4. Use AI to inductively code comments into recurring issue types.
5. Maintain an evolving taxonomy of review issues.
6. Allow the expert to quickly validate, modify, merge, and split AI-generated labels.
7. Accumulate examples and counterexamples for each issue type.
8. Export the resulting review knowledge in a format usable by coding agents.

Secondary goals

* Track how the taxonomy evolves over time.
* Associate comments with Git commits.
* Eventually connect comments to the revisions made by paper authors.
* Support multiple projects/papers.
* Support multiple LaTeX commenting syntaxes.
* Make the underlying representation independent of LaTeX so other review sources can be added later.

⸻

4. Non-Goals for v0.1

Do not attempt to build:

* a general-purpose LaTeX editor;
* a full Overleaf replacement;
* a fully autonomous paper reviewer;
* automatic modification of manuscript text;
* a cloud-based collaborative review platform;
* a complex multi-user permission system;
* a general-purpose annotation platform;
* a sophisticated vector database infrastructure;
* a large autonomous multi-agent architecture.

The prototype should demonstrate the distillation loop, not solve every aspect of scholarly reviewing.

⸻

5. Primary User Workflow

The intended workflow should require minimal behavioral change from the reviewer.

Step 1 — Initialize a project

reviewdistill init

This creates a project configuration such as:

project:
  name: paper-01
comments:
  latex_commands:
    - myremark

Multiple commands should be supported:

comments:
  latex_commands:
    - myremark
    - note
    - review

The exact commands are project-specific.

The system must not assume that all projects use \myremark.

Step 2 — Proofread normally

The user continues to annotate the LaTeX source using their existing commands.

For example:

The results demonstrate that ...
\myremark{I think "demonstrate" is too strong here. The experiment only provides evidence for this claim.}

Another project might use:

\note{This paragraph does not explain why this design decision was necessary.}

The extraction layer should treat the syntax as an input mechanism, not as a semantic label.

Step 3 — Extract comments

reviewdistill extract

ReviewDistill identifies new comments and extracts:

* comment text
* source file
* line number
* source command
* surrounding manuscript text
* section/subsection
* Git commit
* other available contextual information

Step 4 — AI-assisted coding

In `reviewdistill serve`, Unlabeled → **Get AI suggestions**.

Workbench **Settings** (header, next to Export) has two panels. **Assistant** writes `llm.provider` / `llm.model` to the chosen paper’s `.reviewdistill/config.yaml` and the matching API key to that paper’s `.reviewdistill/.env` (gitignored). **Data** shows the home folder (same as `reviewdistill paths`) and does not Save. Opening Settings always lands on Assistant. The Unlabeled empty state **Configure LLM** opens the same dialog. GET `/api/llm-settings` never returns the secret (`key_set` only). File editing still works. Process environment still wins over `.env`. Do not write `llm.api_key` into YAML; do not store keys in the JSONL store.

`reviewdistill paths use DIR` persists `DIR` in `~/.config/reviewdistill/home` so later CLI commands use that folder. `reviewdistill paths move DIR` copies the current home (JSONL files) into an empty `DIR`, then uses it; it leaves the old folder in place and refuses if the store is busy.

Assistant fields: Paper (cwd paper preselected when registered), Provider (DeepSeek / OpenAI / Anthropic), Model (filled with that provider’s default), API key (password + show/hide). Save is disabled until a paper is chosen. An empty key field on Save keeps the existing `.env` value. `POST /api/llm-settings` with `api_key` omitted or `""` means keep; unknown project 404; unknown provider 400; new provider with no key 400. This dialog does not write a home-level `~/.reviewdistill` key, probe the key live, or offer mock / Ollama / custom base URL.

For each new observation, AI considers:

* the raw comment;
* manuscript context;
* existing issue types;
* previous similar comments;
* examples associated with those issue types.

It proposes:

Existing issue type:
  Overclaiming
Confidence:
  0.91
Rationale:
  The reviewer objects to "demonstrate" because the evidence
  only supports a weaker claim.
Suggested evidence:
  "demonstrate" → "suggest"

Alternatively, it may propose:

New issue type:
  Insufficient justification of methodological choice
Definition:
  The manuscript describes a methodological or design decision
  without explaining why that decision was made.

Step 5 — Human validation

The reviewer sees the workbench.

For each comment:

────────────────────────────────────────
Comment
"This paragraph does not explain why this design
decision was necessary."
Context
"We designed the interface using ..."
────────────────────────────────────────
Assign type
NEW ISSUE TYPE
Insufficient methodological justification
Confidence: 0.78
[Accept] [Change]
Quality
[Verify] [Drop]
────────────────────────────────────────

The user should be able to validate a suggestion with minimal interaction.

Step 6 — Continuous accumulation

After multiple reviews, the system may have:

Overclaiming
  17 observations
Missing methodological justification
  9 observations
Ambiguous terminology
  14 observations
Unsupported causal claim
  7 observations
Weak motivation
  12 observations

The system should continuously use these accumulated observations to improve future coding.

⸻

6. Core Data Model

The system should explicitly separate raw observations from AI interpretations.

6.1 ProofreadingComment

Represents what the reviewer actually wrote. Field definitions, statuses, and fingerprinting: `docs/data-schema.md`.

ProofreadingComment(
    id,
    project_id,
    source_type,
    source_command,
    file_path,
    line_number,
    raw_text,
    context_text,
    section,
    git_commit,
    git_url,
    fingerprint,
    status,
    quality,
    supersedes_id,
    created_at
)

Important principle:

raw_text must never be overwritten by AI interpretation.

The original observation is the primary evidence.

⸻

6.2 Coding

Represents an AI or human interpretation of a comment.

Coding(
    id,
    comment_id,
    issue_type_id,
    coder_type,
    confidence,
    rationale,
    status,
    created_at
)

Possible coder_type:

ai
human

Possible status:

proposed
accepted
modified

A comment may eventually have multiple codings.

⸻

7. Issue Taxonomy

The taxonomy represents the reviewer’s evolving conceptualization of common problems.

An IssueType should contain approximately:

IssueType(
    id,
    code,
    name,
    category,
    definition,
    status,
    created_at,
    updated_at
)

Example:

code: OVERCLAIM
name: Overclaiming
category: Argumentation
definition: >
  A claim is stated more strongly than the evidence or analysis
  presented in the manuscript supports.

Each issue type should additionally support:

Examples

"The results demonstrate..."
→ evidence only supports "suggest"

Counterexamples

Cases where superficially similar text should not receive the issue type.

Notes

Additional observations from the reviewer.

⸻

8. Taxonomy as an Evolving Object

The taxonomy must not be treated as a static list generated once.

ReviewDistill should support:

Add

Create a new issue type.

Rename

"Overly strong claim"
→
"Overclaiming"

Edit

Refine the definition.

Merge

"Unsupported claim"
+
"Overly strong claim"
→
"Overclaiming"

Split

"Insufficient explanation"
→
"Missing motivation"
+
"Missing methodological justification"

Move

Move an issue type between higher-level categories.

Deactivate

The group leaves the live taxonomy. Labeled comments return to Unlabeled. Codings are stored on the history event so undo restores them.

Historical data must never be silently deleted when the taxonomy changes.

⸻

9. AI Coding Strategy

The coding process should be inductive, inspired by qualitative coding rather than predetermined classification.

For every new comment:

Stage 1 — Retrieve potentially relevant existing issues

Search the existing taxonomy and previously coded comments.

Possible approaches:

* lexical similarity;
* embeddings;
* LLM semantic comparison;
* simple database queries.

For v0.1, embeddings are optional.

A vector database is not required.

Stage 2 — Generate coding candidates

The model should consider:

Existing issue A
Existing issue B
Existing issue C
New issue

and produce a ranked recommendation.

Stage 3 — Explain the recommendation

The AI should explain:

Why does this comment belong to this issue type?

The explanation should refer to the actual observation and manuscript context.

Stage 4 — Allow disagreement

The AI must not silently modify the taxonomy.

The human reviewer remains the authority.

⸻

10. Important Distinction: Observation vs Interpretation

The system should explicitly preserve the distinction between:

Observation

“I think ‘demonstrate’ is too strong here.”

and:

Interpretation

“Overclaiming”

and:

Operational rule

Flag strong evidential verbs such as “demonstrate” when the cited evidence is observational rather than causal.

This progression is fundamental to ReviewDistill:

Observation
    ↓
Code
    ↓
Issue Type
    ↓
Definition
    ↓
Examples / Counterexamples
    ↓
Operational Review Rule

The system should not prematurely collapse these levels.

⸻

11. Context Extraction

A comment without manuscript context is often ambiguous.

For each comment, automatically extract approximately:

* 1–3 surrounding sentences;
* containing paragraph;
* section/subsection;
* nearby citation(s);
* nearby figure/table references;
* source file;
* line number.

Example:

Comment:
"I don't think this follows."
Section:
4.2 Results
Context:
"Model A achieved higher accuracy than Model B.
Therefore, Model A is more suitable for real-world applications."

This allows AI coding to distinguish between different kinds of criticism.

⸻

12. Git Integration

Because the manuscripts are likely Git repositories, Git should be integrated from the beginning.

For every extracted comment, record:

repository
remote URL (if a git remote such as origin is configured)
commit hash
file
line

This makes it possible to later reconstruct:

Original manuscript
       ↓
Reviewer comment
       ↓
Author revision
       ↓
Final manuscript

This is particularly valuable for future versions of ReviewDistill.

For example:

Original:
"The results demonstrate that..."
Reviewer:
"Too strong."
Revision:
"The results suggest that..."

This could eventually become a high-quality example of the review rule:

When evidence does not establish a claim conclusively,
prefer weaker epistemic language.

Version-to-version revision linkage is not required for v0.1, but the data model should not prevent it.

⸻

13. Continuous Distillation

This is the defining feature of ReviewDistill.

The system should maintain a distinction between:

Current review corpus

All raw comments accumulated across papers.

Current coding state

The latest accepted coding of those comments.

Current taxonomy

The reviewer’s current conceptualization of recurring issues.

Review knowledge

The operationalized knowledge derived from the taxonomy.

Conceptually:

                 New Review
                     │
                     ▼
             New Observations
                     │
                     ▼
        ┌────────────────────────┐
        │ Existing Review Corpus │
        └────────────┬───────────┘
                     │
                     ▼
              AI Re-coding /
             Pattern Discovery
                     │
                     ▼
          Evolving Taxonomy
                     │
                     ▼
         Refined Review Knowledge
                     │
                     ▼
           Future Review Coding

The prototype should make this accumulation visible.

For example:

ReviewDistill has processed 184 comments across 7 papers.

12 recurring issue types have been identified.

3 issue types were introduced this month.

2 issue types were merged after additional evidence.

⸻

14. Workbench UI

The primary UI should be a local web application.

The central screen should be a coding workbench: Issue Taxonomy, Issue Details, and Comments on one screen — not a generic dashboard.

Example:

```
ReviewDistill · Workbench · History · Export
────────────────────────────────────────
Selectors  [MISSINGINTRODUCT (17) ×]                    [Unlabeled (8)]
────────────────────────────────────────
Issue Taxonomy  Issue Details        Comments
Argumentation   Overclaiming         17 total · 1 selected
  Overclaiming  Definition
  17 accepted   Rename / Split
Clarity
```

The top bar switches Workbench and History, and opens Export (format plus deactivate). Selectors are a second header: a dismissable chip named with the issue **code** once a group is selected, and a persistent Unlabeled chip on the right. Unlabeled and issue groups share this one screen.

Column order is always Issue Taxonomy | Issue Details | Comments. Clicking a type selects it: Issue Details shows that type, Comments filters to its accepted comments, and its code chip becomes the active selector. The Comments header shows total and selected counts.

The Comments panel can switch between a list of comments and a single comment. The list shows truncated text so you can scan, and marks comments that are not in the manuscript. The single-comment view shows the full text, manuscript context, location, and record metadata. **Accept** and **Change** assign or change the issue type (there is no Reject: not accepting a suggestion leaves the comment unlabeled). **Verify** and **Drop** stamp quality, independent of the label.

Selector chips are mutually exclusive. Sure/Unsure confidence chips are not in this product. Counterexamples are not collected in Issue Details (they are not available from LaTeX annotations). Deactivate a group from the Export dialog, not from Issue Details.

⸻

15. Taxonomy View

The same workbench is the taxonomy view. Issue Taxonomy stays on the left; Issue Details stays in the middle. Clicking an issue type selects it: Issue Details shows the definition, Comments shows that type’s labeled working-set comments, and a selector chip named with its code (for example `MISSINGINTRODUCT (17)`) becomes active.

```
Selectors  [MISSINGINTRODUCT (17) ×]                    [Unlabeled]
Issue Taxonomy         Issue Details             Comments
Argumentation          Overclaiming              17 total · 1 selected
  Overclaiming    17   Definition
```

Issue Details does not repeat comment text and does not collect counterexamples. Labeled comments in the Comments panel are the examples. Export (and deactivate) live in the header Export dialog.

Drag an unlabeled comment onto a type: same as Change.
Drag a type onto another type: merge (source into target).
Drag a type onto a category heading: move (`POST /api/taxonomy/{id}/move` with `{ "category" }` so the drag does not round-trip definition fields).
Split stays in Issue Details. Rename and definition editing are in-place on the Issue type and Definition panels. Deactivate is chosen in Export.
Divide, flatten, and ungrouped nodes are not in this product. Drag uses native HTML5 only.

The Comments header has list / one-comment controls. The list is for scanning. One comment shows context and metadata, with prev / pager / next at the bottom (one comment per page).

Overclaiming
Definition
A claim is stronger than the evidence supports.

⸻

16. Taxonomy Evolution View

History is a chronological log of taxonomy mutations and workbench verdicts (the `taxonomy_events` table). The History page lists each event with a short summary and the raw payload JSON. **Undo** and **Redo** invert or reapply the tip of the log. They mark the row undone (`undone` column) rather than appending a new event. A new forward action deletes the redo tail. Undo/Redo act on the tip, not on a selected row. Jump-to-event restore is out of scope.

Get AI suggestions is one `propose` event for the batch. Accept of a newly created issue type is `add` then `accept`; Undo Accept first. Old `merge`/`split` rows without invert payload fields cannot be undone (Undo disabled while they are the tip).

| Type | When | Undo |
|------|------|------|
| `add` | New issue type | Deactivate that type |
| `rename` | Name/code change | Restore `before` |
| `edit` | Definition/notes | Restore `before` |
| `move` | Category change only (`from` ≠ `to`) | Move back to `from` |
| `deactivate` | Deactivate (labeled comments return to Unlabeled) | Reactivate; restore labels |
| `merge` | Merge (payload includes reassigned ids) | Reactivate sources; move rows back |
| `split` | Split (payload includes deleted coding dumps) | Reactivate source; deactivate created types; restore codings |
| `propose` | Get AI suggestions | Delete created proposed rows; restore any it replaced |
| `accept` | Accept | Coding back to proposed; delete example if this accept created it |
| `change` | Change | Delete human coding; restore proposal; delete example if created |
| `verify` | Verify | Restore `previous_quality` |
| `drop` | Drop | Restore `previous_quality` |

`GET /api/history` — events newest first, each with `undone` and `summary`; top-level `can_undo`, `can_redo`. `POST /api/history/undo` and `POST /api/history/redo` — `{ ok: true }` or 400 if nothing to do / cannot invert.

A sophisticated visualization of splits and merges is not required for v0.1.

⸻

17. CLI

The initial CLI should be approximately:

reviewdistill init

Initialize a repository.

reviewdistill extract

Extract new proofreading comments.

reviewdistill export

Export reusable review knowledge.

reviewdistill serve

Start the local web UI.

Future:

reviewdistill review

Use the distilled knowledge to review a new manuscript.

⸻

18. Export Format

The exported review knowledge should be human-readable and usable by coding agents.

For example:

# Scholarly Review Rubric
## Overclaiming
### Definition
Flag claims whose strength exceeds the evidence presented.
### Examples
- "The results demonstrate..." when evidence is correlational.
- "This proves..." when the experiment does not establish causality.
### Counterexamples
Do not flag strong claims when the experimental design directly
supports the stated conclusion.

A YAML/JSON representation should also be supported for programmatic use.

⸻

19. Coding-Agent Integration

The exported taxonomy should be usable by tools such as Cursor.

Conceptually:

ReviewDistill
     │
     │ export
     ▼
review-rubric.md
     │
     ▼
Coding Agent
     │
     ▼
New Manuscript
     │
     ▼
Potential Review Issues

The coding agent should not simply receive a list of labels.

It should receive:

Issue
Definition
Examples
Counterexamples

This transforms qualitative coding results into operational review knowledge.

⸻

20. Source Extraction Architecture

The comment-extraction layer should be extensible.

Define an interface conceptually like:

class CommentExtractor:
    def extract(self, source) -> list[ProofreadingComment]:
        ...

Initial implementation:

LatexCommandExtractor

Future implementations:

GithubReviewExtractor
MarkdownExtractor
WordCommentExtractor

The normalized output should always be ProofreadingComment.

This ensures that the system’s conceptual model is not tied to LaTeX.

⸻

21. LaTeX Extraction

The extractor should support configurable commands.

Example:

comments:
  latex_commands:
    - myremark

or:

comments:
  latex_commands:
    - myremark
    - question
    - revise

The parser should extract comments robustly enough to handle:

* multiline comments;
* comments containing LaTeX;
* comments near paragraphs;
* escaped characters;
* nested braces where feasible.

The command name should be retained:

source_command = "question"

but should not automatically determine the semantic issue type.

For example:

\question{This argument does not follow.}

could still be coded as:

Logical gap

⸻

22. Incremental Extraction

Extraction must be idempotent.

Running `reviewdistill extract` twice must not duplicate comments that are still present.

Identity (new, revision, move, gone from the source, Verify vs Drop) is defined in [`comment-identity.md`](comment-identity.md). The stored project and comment rows are [`data-schema.md`](data-schema.md).

`reviewdistill extract --watch` runs the same extraction after LaTeX sources settle. It does not run labeling and does not Verify or Drop.

The AI never overwrites the reviewer’s comment text. Source-driven revision of a still-present comment updates that observation’s wording in place.

⸻

23. Storage

Use JSONL files in the home folder (one object per line, sorted by id).

Suggested entities:

projects
comments
codings
issue_types
issue_examples
issue_counterexamples
taxonomy_events
git_commits

JSONL files in the home folder, one object per line. SQLModel (or Pydantic) records are fine.

No external database server should be required.

⸻

24. Local-First / Privacy

The prototype should be local-first.

The manuscript and review comments should remain on the user’s machine unless the user explicitly configures an external LLM.

LLM access should be abstracted behind a provider interface:

class LLMProvider:
    def generate(...)

Potential providers:

* OpenAI
* Anthropic
* DeepSeek
* local models

The application should make it clear when manuscript content is being sent externally.

Where practical, send only the minimum necessary context:

review comment
+
relevant manuscript context
+
relevant existing issue definitions/examples

Do not send the entire repository unnecessarily.

⸻

25. Suggested Technical Stack

A reasonable prototype stack is:

Backend

* Python
* Typer for CLI
* FastAPI for local API
* JSONL files in the home folder

Frontend

* Vue 3 + TypeScript SPA (`client/`)
* FastAPI JSON under `/api`
* `reviewdistill serve` serves the built SPA (no Node at runtime)

However, simplicity is more important than these specific technologies.

⸻

26. Suggested Project Structure

reviewdistill/
│
├── cli/          init, extract, export, serve
├── extraction/   LaTeX comments + incremental match
├── coding/       AI propose, retrieve, validate, cluster
├── taxonomy/     issue types, merge/split, export
├── context/      manuscript neighborhood
├── llm/          provider interface
├── db/           JSONL models and session
└── web/          FastAPI `/api` + packaged client static

The exact structure can be simplified for the prototype.

⸻

27. AI Prompting Principles

AI prompts should explicitly distinguish:

What the reviewer observed

from:

What the AI infers

For example:

Reviewer observation:
"I think 'demonstrate' is too strong."
Manuscript context:
"The experiment..."
Existing issue types:
...
Task:
Determine whether this observation is best explained by an
existing issue type. If so, recommend the best match.
If no existing issue type adequately captures the observation,
propose a candidate new issue type.
Do not modify the taxonomy automatically.

This helps preserve the qualitative-analysis character of the system.

⸻

28. Human-in-the-Loop Principle

The system should be AI-assisted, not AI-authoritative.

The reviewer is the expert whose practice is being distilled.

Therefore:

AI proposes
      ↓
Human validates
      ↓
Taxonomy changes
      ↓
Future AI proposals improve

Human decisions should themselves become data.

For example:

AI proposed:
Unsupported claim
Human selected:
Overclaiming

This provides evidence that the AI’s conceptualization was incorrect and can improve future suggestions.

⸻

29. Future Research Direction

The prototype should leave room for a stronger research system in which ReviewDistill learns a reviewer’s practice over many papers.

Potential future capabilities include:

Review-pattern discovery

Automatically identify patterns that have not yet been formally coded.

Taxonomy refinement

Detect when an existing category has become too broad.

Reviewer-specific modeling

Learn what particular issues a reviewer tends to identify.

Revision-aware learning

Connect comments to subsequent author revisions.

Agentic review

Use the distilled knowledge to review new manuscripts automatically.

Confidence calibration

Determine which review issues can be reliably detected by an AI and which require human judgment.

Review-practice comparison

Potentially compare the taxonomies of different reviewers.

⸻

30. Prototype Success Criterion

The prototype is successful if the following workflow works end-to-end:

1. Clone a paper repository.
2. Configure its LaTeX comment commands.
3. Proofread normally.
4. Run:
       reviewdistill extract
5. ReviewDistill automatically finds the comments.
6. It extracts manuscript context.
7. In the workbench, Get AI suggestions.
8. AI proposes codes using the accumulated taxonomy.
9. The reviewer rapidly labels comments (Accept / Change) and stamps quality (Verify / Drop).
10. The taxonomy accumulates examples and definitions.
11. Review a second paper.
12. The accumulated taxonomy improves the coding of its comments.
13. Export:
       review-rubric.md
14. Use the rubric with a coding agent to review a new paper.

The key demonstration is therefore not merely that AI can classify proofreading comments.

The key demonstration is:

A stream of informal expert review comments can be continuously distilled into an evolving, operationalized representation of the expert’s review practice, which can subsequently be reused by AI systems.

⸻

31. Research Framing

A useful conceptual framing for the project is:

ReviewDistill investigates how AI can continuously distill informal expert review observations into an evolving, reusable representation of scholarly review practice.

The process resembles qualitative analysis:

Open coding
    ↓
Recurring observations
    ↓
Category formation
    ↓
Category refinement
    ↓
Operational definitions
    ↓
Examples / counterexamples
    ↓
Reusable coding/review framework

But the distinctive system contribution is the continuous loop:

             ┌─────────────────────┐
             │                     │
             ▼                     │
       Expert Reviews              │
             │                     │
             ▼                     │
      Informal Comments            │
             │                     │
             ▼                     │
       AI Coding                   │
             │                     │
             ▼                     │
    Evolving Taxonomy              │
             │                     │
             ▼                     │
    Operationalized Rules          │
             │                     │
             ▼                     │
       Future Reviews ─────────────┘

The system thus treats proofreading not simply as annotation, but as a source of continuously accumulating review knowledge.