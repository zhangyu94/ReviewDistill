# Workflow

Init a paper, proofread with the same macros you already use, extract, label in the UI, then reuse the taxonomy on the next paper.

## Init

```sh
reviewdistill init --name paper-01 --command myremark
```

That writes `.reviewdistill/config.yaml` in the paper repo:

```yaml
project:
  name: paper-01
comments:
  latex_commands:
    - myremark
```

`--command` is repeatable (`myremark`, `note`, `review`). The extractor treats those names as markers, not as labels. Nothing assumes `\myremark`.

## Proofread

Keep annotating the `.tex` file:

```latex
The results demonstrate that ...
\myremark{I think "demonstrate" is too strong here. The experiment only provides evidence for this claim.}
```

Another paper might use `\note{This paragraph does not explain why this design decision was necessary.}`.

## Extract

```sh
reviewdistill extract
```

Each hit stores comment text, file, line, command name, manuscript neighborhood, section, Git commit, and related context. Pairing (new, revision, move, gone) is [`comment-identity.md`](comment-identity.md).

## Label with AI

In `reviewdistill ui`, **Label with AI** is in the Comments header whenever unlabeled comments still need proposals (even if the Unlabeled chip is off). A thin progress bar at the top of the window runs until the batch finishes.

The batch **accept-assigns** those comments; new names are created immediately. Selectors do not change. If Unlabeled is on, that list may empty; the snackbar and tree counts are how you find the work. A dismissible snackbar says they appear in Label Taxonomy. A failed retry leaves a previous snackbar in place. If the UI cannot reach the ReviewDistill server, that snackbar says so in plain language. **Accept** remains for leftover stored proposals.

For each observation the model sees the raw comment, manuscript context, existing labels, similar comments, and examples. It may recommend an existing leaf or a new name with a definition. A leftover stored proposal stays until Accept or a label is picked in the menu.

**Label with AI**, header fork, and leaf fork accept-assign in the same batch; they do not leave new proposals. Selecting a label assigns it; there is no Change button. The menu shows the current label when the comment is labeled. Label with AI does not have to be clicked again this session.

An existing-label id that is not in the active taxonomy is treated as a new name when the model also sent one. A new recommendation without `proposed_label_name` is **No AI suggestion**, is not stored, and stays in the Label with AI queue. An accepted assignment on an inactive label is unlabeled and stays in that queue too.

## Settings and data folder

Header **Settings** (next to History and Export) has two panels. Opening Settings always lands on Assistant. **Configure LLM** in the Unlabeled empty state opens the same dialog.

**Assistant** writes `llm.provider` / `llm.model` to the ReviewDistill home `config.yaml` and the matching API key to that folder’s `.env` (gitignored). `GET /api/llm-settings` returns the saved key (`api_key`) so Settings can show it (password + show/hide). It reads home files only (not `REVIEWDISTILL_LLM_*`). File editing still works.

Label with AI is store-wide, so leftover paper `llm:` / `.env` are ignored. Process environment still wins over `.env`. `REVIEWDISTILL_LLM_PROVIDER` / `REVIEWDISTILL_LLM_MODEL` override home YAML at run time. Do not write `llm.api_key` into YAML; do not store keys in the JSONL store.

Fields: Provider (DeepSeek / OpenAI / Anthropic), Model (filled with that provider’s default), API key (password + show/hide, filled from home `.env` when set). There is no paper picker. Save is disabled until a provider is chosen. An empty key field on Save keeps the existing `.env` value. `POST /api/llm-settings` with `api_key` omitted or `""` means keep; unknown provider 400; new provider with no key 400. This dialog does not probe the key live or offer mock / Ollama / custom base URL.

**Data** shows the home folder (same as `reviewdistill paths`) in an editable field, or **Choose…** to pick a folder. **Save** is `paths use` (points at that folder, does not copy files). **Open folder** reveals it in the file manager. Backup and `paths move` are in that folder’s `README.md`.

`reviewdistill paths use DIR` persists `DIR` in `~/.config/reviewdistill/home`. `reviewdistill paths move DIR` copies the current home (JSONL files, `config.yaml`, `.env`) into an empty `DIR`, then uses it; it leaves the old folder in place and refuses if the store is busy.

## Validate

The reviewer sees Label Taxonomy, Label Details, and Comments. Assign from the row menu or by dragging onto a leaf. **Verify** stamps the observation; **Delete** removes a bad extract.

```
Comment
"This paragraph does not explain why this design
decision was necessary."
Context
"We designed the interface using ..."
Assign label
New: Insufficient methodological justification  Why?  [Accept]
[Choose a label… ▾]
Triage
[lock Verify] [bin Delete]
Location
file, line, heading
```

## Accumulate

After several papers the taxonomy has counts per label (for example Overclaiming 17, Missing methodological justification 9). Later Label with AI and retrieval use those examples.
