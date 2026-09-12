# History

The **History** page lists taxonomy and coding events you can **Undo** and **Redo**.

Typical events: labeling a comment, Verify / Drop, nesting or merging a type, flattening or removing a subtree, renaming, deactivating. No-op moves are not logged.

Use this when a suggestion or a drag-and-drop went to the wrong type. Extract-driven revisions of comment text are source updates, not history undos.

API: `GET /api/history`, `POST /api/history/undo`, `POST /api/history/redo`. The product spec in the repository has the full event table.
