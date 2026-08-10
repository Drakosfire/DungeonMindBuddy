---
pr_body_template: |
  ## Handoff pointer
  - Conversation: Eldyrwild Lysandra Threat Direction Correction
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-eldyrwild-lysandra-threat-direction-correction.md
  - PR / branch: build/eldyrwild-lysandra-threat-direction-correction
  - Docs authority sync: post-#536 parent-relative contract; BUILD blocked until contribution-integrity heal for contribution:d3d244474789879c

  ## Verification pointer
  - Base/head: record exact implementation base and head in review handback
  - Changed paths: only §4 allowlist plus any explicitly exercised bounded-discovery path
  - Verification: execute every applicable §7 command/scenario and report exact results
  - Conformance gate: parent-relative P→Q delta (not absolute 346/295/51/2 as sole merge gate)
  - Rebuild: pinned rebuild reconstructing Q is NOT WAIVABLE

  The checked-in handoff, cumulative code diff, nano commits, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only. Document sync is a separate operation; this docs sync is a
  prerequisite before BUILD and the implementation PR must not invent the
  contract.
---

# HANDOFF — governed Eldyrwild Lysandra threat-direction correction

**Created:** 2026-08-09.  
**Status:** BLOCKED ON ELDYRWILD CONTRIBUTION-INTEGRITY HEAL — post-#536 parent-relative contract is canonical in this handoff; BUILD remains blocked until pinned contribution replay is healed for `contribution:d3d244474789879c` (separate predecessor slice), then Lysandra BUILD may dispatch.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-lysandra-threat-direction-correction.md`  
**Conversation name:** `Eldyrwild Lysandra Threat Direction Correction`  
**Flow / agent:** `BUILD`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** DungeonBuddy design steward — 2026-08-09  
**Code agent:** fresh BUILD code agent using the same conversation name  
**PR title:** `BUILD: correct Eldyrwild Lysandra threat direction`

> **Dispatch gate:** This docs-authority sync is a **prerequisite before BUILD**. The design/docs sync anchor is current `origin/main` at docs-dispatch (includes merged PR #536). Design predecessors to name: PR #536 merge `413e808112dc85499651cf232ff71614dc4b18b6` (`KERNEL: make relationship conformance current-support aware`) plus the previous Lysandra handoff landing `551f9ce1b147fdeb6b1f79cdb9fe8082aef7eb19`. Tracker dependency chain for Lysandra: **#534 + #536 + contribution-integrity heal** for `contribution:d3d244474789879c`. Do **not** treat this slice as READY for BUILD until that heal lands. Before the first implementation change, record the exact `origin/main` SHA; prove it is a descendant of `413e8081…` and of the #534 merge `99f1d18d…`; prove this post-#536 handoff exists on that base; re-read the active Campaign Supergraph tracker; and prove it names `eldyrwild-lysandra-threat-direction-correction` as `READY` only after the contribution-integrity heal predecessor is done. The implementation PR must not invent the contract — it consumes this synced handoff.
>
> This is the first real use of the targeted structural edge-correction primitive. The slice owns **one exact Eldyrwild correction only**. It must not become a generic correction API, a Graph Review UI, a conformance exception, a global edge reversal, a source-prose rewrite, or an omnibus repair of the remaining source-correction ledger.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Adjudication anchor** | Immutable Eldyrwild revision `rev:3413bf6f5044cf2680233f5e37c90dcf` with payload SHA256 `346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa`; the source-grounded relationship adjudication and source seals are bound to this historical revision. |
| **Defective historical edge X** | `edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists`, structurally `npc_lysandra --threatens--> node:cultists_of_longmont`. |
| **Exact target support** | The source support pair `(contribution:86ea8a3d97dd18cc, assertion:1dc0fef6561c3282)` identified by the adjudication fixture for X. |
| **Corrected edge X′** | A distinct current edge representing `node:cultists_of_longmont --threatens--> npc_lysandra`; the preferred edge object ID for this slice is `edge:node:cultists_of_longmont:threatens:npc_lysandra`. |
| **Historical source authority** | The Session-8 recap artifact, evidence ref, source span, source seal, original contribution/assertion, and old immutable revision showing why X existed. They remain inspectable after correction and are never rewritten to pretend the extraction was originally correct. |
| **Correction authority C** | One checked-in, human-authored `GraphContribution` using the PR #534 `assertion_corrections` contract to contradict X and supply X′. |
| **Eligible parent P** | The exact current Eldyrwild revision to which C may be applied: P must be the adjudication anchor or a proven descendant; the adjudication for X must still be `ANCHOR`/`CARRIED_FORWARD` with verified source grounding and durable shape; the exact target support must still be active and sole; **X must still be in P's effective residual set** (not merely durable/present); and if a replacement edge X′ already exists with a matching structural fingerprint, prove it is **not already current from unrelated authority** (no active current support that would destroy the parent-relative `+1/−1` invariant). Structural fingerprint match alone is insufficient for eligibility. |
| **Corrected descendant Q** | The one immutable revision produced by applying C to eligible parent P with expected-parent/CAS publication. |
| **Source seal** | The checked-in immutable source-grounding record for X, including Session-8 artifact SHA and paragraph-013 excerpt SHA. |
| **Parent-relative conformance delta** | Lysandra BUILD acceptance observation against P→Q (post-#536 current-support-aware conformance): `semantic(Q) == semantic(P)`; `represented(Q) == represented(P) + 1`; `residual(Q) == residual(P) - 1`; `mechanics(Q) == mechanics(P)`; plus X remains historically materialized/inspectable, X is absent from Q's current effective residual set, X′ is current and represented, source seals unchanged, and Q is replay-equivalent (pinned rebuild reconstructs Q — **NOT WAIVABLE**). Absolute historical counts are not the merge gate. |
| **Formal conformance re-anchor** | The successor slice `eldyrwild-effective-conformance-after-first-correction` that owns formal current-descendant fixture/tracker re-anchoring after Q. It must record the **actual current baseline** on the live head (do not force historical absolute counts onto an evolved live head). If and only if P is demonstrably the exact canonical historical `346/294/52/2` baseline, record the stronger exact result `346/295/51/2` as an optional strengthening observation — never as the sole Lysandra BUILD gate. This PR may observe the parent-relative delta read-only but must not alter conformance interpretation or its canonical fixtures to obtain it. |

## Agent flow and nano-commit contract

Use `BUILD` for this implementation. Keep the work in nano commits. Recommended story shape:

1. **Authority artifact:** capture the exact live target shape from an eligible parent and check in one canonical correction `GraphContribution`; lock its deterministic IDs, semantic source-payload digest, **and** raw artifact SHA256 in tests/service constants.
2. **Guarded apply seam:** add the Eldyrwild-specific preflight/apply service and a headless operator CLI that delegates the semantic mutation to `graph_memory.kernel.correct_edge_assertion_support`; enforce `--allow-live-world` when apply targets canonical `world_graph_root()`.
3. **Failure proofs:** prove stale parent, ineligible target (including missing effective residual / X′ already current from unrelated authority), source/ancestry drift, semantic and byte-level artifact tamper (`integrity_failure`), collision, canonical-root apply without opt-in, and exact retry all fail/no-op safely.
4. **Real descendant proof:** on a clone of the real Eldyrwild store, publish Q and prove old/new projection, unrelated support preservation, source-history preservation, and pinned rebuild equivalence.
5. **Semantic observation:** run the existing effective-conformance analyzer read-only against both P and Q; require the parent-relative delta (`semantic` unchanged, `represented` +1, `residual` −1, `mechanics` unchanged) plus X/X′/seal/replay invariants without changing analyzer/catalog/fixture semantics. If and only if P is the exact canonical historical `346/294/52/2` baseline, also record the stronger exact `346/295/51/2` result.

Do not modify the generic PR #534 correction machinery unless an existing-contract regression is proven. If this real use case requires changing the generic correction contract, stop and return to design instead of folding the redesign into this PR.

## Review and doc-sync contract

Review the cumulative diff and nano-commit sequence against this handoff. The implementation PR must not update the roadmap, tracker, current-state guide, this handoff status, or effective-conformance anchor fixtures as part of the code/data mutation. Those are separate document/conformance sync operations after implementation review/merge.

This docs-authority sync (post-#536 parent-relative contract + operator/integrity requirements) lands on `main` as a prerequisite before BUILD dispatch. Docs/tracker edits stay out of the Lysandra implementation PR; this docs sync owns them. The implementation PR itself must remain bounded to §4 and must not invent the contract.

## §1 Mission and merge-ready invariant

**Mission:** An operator can publish the adjudicated Lysandra threat-direction correction through the governed Kernel correction seam so that current Eldyrwild truth says the cultists threaten Lysandra while the original Session-8 assertion and evidence remain historical authority.

**Merge-ready invariant:** Against one exact eligible Eldyrwild parent revision P, the exact sole-active support `(contribution:86ea8a3d97dd18cc, assertion:1dc0fef6561c3282)` is atomically contradicted and one checked-in human-authored replacement `node:cultists_of_longmont --threatens--> npc_lysandra` becomes current in one immutable descendant Q, while the original recap/source seal/contribution/evidence and every unrelated assertion support remain unchanged, ancestry/source/identity drift and stale parents fail closed, exact retry publishes no second descendant, and pinned contribution replay reconstructs Q exactly.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** The only durable behavior is applying one pre-authored correction C to one eligible Eldyrwild parent P. Status/preflight, CLI, retry, replay, projection, and semantic observation all prove or protect that same transition. |
| What adversarial sequence is most likely to falsify it? | Inspect an apparently eligible P → author/apply C → discover that P’s target support or source grounding had drifted, or head advances between inspection and publish → code silently searches by labels/edge shape or applies to the newer head anyway. The second major risk is that C corrects X but accidentally retires other assertions from contribution `86ea…` or rewrites the Session-8 source evidence. |
| Would the proposed §7 evidence actually detect that failure? | **Yes.** The real-clone proof fingerprints all sibling support owned by the target contribution, binds preflight to the existing continuity/source-seal analyzer, forces a stale-parent interleaving, projects P and Q, and rebuilds Q from contribution history. |
| Which owning boundary is easiest to under-test? | The one-off apply seam. The generic Kernel is already strongly proved; this slice can still be wrong if the wrapper accepts the wrong parent, wrong target, caller-injected semantics, or a correction artifact whose scope/provenance does not match the real target. |
| What fact would force this slice to stop or split? | Any of: target IDs no longer identify the adjudicated edge; target support is not sole-active; X is not `ANCHOR`/`CARRIED_FORWARD` on the intended parent; X is not in P's effective residual set; X′ already exists with active current support from unrelated authority (would destroy `+1/−1`); a new source-domain/public schema is required; generic Kernel changes are required; or existing effective conformance cannot observe the parent-relative delta on a correct Q without a new semantic exception. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/STATUS-world-graph-continuity-spine.md`; adjudication/source-seal fixtures from PR #526/#531 |
| Repository rules | Public graph mutation crosses `graph_memory.kernel`; one immutable revision + expected-parent CAS; source-derived and human-authored assertions stay distinguishable; graph corrections survive replay; diagnostic/adjudication code is not mutation authority; agents are not privileged writers |
| Design anchor | Docs-dispatch `origin/main` (includes #536). Design predecessors: PR #536 merge `413e808112dc85499651cf232ff71614dc4b18b6` (current-support-aware conformance) + previous Lysandra handoff landing `551f9ce1b147fdeb6b1f79cdb9fe8082aef7eb19`; also requires merged PR #534 `99f1d18dffd48d7e46250d63892adfae97a654a8` |
| Implementation base | Exact `origin/main` SHA at BUILD dispatch, recorded before code; must be a descendant of `413e8081…` and `99f1d18d…`, contain this post-#536 handoff, have the contribution-integrity heal for `contribution:d3d244474789879c` landed, and have tracker state synced so this slice is `READY` |
| Predecessor contract | Merged PR #534: `GraphContributionAssertionCorrection`, `create_edge_assertion_correction_contribution`, `correct_edge_assertion_support`, contradicted support lineage, exact retry, replay, lifecycle/integrity fail-closed behavior. Merged PR #536: current-support-aware relationship conformance / parent-relative P→Q delta arithmetic. Separate predecessor: Eldyrwild contribution-integrity heal for `contribution:d3d244474789879c` digest mismatch (revision-bound seal vs ledger) — **blocking** until done. |
| Exact input consumed | One repository-approved correction `GraphContribution` C; one exact expected parent revision P; the built-in Eldyrwild adjudication/source-seal authority; the exact target IDs `contribution:86ea8a3d97dd18cc` / `assertion:1dc0fef6561c3282` / defective edge X |
| Named successor | `eldyrwild-effective-conformance-after-first-correction` |
| What remains false | No generic Graph Review correction UX; no second source correction; no formal new effective-conformance anchor/fixture; remaining Buddy residuals are not repaired; correction lifecycle reversal remains unsupported; DungeonMind product-authority cutover remains blocked |
| Explicit non-goals | Rewriting Session-8 recap prose; changing source seals/adjudication findings; adding a reverse adapter; changing `dnd5e:threatens`; global predicate/endpoint rewrite; changing generic Kernel correction semantics; new server route/API; UI; Hermes write path; Plan/Play mutation; identity/decomposition work; cleanup of other residuals |

Read authoritative inputs in order before changing code:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
3. `Docs/Design/STATUS-world-graph-continuity-spine.md`
4. this handoff
5. merged predecessor `Docs/Plans/HANDOFF-kernel-targeted-edge-assertion-correction.md`
6. `src/graph_memory/kernel/contribution_models.py`
7. `src/graph_memory/kernel/contributions.py`
8. `src/graph_memory/kernel/contribution_merge.py`
9. `src/graph_memory/kernel/contribution_rebuild.py`
10. `apps/live_control_server/integrations/dungeonmind_kernel/relationship_residual_adjudication.py`
11. `apps/live_control_server/integrations/dungeonmind_kernel/relationship_adjudication_continuity_v1.py`
12. `apps/live_control_server/integrations/dungeonmind_kernel/relationship_effective_conformance_v1.py` — **read-only contract consumer in this slice**
13. `tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_adjudication_v1.json`
14. `tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_source_seals_v1.json`
15. `tests/test_dungeonmind_relationship_effective_conformance.py` — read for expected semantics; do not edit under the normal allowlist
16. PR #373 C1 additive-apply service/CLI as an operational precedent only; do not generalize this correction into bundle application

If the base moved, an authority conflicts, the target shape differs, or the invariant cannot be preserved, stop and report the consequence before implementation.

### Exact adjudicated target authority

The implementation must use these values literally; do not rediscover the target via text/labels:

```text
world_id:
  eldyrwild
campaign_id:
  longmont-c1

historical adjudication revision:
  rev:3413bf6f5044cf2680233f5e37c90dcf
historical graph payload sha256:
  346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa

defective edge X:
  edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists
historical structural shape:
  npc_lysandra --threatens--> node:cultists_of_longmont

target assertion:
  assertion:1dc0fef6561c3282
target supporting contribution:
  contribution:86ea8a3d97dd18cc

adjudication disposition:
  SOURCE_CORRECTION_REQUIRED
reason_code:
  DIRECTION_CONTRADICTION
next_action:
  AUTHOR_BUDDY_SOURCE_CORRECTION
mapped DungeonMind term:
  dnd5e:threatens

required corrected structural shape:
  node:cultists_of_longmont --threatens--> npc_lysandra
preferred replacement edge object id X′:
  edge:node:cultists_of_longmont:threatens:npc_lysandra
```

The adjudication deliberately did **not** authorize an adapter-level reversal. `reverse_endpoints=false` plus `SOURCE_CORRECTION_REQUIRED` means the durable graph assertion is wrong and must be corrected through authored graph authority.

### Exact historical source seal

The original source is valid evidence; the structural extraction direction is the defect.

```text
primary evidence ref:
  evidence:artifact:recap:longmont-c1:session-8:session-8:recap:paragraph:013
source artifact:
  artifact:recap:longmont-c1:session-8
artifact URI:
  repo://out/graph_memory/runs/longmont-c1/session-8/20260721T231221Z/normalized_recap_source.md
artifact content sha256:
  8463945d7548f8a7a31ea4d96d1d61b95a28830c57f2deead99627aac8271bc2
source span:
  session-8:recap:paragraph:013
locator:
  paragraph:013
excerpt sha256:
  b53b65f72cddb16f1bd9abecbd36ef8c4eb43d513391ec4b866a3e57db63e8de
```

Normalized excerpt, for human review only:

> The party quickly jumps into battle and makes quick work of two of the Cultists. They seem to go down easily and things seem straightforward, until the remaining Cultists split open to reveal huge mouths full of teeth. Before the party can react the Cultists jump on the guards in the cages. Falling upon, gorging on, and merging with the guards in cages something corrupted and fleshy is born. Captain Lysandra, barely able to hold off the giant meat maw trying to consume her, screams for help while fighting for her life.

Do not change any of those historical values in this slice.

### Eligible-parent rule

Before C may publish against parent P, all must be true:

1. P is the exact current Eldyrwild head supplied as `expected_parent_revision_id`.
2. `prove_revision_is_anchor_or_descendant_v1(...)` proves P is the adjudication anchor or its descendant.
3. `analyze_relationship_adjudication_continuity_v1(...)` returns X as `ANCHOR` or `CARRIED_FORWARD` with `source_grounding_verified=true` and `durable_shape_verified=true`.
4. The exact target contribution exists and is active.
5. The exact target assertion exists in that contribution and is an accepted `edge` assertion.
6. Durable support for `assertion:1dc0fef6561c3282` is `supported` with exactly one active contribution, exactly `contribution:86ea8a3d97dd18cc`.
7. The live edge object for X still has source `npc_lysandra`, target `node:cultists_of_longmont`, predicate `threatens`.
8. X is still in P's **effective residual** set (not merely durable/present on the revision).
9. The replacement edge ID does not already exist with conflicting current structure/authority. If a replacement edge X′ already exists with a matching structural fingerprint, prove it is **not already current from unrelated authority** — no active current support that would destroy the parent-relative `represented +1` / `residual −1` invariant. Structural fingerprint match alone is insufficient for eligibility.
10. The checked-in correction artifact validates and its replacement assertion preserves the target assertion's exact `campaign_scope`, `visibility`, `epistemic_kind`, and `temporal_scope` as required by PR #534.

If any item fails, the state is **ineligible**, not “close enough.” Do not search for a replacement target by edge label, node label, predicate, source text, or adjacency.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Load approved correction artifact | No checked-in real Lysandra correction | Load exactly one known-path `GraphContribution`; verify deterministic identity/digest and exact target/replacement constants | Yes | one-off apply service |
| Inspect eligible parent | Generic Kernel can correct if caller supplies C, but nothing binds the real adjudication to the real target | Prove ancestry, continuity/source seal, X in effective residual, exact target support, old shape, replacement absence or not-already-current-from-unrelated-authority, and correction-artifact coherence (digest + raw SHA256) | Yes | one-off apply service |
| Operator status CLI | No dedicated one-off command | Read-only status shows exact head + `eligible` / `already_applied` / `ineligible` / `integrity_failure` state; never mutates; may run without `--allow-live-world` | Yes | CLI + service |
| Apply C to P | Capability exists generically but not wired to this approved real correction | Call `kernel.correct_edge_assertion_support` with the fixed C and exact expected parent P; publish one Q; live-write fence requires `--allow-live-world` when targeting canonical `world_graph_root()` | Yes | service → Kernel |
| Read old pinned P | Historical defective edge is current there | P remains immutable and still projects X as it did before | Yes | Kernel projection |
| Read corrected Q | No real correction exists yet | X is non-current; X′ is current with faction→npc `threatens` structure | Yes | Kernel projection |
| Inspect original Session-8 authority | Source seal and evidence are historical authority | Artifact/seal/evidence bytes and identifiers remain unchanged/resolvable | Yes | graph/source data + diff proof |
| Inspect sibling assertions from target contribution | Same source contribution may carry unrelated facts | Every non-target support/provenance record attributable to `contribution:86ea…` is byte/semantic-equivalent before/after | Yes | assertion support store |
| Stale expected parent | Generic CAS protects publication | Wrapper must not replace P with “current head”; stale apply fails and newer head remains unchanged | Yes | service + Kernel CAS |
| Exact retry | Generic correction can no-op | Re-running same approved C on Q returns no second descendant and no duplicate contradiction/support lineage | Yes | service + Kernel |
| Ineligible target/source drift | Generic op may reject some target conditions, but wrapper owns real adjudication eligibility | Fail before semantic mutation; no label/shape fallback | Yes | one-off service |
| Replacement collision | Generic Kernel rejects structural collision | Wrapper preflight + Kernel both fail closed; never reuse unrelated edge identity | Yes | service + Kernel |
| Pinned rebuild Q | Generic correction is replayable | Rebuild from durable contribution history equals Q exactly | Yes | Kernel rebuild |
| Existing effective conformance on Q | Live head counts may have evolved past the historical `294/52` baseline | Read-only analyzer on P and Q must observe the parent-relative delta: `semantic(Q)==semantic(P)`, `represented(Q)==represented(P)+1`, `residual(Q)==residual(P)-1`, `mechanics(Q)==mechanics(P)`; plus X historically inspectable, X absent from Q's current effective residual set, X′ current and represented, source seals unchanged; if and only if P is the exact canonical historical `346/294/52/2` baseline, also record stronger exact `346/295/51/2`; if not, stop rather than adding a special case | Yes | existing analyzer, observation only |
| Formal descendant conformance fixture | Not yet published | Remains deferred; successor owns formal current-descendant fixture/tracker re-anchoring and must record the actual current baseline; no canonical fixture/report re-anchor in this PR | Yes | named successor |

### Ordered failure sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Status P says eligible → unrelated writer advances head to R → operator submits apply with expected P | No correction mutation; R remains head; C is not treated as authorized for R without a fresh status/preflight | stale-parent adversarial test |
| P is descendant but X source grounding or durable shape drifts → operator tries apply | Fail closed before C publication; original/current head unchanged | eligibility-drift tests |
| Exact target assertion gains a second active supporting contribution → operator tries apply | Fail closed; neither source is contradicted; X′ absent | multi-support regression through one-off wrapper |
| Approved correction JSON is edited after constants/digest are locked → operator tries apply | Integrity failure before graph mutation (`integrity_failure`); covers semantic field mutation and byte-level artifact SHA256 seal | artifact tamper test |
| X′ edge ID already exists with unrelated structure → operator tries apply | Fail closed; no support transition | collision test |
| Apply C successfully → call exact apply again against Q | `published=false`/idempotent no-op; head stays Q; no duplicate support/contradiction lineage | retry test |
| Apply C → rebuild Q from contributions | Fingerprint equivalent to Q; X stays historical/non-current; X′ stays current; **NOT WAIVABLE** — forbid waiving known baseline rebuild failures | pinned rebuild test |
| Apply C → inspect every other assertion support attributable to target contribution | All siblings unchanged; only target support transitions to contradicted lineage | real-clone atomicity fingerprint |
| Apply C → run existing effective analyzer on P and Q | Parent-relative delta holds (`semantic` unchanged, `represented` +1, `residual` −1, `mechanics` unchanged); X/X′/seal/replay invariants hold; stronger absolute `346/295/51/2` recorded only when P is the exact canonical historical `346/294/52/2` baseline | semantic observation gate |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `graph_data/approved_graph_corrections/eldyrwild/lysandra-threat-direction-v1.json` | Durable, reviewable human-authored correction contribution C using the existing `GraphContribution` schema; no new correction schema/manifest |
| Create | `apps/live_control_server/services/eldyrwild_lysandra_threat_direction_correction.py` | Lock exact adjudication/target/artifact authority, perform read-only eligibility/status, and delegate publication to the public Kernel correction seam |
| Create | `scripts/apply_eldyrwild_lysandra_threat_direction_correction.py` | Headless operator entry point for status/apply against an explicit world-graph root and exact expected parent; no arbitrary target/replacement parameters |
| Create | `tests/test_eldyrwild_lysandra_threat_direction_correction.py` | Own artifact integrity, eligibility, stale/retry/collision/multi-support, real-clone atomicity, projection, source-history, rebuild, and semantic observation proofs |

**Bounded discovery exception:**

```text
Directory: tests/fixtures/graph_memory/eldyrwild_lysandra_threat_direction/
Maximum additional paths: 3
Allowed path kinds: test-only captured predecessor records needed to make a non-skippable hermetic proof use the real target vocabulary/shape
Decision rule for including one: only if the exact target contribution or its minimum prerequisite graph objects cannot be reproduced in the owning test without inventing fields that are not present in the real eligible Eldyrwild parent. Any captured fixture must be copied from the real predecessor, source-digest bound, and used only for tests. Do not copy the whole world store.
```

No production path outside the four primary allowlist entries is authorized. If the real correction requires modifying generic Kernel code, continuity/conformance analyzers, source-seal/adjudication fixtures, route registration, or any other production module, stop and report why the predecessor contract is insufficient.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/kernel/contribution_*` and `src/graph_memory/evidence/assertion_support.py` | PR #534 owns the generic correction contract and is merged. A required change here means the predecessor contract failed and needs separate design/review. |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_adjudication_v1.json` | Historical adjudication authority; this correction consumes it and must not rewrite it to make the new graph agree. |
| `tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_source_seals_v1.json` | Historical source seal; must remain byte-identical. |
| Session-8 normalized recap/source corpus | The prose is valid historical evidence. Editing it would destroy the disagreement this feature exists to preserve. |
| `relationship_explicit_adapters_v1.py` or adapter fixtures | This is not an adapter/reversal rule. |
| `relationship_effective_conformance_v1.py` and canonical effective-conformance fixture | Formal current-descendant re-anchor belongs to the named successor (must record the actual current baseline). This PR may run the analyzer read-only as a parent-relative acceptance observation. |
| DungeonMind dependency or `dnd5e:threatens` vocabulary | The corrected faction→npc relationship is already admitted; no vocabulary change is needed. |
| Graph Review UI/routes/API | This is a repository-approved one-off data maintenance correction, not the product authoring UX. |
| Generic correction management/list/revert surface | Correction lifecycle reversal remains explicitly unsupported by the PR #534 contract. |
| Other 34 `SOURCE_CORRECTION_REQUIRED` residuals | First real exemplar only; no batch repair. |
| Compound decomposition, identity migration, insufficient-evidence work | Different authority/invariants and separate successor classes. |
| Tracker/roadmap/status/handoff completion edits | Separate document sync after implementation merge. |
| Actual shared/canonical operator world-root mutation during automated tests | Tests must use temporary clones. Never make repository test execution mutate an operator's canonical Eldyrwild store. |

## §6 Implementation contract and conditional matrices

### Approved correction artifact

The checked-in file is not a new schema. It must validate directly as the existing `GraphContribution` model and be constructed with the public PR #534 helpers, not by hand-writing assertion/contribution IDs.

Required semantic shape:

```text
GraphContribution C
  world_id = "eldyrwild"
  source_kind = "graph_review_authored_assertion"
  authored_by = "gm"
  source_artifact_id = "graph-native:eldyrwild-correction:lysandra-threat-direction-v1"
  source_revision_id = "correction:eldyrwild:lysandra-threat-direction-v1"
  supersedes_contribution_id = null
  candidate_assertions = []
  rejected_assertions = []
  unresolved_mentions = []
  identity_decision_ids = []

  accepted_assertions = [X′ assertion]
  assertion_corrections = [
    {
      correction_kind: "contradicts_and_replaces",
      target_contribution_id: "contribution:86ea8a3d97dd18cc",
      target_assertion_id: "assertion:1dc0fef6561c3282",
      replacement_assertion_id: <computed exact X′ assertion ID>
    }
  ]

X′ assertion
  assertion_kind = "edge"
  acceptance_state = "accepted"
  subject_node_id = "node:cultists_of_longmont"
  target_node_id = "npc_lysandra"
  predicate = "threatens"
  value.edge_id = "edge:node:cultists_of_longmont:threatens:npc_lysandra"
  identity_resolution_outcome = "resolved_existing"
  campaign_scope = <exact target assertion campaign_scope>
  visibility = <exact target assertion visibility>
  epistemic_kind = <exact target assertion epistemic_kind>
  temporal_scope = <exact target assertion temporal_scope>
```

For X′ provenance, use the existing graph-native/manual authored provenance convention; **do not introduce a new source-domain enum in this slice**. The replacement's authored evidence must point to the correction artifact itself (for example a stable graph-review evidence ref and `graph-data://approved-graph-corrections/eldyrwild/lysandra-threat-direction-v1.json` URI). Do not relabel the Session-8 recap as if it directly asserted the corrected direction. The historical recap evidence remains attached to X and the adjudication/source seal.

After generating C with public helpers, record in code/tests/review handback:

```text
replacement assertion ID:
correction contribution ID:
correction source-payload SHA256:
approved artifact raw SHA256:
```

Those values are derived outputs, not design-agent guesses. The service must lock them so editing the checked-in artifact cannot silently change the approved mutation. Approved artifact authority must seal **both** (1) the semantic source-payload digest and (2) the raw checked-in artifact SHA256 (byte-level seal). Tamper tests must cover byte-level artifact sealing, not only semantic field mutation.

### Public/operator operation

```text
Input:
  root: exact World Graph root (explicit in tests/CLI or existing configured default)
  expected_parent_revision_id: exact nonblank Eldyrwild head revision
  approved correction artifact: fixed repository path only; no caller override
  allow_live_world: required opt-in when apply targets the canonical configured world_graph_root()

Output:
  existing Kernel ContributionMergeResult for apply, plus read-only module-private preflight/status data for operator display

Invariant:
  same as §1

Failure behavior:
  missing world/head → fail closed
  parent not anchor/descendant → fail closed
  X continuity not ANCHOR/CARRIED_FORWARD → fail closed
  source grounding not verified → fail closed
  exact target contribution/assertion missing/inactive → fail closed
  target support not sole-active from contribution:86ea… → fail closed
  X not in P's effective residual set → fail closed
  live X shape differs → fail closed
  X′ already current from unrelated authority (would destroy +1/−1) → fail closed
  correction artifact identity/digest or raw SHA256 differs from locked authority → integrity_failure
  target/replacement scope mismatch → fail closed (Kernel contract)
  X′ collision/conflicting authority → fail closed
  apply against canonical world_graph_root() without --allow-live-world → fail closed
  stale expected parent → fail closed; never refresh-and-write automatically

Replay / idempotency:
  same exact C after success → existing Kernel idempotent no-op; no second descendant
  already_applied inferred only by proving exact correction contribution C from revision-bound contribution/manifest authority — not merely from support state + edge shape
  changed C bytes/linkage/replacement → rejected by locked artifact identity/digest and raw SHA256; do not treat as a new approved correction
  retry after post-commit bookkeeping failure → existing PR #534 revision-bound recovery semantics apply

Trust boundary:
  Verifies:
    exact world/revision ancestry
    exact adjudication target IDs and structural shape
    source-seal continuity for X on P
    X in P's effective residual set
    sole-active target support
    X′ not already current from unrelated authority
    exact checked-in C identity/digest and raw artifact SHA256
    replacement identity/scope/collision constraints
    expected-parent CAS
    live-write fence for canonical root
  Records or trusts without proving:
    the human semantic judgment that cultists threaten Lysandra; that judgment is already source-grounded by the adjudication and becomes authored graph authority through C
```

### Commit model

```text
Commit point:
  successful kernel.correct_edge_assertion_support(...) → publish_world_graph_revision CAS advancement

Before commit:
  status/preflight and artifact loading are read-only; writing/staging C's ledger record follows the existing Kernel correction implementation and is not a new authority model

After commit:
  Q is the current head in the selected root; X support is contradicted historical lineage; X′ support is current; C is revision-bound replay authority

Truthful result after a post-commit failure:
  defer to PR #534: publication remains authoritative; exact retry discovers/no-ops/repairs bookkeeping rather than applying semantic mutation twice
```

### Operator CLI contract

Use one script with two explicit modes, or equivalent repository CLI conventions:

```text
status
  read only
  may run without --allow-live-world even when --root resolves to canonical world_graph_root()
  prints exact head revision and one of: eligible | already_applied | ineligible | integrity_failure
  already_applied must be inferred by proving exact correction contribution C from revision-bound contribution/manifest authority — not merely from support state + edge shape
  names exact target/correction/replacement IDs and diagnostic reason

apply
  requires --expected-parent-revision-id
  uses the fixed approved artifact and fixed Eldyrwild target only
  no --source-node, --target-node, --predicate, --assertion-id, --contribution-id, or arbitrary correction-file flags
  --root is optional and still defaults to the configured canonical world_graph_root()
  when the resolved world-graph root path equals the configured canonical world_graph_root(), apply MUST require --allow-live-world
  apply without that second opt-in must fail closed when targeting the canonical root
  temp clones remain unaffected (no --allow-live-world required when root ≠ canonical)
```

CLI invocation itself is the explicit operator action. Do not add a server route or silent startup migration.

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| status | Load fixed C + exact head + built-in adjudication/continuity | `eligible` or `already_applied` (C proved from revision-bound contribution/manifest authority) with exact IDs/revision | `ineligible` with reason | Fail closed; no graph mutation | `integrity_failure`; Fail closed; no fallback | Report ineligible/stale state | Safe/read-only |
| apply | Require fixed C + exact expected P; require `--allow-live-world` when root = canonical `world_graph_root()` | One Q or exact no-op if C already applied | No semantic fallback | Fail closed | Fail closed / `integrity_failure` | CAS failure; never substitute current head; canonical apply without opt-in fails closed | Exact C on Q no-ops |
| target lookup | Exact contribution/assertion/support IDs | Sole-active match; X in effective residual | Ineligible | Fail closed | Fail closed | Inactive/multi-source blocks | No label/edge search |
| source authority | Built-in continuity/source seals | X is ANCHOR/CARRIED_FORWARD and grounded | Ineligible | Fail closed | Fail closed | Drift blocks | No source-text fallback |
| corrected read | Exact Q | X′ current; X non-current | Existing projection miss behavior | Existing projection error | Existing integrity error | P remains immutable | Deterministic |
| rebuild | Q replay manifest + contribution ledger | Equivalent to Q (**NOT WAIVABLE**) | n/a | Fail closed | Fail closed | P/Q pins are immutable | Deterministic |
| effective observation | Existing analyzer on exact P and Q | Parent-relative delta; stronger absolute `346/295/51/2` only iff P is exact historical `346/294/52/2` | Stop | Analyzer unavailable = stop gate | Stop; no special-case fix | Exact revision only | Read-only |

No fallback source is permitted for target identity, adjudication, correction semantics, or expected parent.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| World | Exact `eldyrwild` | Other world fails | No |
| Campaign | Exact adjudicated `longmont-c1`; replacement preserves target scope | Mismatch fails | No |
| Parent revision | Exact caller-supplied current P, proven anchor/descendant | Stale/non-descendant fails | No |
| Historical edge X | Exact full edge ID + exact source/target/predicate | Shape drift fails | No |
| Target contribution | Exact `contribution:86ea8a3d97dd18cc` | Missing/inactive fails | No |
| Target assertion | Exact `assertion:1dc0fef6561c3282` | Missing/multi-support fails | No |
| Replacement edge X′ | Exact `edge:node:cultists_of_longmont:threatens:npc_lysandra` unless preflight proves repository canonicalization requires a different deterministic ID **before artifact approval** | Existing/conflicting identity is a stop condition; fingerprint match with unrelated current support is ineligible | No runtime fallback |
| Correction contribution C | Deterministic ID from checked-in bytes/helper output; locked source-payload digest **and** raw artifact SHA256 after authoring | Mismatch/tamper → `integrity_failure` | No |
| Node labels / aliases | Display only | Never used for mutation target | No |
| Predicate/endpoint search | Prohibited as identity mechanism | Never “find closest” | No |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Store approved correction | One checked-in `GraphContribution` JSON using existing schema | Model load/dump preserves target/replacement link and deterministic identity/source digest; raw file SHA256 sealed | Same file = same C | No new schema; PR #534 defaults keep older contributions compatible | Git revert removes future approved artifact, not already-published graph history |
| Apply correction | Immutable World Graph Q + C ledger + support lineage + replay manifest | Reload Q preserves X contradicted / X′ supported | Exact retry no new Q; `already_applied` via revision-bound C proof | Existing PR #534 contract | Correction lifecycle reversal is unsupported; do not use generic retract/supersede |
| Rebuild Q | Existing contribution ledger + revision-bound replay manifest/digests | Canonical fingerprint equals pinned Q (**NOT WAIVABLE**) | Deterministic | Existing legacy handling from PR #534 | Head rollback is not a correction reversal feature |
| Historical P | Existing immutable revision | X remains current exactly as before | Read-only | No migration | Immutable |
| Historical source seal | Existing checked-in fixture/source artifact | Byte/semantic identity unchanged | Read-only | No migration | Immutable historical authority |

### D. Predecessor-to-consumer mapping

**Grounding sources:** PR #534 public Kernel contract; PR #536 current-support-aware conformance; checked-in residual adjudication fixture; checked-in residual source-seal fixture; exact target contribution loaded from eligible P; contribution-integrity heal for `contribution:d3d244474789879c` as blocking predecessor.

| Predecessor field / outcome | Real shape and optionality | Consumer field / behavior | Transformation | Proof fixture/test |
|---|---|---|---|---|
| adjudication `edge_id` | Exact X ID | service `TARGET_EDGE_ID` | Literal equality only | owning test + real clone |
| `supporting_assertion_ids` | For X: exactly `assertion:1dc0fef6561c3282` | C `target_assertion_id` | Literal equality only | artifact integrity test |
| `supporting_contribution_ids` | For X: exactly `contribution:86ea8a3d97dd18cc` | C `target_contribution_id` | Literal equality only | artifact integrity test |
| adjudication `DIRECTION_CONTRADICTION` / `AUTHOR_BUDDY_SOURCE_CORRECTION` | Human semantic classification | authorization to use correction primitive | Consumed as fixed authority; no runtime inference | preflight test |
| source seal artifact/span/excerpt hashes | Exact immutable values | eligible-parent source-grounding gate | Existing continuity analyzer verifies them | real-clone preflight |
| live target assertion scope fields | Existing exact values; must be loaded, not guessed | X′ campaign/visibility/epistemic/temporal scope | Copy exactly | artifact-vs-target test |
| PR #534 correction link | exact target contribution/assertion + replacement assertion ID | C `assertion_corrections[0]` | Existing factory | model round-trip test |
| `correct_edge_assertion_support` | requires exact expected parent + one correction contribution | apply operation | Direct call; no semantic wrapper mutation | stale/retry/real apply tests |
| `ContributionMergeResult` | existing Kernel result | CLI/result reporting | Serialize/print only | CLI test |

Invented “close enough” target fixtures are not acceptable proof. If hermetic tests require captured predecessor data, use the §4 bounded fixture exception and source-digest bind it to the real record.

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| C is exactly one approved existing-schema correction | graph-data artifact/service | contract | focused owning test | `GraphContribution` validates; exactly one accepted edge + one correction; locked contribution ID/source-payload digest **and** raw artifact SHA256 match; exact target IDs; no supersession/identity/unresolved extras | new schema/manifest required; deterministic identity mismatch |
| P is eligible only under historical adjudication/source authority | service | adversarial/contract | hermetic + real-clone status tests | ancestry proven; X continuity ANCHOR/CARRIED_FORWARD; source grounding and shape verified; X in P's effective residual; exact sole target support; X′ not already current from unrelated authority | any label/text fallback or unverifiable source seal |
| One real correction publishes Q | service → Kernel | integration | clone current Eldyrwild store; run status then apply with exact P | one new revision Q, parent=P, published=true, C revision-bound | no descendant, extra revision, or canonical root mutated by test |
| Old P stays historical truth | projection | regression | project P after Q exists | X is current in P; X′ absent/non-current | P behavior changes |
| Q exposes corrected current truth | projection | contract | project Q | X non-current; X′ current with cultists→Lysandra `threatens` | old+new both current, neither current, wrong endpoint/predicate |
| Only exact target support changes | assertion support | adversarial | fingerprint all support records whose active/history includes `contribution:86ea…` before/after | target moves to contradicted lineage; every sibling support/provenance exact-equal | any sibling drift |
| Original Session-8 authority remains historical | graph/source data | contract/regression | compare source seal + artifact/evidence identifiers before/after; changed-path audit | source-seal fixture/corpus bytes unchanged; old contribution/evidence still loadable | source prose/seal/evidence rewrite/delete |
| Stale parent cannot mutate | service + Kernel CAS | adversarial | status P → publish unrelated R → apply expected P | stale failure; R remains head; no C authority | wrapper auto-refreshes to R and writes |
| Multi-source/target drift fails closed | service + Kernel | adversarial | synthetic/captured target gains second supporter or target status changes | no head move; no X contradiction; no X′ | one source silently selected |
| Artifact tamper fails closed | service | integrity | mutate copy of C bytes/linkage/replacement after locked digest **and** mutate raw file bytes after locked SHA256 | `integrity_failure` before mutation; byte-level seal covered, not only semantic field mutation | changed C accepted as approved |
| Canonical live-write fence | CLI + service | adversarial | apply with resolved root = configured `world_graph_root()` and without `--allow-live-world` | fail closed; no mutation; status still readable without the flag | apply succeeds against canonical root without second opt-in |
| X′ collision / unrelated-current fails closed | service + Kernel | adversarial | pre-create unrelated/conflicting X′ edge ID, or X′ already current from unrelated authority | no mutation | collision reused/merged or `+1/−1` destroyed |
| Exact retry is idempotent | service + Kernel | adversarial | apply exact C on Q; status reports `already_applied` via revision-bound C proof | `published=false`/existing no-op diagnostic; head=Q; lineage counts remain one | second descendant/duplicate support; `already_applied` inferred from support/edge shape alone |
| Q replay is deterministic | rebuild | contract/integrity | `rebuild_from_contributions(... compare_revision_id=Q, publish=False)` | `rebuild_equivalent_to_pinned_revision` (**NOT WAIVABLE** — forbid waiving known baseline rebuild failures) | rebuild differs, invents authority, or rebuild failure is waived |
| Current semantic pipeline recognizes the correction without exception | existing effective analyzer | integration observation | analyze exact P and Q on real clone | parent-relative delta: `semantic(Q)==semantic(P)`, `represented(Q)==represented(P)+1`, `residual(Q)==residual(P)-1`, `mechanics(Q)==mechanics(P)`; X historically materialized/inspectable; X absent from Q's current effective residual set; X′ current and represented; source seals unchanged; if and only if P is exact canonical historical `346/294/52/2`, also record stronger exact `346/295/51/2`; no new adapter/special interpretation | parent-relative delta fails, or change to analyzer/catalog required to obtain it |
| Historical anchor stays historical | existing effective analyzer | regression | analyze historical anchor after Q proof | remains `346/294/52/2` (historical absolute baseline for the adjudication anchor itself) | anchor fixture/meaning moves |
| No hidden production scope | repository diff | contract | changed-path/diff commands | only §4 + allowed test fixtures | any production path outside §4 |

Run and record exact results for at least:

```bash
uv sync --locked

uv run ruff check \
  apps/live_control_server/services/eldyrwild_lysandra_threat_direction_correction.py \
  scripts/apply_eldyrwild_lysandra_threat_direction_correction.py \
  tests/test_eldyrwild_lysandra_threat_direction_correction.py

uv run pytest tests/test_eldyrwild_lysandra_threat_direction_correction.py -q

uv run pytest \
  tests/test_graph_kernel_contribution_merge.py \
  tests/test_graph_kernel_contribution_rebuild.py \
  tests/test_dungeonmind_relationship_adjudication_continuity.py \
  tests/test_dungeonmind_relationship_effective_conformance.py \
  -q

git diff --check
git diff --stat <implementation-base>...HEAD -- <§4 paths plus approved test fixtures>
git diff --name-only <implementation-base>...HEAD
```

Also execute the operator CLI against a **temporary clone** of the real Eldyrwild root:

```text
1. clone configured Eldyrwild world store + required source-run anchors to a temp root
2. status against temp root; record exact P and eligibility evidence (including X in effective residual)
3. apply --expected-parent-revision-id P  (temp clone: no --allow-live-world required)
4. record exact Q and ContributionMergeResult
5. status again; must report already_applied via revision-bound C proof
6. apply exact C again against Q; must no-op
7. project P and Q and record exact X/X′ currentness
8. pinned rebuild Q; record equivalence (**NOT WAIVABLE**)
9. run existing effective conformance on P and Q; record parent-relative delta; if and only if P is exact canonical historical 346/294/52/2, also record stronger exact 346/295/51/2
10. rerun historical anchor effective conformance; record unchanged 346/294/52/2
11. prove apply against canonical world_graph_root() without --allow-live-world fails closed; status remains readable
```

### Minimal live / dogfood proof

```text
Existing surface used:
  Headless operator CLI + existing World Graph/Kernel; no new UI or route.

Smallest realistic scenario:
  Copy the real configured Eldyrwild store to a temporary root, retain read access to the real sealed Session-8 source run, inspect eligibility, and apply the exact approved Lysandra correction once.

Expected observation:
  P is eligible; one Q publishes; old P remains unchanged; Q projects cultists→threatens→Lysandra only; siblings/source history survive; rebuild equals Q (**NOT WAIVABLE**); existing effective analyzer observes the parent-relative P→Q delta (stronger absolute 346/295/51/2 only iff P is the exact historical 346/294/52/2 baseline).

Evidence captured:
  exact implementation SHA, P, Q, target assertion/contribution IDs, X′ assertion ID, C contribution ID/source-payload digest/raw artifact SHA256, status/apply results, projection assertions, sibling-support fingerprint, source-seal hash, rebuild diagnostic, P and Q effective-conformance counts and parent-relative delta.
```

This real-clone proof is a merge gate for this **real data correction**. Do not weaken it to an optional/skip-only test. If the real Eldyrwild store or required source-run anchors are unavailable, stop and report missing acceptance authority; do not substitute a synthetic “equivalent” world for the real proof.

### Baseline failure protocol

For any required command already failing on implementation base:

- run the same command on base and head;
- record exact failure names/counts for both;
- do not call the gate green;
- require an explicit operator waiver if the failure remains an acceptance gate;
- no waiver may excuse failure of the real-clone correction, stale-parent, sibling-preservation, source-history, **pinned rebuild reconstructing Q**, or parent-relative semantic observation gates;
- explicitly forbid waiving known baseline rebuild failures for the Q replay invariant.

## §8 Required review handback

The review handback, not the PR description, must include:

1. Exact PR URL or branch/head SHA being reviewed.
2. §1 Mission and merge-ready invariant copied exactly.
3. Exact implementation-base SHA and proof it descends from `413e8081…` (PR #536) and `99f1d18d…` (PR #534); proof contribution-integrity heal for `contribution:d3d244474789879c` is landed.
4. Confirmation that tracker/handoff dispatch gates were satisfied before code began (this post-#536 docs sync is a prerequisite; status was not READY until heal + tracker sync).
5. Nano-commit list and the discrete authority/apply/proof story for each.
6. Actual changed paths and focused diff stat limited to §4 + approved test fixtures.
7. Derived correction authority values:
   - X′ assertion ID;
   - C contribution ID;
   - C source-payload SHA256;
   - approved artifact raw SHA256.
8. Real-clone P and Q revision IDs and whether P was anchor or descendant.
9. Exact preflight continuity row for X on P, including proof X was in P's effective residual set.
10. Before/after target support payload and sibling-support fingerprint/equality proof.
11. Proof that source-seal/corpus historical authority was unchanged.
12. Old-P and corrected-Q projection proof.
13. Pinned rebuild result for Q (**NOT WAIVABLE**).
14. Exact retry and stale-parent results; proof `already_applied` used revision-bound C authority.
15. Existing effective-conformance observation on P and Q (parent-relative delta); if and only if P is exact canonical historical `346/294/52/2`, also the stronger exact `346/295/51/2`; historical anchor remains `346/294/52/2`.
16. Every §7 command/scenario and exact result with provenance: author-local, independently rerun local, CI, or manual/real-clone.
17. Baseline failures with base/head comparison; confirm no rebuild waiver.
18. Explicit operator waivers; `none` when none exist.
19. Paths outside §4; `none` or a stop report.
20. Stop conditions encountered and resolution; `none` when none exist.
21. Named successor `eldyrwild-effective-conformance-after-first-correction` remains unimplemented.
22. Confirmation that no source prose, source-seal/adjudication fixture, adapter, DungeonMind vocabulary, or generic Kernel semantics changed; docs/tracker edits stayed out of the implementation PR.
23. Proof that apply against canonical `world_graph_root()` without `--allow-live-world` fails closed.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true:

- [ ] Exactly one real Eldyrwild assertion correction was delivered — proved by §7 real-clone publish.
- [ ] C is a checked-in human-authored `GraphContribution`, not caller-injected semantics or a second correction schema — proved by artifact contract test/diff.
- [ ] Approved artifact seals both semantic source-payload digest and raw checked-in SHA256; tamper covers byte-level seal — proved by integrity tests.
- [ ] P eligibility is bound to exact ancestry + adjudication/source-seal continuity + X in effective residual + exact target support + X′ not already current from unrelated authority — proved by preflight tests and real-clone status.
- [ ] X is contradicted and X′ is current in exactly one Q — proved by support + projection tests.
- [ ] Every unrelated assertion/support/provenance from `contribution:86ea…` remains unchanged — proved by sibling fingerprint.
- [ ] Original Session-8 source/evidence/seal remains historical authority and unchanged — proved by source-history/diff evidence.
- [ ] Stale, multi-source, drifted, tampered, collision, and canonical-root-without-`--allow-live-world` paths fail closed — proved by adversarial tests.
- [ ] Status reports `eligible` / `already_applied` / `ineligible` / `integrity_failure`; `already_applied` uses revision-bound C proof — proved by status tests.
- [ ] Exact retry does not publish a second descendant or duplicate lineage — proved by retry test.
- [ ] Pinned `rebuild_from_contributions` reconstructs Q — proved by rebuild test; **NOT WAIVABLE**.
- [ ] Existing semantic analysis observes the parent-relative P→Q delta without analyzer/catalog changes; stronger absolute `346/295/51/2` recorded only iff P is exact historical `346/294/52/2` — proved by read-only semantic observation.
- [ ] Historical anchor still observes `346/294/52/2` — proved by regression observation.
- [ ] No production path outside §4 changed — proved by changed-path audit.
- [ ] No generic Kernel correction redesign, UI/route, global reversal, source rewrite, or second residual repair was introduced — proved by cumulative diff review.
- [ ] Docs/tracker/handoff edits stayed out of the implementation PR — proved by changed-path audit.
- [ ] Baseline failures are reported truthfully and any required waiver is explicit; rebuild failures are not waived.
- [ ] The named formal conformance successor remains unimplemented and unclaimed.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- the active tracker does not make this slice dispatchable after the post-#536 docs sync and contribution-integrity heal for `contribution:d3d244474789879c`;
- `origin/main` is not a descendant of the #536 merge (`413e8081…`) / #534 merge (`99f1d18d…`) anchors, or the predecessor correction/conformance API materially changed;
- `contribution:86ea8a3d97dd18cc` / `assertion:1dc0fef6561c3282` no longer identify the adjudicated target;
- the exact target has zero or multiple active supporters;
- P is not the adjudication anchor/descendant or X is not `ANCHOR`/`CARRIED_FORWARD` with verified source grounding/durable shape;
- X is not in P's effective residual set;
- X′ already exists with active current support from unrelated authority (would destroy the parent-relative `+1/−1` invariant);
- the target's scope/provenance shape cannot be represented by the existing PR #534 correction contract;
- the preferred X′ edge identity collides with existing authority and no canonical distinct identity is already dictated by repository rules;
- authoring C honestly requires a new source-domain enum or another new durable schema;
- the one-off service would need a generic server route/API or arbitrary correction parameters;
- the real-clone proof cannot access the real Eldyrwild store/source anchors;
- the corrected Q does not produce the parent-relative conformance delta under the existing analyzer without changing analyzer/catalog semantics;
- pinned rebuild fails to reconstruct Q (do not waive);
- any source prose, source-seal/adjudication fixture, generic Kernel code, adapter catalog, DungeonMind vocabulary, or unrelated residual must change to make the correction appear successful;
- correction lifecycle reversal becomes necessary;
- a path outside §4/bounded test fixtures is required;
- a required acceptance command has a new head-only failure or needs an unapproved waiver.

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

## Named successor — remains false in this PR

`eldyrwild-effective-conformance-after-first-correction`

That successor owns the durable/documented descendant semantic re-anchor after Q exists. It should consume the exact Q revision and correction IDs from the Lysandra BUILD PR, prove continuity behavior for the old finding and ordinary DungeonMind representation for X′, and update the canonical effective-conformance evidence while leaving the original adjudication revision/source seals immutable. It owns formal current-descendant fixture/tracker re-anchoring and **must record the actual current baseline** on the live head — do not force historical absolute counts onto an evolved live head. If and only if the eligible parent was demonstrably the exact canonical historical `346/294/52/2` baseline, the stronger exact result `346/295/51/2` may be recorded; otherwise re-anchor to the observed post-correction counts. It must not retroactively become part of this correction PR.
