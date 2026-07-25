# Design — Threat + Statblock Authoring and Projection Workflow

**Status:** ACTIVE PRODUCT / INTEGRATION DESIGN
**Date:** 2026-07-21
**Repositories:** `Drakosfire/DungeonMindBuddy`, `Drakosfire/DungeonMindServer`
**DungeonBuddy implementation owner:** `Drakosfire/DungeonMindBuddy`
**DungeonMind statblock contract owner:** `Drakosfire/DungeonMindServer`
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)
**PR sequence:** [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)

## 1. Authority and purpose

This document defines the product workflow that joins DungeonBuddy's World Graph, Plan, Graph Review, Markdown canvas, and combat prototype to DungeonMindServer's statblock v1 contract.

It implements, but does not replace:

- [`DESIGN-authored-threat-statblock-domain-contract.md`](DESIGN-authored-threat-statblock-domain-contract.md), which owns the DungeonBuddy product-domain separation between Threat, statblock mechanics, placement, projection, and combat state;
- [`DECISION-statblock-contract-consumer-boundary.md`](DECISION-statblock-contract-consumer-boundary.md), which fixes the service ownership boundary;
- DungeonMindServer's `Docs/Design/DESIGN-dungeonbuddy-statblock-contract-v1.md`, which owns the canonical mechanics contract, validation, generation, identity, revisions, persistence, and CDN asset references;
- [`ARCHITECTURE-campaign-supergraph.md`](ARCHITECTURE-campaign-supergraph.md), which owns World Graph identity, contribution, projection, and agent-write semantics;
- [`CONTRACT-agent-tool-authored-prep-contributions-v0.md`](CONTRACT-agent-tool-authored-prep-contributions-v0.md), which owns `draft_only`, `preview_write`, and `confirm_commit` semantics.

When this document disagrees with those authorities, the owning document wins. This document's purpose is to remove implementation ambiguity at the seams between them.

## 2. Target experience

The GM can:

```text
select a World Graph campaign/focus lens in Plan
→ ask Hermes for grounded scene/faction/threat context
→ develop a new threat concept in conversation
→ paste or send the authored prose into the Statblock Workbench
→ save a ThreatDraft
→ generate a typed DungeonMind statblock candidate
→ inspect a styled semantic statblock
→ edit and validate the candidate
→ revise or regenerate it
→ persist an immutable statblock revision
→ preview and confirm creation of a Threat + exact revision binding in the World Graph
→ open the composed Threat Sheet from Plan or graph references
→ embed an exact revision-pinned statblock in Markdown
→ append later mechanics revisions without mutating earlier placements
→ add the exact revision to combat as a mutable CombatantInstance
→ generate, select, and bind CDN media without changing mechanics identity
```

The workflow must remain truthful at every intermediate state. A candidate is not accepted mechanics. Accepted mechanics are not graph truth. A graph Threat is not an active combatant. Media changes are not mechanics revisions.

## 3. Locked object model

### 3.1 User-facing composition

The product may present one composed **Threat Sheet**. The composed sheet is a projection, not a new canonical record.

```text
Threat Sheet projection
  = Threat or ThreatDraft identity
  + exact GeneratedStatblockCandidateV1 or StatblockRevisionResourceV1
  + ThreatStatblockBinding
  + selected media
  + placement/runtime actions allowed by the host surface
```

### 3.2 Durable ownership

| Object | Owner | Mutable? | Purpose |
|---|---|---:|---|
| `ThreatDraft` | DungeonBuddy | Yes, revisioned | Non-canonical authored concept and workflow state. |
| `GeneratedStatblockCandidateV1` | DungeonMindServer | No after creation; expires | Typed mechanical proposal awaiting judgment. |
| `StatblockResourceV1` | DungeonMindServer | Server metadata only | Stable logical mechanics identity. |
| `StatblockRevisionResourceV1` | DungeonMindServer | No | One immutable accepted mechanics truth. |
| `Threat` | DungeonBuddy World Graph | Through governed contributions | Campaign/world identity and relationships. |
| `ThreatStatblockBinding` | DungeonBuddy governed graph/write records | Through governed replacement | Exact relationship from a Threat to reusable mechanics. |
| `ThreatPlacement` | DungeonBuddy Plan/Play data | Yes | Contextual use in a plan, scene, or prepared encounter. |
| `CombatantSeed` | DungeonBuddy projection | No | Deterministic adapter output from one exact revision. |
| `CombatantInstance` | DungeonBuddy combat runtime | Yes | Current HP, initiative, conditions, resources, and encounter state. |
| `AssetRefV1` / media selection | DungeonMindServer reference + DungeonBuddy selection | Selection is mutable | CDN resource and campaign/form presentation choice. |

### 3.3 Forbidden collapses

Do not:

- store the complete statblock definition as the Threat graph node;
- make rendered Markdown authoritative mechanics;
- mutate accepted mechanics in place;
- let a generated candidate silently create graph truth;
- let a preferred/latest statblock revision silently rebase a Plan placement, Markdown embed, or combatant;
- write combat state back into a statblock revision;
- include media selection in the mechanics digest;
- treat Hermes chat history as campaign memory or authoring authority;
- make the browser a privileged DungeonMindServer client.

## 4. DungeonBuddy-local workflow records

These are DungeonBuddy-owned records. They are not additions to the canonical DungeonMind statblock schema.

### 4.1 `ThreatDraftV1`

```text
schema: dmb_threat_draft_v1

draft_id
version
world_id
campaign_id
focus?                         # session/prep lens, not identity ownership
name
slug_hint?
description
threat_kind
intended_roles[]
tags[]
generation_intent
  ruleset
  target_cr?
  complexity?
  must_include[]
  must_avoid[]
encounter_context
  party_level?
  party_size?
  terrain_notes[]
graph_context_snapshot
  graph_revision_id
  selected_node_ids[]
  admitted_source_anchor_ids[] # opaque pointers only
candidate_refs[]
accepted_mechanics_ref?
workflow_state
created_by
created_at
updated_at
```

Required behavior:

- A draft survives provider failure, validation failure, browser reload, and candidate expiry.
- Draft version increments on authored concept changes.
- Candidate generation records the exact draft version used.
- `graph_context_snapshot` preserves pointers and the graph revision used; it does not copy a hidden corpus dump into the draft.
- A draft may exist with no candidate and no accepted mechanics.

### 4.2 Candidate reference

```text
ThreatDraftCandidateRefV1
  candidate_id
  generated_from_draft_version
  request_id
  created_at
  expires_at
  status: active | superseded | rejected | expired | accepted_source
```

DungeonBuddy may cache a candidate response for UI reload, but the cached copy is not a mechanics authority and must retain the candidate ID and contract version.

### 4.3 Accepted mechanics reference

```text
AcceptedMechanicsRefV1
  provider: dungeonmind
  statblock_id
  revision_id
  contract
  contract_version
  definition_digest
  accepted_from_candidate_id?
  accepted_from_draft_version
  accepted_at
```

This may be attached to the draft before graph publication. That state is honestly named `mechanics_saved`, not `published` or `canonical_threat`.

### 4.4 Pending graph publication

```text
PendingThreatPublicationV1
  publication_id
  draft_id
  draft_version
  accepted_mechanics_ref
  expected_parent_graph_revision
  proposal_id
  proposal_version
  proposal_digest
  proposed_effect_summary
  status: prepared | stale | committed | failed
  last_error?
```

This record enables recovery when statblock persistence succeeds but graph publication does not.

## 5. Cross-service transport

### 5.1 Required direction

```text
DungeonBuddy browser
  → DungeonBuddy live-control/backend route
  → DungeonBuddy server-owned DungeonMind statblock client
  → authenticated DungeonMindServer internal v1 route
```

The browser never receives `DUNGEONMIND_INTERNAL_API_KEY` or equivalent credentials.

### 5.2 Generated client rule

DungeonMindServer's published OpenAPI remains contract authority. DungeonBuddy:

- vendors or generates transport types from the published artifact;
- proves fingerprint/byte identity as already established;
- may wrap generated types in a server-side client adapter;
- may create local view models only as explicit derived projections;
- must not create a second handwritten canonical statblock interface.

### 5.3 Configuration

DungeonBuddy server configuration must distinguish:

```text
DUNGEONMIND_STATBLOCKS_BASE_URL
DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY
DUNGEONMIND_STATBLOCKS_TIMEOUT_SECONDS
DUNGEONMIND_STATBLOCKS_ENABLED
```

Readiness must be honest:

- missing configuration: unavailable, not a mock success;
- Server liveness but generation disabled: read/validate capabilities may remain available if the Server advertises them;
- timeout/provider failure: typed downstream failure;
- internal authentication failure: configuration/operator error, not user validation failure.

## 6. Generation and candidate lifecycle

### 6.1 Generate

DungeonBuddy maps one exact draft version to `GenerateCandidateRequestV1`.

The first implementation uses explicit paste/send from the GM. “Create from this Hermes response” may be added later using the same draft API; it must not create a separate candidate path.

Default image behavior for the critical path is `generate_images=false`. Image generation is a later independent capability.

### 6.2 Candidate review

Candidate review composes:

```text
ThreatDraft identity and authored description
+ GeneratedStatblockCandidateV1.definition
+ validation_receipt
+ generation_receipt
+ asset_brief/assets/warnings
+ DungeonBuddy review state
```

The semantic renderer reads the structured definition. It must not use Markdown as the source of the displayed mechanics.

### 6.3 Edit and validate

The editor owns a complete `StatblockDefinitionV1_Input` working copy.

- Editing does not mutate the Server candidate.
- Preview validation calls `statblock-definitions:validate`.
- Error issues block acceptance.
- Warning issues remain visible and may be accepted if allowed by Server semantics.
- Editing typed mechanics or `rules_text` requires revalidation.
- Unsupported deterministic automation remains typed `human_adjudicated`; the UI does not pretend it is executable.

### 6.4 Revise/regenerate

Revision generation returns another candidate.

- Source may be the edited full definition or an exact accepted revision locator.
- Candidate lineage is DungeonBuddy review metadata plus Server generation provenance.
- Earlier candidates remain inspectable as superseded/rejected records where retained.
- Regeneration never overwrites an accepted revision or a draft version silently.

## 7. Acceptance ordering and failure semantics

### 7.1 Mechanics persistence comes first

Acceptance of mechanics calls DungeonMindServer first:

```text
candidate/edited definition
→ validate
→ POST create statblock or append revision
→ receive exact immutable revision locator and digest
```

A graph proposal must not reference a revision that has not been persisted.

### 7.2 Graph publication is a separate governed action

Creating/updating the Threat and binding uses DungeonBuddy's existing `preview_write` → proposal-bound `confirm_commit` path.

Graph publication includes:

- one authored source artifact or governed authored record for the Threat concept;
- one Threat node assertion or update;
- optional relationships explicitly selected for publication;
- one external statblock resource node assertion when absent;
- one `uses_statblock` edge carrying a typed binding state;
- required campaign, visibility, epistemic, temporal, and provenance metadata.

### 7.3 Truthful partial completion

| State | Meaning | Allowed next actions |
|---|---|---|
| `draft` | Authored concept only. | Generate, edit, discard. |
| `candidate_ready` | Typed proposal exists. | Edit, validate, revise, reject, accept mechanics. |
| `mechanics_saved` | Immutable revision exists; no graph publication claimed. | Prepare graph publication, open mechanics view, retry. |
| `publication_prepared` | Revision-bound graph proposal exists. | Confirm or refresh if stale. |
| `published` | Threat + binding committed at a graph revision. | Place, embed, edit through new revisions. |
| `publication_failed` | Mechanics remain valid; graph write failed or became stale. | Rebuild preview and reconfirm. |

No rollback deletes a valid statblock revision merely because graph publication failed. Orphaned/unbound mechanics are valid library resources and may be rebound later.

## 8. Graph representation

### 8.1 Threat identity

The Threat is the world/campaign graph object.

Recommended ID policy:

```text
threat:<stable-slug-or-generated-id>
```

Display name is not identity. Existing-object resolution must run before creating a new Threat when the workflow is publishing into an established campaign.

### 8.2 External statblock resource node

The current graph edge contract requires graph endpoints. The v1 integration therefore represents the logical statblock as a lightweight external-resource node, not as a copied mechanics object.

```text
node_id: external:dungeonmind:statblock:<statblock_id>
kind: external_resource
role: statblock
label: current display name projection
state.external_resource:
  provider: dungeonmind
  resource_type: statblock
  resource_id: <statblock_id>
  contract: dungeonmind.dungeonbuddy-statblocks
  contract_version: 1.0.0
```

This node supports traversal and reverse lookup. It does not contain `StatblockDefinitionV1`.

### 8.3 Binding edge

```text
Threat --uses_statblock--> External statblock resource
```

The edge carries typed state:

```text
state.threat_statblock_binding:
  binding_id
  provider: dungeonmind
  statblock_id
  selected_revision_id
  definition_digest
  role: primary | alternate | phase | encounter_variant | template
  revision_resolution_policy: pinned | campaign_preferred
  phase_key?
  variant_label?
```

Rules:

- A Plan placement, Markdown embed, and CombatantSeed always resolve to `pinned` with an exact revision.
- A Threat library view may use `campaign_preferred`, but the resolved projection must disclose the exact revision.
- Changing selected revision produces a governed binding replacement/update, not mutation of the Server revision.
- One statblock may serve several Threats; one Threat may have several bindings.

### 8.4 Authored-prep semantics

A newly designed threat normally publishes as:

```text
lifecycle: planned
epistemic_kind: plan
visibility: gm
campaign_scope: selected campaign
```

Placement may advance authored-prep lifecycle to `placed`. Neither generation nor placement proves `played`. `world_canon` remains an explicit promotion.

## 9. Projection registry and UI ownership

### 9.1 One renderer family

Create one semantic statblock renderer family with host policies for:

- candidate review;
- accepted full statblock;
- compact summary;
- Markdown/Tiptap embed;
- Plan reference projection;
- Play/combat drilldown;
- print/export.

Renderer inputs are typed candidate/revision definitions plus optional Threat/media context. Renderer CSS and design tokens belong to DungeonBuddy.

### 9.2 Workbench

The existing `StatblockWorkbenchModule` is the host seam, not the future domain contract.

When the typed candidate workbench becomes production-ready:

- remove mock generate/render from the normal workflow;
- remove corpus Markdown promotion/retrieval activation controls from the normal workflow;
- retain a predecessor only if a named consumer remains;
- do not introduce a second Plan-specific statblock module.

### 9.3 Surface action policy

| Surface | Primary statblock actions |
|---|---|
| Plan | Generate/review, open Threat Sheet, embed, place, open graph publication/review. |
| Graph Review / Ingest | Review/confirm Threat and binding graph effects; identity correction. |
| Play | Open exact revision, add to combat, inspect encounter placement. |
| Build | Later durable authoring/library affordances; does not block the Plan slice. |
| Agent Interaction | Read context; draft/propose via typed tools only; no privileged commit. |

## 10. Markdown and Tiptap embed

### 10.1 Canonical stored locator

A live embed stores a typed locator, not copied statblock JSON or Markdown:

```markdown
:::dmb-statblock{threat="threat:example" statblock="sb_abc" revision="rev_def" view="full"}
:::
```

Tiptap stores equivalent node attributes.

Required attributes:

```text
provider=dungeonmind
statblock_id
revision_id
view=summary|full
threat_id?       # optional composition context
```

### 10.2 Resolution behavior

- Resolve the exact revision.
- Never select latest for a pinned embed.
- Missing/unavailable revision renders an honest unresolved block retaining the locator.
- A newer revision may produce a non-destructive “update available” affordance.
- Portable export may expand the embed to snapshot Markdown/HTML, clearly marked as an export snapshot.

## 11. Revision workflow

Accepted revision editing is:

```text
open exact revision
→ fork a complete editable definition candidate
→ edit and validate
→ optionally revise through model assistance
→ append immutable revision with exact parent_revision_id
→ compare old/new
→ explicitly update selected binding or placement
```

Concurrency rules:

- append requires the expected parent revision;
- stale parent fails closed;
- no silent rebase;
- existing placements, embeds, and combatants retain their pinned revision;
- upgrading one placement does not change every use of the logical statblock.

## 12. Combat integration

### 12.1 Adapter

One exact `StatblockRevisionResourceV1` derives one deterministic `CombatantSeedV1`:

```text
provider
statblock_id
revision_id
definition_digest
name
armor_class
max_hit_points
hit_point_formula?
initiative_modifier
speed_summary
challenge_rating
human_adjudicated_element_keys[]
```

### 12.2 Instance

The existing combat tracker receives the seed and creates a `CombatantInstance` with mutable encounter state.

- Store the exact locator and a bounded operational snapshot.
- Full drilldown resolves the exact revision.
- Reload/export must not depend on corpus Markdown paths.
- Current HP, initiative, conditions, and notes never modify the revision.
- Combat remains a Play mode/lens, not a peer graph or mechanics authority.

## 13. Media

### 13.1 Images

The first media capability uses existing `AssetRefV1` and `AssetBindingV1`.

- Candidate image generation is optional and non-blocking.
- DungeonMindServer owns generation/storage and durable CDN references.
- DungeonBuddy owns selection, role, Threat/form binding, crop/focal metadata if locally supported, and surface display.
- Asset failures do not invalidate otherwise valid mechanics.
- Image selection does not change `definition_digest`.

### 13.2 3D models

`AssetRefV1` is image-specific and must not be quietly widened.

3D support requires a separate later contract covering at least:

```text
media_kind
model MIME/format
canonical file
preview image
variants/LOD
source asset/derivation lineage
generation job state
mesh/size validation where relevant
CDN/storage locator
presentation role
```

No initial statblock workflow PR may claim 3D support by storing a model URL in an image field.

## 14. Observability and audit

Every cross-service operation should bind a stable correlation/request ID.

Minimum useful fields:

```text
operation
request_id / idempotency_key
world_id / campaign_id / focus
threat_draft_id + version
candidate_id
statblock_id / revision_id / definition_digest
graph proposal id / digest / expected parent
graph committed revision
outcome
latency and typed failure category
```

Do not log internal API keys, full hidden prompts, or unbounded authored prose.

## 15. Security boundaries

- Internal service credentials remain server-side.
- All IDs/locators are validated before use.
- Exact revision reads do not accept arbitrary URLs or filesystem paths.
- Media deletion remains provider-owned/record-owned; DungeonBuddy does not delete by user-supplied CDN URL.
- Request and response body limits remain bounded.
- Draft prose and generation context are treated as user content, not executable instructions to the backend.
- Graph visibility/admissibility remains enforced when context is gathered or projected.

## 16. Demolition map

The new workflow has no backwards-compatibility obligation to preserve these as product architecture:

- mock statblock generation/render commands;
- Markdown-first `StatblockDraftArtifactView` as canonical mechanics;
- corpus promotion as the way a new statblock becomes usable;
- retrieval activation as the way an accepted statblock is opened;
- generated-statblock lookup by corpus artifact path;
- combat insertion from pending Markdown or corpus filename;
- duplicated handwritten statblock transport types.

Each replacement PR must remove its predecessor path when the replacement becomes production-ready or name the exact remaining consumer and deletion owner.

## 17. End-to-end acceptance

The workstream is complete when a GM can execute this real slice:

1. Select Campaign 2 and a scene/session focus in Plan.
2. Ask Hermes about a scene and the Shepherds' Flock; inspect graph-grounded context.
3. Paste the designed creature prose into the workbench and save a draft.
4. Generate and inspect a typed candidate.
5. Edit one mechanic and validate it.
6. Persist an immutable statblock revision.
7. Preview and confirm a `planned`, GM-visible Threat and exact statblock binding into the World Graph.
8. Reload and open the composed Threat Sheet from the graph at the committed revision.
9. Embed the exact statblock revision into the Plan Markdown document and reload it.
10. Append a new mechanics revision without changing the existing embed.
11. Add the pinned revision to combat; change HP and conditions without changing the revision.
12. Generate/select an image asset and see it on the Threat Sheet without changing the mechanics digest.

3D media is explicitly outside this completion gate.
