# PR011A3 — Session 24 durable memory dogfood (Session 25 waived)

**Status:** `BLOCKED`  
**Terminal verdict:** `BLOCKED`  
**Date/time:** 2026-07-18T10:11–10:20 America/Denver  
**Closeout branch:** `agent/pr011a3-closeout-corpus-ui-readiness`  
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

Follow-up (not this PR): align live evidence_refs with CandidateGraphPreview
  EvidenceRef IR (or a documented promote-path materializer), then resume
  Session 24 closeout acceptance.
```

## Stage 2 — Prepare / review (FAILED)

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

proposal ID: n/a
selected assertion IDs: n/a
```

## Publication / Reload / Retrieval

```text
outcome: n/a — confirm not attempted
committed revision: n/a
head advanced: no (still rev:5cadc9798562862cdde22350d8a3b56c)
browser reload / server restart / Hermes: n/a
```

## Source-family readiness

| Source family                  | Current UI entry contract                | Proven in this PR? | Ready? | Reason |
| ------------------------------ | ---------------------------------------- | -----------------: | -----: | ------ |
| Canonical session recap        | Campaign + session + recap text/artifact |                 No |     No | SemanticState fixed; prepare still blocked on EvidenceRef `source_ref_id` |
| Campaign NPC/location/faction  | No declared general contract on base     |                 No |     No | General source artifact intake required |
| Session prep/plot artifact     | No declared general contract on base     |                 No |     No | Scope and canon semantics required |
| Worldbuilding location/setting | No declared general contract on base     |                 No |     No | World-scoped source contract required |
| Statblock/mechanical artifact  | No declared general contract on base     |                 No |     No | Typed mechanical source/consumer contract required |
| Item/homebrew document         | No declared general contract on base     |                 No |     No | General source contract required |

## Terminal verdict

```text
BLOCKED
blocking stage: Stage 2 prepare (after Session 25 → Session 24 waiver)
observed failure: mapping_error — extractor semantic_state aliases on all current Session 24 promotable runs
whether head advanced: no
whether source or preview artifacts changed: no
safe retry condition:
  1) land successor that emits typed promote-eligible SemanticState from recap extraction;
  2) produce one fresh Session 24 UI/run (or re-extract) under that contract;
  3) re-run prepare → review → confirm → reload → Hermes on the same closeout invariant
required follow-up capability:
  Align category extractor SemanticState with CandidateGraphPreview + promote matrix
  (Backlog READY entry; not implemented in this closeout)
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
No extractor/promote semantics rewrite was shipped in this closeout.
No World Graph confirm/publish was attempted.
Head unchanged: rev:5cadc9798562862cdde22350d8a3b56c
The agent stopped after recording the readiness verdict (BLOCKED).
```

## Operator decision required (next)

```text
Choose one:
A) Authorize a successor PR (outside this closeout allowlist) to align the category
   extractor DEFAULT_SEMANTIC_STATE with typed promote-eligible SemanticState, then
   re-dispatch Session 24 closeout acceptance; or
B) Defer acceptance; keep PR011B and backfill blocked; or
C) Provide a different already-typed promote-eligible Session 24 candidate produced
   without hand-editing (e.g. gold-grade IR from an approved pipeline) — rare.
```
