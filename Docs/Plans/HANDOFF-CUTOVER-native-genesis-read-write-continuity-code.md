---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2C3 — native genesis read/write continuity
  - Flow: CUTOVER
  - Direction: CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md`
  - Frozen design authority: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §4
  - Exact implementation/dispatch base: `d96a21363fd0decbcb8c4390f951a6316b53060c`
  - Exact #647 design base: `f1fd3f6aa4270de2af44a4e249f127332622b785`
  - Design PR #647 merge: `d96a21363fd0decbcb8c4390f951a6316b53060c`
  - Current Buddy `main`: `555a9c7965aca47a24536277b9b36ae569a7285a`
  - Accepted design head: `1f5676c204ee917d18efd553106c07306541e820`
  - Design review: Cycle 7 PASS-equivalent `5034239255`
  - D.2C2 implementation #645 merge: `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`
  - DungeonMind provider pin: `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`

  ## Mission
  Generalize Buddy's DungeonMind-native authority binder across both legal genesis families so a D.2C2-reviewed first-world `D_0` can immediately use the same mounted projection, retrieval, mutation-context, and governed existing-parent write paths as an adopted existing world, without weakening the Eldyrwild Buddy-A → D_A bridge.

  ## Merge contract
  - one shared `DirectAuthorityBinding` supports existing-world adoption and reviewed first-world initialization
  - first-world bindings have `legacy_buddy_revision_id=None`; no fake Buddy revision is invented
  - `D_0` and later DungeonMind revision pins pass through unchanged
  - adopted Buddy-A still rewrites exactly to adopted D_A
  - `D_0` is a legal parent for existing-parent governed publication
  - both genesis receipts, receipt-without-head, and head-without-genesis fail as integrity
  - no new DungeonMind provider contract, first-world-only read factory, Buddy fallback, D.2C4 authoring work, or D.3 demolition work
  - one real-PostgreSQL witness proves first-world D_0 → native read/retrieval → WorldGraphAuthority → one legal D_1 → native read, plus adopted-world regression
  - predecessor/state authorities are synchronized backward-looking; D.2C4 and D.3 remain false
---

# HANDOFF — CUTOVER D.2C3 CODE: native genesis read/write continuity

**Created:** 2026-08-26  
**Status:** ACTIVE — IMPLEMENTATION IN PROGRESS / Buddy #651  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md`  
**Conversation/workstream:** `DungeonBuddy / Campaign Supergraph CUTOVER`  
**Flow / owner:** `CUTOVER`  
**Direction:** CODE → REVIEW  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Branch:** `cutover/native-genesis-read-write-continuity`  
**Base revision:** `d96a21363fd0decbcb8c4390f951a6316b53060c` (#647 merge / original dispatch)  
**#647 exact design base:** `f1fd3f6aa4270de2af44a4e249f127332622b785`  
**Current Buddy `main`:** `555a9c7965aca47a24536277b9b36ae569a7285a` (PLAY-SURFACE cockpit re-anchor; merged into this repaired head)  
**PR title:** `CUTOVER: native genesis read/write continuity`  
**Frozen design authority:** `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §4  
**Design PR #647 merge:** `d96a21363fd0decbcb8c4390f951a6316b53060c`  
**Accepted design head:** `1f5676c204ee917d18efd553106c07306541e820`  
**Design review:** Cycle 7 PASS-equivalent `5034239255`  
**D.2C2 implementation:** Buddy #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`; accepted head `f772db17e00cbe2c0198ae53f169a10a6332a3ed`; Cycle 2 PASS-equivalent `5026532158`  
**DungeonMind provider pin:** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`  
**Named successor:** D.2C4 manual Graph Review authoring continuity  

> This is the parseable implementation dispatch wrapper authorized by merged #647. The merged design is semantic authority. If CODE discovers a conflict with that design, a new DungeonMind provider need, or a second capability, stop and re-brief rather than choosing locally.

## §1 Mission and merge-ready invariant

**Mission:** A world created through D.2C2 reviewed first-world initialization can immediately use DungeonBuddy's normal DungeonMind-native read and governed-write paths, while existing adopted worlds retain their exact legacy revision bridge.

**Merge-ready invariant:** **The one shared DungeonMind `DirectAuthorityBinding` recognizes exactly two reciprocal-exclusive genesis authorities—existing-world adoption and reviewed first-world initialization—and every mounted native projection, retrieval, mutation-context, and existing-parent publication derives revision truth from that binding. Reviewed-init worlds use real DungeonMind `D_0`/descendant IDs with no fake Buddy revision; adopted worlds preserve the exact Buddy-A → D_A compatibility rewrite. Contradictory or unrecognized genesis state fails closed as integrity.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every changed path consumes the same genesis binding and revision algebra. |
| Most likely adversarial sequence | D.2C2 creates D_0 → binder still asks for adoption receipt → reads/writes fail, or a repair invents a fake legacy revision and accidentally rewrites a real D_0 pin. |
| Will §7 detect that failure? | Yes. The owning PostgreSQL witness starts with real D.2C2 creation, immediately exercises mounted native reads and `WorldGraphAuthority`, then publishes/reads a child and separately reruns adopted A→D_A behavior. |
| Easiest owning boundary to under-test | Shared write path: direct reads may pass while `_classify_parent_revision()` still rejects or misclassifies D_0. The witness must publish a real child through an already-landed authority path. |
| Fact that forces stop/split | Any required DungeonMind provider/repository contract change; any supported genesis family beyond the two frozen families; any need to migrate Graph Review manual authoring or remove legacy engine routes in this slice. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Merged #647, `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §4 |
| Base revision | `d96a21363fd0decbcb8c4390f951a6316b53060c` |
| Predecessor contract | D.2C2 #645 reviewed first-world initialization; DungeonMind reviewed-init provider #46 |
| Exact input consumed | `bundle.existing_world_adoptions.get_for_world`, `bundle.reviewed_world_initializations.get_for_world`, `bundle.world_graph.get_head/get_revision`, existing projection/retrieval requests, existing `WorldGraphAuthority` requests |
| Named successor | D.2C4 manual-authoring continuity |
| What remains false | Manual Graph Review authoring still targets legacy overlay/file semantics; mounted legacy graph-engine imports/routes still exist; D.3A/D.3B are not begun. |
| Explicit non-goals | No D.2C4, D.3A/D.3B, authority-mode parser rehome, import blocker, buddy_files removal, UI changes, APP-STATE, provider changes. |
| Branch / isolated checkout | `cutover/native-genesis-read-write-continuity` from exact base above; isolated checkout/worktree required. |
| Parallel lanes / collision hotspots | APP-STATE #650 is MERGED at `cc016661f80416e0816f56349217cf33c53a195f`. PLAY-SURFACE current `main` is `555a9c7965aca47a24536277b9b36ae569a7285a` (cockpit re-anchor; disjoint). Open PLAY-SURFACE #652 does not overlap this lease. This repaired head merged that `main`. CUTOVER state-authority docs remain this lane's hotspot. |
| Runtime/state ownership | Real PostgreSQL authority witness must use an isolated test DB/schema/world IDs; do not share mutable world IDs with another worker. No Buddy world-file mutation is required by the native witness. |
| State-authority sync set after merge | `Docs/Plans/STEWARDS-ANCHOR-cutover.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; ACTIVE_AUTHORITY tracker/roadmap mirrors; `Docs/Design/STATUS-world-graph-continuity-spine.md` if stale; merged #647 design handoff status/facts. |

Before code, re-read `AGENTS.md`, merged #647 §4, current `world_graph_reads.py`, `world_graph_writes.py`, `world_graph_authority_adapter.py`, and the owning first-world/direct-read/authority tests. Re-check current `main` and active PR write leases. If #650 or another lane has acquired any §4 path or the base has materially changed the binder contract, stop/serialize/rebase before editing.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| D.2C2 first-world D_0 → native projection | Binder requires existing-world adoption receipt, so reviewed-init-only world cannot bind. | Verified reviewed-init receipt + head creates first-world binding and projection reads D_0. | Yes | direct read service + real PG |
| D.2C2 first-world D_0 → native retrieval | Same adoption-only binder failure. | Search and exact-object retrieval operate on D_0 using normal retrieval service. | Yes | direct retrieval service + real PG |
| `WorldGraphAuthority.current_head/read_revision/mutation_context` on D_0 world | Shared write service inherits adoption-only binder. | Same shared binding exposes D_0/head and builds mutation context. | Yes | authority adapter + real PG |
| Governed child publish with parent D_0 | Parent classifier receives binding whose legacy ID is currently mandatory. | D_0 is a real DungeonMind parent; existing-parent publication creates one D_1. | Yes | governed write publication + real PG |
| Exact retry/recover child | Existing D.2A/D.2B algebra exists but has never been proved from D_0 genesis. | Same operation recovers the same child; no duplicate head/revision. | Yes | authority adapter + repository |
| Adopted Buddy-A revision pin | Existing path rewrites Buddy-A to adopted D_A. | Exactly unchanged. | Yes | direct read binder/pin algebra |
| Both genesis receipts | No valid supported state. | `authority_integrity`; no fallback or arbitrary preference. | Yes | binder unit/adapter |
| Recognized receipt without head | Contradictory state. | `authority_integrity`, not availability/missing. | Yes | binder unit/adapter |
| Head with neither receipt | Existing binder reports adoption receipt missing. | Integrity: published authority exists without recognized genesis. | Yes | binder unit/adapter |
| No head and neither receipt | Uninitialized/not-adopted. | Preserve ordinary not-initialized/not-adopted fail-closed behavior; do not mislabel as a valid initialized world. | Yes | binder unit/adapter |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| reviewed-init receipt → D_0 → no adoption receipt → projection | Projection succeeds from reviewed-init binding; no Buddy fallback. | PG witness A |
| D_0 binding → request revision pin `D_0` | Pin passes through unchanged; no A→D_A rewrite. | pin unit + PG witness |
| adopted receipt A→D_A → request pin A | Still rewrites exactly to D_A. | adopted regression |
| reviewed-init D_0 → mutation context → publish child → retry | One D_1, parent D_0, same retry/recovery result. | PG witness A |
| both receipts exist | Binder refuses as integrity before read/write service is trusted. | fail-closed unit/integration |
| head exists, receipt rows absent/corrupt | Binder refuses as integrity; never invents third genesis. | fail-closed unit/integration |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | Generalize receipt-backed binder, optional legacy revision, genesis discriminator, and pin/integrity algebra. Do not rewrite DungeonMind graph-payload evidence. |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` | Make parent/write classification consume optional legacy bridge without changing publication semantics. |
| Modify if required | `apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py` | Consume shared generalized binding only; no new authority family. |
| Modify if required | `apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py` | Share verified reviewed-init receipt error mapping only if needed; do not alter first-world initialization semantics. |
| Modify | `tests/test_cutover_dungeonmind_first_world_initialization.py` | Extend owning first-world evidence through native continuity where appropriate. |
| Modify | `tests/test_cutover_direct_dungeonmind_world_graph_reads.py` | Two-genesis binder/pin/integrity regression coverage. |
| Modify | `tests/test_cutover_dungeonmind_world_graph_authority.py` | D_0 parent/current-head/read/mutation/retry authority proof. |
| Create if clearer | `tests/test_cutover_native_genesis_continuity.py` | One focused real-PG two-genesis witness instead of overloading existing suites. |
| Modify regression only if needed | `tests/test_cutover_threat_authority_port_integration.py` | D.2A child-publication regression from generalized binder. |
| Modify regression only if needed | `tests/test_cutover_worldbuilding_authority_port_integration.py` | D.2B regression; no semantic changes. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-cutover.md` | Backward-looking predecessor/design state sync. |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Record #645/#647 completed truth; D.2C3 active; successors blocked. |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Same truthful sequencing sync. |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` | Mirror authoritative tracker state. |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | Mirror authoritative roadmap state. |
| Modify if stale | `Docs/Design/STATUS-world-graph-continuity-spine.md` | Align current continuity claim only if it still claims D.2C2/D.3 old state. |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` | Backward-looking status metadata only: #647 merged/accepted review facts; do not alter frozen §4/§5/§6 semantics. |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md` | Execution/evidence handback metadata. |

**Bounded discovery exception:**

```text
Directory: tests/
Maximum additional paths: 3
Allowed path kinds: existing CUTOVER direct-read/adoption/authority regression tests only
Decision rule: a path may be added only when it already owns one §3 behavior and moving the proof would duplicate fixtures or weaken owning-boundary evidence. No product/service path is covered by this exception.
```

A required production path outside this lease is a stop report. Do not absorb it because the diff is small.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/application_state/**` | APP-STATE #650 ownership / separate persistence invariant. |
| `apps/live_control_server/services/play_*.py` | APP-STATE/Play lane. |
| `tests/application_state/**`, `tests/test_play_*.py`, `tests/test_live_play_*.py` | APP-STATE #650 regression ownership. |
| `apps/live_control_server/routes/graph_authoring.py` and graph-authoring services/UI | D.2C4 successor. |
| `apps/live-control-ui/**` | No UI behavior changes in D.2C3. |
| `apps/live_control_server/config.py` authority selector | D.3A parser rehome. |
| `apps/live_control_server/services/world_graph_prewarm.py` | D.3A mounted-engine excision. |
| `apps/live_control_server/routes/world_graph_bootstrap.py` / bootstrap service | D.3A retirement. |
| `apps/live_control_server/services/union_supergraph_projection_adapter.py` | D.3A store-preview retirement. |
| `graph_memory/kernel/**`, `graph_memory/world_supergraph/**`, `graph_memory/union_supergraph/**` | D.3A/D.3B; no demolition here. |
| `pyproject.toml`, `uv.lock` | DungeonMind provider pin is already correct; changing provider dependency is a STOP. |
| DungeonMind repository | #647 explicitly requires no new provider/repository contract. |

Do not install the D.3A import blocker and do not remove `buddy_files` compatibility in this slice.

## §6 Implementation contract

```text
Input:
  world_id
  DungeonMind repository bundle
  existing-world adoption receipt (optional)
  reviewed-world initialization receipt (optional)
  current DungeonMind world head (optional)
  existing projection/retrieval/publish requests

Output:
  one DirectAuthorityBinding for exactly one recognized genesis family
  normal native projection/retrieval services
  normal WorldGraphAuthority behavior for a real DungeonMind parent

Invariant:
  exactly one recognized genesis receipt + coherent head determines binding;
  adopted worlds retain A→D_A bridge; reviewed-init worlds have no legacy bridge.

Failure behavior:
  both receipts present            → authority_integrity
  recognized receipt, no head      → authority_integrity
  head, neither receipt            → authority_integrity
  no head, neither receipt         → existing uninitialized/not-adopted fail-closed result
  provider persistence integrity   → authority_integrity, never authority_unavailable
  provider unavailable             → authority_unavailable
  unknown revision pin             → existing revision_not_bridged/not-found behavior

Replay / idempotency:
  same read/pin → same resolved DungeonMind revision
  same governed operation → existing publish/recover algebra, one logical child
  changed operation/parent → existing stale/conflict behavior

Trust boundary:
  Verifies: recognized genesis receipt family, receipt/head coherence, exact bridge identity when adoption exists, exact real DungeonMind revisions/parents.
  Records/trusts without proving: no new facts beyond already-landed provider receipt/revision integrity guarantees.
```

No new durable format or provider command is introduced. The only Buddy value-shape change is `DirectAuthorityBinding` becoming capable of representing the already-real reviewed-init genesis family.

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| adopted native read | adoption receipt + head | A→D_A bridge / native result | no head+no genesis remains not-adopted | 503 authority unavailable | contradictory receipt/head → integrity | immutable revision semantics | deterministic |
| reviewed-init native read | reviewed-init receipt + head | D_0/descendant native result | no head+no genesis remains uninitialized | 503 authority unavailable | both receipts / missing head / orphan head → integrity | immutable revision semantics | deterministic |
| governed child publish | shared binding + sealed parent | one child under real DM parent | missing authority head fails closed | authority unavailable | contradictory genesis → integrity before publish | stale parent unchanged | existing recover/idempotency |

No Buddy-file fallback is permitted for a configured DungeonMind-native path.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Adopted legacy revision A | Exact receipt-owned A maps to receipt D_A. | Any other pin passes through to DM and may fail not-found. | No |
| Reviewed-init D_0 | No legacy alias exists; D_0 is already the real ID. | Never reinterpret D_0 as Buddy identity. | No |
| Both receipt families | Impossible/contradictory world identity. | Integrity failure. | No |
| Head without receipt | Unknown genesis authority. | Integrity failure. | No |

Alias/label/normalized-key identity is not applicable to genesis revision binding.

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| Bind/read adopted world | existing adoption receipt + immutable graph revisions | A→D_A remains exact | read-only deterministic | preserve legacy bridge | no writes |
| Bind/read reviewed-init world | existing reviewed-init receipt + immutable D_0 descendants | D_0 passes through exactly | read-only deterministic | no legacy bridge invented | no writes |
| Publish child of D_0 | existing finalized review/publication + graph revision/head | child parent is sealed D_0/current DM parent | existing recover semantics | same publication family | provider UoW semantics unchanged |

### D. Predecessor → consumer mapping

**Grounding source:** merged #647 §4 plus current DungeonMind repository bundle and Buddy direct read/write code.

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| adoption receipt | optional per world | recognized genesis family A | source Buddy revision + published D_A populate bridge binding | adopted regression |
| reviewed-init receipt | optional per world | recognized genesis family D_0 | published revision populates first revision; legacy ID = None | first-world PG witness |
| `world_graph.get_head` | optional | required when either receipt exists | head ID becomes binding current head | integrity + PG witness |
| adoption `source_world_revision_id` | required only for adoption | exact compatibility pin | A → D_A | direct-read regression |
| reviewed-init `published_revision_id` | required/verified | real genesis revision | pass through unchanged | D_0 projection/retrieval/publish witness |
| both receipts | forbidden | no consumer path | integrity | adversarial test |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Reviewed-init D_0 binds without adoption receipt | real PG + direct service | owning integration | create pristine world through real D.2C2 prepare/confirm, then build native services | one reviewed-init receipt; zero adoption receipts; binding genesis reviewed-init; legacy ID None | any Buddy fallback/fake legacy ID |
| D_0 is natively projectable/retrievable | mounted native read services | owning integration | search + exact-object retrieval immediately after first-world confirm | admitted D_0 result with exact revision identity | helper-only proof or skipped PG |
| WorldGraphAuthority works from D_0 | authority adapter + real PG | owning integration | current_head/read_revision/mutation_context then D.2A or D.2B publish | one legal child whose parent is D_0/sealed DM parent | provider change required |
| Retry/recovery from D_0 stays exact | authority adapter + repository | adversarial integration | replay same operation after child publish/lost-response seam | same child, no duplicate revision/head | changed idempotency contract |
| A→D_A bridge unchanged | direct read + adopted fixture/PG | regression | existing Eldyrwild adoption bridge cohort | exact old bridge behavior | regression |
| Contradictory genesis fails closed | binder | adversarial unit/integration | both receipts; receipt/no-head; head/no-receipt | stable integrity classification | arbitrary preference/fallback |
| No provider expansion | cumulative diff | contract/static | inspect changed paths/imports | no DungeonMind repo edit, no new command/UoW/family | any provider contract need |
| State authorities truthful | docs/state | contract | inspect cumulative state sync | #645 and #647 DONE facts exact; D.2C3 active; D.2C4/D.3 blocked/not done | current slice pre-marked DONE |

Exact verification commands, adjusting only test selection if an owning test is created under the bounded exception:

```bash
uv run pytest tests/test_cutover_dungeonmind_first_world_initialization.py tests/test_cutover_direct_dungeonmind_world_graph_reads.py tests/test_cutover_dungeonmind_world_graph_authority.py tests/test_cutover_native_genesis_continuity.py -q
uv run pytest tests/test_cutover_threat_authority_port_integration.py tests/test_cutover_worldbuilding_authority_port_integration.py -q
uv run ruff check apps/live_control_server/integrations/dungeonmind tests/test_cutover_dungeonmind_first_world_initialization.py tests/test_cutover_direct_dungeonmind_world_graph_reads.py tests/test_cutover_dungeonmind_world_graph_authority.py tests/test_cutover_native_genesis_continuity.py
git diff --check
git diff --name-only d96a21363fd0decbcb8c4390f951a6316b53060c...HEAD
```

The required real-PostgreSQL continuity witness must report exact pass/fail/skip counts and have **zero required skips**. Pre-existing environment-dependent skips in unrelated regression cohorts must be called out separately and compared to baseline; they do not satisfy the D.2C3 witness.

### Minimal live / dogfood proof

```text
Existing surface: mounted first-world exact-run prepare/confirm plus native World Graph read/write service boundaries.
Smallest realistic scenario: create a two-node/one-relationship reviewed first world, confirm D_0, immediately search/read one object, obtain mutation context, publish one legal child through an existing authority family, read the child, retry the same operation.
Expected observation: no adoption receipt is needed, no Buddy graph revision is fabricated, D_0 is the parent, one child exists, retry recovers it, and native reads show the child.
Evidence captured: test output + exact world/init/revision IDs and receipt counts in the review handback.
```

### Baseline failure handling

If any required cohort fails or skips on the exact base, record the same command at base and head. The implementation must not add failures/skips. A required D.2C3 PostgreSQL witness skip has no waiver in this handoff.

## Execution record — Review Cycle 3 stop/rebrief, not DONE

This PR remains `DOING`. Do not treat the following as merge-ready `DONE`. Native projection of #645 `D_0` facts is **not** claimed.

**Cycle 1 blockers 2–4 remain closed:** genesis reread; parent `PersistenceIntegrityError` → integrity; #647 exact design base `f1fd3f6…` vs merge `d96a2136…`.

**Cycle 2 blocker 1 is reopened as a stop.** `_SourceAlignedWorldGraphRepository` rewrote `evidence_refs.source_domain` in memory before DungeonMind scoped an immutable revision. That broadens admissibility and is forbidden by the native-read contract. The shim is removed. Projection/retrieval consume `bundle.world_graph` exactly.

```text
Stop condition:
  making first-world native projection work requires rewriting DungeonMind graph-payload provenance (or a new provider/mutation capability)
Invariant clause affected:
  D.2C2 D_0 is natively projectable/retrievable from the exact stored revision
Why current mission cannot absorb it:
  #645 stamps SourceDomain.OTHER on first-world contribution evidence. DungeonMind treats artifact/graph domain disagreement as invalid evidence. Buddy may not reconstruct graph truth or broaden admissibility. Changing durable initialization command bytes was already rejected (Cycle 1). A global in-memory rewrite was rejected (Cycle 2) because it would also mask genuine provenance corruption.
Required evidence now missing:
  native admitted projection/retrieval of #645-shaped D_0 facts from unmodified stored revision bytes
Affected paths/ownership layers:
  D.2C2 first-world mapping / stored D_0 graph_payload evidence_refs; DungeonMind graph_scope provenance check; not D.2C3 binder algebra
Proposed successor or re-brief:
  D.2C2 provenance compatibility/repair (reviewed DESIGN, then CODE) precedes remaining D.2C3 native-projection proof
  sequence: D.2C2 provenance → D.2C3 two-genesis binder (#651 resumes original job) → D.2C4
State-authority update needed:
  record the provenance predecessor as REQUIRED / not dispatched; keep D.2C3 DOING / merge blocked on that predecessor for native projection; D.2C4 remains BLOCKED
```

**Owning cohort** (`DMB_CUTOVER_TEST_DATABASE_URL=postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind_cutover_test`):

```text
uv run pytest tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_dungeonmind_world_graph_authority.py \
  tests/test_cutover_native_genesis_continuity.py -q
119 passed, 12 skipped, 10 warnings in 190.59s
```

The 12 skips are pre-existing D.1 Buddy-hydration retirement skips in `tests/test_cutover_dungeonmind_world_graph_authority.py`. The D.2C3 PostgreSQL witness `test_reviewed_init_d0_native_read_write_continuity` did not skip: stored `D_0` evidence domains remained `{"other"}`, exact first-world confirm reused `command_sha256` / `already_initialized`, the two-genesis binder bound reviewed-init with `legacy_buddy_revision_id=None`, one child published under `D_0`, and native projection did **not** admit `obj_session22_vial` / `mystery_puddles`.

**D.2A / D.2B regression:**

```text
uv run pytest tests/test_cutover_threat_authority_port_integration.py \
  tests/test_cutover_worldbuilding_authority_port_integration.py -q
4 passed, 10 warnings in 85.13s
```

**Ruff:** `All checks passed!` on the leased Python paths including `tests/test_cutover_native_genesis_continuity.py`.

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR / branch / final head SHA;
2. exact implementation base and rebase status;
3. design authority: #647 merge `d96a21363fd0decbcb8c4390f951a6316b53060c`, accepted head `1f5676c204ee917d18efd553106c07306541e820`, Cycle 7 PASS-equivalent `5034239255`;
4. D.2C2 predecessor: #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`, accepted head `f772db17e00cbe2c0198ae53f169a10a6332a3ed`, Cycle 2 PASS-equivalent `5026532158`;
5. cumulative changed paths vs §4 and any bounded-discovery tests used;
6. active parallel PRs checked, including #650 status/lease at review time;
7. implemented two-genesis binding shape and exact error mapping;
8. proof `legacy_buddy_revision_id=None` for reviewed-init; no fake Buddy revision;
9. A→D_A pin proof and D_0 passthrough/parent proof;
10. real-PostgreSQL witness exact pass/fail/skip counts and world/init/revision topology;
11. exact retry/recovery result and one-child count;
12. Eldyrwild/adoption, D.2A Threat, and D.2B worldbuilding regression results;
13. both-receipt / receipt-without-head / head-without-genesis integrity proofs;
14. exact verification commands, ruff, `git diff --check`, and baseline comparisons;
15. backward-looking state sync: #645 DONE, #647 design DONE with real merge/review facts, D.2C3 active/this PR, D.2C4 blocked, D.3A blocked, D.3B blocked, D.3 not DONE;
16. paths outside §4 (`none` or stop report), stop conditions, and named successor still false.

The dispatch seed is **not Review Cycle 1**. Review Cycle 1 begins only with executable implementation and owning evidence on a distinct implementation head.

## §9 Acceptance rubric

- [ ] Exactly one capability is delivered: shared native genesis binding across adoption and reviewed initialization.
- [ ] `DirectAuthorityBinding.legacy_buddy_revision_id` is optional and first-world binding uses `None`, not a sentinel/fake revision.
- [ ] Binding records/otherwise exposes which of the two legal genesis families authorized it.
- [ ] Existing-world Buddy-A still maps exactly to D_A.
- [ ] First-world D_0 and descendants pass through as real DungeonMind revision IDs.
- [ ] D_0 is accepted as a legal existing parent by the normal governed write path.
- [ ] One real-PG witness proves D.2C2 D_0 → native projection/retrieval → authority child → native child read → exact retry, with zero required skips.
- [ ] Both receipts, receipt-without-head, and head-without-genesis fail as integrity; no fallback/third genesis is invented.
- [ ] Existing adoption, D.2A Threat, and D.2B worldbuilding behavior remains green or baseline-equivalent.
- [ ] No DungeonMind provider/repository code or dependency pin changes.
- [ ] No D.2C4 authoring, D.3A import-blocker/route retirement, buddy_files removal, or legacy package deletion is performed.
- [ ] Actual changed paths stay inside §4 / bounded discovery and do not collide with APP-STATE #650 or any later active lane.
- [ ] Backward-looking state sync records #645 and #647 completion truth without pre-marking D.2C3 DONE.
- [ ] D.2C4 remains the named blocked successor; D.3 remains false.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- a required native read/write needs a new DungeonMind command, repository method, provider UoW, schema, or publication family;
- a third genesis family or ambiguous legal receipt topology is discovered;
- making first-world continuity work requires a fake Buddy revision, local graph store, Buddy fallback, adoption row, or D_0 rewrite;
- a required production path lies outside §4;
- #650 or another active lane acquires a §4 path or unsafe shared PostgreSQL/runtime state;
- the fix requires Graph Review manual-authoring migration, UI changes, authority selector rehome, import blocking, or legacy engine deletion;
- required real-PG owning evidence cannot run with zero required skips;
- baseline/head regressions require an unapproved waiver;
- merged #647 semantics or the pinned DungeonMind provider materially differ from the contracts described here.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
