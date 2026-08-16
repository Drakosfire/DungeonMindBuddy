---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P2B2
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-run-progress-cas.md
  - Branch / PR: agent/play-run-progress-cas / `PLAY: persist CAS Run progress`

  ## Verification pointer
  - Design anchor: PR #599 reviewed head `226d6a5f04055faaf7b8164fee1d85940c0b37a6`
  - Base/head: `13ef4d806f2961b8a26f3474a07b9f1e76165f28` / <implementation head>
  - Predecessor: merged PR #599 / P2B1 immutable Run-bound Playable reference manifest
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — persist CAS Run progress against the sealed manifest

> **MERGED / HISTORICAL (2026-08-16):** PR **#601** merged as
> `51ed2a6e89b56d2ef033215e23d309ce03a51c87` after **2 review cycles**.
> Reviewed head `c9d2697c1f7e6b11235a753ceb45c4e514a423eb`;
> implementation/evidence head `8538409e1027ca8e84990bd86cd07ee2ccf99a72`.
> P2B2 persisted one full Run-progress snapshot under `run_revision` CAS
> against the sealed P2B1 manifest. Successor:
> [`HANDOFF-PLAY-run-rebase.md`](HANDOFF-PLAY-run-rebase.md)
> (P2C explicit preserve-only Run rebase to a newer Playable revision).

**Created:** 2026-08-15  
**Status:** MERGED — PR #601 / main `51ed2a6e89b56d2ef033215e23d309ce03a51c87`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-run-progress-cas.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P2B2`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** PR #599 final reviewed head `226d6a5f04055faaf7b8164fee1d85940c0b37a6`  
**Implementation base:** `13ef4d806f2961b8a26f3474a07b9f1e76165f28`  
**Suggested branch:** `agent/play-run-progress-cas`  
**PR title:** `PLAY: persist CAS Run progress`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — merge P2B1, close its state, then pin P2B2

PR #599 is review-complete at:

```text
226d6a5f04055faaf7b8164fee1d85940c0b37a6
Review cycles: 3
```

That is **not** merge authority. Before CODE dispatch:

1. PR #599 must actually merge;
2. one guarded post-#599 state-authority sync must:
   - mark `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md` merged/historical with the exact PR #599 merge SHA and **3 review cycles**;
   - update `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` so the integration tip and merged capability name P2B1, P2B2 is current next, this handoff is current next, P2C is the named successor, and the Play-owned hoist posture remains truthful;
   - update this handoff from `DESIGNED / DO NOT DISPATCH` to active implementation and replace every `PIN_AFTER_POST_599_STATE_SYNC` with the exact state-sync merge/base SHA;
   - make no stable architecture edit unless the merged P2B1 evidence contradicts an architecture claim;
3. re-read current `main`, P2A Run record code, merged P2B1 manifest code, and the current roadmap;
4. run:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-run-progress-cas.md
```

5. stop if the merged P2B1 contract, Run record shape, `run_revision` semantics, manifest immutability, lock/persistence primitive, route namespace, or §4 ownership changed materially.

Required sequence after sync:

```text
P2A  — durable Run identity + exact Playable revision/digest binding     MERGED
P2B1 — immutable Run-bound Playable reference manifest                  MERGED
P2B2 — durable CAS Run progress against the sealed manifest             NEXT
P2C  — explicit Run rebase/migration to a newer Playable revision       FALSE
```

`linkedRuntimeHandles` remains deferred until a real Combat/other-runtime consumer requires it.

---

## §1 Mission and merge-ready invariant

**Mission:** DungeonBuddy can durably replace one Run's current table-progress snapshot — current Scene/Beat, resolved Beats, authored Choice selections, and element notes — against the immutable P2B1 reference manifest, so a table run can survive reload/restart without mutating authored Playable Material or trusting the current Runbook revision.

**Merge-ready invariant:**

> **For one existing P2A Run with one valid sealed P2B1 manifest, every successful progress write is a single atomic compare-and-swap transition of the authoritative Run record from exact `run_revision = N` to `N+1`, preserving the immutable Run→Playable binding and validating every persisted Playable reference against that Run's sealed manifest; stale competing state never overwrites a newer Run, current/latest Runbook bytes are never consulted as fallback, persisted progress is revalidated fail-closed on reload, and no progress sidecar, second concurrency token, Playable mutation, migration/rebase, event history, Combat state, World/Source/Mechanics write, or UI workflow is introduced.**

### Why this is one capability

The progress fields are independently meaningful to the GM, but they share one durable object, one concurrency token, one reference-admission authority, one mutation endpoint, and one failure model. Splitting Scene, Beat, choice, and note writes into separate PRs would duplicate the same CAS contract and create avoidable intermediate Run schemas.

P2B2 therefore owns one **full progress snapshot replacement**:

```text
current Scene / Beat
resolved Beats
Choice → Option selections
notes by Playable element ID
```

It does not own a timeline of how that snapshot was reached.

### Record-shape decision — no second progress sidecar

P2B2 must keep mutable progress in the existing one-file Run authority under:

```text
out/runtime/play/runs/{run_id}.json
```

Do **not** add `out/runtime/play/progress/...` or another durable progress file.

Reason:

```text
run_revision
+ the progress state protected by that revision
```

must commit atomically. A second file would create a multi-file commit/recovery problem and effectively a second state authority.

P2B2 may add one nested `progress` object to the existing internal Play-owned `dmb_play_run_record_v1` record. Existing P2A records without the field must load as the empty progress state and must not be rewritten merely by GET/list/replay.

This additive-v1 decision is permitted only because re-anchor currently finds no independent production consumer of the exact closed P2A JSON field set; `PlayRunRecord` and its handoff are the only repository authorities found for `dmb_play_run_record_v1`. If dispatch-time discovery finds an independent consumer that requires exact v1 field closure, **stop** and re-brief a versioned Run-record migration rather than silently breaking it.

### Canonical progress shape

```text
progress:
  current_scene_id: <scene:* | null>
  current_beat_id: <beat:* | null>
  resolved_beat_ids: [<beat:*>, ...]
  selections:
    <choice:*>: <option:*>
  notes_by_element_id:
    <scene:*|beat:*|choice:*|option:*>: <exact note text>
```

Rules:

- empty progress is `null / null / [] / {} / {}`;
- `resolved_beat_ids` is a set-like snapshot, **not resolution history**; persist duplicate-free lexicographic order;
- `selections` is current mapping state, not a choice-event history;
- `notes_by_element_id` is current scratch-note text, not an append-only journal;
- note text round-trips exactly; do not trim or normalize it;
- object/map key ordering has no product meaning even if the writer emits deterministic order;
- omitting a selection/note from the next full replacement removes it;
- `current_beat_id` may be non-null only when `current_scene_id` is non-null and the Beat belongs to that exact Scene;
- a resolved Beat may belong to any Scene in the bound manifest;
- a selected Choice/Option may belong to any Scene in the bound manifest;
- a note may target any of the four P1 element kinds;
- current Beat may also appear in `resolved_beat_ids`; P2B2 does not invent a workflow rule forbidding that state.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Add one empty/default progress snapshot to the Run record | No; representation needed by mutation/read | Same Run contract | **Include** |
| Replace progress snapshot under `run_revision` CAS | Yes | Existing Run authority + one mutation API | **Include** |
| Validate Scene/Beat/Choice/Option references against P2B1 manifest | No; safety clause of same mutation | Existing manifest authority | **Include** |
| Revalidate persisted progress on GET/list/create replay | No; persistence integrity clause | Same Run contract | **Include** |
| Immediate response-loss replay/no-op recognition | No; replay clause | Same mutation API | **Include** |
| Separate per-field PATCH endpoints | Yes | Additional mutation workflows | **Exclude** |
| Progress sidecar | Yes | Second durable Runtime authority | **Prohibited** |
| Progress event log/history/audit stream | Yes | New durable history contract | **Exclude** |
| Auto-seal/rebuild missing P2B1 manifest | Yes | Changes P2B1 lifecycle | **Prohibited** |
| Read/parse current Runbook to validate refs | No | Unsafe fallback | **Prohibited** |
| Explicit rebase/migration to newer Playable | Yes | Lifecycle transition | **Exclude — P2C** |
| `linkedRuntimeHandles` / Combat linkage | Yes | Cross-runtime contract | **Exclude** |
| Play surface controls/projection | Yes | UI/operator workflow | **Exclude — later Play projection** |
| Runtime → Playable adoption | Yes | Proposal/adoption workflow | **Exclude — P5** |
| Generic Buddy/DungeonMind runtime state abstraction | Yes | Cross-domain contract | **Exclude — hoist review only** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path is one exact Run-record progress snapshot protected by the Run's one CAS token and admitted only by the Run's one immutable manifest. |
| Most likely adversarial sequence | Two callers read `run_revision=N`; A writes valid progress X; B writes different valid progress Y with the same expected N. Required: exactly one atomic N→N+1 write; loser gets 409; winner remains byte/semantic authority. |
| Will §7 actually detect that failure? | Yes. An owning service concurrency test interleaves two real writes against one temp Run file and proves one winner / one 409 / no lost update. |
| Easiest owning boundary to under-test | Persisted integrity. Request-time validation can be perfect while tampered on-disk progress later reloads as truth. §7 therefore corrupts persisted references and proves GET/list/create replay fail 500 without rewrite. |
| Fact that forces stop/split | Need for a second token/file, historical event ordering, current Runbook fallback, automatic manifest creation, P2C migration, UI workflow, Combat linkage, or an independent exact-v1 consumer. |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 Core invariant;
   - §4.2 stable element identity;
   - §6 choices/branching;
   - §7 Runtime State + §7.1 Runtime invariants;
   - §11 persistence/revision rules.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - P2 decomposition;
   - merged P2A/P2B1 evidence and hoist posture;
   - P2B2/P2C boundary.
3. merged P2A:
   - `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md`;
   - `apps/live_control_server/services/play_run_registry.py`;
   - `apps/live_control_server/routes/play_runs.py`.
4. merged P2B1:
   - `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md`;
   - `apps/live_control_server/services/play_run_reference_manifest.py`;
   - `tests/test_play_run_reference_manifest.py`;
   - `tests/test_live_play_run_reference_manifest.py`.
5. `apps/live_control_server/services/registry_file_lock.py`.
6. `src/live_play/live_store.py`.
7. `AGENTS.md`.
8. `Docs/Process/STEWARD-CYCLE.md`.

### Predecessor contracts consumed unchanged

#### P2A Run authority

P2A owns:

```text
run_id
campaign_id
playable_artifact_id
playable_revision
playable_content_sha256
run_revision
created_at
updated_at
```

`run_revision` begins at 1 and was explicitly reserved for successor progress CAS. P2B2 must use it; no ETag, digest token, manifest revision, or progress revision may be introduced.

The immutable binding fields remain immutable in P2B2.

#### P2B1 reference-admission authority

P2B1 owns exactly one immutable sidecar:

```text
out/runtime/play/reference-manifests/{run_id}.json
```

with exact Run/artifact/revision/SHA binding and canonical Scene/Beat/Choice/Option entries plus membership.

P2B2 trusts that sidecar only after P2B1's persisted model/binding validation succeeds. P2B2 does not parse Markdown and does not consult workspace-document current state.

### Lane table

| Field | Required content |
|---|---|
| Parent authority | `ARCHITECTURE-playable-material-and-runtime.md` + living Playable hoist roadmap |
| Base revision | `13ef4d806f2961b8a26f3474a07b9f1e76165f28` |
| Predecessor contract | merged PR #599 / P2B1 immutable bound reference manifest + P2A Run CAS token |
| Exact input consumed | existing Run UUID + `expected_run_revision` + complete caller-authored progress snapshot |
| Output | same authoritative Run record, unchanged for no-op/replay or atomically advanced exactly one revision with validated progress |
| Named successor | `P2C — explicit Run rebase/migration to a newer Playable revision` |
| What remains false | no rebase/migration, no linked runtime handles, no event history, no Play UI/projection, no Runtime→Playable adoption |
| Explicit non-goals | current Runbook parsing, manifest creation/mutation, partial field PATCH, World/Source/Mechanics/Combat writes, generic kernel contract |
| Branch / isolated checkout | `agent/play-run-progress-cas` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | existing `/api/live/play-runs` router, Run JSON files, P2B1 manifest helper, living roadmap; serialize with any lane touching those paths/runtime files |
| Runtime/state ownership | tests use temp repo roots only; production Run files remain under `out/runtime/play/runs/`; manifest is read-only prerequisite |
| State-authority sync set after merge | this handoff completion + living Playable hoist roadmap current sequence; stable architecture only if evidence changes a claim |

---

## §3 Observable paths and adversarial sequences

### Canonical P2B2 API

```http
PUT /api/live/play-runs/{run_id}/progress
```

Request — **full replacement, not PATCH**:

```json
{
  "expected_run_revision": 3,
  "progress": {
    "current_scene_id": "scene:gate",
    "current_beat_id": "beat:arrival",
    "resolved_beat_ids": ["beat:briefing"],
    "selections": {
      "choice:route": "option:fire"
    },
    "notes_by_element_id": {
      "beat:arrival": "Door barred from the inside."
    }
  }
}
```

All five progress members are required in the request so omission cannot accidentally mean either "leave unchanged" or "clear". Nullable/empty values express clearing explicitly.

Response:

```text
PlayRunRecord
```

There is no separate P2B2 GET endpoint. Existing:

```http
GET /api/live/play-runs/{run_id}
GET /api/live/play-runs
PUT /api/live/play-runs/{run_id}   # P2A create/replay
```

return the authoritative Run record including the progress snapshot after P2B2.

### Mutation / replay semantics

For a valid bound manifest and canonical requested progress:

```text
expected == current run_revision
  requested progress differs
    → atomic write
    → run_revision += 1
    → updated_at changes
    → created_at + immutable binding unchanged

expected == current run_revision
  requested progress equals current
    → semantic no-op
    → return current record unchanged
    → no timestamp/revision/file rewrite

expected == current run_revision - 1
  requested progress equals current
    → immediate response-loss replay
    → return current record unchanged
    → no timestamp/revision/file rewrite

any other stale expected revision
  → 409
  → no write
```

The narrow `N` → current `N+1` equality replay exists only to make:

```text
write committed
→ HTTP response lost
→ caller retries exact same request with expected N
```

safe without double-incrementing the Run.

A stale request that asks for different progress always returns 409.

### Reference-admission rules

Build a lookup from the validated P2B1 manifest.

| Progress reference | Required manifest fact |
|---|---|
| `current_scene_id` | included element of `kind=scene` |
| `current_beat_id` | included element of `kind=beat`; its `scene_id` equals `current_scene_id` |
| each `resolved_beat_ids[]` | included element of `kind=beat` |
| each `selections` key | included element of `kind=choice` |
| each `selections` value | included element of `kind=option`; its `choice_id` equals the mapping key |
| each `notes_by_element_id` key | included element of any P1 kind |

Invalid caller references are 422 and write nothing.

Persisted references violating the same rules are integrity corruption: GET/list/create-replay/mutation must fail 500 and must not silently clear, retarget, or rewrite the record.

### Observable path table

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| New Run create | binding-only Run, revision 1 | same binding plus empty progress state; revision 1 | Yes | Run registry |
| Legacy P2A Run without `progress` field | loads exact old record shape | load as empty progress in memory; no read-time rewrite | Yes | Run registry |
| First valid progress PUT | no mutation API | validate bound manifest, atomically persist N→N+1 | Yes | Run registry + route |
| Current-token identical PUT | n/a | exact no-op; bytes/timestamps/revision unchanged | Yes | Run registry |
| Lost-response exact replay | n/a | immediate N→N+1 equality replay returns current unchanged | Yes | Run registry |
| Competing stale different PUT | n/a | 409, winner remains authority | Yes | Run registry lock/CAS |
| Unknown Run | n/a | 404, no write | Yes | Run registry |
| Invalid Run UUID/body | n/a | 422, no write | Yes | route/model |
| Missing P2B1 manifest before first progress mutation | no progress write | 409; never auto-seal or consult Runbook | Yes | Run progress admission |
| Malformed/mismatched manifest | n/a | 500, no Run mutation | Yes | P2B1 persisted authority |
| Unknown/wrong-kind progress ID | n/a | 422, no write | Yes | manifest-backed progress validation |
| Current Beat belongs to another Scene | n/a | 422, no write | Yes | manifest membership validation |
| Option does not belong to selected Choice | n/a | 422, no write | Yes | manifest membership validation |
| Runbook advances after P2B1 seal | current workspace differs from Run binding | progress PUT still succeeds against sealed manifest; no workspace read | Yes | Run progress service |
| GET after restart | binding reload | exact persisted progress reloaded and revalidated | Yes | Run authority |
| List after restart | binding list | progress revalidated for every record; corruption fails whole list | Yes | Run authority |
| P2A create replay after progress | returns existing binding record | returns current Run unchanged; never resets progress/revision | Yes | Run registry |
| Tampered persisted progress ref | no progress fields yet | 500 on authoritative read/replay; no repair/rewrite | Yes | Run persisted integrity |
| Manifest bytes during progress PUT | immutable sidecar | byte-for-byte unchanged | Yes | P2B1 authority |
| Runbook bytes during progress PUT | authored authority | unchanged / not read | Yes | Playable authority |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| A reads N → B reads N → A writes X → B writes Y | one N→N+1 winner; loser 409; final state exactly winner | interleaved CAS service test |
| write N→N+1 commits → response lost → exact request retries with expected N | return current N+1 unchanged; no second write | response-loss replay test |
| current N+1 → same progress with expected N+1 | no-op; byte-for-byte unchanged | current-token no-op test |
| Run created → P2B1 not sealed → progress PUT | 409; no Run rewrite; no workspace parse/auto-seal | missing-manifest test |
| Run + manifest sealed at Playable N/A → Runbook commits N+1/B → progress PUT | succeeds using sidecar only | post-advance no-workspace test |
| valid progress persisted → on-disk `current_scene_id=scene:ghost` tamper → GET/list/create replay | 500; tampered bytes remain; no default/reset | persisted-corruption tests |
| valid selection persisted → on-disk option retargeted to another Choice → GET | 500; no rewrite | membership-corruption test |
| legacy P2A record lacks `progress` → manifest exists → first progress PUT | loads empty state, writes one additive P2B2 record at revision 2 | legacy upgrade-on-mutation test |
| valid progress PUT → manifest file compared before/after | exact same manifest bytes | manifest immutability regression |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create / Modify | `Docs/Plans/HANDOFF-PLAY-run-progress-cas.md` | checked-in P2B2 slice authority; pin/status/evidence handback |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | mandatory P2B2 review-ledger disposition only; current sequence is synchronized before dispatch |
| Modify | `apps/live_control_server/services/play_run_registry.py` | additive progress model, persisted integrity validation, one-file CAS/no-op/replay mutation |
| Modify | `apps/live_control_server/services/play_run_reference_manifest.py` | expose/reuse one record-bound validated manifest loader so Run integrity can validate persisted progress without workspace fallback or parser duplication |
| Modify | `apps/live_control_server/routes/play_runs.py` | add the one full-snapshot progress PUT endpoint |
| Modify | `tests/test_play_run_registry.py` | update P2A regression expectations for additive empty progress while preserving binding/replay behavior |
| Create | `tests/test_play_run_progress.py` | owning service/persistence/CAS/reference-integrity/adversarial proof |
| Create | `tests/test_live_play_run_progress.py` | HTTP contract/status/full-replacement/replay proof |

### Bounded discovery exception

```text
Directory:
  tests/

Maximum additional paths:
  1

Allowed path kinds:
  existing Play Run integrity regression test only

Decision rule:
  allowed only if the additive `progress` field requires a focused compatibility
  assertion in an existing P2A integrity file; no production path, schema owner,
  UI, manifest grammar, or new workflow may enter through this exception.
```

A required production path outside the explicit lease is a stop report.

### Parallel/runtime collision note

This handoff may be designed while PR #599 is open because this design branch creates only this new handoff path. **CODE may not dispatch** until PR #599 is merged and the state sync closes its roadmap/handoff lease.

Future P2B2 implementation owns mutations of `out/runtime/play/runs/{run_id}.json` during tests/operation. It reads P2B1 manifest files but must never mutate them.

---

## §5 Explicitly out of scope / collision boundary

| Path / authority | Why this slice must not touch or claim it |
|---|---|
| P1 Markdown/TipTap identity files | P2B2 consumes P2B1 manifest; it does not parse or change authored identity grammar |
| workspace-document registry / Markdown write services | current Runbook state is not a progress authority or fallback |
| `out/runtime/play/reference-manifests/**` | immutable P2B1 authority; read-only in P2B2 |
| `apps/live_control_server/main.py` | Play Runs router already mounted |
| `apps/live-control-ui/src/**` | no UI/operator workflow in P2B2 |
| Combat services/state | `linkedRuntimeHandles` deferred |
| World/Source/Mechanics registries | Runtime progress cannot publish or mutate these authorities |
| DungeonMind / DungeonMindDnD | no cross-repo contract in this slice |
| P2C binding/manifest migration | separate lifecycle invariant |
| Runtime→Playable proposal/adoption | later explicit adoption flow |

---

## §6 Implementation contract

```text
Input:
  existing Run UUID
  expected_run_revision
  complete progress replacement payload
  existing immutable P2B1 manifest bound to that Run

Output:
  one authoritative PlayRunRecord:
    unchanged for semantic no-op / exact immediate replay
    OR atomically rewritten once with run_revision + 1 and validated progress

Invariant:
  same §1 invariant

Failure behavior:
  invalid run/body/reference -> 422/404 as specified, no write
  missing required manifest -> 409, no write, no auto-seal
  stale different CAS -> 409, no write
  persisted Run/manifest/progress corruption -> 500, no repair/rewrite
  write failure before atomic replace -> 500, prior Run remains authority

Replay / idempotency:
  current-token same progress -> return exact current record unchanged
  immediately stale N with current N+1 and same progress -> return exact current record unchanged
  stale token with different progress -> 409
  retry after pre-commit failure -> same expected token may retry
  retry after committed-but-response-lost write -> immediate equality replay returns committed record

Trust boundary:
  Verifies:
    Run persisted model and filename identity
    P2B1 manifest persisted model + exact Run binding
    all progress reference kinds/membership
    expected_run_revision / replay relation
  Records/trusts without proving:
    exact note text as operator-authored Runtime content
    no semantic interpretation of note text or choice meaning
```

### Commit point

```text
Commit point:
  atomic replace of out/runtime/play/runs/{run_id}.json via existing write_json

Before commit:
  persisted Run remains exact authority; no manifest/workspace mutation

After commit:
  new Run bytes at run_revision N+1 are authority

Truthful result after post-commit response failure:
  exact immediate replay returns the committed record unchanged
```

### A. State / fallback matrix

| Observable path | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|
| Progress PUT | one atomic Run transition | unknown Run 404 / missing manifest 409 | filesystem write error 500 | malformed Run/manifest/progress 500 | different stale CAS 409 | narrow equality replay/no-op |
| Run GET | validated current Run + progress | unknown Run 404 | n/a | bad persisted progress/manifest 500 | n/a | deterministic read |
| Run list | validated records | empty list | n/a | any corrupt persisted progress fails closed | n/a | deterministic read |
| P2A create replay | current existing Run unchanged | new create follows P2A | workspace only for genuinely new Run | corrupt existing Run/progress 500 | different binding 409 | never resets progress |

**Fallback:** none. Current/latest Runbook bytes are never a reference-admission fallback after P2B1.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Scene ref | exact manifest `scene:*` | missing/wrong kind rejected | No |
| Beat ref | exact manifest `beat:*`; current Beat must match current Scene membership | mismatch rejected | No |
| Choice selection key | exact manifest `choice:*` | missing/wrong kind rejected | No |
| Option selection value | exact manifest `option:*` belonging to exact Choice | cross-choice rejected | No |
| Note key | exact included manifest element ID of any kind | missing rejected | No |
| Labels/titles/order | never identity | not consulted | No |
| Runbook newer revision | remains unrelated to this Run's progress admission until P2C | no auto-retarget | No |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| New Run after P2B2 | same Run JSON with empty progress, revision 1 | exact binding + empty progress | P2A replay unchanged | additive internal v1 field | delete test temp only; no product delete API added |
| Progress write | same Run JSON, revision N+1 | exact validated snapshot after restart | current no-op + immediate equality replay | legacy record without progress loads empty; first mutation persists progress | stale writer never overwrites |
| GET/list | same file authority | persisted progress revalidated against sidecar | read-only | no read-time rewrite | n/a |

### D. Predecessor → consumer mapping

**Grounding source:** merged P2A `PlayRunRecord` + merged P2B1 `PlayRunReferenceManifest`.

| Predecessor field/outcome | Real shape/optionality | P2B2 behavior | Transformation | Proof |
|---|---|---|---|---|
| `PlayRunRecord.run_revision` | positive int, starts 1 | sole CAS token | N → N+1 only on actual different successful state write | CAS tests |
| Run binding quartet | immutable IDs/revision/SHA | preserved exactly | none | before/after assertions |
| manifest Scene entry | exact kind/id | admits current Scene/note | lookup only | reference tests |
| manifest Beat entry + `scene_id` | exact membership | admits current/resolved Beat | lookup + current-scene equality | membership tests |
| manifest Choice entry + `scene_id` | exact membership | admits selection key/note | lookup only | selection tests |
| manifest Option entry + `choice_id` + `scene_id` | exact membership | admits selected option/note | lookup + choice equality | selection tests |
| missing manifest | 404 in P2B1 GET | progress precondition failure | remap to 409 for mutation only | missing-manifest test |
| malformed/mismatched manifest | 500 | block progress/read integrity | preserve 500 | corruption tests |

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Full valid snapshot persists and reloads | Run service | contract/persistence | focused progress test | revision +1, exact progress after fresh read | any lost field/reference |
| Every reference validates against sealed manifest | Run service | adversarial | unknown/wrong-kind/cross-membership cases | 422, Run bytes unchanged | permissive admission |
| Missing manifest never auto-seals | Run service | adversarial | create Run but do not seal; PUT progress | 409; no manifest/Run rewrite; no workspace call | any fallback/create |
| Runbook advance is irrelevant after seal | Run service | regression | seal at N → advance Runbook → PUT progress | success against manifest; workspace lookup can be monkeypatched to explode | current-state dependency |
| CAS prevents lost update | Run file lock + service | concurrency | two writers same expected N, different snapshots | exactly one success, one 409, final state winner | both succeed / overwrite |
| Current-token same-state PUT is no-op | Run service | replay | exact same progress at current revision | identical bytes/timestamps/revision | revision churn |
| Lost-response replay is idempotent | Run service | replay | successful N→N+1 then exact retry expected N | returns N+1; bytes unchanged | double increment |
| P2A create replay never resets progress | Run registry | regression | mutate progress then original create PUT | current progressed record unchanged | reset/rewrite |
| Persisted progress is revalidated on authoritative reads | Run registry | corruption | tamper ghost/cross-membership ID then GET/list/create replay | 500, tampered bytes unchanged | silent load/reset |
| Legacy P2A record remains readable | Run registry | compatibility | remove/omit `progress` field | empty progress in memory; no read rewrite | forced migration on read |
| Legacy record can receive first progress mutation | Run service | compatibility | legacy bytes + valid manifest + PUT expected 1 | one atomic revision-2 progressed record | migration split/partial write |
| Manifest remains immutable | P2B1 authority | regression | byte-compare before/after progress writes | identical manifest bytes | any sidecar mutation |
| P2A/P2B1 regressions remain green | predecessor boundaries | regression | focused predecessor suites | green | predecessor break |
| Roadmap ownership/sequence still holds | living roadmap | design review | exact-head review | `ROADMAP_REVIEW — ...` | stale design claim |

### Exact verification commands

Run from repository root unless noted:

```bash
uv run pytest -q \
  tests/test_play_run_progress.py \
  tests/test_live_play_run_progress.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_play_run_registry.py \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry_integrity.py

uv run ruff check \
  apps/live_control_server/services/play_run_registry.py \
  apps/live_control_server/services/play_run_reference_manifest.py \
  apps/live_control_server/routes/play_runs.py \
  tests/test_play_run_progress.py \
  tests/test_live_play_run_progress.py \
  tests/test_play_run_registry.py

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-run-progress-cas.md \
  --pr <PR_NUMBER>

git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

If the bounded test-discovery exception is used, include that path in scoped ruff when Python and in the focused pytest command.

No TypeScript suite is required by default: P2B2 must not change P1 Markdown/TipTap identity or parser semantics. If implementation unexpectedly requires a UI/P1 file, stop rather than adding TS verification after the fact.

### Minimal live / dogfood proof

Not applicable — P2B2 exposes no Play UI. HTTP/service integration against temp-root real persistence is the owning boundary. P3 or a later Play surface slice owns table controls.

### Roadmap review gate

Before final PASS, answer:

```text
Did P2B2 evidence change ownership, sequence, hoist posture, successor boundaries,
or assumptions in ROADMAP-playable-hoist-dungeonmind-kernel.md?
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
P2B2_HOIST_OBSERVATION
- Did Run-progress CAS become useful outside Play Runtime? yes/no/not yet
- Did P2B2 expose a real shared Buddy runtime-state primitive? yes/no/not yet
- Did another independent consumer require WorkObjectRevisionRef or WorkObjectElementRef?
- Did progress integrity require a generic cross-domain reference validator?
- DungeonMind relevance discovered? none / exact future audit question only
```

Default expected disposition remains **Play-owned / not yet**.

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
10. exact CAS/replay/persisted-integrity conclusions;
11. roadmap disposition + `P2B2_HOIST_OBSERVATION`;
12. named successor `P2C` still false.

---

## §9 Acceptance rubric

- [ ] Exactly one Run-progress snapshot capability is delivered.
- [ ] Progress is stored in the same authoritative Run file protected by `run_revision`; no second progress file/token exists.
- [ ] Immutable P2A Run binding is byte/semantic-preserved across progress mutation.
- [ ] Every non-null/set progress reference is admitted by the exact P2B1 manifest with required kind/membership.
- [ ] Missing manifest fails 409 without auto-seal/current-Runbook fallback.
- [ ] Malformed/mismatched manifest and malformed persisted progress fail 500 without rewrite.
- [ ] Successful different-state mutation advances `run_revision` exactly once and updates only mutable Run state/timestamp.
- [ ] Current-token identical state is a no-op with exact bytes unchanged.
- [ ] Immediate lost-response replay returns the committed current record without another increment.
- [ ] Two concurrent same-token different writes cannot both succeed.
- [ ] GET/list/P2A replay revalidate non-empty persisted progress and never silently reset it.
- [ ] Legacy P2A records lacking `progress` remain readable without read-time rewrite and can receive one safe first mutation.
- [ ] Runbook changes after P2B1 seal are not consulted by progress mutation.
- [ ] P2B1 manifest bytes remain unchanged.
- [ ] No P2C migration, event history, linked runtime handles, UI, Combat/World/Source/Mechanics write, or adoption workflow entered scope.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Roadmap review disposition is recorded at the implementation/evidence head.
- [ ] P2C remains unimplemented/unclaimed.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

- PR #599 is not merged or post-merge state authorities disagree;
- P2B1 merged semantics differ materially from the reviewed `226d6a5f...` contract used here;
- progress cannot commit atomically with `run_revision` in one Run file;
- implementation needs a second progress sidecar or concurrency token;
- an independent consumer requires exact closed `dmb_play_run_record_v1` shape, forcing explicit schema-version migration design;
- correct reference validation requires current/latest Runbook bytes or P1 parser changes;
- P2B1 manifest must be created, rebuilt, or mutated by progress code;
- progress needs event ordering/history rather than current snapshot state;
- P2C rebase/migration semantics become necessary to make the current slice correct;
- linked Combat/runtime handles become required;
- a UI/operator workflow is required;
- required production path falls outside §4;
- another active lane owns a §4 path or shared Run-state resource;
- owning-boundary concurrency/reload/corruption proof cannot be produced;
- baseline/head gate requires an unapproved waiver;
- roadmap/architecture conflict appears.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
