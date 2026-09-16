# Taxonomy

Keep the reviewer’s wording as evidence. Labels and assignments are interpretation; they never overwrite `raw_text`.

Field lists, statuses, and pairing: [`data-schema.md`](data-schema.md).

## Comment

The stored observation is what the reviewer wrote:

```
ProofreadingComment(
    id,
    project_id,
    source_type,
    source_command,
    file_path,
    line_number,
    raw_text,
    context_text,
    context_offset,
    section,
    git_commit,
    git_url,
    status,
    verified,
    supersedes_id,
    created_at
)
```

`raw_text` is never overwritten by AI interpretation.

## Assignment

An assignment is an AI or human reading of that comment:

```
Assignment(
    id,
    comment_id,
    label_id,
    coder_type,
    confidence,
    rationale,
    status,
    created_at
)
```

`coder_type` is `ai` or `human`. Assignment `status` is `proposed`, `accepted`, or `modified`. A comment may have several assignments over time.

## Labels

The live taxonomy is the reviewer’s current map of recurring problems. A label looks like:

```
Label(
    id,
    name,
    parent_id,
    position,
    definition,
    status,
    created_at,
    updated_at
)
```

It is a forest of arbitrary depth. `parent_id` is null for a root, otherwise another label’s id. `position` is order among siblings and is rewritten to `0..n-1` whenever that sibling list changes. Every node is a real label: it can have children and its own labeled comments. There are no folder-only nodes.

Invariants: `parent_id` is null or an **active** label; there are no cycles. Inactive labels keep their last parent and position so undo can restore them; they are omitted from the live tree. Active `name` stays unique the same way as image-taxonomy-labeler: if `Overclaiming` is taken, the next is `Overclaiming (2)`, filling gaps. Create uses name `New label`, `New label (2)`, …. Rename and Accept of a new label use the same name suffix. Inactive names do not block a live name.

Load does not rewrite leftover `category` or `proposed_issue_category` fields. Missing `parent_id` is a root. An active label whose parent is missing, inactive, or cyclic fails fast. Do not promote old category strings into parent labels.

A proposal for a **new** label stores `proposed_parent_id`: an existing active label id, or null for a root. Unknown or omitted parent becomes a root. Do not mint an intermediate parent from a free-text name.

```yaml
name: Overclaiming
parent_id: null
definition: >
  A claim is stated more strongly than the evidence or analysis
  presented in the manuscript supports.
```

Each label can also hold examples (`"The results demonstrate..."` when the evidence only supports “suggest”), stored on `label_examples`. `detection_guidance` is used in retrieval and is not shown in Label Details. `notes` is not a field.

## Evolution

The taxonomy is not a list generated once. ReviewDistill supports:

| Action | What it does |
| --- | --- |
| Add | Create a new label |
| Rename | e.g. “Overly strong claim” → “Overclaiming” |
| Edit | Refine the definition |
| Merge | “Unsupported claim” + “Overly strong claim” → “Overclaiming” |
| Split | “Insufficient explanation” → “Missing motivation” + “Missing methodological justification” |
| Move | Nest a label under another, or reorder it among siblings (before / after) |
| Flatten | Reassign descendant comments onto this label and deactivate the descendants |
| Remove | Delete this label and its subtree. Undo restores the dump |

There is no Deactivate button and no HTTP deactivate route. Flatten, split, and merge still retire labels this way: the group leaves the live taxonomy, children become siblings, and labeled comments on that label return to Unlabeled. Assignments are stored on the history event so undo restores them. A leftover accepted assignment on an inactive label does not count as labeled. Export unchecking a label is a one-shot filter (`--id`); it does not deactivate the row.

Historical data is never silently deleted when the taxonomy changes.

## AI coding

Coding is inductive: start from the observation, then match or propose a label. It is not a closed classifier over a frozen list.

For every new comment:

1. **Retrieve** potentially relevant existing issues from the taxonomy and previously assigned comments (lexical similarity, embeddings, LLM comparison, or simple queries). Embeddings are optional. A vector database is not required.
2. **Recommend** a ranked choice among existing leaves or a new name.
3. **Explain** why this comment belongs there, using the observation and manuscript context.
4. **Leave the decision to the reviewer.** The model does not silently modify the taxonomy.

## Observation vs interpretation

Keep these levels separate:

| Level | Example |
| --- | --- |
| Observation | “I think ‘demonstrate’ is too strong here.” |
| Interpretation | “Overclaiming” |
| Operational rule | Flag strong evidential verbs such as “demonstrate” when the cited evidence is observational, not causal |

```
Observation
    ↓
Code
    ↓
Label
    ↓
Definition
    ↓
Examples / Counterexamples
    ↓
Operational Review Rule
```

Do not collapse these into one field.

## Distillation over papers

The product keeps four things distinct:

* **Current review corpus:** all raw comments across papers
* **Current assignment state:** the latest accepted assignment of those comments
* **Current taxonomy:** the reviewer’s current map of recurring issues
* **Review knowledge:** the operationalized knowledge derived from that taxonomy

```
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
```

Make accumulation visible, for example: 184 comments across 7 papers; 12 recurring labels; 3 introduced this month; 2 merged after more evidence.

## Prompts

Prompts must distinguish what the reviewer observed from what the model infers:

```
Reviewer observation:
"I think 'demonstrate' is too strong."
Manuscript context:
"The experiment..."
Existing labels:
id, name, parent_id
...
Task:
Determine whether this observation is best explained by an
existing label. If so, recommend the best match.
If no existing label adequately captures the observation,
propose a candidate new label (parent_id of an existing
label, or omit for a root).
A new definition must state the manuscript pattern a reader
would see in the passage, not a class of comments.
Do not modify the taxonomy automatically.
```

## Human in the loop

The reviewer is the expert whose practice is being distilled. AI proposes; the human validates; the taxonomy changes; later proposals improve.

Human decisions are data. If the model proposed “Unsupported claim” and the reviewer chose “Overclaiming”, that disagreement can improve later suggestions.
