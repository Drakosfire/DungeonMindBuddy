# HANDOFF — V6.2 vNext complete-object read adaptation + World-object DTO preservation

**Status:** COMPLETE
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Buddy base:** `9473244f57e7845928fc47225fd08863ea85804b`  
**DungeonMind current main at design:** `54a419f99057d96e0c4e7620d8bd8ccc6816fb62`  
**Buddy DungeonMind runtime pin:** `0f709d76fdc53bac9c9258d1751463ae2c76ca71`  
**V6.1 implementation:** PR #749, head `9e2abbae42acc847b214460644caef2448637495`, review `5312320001`, merge `7a63c8b39937776ddede24d3d76001ef59fd37c4`  
**Kernel prerequisite:** `V6_K1_COMPLETE_ENTITY_AUTHORIZED_ALIASES_ACCEPTED` — PR #76, head `91d2ebaf8aadf512a26ac209cfe8f6414063e732`, review `5321738653`, merge `f3738f3af3e3c8e204668a3d87d240a32c0d3988`  
**Canonical witness:** `tests/fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json`  
**Suggested branch:** `vnext/v6-2-complete-object-read-adaptation`  
**Suggested PR title:** `VNEXT: adapt complete entity reads to World-object DTO`  
**Acceptance token:** `V6_2_VNEXT_COMPLETE_OBJECT_DTO_PRESERVATION_ACCEPTED`  
**PR:** #767
**Accepted substantive head:** `69fedb9918c602a92af32d74453a2b00ed2b73da`
**Steward review:** `5324647959` — `V6_2_SUBSTANTIVE_PASS`
**Merge:** `f30b4c906bb179b25f00207c40cb38c0debdc264` — exact reviewed substantive implementation
**Disposition:** `V6_2_VNEXT_COMPLETE_OBJECT_DTO_PRESERVATION_ACCEPTED`
**Successor:** V6.3 — Buddy governed-write adaptation / publication mapping

## 1. Primary question

> Can DungeonMindBuddy reconstruct its existing selected complete World-object DTO from one exact native-vNext complete-entity read without old World-shaped DungeonMind read APIs, raw alias authority access, full-graph projection, or production cutover?

A PASS proves this dormant path:

```text
WorldGraphObjectProjectionRequest
+ exact ParsedKnowledgeRevision
+ pinned KnowledgeSourceReader
+ explicit read identity
        ↓
V6.1 DungeonBuddyVNextProjectionInput
        ↓
build_dungeonbuddy_read_context(...)
        ↓
EntityReadService.get_complete_entity(...)
        ↓
bounded related get_entity(...) hydration
        ↓
Buddy-owned presentation/provenance mapping
        ↓
WorldGraphObjectProjectionResult
```

This PR does not select live authority and does not replace the current production route.

## 2. First commit — control-plane cleanup

### Seal V6.1

`Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md` still says ACTIVE.

Update it to:

```text
Status: COMPLETE
PR: #749
accepted substantive head: 9e2abbae42acc847b214460644caef2448637495
review: 5312320001
merge: 7a63c8b39937776ddede24d3d76001ef59fd37c4
disposition: V6_1_DUNGEONBUDDY_DOMAIN_RUNTIME_ACCEPTED
successor: V6.2
```

### Record V6.K1

The new V6.2 handoff records:

```text
V6_K1_COMPLETE_ENTITY_AUTHORIZED_ALIASES_ACCEPTED
```

with the PR #76 anchors above.

### Correct the dependency comment

`pyproject.toml` already pins DungeonMind at `0f709d76...`, which contains V6.K1 and semantic-profile V3. Its nearby comment still describes the pin as PR #75/V5-era runtime.

Fix the comment only.

Do not repin merely for PR #78; PR #78 is docs/test finalization and V6.2 needs no new runtime from it.

No `uv.lock` change is expected.

## 3. Ownership

This adapter is Buddy-owned.

Buddy owns:

```text
dnd5e:name / classification / summary meaning
Buddy claim-mode presentation
campaign-scope presentation
GM/player product vocabulary
fictional-time presentation
source campaign/session metadata interpretation
WorldGraphObjectProjectionResult
```

Kernel owns:

```text
admitted assertions
authorized aliases
related endpoints
source/evidence validity
exact revision identity
```

WorldKeeper does not own this adapter and must not learn Buddy predicate/profile/presentation vocabulary.

## 4. Dormant adapter seam

Prefer a new module such as:

```text
apps/live_control_server/integrations/dungeonmind/vnext_complete_object.py
```

Provide an entry point conceptually:

```python
project_complete_world_object_vnext(
    *,
    parsed_revision: ParsedKnowledgeRevision,
    source_reader: KnowledgeSourceReader,
    request: WorldGraphObjectProjectionRequest,
    read_identity: DungeonBuddyVNextReadIdentity,
) -> WorldGraphObjectProjectionResult
```

Add a frozen read-identity value object:

```text
space_id
revision_id
head_revision_id
is_head
```

It supplies metadata for an already-selected revision; it does not choose authority.

Fail closed unless:

```text
read_identity.space_id == parsed_revision.space_id
read_identity.revision_id == parsed_revision.revision_id
request.world_id == parsed_revision.space_id
request.revision_pin is None OR request.revision_pin == parsed_revision.revision_id
```

Do not query a live head.

## 5. Complete-object request semantics

Complete selected-object truth remains cross-campaign:

```text
scope_mode = "world"
```

`request.campaign_id` and session focus are presentation metadata only.

Role maps exact:

```text
gm     → gm
player → player
```

Anything else fails closed.

Always pin V6.1 input to `parsed_revision.revision_id`.

For session focus:

```text
session_id = request.focus.session_id
focus campaign = request.focus.campaign_id OR request.campaign_id
```

Focus must not alter admission.

## 6. Kernel read shape

Build the V6.1 context and call exactly one:

```text
EntityReadService.get_complete_entity(context, request.node_id)
```

For every `related_entity` returned, Buddy may call:

```text
EntityReadService.get_entity(context, related_entity_id)
```

only to hydrate display name/classification/summary.

Required work shape:

```text
1 complete selected read
+ at most N basic related reads
```

where N is the number of related entities returned by the selected read.

Do not scan unrelated entities. Do not recursively expand neighbors.

Do not use:

```text
WorldGraphProjectionService
WorldGraphRetrievalService
WorldGraphProjectionRequestV2
ScopeModeV2
VersionedUnionGraphSnapshotReader
full vNext projection
```

## 7. No fabricated authority rows

Do not synthesize fake assertions for entity existence or aliases.

```text
Entity → found + node identity
CompleteEntityLookupResult.aliases → node.aliases
```

Only real vNext assertions may enter:

```text
result.assertions
result.relationships
```

No fake `existence` or `alias` assertion IDs.

Selected aliases must come only from:

```text
CompleteEntityLookupResult.aliases
```

The adapter must not access raw:

```text
aliases_by_id
alias_exact_index
aliases_by_entity
```

## 8. Selected node mapping

Use admitted selected-subject assertions only.

### Label

`dnd5e:name`, literal string:

```text
0 distinct values → entity_id display fallback
1 distinct value  → that value
>1 distinct values → typed ambiguity error
```

### Kind

`dnd5e:classification`, term-ref:

```text
0 distinct values → "entity"
1 distinct value  → wire term
>1 distinct values → typed ambiguity error
```

Wire terms strip only `dnd5e:`:

```text
dnd5e:npc      → npc
dnd5e:location → location
```

Do not strip arbitrary namespaces.

### Role

```text
role = kind
```

### Summary

`dnd5e:summary`, literal string:

```text
0 values → None
1 distinct value → that value
>1 distinct values → None
```

All summary assertions remain in the assertion ledger; do not choose a winner.

### Aliases

```text
node.aliases = alias_text ordered by alias_id
```

### Node campaign scope

```text
node.campaign_scope = None
```

A vNext Entity is space-global identity. Campaign scope belongs to assertions.

## 9. Assertion mapping

Partition selected complete-read assertions:

```text
entity_ref → relationship
everything else → WorldGraphObjectProjectionAssertion
```

Related-node hydration assertions do not enter the selected object's assertion ledger.

Map assertion kind:

```text
dnd5e:summary → "summary"
otherwise      → "property"
```

For normal properties:

```text
predicate = wire predicate
label = full qualified predicate
```

For summary:

```text
predicate = "summary"
label = "summary"
```

Values:

```text
literal string:
  text_value = exact string
  value = {}

literal object:
  value = thawed object
  text_value = None

term_ref:
  text_value = wire term
  value = {"term": exact qualified term}
```

If the current DTO cannot represent a literal losslessly, fail closed. Do not stringify arbitrary lists/numbers/bools.

## 10. Buddy metadata presentation

### Campaign scope

```text
0 dungeonbuddy.scope:campaign bindings → None
1 binding → exact value
>1 bindings → fail closed
```

### Visibility

Map to existing product vocabulary based on whether player-only labels satisfy the vNext requirement:

```text
public → player
labels_any containing player → player
labels_any gm-only → gm
labels_all containing gm → gm
labels_all player-only → player
```

This is presentation only; Kernel admission already authorized the assertion.

### Epistemic kind

Use Buddy claim mode, not generic derivation basis:

```text
dungeonbuddy.claim:fact           → fact
dungeonbuddy.claim:belief         → belief
dungeonbuddy.claim:rumor          → rumor
dungeonbuddy.claim:plan           → plan
dungeonbuddy.claim:observed_event → observed_event
```

Do not map `asserted/inferred/speculative` into the product field.

### Temporal scope

Preserve vNext semantics:

```text
timeless    → {"kind":"timeless"}
unknown     → {"kind":"unknown"}
utc_interval→ {"kind":"utc_interval", ...}
domain_ref  → {"kind":"domain_ref", "schema": exact term, "payload": exact thawed payload}
```

## 11. Relationship mapping

Every admitted entity-ref assertion touching the selected entity becomes a product relationship:

```text
edge_id        = assertion_id
source_node_id = assertion.subject_entity_id
target_node_id = assertion.value.entity_id
predicate      = wire predicate
label          = wire predicate with "_" → " "
```

Direction relative to selected:

```text
selected == source → outgoing
selected == target → incoming
```

Preserve:

```text
visibility
campaign_scope
epistemic_kind
temporal_scope
evidence_ref_ids
source_artifact_ids
```

Relationship `session_ids` come only from admitted evidence source metadata, never by parsing IDs.

## 12. Coherent provenance presentation join

Kernel admission has already decided membership, but Buddy needs source-domain metadata for presentation.

Use the already-pinned:

```text
context.source_reader
```

for one targeted snapshot over only artifact/revision IDs referenced by the admitted result.

Do not open a fresh source epoch and do not use this join to recover excluded knowledge.

Interpret Buddy-owned:

```text
dungeonbuddy.source:context_v1
```

as:

```text
campaign_id: nonblank string
session_id: optional nonblank string
```

Conflicting duplicate entries fail closed. Missing entry means unknown presentation campaign/session.

Map source classification:

```text
dungeonbuddy.source:recap → recap
```

Strip only `dungeonbuddy.source:`.

## 13. Source bindings

For every returned evidence ref build the existing:

```text
WorldGraphObjectProjectionSourceBinding
```

with:

```text
evidence_ref_id
source_artifact_id
source_revision_id
content_sha256
source_span_ref_id
source_domain
session_id
excerpt = None
```

Initial status:

```text
missing revision digest → source_binding_unavailable
digest + no source_span_ref_id → no_source_span
digest + source_span_ref_id → span_unresolvable
```

Do not read APP-STATE source bodies or filesystem content in V6.2.

Do not parse `locator` into a source-span identity.

## 14. Focus presentation

Evidence matches focus iff:

```text
session_id matches
AND
if focus campaign exists, source campaign matches
```

Use only for:

```text
evidence_badge.is_focus_session_evidence
node.anchored_to_focus_session
adjacency.anchored_to_focus_session
```

Prove the same request with/without focus yields identical:

```text
assertion IDs
relationship IDs
aliases
source bindings
```

Only presentation flags may differ.

## 15. Node evidence / adjacency

Selected node evidence is the union of support for:

```text
selected-subject non-relationship assertions
authorized selected aliases
```

Relationship evidence belongs on relationships/adjacency.

Create one `WorldGraphProjectionAdjacencyCandidate` per selected relationship using the related entity's hydrated display values.

No source excerpts.

For this dormant adapter:

```text
suggested_expansions = []
```

Do not invent ranking semantics.

## 16. Related-node boundary

For each related entity, use only its basic `get_entity()` result to populate:

```text
label
kind
role
summary
evidence presentation
adjacency back to selected
```

Set:

```text
related_node.aliases = []
```

Do not raw-scan aliases and do not recursively call complete reads only to fill decorative related aliases.

If cutover evidence later proves related aliases are required, handle that as a separate bounded decision.

## 17. Snapshot / completeness / fingerprint

Snapshot:

```text
world_id         = read_identity.space_id
campaign_id      = request.campaign_id
revision_id      = read_identity.revision_id
head_revision_id = read_identity.head_revision_id
is_head          = read_identity.is_head
focus            = request.focus
admissibility    = request.admissibility
scope_mode       = "world"
```

Completeness maps directly from Kernel. Do not turn partial into complete.

Reuse unchanged:

```text
object_projection_semantic_fingerprint(...)
```

Do not create a second product fingerprint.

## 18. Canonical V2 witness

Use the existing V2 fixture and select:

```text
entity:npc:brennan-tallow
```

GM expectation:

```text
found = true
node.label = Brennan Tallow
node.kind = npc
node.role = npc
node.aliases = ["Old Tallow"]
node.summary = Secretly smuggles Mireward night-root to the docks
node.campaign_scope = None

relationship:
  edge_id = as:brennan-located-in-mireward
  source = entity:npc:brennan-tallow
  target = entity:loc:mireward
  predicate = located_in
  direction = outgoing
  campaign_scope = campaign-longmont
  epistemic_kind = observed_event

related node entity:loc:mireward:
  kind = location

real assertion ledger includes:
  as:brennan-name
  as:brennan-classification
  as:brennan-secret-plan

does not invent:
  existence
  alias

retracted rumor absent

source:
  domain = recap
  campaign = campaign-longmont
  session = session-28
  content digest preserved
```

Player expectation:

```text
name visible
classification visible
authorized alias visible
located_in visible
GM-only provisional secret plan absent
retracted rumor absent
```

Do not add a second product filter after Kernel admission.

## 19. Required negative tests

Prove fail-closed behavior for:

```text
revision/read-identity mismatch
unknown admissibility
two distinct admitted names
two distinct admitted classifications
unsupported literal shape
conflicting dungeonbuddy.source:context_v1 metadata
```

Missing selected object returns normal:

```text
found=false
node=None
resolved_node_id=None
```

with exact snapshot identity.

## 20. Optional V3 regression

If inexpensive, add one small regression for an already-admitted:

```text
dungeonbuddy.custom:<predicate>
entity_ref
```

under the opt-in V3 Buddy profile.

It should map as an ordinary relationship without special Kernel logic.

Do not make V3 required for V6.2 and do not create a V2→V3 transition.

## 21. Production path remains frozen

Prefer no edits to:

```text
apps/live_control_server/services/world_graph_object_projection.py
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
current routes
authority binder
frontend contracts
```

V6.2 is a dormant alternate implementation only.

## 22. Expected changed surface

Approximately:

```text
Docs/Plans/HANDOFF-v6-1-dungeonbuddy-vnext-domain-runtime-foundation.md
Docs/Plans/HANDOFF-v6-2-vnext-complete-object-read-adaptation.md
pyproject.toml  # comment only

apps/live_control_server/integrations/dungeonmind/vnext_complete_object.py

tests/test_v6_2_vnext_complete_object_adapter.py
```

No `uv.lock` change expected.

## 23. Explicitly out of scope

Do not implement:

```text
production route switching
live native-vNext head lookup
bridge-genesis migration
V2→V3 profile transition
WorldKeeper changes
generic projection/search adaptation
write/publication adaptation
source-body reads
APP-STATE excerpt hydration
filesystem fallback
alias search
related-node recursive complete hydration
suggested-expansion parity
new DTO schema
frontend changes
Kernel changes
```

## 24. Stop conditions

Stop and rebrief if:

- selected authorized aliases require raw alias access;
- selected object mapping requires full-space projection;
- related display hydration requires unrelated entity scans;
- source campaign/session cannot be read from the pinned source view;
- DTO preservation requires inventing authority rows;
- singular label/kind would require silently choosing conflicting admitted facts;
- a required current Buddy literal cannot be represented losslessly;
- live head selection is required;
- a production route must switch;
- V2→V3 transition is required;
- Buddy vocabulary must enter DungeonMind;
- WorldKeeper must learn Buddy presentation semantics.

## 25. Acceptance matrix

PASS requires:

1. V6.1 sealed COMPLETE.
2. V6.K1 recorded.
3. no unnecessary DungeonMind repin.
4. exact revision goes through V6.1 context.
5. native `EntityReadService` complete selected read.
6. bounded related basic reads only.
7. no full projection.
8. no old World-shaped DungeonMind read imports.
9. no raw alias access.
10. authorized aliases populate selected node.
11. no fake existence/alias assertions.
12. name/classification/summary mapping proven.
13. entity-ref → relationship proven.
14. relationship direction proven.
15. campaign/visibility/claim-mode/temporal presentation proven.
16. source domain/campaign/session/digest mapping proven.
17. focus does not alter membership.
18. GM secret plan visible to GM and absent to player.
19. retracted rumor absent.
20. exact product DTO unchanged.
21. semantic fingerprint deterministic.
22. missing object clean.
23. ambiguity/lossless-value failures clean.
24. production route unchanged.
25. V3 optional/parallel.
26. existing World-object projection regression green.

## 26. Verification

Run:

```text
uv sync --locked

uv run pytest -q \
  tests/test_v6_0_1_dungeonbuddy_evidence_metadata_contract.py \
  tests/test_v6_1_dungeonbuddy_vnext_domain_runtime.py \
  tests/test_v6_2_vnext_complete_object_adapter.py \
  tests/test_world_graph_object_projection.py

uv run ruff check \
  src/graph_memory/vnext \
  apps/live_control_server/integrations/dungeonmind/vnext_complete_object.py \
  tests/test_v6_2_vnext_complete_object_adapter.py

git diff --check
```

Also run the default non-live suite and classify inherited base/head failures exactly.

## 27. Handback

Return:

```text
base / exact head / PR / commits / changed paths

V6.1 completion record
Kernel V6.K1 anchor
DungeonMind runtime pin

selected complete-read count
related basic-read count
presentation provenance snapshot count
source IDs requested

GM witness
player witness
focus witness
missing-object witness
ambiguity failures
optional V3 witness

product semantic fingerprint
Kernel complete-result digest

proof:
  no old World read imports
  no raw alias access
  no production route change

focused tests
World-object regression
default-suite classification
Ruff
diff check

what remains false
named successor
```

## 28. Acceptance and successor

Only Steward review may record:

```text
V6_2_VNEXT_COMPLETE_OBJECT_DTO_PRESERVATION_ACCEPTED
```

PASS means DungeonBuddy can reconstruct its selected complete World-object DTO from exact admitted native-vNext knowledge without old World-shaped DungeonMind reads or consumer-side authority invention.

It does not mean production uses the adapter, migration is complete, writes use vNext, or cutover is authorized.

After acceptance, dispatch:

```text
V6.3 — Buddy governed-write adaptation / publication mapping
```

Do not begin V6.3 in this PR.
