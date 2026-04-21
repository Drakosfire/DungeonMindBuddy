# Session recap autonomous timeline pass (Stage 2 v1) — gate status

**Spec:** [EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md](EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md)
**v0 (operator-instructed):** [STATUS-Session-Recap-Timeline-Append-Benchmark.md](STATUS-Session-Recap-Timeline-Append-Benchmark.md)

Update **Last verified** when you re-run the listed commands.

---

## Status: ACTIVE (2026-04-21, unpaused) — schema preconditions met; Iteration 3 design open

Restart conditions from the pause have all landed. Snapshot of what's now true that wasn't true at the Iteration 2 fail:

- ✅ **Corpus subject-schema convention** (`Docs/CONVENTION-Corpus-Subject-Schemas.md` + PC + Location + NPC) committed (`51b2f67`). The grader and prompt can now lean on `subject_class: {npc,pc,...}` and `subject_doc_kind: {hub_index, timeline, dossier, ...}` as canonical vocabulary instead of free-form strings.
- ✅ **Read-only lint** (`scripts/lint_corpus_hubs.py`) shipped + passes (7/7 unit tests, 56/56 combined). Current state: `20 hubs scanned, 15 OK, 5 with issues` — all 5 remaining are Location top-level / region READMEs, out of scope for this slice.
- ✅ **Cursor layout-conventions rule refreshed** (`2dd2ac1`) so the always-applied prompt context references the new schema.
- ✅ **NPC + PC hub migration** committed (`eea218b`): 12 NPC hub READMEs + Caelynn + Bonogo all carry the canonical frontmatter; Bonogo gained inception satellites (slim dossier + Session-1 timeline seed). Corpus fingerprint advanced `a090a1d9…` → `5cff0388…`; pinned in `evals/lysandra_vertical_slice/gold/step0_environment.json`.
- ✅ **PC writer-allowlist** widened (`d1dad5a`, included in Iteration 2 Fix 1) — `_TIMELINE_RE` admits both `NPCs/<slug>/timeline.md` and `PCs/<slug>/timeline.md`. End-to-end PASS on Caelynn append still pending — the writer accepts the path; the model just hasn't reached commit phase for Caelynn in any iteration-2 run.

**Iteration-2 failure surface (still load-bearing for Iteration 3 design):**

- TP1 0/3 — preview-only short-circuit dominates; Caelynn never reached commit despite Fix 1.
- TP2 2/3 — regressed once Fix 2 enabled commits; Dustwalker (a SKIP target) got committed in run 2.
- TP4 0/3 — model produces no `hub-proposal:` entries even with two worked examples in the suffix.

**Iteration-2 Recommended Next Actions, re-scored under the new schema preconditions:**

| # | Action | Status / change since the recommendation was written |
|---|--------|------------------------------------------------------|
| 1 | Pair commit-checklist with explicit SKIP guard (one sentence in suffix) | Still applicable; schema-agnostic. |
| 2 | Split the turn into one preview→commit per slug (runner loop) | Still applicable; schema-agnostic. Likely the highest single-lever fix for TP1+TP2. |
| 3 | Force non-empty `unsure_queue` when recap names NPCs not in supplied list | **Now sharper:** can require `hub-proposal:` entries to name `subject_class` + `subject_doc_kind` per the schema. Grader can validate the structured proposal. |
| 4 | Promote "preview-only is a failure" lesson into cached planner instructions | Still backlog-only — scope-creep risk per Round-4 warning. Defer. |
| 5 | Cohort diversification (S18/S19, model upgrade) | Still defer until TP1 ≥ 1/3 and TP2 ≥ 3/3 reliably. |

**New post-pause option that didn't exist at Iteration 2 close:**

- **6 — Build `list_npc_hubs(campaign)` / `list_pc_hubs(campaign)` deterministic discovery tools.** The schema lint already discovers hubs by path; promoting that primitive to a planner tool means the model no longer has to discover hubs from prose. This is the `[READY] Engineering principle — prefer deterministic corpus-search tools over LLM discovery` backlog item; the schema work is the precondition that makes those tools well-typed. Plausibly the biggest single unlock for both TP1 and TP4 simultaneously.

**Iteration 3 (2026-04-21) — structural runner + discovery tools landed:**

- **2.5 baseline (single-turn, post-migration):** N=3 `gpt-5.4-mini` — **0/3** overall; TP1 **0/3**, TP2 **3/3**, TP3 **3/3**, TP4 **0/3**, TP5 **3/3**. Same dominant failure mode as Iteration 2 (Lysandra-only commits + wrong “no beat” skips for Sara/Thrin/Caelynn + empty `unsure_queue`). Run 2 additionally failed the Lysandra **beat_regex** hybrid rubric (“Karesmine” typo in the committed beat cell). Cohort cost sum **~$0.046** (lower than Iteration 2 because two runs used heavy cached input).
- **`--per-slug` runner:** `step1_timeline_pass_run.py --per-slug` chains **six** single-subject micro-turns + **one** hub-proposal-only micro-turn (`merge_planning_turn_details_chain`, artifact tag `--7turn--`). First smoke (before per-slug commit-checklist reinforcement) showed Lysandra **preview-only** with “paste token for operator” leakage → per-slug suffix now mirrors the monolithic **commit checklist** (“do not ask human to apply”).
- **`list_npc_hubs` / `list_pc_hubs`:** New read-only planner tools (`src/agent/planner.py`) listing child hub folders under a corpus-relative `…/NPCs` or `…/PCs` root. Both single-turn and per-slug instruction suffixes mention them as optional discovery.

**Still open:** TP1/TP4 live PASS evidence; TP2 SKIP guard when commits become reliable; TP4 model still often claims “no hub proposals needed.”

---

## Legend

Same tokens as v0 / Stage-1 STATUS: **PASS**, **PASS (live)**, **OPEN**, **BLOCKED**.

---

## Automation gates

| Gate | Status | Last verified | How verified |
|------|--------|---------------|--------------|
| TP1 APPEND completeness | FAIL (live) | 2026-04-21 | Iteration 2 cohort N=3 `gpt-5.4-mini`: 0/3 (preview-only short-circuit on most slugs; only Lysandra committed across runs 2 & 3). See [REPORT-Timeline-Pass-Live-2026-04-21.md](REPORT-Timeline-Pass-Live-2026-04-21.md). |
| TP2 SKIP correctness | FAIL (live) | 2026-04-21 | Iteration 2 — 2/3. The commit-checklist fix (Fix 2) finally got the model to commit in run 2, which exposed the latent selectivity drift: it committed a Session-20 row to Dustwalker (a SKIP target) → TP2 fail. Run 1 (zero commits) and run 3 (only Lysandra) still trivially passed TP2. |
| TP3 Tool contract (per-slug two-phase + forbidden tools) | PASS (live) | 2026-04-21 | Iteration 2 — 3/3, no `write_corpus_file` / no recap-assembly tools / preview→commit ordering correct on every commit that landed. |
| TP4 FLAG completeness (`hub-proposal:`-prefixed `unsure_queue` entries) | FAIL (live) | 2026-04-21 | Iteration 2 — 0/3; all three runs returned `unsure_queue: null` or `[]`. The grader is now stricter (Fix 3 requires the literal `hub-proposal:` prefix at the start of each entry's `question`), but the model did not produce *any* hub-proposal entries this cohort. |
| TP5 Hallucination guard (`allowed_npc_slugs`) | PASS (live) | 2026-04-21 | Iteration 2 — 3/3, every `npc_slug` was in `allowed_npc_slugs`. |
| TP6 Pre-state offline | PASS | 2026-04-21 | `tests/test_timeline_pass_pre_state.py` (5 tests) |

**Offline batch:**

```bash
uv run pytest tests/test_timeline_pass_grader.py tests/test_timeline_pass_pre_state.py \
  tests/test_timeline_pass_per_slug_order.py tests/test_planner_hub_list_tools.py -q
```

---

## Live cohort log

| Date | Model | N | Pass | Notes / artifacts |
|------|-------|---|------|-------------------|
| 2026-04-21 | gpt-5.4-mini | 3 | 0/3 | **Iteration 1.** Per-gate: TP1 0/3, TP2 3/3, TP3 3/3, TP4 0/3, TP5 3/3. Cost sum $0.0668 (mean $0.0223, max $0.0348). Cohort summary: `evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/timeline_pass_summary--gpt-5.4-mini--N3--20260421T150514Z.{md,json}`. Findings + recommended next actions: [REPORT-Timeline-Pass-Live-2026-04-21.md](REPORT-Timeline-Pass-Live-2026-04-21.md). |
| 2026-04-21 | gpt-5.4-mini | 3 | 0/3 | **Iteration 2 (post Fix 1+2+3).** Per-gate: TP1 0/3, TP2 2/3, TP3 3/3, TP4 0/3, TP5 3/3. Cost sum $0.0601 (mean $0.0200, max $0.0257). Cohort summary: `evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/timeline_pass_summary--gpt-5.4-mini--N3--20260421T154354Z.{md,json}`. Fix 1 (PC writer-allowlist) verified working (PCs/caelynn preview returned `ok=true` in run 1). Fix 2 (commit-checklist) increased commit count from 0→2 in run 2 but the model still drops most commits and now exposes latent SKIP-selectivity drift on Dustwalker. Fix 3 (TP4 prefix) made the gate stricter; this cohort produced zero hub-proposal entries at all. See [REPORT-Timeline-Pass-Live-2026-04-21.md](REPORT-Timeline-Pass-Live-2026-04-21.md) Iteration 2 section. |
| 2026-04-21 | gpt-5.4-mini | 3 | 0/3 | **Iteration 2.5 (single-turn baseline, post hub-schema migration).** Per-gate: TP1 0/3, TP2 3/3, TP3 3/3, TP4 0/3, TP5 3/3. Confirms Iteration-2 failure shape still holds after corpus README migrations; run 2 added a Lysandra hybrid-rubric FAIL (“Karesmine” typo vs regex anchor). |
| 2026-04-21 | gpt-5.4-mini | 1 | 0/1 | **Iteration 3 smoke — `--per-slug` (7 chained turns), pre per-slug commit-checklist reinforcement.** Lysandra micro-turn stopped at preview-only (instructed operator to apply token); Sara/Thrin/Caelynn rationalized skipping appends; hub micro-turn returned empty `unsure_queue` → TP1/TP4 FAIL. Per-slug suffix was tightened immediately after this run. |

---

## Follow-ups

- ~~**PC-timeline writer allowlist**~~ — **resolved (2026-04-21, Iteration 2 Fix 1).** `_TIMELINE_RE` in `src/agent/corpus_writer.py` now matches both `NPCs/<slug>/timeline.md` and `PCs/<slug>/timeline.md`. Verified live on the Caelynn preview in iteration-2 run 1 (`ok=true phase=preview`). New unit tests cover both shapes and explicit denial of look-alike paths in `tests/test_corpus_writer.py`.
- **TP4 hub-proposal prefix contract (Iteration 2 Fix 3).** TP4 now requires the literal `hub-proposal:` prefix (case-insensitive on the token) at the start of each `unsure_queue` entry's `question` field; substring-only mentions of must-flag names no longer count. Soft flags use the same rule. Documented in EXPERIMENT § E.
- **Preview-only short-circuit is still the dominant TP1 failure driver.** Iteration 2 Fix 2 (commit-checklist suffix) helped marginally — commit count went from 0→2 in run 2 — but the model still drops most commits before answering. Next step is likely either (a) splitting the turn (one slug at a time) or (b) a dispatcher-side warning when a preview is followed by a non-`append_timeline_row` tool. See REPORT Iteration 2 § "Recommended next actions".
- ~~**Deterministic discovery tools**~~ — **`list_npc_hubs` / `list_pc_hubs` landed (2026-04-21, Iteration 3).** Corpus-relative `…/NPCs` and `…/PCs` inventory (slug + `timeline.md` / `README.md` presence). Optional in timeline-pass suffixes; broader planner adoption (cached instructions / recap-ingest) remains backlog.
