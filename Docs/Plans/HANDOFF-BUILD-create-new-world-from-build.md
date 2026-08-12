---
# Instantiated from the operator-provided HANDOFF.template.md on 2026-08-11.
# The checked-in handoff, cumulative diff, numbered review handback, and
# independently rerun verification are authoritative. The PR body is transport only.
pr_body_template: |
  ## Handoff pointer
  - Conversation: CON-READY
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md
  - Branch: agent/con-ready-build-new-world-source

  ## Verification pointer
  - Base: 575dcdc47be6132dfe87d8f41bd7b862a63b64f7
  - Merged predecessor: PR #562
  - Verification: see §7 and the latest numbered review handback

  The checked-in handoff, cumulative code diff, nano commits, review handback,
  and independently rerun verification are the review contract. The PR
  description is transport metadata only.
---

# HANDOFF — BUILD: Create a New World from Build

**Created:** 2026-08-11  
**Status:** ACTIVE — dispatch exactly one implementation capability  
**Conversation / workstream:** `CON-READY`  
**Flow / agent:** `BUILD`  
**Handoff direction:** `DESIGN → CODE`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md` on the implementation branch  
**Implementation branch:** `agent/con-ready-build-new-world-source`  
**PR title:** `BUILD: create a new world from Build`  
**Base:** `main` at `575dcdc47be6132dfe87d8f41bd7b862a63b64f7` — merged PR #562  
**Merged predecessor:** PR #562 — `BUILD: import pasted Markdown as a lossless world source`  
**Roadmap slice:** `CR01B` — finish the new-world half of `CR01 — Source Ingress & Reading` before rich source reading  
**Primary user story:** `CR-U1 — Bring external material into DungeonBuddy`  
**Named immediate successor:** rich source reading for `CR-U2`  

> **Dispatch rule:** This handoff is authoritative once checked into the implementation branch. It does not need to merge to `main` before BUILD starts, and its presence on `main` is not a merge gate.
>
> **PR-body rule:** The PR description is optional transport metadata. It is never a merge gate and is never a substitute for the handoff, cumulative diff, nano-commit story, review handback, or verification.
>
> **Review-count rule:** Every formal review increments the review-cycle count exactly once. The first formal review on this PR is `Review Cycle 1`; every later formal review is 2, 3, 4, … regardless of PASS or CHANGES REQUESTED. Fix commits, discussion comments, CI reruns, and dogfood notes do not increment the count until a formal review occurs.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Independently useful outcome** | An outcome that remains valuable if neighboring roadmap work never ships. |
| **Public/durable contract** | A persisted format, identifier, API, schema, file representation, or externally consumed interface that must remain interpretable beyond one call stack. |
| **Observable path** | A user-visible or externally observable route through success, error, retry, persistence, and operator behavior. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved. |
| **Invariant** | The property every changed layer and observable path establishes or protects. |
| **Evidence ledger** | Mapping from invariant clauses to owning boundaries, required proof, produced result, provenance, and stop condition. |
| **World container** | The minimum durable product identity that says a named world exists and owns a source-root directory. It is not a World Graph, campaign, or published corpus. |
| **Managed world** | A world container created through this product contract and recorded in the managed world-container registry. |
| **World-level Build scope** | A Build source whose exact `world_id` is the world container ID and whose required legacy-compatible `campaign_id` field also carries that same world ID. This does **not** assert that a campaign exists. |
| **Source root** | Server-owned `corpus/<world_id>-markdown/`, created for the world container so PR #562 source storage can later place managed sources beneath `_dungeonbuddy/sources/`. |
| **Stop condition** | A discovered fact that invalidates the slice boundary or required proof and must be reported before implementation expands. |

---

# §0 Pickup and operating rules

Before implementation:

1. Read `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`.
2. Read `Docs/Roadmaps/ROADMAP-con-ready.md`.
3. Reconcile this handoff against current `main`, open PRs, and the merged PR #562 implementation.
4. Confirm no newer branch has already introduced a general world-container registry or new-world Build flow.
5. If repository truth contradicts a foundational assumption below, stop and report the contradiction rather than layering a second authority system over it.

The governing question for every implementation choice is:

> **If the architecture disappeared from the PR description and I only watched the GM use Build, what new thing could they reliably do?**

For this PR the answer must be:

> **Create a genuinely new named world from Build, then create/import the first source into it without manual directory creation, hardcoded campaign-map edits, or CLI work.**

Do not turn this into a graph-bootstrap, campaign-management, source-reader, asset, or generalized workspace-management PR.

---

# §1 Mission and merge-ready invariant

## Primary CON-READY user story

`CR-U1 — Bring external material into DungeonBuddy`

Roadmap requirement still false after PR #562:

> the GM can choose an existing world **or establish a new world**.

## Current user-visible failure

PR #562 made lossless pasted Markdown ingress work for an **already admitted world**. Its Hesta dogfood then exposed the remaining placement failure: Build only offers existing known/admitted campaign scopes. If the GM is preparing a convention one-shot in a world that does not exist yet, they must leave the product and manually establish filesystem/mapping state before Import can succeed.

The dogfood backlog captured this exact signal:

> Build Import should be able to designate a new world or campaign.

This PR takes the smallest useful half of that signal: **new world creation**. It deliberately does not invent campaign lifecycle.

## Mission

> **As a GM creating or importing a Build source, I can establish a new named world from the same Build flow, so the first source lands durably in that world and the world remains available for later Build sources without manual filesystem or code edits.**

## One independently useful outcome after this PR

From either `+ New source` or `Import source`, the GM can select `New world`, enter a human world name, submit the operation, and end with:

- one durable world-container identity;
- one server-created source root owned by that world;
- one Build worldbuilding source using the exact new world identity;
- the existing PR #562 source/import path for source bytes;
- the new world available as an existing destination after reload and for a second Build source.

## Merge-ready invariant

> **One explicit Build new-world intent creates or reconciles one durable managed world container with one server-owned source root; the first Build source uses that exact world identity through the existing PR #562 workspace/source-import authority; retries cannot duplicate the world, partial source failures do not roll the world back or create another world, existing campaign flows remain unchanged, and world creation alone does not create a World Graph, campaign, graph mapping, publication, or source content.**

## What remains deliberately false afterward

- `CR-U2` rich source reading is still false and is the immediate CON-READY successor.
- Creating a **new campaign inside an existing world** is still false.
- The new world has no World Graph merely because the container exists.
- The new world is not added to `WORLD_ID_BY_CAMPAIGN` and does not become a graph-projection mapping.
- Graph Find / graph object insertion for a brand-new graphless world may remain unavailable with truthful UX.
- World rename, delete, archive, merge, import/adopt-existing-directory, and campaign administration remain false.
- `.md` file upload, asset upload, image resolution, extraction, Hermes source follow-through, statblocks, playable-layer work, and combat remain false.

## Real one-shot dogfood proof

Use Build to create a world that does not exist on disk or in any hardcoded map, import a small real one-shot Markdown source into it, hard reload, then create a second Build source in the same world. No terminal, manual `mkdir`, registry editing, or source-specific fixture metadata is allowed.

## Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Every path establishes or reuses one exact managed world container before delegating source creation/import to #562. |
| What adversarial sequence is most likely to falsify it? | `world create succeeds → response/source create fails → user retries → duplicate world/root/source is minted`, or `new world silently becomes graph/corpus authority because its directory exists`. |
| Would §7 evidence detect that failure? | **Yes.** Registry/route tests own world identity and root lifecycle; controller tests own recovery/composition; existing #562 regression tests own source identity/import; dogfood proves the complete GM path. |
| Which boundary is easiest to under-test? | The seam between successful world creation and failed source creation/import. The world must remain reusable, while #562's pending-source identity remains separate. |
| What fact would force a stop/split? | Discovery of an already-authoritative general world registry/container contract, or evidence that merely creating `corpus/<world>-markdown/` grants graph/publication authority in a product path. |

---

# §2 Context, authority, and boundaries

## 2.1 Re-anchored repository truth

At dispatch, current `main` is:

`575dcdc47be6132dfe87d8f41bd7b862a63b64f7`

This is the merge commit for PR #562.

PR #562 established:

- exact `world_id` on new world-scoped `worldbuilding_source` records;
- server-derived source target `corpus/<world_id>-markdown/_dungeonbuddy/sources/<document_id>/source.md`;
- an intentional requirement that `corpus/<world_id>-markdown/` already exist before such a source can be created;
- one-time exact `source_import` through the existing Tiptap/Canvas CAS authority;
- managed `_dungeonbuddy` exclusion from legacy batch ingest, planner manifest/ref index, planner fingerprint, and Hermes lexical fallback;
- retry-safe source identity and hard-reload recovery;
- SourceArtifact packaging using exact record `world_id`;
- no implicit graph extraction/publication.

This PR **must reuse** those contracts. It should remove the manual prerequisite for the world source root, not redesign source storage or source-import authority.

## 2.2 Current placement/mapping constraints

Current Build create/import derives world identity from existing scope mapping in `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts`, whose campaign map is intentionally static:

```text
longmont-c1 → eldyrwild
longmont-c2 → eldyrwild
```

Current Build bare-entry creation choices are likewise rooted in known campaigns plus campaign IDs already present on Build sources.

Do **not** solve new-world creation by dynamically mutating or appending to that campaign map. A new world is not a campaign mapping.

## 2.3 Existing graph bootstrap is not this contract

`apps/live_control_server/routes/world_graph_bootstrap.py` is an existing, Eldyrwild-specific graph bootstrap flow. It is not a general world-container API.

Do not widen or repurpose it in this PR.

World container creation establishes source placement only. Generic graph initialization belongs to CR02 when source-backed world ingestion needs it.

## 2.4 Authority matrix

| Concern | Authority before this PR | Authority after this PR |
|---|---|---|
| World display name + managed world existence | none/general mechanism absent | new world-container registry |
| World ID | existing hardcoded/legacy identities or caller field on source create | server-owned exact ID on managed world record |
| World source root | pre-existing filesystem directory | world-container service creates and owns root for managed worlds |
| Build source identity | workspace document registry | unchanged |
| Build source target | workspace document registry server derivation | unchanged |
| Source bytes | Tiptap/Canvas write authority + #562 `source_import` | unchanged |
| Campaign mapping | static/current mapping code | unchanged |
| World Graph | graph-memory/bootstrap/promotion authorities | unchanged; **not created here** |
| Source publication/extraction | existing explicit ingest/promotion paths | unchanged; world/source presence alone does nothing |

## 2.5 Public/durable contract introduced by this PR

A minimal **managed world-container registry** is allowed and expected unless implementation discovers an existing general authority that already satisfies the same need.

Proposed durable shape:

```text
dmb_world_container_registry_v1
  records[]
    dmb_world_container_record_v1
      world_id
      name
      source_root_relpath
      created_at
```

Recommended persistence:

`out/registries/world_containers.json`

Recommended source root:

`corpus/<world_id>-markdown/`

The exact serializer/model names may vary if repository conventions strongly prefer another name, but the semantics above are frozen:

- `world_id` is immutable identity;
- `name` is human-facing display text;
- `source_root_relpath` is server-derived and cannot be supplied by the client;
- creation does not create graph/campaign/source records;
- registry records survive restart.

If an existing canonical general world registry is discovered, **STOP** and report rather than introduce a parallel registry.

## 2.6 Managed world creation API

A narrow live-control API is allowed and expected, for example:

```text
GET  /api/live/world-containers
POST /api/live/world-containers
```

Create input should be human-facing and minimal:

```json
{ "name": "The Glass Orchard" }
```

Normal clients must **not** supply:

- `world_id`;
- filesystem path;
- graph revision/graph root;
- campaign ID;
- source document ID.

The server owns exact ID derivation/allocation and the source-root path.

## 2.7 World name and identity rules

The implementation must freeze and test a deterministic, server-owned safe-ID policy before merge. The handoff does not require a particular slug/hash spelling, but these behaviors are required:

1. user name is trimmed and normalized for duplicate comparison while preserving a human display name;
2. empty/whitespace-only names fail 422;
3. the resulting world ID satisfies the existing safe world-ID requirements used by workspace source storage;
4. exact same normalized world name is idempotent/reconcilable and cannot mint a second managed world on retry;
5. if ID derivation collides with a **different** managed name, fail closed with 409 rather than silently suffixing/adopting;
6. client-supplied IDs/paths are rejected by contract;
7. an unmanaged pre-existing source root at the would-be managed path must not be silently adopted.

A readable slug is desirable but not more important than stable exact identity and retry safety.

## 2.8 Filesystem + registry transaction rule

World creation spans a managed registry record and one directory. It must not leave a durable record that claims a missing root after an ordinary failed operation.

Required behavior:

- validate name/ID/path first;
- serialize concurrent registry creates with the existing registry-lock conventions or an equivalently bounded lock;
- if root creation fails, do not commit the registry record;
- if registry persistence fails after this operation created a new empty root, best-effort remove only that newly created empty root;
- never recursively delete or roll back a pre-existing/non-empty path;
- after a successful response (or a lost response after success), GET/list can recover the exact managed world.

Do not create a general filesystem transaction framework for this.

## 2.9 Build world-level scope compatibility

The existing workspace document record still requires `campaign_id`.

For a Build source that belongs directly to a managed world and not to a campaign, this PR uses the existing world-level compatibility representation:

```text
world_id    = <exact managed world id>
campaign_id = <same exact managed world id>
```

This means **“world-scoped Build source”**, not “a campaign named after the world.”

The controller should carry an explicit destination object/identity for managed worlds rather than attempting to force the new world through `getWorldIdForCampaign()` or append it to `WORLD_ID_BY_CAMPAIGN`.

The record itself remains enough to reopen the Build source after hard reload.

## 2.10 Existing-scope compatibility

Existing campaign destinations such as Longmont C1/C2 must continue through their current mapping and current source behavior unchanged.

Do not migrate legacy Build sources or rewrite existing campaign IDs/world IDs.

## 2.11 World creation does not equal graph admission

After new-world creation:

- no World Graph revision is required to exist;
- graph projection for the new world may truthfully be unavailable;
- no entry is added to `WORLD_ID_BY_CAMPAIGN`;
- no implicit graph bootstrap endpoint is called;
- no extraction/promotion runs;
- no legacy corpus ingestion runs merely because the world root exists.

A source can be useful/readable before a graph exists. CR02 owns generic first-graph initialization as needed for extraction/publication.

---

# §3 Observable paths and adversarial sequences

## 3.1 Normal Import into new world

```text
Build
  → Import source
  → destination: New world
  → world name: The Glass Orchard
  → source title + Markdown
  → submit once
  → create/reconcile managed world container
  → source root now exists
  → create one world-scoped worldbuilding_source
  → existing #562 source_import
  → activate exact documentId
  → Build shows source
```

Expected durable identities:

```text
World container:
  world_id = W
  name = The Glass Orchard
  root = corpus/W-markdown/

Workspace source:
  document_id = D
  world_id = W
  campaign_id = W
  target = corpus/W-markdown/_dungeonbuddy/sources/D/source.md
```

## 3.2 Normal New Source into new world

Same world-container sequence, but after world creation use existing blank-source creation rather than `source_import`.

The world container should not depend on pasted source content.

## 3.3 Reuse managed world after reload

```text
hard reload Build
  → managed worlds are listed from server authority
  → The Glass Orchard is an existing destination
  → New Source / Import source selects it
  → no world-create POST needed
  → source uses exact existing W
```

## 3.4 World create succeeds; source create fails

```text
POST world succeeds
  → POST workspace source fails
  → world W remains durable/selectable
  → UI reports source failure truthfully
  → retry/re-submit reconciles/reuses W
  → no second world
```

Do not delete W as rollback. The GM explicitly asked to create it, and it is independently useful state.

## 3.5 World create succeeds; import prepare/commit fails

After the workspace record exists, **PR #562 pending-source authority owns the retry**. The new world lifecycle must not invent a competing pending-source mechanism.

Expected:

- exact W reused;
- exact pending document D reused under #562 rules;
- no second W;
- no second D unless #562's normal fresh-import semantics explicitly require one after the previous lifecycle is retired.

## 3.6 World create response is lost

On ambiguous create failure, retry/recovery must reconcile server state before blindly creating another world. Exact strategy may use the managed-world list/get contract, but behavior is frozen:

- if matching managed world exists, reuse it;
- if no matching managed world exists, retry creation;
- if a conflicting different world owns the derived identity/path, fail closed.

## 3.7 Double submit

While world/source creation is in flight, the UI must not issue a second independent world-create intent.

## 3.8 Name collision / unmanaged root

- same normalized managed name → same/reconciled world;
- conflicting different managed name/identity → 409, no suffix magic;
- unmanaged root occupying intended managed path → fail closed; do not adopt/delete it.

## 3.9 Existing campaign regression

`Import source → Longmont C2` must behave as it did after #562. New world support cannot make all sources world-level or change the campaign picker into guessed world identity.

## 3.10 Graphless new world

If the user tries graph-specific Build capability before CR02 has initialized a graph, the product may show the existing unavailable/empty/error state. It must not silently map the world to Eldyrwild or another known campaign.

## 3.11 Restart

Restarting live-control and reloading Build must preserve:

- world-container record;
- source root;
- existing managed world as destination;
- source records/bytes already guaranteed by #562.

---

# §4 Strict implementation scope / changed-path allowlist

Every production-path change must be listed here or be justified under the bounded discovery exception and added to the handoff before review acceptance.

## Server — expected

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/world_container_registry.py` | File-backed managed world identity + source-root lifecycle. |
| Create | `apps/live_control_server/routes/world_containers.py` | Narrow list/create live-control API. |
| Modify | `apps/live_control_server/main.py` | Register the new route. |
| Create | `tests/test_world_container_registry.py` | Registry/root/idempotence/collision/adversarial proof. |
| Create | `tests/test_live_world_containers.py` | HTTP contract proof. |
| Modify | `tests/test_workspace_document_registry.py` | Integration proof: managed root enables existing #562 world-scoped source contract without weakening missing-root fail-closed behavior. |

## Frontend — expected

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | World-container API types. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | List/create managed world API calls. |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Wire contract proof. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.tsx` | Existing destination vs New world interaction for New Source + Import. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.test.tsx` | Component behavior, validation, duplicate-submit proof. |
| Modify | `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts` | Compose world creation/recovery with existing source creation/import authority. |
| Modify | `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.test.ts` | State-machine/adversarial proof. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx` | Prop/wiring only if controller UI contract requires it. |
| Modify | `apps/live-control-ui/src/buildSurface/buildSurface.css` | Minimal destination/new-world form styling only if required. |

## Durable contract documentation — expected

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Design/CONTRACT-world-container-v1.md` | Freeze the new durable registry/API/path/authority contract. |
| Current handoff | `Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md` | Implementation/review authority. |

## Paths that should usually remain unchanged

- `apps/live_control_server/services/workspace_document_registry.py` — #562 already has the correct root-precondition and source path. Prefer proving composition rather than weakening it.
- `apps/live_control_server/services/tiptap_markdown_write.py` — no source-write change required.
- `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts` — already accepts explicit `worldId` for worldbuilding-source intent.
- `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` — do not mutate static campaign mapping to fake new-world graph admission.
- `apps/live_control_server/routes/world_graph_bootstrap.py` — do not generalize Eldyrwild graph bootstrap here.

Changing one of these production paths requires an explicit handoff reconciliation explaining why the same CR-U1 invariant cannot be implemented without it.

## Bounded discovery exception

Adjacent owning tests/types/helpers may be changed when current repository structure resolves to a different exact filename than this handoff expected. Before expanding:

1. name the discovered path;
2. state which invariant clause it owns;
3. confirm it is not a new capability;
4. add it to the handoff/handback.

Unrelated cleanup is not a bounded exception.

---

# §5 Explicitly out of scope

Do not implement any of the following in this PR:

- new campaign creation or campaign registry;
- edits to hardcoded campaign→world graph mapping solely to admit the new world;
- generic graph creation/bootstrap;
- changes to Eldyrwild-specific graph bootstrap;
- extraction, review, graph publication, or promotion;
- source reader / rendered Markdown mode;
- Markdown file upload;
- asset upload/copy/serving/image rendering;
- Hermes source follow-through;
- NPC/place/threat projections;
- statblock import;
- Playable Layer persistence;
- combat integration;
- world rename/delete/archive/merge;
- adopting arbitrary pre-existing `corpus/*-markdown` roots;
- scanning the filesystem to infer managed worlds;
- moving/migrating existing world roots or existing Build sources;
- changing #562 `source_import` normalization/CAS/retry semantics;
- auto-creating a graph or campaign as a side effect of world creation;
- arbitrary world metadata/description/settings framework;
- generalized multi-tenant account/world permissions.

If implementation needs one of these to make the mission true, stop and return evidence rather than widening silently.

---

# §6 Implementation contract

## 6.1 World-container service contract

The service owns:

- managed world registry load/list/create;
- server-generated immutable world ID;
- human display name;
- server-derived source-root path;
- source-root creation;
- duplicate/idempotence checks;
- unmanaged-path collision refusal;
- file-backed persistence using repository locking/CAS conventions.

It does **not** own:

- source documents;
- source bytes;
- graph state;
- campaigns;
- extraction;
- publication.

## 6.2 Suggested schema contract

```text
WorldContainerRecordV1
  schema_version = dmb_world_container_record_v1
  world_id: non-empty safe immutable string
  name: non-empty human display string
  source_root_relpath: exact server-derived relative path
  created_at: UTC timestamp

WorldContainerRegistryV1
  schema_version = dmb_world_container_registry_v1
  records: WorldContainerRecordV1[]
```

No mutable fields are required for this slice.

If implementation adds `updated_at`, it must not imply a rename/update API exists.

## 6.3 Identity matrix

| Identity | Rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| World container | exact `world_id` | duplicate/collision resolved by registry rules, never title guessing downstream | No guessed world |
| World display | `name` | normalized only for create duplicate comparison; display remains human-facing | No identity-by-display after selection |
| Source root | server derives from exact world ID | unmanaged pre-existing path blocks create | No client path |
| Existing campaign destination | current exact campaign ID + mapped world | current fail-closed behavior | No new guessing |
| Managed world destination | exact world record | `campaign_id=world_id`, `world_id=world_id` for Build source | No campaign fabrication |
| Workspace source | exact `document_id` | #562 rules | No title fallback |
| Graph | no graph identity created here | graph absence is allowed | No Eldyrwild fallback |

## 6.4 Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Rollback |
|---|---|---|---|---|
| Create world | world-container registry + source-root dir | list/restart returns same world ID/name/root | same normalized create intent reconciles; conflicting collision fails | only clean up a newly created empty root when the registry create itself fails |
| Create source in new world | existing workspace registry | same document/world/path on reopen | existing create lifecycle | world remains if source create fails |
| Import source in new world | existing workspace registry + #562 exact source file | exact Markdown + world/document identity | #562 pending/import recovery | world remains if import fails |
| Create second source later | existing world record + normal source create | same W, new D | no world create required | n/a |
| Restart | registry + filesystem | same W and destinations | idempotent read | n/a |

## 6.5 Frontend destination model

Do not keep representing every destination as a bare `campaignId` string once managed worlds exist.

A bounded product model should distinguish at least:

```text
Existing campaign destination
  kind = campaign
  campaignId
  worldId
  label

Managed world destination
  kind = world
  worldId
  label
  Build compatibility campaignId = worldId

New world intent
  kind = new_world
  name
```

Exact TypeScript names are implementation-owned. The behavior is not.

This explicit destination model prevents two bad shortcuts:

1. adding arbitrary worlds to `WORLD_ID_BY_CAMPAIGN`;
2. pretending a new world is a new campaign.

## 6.6 Build UI contract

Both New Source and Import Source must support:

```text
Destination
  - existing current campaign/scope choices
  - managed worlds returned by server
  - New world…
```

When `New world…` is selected:

- show `World name`;
- require non-empty world name;
- keep source `Title` separate;
- Import still requires non-empty Markdown without modifying it;
- submit is one intentional operation from the GM's perspective;
- busy state covers world + source composition and blocks duplicate submit.

Do not expose:

- world IDs;
- source-root paths;
- graph bootstrap jargon;
- registry vocabulary.

## 6.7 Composition order

For a new-world New Source:

```text
validate form
→ create/reconcile world W
→ create workspace source D with {campaignId: W, worldId: W}
→ activate D
```

For a new-world Import Source:

```text
validate form
→ create/reconcile world W
→ create workspace source D with {campaignId: W, worldId: W}
→ #562 exact source_import
→ activate D
```

Do not combine world+source persistence into one new backend mega-endpoint. Existing source lifecycle remains authoritative and separately testable.

## 6.8 Retry separation

There are two distinct retained identities:

- world W — durable after successful world creation;
- pending source D — owned by #562 pending-import lifecycle if source creation/import progressed far enough.

Recovery must never conflate them.

Examples:

### A. World created, workspace POST failed

Retry should reuse W and perform the workspace create again. There is no D yet.

### B. World created, workspace D exists, source_import failed

Retry should reuse W and let #562 recover exact D.

### C. World create response ambiguous

Reconcile managed world registry first. Do not POST source until exact W is known.

### D. User changes destination after failure

Do not silently carry pending D from W1 into W2. Existing #562 scope mismatch must continue to fail closed or the pending lifecycle must be explicitly retired before a fresh source intent.

## 6.9 Existing source-root precondition remains valuable

Do **not** weaken workspace document creation to auto-create arbitrary world roots on every source POST.

The intended composition is:

```text
explicit GM action: create world
  → world-container service creates root
  → existing workspace source create verifies root exists
```

This preserves a clean authority distinction and prevents a typoed/forged source request from creating new worlds implicitly.

## 6.10 Managed world discovery

The UI discovers managed worlds from the new registry API, not by scanning `corpus/`.

Filesystem presence alone is not managed-world authority.

Existing legacy campaign choices continue through existing mechanisms. This PR does not require retroactively registering Eldyrwild as a managed world just to preserve current behavior.

## 6.11 Graph-context behavior

A dynamic managed world should not be inserted into static campaign map merely to make graph controls look available.

If Build's graph capability is invoked for a graphless/dynamically unmapped world, fail truthfully. If a minor UI guard is required to avoid a misleading error loop, stop and reconcile the exact path before changing graph authority code.

## 6.12 Source publication behavior

The world root may contain only `_dungeonbuddy` managed source storage after the first import. Existing #562 exclusions remain authoritative.

Creating W or D must not call:

- batch ingest;
- planner corpus publication;
- extraction/promotion;
- graph bootstrap;
- Hermes lexical discovery.

## 6.13 Error copy

Prefer human product language:

- `That world already exists.`
- `Could not create the world.`
- `The world was created, but the source could not be created.`
- `This source belongs to a different destination.`

Avoid exposing:

- registry token;
- source root path;
- `WORLD_ID_BY_CAMPAIGN`;
- Pydantic/internal schema names.

Technical details may remain in logs/tests.

---

# §7 Evidence required to merge

Every guarantee below is merge-blocking unless explicitly waived by the operator. A PR description cannot satisfy an evidence row.

## 7.1 Evidence ledger

| Guarantee / invariant clause | Owning boundary | Evidence class | Command / scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| World create persists one exact managed identity | world-container service | contract | `uv run pytest tests/test_world_container_registry.py` | create/list/reload same W/name/root | duplicate or transient identity |
| World root is server-owned | world-container service | adversarial | same test | client cannot supply path/id; safe derived root only | client path authority |
| Empty/invalid/collision/unmanaged-root fail closed | world-container service | adversarial | same test | 422/409 as appropriate; no record/path corruption | silent adoption/suffix/delete |
| Registry/root creation does not leave ordinary partial state | world-container service | failure injection | same test | mkdir failure no record; registry failure cleans only newly created empty root | record claims missing root or destructive rollback |
| Same create intent is retry-safe | world-container service | replay | same test | exact normalized world create reconciles one W | retry mints W2 |
| HTTP list/create is narrow | live route | contract | `uv run pytest tests/test_live_world_containers.py` | exact request/response fields; extras rejected according to repository policy | API widens to graph/campaign/path authority |
| Managed world root composes with #562 source contract | workspace registry | integration | `uv run pytest tests/test_workspace_document_registry.py` | source create succeeds only after managed root exists; missing root still fails closed | workspace create starts implicitly creating worlds |
| Existing campaign source creation remains unchanged | Build controller | regression | focused frontend controller tests | Longmont existing path still exact | dynamic-world work breaks existing campaign flow |
| New world → New Source uses W exactly | Build controller | state-machine | `pnpm exec vitest run src/buildSurface/useBuildWorkspaceDocumentController.test.ts` | one W then one D, `{worldId:W,campaignId:W}` | guessed campaign or duplicate W/D |
| New world → Import uses existing #562 source_import | Build controller | state-machine | same | one W, one D, existing import path; exact body preserved by existing tests | second writer or source rewrite |
| World success + source failure reuses W | Build controller | adversarial | same | retry creates/reuses source without W2 | duplicate world |
| World ambiguous response reconciles before source | Build controller | adversarial | same | list/reconcile exact W before proceeding | blind re-POST / duplicate |
| Pending #562 source remains destination-bound | Build controller | adversarial | same | W1 pending D cannot silently move to W2 | cross-world source corruption |
| UI exposes existing vs New world without IDs | Build component | component | `pnpm exec vitest run src/buildSurface/BuildDocumentCreateControl.test.tsx` | world-name validation, intentional submit, duplicate disabled | internal IDs/paths or accidental submit |
| API wire types remain exact | UI API | contract | `pnpm exec vitest run src/api/liveApi.test.ts` | list/create payloads exact | silent field drift |
| Existing #562 import/fidelity regressions stay green | source/import boundaries | regression | include existing focused source/import tests | exact source bytes and sealed Save unchanged | new-world composition weakens #562 |
| No graph/campaign bootstrap side effect | diff + owning tests | negative capability | inspect changed paths; server tests | no graph revision/map mutation from world create | world creation silently publishes graph/campaign |
| Type/build integration | UI package | compile/build | `pnpm exec tsc -b && pnpm build` | success | type/runtime build failure |
| No hidden path expansion | git diff | scope | `git diff --name-only 575dcdc47be6132dfe87d8f41bd7b862a63b64f7...HEAD` | only §4 + reconciled bounded exceptions | unrelated production path |
| Diff hygiene | git | hygiene | `git diff --check` | clean | whitespace/merge debris |

## 7.2 Required backend focused run

After focused iteration, run as one command:

```bash
uv run pytest \
  tests/test_world_container_registry.py \
  tests/test_live_world_containers.py \
  tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py \
  tests/test_live_tiptap_markdown_write.py \
  tests/test_source_artifact.py \
  tests/test_batch_ingest_managed_source_exclusion.py \
  tests/test_planner.py \
  tests/test_hermes_dungeonbuddy_plugin.py
```

The inherited failures previously waived for PR #562 are **not automatically waived for this PR**. Base/head comparison starts from `575dcdc4`. If the same base failures remain, record exact base/head parity and request a fresh operator waiver only if acceptance requires it.

## 7.3 Required frontend focused run

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/buildSurface/useBuildWorkspaceDocumentController.test.ts \
  src/buildSurface/BuildDocumentCreateControl.test.tsx \
  src/api/liveApi.test.ts \
  src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx
pnpm exec tsc -b
pnpm build
```

Add a BuildSurfaceContext/Page owning test only if UI wiring changes require it; record the exact addition in the evidence ledger.

## 7.4 Minimal live / dogfood proof

**Existing surface:** Build.  
**Starting condition:** choose a world name that does not exist in managed registry, hardcoded campaign mapping, or `corpus/<world>-markdown/` on the dogfood machine.

Suggested real one-shot test:

```text
World name: The Glass Orchard
Source title: The Glass Orchard — Convention One-Shot
```

Paste representative Markdown with headings, prose, a table, and at least one unsupported-by-editor construct so #562's exact-source behavior remains exercised.

Expected operator journey:

1. Open Build with no manual filesystem prep.
2. Choose `Import source`.
3. Select `New world`.
4. Enter `The Glass Orchard`.
5. Enter source title and paste Markdown.
6. Submit once.
7. Source opens in Build.
8. Record the created world display name and exact returned world ID from developer evidence, but the UI should not require the GM to see/use the ID.
9. Confirm the source record has `world_id=W` and world-level `campaign_id=W`.
10. Confirm target is beneath `corpus/W-markdown/_dungeonbuddy/sources/D/source.md`.
11. Hard reload and confirm same D/source.
12. Open `+ New source` or `Import source` again and select **The Glass Orchard** as an existing destination.
13. Create a second source and confirm it uses the same W without another world create.
14. Restart live-control or otherwise prove the managed-world list survives process restart.
15. Confirm no World Graph bootstrap/revision, extraction run, or legacy publication was created merely by creating W/importing D.

Capture:

- world record (W/name/root);
- first source D + world/campaign fields;
- second source identity using same W;
- hard-reload/restart note;
- concise UI observation/screenshot if practical;
- confirmation no manual `mkdir`, registry edit, or map edit was used;
- any dogfood friction as backlog notes, without expanding this PR unless it violates the invariant.

## 7.5 Baseline failure protocol

For any required command failing on base:

1. run/cite the same command or exact failing subset on base `575dcdc47be6132dfe87d8f41bd7b862a63b64f7` and HEAD;
2. state whether HEAD adds, removes, or preserves failures;
3. do not call a non-green gate green;
4. name any operator waiver explicitly;
5. waivers from earlier PRs do not silently transfer.

---

# §8 Required review handback

Every formal review handback begins with exactly one of:

```text
Review Cycle N — PASS
```

or

```text
Review Cycle N — CHANGES REQUESTED
```

where `N` is one greater than the preceding formal review cycle on **this PR**.

The handback must include:

1. Exact PR URL plus branch and head SHA.
2. Base `575dcdc47be6132dfe87d8f41bd7b862a63b64f7` or a deliberately reconciled replacement base.
3. §1 Mission and merge-ready invariant copied exactly.
4. Finding ledger from all prior review cycles with current closure state.
5. §7 evidence ledger: required evidence, produced result, and provenance.
6. Nano-commit list and discrete fix/proof story for each commit.
7. Actual changed paths and focused diff stat limited to §4/bounded exception.
8. Every required test/build/manual scenario and exact result.
9. Provenance of each result: author-local, independently rerun local, CI, or manual/dogfood.
10. Baseline failures and base/head comparison.
11. Operator waivers; `none` when none exist.
12. Paths outside §4; `none` or stop report.
13. Stop conditions encountered and resolution; `none` when none exist.
14. Successors still false: CR-U2 rich reader/assets, new-campaign creation, CR02 graph initialization/extraction, CR03 Hermes source follow-through.
15. Confirmation that #562 `source_import`/fidelity authority was not weakened.
16. Confirmation that world/source presence did not silently become graph/corpus publication.
17. Confirmation that static existing campaign→world graph mapping was not used as the managed-world registry.

A generic PR description is neither required nor sufficient.

---

# §9 Acceptance rubric

The reviewer accepts only when every applicable bullet is true and each behavioral claim names its §7 proof.

- [ ] Exactly one independently useful capability was delivered: creating/reusing a managed new world from Build source creation/import.
- [ ] The GM can perform the §7 new-world dogfood without CLI, manual filesystem creation, or code/map edits.
- [ ] One explicit new-world intent produces one durable exact world identity.
- [ ] Managed world identity survives hard reload and process restart.
- [ ] Human world name is shown in Build; world ID/path remain implementation detail in normal UX.
- [ ] Client cannot choose world ID or source-root path in the world-create contract.
- [ ] Empty/invalid world names fail closed.
- [ ] Same normalized create intent/retry does not mint a second world.
- [ ] Conflicting identity/name/root conditions fail closed without silent suffix/adoption/deletion.
- [ ] World create does not leave a registry record pointing at a missing root after ordinary failure.
- [ ] World creation does not recursively delete or overwrite a pre-existing path.
- [ ] The first source uses the exact created W.
- [ ] World-level Build source records use exact `world_id=W` and compatibility `campaign_id=W` without claiming campaign creation.
- [ ] Workspace source storage still comes from #562 server-derived target authority.
- [ ] Import still uses #562 one-time exact `source_import`; no second source writer exists.
- [ ] Source create/import failure after world success keeps and reuses W.
- [ ] #562 pending source recovery remains exact and destination-bound.
- [ ] Existing Longmont campaign source creation/import remains unchanged.
- [ ] A managed new world is available as an existing destination for later Build sources after reload.
- [ ] `WORLD_ID_BY_CAMPAIGN` was not turned into the managed world registry.
- [ ] No generic graph bootstrap was smuggled into world creation.
- [ ] No campaign was automatically created.
- [ ] No extraction/promotion/publication occurs merely because world/root/source exists.
- [ ] Existing managed `_dungeonbuddy` exclusions remain intact.
- [ ] No production path outside §4 changed without explicit reconciliation.
- [ ] Every formal review is numbered and increments the review count once.
- [ ] PR description was not treated as review/merge authority.
- [ ] Named successors remain unimplemented and unclaimed.

---

# Stop conditions

Stop and report rather than expanding if implementation discovers any of the following.

## World-authority stops

- A canonical general world-container/registry contract already exists and would conflict with the proposed registry.
- Correct new-world creation requires mutating World Graph state before a source can exist.
- A world cannot be represented as a world-level Build scope without creating a synthetic campaign that other product code treats as real campaign authority.
- Creating `corpus/<world>-markdown/` by itself causes a product ingest/index/publication path to treat the empty/new world as published authority.
- Existing source-root naming is not actually the stable boundary assumed by #562.

## Filesystem / persistence stops

- Safe create cannot be implemented without a destructive or broad recursive filesystem operation.
- Registry + source-root lifecycle cannot fail closed without inventing a general transaction framework.
- Existing unmanaged roots must be adopted/migrated to make the normal new-world path work.
- World creation would require relocating existing source files.

## Scope stops

- Correctness requires a campaign registry or new-campaign lifecycle.
- Correctness requires generalized graph bootstrap or changes to the Eldyrwild bootstrap.
- Correctness requires rich source rendering, asset serving, extraction, Hermes, statblock, Playable Layer, or Combat changes.
- A production path outside §4 is necessary and does not clearly establish the same CR-U1 invariant.
- Implementation begins changing #562 source-write semantics rather than composing with them.

## Evidence stops

- Any invariant clause cannot be tested at its owning boundary.
- New-world dogfood still requires manual `mkdir`, registry editing, or hardcoded mapping edits.
- A required base/head failure needs an operator decision before acceptance.
- The dogfood creates a world but cannot reuse it for a second Build source after reload.

Use this stop-report shape:

```text
CON-READY / BUILD stop report
Head SHA:
Observed repository fact:
Assumption contradicted:
Primary CR-U story affected:
Why the current slice cannot proceed safely:
Smallest decision needed from operator/steward:
Paths/evidence inspected:
What remains untouched:
```

---

# Successor notes

After this PR, re-anchor before dispatching again. The likely next CON-READY slice is:

## CR01C — Rich Source Reading (`CR-U2`)

GM-visible target:

> Open an imported source and read it as a real document with useful headings, paragraphs, emphasis, lists, tables, links, spacing, and typography, using the exact authoritative Markdown preserved by #562.

Do not assume TipTap edit projection is sufficient for reading: current authoring admission intentionally seals/loses presentation for unsupported constructs such as ordinary links/images/raw HTML. CR01C should read from authoritative source Markdown rather than weakening edit-save fidelity just to make reading look rich.

Also still available as a separate later product decision:

- create a new **campaign inside an existing world**;
- generic first-graph initialization for CR02.

Re-evaluate dogfood after merge before deciding their order.

---

# Handoff footer

```text
CON-READY Steward Re-anchor
Current main SHA: 575dcdc47be6132dfe87d8f41bd7b862a63b64f7
Merged predecessor: PR #562 — BUILD lossless existing-world Markdown import
Selected CR-U story: CR-U1
GM-visible capability now targeted: Create a new named world from Build and place/reuse sources in it
What is already true: existing-world lossless paste import, exact world-scoped source identity/path, reload-safe source recovery
What remains false: CR-U2 rich reader, new campaign creation, graph initialization/extraction, Hermes source follow-through
Authority boundary: world container owns named world + source root; workspace registry owns source identity/path; Tiptap/Canvas owns source bytes; graph/campaign authority unchanged
Implementation branch: agent/con-ready-build-new-world-source
Required proof: §7 owning tests + new-world one-shot dogfood
Real-material dogfood scenario: create The Glass Orchard from Import, hard reload, then create second source in same world
Stop conditions: see above
Known parallel work/collisions: none found at dispatch; re-check before implementation
Successor candidates: CR01C rich source reading; later new-campaign creation; CR02 generic graph initialization
```
