# HANDOFF — SBW Dogfood Gate A: Context-Aware ThreatDraft Create-and-Generate

**Created:** 2026-07-26
**Status:** ACTIVE — dispatch exactly one demo-enablement capability, then pause for operator dogfood.
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw-dogfood-create-generate.md`
**Implementation base:** `8a73b10185e0e4b5c84bca92c2b1f3e0deda9432`
**Suggested branch:** `feat/sbw-dogfood-create-generate`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Workstream:** Threat + Statblock Authoring and Projection
**Predecessor:** PR `#417`, `SBW06a` merged
**Paused successor:** `SBW06b` — do not begin automatically after this PR

> This is an intentional dogfood/demo pause inserted between `SBW06a` and `SBW06b`. Its purpose is to expose the already-built prose → durable ThreatDraft → DungeonMindServer candidate → structured workbench path without requiring manual API calls or copying draft IDs and versions between tools.

---

## §0 Capability decomposition decision

| Candidate outcome                                                                                                                  | Independently useful? |                            Durable contract changed? |  Surface changed? | Decision                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------- | --------------------: | ---------------------------------------------------: | ----------------: | --------------------------------------------------------------- |
| Enter threat prose and exact context, create a durable ThreatDraft, then generate and load its candidate in the existing workbench |                   Yes | No new backend contract; consumes existing contracts |               Yes | **Include**                                                     |
| Expand the typed editor to cover movement, saves, senses, resources, phases, mechanics, and all other contract fields              |                   Yes |                                                   No |               Yes | **Successor — exclude**                                         |
| Add model-assisted revise controls                                                                                                 |                   Yes |                         Uses SBW06 durable contracts |               Yes | **SBW06c — exclude**                                            |
| Attach revise lineage to ThreatDraft refs                                                                                          |                   Yes |                                                   Yes |                No | **SBW06b — exclude**                                            |
| Revise from an accepted mechanics locator                                                                                          |                   Yes |                      Uses accepted revision identity |               Yes | **SBW06d — exclude**                                            |
| Add automatic World Graph/campaign selection or a general context browser                                                          |                   Yes |                                          Potentially |               Yes | **Successor — exclude**                                         |
| Add ThreatDraft list, search, load, update, delete, or management UI                                                               |                   Yes |                 No new schema, but separate workflow |               Yes | **Successor — exclude**                                         |
| Persist browser form/editor state                                                                                                  |                   Yes |                         Browser persistence contract |               Yes | **Successor — exclude**                                         |
| Conduct and publish the complete operator dogfood findings report                                                                  |                   Yes |                                      Report artifact | Operator workflow | **Immediate post-merge activity — exclude from implementation** |

**Selected capability**

A GM can enter a new threat description and exact generation context in the Statblock Workbench, create one durable ThreatDraft, and immediately generate and load a real typed candidate.

**Why the included work is one capability**

ThreatDraft creation and candidate generation are already separate backend operations, but neither is independently useful in this surface without the other. The browser operation exists to cross one missing product seam: authored prose becomes the exact durable draft from which the displayed candidate was generated.

**Named successors**

* Editor coverage expansion.
* `SBW06b` candidate-ref lineage materialization.
* `SBW06c` revise UI.
* Exact campaign/graph context picker.
* Draft management and browser persistence.
* A separately recorded dogfood findings report.

---

## §1 Mission

A GM can author a new threat in the Statblock Workbench and generate its real typed candidate without leaving the browser or manually creating and copying a ThreatDraft identity.

**Invariant**

```text
The candidate loaded after create-and-generate was generated from the exact durable
ThreatDraft returned by the create operation, using that returned draft_id and version.

No candidate may be presented as generated from unsaved form text, placeholder campaign
or graph provenance, a guessed draft version, or another draft selected by label.
```

**Mission falsification test**

```text
This is not one slice if implementation must also expand the mechanics editor,
implement revise lineage or revise UI, add a general campaign/graph selector,
persist browser drafts, publish graph truth, or redesign the statblock renderer.
```

---

## §2 Context, authority, and boundaries

| Field                           | Required content                                                                                                                                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent authority                | `Docs/Design/DESIGN-threat-statblock-authoring-projection-workflow.md`; `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`; `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md` |
| Repository rules                | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`                                                                                                  |
| Base revision                   | `8a73b10185e0e4b5c84bca92c2b1f3e0deda9432`                                                                                                                                                                 |
| Existing durable input contract | `CreateThreatDraftRequest` → `ThreatDraftV1` through existing ThreatDraft routes/store                                                                                                                     |
| Existing generation contract    | Exact `(draft_id, expected_draft_version)` through `generateThreatDraftCandidate`                                                                                                                          |
| Existing consumer               | `StatblockWorkbenchModule` candidate load, renderer, limited editor, validation, and mechanics acceptance                                                                                                  |
| Exact input consumed            | Operator-authored threat form plus explicit or already-authoritative world, campaign, graph revision, ruleset, and actor values                                                                            |
| Named successor                 | Operator dogfood findings, followed by an explicit roadmap decision; `SBW06b` is not automatically dispatched                                                                                              |
| What remains false              | No editor expansion, revise UI, revise lineage attachment, graph publication, automatic context lookup, or durable browser form                                                                            |
| Explicit non-goals              | Backend schema redesign, new candidate generation endpoint, draft update/delete/list UI, renderer redesign, mechanics contract changes, image work, combat work                                            |

Read these inputs in order before changing code:

1. `Docs/Design/DESIGN-threat-statblock-authoring-projection-workflow.md`
2. `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
3. `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
4. `Docs/Plans/HANDOFF-sbw02-threat-draft-store.md`
5. `Docs/Plans/HANDOFF-sbw03-generate-candidate-from-draft.md`
6. `Docs/Plans/HANDOFF-sbw04-semantic-renderer-candidate-workbench.md`
7. `Docs/Plans/HANDOFF-sbw05-typed-candidate-edit-validation.md`
8. `apps/live_control_server/models/threat_draft.py`
9. `apps/live_control_server/routes/threat_drafts.py`
10. `apps/live_control_server/services/statblock_candidate_generation.py`
11. `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx`
12. Existing owning-boundary tests
13. Repository agent and external-PR-loop rules

### Authority precedence

```text
1. Repository architecture and accepted decisions
2. Current roadmap and PR tracker
3. This checked-in handoff
4. Existing backend models, routes, services, and tests
5. Existing frontend API contracts and component tests
6. Chat summaries or attached context
```

If the implementation base has moved, rebase onto current `main` and report every material change in the named seams. Do not silently adapt to a changed ThreatDraft or generation contract.

---

## §3 Observable-path inventory

| Observable path                              | Current behavior                                                      | Required behavior                                                                                                               | Owning boundary         |
| -------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| New-threat authoring                         | No workbench form creates a real ThreatDraft                          | Form accepts prose and required exact context                                                                                   | Workbench component     |
| Create success                               | Operator must create a draft elsewhere and copy its ID/version        | Returned exact `draft_id` and `version` are displayed and retained                                                              | `liveApi` + component   |
| Create → generate                            | Manual second action using copied identity                            | Generation begins from the returned identity without operator copying                                                           | Component orchestration |
| Generate success                             | Existing manual draft-generation path loads candidate                 | Same existing candidate load/render path is used                                                                                | Component               |
| Create success, generation failure           | Draft exists but current UI has no joined state                       | Keep and display exact draft identity; offer retry generation using the same version; do not create another draft automatically | Component               |
| Create validation failure                    | Not available in this UI                                              | Show typed failure; do not call generation                                                                                      | API/component           |
| Create transport outcome unknown             | Not available in this UI                                              | Do not automatically retry create or claim no draft exists; preserve entered form and show truthful uncertainty                 | Component               |
| Generate dependency unavailable              | Existing generation error                                             | Preserve exact created draft identity and offer retry                                                                           | Component               |
| Candidate generated but candidate load fails | Existing load error                                                   | Retain exact candidate ID and existing exact-candidate retry behavior                                                           | Existing component path |
| Double submit                                | Not applicable today                                                  | At most one create request from one user submit; disable and guard synchronously                                                | Component               |
| Newer operation overtakes older operation    | Existing generation/load uses monotonic candidate-operation ownership | Claim operation ownership before create; stale create/generate/load outcomes must not replace newer UI state                    | Component               |
| Manual existing-draft generation             | Requires draft ID/version                                             | Retain as a secondary/recovery path; do not delete it in this slice                                                             | Existing component      |
| Browser refresh                              | Draft remains durable, joined UI state is lost                        | No browser-persistence claim; exact IDs must be visible so the existing manual path can recover                                 | Component copy          |
| Start another threat                         | No joined workflow                                                    | Reset only transient form/orchestration state; never delete the prior durable draft                                             | Component               |
| Existing edit/validate/save                  | Already present after candidate load                                  | Continue unchanged                                                                                                              | Existing workbench      |

A behavior outside this table is a scope expansion unless it is required to preserve the invariant.

---

## §4 Files in scope — allowlist

| Action | Path                                                                         | Purpose                                                                                                              |
| ------ | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Create | `Docs/Plans/HANDOFF-sbw-dogfood-create-generate.md`                          | Check in this complete dispatch authority                                                                            |
| Modify | `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`             | Record the dogfood gate between merged SBW06a and paused SBW06b                                                      |
| Modify | `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`             | Record current slice and post-merge operator gate                                                                    |
| Modify | `Backlog.md`                                                                 | Mark the existing context-aware Workbench ThreatDraft create-and-generate item as dispatched/completed by this slice |
| Modify | `apps/live-control-ui/src/api/types.ts`                                      | Add frontend types mirroring the existing ThreatDraft create request/response shapes                                 |
| Modify | `apps/live-control-ui/src/api/liveApi.ts`                                    | Add the existing ThreatDraft create API wrapper; do not invent a new backend endpoint                                |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts`                               | Prove exact method, route, body, and typed response                                                                  |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx`      | Add the joined create-and-generate browser operation                                                                 |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | Prove orchestration, state ownership, failure, retry, and no-placeholder behavior                                    |

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/surface/modules/

Maximum additional paths:
  1

Allowed path kinds:
  An existing CSS file already owned by StatblockWorkbenchModule.

Decision rule:
  Include only when existing component classes cannot express the new form clearly.

Required report:
  Name the path and explain why existing styling was insufficient.
```

No Python production path is expected to change. If the existing ThreatDraft route cannot support this operation as documented, stop and report rather than redesigning it inside this PR.

---

## §5 Files and capabilities explicitly out of scope

| Path or capability                                                                | Why excluded                                                   |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `apps/live_control_server/models/threat_draft.py`                                 | Existing durable model is predecessor authority                |
| `apps/live_control_server/services/threat_draft_store.py`                         | Existing persistence behavior is not being redesigned          |
| `apps/live_control_server/services/statblock_candidate_generation.py`             | Existing generation orchestration is consumed unchanged        |
| `apps/live_control_server/services/statblock_candidate_revision.py`               | Revise is not part of initial dogfood entry                    |
| `apps/live_control_server/models/statblock_candidate_revision.py`                 | `SBW06b+` ownership                                            |
| `apps/live-control-ui/src/statblocks/editor/**`                                   | Editor expansion is a separately useful capability             |
| `apps/live-control-ui/src/statblocks/render/**`                                   | Renderer redesign must be driven by dogfood findings           |
| ThreatDraft list/search/load/update/delete UI                                     | Separate draft-management workflow                             |
| World Graph context browser or automatic graph resolution                         | Separate context-selection capability                          |
| Hard-coded Mireward, campaign, world, graph revision, actor, or provenance values | Would create false provenance                                  |
| `localStorage` or `sessionStorage` form persistence                               | Separate durable browser-state contract                        |
| Revise, compare, append, graph publish, embed, combat, or media                   | Named roadmap successors                                       |
| Comprehensive dogfood report                                                      | Must follow the implementation and be authored from actual use |

Nearby code is not authorization.

## §6 Implementation contract

### Input

The new form creates one existing `CreateThreatDraftRequest`.

Required exact values must include:

```text
name
description
threat_kind
created_by

world_id
campaign_id
graph_context_snapshot.graph_revision_id

generation_intent.ruleset.system
generation_intent.ruleset.edition
```

The form may also expose the existing optional generation controls:

```text
focus.session
focus.prep_label
slug_hint

generation_intent.target_cr
generation_intent.complexity
generation_intent.must_include
generation_intent.must_avoid

intended_roles
tags

encounter_context.party_level
encounter_context.party_size
encounter_context.terrain_notes

graph_context_snapshot.selected_node_ids
graph_context_snapshot.admitted_source_anchor_ids
generation_intent.ruleset.house_ruleset_id
```

Empty optional lists must be sent as empty lists where required by the existing model. Do not send UI-only strings that do not match the real request shape.

### Context authority rule

Use an exact value already available from an authoritative Live Control context only when it can be read directly without adding a new lookup, selector, or inference path.

Otherwise expose an explicit operator input.

Prohibited defaults include:

```text
world_id = "demo"
campaign_id = "current"
graph_revision_id = "latest"
created_by = "user"
a hard-coded Mireward campaign or revision
```

A visible, configurable ruleset default is permitted only when it is already an established repository/application default. Do not invent a new ruleset vocabulary in this slice.

### Output

On create success:

```text
createdDraft.draft_id
createdDraft.version
createdDraft.name
```

must become the sole authority for the immediately following generation call.

The implementation must then call the existing generation path with:

```text
draft_id = createdDraft.draft_id
expected_draft_version = createdDraft.version
```

On generation success, reuse the existing exact-candidate load path. Do not introduce a second renderer or duplicate candidate state machine.

### Operation ordering

```text
1. Validate required form fields locally.
2. Claim the next shared candidate-operation ownership token.
3. Synchronically block duplicate submission.
4. POST one ThreatDraft create request.
5. Ignore the response if a newer candidate operation owns the component.
6. Record and display the exact returned draft ID/version.
7. POST generation using that exact returned ID/version.
8. Ignore the response if a newer operation owns the component.
9. On success, load the exact returned candidate through the existing load path.
10. On generation failure, retain the created draft identity and permit exact retry.
```

The operation token must be claimed before create. A stale create response must not initiate generation or replace state after a newer load, generation, or create-and-generate action.

### Create failure behavior

```text
Definite request validation/rejection:
  show the typed failure;
  do not generate;
  allow correction and a new create attempt.

Transport or response uncertainty:
  preserve entered values;
  do not automatically POST create again;
  do not state that no draft was created;
  display that creation outcome is unknown.

Post-create generation failure:
  state that the draft was created;
  show exact draft ID/version;
  retry generation against the same draft;
  never create a replacement draft as part of retry.
```

### Start-another behavior

An explicit “Start another threat” action may clear transient component state and unlock the form.

It must not:

* delete the prior ThreatDraft;
* mark the prior ThreatDraft abandoned;
* clear or mutate its candidate refs;
* claim the prior creation did not happen.

### Existing manual path

Retain the existing `Generate from ThreatDraft` exact-ID/version form. It remains useful for:

* drafts created before this slice;
* browser refresh recovery;
* operator inspection and debugging;
* generation retry when only an exact draft identity is known.

The new create-and-generate path may populate that existing form with the returned exact identity.

### Trust boundary

```text
Verifies:
  required form values are present;
  numeric fields are valid;
  create response contains a usable exact draft_id/version;
  generation uses that returned identity;
  candidate load uses the exact generated candidate_id.

Trusts from the server:
  persisted ThreatDraft field normalization;
  generated draft UUID;
  committed draft version;
  candidate generation and cache classification.

Rejects:
  missing exact world/campaign/graph revision identity;
  guessed "latest" graph context;
  stale create/generate results;
  malformed create responses;
  candidate presentation not bound to the generated candidate ID.
```

---

### §6A State and fallback matrix

| Path                   | Loading                                         | Exact success                                 | Ordinary miss                  | Dependency unavailable           | Integrity failure            | Stale result                   | Retry                                          |
| ---------------------- | ----------------------------------------------- | --------------------------------------------- | ------------------------------ | -------------------------------- | ---------------------------- | ------------------------------ | ---------------------------------------------- |
| Create draft           | Disable duplicate submit; show creating state   | Display exact ID/version and begin generation | Not applicable                 | Preserve form; classify honestly | Fail closed; do not generate | Ignore                         | New create only when prior outcome is definite |
| Generate created draft | Show generating state with exact draft identity | Load exact candidate                          | Typed generation miss/failure  | Retain draft identity            | Fail closed                  | Ignore                         | Same draft ID/version                          |
| Load candidate         | Existing loading state                          | Existing renderer/editor path                 | Existing missing/expired state | Existing unavailable state       | Existing integrity state     | Ignore                         | Existing exact-candidate retry                 |
| Start another          | Explicit operator action                        | Reset transient UI only                       | —                              | —                                | —                            | Invalidates prior UI ownership | Creates a new draft only after submit          |
| Manual existing draft  | Existing form                                   | Existing behavior                             | Existing error                 | Existing error                   | Existing failure             | Existing ownership rules       | Existing exact retry                           |

There is no fallback to mock mechanics, corpus artifacts, another candidate, another draft, or latest graph context.

---

### §6B Identity matrix

| Situation          | Required matching rule              | Ambiguity behavior                         | Fallback                   | Persistence consequence               |
| ------------------ | ----------------------------------- | ------------------------------------------ | -------------------------- | ------------------------------------- |
| Created draft      | Exact returned `draft_id`           | Malformed/absent ID fails closed           | None                       | Durable server draft                  |
| Draft version      | Exact returned `version`            | Malformed/absent version fails closed      | None                       | Generation binds exact version        |
| Candidate          | Exact generated `candidate_id`      | Malformed/absent ID is failure             | None                       | Existing candidate cache/ref behavior |
| World/campaign     | Exact explicit or authoritative IDs | Missing blocks submit                      | None                       | Stored on ThreatDraft                 |
| Graph revision     | Exact revision ID                   | Missing blocks submit                      | No latest fallback         | Stored in graph context snapshot      |
| Display label/name | Presentation only                   | Never selects identity                     | No                         | No rebinding                          |
| Browser refresh    | No implicit restoration             | User must provide exact draft/candidate ID | Existing manual forms only | Server records remain unchanged       |

---

### §6C Persistence and replay matrix

| Operation                               | Durable representation                     | Round-trip guarantee                         | Replay behavior                                      | Rollback                      |
| --------------------------------------- | ------------------------------------------ | -------------------------------------------- | ---------------------------------------------------- | ----------------------------- |
| ThreatDraft create                      | Existing `ThreatDraftV1` store             | Returned ID/version identify committed draft | No automatic create replay after uncertain transport | No browser rollback or delete |
| Candidate generation                    | Existing generation journal/cache/ref path | Exact created draft version drives request   | Existing same-key backend behavior                   | No candidate deletion         |
| Generation retry after definite failure | Same durable draft                         | Same ID/version                              | Reuse exact draft; do not recreate                   | None                          |
| Candidate load                          | Existing cache/read route                  | Exact candidate ID                           | Existing exact retry                                 | None                          |
| Browser state                           | React memory only                          | No refresh claim                             | No persistence                                       | Reset affects UI only         |

This slice introduces no new durable frontend storage and no new backend schema.

---

### §6D Predecessor-to-consumer mapping

**Grounding sources**

```text
apps/live_control_server/models/threat_draft.py
apps/live_control_server/routes/threat_drafts.py
apps/live_control_server/services/statblock_candidate_generation.py
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

| Predecessor field/outcome                         | Consumer behavior               | Transformation                             | Proof                        |
| ------------------------------------------------- | ------------------------------- | ------------------------------------------ | ---------------------------- |
| `CreateThreatDraftRequest.name`                   | Name input                      | Trim only as existing server/model permits | API/component test           |
| `description`                                     | Main threat prose field         | Preserve complete authored prose           | Exact request-body assertion |
| `world_id`, `campaign_id`                         | Context inputs                  | No label-to-ID inference                   | Component test               |
| `graph_context_snapshot.graph_revision_id`        | Exact graph context field       | No latest lookup                           | Component/API test           |
| `selected_node_ids`, `admitted_source_anchor_ids` | Optional advanced inputs        | Parse into bounded string arrays           | Component test               |
| `generation_intent.ruleset`                       | Ruleset controls                | Exact object shape                         | API test                     |
| `target_cr`, `complexity`, include/avoid          | Optional generation controls    | Existing request vocabulary only           | API test                     |
| create response `draft_id`                        | Existing draft ID state         | Copy exact value                           | Orchestration test           |
| create response `version`                         | Existing expected-version state | Copy exact integer                         | Orchestration test           |
| generation success candidate ID                   | Existing `loadCandidate` path   | No duplicate candidate state machine       | Component test               |
| generation failure                                | Draft-created partial state     | Retain exact draft identity                | Component test               |

---

## §7 Verification ownership map and commands

| Guarantee                                                           | Owning boundary       | Required proof                                        |
| ------------------------------------------------------------------- | --------------------- | ----------------------------------------------------- |
| Request mirrors existing ThreatDraft create contract                | `liveApi`             | Exact HTTP method, URL, and body test                 |
| Exact returned draft identity drives generation                     | Component             | Mocked create → generate argument assertions          |
| No generation after create failure                                  | Component             | Failure test                                          |
| Generation failure retains draft and retries without recreating     | Component             | Create count remains one; generation count increments |
| Duplicate submit creates at most one draft                          | Component             | Synchronous double-click/in-flight test               |
| Newer operation wins over delayed create                            | Component             | Deferred promise race                                 |
| Newer operation wins over delayed generation                        | Component             | Deferred promise race                                 |
| No hard-coded campaign/world/graph provenance                       | Component/source test | Required fields or authoritative injected values      |
| Existing manual generate path still works                           | Component regression  | Existing tests remain green                           |
| Existing candidate render/edit/validate/save path remains reachable | Component/manual      | Candidate automatically loads into existing path      |
| No backend contract changed                                         | Diff boundary         | No Python production path in diff                     |

Run and record exact results:

```bash
cd apps/live-control-ui

npm test -- --run \
  src/surface/modules/StatblockWorkbenchModule.test.tsx \
  src/api/liveApi.test.ts

npm run typecheck
```

The full typecheck is known to have unrelated baseline debt in this repository. If it fails, run the identical command on base and head, compare diagnostic sets, and report whether the slice introduced any new diagnostic.

Run existing backend contract regression without modifying backend code:

```bash
cd <repo-root>

uv run pytest \
  tests/test_threat_draft_routes.py \
  tests/test_statblock_candidate_routes.py \
  tests/test_statblock_candidate_generation.py \
  -q --tb=line
```

Then:

```bash
git diff --check

git diff --stat \
  8a73b10185e0e4b5c84bca92c2b1f3e0deda9432...HEAD -- \
  Docs/Plans/HANDOFF-sbw-dogfood-create-generate.md \
  Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md \
  Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md \
  Backlog.md \
  apps/live-control-ui/src/api/types.ts \
  apps/live-control-ui/src/api/liveApi.ts \
  apps/live-control-ui/src/api/liveApi.test.ts \
  apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx \
  apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx

git diff --name-only \
  8a73b10185e0e4b5c84bca92c2b1f3e0deda9432...HEAD
```

### Minimal live proof — required

Use the existing Live Control surface. Do not build a separate demo page.

**Scenario**

1. Start the Buddy backend and Live Control UI using the repository’s standard development commands.
2. Connect to a real local DungeonMindServer instance.
3. Enter a newly authored Mireward threat that is not copied from an existing statblock fixture.
4. Supply exact world, campaign, graph revision, ruleset, and actor values.
5. Submit create-and-generate once.
6. Observe the exact durable draft ID/version.
7. Observe the exact candidate ID and structured renderer.
8. Switch to the existing editor.
9. Make one supported scalar or rules-text change.
10. Validate the working copy.
11. Do not expand or fix the editor during this proof.
12. Optionally continue through existing Accept/Save solely to confirm the new entry path reaches the current vertical slice.

**Required evidence**

Record in the PR body:

* exact base and head SHAs;
* the non-sensitive threat description used;
* exact draft ID/version;
* exact candidate ID;
* create outcome;
* generation outcome;
* renderer observation;
* editor/validation observation;
* whether Accept/Save was exercised;
* screenshots or a short recording when practical;
* every friction point noticed, without fixing it unless required by this handoff.

Do not convert dogfood observations into extra implementation scope.

---

## §8 Demolition declaration

```text
Replaced path:
  Manual API creation of a ThreatDraft followed by copying draft_id/version
  into the Statblock Workbench for every newly authored threat.

Deleted in this PR:
  No.

Retained reason:
  Exact-ID/version generation remains necessary for existing drafts, refresh
  recovery, debugging, and operator-controlled retry.

Named remaining consumer:
  Existing durable ThreatDrafts and exact recovery workflows.

Required deletion owner:
  None currently. Dogfood may determine whether the manual path should remain
  as an advanced/recovery affordance permanently.
```

No mock or corpus fallback is introduced.

---

## §9 Required implementation handback

The PR body must include:

1. Base SHA `8a73b10185e0e4b5c84bca92c2b1f3e0deda9432`.
2. Head SHA.
3. Actual changed paths.
4. Focused diff stat.
5. Exact automated command results and exit codes.
6. Base/head typecheck comparison when the full typecheck remains red.
7. Minimal live-proof evidence with exact draft and candidate identity.
8. Explicit provenance for author-local, independently rerun, CI, and manual evidence.
9. Paths outside the allowlist, or `none`.
10. Baseline failures and waivers, or `none`.
11. Stop conditions encountered, or `none`.
12. Confirmation that no Python production contract changed.
13. Confirmation that the limited editor was not expanded.
14. Confirmation that `SBW06b`, `SBW06c`, graph publication, and renderer redesign remain false.
15. A concise dogfood observation ledger without opportunistic fixes.
16. Confirmation that this complete handoff was implemented without compression or omitted constraints.

Do not report the entire statblock authoring workflow as complete.

---

## §10 Acceptance rubric

The reviewer accepts only when all are true:

* [ ] A new threat can be authored and submitted from the existing workbench.
* [ ] Exactly one durable ThreatDraft is created for one successful submit.
* [ ] The returned exact `draft_id` and `version` drive generation.
* [ ] The resulting exact candidate loads through the existing renderer path.
* [ ] A create failure cannot dispatch generation.
* [ ] A generation failure retains the created draft and retries without creating another draft.
* [ ] Duplicate submit is guarded synchronously.
* [ ] Delayed create/generate results cannot overwrite a newer operation.
* [ ] World, campaign, graph revision, actor, and ruleset values are exact and non-placeholder.
* [ ] No mock, corpus, latest, label, or alternate-candidate fallback exists.
* [ ] The existing manual exact-draft generation path remains operational.
* [ ] Browser refresh behavior is described honestly; no persistence is implied.
* [ ] Existing edit, validation, and acceptance behavior remains unchanged.
* [ ] No backend production file changed.
* [ ] No editor or renderer expansion was absorbed.
* [ ] The required live proof used a real newly authored Mireward threat.
* [ ] Dogfood observations were recorded but not silently implemented.
* [ ] Roadmap/tracker now show this dogfood gate and keep `SBW06b` paused.
* [ ] No unexpected path changed.

---

## §11 Post-merge operator gate

Merging this PR does not authorize automatic continuation into `SBW06b`.

After merge, stop implementation dispatch and conduct a GM-led dogfood session using the new entry path.

The operator should evaluate:

```text
Can I describe the threat naturally?
Did the generated creature match the intended role?
Can I find the combat-critical information quickly?
Which generation mistakes are most common?
Which currently protected editor fields actually block correction?
Are validation messages understandable?
Does save mechanics feel distinct from graph publication?
Can I recover after an ordinary failure or refresh?
What feels like implementation plumbing rather than a GM workflow?
```

The next roadmap decision must be based on those findings.

Possible outcomes include:

* resume `SBW06b`;
* prioritize renderer usability;
* add one narrowly selected editor capability;
* improve ThreatDraft authoring context;
* improve candidate/draft navigation;
* fix a discovered reliability blocker.

Do not assume `SBW06b` remains next merely because it was next before dogfood.

---

## Stop conditions

Stop and report rather than expanding scope when:

* the existing create route cannot support a truthful joined operation;
* exact graph/campaign context cannot be supplied without creating a general selector or inference system;
* the create response lacks exact durable draft identity;
* create transport uncertainty requires a new idempotency contract for this capability to be usable;
* the component cannot reuse the existing candidate-operation ownership model;
* a new browser persistence contract appears necessary;
* a backend model, route, or store change is required;
* a path outside §4 or its bounded exception is needed;
* the editor or renderer must change to make create-and-generate technically function;
* live proof exposes a severe blocker that invalidates the mission;
* current `main` materially differs from the pinned predecessor contracts.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently widening the PR.

---

## Final dispatch check

* [ ] Branch from `8a73b10185e0e4b5c84bca92c2b1f3e0deda9432`.
* [ ] Check this complete handoff into the canonical path.
* [ ] Read all authorities and predecessor seams.
* [ ] Confirm existing create route shape before editing frontend types.
* [ ] Confirm the form has no placeholder identity or provenance.
* [ ] Reuse the current candidate-operation ownership mechanism.
* [ ] Keep the existing manual generation path.
* [ ] Treat create-success/generate-failure as truthful partial completion.
* [ ] Add owning-boundary race and retry tests.
* [ ] Run required frontend and backend regression commands.
* [ ] Perform the real Mireward live proof.
* [ ] Record dogfood friction without expanding scope.
* [ ] Pause after merge for operator review.
