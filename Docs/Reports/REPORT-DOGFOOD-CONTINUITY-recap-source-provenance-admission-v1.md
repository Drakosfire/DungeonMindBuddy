# REPORT — DOGFOOD-CONTINUITY: recap source provenance admission v1

**Status:** Cycle 2 HOLD repaired in place; awaiting Review Cycle 3. Historical accepted World unchanged.
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md)
**Implementation branch:** `dogfood-continuity/recap-source-provenance-admission-v1`
**Dispatch base:** `main@933d347990b96a6dc84eb7e0881dba476dd3d462`
**Classification:** P3 — source pair was never admitted (P1) and recap evidence was incompatible with the admitted artifact (P2)
**Witness World:** `world:recap-provenance-pg` on disposable `dmb_cutover_test`
**Accepted World:** not mutated
**GOVERNED RECAP SOURCE PROVENANCE CONTRACT:** Cycle 2 HOLD — not yet accepted
**PRODUCT LOADABILITY:** `NOT_READY` (historical accepted World still unread)
**OPERATOR DOGFOOD:** `NOT_READY`

This slice does **not** rebuild `dmb_current_corpus_acceptance_v1`. Case B remains the defect witness for that World.

---

## Verdict

```text
P1  confirmable prepare while DungeonMind source pair is absent
    TRUE before repair — prepare never called WorldGraphSourceAdmissionAuthority

P2  admitted pair, but published recap evidence incompatible
    TRUE before repair — two stacked mismatches:
      1. source_extraction used _EmptyEvidenceView → SourceDomain.OTHER
      2. after (1), Buddy producer key "recap" ≠ DungeonMind lift key "session_recap"
         (v1 EvidenceRef lifts source_domain_key = SESSION_RECAP.value)

P3  both required by one provenance-complete write
    TRUE — this PR

P4  Buddy-correct pair still rejected by DungeonMind SourceRepository/projection
    FALSE for a fresh write after P1+P2 repair

P5  only in-place rewrite of the accepted World would make it readable
    not attempted — historical remediation remains a separate steward decision
```

A confirmable recap candidate can no longer exist while its DungeonMind source pair is absent. A fresh published object survives native scoped projection and exact-object / search / neighborhood / evidence at the child revision.

---

## Localization ledger (fresh recap write, before repair)

Reproduced on a disposable World, not the accepted corpus database.

```text
Buddy source_artifact_id:          artifact:recap:longmont-c2:session-9
Buddy source_revision token:       sha256:<session-9.md digest>
source domain / campaign / session / world:
  recap / longmont-c2 / session-9 / world:recap-provenance-pg
catalog-aware DM source_revision_id: same sha256 token (no collision)
SourceRepository artifact before prepare: missing
SourceRepository revision before prepare: missing
candidate confirmable?:            yes (P1)
sealed proposal source fields:     candidate_admission only; no source_admission
SourceRepository after prepare:    still missing
v2 EvidenceRef source_artifact_id: artifact:recap:longmont-c2:session-9
v2 EvidenceRef source_revision_id: sha256 token
v2 EvidenceRef source_domain:      other   (empty evidence-view fallback)
v2 EvidenceRef locator / can_open: none / false
```

Owning seams:

1. `prepare_candidate_graph_admission()` returned `confirmable=True` without `prove_or_admit()`.
2. `_build_pair_to_dm()` is derivation, not SourceRepository admission.
3. `_build_v2_candidate()` used `_EmptyEvidenceView()` for `source_kind=source_extraction`, so `_map_contribution_evidence_ref()` stamped `SourceDomain.OTHER`.
4. After (3) was repaired, native projection still rejected the object as `evidence_source_domain_mismatch`: admitted `SourceArtifactV2.source_domain_key="recap"` versus lifted evidence key `"session_recap"`.

P4 was not the first owning defect. DungeonMind's check is exact key+family equality; Buddy had to admit and stamp the pair that check already requires.

---

## Repair

Reuse the mounted `WorldGraphSourceAdmissionAuthority`. No second catalog, no direct SQL, no DungeonMind pin change, no accepted-World rewrite.

| Boundary | Change |
|---|---|
| Prepare | After a candidate is structurally confirmable, prove/admit the exact recap source pair and seal `effect.source_admission`. Nonconfirmable inspects do not admit. |
| Canonical key | Buddy producer domain `recap` is admitted as DungeonMind family key `session_recap`, matching v1→v2 evidence lift. Exact replay is the SourceRepository idempotent put, not a `prove()` fallback. |
| Confirm | Missing/drifting sealed admission fails closed. Writes-layer `_reprove_source_extraction()` snapshot-proves before `_build_pair_to_dm()`. |
| Evidence | `source_extraction` uses `_recap_extraction_evidence_view` (`session_recap`, admitted revision locator) instead of the generic OTHER fallback. OTHER remains the missing-evidence default for unrelated contributions. |
| Live run | `extract_promote.prepare` requires the canonical registry `source_artifact` and fails closed when it is missing. Synthesis remains test/non-product only. |
| Domain | Non-recap source domains are rejected before admission so evidence cannot be stamped `session_recap` over a worldbuilding/other artifact. |
| Conflict | `source_identity_conflict` from `prove_or_admit()` is not converted into success via `prove()`. Exact replay stays on the idempotent SourceRepository contract. |

`contribution_mapping.py` was not changed. The OTHER fallback is still correct for empty stores; recap writes no longer depend on it.

---

## Review Cycle 1 HOLD (head `5827f7b360c2ae1adf4eff2df2757bd8fa9bdabe`)

Four blockers were real. This Cycle 2 head repairs them in place on #729:

1. Removed the `prove()` fallback on `source_identity_conflict`. Same-token / divergent artifact fingerprint now fails closed without proving the stored pair.
2. Product `extract_promote.prepare()` no longer synthesizes a source artifact when the canonical registry record is missing.
3. Non-recap domains are rejected in both `_canonical_recap_source_artifact` and `_scope_check_recap_source_artifact` before admission.
4. Added prepare→source-drift→confirm/head-unchanged and collision-safe same-token/different-artifact regressions through `prepare_candidate_graph_admission` / `confirm_candidate_graph_admission`. Confirm re-proves the sealed pair and fingerprint on that seam when an authority is injected, and `world_graph_writes` re-proofs independently. Out-of-lease edits to `tests/test_candidate_graph_admission_contract.py` and `tests/test_graph_preview_runner.py` remain reverted.

```text
FRESH GOVERNED RECAP WRITE CONTRACT = awaiting Cycle 2
PRODUCT LOADABILITY = NOT_READY
```

---

## Review Cycle 2 HOLD (head `c2a7b1819728409e1b1113ac08cea94b4332345b`)

Two authority-boundary blockers remained after Cycle 1. This Cycle 3 head repairs them in place on #729:

1. Removed the `PYTEST_CURRENT_TEST` in-memory catalog. Production `_source_admission_authority()` uses the mounted factory. Confirmable recap admission now requires the canonical source artifact; synthesis is gone. Existing contract/preview tests inject artifact + authority under the steward lease expansion.
2. Canonicalized Buddy `recap` → DungeonMind `session_recap` once in `DungeonMindWorldGraphSourceAdmissionAdapter._store_artifact_v2`. Candidate admission no longer rewrites the caller domain. Graph Review and recap candidate admission of the same artifact/token are exact no-op identity in both orders.

```text
FRESH GOVERNED RECAP WRITE CONTRACT = awaiting Cycle 3
PRODUCT LOADABILITY = NOT_READY
```

---

## Fresh native witness

Disposable database `dmb_cutover_test` (not `dmb_current_corpus_acceptance_v1`). Command:

```text
DMB_CUTOVER_TEST_DATABASE_URL=postgresql://…/dmb_cutover_test
uv run pytest -q tests/test_candidate_graph_source_provenance_admission.py
```

Postconditions on `world:recap-provenance-pg` / `candidate:brin`:

```text
source artifact exists                 yes (session_recap / SESSION_RECAP)
source revision exists                 yes
source pair snapshot-provable          yes at prepare; graph head unchanged
confirmable without admission          no
head advances exactly once on confirm  yes (product confirm seam)
exact retry                            same committed revision; already_applied
published object in scoped projection  yes
native exact-object                    outcome != empty; resolved_node_id = candidate:brin
native search "Brin"                   matched
native neighborhood seed               candidate:brin present
native evidence(node)                  session_recap anchors; not OTHER
prepare then delete source then confirm fail closed; head unchanged
prepare then fingerprint-drift then confirm fail closed; head unchanged
same token, different artifacts        catalog-aware `token::{artifact_id}` suffix through prepare
same token, divergent fingerprint      source_identity_conflict; prove() not used
missing canonical registry artifact    extract_promote.prepare fails closed
missing candidate source artifact      confirmable prepare fails closed; no synthesis
graph review then recap admission      exact no-op identity; stored key session_recap
recap admission then graph review      exact no-op identity; stored key session_recap
non-recap source domain                rejected before admission
unknown object id                      empty; no prefix guess
foreign campaign / fingerprint drift   fail closed before publication
```

Contract/preview companions inject source artifact + source-admission authority: `tests/test_candidate_graph_admission_contract.py`, `tests/test_graph_preview_runner.py::test_reviewable_unsupported_candidate_is_exact_admission_input`. `tests/test_cutover_dungeonmind_first_world_initialization.py::test_candidate_admission_real_postgres_sequence` remains out of lease and may fail closed without an explicit source artifact.

---

## What this Cycle 3 request does not establish

```text
historical accepted World repaired
C2S22 rev:24268294e868b30034e247aa9e23087b readable
full current-corpus product loadability
operator dogfood readiness
semantic coverage / Agent usefulness / model selection
```

Party-registry D0 objects on the witness World still carry `other` evidence against a party-registry artifact (`evidence_source_domain_mismatch`). They are genesis leftovers, not this recap write contract. They do not hide a freshly admitted recap object.

---

## Steward next action (not this PR)

After merge and state-authority sync, choose one:

```text
A. pristine candidate/source replay into a new acceptance World without model regeneration
B. pristine current-corpus acceptance rerun through this production path
C. separately designed historical provenance compatibility/backfill, only if the exact old World must be preserved
```
