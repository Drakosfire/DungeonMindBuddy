# BUILD: save backups under the configured artifact data root

Status: ACTIVE — PRIME solo implementation; ARCHITECTURE independent review.

Base `af7cbebc44b737a41ae416d87960e8b71bc3ac6e`; branch `codex/build-backup-artifact-root`; non-serving checkout `/tmp/prime-recap-mention-boundaries`. Serial one PR. DOGFOOD's welcome UI lease is disjoint. Actual rendered Save in the private Mirathorn copy passed prepare but commit raised ValueError computing backup path relative to the code archive rather than configured artifact root. Source and registry remained revision2/unchanged; the disposable browser draft was discarded and owned preview original source roots restored. All21APP tables unchanged.

## Invariant / exclusive write set

File-backed Markdown commit resolves source and backup metadata against the same configured artifact root, including when code and data roots differ. Backup remains a sibling .backups file containing exact old bytes; registry/CAS/atomic-write/rollback and import semantics are unchanged. No new provider or publication behavior.

- `Docs/Plans/HANDOFF-BUILD-backup-artifact-root.md`
- `apps/live_control_server/services/tiptap_markdown_write.py`
- `tests/test_tiptap_markdown_write.py`

## Verification

Exercise actual live prepare/commit route functions with distinct code and configured data roots; save/reopen, exact backup path/content, data registry revision and untouched code root. Reproduce on exact accepted base; run writer/historical regressions and diff/Ruff. Commit/push/open one PR for ARCHITECTURE review before PRIME merge. No inference, serving changes, retained document/APP or World writes in implementation. Rendered copied-source acceptance resumes only from a newly pinned matched accepted deployment.
