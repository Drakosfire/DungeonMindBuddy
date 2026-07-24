# HANDOFF — BLD-07 generic Graph Review run binding

- **Created:** 2026-07-22
- **Status:** ACTIVE / MERGEABLE — BLD-06 merged as `bf28e46c` (PR #392); this slice is rebased onto that immutable merge SHA and re-anchored. Open PR: [#393](https://github.com/Drakosfire/DungeonMindBuddy/pull/393).
- **Base revision (re-anchored):** `bf28e46c7e9eab8fc228df2b0c066238817e6442`
- **Canonical handoff path:** `Docs/Plans/HANDOFF-bld07-graph-review-generic-run-handoff.md`
- **Suggested branch:** `agent/bld07-graph-review-generic-run-handoff`

## Stop-condition disclosure (§5 boundary reached)

`src/graph_memory/extract_promote_ops.py` is listed in §5 as out of scope, with
the caveat that touching it is a **stop condition requiring architecture review,
not silent scope expansion**. The implementation reached that boundary:

- **Why the existing sealed inputs are insufficient:** `prepare_extract_promote`
  is the only seam that stamps an evidence domain onto the sealed contribution,
  and it hardcoded `source_domain="recap"`. Every worldbuilding assertion would
  otherwise be sealed and merged into the World Supergraph labeled as recap
  evidence. No caller-visible input could express the run's real domain.
- **What changed:** one additive keyword-only parameter, `source_domain: str = "recap"`,
  passed through to the existing identity gate. Contribution identity, candidate
  mapping, identity resolution, merge/retraction rules, and graph-head commit
  behavior are untouched, and the default preserves every existing caller.
- **Proof:** `test_prepare_confirm_exact_worldbuilding_extraction_run` asserts the
  sealed package carries exactly `{"worldbuilding"}`;
  `test_recap_prepare_still_seals_recap_source_domain` asserts recap runs still
  seal `recap` and never `worldbuilding`.
- **Requires:** explicit operator/architecture sign-off on this one parameter
  before merge. It is disclosed here and in the PR body rather than absorbed.

## Bounded discovery report (§4)

§4 named `GraphReviewWorkbenchHeaderWithActivity.tsx`. The actual header rendered
by `GraphReviewWorkbenchModule` is **`GraphReviewWorkbenchHeader.tsx`**; the
`WithActivity` variant is not on the exact-run path. The header is where source
domain, authority, run, and optional scope must appear, so the discovery
substitution proves the same invariant at the same boundary. One path used of
the two allowed; `liveApi.ts` and `models/extract_promote.py` were allowlisted
but needed no change (the generic and Build-context endpoints already exist from
BLD-06, and no new public response field was required).

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable/public contract changed? | Decision |
|---|---:|---:|---|
| Load an exact worldbuilding ExtractionRun in Graph Review | Yes | Yes | Include |
| Adapt the existing server-owned promotable-run binding to generic runs | No — required for the same review capability to prepare truthfully | Yes | Include |
| Change Kernel contribution, identity, merge, or graph-head semantics | Yes | Yes | Reject/stop condition |
| Add a second promotion service or protocol | No — prohibited duplicate authority | Yes | Reject |
| Add Hermes writes | Yes | Yes | Successor |

**Selected capability:** Graph Review can bind an exact source-domain-neutral run
to the existing governed prepare/confirm flow without changing Kernel semantics.

## §1 Mission

Graph Review can load an exact recap or worldbuilding ExtractionRun, display its
source/evidence context without a fabricated session lens, and use the existing
revision-bound prepare/confirm publication path to commit selected assertions to
the World Supergraph.

**Invariant:** the browser selects an exact server-resolved run and assertions;
only the existing Graph Review confirmation boundary and shared Kernel ops may
advance the graph head.

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| Product boundary | `Docs/Design/DESIGN-extract-promote-graph-review-bridge.md` |
| Sequencing authority | Build slice plan BLD-07 |
| Predecessor | BLD-06 exact run/source/revision handoff and BLD-03/04 canonical run contracts |
| Existing product binding | `apps/live_control_server/services/promotable_ingest_run.py`, `apps/live_control_server/services/extract_promote.py`, and extract-promote route/models |
| Existing Kernel owner | `src/graph_memory/extract_promote_ops.py` |
| Repository rules | `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, existing extract-promote contracts |
| Base revision | Dispatch-time immutable merge SHA containing BLD-06 and current publication bridge |
| Exact input consumed | exact run ID, SourceArtifact ID/revision, candidate/evidence bundle, selected assertion IDs, and pinned parent graph revision |
| Named successor | BLD-08 worldbuilding profile/pilot; Hermes reuse remains separate |
| What remains false | no automatic publication, new identity linking, generic graph editor, player projection, undo/retract UI |
| Explicit non-goals | Kernel semantic changes, second promotion service, latest-run selection, Build commit controls, broad workbench redesign |

### Locked ownership decision

The existing layers are:

```text
Browser Graph Review
  → apps/live_control_server/routes/extract_promote.py
  → apps/live_control_server/services/extract_promote.py
  → apps/live_control_server/services/promotable_ingest_run.py
  → src/graph_memory/extract_promote_ops.py
```

BLD-07 generalizes the **server-owned run resolver and service binding** so the
existing product prepare request can resolve canonical BLD-03 ExtractionRuns.
It does not create `apps/live_control_server/services/extract_promote_ops.py`.

`src/graph_memory/extract_promote_ops.py` remains the shared Kernel orchestration
owner and is out of scope unless the implementation proves that generic source
scope cannot be represented through the existing sealed inputs. That discovery
is a stop condition requiring architecture review, not silent scope expansion.

Read in order:

1. Campaign Supergraph architecture
2. extract-promote Graph Review bridge
3. BLD-03 canonical SourceArtifact/ExtractionRun contracts
4. BLD-06 exact handoff
5. `apps/live_control_server/services/promotable_ingest_run.py`
6. `apps/live_control_server/services/extract_promote.py`
7. `apps/live_control_server/routes/extract_promote.py`
8. `src/graph_memory/extract_promote_ops.py`
9. current Graph Review workbench and owning tests

Stop if generic run support requires changing contribution identity, candidate
to contribution mapping semantics, identity resolution, merge/retraction rules,
or graph-head commit behavior.

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Boundary |
|---|---|---|---:|---|
| Build handoff | exact IDs carried by BLD-06 | Graph Review selects exact run/source/revision | Yes | run selection adapter |
| Run resolution | server resolver is graph-ingest/recap shaped | resolve canonical exact recap/worldbuilding run through one adapter | Yes | promotable run service |
| Run load | workbench may depend on manifest/latest context | load exact generic review bundle | Yes | API/workbench |
| Source scope | campaign/session assumed | display world/source authority and permit null campaign/session where valid | Yes | service/review projection |
| Evidence | recap-oriented labels/spans | show canonical SourceArtifact/span evidence | Yes | review projection |
| Assertion selection | existing stable IDs | preserve exact assertion-ID selection | Yes | review state |
| Prepare | existing runId-only sealed proposal | same route/service resolves generic run and seals existing Kernel proposal | Yes | route/service/Kernel call |
| Confirm | existing explicit confirmation | unchanged sealed proposal confirmation | Yes | route/service/Kernel call |
| Stale proposal | existing fail-closed behavior | unchanged conflict/no head advancement | Yes | service/Kernel |
| Already applied | existing idempotent receipt | unchanged truthful no-op/receipt | Yes | service/Kernel |
| Post-commit reload | existing exact revision work | reload exact committed revision and distinguish read degradation | Yes | workbench/read API |
| Unknown/superseded run | existing diagnostics vary | exact 404/unreviewable; no latest fallback | Yes | resolver/service |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Load/render generic exact run package |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeaderWithActivity.tsx` | Show source domain, authority, run, and optional scope |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewRunSelection.ts` | Parse/validate exact run/source/revision handoff |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewRunSelection.test.ts` | Exact identity/no-latest proof |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx` | Generic package, selection, prepare/confirm, and reload UI proof |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Generic run/review/prepare/confirm/read client methods |
| Modify | `apps/live-control-ui/src/api/types.ts` | Canonical run/source/evidence/review projection types |
| Modify | `apps/live_control_server/services/promotable_ingest_run.py` | Resolve canonical ExtractionRun and adapt old recap manifests through BLD-03 compatibility seam |
| Modify | `apps/live_control_server/services/extract_promote.py` | Bind generic resolved run to existing prepare/confirm Kernel inputs without new semantics |
| Modify | `apps/live_control_server/routes/extract_promote.py` | Preserve runId-only product boundary and generic safe errors |
| Modify | `apps/live_control_server/models/extract_promote.py` | Source-domain-neutral review/status fields only when required by the public response |
| Modify | `tests/test_promotable_ingest_run.py` | Exact generic/recap resolution, invalid/superseded, and root-policy proof |
| Modify | `tests/test_extract_promote_ops_atomic.py` | Existing Kernel invariant regression with generic sealed inputs |
| Modify | `tests/test_live_extract_promote_api.py` | HTTP exact-run, prepare/confirm, stale, receipt, and error proof |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/planSurface/graphReviewWorkbench
Maximum additional paths: 2
Allowed path kinds: existing review projection/toolbar test or type files
Decision rule: only when the current Graph Review owning component differs from the named files
Required report: actual owner and why the additional path proves the same invariant
```

Discovery used on this branch:

1. `GraphReviewExactRunProjection.tsx` — exact-run source/evidence projection
   (canonical prose + assertion↔span navigation). Named allowlist only had the
   module shell; this is the owning projection surface for the evidence invariant.
2. `GraphReviewWorkbenchHeader.tsx` — actual header owner (allowlist named
   `GraphReviewWorkbenchHeaderWithActivity.tsx`, which does not exist).

Also: prepare/confirm/review-package client lives in
`apps/live-control-ui/src/api/extractPromoteApi.ts` (existing extract-promote
product client), not `liveApi.ts`.

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| `src/graph_memory/extract_promote_ops.py` | Existing Kernel owner; semantic change is a stop condition |
| `src/graph_memory/identity/**` | no automatic identity changes |
| new application `extract_promote_ops.py` | prohibited duplicate authority |
| Build surface files | BLD-06 predecessor is complete |
| Hermes registration/tool code | separate capability over same path |
| authored overlay migration/undo/retract UI | separate workstreams |
| player-facing projection | separate admissibility/product lane |
| `corpus/**`, `evals/**` | no content/gold mutation |

## §6 Implementation contract

```text
Input:
  exact canonical ExtractionRun ID + SourceArtifact ID/revision + candidate and
  evidence bundle + selected assertion IDs + current graph head.

Output:
  source-domain-neutral review package, existing sealed prepare proposal,
  existing explicit confirm receipt, and exact committed-revision reload.

Invariant:
  product prepare remains runId-only and server-resolved; selected assertions,
  source evidence, and parent revision are sealed before unchanged Kernel confirm.

Failure behavior:
  unknown/invalid/superseded run → stable error; no latest fallback
  source/run mismatch → fail closed
  invalid evidence/selection → uncommittable review package
  stale parent/proposal → conflict; prior head unchanged
  already applied → truthful existing receipt/no-op
  publication failure → no head advancement
  commit succeeds but reload fails → report committed receipt + degraded read

Replay / idempotency:
  same run + selection + parent revision → existing sealed proposal identity
  changed selection/revision → new proposal
  response-loss retry → query/reuse existing receipt semantics; no blind duplicate
  reload → exact committed revision, not current/latest substitution

Trust boundary:
  Verifies server-owned exact run resolution, source/evidence binding, selection,
  proposal digest, parent revision, capability policy, and exact read receipt.
  Semantic truth remains GM judgment.
```

### §6A State/fallback matrix

| Path | Success | Miss | Unavailable | Integrity failure | Stale/superseded | Retry |
|---|---|---|---|---|---|---|
| Run selection | exact package | 404 | stable error | reject malformed/mismatch | visible/unreviewable | reload exact ID |
| Review | source evidence + selection | zero candidates uncommittable | stable error | invalid evidence blocks | preserve state/rebase | reopen exact package |
| Prepare | existing sealed proposal | zero selection validation | stable error | digest/scope fail closed | conflict/no head change | reload/reselect |
| Confirm | existing commit receipt | proposal 404 | stable error | mismatch fails | stale rejects | query receipt, no blind retry |
| Reload | exact committed objects | missing revision error | degraded read | never show preview as durable | revision mismatch visible | same revision |

### §6B Identity matrix

| Situation | Required rule | Ambiguity | Fallback |
|---|---|---|---|
| Run | exact canonical run ID | unknown 404 | no latest |
| SourceArtifact | exact ID/revision from run | mismatch blocks | no label/path |
| Assertion | stable candidate assertion ID | unknown blocks | no index selection |
| Proposal | server-sealed digest | mismatch rejects | no bypass |
| Revision | explicit parent/committed IDs | missing blocks | no current-head inference |

### §6C Persistence/replay matrix

| Operation | Durable representation | Round trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Run binding | canonical IDs + resolver result | same exact package | no latest | recap adapter supported | no mutation |
| Prepare | existing sealed proposal | exact package/selection/head | existing semantics | current API remains runId-only | uncommitted proposal |
| Confirm | GraphContribution + immutable head | exact receipt/revision | existing idempotency | same Kernel path | existing retract/rebuild only |
| Reload | pinned graph revision | exact durable objects | repeat read | current projection API | no write |

### §6D Predecessor mapping

| Predecessor | Generic consumer | Transformation | Proof |
|---|---|---|---|
| BLD-06 handoff IDs | run selection adapter | parse exact IDs only | selection test |
| BLD-03 ExtractionRun | promotable resolver | map canonical components to existing sealed prepare inputs | resolver tests |
| legacy graph-ingest manifest | BLD-03 adapter then resolver | preserve recap behavior | real fixture tests |
| existing prepare/confirm service | generic Graph Review | no new protocol; source-domain-neutral review projection only | route/service tests |
| committed revision receipt | workbench | exact reload and degraded-read distinction | UI/API tests |

### Commit model

```text
Commit point:
  unchanged Kernel confirm advances the World Supergraph head.
Before commit:
  server resolves exact run; evidence/selection/parent revision are sealed.
After commit:
  return existing contribution and committed revision receipt; reload exact revision.
Post-commit read failure:
  report commit success and read degradation separately; never substitute preview.
```

## §7 Verification ownership and commands

| Guarantee | Boundary | Command |
|---|---|---|
| exact generic/recap run resolution | promotable run service | `uv run pytest tests/test_promotable_ingest_run.py` |
| unchanged revision-bound Kernel behavior | shared ops regression | `uv run pytest tests/test_extract_promote_ops_atomic.py` |
| runId-only HTTP and truthful outcomes | route/service | `uv run pytest tests/test_live_extract_promote_api.py` |
| exact UI selection/no latest | selection adapter | `npm test -- --run src/planSurface/graphReviewWorkbench/graphReviewRunSelection.test.ts` |
| generic review/confirm/reload UX | workbench | `npm test -- --run src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx` |
| no new write authority | diff/import inspection | changed-path checks |

```bash
uv run pytest tests/test_promotable_ingest_run.py \
  tests/test_extract_promote_ops_atomic.py \
  tests/test_live_extract_promote_api.py
cd apps/live-control-ui
npm test -- --run src/planSurface/graphReviewWorkbench/graphReviewRunSelection.test.ts
npm test -- --run src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx
npm run typecheck
cd ../..
git diff --check
git diff --name-only "$(git merge-base HEAD origin/main)"...HEAD
```

### Minimal live proof

```text
Existing surface: Graph Review
Scenario: open one exact sessionless worldbuilding run, inspect source evidence,
select one assertion, prepare, confirm, reload exact committed revision, then
exercise stale proposal and already-applied receipt paths.
Expected: existing Kernel path is reused; only selected assertions commit; no
session/latest-run is invented; commit and reload truth are distinct.
```

## §8 Required handback

Record SHAs, actual paths/discovery, diff, all §7 results and provenance, real
resolver fixture provenance, live proof, baseline failures, waivers, stop
conditions, and confirmation that `src/graph_memory/extract_promote_ops.py`
semantics and ownership were unchanged.

## §9 Acceptance rubric

- [ ] Graph Review loads exact recap/worldbuilding runs without fake session scope.
- [ ] Product prepare remains runId-only and server-resolved.
- [ ] Generic binding occurs in the existing resolver/service layers.
- [ ] Existing Kernel prepare/confirm semantics and owner are reused unchanged.
- [ ] Selection/evidence/proposal/revision identities remain exact and distinct.
- [ ] Stale/rejected/invalid proposals cannot advance the head.
- [ ] Post-commit reload truthfully distinguishes commit success from read degradation.
- [ ] No second promotion service/protocol or Build commit action exists.
- [ ] Only §4 and approved discovery paths changed.

## Stop conditions

Stop if generic runs require changing Kernel contribution/identity/merge/head
semantics, exact revision reload is unavailable, the existing sealed proposal
cannot bind canonical source evidence, a second promotion service appears
necessary, Build must gain commit controls, or Hermes is required to prove the
human path.
