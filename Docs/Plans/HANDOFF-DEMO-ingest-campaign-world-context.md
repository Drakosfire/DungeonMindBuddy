---
title: Separate source campaign and selected World in Ingest
document_class: implementation_handoff
status: ACTIVE
created_at: "2026-10-07"
workstream: DEMO
pr_topology: serial
implementation_branch: codex/demo-ingest-world-scope
base_ref: 3026f21bfff0c293159e3f5fe5f3ff328b15bcf5
---

# HANDOFF — DEMO: separate campaign and World scope in Ingest

**Status:** ACTIVE — PRIME authorized this bounded Buddy caller correction.
**Owner:** DEMO. PRIME owns independent review and merge coordination.
**Base:** current Buddy `main@3026f21bfff0c293159e3f5fe5f3ff328b15bcf5`, after
PR #998 merged.
**Branch:** `codex/demo-ingest-world-scope`.
**Topology:** serial, one implementation PR.

## User outcome and contract

On Ingest, a verified selected managed World is accepted when the server-resolved
Plan view names that exact `world_id`, even when its `campaign_id` context differs.
Do not treat a campaign identifier as the publication World identity.

Use the existing `getPlanView(managedWorldId)` resolution. Require
`response.world_id === managedWorldId`; reject a missing or foreign `world_id`
before mounting Graph Review. Do not compare `response.campaign_id` to the
selected World. The source/run `campaign_id` remains source scope and is displayed
separately in read-only recap review.

Retain the existing source and target guards:

- Ingest requires a verified managed selection before reading context.
- A non-recap Extraction Run whose `campaign_id` does not match the selected
  World is rejected before Graph Review.
- A recap Run keeps its own source artifact, campaign and session identity in
  read-only source review; selecting a World does not associate or import it.
- The existing graph projection continues to require exact campaign/session,
  selected `world_id`, verified revision pins and the shared projection
  integrity check.
- SERVER #980 remains authoritative for prepare/confirm: it validates the
  source-declared-World constraint and the captured selected managed/native
  binding. This caller change does not weaken or replace those checks.

## Failure cases

1. Legacy, loading or failed World selection performs no plan/run reads.
2. A Plan view with missing or foreign `world_id` shows an actionable error and
   does not mount Graph Review, even if `campaign_id` equals the selected ID.
3. An exact managed World response is accepted when `campaign_id` differs; this
   includes the source campaign `longmont-c2` with selected World `elderwyld`.
4. A foreign non-recap Run remains rejected when its source campaign differs
   from the selected World.
5. Recap source review keeps source identity distinct from the selected target
   and never claims association or publication.
6. Server rejection of a conflicting source-declared World or changed managed /
   native binding remains authoritative; no client-only identity permits a
   governed write.

## Exclusive write lease

Modify only:

- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-ingest-campaign-world-context.md`
- `Docs/Plans/HANDOFF-DEMO-selected-world-recap-prepare.md` — truthful #985
  settlement only

No server route/schema, AppState contract, plan projection service, graph
projection, native World, source candidate, corpus, provider, Agent conversation
or dock, or database path is leased. No runtime port or mutable external state
is used. If another path is required, stop for an explicit owner transfer.

`Docs/Roadmaps/ROADMAP-demo.md` is not in this lease. Open PR #979 still carries
an older roadmap diff even though PRIME transferred that path to #985, which has
merged. PRIME has been asked to confirm whether the roadmap may be synchronized
in this PR or should wait until #979 reconciles its superseded hunk. This handoff
does not grant permission to edit that path.

## Re-anchor and collision record

- GitHub main is `3026f21bfff0c293159e3f5fe5f3ff328b15bcf5`. PR #985 merged at
  `c49bde2fb91a5e7722f4332c1792e3267cf337cd`; its ten-path selected-target
  caller lease is closed. PR #1000 changes Plan conversation/dock paths only.
  PR #998 subsequently added only its Server operator handoff; the exact
  `bcb6f595..3026f21b` comparison contains that one added handoff and no leased
  path. Those paths are outside this lease.
- The exact current-main GitHub blobs for the leased page and test are
  `c02d1449c826f4a85749e78f89a168ef8fd3b957` and
  `9fd48aec0c1be930b8dcdba0d3b2d306a29966a3`. Local verification uses the
  available `e1c85fdf1ca0e8c66d0234bf92d8fff60d197d3c` checkout because network
  fetch is unavailable; both leased input blobs match current main byte for
  byte. GitHub's `e1c85fdf..bcb6f595` comparison contains only #1000's 20
  Agent/Plan dock files, none in this lease; `bcb6f595..3026f21b` contains only
  #998's Server handoff.
- Open #979 includes Agent conversation paths and its superseded roadmap hunk;
  it does not edit the leased Ingest caller or test. #917 edits Agent/Plan
  paths, #998 edits only its Server handoff, and #939 is APP-STATE attribution.
  No open PR has a writer on this slice's code/test paths.
- The #985 handoff's World context path list did not include
  `SelectedWorldMemoryIngestPage.tsx`; no path transfer into this slice is
  assumed. The new caller lease stays limited to the two Ingest files above.

## Owning-boundary acceptance

Run the mounted `MemoryIngestPage` suite. It must prove both sides of the
identity rule: an exact selected `world_id` with a distinct campaign context is
accepted, while a foreign/missing `world_id` and a foreign non-recap Run remain
blocked before Graph Review. Preserve the recap read-only source review, no-World
no-read checks, and stale-load fencing. Run the production UI build or typecheck,
`git diff --check`, and inspect the exact cumulative base-to-head diff for this
four-path lease.

No runtime/provider request, recap prepare, confirm, source mutation, AppState
write, or native Graph write is part of this slice. The change is a Buddy caller
correction and does not establish recap publication, rollout or J1 acceptance.
