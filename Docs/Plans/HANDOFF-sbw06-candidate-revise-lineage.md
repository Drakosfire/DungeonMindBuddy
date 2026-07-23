# HANDOFF — SBW06 Candidate revise/regenerate and lineage

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch **after `SBW07` merges** as bites `SBW06-contract` → `SBW06a–d` (roadmap §5.1). Re-anchor base, routes, and generated types.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`  
**Workstream:** `SBW06`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability across a contract PR plus four code PRs: create a new candidate proposal from an exact source and preserve lineage. Do not persist mechanics, compare accepted revisions, update graph bindings, or generate media.

## Bite schedule

| Bite | PR mission | Allowlist focus | Still false |
|---|---|---|---|
| `SBW06-contract` | Doc-only: revise journal choice + lineage/status transition table | Docs only; no implementation | All code |
| `SBW06a` | Revise from edited `source_definition` | Client + revision service + tests | Status UI, accepted-revision source |
| `SBW06b` | Candidate-ref status + lineage persistence | Draft store/ref transitions + tests | UI, accepted-revision revise |
| `SBW06c` | Revise UI | Workbench + liveApi | Accepted-revision source |
| `SBW06d` | Revise from accepted `source_locator` | Service/route/tests using SBW07 locators | Graph, compare, media |

**Why after SBW07:** accepted-revision source needs exact locators; revise durability is deferred until first mechanics save is proven (SBW03 lesson).

## §12 Revise contract freeze (fill in `SBW06-contract` PR)

Before any `SBW06a+` code PR, the contract PR must publish:

1. Whether revise reuses the SBW03 generate journal or a **separate** revise operation journal (recommendation: separate journal keyed by revise `request_id`, reusing Server durable-code terminality patterns without reopening generate semantics).
2. Closed status transition table for `ThreatDraftCandidateRefV1.status`.
3. Partial-completion rule: Server revise success + local ref-write failure → truthful recoverable state.
4. Source mutual exclusion: `source_definition` XOR `source_locator`; no latest/display-name fallback.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Revise/regenerate from exact edited definition or accepted revision | Yes | Yes | Yes | Include |
| Preserve candidate lineage and superseded/rejected statuses | No; required for truthful revision | Yes | Yes | Include under same invariant |
| Save immutable mechanics | Already required | Yes | Yes | **Predecessor `SBW07` (must be merged first)** |
| Compare accepted revisions | Yes | No | Yes | Successor `SBW13` |
| Upgrade graph bindings/embeds | Yes | Yes | Yes | Successor `SBW14` |

**Selected capability:** the GM can ask for a revised candidate from one exact source while every prior proposal remains identifiable and inspectable.

## §1 Mission

A GM can produce a new typed candidate from an exact working definition or accepted revision so model-assisted iteration never silently overwrites earlier proposals or durable mechanics.

**Invariant**

```text
Every revise/regenerate operation creates a new candidate_id whose lineage names one exact source and explicit revision instructions; prior candidates and accepted revisions are never mutated.
```

**Mission falsification test**

```text
This is not one slice if implementation must also create/append a durable statblock revision, compare accepted revisions, change graph bindings, or manage images.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §6.4; tracker `SBW06`; DungeonMindServer revise-candidate contract |
| Repository rules | `AGENTS.md`; external-agent PR loop rules/template |
| Base revision | Actual merged SHA containing `SBW01–05` **and `SBW07`** |
| Predecessor contract | Exact candidate refs; complete typed editor working copy; validation digest/receipt state; **`SBW07` accepted-mechanics locators for `source_locator` revise** |
| Exact input consumed | Source kind + exact source locator/value + explicit revision instructions + request/idempotency key |
| Named successor | `SBW13` accepted revision append/compare (not `SBW07` — save precedes this slice) |
| What remains false | New candidate remains a proposal; no new mechanics identity or graph truth is changed |
| Explicit non-goals | First immutable save (already `SBW07`), append accepted revision, compare view, graph, embed, combat, media, silent latest selection |

Read in order:

1. integration design and tracker
2. merged `SBW05` editor/validation contracts
3. merged `SBW07` accepted-mechanics ref / locator contract
4. current DungeonMindServer revise-candidate generated API/types/fixtures
5. `SBW03` generation/cache/ref lifecycle
6. workbench candidate state tests

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Revise edited working copy | No model iteration | Submit complete typed definition + instructions | Yes | service/route/UI |
| Revise exact accepted revision | Not yet productized | Submit exact statblock/revision locator + instructions | Yes | service/route/UI |
| Preserve selected elements | Undefined | Explicit preserve keys/sections option when Server supports it | Yes | request mapper |
| Success | Potential replace-in-place UX | New candidate ref; prior source remains | Yes | orchestration/store/UI |
| Provider failure | Could lose working state | Typed error; source and instructions retained | Yes | service/UI |
| Stale source | Undefined | Reject before call or map Server conflict; no silent latest | Yes | service |
| Supersede/reject candidate | Not modeled fully | Explicit review-status transition; mechanics unchanged | Yes | draft candidate-ref store |
| Duplicate/replay | Undefined | Stable idempotency and candidate-ref dedupe | Yes | orchestration/store |
| Reload lineage | No product lineage view | Exact parent/source/status visible after reload | Yes | store/UI |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/models/statblock_candidate_workflow.py` | Strict revise request/lineage/status types |
| Create/Modify | `apps/live_control_server/services/statblock_candidate_revision.py` | Exact source mapping and downstream orchestration |
| Modify | `apps/live_control_server/services/statblock_candidate_cache.py` | Store/read new candidate and lineage metadata |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Atomic candidate-ref status/lineage update |
| Modify | `apps/live_control_server/routes/statblock_candidates.py` | Revise and status-transition endpoints |
| Create | `tests/test_statblock_candidate_revision.py` | source/stale/replay/failure proof |
| Modify | `tests/test_statblock_candidate_routes.py` | route/status proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | revise/status request/response types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | revise/status calls |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | mapping proof |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | revision instructions, lineage, supersede/reject UX |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | workflow and failure preservation proof |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package and generated v1 contract fixtures
Maximum additional paths: 3
Allowed path kinds: adapter method, generated type export, one captured revise success/error fixture
Decision rule: required to consume the current Server revise contract exactly
Required report: identify exact source variants and idempotency/error vocabulary
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| create first immutable statblock revision | Predecessor `SBW07` (already merged; this slice consumes locators only) |
| append accepted child revision | `SBW13` |
| accepted revision comparison | `SBW13` |
| preferred/binding/embed upgrade | `SBW14` |
| graph publication | `SBW08–09` |
| image generation or selection | `SBW16–17` |
| merge divergent revision branches | later design if dogfood requires it |
| automatic overwrite of active candidate | prohibited by invariant |

## §6 Implementation contract

```text
Input:
  source_kind = edited_definition | candidate | accepted_revision
  exact source payload/locator
  revision_instructions
  preserve_element_keys / preserve_sections when supported
  draft_id + expected draft version/status token
  idempotency/request ID

Output:
  new GeneratedStatblockCandidateV1
  lineage record naming exact source, request, instructions digest, and timestamps
  explicit review status updates for source candidate when requested

Invariant:
  new candidate identity; exact source remains unchanged and inspectable

Failure behavior:
  stale draft/status/source -> conflict before unsafe state change
  missing exact revision/candidate -> not found; no fallback to latest
  validation/provider/refusal/timeout -> typed failure; source/editor/instructions retained
  malformed result -> fail closed; no active candidate ref appended
  downstream success + local ref-write failure -> truthful partial completion retaining candidate locator for reconciliation

Replay / idempotency:
  same idempotency key + same exact source/instructions -> same result
  same key + changed source/instructions -> conflict
  new key -> new candidate proposal
  duplicate candidate response -> ref dedupe by candidate_id

Trust boundary:
  Verifies: exact source identity/digest, complete typed definition, instruction bounds, generated response shape
  Records without proving: whether revision improves balance or fulfills intent
  Rejects: display-name source selection, implicit latest, hidden corpus search, in-place candidate mutation
```

### Lineage decisions

- `source_kind=edited_definition` records the submitted definition digest and originating candidate/draft version; it does not persist the full working copy as a new authority beyond existing candidate cache needs.
- `source_kind=accepted_revision` requires exact `statblock_id` + `revision_id` + expected digest when available.
- Source candidate status may transition `active -> superseded|rejected|accepted_source`; transitions are explicit and atomic. A new candidate does not automatically reject its source.
- Lineage is review metadata and must remain distinct from Server generation provenance while preserving both.
- Instructions are bounded user content; logs record digest/length, not full hidden prose.

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Downstream unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Revise edited definition | retain working copy | new candidate/ref | N/A | typed failure; edits retained | fail closed | stale draft/status conflict | idempotent by key |
| Revise candidate | exact source read | new candidate/ref | 404 | typed failure | fail closed | expired/superseded policy explicit | new key for new proposal |
| Revise accepted revision | exact revision read | new candidate/ref | 404 | typed failure | digest mismatch fail | stale/missing exact source | safe |
| Status transition | current ref load | atomic transition | 404 | N/A | fail closed | invalid transition conflict | same transition idempotent |

No fallback to current/latest candidate or revision.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Source candidate | exact `candidate_id` | none | No | immutable source ref |
| Edited definition | deterministic digest + originating candidate/draft locator | mismatch = stale | No | lineage source |
| Accepted revision | exact statblock/revision IDs and digest | none | No | no latest |
| New candidate | exact returned candidate ID | collision with different payload = integrity failure | No | new ref |
| Instructions | digest over normalized bounded text/options | changed instructions distinct | No | replay key input |
| Display name | informational | duplicates irrelevant | No | never selection key |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Recovery |
|---|---|---|---|---|---|
| Append lineage/ref | versioned draft candidate-ref metadata | source/new IDs/status preserved | dedupe new candidate ID | additive schema version | reconcile by candidate ID/request ID |
| Status transition | atomic ref update | exact status retained | same transition idempotent | invalid transitions rejected | reread current draft |
| Revision request replay | idempotency record/downstream contract | same source/instructions | same result; changed conflict | real Server semantics preserved | exact-read candidate |

### §6D Predecessor-to-consumer mapping

**Grounding source:** current generated revise-candidate request/response and error fixtures.

Required implementation mapping:

| Predecessor field/outcome | Consumer behavior | Rule | Proof |
|---|---|---|---|
| source definition or exact revision locator | mutually exclusive source variant | no implicit latest | fixture tests |
| revision instructions | bounded request field | exact copy/normalization declared | request snapshot |
| preserve element keys/options | explicit controls | pass only supported values | fixture |
| candidate ID/receipts | new candidate/ref | preserve exact IDs | route test |
| source/provenance | lineage disclosure | preserve Server + Buddy metadata separately | reload test |
| conflict/not found/refusal | typed UI state | stable mapping | error fixtures |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| New candidate never overwrites source | service/store | focused tests | distinct IDs; source readable |
| Exact source/no latest fallback | service | stale/missing source tests | typed 404/409; zero alternate read |
| Working state retained on failure | UI/service | timeout/refusal tests | edits/instructions remain |
| Status transitions valid/idempotent | store/route | transition matrix tests | invalid conflict; same safe |
| Replay semantics | integration | duplicate/changed key tests | same result or conflict |
| Lineage reload | store/UI | reload test | exact source/instruction digest visible |
| Real Server contract | adapter/fixture | contract/fingerprint tests | no invented fields |

Required commands:

```bash
uv run pytest tests/test_statblock_candidate_revision.py tests/test_statblock_candidate_routes.py -q
cd apps/live-control-ui && npm test -- --run src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

From the existing workbench, revise one edited attack with explicit instructions, show a new candidate ID and lineage, inspect the original candidate, then simulate timeout and prove the edited definition/instructions remain. Reject or supersede one candidate and reload.

## §8 Required handback

Include source-variant mapping, transition table, base/head, actual paths, commands/results/provenance, live candidate IDs/statuses, partial-completion handling, baseline failures/waivers, and confirmation that no mechanics save/graph/compare/upgrade/media ships.

## §9 Acceptance rubric

- [ ] Every revision creates a new candidate ID.
- [ ] Exact source and instruction digest are reloadable.
- [ ] No latest/display-name fallback exists.
- [ ] Prior candidates and accepted revisions remain unchanged.
- [ ] Failure retains editor/source/instructions.
- [ ] Status transitions are explicit, validated, and replay-safe.
- [ ] Downstream-success/local-failure state is recoverable and truthful.
- [ ] No immutable save, accepted compare, graph update, or media capability ships.

## §10 Reviewer protocol

Trace source identity and every state transition. Search for assignment replacing candidate bodies, `latest`, name matching, auto-reject, silent source switching, and save/append calls.

## §11 Re-review protocol

Re-run all source variants, transition matrix, replay, stale, timeout, and partial-completion tests after every fix.

## Stop conditions

Stop if:

- Server revise semantics cannot identify an exact source;
- the candidate cache/ref model cannot preserve lineage/status distinctly;
- an accepted revision source requires implicit latest;
- idempotency is undefined for revise operations;
- a new candidate cannot be recovered after downstream success/local write failure;
- a path outside the allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW07` (and `SBW05`).
- [ ] Capture real revise fixtures and source variants.
- [ ] Confirm first-save is already true via `SBW07`; graph, compare, upgrade, and media remain false.
- [ ] `SBW06-contract` transition table approved before `SBW06a+` code.
