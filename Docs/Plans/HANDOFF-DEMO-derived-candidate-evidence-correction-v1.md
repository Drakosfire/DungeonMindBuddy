---
pr_body_template: |
  ## Handoff pointer
  * Workstream: DEMO / Of Conks J1
  * Handoff: Docs/Plans/HANDOFF-DEMO-derived-candidate-evidence-correction-v1.md
  * Mission: derive one strictly qualified candidate from explicit literal evidence corrections without changing its parent
---

# HANDOFF — DEMO: derive a qualified candidate from reviewed evidence corrections

**Created:** 2026-09-27
**Status:** ACTIVE — #777 merged and state authority synchronized; no predecessor gate
**Flow / owner:** DEMO / Buddy extraction-review and candidate-run boundary
**PR topology:** serial; one assigned implementation PR; no dependent PR before merge and state sync
**Base:** Buddy `main@076047e241ad1ac665083806ea9578ed6ec1e547`
**Review authority:** PRIME exact-head review, then steward merge under the user's explicit authority
**Runtime/state ownership:** the disposable Of Conks witness only; isolate any test databases, ports and output roots. C1/C2 and the earlier Of Conks ghost run are excluded.

| Field | Contract |
|---|---|
| Runtime/state ownership | Fresh Of Conks witness World `of-conks-j1-fresh-rehearsal`, its APP-STATE pair, and isolated tests; no write to C1/C2 or the ghost run. |

## §1 Mission and invariant

The exact Of Conks source is durable and the frozen extraction run is now
inspectable (#777), but its candidate has three nonliteral anchor quotes.
Strict publication correctly rejects the entire candidate. There is no
accepted product path to correct those quotes on a frozen run.

**One merge-ready invariant:** A GM can explicitly replace only flagged
nonliteral anchor quotes with text that occurs in the exact pinned paragraph,
creating a new immutable, fully qualified child ExtractionRun. The parent
run, source, span index and candidate bytes remain unchanged. Prepare and
confirm use the child run's server-owned component digest and the existing
strict publication path. This slice does not publish a World revision.

The child is a derived candidate, not a rewrite or silent model repair.
The UI must display its parent identity and navigate to the child after seal.
The source is licensed local material; never commit it or candidate-derived
copyrighted prose into Git fixtures.

## §2 Exact authority and predecessor sync

- Parent run: `124b2191-a493-40d5-a915-c9170848cc67`, `reviewable`.
- Parent source document: `a775e748-b9f7-4d7e-b03d-abffcc62223d`, revision 2,
  48,778 bytes, SHA-256 `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`.
- Parent candidate SHA-256:
  `3f945649d4b2830accd3d53ecab999ae0f5a703a5bd46e2c78b7eed153b7cab7`.
- Three affected assertions: `npc_torbin_jove`,
  `faction_baldurs_gate_mages_guild`, `edge_22`; all other quote refs are valid.
- #777 merged at `89a3065074b3e911bc73ca84820b647fc9927057` after one
  formal review cycle; handoff and both roadmap copies synchronized at
  `076047e2`. No predecessor state sync remains for this implementation PR.
- #777's review projection is inspection authority, not publish authority.
  The strict `_assert_and_project_candidate_evidence` path remains the final
  gate for every child and for prepare/confirm.

## §3 Behavior contract

| Case | Required outcome |
|---|---|
| Parent inspection | Review package identifies each invalid quote and the exact canonical paragraph; parent remains inspectable and unpublishable. |
| Explicit correction | Request names parent run, expected parent candidate SHA, assertion ID, evidence ref/index, original quote/index, and operator-selected replacement. No browser-supplied path or candidate JSON. |
| Scope of edit | Server changes exactly the named `anchor_quotes` values in a deep copy. Every other candidate field and list order is byte-semantically unchanged. Duplicate quote/index ambiguity, missing target, stale original, stale digest, or extra changed field fails closed. |
| Literal witness | Each replacement must occur in its exact pinned span paragraph under the existing anchor matcher. A replacement from a nearby paragraph, a paraphrase, blank text, or unchanged invalid quote fails. |
| Complete qualification | After all replacements, strict validation of the entire candidate must pass. Partial correction cannot produce a reviewable child. Unsupported structure/identity remains subject to the existing admission gates. |
| Child identity | New canonical ExtractionRun with its own immutable candidate component and digest; reused verified source and span-index component refs; durable lineage includes parent run ID, parent candidate SHA and deterministic correction digest. Parent status and bytes do not change. Do not use `supersede_extraction_run`. |
| Failure atomicity | Create a draft child first; write its candidate under a child-owned output path, strict-validate and advance through legal lifecycle states to `reviewable`. A crash before final seal leaves no reviewable child. Any orphan/draft is never a promotable fallback. |
| Retry | Identical correction payload on the same parent resolves to the same child identity/result; a conflicting payload under that identity fails closed. Concurrent retries cannot produce two reviewable children for one exact correction digest. |
| Prepare/confirm | The returned child `runId` is the sole browser-facing selector. Existing server resolution and immutable component SHA checks are reused. Tampering with child bytes or source/index blocks review, prepare and confirm. No second browser-supplied candidate digest/path becomes authority. |
| Product UI | Flagged quote editor offers the canonical paragraph as reference, requires a deliberate replacement, shows pending corrections, and submits once. On success open the child run; do not relabel the parent as valid. Publish remains disabled for incomplete/invalid parent or child. |
| No mutation | Correction itself makes zero DungeonMind World writes and zero model calls. Only a later, separate governed confirm could create a World head. |

The child must retain the parent's source-domain/profile/world binding. A child
with a newly invented campaign/session/World or changed non-evidence semantics
is invalid. The implementation may use canonical serialized correction content
to derive an idempotent child ID; it must not expose that storage path as an
API parameter.

## §4 Write lease / bounded discovery

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/exact_run_evidence_correction.py` | Child derivation, strict validation, lifecycle/idempotency. |
| Modify | `apps/live_control_server/services/extract_promote.py` | Reuse strict evidence validator and child review projection only. |
| Modify | `apps/live_control_server/services/graph_run_registry.py` | If needed, accept a server-determined child run ID with fail-closed duplicate handling. |
| Modify | `apps/live_control_server/models/extract_promote.py` | Typed correction request/result and child lineage projection. |
| Modify | `apps/live_control_server/routes/extract_promote.py` | One bounded correction route. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Typed API client. |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Operator quote correction and child navigation. |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Product integration proof. |
| Create | `tests/test_demo_derived_candidate_evidence_correction.py` | Owning-boundary adversarial service tests. |
| Modify if needed | `tests/test_promotable_ingest_run.py` | Durable registry/prepare/confirm proof if its fixture is the owning seam. |
| Modify if needed | `Docs/Roadmaps/ROADMAP-demo.md` | Backward-looking #777 truth only. |
| Modify if needed | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md` | Byte-identical roadmap mirror. |

Discovery of a necessary path outside this table stops implementation for
steward lease amendment or split. Neither DungeonMind nor WorldKeeper is
leased. Production candidate generation/prompt code is not leased.

## §5 Exclusions and collision stops

| Path | Rule |
|---|---|
| `src/graph_memory/extraction/**` | No prompt/model/extraction change; this is operator-reviewed derivation, not a rerun. |
| `src/graph_memory/ingestion/extraction_run.py` | Use existing `lineage` and lifecycle; do not extend the public ExtractionRun schema in this slice. |
| `apps/live_control_server/services/candidate_graph_admission.py` | Preserve strict candidate/admission semantics; no normalization of false evidence. |
| DungeonMind / WorldKeeper repositories | No cross-repository contract or write. |
| `out/**`, licensed Of Conks source | Runtime evidence only; never stage or commit. |
| C1/C2 or ghost-run databases | No mutation. |

If the existing run registry cannot support a safely idempotent child without
a second durable contract, stop and rebrief rather than hiding a new registry
system in this PR. If correction would need to change asserted meaning, source
span identity or non-quote candidate fields, that is not this slice.

## §6 Implementation approach

Re-anchor current `main`, check active PRs/worktrees/leases, then use a clean
isolated implementation worktree. Start with pure correction targeting and
strict whole-candidate validation. Add child persistence and idempotent retry
under the canonical ExtractionRun registry. Only then wire one operator UI
submit path. Freeze the exact implementation head before live replay.

## §7 Evidence required

```bash
uv run pytest -q tests/test_demo_derived_candidate_evidence_correction.py tests/test_promotable_ingest_run.py
cd apps/live-control-ui && npm test -- --run src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
uv run ruff check apps/live_control_server/services/exact_run_evidence_correction.py apps/live_control_server/services/extract_promote.py apps/live_control_server/services/graph_run_registry.py apps/live_control_server/models/extract_promote.py apps/live_control_server/routes/extract_promote.py tests/test_demo_derived_candidate_evidence_correction.py
git diff --check
```

Owning-boundary tests must cover: exact three-quote correction; unchanged
parent bytes/status; unchanged non-quote candidate projection; invalid or
partial replacement; stale SHA/original/index; duplicate targeting; idempotent
retry and conflicting retry; crash/draft not promotable; child byte drift; and
strict prepare/first-World/confirm bindings. Product test must prove parent
blocker, deliberate quote edit, child navigation, and publish gating. Live
disposable replay uses the pinned Of Conks source and frozen candidate with
zero model calls, and checks no World head appears from correction alone.
Report any inherited base failure separately; do not claim a green build if
the known `ThreatPublicationPanel.tsx` JSX error remains.

## §8 PR and handback

Open one `DEMO: derive a qualified candidate from reviewed evidence` PR on
an isolated branch after this ACTIVE handoff is durably on `main`. Report
exact head, parent/child digests, child lineage, full evidence, cost/model-call
count, World-head before/after, and all limitations. PRIME reviews every
distinct head before merge. No J1/full-DEMO completion claim from this slice.

After merge, the steward records PR/review/merge facts in this handoff and
both byte-identical roadmap copies as one guarded sync. A later governed
publication and Plan/Play dogfood remain separate outcomes.

## §9 Acceptance / stop checklist

- [ ] Parent source/index/candidate bytes and status are unchanged.
- [ ] Only explicit bad quotes change in a new child; every replacement is literal in its exact source span.
- [ ] Strict whole-child evidence validation passes before `reviewable` seal.
- [ ] Child lineage and idempotent retry are durable and fail closed.
- [ ] Existing prepare/confirm bind to child ID/digest and reject drift.
- [ ] UI distinguishes frozen parent from derived child and never enables publish on invalid evidence.
- [ ] Correction calls no model and creates no World head.
- [ ] Exact-head tests, live witness, PRIME review, and lease compliance are recorded.
