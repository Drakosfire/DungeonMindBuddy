---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P2B1
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md
  - Branch / PR: agent/play-run-reference-manifest / `PLAY: seal Run-bound Playable reference manifest`

  ## Verification pointer
  - Design anchor: `bc80f7125499817050f08abc79b71b87d327b2a9` (merge of PR #596 / P2A)
  - Base/head: <f29132f14e0a29565979c3de95dce6d01976db05> / <implementation head>
  - Predecessor: merged PR #596 / P2A exact Run→Runbook revision+digest binding
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — seal exact Run-bound Playable reference manifest

> **MERGED / HISTORICAL (2026-08-15):** PR **#599** merged as
> `26ddd83ddbec381c816fbd2ede891aa5d816b9e1` after **3 review cycles**. P2B1
> sealed the immutable Run-bound Playable reference manifest (canonical
> Scene/Beat/Choice/Option IDs and membership only). Successor:
> [`HANDOFF-PLAY-run-progress-cas.md`](HANDOFF-PLAY-run-progress-cas.md)
> (P2B2 durable CAS Run progress against the sealed manifest).

**Created:** 2026-08-15  
**Status:** MERGED — PR #599 / main `26ddd83ddbec381c816fbd2ede891aa5d816b9e1`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P2B1`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #596 at `main` `bc80f7125499817050f08abc79b71b87d327b2a9`  
**Implementation base:** `f29132f14e0a29565979c3de95dce6d01976db05`  
**Suggested branch:** `agent/play-run-reference-manifest`  
**PR title:** `PLAY: seal Run-bound Playable reference manifest`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — close P2A state and pin the implementation base

PR #596 is merged as:

```text
bc80f7125499817050f08abc79b71b87d327b2a9
```

Before CODE dispatch, one guarded post-#596 state-authority sync must:

1. mark `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md` merged/historical with PR #596, merge `bc80f7125499817050f08abc79b71b87d327b2a9`, and **2 review cycles**;
2. update `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` so:
   - integration tip names merged PR #596 / `bc80f7125499817050f08abc79b71b87d327b2a9`;
   - P2A is recorded as merged;
   - the former P2B is decomposed into P2B1/P2B2 below;
   - P2B1 is the current next slice;
   - this handoff is the current next handoff;
   - Runtime remains DungeonMindBuddy Play-owned;
   - `WorkObjectRevisionRef` and `WorkObjectElementRef` remain not yet justified;
3. check in this handoff;
4. make no stable architecture edit unless the sync review finds an actual contradiction.

Required P2 decomposition after this design review:

```text
P2A  — durable Run identity + exact Playable revision/digest binding     MERGED
P2B1 — immutable Run-bound Playable reference manifest                  NEXT
        exact Scene/Beat/Choice/Option IDs + membership only
P2B2 — durable CAS Run progress against the P2B1 manifest
        current Scene/Beat, resolved Beats, selections, notes
P2C  — explicit Run rebase/migration to a newer Playable revision
        with fail-closed missing/replaced reference handling
```

`linkedRuntimeHandles` stays deferred until a real Combat/other runtime consumer requires it.

After the state sync lands:

1. fetch/re-read current `main`;
2. replace `f29132f14e0a29565979c3de95dce6d01976db05` everywhere in this handoff with that exact SHA;
3. verify P2A Run service/routes and P1 identity/index authorities still match §2;
4. verify the roadmap still names P2B1 next;
5. run:

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md
```

6. stop if the base, Run record contract, workspace snapshot semantics, P1 marker grammar, lock/persistence primitives, or §4 ownership materially changed.

The pin-at-dispatch edit is handoff completion, not capability expansion.

---

## §1 Mission and merge-ready invariant

**Mission:** DungeonBuddy can seal one immutable reference-admission manifest for an existing P2A Run from the exact committed Runbook revision that Run is bound to, so later Runtime progress can validate stable Scene/Beat/Choice/Option references after the authored Runbook moves on without copying prose or inventing a historical Playable archive.

**Merge-ready invariant:**

> **For one existing Run UUID, DungeonBuddy either durably seals exactly one immutable manifest whose Run/artifact/revision/content-SHA identity exactly equals the P2A binding and whose entries are a deterministic, fail-closed derivation of only canonical P1 Scene/Beat/Choice/Option IDs plus their membership, or it writes nothing; identical seal replay returns the exact persisted manifest unchanged without consulting current workspace state, a Runbook that has already advanced cannot be substituted for the bound revision, malformed/ambiguous Playable identity cannot be admitted, and the manifest contains no authored prose, display labels, progress state, World/Source/Mechanics truth, or migration behavior.**

### Why the former P2B is split again

P2A proved exact Run→Playable revision binding, but intentionally persisted no Playable structure.

The next runtime fields require owning-boundary validation:

```text
currentSceneId
currentBeatId
resolvedBeatIds[]
choiceId → optionId
notesByElementId
```

A direct P2B progress implementation now has **two independently useful durable outcomes**:

1. establish an exact durable reference-admission authority for the bound Playable revision;
2. mutate Run progress under CAS using that authority.

Those are separable and have different failure models.

There is also a version-availability problem that must be solved before progress writes:

```text
Run binds Runbook revision N / SHA A
→ authored Runbook advances to N+1 / SHA B
→ current workspace can no longer prove which element IDs existed in N
```

P2B2 must never validate against N+1 merely because it is current. P2B1 therefore seals only the minimum identity/membership facts needed for later reference admission **while N/A is still exactly available**.

This is not a historical Playable archive:

- no Markdown body;
- no heading/title text;
- no Beat prose;
- no Choice/Option labels;
- no consequences;
- no ordering contract for rendering/navigation;
- no source/world/mechanics payload;
- no mutable progress.

The canonical authored structure remains P1 semantic Markdown. The P2B1 manifest owns only the statement:

> these exact stable Playable element IDs, with these exact structural memberships, were admissible for this Run's bound Playable version.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Parse the existing P1 marker/membership contract at the server boundary | No; required proof for manifest admission | Internal Play-owned resolver seam | **Include** |
| Seal immutable Run-bound element/membership manifest | Yes | Yes — new Runtime sidecar/API | **Include** |
| GET/reload exact manifest after restart | No; durability clause | Same contract | **Include** |
| Replay seal after Runbook advances | No; idempotency clause | Same contract | **Include** |
| Current Scene / Beat mutation | Yes | Mutable Runtime contract | **Exclude — P2B2** |
| Resolved Beats | Yes | Mutable Runtime contract | **Exclude — P2B2** |
| Choice selections | Yes | Mutable Runtime contract | **Exclude — P2B2** |
| Element notes | Yes | Mutable Runtime contract | **Exclude — P2B2** |
| Auto-create manifest as part of P2A Run creation | Yes; changes P2A commit shape/multi-file behavior | Different creation transaction | **Exclude** |
| Store historical Runbook Markdown/Tiptap JSON | Yes | Historical Playable archive | **Prohibited** |
| Explicit rebase/migration | Yes | Lifecycle transition | **Exclude — P2C** |
| Generic `WorkObjectElementRef` | Yes | Buddy-shared abstraction | **Exclude — hoist review only** |
| DungeonMind contract | Yes | Cross-repo contract | **Prohibited** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path asks whether one Run has one exact immutable admissible-element manifest for its already-bound Playable version, or no manifest is written. |
| Most likely adversarial sequence | Create Run at N/A → Runbook advances to N+1/B before manifest seal → seal request. Required result: 409/no manifest, never parse N+1 as if it were N. |
| Will §7 detect it? | Yes. A real workspace commit advances the Runbook between P2A Run creation and P2B1 seal; the owning route/service test asserts 409 and no sidecar. |
| Easiest owner to under-test | Cross-language grammar parity. A permissive Python regex can accidentally accept a marker/membership shape the P1 TypeScript authority would block. §7 therefore includes canonical/malformed/orphan/duplicate/membership parity fixtures plus the existing P1 TypeScript suites. |
| Fact that forces stop/split | If exact manifest derivation requires storing historical Markdown, modifying P1 Markdown/Save grammar, changing workspace-document schema, adding mutable progress, or creating a generic cross-domain work-object ref, stop. |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 Core invariant;
   - §4.2 Stable element identity;
   - §5 Runbook / Scene / Beat;
   - §6 Choices and branching;
   - §7 Runtime State + §7.1 Runtime invariants;
   - §11 Persistence and revision rules.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - P2 decomposition;
   - P2A review evidence;
   - hoist posture.
3. merged P1 identity/index authorities:
   - `Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md`;
   - `Docs/Plans/HANDOFF-PLAY-playable-structure-index.md`;
   - `Docs/Plans/HANDOFF-PLAY-choice-option-identity.md`;
   - `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`;
   - `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts`.
4. merged P2A authority:
   - `Docs/Plans/HANDOFF-PLAY-durable-run-binding.md`;
   - `apps/live_control_server/services/play_run_registry.py`;
   - `apps/live_control_server/routes/play_runs.py`.
5. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`.
6. `apps/live_control_server/services/workspace_document_registry.py`
   - `WorkspaceDocumentSnapshot`;
   - `get_workspace_document_snapshot_unlocked()`;
   - workspace document mutation lock contract.
7. `apps/live_control_server/services/registry_file_lock.py`.
8. `src/live_play/live_store.py`.
9. PR #578 `play_run_state.py` as mining evidence only.
10. `AGENTS.md`.
11. `Docs/Process/STEWARD-CYCLE.md`.

### Predecessor contracts consumed unchanged

#### P1 semantic identity

Canonical marker envelope remains:

```md
<!-- dmb-playable-element:v1 kind=scene id=scene:<opaque-id> -->
## Scene title

<!-- dmb-playable-element:v1 kind=beat id=beat:<opaque-id> -->
### Beat title

<!-- dmb-playable-element:v1 kind=choice id=choice:<opaque-id> -->
### Which way?

<!-- dmb-playable-element:v1 kind=option id=option:<opaque-id> -->
#### One option
```

Exact P1 ID grammar:

```regex
^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$
```

Exact structural interpretation:

```text
Scene  → starts current Scene; clears active Choice
Beat   → requires current Scene; belongs to it; clears active Choice
Choice → requires current Scene; belongs to it; becomes active Choice
Option → requires current Scene + active Choice; belongs to both
```

All P1 markers are root-level, unique, single-line canonical comments immediately followed by the heading they identify. Heading levels remain H2/H3/H3/H4 respectively.

P2B1 must not change that grammar. It creates a **second Play-owned consumer** of the existing grammar at the server boundary.

#### P2A Run binding

P2A record remains authoritative and unchanged:

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
```

P2B1 does not add fields to `dmb_play_run_record_v1`, does not increment `run_revision`, and does not alter P2A create/list/get semantics.

### Ownership

The P1 semantic Markdown body remains **Playable authority**.

The P2A Run record remains **Run identity/version-binding authority**.

The P2B1 manifest is a **Play Runtime reference-admission sidecar**. It owns only a frozen set of admissible element IDs and membership for one exact Run binding.

It must not become:

- a second Playable document;
- a projection source for titles/prose/order;
- a workspace-document schema extension;
- a generic Canvas element registry;
- World/Source/Mechanics authority;
- mutable Run progress.

### Lane table

| Field | Required content |
|---|---|
| Base revision | `f29132f14e0a29565979c3de95dce6d01976db05` |
| Design anchor | `bc80f7125499817050f08abc79b71b87d327b2a9`, merge of PR #596 |
| Predecessor contract | P1 four-kind marker/index + P2A immutable Run binding |
| Exact input consumed | Existing Run UUID; its persisted artifact/revision/SHA binding; current coherent workspace snapshot only when sealing is not already complete |
| Output | One immutable `PlayRunReferenceManifestV1`, or fail closed with no sidecar |
| Named successor | `P2B2 — durable CAS Run progress against the sealed manifest` |
| What remains false | No current Scene/Beat, resolved Beats, selection, notes, rebase/migration, linked runtime handles, Play UI |
| Branch / isolated checkout | `agent/play-run-reference-manifest` in isolated worktree/equivalent |
| Parallel collision hotspots | `apps/live_control_server/routes/play_runs.py`, active Playable roadmap, `out/runtime/play/**`; PR #578 remains mining evidence only |
| Runtime/state ownership | Tests use temp repo roots only. Production manifest data lives under `out/runtime/play/reference-manifests/`; never touch operator real runtime state in tests. |
| State-authority sync after merge | This handoff completion + living Playable roadmap current sequence. Stable architecture only if evidence changes a claim. |

### Hoist posture at dispatch

P2B1 is the first server/runtime consumer of the P1 marker family, but it is still a **Play-domain** consumer.

Therefore default posture remains:

```text
WorkObjectRevisionRef: not yet justified
WorkObjectElementRef:  not yet justified
DungeonMind contract:  none
```

A generic Buddy ref becomes plausible only when another independent non-Play consumer—such as agent/document mutation—needs the same work-object element addressing invariant.

### Roadmap review is a merge gate

Before final PASS, record exactly one:

```text
ROADMAP_REVIEW — UPDATED
...
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
...
```

Required observation:

```text
P2B1_HOIST_OBSERVATION
- Did server-side marker/reference resolution remain cleanly Play-owned?
- Did another independent Buddy consumer require the same element-ref contract?
- Is WorkObjectRevisionRef justified now? yes/no/not yet
- Is WorkObjectElementRef justified now? yes/no/not yet
- Did a historical Playable archive become necessary? yes/no
- DungeonMind relevance discovered? none / exact future audit question only
```

The roadmap ledger names the implementation/evidence head, not the later bookkeeping SHA.

---

## §3 Observable paths and adversarial sequences

### Canonical API

Reuse the already-mounted P2A router; do not add a new `main.py` route mount.

#### Seal or replay the reference manifest

```http
PUT /api/live/play-runs/{run_id}/reference-manifest
```

No caller-authored structure body is accepted.

The Run binding determines the only admissible source.

#### Read the manifest

```http
GET /api/live/play-runs/{run_id}/reference-manifest
```

GET never creates a manifest.

### Canonical persisted manifest

```text
schema_version: dmb_play_run_reference_manifest_v1
run_id: <canonical Run UUID>
playable_artifact_id: <exact P2A artifact UUID>
playable_revision: <exact P2A revision>
playable_content_sha256: <exact P2A content SHA>
elements:
  - kind: scene | beat | choice | option
    element_id: <canonical P1 element ID>
    scene_id: <canonical Scene ID when Beat/Choice/Option>
    choice_id: <canonical Choice ID only when Option>
sealed_at: <ISO-Z>
```

Canonical element ordering is **lexicographic by `element_id`**, not document order.

That is deliberate. P2B1 is reference-admission evidence, not a rendering/navigation index.

Field rules:

| kind | `scene_id` | `choice_id` |
|---|---|---|
| scene | absent | absent |
| beat | required | absent |
| choice | required | absent |
| option | required | required |

No other keys are admitted.

### Persistence root

```text
out/runtime/play/reference-manifests/{run_id}.json
```

Do **not** place manifest JSON beside P2A Run files under `out/runtime/play/runs/`; P2A list discovery intentionally treats every `*.json` in that directory as a Run record.

### Server-side P1 resolver contract

P2B1 may implement a private Play-owned semantic-Markdown scanner sufficient to derive the manifest. It must remain internal to the manifest capability.

The resolver must:

1. consume the exact `WorkspaceDocumentSnapshot.markdown` body whose revision/SHA equals the Run binding;
2. recognize only the canonical P1 marker envelope/kinds/ID grammar;
3. require immediate marker→ATX-heading adjacency;
4. require exact heading levels:
   - Scene H2;
   - Beat H3;
   - Choice H3;
   - Option H4;
5. require global exact-ID uniqueness;
6. apply the exact P1B/P1C membership rules above;
7. fail closed on malformed/orphan/level-mismatch/duplicate/orphan-membership structure;
8. treat canonical-marker-looking text inside fenced code blocks as literal example text, not semantic structure;
9. reject non-fenced occurrences of the `dmb-playable-element:` prefix that are not a canonical root-level marker rather than silently ignoring a near-marker;
10. derive only element IDs/membership; no title/prose/content extraction.

Do not add a Markdown parser dependency merely to implement this slice. If faithful P1 semantics cannot be implemented with a bounded Play-owned scanner and focused parity evidence, stop and re-brief rather than introducing a new general Markdown authority.

### Seal admission

For a Run without an existing manifest:

1. validate/load the exact P2A Run record;
2. acquire the per-manifest mutation lock;
3. re-check whether the manifest already exists;
4. acquire the existing workspace-document mutation lock for `run.playable_artifact_id`;
5. load one coherent workspace snapshot through the unlocked seam;
6. require:
   - same exact document ID;
   - `kind == runbook`;
   - `status == active`;
   - `content_status == committed`;
   - `file_exists == true`;
   - `loaded_revision == run.playable_revision`;
   - `content_sha256 == run.playable_content_sha256`;
7. derive the exact P1 reference set/membership;
8. atomically persist the manifest **while the workspace mutation lock remains held**;
9. return it.

The workspace lock spans coherent admission through atomic manifest commit for the same reason P2A held it through Run creation: the bound document must not advance between validation and durable evidence creation.

### Replay admission

If the manifest already exists:

1. validate the P2A Run record;
2. validate the persisted manifest;
3. require exact manifest Run/artifact/revision/SHA identity equal to the Run record;
4. return the manifest unchanged;
5. do **not** read current workspace state;
6. do **not** rewrite `sealed_at` or manifest bytes;
7. do **not** mutate the Run or increment `run_revision`.

This permits:

```text
seal at Runbook N
→ Runbook advances to N+1
→ lost HTTP response / restart
→ identical PUT
→ exact N-bound manifest returns unchanged
```

### Observable path table

| Path | Required behavior | Owning boundary |
|---|---|---|
| Seal exact manifest | Persist one exact ID/membership sidecar for Run binding | manifest service + workspace snapshot + P1 resolver |
| Same PUT replay | Return exact existing manifest unchanged; no workspace read | manifest service/store |
| Runbook advances after successful seal | Existing manifest remains exact and replayable | manifest store |
| Runbook advances before first seal | 409; no manifest; never parse current N+1 as bound N | workspace admission |
| Unknown Run | 404; no manifest | P2A Run authority |
| Invalid Run UUID | 422 | P2A identity validation / route |
| GET missing manifest for existing Run | 404; no implicit creation | manifest authority |
| Malformed persisted Run | 500 | P2A Run authority |
| Malformed persisted manifest | 500; never reset/rebuild silently | manifest store |
| Persisted manifest identity differs from Run | 500; fail closed | manifest store + Run binding |
| Canonical Scene/Beat/Choice/Option structure | exact IDs/membership, no labels/prose | P1 resolver |
| Malformed/orphan/duplicate marker | reject; no manifest | P1 resolver |
| Orphan Beat/Choice/Option membership | reject; no manifest | P1 resolver |
| Marker example inside fenced code | ignored as literal code | P1 resolver |
| Existing P2A Run record | bytes/revision/timestamps unchanged | Run authority regression |
| Existing Runbook | bytes/revision/SHA unchanged | workspace authority regression |

### Adversarial sequences

| Sequence | Required safe outcome | §7 proof |
|---|---|---|
| Run at N/A → workspace commits N+1/B → first seal | 409; no manifest | stale-bound-version test |
| Seal begins on N/A → concurrent Runbook mutation attempts N+1 | mutation blocks until manifest write commits; manifest names N/A | interleaving test |
| Seal commits → response lost → Runbook advances → retry | exact persisted manifest; no workspace read/rewrite | replay-after-advance test |
| Manifest file exists with another `run_id` or binding | 500; never adopt/overwrite | identity-integrity test |
| Duplicate element ID in bound Markdown | fail closed; no sidecar | parser integrity test |
| Option appears before active Choice | fail closed; no sidecar | membership test |
| `dmb-playable-element:` typo outside code fence | fail closed; no silent omission | near-marker test |
| canonical marker text inside fenced code | ignored; does not become a reference | code-fence test |

---

## §4 Files in scope — write lease

Expected implementation paths:

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md` | Pin exact dispatch base/status and later review evidence only |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Mandatory P2B1 review-ledger disposition only; current sequence is synchronized before dispatch |
| Create | `apps/live_control_server/services/play_run_reference_manifest.py` | P1 marker/membership resolution, strict manifest model/store, exact seal/replay logic |
| Modify | `apps/live_control_server/routes/play_runs.py` | Add PUT/GET manifest subroutes to the already-mounted P2A router |
| Create | `tests/test_play_run_reference_manifest.py` | Owning parser/store/service/persistence/interleaving proof |
| Create | `tests/test_live_play_run_reference_manifest.py` | HTTP contract and real app-mount proof |

### Bounded discovery exception

```text
Directory:
  tests/

Maximum additional paths:
  1

Allowed path kinds:
  focused immutable fixture/helper used only by the P2B1 parser parity or concurrency proof

Decision rule:
  required solely to prove the same Run-bound reference-manifest invariant;
  no production owner, UI, schema, or new workflow.
```

A required production path outside the explicit lease is a stop report.

### Deliberate non-lease

P2B1 may read but must not modify:

```text
apps/live_control_server/services/play_run_registry.py
apps/live_control_server/main.py
apps/live_control_server/services/workspace_document_registry.py
apps/live_control_server/services/registry_file_lock.py
src/live_play/live_store.py
apps/live-control-ui/src/**
apps/live_control_server/services/combat_state.py
src/graph_memory/**
```

If P2B1 requires changing P2A Run schema/create semantics, P1 Markdown/TipTap grammar, workspace-document schema/writer, generic locks/writer, UI, or Graph/Combat authority, stop and re-brief.

---

## §5 Explicitly out of scope / collision boundary

| Concern | Why excluded |
|---|---|
| `current_scene_id` / `current_beat_id` | P2B2 mutable progress |
| `resolved_beat_ids` | P2B2 mutable progress |
| `selections` | P2B2 mutable progress |
| `notes_by_element_id` | P2B2 mutable progress |
| `run_revision` mutation/CAS endpoint | P2B2 |
| automatic “next Beat/Scene” navigation | Projection/product behavior; manifest intentionally discards order |
| historical Runbook Markdown/Tiptap storage | P2C explicitly forbids inventing historical Playable archive in Runtime |
| auto-seal during P2A Run creation | Would change P2A commit point into multi-file creation behavior |
| manifest repair from current/newer Runbook | Silent retarget; violates exact binding |
| Playable rebase/migration | P2C |
| Play UI / Beats panel / client API wrappers | P3/product consumer later |
| `linkedRuntimeHandles` | Defer until real Combat/runtime consumer |
| Combat fields | Combat-owned |
| consequences / transition semantics | Authored Playable; not reference admission |
| World/Source/Mechanics data | External authorities; manifest stores none |
| generic `WorkObjectElementRef` | No independent non-Play consumer yet |
| DungeonMind/DungeonMindDnD | No kernel/profile contract |
| PR #578 runtime schema | Mining evidence only; adventure enums/defaults remain rejected |

---

## §6 Implementation contract

### Public service contract

```text
Input:
  run_id: canonical P2A Run UUID

Source authority when no manifest exists:
  persisted P2A Run binding
  + coherent current workspace snapshot that must exactly equal that binding

Output:
  one immutable PlayRunReferenceManifestV1

Invariant:
  same as §1

Failure:
  invalid run UUID                       → 422, no mutation
  unknown Run                            → 404, no mutation
  existing malformed Run                → 500, no mutation
  manifest absent + bound revision gone → 409, no manifest
  workspace integrity failure           → truthful propagated failure, no manifest
  invalid P1 marker/structure            → 409, no manifest
  malformed persisted manifest           → 500, no reset/rebuild
  manifest identity != Run binding       → 500, no overwrite
```

### Suggested models

Names may adapt to repository conventions; semantics may not drift.

```python
class PlayRunReferenceElement(BaseModel):
    kind: Literal["scene", "beat", "choice", "option"]
    element_id: str
    scene_id: str | None = None
    choice_id: str | None = None


class PlayRunReferenceManifest(BaseModel):
    schema_version: Literal["dmb_play_run_reference_manifest_v1"]
    run_id: str
    playable_artifact_id: str
    playable_revision: int
    playable_content_sha256: str
    elements: list[PlayRunReferenceElement]
    sealed_at: str
```

`elements` is strict, duplicate-free, and sorted lexicographically by `element_id` before persistence.

The model must enforce the kind/membership matrix rather than trusting the parser alone.

### Identity matrix

| Situation | Required rule | Ambiguity | Fallback |
|---|---|---|---|
| Run | Exact canonical P2A UUID | invalid/unknown → 422/404 | No semantic run slug |
| Manifest file | Filename Run UUID must equal body `run_id` | mismatch → 500 | No body/filename winner |
| Playable artifact/version | Exact equality with P2A Run binding | mismatch → 500 for persisted manifest; 409 when current workspace cannot supply bound version | No latest/current substitution |
| Scene/Beat/Choice/Option ID | Exact canonical P1 complete ID | invalid/duplicate → block | No label/title/position |
| Beat membership | Exact nearest preceding marked Scene in bound Markdown | orphan → block | No inferred Scene from name/order |
| Choice membership | Exact nearest preceding marked Scene | orphan → block | No |
| Option membership | Exact active marked Choice + its Scene | orphan → block | No |
| Rename after manifest seal | No effect on manifest identity | n/a | Titles are not stored |

### Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| Seal | `out/runtime/play/reference-manifests/{run_id}.json` | exact strict model | existing exact manifest returned byte/semantic unchanged | v1 only | no product delete |
| GET | validated sidecar + P2A binding cross-check | exact | repeatable | absent → 404; malformed → 500 | n/a |
| Runbook advances after seal | sidecar unchanged | exact N-bound refs survive | replay reads sidecar, not workspace | P2C owns future rebase | no auto-retarget |
| Runbook advances before seal | no durable sidecar | n/a | retry remains 409 until an explicit future lifecycle action | P2C / new Run decision | no current-version fallback |

### State/fallback matrix

| Path | Initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Replay |
|---|---|---|---|---|---|---|---|
| PUT manifest | lock + exact snapshot only if absent | persist/return exact manifest | unknown Run → 404 | workspace failure propagated | parser/store failure closed | current workspace != bound version → 409 | existing manifest returned without workspace read |
| GET manifest | read Run + sidecar | exact manifest | manifest absent → 404 | n/a | malformed/mismatch → 500 | Runbook current state irrelevant | repeat exact |

No fallback source exists.

### Parser trust boundary

The server resolver verifies only:

- canonical P1 marker spelling/version/kind/ID;
- root-level near-marker rejection outside fenced code;
- immediate marker/ATX-heading adjacency;
- heading-level mapping;
- exact ID uniqueness;
- Scene/Beat/Choice/Option membership.

It does **not** verify or record:

- heading title text;
- Beat kind/content;
- consequences;
- transition meaning;
- whether the GM made a wise Playable design;
- World/Source/Mechanics truth.

### Commit point

The commit point is the atomic replace of the new manifest JSON file while the exact bound workspace-document lock is still held.

Before commit:

- the Run exists;
- no durable P2B1 reference authority exists.

After commit:

- the exact reference set/membership is durable even if the Runbook immediately advances;
- response loss is handled by replaying the same PUT against the sidecar;
- Run record and Runbook remain unchanged.

P2B1 has no multi-file transaction.

### Replay / idempotency

```text
manifest absent + exact bound workspace still available:
  derive + persist once

manifest exists:
  validate against Run binding
  return unchanged before workspace read

manifest absent + current workspace no longer equals Run binding:
  409; no derivation from current bytes

malformed/mismatched existing manifest:
  500; never overwrite or reconstruct automatically
```

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Required proof | Merge blocker |
|---|---|---|---|---|
| Exact Run binding is copied, never caller-authored | service | contract | create P2A Run then seal; response identity exactly equals Run | route accepts artifact/revision/SHA body |
| Canonical four-kind parse | resolver | parity | Scene/Beat/Choice/Option fixture with exact IDs/membership | labels/order used as identity |
| Malformed/orphan/level mismatch blocks | resolver | adversarial | fixture matrix | permissive omission/repair |
| Duplicate ID blocks | resolver | integrity | duplicate fixture | first/latest winner |
| Beat/Choice/Option membership matches P1 | resolver | contract | mixed Scene/Beat/Choice/Option fixture | orphan silently attached |
| Fenced marker example is literal | resolver | regression | code-fence fixture | fake semantic ref admitted |
| Near-marker outside fence blocks | resolver | integrity | typo/blockquoted/indented marker fixture as applicable to P1 root-only contract | silent ignore |
| Existing P1 TS contract still green | P1 predecessor | regression | existing Playable identity/index Vitest suites | Python behavior relies on changed/failed predecessor |
| Exact first seal persists | service/store | integration | real temp workspace Runbook → P2A Run → PUT manifest → sidecar | in-memory-only success |
| Workspace lock spans derivation through write | service + workspace mutation lock | concurrency | block manifest write; concurrent Runbook metadata/content mutation cannot finish until release | snapshot N validated then sidecar written after N+1 |
| Runbook advance before first seal refuses | service/route | adversarial | P2A Run at N → commit N+1 → PUT → 409/no sidecar | current version substituted |
| Replay after Runbook advance | service/route | idempotency | seal N → advance N+1 → same PUT → exact unchanged sidecar, no snapshot lookup | replay blocked or rewritten |
| Manifest identity mismatch fails closed | store | integrity | filename/body or artifact/revision/SHA mismatch → 500 | reset/overwrite |
| Corrupt manifest fails closed | store/route | integrity | invalid JSON/schema → 500 | auto-rebuild |
| GET absent does not create | route | API | existing Run/no manifest → 404 and no file | implicit setup on GET |
| Run bytes unchanged | cross-authority | regression | before/after P2A Run file exact bytes | `run_revision`/timestamp mutation |
| Runbook bytes/revision unchanged | cross-authority | regression | before/after workspace snapshot | P2B1 writes Playable |
| Real app route mounted through existing router | FastAPI app | integration | `TestClient(create_app())` PUT/GET | service-only dead API |
| No prose/order leaks into sidecar | persisted schema | regression | inspect JSON keys/values | title/text/order becomes Runtime copy |
| Roadmap reconsidered | process | review | disposition + `P2B1_HOIST_OBSERVATION` | stale hoist/sequence claim |

### Exact verification commands

From repository root, adapt only to repository-standard equivalents:

```bash
uv run pytest -q \
  tests/test_play_run_reference_manifest.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_play_run_registry.py \
  tests/test_live_play_runs.py \
  tests/test_play_run_registry_integrity.py

uv run ruff check \
  apps/live_control_server/services/play_run_reference_manifest.py \
  apps/live_control_server/routes/play_runs.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_live_play_run_reference_manifest.py

cd apps/live-control-ui
pnpm exec vitest run \
  src/tiptap/playable/playableStructureIndex.test.ts \
  src/tiptap/playable/playableChoiceOptionIdentity.test.ts
cd ../..

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-run-reference-manifest.md \
  --pr <PR_NUMBER>

git diff --check
git diff --name-only <BASE_SHA>...HEAD
```

If the exact existing P1 test filenames differ at dispatch, use the nearest owning P1 identity/index suites and record the substitution. Do not modify UI code/tests merely to make this backend slice easier.

### Required first-seal scenario

```text
1. create a temp Runbook workspace record;
2. commit canonical P1 Scene/Beat/Choice/Option Markdown through existing workspace authority;
3. create a P2A Run bound to that exact revision/SHA;
4. PUT /reference-manifest;
5. verify one sidecar exists under out/runtime/play/reference-manifests/;
6. verify exact Run binding copied from the Run record;
7. verify only IDs/membership + seal metadata persisted;
8. construct a fresh read context and GET the exact manifest;
9. verify P2A Run bytes and Runbook snapshot are unchanged.
```

### Required stale-version scenario

```text
1. create Runbook revision N / SHA A with known element set;
2. create P2A Run bound to N/A;
3. advance the Runbook to N+1 / SHA B, adding/removing/changing markers;
4. first PUT /reference-manifest;
5. expect 409;
6. assert no sidecar exists;
7. specifically assert no N+1-only element can enter a manifest for the N-bound Run.
```

### Required replay-after-advance scenario

```text
1. create Run at N/A;
2. seal manifest from N/A;
3. capture sidecar bytes;
4. advance Runbook to N+1/B;
5. replay PUT /reference-manifest;
6. expect exact original response/bytes/sealed_at;
7. prove current workspace snapshot was not required for replay.
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
P2B2 — durable CAS Run progress against the sealed manifest
```

13. exactly one roadmap disposition;
14. exact roadmap ledger row using implementation/evidence head;
15. `P2B1_HOIST_OBSERVATION`.

---

## §9 Acceptance rubric

- [ ] Post-#596 mutable-state sync landed before dispatch.
- [ ] Exact implementation base pinned after that sync.
- [ ] P2A remains the Run identity/version-binding authority unchanged.
- [ ] Manifest is a separate Runtime sidecar outside authored workspace storage and outside the P2A Run directory.
- [ ] Seal request accepts only Run UUID; caller cannot submit element IDs/index/body.
- [ ] First seal requires current coherent workspace snapshot to exactly equal the Run's bound artifact/revision/SHA.
- [ ] Workspace mutation is serialized through manifest atomic commit.
- [ ] Existing exact manifest replay does not consult current workspace state.
- [ ] Runbook advance before first seal fails 409 without current-version substitution.
- [ ] Runbook advance after successful seal does not rewrite/invalidate the manifest.
- [ ] Canonical Scene/Beat/Choice/Option IDs and membership are derived from the exact P1 v1 marker contract.
- [ ] Malformed/orphan/level-mismatch/duplicate identities fail closed.
- [ ] Orphan Beat/Choice/Option membership fails closed.
- [ ] Fenced code examples do not become semantic references.
- [ ] Manifest stores no heading text, prose, consequences, display labels, World/Source/Mechanics content, or mutable progress.
- [ ] Manifest ordering is canonical by `element_id`, not a rendering/navigation contract.
- [ ] GET missing manifest returns 404 and never creates one.
- [ ] Malformed/mismatched persisted manifest fails 500 without auto-repair.
- [ ] P2A Run bytes, `run_revision`, timestamps, and binding remain unchanged.
- [ ] Runbook bytes/revision/SHA remain unchanged.
- [ ] No `main.py` change; subroutes use the existing P2A router.
- [ ] No UI/API client work.
- [ ] No generic `WorkObjectElementRef` or DungeonMind contract.
- [ ] Actual changed paths stay inside §4/bounded discovery.
- [ ] Focused tests, P1 predecessor tests, ruff, preflight, diff check, and name-only gate pass or baseline differences are truthfully recorded.
- [ ] Roadmap review + P2B1 hoist observation are explicit.
- [ ] P2B2 progress remains unimplemented/unclaimed.

---

## Stop conditions

Stop and report instead of expanding if any of these appears:

- post-#596 current-sequence authorities are not synchronized before dispatch;
- current `main` materially changes P2A Run identity/version fields or replay semantics;
- P1 marker/version/kind/ID/membership grammar changed from the design anchor;
- exact P1 parity requires modifying UI Markdown/TipTap authority;
- faithful server resolution requires a new general-purpose Markdown dependency/authority rather than a bounded Play-owned scanner;
- the bound Runbook revision must be historically reconstructed from bytes no longer available;
- implementation starts storing titles/prose/order/consequences to make future UI easier;
- P2B1 appears to need current/resolved/selection/note mutation;
- P2A Run record/schema/create commit point must change;
- workspace-document schema/writer must change;
- a generic work-object ref abstraction becomes necessary rather than merely attractive;
- a required production path falls outside §4;
- another active merge lane owns `apps/live_control_server/routes/play_runs.py` or the active Playable roadmap;
- production tests would touch operator real `out/runtime/play/` state;
- implementation evidence contradicts the architecture's Playable/Runtime separation.

Report:

```text
Stop condition:
Invariant clause affected:
Why P2B1 cannot absorb it:
Required evidence now missing:
Affected paths/ownership:
Proposed successor or re-brief:
Roadmap claim affected:
State-authority update needed:
```
