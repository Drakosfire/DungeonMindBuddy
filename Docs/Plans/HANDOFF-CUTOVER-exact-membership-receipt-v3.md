---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER — exact adopted-membership checkpoint
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-exact-membership-receipt-v3.md
  - Implementation repository: Drakosfire/DungeonMind

  ## Predecessor truth
  - DungeonMind PR #35 is the merged bounded read-only correspondence predecessor (merge `9ff0d1f9e278e44fb1444bdf1fda8beb6348bc11`, 2026-08-18; 3 review cycles; steward split disposition).
  - The Buddy guarded predecessor sync recording that merge truth landed with the commit that activated this handoff.
  - The parked pinned-snapshot catch-up handoff remains blocked behind this slice.

  Strengthen existing-world adoption receipts from cardinality-only history pins to
  one exact membership checkpoint over source artifacts, source revisions,
  contributions, and identity decisions. A stale-snapshot classification is legal
  only when the currently durable adopted membership still matches that checkpoint.
---

# HANDOFF — exact adopted-membership receipt V3

**Created:** 2026-08-17
**Status:** ACTIVE — predecessor gate satisfied: DungeonMind PR #35 merged `9ff0d1f9e278e44fb1444bdf1fda8beb6348bc11` (2026-08-18) and the §11 guarded Buddy predecessor sync lands with this commit; the exact-membership receipt V3 implementation is the current CUTOVER work and may dispatch per §8/§9
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-exact-membership-receipt-v3.md`
**Conversation/workstream:** `CUTOVER — exact adopted-membership checkpoint`
**Flow / owner:** `CUTOVER`
**Direction:** DESIGN → CODE → REVIEW
**Buddy design base:** `93ad974d2f9690e5f8f552059d2fb71f5181b9b9`
**DungeonMind predecessor PR:** #35, merged head `36e9c0d21aaccbd9dfe850a5f6fe27e1e9789529`; merge SHA `9ff0d1f9e278e44fb1444bdf1fda8beb6348bc11` (2026-08-18)
**DungeonMind implementation base:** `9ff0d1f9e278e44fb1444bdf1fda8beb6348bc11` (post-#35 `main`)
**Suggested implementation branch:** `dnd/cutover-exact-membership-receipt-v3`
**Suggested implementation PR title:** `CUTOVER: pin exact adopted membership in receipt V3`

> Repository authority beats this handoff. Re-anchor both repositories before dispatch and replace provisional predecessor facts with exact merged truth.
>
> This slice is the explicit split created by DungeonMind PR #35 Review Cycle 3. PR #35 proved exact bundle identity, fail-closed resolution for reachable/complete enumerated history, closed result algebra, and read-only correspondence behavior, but its V2 receipt retains only four adoption-time cardinalities. Exact adopted membership under a different supplied snapshot therefore requires a stronger durable checkpoint.

## §1 Mission and merge-ready invariant

**Mission:** make the adoption receipt itself sufficient to prove the exact adopted durable history membership before a `STALE` classification can hide deletion, same-cardinality substitution, or same-ID coherent rewrite.

**Merge-ready invariant:** for an `ExistingWorldAdoptionReceiptV3`, the receipt carries one deterministic `membership_sha256` calculated at adoption from the exact sealed bundle's four durable history families. On every correspondence check, DungeonMind independently enumerates the current durable membership, recomputes the same digest after normal adapter integrity verification, and compares it with the receipt **before any classification is returned**.

The four pinned families are exactly:

1. source artifacts;
2. source revisions;
3. graph contributions;
4. identity decisions.

The checkpoint is identity **and** payload sensitive: each family contributes sorted `(record_id, record_fingerprint)` pairs, not counts alone.

Required behavior:

```text
V3 receipt + exact current membership + different valid source snapshot
  → normal STALE classification

V3 receipt + deleted adopted record + different valid source snapshot
  → PersistenceIntegrityError; never STALE

V3 receipt + same-cardinality adopted-ID substitution + different valid source snapshot
  → PersistenceIntegrityError; never STALE

V3 receipt + same-ID coherent durable rewrite + different valid source snapshot
  → PersistenceIntegrityError; never STALE

V3 receipt + exact supplied adopted bundle + reconstructable durable divergence
  → preserve the existing detailed correspondence algebra:
     MISMATCH where reconstruction succeeds and differs;
     PersistenceIntegrityError where adopted identities/rows are missing or invalid
```

This slice does not add a new correspondence classification. `CORRESPONDING / STALE / MISMATCH / NOT_ADOPTED` remains the closed classification vocabulary.

## §2 Why this slice exists

DungeonMind PR #35's Cycle 3 STOP identified one exact remaining class:

```text
adopt A containing unreferenced U
→ delete U
→ insert different valid X so family counts remain unchanged
→ present valid different snapshot B
```

Complete enumeration plus receipt counts can see the current membership and its cardinality, but a V2 receipt cannot independently say whether current `X` or missing `U` was the member originally adopted. If the supplied bundle is B, its identities cannot safely reconstruct A's historical membership.

A V3 membership digest closes that ambiguity without storing the whole bundle or creating a second writer.

This is deliberately inserted **before** the parked `HANDOFF-CUTOVER-pinned-exact-snapshot-catchup.md` slice. Catch-up must not be built on a stale-state classifier that can bless same-cardinality substitution.

## §3 Predecessor and sequencing truth

### PR #35 predecessor

Merged truth (recorded by the §11 guarded Buddy predecessor sync):

- repository: `Drakosfire/DungeonMind`
- PR: #35 — `DONE`
- base: `d2204dd0901237d8b446b4f2363f896306e32e6f`
- merged head: `36e9c0d21aaccbd9dfe850a5f6fe27e1e9789529`
- merge SHA: `9ff0d1f9e278e44fb1444bdf1fda8beb6348bc11` (2026-08-18)
- Review Cycle 1: `4955043192` — CHANGES REQUIRED
- Review Cycle 2: `4955268953` — CHANGES REQUIRED
- Review Cycle 3: `4955637320` — STOP/CHANGES REQUIRED under the original exact-membership interpretation; residual explicitly split into this successor
- final disposition: merged by steward split decision (PR disposition comment), 3 formal review cycles; the split residual is owned by this handoff, not silently solved

The pre-dispatch gate is satisfied:

1. #35 is merged on the exact Cycle-3-reviewed head `36e9c0d2…`;
2. this guarded Buddy predecessor sync records that merge and review-cycle truth;
3. repository authority states that exact membership checkpointing is the current CUTOVER slice, not that the whole correspondence/catch-up chain is complete;
4. product authority remains Buddy and `CUTOVER_NOT_READY` remains true.

### Parked catch-up successor

`cutover/design-pinned-snapshot-catchup` remains parked. Its handoff must be re-anchored after this slice merges because a successful catch-up will need to advance the exact membership checkpoint from source snapshot A to B rather than treating the original adoption receipt as a forever-current checkpoint.

No catch-up implementation may dispatch from the parked handoff unchanged.

## §4 Exact membership digest contract

Receipt V3 adds one field to the V2 receipt facts:

```text
ExistingWorldAdoptionReceiptV3
  schema_version = "dm_existing_world_adoption_receipt_v3"
  adoption_id: str
  world_id: str
  bundle_sha256: str
  source_provenance: ExistingWorldAdoptionSourceProvenanceV1
  published_revision_id: str
  graph_schema: str
  graph_payload_sha256: str
  adopted_at: datetime
  source_artifact_count: int
  source_revision_count: int
  contribution_count: int
  identity_decision_count: int
  membership_sha256: str
```

All existing V2 fields retain their current semantics. Counts remain useful diagnostics; they are no longer sufficient proof of exact membership.

### Canonical membership payload

The V3 schema fixes the hashing algorithm. Implement one shared DungeonMind helper used by adoption, correspondence, and promotion:

```json
{
  "schema_version": "dm_existing_world_adoption_membership_v1",
  "source_artifacts": [
    {"record_id": "...", "record_fingerprint": "..."}
  ],
  "source_revisions": [
    {"record_id": "...", "record_fingerprint": "..."}
  ],
  "contributions": [
    {"record_id": "...", "record_fingerprint": "..."}
  ],
  "identity_decisions": [
    {"record_id": "...", "record_fingerprint": "..."}
  ]
}
```

Rules:

- each family is sorted lexicographically by `record_id` before hashing;
- duplicate IDs are invalid before hashing;
- `record_fingerprint` is the repository's canonical SHA-256 of the record model's JSON representation, matching the persistence adapter fingerprint semantics for these four record families;
- the envelope itself is canonical-JSON hashed with SHA-256;
- family names and `dm_existing_world_adoption_membership_v1` are domain separators and part of the digest;
- list ordering supplied by callers/adapters must not affect the result;
- changing any record ID, record payload, family membership, or family assignment changes `membership_sha256`.

Do not define membership as a concatenated count string or as hashes of unordered Python container representations.

## §5 New-adoption behavior

The accepted source artifact remains `ExistingWorldAdoptionBundleV2`; this slice does **not** require a Bundle V3 or Command V3.

For a new V2-bundle adoption after this capability lands:

1. parse and validate the exact canonical bundle as today;
2. compute `bundle_sha256` and graph identity as today;
3. compute `membership_sha256` directly from the parsed bundle records already in hand;
4. perform the existing atomic adoption unit of work unchanged in authority shape;
5. persist `ExistingWorldAdoptionReceiptV3` as the terminal receipt.

The existing `existing_world_adoptions` table already stores `schema_version`, `record_fingerprint`, and a JSON payload. A new scalar PostgreSQL column is **not required** merely to persist `membership_sha256`; do not introduce a migration unless re-anchor proves the current persistence contract actually requires one.

New V1-bundle legacy behavior is not part of CUTOVER and must not be broadened casually.

## §6 Existing Eldyrwild V2 receipt — selected policy

**Selected: steward-supervised V2 → V3 promotion from the exact sealed source bundle.**

Permanent silent degradation is rejected for the cutover-critical Eldyrwild world. The actual adopted world must gain the same exact-membership checkpoint required of new V3 receipts before later CUTOVER gates depend on `STALE`.

The accepted historical source remains:

- Buddy bundle blob: `274cdd9e6d38d5a00aa43d780779e95a7919d975`
- bundle SHA-256: `90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f`
- source revision: `rev:0c644e56b45bcaac709012206e3e41c2`
- adopted DND revision: `rev:34b1f8e2625d5ba693fc726a2a1a4720`

### Promotion safety contract

Promotion is explicit; ordinary adoption replay must not silently mutate a V2 receipt.

Given exact sealed bundle bytes and a world with a V2 receipt:

1. parse/validate the supplied bundle and require its exact `bundle_sha256`, `adoption_id`, `world_id`, source provenance, graph identity, and published revision to agree with the V2 receipt;
2. independently enumerate the current four durable membership families through normal verified repository reads;
3. compute expected membership digest from the sealed bundle;
4. compute current durable membership digest from the enumerated records;
5. require the two digests to match exactly;
6. require the existing exact-bundle correspondence check to succeed for the supplied A snapshot; a `MISMATCH`, missing row, invalid row, or dependency failure aborts promotion;
7. atomically replace only the receipt's versioned representation with the equivalent V3 receipt carrying that digest;
8. preserve every V2 adoption fact byte/semantically equal except `schema_version`, `membership_sha256`, and the receipt's derived record fingerprint/payload representation;
9. do not mutate graph head/revisions, source records, contributions, identity decisions, evidence, or source authority;
10. read back and reconstruct the V3 receipt before success is returned.

### Promotion replay/conflict

- V3 receipt already present with the same exact adoption facts and digest → exact no-op success;
- V2 receipt + exact bundle/current digest → one atomic promotion;
- V2 receipt + wrong bundle → fail, zero mutation;
- V2 receipt + current membership digest differing from sealed bundle → fail, zero mutation;
- V3 receipt + different requested digest/bundle identity → fail integrity/conflict, zero mutation.

A promotion digest must **never** be minted solely from the current database state. That would bless the very corruption this slice exists to detect.

## §7 Correspondence behavior with V3 and legacy receipts

The receipt is still retrieved independently by `get_for_world(world_id)`. No latest-head, label, or current-row guessing is introduced.

### V3 preflight

After receipt/revision/history rows reconstruct successfully and before returning a classification:

```text
current_membership_sha256 = hash(enumerated durable four-family membership)
checkpoint_matches = current_membership_sha256 == receipt.membership_sha256
```

Then:

- if exact supplied bundle identity differs from the V3 receipt and `checkpoint_matches` is true → the existing `STALE` path remains legal;
- if exact supplied bundle identity differs and `checkpoint_matches` is false → raise `PersistenceIntegrityError` with a stable reason such as `adopted_membership_checkpoint_mismatch`; never return `STALE`;
- if exact supplied bundle identity matches and the checkpoint differs, preserve the existing detailed comparison semantics: missing adopted identities/invalid durable records raise; reconstructable coherent divergence may return `MISMATCH`; it may not return `CORRESPONDING`;
- a matching checkpoint does not replace graph/evidence/history comparisons. `CORRESPONDING` still requires the existing six-check contract to match.

### Unpromoted V2 degradation

A V2 receipt has no independent exact-membership checkpoint.

Safe compatibility behavior is:

- exact supplied bundle identity equal to the V2 receipt may continue through detailed comparison because the supplied sealed A bytes provide the expected membership identities;
- a different supplied bundle that would otherwise classify `STALE` must fail closed with `PersistenceIntegrityError` / stable `adoption_membership_checkpoint_required` reason until the receipt is promoted;
- never silently preserve the weaker cardinality-only `STALE` guarantee after V3 support exists.

The cutover-critical Eldyrwild proof must promote to V3, so this degraded path is a legacy guardrail rather than the intended operational state.

`NOT_ADOPTED` remains only a `get_for_world` miss. Persistence unavailability remains `PersistenceUnavailableError`.

## §8 Expected DungeonMind write lease

Finalize against exact post-#35 `main` before dispatch. Expected paths are:

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/dungeonmind/contracts/existing_world_adoption.py` | Add `ExistingWorldAdoptionReceiptV3` and receipt schema literal |
| Modify | `src/dungeonmind/contracts/__init__.py` | Export V3 under established convention |
| Create | `src/dungeonmind/domain/existing_world_membership.py` | Shared canonical four-family membership digest helper |
| Modify | `src/dungeonmind/application/repositories.py` | Expand durable receipt alias; add narrowly named V2→V3 promotion repository seam if required |
| Modify | `src/dungeonmind/application/existing_world_adoption.py` | New adoptions emit V3; explicit supervised promotion application seam |
| Modify | `src/dungeonmind/application/existing_world_correspondence.py` | V3 checkpoint preflight + explicit V2 stale degradation |
| Modify | `src/dungeonmind/infrastructure/memory/repositories.py` | V3 receipt support and atomic promotion parity |
| Modify | `src/dungeonmind/infrastructure/postgres/existing_world_adoption.py` | V3 reconstruction/insert + row-locked atomic V2→V3 promotion |
| Modify | `tests/unit/test_existing_world_adoption.py` | Digest/new-adoption/promotion contract proofs |
| Modify | `tests/integration/test_postgres_existing_world_adoption.py` | PostgreSQL V3 persistence/promotion atomicity |
| Modify | `tests/unit/test_existing_world_correspondence.py` | V3 and legacy-V2 classification/error algebra |
| Modify | `tests/integration/test_postgres_existing_world_correspondence.py` | Owning-boundary adversarial membership proofs |
| Reuse unchanged | `tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json` | Exact sealed promotion authority |

### Bounded discovery

- package export files already established by post-#35 `main` may be modified only when required for the V3 public receipt/application seam;
- **no migration is pre-authorized** because the current receipt table's versioned JSON payload can carry the new field. If implementation proves a migration is actually required, STOP and re-brief rather than adding it silently;
- no Buddy runtime files;
- no catch-up receipt/runtime;
- no graph-head mutation APIs;
- no product routing/read switch.

If post-#35 repository shape materially differs, stop and re-brief the exact path lease.

## §9 Adversarial evidence required

The implementation PR must prove all of these at the owning boundary:

| Sequence | Required outcome |
|---|---|
| new V2 bundle adoption | terminal receipt is V3 and `membership_sha256` equals independently recomputed sealed-bundle membership digest |
| same records presented in different enumeration order | same membership digest |
| change one record ID only | different membership digest |
| change one record payload/fingerprint only | different membership digest |
| delete one adopted unreferenced source record, then present B | `PersistenceIntegrityError`; never `STALE` |
| delete adopted U + insert unrelated X, restoring the same count, then present B | `PersistenceIntegrityError`; never `STALE` |
| coherently rewrite same adopted ID/payload fingerprint, then present B | `PersistenceIntegrityError`; never `STALE` |
| exact A + coherent same-ID divergence | existing algebra preserved: `MISMATCH` where reconstruction succeeds; never `CORRESPONDING` |
| exact A + missing adopted identity | `PersistenceIntegrityError` |
| pristine A + valid B | `STALE`, both source revisions still reported, all five later diagnostic checks remain `not_evaluated` |
| V2 exact A | detailed exact-bundle comparison remains possible |
| V2 + valid B before promotion | explicit membership-checkpoint-required error; never cardinality-only `STALE` |
| exact Eldyrwild V2 promotion | V3 receipt produced; expected sealed digest == current durable digest; no graph/history/head mutation |
| V2 promotion after same-count substitution | fail; receipt remains V2; zero other mutation |
| V3 promotion replay | canonical no-op / same receipt |
| repeated V3 correspondence | deterministic result; zero writes |
| dependency unavailable during enumeration | `PersistenceUnavailableError`; no classification and no recovery write |

The PostgreSQL proof must include before/after counts and exact head/revision identities so receipt promotion cannot be mistaken for a world-state mutation.

## §10 Classification and error compatibility

This slice strengthens a durable precondition; it does not create a fifth state.

Existing public result shape remains:

```text
CORRESPONDING | STALE | MISMATCH | NOT_ADOPTED
```

Typed errors remain raised rather than encoded as classifications.

New stable diagnostic reasons may be added under existing `PersistenceIntegrityError`, expected at minimum:

- `adopted_membership_checkpoint_mismatch`
- `adoption_membership_checkpoint_required`
- `adoption_receipt_promotion_identity_mismatch` or equivalent narrowly named promotion failure

Do not add a new top-level error class unless implementation proves the existing taxonomy cannot truthfully express the failure and the steward re-briefs it first.

## §11 Authority and backward-looking Buddy sync

When #35 actually merges, before this implementation dispatches, the steward re-anchors and synchronizes the mutable CUTOVER authority set. Expected set:

- `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
- `Docs/Design/STATUS-world-graph-continuity-spine.md`
- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Plans/HANDOFF-CUTOVER-observational-correspondence-drift.md`
- this handoff if exact predecessor pins/status require finalization

Required meaning:

- record #35 exact merged head/merge SHA/final review disposition truthfully;
- record that #35 delivered the bounded read-only correspondence foundation;
- record the Cycle 3 exact-membership class as intentionally owned by this V3 successor rather than silently calling it solved;
- make exact-membership receipt V3 the current CUTOVER work;
- keep pinned snapshot catch-up parked behind V3;
- keep actual quiescence, writer ownership transfer, product authority switch, rollback operator workflow, first DND-owned mutation, and Buddy demolition unresolved;
- preserve Buddy product authority and `CUTOVER_NOT_READY`.

No routine standalone documentation PR is required for that predecessor sync.

## §12 Review handback

Return:

1. Review Cycle N and exact DND PR/head/base;
2. #35 exact predecessor merge SHA and review truth;
3. exact `membership_sha256` algorithm implementation path and canonical test vector;
4. exact sealed Eldyrwild bundle digest and promoted V3 receipt identity;
5. proof expected bundle membership digest equals independently enumerated durable membership digest before promotion;
6. V2→V3 promotion before/after receipt identity and proof no world/head/history rows changed;
7. same-count substitution + stale-B owning-boundary proof;
8. same-ID coherent rewrite + stale-B owning-boundary proof;
9. exact-A coherent divergence proof preserving `MISMATCH` semantics;
10. V2 stale degradation proof;
11. full unit/integration/type/lint/diff-check evidence with inherited failures compared base/head rather than rewritten as green;
12. actual changed paths versus the finalized §8 lease;
13. confirmation product authority remains Buddy / `CUTOVER_NOT_READY`.

## §13 Acceptance rubric

- [ ] `ExistingWorldAdoptionReceiptV3` exists with exact `membership_sha256` semantics.
- [ ] Membership digest covers all four families as sorted `(record_id, record_fingerprint)` pairs under a fixed domain-separated canonical payload.
- [ ] New V2-bundle adoption emits V3 without requiring a new bundle schema.
- [ ] Exact Eldyrwild V2 receipt is promoted only under steward-supervised sealed-bundle/current-membership equality.
- [ ] Promotion changes only the receipt representation and is atomic/idempotent.
- [ ] V3 correspondence verifies exact current membership before allowing `STALE`.
- [ ] Deletion cannot hide behind `STALE`.
- [ ] Same-cardinality substitution cannot hide behind `STALE`.
- [ ] Same-ID coherent rewrite cannot hide behind `STALE`.
- [ ] Identity-matched reconstructable divergence still preserves `MISMATCH`; missing/invalid adopted state remains an integrity error.
- [ ] Unpromoted V2 does not silently return cardinality-only `STALE`.
- [ ] `CORRESPONDING / STALE / MISMATCH / NOT_ADOPTED` remains the classification vocabulary.
- [ ] No catch-up, writer transfer, read switch, dual write, or product-authority transition is introduced.
- [ ] Parked catch-up remains blocked until this slice merges and is re-anchored.
- [ ] Buddy remains product authority; disposition remains `CUTOVER_NOT_READY`.

## Stop conditions

Stop and report rather than expanding if:

- exact membership requires storing the complete source bundle or a second durable history ledger rather than one receipt digest;
- a new PostgreSQL migration is required despite the existing versioned JSON receipt payload;
- record fingerprint semantics differ between the application helper and persistence adapters for any of the four families;
- V2→V3 promotion cannot be made atomic without mutating graph/history state;
- exact Eldyrwild current durable membership no longer equals the sealed source bundle at promotion time;
- V3 preflight requires catch-up/current-authority selection semantics to decide what checkpoint is current;
- the implementation needs to change the public correspondence classification vocabulary;
- the parked catch-up slice must be implemented to make V3 meaningful;
- any required path falls outside the finalized write lease.

The next CUTOVER slice after this one is the re-anchored pinned exact-snapshot catch-up design. That successor must explicitly define how a successful A→B catch-up advances the exact membership checkpoint; it may not keep treating the original adoption receipt's A checkpoint as forever current.
