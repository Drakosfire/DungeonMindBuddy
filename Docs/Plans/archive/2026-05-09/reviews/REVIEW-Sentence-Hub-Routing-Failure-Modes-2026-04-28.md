# Review — Sentence-level hub routing failure modes (Campaign 2 Session 20, PC manifest)

**Date:** 2026-04-28 · **Updated:** 2026-04-29 (harness telemetry + latest full-scenario run)  
**Audience:** GM / reviewer (plain language; no internal hypothesis labels in section titles).  
**Scope:** Live cohorts and full-scenario sidecars from `evals/sentence_routing_retrieval_falsification/` on **PC-only** manifests for Session 20 recap slices. This document describes **what keeps failing**, what recently improved, and what to try next, grounded in committed cohort summaries and sidecars—not prompt tuning opinion.

**What the harness grades (one paragraph):** For each short text fragment (“sentence unit”) from a recap, the model must either assign **zero or more player-character hub slugs** from a fixed list, or abstain. Gold rows mark cases where specific PCs **must** appear, **must not** appear, or where **non-routing labels** (diagnostic buckets) are expected for telemetry. A run “fails” when any gold check fails or when the model output violates schema rules (e.g. contradictory fields).

**Note on file paths:** Artifact filenames may still contain legacy harness prefixes (`sentence_routing_stage_b_`*). That does not mean this review uses “stage” jargon—it is only how runs were saved on disk.

---

## 1. Executive summary (what the evidence agrees on)

1. **The dominant failures are routing judgments, not cost explosions.** Per-run costs on slice cohorts stayed roughly **$0.004–$0.008** per run on `gpt-5.4-mini`; cohort sums for N=3–5 slices landed around **$0.013–$0.028**. Recent full Session 20 runs landed around **$0.031–$0.039** per attempt on comparable manifests (§2).
2. **Full-scenario headline scores moved with gold edits and instrumentation.** A **2026-04-28** sidecar shows **58/74** gold checks passing; a **2026-04-29** live run after rubric/prompt updates shows **64/74** graded passes but **strict-schema B0** still present on some rows (§2). An older **2026-04-27** sidecar reached **63/74** under earlier gold. Compare by bucket and `**wire_strict_parse_ok`**, not headline alone—the gold split shifted from **48/26** must-route/must-abstain to **50/24**.
3. **Recent progress is structural.** The current harness now has a campaign party registry, `the_party` sentinel handling, duplicate PC stripping when `the_party` is mixed with explicit PC slugs, diagnostic-bucket telemetry, and **always-on gold gate counting** with coercion/audit flags (§1 §6). That makes failures easier to diagnose even when headline pass rates fluctuate with gold edits.
4. **The hard problems cluster into four shapes:** (A) whole-party vs narrow-cast mismatch, (B) multi-PC same-beat completeness, (C) listener / reported-speech boundary to a PC, (D) rare **internally contradictory model output** (assigns hubs but also emits a “placeholder” diagnostic label—caught by validation before scoring routing parity).
5. **Optional prompt addenda are not a universal fix.** One addendum improved some party-roster slices but did not clear the **mixed sentinel** scenario at N=5; a stricter addendum removed one failure mode at the cost of new misses elsewhere (see §8).
6. **Gold gate totals are always counted in telemetry.** As of 2026-04-29, the Stage B runner never leaves `gold_gate_checks_*` null when gold exists: if strict wire JSON fails validation, the harness may **coerce** diagnostics for a grading-only second parse, or fall back to counting gates against an empty route map. Sidecars record `**wire_strict_parse_ok`** and `**graded_after_wire_coercion**` so you can tell whether the headline pass/fail included a strict-schema failure while still seeing B1/B2-style breakdowns (see §6).

---

## 2. Current progress snapshot

**Full-scenario comparison (2026-04-28 run):** Representative full Session 20 sidecar before the telemetry fix:

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260428T233927847613Z.json`
- Result: **58/74** gold checks passing; `must_route` **35/50**, `must_abstain` **23/24**.
- Failure buckets: `b1_missing_expected_hub=12`, `b1_over_route=3`, `b2_over_assigned=1`, `b0_diagnostic_null_when_assigned=0`.
- Cost: **$0.039401**.

**Full-scenario comparison (2026-04-29 run, post gold-gate telemetry + rubric tweaks):** Same scenario JSON (`scenario_c2_session20_pc.json`), including `**u-L0014-03` → `the_party`** party-roster gold and routing prompt rule **3b** (indirect PC / continuity owner). Live model output:

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-29/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260429T010351303942Z.json`
- Result: **64/74** gold checks passing (`must_route` **41/50**, `must_abstain` **23/24**). **Strict wire JSON still failed** (`B0: routes JSON invalid`) on two rows with `**event_or_object_placeholder`** while `**assigned_hubs` was non-empty**—the run remains `**pass: false`** because that violation is preserved. Telemetry shows `**wire_strict_parse_ok: false**` and `**graded_after_wire_coercion: true**`, meaning B1/B2 counts above were produced **after** diagnostic coercion for grading, not from a fully schema-clean wire payload.
- Routed judgment buckets (from graded output): `b1_missing_expected_hub=9`, `b2_over_assigned=1` (B0 line still listed under `violations.stage_b` but not duplicated into the legacy B0 histogram buckets the same way).
- Cost: **~$0.031** (`scenario_estimated_cost_usd` in sidecar).

Interpreting **64/74** vs **58/74:** the gold row set and party-row adjudication changed between these dates—use them as **illustrative** progress signals, not a controlled A/B. The durable learning is that **headline gold pass rate and strict-schema health are now both visible** in one artifact.

The best older full-scenario sidecar found on disk is:

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-27/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260427T015742700112Z.json`
- Result: **63/74** gold checks passing; `must_route` **40/48**, `must_abstain` **23/26**.
- Failure buckets: `b1_missing_expected_hub=8`, `b1_over_route=0`, `b2_over_assigned=3`.
- Cost: **$0.02794**.

**Interpretation:** The headline **58/74** (2026-04-28) is not "best ever." The 2026-04-28 run had stronger schema telemetry on the wire, cleaner abstain performance in that snapshot, and no diagnostic/hub contradiction failures in buckets, while dominant misses were B1 routing judgments. The 2026-04-29 run shows **higher graded gate pass count** but **still records a strict B0** until the model stops emitting illegal diagnostic+hubs combinations—so "better routing score" and "clean wire" are decoupled in reporting. Because must-route pressure increased when gold evolved, future comparisons should report:

- full-scenario `gold_gate_checks_pass / total`,
- `must_route pass / total`,
- `must_abstain pass / total`,
- B1 missing vs B1 over-route vs B2 over-assigned,
- B0 diagnostic contradiction count (and, since 2026-04-29, `**wire_strict_parse_ok`** / `**graded_after_wire_coercion**`),
- cost.

---

## 3. Failure mode A — Whole-party spread vs narrow cast (two opposite errors)

**Plain description:** Some recap units call for **every PC on the roster** as the joint subject (party name, “the team,” joint movement). Others call for **only the PCs named or clearly implicated in that same unit**. The model often **under-spreads** (misses one or more roster slots when it should copy the full party list) or **over-spreads** (assigns all PCs when gold expects only a subset for that unit).

**Typical signature in artifacts:** violations cite **missing expected hubs** for roster-copy rows (e.g. `u-L0026-03`, `u-L0030-03`) or **too many hubs assigned** when gold expects only a subset for that unit.

**Evidence (mixed sentinel scenario — roster-copy, multi-PC, and abstain-pressure rows in one gold file; N=5):**

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185202Z.json` — `u-L0030-03` missed full roster in **3/5** runs; `u-L0026-06` failed **5/5** (mix of missing hubs vs one over-route).
- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185204Z.json` — strict prompt: `u-L0026-06` still missed **Bonogo** in **5/5**; `u-L0030-03` missed in **4/5**; `u-L0026-03` missed in **2/5** (stricter narrow-multi-PC rules traded away some roster-copy recall vs continuation-only).

**Reviewer takeaway:** This is not a single knob problem. Treat **“copy roster exactly”** and **“only PCs substantively in this beat”** as **different decisions** that need either clearer gold adjudication, a structural pre-tag for units, or separate prompt precedence—not one continuity paragraph.

---

## 4. Failure mode B — Same-beat multi-PC roles (subset completeness)

**Plain description:** In one short unit, **two or three PCs** each play an identifiable role (actor, rescue target, locus of action). Gold expects **those** slugs—not the whole party. The model often returns **too small** a set (drops a PC who is still grammatically central to that unit).

**Typical signature:** Missing expected hubs on units like `u-L0026-06` while assigning a strict subset (commonly **Caelynn + Ephanna** without **Bonogo**).

**Evidence:** Same cohort summaries as §3 (`evals/sentence_routing_retrieval_falsification/README.md` documents recurring misses on `u-L0026-06`, including dropped **Bonogo** under the strict prompt variant). Failure repeats across runs (not one-off noise).

**Reviewer takeaway:** This failure mode is orthogonal to roster-copy: it needs **role intersection**, not party-wide expansion.

---

## 5. Failure mode C — Listener / reported-speech boundary (PC hub vs abstain)

**Plain description:** Some units are **NPC-led speech or concern** where a PC is conversationally present (“listening locus”) but **not** the retrieval subject of the beat. Gold may say **no PC hub**; the model often **still attaches one or more PC hubs** because a PC is salient in the sentence.

**Anchor row:** `u-L0018-10` (appears repeatedly as the residual failure after other fixes).

**Evidence:**

- `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185646Z.json` — cohort **2/5 PASS**; remaining failures include **false PC attachment** on this row in **3/5** runs (see harness notes in `evals/sentence_routing_retrieval_falsification/README.md` for the same cohort).

**Reviewer takeaway:** This is partly **product intent**: does the GM want “anything Bonogo heard” on Bonogo’s timeline, or only beats where Bonogo is an actor/object/decision locus? Until that intent is pinned, prompt tweaks will thrash.

---

## 6. Failure mode D — Internally contradictory outputs (validator failures)

**Plain description:** Occasionally the model assigns **one or more PC hubs** *and* emits a **non-empty placeholder-style diagnostic label** in the same row. That combination is **disallowed by schema**: if hubs are assigned, the diagnostic label must be empty. These rows fail validation before normal gold checks.

**Typical signature:** Per-run sidecars record validation failures such as **“routing_diagnostic_bucket must be null when assigned_hubs is non-empty.”**

**Evidence:**

- Concrete example is quoted in `evals/sentence_routing_retrieval_falsification/README.md` (multi-PC recall slice: run failed solely because of one contradictory row on unit `u-L0032-09`).
- Abstain-pronoun-context reruns: continuation variant showed this contradiction in **2/5** runs (`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185648Z.json`); strict variant drove this to **0/5** (`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185646Z.json`).

**Reviewer takeaway:** This is a **real confused-routing signal**, distinct from “picked wrong PC.” Cohort JSON still exposes it under the internal counter name `b0_diagnostic_null_when_assigned`—use it as engineering telemetry, not as a label for humans unless you adopt it formally.

**Harness note (2026-04-29):** Two layers apply: **(1) Strict validation** of the model’s wire JSON (what the API/schema allowed). **(2) Grading telemetry** may still run after **coercing** illegal `routing_diagnostic_bucket` values for rows with hubs so `gold_gate_checks_*` and B1/B2 violations are populated. A sidecar can therefore list `**B0: routes JSON invalid: …`** *and* show non-null `**gold_gate_checks_pass/total*`* plus `b1_*` / `b2_*` buckets—check `**wire_strict_parse_ok**` and `**graded_after_wire_coercion**`. Do not read “64/74” as “no schema problem” if `wire_strict_parse_ok` is false.

**Progress update:** The **2026-04-28** full Session 20 sidecar in §2 had clean B0 histogram buckets on the wire. The **2026-04-29** full run still hit **strict** B0 on **two** rows (`event_or_object_placeholder` with non-empty hubs—invalid unless cleared or only `npc_placeholder` under the documented exception). Graded routing misses on that run are predominantly **B1** (9× missing hub) plus **1× B2** over-assigned—the same *shape* of failure as before, with schema noise isolated in the B0 string and audit flags.

---

## 7. Non-failure / telemetry-only: placeholder taxonomy disagreements

**Plain description:** When no hubs are assigned, the model must pick one of several **semantic placeholder categories** (NPC-shaped vs location-shaped vs object/event-shaped vs empty). Gold may disagree with the model on category while **agreeing that no PC hub should attach**.

**Evidence:** Bucket-focused cohorts record soft **diagnostic expectation** pass/fail counts without failing the run gate unless enforcement is turned on—see e.g.  
`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--N3--20260428T164441Z.json`.

**Reviewer takeaway:** Treat these as **labeling hygiene**, not proof that routing-to-hubs is solved or broken—unless you explicitly decide category accuracy is a product requirement.

---

## 8. Cross-cutting lesson from prompt variants (why “one more paragraph” stalled)

**Observation:** A **party-continuation addendum** improved some **party-boundary** and **bucket-sentinel** slices but **did not** clear the **mixed sentinel** scenario at N=5. A **stricter narrow-multi-PC addendum** reduced **whole-roster over-expansion** on some draws but **increased roster-copy misses**—the trade-off is spelled out under “graveyard” / strict-vs-continuation comparison in `evals/sentence_routing_retrieval_falsification/README.md` (2026-04-28 N=5 mixed-sentinel results).

**Reviewer takeaway:** The remaining gap is less “missing explanation text” and more **ambiguous unit taxonomy at authoring time** (what kind of unit is this?) plus **GM retrieval intent** on edge rows like §5.

---

## 9. Suggested review checklist (for you, before more engineering)

For each recurring failing unit ID you care about:

1. **Intent:** Should this beat be retrievable from **each** named PC’s continuity surface, **one** PC’s, or **no** PC’s?
2. **Mechanism:** Is the failure **spread**, **subset**, **listener boundary**, or **schema contradiction** (§§3–6)?
3. **Gold action:** If intent is unclear, adjust gold + `scenario_notes` **before** chasing prompt wins—per `.cursor/rules/gold-realignment-vs-deflation.mdc`.

---

## 10. Next steps

1. **Freeze the comparison frame before optimizing.** For full-scenario progress, compare the current base prompt against the same `scenario_c2_session20_pc.json` gold and report the telemetry listed in §2 (including `**wire_strict_parse_ok`** when present). Avoid using a single `58/74`, `63/74`, or `64/74` headline as the sole decision metric—strict-schema health and graded gate pass rate can diverge after the coercion instrumentation.
2. **Adjudicate the listener-boundary row before prompt work.** `u-L0018-10` is the residual B2 row in the latest full sidecar. Decide whether a PC being the listener / conversational locus should make that unit retrievable from the PC hub. If yes, move the row to `must_route` with a `scenario_notes` rationale. If no, keep gold unchanged and encode the rule explicitly.
3. **Separate roster-copy from same-unit role intersection.** The current prompt variants keep trading one error for another: full-roster expansion helps `u-L0026-03` / `u-L0030-03` shapes but risks over-routing narrower rows like `u-L0026-06`. The next robust lever is likely a structured pre-tag or base-prompt decision split:
  - `roster_copy_candidate`: party/team/group is the joint subject; server expansion via `the_party` is allowed.
  - `same_unit_role_intersection`: only PCs with actor/object/locus roles in this unit should be assigned.
  - `listener_only_or_reported_speech`: do not route to PC unless the adjudication in step 2 says listener continuity counts.
4. **Keep diagnostic contradictions as a permanent counter.** Prefer `**wire_strict_parse_ok: true`** on full-scenario runs; when it is false, treat B0 as **blocking** for “ship confidence” even if graded `gold_gate_checks_*` look improved. Prioritize B1 recall / over-route split and residual B2 rows once the wire is clean or contradictions are rare.
5. **Run the promotion gate only after a targeted change.** For any base-prompt rewrite or structural pre-tag, rerun the bucket sentinel and H1/H2 mixed sentinel at N=5 before expanding to the full scenario. Report pass vector, B1/B2 buckets, diagnostic contradiction count, and cost.
6. **Cost check:** The 2026-04-28 full-scenario run cost **$0.039401**; the 2026-04-29 full run cost **~$0.031**—not a regression vs the older **$0.02794** best-effort baseline, but always cite `**scenario_estimated_cost_usd`** per run when comparing cohorts.

---

## 11. Primary artifact index (for deep dives)


| Topic                                                                        | Example cohort summary                                                                                                                                                                 |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mixed sentinel (roster + multi-PC + abstain rows), continuation variant, N=5 | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185202Z.json`  |
| Mixed sentinel, strict variant, N=5                                          | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185204Z.json` |
| Abstain-pronoun context, continuation, N=5                                   | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185648Z.json`  |
| Abstain-pronoun context, strict, N=5                                         | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185646Z.json` |
| Full Session 20 sidecar (2026-04-28 baseline in §2)                          | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260428T233927847613Z.json`    |
| Full Session 20 sidecar (2026-04-29; coercion grading, strict B0 preserved)  | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-29/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260429T010351303942Z.json`    |
| Historical best full Session 20 sidecar found on disk                        | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-27/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc--FAIL--20260427T015742700112Z.json`    |


Gold scenario definitions live under `evals/sentence_routing_retrieval_falsification/gold/` (filenames match `scenario_id` strings inside the JSON).

Full prose context for each unit lives in corpus recap markdown referenced by scenario JSON (`input.recap_relative_path`); **do not paste player-identifying excerpts into public threads**—review locally.