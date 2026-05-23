# CHECKLIST — C1S4 preplanning vertical slice

- [x] Canonical super-plan: `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` v33, especially `pilot_memory_ingest` and `synthetic_session4_prep_benchmark`.
- [x] Planning rationale: `Docs/Plans/RATIONALE-c1s4-preplanning-vertical-slice.md`.
- [x] Implementation handoff: superseded — see `Docs/Plans/archive/2026-05-22/handoffs/HANDOFF-next-c1s4-preplanning-vertical-slice-scaffold.md`.

## Reanchor block (fill first each session)

- [x] **Active slice:** C1S4 preplanning vertical slice — Step 2C expected-context benchmark lane through PR #67 admission diagnostics; Steps 3–5 stub/synthetic prep complete; Step 6 oracle scaffold exists.
- [x] **Last green artifact (path):** PR #67 merge **`8978e92`** (2026-05-22T22:04:29Z) — `evals/c1s4_preplanning_vertical_slice/artifacts/pr67/pr67_required_group_admission_diagnostics.json`; Step 2C multimode report + canvas payload on **`main`** @ **`f4f25f7`** (`chore(c1s4): refresh benchmark artifacts and PR67 canvas diagnostics`). Tier-A strict misses: Q3 distance only (`strict_gold_lane_mismatch` ×3); Q3 route gap passes via source-derived gap; Q5 strict passes via gold realignment (PR66 visibility). **Cost:** $0 (deterministic harness).
- [x] **Open evidence gap:** Q3 distance (`mirathorn_distance_estimate_from_play`) — `failure_stage=no_session_evidence`; needs corpus session-memory evidence for “mirathorn + week” or explicit gold-contract decision (not admission budget tuning).
- [x] **Next command to run:** `uv run pytest tests/test_c1s4_*.py -q`; `bash scripts/c1s4_update_expected_context_canvas.sh` (optional live canvas refresh).

---

## Deterministic scaffold completion

- [x] C1S1–C1S3 are the only planner-visible KB inputs.
- [x] C1S4 is held out as oracle-only.
- [x] All C1S4 source/derivative surfaces are excluded from planner-visible context.
- [x] Preferred oracle source is normalized C1S4 recap when present.
- [x] Original C1S4 recap remains fallback oracle source and forbidden planner-visible source.
- [x] Canonical session-memory ingestion location is `src/session_memory/`.

## Out-of-scope guardrails (scaffold PR only)

Scaffold-era guardrails; post-scaffold PR #58–#67 intentionally extended retrieval, gold, and canvas surfaces.

- [x] No retrieval tuning introduced in the scaffold PR.
- [x] No corpus mutation.
- [x] No baseline regeneration.
- [x] No live planner/oracle grading in scaffold PR.

## PR milestones — Step 2C retrieval lane (PR #58–#67)

- [x] PR #58 — campaign corpus record materialization.
- [x] PR #59 — Step 2C query alias expansion.
- [x] PR #60 — admission preservation infrastructure.
- [x] PR #61 — candidate merge allocation repair.
- [x] PR #62 — renderer provenance / section repair.
- [x] PR #63 — source-derived context gaps; gold known-gaps removed from planner packets.
- [x] PR #64 — planner prompt / evaluator control split.
- [x] PR #65 — planner-surface coverage to full benchmark (merge **`777a8bc`**, 2026-05-22).
- [x] PR #66 — provenance-safe planner affordance retrieval (merge **`66972d2`**, 2026-05-22).
- [x] PR #67 — budgeted admission diagnostics + prior route-event preservation (merge **`8978e92`**, 2026-05-22).

## Beat/question target artifact

- [x] `gold/c1s4_beat_question_targets.json` exists.
- [x] Q1–Q38 are represented.
- [x] Questions are labeled with authority labels.
- [x] Questions are labeled with oracle-risk labels.
- [x] Oracle-sensitive C1S4 terms are forbidden unless sourced.
- [x] Worldbuilding/ecology gaps are explicitly marked.
- [x] Support-knowledge dependency is explicitly marked for Hempholm questions.
- [x] Target artifact is marked planner-visible: forbidden.
- [x] Validator and tests pass.

## Step 3 — Stub answer packets

- [x] `answer_packet_harness.py` exists.
- [x] `step3_build_stub_answer_packets.py` exists.
- [x] Answer packet schema is `dmb_c1s4_answer_packet_v1`.
- [x] `answer_generation_status` is `stubbed_not_generated`.
- [x] `answer_text` remains null.
- [x] `structured_answer` remains null.
- [x] Q35 remains skipped.
- [x] Eval-only fields are rejected.
- [x] Oracle leakage checks are preserved.
- [x] Tests pass.

- [x] PR #35: Add Step 4 generated answer packet harness (`template_stub`) with Q35 skip preservation, guardrail retention, unsupported forbidden-term checks, and no oracle grading.

## Step 5 — Synthetic prep packet

- [x] `synthetic_prep_packet_harness.py` exists.
- [x] `step5_build_synthetic_prep_packet.py` exists.
- [x] Prep packet schema is `dmb_c1s4_synthetic_prep_packet_v1`.
- [x] Required sections exist.
- [x] Q35 remains skipped.
- [x] Known gaps are preserved.
- [x] Must-not-include guardrails are preserved.
- [x] Retrieval mode is preserved.
- [x] Packet does not claim observed C1S4 match.
- [x] Oracle leakage causes validation failure.
- [x] Unsupported forbidden terms cause validation failure.
- [x] Tests pass.

## Step 6 — Oracle comparison scaffold

**Status:** harness exists; unit tests green (`tests/test_c1s4_oracle_comparison_harness.py`); full end-to-end live prep→oracle grading cohort not yet exercised.

- [x] `oracle_comparison_harness.py` exists.
- [x] `step6_compare_synthetic_prep_to_oracle.py` exists.
- [x] Oracle policy is explicit.
- [x] Oracle visibility is `step6_only`.
- [x] Planner visibility is `forbidden`.
- [x] Step 6 loads oracle material only inside comparison.
- [x] Synthetic prep packet is not mutated with oracle text.
- [x] Section comparisons are produced.
- [x] No final score is emitted.
- [x] Tests pass.

## Step 2C — Expected context benchmark

- [x] `gold/c1s4_expected_context_gold.json` exists.
- [x] `expected_context_benchmark.py` exists.
- [x] `step2c_expected_context_benchmark.py` exists.
- [x] Gold schema is `dmb_c1s4_expected_context_gold_v1`.
- [x] Report schema is `dmb_c1s4_expected_context_benchmark_report_v1`.
- [x] Gold is planner-forbidden/eval-only.
- [x] Benchmark runs `prior_only`.
- [x] Benchmark runs `prior_plus_support_content_only`.
- [x] Benchmark runs `prior_plus_support_content_plus_lexical_hints`.
- [x] Required context groups are graded.
- [x] Forbidden context groups are graded.
- [x] Known-gap expectations are graded.
- [x] Mode deltas are reported.
- [x] Tests prove gold does not leak into Step 2 retrieval/context packets.

## Step 2D — Expected-context canvas projection

- [x] `expected_context_canvas_payload.py` exists.
- [x] `step2d_expected_context_canvas_emit.py` exists.
- [x] Payload schema is `dmb_c1s4_expected_context_canvas_payload_v1`.
- [x] Payload consumes Step 2C report JSON.
- [x] Payload shows mode summaries.
- [x] Payload shows per-question pass/fail rows.
- [x] Payload shows missing required context groups.
- [x] Payload shows forbidden context hits.
- [x] Payload shows known-gap checks.
- [x] Payload shows mode deltas.
- [x] Failing cards open by default.
- [x] Canvas emitter patches generated block markers.
- [x] Canvas is documented as projection, not canonical state.
- [x] Tests pass.

---

## Session log

### 2026-05-22 (UTC) — atomic doc-sync after PR #65–#67 + artifact landing prep

- What turned green: [PR #65](https://github.com/Drakosfire/DungeonMindBuddy/pull/65) merge **`777a8bc`**; [PR #66](https://github.com/Drakosfire/DungeonMindBuddy/pull/66) merge **`66972d2`**; [PR #67](https://github.com/Drakosfire/DungeonMindBuddy/pull/67) merge **`8978e92`**. Step 2C/2D checklist rows closed; PR #58–#67 milestone block added. Scaffold handoff archived under `Docs/Plans/archive/2026-05-22/handoffs/`.
- Artifact commit **`f4f25f7`** (cherry-pick of **`e4a2495`**): PR67 admission diagnostics on expected-context canvas + refreshed `last_c1s4_step2c_multimode_report.json` / `last_c1s4_expected_context_canvas_payload.json` — on `main`.
- Step 6: harness + tests exist; marked complete at scaffold level; end-to-end oracle cohort still open.
- Dominant open gap: Q3 distance `no_session_evidence` (gold/data contract, not admission budget).
- **Cost:** $0.
