---
# Literal Markdown the worker MUST use as the PR-body skeleton.
# The complete checked-in handoff remains authoritative.
pr_body_template: |
  ## Outcome
  The World Graph can persist and project a typed external DungeonMind statblock resource plus one exact pinned `ThreatStatblockBinding` without copying statblock mechanics into graph state.

  ## Merge-ready invariant
  One accepted graph contribution must round-trip a deterministic external-resource node and immutable exact binding edge derived from the same six-field mechanics locator; provider, IDs, contract, revision, and digest must agree at assertion, stored-revision, and projection boundaries, while mismatches, unknown schemas, definition-shaped payloads, and ambiguous binding selection fail closed without a DungeonMind call or product publication.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Strict external-resource and binding payloads | graph contract models | valid/invalid model matrix | {{TODO}} |
  | Exact locator fields survive contribution materialization and immutable reload | Kernel contribution + revision store | publish/reload integration proof | {{TODO}} |
  | Binding fields participate in semantic identity and replay | assertion identity + support ledger | same-input replay and changed-locator distinction tests | {{TODO}} |
  | Revision-pinned projection exposes typed resource and binding views | World Graph projection | exact projection assertions | {{TODO}} |
  | Mechanics bodies and inconsistent identities fail before publish | validation/materialization | adversarial rejection matrix | {{TODO}} |

  ## Scope and explicit deferrals
  - Minimum base: `fb5a66d48cd63b4644a14ad6321bd0cb8243adbb`
  - Actual base/head: {{TODO}}
  - Actual changed paths: {{TODO}}
  - Paths outside §4: {{TODO: none or stop report}}
  - Deferred and still false: product publication, create-or-connect, DMS existence verification, Hermes hydration, Threat Sheet UX, placement, revision adoption, and combat.

  ## Evidence produced
  ### Automated
  {{TODO}}

  ### Adversarial
  {{TODO}}

  ### Regression
  {{TODO}}

  ### Manual / dogfood
  Not applicable — this PR creates a reusable graph contract and synthetic owning-boundary proof, not a user-facing publication path.

  ## Gaps, waivers, and stop conditions
  {{TODO: none, or exact missing evidence / waiver / split}}
---

# HANDOFF — PR457 SBW08 exact statblock resource and Threat binding contract

**Created:** 2026-07-30.  
**Status:** ACTIVE — dispatch exactly one graph-contract capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr457-sbw08-statblock-binding-contract.md`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Minimum implementation base:** `fb5a66d48cd63b4644a14ad6321bd0cb8243adbb`  
**Suggested branch:** `feat/sbw08-statblock-binding-contract`

> **Predecessor gate:** The operator has manually confirmed the real create → generate → edit → validate → accept → reopen path at least twice. Do not dispatch another R0-A proof and do not make this contract slice re-prove Workbench mechanics persistence.
>
> **Dispatch boundary:** This PR defines how an already accepted exact statblock revision is represented inside the World Graph. It does not publish a product Threat, call DungeonMindServer, hydrate mechanics, or add Workbench/UI actions.
>
> This handoff supersedes `Docs/Plans/HANDOFF-sbw08-world-graph-statblock-binding-contract.md` and the mistaken `HANDOFF-pr457-r0a-accepted-revision-proof.md`.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Mechanics locator** | The existing Buddy-owned six-field exact identity: `provider`, `statblock_id`, `revision_id`, `contract`, `contract_version`, `definition_digest`. |
| **External statblock resource** | A logical DungeonMind statblock endpoint represented as a graph node. It identifies the logical resource and contract but stores no mechanics definition. |
| **ThreatStatblockBinding** | An immutable exact relationship from one graph Threat to one exact mechanics locator. |
| **Pinned-only v1** | Every binding names an exact revision and digest. There is no `latest`, `campaign_preferred`, or implicit upgrade behavior in this contract. |
| **Binding projection** | Typed resource/binding metadata exposed from a revision-pinned World Graph projection so later consumers can hydrate the owning resource. |
| **Mechanics body** | `StatblockDefinitionV1`, rules elements, rendered statblock Markdown, or equivalent canonical mechanics content. It must never enter graph state. |

## §1 Mission and merge-ready invariant

The World Graph can persist and project a typed external DungeonMind statblock resource plus one exact pinned `ThreatStatblockBinding` without copying statblock mechanics into graph state.

**Merge-ready invariant:** One accepted graph contribution must round-trip a deterministic external-resource node and immutable exact binding edge derived from the same six-field mechanics locator; provider, IDs, contract, revision, and digest must agree at assertion, stored-revision, and projection boundaries, while mismatches, unknown schemas, definition-shaped payloads, and ambiguous binding selection fail closed without a DungeonMind call or product publication.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. Models, assertion identity, materialization, immutable reload, validation, and projection all preserve or reject the same exact resource/binding identity. |
| Most likely adversarial failure? | A valid binding is published, then another assertion reuses its binding/edge ID with a changed revision or digest; generic state merge preserves stale fields while support/projection appears healthy. |
| Does §7 detect it? | Yes. Tests require immutable deterministic binding identity, changed-locator distinction, same-ID mismatch rejection, and projection from active assertion authority rather than stale stored fallback. |
| Easiest boundary to under-test? | Projection. Current projection reconstructs active semantics from contribution support, while arbitrary nested state can be dropped or become stale during materialization. |
| What forces a stop/split? | Needing a generic arbitrary-property framework, product publication workflow, a DMS read, preferred/latest resolution, graph-wide primary-binding policy, or changes outside the bounded graph contract paths. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`; `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`; `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md` |
| Operator evidence | The GM has manually confirmed accepted mechanics creation and exact reopen at least twice; this satisfies the predecessor product dependency for contract dispatch. |
| Existing exact identity | `apps/live_control_server/integrations/dungeonmind_statblocks/mechanics_locator.py::MechanicsLocatorV1` |
| Current graph write authority | `GraphContributionAssertion` → `apply_accepted_assertions` → immutable World Graph revision and assertion-support ledger |
| Current read authority | revision-pinned `graph_memory.kernel.world_projection` and `graph_memory.projection.world_projection` contracts |
| Exact input consumed | Synthetic accepted node + edge assertions carrying a valid six-field locator; no live DMS object is required for contract tests |
| Named successor | `SBW09a` durable publication operation, then `SBW09b` create-or-connect and `SBW09c` governed commit |
| What remains false | No GM can yet publish or bind a Workbench statblock through the product; no consumer can hydrate mechanics from the binding |
| Explicit non-goals | Workbench, product routes/UI, DMS transport, real campaign mutation, query ranking, hydration, Threat Sheet, placement, combat, revision adoption, media |

Read in order:

1. `AGENTS.md` and external-agent PR-loop rules.
2. Current roadmap and tracker.
3. `apps/live_control_server/integrations/dungeonmind_statblocks/mechanics_locator.py`.
4. `src/graph_memory/kernel/contribution_models.py` and `contributions.py`.
5. `src/graph_memory/kernel/contribution_merge.py`.
6. `src/graph_memory/union_supergraph/model.py` and `validate.py`.
7. `src/graph_memory/kernel/world_projection.py` and `src/graph_memory/projection/world_projection.py`.
8. Existing focused graph tests named in §4.
9. The older SBW08 handoff only as historical research; this file owns current dispatch.

Authority precedence:

```text
current repository rules
→ publication-first roadmap/tracker, with operator-confirmed accepted-revision prerequisite satisfied
→ this re-anchored PR457 handoff
→ current Kernel and projection contracts
→ older SBW08 design notes
→ chat summaries
```

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant? | Owner |
|---|---|---|---:|---|
| Parse external-resource assertion | Generic `value`/`state` dictionaries accept or drop arbitrary nested fields | Recognized external-resource payload validates against one strict versioned model | Yes | new graph contract model + contribution materialization |
| Parse binding assertion | Generic edge value can carry arbitrary data | `uses_statblock` binding requires exact endpoints and six-field locator agreement | Yes | contract model + contribution materialization |
| Assertion semantic identity | All non-provenance value fields are hashed generically | Exact locator, role, phase/variant metadata, and deterministic IDs participate in identity | Yes | existing `compute_assertion_id` plus focused tests |
| First materialization | Current node/edge state stores only shared lifecycle fields | Typed external resource/binding state survives in the immutable graph revision | Yes | `contribution_merge.py` |
| Same contribution replay | Existing contribution/support replay is idempotent | No duplicate external node, binding edge, or support record | Yes | Kernel contribution lifecycle |
| Changed locator | Generic edge ID can collide while state is not replaced | Changed revision/digest/role creates a distinct deterministic binding; same binding ID with different content rejects | Yes | ID helper + materialization validation |
| Store validation | Structural validator checks generic maps/endpoints | Typed nested state, endpoint agreement, locator formats, and no-mechanics rule are checked | Yes | `union_supergraph/validate.py` |
| Immutable reload | Generic state round-trips but lacks typed guarantee | Exact typed values round-trip with no field loss | Yes | World Graph revision store/model |
| Revision-pinned projection | Node/relationship views omit typed external metadata | Optional typed `external_resource` and `threat_statblock_binding` views expose exact identity | Yes | projection contracts + Kernel projector |
| Multiple bindings | Existing graph can hold multiple edges | Projection returns all bindings; no implicit primary/latest selection; consumers must handle zero/one/many explicitly | Yes | projection contract |
| Retraction/supersession | Assertion support controls projectability | Existing support semantics remain authoritative; this slice adds no cascade deletion or resource mutation | Yes | support ledger/projection |

Adversarial sequences:

| Sequence | Required safe outcome | Proof |
|---|---|---|
| Valid external node + binding → publish → reload → pinned projection | Exact locator and role fields are equal at assertion, stored state, and projection | round-trip integration test |
| Same contribution replayed | Same revision semantics/support; no duplicate edge/resource | replay test |
| Same Threat + same locator + same role | Deterministic binding/edge identity is identical | identity unit test |
| Same binding ID + changed revision/digest | Reject before publish; never preserve stale stored binding under new active support | mismatch test |
| Same Threat + changed revision/digest | New immutable binding/edge identity; old binding is not silently repinned | identity distinction test |
| Binding target statblock ID disagrees with external node | Reject before publish | endpoint/locator agreement test |
| `definition`, `rules_elements`, or rendered mechanics included | Reject before publish; raw body absent from graph revision | no-mechanics negative tests |
| Unknown schema/version or extra nested field | Fail closed | strict-model tests |
| Two projected `role=primary` bindings | Return both without selecting one; later policy must resolve explicitly | projection ambiguity test |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/union_supergraph/statblock_binding.py` | Strict versioned resource/binding models, ID helpers, locator/endpoint agreement, no-mechanics validation |
| Modify | `src/graph_memory/union_supergraph/model.py` | Type optional stored external-resource and binding state without breaking existing graph payloads |
| Modify | `src/graph_memory/kernel/contribution_merge.py` | Recognize, validate, and materialize typed resource/binding state |
| Modify | `src/graph_memory/union_supergraph/validate.py` | Validate stored typed contracts and cross-object agreement |
| Modify | `src/graph_memory/projection/world_projection.py` | Add optional typed node/relationship projection fields |
| Modify | `src/graph_memory/kernel/world_projection.py` | Reconstruct and expose typed metadata from active assertion authority, fail closed on disagreement |
| Create | `tests/test_statblock_binding_graph_contract.py` | Focused model, identity, merge/reload, replay, mismatch, and projection proof |
| Modify if needed | `tests/test_union_supergraph_validate.py` | Store-level valid/invalid contract matrix |
| Modify if needed | `tests/test_graph_kernel_world_projection.py` | Projection regression and ambiguity behavior |
| Create if needed | `tests/fixtures/graph_memory/statblock_binding_valid.json` | One deterministic valid contract fixture |
| Create if needed | `tests/fixtures/graph_memory/statblock_binding_invalid.json` | Bounded negative fixture set when inline cases are insufficient |

### Bounded discovery exception

```text
Directory: src/graph_memory/kernel/, src/graph_memory/union_supergraph/, src/graph_memory/projection/, tests/
Maximum additional paths: 4
Allowed path kinds: exact existing serializer/load helper, assertion-support test, or fixture helper directly required to prove the invariant
Decision rule: add only when the named file owns strict parsing, immutable round-trip, assertion identity, or revision-pinned projection for this contract
```

Any `apps/**`, product route/component, DMS client, campaign corpus, runtime store, or broad graph framework path is a stop condition.

## §5 Explicitly out of scope

| Path or capability | Why excluded |
|---|---|
| `apps/live_control_server/**` and `apps/live-control-ui/**` | `SBW09` owns product publication and consumer transport |
| DungeonMindServer calls or fixtures | Graph records a locator claim; existence/digest verification occurs during later hydration |
| Real Eldyrwild campaign contribution | Contract proof uses synthetic deterministic graph data; governed real publication is `SBW09c` |
| `StatblockDefinitionV1`, rules elements, rendered Markdown, asset bodies | Mechanics authority must stay outside the graph |
| `campaign_preferred`, `latest`, fallback revision resolution | v1 is exact pinned-only |
| Automatic primary-binding selection | Projection returns all; selection policy belongs to `SBW09/SBW10` |
| Rebinding/upgrading an existing binding | Later revision/adoption work; changed locator creates a new immutable binding identity |
| Generic arbitrary node/edge property framework | Separate architecture decision if strict nested contracts cannot fit existing extension seams |
| Query ranking by mechanics capability | `SBW10a` after publication and hydration |
| Threat compact/full UI | `SBW10b` |
| Placement and combat | `AOW03/AOW04`, `COMBAT01`, `SBW15` |

## §6 Implementation contract and matrices

### External statblock resource v1

```text
assertion_kind: node
subject_node_id: external:dungeonmind:statblock:<statblock_id>
value.kind: external_resource
value.role: statblock
value.external_resource:
  schema: dmb_external_resource_v1
  provider: dungeonmind
  resource_type: statblock
  resource_id: <sb_[a-z0-9]+>
  contract: dungeonmind.dungeonbuddy-statblocks
  contract_version: "1.0.0"
```

The logical resource node does not carry `revision_id`, `definition_digest`, URLs, or mechanics content.

### ThreatStatblockBinding v1

```text
assertion_kind: edge
subject_node_id: <exact Threat node id>
target_node_id: external:dungeonmind:statblock:<statblock_id>
predicate: uses_statblock
value.edge_id: <deterministic edge id from binding_id>
value.direction: outbound
value.threat_statblock_binding:
  schema: dmb_threat_statblock_binding_v1
  binding_id: <deterministic immutable binding id>
  provider: dungeonmind
  statblock_id: <sb_[a-z0-9]+>
  revision_id: <rev_[a-z0-9]+>
  contract: dungeonmind.dungeonbuddy-statblocks
  contract_version: "1.0.0"
  definition_digest: <sha256:[0-9a-f]{64}>
  role: primary | alternate | phase | encounter_variant | template
  phase_key: <string|null>
  variant_label: <string|null>
```

Rules:

- v1 is always pinned; revision and digest are mandatory.
- External node ID, resource ID, binding statblock ID, and target endpoint must agree.
- `binding_id` is deterministically derived from Threat ID, all six locator fields, role, `phase_key`, and `variant_label`.
- `edge_id` is deterministically derived from `binding_id`; display labels never participate in resolution.
- `phase_key` is required only for `role=phase`; incompatible role metadata rejects.
- A changed locator or role metadata creates a new binding identity. No in-place repin exists.
- Nested contract models forbid unknown fields.
- Recognized external-resource/binding assertions reject sibling or nested definition-shaped fields.
- Graph validation proves structural identity agreement, not that DungeonMind currently serves the locator.

### State and fallback matrix

| Path | Exact success | Miss/unavailable | Integrity/contract failure | Retry/replay | Fallback |
|---|---|---|---|---|---|
| Parse assertion | strict typed payload | unrecognized ordinary graph assertion follows existing path | recognized malformed payload rejects | deterministic | none |
| Materialize | typed nested state written | missing endpoint rejects | ID/locator/schema mismatch rejects atomically | same contribution idempotent | none |
| Reload | exact state | missing revision uses existing not-found behavior | malformed stored state fails validation | deterministic | none |
| Projection | typed optional view on pinned revision | ordinary non-resource node/edge has null typed field | disagreement/malformed typed state = projection integrity error | deterministic | no stored-state guess when active assertion authority exists |
| DMS existence | not checked | N/A | N/A | N/A | deferred to hydration |

### Identity matrix

| Situation | Rule | Ambiguity | Fallback |
|---|---|---|---|
| External logical resource | deterministic provider/resource/statblock node ID | mismatch rejects | none |
| Binding | deterministic content-bound `binding_id` | same ID + different payload rejects | none |
| Exact revision | exact `revision_id` + digest | no latest | none |
| Labels/aliases | presentation only | never identity | none |
| Multiple bindings | all are projected | zero/one/many remains explicit; no winner | none |
| New revision adoption | new binding identity in later governed workflow | old binding remains pinned until retracted/superseded | none |

### Persistence and replay matrix

| Operation | Durable representation | Round-trip | Replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Accepted contribution | existing `GraphContributionAssertion` plus typed nested value | exact | existing contribution idempotency | old graph objects remain readable with null typed views | contribution lifecycle semantics |
| Materialized resource | node typed state | exact | no duplicate node | optional additive field | support/retraction semantics |
| Materialized binding | edge typed state | exact | no duplicate edge | optional additive field | support/retraction semantics |
| Projection | derived typed view | exact locator fields | deterministic | new optional fields | revision pin preserves historical view |

### Predecessor-to-consumer mapping

| Existing mechanics locator | Graph resource/binding field | Transformation | Proof |
|---|---|---|---|
| `provider` | resource + binding provider | exact string | compatibility test |
| `statblock_id` | resource ID, external node ID, binding field | validate exact agreement | mismatch tests |
| `revision_id` | binding revision ID | exact | round-trip test |
| `contract` | resource + binding contract | exact | round-trip test |
| `contract_version` | resource + binding version | exact | unknown-version rejection |
| `definition_digest` | binding digest | exact, no recompute | round-trip/mismatch test |

Do not import app-layer mechanics models into graph runtime if that violates layering. Mirror the frozen six-field wire contract in a graph-owned strict model and prove field compatibility in tests.

## §7 Evidence required to merge

| Guarantee | Boundary | Evidence class | Command/scenario | Expected result | Stop condition |
|---|---|---|---|---|---|
| Strict typed models and bounds | contract module | unit/contract | focused model matrix | valid shapes parse; malformed/extra/mechanics fields reject | permissive unknown fields remain |
| Deterministic identity | ID helpers + existing assertion hashing | unit/adversarial | same locator vs changed revision/digest/role | same input same IDs; changed semantic input distinct | changed locator can reuse binding/edge ID |
| Materialize + immutable reload | contribution merge/world store | integration | publish synthetic contribution, reload exact revision | exact typed fields preserved | field loss or stale generic fallback |
| Replay | contribution/support ledger | adversarial | apply/replay same contribution | no duplicate node/edge/support | duplicate or divergent state |
| Cross-object agreement | validation/materialization | negative integration | node/target/binding mismatch matrix | reject before publish | inconsistent revision published |
| No mechanics in graph | validation/materialization | security/contract | definition-shaped key matrix | reject; payload absent from stored revision | mechanics body survives |
| Projection exactness | Kernel projection | integration | revision-pin projection | typed node and relationship views equal assertion authority | typed fields omitted or reconstructed from stale state |
| Ambiguous primary handling | projection | adversarial | two distinct primary bindings | both returned; no implicit winner | first-wins selection |
| Regression | existing graph suites | regression | commands below | no unrelated projection/validation regression | new failures without base comparison |

Required commands:

```bash
uv run pytest -q tests/test_statblock_binding_graph_contract.py
uv run pytest -q tests/test_union_supergraph_validate.py tests/test_graph_kernel_world_projection.py
uv run ruff check src/graph_memory/union_supergraph src/graph_memory/kernel/contribution_merge.py src/graph_memory/kernel/world_projection.py src/graph_memory/projection/world_projection.py tests/test_statblock_binding_graph_contract.py
uv run mypy src/graph_memory/union_supergraph/statblock_binding.py src/graph_memory/union_supergraph/model.py src/graph_memory/kernel/contribution_merge.py src/graph_memory/kernel/world_projection.py src/graph_memory/projection/world_projection.py
uv run python -m graph_memory.union_supergraph.validate --json

git diff --check
git diff --name-only <base>...HEAD
git diff --stat <base>...HEAD -- \
  src/graph_memory/union_supergraph/statblock_binding.py \
  src/graph_memory/union_supergraph/model.py \
  src/graph_memory/kernel/contribution_merge.py \
  src/graph_memory/union_supergraph/validate.py \
  src/graph_memory/projection/world_projection.py \
  src/graph_memory/kernel/world_projection.py \
  tests/test_statblock_binding_graph_contract.py \
  tests/test_union_supergraph_validate.py \
  tests/test_graph_kernel_world_projection.py \
  tests/fixtures/graph_memory/statblock_binding_valid.json \
  tests/fixtures/graph_memory/statblock_binding_invalid.json
```

Baseline failure protocol applies: compare the exact command on base and head; do not call a pre-existing failure green.

## §8 Required PR description and handback

The PR body must use the frontmatter skeleton and include:

1. §1 mission and invariant verbatim.
2. Base and head SHAs.
3. Actual changed paths and any bounded-discovery path.
4. Field map from the six-field mechanics locator to assertion, stored state, and projection.
5. Exact binding-ID/edge-ID algorithm and examples.
6. Every §7 result with provenance.
7. Base/head comparison for failures.
8. Confirmation that no app/DMS/product path changed.
9. Confirmation that no mechanics definition entered graph fixtures or revisions.
10. Named successors still false.

Demolition declaration:

```text
Replaced path: generic untyped storage of recognized external-statblock/binding metadata
Deleted in this PR: no — generic state remains for unrelated graph objects
Retained reason: the Kernel supports many graph object kinds; this slice adds a strict recognized contract, not a general state rewrite
Named remaining consumer: ordinary nodes/edges without the recognized schemas
Required deletion owner: none for this slice
```

## §9 Acceptance rubric

- [ ] Exactly one capability shipped: typed exact statblock resource + Threat binding graph contract.
- [ ] The six-field mechanics locator maps exactly into graph state and projection.
- [ ] v1 is pinned-only; no latest/preferred fallback exists.
- [ ] Deterministic binding identity changes when revision, digest, role, phase, or variant changes.
- [ ] Same binding ID with different semantic content fails before publish.
- [ ] Exact typed fields survive contribution materialization, immutable reload, and revision-pinned projection.
- [ ] Projection exposes every binding and never first-wins an ambiguous primary.
- [ ] Unknown schema/version/extra fields fail closed.
- [ ] Mechanics definitions, rules bodies, rendered Markdown, and assets are rejected from graph state.
- [ ] Existing contribution support/retraction semantics remain authoritative; no custom cascade deletion was added.
- [ ] No DungeonMind call, real campaign mutation, product publication, hydration, placement, or combat work entered scope.
- [ ] Every required test/command has a truthful result and provenance.
- [ ] No path outside §4 or the bounded exception changed.
- [ ] `SBW09a` remains the next product successor.

## Stop conditions

Stop and report rather than widening if:

- current `main` moved materially in Kernel contribution/projection contracts;
- the six-field mechanics locator differs from the checked-in Buddy contract;
- strict nested contracts require a generic arbitrary-property framework;
- graph publication needs a DMS call to validate this contract;
- existing contribution identity cannot distinguish changed binding locators;
- current merge behavior can silently retain stale binding state and cannot be fixed within the named paths;
- primary-binding uniqueness requires product/governance policy rather than graph contract validation;
- a required production path is outside §4;
- any test requires real campaign/runtime mutation;
- mechanics content must be stored to make projection usable.

```text
Stop condition:
Why this mission cannot absorb it:
Invariant clause affected:
Required evidence missing:
New public/durable contract discovered:
Affected paths/owners:
Proposed successor or split:
Tracker update required:
```
