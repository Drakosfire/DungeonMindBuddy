---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Campaign Supergraph / CUTOVER — exact Eldyrwild DungeonMind v6 adoption bundle
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-eldyrwild-dungeonmind-v6-adoption-bundle.md
  - Branch / PR: agent/cutover-eldyrwild-dungeonmind-v6-adoption-bundle / `CUTOVER: seal exact Eldyrwild DungeonMind v6 adoption bundle`

  ## Verification pointer
  - Design anchor: DungeonMind PR #32 merge `3d34d53b1c24862da32cf5f9f25e9b05b6ba5441`
  - Buddy source anchor at design time: `0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96`
  - Implementation base/head: <PIN_AFTER_CUTOVER_STATE_SYNC> / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and exact sealed bundle SHA are the review contract. This
  body is transport metadata.
---

# HANDOFF — seal exact Eldyrwild DungeonMind v6 existing-world adoption bundle

**Created:** 2026-08-15  
**Status:** DESIGNED — **DO NOT DISPATCH CODE** until this CUTOVER state-authority sync merges, then replace every `PIN_AFTER_CUTOVER_STATE_SYNC` with that exact merge SHA before implementation proceeds.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-eldyrwild-dungeonmind-v6-adoption-bundle.md`  
**Conversation/workstream:** `Campaign Supergraph / CUTOVER — exact Eldyrwild DungeonMind v6 adoption bundle`  
**Flow / owner:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW  
**Design-time Buddy anchor:** `0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96`  
**Implementation base:** `PIN_AFTER_CUTOVER_STATE_SYNC`  
**DungeonMind consumer pin:** `3d34d53b1c24862da32cf5f9f25e9b05b6ba5441`  
**Suggested branch:** `agent/cutover-eldyrwild-dungeonmind-v6-adoption-bundle`  
**PR title:** `CUTOVER: seal exact Eldyrwild DungeonMind v6 adoption bundle`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## Dispatch gate — repair CUTOVER state authority first

This handoff is complete enough to design the technical slice. CODE remains
illegal until this CUTOVER state-authority sync merges and
`PIN_AFTER_CUTOVER_STATE_SYNC` is replaced with that merge SHA.

At design time Buddy `main` was exactly:

```text
0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96
```

This documents PR is the required CUTOVER state-authority sync. Dispatch base
for the sync itself is current `origin/main`:

```text
bc80f7125499817050f08abc79b71b87d327b2a9
```

which is Merge pull request #596 (`PLAY: durable-run-binding`). That PLAY lane
is no longer an open write-lease competitor. Current repository law still
required the CUTOVER tracker/roadmap/status/handoff set to agree before the
next dependent CODE dispatch. Before this sync they did not.

Before this sync, Campaign Supergraph authorities still claimed, among other
stale facts:

```text
Captain/Thrin alias package is next
five dual-sense relationships still block package construction
DungeonMind existing-world adoption seam is still future/blocked
DungeonMind pin = be76acc997c5fbcb8ceaa090969ec051afa6051d
```

Repository/external authority had already advanced through:

```text
Buddy PR #587  Captain/Thrin alias package               MERGED
Buddy PR #588  dual-sense decomposition package         MERGED
DungeonMind #31 relationship endpoint aspects v6        MERGED
DungeonMind #32 atomic existing-world adoption boundary MERGED
```

This documents PR is the guarded CUTOVER state-authority sync that updates:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-eldyrwild-dungeonmind-v6-adoption-bundle.md
```

The sync records:

```text
#587 DONE / merged alias package authority
#588 DONE / merged dual-sense package authority
DungeonMind #31 DONE / dm_union_graph_v6 aspect representation
DungeonMind #32 DONE / dm_existing_world_adoption_bundle_v1 atomic boundary
this bundle producer = next CUTOVER implementation slice
DungeonMind product authority cutover = still BLOCKED
five Buddy relationship STOPs = still STOP until durable DungeonMind adoption + remeasurement
canonical Eldyrwild = rev:0c644e56b45bcaac709012206e3e41c2
canonical payload = 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
Buddy lock remains be76acc… until the producer slice repins to 3d34d53…
```

Do **not** modify stable architecture merely to record sequencing. If the sync
finds an actual architecture contradiction, stop and re-brief instead.

After this sync merges:

1. re-read current `main`;
2. record its exact merge SHA as `PIN_AFTER_CUTOVER_STATE_SYNC` in this handoff;
3. re-run `scripts/steward_preflight.py` against this handoff;
4. re-check open PRs and current write leases;
5. only then dispatch CODE.

---

## §1 Mission and merge-ready invariant

**Mission:** CUTOVER can produce one canonical, non-mutating
`dm_existing_world_adoption_bundle_v1` for the exact current Eldyrwild World
Graph so the already-merged DungeonMind #32 adoption boundary has a complete,
source-grounded artifact to consume in the next operator slice.

**Merge-ready invariant:** given the one integrity-attested Eldyrwild source
revision, the current source/identity/contribution authority, the current
Captain/Thrin alias proof, the sealed dual-sense package, and the exact pinned
DungeonMind #32 contracts, the producer deterministically emits **one and only
one canonical bundle byte sequence** whose graph/history/source contents are
complete and internally closed, whose v6 aspect semantics admit all five
previous relationship STOPs without changing Buddy identity, and whose build
performs zero live Buddy mutation and zero DungeonMind persistence mutation.
Any source drift, package drift, unaccounted durable element, lossy history
mapping, counterfeit semantic catalog, or dependency mismatch fails closed and
produces no replacement bundle.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes**, if this remains an offline producer only. Reading, translating, sealing, and verifying one bundle are one capability. Applying it to DungeonMind is a separate successor. |
| Most likely adversarial sequence | Load current Buddy store → accept caller-provided package/proof/catalog pins → translate against mismatched authority → seal apparently valid bundle. The producer must instead mint authority from exact reads and internally recomputed hashes. |
| Will §7 detect that failure? | Yes. Adversarial tests swap store/revision, alter #588 bytes, counterfeit `world-object-v5`, change history rows after attestation, and require refusal before bundle write. |
| Easiest owning boundary to under-test | Historical translation. A final graph can look correct while contributions, identity decisions, source revisions, alias lineage, or mechanics-specialization history were silently dropped. §7 requires complete source/history accounting independent of graph parse success. |
| Fact that forces stop/split | Any durable Buddy history semantics required for correspondence cannot be represented by the existing DungeonMind #32 bundle contracts without inventing a second archival schema, abusing `diagnostics`, or adding a new public/runtime export API. |

### One important count rule

Do **not** interpret:

```text
CONTRIBUTION_HISTORY = 5291
```

as “there are 5,291 `GraphContribution` rows.” It is a conformance-classified
durable-element count. The producer must independently enumerate the real
contribution ledger and prove both:

```text
actual contribution records translated exactly once
5291 classified CONTRIBUTION_HISTORY elements accounted for by the resulting source/history mapping
```

Likewise, `IDENTITY_HISTORY = 20` is a measured conformance expectation, not a
license to force a list to length 20. Measure current reality.

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; `Docs/Process/STEWARD-CYCLE.md`; Campaign Supergraph architecture; DungeonMind ADR-0018; DungeonMind #32 adoption-boundary contract/handoff |
| Design-time Buddy anchor | `0ec7c6711ada5a05b5dc301ce7a5394ff2d7ee96` |
| Implementation base | `PIN_AFTER_CUTOVER_STATE_SYNC` — must be the exact merge SHA of the required sync above |
| Canonical Buddy world | `eldyrwild` |
| Canonical Buddy revision | `rev:0c644e56b45bcaac709012206e3e41c2` |
| Canonical Buddy graph payload SHA-256 | `0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2` |
| Buddy predecessor #587 | merge `cc5dc6ddba0750924a46cf13843498c124937e5f`; current Captain/Thrin source-grounded alias package |
| Current alias proof regression anchor | `package_proof_sha256=24881d132f79d7692c5bad0fe5ad605765f9e25c7f83189546f075e1633d5ff6`; fixture SHA `14f653850f78040c15bc5d3fef34b7bb43dde74951afbf2c83600c29ad2829d7` — regression only; regenerate proof from the attested current store |
| Buddy predecessor #588 | merge `3415fcf96a28a29907e248e047ea0d2e75c50071` |
| #588 raw package | `graph_data/approved_graph_corrections/eldyrwild/relationship-dual-sense-decomposition-v1/manifest.json` |
| #588 raw package SHA-256 | `53986158ec9ad326481755f7baef9f425d973f34a65b789f96e92e3f55208ef8` |
| #588 canonical payload SHA-256 | `d71453926b0475ca686b9c94452688d5a6b285afab304c35d48035c252240207` |
| #566 predecessor repair SHA-256 | `96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247` |
| DungeonMind #31 | merge `351af975598ee6f28d65634da150ac83d9b79808`; `dm_union_graph_v6`; assertion-scoped endpoint aspects |
| DungeonMind #32 / consumer pin | merge `3d34d53b1c24862da32cf5f9f25e9b05b6ba5441`; `dm_existing_world_adoption_bundle_v1` |
| D&D vocabulary pin | `world-object-v5`; canonical catalog SHA-256 `f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8` |
| Exact input consumed | integrity-loaded Buddy revision + durable source/evidence/contribution/identity ledgers + regenerated #587 proof + exact #588 bytes + pinned DungeonMind contracts |
| Named successor | `CUTOVER — apply the sealed Eldyrwild existing-world bundle to a real DungeonMind PostgreSQL target and prove terminal receipt/retry/recovery/readback` |
| What remains false | DungeonMind has not adopted Eldyrwild; Buddy product authority does not move; five relationship STOPs remain STOP; no transport/admin adoption surface is introduced |
| Explicit non-goals | no Buddy graph mutation; no DungeonMind DB write; no HTTP/admin route; no generic export framework; no new DungeonMind schema; no broad relationship cleanup; no synthetic companion world-object identities |
| Branch / isolated checkout | `agent/cutover-eldyrwild-dungeonmind-v6-adoption-bundle` in its own worktree/equivalent checkout |
| Runtime/state ownership | Buddy world graph is **read-only** for this lane. Bundle output is repo-local. DungeonMind PostgreSQL is not opened. No app server/port required. |
| State-authority sync after merge | `Docs/Plans/PR-TRACKER-campaign-supergraph.md`, `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`, `Docs/Design/STATUS-world-graph-continuity-spine.md`, this handoff status/completion record. Do not dispatch the operator successor until that guarded sync is complete. |

### Parallel-lane assessment

At design time open Buddy PR #596 was PLAY-owned. It has since merged as
`bc80f7125499817050f08abc79b71b87d327b2a9`. Expected source-write overlap
with the later CODE lease is **none**.

`pyproject.toml` / `uv.lock` remain repository-wide dependency collision
hotspots owned by the CODE slice. Before CODE dispatch, re-run preflight and
inspect open PRs. If another lane has since leased either dependency file,
serialize or transfer ownership; do not “let Git sort it out.”

The DungeonMind repin may alter the shared Python environment even without a
source-write collision. After the repin, run the relevant PLAY/import boundary
regressions so the dependency change cannot silently invalidate another lane.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Exact source load | Existing CUTOVER analyzers can load/attest current revision; no v6 adoption artifact exists | Refuse any world/revision/payload mismatch before translation | Yes | offline CUTOVER builder |
| Dependency binding | Buddy still pins DungeonMind `be76acc…` | Exact dependency is #32 merge `3d34d53…`; lockfile agrees | Yes | package/lock + import test |
| Alias authority | #587 proof/fixture exists | Regenerate from attested current store and exact contribution sources; do not trust fixture as live authority | Yes | alias proof boundary |
| Dual-sense authority | #588 package exists | Load exact file bytes, recompute raw/self hash, bind exact revision/payload, call pinned DungeonMind materialization adapter | Yes | package loader + DM adapter |
| Source/evidence translation | Diagnostic conformance proves representability but no adoption records are sealed | Every graph/history source reference closes over bundled `SourceArtifactV2`/`SourceRevision` | Yes | source translator + DM parser |
| Contribution history | Buddy durable ledger exists; #32 stores DM `GraphContribution` rows but does not translate | Every durable contribution selected by exact ledger authority is mapped once; source digests/status/order/accounting are proven | Yes | history translator |
| Identity history | Buddy identity decisions remain Buddy-shaped | Every durable decision in the pinned revision/history authority is mapped once with no silent semantic drop | Yes | history translator |
| v6 graph | No real Eldyrwild `dm_union_graph_v6` payload | Full deterministic graph with exact object IDs, assertion metadata, aliases, properties, relationships, evidence, three aspects, five endpoint selections | Yes | graph builder + versioned reader |
| D&D semantics | Five dual-sense edges are still Buddy STOPs | The bundle graph is locally admissible under exact built-in world-object-v5 through aspect selection; Buddy source remains unchanged | Yes | D&D conformance |
| Canonical artifact | No existing bundle | Exact canonical bytes from DungeonMind #32 helper written to one repo artifact path; raw file SHA recorded | Yes | bundle serializer |
| Retry/check | No producer | Rebuild from unchanged exact inputs yields byte-identical file/SHA; `--check` makes no writes | Yes | CLI/build tool |
| Source drift | Current canonical world may evolve before dispatch | Fail `stale_source_authority`; never silently “use latest” | Yes | loader |
| History gap | A Buddy-only durable field may lack a legitimate DM mapping | Fail `history_mapping_gap`; do not hide it in diagnostics or invent another schema | Yes | history translator |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| store A + manifest/pins B | Refuse before any bundle bytes are emitted | T03 |
| genuine #588 semantic content with one changed raw byte/reseal omitted | Raw/self-hash validation refuses | T06 |
| caller passes widened fake `world-object-v5` still labeled v5 | Pinned DM adapter refuses `vocabulary_pin_mismatch` | T10 |
| alias fixture says PASS but fresh attested store differs | Fresh proof wins; build refuses stale fixture/policy | T05 |
| contribution index lists row whose on-disk source digest differs from pinned replay digest | Refuse; no source-history coercion | T14 |
| history translator encounters unsupported Buddy-only semantically material field | Refuse `history_mapping_gap`; no bundle replacement | T17 |
| aspect ID from object A attached to endpoint object B | DM v6 reader refuses wrong-owner aspect | T25 |
| graph parses but one evidence source revision is absent from bundle | #32 parser refuses source closure | T28 |
| same semantic rows returned in different iteration order | Canonical graph/bundle bytes remain identical | T31 |
| builder crashes before final atomic artifact replace | Existing checked-in bundle remains byte-identical or absent; no partial authoritative file | T34 |
| user runs build/check with live Buddy root | Before/after world head, revision tree digest, source authority digest, contribution ledger digest, identity digest identical | T35 |
| bundle build succeeds | Five Buddy STOPs remain STOP; no `CUTOVER_READY` claim | T39 |

---

## §4 Files in scope — write lease

The checked-in handoff created by the prerequisite state sync becomes part of
the implementation review contract, so the implementation lane may update only
its dispatch-base/evidence/completion fields there.

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-CUTOVER-eldyrwild-dungeonmind-v6-adoption-bundle.md` | Pin exact post-sync implementation base and record review evidence; no architectural rewrite |
| Modify | `pyproject.toml` | Repin DungeonMind dependency to exact #32 merge `3d34d53b1c24862da32cf5f9f25e9b05b6ba5441` |
| Modify | `uv.lock` | Lock exact DungeonMind dependency graph corresponding to `pyproject.toml` |
| Create | `apps/live_control_server/integrations/dungeonmind_kernel/eldyrwild_existing_world_adoption_bundle_v1.py` | Pure Buddy→DungeonMind translation, deterministic IDs, graph construction, bundle composition; no filesystem mutation except through caller-supplied artifact writer |
| Create | `scripts/build_eldyrwild_dungeonmind_v6_adoption_bundle.py` | Offline source-attestation/orchestration boundary; exact reads, fresh proof generation, build/check, atomic repo artifact write |
| Create | `graph_data/approved_existing_world_adoptions/eldyrwild/dungeonmind-v6/bundle.json` | Exact canonical `dm_existing_world_adoption_bundle_v1` artifact consumed by successor operator slice |
| Create | `tests/test_eldyrwild_existing_world_adoption_bundle_v1.py` | Hermetic contract/adversarial/unit proof for translator and deterministic bundle semantics |
| Create | `tests/test_build_eldyrwild_dungeonmind_v6_adoption_bundle.py` | Offline builder/atomic-write/no-mutation/CLI proof |

### Bounded discovery exception

```text
Directory:
  tests/
Maximum additional paths:
  1
Allowed path kinds:
  one existing import-boundary or dependency-smoke test only
Decision rule:
  use only if the DungeonMind repin cannot be proved against shared import/runtime
  compatibility in the two new tests without duplicating an existing repository-level
  dependency boundary test. Production paths are NOT covered by this exception.
```

A required production path outside the eight paths above is a STOP. In
particular, do not quietly modify `whole_world_conformance_v4.py`/`v5.py`,
Graph Kernel stores, routes, repositories, or DungeonMind itself to make the
bundle easier to construct.

### Offline ledger-read rule

The build script may use existing Buddy durable ledger **read** functions needed
to enumerate the exact contribution/identity/source authority for this one
migration artifact. It must not add a generic runtime/public history-export API
in this PR.

If construction proves a new public Kernel read seam is actually required to
avoid an architecture violation, STOP and split that seam into its own PR. Do
not introduce it under the bounded discovery exception.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/kernel/**` | No new public Kernel API or mutation contract; source system stays authoritative/read-only |
| `src/graph_memory/world_supergraph/**` | No store-format or ledger mutation to fit migration |
| `apps/live_control_server/main.py` | PLAY #596 / central router collision; no runtime route required |
| `apps/live_control_server/routes/**` | No HTTP/admin/operator workflow in producer slice |
| `apps/live_control_server/services/play_*` | Active PLAY ownership |
| `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Active PLAY sequencing authority |
| `graph_data/approved_graph_corrections/**` | Existing #566/#588 authority is immutable input, never rewritten |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_alias_assertion_package_after_shadow_alias_remove_v1.json` | #587 regression evidence is input/history, not live authority and not rewritten |
| DungeonMind repository | #31/#32 contracts are consumed exactly; no sibling-repo edits |
| DungeonMind PostgreSQL | Producer only; no mutation, migration, receipt, or publication |
| Buddy canonical Eldyrwild files | Read-only; no graph head/revision/contribution/identity/source mutation |
| product-authority selection | Still Buddy; adoption bundle existence is not cutover |
| five Buddy relationship STOP statuses | Stay STOP until successor durable adoption + Buddy remeasurement |
| generic migration/export framework | One exact Eldyrwild artifact only |
| synthetic companion world-object IDs | #588/#31 explicitly preserve one identity with assertion-scoped semantic aspects |

---

## §6 Implementation contract

```text
Input:
  exact Buddy source repository anchor = PIN_AFTER_CUTOVER_STATE_SYNC
  exact world_id = eldyrwild
  exact revision = rev:0c644e56b45bcaac709012206e3e41c2
  exact graph payload SHA = 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
  integrity-loaded UnionSupergraphStore
  durable contribution/source/identity ledgers corresponding to that authority
  fresh Captain/Thrin alias package proof from that exact store
  exact #588 manifest raw bytes
  DungeonMind dependency = 3d34d53b1c24862da32cf5f9f25e9b05b6ba5441
  exact built-in world-object-v5 catalog

Output:
  graph_data/approved_existing_world_adoptions/eldyrwild/dungeonmind-v6/bundle.json
  bytes exactly equal DungeonMind existing_world_adoption_bundle_canonical_bytes(bundle)
  one printed/review-recorded raw file SHA-256

Invariant:
  §1

Failure behavior:
  any source/package/dependency/history/semantic/closure/determinism mismatch
  → typed/fixed reason code
  → no replacement authoritative bundle
  → no Buddy mutation
  → no DungeonMind mutation

Replay / idempotency:
  same exact source authority → byte-identical bundle and SHA
  changed source revision/payload/history/package → refuse until steward re-anchors/re-briefs
  --check on matching artifact → success, zero writes
  --check on drift → nonzero refusal, zero writes
  --write → temp file + fsync + atomic replace only after complete validation

Trust boundary:
  Verifies internally:
    exact source revision/payload integrity
    exact source/history closure and digests
    fresh alias proof binding
    #588 raw/canonical package hashes
    exact bundled world-object-v5 identity/catalog digest
    v6 graph parse and endpoint-aspect ownership
    D&D predicate endpoint admission
    #32 bundle canonical bytes and source closure
  Records/trusts without proving:
    human/operator authorization to later apply this migration
    whether a future PostgreSQL target is pristine
    whether Buddy product authority should move after adoption
```

### 6.1 Dependency pin is part of this capability

Current Buddy still depends on DungeonMind PR #30:

```text
be76acc997c5fbcb8ceaa090969ec051afa6051d
```

The producer requires contracts merged in #31/#32. Repin exactly to:

```text
3d34d53b1c24862da32cf5f9f25e9b05b6ba5441
```

Do not pin a branch, tag, `main`, range, or “latest.” Tests must prove the loaded
DungeonMind package exposes:

```text
dm_union_graph_v6
dm_relationship_endpoint_aspect_v1
dm_existing_world_adoption_bundle_v1
existing_world_adoption_bundle_canonical_bytes
DndRelationshipAspectMaterializationPlanV1
world-object-v5 ref with catalog SHA f9fd5420...
```

### 6.2 Adoption identity and provenance

Use one stable adoption intent ID independent of bundle bytes:

```text
adoption:eldyrwild:rev:0c644e56b45bcaac709012206e3e41c2:dm_union_graph_v6
```

This deliberately lets DungeonMind #32 detect “same adoption intent, different
bytes” as a conflict after durable adoption rather than silently creating a new
migration identity.

Required bundle provenance:

```text
producer_id = DungeonMindBuddy
producer_revision = PIN_AFTER_CUTOVER_STATE_SYNC
source_world_revision_id = rev:0c644e56b45bcaac709012206e3e41c2
source_graph_payload_sha256 = 0640d7ef...
```

`producer_revision` means the exact **source repository anchor from which this
migration authority was dispatched**, not the later generator commit SHA. This
avoids a circular “bundle contains the commit that contains the bundle” scheme.

Required `authority_refs` must include at least:

1. fresh Captain/Thrin alias package proof
   - schema: `dmb_alias_assertion_package_conformance_v1`
   - identifier: `alias_assertion_package_v1`
   - SHA: fresh proof digest, expected at design time `24881d132f79d7692c5bad0fe5ad605765f9e25c7f83189546f075e1633d5ff6`
2. dual-sense package
   - schema: `dmb_relationship_dual_sense_decomposition_v1`
   - identifier: package identifier from exact manifest
   - SHA: raw manifest SHA `53986158ec9ad326481755f7baef9f425d973f34a65b789f96e92e3f55208ef8`
3. exact contribution-history source authority digest computed by the producer
4. exact identity-history source authority digest computed by the producer
5. any already-existing source repair authority required to explain the four projected kind repairs, using its real existing schema/identifier and raw SHA `96cc26fc...`

Do not invent a self-attesting `bundle_sha256` inside the bundle. DungeonMind
#32 computes that from consumed canonical bytes.

### 6.3 Source authority translation

Translate Buddy `GraphMemorySourceArtifact` to DungeonMind `SourceArtifactV2`
without collapsing distinct axes.

| Buddy source field | DungeonMind field | Rule |
|---|---|---|
| `source_artifact_id` | `source_artifact_id` | preserve exact ID |
| `source_domain` | `source_domain_key` | preserve exact opaque Buddy value |
| known accepted generic domain | `source_domain` | reuse the existing CUTOVER v5 explicit mapping only; never coerce unknown to `OTHER` |
| `world_id` absent but source is in exact Eldyrwild store | `world_id` | set `eldyrwild` only because membership in the attested world is the authority; conflicting non-null value refuses |
| `campaign_id` | `campaign_id` | preserve |
| `session_id` | `session_id` | preserve; do not fabricate from fictional time |
| `uri` | `uri` | preserve |
| `authority_state` | `review_state` | draft/reviewed/canonical; this is review standing, **not** evidentiary `authority` |
| no exact Buddy evidentiary-authority field | `authority` | `null`; do not infer primary/derived/reference |
| `visibility_state` | `source_visibility_state` | preserve opaque producer classification |
| no exact access-policy field | `visibility` | `null`; do not infer GM/player merely from source visibility classification |
| `artifact_kind` | `artifact_kind` | preserve |
| `document_class` | `document_class` | preserve |
| workspace doc id + revision | `workspace_document_ref` | map only when both are present and valid |
| `lineage` | `lineage` | preserve JSON exactly |
| `status` | `status` | active/superseded exact mapping |
| timestamps | created/updated | parse exact valid datetime; nonblank malformed timestamp refuses instead of disappearing |

Source revision policy:

```text
if an exact Buddy source_revision_id already exists in durable references:
  preserve that id and prove its artifact/hash lineage

else if artifact has a content_sha256:
  mint one deterministic migration source-revision id from
  (world_id, source_artifact_id, normalized exact content_sha256)
  and use body_storage=external with the exact source URI/locator

else:
  current_revision_id = null
  no fake SourceRevision row
```

A referenced source revision without enough source authority to construct an
exact `SourceRevision` is `source_revision_mapping_gap` and blocks merge.

Deterministic migration source-revision IDs must use a versioned canonical tuple
and a collision-resistant full/long digest. Never use label, list position, or
filesystem order.

### 6.4 Evidence translation

Every Buddy evidence row represented in the v6 graph becomes exact
`GraphEvidenceRecordV2`/`EvidenceRefV2` shape using the existing CUTOVER source
domain mapping:

```text
evidence_ref_id            preserve
source_artifact_id         preserve
source_revision_id         mapped exact source revision or null
source_domain_key          preserve exact Buddy value
source_domain              accepted generic mapping or null
role/open/highlight flags  preserve
session_id                 preserve as real-world session ref
span/locator/URI fields    preserve independently
```

Do not infer fictional chronology from `session_id`.

### 6.5 Historical contribution translation

Enumerate the exact durable contribution ledger; do not infer the list from the
5291 conformance count.

Required source-kind map:

```text
source_extraction                -> extraction
standing_context                 -> standing_context
graph_review_authored_assertion  -> graph_review
identity_decision                -> identity_decision
manual_import                    -> manual_import
```

Contribution IDs, world ID, source IDs, extraction profile, produced time,
campaign scope, lifecycle status, supersession identity, and authored-by value
must preserve semantic correspondence.

Buddy's three assertion partitions map to one DungeonMind assertion list:

```text
candidate_assertions -> acceptance_state=candidate
accepted_assertions  -> acceptance_state=accepted
rejected_assertions  -> acceptance_state=rejected
```

The producer must validate that each row's stored state is compatible with the
owning partition. Do not silently normalize contradictory partition/state data.

Buddy assertion `value` is structured JSON while DungeonMind v1 history value
is string/null. A translation is permitted only if it is **deterministic and
reversible**. Use canonical JSON text for the full Buddy JSON value and prove a
round trip back to the exact source value. Do not pretty-print, stringify Python
reprs, or discard `{}`/null distinctions.

For every other Buddy-only contribution/assertion field, the implementation
must produce an explicit accounting classification:

```text
DIRECT_MAP
REVERSIBLE_NORMALIZATION
OPERATIONAL_REDUNDANCY_PROVEN
UNREPRESENTABLE
```

`UNREPRESENTABLE` is a merge blocker.

`OPERATIONAL_REDUNDANCY_PROVEN` is permitted only when the field's entire
meaning is already represented by another translated first-class DungeonMind
field **and** the exact raw Buddy contribution-history digest is carried in
`source_provenance.authority_refs`.

Do **not** put unresolved mentions, assertion corrections, evidence identities,
merge replay details, or arbitrary Buddy source rows into DungeonMind
`diagnostics` merely to claim losslessness. If first-class correspondence is
not possible, stop and split a DungeonMind contract change.

Each translated contribution must also satisfy #32 source closure for the
contribution and every assertion.

### 6.6 Identity-decision history translation

Enumerate exact durable identity decisions from the pinned source authority.
Do not derive history merely from final aliases/redirects.

Preserve exact decision ID, world ID, decision kind, actor, reason, reversible
flag, status, alias, supersession identity, and timestamp wherever the target
contract has the corresponding semantic field.

Derive DungeonMind `subject_object_ids` / `target_object_ids` by a
**decision-kind-specific** mapping from Buddy's subject/target/affected-node
shape. Each of the actual decision kinds present in Eldyrwild must have a named
test case and inverse/source-correspondence proof.

Buddy-specific `merge_side_effects`, source candidate identity, affected-node
lists, alias-remove lineage, split/unmerge details, or other fields may not be
silently dropped. Apply the same accounting classes as contribution history.
Any semantically material `UNREPRESENTABLE` field is a STOP requiring a
DungeonMind contract successor before this bundle can merge.

### 6.7 Durable graph assertion IDs

Do not change Buddy world-object IDs. Do not create synthetic companion objects
for semantic aspects.

Existing source-grounded DungeonMind assertion IDs already produced by approved
proofs must be reused exactly. In particular the current #587 proof presently
produces:

```text
Captain       assertion:cutover-alias:efac2be8dcac08b80b6a71ee
Thrin Branchborn assertion:cutover-alias:ed979aedbe0b7885e4ef1471
```

Regenerate and verify rather than hardcoding them as authority.

For required DungeonMind assertions that have no existing durable target ID,
derive a migration assertion ID from one canonical, versioned tuple containing:

```text
world_id
source_world_revision_id
assertion_family
stable Buddy durable element identity
sorted exact source assertion/support IDs
semantic payload needed to disambiguate the assertion
```

Required prefix:

```text
assertion:cutover-v6:<digest>
```

The derivation function itself is part of this migration contract and must be
one implementation, one test matrix, deterministic across list/map iteration,
and collision-checked across the whole payload.

`aspect_key` remains a semantic label, not identity. Relationship endpoints
reference exact **aspect assertion IDs**.

### 6.8 Exact three aspects and five endpoint selections

The #588 package and DungeonMind #31 materialization plan must produce exactly
these secondary senses on the same original object IDs:

| Object ID | Buddy primary/stored sense | Secondary aspect key | DungeonMind kind |
|---|---|---|---|
| `loc:wizard_college` | location | `organization` | `dnd5e:faction` |
| `node:meat_distribution_network_session9` | party | `site` | `dnd5e:location` |
| `node:hempholm_folk_revelry` | group | `event` | `dnd5e:event` |

Exactly these five relationship edges use the assigned aspect endpoint:

```text
edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of
edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9
edge:node:headmaster_tinkerbright:leads:loc:wizard_college
edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry
edge:pc:caelynn:participates_in:node:hempholm_folk_revelry
```

Every retained edge uses the primary kind unless another existing approved
adapter explicitly governs it.

No global kind rewrite is permitted for any of the three objects.

### 6.9 Knowledge assertion metadata

Every object existence, alias, summary, property, aspect, and relationship
assertion in v6 must carry full `KnowledgeAssertionMetadataV1`:

```text
assertion_id
campaign_scope
visibility
epistemic_kind
canon_state
evidence_ref_ids (non-empty)
session_refs
temporal_scope
```

Derive metadata from exact current Buddy assertion support/evidence/source
lineage and existing approved CUTOVER policies. The graph builder must not
invent permissive defaults.

Specific prohibitions:

```text
missing visibility -> do not default to player
missing epistemic state -> do not default to fact
session_id -> do not infer fictional_time_ref
unknown temporal information -> TemporalScopeKind.UNKNOWN, not WORLD_TIMELESS
```

Aspect metadata must be source-grounded. It cannot use the #588 package file as
its sole “evidence”; the package authorizes semantic decomposition, while
underlying source evidence grounds the knowledge assertion.

### 6.10 Full v6 graph construction

The graph payload must use exact merged DungeonMind `dm_union_graph_v6` and
required discriminator:

```text
relationship_endpoint_aspect_schema = dm_relationship_endpoint_aspect_v1
```

Deterministic nested ordering is required before the bundle serializer sees the
payload:

```text
objects by object_id
aliases/properties/aspects by assertion_id (with stable tie-breakers)
relationships by relationship_id
evidence by evidence_ref_id
all metadata ID lists sorted only where order is semantically unordered
```

Do not sort lists whose order is itself source semantics.

The output graph must be accepted by the exact DungeonMind versioned graph
reader and have zero global assertion-ID collisions.

### 6.11 Mechanics specialization accounting

`uses_statblock` is not to be opportunistically relabeled as a D&D semantic
relationship. The current canonical CUTOVER relationship inventory retains
three mechanics-specialization attachments.

The producer must reuse the existing #521/current-v5 mechanics-specialization
semantics and prove every retained mechanics attachment is accounted for in the
bundle's portable graph/source/history authority without inventing a semantic
predicate.

If the #32 bundle contract cannot preserve the required current mechanics
meaning, that is `mechanics_mapping_gap` and a STOP. Do not make the count zero
by omission.

### 6.12 Whole-world completeness ledger

Before sealing, enumerate every durable element from the exact current Buddy
revision and assign exactly one owning disposition:

```text
V6_GRAPH_ASSERTION
SOURCE_OR_EVIDENCE_AUTHORITY
CONTRIBUTION_HISTORY
IDENTITY_HISTORY
MECHANICS_SPECIALIZATION
APPROVED_MIGRATION_ASPECT
```

Required:

```text
unaccounted_durable_elements = 0
multiply_accounted_elements = 0 unless the overlap is explicitly expected and proven non-duplicative
ATTRIBUTE_ASSERTION = 0
EVIDENCE_PROVENANCE = 0 under regenerated #587 package authority
WORLD_OBJECT_KIND = 0
five prior RELATIONSHIP_PREDICATE STOPs = represented in v6 bundle via #588/#31 aspects
```

The five Buddy source-system STOP statuses themselves do not change here. This
is bundle representation, not external durable adoption.

### 6.13 D&D semantic proof

Use the exact bundled DungeonMind loader for `world-object-v5`. Do not allow a
caller-supplied same-name catalog to become semantic authority.

For every semantic relationship in the output graph:

```text
resolve effective source kind using selected aspect assertion when present
resolve effective target kind using selected aspect assertion when present
validate predicate source/object kind admission against exact world-object-v5
```

All semantic relationships must pass. Mechanics-specialization rows are
accounted separately and are not forced through D&D predicate admission.

### 6.14 Canonical bundle bytes

Construct the exact merged `ExistingWorldAdoptionBundleV1` and serialize only
through DungeonMind #32:

```python
existing_world_adoption_bundle_canonical_bytes(bundle)
```

Do not reimplement “equivalent” canonicalization in Buddy.

The raw checked-in `bundle.json` bytes must equal that helper output exactly,
including its newline behavior.

The build script prints at minimum:

```text
world_id
source revision
source graph payload SHA
DungeonMind dependency SHA
actual contribution record count
actual identity decision record count
CONTRIBUTION_HISTORY classified element count
IDENTITY_HISTORY classified element count
object count
relationship count
aspect count = 3
aspect-selected relationship count = 5
mechanics specialization count
source artifact count
source revision count
evidence count
bundle byte length
bundle SHA-256
graph payload canonical SHA-256
expected first DungeonMind revision ID (computed, not applied)
```

Do not store a sidecar digest as independent authority. The file bytes are
authority; SHA is recomputed by verification and recorded in review handback.

### 6.15 Artifact size gate

If canonical `bundle.json` exceeds **50 MiB**, stop before committing it and
report the measured size. Do not silently introduce Git LFS, object storage, a
compressed wrapper, chunk manifest, or transport protocol. Those are separate
artifact/transport contracts requiring steward design.

### 6.16 Atomic repo artifact write

`--write` may only replace the repo artifact after every validation above has
passed.

Required write pattern:

```text
build complete bytes in memory/temp
validate exact DungeonMind parse/closure
fsync temp file
atomic replace bundle.json
```

A build failure before replace must leave the previous file untouched.

`--check` performs no writes and compares regenerated canonical bytes to the
checked-in artifact.

---

## §7 Evidence required to merge

Use these test IDs in the implementation handback.

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Expected evidence / stop condition |
|---|---|---|---|---|
| T01 | Exact DungeonMind #32 dependency pin | package/import | contract | pyproject + lock resolve exact `3d34d53…`; wrong SHA fails test |
| T02 | Exact canonical Buddy revision/payload | builder source loader | adversarial | exact source passes; other head/revision/payload refuses |
| T03 | Store/manifest mix-and-match attack refused | source attestation | adversarial | store A + pins B cannot mint build authority |
| T04 | Current world/source/history read is non-mutating | builder | regression | before/after digests equal |
| T05 | #587 alias proof is regenerated, not fixture-trusted | alias proof | adversarial | stale fixture cannot authorize current store; fresh package has exactly Captain/Thrin, residuals `[]` |
| T06 | #588 exact raw package SHA/self-hash | package loader | contract/adversarial | exact SHA `539861…`, canonical payload `d714…`; byte drift refuses |
| T07 | #588 exact world/revision/payload binding | package loader | adversarial | foreign revision package refuses |
| T08 | Exactly three aspect directives | DM #31 adapter | contract | exact object/aspect/kind rows |
| T09 | Exactly five endpoint directives | DM #31 adapter | contract | exact five edge IDs |
| T10 | Counterfeit world-object-v5 rejected | D&D adapter | adversarial | same revision label + widened predicate still refuses `vocabulary_pin_mismatch` |
| T11 | SourceArtifactV2 translation preserves axes | source adapter | round-trip | authority/review/visibility/source-key distinctions preserved; no invented OTHER/GM |
| T12 | SourceRevision closure | source adapter | contract | referenced revisions exist and belong to exact artifact |
| T13 | Evidence v2 translation/closure | graph builder | round-trip | evidence IDs/locators/session refs preserved; source closure passes |
| T14 | Contribution ledger digest/replay authority exact | history loader | adversarial | changed record vs revision-bound digest refuses |
| T15 | Real contribution record count measured | history loader | contract | equals exact durable ledger enumeration; not hardcoded 5291 |
| T16 | Contribution partition/source-kind/value mappings reversible | history adapter | round-trip | every translated record corresponds to exact Buddy source semantics |
| T17 | No unaccounted/lossy contribution field | history adapter | adversarial | semantically material unmapped field yields `history_mapping_gap` |
| T18 | Actual identity-decision ledger measured | history loader | contract | every exact durable decision included once; no forced count |
| T19 | Decision-kind mapping complete | history adapter | table-driven | each actual kind maps subject/target/alias/status/supersession correctly |
| T20 | No unaccounted/lossy identity field | history adapter | adversarial | material unmapped side effect yields `history_mapping_gap` |
| T21 | Raw contribution/identity history authority digests are bound into provenance | bundle | contract | recompute from exact source rows and match refs |
| T22 | Existing Captain/Thrin assertion IDs reused | graph builder | regression | fresh #587 IDs equal graph alias assertion IDs |
| T23 | New assertion ID derivation deterministic | graph builder | property/regression | reorder input maps/lists → same IDs; semantic tuple change → different ID |
| T24 | Global assertion IDs unique | DM v6 reader | adversarial | intentional collision refuses |
| T25 | Aspect ownership exact | DM v6 reader | adversarial | wrong-owner/missing aspect ref refuses |
| T26 | Primary fallback preserved | graph builder | regression | unrelated relationships use primary kind |
| T27 | D&D admission complete | semantic validator | contract | every semantic relation admitted against exact built-in v5 |
| T28 | Bundle source closure complete | DM #32 parser | adversarial | missing artifact/revision used by graph/history refuses |
| T29 | Full v6 graph parses under exact versioned reader | DM reader | contract | world/schema/discriminator/aspects all valid |
| T30 | Whole-world completeness | CUTOVER analyzer | regression | zero unaccounted; required class counts/dispositions prove closure |
| T31 | Deterministic canonical bytes | serializer | property | reordered semantically unordered inputs → identical bundle bytes/SHA |
| T32 | Raw bundle file equals #32 canonical helper bytes | file verifier | contract | byte-for-byte equality including newline |
| T33 | Bundle has no self-asserted hash trust | contract | regression | no `bundle_sha256` field; verifier hashes consumed bytes |
| T34 | Atomic artifact replacement | build script | failure injection | pre-replace failure leaves prior file unchanged/no partial file |
| T35 | Zero Buddy mutation on realistic build/check | live/offline builder | dogfood | head/tree/source/contribution/identity digests unchanged |
| T36 | Zero DungeonMind mutation | build script/import | boundary | no repository/DB/adopt call reachable from producer |
| T37 | Artifact size within accepted repo transport | build script | contract | <= 50 MiB or STOP |
| T38 | Shared dependency repin does not break repository import boundary | repo regression | regression | applicable import/test suite remains green |
| T39 | No premature CUTOVER claim | report/handoff | regression | producer result explicitly says adoption not performed; five Buddy STOPs remain STOP |
| T40 | `--check` is exact idempotent verification | build script | regression | checked-in bytes regenerate identically; zero writes |

### Exact verification commands

After implementation base is pinned, the author must provide exact results for:

```bash
uv sync --locked

uv run pytest -q \
  tests/test_eldyrwild_existing_world_adoption_bundle_v1.py \
  tests/test_build_eldyrwild_dungeonmind_v6_adoption_bundle.py

uv run python scripts/build_eldyrwild_dungeonmind_v6_adoption_bundle.py --check

# Full repository unit/regression suite used by this repo's current CI contract.
# Record the exact command actually used; do not silently substitute a smaller suite.
uv run pytest -q

uv run ruff check \
  apps/live_control_server/integrations/dungeonmind_kernel/eldyrwild_existing_world_adoption_bundle_v1.py \
  scripts/build_eldyrwild_dungeonmind_v6_adoption_bundle.py \
  tests/test_eldyrwild_existing_world_adoption_bundle_v1.py \
  tests/test_build_eldyrwild_dungeonmind_v6_adoption_bundle.py

uv run pyright

git diff --check
git diff --name-only PIN_AFTER_CUTOVER_STATE_SYNC...HEAD

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-CUTOVER-eldyrwild-dungeonmind-v6-adoption-bundle.md
```

If repo-wide Ruff/test state has a pre-existing baseline failure, reproduce the
same exact command on base and head and prove head adds no failures. Do not
expand the lease to fix unrelated baseline debt.

### Minimal realistic proof

This slice is non-mutating, but it still requires one real-source dogfood build
against the current local Eldyrwild world root:

```text
1. capture Buddy current head + canonical revision/payload + world tree digest
2. capture source-authority, contribution-ledger, identity-ledger digests
3. run producer --check (or --write once when intentionally regenerating artifact)
4. capture the same Buddy digests again
5. prove all Buddy source digests/head are byte-identical
6. prove no DungeonMind PostgreSQL connection/adoption occurred
7. record emitted bundle SHA/size/count ledger
```

The checked-in artifact must then pass hermetic `--check` from the same source
authority. If reviewer infrastructure cannot access the real Buddy world root,
separate author-local live proof from reviewer hermetic/CI proof; do not claim
an independent live rerun happened.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. exact implementation base after the prerequisite CUTOVER state sync;
3. §1 mission/invariant disposition;
4. actual changed paths vs §4, including bounded discovery use (`none` expected);
5. exact DungeonMind dependency SHA from lock resolution;
6. exact source world/revision/payload pins re-proved;
7. fresh #587 package proof SHA and exact two alias assertion IDs;
8. #588 raw + canonical payload hashes;
9. actual contribution record count **and separately** `CONTRIBUTION_HISTORY` element count;
10. actual identity decision record count **and separately** `IDENTITY_HISTORY` element count;
11. history field-accounting table: DIRECT_MAP / REVERSIBLE_NORMALIZATION / OPERATIONAL_REDUNDANCY_PROVEN / UNREPRESENTABLE;
12. complete graph counts, source/evidence counts, aspect=3, selected relationships=5, mechanics count;
13. zero-unaccounted completeness proof;
14. bundle file byte length + SHA-256 + graph payload SHA + expected first DungeonMind revision ID;
15. T01–T40 evidence disposition and provenance (author-local / independent / CI / dogfood);
16. before/after no-mutation digests;
17. nano-commit/fix story;
18. baseline failures/waivers;
19. prior finding ledger on re-review;
20. explicit statement that the named operator successor remains unimplemented and Buddy remains product authority.

Review-cycle law comes from `AGENTS.md`; do not restate/renumber cycles based on
fix commits. One formal judgment against one distinct head SHA is one cycle.

---

## §9 Acceptance rubric

- [ ] Prerequisite CUTOVER state-authority sync landed and the handoff base is the exact sync merge SHA.
- [ ] One capability only: exact non-mutating Eldyrwild adoption bundle producer.
- [ ] Buddy dependency is exact DungeonMind #32 merge `3d34d53b1c24862da32cf5f9f25e9b05b6ba5441`; lock agrees.
- [ ] Source load proves exact `eldyrwild` revision `rev:0c644e56…` and payload `0640d7ef…` or refuses.
- [ ] #587 alias authority is freshly regenerated from the attested store and still proves exactly Captain + Thrin with no residual.
- [ ] #588 raw/canonical package hashes are internally recomputed and exact.
- [ ] Exact three secondary aspects and exact five endpoint selections are present; no companion object IDs exist.
- [ ] All graph assertions have source-grounded `KnowledgeAssertionMetadataV1` and globally unique assertion IDs.
- [ ] Full `dm_union_graph_v6` parses with the required aspect discriminator and correct aspect ownership.
- [ ] Every semantic relationship passes exact built-in world-object-v5 admission; counterfeit same-name catalog fails.
- [ ] Source artifacts/evidence/source revisions are complete and close every graph/history reference.
- [ ] Actual contribution ledger records are enumerated and translated once; no 5291-as-row-count shortcut exists.
- [ ] Actual identity decision records are enumerated and translated once; no forced-count shortcut exists.
- [ ] Every Buddy history field is explicitly accounted; no material field is hidden in `diagnostics` or silently dropped.
- [ ] Current conformance history expectations are freshly measured, not copied from handoff constants.
- [ ] Whole-world completeness has zero unaccounted durable elements.
- [ ] Three current `uses_statblock` mechanics-specialization attachments are accounted without predicate relabeling or omission.
- [ ] Bundle bytes are exactly DungeonMind #32 canonical bytes and checked in at the one leased artifact path.
- [ ] Bundle is <= 50 MiB or the PR stops before inventing transport.
- [ ] Rebuild/reorder is byte deterministic; `--check` is no-write.
- [ ] Real-source before/after Buddy mutation digests are identical.
- [ ] No DungeonMind PostgreSQL/adoption path is invoked.
- [ ] No paths outside §4/bounded discovery were changed.
- [ ] Active parallel lanes did not acquire conflicting dependency/state ownership without an explicit serialization decision.
- [ ] Five Buddy relationship STOPs remain STOP and `CUTOVER_NOT_READY` remains truthful after bundle build.
- [ ] Named successor is explicit operator/transport adoption + real PostgreSQL receipt/readback/retry/recovery proof.

---

## Stop conditions

Stop and report instead of expanding when any of these appears:

- the prerequisite state-authority sync has not landed or mutable CUTOVER docs still disagree;
- current Buddy canonical revision/payload differs from the pins in this handoff;
- current #587 proof no longer yields exactly the two approved alias rows;
- #588 raw or canonical package hash differs;
- DungeonMind dependency cannot pin exactly to #32 without unrelated compatibility work;
- a required Buddy durable history record cannot be enumerated without introducing a new public/runtime Kernel API;
- a Buddy history field is semantically material and cannot be represented/accounted without a new DungeonMind contract;
- implementing “losslessness” would require hiding source payloads in `diagnostics` or inventing an archival side schema;
- current mechanics-specialization meaning cannot survive the #32 bundle contract;
- a fourth aspect or sixth aspect-selected relationship appears;
- the five assigned relationships require object splitting/global kind rewrite instead of #31 aspect semantics;
- a new source/evidence/domain mapping would require semantic guessing;
- whole-world completeness has any unaccounted durable element;
- canonical bundle exceeds 50 MiB;
- a live Buddy mutation, DungeonMind DB mutation, HTTP/admin workflow, or product-authority switch becomes necessary;
- required production path is outside §4;
- another active lane owns `pyproject.toml`, `uv.lock`, the handoff, or another required path;
- repo-wide dependency repin creates a new unrelated failure that cannot be explained as baseline-equivalent;
- merge readiness depends on an operator waiver not already authorized.

Report using the repository stop format:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```

---

## Named successor — real DungeonMind adoption

After this producer merges **and** its CUTOVER state-authority sync is complete,
re-anchor both repositories and design one explicit operator/transport slice
that consumes the exact sealed bundle bytes against a real DungeonMind
PostgreSQL target.

That successor owns:

```text
pristine-target preflight
explicit adoption invocation
terminal dm_existing_world_adoption_receipt_v1
exact first DungeonMind Eldyrwild revision
source/history/graph readback
exact retry
same-world/different-bundle conflict
uncertain-outcome recovery probe
normal post-adoption reads
```

Only after that durable external adoption exists should Buddy remeasure:

```text
five relationship STOPs
whole-world CUTOVER disposition
product-authority transition eligibility
```

A successful bundle build is **necessary but not sufficient** for CUTOVER.
