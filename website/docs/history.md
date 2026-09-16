# History

The **History** dialog (header, next to Settings and Export) lists taxonomy and assignment events you can **Undo** and **Redo**. A chevron on a row expands extra details when they exist: a plain-language explanation, the full text of affected comments, a saved definition, or names the list line does not already show. The dialog does not show payload JSON or ids.

Typical events: labeling a comment, Label with AI, fork/split, Verify / Unverify / Delete, nesting or merging a label, flattening or removing a subtree, renaming, grouping unlabeled comments onto `ungrouped`. Undo of Label with AI or fork restores the comments to unlabeled and dismisses the assignment snackbar. No-op moves are not logged.

Use this when a suggestion or a drag-and-drop went to the wrong label. Extract-driven revisions of comment text are source updates, not history undos.

API: `GET /api/history` (each event includes `summary` and `details`), `POST /api/history/undo`, `POST /api/history/redo`. The product spec in the repository has the full event table.
