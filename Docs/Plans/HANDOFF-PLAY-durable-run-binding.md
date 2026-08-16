---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P2A
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-durable-run-binding.md
  - Branch / PR: agent/play-durable-run-binding / `PLAY: bind durable Run to exact Playable revision`

  ## Verification pointer
  - Design anchor: `bb937f4a0792e51d2dc7d73132c20253c0becf47` (merge of PR #594)
  - Base/head: `0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96` / <implementation head>
  - Predecessor: merged PR #595 state sync after PR #594 / P1C Choice+Option identity
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — durable Run binding to exact Playable revision

**Created:** 2026-08-15  
**Status:** ACTIVE IMPLEMENTATION / MERGE BLOCKED — PR #595 satisfied the state-sync/base gate; CODE was dispatched from the exact pinned base, while required executable §7/preflight evidence remains outstanding.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P2A`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #594 at `main` `bb937f4a0792e51d2dc7d73132c20253c0becf47`  
**Implementation base:** `0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96`  
**Suggested branch:** `agent/play-durable-run-binding`  
**PR title:** `PLAY: bind durable Run to exact Playable revision`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — state sync and base pin satisfied; executable preflight evidence outstanding

PR #595 completed the post-PR-#594 mutable state-authority sync and merged to `main` as:

```text
0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96
```

That merge:

- recorded P1C / PR #594 as merged;
- decomposed P2 into P2A / P2B / P2C;
- made P2A the current next slice;
- checked in this handoff;
- kept Runtime DungeonMindBuddy Play-owned;
- kept `WorkObjectElementRef` unjustified;
- made no stable architecture change.

The P2A lane was re-anchored against that exact SHA before code changes. The branch `agent/play-durable-run-binding` was created directly from it, the roadmap still named P2A as next, and the workspace snapshot/lock/persistence seams were re-read before implementation.

Required P2 decomposition remains:

```text
P2A — durable Run identity + exact Playable revision/digest binding
P2B — durable element-referenced Run progress
       current Scene/Beat, resolved Beats, selections, notes
P2C — explicit Run rebase/migration to a newer Playable revision
       with fail-closed missing/replaced reference handling
```

`linkedRuntimeHandles` stays deferred until a real Combat/other runtime consumer requires it.

The canonical executable preflight remains:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-durable-run-binding.md
```

The current stewardship environment can inspect and mutate the repository through the GitHub connector but does not provide a runnable repository checkout/`gh` environment. Connector-backed re-anchor, open-PR/branch collision review, and §4 changed-path checks were performed, but those are **not** recorded as a passing invocation of `steward_preflight.py`. The command remains required merge evidence and is an explicit blocker until independently produced.

The dispatch pin is handoff completion, not capability expansion.

---

## §1 Mission and merge-ready invariant

**Mission:** DungeonBuddy can durably create, reload, and discover an opaque Run that is bound to one exact committed Playable Runbook revision and content digest, so later mutable table progress has a truthful Runtime authority instead of being stored in the Playable document or inferred from labels.

**Merge-ready invariant:**

> **For one caller-chosen opaque Run UUID, DungeonBuddy either durably records exactly one immutable binding to one admitted committed Runbook workspace-document identity + revision + content SHA, or it makes no Run; replaying the same Run UUID with the same exact binding is idempotent, reusing that Run UUID for a different binding fails closed, persisted records survive process restart, and P2A creates no element progress, Playable mutation, World write, Combat state, or second copy of Playable structure.**

### Why P2 is split before implementation

The architecture requires a Run eventually to reference:

```text
currentSceneId
currentBeatId
resolvedBeatIds
choiceId → optionId
notesByElementId
```

P1C proved those IDs exist on the client-side Playable grammar/index.

The live-control server does **not** currently own a canonical Playable structure resolver. Putting reference-bearing runtime fields into the first server Run PR would force one of two unsafe choices:

1. trust caller-supplied element IDs without owning-boundary validation; or
2. duplicate/reimplement the Playable Markdown/index grammar in Python without a deliberate authority decision.

P2A does neither.

It first establishes the durable Runtime identity, exact Playable binding, persistence location, retry semantics, and API boundary. P2B must then design exact element-reference admission from the real consumer pressure created by this Run authority.

### What P2A learns from PR #578

Keep as evidence:

- Run state is valuable as a separate persisted table-time object;
- file-backed runtime state under `out/` is sufficient for the current product scale;
- JSON is useful for review/debugging after a session;
- run identity must be path-safe.

Reject from the prototype:

- adventure-specific `campaign_id`, `adventure_id`, and default scene values;
- hardcoded branch enums such as `hill | alchemist | guild`;
- implicit default Run creation on GET;
- human-semantic run IDs as authority;
- blind last-writer-wins PUT of the whole mutable state document;
- storage under authored `out/workspace` semantics.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every P2A path answers whether one opaque Run UUID has one exact durable Playable binding, or no mutation occurs. |
| Most likely adversarial sequence | Caller reads Runbook revision N → Runbook advances to N+1 → caller attempts Run creation using expected N/digest N. Creation must reject 409 rather than silently bind N+1. |
| Will §7 detect it? | Yes. Required route/service tests use the real workspace snapshot authority and stale expected revision/digest cases. |
| Easiest owner to under-test | Retry/idempotency. A lost successful response followed by the same PUT must return the existing Run, not create another or mutate timestamps/revisions. |
| Fact that forces stop/split | If exact binding requires parsing Scene/Beat/Choice/Option structure, adding progress state, modifying workspace-document schema/writer, or inventing a generic shared work-object reference, stop. Those are successors/hoist decisions, not P2A. |

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Exact Run → committed Runbook revision/digest binding | Yes | Yes | **Include** |
| Opaque Run UUID + idempotent create replay | No, integrity of same capability | Same contract | **Include** |
| Durable restart/reload | No, durability clause | Same contract | **Include** |
| List/discover Runs by campaign / Playable artifact | No, resume/discovery clause | Same API family | **Include** |
| Monotonic `run_revision` starting at 1 | No, concurrency envelope for successor writes | Same Run record | **Include** |
| Current Scene / Beat | Yes | New mutable runtime contract | **Exclude — P2B** |
| Resolved Beats | Yes | New mutable runtime contract | **Exclude — P2B** |
| Choice selections | Yes | New mutable runtime contract | **Exclude — P2B** |
| Element notes | Yes | New mutable runtime contract | **Exclude — P2B** |
| Explicit Playable rebase/migration | Yes | New lifecycle transition | **Exclude — P2C** |
| Linked Combat/runtime handles | Yes | Cross-runtime linking contract | **Exclude until real consumer / P4** |
| Play UI | Yes | New operator workflow | **Exclude — P3** |
| Generic `WorkObjectElementRef` | Yes | Buddy-shared contract | **Exclude — hoist review only** |
| DungeonMind contract | Yes | Cross-repo kernel contract | **Prohibited** |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 Core invariant;
   - §7 Runtime State;
   - §7.1 Runtime invariants;
   - §11 Persistence and revision rules.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - P1C completion evidence;
   - P2;
   - hoist decision after P2.
3. `Docs/Plans/HANDOFF-PLAY-choice-option-identity.md`
   - exact predecessor identity contract.
4. `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`
5. `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts`
   - **read only in P2A**; P2A does not consume element structure yet.
6. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`
7. `apps/live_control_server/services/workspace_document_registry.py`
   - `WorkspaceDocumentSnapshot`;
   - `get_workspace_document_snapshot()`;
   - coherent `loaded_revision + content_sha256 + file_fingerprint`.
8. `apps/live_control_server/services/registry_file_lock.py`
9. `src/live_play/live_store.py`
10. PR #578 evidence only:
    - `apps/live_control_server/services/play_run_state.py`
    - `apps/live_control_server/routes/play_run_state.py`
11. `AGENTS.md`
12. `Docs/Process/STEWARD-CYCLE.md`

### Owning authority

P2A creates a new **Play Runtime** authority.

It does not become:

- workspace-document authority;
- Playable authority;
- source authority;
- graph authority;
- Combat authority;
- a generic work-object store.

The persisted Run record owns only:

- Run identity;
- immutable binding to the exact Playable version it began from;
- Runtime record revision/timestamps needed for later safe mutation.

### Admitted Playable in P2A

P2A intentionally starts with:

```text
workspace document kind == runbook
status == active
content_status == committed
exact loaded_revision supplied by caller
exact content_sha256 supplied by caller
```

This is a bounded first implementation of the architecture's broader “Playable Artifact” concept.

P2A must **not** claim that every `plan` or `worldbuilding_source` document is runnable merely because the generic editor can carry playable markers.

### Exact version identity

For P2A:

```text
playableArtifactId  := WorkspaceDocumentRecord.document_id
playableRevisionId  := (WorkspaceDocumentSnapshot.loaded_revision,
                        WorkspaceDocumentSnapshot.content_sha256)
```

Persist both components separately:

```text
playable_revision
playable_content_sha256
```

Do not persist `file_fingerprint` as version identity. It is an integrity/physical-file observation, not a stable content identity.

### Lane table

| Field | Required content |
|---|---|
| Base revision | `0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96` |
| Design anchor | `bb937f4a0792e51d2dc7d73132c20253c0becf47`, merge of PR #594 |
| Predecessor contract | P1A/P1B/P1C durable four-kind Playable identity/index plus existing workspace snapshot revision/digest authority |
| Exact input consumed | Caller Run UUID + exact committed Runbook workspace `document_id`, expected revision, expected content SHA |
| Output | One durable `PlayRunRecordV1` or fail-closed error with no new Run |
| Named successor | `P2B — durable element-referenced Run progress` |
| What remains false | No current Scene/Beat, resolved Beats, choice selection, notes, migration/rebase, linked runtime handles, Play projection/UI |
| Branch / isolated checkout | `agent/play-durable-run-binding` in isolated worktree/equivalent |
| Parallel collision hotspots | `apps/live_control_server/main.py`, active Playable roadmap; route namespace `/api/live/play-runs` |
| Runtime/state ownership | Test runtime must use a temp root. Production data lives only under `out/runtime/play/runs/`; do not point tests at the operator's real `out/`. |
| State-authority sync after merge | P2A handoff completion + living Playable hoist roadmap current sequence. Stable architecture only if evidence changes a claim. |

### Roadmap review is a merge gate

Before final PASS:

```text
Did P2A evidence change ownership, sequence, hoist posture, successor boundaries,
or assumptions in ROADMAP-playable-hoist-dungeonmind-kernel.md?
```

Record exactly one:

```text
ROADMAP_REVIEW — UPDATED
...
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
...
```

The roadmap ledger names the implementation/evidence head, not a later bookkeeping SHA.

Required observation:

```text
P2A_HOIST_OBSERVATION
- Did exact Run→work-object revision/digest binding become useful outside Play Runtime?
- Is a generic WorkObjectRevisionRef justified now? yes/no/not yet
- Is WorkObjectElementRef justified now? yes/no/not yet
- Did P2A discover a real need for server-owned Playable element resolution?
- DungeonMind relevance discovered? none / exact future audit question only
```

Default expected disposition remains **not yet**.

---

## §3 Observable paths and adversarial sequences

### Canonical P2A API

Prefix:

```text
/api/live/play-runs
```

#### Create or replay one Run

```http
PUT /api/live/play-runs/{run_id}
```

Request:

```json
{
  "playable_artifact_id": "workspace-document-uuid",
  "expected_playable_revision": 7,
  "expected_playable_content_sha256": "64-lowercase-hex"
}
```

`run_id` is an opaque UUID supplied by the caller for replay-safe creation. It is equality-only and must not encode campaign, session, title, or adventure semantics.

#### Read one Run

```http
GET /api/live/play-runs/{run_id}
```

#### Discover Runs

```http
GET /api/live/play-runs
GET /api/live/play-runs?campaign_id=<campaign>
GET /api/live/play-runs?playable_artifact_id=<workspace-uuid>
GET /api/live/play-runs?campaign_id=<campaign>&playable_artifact_id=<workspace-uuid>
```

No endpoint in P2A mutates an existing Run's semantic state or binding.

### Canonical persisted record

```text
schema_version: dmb_play_run_record_v1
run_id: <canonical UUID>
campaign_id: <derived from admitted Runbook record>
playable_artifact_id: <exact workspace document UUID>
playable_revision: <exact loaded_revision at admission>
playable_content_sha256: <exact normalized Markdown SHA-256>
run_revision: 1
created_at: <ISO-Z>
updated_at: <same as created_at in P2A>
```

`campaign_id` is copied only as immutable Runtime tenancy/discovery metadata. It is derived from the admitted Runbook record; the caller does not author it.

`run_revision` starts at 1. P2A does not yet expose a mutation that increments it. P2B must use it as the expected-revision/CAS boundary for progress writes rather than adding a second concurrency token later.

### Persistence root

Permanent runtime path:

```text
out/runtime/play/runs/{run_id}.json
```

Rationale:

- outside authored workspace-document storage;
- outside World/Source/Combat authorities;
- one file per Run avoids a hot whole-registry rewrite during future table-time progress updates;
- human-inspectable dogfood/debugging remains possible;
- atomic sibling-temp + replace can reuse `src/live_play/live_store.write_json`.

Do not use the #578 path:

```text
out/workspace/play/{run_id}.json
```

because `workspace` is the authored work-object authority and Runtime must remain separate.

### Binding admission

For a new Run UUID:

1. load one coherent `WorkspaceDocumentSnapshot`;
2. require exact `document_id`;
3. require `record.kind == "runbook"`;
4. require `record.status == "active"`;
5. require `record.content_status == "committed"`;
6. require `file_exists == true`;
7. require caller `expected_playable_revision == loaded_revision`;
8. require caller normalized SHA exactly equals `content_sha256`;
9. derive `campaign_id` from the admitted record;
10. persist the Run atomically.

No Playable Markdown is parsed or copied into the Run record.

### Idempotent replay

If `{run_id}.json` already exists:

- validate the persisted record first;
- if its exact immutable binding matches the request, return it unchanged;
- do **not** update `updated_at`;
- do **not** increment `run_revision`;
- do **not** require the Runbook to still be the current workspace revision merely to acknowledge an already-successful create replay;
- if the same Run UUID names any different binding, return **409**.

This is necessary for:

```text
create committed successfully
→ HTTP response lost
→ caller retries same PUT
```

The retry must not create another Run and must not rewrite history.

### Observable path table

| Path | Required behavior | Owning boundary |
|---|---|---|
| Exact create | Persist one exact Run binding | Run service + workspace snapshot |
| Same PUT replay | Return exact existing record unchanged | Run service |
| Same Run UUID, different artifact | 409, no mutation | Run service |
| Same Run UUID, different revision/digest | 409, no mutation | Run service |
| Stale expected Playable revision | 409, no Run | workspace snapshot admission |
| Stale expected content SHA | 409, no Run | workspace snapshot admission |
| Non-runbook document | 422, no Run | Run admission |
| Draft Runbook | 409, no Run | Run admission |
| Discarded Runbook | 409, no Run | Run admission |
| Missing/corrupt committed target | propagate truthful fail-closed workspace integrity error | workspace snapshot authority |
| GET after restart | Exact persisted record | file-backed Run authority |
| List after restart | Exact persisted records, deterministic ordering | Run authority |
| Invalid Run UUID | 422 | route/service identity validation |
| Unknown Run UUID | 404 | Run authority |
| Malformed persisted Run JSON | 500; never default/reset/skip silently | Run authority |
| Existing P1 Playable document | Never modified | workspace/Playable authority |

### Adversarial sequences

| Sequence | Required safe outcome | §7 proof |
|---|---|---|
| read revision N → Runbook commits N+1 → PUT expecting N | 409; no Run file | stale revision route test |
| read digest A → bytes differ/digest B → PUT expecting A | 409; no Run | stale digest test |
| successful PUT → lose response → identical PUT | same record; `run_revision=1`; timestamps unchanged | replay test |
| successful PUT A → same Run UUID with artifact/revision B | 409; A remains byte/semantic authority | collision test |
| create → process/service restart → GET | exact same record | persistence/reload test |
| create two different Run UUIDs for same Runbook revision | both allowed; Runs are distinct table executions | multi-run test |
| malformed on-disk JSON → GET/list | explicit 500; never synthesize default | corruption test |
| Runbook later advances | P2A stored binding remains unchanged; no automatic rebind | immutable binding regression |
| GET existing Run after Runbook later advances | return stored Run; do not silently rewrite binding | immutable binding regression |

---

## §4 Files in scope — write lease

Expected changed paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md` | P2A checked-in slice authority |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Mandatory P2A review-ledger disposition only; current-sequence/P2 decomposition is synchronized before dispatch |
| Create | `apps/live_control_server/services/play_run_registry.py` | Run identity, exact binding admission, file-backed persistence, list/read/idempotent create |
| Create | `apps/live_control_server/routes/play_runs.py` | P2A `/api/live/play-runs` API |
| Modify | `apps/live_control_server/main.py` | Register the one new router |
| Create | `tests/test_play_run_registry.py` | Owning service/persistence/adversarial proof |
| Create | `tests/test_live_play_runs.py` | HTTP status/shape/idempotency/integration proof |

### Bounded discovery exception

```text
Directory:
  tests/

Maximum additional paths:
  2

Allowed path kinds:
  focused test fixture/helper only

Decision rule:
  required solely to exercise the same P2A API/persistence invariant against
  temporary workspace/run roots; no production owner, schema, UI, or new workflow.
```

A required **production** path outside the explicit lease is a stop report.

### Deliberate non-lease

P2A may read but must not modify:

```text
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/registry_file_lock.py
src/live_play/live_store.py
apps/live-control-ui/src/**
apps/live_control_server/services/combat_state.py
apps/live_control_server/routes/live.py
```

If P2A requires changes to workspace snapshot, lock, generic JSON writer, UI API types, or Playable grammar/index to succeed, stop and re-brief.

---

## §5 Explicitly out of scope / collision boundary

| Concern | Why excluded |
|---|---|
| Scene/Beat/Choice/Option validation | P2B must solve server/reference admission deliberately |
| `currentSceneId` / `currentBeatId` | Mutable progress successor |
| `resolvedBeatIds` | Mutable progress successor |
| `selections` | Mutable progress successor |
| `notesByElementId` | Mutable progress successor |
| Playable revision migration/rebase | P2C |
| historical Playable revision archive | Not established by current workspace authority; do not invent inside Runtime |
| Play UI / Beats panel | P3 projection/workflow |
| TypeScript `liveApi` wrappers/types | No UI consumer in P2A |
| Decision/Consequence / consequences | Authored Playable semantics; not Run binding |
| linked Combat handles | Real cross-runtime consumer later |
| Combat HP/initiative/conditions | Combat-owned |
| workspace document schema/writer | Existing authority consumed unchanged |
| Playable Markdown grammar/index | Existing P1 authority; no server clone in P2A |
| SourceArtifact/DungeonMind | No kernel/source contract in P2A |
| PR #578 `play_run_state.py` | Mining evidence only; do not cherry-pick adventure-specific schema |

---

## §6 Implementation contract

### Public service contract

```text
Input:
  run_id: canonical UUID
  playable_artifact_id: workspace document UUID
  expected_playable_revision: positive integer
  expected_playable_content_sha256: canonical SHA-256

Admission:
  coherent workspace snapshot
  kind=runbook
  status=active
  content_status=committed
  file_exists=true
  exact expected revision
  exact expected content SHA

Output:
  one immutable PlayRunRecordV1 binding

Invariant:
  same as §1

Failure:
  invalid IDs/input                 → 422, no mutation
  unknown playable document         → 404, no mutation
  non-runbook                       → 422, no mutation
  draft/discarded                   → 409, no mutation
  revision/digest mismatch          → 409, no mutation
  corrupt committed workspace bytes → truthful workspace error, no mutation
  same run_id / different binding   → 409, existing Run unchanged
  malformed persisted Run           → 500, no default/reset
```

### Record contract

Suggested model:

```python
class PlayRunRecord(BaseModel):
    schema_version: Literal["dmb_play_run_record_v1"]
    run_id: str
    campaign_id: str
    playable_artifact_id: str
    playable_revision: int
    playable_content_sha256: str
    run_revision: int = 1
    created_at: str
    updated_at: str
```

Suggested request:

```python
class CreatePlayRunRequest(BaseModel):
    playable_artifact_id: str
    expected_playable_revision: int
    expected_playable_content_sha256: str
```

Suggested list response:

```python
class PlayRunsListResponse(BaseModel):
    schema_version: Literal["dmb_play_runs_list_v1"]
    records: list[PlayRunRecord]
```

Names may change only if the existing repository naming conventions require it. The semantic fields/invariant may not drift without a stop report.

### Identity matrix

| Situation | Rule | Ambiguity | Fallback |
|---|---|---|---|
| Run UUID | Opaque canonical UUID; equality only | Invalid → 422 | No slug/title/session derivation |
| Playable artifact | Exact workspace `document_id` | Unknown → 404 | No title/path lookup |
| Playable revision | Exact `loaded_revision` | Mismatch → 409 | No latest |
| Playable content | Exact SHA-256 | Mismatch → 409 | No “revision is enough” fallback |
| Campaign | Derived from admitted Runbook | Caller cannot override | No |
| Same Run UUID replay | Exact same immutable binding returns existing | Any difference → 409 | No overwrite |

### Persistence matrix

| Operation | Representation | Round-trip | Replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Create Run | `out/runtime/play/runs/{uuid}.json` | exact Pydantic record | identical PUT returns same record | v1 only | delete only in tests; no product delete |
| GET | validated file | exact | repeatable | malformed → 500 | n/a |
| List | validated directory records | deterministic | repeatable | malformed member → fail whole list | n/a |

Deterministic list order:

```text
created_at descending, then run_id ascending as tie-breaker
```

Do not use filesystem iteration order as API order.

### Replay / idempotency

```text
same run_id + same exact binding:
  return existing unchanged

same run_id + different artifact/revision/digest:
  409; existing record unchanged

different run_id + same exact Playable binding:
  allowed; represents a distinct Run

retry after file write but lost HTTP response:
  same PUT returns the existing exact record
```

### Commit point

The commit point is the atomic replace of the new Run JSON file.

Before commit:

- no durable Run exists.

After commit:

- the Run binding exists even if response delivery fails;
- replay must return it unchanged.

P2A has no multi-file transaction.

### Trust boundary

P2A verifies:

- Run UUID shape;
- exact workspace document identity;
- admitted Runbook lifecycle state;
- exact workspace revision and content digest;
- persisted record schema/integrity;
- replay identity.

P2A deliberately does **not** verify:

- Scene/Beat/Choice/Option existence;
- semantic wisdom/completeness of Playable content;
- whether a Run should advance;
- World/Source truth;
- Combat state.

---

## §7 Evidence required to merge

| Guarantee | Boundary | Evidence | Required proof | Merge blocker |
|---|---|---|---|---|
| Exact committed Runbook binding | service + real workspace snapshot | contract/integration | create against temp workspace registry + committed target | binding from caller fields alone |
| Stale revision refuses | service/route | adversarial | expected N against actual N+1 → 409, no file | latest silently accepted |
| Stale SHA refuses | service/route | adversarial | expected A against snapshot B → 409 | digest ignored |
| Non-runbook refuses | service | contract | committed Plan or worldbuilding_source → 422 | broad unreviewed runnable kinds |
| Draft/discarded refuses | service | lifecycle | each → 409 | Run created |
| Idempotent replay | service + route | replay | identical PUT twice; deep-equal record + unchanged bytes/timestamps/run_revision | second mutation/new Run |
| Run-ID collision refuses | service + route | adversarial | same UUID different binding → 409; original unchanged | overwrite |
| Restart persistence | file authority | persistence | create → new service/read call from disk → exact GET/list | in-memory-only success |
| Multiple Runs same Playable | service | identity | two UUIDs same binding both survive | accidental uniqueness |
| Corrupt Run fails closed | file authority | integrity | invalid JSON / invalid record → explicit error | default/reset/skip |
| Deterministic list | route/service | regression | creation ties/order fixture | filesystem-order API |
| Existing Playable bytes untouched | cross-authority | regression | before/after workspace snapshot digest/revision identical | P2A rewrites Runbook |
| Router mounted | FastAPI app | integration | TestClient real app path | service-only dead API |
| Roadmap reconsidered | process | review | disposition + ledger | stale roadmap |

### Exact verification commands

From repository root, adapt only to repository-standard equivalents:

```bash
uv run pytest -q \
  tests/test_play_run_registry.py \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry_integrity.py

uv run ruff check \
  apps/live_control_server/services/play_run_registry.py \
  apps/live_control_server/routes/play_runs.py \
  tests/test_play_run_registry.py \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry_integrity.py

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-durable-run-binding.md \
  --pr <PR_NUMBER>

git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

If `main.py` has an existing focused app/router test that is the repository's owning route-mount proof, the coding agent may add it to the pytest command without widening production scope.

### Required persistence scenario

The focused suite must include one realistic sequence:

```text
1. create a temp Runbook workspace record;
2. commit exact Markdown through the existing workspace authority or construct the
   same admitted on-disk + registry state using its canonical test fixture;
3. read its coherent snapshot;
4. PUT Run UUID with exact revision+SHA;
5. verify one Run JSON exists outside workspace storage;
6. construct a fresh service/read context;
7. GET/list and recover the exact binding;
8. verify the Runbook snapshot revision+SHA did not change.
```

### Required stale-create scenario

```text
1. capture Runbook snapshot revision N / SHA A;
2. advance the Runbook to revision N+1 / SHA B through existing workspace authority;
3. PUT a new Run UUID with expected N / A;
4. expect 409;
5. assert no Run file was created.
```

### Baseline failure handling

If any required command fails on the pinned base, run the same command on base and head, record exact deltas, and do not waive a new failure as pre-existing without evidence.

No CI must be invented. Report whether checks are actually attached to the exact head.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/reviewed head SHA;
2. implementation/evidence head separately when roadmap bookkeeping follows;
3. exact pinned base;
4. §1 mission/invariant disposition;
5. §7 required vs produced evidence and provenance:
   - author-local;
   - independently rerun;
   - CI if actually present;
6. actual changed paths vs §4;
7. nano-commit/fix story;
8. baseline failures/waivers;
9. paths outside §4 (`none` or stop report);
10. stop conditions encountered/resolution;
11. previous finding ledger on re-review;
12. named successor remains false:

```text
P2B — durable element-referenced Run progress
```

13. exactly one roadmap disposition;
14. exact roadmap ledger row using implementation/evidence head;
15. `P2A_HOIST_OBSERVATION`.

---

## §9 Acceptance rubric

- [ ] Post-#594 mutable-state sync landed before dispatch.
- [ ] Exact implementation base pinned after that sync.
- [ ] P2A creates one Runtime authority outside authored workspace storage.
- [ ] Run IDs are opaque UUIDs and never parsed for campaign/session/title.
- [ ] A new Run binds one exact committed active Runbook workspace document.
- [ ] Binding persists both workspace revision and content SHA.
- [ ] Caller must prove expected revision and expected SHA; there is no “latest” fallback.
- [ ] `campaign_id` is derived from the admitted Runbook, not caller-authored.
- [ ] `run_revision` begins at 1 and is not spuriously incremented on replay.
- [ ] Same Run UUID + same binding is idempotent.
- [ ] Same Run UUID + different binding fails 409 without overwrite.
- [ ] Different Run UUIDs may bind the same Playable revision.
- [ ] GET/list survive process restart/file reload.
- [ ] Malformed persisted Run fails closed.
- [ ] List order is deterministic.
- [ ] P2A does not mutate workspace document bytes or registry revision.
- [ ] P2A does not parse/copy Playable structure.
- [ ] No current Scene/Beat, resolved Beats, choices, notes, migration, or linked handles.
- [ ] No UI/API client work.
- [ ] No DungeonMind/kernel/profile changes.
- [ ] Actual changed paths stay inside §4/bounded discovery.
- [ ] Focused tests, ruff, preflight, diff check, and name-only gate pass or baseline differences are truthfully recorded.
- [ ] Roadmap review + P2A hoist observation are explicit.
- [ ] P2B remains unimplemented/unclaimed.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

- post-#594 current-sequence authorities are not synchronized before dispatch;
- current `main` materially changes workspace snapshot identity/revision/digest semantics;
- exact Run binding requires modification of the workspace-document schema or Markdown writer;
- P2A appears to require Scene/Beat/Choice/Option parsing or validation;
- a progress field becomes necessary to make the first Run record work;
- historical Playable revision storage/archive becomes necessary;
- a generic work-object ref abstraction becomes necessary rather than merely attractive;
- a required production path falls outside §4;
- another active lane owns `main.py`, the Playable roadmap, or the proposed route namespace;
- production tests would touch the operator's real `out/` runtime state;
- durable creation cannot be made replay-safe under the proposed identity semantics;
- implementation evidence contradicts the architecture's Playable/Runtime separation.

Report:

```text
Stop condition:
Invariant clause affected:
Why P2A cannot absorb it:
Required evidence now missing:
Affected paths/ownership:
Proposed successor or re-brief:
Roadmap claim affected:
State-authority update needed:
```