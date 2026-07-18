# Decision: DungeonMind Statblock Contract Consumer Boundary

**Status:** ACTIVE DECISION  
**Created:** 2026-07-17  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Authoritative contract owner:** `Drakosfire/DungeonMindServer`  
**Authoritative contract document:** `Docs/Design/DESIGN-dungeonbuddy-statblock-contract-v1.md`  
**DungeonMindServer decision commit:** `5455fb50a398dbc8965ceec494ab0dd0b356edb9`

## 1. Purpose

This document fixes DungeonBuddy's side of the statblock boundary after the detailed contract
design moved to its correct owner: DungeonMindServer.

It narrows and supersedes the schema, route, generation-envelope, validation, and revision-store
ownership portions of:

```text
Docs/Design/DESIGN-authored-threat-statblock-domain-contract.md
```

That earlier document remains authoritative for DungeonBuddy's product-domain concerns:

- `ThreatDraft`;
- `Threat`;
- graph authorship;
- Threat-to-statblock bindings;
- summary and full projections;
- Plan, scene, and Play placement;
- combat runtime state.

DungeonBuddy does not own, duplicate, or independently evolve the statblock mechanics schema.

## 2. Locked boundary

```text
DungeonMindServer
  owns the canonical statblock contract, generation, validation, identity, revisions,
  digests, persistence, and CDN asset references

DungeonBuddy
  owns authored Threat identity, graph relationships, human review, projections,
  campaign placements, preferred revision selection, and combat runtime state
```

DungeonBuddy is a first-party extension of DungeonMind. The relationship is not an integration
between unrelated products with competing contract authorities.

## 3. Authoring workflow

```text
GM brainstorms with DungeonBuddy
→ DungeonBuddy creates or updates a ThreatDraft
→ DungeonBuddy backend sends authored description and generation intent to DungeonMindServer
→ DungeonMindServer returns a GeneratedStatblockCandidateV1
→ DungeonBuddy projects the candidate for review
→ GM edits, regenerates, accepts, or rejects
→ DungeonBuddy submits the complete accepted StatblockDefinitionV1
→ DungeonMindServer persists an immutable StatblockRevisionResourceV1
→ DungeonBuddy authors or updates the Threat graph node
→ DungeonBuddy creates a binding to the exact statblock revision
```

Generation failure does not erase the ThreatDraft. A generated candidate does not silently
become graph truth or accepted mechanics.

## 4. DungeonBuddy-owned objects

### 4.1 `ThreatDraft`

Mutable authored concept during brainstorming.

```text
ThreatDraft
  draft_id
  name
  description
  threat_kind
  intended_role
  tags
  image selections
  generation intent
  candidate locators
  authored provenance
```

A ThreatDraft may exist without mechanics.

### 4.2 `Threat`

Durable graph-addressable world object.

```text
Threat
  threat_id
  name
  canonical campaign description
  threat_kind
  tags
  image bindings
  graph relationships
  statblock bindings
  contribution provenance
```

The graph node stores world identity and relationships. It does not embed the full canonical
statblock or mutable combat state.

### 4.3 `ThreatStatblockBinding`

Typed many-to-many relation between world identity and reusable mechanics.

```text
ThreatStatblockBinding
  binding_id
  threat_id
  provider: dungeonmind
  statblock_id
  selected_revision_id
  role
  revision_resolution_policy
  phase or variant metadata
  provenance
```

Possible roles include:

```text
primary
alternate
phase
encounter_variant
template
```

One Threat may use several statblocks. Several Threats may share one statblock.

### 4.4 `ThreatPlacement`

Contextual use of a Threat in a Plan, scene, prepared encounter, or Play surface.

It may own:

```text
quantity
role in the scene
trigger or arrival timing
visibility
GM notes
encounter-local adjustments
exact pinned statblock revision
```

### 4.5 `CombatantInstance`

Mutable encounter state created from an exact accepted revision.

```text
CombatantInstance
  combatant_instance_id
  statblock_id
  revision_id
  current_hp
  temporary_hp
  initiative
  conditions
  resources
  position
  turn state
  encounter-local notes and overrides
```

No runtime field writes back into the statblock revision.

## 5. DungeonMindServer-owned objects consumed by DungeonBuddy

DungeonBuddy consumes, but does not redefine:

```text
StatblockDefinitionV1
GeneratedStatblockCandidateV1
StatblockResourceV1
StatblockRevisionResourceV1
ValidationReceiptV1
AssetRefV1
```

Their exact fields, rule-element union, validation semantics, canonicalization, identities,
routes, and errors are defined in DungeonMindServer.

DungeonBuddy should consume generated TypeScript DTOs or a generated client from the
DungeonMindServer OpenAPI contract. Hand-maintained duplicate interfaces are prohibited for
the canonical transport and mechanics types.

Local view models are allowed when they are explicitly derived projections.

## 6. Review and editing

DungeonBuddy owns the review experience and decision, not mechanics validation authority.

The review projection composes:

```text
ThreatDraft identity and description
+ GeneratedStatblockCandidateV1 definition
+ validation issues
+ candidate assets and asset brief
+ DungeonBuddy review state and actions
```

The GM may:

```text
edit the ThreatDraft
edit proposed mechanics
regenerate from revised intent
request a variant
select or change images
accept
reject
```

A DungeonBuddy mechanics edit operates on the complete `StatblockDefinitionV1` generated from
DungeonMindServer's contract types. Acceptance sends the complete definition back to
DungeonMindServer for validation and immutable revision creation.

DungeonBuddy does not patch untyped JSON fields or persist a local mechanics fork.

## 7. Projection ownership

DungeonBuddy owns semantic renderers and visual styling for:

```text
identity chip
summary card
full statblock
review editor
Plan reference
scene reference
Play reference
combat drilldown
print view
agent context
embedding document
```

The source is the exact `StatblockDefinitionV1` in an accepted candidate or revision.
DungeonMindServer does not need to return canonical Markdown or copied combat defaults.

Renderer changes do not create mechanics revisions.

### 7.1 Summary composition

A compact Threat/statblock summary may combine:

```text
Threat identity summary
  authored campaign-world concept

mechanical digest
  deterministic values such as size, type, AC, HP, CR, and movement

tactical summary
  generated or edited table-use guidance with explicit provenance
```

These meanings should not collapse into one ambiguous `summary` field.

### 7.2 Full view

The full view renders structured headers and the accepted rule-element `rules_text`. Typed
mechanics support controls, summaries, search, and combat interaction. DungeonBuddy must not
silently rewrite accepted rules text from its own local interpretation.

## 8. Revision resolution

```text
Threat library or identity view
  may follow the campaign-selected preferred revision

Plan placement
  pins statblock_id + revision_id

scene placement
  pins statblock_id + revision_id

prepared encounter
  pins statblock_id + revision_id

CombatantInstance
  always pins statblock_id + revision_id
```

When a newer revision exists, DungeonBuddy should present an explicit decision:

```text
compare
update this placement
keep pinned revision
```

No prepared or live context silently rebases to the latest revision.

## 9. Images

DungeonMindServer provides CDN-backed `AssetRefV1` values and owns the storage contract.

DungeonBuddy owns campaign selection and placement:

```text
Threat portrait or token
  normally bound to the Threat

form-, phase-, or statblock-specific art
  may be bound through the statblock revision or ThreatStatblockBinding
```

Changing preferred art, crop, alt text, or projection role does not create a mechanics
revision.

## 10. Combat tracker adaptation

The existing combat tracker is valuable predecessor implementation and should be upgraded
before any required surface rebuild.

The first adapter derives from one exact revision:

```text
name
default armor class
maximum hit points
initiative modifier
speed summary
statblock_id
revision_id
```

The tracker stores a small operational snapshot alongside the exact locator so live state is
stable during play and survives export/reload. The full statblock drilldown resolves through
the exact revision.

DungeonBuddy does not accept a Markdown blob as the durable combat mechanics source.

## 11. Graph behavior

The Threat is the graph node. The statblock remains a reusable external mechanics resource.

```text
Threat node
  --uses_statblock--> exact DungeonMind statblock revision locator
```

The graph may denormalize compact display/index fields, but those fields are projections and
must retain their source revision locator.

A generic statblock may serve several graph nodes. A graph node may select several statblocks
for forms, phases, variants, or templates.

## 12. Transport and authentication

The browser does not call privileged DungeonMindServer internal routes.

```text
DungeonBuddy UI
→ DungeonBuddy backend/tool boundary
→ authenticated DungeonMindServer internal contract route
```

DungeonBuddy must preserve stable request IDs and idempotency keys across retries. It must
surface typed failures rather than converting every error into a generic generation failure.

## 13. No backwards-compatibility obligation

DungeonBuddy's new integration does not depend on:

- old `StatBlockDetails` JSON;
- v2 command-board draft envelopes;
- Markdown-first statblocks;
- `CombatDefaults` copies;
- current StatBlockGenerator project/session persistence;
- old browser routes;
- current statblock path references in the combat prototype.

Existing routes may continue serving their current clients until separately retired. The
DungeonBuddy integration is built against the new DungeonMindServer contract only.

## 14. Consumer implementation ladder

### A. Generated contract client

Generate DungeonBuddy transport types/client from DungeonMindServer OpenAPI.

### B. ThreatDraft generation tool

Send authored description and intent through the DungeonBuddy backend.

### C. Candidate review projection

Render typed candidate mechanics, validation, assets, and review actions.

### D. Acceptance and binding

Persist through DungeonMindServer, then create/update Threat and binding without claiming
success on partial completion.

### E. Read projections

Implement summary and full statblock views from exact revisions.

### F. Combat adapter

Add an accepted revision to the existing tracker and preserve exact revision identity.

### G. Placement support

Place pinned Threat/statblock references into Plans, scenes, prepared encounters, and Play.

### H. Revision workflow

Compare, edit, validate, append, and deliberately upgrade placements.

## 15. Consumer acceptance criteria

DungeonBuddy satisfies this boundary when:

- it has no independent canonical statblock schema;
- generated contract types come from DungeonMindServer;
- a ThreatDraft survives failed generation;
- a candidate is reviewable without becoming graph truth;
- acceptance produces an exact immutable revision locator;
- the Threat graph node and statblock revision remain distinct;
- summary and full views derive from the same revision;
- the combat tracker accepts a revision without Markdown as canonical storage;
- Plan, scene, and combat references remain pinned;
- one statblock can serve several Threats and one Threat can use several statblocks;
- runtime combat state never mutates the revision;
- unsupported automation is presented honestly through the contract's human-adjudicated type.

## 16. Authority rule

When this document and the earlier authored-threat design discuss the exact statblock schema,
route family, generation envelope, validation, canonicalization, or revision persistence, the
DungeonMindServer contract document is authoritative.

When they discuss ThreatDraft, Threat, graph authorship, bindings, campaign placement,
DungeonBuddy projections, or combat runtime state, DungeonBuddy's domain documents are
authoritative.
