# Plan presentation persistence in Content

Status: ACTIVE for the Content-owner prerequisite. This serial slice starts from
`774aa06344eb0a9411855eccdc7e33e7fead89c4` on
`codex/plan-presentation-content`, in the existing isolated Plan lane.

The ordinary plain-Plan feature merged in #4264. Its composed-page successor
needs a durable basis before normal Send can target a row slot. Current Plan
prepare and commit reject presentation, and current Plan editing stores only
Markdown and title. The existing presentation relation references a
`WorkRevision` and can carry a checked `PagePresentationV1` for a World-owned
Plan without changing its representation.

## Scope and authority

The user has delegated routine implementation and review for this lane. This
slice owns only the internal Content transaction, typed snapshots and tests, and
the predecessor handoff status and verification selector expectation. The
current hosted-authorization integration draft #3824 overlaps the Plan editor
and Markdown Save router. Its active two-path scope is recorded in
[the registered World fixture handoff](HANDOFF-BUDDY-v9-registered-world-fixture.md).
The later assignment must reconcile the exact integration diff and preserve
hosted authorization. Plan Snapshot HTTP types, editor activation, the
successor reader fence, and nested agent placement belong to later assignments.

Expected write set:

- `src/application_state/content/service.py`
- `src/application_state/content/types.py`
- `src/application_state/content/page_presentation.py`
- `tests/application_state/test_authored_pages_postgres.py` for shared revision
  presentation storage coverage
- `tests/test_ownership_ci_partition.py` for the exact four already-admitted
  ordinary Plan selectors added by merged #4264
- This handoff and the finished plain-Plan handoff

Use the lane's locked Python environment and an owned disposable PostgreSQL
cluster. Run exact-source tests for the Content mutation and snapshot owners,
including existing authored Page and Plan regression coverage. The existing
table and reader fence migration remain the deployed schema contract.

## Invariant

Admit a sidecar only for an active World-owned Plan and its exact CAS basis.
Markdown, revision and presentation commit atomically. A layout-only change has
its own revision. A retry succeeds only if the same Markdown, title and
presentation already landed. A failed write, stale draft, wrong World or
omitted/null presentation on an enrolled Plan leaves the current revision and
stable identities intact. An explicit projection to identity-only presentation
retains those identities. Legacy Markdown-only autosave and the in-transaction
agent-confirm writer must refuse an enrolled Plan before destructive mutation.
Cold reads join presentation to the exact Markdown revision rather than a
divergent working copy.

Required disposable evidence includes layout-only Save, edited Markdown with
stable existing IDs, omitted/null and foreign/stale refusals, lost-ack replay,
transaction rollback, ordinary sidecar-free compatibility and cold snapshot
readback. The public Plan Save route continues to refuse presentation until the
separately governed wire/editor and reader-fence slice can verify ordinary Save,
Undo/Redo and a real cold browser reopen. Inside-slot agent targeting follows
that slice.
