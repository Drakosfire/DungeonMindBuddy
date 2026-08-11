# HANDOFF — Eldyrwild descendant residual adjudication (Session-25)

**Created:** 2026-08-10
**Updated:** 2026-08-10 — repair multi-anchor continuity composition + successor-state contract (review `4902636441`)
**Status:** DESIGN REPAIR — multi-anchor + successor-state contract locked; land this handoff on `main` before BUILD; do **not** dispatch BUILD from an incomplete composition model
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md`
**Conversation name:** `DUNGEONMIND-CUTOVER`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `ADJUDICATION: seal Session-25 descendant residual findings`
**Branch:** `build/eldyrwild-descendant-residual-adjudication-session25`

**Required predecessors:**
- PR #550 merge + canonical C₃ live exit (`P→Q₃`)
- Third effective re-anchor DONE (`eldyrwild-effective-conformance-after-third-correction` / #554, merge `21e28e7871e84b00a8aa80593b894cb629e652ac`) so formal `R_current = Q₃ = rev:ba3abde1bfc3659795bcd77bb55eb9f7`

> **Dispatch gate:** Fresh `origin/main` must include #554 as ancestor. Canonical Eldyrwild head and formal `R_current` must both be exact `rev:ba3abde1bfc3659795bcd77bb55eb9f7` with analyzer headline `367 / 311 / 56 / 3`. Prove `remaining_residual_edge_ids − ELDYRWILD_RESIDUAL_FINDINGS` equals the exact seven Session-25 edge IDs below. If head, counts, or the seven-set drift, stop and re-capture. Do not start BUILD until this DESIGN contract (multi-anchor + successor-state) has merged.

---

## Shared vocabulary

| Term | Definition |
| --- | --- |
| **A** | Immutable historical adjudication anchor `rev:3413bf6f5044cf2680233f5e37c90dcf` with sealed **59** findings + source seals. Untouchable by this slice. Owns the existing single-anchor continuity report. |
| **S25** | Session-25 ingest child of A: `rev:df92031efcd379b9c52e0df2e3ff7217`, `graph_payload_sha256=5361c9734c84702a5ac6b012c1b5470c5991f3d31bb836721375fbab3727c71f`, `operation_ids=[contribution:a4231edb9a228963]`. **Exact descendant-adjudication anchor** — first revision containing U₇. |
| **Q₃ / R_current** | Formal current effective-conformance baseline after third re-anchor: `rev:ba3abde1bfc3659795bcd77bb55eb9f7` (`367 / 311 / 56 / 3`). Current conformance truth — **not** the historical adjudication origin for U₇. |
| **U₇** | The exact seven UNADJUDICATED residual edge IDs at Q₃ (`remaining − A findings`). |
| **A continuity authority** | Existing v1 continuity analyzer/report: one report-level `anchor_revision_id` / `anchor_graph_payload_sha256`, `anchor_finding_count=59`, shapes loaded only from A. Remains semantically untouched. |
| **S25 descendant authority** | Separate sealed 7-row findings+seals ledger whose continuity is anchored at **S25** (not A, not Q₃). |
| **Composed continuity view** | Downstream composition of A authority ∪ S25 authority (or an explicit multi-authority v2 report). Not a silent union into the old single-anchor schema. |
| **Closed historical successor dispositions** | `EXPLICIT_ADAPTER_CANDIDATE`, `NEW_PREDICATE_CANDIDATE`, `EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE` when they encode *already-closed* A-era successor work. Forbidden in the residual ledger only under that historical closed authority. |
| **Open descendant candidate dispositions** | The same class names when freshly sealed by S25 authority for previously unadjudicated edges. Honest residual candidates — not automatically closed. |
| **UNADJUDICATED** | Effective-conformance inventory bucket for current residuals that lack an active sealed finding — not a #526 disposition enum value. |

---

## §0 Why these seven are UNADJUDICATED

They are **post-A inventory growth**, not holes in the sealed 59:

1. All seven are absent from A’s graph and from `ELDYRWILD_RESIDUAL_FINDINGS`.
2. All seven first appear at S25 (`rev:df92031e…`), parent(S25)==A, via `contribution:a4231edb9a228963` (Session-25 recap).
3. Continuity only iterates sealed A findings → no rows for U₇.
4. Effective conformance therefore classifies them `UNADJUDICATED` (`unadjudicated_remaining_count=7`, `requires_readjudication_count=0`).
5. C₁/C₂/C₃ re-anchors left `UNADJUDICATED: 7` unchanged.

`REQUIRES_READJUDICATION` is the wrong home: that state is for sealed findings whose durable shape/source grounding drifted. U₇ need **new sealed judgments** under a descendant authority whose historical origin is S25.

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
  first_revision / descendant adjudication anchor = rev:df92031efcd379b9c52e0df2e3ff7217
  descendant anchor_graph_payload_sha256 = 5361c9734c84702a5ac6b012c1b5470c5991f3d31bb836721375fbab3727c71f
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
| 3 `governs` Hesta→apothecary | `SOURCE_CORRECTION_REQUIRED` or open descendant adapter/predicate/endpoint candidate |
| 4 `participates_in` Orik→shelter | representable / correction after grounding |
| 1 `reports_threat_in` guards→west-wall | parallel existing threat-observation residuals |

---

## §2 Mission and merge-ready invariant

Seal source-grounded adjudication for exact U₇ as an **S25-anchored descendant adjudication authority** that composes with immutable A/#526 findings, so effective conformance can assign disposition/ownership and later correction/adapter slices may select those edges by class — without rewriting A continuity semantics or pretending Q₃ is their adjudication origin.

**Merge-ready invariant:**

> For exact `R_current = rev:ba3abde1bfc3659795bcd77bb55eb9f7`: historical A adjudication (59 findings + seals + fixtures + SHA pins) and the existing A continuity report (`anchor_revision_id=A`, `anchor_finding_count=59`) remain byte-stable and semantically single-anchor; a separate S25-anchored descendant ledger covers exactly U₇ with verified Session-25 excerpts and S25 payload pin `5361c973…`; composed continuity at Q₃ shows 59 A rows `CARRIED_FORWARD` under A authority and 7 descendant rows `CARRIED_FORWARD` under S25 authority (never re-anchored to Q₃); former U₇ leave the `UNADJUDICATED` bucket because they now have sealed authority; headline representation counts stay `367 / 311 / 56 / 3` unless this PR intentionally owns a semantic representation change (it does not); open descendant candidate dispositions may remain residual without triggering the historical closed-successor forbidden guard; this PR publishes **no** World Graph revision.

This is a **read/seal/composition slice**. It owns no graph mutation and no correction or adapter implementation semantics.

**DONE definition:** Merged adjudication + composition package with proofs below. No post-merge live apply gate.

---

## §3 Locked architecture — multi-anchor continuity composition

### Why a naive `A ∪ U₇` union fails

The existing continuity implementation has **one** report-level `anchor_revision_id` / `anchor_graph_payload_sha256` and derives every expected edge shape from that one anchor:

| If you… | Failure |
| --- | --- |
| Keep the report anchored at A and union in U₇ | U₇ do not exist at A → expected-shape construction fails |
| Re-anchor the union at Q₃ | Historical 59 are silently re-anchored to current state → immutable-A boundary defeated |
| Inflate `anchor_finding_count` 59→66 under the old schema | Callers lose the ability to distinguish which authority authorized each row |

Therefore BUILD must **not** “just union findings into the existing A continuity report.”

### Locked choice (Option A′ — dual authority, compose downstream)

1. **Keep A continuity analyzer/report semantics unchanged.**
   - Still anchored at A.
   - Still `anchor_finding_count=59`.
   - Still loads expected shapes only from A.
   - Historical continuity fixtures / SHA pins for A’s 59 stay byte-stable.

2. **Create a separate seven-row S25 descendant authority.**
   - Findings map + source seals for exact U₇ only.
   - Continuity for those rows is anchored to **S25 = `rev:df92031efcd379b9c52e0df2e3ff7217`** with exact payload `5361c9734c84702a5ac6b012c1b5470c5991f3d31bb836721375fbab3727c71f`.
   - At the S25 revision itself, descendant rows are `ANCHOR`.
   - At every proven descendant of S25 — including Q₃ — descendant rows are `CARRIED_FORWARD`.
   - Q₃ remains `R_current` / current conformance truth; it is **not** their historical adjudication origin.

3. **Compose the two authorities downstream** (preferred for this slice), **or** introduce an explicit multi-authority v2 report if composition cannot be represented without lying to the old schema.
   - Composition must expose, per row, which authority authorized it (`A` vs `S25`) and which anchor revision/payload that authority uses.
   - Report-level metadata after composition must **not** quietly rewrite A’s `anchor_finding_count=59` into 66 under the old single-anchor fields.
   - If a v2 envelope is required, the old A report remains loadable and unchanged; v2 is additive.

### Shape / grounding pin

Seal descendant findings against durable shape + source grounding as they exist at the **S25 adjudication origin**, then prove those same durable facts still hold when carried to Q₃. Do not seal U₇ as if they were adjudicated at Q₃.

### Rejected options

| Option | Why reject |
| --- | --- |
| Extend A findings to 66 / retarget seals to Q₃ | Rewrites immutable adjudication; breaks SHA pins, `EXPECTED_RESIDUAL_COUNT=59`, ROADMAP ban |
| Silent union into old single-anchor continuity | Either missing U₇ at A or silent re-anchor of the 59 at Q₃ |
| Correction-first without adjudication | Violates tracker gate; loses class routing; breaks continuity-gated eligibility |
| Soft labels only in effective fixture | Not authority; cannot gate corrections |

---

## §3b Locked architecture — successor-state / forbidden-disposition scoping

Effective conformance today rejects remaining residuals whose disposition is in:

```text
EXPLICIT_ADAPTER_CANDIDATE
NEW_PREDICATE_CANDIDATE
EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE
```

That guard encodes **closed historical successors** from the A-era work (`_FORBIDDEN_REMAINING_DISPOSITIONS` under active A continuity). A brand-new S25 candidate is **not** automatically closed.

### Staged semantics BUILD must implement

1. **Source-ground honestly.** Do not force U₇ into terminal classes merely to keep the fixture green.
2. **Clear `UNADJUDICATED`** because each of the seven now has sealed descendant authority — regardless of whether the sealed disposition is terminal or an open candidate class.
3. **Keep headline counts `367 / 311 / 56 / 3`.** This PR does not own semantic representation change; candidate dispositions remain residual until a later bounded adapter/vocabulary/correction slice moves them.
4. **Scope the forbidden-remaining guard to the historical closed A authority** (or replace it with explicit per-finding successor state such as `successor_state=CLOSED_HISTORICAL` vs `OPEN_DESCENDANT_CANDIDATE`). Do **not** weaken the guard generically for all findings.
5. **Later adapter / new-predicate / endpoint-extension implementation is a separate bounded slice.** Descendant adjudication may emit the candidate disposition; it does not implement the successor work.

If BUILD discovers that composition requires a transitional effective inventory field for open descendant candidates, document it explicitly — but do not smuggle representation changes into headline counts.

---

## §4 Implementation scope (exact allowlist)

| Action | Path |
| --- | --- |
| Modify | `Docs/Plans/HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md` |
| Create | descendant findings module/API (A map stays frozen at 59; S25 authority is separate) |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_descendant_residual_source_seals_v1.json` |
| Create | descendant adjudication fixture(s) + owning tests |
| Create | S25-anchored descendant continuity path and/or explicit composed / multi-authority report surface |
| Modify | `apps/.../relationship_adjudication_continuity_v1.py` — keep A path semantically untouched; add S25 authority + composition (or additive v2). Do **not** union U₇ into A’s single-anchor report |
| Modify | `apps/.../relationship_effective_conformance_v1.py` — resolve disposition/ownership from composed active findings; scope `_FORBIDDEN_REMAINING_DISPOSITIONS` to closed historical A authority (or per-finding successor state) |
| Modify | `tests/fixtures/.../eldyrwild_relationship_effective_conformance_v1.json` — disposition/ownership inventory only (`UNADJUDICATED` for these seven → adjudicated classes, possibly including open candidate classes); headline `367/311/56/3` unchanged |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` |

Unchanged by design: Kernel mutation APIs, correction services/artifacts, A findings map, A residual adjudication fixture, A source seals, historical A continuity fixture SHA pins / `anchor_finding_count=59`, World Graph revisions, adapter/vocabulary implementation for any newly sealed open candidates.

---

## §5 Required proofs

1. At Q₃: `remaining − A_findings == exact U₇` (regression).
2. A adjudication fixture SHA, A source-seal `sealed_count=59`, and A continuity report semantics (`anchor_revision_id=A`, `anchor_finding_count=59`) unchanged.
3. New seals: each of U₇ has excerpt SHA verified against Session-25 artifact bytes.
4. S25 descendant continuity: at S25 the seven rows are `ANCHOR` under S25 authority with payload pin `5361c973…`; at Q₃ the seven rows are `CARRIED_FORWARD` under S25 authority (not `ANCHOR`, not re-anchored to Q₃).
5. A continuity at Q₃: 59 A rows still `CARRIED_FORWARD` under A authority; shapes still derived from A.
6. Composed view (or v2): callers can distinguish which authority authorized each row; old single-anchor fields do not silently report 66 A findings.
7. Effective at Q₃: headline counts still `367/311/56/3`; `unadjudicated_remaining_count=0`; ownership sums consistent; none of U₇ remain in the UNADJUDICATED inventory.
8. If any of U₇ seals as an open candidate disposition, it may remain residual without tripping the historical closed-successor forbidden guard; A-era closed candidates remain forbidden as today.
9. Non-descendant / wrong-world / wrong-edge / wrong-anchor-payload fail closed.
10. Canonical world-graph tree digest + head unchanged (no `--allow-live-world`, no publish).
11. Hermetic injected-authority tests for the composition path (mirror #531 style), including an adversarial “naive union into A report” rejection if that path exists.

---

## §6 Explicit non-goals

- Mutating Eldyrwild / correcting any of U₇ in this PR
- Editing A findings, A seals, A residual adjudication fixture, or historical A continuity SHA pins
- Re-anchoring A continuity or U₇ adjudication origin to Q₃
- Treating U₇ as `REQUIRES_READJUDICATION`
- Implementing adapters / new predicates / endpoint extensions for open descendant candidates in this PR
- Whole-world cutover; DungeonMind vocabulary publication
- Omnibus zeroing of the 56-edge ledger
- Rewriting Session-25 recap prose
- Selecting/implementing the next correction slice inside this PR
- Weakening `_FORBIDDEN_REMAINING_DISPOSITIONS` globally so historical closed successors can reappear as residual

---

## §7 Nano-commit shape (BUILD)

1. `ADJUDICATION: seal Session-25 descendant residual findings and source seals (S25 anchor)`
2. `TEST: prove dual-authority continuity composition and UNADJUDICATED clearance at Q₃`
3. `DOCS: tracker/status — S25 descendant authority composed with immutable A; residual selection unblocked for U₇`

---

## §8 Successor after DONE

```text
buddy-remaining-relationship-correction-slices
```

Select one bounded Buddy residual from the Q₃ ledger by adjudicated class — now including former U₇ — never omnibus. Open descendant candidate dispositions route to separate adapter/vocabulary slices, not silent representation in this PR.

---

## §9 One-sentence invariant

> Seal source-grounded judgments for the seven Session-25 residuals as an S25-anchored descendant authority composed with immutable A continuity — clearing `UNADJUDICATED` at Q₃ as `CARRIED_FORWARD` under S25, without rewriting A, re-anchoring history to Q₃, or forcing open candidates into closed terminal classes.
