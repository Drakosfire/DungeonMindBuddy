# STATBLOCK — DungeonMind authority cutover reconnaissance

**Date:** 2026-08-06
**Repository:** `Drakosfire/DungeonMindBuddy`
**PR:** [#515 — STATBLOCK: define DungeonMind authority cutover reconnaissance](https://github.com/Drakosfire/DungeonMindBuddy/pull/515)
**Scope:** docs-only reconnaissance; no production behavior changed

## Executive disposition

```text
Disposition: NOT_READY_FOR_BRIDGE
```

**Primary blocker (reframed 2026-08-07 after Play cutover pressure):**
DungeonMind's accepted D&D profile currently conflates the narrow Threat
proving domain with the reusable world-object/mechanics boundary that
DungeonBuddy Play now requires.

Play authority landed on Buddy `main` (`ROADMAP-play-world-object-combat-projection.md`,
`PR-TRACKER-play-world-object-combat-projection.md`) freezes Threat, NPC, and
PlayerCharacter as distinct first-class world objects and places DungeonMind
kernel cutover re-anchor (`KERNEL-0` / Phase K) before durable
`CombatSourceLocator`, NPC/PC projection, or Combat identity contracts.

The reconnaissance still correctly traced Buddy Threat hydration through
`uses_statblock` / `ThreatStatblockBindingV1` and DungeonMind hydration through
`dnd5e:creature` + required `dnd5e:threatens` + `DndThreatMechanicsBinding`.
Those paths expose two contract collisions that a fixture cannot repair:

1. **Threat identity vs `threatens`.** ADR-0005 defines Threat only as
   contextual `dnd5e:threatens` and rejects a Threat object kind. Buddy and
   Play require persistent Threat world-object identity independent from
   contextual hostility relationships. The bridge must not map
   `threat:* → merely dnd5e:creature` or `uses_statblock → dnd5e:threatens`.
2. **Mechanics availability vs Threat context.** `DndThreatMechanicsBinding`
   requires one or more `dnd5e:threatens` relationships before mechanics can
   bind. Allied NPCs (e.g. Lysandra), other NPCs, and Player Characters need
   exact mechanics without manufacturing fictional hostility.

**Fixture conclusion (corrected):** do not add an intermediate PR merely to
manufacture a better Mireward Latchling fixture. Existing synthetic Buddy
graph-binding/provider fixtures and DungeonMind Tripod conformance fixtures
are sufficient for a later conformance-level mechanics proof after the
semantic contract is re-anchored. Latchling, Lysandra, and a PC become later
real-domain acceptance/dogfood cases once the contract is correct.

**Smallest next action:** a DungeonMind-owned additive/versioned semantic and
mechanics-attachment re-anchor that freezes Threat/NPC/PlayerCharacter world
identity, keeps `dnd5e:threatens` contextual, and attaches external mechanics
without requiring hostility. Only then may a Buddy→DungeonMind conformance
bridge begin. A product shadow call and authority promotion remain later.

## 1. Re-anchor ledger

### Repository and PR state

| Artifact | Exact state | Classification |
|---|---|---|
| DungeonMind `main` | `7c311ae0d0d59d7379dee38780be509970fb3a8c` | MATCH; current B.3a, PR #20 transport, and PR #21 resolver are present |
| DungeonMindBuddy `main` | `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd` | MATCH |
| Buddy PR #515 | base `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd`; head `3f5a328d8326c8695e7a17be72a5a8bc22a24bae`; OPEN, CLEAN, MERGEABLE; no reviews/comments | MATCH |
| Buddy PR #510 | base `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`; head `9ea88533686eb257beec14591451aabe6462b294`; OPEN, CLEAN, MERGEABLE | ADVANCED_SAME_CONTRACT; branch-only Build seam |
| Buddy PR #512 | base `d50d0c3a45761376185d36fb39ae3a098a5b8cfc`; head `5ec7da4341bdd2697c9c0cad4a46a693aa3f01cd`; OPEN, CLEAN, MERGEABLE | ADVANCED_SAME_CONTRACT; branch-only shared Threat presentation seam |
| Buddy PR #508 | merged as `9d4f5a3005f87d07147c03d8eee499af3bd57aa3` | MATCH; source of the real Latchling publication |
| Buddy PR #511 | merged as `fd05c7f20ccae22f2f43ec24642bf70290b0d9c7` | MATCH; OPT02 post-commit resident prewarm |
| Buddy PR #513 | merged as `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd` | MATCH; OPT03 bounded projection recipes |

PR #510 and #512 are still open. Their heads supersede the handoff's older
snapshot SHAs, but neither changes the identity conclusion: both preserve an
exact graph reference and route Threat mechanics through the shared
Threat/projection path. The recommendation does not require either PR to merge
first, but any implementation PR must re-anchor against whichever current
mainline state results.

At dispatch, PR #515's cumulative diff against its base was one file, the
checked-in handoff:

```text
 ...dungeonmind-authority-cutover-reconnaissance.md | 865 +++++++++++++++++++++
 1 file changed, 865 insertions(+)
```

This execution adds the report and handback changes; the final two-file scope
and stat are recorded in the authoritative handoff §13.

## 2. Exact target trace

The committed-main fallback target is Tripod Null-Calf. Mireward Latchling is
recorded separately as supplemental author/operator dogfood evidence; it is not
treated as a committed-main exact target.

### 2.1 Committed-main fallback — Tripod Null-Calf

| Datum | Exact value | Provenance |
|---|---|---|
| World | `eldyrwild` | `tests/fixtures/world_graph_retrieval/api-contract-v1.json` |
| Campaign | `longmont-c2` | retrieval fixture and contribution bundle |
| Graph revision | `rev:031c50b108af3c2523ee04accbf6ea4d` | committed retrieval fixture |
| Durable Threat node | `threat:tripod-null-calf` | committed graph contribution/retrieval fixture |
| Kind / role | `threat` / `encounter-threat` | committed retrieval fixture |
| Committed relationship | `edge:threat:tripod-null-calf:appeared_in:event:longmont-c2:session-23:mireward-gate-battle` | contribution bundle and retrieval fixture |
| `uses_statblock` edge | absent | committed graph search and retrieval fixture |
| Accepted statblock ID | absent | no Tripod-linked accepted mechanics record |
| Accepted revision / digest | absent | no Tripod-linked accepted mechanics record |
| Binding ID / external resource node | absent | no Tripod-linked publication binding |

This target proves the committed graph identity and the blocking absence of
mechanics hydration. Its expected current Buddy query disposition is
`no_binding`; it cannot be passed to DungeonMind as a complete mechanics
target.

### 2.2 Supplemental author/operator evidence — Mireward Latchling

The MAGIC-D3 report records a real publication attempt and exact runtime
values, but the graph publication output and provider response are not checked
into the committed graph/fixture set used by this reconnaissance:

| Datum | Exact value | Provenance |
|---|---|---|
| World | `eldyrwild` | `Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md` |
| Campaign | `longmont-c2` | `Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md` |
| Starting graph head | `rev:50f80a916d63a6ec68411810935023ab` | MAGIC-D3 report |
| Published graph revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` | MAGIC-D3 report; became graph head |
| Durable Threat node | `threat:authored:d16d43d376833e38caf46dd19b1dd17f` | MAGIC-D3 report; `Threat` publication commit |
| Label | `Mireward Latchling` | MAGIC-D3 report |
| Publication operation | `ca9fff4d-92f4-45ed-bb02-672b3b175e34` | MAGIC-D3 report |
| Identity resolution | `c05f202f-2f94-4902-88a4-902bc9f91066` | MAGIC-D3 report |
| Proposal | `5461a95b-11eb-40b2-b2b7-ecbdead35b2d` | MAGIC-D3 report |
| Commit | `523e293c-02c8-41db-97bc-58db9e00891b` | MAGIC-D3 report |
| Binding | `threat-statblock-binding:07ab38b331085b426bb69474` | MAGIC-D3 report |
| Statblock ID | `sb_7727dfeeb8074214a6a9cebf257691ff` | MAGIC-D3 report |
| Statblock revision | `rev_60b7bf03dd8d4a75a0a164ad73ce83b1` | MAGIC-D3 report |
| Definition digest | `sha256:4c843b9e8672c20d94e2594a70a62b0496f009481ac69af64dee071171e2d722` | MAGIC-D3 report |
| Commit state | `committed_unverified` | MAGIC-D3 report |
| Verification | `failed` | `rebuild_unavailable`, `projection_threat_source_domains_mismatch`, `projection_external_resource_source_domain_mismatch` |

The publication and rediscovery proof is real as author/operator observation:
the reported runtime revision advanced, a binding was reported, Plan
rediscovered the Threat, and Hermes found it. It is not a committed-main
fixture or target-specific provider response. The report also correctly records
that the publication was not fully verified. That status cannot be silently
promoted to a verified DungeonMind graph revision during a bridge.

### Current Buddy call and ownership trace

```text
exact scoped graph reference
  → GraphReference / World Graph lens carries world, campaign, scope, revision,
    and Threat node ID
  → project_world_graph(... revision_pin=...)
    → apps/live_control_server/services/world_graph_projection.py
    → graph_memory.kernel.world_read_runtime resolves the pinned revision
  → query_threats_with_hydration(...)
    → apps/live_control_server/services/threat_query_hydration.py
    → _collect_threat_hits identifies Threat nodes
    → _enumerate_statblock_bindings enumerates every uses_statblock edge
  → _validate_binding_against_resource checks the external resource node,
    provider, contract, target, deterministic binding ID, and edge ID
  → _hydrate_binding(...)
    → DungeonMindStatblockV1Client.get_exact_revision(statblock_id, revision_id)
    → verify_exact_revision_mechanics_integrity(...)
  → ThreatQueryHydrationResponseV1
    → apps/live_control_ui/.../ThreatSheetProjection.tsx
    → threatSheetViewModel.ts maps every binding and exact status
  → shared Threat sheet / Plan projection
```

The Buddy service does not select a first binding. It sorts and returns all
binding results. A malformed or duplicated edge becomes an integrity result;
it is not converted into `no_binding`.

The exact HTTP entry point is:

```text
POST /api/live/threats/query-hydration
```

owned by `apps/live_control_server/routes/threat_query_hydration.py`. The
request carries `world_id`, `campaign_id`, `scope_mode`, `revision_pin`,
`query_text`, and the exact Threat node ID in `focus_node_ids`.

### Current Buddy binding shape

`src/graph_memory/union_supergraph/statblock_binding.py` defines:

```text
ThreatStatblockBindingV1
  schema = dmb_threat_statblock_binding_v1
  binding_id
  provider = dungeonmind
  statblock_id = sb_...
  revision_id = rev_...
  contract = dungeonmind.dungeonbuddy-statblocks
  contract_version = 1.0.0
  definition_digest = sha256:<64 lowercase hex>
  role = primary | alternate | phase | encounter_variant | template
  phase_key / variant_label
```

The binding is carried on an outbound `uses_statblock` edge from the Threat to
`external:dungeonmind:statblock:<statblock_id>`. The external resource contract
checks provider, resource type, statblock ID, contract, and version. The
binding itself does not carry `world_id`, `campaign_id`, graph revision, D&D
profile, vocabulary, relationship IDs, or media type. Those values remain in
the graph/projection context or are absent.

## 3. DungeonMind candidate trace

The current DungeonMind path is:

```text
world_id
  + exact graph_revision_id
  + object_id satisfying dungeonmind.dnd5e profile
  + DndMechanicsResourceRef
  → /v1/dnd/threat-mechanics-hydrations
  → exact repository get_revision(world_id, graph_revision_id)
  → graph snapshot reload, payload digest, revision identity, profile, and
    vocabulary checks
  → object_kind = dnd5e:creature
  → one or more subject dnd5e:threatens relationship IDs
  → DndThreatMechanicsBinding
  → one resolver call for the exact resource ref
  → observed resource envelope
  → resource identity and payload digest adjudication
  → DndThreatMechanicsHydration
```

The owning code is:

- `src/dungeonmind_dnd/contracts/mechanics_resources.py`:
  `DndMechanicsResourceRef`, `DndThreatMechanicsBinding`,
  `DndMechanicsResourceEnvelope`, and `DndThreatMechanicsHydration`.
- `src/dungeonmind_dnd/application/threat_mechanics.py`:
  exact graph/profile/object/relationship binding and payload verification.
- `src/dungeonmind_dnd/application/threat_mechanics_transport.py`:
  one exact graph revision read, unchanged B.3a delegation, and stable failure
  categories.
- `src/dungeonmind_dnd/integration/threat_mechanics_api.py`:
  the separate bearer-gated read-only host.
- `src/dungeonmind_dnd/integration/statblock_resource_resolver.py`:
  the exact statblock-v1 resolver added by PR #21.

The transport host is deliberately composed by dependency injection. No
production host bootstrap or provider discovery exists in DungeonMind yet.

The host contract is:

```text
POST /v1/dnd/threat-mechanics-hydrations
Authorization: Bearer <configured capability token>
→ 200 + Cache-Control: no-store on exact hydration
→ 404 graph_revision_not_found or mechanics_resource_not_found
→ 409 threat_mechanics_binding_invalid
→ 502 mechanics_resource_integrity_failure
→ 503 graph_repository_unavailable or mechanics_resource_unavailable
→ 500 internal_error
```

The resolver's exact provider operation is:

```text
GET {DUNGEONMIND_STATBLOCKS_BASE_URL}/api/internal/dungeonbuddy/v1/statblocks/{resource_id}/revisions/{resource_revision}
X-DungeonBuddy-Internal-Key: <configured key>
follow_redirects = false
timeout = configured finite timeout, default 90 seconds, maximum 120 seconds
response body limit = 1 MiB
```

Supported resource identity is:

```text
ruleset_id      = dnd5e
provider_id     = dungeonmind.statblocks
resource_schema = dungeonmind.dungeonbuddy-statblocks.1.0.0
media_type      = application/json
resource_id     = sb_[a-z0-9]+
resource_revision = rev_[a-z0-9]+
payload_sha256  = bare 64-character lowercase hex
```

The resolver maps observed `statblock_id`, `revision_id`, `contract`,
`contract_version`, `definition_digest`, and `canonical_definition` without
repairing them. B.3a remains responsible for accepting or rejecting the
observed envelope.

## 4. Exact identity and ownership matrix

The Latchling rows below are supplemental field-shape evidence from the
operator dogfood report. The committed-main Tripod fallback has no binding or
mechanics fields to map. No row asserts that either target is already a
DungeonMind identity.

| Datum | Buddy current owner and shape | DungeonMind required shape | Same identity now? | Adaptation/proof |
|---|---|---|---|---|
| World | `eldyrwild` in the Latchling publication/projection scope | `DndThreatMechanicsBinding.world_id` opaque token | No proof of shared repository identity | Governed world mapping required; may not be inferred |
| Campaign | `longmont-c2` in Buddy lens/reference | Not a binding field; may exist only in a DungeonMind graph payload/consumer context | No | Decide whether campaign scope is represented in the bridge graph contract |
| Exact graph revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` | `rev:<32 lowercase hex>` with content-addressed DMS revision payload | Lexically compatible, semantically unproven | Reuse is not allowed until the revision payload/provenance is proven equivalent |
| Threat object ID | `threat:authored:d16d43d376833e38caf46dd19b1dd17f` | `obj:<opaque>` | No | New governed identity/profile bridge required; label mapping is forbidden |
| Threat kind | Buddy projection uses `threat`/creature-compatible roles | Exact `dnd5e:creature` | No exact contract mapping | Explicit semantic mapping and profile proof required |
| Threat relationship | Outbound `uses_statblock` edge | Subject `dnd5e:threatens` relationship ID(s) | No | A bridge must define what relationship is being asserted; it cannot rename silently |
| Mechanics binding ID | `threat-statblock-binding:07ab38b331085b426bb69474` | `mechbind:<32 lowercase hex>` derived from graph and resource fields | No | Algorithms and input material differ; recomputation is required under the DMS contract |
| Statblock ID | `sb_7727dfeeb8074214a6a9cebf257691ff` | `resource_ref.resource_id`, `sb_*` grammar | Shape likely compatible | Target provider response must prove byte-for-byte locator identity |
| Statblock revision | `rev_60b7bf03dd8d4a75a0a164ad73ce83b1` | `resource_ref.resource_revision`, `rev_*` grammar | Shape likely compatible | Target provider response must be captured and checked |
| Definition digest | `sha256:4c843b9e8672c20d94e2594a70a62b0496f009481ac69af64dee071171e2d722` | bare lowercase hex in `payload_sha256` | Representation can be adapted | Strip only the exact `sha256:` prefix; target canonical bytes are not yet proven |
| Provider | `dungeonmind` in Buddy external resource/binding | `dungeonmind.statblocks` in DMS resource ref | No | Provider namespace mapping must be explicit |
| Resource schema | Buddy stores `contract` + `contract_version` separately | DMS stores `resource_schema = contract + "." + version` | Deterministic composition possible | No current bridge contract governs it |
| Media type | Not carried by `ThreatStatblockBindingV1`/`ExternalResourceV1` | `application/json` required by `DndMechanicsResourceRef` | Missing on Buddy binding | Provider adapter can supply a fixed value only after contract ownership is accepted |
| Mechanics bytes | Provider response has `canonical_definition` JSON text plus a separate `definition` object | Resolver parses observed `canonical_definition`; B.3a hashes the parsed object | Not demonstrated for either target | Capture the exact target response and reproduce its digest under DungeonMind canonical JSON |
| Current-head behavior | Buddy accepts a pinned `revision_pin`, though context/cache resolution also reads head | DungeonMind transport reads only requested exact revision | Semantic pin exists; read topology differs | Shadow proof must assert no head fallback and preserve the pin |

### Digest and canonicalization conclusion

The `sha256:` prefix difference is a representation difference only if all of
the following are proven:

1. Buddy's `definition_digest` is computed over the same canonical object as
   DungeonMind's `canonical_sha256`.
2. The provider's `canonical_definition` is the exact mechanics source, not
   the separate `definition` field.
3. The target response's parsed canonical object hashes to
   `4c843b9e8672c20d94e2594a70a62b0496f009481ac69af64dee071171e2d722`.

The checked-in Buddy fixture
`tests/fixtures/statblocks/v1/exact-revision-response.json` proves the
provider vocabulary and the `canonical_definition`/`definition` distinction
for `sb_000001` / `rev_000002`, with digest
`935dc0dff1ac7cc8405836764469761a1d26e9e38dd74cd856b8a8a31f0fae51`.
It is not the Latchling payload. The Latchling report contains only the
runtime locator and digest. Therefore digest equivalence for the selected real
Threat is not established.

The DungeonMind `Tripod Null-Calf` fixtures are also explicitly synthetic:
`world:synthetic-gatewatch`, `obj:48e170969a2bb3980e437f7430b7b1c1`, and a
`fixture.dungeonmind.statblocks` resource. They demonstrate the D&D profile
contract only; they are not evidence that Buddy's `threat:tripod-null-calf`
or the Latchling identity has already been mapped.

No current path repairs IDs, chooses `latest`, performs list/search discovery,
or uses the separate `definition` object as a fallback. That is the correct
behavior to preserve.

## 5. Current-vs-DungeonMind failure parity

| Case | Buddy current observable behavior | DungeonMind behavior | Shadow parity state |
|---|---|---|---|
| Exact success | `available` binding and `threat_query_hydration_ok`; exact revision is returned after identity and digest checks | 200 hydration with `Cache-Control: no-store` | Shape compatible; identity/profile bridge missing |
| Zero binding | `no_binding`; query can still return the Threat | No `dnd5e:threatens` relationship produces `object_not_threatening` / binding-invalid if binding is attempted | Mismatch in graph admission; bridge must define zero-binding behavior |
| Multiple bindings | Enumerates every valid edge; returns plural results and partial/unavailable disposition; never first-wins | Binding contains plural sorted Threat relationship IDs, but one `resource_ref`; separate resource bindings would be separate DMS bindings | Requires explicit plural mapping; no first-winner allowed |
| Provider 404 | Client maps downstream 404; service returns `exact_revision_missing` | Resolver returns `None`; B.3a maps to `mechanics_resource_not_found`; host returns 404 | Stable miss categories are compatible, messages/contracts differ |
| Provider 410 | Client maps downstream 410/expired; service returns `exact_revision_missing` | Resolver treats 410 as exact miss and host returns 404 | Compatible miss semantics; needs cross-service result mapping |
| Provider unavailable/timeout | Client maps timeout/unavailable; binding becomes `unavailable` and aggregate may be partial | Resolver raises sanitized failure; host returns 503 `mechanics_resource_unavailable` | Compatible category; Buddy has no DMS-host client yet |
| DMS hydration host unavailable | No current Buddy call path exists | Host/client deployment failure is outside the checked-in DMS contract | Operationally unknown; blocks shadow dogfood, not pure contract work |
| Wrong provider identity | Buddy client validates the response model/contract and produces integrity failure | Resolver preserves observed resource fields; B.3a returns resource identity failure | Failure intent compatible; adapter ownership differs |
| Wrong statblock ID/revision | Buddy exact client rejects response identity mismatch | Resolver does not substitute request fields; B.3a rejects observed mismatch | Compatible only after bridge preserves raw disagreement |
| Wrong schema/version | Buddy strict model rejects contract/version drift | Resolver composes observed schema; B.3a rejects mismatch | Compatible fail-closed outcome; not byte-identical |
| Digest mismatch | Client integrity check or binding comparison produces `integrity_failure` | B.3a produces resource payload/identity integrity failure; host returns 502 | Compatible fail-closed outcome |
| Graph revision missing | Projection service maps missing pinned revision to 404/not found | Exact repository read maps to `graph_revision_not_found` / 404 | Compatible status category |
| Graph head advances after capture | Exact `revision_pin` remains in request/selection; projection context/cache also reads current head and includes it in cache key | Transport calls `get_revision(world_id, revision_id)` and explicitly forbids head reads | Exact result remains pinned, but Buddy read counts cannot be reused as DMS proof |
| Browser reload | #510 reference design stores exact world/campaign/scope/revision/node; MAGIC-D3 publication recovery rereads exact IDs | No browser surface | Product parity belongs to Buddy |
| Process restart | Durable graph/publication state survives; process-local resident/cache/prewarm state is rebuilt | DMS host has no durable resolver cache and recomputes exact hydration | Semantically safe; deployment/readiness proof remains |

“Both fail” is not treated as parity. The cases above retain the owning status
category and identify where the current paths differ.

## 6. Runtime and transport topology

### Current Buddy topology

```text
Browser / Plan / Build
  → Buddy live-control server
  → file-backed World Graph root configured by DUNGEONMIND_WORLD_GRAPH_ROOT
  → exact World Graph projection with revision_pin
  → Buddy POST /api/live/threats/query-hydration
  → Buddy DungeonMindStatblockV1Client
  → configured statblock-v1 provider:
       GET /api/internal/dungeonbuddy/v1/statblocks/{sb_id}/revisions/{rev_id}
       X-DungeonBuddy-Internal-Key
  → exact response validation and digest check
  → ThreatQueryHydrationResponseV1
  → shared Threat sheet / Plan presentation
```

The current accepted-statblock client is also used by statblock candidate
generation, validation, acceptance, and readiness services. Moving mechanics
authority does not delete the whole `DungeonMindStatblockV1Client`; only its
exact Threat hydration role is a future replacement candidate.

### Candidate DungeonMind topology

```text
Buddy product-side shadow seam
  → POST /v1/dnd/threat-mechanics-hydrations
       Authorization: Bearer <capability>
  → DungeonMind exact graph repository get_revision(world_id, graph_revision_id)
  → DungeonMind D&D profile reader and binding derivation
  → DungeonMind statblock_resource_resolver
  → configured provider exact-revision GET with X-DungeonBuddy-Internal-Key
  → no-store verified hydration
```

Repository-defined facts are the route paths, environment variable names,
header names, exact ID grammars, and bounded/redirect/error behavior. The
following are `OPERATIONAL_UNKNOWN` because no deployment/bootstrap contract
is present in this reconnaissance:

- which running service owns the `/api/internal/dungeonbuddy/v1/statblocks`
  route in the target dogfood environment;
- where the separate DungeonMind hydration host is deployed;
- how the Buddy bearer capability and provider internal key are provisioned;
- whether both services can read the same exact graph revision or whether a
  snapshot/profile bridge must be supplied;
- production base URLs and network policy.

These unknowns block a live shadow dogfood, but they do not justify adding
deployment code to this docs-only PR.

An honest cutover must not require a second graph load merely to compare
mechanics. It must reuse one exact Buddy reference and pass a governed
representation of that identity to DungeonMind. At present that
representation does not exist.

## 7. Surface integration map

The product-side convergence point is the shared Threat hydration service,
not a separate Plan or Build mechanics implementation. On committed Buddy
`main`, Plan renders the Threat sheet, while Build still renders the generic
graph object projection. The shared Plan/Build Threat sheet is open PR #512
behavior, not merged-main evidence.

- `ThreatSheetProjection.tsx` builds the request from the exact selection
  tuple and calls `postThreatQueryHydration`.
- `threatSheetViewModel.ts` verifies response world, campaign, scope, and
  revision; selects the exact Threat node ID; maps every binding; and turns
  incomplete “available” payloads into integrity failure rather than rendering
  them.
- The open #512 head adds `ThreatCampaignGlance` and `ThreatHoverMechanics`
  over the same binding/view-model path and makes that path shared with Build.
  It does not establish a second mechanics authority, but it remains
  branch-only until merged.
- The open #510 head carries the exact graph reference through Build Canvas
  save/reload/open behavior. Its exact scope examples and required Latchling
  dogfood remain branch-only/pending.

Plan and Build therefore have one reasonable future shadow insertion point:
the Buddy server-side mechanics orchestration after the exact graph selection
and before the current result is rendered. A hidden comparison there can
leave the current Buddy result authoritative while recording a comparison
outcome. It must not be implemented separately in Plan and Build, and it must
not create a second user-facing projection model.

The current product-side reference does preserve the exact graph tuple
`world + campaign + scope + revision + Threat node ID`. It does not preserve a
DungeonMind `obj:*` ID or a DMS `mechbind:*` identity. No surface currently
owns a mechanics binding independently of the server query service.

## 8. Optimization interaction audit

### OPT01 — completed projection cache

Owner: `src/graph_memory/world_projection_cache.py`.

- The cache key includes resolved root, world, campaign, selected exact
  revision, selected resident generation, current head revision/generation,
  focus, admissibility, scope, and query text.
- A cache hit returns a previously built projection for the same key; a miss
  changes latency only.
- The cache can be disabled with `DMB_WORLD_GRAPH_PROJECTION_CACHE=0`.
- Cache invalidation cannot replace a pinned revision with another revision.
- It does not hydrate mechanics.

### OPT02 — post-commit resident prewarm

Owner: `apps/live_control_server/services/world_graph_prewarm.py` plus
`src/graph_memory/kernel/world_revision_ready.py`.

- The process-local mailbox carries the exact committed world and revision.
- The coordinator checks that the current head still names the notification,
  then loads that exact resident revision.
- It records graph/revision/contribution/source/head read counters.
- A superseded notification is dropped; it does not select another revision.
- It does not call the statblock client or perform mechanics hydration.

### OPT03 — bounded projection recipe replay

Owner: `apps/live_control_server/services/world_graph_projection_recipes.py`.

- Recipes are eligible only for unpinned, queryless, cache-enabled projection
  requests.
- A ready revision is replayed by adding that exact revision as the pin.
- The recipe registry is process-local, bounded, TTL-limited, and not durable.
- It checks the exact current head before replay and stops when superseded.
- It warms graph/projection work only; it does not select a mechanics resource.

A future DungeonMind shadow call belongs outside these projection builders,
after a single exact Threat/binding representation has been admitted. The
optimization layer is non-authoritative and passes this audit. It is not a
cutover blocker.

## 9. Duplicate authority and demolition inventory

| Buddy path/symbol | Authority today | Current consumers | Future replacement candidate | Earliest deletion gate | Retain reason |
|---|---|---|---|---|---|
| `query_threats_with_hydration` | Product-side exact Threat query and hydration orchestration | Threat sheet, Plan/shared graph reference consumers | Replace only the mechanics sub-call after shadow parity | Exact identity/profile bridge, shadow success, bounded dogfood, promotion decision | Product API and failure orchestration remain Buddy-owned |
| `_hydrate_binding` | Per-binding status, multiplicity, and current client call | `query_threats_with_hydration` | Compare DMS result at this seam | Field-by-field parity for all binding statuses and no first-winner drift | One shared comparison point |
| `DungeonMindStatblockV1Client.get_exact_revision` | Current exact provider read and integrity check | Threat hydration plus statblock authoring/acceptance paths | Threat-specific DMS hydration call only | DMS promotion for Threat mechanics, not all statblock operations | Other statblock producer workflows still need the client |
| `build_statblock_v1_client` | Client factory/config boundary | hydration, validation, candidate/revision services | No whole-factory deletion in this slice | Independent callers migrated and separately proved | Shared producer integration |
| `/api/live/threats/query-hydration` | Buddy product API and stable UI failure surface | Plan/Threat sheet and future Build/shared lens | Keep route; change backend authority only after promotion | Product contract compatibility and rollback switch | User-facing orchestration belongs to Buddy |
| `ThreatSheetProjection.tsx` and `threatSheetViewModel.ts` | Presentation and exact result selection | Plan/shared graph reference surfaces | Keep presentation; feed promoted result | UI parity and dogfood | Presentation is not mechanics authority |
| Publication/accepted-revision stores | Accepted statblock producer authority and receipts | Workbench/publication/validation flows | Never delete merely because hydration authority moves | Separate producer migration decision | Mechanics producer remains Buddy-owned |

No deletion is recommended by this reconnaissance. Mechanics authority moving
does not transfer publication, product orchestration, presentation, or
durable-source ownership automatically.

## 10. Candidate cutover shapes

### Shape 1 — conformance-only / pure adapter first

```text
New public/durable contract: not required if kept as a fixture/test adapter;
  the mapping itself must still be governed before production use.
New write path: no.
New deployment dependency: no.
User-visible behavior: none.
Failure-parity risk: low and directly testable.
Rollback boundary: delete/revert the adapter fixture; current Buddy path is untouched.
Duplicate path retained: yes, current Buddy path remains sole authority.
Promotion evidence: exact target response bytes, profile/object/relationship
mapping, canonical digest equality, and adversarial disagreement tests. Use
Latchling only if its supplemental publication evidence becomes reproducible.
```

This is the smallest useful next shape, but its input facts are not yet
complete. It should be the next implementation slice after the missing
mapping decision, not a live consumer.

### Shape 2 — product shadow consumer first

```text
New public/durable contract: a Buddy-to-DungeonMind request/response comparison
  seam and likely operational result telemetry.
New write path: not inherently; comparison must remain non-authoritative.
New deployment dependency: yes, Buddy must reach the bearer-gated DMS host.
User-visible behavior: none while shadowed.
Failure-parity risk: high until the identity/profile and target digest proofs exist.
Rollback boundary: disable the shadow call and retain current hydration.
Duplicate path retained: yes, deliberately.
Promotion evidence: all parity rows, exact call counts, no secret/body leaks,
  repeated exact calls, head-advance behavior, and bounded dogfood.
```

This shape is premature. It would hide an unresolved graph identity mapping
inside a production comparison path.

### Shape 3 — direct authority cutover

```text
New public/durable contract: yes, Buddy product behavior would depend on DMS.
New write path: no required mechanics write, but new operational dependency.
New deployment dependency: yes.
User-visible behavior: likely failure/status changes.
Failure-parity risk: unacceptable before shadow proof.
Rollback boundary: difficult because current path would be removed or bypassed.
Duplicate path retained: no, prematurely.
Promotion evidence: all conformance, shadow, and bounded product dogfood gates.
```

This shape is rejected. A happy-path provider call is not evidence that
authority can move safely.

## 11. Required next decision/proof

```text
Disposition: NOT_READY_FOR_BRIDGE

Primary blocking fact(s):
1. DungeonMind ADR-0005 / threat-v1 / DndThreatMechanicsBinding encode the
   narrow Threat proving domain as if it were the durable
   world-object/mechanics substrate. Play now requires distinct first-class
   Threat, NPC, and PlayerCharacter world identities plus mechanics
   attachment that does not require contextual hostility.
2. Persistent Threat identity and contextual dnd5e:threatens are currently
   conflated; Buddy uses_statblock cannot be renamed into threatens.
3. Mechanics binding currently fails closed with object_not_threatening when
   no dnd5e:threatens edge exists, which falsifies allied-NPC and PC mechanics.

Secondary facts retained as later bridge/parity concerns (not the reason to
stop before a semantic re-anchor):
- Committed Tripod has no uses_statblock / accepted binding (no_binding).
- Latchling values are operator dogfood, committed_unverified, not a
  committed-main fixture.
- Target-specific provider digest equivalence and provider/schema/media
  mapping remain ungoverned until the post-re-anchor conformance bridge.

Conflicting contracts/paths:
- Buddy: threat:* + uses_statblock + ThreatStatblockBindingV1
  (`src/graph_memory/union_supergraph/statblock_binding.py`)
- DungeonMind: obj:* + dnd5e:creature + dnd5e:threatens +
  DndThreatMechanicsBinding
  (`src/dungeonmind_dnd/contracts/mechanics_resources.py`,
   `src/dungeonmind_dnd/application/threat_mechanics.py`)
- Play product freeze: Threat / NPC / PlayerCharacter distinct first-class
  kinds; KERNEL-0 before CombatSourceLocator / durable Play contracts
  (`Docs/Roadmaps/ROADMAP-play-world-object-combat-projection.md`)
- Buddy current hydration:
  `apps/live_control_server/services/threat_query_hydration.py`
- DungeonMind exact transport:
  `src/dungeonmind_dnd/application/threat_mechanics_transport.py`

Smallest decision or proof required before implementation:
DungeonMind must reopen/extend the accepted D&D semantic contract in an
additive/versioned slice:

  DND: re-anchor world-object kinds and mechanics attachment for
  DungeonBuddy cutover

That slice freezes Threat/NPC/PlayerCharacter world identity, keeps
contextual dnd5e:threatens independent, defines mechanics attachment without
hostility, specializes Threat/NPC statblock attachment, documents the PC
mechanics plug-in, supersedes rather than edits current profile/vocabulary
revisions, and names lossless Buddy→obj:* / external-resource mapping
requirements. Do not manufacture a Latchling fixture PR first. Do not harden
Play CombatSourceLocator / NPC / PC durable contracts against the old Buddy
identity model. Do not add a live shadow call or change product authority
until the re-anchored contract exists.
```

## 12. Evidence and command record

### Repository commands

These baseline commands were run before writing the report and appending the
handback; the final changed-path set is recorded in the PR handback.

Buddy PR #515 worktree:

```text
git rev-parse HEAD
3f5a328d8326c8695e7a17be72a5a8bc22a24bae

git status --short
<empty>

git diff --check
<no output>

git diff --name-only 9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd...HEAD
Docs/Plans/HANDOFF-statblock-dungeonmind-authority-cutover-reconnaissance.md
```

DungeonMind main worktree:

```text
git rev-parse HEAD
7c311ae0d0d59d7379dee38780be509970fb3a8c

git status --short
<empty>
```

GitHub PR metadata was queried with:

```text
gh api repos/Drakosfire/DungeonMindBuddy/pulls/510
gh api repos/Drakosfire/DungeonMindBuddy/pulls/512
gh api repos/Drakosfire/DungeonMindBuddy/pulls/515
```

The exact results are recorded in §1. PR #515 had no reviews or comments at
the time of reconnaissance.

### Focused test commands

The following tests were run against the current PR worktrees, not invented
fixtures:

```text
uv run pytest -q tests/test_statblock_binding_graph_contract.py tests/test_threat_query_hydration.py tests/test_dungeonmind_statblocks_client.py
........................................................................ [ 62%]
...........................................                              [100%]
115 passed in 4.25s

uv run pytest -q tests/unit/test_dnd_threat_mechanics.py tests/unit/test_dnd_threat_mechanics_transport_service.py tests/unit/test_dnd_threat_mechanics_api.py tests/unit/test_import_boundaries.py
....................................................                     [100%]
52 passed, 1 skipped
```

The one skipped DungeonMind test module requires the optional `fastapi`
dependency (`tests/unit/test_dnd_threat_mechanics_api.py:12`). The remaining
52 tests passed, including B.3a integrity, exact-revision transport,
unexpected-repository-error classification, and import-boundary checks. No
failure is being treated as green or waived by this report.

## 13. Scope and stop-condition audit

- No Buddy production source changed.
- No DungeonMind source changed.
- No API/schema/type contract changed.
- No graph write, binding persistence, provider discovery, retry, fallback,
  cache, prewarm, deployment, secret provisioning, UI, or duplicate-path
  deletion was added.
- No path outside the PR #515 docs allowlist is required.
- The named successor remains false and is reframed to DungeonMind ownership:
  `DND: re-anchor world-object kinds and mechanics attachment for DungeonBuddy cutover`.
- The later Buddy conformance bridge remains false:
  `STATBLOCK: adapt published Buddy world-object/mechanics identity into re-anchored DungeonMind D&D profile`.
- The later shadow consumer remains false:
  `STATBLOCK: shadow verify Buddy Threat hydration through DungeonMind`.

The reconnaissance is complete as a truthful not-ready result. The primary
blocker is the accepted D&D semantic/mechanics contract shape under Play
pressure, not the absence of a target-specific Mireward fixture. Secondary
mapping and digest concerns remain named for the post-re-anchor bridge.
