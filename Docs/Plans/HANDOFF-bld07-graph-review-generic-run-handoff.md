# HANDOFF — BLD-07 generic Graph Review run handoff

- **Created:** 2026-07-22
- **Status:** DRAFT — dispatch only after BLD-06 and the existing extract-promote bridge are re-anchored
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld07-graph-review-generic-run-handoff.md`
- **Suggested branch:** `agent/bld07-graph-review-generic-run-handoff`

## Shared vocabulary

| Term | Definition |
|---|---|
| Generic run | Recap or worldbuilding ExtractionRun selected by durable run ID. |
| Review package | Server-bound candidate assertions, evidence, and revision metadata presented for judgment. |
| Prepare | Seals a selected proposal against a parent graph revision. |
| Confirm | Explicitly commits the prepared proposal through the existing governed publication path. |

## §1 Mission

Graph Review can load an exact worldbuilding ExtractionRun and use the existing
revision-bound prepare/confirm publication path to commit selected assertions
to the World Supergraph without inventing a session lens or creating a second
write protocol.

**Invariant:** A worldbuilding run is reviewable by exact run/source identity,
and only the existing Graph Review confirmation boundary can advance the graph
head.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Product boundary | `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md` |
| Sequencing authority | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`, BLD-07 |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, existing extract-promote contracts |
| Base revision | Dispatch-time immutable merge SHA containing BLD-06 and the current extract-promote bridge; current `8ff2339f` is reference only |
| Predecessor contract | Exact Build handoff identifiers, ExtractionRun bundle, existing Graph Review and extract-promote APIs |
| Exact input consumed | Run ID, source artifact ID, candidate graph/evidence bundle, selected assertion IDs, pinned parent revision |
| Named successor | BLD-08 worldbuilding profile/pilot; Hermes writes remain separate |
| What remains false | Automatic publication, Hermes-specific write path, generic graph editor, player-facing projection |
| Explicit non-goals | New Kernel semantics, automatic identity linking, second contribution store, latest-run selection, undo/retract, UI redesign outside run loading |

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md`
3. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
4. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
5. Existing extract-promote models/routes/services
6. Existing Graph Review workbench and owning tests

If generic run loading requires changing contribution identity or Kernel
semantics, stop and report it as a separate architecture slice.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Build handoff | Carries run context or opens generic review | Graph Review selects exact run/source/revision | Yes | Run-selection adapter |
| Run load | Review is recap/latest-run-shaped | Load exact worldbuilding run bundle | Yes | API + workbench |
| Evidence display | Candidate/evidence may be recap-oriented | Show source domain/authority/span evidence | Yes | Review panel |
| Assertion selection | Existing review selection | Preserve assertion-level selection for worldbuilding | Yes | Review state |
| Prepare | Existing sealed proposal path | Same path accepts generic run evidence | Yes | Extract-promote service |
| Confirm | Existing explicit commit | Same revision-bound confirmation | Yes | Extract-promote service |
| Post-commit reload | Durable reload must be exact | Reload committed revision and show receipt | Yes | Workbench/read path |
| Error/stale proposal | Existing failure semantics | Preserve fail-closed stale/rejected behavior | Yes | Backend + UI |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Load/render generic run bundle |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeaderWithActivity.tsx` | Show source-domain/run context |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewRunSelection.ts` | Exact run/source/revision selection adapter |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewRunSelection.test.ts` | Selection and identity proof |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Generic run/review/promote API calls |
| Modify | `apps/live-control-ui/src/api/types.ts` | Generic review/run/provenance types |
| Modify | `apps/live_control_server/routes/extract_promote.py` | Accept generic source/run binding |
| Modify | `apps/live_control_server/services/extract_promote_ops.py` | Preserve revision-bound generic proposal semantics |
| Modify | `tests/test_extract_promote_ops_atomic.py` | Worldbuilding run and stale/selection proof |
| Modify | `tests/test_live_extract_promote_api.py` | HTTP boundary and exact-run proof |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx` | Workbench load/review/reload proof |

**Bounded discovery exception:** Not applicable — paths are enumerated.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why out of scope |
|---|---|
| `apps/live-control-ui/src/buildSurface/**` | Build toolbar is predecessor; no Build UI redesign |
| `src/graph_memory/extract_promote_ops.py` | Kernel/publication changes require separate architecture review |
| Hermes tool registration or agent write code | Separate capability over the same path |
| `src/graph_memory/identity/**` | No automatic identity linking |
| Player-facing projection | Separate admissibility/product lane |
| Authored overlay migration | Separate authoring workstream |
| `corpus/**`, `evals/**` | No content/gold mutation |

## §6 Implementation contract and conditional matrices

```text
Input:
  Exact ExtractionRun ID + SourceArtifact ID + candidate/evidence bundle +
  current World Graph head + selected assertion IDs.

Output:
  Reviewable generic package, revision-bound prepare response, explicit
  confirm result, and exact committed-revision reload.

Invariant:
  The prepared proposal binds selected assertions, source evidence, and parent
  revision; confirmation is explicit and reload truth is revision-specific.

Failure behavior:
  Unknown run/source → stable not-found; no latest fallback.
  Invalid evidence/selection → review package remains uncommittable.
  Stale parent revision → prepare/confirm conflict; graph head unchanged.
  Post-commit read failure → report committed truth separately from reload
  failure; never claim preview is durable.
  Rejected/superseded proposal → no graph-head advancement.

Replay / idempotency:
  same run + same selection + same parent revision → sealed proposal identity;
  changed selection/revision → new proposal;
  retry after response loss → query proposal/commit receipt, not duplicate write;
  reload → exact committed revision, never latest projection substitution.

Trust boundary:
  Verifies: server-owned run binding, source evidence, assertion selection,
  proposal digest, parent revision, authorization/policy, and committed read.
  Records or trusts without proving: semantic truth of source claims, which
  remains GM-reviewed.
```

### State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Run selection | Loading exact ID | Render package | 404 exact run | Stable unavailable | Reject malformed bundle | Superseded visible | Re-load exact ID |
| Review | Show evidence/selection | Selected assertions explicit | Empty candidate set is uncommittable | Review unavailable | Invalid evidence blocks prepare | Preserve selection, rebase required | Re-open package |
| Prepare | Working | Sealed proposal | No selection is validation error | Stable error | Digest/evidence fail closed | Conflict, no head change | Re-load head/reselect |
| Confirm | Working | Commit receipt | Unknown proposal 404 | Stable error | Proposal mismatch fails | Stale proposal rejected | Query receipt, no blind retry |
| Reload | Reading committed revision | Exact objects/receipt | Committed revision missing is error | Read unavailable | Never show preview as durable | Revision mismatch visible | Retry same revision |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback |
|---|---|---|---|
| Run | Exact durable run ID | Unknown run is 404 | No latest |
| Source | Exact source artifact ID | Mismatch blocks review | No label/path fallback |
| Assertion | Stable assertion ID from candidate package | Unknown selected ID blocks prepare | No index-based selection |
| Proposal | Server-sealed proposal digest | Digest mismatch rejects confirm | No compatibility bypass |
| Revision | Explicit parent/committed revision | Missing revision blocks commit | No current-head inference |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Run binding | Server-owned run/source IDs | Reload selects same bundle | No latest fallback | Recap runs remain readable | No mutation |
| Prepare | Sealed proposal + digest + parent revision | Same package reloads | Same confirm is idempotent/receipt-queryable per existing contract | Existing promote API preserved | Proposal remains uncommitted |
| Confirm | GraphContribution + immutable head | Exact revision reload | Retry queries receipt/commit state | Existing publication authority | Existing retract/rebuild semantics only |

### Predecessor-to-consumer mapping

| Predecessor | Consumer | Transformation | Proof |
|---|---|---|---|
| BLD-06 handoff IDs | Graph Review selection | Parse exact run/source/revision context | Selection test |
| ExtractionRun bundle | Review package | Adapt generic candidate/evidence to existing review types | Generic run test |
| Existing prepare/confirm API | Worldbuilding review | Preserve sealed proposal and explicit confirmation | Backend route/ops tests |
| Committed revision | Workbench state | Reload exact read snapshot | Durable reload test |

### Commit model

```text
Commit point:
  Existing confirm operation advances the World Graph head.

Before commit:
  Proposal is sealed, selected assertion IDs are explicit, parent revision and
  source evidence are validated.

After commit:
  Return contribution/committed revision receipt and read that exact revision.

Truthful result after post-commit failure:
  Report the commit receipt as committed and the exact reload as degraded;
  never replace the failure with preview material or claim a reload succeeded.
```

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| Exact generic run loads | Workbench/API | `npm test -- --run src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx` | Worldbuilding run shown with source context |
| Selection is assertion-ID based | Selection adapter | `npm test -- --run src/planSurface/graphReviewWorkbench/graphReviewRunSelection.test.ts` | No index/label fallback |
| Prepare/confirm remains revision-bound | Promotion service | `uv run pytest tests/test_extract_promote_ops_atomic.py` | Generic run, stale, and rejected cases |
| HTTP boundary preserves exact IDs | Promotion routes | `uv run pytest tests/test_live_extract_promote_api.py` | Request/response contract |
| Exact committed revision reload is truthful | Workbench/read boundary | Generic run test + promote tests | Receipt/reload distinction |
| No scope creep | Git | `git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD` | Only §4 paths |

```bash
uv run pytest tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
cd apps/live-control-ui
npm test -- --run src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx
npm test -- --run src/planSurface/graphReviewWorkbench/graphReviewRunSelection.test.ts
npm run typecheck
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface used: Graph Review
Smallest scenario: open one generic worldbuilding run, select one assertion,
prepare, confirm, and reload the exact committed revision
Expected observation: only selected assertions commit; receipt and reload agree
Evidence captured: focused tests plus revision-bound local dogfood report
```

## §8 Required handback

1. Base and head SHA.
2. Focused diff stat limited to §4.
3. Exact result of every §7 command.
4. Provenance for each result.
5. Generic run, stale proposal, confirm, and exact-reload evidence.
6. Base/head comparison for baseline failures.
7. Operator waivers; `none` if none.
8. Paths outside §4; `none` or stop report.
9. Stop conditions; `none` if none.
10. Confirmation that BLD-08 and Hermes write capability remain successors.
11. Confirmation that the existing publication boundary was reused.

## §9 Acceptance rubric

- [ ] Graph Review loads exact worldbuilding runs without a fake session — proved by generic-run UI/API tests.
- [ ] Evidence and assertion selection remain source/revision bound — proved by selection and promotion tests.
- [ ] Prepare/confirm uses the existing governed publication path — proved by backend route/ops tests.
- [ ] Stale/rejected proposals cannot advance the graph head — proved by failure tests.
- [ ] Post-commit reload truthfully distinguishes commit from read degradation — proved by durable-reload test.
- [ ] No second write protocol or graph store exists — proved by diff inspection.
- [ ] No path outside §4 changed — proved by changed-path command.
- [ ] BLD-08 remains unimplemented and unclaimed.

## Stop conditions

Stop and report if:

- generic worldbuilding review requires a new graph identity or contribution store;
- the existing prepare/confirm boundary cannot bind source evidence;
- exact revision reload is unavailable;
- Build must gain commit controls;
- Hermes capability is required to prove the human review path.

```text
Stop condition:
Why the current mission cannot absorb it:
New contract discovered:
Affected paths:
Proposed successor slice:
Authority update needed:
```
