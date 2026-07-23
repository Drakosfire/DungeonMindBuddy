# HANDOFF — SBW08 World Graph external statblock resource and binding contract

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED / PARALLEL LANE — dispatch after current graph contract work on `main` stabilizes; re-anchor to the actual Kernel/contribution/projection SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw08-world-graph-statblock-binding-contract.md`  
**Workstream:** `SBW08`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one contract capability: the World Graph can represent and project a typed external DungeonMind statblock resource plus a typed Threat binding. Do not call DungeonMindServer, create a product Threat, add workbench UI, or publish a real campaign contribution.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Represent external statblock resource node | No alone; required graph endpoint | Yes | Projection only | Include |
| Represent typed `ThreatStatblockBinding` edge state | Yes | Yes | Projection only | Include under same invariant |
| Materialize and reload through Kernel/contribution path | No; required durable proof | Yes | No | Include |
| Publish a real Threat + binding | Yes | Yes | Yes | Successor `SBW09` |
| Resolve Server mechanics | Yes | No | Yes | Successor `SBW10` |
| Generic arbitrary graph properties framework | Yes | Yes | Broad | Exclude unless existing architecture requires it; stop condition |

**Selected capability:** the graph contract can store, validate, traverse, fingerprint, reload, and project an exact Threat-to-statblock binding without storing mechanics definitions.

**Why included rows share one invariant:** the external resource node exists only to provide a valid graph endpoint for the typed binding; materialization/projection are required proofs of that single durable relationship contract.

## §1 Mission

A graph contribution can assert and later project a typed relationship from a Threat to an external DungeonMind statblock resource so traversal and exact revision selection are durable without copying canonical mechanics into the graph.

**Invariant**

```text
Graph memory stores only external resource identity and typed binding metadata; selected_revision_id and definition_digest participate in validation and semantic identity, while StatblockDefinitionV1 never enters the graph.
```

**Mission falsification test**

```text
This is not one slice if implementation must also publish a product Threat, call DungeonMindServer, build a Threat Sheet, create generic graph-property authoring UI, or change campaign lifecycle semantics.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §8; authored threat/statblock domain contract; Campaign Supergraph architecture/tracker; Kernel contribution contracts |
| Repository rules | `AGENTS.md`; graph write/kernel rules; external-agent PR loop |
| Base revision | Current immutable `main` SHA after graph contract changes settle |
| Predecessor contract | `GraphContributionAssertion`, union-supergraph node/edge models, semantic assertion identity/fingerprint, immutable revision publish/reload, projection node/relationship views |
| Exact input consumed | Strict node/edge assertion values for `external_resource` and `threat_statblock_binding` |
| Named successor | `SBW09` governed product Threat + binding publication |
| What remains false | No user workflow or campaign object is published; no mechanics can be read/rendered |
| Explicit non-goals | Workbench, Server transport, product graph proposal, generic properties framework, preferred revision UX, media, combat |

Read in order:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. graph roadmap/tracker and active graph contribution contracts
3. integration design §8
4. `src/graph_memory/union_supergraph/model.py`, load/validate/materialize paths
5. contribution assertion/materialization/semantic-identity implementation and tests
6. projection node/relationship view contracts and tests
7. graph object authoring overlay only to understand later consumer needs; do not change product UI here

Authority precedence:

```text
1. Campaign Supergraph architecture and Kernel contracts
2. active graph tracker/decisions
3. integration design
4. this handoff
5. implementation/tests
6. attached research/historical sources
```

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Validate external resource node assertion | Generic node value/state | Strict provider/resource contract; no definition | Yes | contribution/model validation |
| Materialize external resource node | Generic state loses typed external metadata | Typed state survives immutable graph store | Yes | Kernel materialization |
| Validate binding edge assertion | Generic `uses_statblock` could carry arbitrary value | Strict endpoints + provider/IDs/digest/role/policy | Yes | contribution/model validation |
| Materialize binding edge | Edge state only includes shared lifecycle/provenance | Typed binding state survives | Yes | Kernel materialization |
| Semantic identity/fingerprint | May ignore typed edge state | Same binding replay idempotent; changed selected revision/digest distinct | Yes | assertion identity/digest |
| Reload graph revision | Typed state absent | Exact values round-trip | Yes | store/load/model |
| Projection node view | Generic external node | Typed external resource summary exposed | Yes | projection |
| Projection relationship view | Generic edge | Typed binding metadata exposed safely | Yes | projection |
| Traversal/reverse lookup | Generic adjacency | Threat ↔ resource traversable | Yes | graph/projection |
| Definition-shaped payload | Could fit arbitrary value | Reject explicitly | Yes | validation |

## §4 Files in scope — allowlist

Actual names must be re-anchored to current graph main.

| Action | Path | Purpose |
|---|---|---|
| Modify/Create | `src/graph_memory/union_supergraph/model.py` or bounded sibling contract module | Strict external resource and binding state models |
| Modify | current graph contribution assertion model module | Validate typed assertion value/state variants |
| Modify | current contribution materialization module | Preserve typed node/edge state during merge |
| Modify | current semantic assertion identity/fingerprint module | Include selected revision/digest/role/policy in identity |
| Modify | `src/graph_memory/union_supergraph/validate.py` | Store-level invariant checks |
| Modify | current graph projection node-view module | External-resource view |
| Modify | current graph projection relationship/adjacency module | Typed binding view |
| Create/Modify | `tests/fixtures/graph_memory/.../statblock_binding_*.json` | Deterministic contract fixtures |
| Create/Modify | focused graph model/contribution/materialization/projection tests | Owning-boundary proof |
| Modify | graph contract documentation only if required by repository rules | Record exact new durable fields |

### Bounded discovery exception

```text
Directory: src/graph_memory/ and tests/fixtures/graph_memory/
Maximum additional paths: 8
Allowed path kinds: the exact existing model, contribution, identity, materialization, validation, load, projection, and focused test files owning this invariant
Decision rule: include only when the path directly stores, validates, fingerprints, reloads, or projects the typed binding
Required report: map each changed path to one invariant proof; stop if a generic property framework or authoring UI becomes necessary
```

## §5 Explicitly out of scope

| Capability/path | Why excluded |
|---|---|
| `apps/live_control_server/services/statblock_*` | No Server/client workflow in this contract slice |
| `StatblockWorkbenchModule.tsx` | Product authoring is separate |
| graph authoring UI/routes for product publication | `SBW09` |
| creating a real Shepherds' Flock Threat fixture as campaign truth | Use synthetic deterministic graph fixture only |
| copying `StatblockDefinitionV1`, combat minimums, rules text | mechanics authority remains Server-owned |
| generic arbitrary edge-property system | separate graph architecture decision if needed |
| campaign-preferred resolution behavior | later projection/upgrade work |
| media binding | `SBW17` |

## §6 Implementation contract

### External resource node state

```text
node_id: external:dungeonmind:statblock:<statblock_id>
kind: external_resource
role: statblock
state.external_resource:
  schema: dmb_external_resource_v1
  provider: dungeonmind
  resource_type: statblock
  resource_id: <statblock_id>
  contract: dungeonmind.dungeonbuddy-statblocks
  contract_version: 1.0.0
```

### Binding edge state

```text
Threat --uses_statblock--> External statblock resource

state.threat_statblock_binding:
  schema: dmb_threat_statblock_binding_v1
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

### Validation rules

- Source endpoint must be a Threat-compatible graph node kind/role according to active ontology rules; do not broaden Threat identity here if the graph vocabulary differs—re-anchor exact accepted kind.
- Target endpoint must be the matching external resource node.
- Provider/resource/statblock IDs must agree across node ID, node state, and edge state.
- `selected_revision_id` and `definition_digest` are required for `pinned`.
- `campaign_preferred` may omit selected revision only if the owning architecture explicitly permits that durable state; otherwise require an exact selected revision in v1 and defer preferred selection.
- `phase_key` is required only for `role=phase`; incompatible role-specific fields reject.
- Unknown extra fields reject.
- Mechanics definition, rules elements, rendered Markdown, URLs, or asset bodies reject.

```text
Input:
  GraphContributionAssertion node/edge values using the strict state contracts

Output:
  immutable union-supergraph revision containing typed node/edge state and typed projection views

Invariant:
  exact external identity/binding metadata survives; mechanics do not enter graph

Failure behavior:
  endpoint mismatch -> validation failure, no publish
  provider/ID/digest mismatch -> validation failure
  duplicate same semantic assertion -> idempotent support/replay behavior
  changed selected revision/digest/role/policy -> distinct assertion/binding replacement semantics; never silently collapsed
  unknown schema/version -> fail closed

Replay / idempotency:
  same semantic binding and contribution -> existing support/replay behavior
  same binding re-attested by another contribution -> support merges without duplicate edge identity if active graph semantics permit
  changed selected revision -> semantically distinct assertion; exact update/replacement handled by later governed contribution

Trust boundary:
  Verifies: structural ID agreement, enums, digest/locator syntax, endpoint kinds, schema version
  Records without proving: Server resource existence or digest correctness
  Rejects: copied mechanics, arbitrary URLs, display-name identity
```

### §6A State and fallback matrix

| Path | Initializing | Success | Miss | Dependency unavailable | Integrity failure | Stale/superseded | Replay |
|---|---|---|---|---|---|---|---|
| Validate assertion | parse strict state | accepted candidate assertion | endpoint absent = validation error | N/A | fail closed | active graph parent handled by normal Kernel | same semantic identity idempotent |
| Materialize | load base graph | typed node/edge state stored | N/A | N/A | atomic publish fails | normal immutable revision semantics | support merge rules |
| Reload | strict load | exact state | missing object normal miss | N/A | unknown schema/mismatch fails | revision pin exact | safe |
| Projection | project exact revision | typed view | missing object unresolved | N/A | fail closed/diagnostic | exact revision remains | deterministic |

No fallback to label lookup, external Server call, or copied definition.

### §6B Identity matrix

| Situation | Required rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| External node | deterministic provider/resource/statblock ID | mismatch rejects | No | reusable endpoint |
| Binding | stable `binding_id` plus semantic fields under active assertion identity rules | collision with different fields rejects/distinct assertion | No | exact relationship identity |
| Threat endpoint | exact graph node ID | alias resolution only before contribution creation, not Kernel materialization | No | stable source |
| Revision | exact selected revision ID for pinned | no latest | No | semantic identity input |
| Digest | exact bounded digest format | mismatch rejects | No | semantic identity input |
| Rename labels | labels may change without identity | none | No | node/edge IDs stable |
| Rebinding | new governed assertion/replacement | never in-place unnoticed mutation | No | later publication/upgrade contract |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Publish fixture contribution | immutable graph revision node/edge state | exact typed values | normal contribution idempotency/support | schema/version strict | later retraction/supersession uses Kernel semantics |
| Reload | strict model | no field loss | safe repeat | unknown version fails | N/A |
| Projection | derived typed view | IDs/revision/digest retained | deterministic | additive consumer versioning if needed | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** current `GraphContributionAssertion.value`, `UnionSupergraphNode.state`, `UnionSupergraphEdge.state`, assertion identity, and projection view types.

The implementation handback must include an exact field map from assertion value to stored state and projection. Minimum:

| Assertion input | Stored graph field | Projected field | Proof |
|---|---|---|---|
| external resource provider/type/id/contract | `node.state.external_resource` | typed node resource view | materialize/reload/projection test |
| binding ID/provider/statblock/revision/digest | `edge.state.threat_statblock_binding` | typed relationship view | same |
| role/policy/phase/variant | typed edge state | relationship detail | role matrix tests |
| lifecycle/provenance/visibility/campaign scope | existing shared node/edge state | existing projection fields | regression tests |
| copied definition/unknown fields | rejected | none | validation negative fixture |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Strict node/binding validation | model/contribution | focused unit tests | valid/invalid matrix |
| Typed state survives publish/reload | Kernel/materialization/store | immutable revision integration test | exact values |
| Same binding replay is idempotent | contribution/identity | replay test | no duplicate semantic edge/support correct |
| Changed revision is distinct | assertion identity | comparison test | distinct fingerprint/assertion |
| Projection exposes typed metadata | projection | fixture projection test | exact IDs/digest/role/policy |
| Mechanics never stored | validation + fixture inspection | negative tests/search | definition payload rejected/absent |
| Existing graph contracts remain green | repository | focused graph suite | no regression |

Commands must be re-anchored to actual modules, including:

```bash
uv run pytest <focused graph model/contribution/materialization/projection tests> -q
uv run python -m graph_memory.union_supergraph.validate <new fixture path>
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Not applicable — this is a durable graph contract slice. Use deterministic synthetic fixtures and immutable revision/projection tests; do not create campaign truth or a new UI.

## §8 Required handback

Include base/head, actual paths, contract schemas, exact input→stored→projection map, identity/fingerprint evidence, validation matrix, commands/results/provenance, baseline failures/waivers, and confirmation that no Server/product publication/UI/mechanics payload shipped.

## §9 Acceptance rubric

- [ ] Strict external resource and binding schemas exist.
- [ ] Provider/resource/statblock/revision/digest agreement is validated.
- [ ] Typed state survives immutable publish/reload/projection.
- [ ] Same binding replay is idempotent under normal contribution semantics.
- [ ] Changed selected revision/digest is semantically distinct.
- [ ] No full mechanics definition, Markdown, URL payload, or media body enters graph state.
- [ ] No product Threat publication or Server call ships.
- [ ] No generic property framework is silently introduced.

## §10 Reviewer protocol

Review the graph semantic identity first. Trace every input field through materialization and projection. Search fixtures/state for definition-shaped keys, rules text, asset bodies, URLs, and display-name identity. Confirm shared lifecycle/provenance state is not overwritten.

## §11 Re-review protocol

Rerun the complete validation matrix, replay/distinct-identity tests, immutable reload, and projection tests after every fix. Recheck generic graph contracts for accidental broadening.

## Stop conditions

Stop if:

- typed edge state requires a generic graph-property architecture decision not already accepted;
- semantic assertion identity cannot include selected revision/digest without breaking existing invariants;
- external-resource nodes conflict with active ontology constraints;
- `campaign_preferred` semantics are unresolved;
- current projection contracts cannot expose typed state without a separate public-contract slice;
- a real campaign write or Server existence check is needed for proof;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor to current graph main and exact model paths.
- [ ] Resolve whether v1 permits `campaign_preferred` without exact selected revision; default to pinned-only if not.
- [ ] Confirm synthetic fixtures only.
- [ ] Confirm `SBW09+` remain false.
