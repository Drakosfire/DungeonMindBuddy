# HANDOFF — BLD-06 Build extraction toolbar

- **Created:** 2026-07-22
- **Status:** PREPARED / DRAFT — may be stacked against the BLD-04 and BLD-05 heads; ACTIVE / MERGEABLE only after both merge, rebase, and immutable merge-SHA re-anchor.
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld06-build-extraction-toolbar.md`
- **Suggested branch:** `agent/bld06-build-extraction-toolbar`

## Shared vocabulary

| Term | Definition |
|---|---|
| Extraction launch | Build submits a prepared source artifact to the generic extraction controller. |
| Exact run | Durable run ID returned by the controller; never “latest run”. |
| Handoff | Navigation carrying source artifact, run, and revision identifiers into Graph Review. |
| Terminal action | **Open in Graph Review**, not direct promotion. |

## §1 Mission

Build can prepare a saved worldbuilding source, launch one source-aware
extraction run, recover its exact status, and open that exact run in Graph
Review without exposing a Build-side graph commit action.

**Invariant:** Every extraction launch is bound to a saved source revision and
ends in an explicit run state or an exact Graph Review handoff; Build never
publishes graph memory.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-06 |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, source-artifact/run contracts from BLD-03/04 |
| Base revision | Dispatch-time immutable merge SHA containing BLD-04 and BLD-05; current `8ff2339f` is reference only |
| Predecessor contract | Build shell/source save, generic graph-preview routes, SourceArtifact/ExtractionRun APIs |
| Exact input consumed | Saved source document ID/revision, source metadata, extraction profile, and server-issued run response |
| Named successor | BLD-07 generic Graph Review run loading/publication handoff |
| What remains false | Graph Review generic selection/commit, worldbuilding profile tuning, PDF/OCR, automatic promotion |
| Explicit non-goals | Build-side merge, selecting all assertions, second review UI, browser model/provider controls, latest-run lookup |

Read in order:

1. `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`
2. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
3. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
4. BLD-03/04 source/run and graph-preview contracts
5. BLD-05 Build shell
6. Existing Graph Review route/query contract

If Graph Review cannot accept an exact run identifier without changing its
contract, carry only the identifier handoff and stop before redesigning review.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Extract button | No Build extraction action | Enabled only for saved/current source | Yes | Build toolbar |
| Prepare source | Source may be dirty/stale | Save/prepare exact revision first | Yes | Toolbar + source API |
| Launch extraction | Recap-shaped or absent | Submit source artifact/profile to generic route | Yes | API/controller |
| Status | User may infer latest run | Poll exact run ID and show lifecycle | Yes | API + toolbar |
| Failure | Generic UI error | Stable diagnostic + run ID, no raw payload | Yes | API/toolbar |
| Refresh | Run context may be lost | Recover exact run from URL/local state | Yes | Build page |
| Graph Review handoff | May open generic route | Carry exact source/run/revision identifiers | Yes | Toolbar navigation |
| Commit | No Build authority | No commit control/action in Build | Yes | Build boundary |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Source-aware prepare/extract/status/handoff client methods |
| Modify | `apps/live-control-ui/src/api/types.ts` | Request/response/run lifecycle types |
| Create | `apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx` | Extract/status/handoff controls |
| Create | `apps/live-control-ui/src/buildSurface/useBuildExtraction.ts` | Exact-run lifecycle hook |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx` | Mount toolbar and preserve source revision |
| Create | `apps/live-control-ui/src/buildSurface/BuildIngestToolbar.test.tsx` | Toolbar state/error/terminal-action proof |
| Create | `apps/live-control-ui/src/buildSurface/useBuildExtraction.test.ts` | Hook lifecycle and exact-run proof |
| Modify | `apps/live_control_server/routes/graph_preview.py` | Source-aware launch/status route wiring |
| Modify | `apps/live_control_server/services/graph_run_registry.py` | Exact-run status/recovery seam if required by API |
| Create | `tests/test_graph_preview_routes.py` | Route payload, stale-source, status, and run-ID proof |

**Bounded discovery exception:** Not applicable — paths are enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/**` | Generic review loading belongs to BLD-07 |
| `apps/live_control_server/services/extract_promote_ops.py` | Build cannot call publication directly |
| `apps/live-control-ui/src/buildSurface/**` other than listed files | Avoid hidden Build redesign |
| `src/graph_memory/extraction/**` | Runtime was delivered by BLD-04 |
| `corpus/**`, `evals/**` | No source/gold mutation |
| Model/provider selector UI | Policy is server-owned |
| Latest-run APIs or fallback selection | Exact run identity is the invariant |

## §6 Implementation contract and conditional matrices

```text
Input:
  Saved source document ID + committed revision/digest, source artifact ID,
  extraction profile, and authenticated server API context.

Output:
  Exact run ID, durable lifecycle status, safe diagnostics, and a Graph Review
  handoff containing source artifact/run/revision identifiers.

Invariant:
  No launch occurs for unsaved/stale source; no handoff substitutes latest run;
  no Build action confirms or commits a graph proposal.

Failure behavior:
  Unsaved source → disable/block launch and point to save.
  Stale source → conflict state; preserve editor content.
  Launch failure → failed run/error with safe diagnostic and no fake success.
  Status unavailable → retain exact run ID and show recoverable unavailable state.
  Handoff missing exact run → block navigation or show explicit error.

Replay / idempotency:
  same source revision/profile → server run policy determines reuse/distinct run;
  changed revision/profile → distinct run;
  retry after launch response loss → query exact idempotency key/run if supplied;
  refresh → recover exact run, never latest.

Trust boundary:
  Verifies: source revision, server response, run ID, status, handoff payload.
  Records or trusts without proving: candidate semantic correctness and
  publication eligibility, which Graph Review owns.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Toolbar mount | Show disabled/loading | Show controls | No source disables extract | Show save/API unavailable | Hide unsafe action | Stale disables launch | Re-read source |
| Launch | Working state | Exact run ID/status | Invalid source error | Safe retryable error | No fake run success | 409/source conflict | Retry explicit action |
| Status | Poll exact run | Render current lifecycle | Exact run 404 | Preserve run ID/error | Mark failed/unreviewable | Superseded status visible | Poll/backoff exact run |
| Handoff | Disabled until run reviewable | Open exact Graph Review context | Missing run blocks | Show navigation error | No latest-run fallback | Preserve revision context | Retry navigation |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Source document | Use durable document ID + revision | Missing revision blocks launch | No |
| Source artifact | Use server-issued artifact ID | Mismatch blocks launch | No |
| Run | Use exact server-issued run ID | Missing/unknown run blocks handoff | No latest |
| Handoff query | Carry IDs, not labels/paths | Missing field is contract error | No inferred context |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Launch request | Source/revision/profile + idempotency/run policy | Server run records exact input | Follow BLD-03 run policy | Recap launch remains valid | Failed run is visible |
| Run status | Exact run ID + lifecycle | Refresh returns same status | No latest substitution | Existing status routes remain readable | No client deletion |
| Handoff | URL/state with source/run/revision IDs | Graph Review receives exact context | Reopen same run | Existing Graph Review entry remains valid | Back navigation |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| BLD-02 committed source revision | Launch request | Require current source digest/revision | Toolbar/route tests |
| BLD-03 SourceArtifact | Extraction request | Send exact artifact ID and profile | Route test |
| BLD-03 ExtractionRun | Status/handoff | Persist and carry exact run ID | Hook/route tests |
| Existing Graph Review route | Handoff | Add query/context identifiers without review redesign | Toolbar test |

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Unsaved/stale source cannot launch | Build toolbar + route | `npm test -- --run src/buildSurface/BuildIngestToolbar.test.tsx` and backend route tests | Disabled/control and 409 cases |
| Exact run status survives refresh | Hook/API boundary | `npm test -- --run src/buildSurface/useBuildExtraction.test.ts` | Exact ID retained |
| Server rejects invalid launch | Graph preview route | `uv run pytest tests/test_graph_preview_routes.py` | Stable errors/no fake success |
| Handoff opens exact run | Toolbar navigation | Toolbar test | IDs carried, no latest fallback |
| No Build publication control | Build component/diff | Focused UI tests + diff inspection | No confirm/commit call |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
uv run pytest tests/test_graph_preview_routes.py
cd apps/live-control-ui
npm test -- --run src/buildSurface/BuildIngestToolbar.test.tsx
npm test -- --run src/buildSurface/useBuildExtraction.test.ts
npm run typecheck
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: /build
Smallest scenario: save one source, launch extraction, refresh during status,
then open Graph Review from the exact completed run
Expected observation: exact run state survives and handoff carries all IDs
Evidence captured: focused tests and local UI/API trace without corpus payload
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Unsaved/stale, refresh, failure, and exact-handoff evidence.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-07 owns generic Graph Review loading/commit.
11. Confirmation that Build has no publication call.

## §9 Acceptance rubric

- [ ] Launch requires a saved current source revision — proved by toolbar and route tests.
- [ ] Run status is keyed by exact durable run ID — proved by hook/route tests.
- [ ] Refresh/retry never selects latest run implicitly — proved by exact-ID tests.
- [ ] Failures are safe and recoverable without raw corpus payloads — proved by route/UI tests.
- [ ] Terminal Build action opens Graph Review and does not commit — proved by toolbar/diff inspection.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] BLD-07 remains unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- Graph Review requires a new publication API to accept the handoff;
- launch cannot be bound to a saved source revision;
- exact run IDs are unavailable from the backend;
- a Build-side candidate review panel is required;
- the status API can only return latest-run semantics.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
