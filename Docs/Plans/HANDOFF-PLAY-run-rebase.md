---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P2C
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-run-rebase.md
  - Branch / PR: agent/play-run-rebase / `PLAY: rebase Run to newer Playable revision`

  ## Verification pointer
  - Design anchor: merged PR #601 / P2B2 at `51ed2a6e89b56d2ef033215e23d309ce03a51c87`
  - P2B2 reviewed head: `c9d2697c1f7e6b11235a753ceb45c4e514a423eb`
  - P2B2 implementation/evidence head: `8538409e1027ca8e84990bd86cd07ee2ccf99a72`
  - Base/head: `47b71c64dc880c051339e5cf08c4be344ea74366` / `5d0c050492886e03e7e6e8e323c359c29930e9cd`
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — explicitly rebase one Run to a newer Playable revision

**Created:** 2026-08-16  
**Status:** CODE IN PR [#612](https://github.com/Drakosfire/DungeonMindBuddy/pull/612) — Cycle 1 repair of source integrity, preserve-only intent proof, rebase receipt, and orphan-intent list isolation.
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-run-rebase.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P2C`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #601 / P2B2 at `51ed2a6e89b56d2ef033215e23d309ce03a51c87`  
**P2B2 reviewed head:** `c9d2697c1f7e6b11235a753ceb45c4e514a423eb`  
**P2B2 implementation/evidence head:** `8538409e1027ca8e84990bd86cd07ee2ccf99a72`  
**P2B2 review cycles:** `2`  
**Implementation base:** `47b71c64dc880c051339e5cf08c4be344ea74366`
**Suggested branch:** `agent/play-run-rebase`  
**PR title:** `PLAY: rebase Run to newer Playable revision`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — close merged P2B2 state, then pin P2C

PR #601 is merged as:

```text
merge:               51ed2a6e89b56d2ef033215e23d309ce03a51c87
reviewed head:       c9d2697c1f7e6b11235a753ceb45c4e514a423eb
implementation head: 8538409e1027ca8e84990bd86cd07ee2ccf99a72
review cycles:        2
```

Current `main` contains the merge, but the mutable P2 current-sequence block and the P2B2 handoff still describe P2B2 as active/current. That is expected immediately after merge and is **not** dispatch authority for P2C.

Before CODE dispatch, one guarded post-#601 state-authority sync must:

1. mark `Docs/Plans/HANDOFF-PLAY-run-progress-cas.md` **MERGED / HISTORICAL** with:
   - PR #601;
   - merge `51ed2a6e89b56d2ef033215e23d309ce03a51c87`;
   - reviewed head `c9d2697c1f7e6b11235a753ceb45c4e514a423eb`;
   - implementation/evidence head `8538409e1027ca8e84990bd86cd07ee2ccf99a72`;
   - **2 review cycles**;
   - successor `HANDOFF-PLAY-run-rebase.md`;
2. update `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` so:
   - integration tip names merged PR #601 / `51ed2a6e89b56d2ef033215e23d309ce03a51c87`;
   - merged capability is P2B2 durable CAS Run progress;
   - P2C is the current next slice;
   - this handoff is the current next handoff;
   - P3 native Play projections is the named successor after P2C;
   - Runtime remains DungeonMindBuddy Play-owned;
   - `WorkObjectRevisionRef`, `WorkObjectElementRef`, and a generic transaction framework remain not yet justified;
3. land this handoff on `main` as part of that guarded sync if it is not already present there;
4. make no stable architecture edit unless the sync review finds a real contradiction. The architecture already says a Run binds to an exact **or explicitly migrated** Playable revision.

Required sequence after sync:

```text
P2A  — durable Run identity + exact Playable revision/digest binding     MERGED
P2B1 — immutable Run-bound Playable reference manifest                  MERGED
P2B2 — durable CAS Run progress against the sealed manifest             MERGED
P2C  — explicit preserve-only Run rebase to newer Playable revision     NEXT
P3   — native Play projections                                           FALSE
```

`linkedRuntimeHandles` remains deferred until a real Combat/other-runtime consumer requires it.

After the state sync lands:

1. fetch/re-read current `main`;
2. replace every `PIN_AFTER_POST_601_STATE_SYNC` in this handoff with that exact state-sync merge/base SHA on the implementation branch;
3. re-read the merged P2A/P2B1/P2B2 services and tests named in §2;
4. verify the roadmap still names P2C next;
5. run:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-run-rebase.md
```

6. stop if the Run record, `run_revision`, manifest immutability/binding, P2B2 progress shape, workspace snapshot contract, per-file lock primitive, or §4 ownership changed materially.

---

## §1 Mission and merge-ready invariant

**Mission:** DungeonBuddy can explicitly move one existing Run UUID from its exact current Playable revision to one exact newer committed revision of the **same Runbook artifact**, preserving the Run's current progress only when every durable progress reference remains admissible in the target revision, while surviving process/response failure across the required Run+manifest two-file transition without retaining historical Playable bodies or silently retargeting missing references.

**Merge-ready invariant:**

> **For one existing Run UUID at exact `run_revision = N`, an actual rebase either writes nothing, or durably prepares one exact forward-only rebase intent and eventually commits exactly one coherent target pair consisting of (a) the same Run UUID/artifact/campaign with target Playable revision+SHA, unchanged admitted progress, `run_revision = N+1`, and `rebased_from_run_revision = N`, and (b) one replacement immutable P2B1-format manifest derived from that exact target revision. No current/latest Runbook bytes are consulted after intent is durable; no non-rebase operation may observe or mutate through a pending half-transition; removed/wrong-kind/wrong-membership Runtime references block before intent; exact retry can recover each recognized commit stage without double-incrementing; completed no-intent replay requires that receipt plus the persisted target pair, and current-token same-target no-op returns success only when the persisted target Run and target manifest still form that same coherent pair; successful rebase retains no old manifest, old Run snapshot, historical Markdown, mapping history, or second concurrency token.**

### Why P2C is preserve-only

The architecture requires migration/rebase to be explicit when referenced IDs are removed or semantically replaced. P2C does **not** invent a second mapping language inside the rebase request.

Existing P2B2 already owns one full Runtime progress replacement:

```text
current Scene / Beat
resolved Beats
Choice → Option selections
notes by Playable element ID
```

Therefore removed/replaced references are handled explicitly by composition:

```text
old-bound Run progress
→ P2B2 full replacement clears/adjusts references that cannot survive
→ P2C rebase preserves the remaining exact references
→ optional P2B2 replacement after rebase may select new target-only IDs
```

This keeps one concurrency token and one progress mutation vocabulary.

P2C treats an unchanged stable element ID as the same semantic identity. It does not compare titles/prose to infer whether an author accidentally reused an ID for different semantics; the architecture's stable-ID contract requires semantic replacement to receive a replacement ID.

### Why a durable rebase intent is part of this capability

P2B2 made the Run JSON one CAS authority while P2B1 keeps reference admission in a separate manifest file:

```text
out/runtime/play/runs/{run_id}.json
out/runtime/play/reference-manifests/{run_id}.json
```

A same-Run rebase must change both bindings. Two independent `write_json()` replacements are not a crash-atomic transaction.

P2C therefore owns one **Play-specific forward-recovery intent**, persisted before either canonical file changes. This is not a second concurrency token and not a historical Playable archive. It exists only to make the one rebase transaction recoverable.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Explicit same-artifact target revision/SHA admission | No; prerequisite to rebase | Same rebase API | **Include** |
| Derive target P2B1-format manifest from exact target snapshot | No; safety clause | Reuses Play-owned manifest contract | **Include** |
| Prove existing progress survives target manifest unchanged | No; migration safety clause | Reuses P2B2 progress contract | **Include** |
| Persist forward-only rebase intent before two-file mutation | No; crash-safety clause | New internal Play Runtime transaction record | **Include** |
| Replace manifest + Run under one Run lifecycle lock | Yes | Existing authorities under explicit migration boundary | **Include** |
| Exact replay/recovery after intent/manifest/Run/cleanup failure | No; idempotency clause | Same rebase API | **Include** |
| Block other Run/manifest operations while recovery is pending | No; isolation clause | Existing APIs gain a temporary 503 state | **Include** |
| Caller-authored old-ID → new-ID mapping | Yes | New migration vocabulary | **Exclude** |
| Cross-artifact Run migration | Yes | Changes Run identity/binding semantics | **Exclude** |
| Historical Runbook/manifest archive | Yes | New history authority | **Prohibited** |
| Rebase rollback/undo | Yes | New lifecycle transition | **Exclude** |
| Progress event log | Yes | New Runtime history | **Exclude** |
| `linkedRuntimeHandles` migration | Yes | Cross-runtime contract | **Exclude** |
| Rebase UI / conflict-resolution UI | Yes | New operator workflow | **Exclude — P3/later** |
| Generic Buddy multi-file transaction framework | Yes | Shared infrastructure contract | **Exclude — hoist review only** |
| Generic `WorkObjectRevisionRef` / `WorkObjectElementRef` | Yes | Buddy-shared abstraction | **Exclude — hoist review only** |
| DungeonMind contract | Yes | Cross-repo contract | **Prohibited** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path is one same-Run forward migration from one coherent Run+manifest pair to another, under one `run_revision` CAS and one recovery intent. |
| Most likely adversarial sequence | Intent persists → target manifest replaces old manifest → Run write fails/process dies. Required: no ordinary read/progress/seal may accept the mixed pair; exact rebase retry recognizes source-Run + target-manifest and completes the one N→N+1 Run commit without workspace lookup. |
| Will §7 detect that failure? | Yes. Inject failure after manifest commit, prove pending-intent 503 isolation, then exact replay to completion with one revision increment. |
| Easiest owner to under-test | Isolation. In-process locking can hide a crash-stage mixed pair. §7 therefore proves both a concurrent GET cannot observe the half-commit while the lock is held and restarted/non-rebase operations fail while the durable intent remains. |
| Fact that forces stop/split | Need for caller-authored ID mapping, cross-artifact migration, old Playable body/history, generalized transaction infrastructure, parser grammar changes, or Runtime-handle/Combat migration. |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 Core invariant;
   - §4.2 Stable element identity;
   - §6 Choices and branching;
   - §7 Runtime State + §7.1 Runtime invariants;
   - §11 Persistence and revision rules.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - P2 decomposition;
   - P2A/P2B1/P2B2 review evidence;
   - P2C boundary and P3 successor;
   - hoist posture.
3. merged P2A:
   - `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md`;
   - `apps/live_control_server/services/play_run_registry.py`;
   - `tests/test_play_run_registry.py`;
   - `tests/test_live_play_runs.py`;
   - `tests/test_play_run_registry_integrity.py`.
4. merged P2B1:
   - `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md`;
   - `apps/live_control_server/services/play_run_reference_manifest.py`;
   - `tests/test_play_run_reference_manifest.py`;
   - `tests/test_live_play_run_reference_manifest.py`.
5. merged P2B2 / PR #601:
   - `Docs/Plans/HANDOFF-PLAY-run-progress-cas.md`;
   - `apps/live_control_server/services/play_run_registry.py`;
   - `apps/live_control_server/routes/play_runs.py`;
   - `tests/test_play_run_progress.py`;
   - `tests/test_live_play_run_progress.py`.
6. `apps/live_control_server/services/registry_file_lock.py`.
7. `apps/live_control_server/services/workspace_document_registry.py`
   - `WorkspaceDocumentSnapshot`;
   - `get_workspace_document_snapshot_unlocked()`;
   - workspace document mutation lock contract.
8. `src/live_play/live_store.py` — atomic single-file JSON replacement only.
9. `Docs/Plans/HANDOFF-sbw09c2b-threat-publication-commit-recovery.md` as **repository precedent only** for durable intent-before-mutation and truthful uncertain-outcome recovery. Do not import its Graph-specific state machine or authorities.
10. `AGENTS.md`.
11. `Docs/Process/STEWARD-CYCLE.md`.

### Predecessor contracts consumed and intentionally extended

#### P2A/P2B2 Run authority

Current Run record:

```text
schema_version: dmb_play_run_record_v1
run_id
campaign_id
playable_artifact_id
playable_revision
playable_content_sha256
run_revision
created_at
updated_at
progress:
  current_scene_id
  current_beat_id
  resolved_beat_ids
  selections
  notes_by_element_id
```

P2A originally made the binding immutable. The stable architecture explicitly permits an **explicitly migrated** binding. P2C is that sole lifecycle exception.

P2C must preserve:

```text
run_id
campaign_id
playable_artifact_id
created_at
progress      # exact semantic snapshot; canonical resolved-beat ordering unchanged
```

P2C changes on an actual rebase:

```text
playable_revision
playable_content_sha256
run_revision: N → N+1
updated_at
```

No other mutation path gains permission to edit the binding fields.

#### P2B1 manifest authority

Canonical sidecar remains:

```text
out/runtime/play/reference-manifests/{run_id}.json
schema_version: dmb_play_run_reference_manifest_v1
run_id
playable_artifact_id
playable_revision
playable_content_sha256
elements[]
sealed_at
```

Within one binding, that manifest remains immutable. P2C is the one explicit lifecycle boundary allowed to replace the canonical sidecar with a newly derived immutable manifest for the newly committed Run binding.

Successful P2C retains only the target canonical manifest. It must not rename/archive the source manifest or keep per-revision manifest history.

#### P2B2 progress authority

P2C does not transform progress. It asks whether the exact current canonical progress snapshot is valid against the target manifest under the same P2B2 admission rules:

- current Scene exists as Scene;
- current Beat exists as Beat and belongs to current Scene;
- every resolved Beat exists as Beat;
- every selected Choice exists as Choice;
- every selected Option exists as Option and belongs to that Choice;
- every note target exists as one of the four Playable element kinds.

Failure is a pre-intent 409 with no mutation. P2B2 remains the only progress-edit API.

### Target revision boundary

A new rebase intent may target only:

```text
same playable_artifact_id
same campaign scope
current active committed Runbook workspace snapshot
exact caller-supplied target revision
exact caller-supplied target content SHA
target revision strictly newer than the Run's current playable_revision
```

DungeonBuddy does not have historical Runbook body storage. Therefore P2C cannot newly prepare a rebase to an arbitrary non-current historical revision.

Once a rebase intent is durable, exact replay may complete from the intent even if the workspace Runbook subsequently advances again. No current workspace lookup is permitted on recovery.

### Lane table

| Field | Required content |
|---|---|
| Parent authority | `ARCHITECTURE-playable-material-and-runtime.md` + living Playable hoist roadmap |
| Base revision | `47b71c64dc880c051339e5cf08c4be344ea74366` |
| Design anchor | merged PR #601 / `51ed2a6e89b56d2ef033215e23d309ce03a51c87` |
| Predecessor contract | P2A Run identity + P2B1 immutable manifest + P2B2 canonical CAS progress |
| Exact input consumed | existing Run UUID + `expected_run_revision` + exact target revision/SHA of the same Runbook artifact |
| Output | same Run UUID at target binding with unchanged admitted progress and exactly one replacement target manifest, or no new intent/mutation; pending intent is forward-recoverable |
| Named successor | `P3 — native Play projections` |
| What remains false | no ID mapping, cross-artifact migration, old revision archive, undo, linked runtime handles, Play UI/projection, Runtime→Playable adoption |
| Branch / isolated checkout | `agent/play-run-rebase` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | Run registry/service, manifest service, `/api/live/play-runs` router, living roadmap, `out/runtime/play/runs/**`, `reference-manifests/**`, `rebase-intents/**`; serialize with any lane touching these |
| Runtime/state ownership | tests use temp repo roots only; production P2C may mutate one Run file + one manifest + one ephemeral intent for the same Run |
| State-authority sync after merge | mark P2 complete/P2C merged and advance current sequence to P3; stable architecture only if evidence changes a claim |

### Hoist posture at dispatch

Default:

```text
Run rebase transaction:        Play-owned
Generic multi-file transaction: not yet justified
WorkObjectRevisionRef:          not yet justified
WorkObjectElementRef:           not yet justified
DungeonMind contract:           none
```

One Play-owned recovery journal is evidence, not sufficient reason to create generic Buddy transaction infrastructure.

---

## §3 Observable paths and adversarial sequences

### Canonical API

Reuse the mounted Play Runs router.

```http
PUT /api/live/play-runs/{run_id}/rebase
```

Request:

```json
{
  "expected_run_revision": 4,
  "target_playable_revision": 12,
  "target_playable_content_sha256": "<64 lowercase hex>"
}
```

No `playable_artifact_id` is accepted. P2C is same-artifact only.

No progress, ID mapping, manifest elements, or conflict-resolution instructions are caller-authored.

Response on complete/no-op/replay success:

```text
PlayRunRecord
```

There is no separate dry-run, rebase-plan, abort, rollback, or history endpoint in P2C.

### Rebase request admission when no intent exists

Under the Run lifecycle lock:

1. validate canonical Run UUID and request fields;
2. load the exact persisted Run through the same P2B2 authoritative integrity contract as ordinary Run reads (`_load_authoritative_record`), without recursively entering public Run GET. Empty progress may omit a source-manifest read; non-empty persisted progress must already be canonical and admitted by the current source manifest;
3. if current Run binding == requested target binding, prove the persisted target pair before any success return (§3 below):
   - load the canonical persisted manifest; the empty-progress missing-manifest exception does **not** apply here;
   - require strict P2B1 persisted integrity and exact `run_id` / artifact / revision / content-SHA binding to the current target Run;
   - require persisted progress, when present, to be canonical and admitted by that target manifest;
   - missing, corrupt, or mismatched manifest → 500; no workspace fallback, no rewrite, no 200;
   - `run_revision == expected_run_revision + 1` **and** `rebased_from_run_revision == expected_run_revision` → completed response-loss replay; return current Run unchanged;
   - `run_revision == expected_run_revision` → current-token same-target no-op; return current Run unchanged;
   - any other revision relation, including `expected + 1` from an unrelated progress mutation, → 409;
4. require `expected_run_revision == current.run_revision` for a new rebase;
5. require `target_playable_revision > current.playable_revision`;
6. load the current P2B1 source manifest when present and require exact current binding;
   - malformed/mismatched current manifest → 500;
   - missing current manifest is allowed **only when this is a new rebase and current progress is empty**;
   - missing current manifest with any durable progress reference → 500/no intent;
7. acquire the canonical manifest mutation lock;
8. acquire the workspace-document mutation lock for the same `playable_artifact_id`;
9. load one coherent current workspace snapshot through the unlocked seam;
10. require same document ID/campaign, `kind=runbook`, active, committed, file exists, exact target revision, exact target SHA;
11. derive one target P2B1-format manifest with the existing P1 resolver semantics;
12. admit the existing canonical progress snapshot against that target manifest;
13. if any progress reference fails target admission, return 409 **before intent** and write nothing;
14. prepare exact target Run record:
    - same run/campaign/artifact/created_at/progress;
    - target revision/SHA;
    - `run_revision = N+1`;
    - one fixed target `updated_at`;
15. prepare exact target manifest with one fixed `sealed_at`;
16. persist one rebase intent atomically;
17. continue the forward commit state machine.

Hold the workspace mutation lock through durable intent creation and the normal in-process canonical commit. A process crash releases the OS lock; exact recovery then relies only on the durable intent.

### Canonical rebase intent

Persistence root:

```text
out/runtime/play/rebase-intents/{run_id}.json
```

Schema:

```text
schema_version: dmb_play_run_rebase_intent_v1
run_id
expected_source_run_revision
source_playable_artifact_id
source_playable_revision
source_playable_content_sha256
source_run_token                 # exact source Run-file token
source_manifest_token            # exact source manifest token or literal "absent"
target_run                       # exact complete PlayRunRecord to commit
target_manifest                  # exact complete P2B1-format manifest to commit
prepared_at
```

The intent must be strict/fail-closed. `target_run.run_id`, artifact, campaign, revision/SHA, progress, and `run_revision` must be internally consistent with the source/request. `target_manifest` must bind exactly to `target_run`.

The intent contains:

- no Runbook Markdown/Tiptap body;
- no source manifest payload;
- no old Run snapshot/history;
- no caller-authored mapping;
- no event log;
- no generic transaction metadata unrelated to this Run rebase.

One Run may have at most one intent path. Intent existence blocks a different rebase request.

### Run lifecycle lock and isolation

Use the existing per-Run file mutation lock as the **outer Run lifecycle lock**; do not introduce a second lock namespace/token merely for P2C.

Canonical lock order for operations that need multiple authorities:

```text
Run lifecycle lock
→ manifest mutation lock when manifest write is possible
→ workspace-document mutation lock when a fresh target snapshot is required
```

P2C must refactor public predecessor operations so the same Run lifecycle lock protects coherent observation/mutation of the Run+manifest pair:

- Run GET;
- Run list per record;
- P2A create/replay;
- P2B2 progress mutation;
- P2B1 manifest GET;
- P2B1 seal/replay;
- P2C rebase/recovery.

Avoid recursive flock acquisition by adding explicit private/unlocked load seams where required. Public methods must not call one another in a way that reacquires the same Run lock.

While a rebase intent exists, every **non-rebase** authoritative Run/manifest operation for that Run returns 503 and performs no write:

```text
GET Run
list Runs (fail the list rather than skip the Run)
P2A create/replay
P2B2 progress PUT
P2B1 manifest GET
P2B1 manifest PUT/seal
```

List isolation must discover pending intent files independently of `out/runtime/play/runs/*.json`. An intent with no corresponding Run file still fails the whole list (503); it must not return a successful list that omits the pending Run.

Reason: after a crash the canonical files may be source/source, source/target, or target/target-with-cleanup-pending. No other operation may mutate or present stale/mixed authority before the rebase is reconciled.

### Forward-only commit state machine

After intent is durable, P2C never rolls back to the source binding. Exact replay completes forward.

Normal sequence under Run + manifest locks:

```text
1. rebase intent durable
2. replace canonical manifest with target_manifest
3. replace canonical Run with target_run       ← logical product commit point
4. delete rebase intent                        ← cleanup
5. return target_run
```

Recognized exact-replay stages:

| Canonical files + intent | Meaning | Exact same rebase request |
|---|---|---|
| source Run token + source manifest token/absence | intent prepared; canonical pair not changed | install target manifest, then target Run, cleanup |
| source Run token + exact target manifest | manifest installed, Run not committed | install target Run, cleanup |
| exact target Run + exact target manifest | product commit happened; cleanup pending | delete intent, return target Run |
| anything else | contradictory/tampered recovery state | 500, no write |

Before installing canonical state from `prepared` or `manifest_installed`, recovery must re-prove the intent's preserve-only relation against the still-present source Run: campaign, creation identity, artifact, and progress must equal the source; target progress must remain canonical and admitted by the intent's target manifest. A structurally valid tamper of those preserved fields is 500 with no write, not silent recovery.

After intent exists, recovery must not consult workspace state.

I/O failure **before** the intent becomes durable leaves source authority untouched and retryable normally.

I/O/process uncertainty **after** durable intent leaves the intent in place. Return/raise a retryable 503 when the process remains alive and cannot complete. Exact retry resumes from the recognized stage. A different request is 409.

### Product commit and response-loss replay

The logical product commit point is the atomic replacement of the Run file with `target_run` **after** the target manifest is already canonical.

Normal in-process readers cannot observe the intermediate source-Run/target-manifest pair because they share the Run lifecycle lock.

If the process dies in that stage, the durable intent blocks ordinary operations and exact replay completes the target Run commit.

After successful cleanup, no intent remains. A lost HTTP response is recognized without workspace lookup, but **not from the Run record alone**. Completed replay must prove the coherent target pair.

Completed response-loss replay:

```text
current Run binding == requested target binding
and current run_revision == expected_run_revision + 1
and current rebased_from_run_revision == expected_run_revision
and canonical persisted target manifest exists
and that manifest passes strict P2B1 persisted integrity
and that manifest binds exactly to the current target Run
  (run_id / artifact / revision / content SHA)
→ exact response-loss replay
→ return current Run unchanged
→ no manifest rewrite / no revision increment / no workspace read
```

`run_revision == expected + 1` is not sufficient by itself. P2B2 progress mutation increments the same CAS counter without changing the Playable binding, so completed rebase replay also requires the explicit `rebased_from_run_revision` receipt written by that rebase. An unrelated progress N→N+1 on an already-bound target must remain 409.

If the Run matches that completed-replay revision/binding/receipt relation but the canonical target manifest is missing, corrupt, or bound to a different Run/artifact/revision/SHA, fail closed **500**. Do not return 200, do not consult workspace, and do not rewrite or recreate the manifest. Ordinary Run GET with empty progress may omit a manifest read; rebase completed-replay must not reuse that shortcut.

Current-token same-target no-op is a distinct admission with the same pair-integrity proof, not an implicit sibling of the early return:

```text
current Run binding == requested target binding
and current run_revision == expected_run_revision
and the same canonical target-manifest integrity/binding proof as completed replay
→ return current Run unchanged
```

Missing/corrupt/mismatched target manifest on this path is also 500 with no workspace fallback or rewrite.

Any stale request naming a different target returns 409.

### Progress-survival admission

Rebase preserves progress **exactly**; it never silently drops or remaps references.

| Existing Runtime reference | Target requirement |
|---|---|
| `current_scene_id` | same ID exists as Scene |
| `current_beat_id` | same ID exists as Beat and belongs to same `current_scene_id` |
| each `resolved_beat_ids[]` | same ID exists as Beat |
| each `selections` key | same ID exists as Choice |
| each `selections` value | same ID exists as Option and still belongs to that Choice |
| each `notes_by_element_id` key | same ID exists as one of the four Playable kinds |

Any failure is 409 before intent creation.

Error text must identify at least the failing progress field and element ID. A complete mapping/conflict-report schema is not part of this slice.

### Observable path table

| Path | Required behavior | Owning boundary |
|---|---|---|
| Rebase with all refs surviving | one intent → target manifest → N→N+1 target Run → intent cleanup | rebase service + Run/manifest stores |
| Rebase empty progress across total element replacement | allowed; no Runtime refs require preservation | rebase service |
| Rebase with removed current Scene/Beat | 409 before intent; source bytes unchanged | target progress admission |
| Rebase with removed resolved Beat | 409 before intent; source bytes unchanged | target progress admission |
| Rebase with removed/cross-choice selection | 409 before intent; source bytes unchanged | target progress admission |
| Rebase with removed note target | 409 before intent; source bytes unchanged | target progress admission |
| Target revision/SHA not current exact snapshot | 409; no intent | workspace target admission |
| Target malformed P1 identity/membership | fail closed; no intent | existing P2B1 resolver |
| Same target/current token | 200 no-op only after target-pair integrity; missing/corrupt/mismatched target manifest 500 | rebase replay admission |
| Lost response after completed rebase | exact old-token retry returns target unchanged only after target-pair integrity | rebase replay admission |
| Completed rebase then missing/corrupt/wrong-binding target manifest | old-token retry 500; no workspace; no rewrite | rebase replay integrity |
| Different stale target | 409 | CAS/replay admission |
| Missing source manifest + empty progress | allowed; source token=`absent`, target manifest is installed | compatibility path |
| Missing source manifest + non-empty progress | 500/no intent | Runtime integrity prerequisite |
| Malformed/mismatched source manifest | 500/no intent | P2B1 persisted integrity |
| Failure writing intent | 500; canonical source pair unchanged; no durable intent | pre-commit persistence |
| Failure after intent before/while manifest write | 503; intent remains; exact replay completes | recovery state machine |
| Failure after target manifest before Run write | 503; source Run + target manifest + intent; ordinary APIs 503; exact replay commits target Run | recovery state machine |
| Failure after target Run before intent cleanup | product committed; ordinary APIs 503 while intent remains; exact replay cleans without increment | recovery state machine |
| Concurrent GET during in-process half commit | waits on Run lifecycle lock; returns only coherent target pair after release | lock isolation |
| Concurrent P2B2 progress wins before rebase lock | rebase expected revision becomes stale → 409 | Run lifecycle CAS |
| Rebase intent wins before P2B2 progress | progress waits, then 503 while intent exists or 409 after completed new revision | Run lifecycle isolation |
| Workspace mutation races new rebase preparation | serialized; target snapshot/intent pair is coherent | workspace lock |
| Workspace advances after intent before recovery | exact replay completes from intent; no workspace lookup | recovery |
| P2B1 manifest PUT after completed rebase | exact target sidecar replay, unchanged/no workspace | manifest predecessor regression |
| P2B2 progress after completed rebase | validates against target manifest and advances from N+1 normally | progress predecessor regression |
| P2A replay using old binding after rebase | 409; Run is explicitly migrated | P2A lifecycle regression |
| P2A replay using target binding after rebase | returns current Run unchanged | P2A lifecycle regression |
| Successful rebase filesystem | one Run, one target manifest, no intent, no old per-revision history | persistence audit |

### Adversarial sequences

| Sequence | Required safe outcome | §7 proof |
|---|---|---|
| N/source → prepare M/target → target manifest commit → Run write raises | durable intent + source Run + target manifest; all non-rebase APIs 503; exact PUT resumes to one N+1 target Run | injected Run-write failure/restart test |
| N/source → intent write succeeds → manifest write raises | intent + source/source; exact retry finishes; no second intent/revision | injected manifest-write failure |
| N/source → target pair commits → intent unlink raises | target/target + intent; exact retry cleans; run_revision remains N+1 | cleanup failure test |
| rebase holds lock after manifest replacement → GET starts | GET does not return mixed pair; waits until lock release | interleaving test |
| two rebase callers same N but different targets | exactly one intent/request owns recovery; other 409 | concurrency/request-identity test |
| progress mutation and rebase start from N | no lost update; one operation linearizes first and the other cannot overwrite | interleaving test |
| target snapshot M/B → workspace attempts M+1/C before intent | workspace/rebase lock ordering yields one coherent target; no mixed derivation | workspace interleaving test |
| target intent M/B durable → process dies → workspace advances M+1/C → exact retry | completes M/B from intent; never parses C | recovery-after-advance test |
| target removes `beat:old` still resolved in Runtime | 409 before intent; no manifest/Run changes | blocker test |
| operator clears `beat:old` through P2B2 then retries | rebase succeeds if remaining refs survive | composition test |
| rebase completes → request response lost → exact old-token retry | current target Run+manifest returned unchanged; no rewrite/increment/workspace read | response-loss test |
| rebase completes → delete/corrupt/retarget target manifest → exact old-token retry | not 200; 500 fail-closed; no workspace read; no rewrite/recreate; Run bytes unchanged | completed-replay pair-integrity test |

---

## §4 Files in scope — write lease

Expected implementation paths:

| Action | Path | Purpose |
|---|---|---|
| Create / Modify | `Docs/Plans/HANDOFF-PLAY-run-rebase.md` | checked-in P2C authority; pin/status/evidence handback |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | mandatory P2C review-ledger disposition only; current sequence is synchronized before dispatch |
| Create | `apps/live_control_server/services/play_run_rebase.py` | strict rebase request/intent models, target admission, forward-recovery state machine |
| Modify | `apps/live_control_server/services/play_run_registry.py` | Run lifecycle-lock seam, pending-intent isolation, lock-aware raw/authoritative Run helpers consumed by rebase |
| Modify | `apps/live_control_server/services/play_run_reference_manifest.py` | Run-lifecycle locking for manifest APIs and bounded target-manifest derivation/replacement helpers reusing the existing P1 resolver |
| Modify | `apps/live_control_server/routes/play_runs.py` | add one rebase PUT route; preserve existing route namespace |
| Create | `tests/test_play_run_rebase.py` | owning persistence/CAS/recovery/concurrency/blocker/predecessor proof |
| Create | `tests/test_live_play_run_rebase.py` | HTTP request/status/replay/pending-intent contract proof |

### Bounded discovery exception

```text
Directory:
  tests/

Maximum additional paths:
  2

Allowed path kinds:
  existing Play Run / reference-manifest integrity regression tests only

Decision rule:
  allowed solely when the lifecycle-lock or pending-intent behavior is best proven at
  an existing predecessor test boundary; no production path, parser grammar, UI,
  shared transaction framework, or new workflow may enter through this exception.
```

A required production path outside the explicit lease is a stop report.

### Deliberate non-lease

Read but do not modify unless a stop/re-brief is approved:

```text
apps/live_control_server/services/registry_file_lock.py
apps/live_control_server/services/workspace_document_registry.py
src/live_play/live_store.py
apps/live-control-ui/**
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
```

The existing Run-file `registry_mutation_lock()` is sufficient as the lifecycle serializer. If implementation requires a new generic lock/transaction primitive, stop rather than silently hoisting it.

### Parallel/runtime collision note

This handoff may be designed while the post-#601 state sync is not yet merged because this design branch creates only this new handoff path.

CODE may not dispatch until the sync closes P2B2's active roadmap/handoff state and pins P2C.

P2C tests must use temp repository roots. Do not point recovery/failure injection at operator runtime under real `out/runtime/play/**`.

---

## §5 Explicitly out of scope / collision boundary

| Path / authority | Why P2C must not touch or claim it |
|---|---|
| P1 Markdown/TipTap identity files | target manifest reuses P2B1 resolver; no identity grammar change |
| Workspace-document schema/write contract | P2C reads/locks exact committed target; does not alter document authority |
| Historical Playable storage | explicitly prohibited by roadmap/architecture; intent stores no Markdown and no source manifest payload |
| Caller-authored ID remapping | P2B2 clears old refs before rebase; P2B2 sets new refs after rebase |
| Cross-artifact migration | different capability/identity lifecycle |
| Rebase abort/rollback/history | forward-only recovery is the selected invariant |
| `linkedRuntimeHandles` | deferred until a real Combat/other-runtime consumer exists |
| Combat services/state | no Runtime-handle migration in P2C |
| World/Source/Mechanics registries | rebase cannot publish/mutate these authorities |
| `apps/live-control-ui/**` | no operator UI/projection in P2C |
| P3 native Play projection | named successor |
| Runtime→Playable proposal/adoption | later explicit adoption flow |
| Generic Buddy transaction journal | one Play-owned use does not justify hoist |
| DungeonMind / DungeonMindDnD | no cross-repo contract |

---

## §6 Implementation contract

```text
Input:
  existing canonical Run UUID
  expected_run_revision
  exact newer target revision + target SHA
  same current Runbook artifact

Output:
  source pair unchanged and no intent
  OR one durable pending rebase intent
  OR one completed coherent target Run + target manifest with intent removed

Invariant:
  same §1 invariant

Failure behavior:
  bad request / invalid target -> 422/409 before intent, no writes
  progress ref cannot survive target -> 409 before intent, no writes
  malformed source Run/manifest -> 500 before intent
  I/O before intent durability -> 500, source pair remains authority
  I/O after intent durability -> 503/recovery pending, intent remains
  malformed/contradictory intent recovery state -> 500, no speculative repair

Replay / idempotency:
  current-token same target -> no-op only after persisted target-pair integrity
  old-token exact completed target -> response-loss replay only after persisted target-pair integrity
  exact request with pending intent -> resume recognized forward stage
  different request with pending intent -> 409
  stale different target without intent -> 409

Trust boundary:
  Verifies:
    current Run persisted shape / canonical progress
    canonical persisted target manifest on completed replay / current-token no-op
    current source manifest when required/present for a new rebase
    expected_run_revision
    exact current target workspace revision + SHA before intent
    target P1 identity/membership through existing resolver
    every existing progress reference against target manifest
    intent internal consistency and recognized recovery stages
  Records/trusts without proving:
    stable same element ID means same semantic Playable identity
    operator decision to clear/retain Runtime progress through P2B2
```

### A. Rebase blocker handling

P2C performs no implicit data loss.

If target admission fails for a persisted Runtime reference:

```text
rebase returns 409
intent does not exist
source Run bytes unchanged
source manifest bytes/absence unchanged
workspace bytes unchanged
```

Operator path:

```text
1. GET current Run
2. PUT current full progress replacement under current run_revision
   to clear references that intentionally will not survive
3. retry rebase with the new expected_run_revision
4. after success, optional PUT progress may select target-only IDs
```

This is the explicit missing/replaced-reference handling required by the architecture.

### B. Rebase intent state machine

```text
NO_INTENT
  validate source + target + progress
  write intent
      ↓
PREPARED
  source Run + source manifest/absence
  write target manifest
      ↓
MANIFEST_INSTALLED
  source Run + target manifest
  write target Run
      ↓
RUN_COMMITTED
  target Run + target manifest
  delete intent
      ↓
CLEAN_TARGET
```

No backward transition exists in P2C.

`RUN_COMMITTED` is product truth even if cleanup/response fails. While intent remains, ordinary APIs still return recovery-pending 503 so the one exact rebase request can reconcile cleanup first.

### C. State / fallback matrix

| Observable path | Exact success | Ordinary miss/conflict | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|
| Rebase PUT, no intent | target pair N→N+1 | unknown Run 404; blockers/target mismatch 409 | write failure pre-intent 500 | malformed source/target 500/422; completed-replay missing/corrupt/mismatched target manifest 500 | stale run revision 409 | same-target no-op/replay only after target-pair integrity |
| Rebase PUT, intent exists | resume recognized stage | different request 409 | post-intent I/O 503 | bad intent/contradictory stage 500 | n/a | exact request only |
| Run GET/list during intent | none | recovery pending 503 | n/a | malformed intent may surface on rebase as 500 | n/a | no fallback |
| P2B2 progress during intent | none | recovery pending 503 | n/a | n/a | n/a | retry after rebase clean |
| P2B1 manifest GET/PUT during intent | none | recovery pending 503 | n/a | n/a | n/a | retry after rebase clean |
| P2A create/replay during intent | none | recovery pending 503 | n/a | n/a | n/a | retry after rebase clean |

**Fallback:** none. Never validate/recover against latest workspace bytes after intent, never keep the source manifest as a hidden fallback, never silently drop progress.

### D. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Run identity | exact same `run_id` | never create successor Run silently | No |
| Playable artifact | exact same `playable_artifact_id` | cross-artifact request not representable | No |
| Target revision | exact caller target, strictly newer for actual rebase | current snapshot mismatch 409 | No |
| Target SHA | exact caller target SHA | mismatch 409 | No |
| Stable Runtime element ID | same target ID/kind/membership as required | missing/replaced blocks 409 | No |
| Stable ID with changed title/prose | still same semantic identity under architecture | prose not compared | No text heuristic |
| Target-only element | not auto-selected | available to later P2B2 mutation after rebase | No |

### E. Persistence / recovery matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| Prepare rebase | one intent JSON | exact target Run+manifest recoverable without workspace | exact request resumes | source manifest may be absent only with empty progress | none |
| Manifest install | canonical manifest path replaced | exact target P2B1 payload | replay recognizes exact target | source manifest not archived | none |
| Run commit | same Run JSON path, revision N+1 | same progress + target binding after restart | old-token exact target replay only after target-pair integrity | P2A old binding now conflicts | none |
| Cleanup | intent deleted | steady state has no migration artifact | completed retry no-op only after target-pair integrity | no history retained | n/a |

### F. Predecessor → consumer mapping

| Predecessor field/outcome | P2C behavior | Proof |
|---|---|---|
| `PlayRunRecord.run_id` | unchanged | happy-path persistence |
| `campaign_id` / artifact ID | unchanged | target admission assertions |
| `playable_revision` / SHA | source → exact target only at explicit commit | before/after + replay |
| `run_revision` | sole CAS token; +1 once per actual rebase | CAS/recovery tests |
| `rebased_from_run_revision` | explicit completed-rebase receipt; omitted until a rebase commits; cleared by later progress mutation | old-token replay vs progress N→N+1 |
| `progress` | preserved exactly; only target-admitted or block | blocker + equality assertions |
| source manifest | validate if present; absence allowed only for empty progress | compatibility tests |
| P2B1 P1 resolver | derive target manifest; no parser divergence | predecessor suite |
| P2B2 progress PUT | only mechanism to clear old refs / add target refs | composition tests |
| P2A create replay | old binding conflicts after migration; target binding replays | lifecycle regression |

### G. Commit point

```text
Durable decision point:
  rebase intent atomic write
  → from here the operation is forward-recoverable and blocks other Run operations

Logical product commit point:
  target Run atomic replace
  → target manifest is already canonical
  → Run binding/revision now names target

Cleanup:
  delete intent
```

Do not report a clean completed rebase, completed response-loss replay, or current-token same-target no-op while the canonical target Run or target manifest is missing, corrupt, or mismatched. Fail closed without workspace fallback or rewrite.

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Required scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Stable-ref rebase succeeds | rebase service/store | contract/persistence | source N + target M preserving refs | same Run/progress, target binding+manifest, revision +1, no intent/history | any copied/dropped state |
| Empty progress can cross full element replacement | rebase service | compatibility | source refs none, target IDs entirely different | success | old manifest unnecessarily required |
| Missing/replaced refs block before intent | target progress admission | adversarial | current Scene/Beat/resolved/selection/note blocker cases | 409, no intent, source bytes unchanged | silent drop/remap |
| Target must be exact current committed snapshot | workspace admission | adversarial | wrong revision/SHA; advance-before-intent | 409/no intent | latest fallback |
| Target parser semantics remain P2B1 | manifest resolver | regression | malformed/orphan/duplicate/membership fixtures | fail closed | parser drift |
| Run lifecycle lock hides in-process half commit | Run/manifest lifecycle | concurrency | block after target manifest write, start GET | GET waits; returns coherent target only after release | mixed response |
| Progress vs rebase cannot lose update | Run lifecycle CAS | concurrency | same source revision, racing progress and rebase | one linearizes; other 409/503, no overwrite | both mutate from N |
| Workspace mutation cannot split target derivation | workspace lock | concurrency | block during prepare/intent, attempt Runbook commit | mutation waits until coherent intent/commit | mismatched target evidence |
| Intent write failure is pre-transaction | rebase store | failure injection | intent `write_json` fails | source pair exact, no intent | partial canonical change |
| Manifest write failure after intent recovers | recovery | failure injection | intent durable, target manifest write fails | 503 + intent; exact retry completes once | lost/unrecoverable intent |
| Run write failure after target manifest recovers | recovery | failure injection | source Run + target manifest + intent | non-rebase 503; exact retry commits N+1 | mixed pair accepted |
| Cleanup failure after product commit recovers | recovery | failure injection | target pair committed, unlink fails | intent remains; exact retry cleanup; no N+2 | double increment |
| Different request cannot hijack intent | recovery identity | adversarial | pending target M, retry target K | 409, bytes unchanged | intent retarget |
| Corrupt/contradictory intent fails closed | recovery integrity | corruption | tamper intent or canonical stage | 500, no speculative repair | first-match recovery |
| Workspace advance after intent is irrelevant | recovery | restart | prepare intent, force recoverable failure, advance Runbook, retry | completes target from intent; workspace seam can explode | latest-state dependency |
| Completed response-loss replay is idempotent | rebase service | replay | clean N→N+1, exact retry expected N against intact target pair | current target Run+manifest unchanged; no workspace/write; no N+2 | second increment |
| Completed replay proves target pair | rebase service | adversarial | clean N→N+1, then delete/corrupt/retarget the target manifest, exact old-token retry | not 200; 500 fail-closed; no workspace/rewrite; Run bytes unchanged | success from Run record alone |
| Pending intent isolates predecessors | public Run/manifest APIs | integration | GET/list/create/progress/manifest GET+PUT while intent remains | 503/no writes | stale/mixed authority exposed |
| P2B1 replay works after rebase | manifest service | regression | completed target then manifest PUT | exact target manifest unchanged/no workspace | rebuild/rewrite |
| P2B2 progresses target-only ID after rebase | progress service | composition | rebase then progress PUT selecting new target element | N+1→N+2 valid mutation | old manifest still used |
| P2A replay semantics are explicit | Run registry | regression | old-binding create vs target-binding create | old 409; target unchanged success | stale binding accepted |
| No historical Runtime archive | filesystem audit | persistence | successful rebase | one Run + one target manifest + no intent/old per-revision artifacts | retained history |
| P2A/P2B1/P2B2 suites remain green | predecessor boundaries | regression | focused predecessor commands | green | predecessor break |
| Roadmap ownership/sequence still holds | living roadmap | design review | exact-head review | `ROADMAP_REVIEW — ...` | stale design claim |

### Exact verification commands

Run from repository root unless noted:

```bash
uv run pytest -q \
  tests/test_play_run_rebase.py \
  tests/test_live_play_run_rebase.py \
  tests/test_play_run_progress.py \
  tests/test_live_play_run_progress.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_play_run_registry.py \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry_integrity.py

uv run ruff check \
  apps/live_control_server/services/play_run_rebase.py \
  apps/live_control_server/services/play_run_registry.py \
  apps/live_control_server/services/play_run_reference_manifest.py \
  apps/live_control_server/routes/play_runs.py \
  tests/test_play_run_rebase.py \
  tests/test_live_play_run_rebase.py

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-run-rebase.md \
  --pr <PR_NUMBER>

git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

If the bounded test-discovery exception is used, include those paths in focused pytest and scoped ruff when Python.

No TypeScript suite is required by default because P2C must reuse P2B1 parser semantics without changing P1 identity grammar. If implementation changes parser grammar or P1 TypeScript files, **stop** rather than quietly adding a TS gate after expanding scope.

### Minimal live / dogfood proof

Not applicable by default. P2C adds no Play UI. Real temp-root service/HTTP persistence and injected restart/failure boundaries are the owning proof.

### Roadmap review gate

Before final PASS, answer:

```text
Did P2C evidence change ownership, P2 completion, hoist posture, P3 successor
boundary, or assumptions in ROADMAP-playable-hoist-dungeonmind-kernel.md?
```

Record exactly one ledger disposition:

```text
ROADMAP_REVIEW — UPDATED
...
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
...
```

The ledger names the implementation/evidence head, not the later bookkeeping SHA.

Required observation:

```text
P2C_HOIST_OBSERVATION
- Did Run rebase become useful outside Play Runtime? yes/no/not yet
- Did the forward-recovery intent expose a genuinely reusable Buddy transaction primitive? yes/no/not yet
- Did another independent consumer require WorkObjectRevisionRef or WorkObjectElementRef? yes/no/not yet
- Did same-artifact migration require historical Playable storage? yes/no
- Did P2C require caller-authored ID mapping? yes/no
- DungeonMind relevance discovered? none / exact future audit question only
```

Default expected disposition remains **Play-owned / no generic hoist / P2 complete → P3 next**.

### Baseline failure handling

No waiver by default. If a required command fails on the pinned base, record the exact same command on base and head, prove the head adds no failure, and obtain an explicit operator waiver before PASS.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact implementation/evidence head separately from later roadmap bookkeeping head;
3. §1 mission/invariant disposition;
4. §7 required vs produced evidence + provenance;
5. nano-commit/fix story;
6. base/head and actual changed paths vs §4;
7. whether bounded discovery was used;
8. baseline failures/waivers;
9. prior finding ledger on re-review;
10. exact target-admission / blocker / CAS conclusions;
11. exact intent-stage recovery, pending-isolation, and completed-replay pair-integrity conclusions;
12. roadmap disposition + `P2C_HOIST_OBSERVATION`;
13. whether P2 is now complete and P3 remains the named successor.

---

## §9 Acceptance rubric

- [ ] Exactly one same-artifact preserve-only Run rebase capability is delivered.
- [ ] Actual rebase requires exact `expected_run_revision` and exact newer current target revision/SHA.
- [ ] `run_id`, campaign, artifact, created time, and progress remain unchanged across actual rebase.
- [ ] Actual rebase advances `run_revision` exactly once, writes `rebased_from_run_revision` as that source revision, and otherwise changes only binding + updated time in the Run record.
- [ ] Target manifest is derived through existing P2B1 identity/membership semantics.
- [ ] Every existing Runtime reference must survive target admission; missing/wrong-membership references return 409 before intent with no writes.
- [ ] No caller-authored ID mapping or silent drop/remap exists.
- [ ] Missing source manifest is tolerated only for empty progress; malformed/mismatched source manifest fails closed.
- [ ] One durable strict rebase intent is written before either canonical authority changes.
- [ ] Intent contains no Runbook body, source manifest payload, old Run snapshot/history, or generic unrelated transaction state.
- [ ] Existing Run file lock is the outer lifecycle serializer; no second concurrency token is introduced.
- [ ] Run/manifest public operations honor the lifecycle lock and do not recursively reacquire it.
- [ ] Pending intent blocks non-rebase Run/manifest GET/list/create/progress/seal operations with 503 and no write.
- [ ] Normal readers cannot observe the in-process source-Run/target-manifest half state.
- [ ] Failure after intent, after manifest install, and after Run commit are each exactly recoverable by same-request replay.
- [ ] Recovery never consults current workspace state after intent is durable.
- [ ] Different request cannot retarget a pending intent.
- [ ] Contradictory/tampered recovery state fails 500 without speculative repair.
- [ ] Completed response-loss replay returns the current target Run only after proving the persisted target manifest still exists, is well-formed, and binds exactly to that Run; missing/corrupt/mismatched manifest fails closed without workspace fallback or rewrite.
- [ ] Current-token same-target no-op uses the same target-pair integrity proof rather than an implicit early return from the Run record alone.
- [ ] Successful steady state contains exactly one Run + one target manifest and no rebase intent/history artifact.
- [ ] P2B1 manifest replay after rebase returns target sidecar unchanged.
- [ ] P2B2 can mutate target-only references after rebase using the new target manifest.
- [ ] P2A old-binding replay conflicts; target-binding replay returns the current migrated Run.
- [ ] No historical Playable archive, cross-artifact migration, undo, UI, linked runtime handles, Combat/World/Source/Mechanics write, or Runtime→Playable adoption entered scope.
- [ ] Actual changed paths remain inside §4 / bounded discovery.
- [ ] Roadmap review disposition is recorded at the implementation/evidence head.
- [ ] P2 completion / P3 successor truth is explicit in review handback.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

- PR #601 merge state has not been atomically synchronized into P2B2 handoff + roadmap before dispatch;
- merged P2B2 semantics differ materially from the contracts assumed here;
- same-Run rebase cannot be made recoverable across Run+manifest replacement without a new generic transaction framework;
- implementation needs historical Runbook Markdown/Tiptap bytes to prepare or recover the target;
- implementation wants to retain old manifests or Run snapshots as per-revision history;
- correct migration requires caller-authored old-ID → new-ID mapping inside the rebase request;
- cross-artifact migration becomes necessary;
- correct target admission requires P1 parser grammar changes;
- progress must be transformed implicitly rather than preserved or pre-edited through P2B2;
- a second Run concurrency/revision token becomes necessary;
- rollback/abort semantics become necessary after intent durability;
- `linkedRuntimeHandles` / Combat migration becomes required;
- UI/operator conflict-resolution workflow becomes required;
- a required production path falls outside §4;
- another active lane owns a §4 path or shared Runtime state;
- owning-boundary crash/recovery or concurrency proof cannot be produced;
- baseline/head gate requires an unapproved waiver;
- roadmap/architecture conflict appears.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed split/re-brief:
State-authority update needed:
```
