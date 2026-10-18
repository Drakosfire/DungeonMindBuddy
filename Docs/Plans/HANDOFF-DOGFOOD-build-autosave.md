# DOGFOOD: durable Build autosave

Status: ACTIVE — bounded implementation lease, 2026-10-18.

Branch: `codex/build-autosave`.

Base: `origin/main@e1223408a4210db40cd92f33720f0e202fd1835d`. The local Git
metadata mount prevents fetch; GitHub comparison confirms the two commits after
the prior base contain only Plan paths, with no Build write-set overlap.

Topology: serial, one PR. PRIME retains merge and serving-runtime authority;
ARCHITECTURE reviews the exact cumulative implementation head.

## Mission

Make ordinary edits to an already loaded Build worldbuilding source durable
through a short, debounced autosave that uses the shared Markdown Canvas save
command and its existing compare-and-swap/verification boundary. Reuse
`DurableSaveStatus` and show the server timestamp only when the accepted
snapshot still matches the active document and revision. Build remains directly
editable; no Read/Edit gate is introduced.

The autosave must be quiet for a clean page and must never create or save merely
because an empty surface was opened. It must not save during loading, a document
switch, a conflict, a save/recovery guard, or another document command. If text
changes during an in-flight save, the existing authoring state remains dirty and
the debounce schedules a later write after the first command settles. Failures
remain visible and do not trigger an automatic retry loop; a later edit or the
existing explicit Save action can retry.

This is a Build-only client behavior slice. It does not change shared authoring,
Plan, Play, Ingest, Graph, server, database, schema, publication, ingestion, or
runtime configuration.

## Authority and supersession

PRIME assigned and authorized this bounded Build successor after Build
Autosave PR #1416 merged as `4958acdb0a2d7592558985e6c86c40da2a29c763`.
That Plan lease is ended; the merged Plan implementation is historical
predecessor evidence. Its settled reusable `DurableSaveStatus` is read-only in
this slice.

PRIME explicitly superseded conflicting ACTIVE path reservations from
`HANDOFF-BUILD-welcoming-authoring`, `HANDOFF-MEDIA-floating-studio`,
`HANDOFF-DOGFOOD-build-extraction-navbar`, and
`HANDOFF-DOGFOOD-mirathorn-build-presentation` only for the paths listed below.
Their old refs and unmerged work remain preserved and are not merged, rebased,
or otherwise modified by this slice. The ACTIVE protected-page lease remains
untouched: shared `useWorkspaceDocumentAuthoring` paths are excluded.

PRIME subsequently amended this same lease to transfer the two
`BuildSurfaceContext` paths from the stale extraction-navbar reservation so
the durable-save presenter can live in the Build surface navbar.

## Exclusive write set

- `Docs/Plans/HANDOFF-DOGFOOD-build-autosave.md`
- `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx`
- `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`
- `apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx`
- `apps/live-control-ui/src/buildSurface/BuildSurfaceContext.test.tsx`
- `apps/live-control-ui/src/buildSurface/useBuildAutosave.ts`
- `apps/live-control-ui/src/buildSurface/useBuildAutosave.test.tsx`
- `apps/live-control-ui/src/buildSurface/buildAutosave.css`

Reuse `apps/live-control-ui/src/components/DurableSaveStatus.tsx` as read-only.
Do not edit `BuildSurfaceContext`, `useBuildWorkspaceDocumentController`,
`useWorkspaceDocumentAuthoring`, global CSS, or any paths not listed above.

## Invariants

- Autosave only after an authored dirty edit on the currently accepted
  `worldbuilding_source` record, with matching active document ID, document
  key, editor instance, snapshot record ID, and loaded/snapshot revision.
- Debounce for 800 ms. Any session or document switch cancels the previous
  timer. Revalidate the exact identity and save guards immediately before
  invoking `session.saveMarkdown()`.
- Keep all writes behind the shared `MarkdownCanvasSession` command and its
  existing CAS, verification, recovery, and document-change fencing. No direct
  API writes or alternate persistence path.
- Never autosave a clean source, an empty landing, a protected/lossy source, a
  conflict, an error state, or while any document command is active.
- After failure, show attention and wait for a later edit or explicit retry;
  do not create a rapid retry loop.
- Derive the displayed durable timestamp exclusively from the current
  `snapshot.record.updated_at`, and only when snapshot identity and revision
  match the accepted record. Keep prior server time distinguishable while local
  edits are unsaved.
- No Graph publication, ingestion, conversation send, Play start, or runtime
  mutation.

## Verification

Run the owning autosave and Build shell tests, UI typecheck/build, and
`git diff --check`. Inspect the exact cumulative base-to-head diff. Record
inherited failures and any rendered/live-runtime limits honestly. Complete one
PR; do not merge it or move 5202 without separate authority.

## Implementation evidence

- The Build-only autosave hook debounces eligible dirty edits for 800 ms and
  calls `MarkdownCanvasSession.saveMarkdown()` after revalidating document ID,
  document key, editor identity, snapshot revision, authoring phase, and save
  guards. It does not write through a separate API path.
- The Build surface navbar reuses `DurableSaveStatus`. Its timestamp comes from
  the active snapshot record and is withheld when snapshot identity or revision
  no longer matches the active record. The floating Page authoring toolbar
  contains formatting and worldbuilding tools only.
- Focused verification: `useBuildAutosave.test.tsx` (7 passed) and
  `BuildSurfaceShell.test.tsx` (33 passed, 1 existing layout test skipped).
  The latter includes an integration check that waits through the debounce and
  types twice into the mounted editor, verifies that the quiet period restarts
  after the final editor transaction, then observes the shared prepare/commit
  boundary and verified server timestamp. The hook also verifies active-command
  blocking, document-switch cancellation, and that a clean draft stays distinct
  from a committed save and has no committed timestamp.
- `npm --prefix apps/live-control-ui run typecheck` passed.
- `npm --prefix apps/live-control-ui run build` passed; Vite emitted its
  existing large-chunk advisory.
- `git diff --check` passed.
- ARCHITECTURE review cycle 1 found two missing regressions: edits made during
  an unchanged dirty session did not restart the debounce, and a clean server
  draft was presented as saved. Both are corrected in the current head and now
  covered by mounted-editor and draft-status tests; review cycle 2 is pending.
- `git fetch origin main` and local branch mutation are unavailable because
  the checkout's shared `.git/worktrees` metadata is read-only. The GitHub API
  confirmed and created `codex/build-autosave` directly at exact main
  `4958acdb0a2d7592558985e6c86c40da2a29c763`; the locally available Build
  source paths were identical to that base before editing. The changes will be
  committed to that authorized remote branch and opened as one PR.

PRIME final navbar-placement ownership transferred after DOGFOOD freeze at01168919ab7e7d64302428569e8b18f30081eae5. Existing buddy-context-loop checkout branchcodex/build-autosave-navbar owns this final amendment. Eight-path allowlist includes BuildSurfaceContext.tsx/.test.tsx; only transferred tested deltas copied from frozen996b. Prior syntax-only test escaping corrected; no source export or new checkout.

## Final navbar amendment evidence

PRIME completed the frozen-owner navbar transfer: status is rendered in BuildSurfaceContext's existing surface status slot; no duplicate Page authoring status. Pure state presentation is shared, save orchestration remains mounted exactly once. Corrected literal escaped backticks in the new Context test and restricted the duplicate-label assertion to the visible status container (legacy hidden diagnostic remains).

47 focused hook/Shell/Context tests PASS, one inherited layout skip; React act warnings retained. Typecheck/final Vite build/diff check PASS (existing chunk advisory). Existing disposable Build31e6d747-a70a-4dc6-8b94-6f2f2c7ba05d was typed in without pressing Save, committed automatically at revision3/server17:15:27.579267Z, reopened with witness/original text retained and timestamp in banner. No real Edge edit, provider call or Graph publication. Independent final-head review pending before merge/delivery.
