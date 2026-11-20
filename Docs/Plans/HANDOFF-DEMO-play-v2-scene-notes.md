---
title: Autosave durable scene notes in World-owned V2 Play
document_class: implementation_handoff
status: ACTIVE
created_at: "2026-10-07"
workstream: DEMO
pr_topology: serial
implementation_branch: codex/demo-play-v2-scene-notes
base_ref: be48c3c846e2ba8f51330ccc1cf41b38c35f8680
---

# HANDOFF — DEMO: autosave durable scene notes in World-owned V2 Play

**Status:** ACTIVE — PRIME authorized this bounded Buddy product slice.
**Owner:** DEMO. PRIME owns independent review and merge coordination.
**Base:** Buddy `main@be48c3c846e2ba8f51330ccc1cf41b38c35f8680`, after #1002 merged.
**Branch:** `codex/demo-play-v2-scene-notes`.
**Topology:** serial, one implementation PR.

## User outcome and contract

A GM running an actual marker-v2 Scene in a World-owned Play Run can jot a
visible Scene note in the Current Moment cockpit. The note autosaves into the
existing Run progress and visibly acknowledges only an exact successful save.
The existing progress snapshot remains the canonical saved note;
`notes_by_element_id` is current scratch text, not a journal.

This slice is limited to World-owned `dmb_world_play_run_record_v2` Runs in the
marker-v2 cockpit. The note key is the exact Scene element ID. The browser-local
recovery cache is versioned and scoped by verified `world_id`, exact `run_id`,
`scene_id`/note element ID, and the Run's exact pinned Playable identity.
Campaign-owned V1 Runs remain unchanged.

Use the existing single fenced full-progress writer and its
`expected_run_revision` CAS through `putWorldPlayRunProgress`. Preserve every
unrelated progress field. Never optimistically update canonical Run state.
Keep edits made during an in-flight request; after the exact request succeeds,
rebase the newer draft on that returned Run and autosave it as a separate edit.
A save acknowledgment requires matching World/Run/playable identity, an
advanced Run revision, and the exact submitted Scene note value.

On conflict, unknown outcome, rejected write, or mismatched success receipt,
keep the draft visible and do not automatically retry. An exact Run reread may
update authoritative state, but does not itself acknowledge a failed request.
The user can explicitly retry only after a current exact Run is available.

In-app navigation and a same-browser reload recover the exact scoped local
draft. The cache records the base note including absent-versus-empty, observed
Run revision, draft text, write state, and an immutable sent snapshot/request
identity where a write was attempted. A cache restore is always visibly
unsaved and never auto-sends or acknowledges a write. Only a matching successful
server response clears its exact sent snapshot; newer edits remain drafts.
Stale Playable bindings do not restore into the current Run. Corrupt or
unavailable storage leaves the in-memory editor usable and shows a warning.
Browser profile loss or user-cleared storage is outside the recovery guarantee.
Server Run progress remains the canonical saved note.

## Failure cases

1. A V1 or campaign-owned Run, missing current Scene, or incoherent Scene
   projection does not expose a World Scene note editor.
2. A note edit is local draft state until a matching successful World progress
   response arrives; no optimistic canonical note is shown.
3. A successful response with the wrong World, Run, playable identity, revision,
   or note text leaves the draft unsaved.
4. A user edit during an in-flight save is retained, based on the exact accepted
   response, and sent only after that response settles.
5. A newer server note suspends autosave and requires explicit review before the
   local draft can replace it.
6. Other notes, selections, current Beat/Scene, and resolved Beats survive a
   note write in the full progress replacement.
7. 409 conflict, 422 rejection, transport/unknown outcome, and failed reread each
   preserve the local draft and make no automatic second PUT, including after reload.
8. Run, World, Scene, or pinned Playable changes never expose another binding's
   draft; returning to an exact scope restores it.
9. Missing, corrupt, wrong-version, or unavailable cache data never becomes a
   saved note and never prevents editing in memory.

## Exclusive write lease

Modify only:

- `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx`
- `apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-play-v2-scene-notes.md`
- `Docs/Plans/HANDOFF-PLAY-SURFACE-decision-interaction.md` — truthful #673 settlement only
- `Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit.md` — truthful BF3A/successor settlement only
- `Docs/Plans/HANDOFF-DEMO-ingest-campaign-world-context.md` — truthful #1001 settlement only

No CSS change; reuse `.play-notes`. No `PlaySurfacePage`, runbook table deck,
Agent, Plan, server route/service, AppState, schema/database, manifest, grammar,
World, provider, API contract, second writer, multi-action decision, or shared
runtime change. Local storage is a scoped recovery cache, never the durable
authority. No ports, service starts, database writes, provider calls, or shared
runtime state are needed. If another path or contract change becomes necessary,
stop and request a steward/owner transfer before editing it.

## Re-anchor and collision record

- Re-fetched remote `main` at `be48c3c846e2ba8f51330ccc1cf41b38c35f8680`;
  #1002 is the only commit after the #1001 merge base and changes Agent turn
  routes/service/tests only.
- The current open PR search returned #1003, #979, #939, #927, #922, #917,
  #887 and older independent work; none leases the two Current Moment paths.
  #1003 owns server source-read receipt work; #979 owns
  Plan conversation and the DEMO roadmap hunk. #917 and #887 remain prototype evidence.
- The active DOGFOOD manual-note-retention lease owns the V1 Runbook table deck
  and its own handoff/tests. It excludes V2 cockpit notes and is untouched.
- No active PR, worktree, runtime, server, database, or output directory shares
  this slice's leased paths or external state.

## Owning-boundary acceptance

The mounted `PlayCurrentMomentCockpit` suite must prove the actual World-owned
marker-v2 route, exact CAS payload, autosave acknowledgment, per-World/Run/Scene
and Playable binding, reload/no-bleed recovery, absent-versus-empty draft, stale
binding quarantine, edits during in-flight saves, and all conflict/unknown/
rejection/no-replay cases. Verify exact successful response binding before
clearing a draft. Exercise storage corruption/unavailability and server-note
hydration. Retain existing decision, Run identity, and stale-completion tests.

Run the focused cockpit suite, relevant existing V2 Play route/service and
progress validation tests, frontend production build, and `git diff --check`.
Inspect the cumulative `base_ref..HEAD` diff and confirm it matches the six-path
lease above. Typecheck/build failures already present at
`ThreatPublicationPanel.tsx:553` must be reported as inherited if reproduced.

## Verification checkpoint

- Mounted cockpit suite: 52 passed. The production build passed; Vite reported
  a large-chunk advisory.
- The existing World Play route and progress validation suites passed 36/36
  serially: `tests/test_world_play_runs_v2.py` and
  `tests/test_play_run_progress.py`. The stable Python test environment used
  this lane's `src` on `PYTHONPATH` and PRIME's private DSN for the existing
  disposable PostgreSQL container. Per-test UUID databases were created and
  dropped; no database service was started. Pytest reported 11 Pydantic
  `schema`-field shadowing warnings.
- An initial run against the repository's stale default port 54329 failed at
  setup (35 errors and one test passed). PRIME supplied the current private
  test endpoint; the passing 36-test run above supersedes that environment
  failure. `uv run` itself could not resolve the local `out/hermes-agent`
  source in this worktree, so the installed test interpreter was used.
- The database-independent response/schema selection ran 19 tests successfully;
  one repository artifact check failed because the base checkout lacks
  `Docs/Plans/HANDOFF-s22-live-play-agent.md`. No code or tests in this slice
  touch that path.
- The World Play server route and note-anchor validation boundary is verified
  by the passing existing suites. No server/API/schema code changed; the exact
  World writer and validation contract remain owned by the existing backend.

No server/schema/API code changes are proposed. The existing owning server
contract remains the durable source of acknowledged note state; browser recovery
is limited to the local cache contract above.

## Predecessor settlement carried by this PR

- DEMO Ingest caller correction PR #1001: accepted head
  `73ad21e00e335f68c66f3d345b84ed2dfcd6fd26`; merged as
  `b06040f16e95da8411d0a93d19710285a84e6236`.
- PLAY-SURFACE BF3A cockpit PR #655: accepted head
  `3d5925c8ad1bdbe934020e1c4cd7f2f3fafbbec7`; merged as
  `4d82f12ad9c6d679b5dbce83db527eb7dbd27957`.
- PLAY-SURFACE BF3B Decision interaction PR #673: accepted head
  `111d68160b074335058c6ad12f77a7499665bb7e`; merged as
  `24f7c25b49fdab8271b0d84d36e4a609b9832d69`. The report records three formal
  review cycles. This consuming PR records backward-looking settlements;
  no status-only PR is needed.

This records only completed predecessors. It does not claim this in-flight
scene-note slice, any unsaved-draft reload capability, or operator acceptance
as complete.
