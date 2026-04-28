# Review — Sentence-level hub routing failure modes (Campaign 2 Session 20, PC manifest)

**Date:** 2026-04-28  
**Audience:** GM / reviewer (plain language; no internal hypothesis labels in section titles).  
**Scope:** Live cohorts from `evals/sentence_routing_retrieval_falsification/` on **PC-only** manifests for Session 20 recap slices. This document describes **what keeps failing**, grounded in committed cohort summaries and sidecars—not prompt tuning opinion.

**What the harness grades (one paragraph):** For each short text fragment (“sentence unit”) from a recap, the model must either assign **zero or more player-character hub slugs** from a fixed list, or abstain. Gold rows mark cases where specific PCs **must** appear, **must not** appear, or where **non-routing labels** (diagnostic buckets) are expected for telemetry. A run “fails” when any gold check fails or when the model output violates schema rules (e.g. contradictory fields).

**Note on file paths:** Artifact filenames may still contain legacy harness prefixes (`sentence_routing_stage_b_*`). That does not mean this review uses “stage” jargon—it is only how runs were saved on disk.

---

## 1. Executive summary (what the evidence agrees on)

1. **The dominant failures are routing judgments, not cost explosions.** Per-run costs on slice cohorts stayed roughly **$0.004–$0.008** per run on `gpt-5.4-mini`; cohort sums for N=3–5 slices landed around **$0.013–$0.028** (see cohort `cost_usd` in files cited below).
2. **“Don’t attach PCs when it’s really about NPCs / places / objects”** has stayed comparatively stable on several slices: many cohorts show **zero** wrongful PC attachments where gold expects none (per-run breakdowns in cited JSON).
3. **The hard problems cluster into four shapes:** (A) whole-party vs narrow-cast mismatch, (B) multi-PC same-beat completeness, (C) listener / reported-speech boundary to a PC, (D) rare **internally contradictory model output** (assigns hubs but also emits a “placeholder” diagnostic label—caught by validation before scoring routing parity).
4. **Optional prompt addenda are not a universal fix.** One addendum improved some party-roster slices but did not clear the **mixed sentinel** scenario at N=5; a stricter addendum removed one failure mode at the cost of new misses elsewhere (see §7).

---

## 2. Failure mode A — Whole-party spread vs narrow cast (two opposite errors)

**Plain description:** Some recap units call for **every PC on the roster** as the joint subject (party name, “the team,” joint movement). Others call for **only the PCs named or clearly implicated in that same unit**. The model often **under-spreads** (misses one or more roster slots when it should copy the full party list) or **over-spreads** (assigns all PCs when gold expects only a subset for that unit).

**Typical signature in artifacts:** violations cite **missing expected hubs** for roster-copy rows (e.g. `u-L0026-03`, `u-L0030-03`) or **too many hubs assigned** when gold expects only a subset for that unit.

**Evidence (mixed sentinel scenario — roster-copy, multi-PC, and abstain-pressure rows in one gold file; N=5):**

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185202Z.json` — `u-L0030-03` missed full roster in **3/5** runs; `u-L0026-06` failed **5/5** (mix of missing hubs vs one over-route).
- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185204Z.json` — strict prompt: `u-L0026-06` still missed **Bonogo** in **5/5**; `u-L0030-03` missed in **4/5**; `u-L0026-03` missed in **2/5** (stricter narrow-multi-PC rules traded away some roster-copy recall vs continuation-only).

**Reviewer takeaway:** This is not a single knob problem. Treat **“copy roster exactly”** and **“only PCs substantively in this beat”** as **different decisions** that need either clearer gold adjudication, a structural pre-tag for units, or separate prompt precedence—not one continuity paragraph.

---

## 3. Failure mode B — Same-beat multi-PC roles (subset completeness)

**Plain description:** In one short unit, **two or three PCs** each play an identifiable role (actor, rescue target, locus of action). Gold expects **those** slugs—not the whole party. The model often returns **too small** a set (drops a PC who is still grammatically central to that unit).

**Typical signature:** Missing expected hubs on units like `u-L0026-06` while assigning a strict subset (commonly **Caelynn + Ephanna** without **Bonogo**).

**Evidence:** Same cohort summaries as §2 (`evals/sentence_routing_retrieval_falsification/README.md` documents recurring misses on `u-L0026-06`, including dropped **Bonogo** under the strict prompt variant). Failure repeats across runs (not one-off noise).

**Reviewer takeaway:** This failure mode is orthogonal to roster-copy: it needs **role intersection**, not party-wide expansion.

---

## 4. Failure mode C — Listener / reported-speech boundary (PC hub vs abstain)

**Plain description:** Some units are **NPC-led speech or concern** where a PC is conversationally present (“listening locus”) but **not** the retrieval subject of the beat. Gold may say **no PC hub**; the model often **still attaches one or more PC hubs** because a PC is salient in the sentence.

**Anchor row:** `u-L0018-10` (appears repeatedly as the residual failure after other fixes).

**Evidence:**

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185646Z.json` — cohort **2/5 PASS**; remaining failures include **false PC attachment** on this row in **3/5** runs (see harness notes in `evals/sentence_routing_retrieval_falsification/README.md` for the same cohort).

**Reviewer takeaway:** This is partly **product intent**: does the GM want “anything Bonogo heard” on Bonogo’s timeline, or only beats where Bonogo is an actor/object/decision locus? Until that intent is pinned, prompt tweaks will thrash.

---

## 5. Failure mode D — Internally contradictory outputs (validator failures)

**Plain description:** Occasionally the model assigns **one or more PC hubs** *and* emits a **non-empty placeholder-style diagnostic label** in the same row. That combination is **disallowed by schema**: if hubs are assigned, the diagnostic label must be empty. These rows fail validation before normal gold checks.

**Typical signature:** Per-run sidecars record validation failures such as **“routing_diagnostic_bucket must be null when assigned_hubs is non-empty.”**

**Evidence:**

- Concrete example is quoted in `evals/sentence_routing_retrieval_falsification/README.md` (multi-PC recall slice: run failed solely because of one contradictory row on unit `u-L0032-09`).
- Abstain-pronoun-context reruns: continuation variant showed this contradiction in **2/5** runs (`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185648Z.json`); strict variant drove this to **0/5** (`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185646Z.json`).

**Reviewer takeaway:** This is a **real confused-routing signal**, distinct from “picked wrong PC.” Cohort JSON still exposes it under the internal counter name `b0_diagnostic_null_when_assigned`—use it as engineering telemetry, not as a label for humans unless you adopt it formally.

---

## 6. Non-failure / telemetry-only: placeholder taxonomy disagreements

**Plain description:** When no hubs are assigned, the model must pick one of several **semantic placeholder categories** (NPC-shaped vs location-shaped vs object/event-shaped vs empty). Gold may disagree with the model on category while **agreeing that no PC hub should attach**.

**Evidence:** Bucket-focused cohorts record soft **diagnostic expectation** pass/fail counts without failing the run gate unless enforcement is turned on—see e.g.  
`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--N3--20260428T164441Z.json`.

**Reviewer takeaway:** Treat these as **labeling hygiene**, not proof that routing-to-hubs is solved or broken—unless you explicitly decide category accuracy is a product requirement.

---

## 7. Cross-cutting lesson from prompt variants (why “one more paragraph” stalled)

**Observation:** A **party-continuation addendum** improved some **party-boundary** and **bucket-sentinel** slices but **did not** clear the **mixed sentinel** scenario at N=5. A **stricter narrow-multi-PC addendum** reduced **whole-roster over-expansion** on some draws but **increased roster-copy misses**—the trade-off is spelled out under “graveyard” / strict-vs-continuation comparison in `evals/sentence_routing_retrieval_falsification/README.md` (2026-04-28 N=5 mixed-sentinel results).

**Reviewer takeaway:** The remaining gap is less “missing explanation text” and more **ambiguous unit taxonomy at authoring time** (what kind of unit is this?) plus **GM retrieval intent** on edge rows like §4.

---

## 8. Suggested review checklist (for you, before more engineering)

For each recurring failing unit ID you care about:

1. **Intent:** Should this beat be retrievable from **each** named PC’s continuity surface, **one** PC’s, or **no** PC’s?
2. **Mechanism:** Is the failure **spread**, **subset**, **listener boundary**, or **schema contradiction** (§§2–5)?
3. **Gold action:** If intent is unclear, adjust gold + `scenario_notes` **before** chasing prompt wins—per `.cursor/rules/gold-realignment-vs-deflation.mdc`.

---

## 9. Primary artifact index (for deep dives)

| Topic | Example cohort summary |
|------|-------------------------|
| Mixed sentinel (roster + multi-PC + abstain rows), continuation variant, N=5 | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185202Z.json` |
| Mixed sentinel, strict variant, N=5 | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185204Z.json` |
| Abstain-pronoun context, continuation, N=5 | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185648Z.json` |
| Abstain-pronoun context, strict, N=5 | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185646Z.json` |

Gold scenario definitions live under `evals/sentence_routing_retrieval_falsification/gold/` (filenames match `scenario_id` strings inside the JSON).

Full prose context for each unit lives in corpus recap markdown referenced by scenario JSON (`input.recap_relative_path`); **do not paste player-identifying excerpts into public threads**—review locally.
