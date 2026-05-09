# Plans archive

Historical plan, handoff, and report material lives under dated folders. **Canonical active** execution plans stay in `Docs/Plans/` root (for example `PLAN-split-corpus-retrieval-to-autonomous-demo.md` and `CHECKLIST-dynamic-lexical-retrieval-rollout.md`).

## Batches

| Folder | Contents |
| ------ | -------- |
| `2026-04-07/` | Phase 6 corpus-question handoffs (pre-archive convention). |
| `2026-05-09/` | Evidence-gap wave reports (Mirathorn council-room experiment series); superseded Mirathorn Cursor plan. See that folder’s `README.md`. |

When moving a file here, prefer:

1. **`git mv`** (preserve history).
2. A **stub** at the old path only when external bookmarks or tooling still expect the original filename (see Mirathorn plan stub in `Docs/Plans/`).
3. Update **in-repo** links in the same change when grep shows dependents.
