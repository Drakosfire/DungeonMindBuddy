---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P3A
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md
  - Branch / PR: agent/play-native-runbook-table-deck / `PLAY: project native Runbook table deck`

  ## Verification pointer
  - Design anchor: merged PR #603 / current main at `bc442717addb264073a68f7528929ec1aac51b2a`
  - Required predecessor before dispatch: merged P2C Run rebase + post-merge state-authority sync naming P3A next
  - Base/head: <PIN_AFTER_P2C_STATE_SYNC> / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — project one durable Runbook as a native Play table deck

**Created:** 2026-08-16  
**Status:** DESIGNED — **DO NOT DISPATCH** until P2C is implemented, merged, and atomically synchronized as complete with P3A named next; then pin the exact implementation base.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P3A`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #603 / `bc442717addb264073a68f7528929ec1aac51b2a`  
**Required predecessor:** P2C — explicit preserve-only Run rebase to newer Playable revision  
**Implementation base:** `PIN_AFTER_P2C_STATE_SYNC`  
**Suggested branch:** `agent/play-native-runbook-table-deck`  
**PR title:** `PLAY: project native Runbook table deck`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — P2C must be product truth first

At this design anchor, repository truth is:

```text
main: bc442717addb264073a68f7528929ec1aac51b2a
PR #603: merged state-authority sync
P2A: merged
P2B1: merged
P2B2: merged
P2C: designed and checked in, not yet implemented
P3: named successor only
```

The living roadmap correctly says P2C is the current next slice and P3 native Play projections is the named successor. This handoff may be designed now because its design branch creates only this new handoff path. CODE may not dispatch from it yet.

Before P3A CODE dispatch, one completed P2C cycle must exist:

1. P2C implementation merged from `HANDOFF-PLAY-run-rebase.md`;
2. the exact P2C review-cycle count and implementation/evidence head are known;
3. a guarded post-P2C state-authority sync marks P2C merged/historical;
4. `ROADMAP-playable-hoist-dungeonmind-kernel.md` names P3A as the current next slice and this handoff as the next handoff;
5. this handoff is present on `main`;
6. every `PIN_AFTER_P2C_STATE_SYNC` is replaced on the implementation branch with that exact synchronized `main` SHA;
7. the implementation agent re-reads the merged P2C Run/manifest lifecycle contracts before editing UI code.

If P2C changes the steady-state Run schema, pending-intent status behavior, Run GET/list behavior, manifest binding semantics, or `run_revision` CAS contract materially, stop and re-brief P3A rather than carrying this design forward by assumption.

---

## §1 Mission and merge-ready invariant

**Mission:** A GM can open one explicit durable Run in a native `/play` surface, see its authored Runbook as a Scene/Beat/Choice table deck, and update the existing P2 Runtime progress without campaign-specific hard-coded adventure data.

**Merge-ready invariant:**

> **Play renders and mutates one Run only from a proven coherent authority set: the exact persisted Run, its exact sealed reference manifest, and a committed workspace Runbook snapshot whose document ID, revision, and content SHA exactly equal that Run binding. Scene/Beat/Choice/Option identity and order come from the existing P1 Playable grammar; authored body content comes from that exact Runbook snapshot; mutable current/resolved/selection/note state comes only from the P2 Run record under the sole `run_revision` CAS token. If the current workspace snapshot no longer equals the Run binding, if the manifest is missing/malformed/mismatched, if client P1 structure disagrees with the sealed manifest, or if P2C reports a recovery-pending Run, Play blocks rather than projecting latest content against stale Runtime, rebuilding authority, auto-rebasing, silently merging conflicts, or falling back to #578 campaign bridges.**

### Why this is P3A

The architecture says P3 replaces #578 campaign bridges with native projections over real authorities. #578 proved the interaction shape, but its Play path is intentionally not mergeable product authority:

```text
ofConksHempholmBeats
+ dmb_play_run_state_v1
+ hard-coded branch enums
+ local Of Conks graph bridges
        ↓
P3 native projection
```

P1 and P2 have now established the durable inputs that dogfood lacked:

```text
P1A/P1B/P1C
stable Scene / Beat / Choice / Option identity + structure

P2A/P2B1/P2B2/P2C
exact Run binding + sealed reference admission + CAS progress + explicit rebase
```

The first native projection should consume those authorities directly before P3 attempts richer World/Source/Mechanics composition.

### Why P2C must precede P3A

DungeonBuddy intentionally does **not** archive historical Runbook Markdown inside Runtime.

Therefore a freshly opened native Play surface can render authored Runbook content only when the available committed workspace snapshot is exactly the revision/SHA to which the Run is bound.

This creates the safe product rule:

```text
Run binding == current committed Runbook snapshot
  → native projection may render

Run binding != current committed Runbook snapshot
  → native projection blocks: rebase required
  → never show latest Runbook prose under old Run progress
```

P2C is the explicit lifecycle operation that can move a stale Run to the newer exact committed revision while preserving only surviving references. Without P2C, P3A would be forced either to lie about revision identity or invent a historical Playable archive, both prohibited.

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Add native `/play` product route and Run chooser | No; entry to same table-deck capability | Surface route only | **Include** |
| Load explicit P2 Run + manifest + exact bound current Runbook snapshot | No; projection admission | Existing APIs | **Include** |
| Reuse P1 Markdown import + structure index | No; identity/order prerequisite | Existing Play-owned contracts | **Include** |
| Verify client structure against sealed P2B1 manifest | No; cross-consumer integrity clause | No new authority | **Include** |
| Render Scene rail + Beat strip + exact authored body slices | Yes | Reconstructable UI projection | **Include** |
| Show authored Choice/Option labels and current selection | No; same Runbook projection | Existing P1/P2 fields | **Include** |
| Mutate current Scene/Beat, resolved Beats, Choice selection, notes | Yes | Reuses existing P2B2 full-progress PUT | **Include** |
| Automatic branch transition/consequence execution | Yes | New semantics not yet authored as executable contract | **Exclude** |
| P2C rebase UI/action | Yes | Separate lifecycle workflow | **Exclude** |
| Generic NPC/location/item Play Object Sheet | Yes | Multi-authority projection | **Exclude — P3B** |
| Graph-reference opening from Play | Yes | Shared Projection-host integration | **Exclude — P3B** |
| Threat exact-mechanics projection | Yes | Mechanics projection | **Exclude — later P3 / P4 boundary** |
| Add to Combat | Yes | Combat mutation | **Exclude — P4** |
| Source Advanced/detail panel | Yes | Cross-authority detail workflow | **Exclude — P3B** |
| Agent proposal/adoption | Yes | Shared mutation workflow | **Exclude — P5** |
| Generic `WorkObjectElementRef` / `WorkObjectRevisionRef` | Yes | Buddy-shared abstraction | **Exclude — hoist review only** |
| DungeonMind contract | Yes | Cross-repository authority | **Prohibited** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Route selection, projection admission, rendering, and progress mutation all operate on one exact Run-bound authority set. |
| Most likely adversarial sequence | Open Run N bound to Runbook rev R → author commits Runbook R+1 elsewhere → user refreshes/reopens Play → UI fetches latest R+1 → unsafe implementation overlays N's old Runtime onto R+1 prose. Required: block as rebase-required before rendering authored content. |
| Will §7 detect that failure? | Yes. One test starts from a Run bound to R, returns workspace snapshot R+1, and proves no projection body/mutation controls are produced and no fallback fetch/rewrite occurs. |
| Easiest owning boundary to under-test | Client/server identity parity. P1 client index and P2B1 server scanner are separate Play-owned consumers of the marker grammar; §7 requires exact manifest/index parity before the projection becomes ready. |
| Fact that forces stop/split | Need for historical Runbook retrieval, new Playable grammar, executable transition semantics, new backend projection authority, graph/object-sheet composition, rebase UI, or a generic shared work-object ref. |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §2 Core invariant;
   - §4 Durable Playable Material;
   - §5 Runbook / Scene / Beat;
   - §6 Choices and branching;
   - §7 Runtime State;
   - §8 Projection architecture;
   - §11 Persistence and revision rules;
   - §12 Surface Interaction Layer boundary;
   - §13 Migration from PR #578.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - promotion test;
   - P1/P2 evidence ledger;
   - current sequence after P2C state sync at dispatch time;
   - P3 / P4 / P5 boundaries;
   - hoist posture.
3. merged P1 contracts:
   - `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`;
   - `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts`;
   - `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`;
   - `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx`;
   - P1A/P1B/P1C tests and handoffs.
4. merged P2 contracts after P2C:
   - `apps/live_control_server/routes/play_runs.py`;
   - `apps/live_control_server/services/play_run_registry.py`;
   - `apps/live_control_server/services/play_run_reference_manifest.py`;
   - `apps/live_control_server/services/play_run_rebase.py` if P2C creates it;
   - P2A/P2B1/P2B2/P2C handoffs and owning tests.
5. workspace authority:
   - `apps/live_control_server/routes/workspace_documents.py`;
   - `apps/live-control-ui/src/api/types.ts` current `WorkspaceDocumentSnapshot`;
   - existing workspace snapshot client function in `liveApi.ts`.
6. Surface Interaction Layer:
   - `apps/live-control-ui/src/surfaceInteraction/projection/ProjectionHost.tsx`;
   - `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`.
7. PR #578 **as dogfood evidence only**, especially:
   - `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`;
   - `apps/live-control-ui/src/playSurface/beats/BeatsPanel.tsx`;
   - `apps/live-control-ui/src/playSurface/beats/ofConksHempholmBeats.ts`;
   - `apps/live-control-ui/src/graphReference/PlayObjectSheetProjection.tsx`;
   - `apps/live-control-ui/src/graphReference/ofConksPlayObjectBridge.ts`.

Do not copy #578's campaign/adventure-specific data contracts into product code. Mine interaction evidence only.

### Current seam observations at design anchor

Current `main` already provides:

```text
shared ProjectionHost
workspace document snapshots with markdown + revision + content_sha256
P1 Markdown → TipTap admission
P1 stable Playable element attrs + structure index
P2 Run GET/list/progress endpoints
P2B1 manifest GET
read-only MarkdownEditorCore via editable=false
```

Current `main` does **not** provide:

```text
/play route
frontend PlayRunRecord / manifest API types
native Runbook table-deck projection
native Scene/Beat Runtime controls
product use of #578's BeatsPanel
historical Runbook revision retrieval
```

PR #578's `BeatsPanel` proves useful Scene/Beat navigation, resolved status, persistent notes, choices, and object chips, but it is built on `OF_CONKS_HEMPHOLM_SPINE`, `OF_CONKS_HEMPHOLM_RUN_ID`, adventure-specific branch enums, and a separate `dmb_play_run_state_v1`. Those are explicitly replacement targets, not predecessor authority.

### Lane table

| Field | Required content |
|---|---|
| Parent authority | Playable architecture + living Playable hoist roadmap |
| Base revision | `PIN_AFTER_P2C_STATE_SYNC` |
| Design anchor | `bc442717addb264073a68f7528929ec1aac51b2a` — merge of PR #603 |
| Predecessor contract | merged P1 identity/index + merged P2 Run/manifest/progress/rebase lifecycle |
| Exact input consumed | explicit Run UUID; P2 Run record; sealed P2B1 manifest; current committed workspace snapshot for that exact Runbook document |
| Output | reconstructable native `/play` Runbook table deck + P2 progress mutations; no new durable UI store |
| Named successor | `P3B — generic Play Object Sheet over World + Source + Playable` |
| What remains false | no graph-object sheet, graph reference open, Threat→Combat, rebase UI, automatic consequence execution, proposal/adoption |
| Branch / isolated checkout | `agent/play-native-runbook-table-deck` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | `App.tsx`, AppChrome nav config, `api/types.ts`, `api/liveApi.ts`, living roadmap, new `playSurface/**`; serialize with any lane touching those paths |
| Runtime/state ownership | no new runtime files; mutations go only through P2 Run progress API; tests mock HTTP or use temp-root server fixtures |
| State-authority sync after merge | add P3A roadmap evidence row; if evidence holds, mark P3A merged and set P3B as next; no stable architecture churn unless evidence contradicts it |

### Hoist posture at dispatch

Default:

```text
Runbook table deck:             Play-owned projection
P1 element identity/index:      Play-owned
P2 Runtime progress:            Play-owned Runtime
ProjectionHost chrome:          already Buddy-shared
WorkObjectElementRef:           not yet justified
WorkObjectRevisionRef:          not yet justified
DungeonMind contract:           none
```

P3A creates another Play-owned consumer of the stable-ID contract. That is evidence worth recording, but it is still not an independent non-Play consumer and therefore does not by itself satisfy the roadmap promotion test.

---

## §3 Observable paths and adversarial sequences

### Canonical product route

Add one native product route:

```text
/play
/play?run=<canonical Run UUID>
```

No router library is introduced in this slice.

`/play` without a `run` query is a chooser over durable Runs returned by the existing P2 list endpoint. It must not auto-open the first, most recent, highest revision, or campaign-name match.

Selecting a Run writes the exact Run UUID into the query string and loads that identity. A directly linked `/play?run=<uuid>` loads the exact named Run without requiring the chooser to succeed first.

### Projection admission pipeline

For an explicit Run UUID:

```text
1. GET exact Run
2. GET exact Run reference manifest
3. GET current workspace snapshot for run.playable_artifact_id
4. prove:
     snapshot.record.document_id == run.playable_artifact_id
     snapshot.record.kind == runbook
     snapshot.record.status == active
     snapshot.record.content_status == committed
     snapshot.file_exists == true
     snapshot.loaded_revision == run.playable_revision
     snapshot.content_sha256 == run.playable_content_sha256
     manifest.run_id == run.run_id
     manifest artifact/revision/SHA == Run binding
5. parse snapshot.markdown through existing markdownToTiptapDoc()
6. require existing blocking-import diagnostics to be clear
7. derive existing indexPlayableStructure()
8. prove exact index ↔ sealed-manifest identity/membership parity
9. derive reconstructable table-deck projection slices
10. render Runtime overlay from the exact Run record
```

No latest/current workspace fallback is permitted after any mismatch.

### Manifest/index parity

P3A is the first UI path that simultaneously has:

- the client P1 structure index derived from exact Runbook bytes; and
- the server-sealed P2B1 manifest derived from the exact same revision.

Before rendering interactive Play, require exact parity:

```text
same element ID set
same kind for each ID
same scene membership for Beat / Choice / Option
same choice membership for Option
```

Ordering comes from the P1 client index because the P2B1 manifest intentionally does not persist rendering order.

A mismatch is an integrity-blocked projection. Do not prefer one parser, rewrite the manifest, or continue with partial controls.

### Reconstructable projection model

Create one pure Play-owned projection function over the admitted TipTap document and existing structure index.

Required conceptual result:

```text
NativeRunbookProjection
  sceneOrder[]
  scenes[]
    sceneId
    title
    bodyDoc          # exact TipTap nodes belonging to Scene preamble only
    beatIds[]
    choiceIds[]
  beats[]
    beatId
    sceneId
    title
    bodyDoc          # exact TipTap nodes until next root playable marker
  choices[]
    choiceId
    sceneId
    title
    bodyDoc
    optionIds[]
  options[]
    optionId
    choiceId
    sceneId
    title
    bodyDoc
```

`bodyDoc` is a reconstructable read-only TipTap document fragment. It is not persisted.

Range rules:

```text
Scene body:
  nodes after marked Scene heading until first following root-level playable marker

Beat body:
  nodes after marked Beat heading until next root-level playable marker

Choice body:
  nodes after marked Choice heading until first Option or next root-level Beat/Choice/Scene

Option body:
  nodes after marked Option heading until next root-level playable marker
```

Heading display text is presentation only. Stable IDs remain the attrs/manifest IDs.

Do not invent Beat `kind`, `intent`, `atTable`, `rulesNow`, `ifTheyWait`, `ifTheySucceed`, `ifTheyFail`, or treasure fields from prose. Existing authored callouts/tables/references render as their existing TipTap nodes through `MarkdownEditorCore editable={false}`.

### Table-deck interaction

The native surface must provide at least:

```text
Run header
Scene rail/deck
current Scene body
Beat strip for current Scene
selected/current Beat body
scene Choices with Options
resolved Beat status
scratch note editor for current Scene/Beat
```

Runtime overlay rules:

- `current_scene_id` marks the authoritative current Scene.
- `current_beat_id` marks the authoritative current Beat.
- `resolved_beat_ids` marks resolved Beat chips/checks.
- `selections[choice_id]` marks the selected Option.
- `notes_by_element_id` provides exact scratch text.

If `current_scene_id` is null, the UI may show the first Scene as a **preview only** but must not write Runtime until the operator explicitly sets a current Scene.

If `current_beat_id` is null, do not invent one. The Beat strip remains available.

### Progress mutation contract

P3A does not create a new mutation API. Every change is one P2B2 full-progress replacement:

```http
PUT /api/live/play-runs/{run_id}/progress
```

with:

```json
{
  "expected_run_revision": "<current authoritative token>",
  "progress": {
    "current_scene_id": "... or null",
    "current_beat_id": "... or null",
    "resolved_beat_ids": [],
    "selections": {},
    "notes_by_element_id": {}
  }
}
```

UI mutations:

| Operator action | Full replacement rule |
|---|---|
| Set current Scene | set scene; clear current Beat if it belongs to a different Scene; preserve resolved/selections/notes |
| Set current Beat | set both its owning Scene and Beat; preserve other progress |
| Toggle resolved Beat | add/remove exact Beat ID; preserve all other fields |
| Select Choice Option | replace only that Choice key with exact Option ID; preserve all other fields |
| Save Scene/Beat note | replace exact note key with exact entered text; empty string is still exact text unless UI explicitly offers delete |

Use one authoritative Run response at a time. Do not allow two simultaneous local progress PUTs from the same component to race with the same `expected_run_revision`.

A simple allowed implementation is:

```text
one in-flight mutation
→ disable authoritative mutation controls
→ success response becomes the next authoritative Run/token
→ re-enable
```

Do not build an optimistic merge engine in P3A.

Notes may keep an unsaved local text draft while a mutation is pending, but UI must distinguish unsaved draft from persisted Run authority.

### Conflict / recovery behavior

- P2B2 `409` stale CAS: do not retry with a guessed/new token and do not merge local progress. Reload the Run; show that Runtime changed; require a new explicit operator action.
- transport/unknown-response failure: retain the exact request as retryable UI state. Retrying that exact request may use P2B2 response-loss semantics. Do not rewrite `expected_run_revision` unless a fresh authoritative Run was loaded.
- P2C recovery-pending `503`: show migration recovery pending; freeze mutation controls; no workspace fallback.
- persisted Run/manifest integrity `500`: show integrity-blocked; no partial deck.
- workspace revision/SHA mismatch: show **Rebase required**; do not render authored Runbook body from the newer snapshot.

### Observable path table

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| App primary nav | no Play route on current main | Play appears as native product surface | Yes | App/AppChrome |
| `/play` no Run selected | no product path | explicit durable Run chooser; no first/latest auto-select | Yes | PlaySurfacePage |
| `/play?run=<uuid>` exact coherent pair | no native projection | native Scene/Beat/Choice deck from exact bound Runbook + P2 Runtime | Yes | admission + projection + component |
| Run unknown | n/a | stable not-found surface; no fallback Run | Yes | API/UI |
| Run/manifest pending P2C recovery | n/a | recovery-pending surface; no authored body/mutation | Yes | API/UI |
| Manifest missing/malformed/mismatched | no native projection | integrity-blocked; no auto-seal/rebuild | Yes | admission |
| Workspace snapshot newer/different | #578 hard-code ignores durable revision | Rebase required; do not render latest under stale Runtime | Yes | admission |
| P1 parse/index blocked | no native projection | integrity-blocked; no heuristic IDs | Yes | projection admission |
| P1 index ≠ sealed manifest | no parity check today | integrity-blocked; no preferred parser/rewrite | Yes | projection admission |
| Set current Scene/Beat | #578 writes separate campaign run-state | P2B2 full replacement CAS | Yes | progress mutation |
| Toggle resolved | #578 overwrites local run-state | P2B2 full replacement CAS | Yes | progress mutation |
| Select Choice Option | #578 adventure branch enums | generic P1 Choice/Option IDs → P2 selection map | Yes | progress mutation |
| Save scratch note | #578 scene_notes in separate schema | exact P2 `notes_by_element_id` text | Yes | progress mutation |
| Stale progress writer | #578 has no CAS | 409 → reload; no silent merge | Yes | progress mutation |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Run bound R → workspace now R+1 → open `/play?run=` | Rebase-required block; no R+1 authored body rendered with R Runtime | admission test |
| exact Run+snapshot but manifest removed | integrity block; no auto-seal | admission test |
| exact Run+snapshot+manifest but client index gives different membership | integrity block; no controls/rewrite | parity test |
| Run projection ready → two rapid mutation clicks | second cannot race same token; one authoritative response establishes next token | component concurrency test |
| progress PUT response lost → operator retries exact request | exact retry is allowed; no local N+2 synthesis | API/component replay test |
| another client advances Runtime N→N+1 → this UI PUTs expected N | 409; UI reloads authoritative N+1; no local overwrite | stale CAS test |
| P2C intent exists → open Play | 503 recovery-pending; no latest workspace fallback | lifecycle test |
| current Scene A/current Beat A1 → set Scene B | request sends Scene B + Beat null, preserving all unrelated progress | mapping test |
| Choice C has options O1/O2 → select O2 | only `selections[C]` changes; no inferred Scene transition | choice test |
| Run has null current Scene | first Scene may be previewed but Run bytes remain unchanged until explicit set-current action | no-hidden-write test |

---

## §4 Files in scope — write lease

Expected implementation paths after the P2C dispatch gate closes:

| Action | Path | Purpose |
|---|---|---|
| Create / Modify | `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md` | pin base/status and record evidence handback |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | P3A evidence ledger / disposition only; current sequence is synchronized before dispatch |
| Modify | `apps/live-control-ui/src/App.tsx` | mount native `/play` route; no new router dependency |
| Modify | `apps/live-control-ui/src/App.test.tsx` | route-level Play regression proof |
| Modify | `apps/live-control-ui/src/chrome/appChromeConfig.ts` | add Play to shared primary nav/labels |
| Modify | `apps/live-control-ui/src/api/types.ts` | exact frontend types for merged P2 Run / manifest contracts only |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | thin existing-endpoint clients: Run list/get, manifest get, progress PUT |
| Create | `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx` | Run chooser + exact admission + native table-deck surface |
| Create | `apps/live-control-ui/src/playSurface/playSurface.css` | Play-owned table-deck presentation only |
| Create | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | pure exact Runbook projection + manifest parity validation |
| Create | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | P1 body-slicing/parity/integrity proof |
| Create | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx` | Scene/Beat/Choice rendering + P2 progress controls |
| Create | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx` | Runtime overlay/CAS/conflict/no-hidden-write component proof |
| Create | `apps/live-control-ui/src/playSurface/runbook/index.ts` | local exports only |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/

Maximum additional paths:
  3

Allowed path kinds:
  existing AppChrome test/config test,
  existing workspace-document API client test,
  existing P1 playable structure regression test

Decision rule:
  allowed only when the changed production seam already exists and proof belongs
  at that existing boundary. No backend production file, #578 campaign bridge,
  graphReference production file, statblock/Combat file, or shared ProjectionHost
  implementation may enter through this exception.
```

A required backend production change is a stop report unless the only issue is adding a missing thin route registration for already-merged P2 endpoints; if that appears, stop and re-brief rather than silently expanding this UI projection slice.

### Deliberate non-lease

Read but do not modify:

```text
apps/live_control_server/**
apps/live-control-ui/src/graphReference/**
apps/live-control-ui/src/statblocks/**
apps/live-control-ui/src/surfaceInteraction/projection/**
apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts
apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts
apps/live-control-ui/src/tiptap/markdown/**
apps/live-control-ui/src/tiptap/extensions/**
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
```

P3A consumes those contracts. It does not repair or widen them.

---

## §5 Explicitly out of scope / collision boundary

| Path / authority | Why P3A must not touch or claim it |
|---|---|
| P2 backend Run/manifest/rebase services | P2C owns lifecycle; P3A is a consumer |
| P1 identity/parser grammar | P3A projects existing grammar; parser change is a separate design |
| `graphReference/**` | P3B owns generic Play Object Sheets/reference opening |
| `statblocks/**` / Combat | later P3/P4 exact mechanics + Add-to-Combat |
| `surfaceInteraction/projection/**` | shared host is already authoritative; P3A main deck does not need new chrome |
| #578 `ofConks*` product imports | dogfood evidence only; hard-coded campaign data is prohibited |
| historical Runbook storage | explicitly outside architecture; P3A blocks stale binding instead |
| executable consequence/transition semantics | no durable authored contract yet |
| P2C rebase button/workflow | separate operator lifecycle UI |
| Source Advanced/detail | P3B multi-authority object projection |
| map/media overlays | asset/annotation successor work |
| agent proposal/adoption | P5 |
| DungeonMind / DungeonMindDnD | no cross-repo contract in P3A |

---

## §6 Implementation contract

```text
Input:
  explicit Run UUID
  merged P2 Run record
  merged P2B1 sealed reference manifest
  current committed workspace snapshot for run.playable_artifact_id
  existing P1 Markdown admission + Playable structure index

Output:
  READY:
    native reconstructable Runbook table-deck projection
    exact P2 Runtime overlay
    P2B2-backed progress controls

  or BLOCKED:
    not found
    recovery pending
    rebase required
    integrity blocked
    transport unavailable

Invariant:
  same §1 invariant

Failure behavior:
  unknown Run -> not found, no fallback Run
  P2C pending 503 -> recovery pending, no workspace fallback
  missing/malformed/mismatched manifest -> integrity blocked
  workspace revision/SHA differs -> rebase required, no authored latest body
  P1 import/index/parity failure -> integrity blocked
  progress 409 -> reload authoritative Run, no automatic merge/retry
  progress 500/503 -> preserve last authoritative view + unsaved note draft separately; no saved claim

Replay / idempotency:
  same exact projection inputs -> deterministic same projection model
  same exact progress PUT retry after response loss -> rely on P2B2 replay contract
  changed workspace snapshot -> never silently replace admitted projection under same Run binding
```

### A. Projection admission state

Use an explicit local discriminated state; names may vary but semantics may not:

```text
idle
run-list-ready
loading-run
ready
not-found
recovery-pending
rebase-required
integrity-blocked
unavailable
```

`ready` requires every §3 admission proof. Rendering the authored Scene/Beat body before admission completes is prohibited.

### B. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Run chooser | loading label | explicit list | empty list | service error | n/a | pending list may 503 after P2C | retry list |
| Exact Run load | loading deck shell only | exact Run | 404 | transport/503 | 500 | n/a | retry exact UUID |
| Manifest load | no deck body yet | exact bound manifest | 404 → integrity blocked | transport/503 | 500/mismatch | n/a | no auto-seal |
| Workspace snapshot | no deck body yet | exact revision/SHA | 404/unavailable | transport | malformed | revision/SHA differs → rebase required | manual reload only |
| P1 projection | no deck body until ready | deterministic deck | n/a | n/a | parser/index/parity block | n/a | same bytes deterministic |
| Progress PUT | disable mutation controls | response becomes authority | n/a | transport/503 | 500 | 409 stale CAS | exact-request retry or fresh reload |

**Fallback:** none. Never use latest Run, first Run, display labels, current workspace bytes with a stale Run binding, dogfood tables, or a rebuilt manifest as fallback authority.

### C. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Run | canonical UUID from URL/chooser | malformed UUID rejected by server/client surface | No |
| Playable artifact | exact `run.playable_artifact_id` workspace document UUID | no title/path lookup | No |
| Playable revision | exact Run revision + SHA | mismatch is rebase-required | No |
| Scene/Beat/Choice/Option | exact P1 stable ID with manifest parity | title/order never identity | No |
| Rename title/prose at same identity in a newer revision | unavailable to old Run on fresh load until rebase | never infer same revision from matching IDs | No |
| Choice selection | exact `choice:* -> option:*` membership | label not identity | No |
| Note target | exact Scene/Beat ID offered by P3A | no label normalization | No |

### D. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| Runbook projection | none; reconstructable in memory | same exact bytes/index produce same projection | deterministic recompute | stale binding blocks; P2C migrates | n/a |
| Current Scene/Beat | P2 Run JSON | server response becomes authority | P2B2 no-op/replay semantics | existing P2 fields | later explicit PUT |
| Resolved Beats | P2 Run JSON canonical list | server canonical ordering retained | full replacement | existing P2 fields | later explicit PUT |
| Choice selections | P2 Run JSON map | exact IDs round-trip | full replacement | existing P2 fields | later explicit PUT |
| Notes | P2 Run JSON exact text | no trim/normalization | full replacement | existing P2 fields | later explicit PUT |

### E. Predecessor → consumer mapping

**Grounding source:** merged P1/P2 schemas and exact workspace snapshot contract at the pinned post-P2C base.

| Predecessor field/outcome | Real shape/optionality | P3A behavior | Transformation | Proof |
|---|---|---|---|---|
| `PlayRunRecord.run_id` | canonical UUID | URL + deck identity | none | route/component test |
| `campaign_id` | string | display/context only | none | component test |
| `playable_artifact_id` | workspace doc UUID | exact snapshot fetch | none | admission test |
| `playable_revision` | int | exact snapshot equality | none | rebase-required test |
| `playable_content_sha256` | lowercase SHA | exact snapshot equality | none | rebase-required test |
| `run_revision` | sole CAS token | expected token for every progress PUT | none | stale/race tests |
| `progress.current_scene_id` | scene/null | active Scene | none | overlay test |
| `progress.current_beat_id` | beat/null | active Beat | none | overlay test |
| `resolved_beat_ids` | canonical list | resolved markers | Set only for local read convenience; server remains authority | overlay/mutation test |
| `selections` | choice→option map | selected Option | none | choice test |
| `notes_by_element_id` | exact text map | note draft source | none | text round-trip test |
| manifest elements | IDs + membership, no order/prose | integrity parity only | compare to P1 index | parity tests |
| workspace snapshot markdown | exact current committed bytes | P1 parse → reconstructable body fragments | existing parser only | projection tests |
| P1 structure index | ordered IDs/membership | deck order/navigation | none | projection tests |
| P2C 503 pending state | HTTP lifecycle signal | recovery-pending UI | no fallback | lifecycle test |

---

## §7 Evidence required to merge

Every material invariant clause requires proof at its owning boundary.

| Guarantee / invariant clause | Owning boundary | Evidence class | Required scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| `/play` is a native product route | App/AppChrome | integration | route + nav test | Play route renders; nav labels correct | hidden/non-native route |
| No automatic Run identity guess | PlaySurfacePage | adversarial | multiple runs, no query | chooser shown, no first/latest GET chosen | implicit selection |
| Exact coherent Run projects | admission + pure projector | contract | exact Run/manifest/snapshot | ready projection with exact IDs/order/body | derived from wrong authority |
| Workspace advancement blocks projection | admission | adversarial | Run bound R, snapshot R+1/SHA2 | `rebase-required`; no authored body/control | latest fallback |
| Missing manifest never auto-seals | admission | adversarial | manifest GET 404 | integrity blocked; no PUT seal | hidden write |
| P1/manifest parity is exact | projector | adversarial | mismatched kind/member/set | integrity block | preferred parser/partial projection |
| P1 body slices preserve authored nodes | pure projector | round-trip | paragraphs/callout/table/reference inside Scene/Beat | exact node JSON preserved in correct slice | prose reinterpretation/loss |
| No invented Beat semantics | pure projector | contract | arbitrary prose headings/body | only title/body/IDs projected | heuristic `kind`/rules/consequences |
| Runtime overlay is P2-only | component | contract | current/resolved/selected/note fixture | exact visual state from Run | local duplicate authority |
| Scene mutation preserves unrelated progress | mutation mapping | contract | set Scene across Beat membership | current Beat cleared only when required; other fields exact | dropped selections/notes |
| Beat mutation sets owning Scene | mutation mapping | contract | choose Beat in Scene B | full progress uses B + Beat; unrelated fields exact | cross-scene invalid state |
| Choice uses stable IDs | component/API | contract | labels renamed, IDs stable | PUT exact choice/option IDs | label identity |
| Notes preserve exact text | component/API | round-trip | whitespace/newlines | exact request/response text | trim/normalize |
| One local mutation cannot race same token | component | concurrency | two rapid actions | second disabled/deferred until first response | two same-token PUTs |
| Stale CAS cannot overwrite | component/API | adversarial | 409 on expected N | reload authoritative Run; no auto-merge | retry with guessed N+1 |
| Response-loss retry stays idempotent | component/API | replay | transport fails after server commit, retry exact request | current state returned, no synthetic second change | rewritten token/payload |
| P2C pending state blocks cleanly | component/API | lifecycle | Run/manifest GET 503 | recovery-pending, no workspace fallback | stale/latest projection |
| Null current Scene causes no hidden write | component | adversarial | Run current_scene=null | preview allowed; no PUT until explicit action | auto-write on mount |
| #578 campaign bridges do not enter product | cumulative diff | scope audit | grep/diff | no `ofConks*`, old run-state schema, branch enums in new Play code | dogfood hard-code |
| P1/P2 predecessor suites remain green | predecessor boundaries | regression | focused existing suites | green | contract break |
| Roadmap ownership still holds | roadmap review | design review | exact implementation evidence | `ROADMAP_REVIEW — ...` + P3A hoist observation | stale sequence/hoist claim |

### Exact verification commands

From repository root unless noted:

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx \
  src/App.test.tsx \
  src/tiptap/playable/playableStructureIndex.test.ts \
  src/tiptap/markdown/markdownToTiptap.test.ts

pnpm run typecheck
pnpm run build

cd ../..
uv run pytest -q \
  tests/test_play_run_progress.py \
  tests/test_live_play_run_progress.py \
  tests/test_play_run_reference_manifest.py \
  tests/test_live_play_run_reference_manifest.py \
  tests/test_live_play_runs.py

# Add the exact merged P2C owning tests here after P2C lands.
# They are mandatory at dispatch because P3A consumes its 503/steady-state lifecycle.

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md \
  --pr <PR_NUMBER>

git diff --check
git diff --name-only <PINNED_BASE>...HEAD
```

If the bounded discovery exception is used, include those test paths in the focused Vitest command.

### Minimal live / dogfood proof

P3A is a visible table surface, so perform one local smoke after automated gates when an operator-safe durable Run is available.

```text
Existing surface:
  native /play

Smallest realistic scenario:
  one committed Runbook with at least two Scenes, two Beats, and one Choice with
  two Options; one sealed P2 Run bound to the exact current revision.

Actions:
  open /play?run=<uuid>
  set Scene B
  set one Beat current
  mark another Beat resolved
  select an Option
  save a whitespace-containing note
  hard refresh

Expected observation:
  authored bodies are the committed Runbook content;
  Scene/Beat/Choice identity survives refresh;
  Runtime overlay persists from P2;
  no Of Conks-specific labels/data appear unless they are actually authored in
  the selected Runbook.

Then commit one newer Runbook revision without rebasing the Run and refresh Play.
Expected:
  Rebase required; latest authored body is not rendered against the old Run.
```

Do not mutate an operator's active real table Run merely to satisfy this smoke; use a disposable/test Run if the only available Run is live.

### Roadmap review gate

Before final PASS, answer:

```text
Did P3A evidence change P3 decomposition, Play-vs-shared ownership,
WorkObjectElementRef/WorkObjectRevisionRef hoist pressure, the P3B successor,
or the P4/P5 boundary?
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

Required observation:

```text
P3A_HOIST_OBSERVATION
- Did native Runbook projection become useful outside Play? yes/no/not yet
- Did P1 client/server identity parity require a generic Buddy element-ref contract? yes/no/not yet
- Did another independent consumer require WorkObjectRevisionRef? yes/no/not yet
- Did P3A require historical Playable storage? yes/no
- Did P3A require new Playable grammar? yes/no
- Did P3A require a backend projection authority? yes/no
- DungeonMind relevance discovered? none / exact future K0 question only
```

Default expected disposition:

```text
Play-owned projection remains correct.
Shared ProjectionHost remains shared infrastructure already in place.
No generic work-object ref hoist yet.
P3B generic Play Object Sheet is next.
```

### Baseline failure handling

No waiver by default. If a required command fails on the pinned base, run the exact same command on base and head, record both results/provenance, prove the head adds no failure, and obtain an explicit operator waiver before PASS.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact implementation/evidence head separately from any later roadmap bookkeeping head;
3. §1 invariant disposition;
4. §7 required vs produced evidence + provenance;
5. exact pinned post-P2C base and merged P2C review-cycle count;
6. nano-commit/fix story;
7. actual changed paths vs §4 and bounded discovery usage;
8. projection admission conclusions: Run/manifest/snapshot/P1 parity;
9. stale-Runbook / Rebase-required conclusion;
10. Runtime mutation/CAS/replay/concurrency conclusions;
11. no-hidden-write conclusion for null current Scene;
12. #578 hard-code exclusion conclusion;
13. roadmap disposition + `P3A_HOIST_OBSERVATION`;
14. whether P3B remains the named successor and P4/P5 remain false;
15. prior finding ledger on re-review.

---

## §9 Acceptance rubric

- [ ] Exactly one native Runbook table-deck capability is delivered.
- [ ] `/play` is a first-class AppChrome product route.
- [ ] Run selection is explicit by durable Run UUID; no first/latest/display-name fallback exists.
- [ ] Ready projection requires an exact persisted Run + exact sealed manifest + exact committed workspace snapshot matching Run revision/SHA.
- [ ] A newer/different workspace snapshot produces Rebase-required and never renders latest authored body under stale Runtime.
- [ ] Missing/malformed/mismatched manifest blocks; P3A never auto-seals/rebuilds it.
- [ ] Existing P1 Markdown admission and structure index are reused without grammar changes.
- [ ] Client P1 element set/kind/membership must exactly match the sealed P2B1 manifest before interactive rendering.
- [ ] Scene/Beat/Choice/Option titles are presentation; stable IDs remain identity.
- [ ] Authored body nodes are rendered read-only without inventing `kind`, `rulesNow`, consequences, transitions, or treasure fields.
- [ ] Runtime current Scene/Beat, resolved Beats, selections, and notes come only from the P2 Run record.
- [ ] Every Runtime mutation uses the sole P2 `run_revision` token and full five-member progress replacement.
- [ ] Scene changes clear an incompatible current Beat but preserve unrelated progress exactly.
- [ ] Choice selection records exact Choice/Option IDs and performs no implicit Scene transition.
- [ ] Notes preserve exact text without trim/normalization.
- [ ] One component cannot race two progress PUTs with the same token.
- [ ] 409 stale CAS never auto-merges or guesses a new token.
- [ ] Exact response-loss retry preserves P2B2 idempotency semantics.
- [ ] P2C recovery-pending 503 produces a blocked surface with no workspace fallback.
- [ ] Null current Scene never causes a mount-time hidden write.
- [ ] No `ofConks*`, `OF_CONKS_*`, `dmb_play_run_state_v1`, or adventure branch enum enters product P3A code.
- [ ] No backend projection store/API is added.
- [ ] No graph Object Sheet, Threat→Combat action, rebase UI, source Advanced panel, map overlay, or proposal/adoption enters scope.
- [ ] Actual paths remain inside §4 / bounded discovery.
- [ ] Typecheck/build + focused P1/P2/P3 tests pass with truthful provenance.
- [ ] Roadmap review disposition is recorded against the implementation/evidence head.
- [ ] P3B remains unimplemented/unclaimed unless evidence forces a re-brief.

---

## Stop conditions

Stop and report instead of expanding when any of these appears:

- P2C is not merged and atomically synchronized before P3A dispatch;
- merged P2C changes Run/manifest steady-state semantics assumed here;
- fresh native projection requires historical Runbook Markdown for an old binding;
- implementation attempts to show current/latest Runbook bytes against a different Run revision/SHA;
- P3A needs to auto-rebase, auto-seal a manifest, or create historical Playable storage;
- current P1 client parser/index cannot faithfully project the exact Runbook without grammar changes;
- client/server identity parity cannot be established from existing P1 index + P2B1 manifest;
- correct table projection requires a new durable Playable semantic schema rather than read-only authored body slices;
- automatic choice transition/consequence execution becomes necessary;
- graph reference opening / Play Object Sheet composition becomes necessary for the invariant;
- exact Threat/Combat behavior becomes necessary;
- a backend production projection authority is required;
- a generic Buddy `WorkObjectElementRef` / `WorkObjectRevisionRef` becomes necessary rather than merely convenient;
- another active lane owns one of the §4 files;
- a required production path falls outside §4;
- typecheck/build or owning-boundary proof cannot be produced;
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
