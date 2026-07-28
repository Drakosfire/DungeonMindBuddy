# HANDOFF — SBW06c Workbench Revise UX: Exact Working Copy, Stable Replay, Inspectable Proposal History

**Created:** 2026-07-27
**Status:** MERGED `#439` / `ff553bd81fc82e65d92ddbd1d05af5fc03f1adc7` (2026-07-28)
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw06c-workbench-revise-ux.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Workstream:** Threat + Statblock Authoring and Projection
**Slice:** `SBW06c`
**Suggested branch:** `feat/sbw06c-workbench-revise`
**Dispatch base / `#435` merge SHA:** `32eb1571f67b64c3b8c8ebd4d9fa9e6059eece05`
**Merge SHA:** `ff553bd81fc82e65d92ddbd1d05af5fc03f1adc7`
**Normative contract:** `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md` §12
**Immediate predecessor:** `SBW06b` — PR `#435`
**Post-merge sequencing authority:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md) — run `R0-A` / `R0-B` before re-anchoring `SBW06d`; `SBW08` is no longer an independent parallel lane ahead of `MAGIC-D2`
**Existing PR:** `#439` (merged)

> This slice turns the proven SBW06b backend into a dogfoodable operator loop. A GM submits the exact current editor working copy with explicit instructions, recovers the same operation after timeout or reload, and receives a new proposal without replacing the source candidate or saved mechanics.

### Review-fix ledger (PR `#439`, post-rebase)

| Finding | Status | Owning fix |
| ------- | ------ | ---------- |
| Storage write swallowed → POST without replay authority | Closed | `writeStoredReviseAttempt` returns boolean after setItem + getItem + validate + request_id/body equality; Workbench blocks POST on false |
| `awaiting_local_refresh` dead end | Closed | `Finish loading revised proposal` runs draft GET → ref/lineage proof → typed candidate load → mark complete; zero revise POSTs |
| `revise_busy` / `revise_history_full` terminalized | Closed | `classifyReviseResult` → `resume_same`; Resume sends exact stored body |
| Accept/Save wrong draft identity / enabled without snapshot | Closed | Candidate-bound `createdDraft` + refreshed `threatDraft` precede Advanced fields; `draftAuthorityUnavailable` disables Accept/Save |
| Proposal history hidden when candidate miss | Closed | `ProposalHistoryPanel` renders from `threatDraft` independently of `activeCandidate` |

### Post-merge authority (2026-07-28)

`#439` merged at `ff553bd8`. Sequencing no longer advances automatically to `SBW06d`. The magic-moment roadmap requires recorded `R0-A` and `R0-B` dogfood before any new SBW06d / AOW / graph-publication handoff is re-anchored. Historical §3 text below describes the pre-merge activation sync and is retained as implementation history.
| Prior four findings (reconcile proof, race ownership, class-driven actions, Unicode) | Preserved | Regression suite retained through rebase |
| Stale ThreatDraft survives draft exit / unknown-draft load | Closed | `clearThreatDraftAuthority` on Start another threat, unknown-draft candidate loads, and cross-draft identity; invalidates revise/draft-fetch generations |
| Every HTTP 409 treated as stale version | Closed | Only exact `expected_version mismatch` detail uses preclaim rebuild; integrity 409s retain attempt and Resume |
| Response `request_id` not verified | Closed | `reviseResponseMatchesAttempt` before classify/mutate; mismatch retains stored attempt |

**Verification (2026-07-28):**

```text
npm --prefix apps/live-control-ui test -- --run \
  src/api/liveApi.test.ts \
  src/statblocks/revision/statblockRevisionAttempt.test.ts \
  src/surface/modules/StatblockWorkbenchModule.test.tsx
→ 161 passed / 0 failed

typecheck: main baseline 34 diagnostics; PR head 33; PR adds no new diagnostics
  (shared planSurface/graphReview failures; PR drops unused writeStoredAcceptOperationId on Workbench)
npm run build: exit 2 on both main and PR for the same tsc -b baseline (vite assets not reached)
Bounded discovery: none
Real-provider dogfood: not run
```

---

## Dispatch gate

Do not start implementation from the provisional PR head.

Before branching:

1. Confirm PR `#435` is merged.
2. Record its actual merge SHA.
3. Rebase this handoff’s metadata on that merge.
4. Confirm `main` still contains:

   * the SBW06b revise POST route;
   * lineage-bearing candidate refs;
   * the `reconciled` revise state;
   * exact same-key replay;
   * ThreatDraft GET by exact draft ID;
   * the Dogfood Gate A Workbench flow.

Stop if PR `#435` is materially changed during merge or if the merge commit does not retain its reviewed invariants.

**Gate evidence (2026-07-27):** `#435` MERGED; merge `32eb1571`; tip `ad41a558` ancestors reviewed tip; route `POST …/candidates:revise` present; `reconcile_revise_candidate_ref` present; Workbench create-and-generate present.

---

## §0 Capability decomposition

| Candidate outcome                                          |                      Independently useful? |        Durable contract changed? | Surface changed? | Decision               |
| ---------------------------------------------------------- | -----------------------------------------: | -------------------------------: | ---------------: | ---------------------- |
| Revise the exact current editor working copy               |                                        Yes |                               No |              Yes | **Include**            |
| Persist exact browser replay authority across reload       |             Required for truthful recovery |                               No |              Yes | **Include**            |
| Load the new reconciled candidate                          |              Required for ordinary success |                               No |              Yes | **Include**            |
| Inspect all prior candidate refs and embedded lineage      |               Required by SBW06c merge bar |                               No |              Yes | **Include**            |
| Preserve separate local edits for each inspected candidate |         Required to inspect history safely |                               No |              Yes | **Include**            |
| Refresh the exact ThreatDraft version after revise         | Required for later validation/save actions |                               No |              Yes | **Include**            |
| Revise from an accepted mechanics locator                  |                                        Yes |    Uses a different exact source |              Yes | **SBW06d**             |
| Compare two candidate or mechanics definitions             |                                        Yes |                               No |              Yes | **SBW13 or successor** |
| Append an immutable child mechanics revision               |                                        Yes |                              Yes |              Yes | **SBW13**              |
| Supersede/reject candidate refs from the UI                |                                        Yes | Uses lifecycle mutation contract |              Yes | **Exclude**            |
| Publish Threat or binding graph state                      |                                        Yes |                              Yes |              Yes | **SBW08–09**           |
| Add image, combat, or document projections                 |                                        Yes |                           Varies |              Yes | **Exclude**            |

### Selected capability

A GM can ask DungeonMindServer to revise the exact current Workbench definition, using explicit revision instructions and one stable request identity, while prior proposals and their lineage remain visible and selectable.

### Why this is one slice

The revise control, browser recovery authority, successful candidate switch, and proposal history all prove the same product invariant:

```text
The source working copy is never replaced in place.

One stable revise operation creates one new durable proposal.

The GM can recover that operation and inspect both source and result.
```

---

## §1 Mission

A GM editing a generated statblock can create a revised proposal without losing unsaved edits, overwriting the source candidate, or confusing a proposal with saved mechanics.

### Merge claim

```text
From one exact current Workbench working copy, the GM can:

1. enter explicit revision instructions;
2. submit one stable request_id;
3. recover the exact same request after timeout or reload;
4. receive one reconciled new candidate;
5. load that candidate;
6. inspect all prior candidate refs and lineage;
7. return to a prior candidate without losing candidate-scoped local edits.
```

### Invariant

```text
source_definition sent to Buddy
    == the exact editor workingCopy snapshot captured for the attempt

request_id on replay
    == the original request_id

replay body
    == the exact stored request body

successful candidate switch
    occurs only after:
        response.result == reconciled
        AND exact ThreatDraft refresh proves the candidate ref
        AND the new candidate can be read by exact candidate_id

source candidate status
    remains unchanged

saved mechanics
    remain unchanged
```

### Mission falsification test

This is not one slice if implementation requires:

* a new Buddy revise journal route;
* accepted-revision source mapping;
* candidate lifecycle status controls;
* immutable mechanics append;
* candidate or revision compare;
* graph publication;
* renderer redesign;
* media;
* combat;
* or DungeonMindServer contract changes.

---

## §2 Authority and boundaries

### Read before editing

1. `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md` §12.
2. `Docs/Plans/HANDOFF-sbw06b-revise-candidate-reconciliation.md`.
3. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`.
4. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`.
5. `apps/live_control_server/models/statblock_candidate_revision.py`.
6. `apps/live_control_server/services/statblock_candidate_revision.py`.
7. `apps/live_control_server/routes/statblock_candidates.py`.
8. `apps/live_control_server/routes/threat_drafts.py`.
9. `apps/live-control-ui/src/api/types.ts`.
10. `apps/live-control-ui/src/api/liveApi.ts`.
11. `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx`.
12. `apps/live-control-ui/src/statblocks/editor/statblockEditorState.ts`.
13. Owning UI and API tests.
14. Repository rules and PR template.

### Authority precedence

```text
1. Accepted architecture and design decisions
2. Frozen SBW06 §12 contract
3. Merged SBW06b implementation and tests
4. Active roadmap and PR tracker
5. This SBW06c handoff
6. Existing UI implementation
7. Chat summaries
```

### Exact source owned by this slice

`SBW06c` supports only:

```text
source_origin_kind = edited_working_copy
```

The source is the editor’s current complete typed working copy. It is not:

* the original generated candidate payload after the GM has edited it;
* the latest Server candidate;
* the accepted mechanics locator;
* a display-name lookup;
* a cached “best available” definition;
* or a corpus/statblock file.

### What remains false after merge

* The revised proposal is not saved mechanics.
* Existing saved mechanics are not modified.
* A mechanics-saved draft cannot append the revised proposal yet.
* No candidate is automatically superseded or rejected.
* No graph node or binding is created.
* No compare view exists.
* No accepted-locator revise exists.
* No status-transition UI exists.

---

## §3 Required authority sync

The first commit must synchronize repository status after PR `#435` merges.

Update:

```text
SBW06-contract — MERGED #413
SBW06a — MERGED #417 / 8a73b101
Dogfood Gate A — MERGED #425 / 13b2e258
SBW06b — MERGED #435 / <actual merge SHA>
current slice — SBW06c
next slice — SBW06d
parallel lane — SBW08 remains independently dispatchable
```

Required documents:

* `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
* `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
* `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`
* `Docs/Plans/HANDOFF-sbw06b-revise-candidate-reconciliation.md`
* this new handoff

Rules:

* Change metadata, banners, status rows, merge SHAs, and current/next markers.
* Do not rewrite frozen §12 semantics.
* Do not claim all of SBW06 complete.
* Do not move SBW08 behind SBW06.
* Do not close SBW04’s real-candidate proof debt without named evidence.
* Do not claim accepted-revision revise or mechanics append.

---

## §4 Current implementation seam

At the implementation base, the backend already supports:

```text
POST /api/live/threat-drafts/{draft_id}/candidates:revise

exact request
→ durable journal claim
→ write-ahead dispatch
→ Server same-key revise
→ candidate cache
→ lineage-bearing ThreatDraft ref
→ journal reconciled
→ typed result
```

The same POST is also the recovery surface:

```text
same request_id + same exact body
→ continue or return the original operation

same request_id + changed body
→ revise_input_conflict
```

The backend also exposes:

```text
GET /api/live/threat-drafts/{draft_id}
GET /api/live/statblock-candidates/{candidate_id}
```

The Workbench currently supports:

```text
create ThreatDraft
→ generate candidate
→ load exact candidate
→ edit typed working copy
→ validate
→ first-save mechanics
```

The missing product path is:

```text
edited working copy
→ revision instructions
→ stable revise attempt
→ recovery/replay
→ reconciled new candidate
→ refreshed proposal history
→ exact new candidate loaded
```

### Architectural decision

Do not add a public revise-journal GET route.

Persist the exact Buddy revise request in browser session state and replay it through the existing POST route. The backend journal remains the operation authority; browser storage preserves the exact request needed to address that authority.

---

## §5 Product decisions

### 5.1 Revise control

Add a visible **Revise with AI** panel for a loaded editable candidate.

Required controls:

* Revision instructions textarea.
* One instruction per line.
* “Preserve element keys where possible” checkbox, default `true`.
* Exact source disclosure:

  * current candidate ID;
  * current ThreatDraft ID and version;
  * current editor state revision;
  * “Current unsaved working copy” wording.
* Primary action: **Create revised proposal**.
* Recovery action when applicable: **Resume same revise**.
* Explicit terminal action when permitted: **Start new revise attempt**.

Do not require a current validation receipt before revising. Revision operates on the complete typed working copy, even if it has not been validated for mechanics persistence.

### 5.2 Exact request construction

Build one `ReviseCandidateFromEditedDefinitionRequestV1` from an immutable snapshot:

```text
request_id
    = crypto.randomUUID() when creating a genuinely new attempt

expected_draft_version
    = current exact ThreatDraft.version

editor_state_revision
    = String(editorState.stateRevision)

source_definition
    = editorState.workingCopy snapshot

revision_instructions
    = normalized instruction lines

preserve_element_keys
    = checkbox value

ruleset
    = editorState.workingCopy.ruleset
```

Before construction, require:

```text
workingCopy.ruleset == currentDraft.generation_intent.ruleset
```

A disagreement is an exact-source integrity block. Do not silently choose either value.

Map optional contextual fields only from durable ThreatDraft data:

```text
intent.target_cr      = draft.generation_intent.target_cr
intent.roles          = draft.intended_roles
intent.complexity     = draft.generation_intent.complexity
intent.must_include   = draft.generation_intent.must_include
intent.must_avoid     = draft.generation_intent.must_avoid

context.party_level   = draft.encounter_context.party_level
context.party_size    = draft.encounter_context.party_size
context.terrain_notes = draft.encounter_context.terrain_notes

source.name_hint      = draft.name
source.description    = draft.description
```

Omit:

* `asset_options`;
* `actor`;
* invented source digests;
* graph-derived prose;
* accepted mechanics locators.

Do not create a second normalization recipe. The UI helper must mirror the frozen backend limits:

* trim each line;
* drop empty lines;
* preserve order;
* maximum 16 instructions;
* maximum 500 Unicode code points per instruction;
* maximum 4,000 code points total;
* do not collapse internal whitespace;
* do not split on commas.

### 5.3 Browser attempt authority

Persist the exact request before beginning the POST.

Use a draft-scoped session key:

```text
dmb.sbw06.reviseAttempt:<draft_id>
```

Suggested stored shape:

```ts
interface StoredReviseAttemptV1 {
  schema: "dmb_sbw06_revise_attempt_v1";
  draft_id: string;
  source_candidate_id: string;
  request_id: string;
  raw_instructions: string;
  request: ReviseCandidateFromEditedDefinitionRequestV1;
  last_result: ReviseResultLabel | null;
  candidate_id: string | null;
  created_at: string;
}
```

Rules:

* `request` is the exact replay body.
* Never reconstruct replay from the current editor.
* Never mutate the stored request after dispatch may have begun.
* Later editor changes remain local edits; they do not modify the unresolved attempt.
* Display which editor revision the unresolved attempt captured.
* There is no local “abandon unresolved revise” action.
* Clearing session storage is not backend proof that the operation ended.

### 5.4 Candidate-scoped working copies

The existing single stored working copy is insufficient once proposal history becomes selectable.

Introduce candidate-scoped storage:

```text
dmb.sbw.workingCopy:<draft_id>:<candidate_id>
```

Required behavior:

* Persist the active candidate’s current working copy on every editor-state change.
* Before selecting another proposal, persist the current candidate’s copy.
* When selecting a proposal, restore its own saved copy if present.
* Otherwise initialize from that candidate’s exact Server definition.
* Never apply candidate A’s local edits to candidate B.
* Treat the existing `dmb.sbw.workbenchJoin.working_copy` as a legacy same-candidate migration input only.
* Do not call candidate-scoped local copies saved mechanics.

### 5.5 ThreatDraft snapshot

Add a full exact ThreatDraft read to Workbench state.

Refresh the draft:

* after restoring a draft ID;
* after loading a candidate with a source draft identity;
* before enabling a fresh revise attempt if the snapshot is absent;
* after a reconciled revise;
* after a known stale-version response;
* after manually selecting “Refresh proposal history.”

Use the GET response’s `version`. Never calculate the next version as `oldVersion + 1`.

If the draft read is unavailable:

* retain candidate and editor state;
* retain revision instructions and pending attempt;
* disable new version-dependent revise/save actions;
* show a retry action;
* do not classify the candidate itself as corrupt.

### 5.6 Proposal history

Render a **Proposal history** panel whenever an exact ThreatDraft snapshot is available.

For every `candidate_ref`, show:

* candidate ID;
* lifecycle status;
* generated-from draft version;
* creation time;
* whether it is the currently loaded candidate;
* lineage summary.

Lineage presentation:

```text
lineage == null
    → “Generated proposal — legacy ref without revise lineage”

edited_working_copy
    → “Revised from working copy at draft v{source_draft_version}”

candidate
    → “Revised from candidate {source_candidate_id}”
      (inspectable only; SBW06c never creates this origin)

accepted_revision
    → “Revised from saved revision {statblock_id}/{revision_id}”
      (inspectable only; SBW06d creates this origin)
```

A details disclosure may show:

* request ID;
* editor state revision;
* source definition digest;
* instruction-options digest;
* exact candidate source identity;
* exact accepted revision identity.

Do not display an evidence score. Do not imply the instruction digest contains recoverable instruction prose.

Selecting a history row loads that exact candidate ID through the existing candidate-read route.

No compare UI belongs in this slice.

### 5.7 Mechanics-saved boundary

When `currentDraft.workflow_state === "mechanics_saved"`:

* Revise with AI may still revise the currently loaded unsaved working copy.
* The UI must say:

```text
Source: current unsaved working copy.
Previously saved mechanics are unchanged.
```

* Do not describe the operation as revising the saved revision.
* Do not offer “Accept again.”
* Disable the existing first-save Accept/Save action for a revised proposal on that draft.
* Display:

```text
This proposal is not saved.
Appending it as a new immutable mechanics revision is not available until SBW13.
```

SBW06d separately owns revising from the exact accepted locator.

### 5.8 No automatic lifecycle mutation

Creating a revised proposal must not:

* supersede the source candidate;
* reject the source candidate;
* mark the new candidate accepted;
* change accepted mechanics;
* change graph state.

Proposal history must visibly retain the source and the result.

---

## §6 UI result and recovery table

| Outcome                              | UI behavior                                                                                          | Stored attempt                                                  |     New request ID allowed? |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------: |
| Request in flight                    | Keep source editor and instructions visible; disable duplicate submit                                | Retain exact body                                               |                          No |
| Transport failure / unknown response | “Outcome unknown”; offer Resume same revise                                                          | Retain exact body and ID                                        |                          No |
| `revise_claimed`                     | Resume same operation                                                                                | Retain                                                          |                          No |
| `dispatched_unknown`                 | Explain Server outcome is uncertain; resume exact body                                               | Retain                                                          |                          No |
| `candidate_received`                 | Candidate exists but product reconciliation is incomplete                                            | Retain                                                          |                          No |
| `cache_stored_ref_pending`           | Candidate cached; draft attachment still pending                                                     | Retain                                                          |                          No |
| `revise_draft_unavailable`           | Draft read/reconcile unavailable; retry same operation                                               | Retain                                                          |                          No |
| `revise_busy`                        | Another unresolved revise owns the draft slot; preserve this unclaimed attempt and allow exact retry | Retain                                                          |           Not automatically |
| `revise_history_full`                | History capacity blocked before dispatch; preserve source/instructions                               | Retain                                                          |           Not automatically |
| `revise_blocked`                     | Show correctable preclaim error; preserve source/instructions                                        | Retain until explicit correction                                | Only after explicit rebuild |
| HTTP `409 expected_version mismatch` | Refresh draft; preserve edits/instructions; offer explicit retry from refreshed version              | Old attempt classified preclaim                                 | Yes, only on explicit retry |
| Definite HTTP `422` before claim     | Preserve editable inputs and show field error                                                        | May discard unclaimed exact body only after explicit correction | Yes, only on explicit retry |
| `revise_input_conflict`              | Stop; local request disagrees with backend authority                                                 | Retain for diagnostics                                          |                          No |
| `revise_integrity_conflict`          | Stop; do not load a candidate as success                                                             | Retain for diagnostics                                          |                          No |
| `terminal_failure`                   | Explain owning boundary proved terminal failure; offer Start new revise attempt                      | Retain until explicit start-new                                 |  Yes, after explicit action |
| `reconciled`                         | Refresh exact draft, prove/display new ref, then load exact candidate ID                             | Retain until refresh/load completes                             |        Yes after completion |

### Reconciled success sequence

```text
1. Receive result=reconciled and candidate_id.
2. GET exact ThreatDraft.
3. Find candidate_ref with that candidate_id.
4. Require:
      ref.request_id == stored request_id
      ref.lineage.revise_request_id == stored request_id
      ref.lineage.source_origin_kind == edited_working_copy
5. Replace current draft snapshot with GET result.
6. Load exact candidate_id.
7. Show both source and result in Proposal history.
8. Only now mark the browser attempt completed.
```

If steps 2–6 fail:

* do not issue another revise;
* retain the same request ID and request body;
* show “Revised proposal reconciled; local refresh incomplete”;
* offer exact draft/candidate refresh.

---

## §7 Files in scope

### Documentation

| Action | Path                                                             | Purpose                             |
| ------ | ---------------------------------------------------------------- | ----------------------------------- |
| Create | `Docs/Plans/HANDOFF-sbw06c-workbench-revise-ux.md`               | Dispatch authority                  |
| Modify | `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md` | Mark SBW06b merged; activate SBW06c |
| Modify | `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` | Synchronize current and next slices |
| Modify | `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`           | Metadata/status only                |
| Modify | `Docs/Plans/HANDOFF-sbw06b-revise-candidate-reconciliation.md`   | Mark merged and record handback     |

### Frontend implementation

| Action | Path                                                                            | Purpose                                                               |
| ------ | ------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Modify | `apps/live-control-ui/src/api/types.ts`                                         | ThreatDraft lineage/history and Buddy revise types                    |
| Modify | `apps/live-control-ui/src/api/liveApi.ts`                                       | GET draft and POST revise calls                                       |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts`                                  | Exact route and body proof                                            |
| Create | `apps/live-control-ui/src/statblocks/revision/statblockRevisionAttempt.ts`      | Pure request, storage, normalization, and result-classification logic |
| Create | `apps/live-control-ui/src/statblocks/revision/statblockRevisionAttempt.test.ts` | Pure adversarial state tests                                          |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx`         | Revise controls, history, recovery, selection                         |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx`    | End-to-end UI behavior                                                |
| Modify | `apps/live-control-ui/src/styles.css`                                           | Revise/history panel styling                                          |

### Explicitly outside the allowlist

Do not modify:

* backend models;
* backend services;
* backend routes;
* generated DungeonMind contract files;
* acceptance orchestration;
* renderer semantics;
* graph code;
* document code;
* combat code;
* media code.

### Bounded discovery exception

One additional frontend helper and its test may be added under:

```text
apps/live-control-ui/src/statblocks/revision/
```

Only if the candidate-scoped working-copy persistence cannot remain cleanly isolated in `statblockRevisionAttempt.ts`.

No backend discovery exception is pre-authorized.

If a backend contract change appears necessary, stop.

---

## §8 Type and API requirements

### 8.1 ThreatDraft types

Expand `ThreatDraftV1` to include the exact fields needed by the Workbench:

* focus;
* intended roles;
* tags;
* generation intent;
* encounter context;
* graph-context snapshot;
* candidate refs;
* accepted mechanics ref;
* workflow state.

Add structurally closed lineage types for all frozen variants:

* edited working copy;
* candidate;
* accepted revision.

`ThreatDraftCandidateRefV1.lineage` must be:

```ts
CandidateLineageV1 | null
```

Legacy null lineage remains valid.

Prefer a discriminated TypeScript union rather than one object with every variant optional.

### 8.2 Buddy revise types

Add:

* `ReviseCandidateFromEditedDefinitionRequestV1`
* `ReviseCandidateFromEditedDefinitionResponseV1`
* `ReviseResultLabel`
* `ReviseOperationStatus`

Reuse generated DungeonMind contract types for:

* `StatblockDefinitionV1_Input`
* `RulesetRef`
* `GenerationIntentV1`
* `EncounterContextV1`
* `SourceSnapshotV1`

Do not hand-copy the statblock definition schema into `api/types.ts`.

### 8.3 API functions

Add:

```ts
getThreatDraft(draftId)
```

using:

```text
GET /api/live/threat-drafts/{draft_id}
```

Add:

```ts
reviseThreatDraftCandidate(draftId, request)
```

using:

```text
POST /api/live/threat-drafts/{draft_id}/candidates:revise
```

Requirements:

* URL-encode IDs.
* Send the exact stored request object.
* Do not mutate, normalize, or add defaults inside `liveApi`.
* Preserve `LiveApiError` status/detail behavior.

---

## §9 Workbench implementation requirements

### 9.1 Keep pure authority logic out of the component

`StatblockWorkbenchModule.tsx` is already large and stateful.

The new pure helper should own:

* instruction normalization and bounds;
* exact request construction;
* attempt serialization validation;
* attempt storage keys;
* result classification;
* candidate-scoped working-copy keys;
* safe read/write helpers.

The component should own:

* current React state;
* async API sequencing;
* race ownership;
* rendering;
* candidate selection.

### 9.2 Race ownership

Extend the existing candidate operation generation pattern.

A stale revise response must not:

* replace a newer candidate selection;
* overwrite a newer draft snapshot;
* reset another candidate’s working copy;
* clear a newer attempt;
* or enable Accept/Save against an old draft version.

Use a monotonically increasing revise request generation plus exact draft/candidate ownership checks.

Guard double-click synchronously with a ref, not only React state.

### 9.3 Interaction with validation

Starting or finishing revise must not claim that the new candidate inherits the source validation receipt.

After loading the new candidate:

* initialize a new editor state from its definition;
* use the candidate’s own generated receipt for review only;
* clear any editor-preview validation association from the previous candidate;
* require a new preview validation before mechanics save.

### 9.4 Interaction with Accept/Save

Accept/Save must use the refreshed current ThreatDraft version.

Do not use:

* the source candidate’s `generated_from_draft_version`;
* the version stored before revise;
* or an inferred increment.

When mechanics are already saved, show the SBW13 boundary instead of offering another first-save action.

### 9.5 Session language

Use product language, not journal terminology, in primary UI:

* “Creating revised proposal…”
* “Revised proposal ready.”
* “Revision outcome unknown.”
* “Proposal attachment still pending.”
* “Resume same revise.”
* “Proposal history.”

Technical IDs and digests belong in details/disclosure views.

---

## §10 Required tests

### Pure helper tests

1. Instruction normalization trims ends, drops empty lines, and preserves internal whitespace.
2. Commas remain part of one instruction.
3. More than 16 instructions fails.
4. More than 500 code points in one instruction fails.
5. More than 4,000 total code points fails.
6. Exact request construction snapshots the current working copy.
7. `editor_state_revision` uses `stateRevision`, not editor epoch.
8. Working-copy and draft ruleset mismatch fails before POST.
9. Stored attempt round-trips without changing the request body.
10. Invalid/corrupt stored attempt fails closed.
11. Candidate-scoped storage cannot return candidate A’s copy for candidate B.
12. Result classification covers every current backend label.

### liveApi tests

1. GET ThreatDraft uses the exact encoded draft ID.
2. POST revise uses the exact encoded draft ID.
3. POST body includes:

   * request ID;
   * current draft version;
   * state revision;
   * exact working copy;
   * normalized instructions;
   * preserve flag;
   * exact ruleset;
   * exact mapped draft intent/context/source.
4. Replay sends byte-equivalent JSON structure from the stored request.
5. `LiveApiError` retains typed HTTP status/detail.

### Workbench success tests

1. Local edits are present in `source_definition`; original candidate output is not substituted.
2. Successful revise performs one POST.
3. `reconciled` triggers exact draft refresh.
4. Draft GET’s returned version replaces the prior version.
5. New candidate loads only after the refreshed draft contains its ref.
6. Source candidate remains in history.
7. Source status remains unchanged.
8. New ref displays edited-working-copy lineage.
9. New candidate becomes active.
10. New candidate starts with fresh editor-preview validation state.
11. No automatic Accept/Save occurs.
12. No automatic supersede/reject occurs.

### Recovery tests

1. Transport timeout preserves:

   * working copy;
   * raw instructions;
   * exact request;
   * request ID;
   * source candidate.
2. Hard reload restores the unresolved attempt.
3. Resume sends the exact original body.
4. Resume does not call `crypto.randomUUID()`.
5. `dispatched_unknown` does not switch candidates.
6. `candidate_received` does not claim ordinary success.
7. `cache_stored_ref_pending` does not claim ordinary success.
8. `revise_draft_unavailable` retains the attempt and offers retry.
9. `revise_busy` preserves instructions and does not create a second request ID.
10. `revise_history_full` preserves instructions and does not dispatch a replacement.
11. `revise_input_conflict` blocks replacement and preserves diagnostics.
12. `revise_integrity_conflict` blocks replacement and candidate switching.
13. `terminal_failure` permits a new ID only after explicit Start new revise attempt.
14. A definite stale-version response refreshes the draft and requires explicit retry.
15. A stale async response after candidate switching is ignored.
16. Double-click starts one POST.

### Proposal-history tests

1. Every draft candidate ref renders.
2. Current candidate is highlighted.
3. Legacy `lineage=null` is visibly described without invented provenance.
4. Edited-working-copy lineage renders source draft version.
5. Candidate and accepted-revision lineage variants deserialize and render inspect-only summaries.
6. Selecting a prior candidate uses its exact ID.
7. Switching candidates preserves separate local working copies.
8. Returning to the source restores its unsaved edits.
9. An expired or unavailable prior candidate leaves history visible.
10. Proposal selection does not mutate statuses.

### Mechanics-saved boundary tests

1. Existing saved mechanics remain visible and unchanged.
2. Revise copy says it uses the current unsaved working copy.
3. The UI does not claim it revised the saved locator.
4. “Accept again” is not offered.
5. The SBW13 append boundary is displayed.
6. No append-revision endpoint is called.

---

## §11 Verification

Run focused frontend tests:

```bash
npm --prefix apps/live-control-ui test -- \
  src/api/liveApi.test.ts \
  src/statblocks/revision/statblockRevisionAttempt.test.ts \
  src/surface/modules/StatblockWorkbenchModule.test.tsx
```

Run type checking:

```bash
npm --prefix apps/live-control-ui run typecheck
```

Run the production build:

```bash
npm --prefix apps/live-control-ui run build
```

Run formatting/diff checks required by repository rules:

```bash
git diff --check
```

### Manual dogfood proof

Use one real generated candidate and demonstrate:

```text
load candidate
→ edit at least two fields
→ enter revision instructions
→ create revised proposal
→ see both source and result in Proposal history
→ select source
→ confirm source edits are retained
→ select revised proposal
→ validate revised proposal
→ hard reload
→ confirm draft/history/current candidate restore
```

Also capture one recovery proof:

```text
interrupt or simulate timeout during revise
→ hard reload
→ source edits and instructions remain
→ Resume same revise
→ no replacement request ID
→ one reconciled result
```

If a real provider is unavailable, use the existing seeded/fake integration boundary and state that limitation in the handback. Do not claim a live provider proof that was not run.

---

## §12 Demolition declaration

### Replaced path

```text
Current gap:
GM edits a candidate but has no product revise control.
Iteration requires leaving the Workbench or generating from draft-level prose again.

Replacement:
Exact editor working copy → stable revise attempt → new inspectable proposal.
```

### Delete in this PR

No backend path is deleted.

Do not delete:

* create-and-generate;
* exact candidate recovery;
* typed editor;
* validation;
* first-save mechanics;
* Advanced draft/candidate controls;
* existing candidate renderer.

### Predecessor behavior that must disappear

* No need to manually copy the current definition into another tool to request a revision.
* No result may silently replace the source candidate in place.
* No candidate switch may discard another candidate’s local working copy.
* No timeout may clear revision instructions or mint a replacement ID.
* No successful revise may leave proposal history hidden from the operator.

---

## §13 Stop conditions

Stop and return a revised proposal rather than widening scope if:

1. PR `#435` merges with materially different request/result semantics.
2. A backend journal-read route appears necessary.
3. The existing POST cannot recover an exact same-key operation.
4. The UI cannot obtain current ThreatDraft version through the existing GET.
5. Candidate lineage cannot be represented without changing the backend schema.
6. Candidate-origin or accepted-revision request construction becomes necessary.
7. Mechanics append or compare becomes necessary.
8. Candidate lifecycle status controls become necessary.
9. Graph, document, combat, or media paths become necessary.
10. A generated DungeonMind contract file must be edited manually.
11. More than the named frontend helper exception is required.
12. The current Workbench cannot safely absorb this slice without broader component decomposition.

If the Workbench size itself blocks safe review, stop and propose one prior behavior-preserving extraction PR. Do not mix a broad component rewrite with SBW06c.

---

## §14 Handback requirements

The PR description must report:

1. Actual base and head SHAs.
2. PR `#435` merge SHA.
3. Exact changed paths.
4. Diff stat.
5. Focused test output.
6. Typecheck output.
7. Build output.
8. Whether real-provider dogfood was run.
9. Exact browser storage keys introduced.
10. Exact request fields sent.
11. How request ID replacement is prevented.
12. How transport failure and reload recover.
13. How candidate-scoped edits are preserved.
14. How draft version refresh is proven.
15. How reconciled success is proven before candidate switching.
16. How prior refs and lineage are displayed.
17. Confirmation that source status is unchanged.
18. Confirmation that accepted mechanics are unchanged.
19. Confirmation that mechanics-saved drafts do not offer “Accept again.”
20. Confirmation that no accepted locator, append, compare, graph, media, or combat behavior shipped.
21. Any bounded discovery exception used.
22. Any baseline failures or waivers.

### Final review questions

The reviewer must be able to answer **yes** to each:

* Does revise submit the exact current working copy?
* Is one stable request ID retained through timeout and reload?
* Is replay the exact stored body?
* Can a stale or partial response avoid replacing the current editor?
* Does success require a reconciled response plus refreshed draft proof?
* Does the new candidate receive a new candidate ID?
* Does the source candidate remain unchanged?
* Are all prior candidate refs inspectable?
* Is lineage visible after reload?
* Can selecting prior candidates preserve separate local edits?
* Are saved mechanics unchanged?
* Is accepted-locator revise still absent?
* Is mechanics append still absent?
* Are graph writes still absent?
* Is there no local abandon action for an unresolved revise?
