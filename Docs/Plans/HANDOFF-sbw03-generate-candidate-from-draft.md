# HANDOFF — SBW03 Generate one typed candidate from one exact ThreatDraft version

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW01` and `SBW02` merge; re-anchor all paths and the base SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw03-generate-candidate-from-draft.md`  
**Workstream:** `SBW03`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch exactly one capability: exact draft-version generation with reloadable candidate reference and truthful failure. Do not add the semantic renderer, editor, acceptance, graph publication, images, or combat.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Map one exact ThreatDraft version to a Server generation request | Yes | Yes | No | Include |
| Retain candidate identity/status for reload | No, required to make generation usable | Yes | No | Include under same invariant |
| Render the candidate as a styled statblock | Yes | No | Yes | Successor `SBW04` |
| Edit/validate mechanics | Yes | Yes | Yes | Successor `SBW05` |
| Generate images | Yes | Yes | Yes | Successor `SBW16` after later decomposition |
| Save accepted mechanics | Yes | Yes | Yes | Successor `SBW07` |

**Selected capability:** one immutable draft version produces one traceable typed candidate proposal through the server-owned integration boundary.

**Why included rows share one invariant:** generation is not usable unless the result can be associated with and reloaded from the exact source draft version. The candidate cache/reference is workflow evidence, not mechanics authority.

## §1 Mission

A caller can generate and later reload a typed statblock candidate from one exact ThreatDraft version without mutating the authored draft or claiming accepted mechanics.

**Invariant**

```text
Every generation result or failure is bound to draft_id, generated_from_draft_version, and request_id; provider outcome never mutates authored concept fields or graph truth.
```

**Mission falsification test**

```text
This is not one slice if it must also style the candidate, edit mechanics, validate a working copy, persist a statblock revision, publish a Threat, or request media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §5–6; tracker `SBW03` |
| Repository rules | `AGENTS.md`; external-agent PR loop rules/template |
| Base revision | Actual merged SHA containing `SBW01` + `SBW02` |
| Predecessor contract | Server-owned statblock client/readiness; strict `ThreatDraftV1` repository/version API |
| Exact input consumed | `draft_id`, `expected_draft_version`, optional caller request ID; complete persisted draft snapshot |
| Named successor | `SBW04` read-only candidate workbench |
| What remains false | Candidate is not accepted, persisted mechanics, graph memory, or rendered product UI |
| Explicit non-goals | Renderer, edit/validate UI, revise, save, graph, images, Markdown, combat, Server schema changes |

Read in order:

1. `Docs/Design/DESIGN-threat-statblock-authoring-projection-workflow.md` §§5–7
2. tracker `SBW03`
3. merged `SBW01` client contract and tests
4. merged `SBW02` models/store/routes
5. current DungeonMindServer v1 OpenAPI/generated contract and exact captured generation fixtures
6. existing workbench endpoint only to identify predecessor route names; do not reuse mock semantics

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Generate current draft version | Mock/corpus-first workbench command | Strict backend request to DungeonMindServer | Yes | orchestration service + route |
| Stale requested version | Undefined | Reject before downstream call | Yes | service |
| Success | No typed candidate lineage | Store candidate ref/status and bounded response cache/locator | Yes | service + draft store |
| Provider timeout | Mock path may hide real dependency | Typed retryable error; draft unchanged | Yes | integration/orchestration |
| Validation/refusal | Not distinct | Preserve Server error category and request ID | Yes | route/service |
| Candidate reload | No v1 workflow | Read cached typed candidate or Server locator by candidate ID | Yes | candidate repository/read route |
| Candidate expiry | Not modeled | Return explicit expired/unavailable state; retain ref | Yes | service/read route |
| Duplicate request/retry | Undefined | Declared idempotency; never append duplicate active refs silently | Yes | orchestration/store |
| Images | Potential old flow | Always `generate_images=false` in this slice | Yes | request mapper |

## §4 Files in scope — allowlist

Exact paths may be renamed by predecessors; re-anchor before dispatch.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/statblock_candidate_workflow.py` | Buddy-local request/ref/cache/error view models only |
| Create | `apps/live_control_server/services/statblock_candidate_generation.py` | Exact draft snapshot → typed Server request orchestration |
| Create | `apps/live_control_server/services/statblock_candidate_cache.py` | Bounded non-authoritative candidate response cache/read behavior |
| Create | `apps/live_control_server/routes/statblock_candidates.py` | Generate/read candidate API |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Atomic candidate-ref append without authored-field mutation |
| Modify | `apps/live_control_server/main.py` | Router mount |
| Create | `tests/test_statblock_candidate_generation.py` | Mapping, stale, failure, retry proof |
| Create | `tests/test_statblock_candidate_routes.py` | Route contract and reload proof |
| Create | `tests/fixtures/statblocks/v1/generated_candidate.json` | Captured contract-real fixture if not already available |
| Modify | `apps/live-control-ui/src/api/types.ts` | Typed API surface only; no product UI |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Generate/read functions only |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Client mapping proof |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package and generated contract fixture directory
Maximum additional paths: 3
Allowed path kinds: client method extension, exact generated type import, captured Server error fixture
Decision rule: required to call the published generate/read candidate contract without handwritten mechanics models
Required report: list real Server operation IDs/routes and fixture provenance
```

## §5 Explicitly out of scope

| Capability/path | Reason |
|---|---|
| `StatblockWorkbenchModule.tsx` | UI replacement belongs to `SBW04` |
| shared semantic renderer | `SBW04` |
| complete-definition editor/validation | `SBW05` |
| revise/regenerate | `SBW06` |
| create/append statblock revision | `SBW07` |
| World Graph models/writes | `SBW08–09` |
| `generate_images=true` or asset binding | media successors |
| corpus promotion/retrieval activation deletion | delete when `SBW04` replaces the normal surface |
| Server implementation changes | report contract defect separately |

## §6 Implementation contract

```text
Input:
  draft_id
  expected_draft_version
  optional client_request_id/idempotency key
  exact ThreatDraftV1 loaded by the service

Output:
  GenerateThreatDraftCandidateResponseV1 containing draft locator, request ID,
  candidate ref/status, typed candidate payload or typed failure

Invariant:
  result is bound to exact draft version; authored fields and graph/corpus remain unchanged

Failure behavior:
  missing draft -> 404, no downstream call
  stale version -> 409, no downstream call
  integration unavailable/auth/timeout/rate limit -> typed failure, no candidate ref unless Server supplied a durable candidate ID
  Server validation/refusal -> typed non-success outcome; draft preserved
  malformed downstream response -> fail closed; do not cache as candidate
  candidate cache write failure after downstream success -> truthful partial result with Server candidate locator when available; recovery must read/reconcile before retry

Replay / idempotency:
  same draft version + same idempotency key -> same downstream operation/result or explicit replay conflict
  same draft version + new key -> permitted new candidate, preserving lineage
  changed draft version -> distinct generation source
  duplicate successful callback/response -> candidate ref deduplicated by candidate_id

Trust boundary:
  Verifies: exact draft version, bounded request mapping, contract shape, candidate ID/expiry/status
  Records without proving: quality or campaign correctness of generated mechanics
  Rejects: implicit corpus retrieval, hidden prompt/source bodies not represented by draft pointers, image request, unknown response fields
```

### Request-mapping decisions

- `description` comes from the exact persisted draft snapshot, not current UI text.
- Ruleset, target CR, complexity, must-include/must-avoid, party/terrain context map explicitly from versioned fields.
- Graph context contributes only admitted pointers or an already-authorized bounded context snapshot produced by an existing graph read path. The generation service must not perform open-ended corpus search.
- `generate_images=false` is hard-coded for this slice.
- Correlation/request ID is created before the downstream call and returned on every outcome.
- A candidate cache copy retains contract/version/candidate ID and is explicitly non-authoritative.

### §6A State and fallback matrix

| Path | Initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/expired | Retry |
|---|---|---|---|---|---|---|---|
| Generate | load exact draft | candidate ref + typed payload | 404 draft | typed downstream failure | fail closed | 409 draft version | declared idempotency |
| Read candidate | load ref/cache/Server read if contract supports | exact candidate ID | 404 ref | unresolved but retain ref | fail closed | explicit expired state | refresh only by new generation |
| Append ref | compare draft version | atomic ref append | N/A | N/A | prior draft remains | stale write rejected | dedupe by candidate ID |

No fallback to mock candidate, corpus Markdown, another draft version, “latest candidate,” or display-name lookup.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Draft | exact `draft_id` | none | No | ref stored on same draft |
| Draft version | exact positive version | mismatch = 409 | No | immutable source claim |
| Candidate | exact Server `candidate_id` | none | No | dedupe key |
| Request | stable request/idempotency key | collision with changed payload = conflict | No | audit/replay key |
| Name | display only | duplicates allowed | No | never used to select candidate |
| Expired candidate | retain exact ID/status | no rebinding | No | historical ref remains |

### §6C Persistence and replay matrix

| Operation | Representation | Round-trip | Duplicate behavior | Compatibility | Recovery |
|---|---|---|---|---|---|
| Candidate ref append | nested `ThreatDraftCandidateRefV1` in draft or sidecar owned by same repository | IDs/version/status preserved | same candidate ID deduped | schema versioned | re-read draft |
| Candidate cache | bounded JSON keyed by candidate ID with contract version/expiry | typed payload preserved | atomic replace only for same exact payload/digest | disposable/rebuildable | Server read or explicit unavailable |
| Generate replay | idempotency record/downstream key | same source version and request mapping | same key same result; changed payload conflicts | no migration from mock artifacts | reconcile by request/candidate ID |

### §6D Predecessor-to-consumer mapping

**Grounding source:** current DungeonMindServer generated OpenAPI/client and captured success/error fixtures.

The implementation PR must fill a field-level table using actual generated names. Minimum required mapping:

| Server field/outcome | Buddy behavior | Transformation | Proof |
|---|---|---|---|
| candidate ID | `candidate_ref.candidate_id` | exact copy | captured fixture test |
| contract/version | cache/ref metadata | exact copy | fixture test |
| created/expiry timestamps | ref lifecycle | parse/normalize only | expiry test |
| definition | cached typed candidate payload | generated DTO; no handwritten schema | contract test |
| validation receipt | candidate review metadata | exact typed mapping | fixture test |
| generation receipt/request ID | audit/correlation | preserve both IDs | route test |
| refusal/error envelope | typed Buddy failure | stable category + safe message | error fixture tests |
| assets/warnings | retain in candidate payload; do not select/bind | exact typed mapping | fixture test |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Stale version blocks downstream | orchestration | focused pytest with fake client call counter | zero calls, 409 |
| Exact request mapping | service | fixture/snapshot test | all design fields mapped; images false |
| Success ref/cache reload | service/store/route | generation + process-reload test | same candidate ID and source version |
| Failure preserves draft | store/service | timeout/auth/refusal parameterized tests | authored digest/version unchanged |
| Replay semantics | orchestration/store | duplicate key/candidate tests | no duplicate ref; conflict on changed payload |
| Contract realism | adapter/fixture | generated contract fingerprint + fixture parse | no handwritten definition model |
| No graph/corpus mutation | integration test/diff | mutation spies + path check | zero writes |

Required commands, re-anchored to actual tests:

```bash
uv run pytest tests/test_statblock_candidate_generation.py tests/test_statblock_candidate_routes.py -q
uv run pytest tests/test_threat_draft_store.py tests/test_threat_draft_routes.py -q
cd apps/live-control-ui && npm test -- --run src/api/liveApi.test.ts src/contracts/dungeonbuddy-statblocks-v1/dungeonbuddyStatblockV1Contract.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use existing API tools: create a draft, generate using its current version against a configured test/dev Server, read the candidate by ID, then edit the draft and prove generation with the old version is rejected before downstream call. Capture IDs and statuses, not authored prose or secrets.

## §8 Required handback

Include actual Server operation IDs/routes, captured fixture provenance, request mapping table, base/head SHAs, changed paths, command results/provenance, live IDs/statuses, baseline failures, waivers, and confirmation that images/renderer/persistence/graph remain false.

## §9 Acceptance rubric

- [ ] One exact draft version maps to one traceable request.
- [ ] Every outcome carries draft/version/request identity.
- [ ] Success is reloadable without treating cache as authority.
- [ ] Stale versions fail before downstream calls.
- [ ] Failures leave authored fields/version unchanged.
- [ ] Replay and uncertain post-success cache failure are truthful.
- [ ] Generated contract types/real fixtures are used.
- [ ] Images are disabled.
- [ ] No renderer, editor, accepted mechanics, graph, Markdown, combat, or media selection ships.

## §10 Reviewer protocol

Review the exact-source invariant before code style. Compare the real Server fixture and request mapping. Search for `latest`, mock fallbacks, corpus reads, image flags, direct browser Server calls, and definition-shaped handwritten dictionaries.

## §11 Re-review protocol

Re-run stale, timeout, replay, malformed-response, and reload tests after every correction. Verify no fix mutates authored draft fields or adds UI presentation.

## Stop conditions

Stop if:

- the Server lacks a candidate-read route and expiry makes the proposed cache insufficient for declared reload semantics;
- the generated contract cannot be consumed without a second mechanics schema;
- graph context requires hidden corpus discovery rather than explicit authorized pointers;
- idempotency behavior is absent or contradicts the design;
- downstream success can be lost without any durable candidate locator;
- a path outside the allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW01–02` merge.
- [ ] Capture real Server success and error vocabulary.
- [ ] Confirm candidate cache is disposable/non-authoritative.
- [ ] Confirm `SBW04+` remain unimplemented.
