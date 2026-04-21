# Session recap autonomous timeline pass (Stage 2 v1) — gate status

**Spec:** [EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md](EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md)
**v0 (operator-instructed):** [STATUS-Session-Recap-Timeline-Append-Benchmark.md](STATUS-Session-Recap-Timeline-Append-Benchmark.md)

Update **Last verified** when you re-run the listed commands.

---

## Status: PAUSED (2026-04-21) — pending corpus subject-schema work

This slice is **paused at Iteration 2 (0/3 PASS, both cohorts)** while the parent agent lands the corpus subject-schema convention work (`Docs/CONVENTION-Corpus-Subject-Schemas.md` + PC/Location specializations + read-only lint). Reasoning, captured here so the ledger is honest:

- The Caelynn-timeline calibration review (2026-04-21) surfaced that the *target* surface this slice grades against — `timeline.md` per subject — is itself under-specified across the corpus: no PC convention, no Location convention, `document_class` over-loaded, hub-vs-satellite boundary not codified. Iterating on planner behavior against an under-specified target risks baking the planner to one human's aesthetic instead of the (yet-to-be-written) schema.
- Iteration 2's residual failures (preview-only short-circuit on TP1, latent SKIP-selectivity drift on Dustwalker exposed by Fix 2, zero `hub-proposal:` entries on TP4) are real planner gaps, but the next-iteration design is cleaner once the schema work tells us **what a PC hub IS** (so `subject_class: pc` + `subject_doc_kind: timeline` is a thing the grader can lean on) and **what a missing-NPC-hub proposal SHOULD propose** (so `unsure_queue` `hub-proposal:` entries can carry the right shape). See `Backlog.md` `[READY] Recap-ingest — autonomous timeline-pass slice` for the parent ticket.
- **Restart conditions:** (a) `Docs/CONVENTION-Corpus-Subject-Schemas.md` + PC and Location specializations land; (b) `scripts/lint_corpus_hubs.py` reports current corpus state so we know which hubs are compliant and which are not; (c) any planner-prompt or grader rewrite stays inside this slice (no new perturbation cohorts on the recap-ingest slice during the pause).
- **Current artifacts are preserved:** all per-run sidecars and cohort summaries under `evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/` remain on disk; the EXPERIMENT spec and grader code are untouched.

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
uv run pytest tests/test_timeline_pass_grader.py tests/test_timeline_pass_pre_state.py -q
```

---

## Live cohort log

| Date | Model | N | Pass | Notes / artifacts |
|------|-------|---|------|-------------------|
| 2026-04-21 | gpt-5.4-mini | 3 | 0/3 | **Iteration 1.** Per-gate: TP1 0/3, TP2 3/3, TP3 3/3, TP4 0/3, TP5 3/3. Cost sum $0.0668 (mean $0.0223, max $0.0348). Cohort summary: `evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/timeline_pass_summary--gpt-5.4-mini--N3--20260421T150514Z.{md,json}`. Findings + recommended next actions: [REPORT-Timeline-Pass-Live-2026-04-21.md](REPORT-Timeline-Pass-Live-2026-04-21.md). |
| 2026-04-21 | gpt-5.4-mini | 3 | 0/3 | **Iteration 2 (post Fix 1+2+3).** Per-gate: TP1 0/3, TP2 2/3, TP3 3/3, TP4 0/3, TP5 3/3. Cost sum $0.0601 (mean $0.0200, max $0.0257). Cohort summary: `evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/timeline_pass_summary--gpt-5.4-mini--N3--20260421T154354Z.{md,json}`. Fix 1 (PC writer-allowlist) verified working (PCs/caelynn preview returned `ok=true` in run 1). Fix 2 (commit-checklist) increased commit count from 0→2 in run 2 but the model still drops most commits and now exposes latent SKIP-selectivity drift on Dustwalker. Fix 3 (TP4 prefix) made the gate stricter; this cohort produced zero hub-proposal entries at all. See [REPORT-Timeline-Pass-Live-2026-04-21.md](REPORT-Timeline-Pass-Live-2026-04-21.md) Iteration 2 section. |

---

## Follow-ups

- ~~**PC-timeline writer allowlist**~~ — **resolved (2026-04-21, Iteration 2 Fix 1).** `_TIMELINE_RE` in `src/agent/corpus_writer.py` now matches both `NPCs/<slug>/timeline.md` and `PCs/<slug>/timeline.md`. Verified live on the Caelynn preview in iteration-2 run 1 (`ok=true phase=preview`). New unit tests cover both shapes and explicit denial of look-alike paths in `tests/test_corpus_writer.py`.
- **TP4 hub-proposal prefix contract (Iteration 2 Fix 3).** TP4 now requires the literal `hub-proposal:` prefix (case-insensitive on the token) at the start of each `unsure_queue` entry's `question` field; substring-only mentions of must-flag names no longer count. Soft flags use the same rule. Documented in EXPERIMENT § E.
- **Preview-only short-circuit is still the dominant TP1 failure driver.** Iteration 2 Fix 2 (commit-checklist suffix) helped marginally — commit count went from 0→2 in run 2 — but the model still drops most commits before answering. Next step is likely either (a) splitting the turn (one slug at a time) or (b) a dispatcher-side warning when a preview is followed by a non-`append_timeline_row` tool. See REPORT Iteration 2 § "Recommended next actions".
- **Deterministic discovery tool** — `list_npc_timelines(campaign_hub)`, per Backlog `[READY]` "Engineering principle — prefer deterministic corpus-search tools over LLM discovery". Once landed, switch this slice to option (b) and trim the user message.
