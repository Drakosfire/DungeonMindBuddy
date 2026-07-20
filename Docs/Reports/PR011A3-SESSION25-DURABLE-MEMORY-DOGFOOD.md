# PR011A3 — Session 24 durable memory dogfood (Session 25 waived)

**Status:** `PARTIAL` — prepare+confirm published; projection integrity blocks UI reload  
**Terminal verdict:** `PARTIAL` (NOT ready for backfill)  
**Date/time:** 2026-07-18T10:11–11:35 America/Denver  
**Closeout / split:** promote-IR reconstituted on `agent/pr011a3-promote-ir-closeout` (from `#367` tip; do not merge fat tip)  
**Base SHA:** `37c0a79ddf323ec073e18a345d902162c330be61` (merge of GitHub PR #366)  
**Head SHA:** *(updated on push)*  
**GitHub PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/367  
**Closeout handoff:** `Docs/Plans/HANDOFF-pr011a3-closeout-live-acceptance-corpus-ui-readiness-gate.md`

## Operator waiver

```text
Session 25 source: WAIVED
Representative source: Campaign 2 Session 24 canonical recap / UI-produced graph-ingest run
Live publish approval for one Session 24 publish: yes (operator directed continuation 2026-07-18)
Post-pass operator intent (NOT executed by this agent):
  - ingest prior recaps
  - then worldbuilding docs
Hard-stop reminder: this agent must not start that backfill even if acceptance later passes.
Heterogeneous/worldbuilding readiness is a separate successor; recap proof must not unlock it.
```

## Environment

```text
date/time: 2026-07-18
base SHA: 37c0a79ddf323ec073e18a345d902162c330be61
server: 127.0.0.1:8000 (uvicorn) + UI 127.0.0.1:5173
world graph root: out/ → out/graph_memory/worlds/eldyrwild/
campaign: longmont-c2
session: session-24 (waived representative)
operator: directed Session 24 waiver + continue acceptance
```

## Preflight

```text
old revision: rev:5cadc9798562862cdde22350d8a3b56c
target source: Session 24 (waived); corpus file present:
  corpus/.../Session Recaps/Session 24 - Mireward Gate Battle.md
target runs (promotable registry):
  graph-ingest:longmont-c2:session-24:20260713T182027Z  (preferred; preview_union_store_ready)
  graph-ingest:longmont-c2:session-24:20260713T181901Z
  graph-ingest:longmont-c2:session-24:20260629T035803Z  (also fails scope on older candidate)
target object absent from head: n/a (prepare never produced selectable assertions)
operator approved one live publish: yes (Session 24 only)
```

## Stage 1 — Source / run binding

```text
UI action: resume existing server-owned Session 24 graph-ingest runs
  (originally under out/graph_memory/runs/longmont-c2/session-24/; no path injection)
source origin: Session 24 normalized recap artifact inside run
  (e.g. .../20260713T181934Z/normalized_recap_source.md)
run ID tried: graph-ingest:longmont-c2:session-24:20260713T182027Z
run status: preview_union_store_ready
candidate graph valid (registry health): true
preview store valid: true
promotable (registry flag): true
warnings: registry promotable=true but prepare rejects candidate SemanticState (see Stage 2)
```

## Typed SemanticState successor (2026-07-18) — operator-approved IR repair

```text
No runtime legacy adapter.
Forward fix: category extractor + staged_edge DEFAULT SemanticState are typed
  played_canon / candidate / source_evidence / system_derived / gm_private.
Registry/prepare parity: load_typed_candidate_graph fail-closed in
  promotable_ingest_run (aliases → not promotable).

One-shot disk rewrite (semantic_state only; out/ gitignored; not committed):
  11 live candidate_graph.json files under out/graph_memory/runs/
  longmont-c1 session-1 (3), session-2 (2)
  longmont-c2 session-23 (4), session-24 (2)
  Empty stubs (3) left unchanged.
  Eval/Mirathorn gold and evals/** left alone (no live worldbuilding registry runs).

Post-repair Session 24 prepare
  (runId graph-ingest:longmont-c2:session-24:20260713T182027Z):
  mapping_error: CLEARED
  new failure: HTTP 422 run_not_promotable —
    candidate graph failed typed parse: 'source_ref_id'
  Evidence refs on live extracts still use extractor-local
    {source_span_ref_id, anchor_quotes} without full EvidenceRef
    (source_ref_id / source_artifact_id / …).
  Head unchanged: rev:5cadc9798562862cdde22350d8a3b56c
  Confirm not attempted.

Follow-up (landed below): EvidenceRef stamp + live IR repair.
```

## Typed EvidenceRef successor (2026-07-18) — operator-approved IR repair

```text
No runtime prepare adapter.
Forward fix: assemble_envelope stamps promote-eligible EvidenceRef from span stubs
  (source_ref_id / source_artifact_id / can_open_source / can_highlight_span / …).
LLM schema unchanged: still emits {source_span_ref_id, anchor_quotes} only.

One-shot disk rewrite (evidence_refs only; out/ gitignored; not committed):
  11 live candidate_graph.json files under out/graph_memory/runs/
  1030 stub refs → full EvidenceRef (same set as SemanticState repair)
  Empty stubs (3) left unchanged.

Post-repair Session 24 prepare
  (runId graph-ingest:longmont-c2:session-24:20260713T182027Z / 181901Z):
  source_ref_id KeyError: CLEARED
  new failure: HTTP 422 run_not_promotable —
    CandidateEdge unexpected keyword argument 'predicate_family'
  Extractor edges still carry predicate_family; typed CandidateEdge IR rejects it.
  Head unchanged: rev:5cadc9798562862cdde22350d8a3b56c
  Confirm not attempted.

Follow-up (landed below): IR projection (predicate_family + promote-safe diagnostics).
```

## Promote IR projection successor (2026-07-18)

```text
Forward fix: project_candidate_graph_for_promote at assemble_envelope /
  canonical_graph_for_runner:
  - strip predicate_family / context_anchor from edges/nodes
  - emit PROMOTE_SAFE_PREVIEW_DIAGNOSTICS (dangerous flags false)
  - move extraction_mode/model_id to envelope review_sidecar
One-shot disk rewrite of 11 live candidates (project + EvidenceRef already present).
Session 24 typed load: PASS (both Jul13 runs).
```

## Stage 2 — Prepare / review (PASSED after IR projection)

```text
POST /api/live/extract-promote/prepare
  body: { schema: dmb_extract_promote_prepare_request_v2, runId: <above> }

Results (before SemanticState repair):
  20260713T182027Z → HTTP 409 mapping_error
  20260713T181901Z → HTTP 409 mapping_error
  20260629T035803Z → HTTP 422 run_scope_mismatch (missing campaign_id/session_id on candidate)

Results (after SemanticState repair on disk + extractor defaults PR):
  20260713T182027Z → HTTP 422 run_not_promotable (missing evidence source_ref_id)
  mapping_error: no longer observed on repaired Session 24 candidate

Results (after EvidenceRef stamp on disk + assemble_envelope stamp):
  20260713T182027Z → HTTP 422 run_not_promotable (predicate_family on CandidateEdge)
  20260713T181901Z → HTTP 422 run_not_promotable (predicate_family on CandidateEdge)
  source_ref_id / EvidenceRef incompleteness: no longer observed

Results (after promote IR projection + live rewrite):
  20260713T182027Z → HTTP 200 — proposalId proposal:a3517f38…;
    acceptedProposalsCount=59; unresolvedMentionsCount=1; rejectedAssertionsCount=1
  20260713T181901Z → HTTP 200 — proposalId proposal:ce12fad5…;
    acceptedProposalsCount=54
  parentRevisionId: rev:5cadc9798562862cdde22350d8a3b56c

proposal ID: proposal:a3517f38fba14ff886ffaef4e746b75c (preferred run)
selected assertion IDs: 59 (selectedByDefault)
```

## Stage 3 — Confirm (PASSED with degraded audit)

```text
POST /api/live/extract-promote/confirm
  schema: dmb_extract_promote_confirm_request_v2
  assertionIds: 59 selectedByDefault from prepare reviewItems
  reviewPackage: sealed from prepare (preferred run 182027Z)

HTTP 200
outcome: published_audit_degraded
headAdvanced: true
committedRevisionId: rev:dc988ccc2f37163da7d4de29ba276db2
parentRevisionId: rev:5cadc9798562862cdde22350d8a3b56c
appliedAssertionCount: 59
affectedObjectIds: 37 (includes pc:karsemine, pc:stafl, npc_lysandra, …)
warnings: post_publication_verification_failed / ValueError
auditStatus: degraded
```

## Stage 4 — Exact reload (PARTIAL)

```text
POST /api/live/world-graph/projection
  worldId=eldyrwild campaignId=longmont-c2 revisionPin=rev:dc988ccc…
  → HTTP 409 projection_integrity_error
  Active node assertions disagree on correction-sensitive semantics
  (pc:baergrom: competing fingerprints role/summary vs prior head)

Disk proof at committed revision (not preview-union):
  out/graph_memory/worlds/eldyrwild/revisions/rev:dc988ccc…/graph.json exists
  all 37 affectedObjectIds present in revision store nodes
  extract-promote/status head == committedRevisionId

UI revision-pinned projection open: BLOCKED by integrity conflict
Durable store presence: PASS
```

## Stage 5 — Restart durability (PASS for head/store)

```text
Re-read extract-promote/status → head still rev:dc988ccc…
Revision graph.json still present; 37/37 affected IDs still resolvable in store
Hermes write: not in scope (PR011B)
Hermes/UI projection read: blocked by same integrity error until identity conflict resolved
```

## Publication / Reload / Retrieval

```text
outcome: published_audit_degraded (confirm HTTP 200; head advanced)
committed revision: rev:dc988ccc2f37163da7d4de29ba276db2
head advanced: yes (from rev:5cadc9798562862cdde22350d8a3b56c)
revision store: 37/37 affectedObjectIds present
projection API: 409 projection_integrity_error (pc:baergrom conflict)
browser reload / Hermes projection: blocked until integrity resolved
```

## Source-family readiness

| Source family                  | Current UI entry contract                | Proven in this PR? | Ready? | Reason |
| ------------------------------ | ---------------------------------------- | -----------------: | -----: | ------ |
| Canonical session recap        | Campaign + session + recap text/artifact |            Partial |     No | Prepare+confirm worked; projection integrity blocks UI reload; audit degraded |
| Campaign NPC/location/faction  | No declared general contract on base     |                 No |     No | General source artifact intake required |
| Session prep/plot artifact     | No declared general contract on base     |                 No |     No | Scope and canon semantics required |
| Worldbuilding location/setting | No declared general contract on base     |                 No |     No | World-scoped source contract required |
| Statblock/mechanical artifact  | No declared general contract on base     |                 No |     No | Typed mechanical source/consumer contract required |
| Item/homebrew document         | No declared general contract on base     |                 No |     No | General source contract required |

## Terminal verdict

```text
PARTIAL — Stages 2–3 PASS; Stage 4 projection API FAIL; store durability PASS
blocking stage: Stage 4 exact UI/API projection reload
observed failure: projection_integrity_error on pc:baergrom competing assertions
  (confirm outcome published_audit_degraded; verification warning)
whether head advanced: yes → rev:dc988ccc2f37163da7d4de29ba276db2
whether source or preview artifacts changed: yes (IR projection repairs under out/)
safe retry / follow-up:
  1) resolve identity/semantic conflict for pc:baergrom (or suppress duplicate assert)
     so revision-pinned projection succeeds;
  2) then re-prove UI reload + optional Hermes read
required follow-up capability:
  World Graph projection integrity for overlapping PC identity on promote
NOT declared READY_FOR_CANONICAL_RECAP_BACKFILL (projection/UI reload incomplete)
```

```text
NOT_READY_FOR_CANONICAL_RECAP_BACKFILL
NOT_READY_FOR_HETEROGENEOUS_CORPUS_UI_INGESTION
```

## Hard-stop attestation

```text
No second source was ingested.
No corpus traversal was started.
No batch or queue was created.
No prior-recap backfill was started.
No worldbuilding ingest was started.
One Session 24 live confirm was executed under operator waiver.
Head advanced once: rev:5cadc979… → rev:dc988ccc…
The agent stopped after recording the readiness verdict (PARTIAL / not ready for backfill).
```

## Operator decision required (next)

```text
Choose one:
A) Authorize successor to fix projection integrity (pc:baergrom competing
   assertions) so revision-pinned UI reload succeeds, then declare readiness; or
B) Accept PARTIAL closeout (head advanced; store durable; UI projection blocked)
   and still keep backfill gated; or
C) Revert/investigate the degraded audit before any further live publishes.
```

## Split reconstruction note

```text
PR #367 retained as DO-NOT-MERGE tracking umbrella.
This report remains PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL.
Repair of a later head (rev:156f166…) is not forward proof that confirm
produces a directly reloadable committed revision.
Successor slices: existing-object observation, atomic multi-contribution,
C1 migration, Plan lens, graph reference UI, Author Node.
```
