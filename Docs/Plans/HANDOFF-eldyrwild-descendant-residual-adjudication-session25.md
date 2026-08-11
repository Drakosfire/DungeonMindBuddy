# HANDOFF — Eldyrwild descendant residual adjudication (Session-25)

**Created:** 2026-08-10
**Status:** READY FOR BUILD — land this handoff on `main` before implementation; depends on third effective re-anchor (`R_current = Q₃`) being DONE
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md`
**Conversation name:** `DUNGEONMIND-CUTOVER`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `ADJUDICATION: seal Session-25 descendant residual findings`
**Branch:** `build/eldyrwild-descendant-residual-adjudication-session25`

**Required predecessors:**
- PR #550 merge + canonical C₃ live exit (`P→Q₃`)
- Third effective re-anchor DONE (`eldyrwild-effective-conformance-after-third-correction` / #554) so formal `R_current = Q₃ = rev:ba3abde1bfc3659795bcd77bb55eb9f7`

> **Dispatch gate:** Fresh `origin/main` must include the third re-anchor merge as ancestor. Canonical Eldyrwild head and formal `R_current` must both be exact `rev:ba3abde1bfc3659795bcd77bb55eb9f7` with analyzer `367 / 311 / 56 / 3`. Prove `remaining_residual_edge_ids − ELDYRWILD_RESIDUAL_FINDINGS` equals the exact seven Session-25 edge IDs below. If head, counts, or the seven-set drift, stop and re-capture.

---

## Shared vocabulary

| Term | Definition |
| --- | --- |
| **A** | Immutable historical adjudication anchor `rev:3413bf6f5044cf2680233f5e37c90dcf` with sealed **59** findings + source seals. Untouchable by this slice. |
| **S25** | Session-25 ingest child of A: `rev:df92031efcd379b9c52e0df2e3ff7217`, `operation_ids=[contribution:a4231edb9a228963]`. First revision containing the seven edges. |
| **Q₃ / R_current** | Formal current baseline after third re-anchor: `rev:ba3abde1bfc3659795bcd77bb55eb9f7` (`367 / 311 / 56 / 3`). |
| **U₇** | The exact seven UNADJUDICATED residual edge IDs at Q₃ (`remaining − A findings`). |
| **Descendant adjudication authority** | A sealed findings+seals ledger pinned to a proven A-descendant, composed with (never rewriting) A’s 59 findings. |
| **UNADJUDICATED** | Effective-conformance inventory bucket for current residuals that lack an active sealed finding — not a #526 disposition enum value. |

---

## §0 Why these seven are UNADJUDICATED

They are **post-A inventory growth**, not holes in the sealed 59:

1. All seven are absent from A’s graph and from `ELDYRWILD_RESIDUAL_FINDINGS`.
2. All seven first appear at S25 (`rev:df92031e…`), parent(S25)==A, via `contribution:a4231edb9a228963` (Session-25 recap).
3. Continuity only iterates sealed A findings → no rows for U₇.
4. Effective conformance therefore classifies them `UNADJUDICATED` (`unadjudicated_remaining_count=7`, `requires_readjudication_count=0`).
5. C₁/C₂/C₃ re-anchors left `UNADJUDICATED: 7` unchanged.

`REQUIRES_READJUDICATION` is the wrong home: that state is for sealed findings whose durable shape/source grounding drifted. U₇ need **new sealed judgments**.

---

## §1 Exact U₇ (capture)

```text
1. edge:faction:town-guards-mireward-gate:reports_threat_in:mystery:session25:west-wall-screaming-and-dark-shapes-below
2. edge:item:crossbow_bolt_light_source:controls_comms_with:loc:north-road
3. edge:node:hesta-bramblewood:governs:organization:merchant-s-crossroads-apothecary
4. edge:node:orik:participates_in:organization:warehouse-gate-sheltering-group
5. edge:node:thrin-branchborn:caused_by:mystery:session25:thrin-ambush-by-hybrid-creatures
6. edge:organization:merchant-s-crossroads-apothecary:same_as:loc:crooked-retort
7. edge:pc:ephanna:hires:node:thrin-branchborn

shared:
  introduced_by_contribution_id = contribution:a4231edb9a228963
  first_revision = rev:df92031efcd379b9c52e0df2e3ff7217
  source_artifact = artifact:recap:longmont-c2:session-25:fd38b5915b32
  content_sha256 = fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
  domain = session-25 / recap
  support_state at Q₃ = supported (active singleton = contribution:a4231edb9a228963)
```

Hypothesis dispositions (BUILD must source-ground; do not treat as sealed truth):

| Edge | Likely class |
| --- | --- |
| 6 `same_as` Crooked Retort | `IDENTITY_NOT_RELATIONSHIP` |
| 2 `controls_comms_with` light→road | `SOURCE_CORRECTION_REQUIRED` or compound |
| 7 `hires` Ephanna→Thrin | `SOURCE_CORRECTION_REQUIRED` |
| 5 `caused_by` Thrin→mystery | `COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP` / correction |
| 3 `governs` Hesta→apothecary | `SOURCE_CORRECTION_REQUIRED` or adapter candidate |
| 4 `participates_in` Orik→shelter | representable / correction after grounding |
| 1 `reports_threat_in` guards→west-wall | parallel existing threat-observation residuals |

---

## §2 Mission and merge-ready invariant

Seal source-grounded adjudication for exact U₇ as a **descendant adjudication authority** that composes with immutable A/#526 findings, so effective conformance can assign disposition/ownership and later correction slices may select those edges by class.

**Merge-ready invariant:**

> For exact `R_current = rev:ba3abde1bfc3659795bcd77bb55eb9f7`, historical A adjudication (59 findings + seals + fixtures + SHA pins) remains byte-stable; the new descendant ledger covers exactly U₇ with verified Session-25 excerpts; continuity carries A∪descendant findings only across proven descendants with unchanged durable shape/source grounding; effective conformance at Q₃ shows these seven leave the `UNADJUDICATED` bucket into adjudicated classes while headline counts stay `367 / 311 / 56 / 3`; this PR publishes **no** World Graph revision.

This is a **read/seal slice**. It owns no graph mutation and no correction semantics.

**DONE definition:** Merged adjudication package with proofs below. No post-merge live apply gate.

---

## §3 Recommended design (Option A — sealed descendant ledger)

Keep A’s `ELDYRWILD_RESIDUAL_FINDINGS` frozen at exactly 59.

Add a parallel sealed package:

```text
ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS  (exactly U₇)
eldyrwild_relationship_descendant_residual_source_seals_v1.json
descendant adjudication + continuity fixtures/tests
```

Compose into continuity and effective conformance:

- Continuity: carry A findings ∪ descendant findings when ancestry + durable shape + sealed grounding hold.
- Effective: disposition/ownership from merged active findings → former U₇ leave `UNADJUDICATED`.
- Preserve A’s fail-closed “exactly 59” guard for the historical map.

**Rejected options:**

| Option | Why reject |
| --- | --- |
| Extend A findings to 66 / retarget seals to Q₃ | Rewrites immutable adjudication; breaks SHA pins, `EXPECTED_RESIDUAL_COUNT=59`, ROADMAP ban |
| Correction-first without adjudication | Violates tracker gate; loses class routing; breaks continuity-gated eligibility |
| Soft labels only in effective fixture | Not authority; cannot gate corrections |

Descendant pin recommendation: seal findings against durable shape/source grounding verified at Q₃ (and prove ancestry through S25). Do not invent a second “current baseline”; Q₃ remains `R_current`.

---

## §4 Implementation scope (exact allowlist)

| Action | Path |
| --- | --- |
| Create | `Docs/Plans/HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md` |
| Create | descendant findings module/API (A map stays frozen at 59) |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_descendant_residual_source_seals_v1.json` |
| Create | descendant adjudication fixture(s) + owning tests |
| Modify | `apps/.../relationship_adjudication_continuity_v1.py` — merge descendant seals/findings without relaxing A’s 59 guard |
| Modify | `apps/.../relationship_effective_conformance_v1.py` — resolve disposition from merged active findings |
| Modify | `tests/fixtures/.../eldyrwild_relationship_effective_conformance_v1.json` — disposition inventory only (`UNADJUDICATED` for these seven → adjudicated classes); headline `367/311/56/3` unchanged |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` |

Unchanged by design: Kernel mutation APIs, correction services/artifacts, A findings map, A residual adjudication fixture, A source seals, historical continuity fixture SHA pins for A’s 59, World Graph revisions.

---

## §5 Required proofs

1. At Q₃: `remaining − A_findings == exact U₇` (regression).
2. A adjudication fixture SHA and A source-seal `sealed_count=59` unchanged.
3. New seals: each of U₇ has excerpt SHA verified against Session-25 artifact bytes.
4. Continuity at Q₃: 59 A rows still `CARRIED_FORWARD`; 7 descendant rows `ANCHOR` or `CARRIED_FORWARD` with grounding verified.
5. Effective at Q₃: counts still `367/311/56/3`; `unadjudicated_remaining_count=0` (or transitional only if staged and documented); ownership sums consistent; none of U₇ remain in the UNADJUDICATED inventory.
6. Non-descendant / wrong-world / wrong-edge fail closed.
7. Canonical world-graph tree digest + head unchanged (no `--allow-live-world`, no publish).
8. Hermetic injected-authority tests for the merge path (mirror #531 style).

---

## §6 Explicit non-goals

- Mutating Eldyrwild / correcting any of U₇ in this PR
- Editing A findings, A seals, A residual adjudication fixture, or historical SHA pins
- Treating U₇ as `REQUIRES_READJUDICATION`
- Whole-world cutover; DungeonMind vocabulary publication
- Omnibus zeroing of the 56-edge ledger
- Rewriting Session-25 recap prose
- Selecting/implementing the next correction slice inside this PR

---

## §7 Nano-commit shape (BUILD)

1. `ADJUDICATION: seal Session-25 descendant residual findings and source seals`
2. `TEST: prove A∪descendant continuity and UNADJUDICATED clearance at Q₃`
3. `DOCS: tracker/status — descendant adjudication authority; residual selection unblocked for U₇`

---

## §8 Successor after DONE

```text
buddy-remaining-relationship-correction-slices
```

Select one bounded Buddy residual from the Q₃ ledger by adjudicated class — now including former U₇ — never omnibus.

---

## §9 One-sentence invariant

> Seal source-grounded judgments for the seven Session-25 residuals as a descendant ledger composed with immutable A authority, clearing `UNADJUDICATED` without rewriting history or mutating the World Graph.
