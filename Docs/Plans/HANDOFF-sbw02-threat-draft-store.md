# HANDOFF — SBW02 Versioned ThreatDraft store and CRUD API

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW01` merges and this handoff is re-anchored to the actual base SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw02-threat-draft-store.md`  
**Workstream:** `SBW02`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch exactly one implementation capability. The worker must not compress this handoff into a smaller prompt or absorb generation, candidate caching, graph publication, rendering, or corpus promotion.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Failure model changed? | Decision |
|---|---:|---:|---:|---:|---|
| Persist a versioned non-canonical threat concept | Yes | Yes | No | Yes | Include |
| Generate a statblock candidate | Yes | Yes | No | Yes | Successor `SBW03` |
| Replace the current workbench UI | Yes | No | Yes | Yes | Successor `SBW04` |
| Publish a Threat to the World Graph | Yes | Yes | Yes | Yes | Successor `SBW09` |
| Migrate legacy statblock draft artifacts | Yes | Yes | Potentially | Yes | Reject from this slice |

**Selected capability:** DungeonBuddy can create, read, list, update, and reload one strictly versioned `ThreatDraftV1` without invoking DungeonMindServer or mutating graph/corpus truth.

**Why the included work is one capability:** the model, repository, routes, and tests establish one invariant: authored threat prose has durable identity and optimistic revision semantics independent of downstream generation.

## §1 Mission

A GM-facing caller can persist and revise a non-canonical threat concept so authored work survives reload and provider failure before any statblock candidate exists.

**Invariant**

```text
A ThreatDraft is a DungeonBuddy-owned, versioned, non-canonical record; every successful authored update preserves draft_id and increments version exactly once.
```

**Mission falsification test**

```text
This is not one slice if implementation must also call DungeonMindServer, store GeneratedStatblockCandidateV1, render a statblock, promote Markdown, or write the World Graph.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/DESIGN-threat-statblock-authoring-projection-workflow.md` §4.1; `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` `SBW02` |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; canonical handoff template |
| Base revision | Re-anchor to merged `main` SHA after `SBW01`; record immutable SHA in PR body |
| Predecessor contract | `SBW01` configuration/route conventions only; no downstream call is required in this slice |
| Exact input consumed | Strict create/update request payloads containing authored fields and graph-context pointers |
| Named successor | `SBW03` exact-draft-version generation |
| What remains false | No candidate exists; no mechanics are validated or saved; no graph object exists |
| Explicit non-goals | UI replacement, candidate cache, generation, Server changes, graph writes, Markdown, combat, media, legacy migration |

Read in order:

1. `Docs/Design/DESIGN-threat-statblock-authoring-projection-workflow.md`
2. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
3. merged `SBW01` implementation and tests
4. `apps/live_control_server/services/workspace_document_registry.py` for file-backed atomic/versioned-store precedent
5. `apps/live_control_server/routes/workspace_documents.py` for route conventions
6. existing statblock draft service/routes only to identify predecessor ownership, not to reuse Markdown-first semantics

Authority precedence:

```text
1. active repository architecture and accepted decisions
2. active tracker
3. this checked-in handoff
4. merged implementation and tests
5. attached/Project Source context
6. chat summaries
```

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Create draft | Transitional statblock artifact flow is Markdown-oriented | Create strict `ThreatDraftV1` version 1 | Yes | repository/service + route |
| Read exact draft | No dedicated domain record | Read by exact `draft_id` | Yes | repository/service + route |
| List drafts | Legacy artifact list does not express ThreatDraft lifecycle | Return bounded summaries ordered deterministically | Yes | repository/service + route |
| Update current version | No optimistic ThreatDraft update | Require `expected_version`; increment once | Yes | repository/service |
| Stale update | Not defined | Return typed 409; write nothing | Yes | repository/service + route |
| Restart/reload | Legacy artifacts may reload, but wrong contract | Exact record round-trips from durable store | Yes | repository |
| Invalid graph pointer | Permissive or absent | Reject malformed revision/node/anchor pointer | Yes | request/domain validation |
| Provider unavailable | Irrelevant today | No downstream call; draft operations remain available | Yes | service |
| Duplicate create request | Undefined | Creates a distinct draft unless explicit idempotency key is intentionally added; do not infer identity from name | Yes | service |

## §4 Files in scope — allowlist

Expected paths; re-anchor exact names after `SBW01` merges.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/threat_draft.py` | Strict versioned domain/request/response models |
| Create | `apps/live_control_server/services/threat_draft_store.py` | Atomic durable repository and optimistic update |
| Create | `apps/live_control_server/routes/threat_drafts.py` | CRUD/list API boundary |
| Modify | `apps/live_control_server/main.py` | Mount the narrow router |
| Create | `tests/test_threat_draft_store.py` | Persistence, identity, version, atomicity proof |
| Create | `tests/test_threat_draft_routes.py` | Route status and strict payload proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | Only if generated/consumer route types are needed now; no UI feature |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Only if a typed client seam is required by a route-contract test |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Only with the two preceding paths |

### Bounded discovery exception

```text
Directory: apps/live_control_server/services/ and src/live_play/
Maximum additional paths: 2
Allowed path kinds: existing atomic JSON writer/config helper imported by the new store
Decision rule: include only when the existing helper already owns atomic-write or repo-root behavior required by the mission
Required report: name the path and why copying the helper would create a second persistence implementation
```

## §5 Explicitly out of scope

| Path or capability | Why excluded |
|---|---|
| `StatblockWorkbenchModule.tsx` | UI replacement is `SBW04` |
| DungeonMind statblock client calls | Generation is `SBW03` |
| `GeneratedStatblockCandidateV1` cache | Candidate lifecycle is `SBW03` |
| graph authoring/Kernal files | Publication is `SBW08–09` |
| corpus Markdown writer/promotion | ThreatDraft is not corpus truth |
| combat state | `SBW13` |
| asset/media storage | `SBW14+` |
| migration of `StatblockDraftArtifactView` | Legacy cleanup occurs when the normal UI is replaced |

## §6 Implementation contract

```text
Input:
  create: authored identity, description, generation intent, encounter context, graph-context pointers
  update: draft_id + expected_version + complete replacement of mutable authored fields

Output:
  strict ThreatDraftV1 or bounded ThreatDraftSummaryV1 list

Invariant:
  successful update preserves draft_id and increments version exactly once

Failure behavior:
  invalid payload -> 422, no write
  unknown draft_id -> 404
  expected_version mismatch -> 409, no write
  corrupted stored record -> fail closed with typed integrity error; do not overwrite
  atomic write failure -> prior readable version remains authoritative

Replay / idempotency:
  same create input -> a new draft unless an explicit client-generated draft_id contract is approved in-slice
  same update with old expected_version -> 409 after first success
  retry after uncertain response -> read exact draft before deciding whether to resubmit
  duplicate delivery -> never increments twice under the same expected_version

Trust boundary:
  Verifies: schema, bounded strings/lists, ID syntax, campaign/world/focus shape, pointer shape, expected version
  Records without proving: authored prose truth, whether selected graph nodes are semantically relevant
  Rejects: absolute paths, arbitrary URLs, copied source bodies, unknown extra fields
```

### §6A State and fallback matrix

| Path | Initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Create | Load/create store directory | version 1 record | N/A | Repo storage unavailable → fail, no phantom draft | fail closed | N/A | safe; may create distinct record, caller must use returned ID |
| Read | Load file/index | exact record | 404 | fail typed | fail closed, preserve file | N/A | safe |
| List | Load index/records | deterministic summaries | empty list | fail typed | fail closed; do not omit corrupt record silently | N/A | safe |
| Update | Read exact record | version +1 | 404 | fail typed | fail closed | 409 | read then retry against current version |

No fallback to corpus Markdown, legacy artifact directories, localStorage, or mock data is permitted.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Exact ID | Generated opaque `draft_id`; validate syntax | none | No | filename/index key derives safely from ID |
| Name/label | Display only | duplicate names allowed | No | never resolves identity |
| Slug hint | Advisory field only | collisions allowed | No | never used as key |
| Rename | Update `name`, preserve `draft_id` | none | No | version increments |
| Delete | Not implemented in this slice | N/A | No | record remains |
| Rebind campaign/world | Prohibited after creation unless design explicitly allows and tests it | reject | No | prevents identity drift |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Create | Versioned JSON record under bounded DungeonBuddy state root plus index if needed | strict model equality excluding serialization-normalized timestamps | new ID/new record | schema literal `dmb_threat_draft_v1`; unknown future schema rejected | delete incomplete temp; no partial visible record |
| Update | Atomic replacement of one record | all unchanged fields preserved; version +1 | stale expected version rejected | no migration of legacy artifact format | prior file remains if replace fails |
| Read/list | Parsed strict model | no permissive field dropping | safe repeat | corrupt/unknown schema fails explicitly | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** design §4.1 and current workspace-document atomic/version conventions.

| Predecessor/design field | Shape | ThreatDraft field/behavior | Transformation | Proof |
|---|---|---|---|---|
| `draft_id` | opaque string | durable identity | generated once | store test |
| `version` | positive integer | optimistic concurrency | start 1, increment once | stale/reload tests |
| `world_id`, `campaign_id` | bounded IDs | immutable scope | exact copy after validation | route/store tests |
| `focus` | optional session/prep lens | context only | strict nested model | model tests |
| `graph_revision_id` | opaque revision locator | snapshot pointer | exact copy; no graph read | round-trip test |
| `selected_node_ids` | bounded list | snapshot pointers | dedupe only if contract declares stable order; otherwise preserve | round-trip test |
| `admitted_source_anchor_ids` | bounded opaque IDs | snapshot pointers | exact copy; never source bodies | security test |

## §7 Verification ownership map

| Guarantee | Boundary | Required command/scenario | Expected evidence |
|---|---|---|---|
| Strict schema and forbidden extras | model/route | `uv run pytest tests/test_threat_draft_routes.py -q` | 422 and no write |
| Atomic create/update/reload | store | `uv run pytest tests/test_threat_draft_store.py -q` | exact round trip |
| Stale update writes nothing | store + route | focused tests | 409; prior digest/content unchanged |
| No downstream/graph/corpus mutation | service tests + diff inspection | fake call guards and changed-path check | zero calls; no changed corpus/graph path |
| Existing server suite remains green | repository | `uv run pytest tests/test_live_statblock_workbench_endpoint.py tests/test_workspace_document_registry.py -q` or re-anchored equivalents | no regression |
| Frontend contract, if touched | UI API | `cd apps/live-control-ui && npm test -- --run src/api/liveApi.test.ts` | typed request/response proof |

Run additionally:

```bash
git diff --check
git diff --stat <base>...HEAD -- <allowlisted paths>
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use an existing API client only: create a draft, restart the server process, read it, update with the prior version, then demonstrate the same update returns 409. Do not build a new panel.

## §8 Required handback

Include base/head SHAs, actual paths, focused diff, exact commands/results/provenance, live API proof, baseline failures, waivers, unexpected paths, stop conditions, schema example, and confirmation that no DungeonMind/graph/corpus call occurs.

## §9 Acceptance rubric

- [ ] One durable `ThreatDraftV1` capability is delivered.
- [ ] Create/read/list/update all obey the same identity/version invariant.
- [ ] Save/reload is proved at the store boundary.
- [ ] Stale writes are rejected without mutation.
- [ ] Names and slug hints never resolve identity.
- [ ] Graph context stores pointers only.
- [ ] No candidate, mechanics, graph, corpus, combat, or media behavior is introduced.
- [ ] No unexpected path changed.
- [ ] Legacy `StatblockDraftArtifactView` remains explicitly transitional, not silently migrated.

## §10 Reviewer protocol

Review the invariant first. Inspect persistent JSON and update failure injection. Search the diff for DungeonMind calls, graph writers, corpus writers, Markdown parsing, UI workflow changes, and name-based lookup. Any such behavior is scope expansion.

## §11 Re-review protocol

Re-run create/update/reload/stale tests after every fix. Verify fixes do not add migration, deletion, candidate fields, or a second persistence store.

## Stop conditions

Stop and report if:

- the chosen state root has no atomic-write precedent and selecting one changes broader storage architecture;
- graph-context pointers cannot be represented without copying source content;
- existing generic artifact storage cannot enforce strict schema/version semantics without a broad migration;
- campaign/world scope mutability remains unresolved;
- a path outside the allowlist is required;
- the slice would need candidate persistence to be useful.

## Final dispatch check

- [ ] Re-anchor to merged `SBW01` base SHA.
- [ ] Confirm route prefix and store root against current main.
- [ ] Confirm every matrix remains accurate.
- [ ] Confirm `SBW03` and later capabilities remain false.
