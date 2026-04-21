# REPORT — Stage-2 v1 (autonomous timeline pass) live cohort, 2026-04-21

**Slice:** `evals/session_recap_timeline_pass_vertical_slice/`
**Spec:** [EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md](EXPERIMENT-Session-Recap-Timeline-Pass-Benchmark.md)
**Ledger:** [STATUS-Session-Recap-Timeline-Pass-Benchmark.md](STATUS-Session-Recap-Timeline-Pass-Benchmark.md)
**Parent v0 (operator-instructed):** [REPORT in STATUS-Session-Recap-Timeline-Append-Benchmark.md](STATUS-Session-Recap-Timeline-Append-Benchmark.md)

---

## Protocol

```bash
uv run pytest tests/test_timeline_pass_grader.py tests/test_timeline_pass_pre_state.py -q
# 33 passed in 0.14s

uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run --print-root
# pre-state spot-check assertions: recap pinned + 4 APPEND rows absent + 2 SKIP files byte-equal to HEAD

DUNGEONMIND_PLANNER_ALLOW_WRITES=1 PLANNER_REVIEW_MODE=summary \
  uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run \
  --n 3 --model gpt-5.4-mini
```

Cohort summary artifact:
`evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/timeline_pass_summary--gpt-5.4-mini--N3--20260421T150514Z.{md,json}`

---

## Cost

- **Cohort sum:** **$0.0668** (mean $0.0223, max $0.0348). Well under the slice cost cap ($1.50 early-stop floor / $3.00 hard cap).
- **Per-run:** $0.0348, $0.0126, $0.0194. Within envelope; cheaper than v0's last cohort ($0.04–0.06/run on ingest+timeline) because the model never reached commit on most appends and three-quarters of the second turn is cached input.
- **Cost-as-signal flag:** **none**. Cohort cost is much lower than would be expected for a 4-commit success path; this is a *behavioral* signal that the model is short-circuiting, not a runtime regression.

## Results table

| Run | Pass? | Cost ($) | TP1 | TP2 | TP3 | TP4 | TP5 | Tool-trace shape |
|----:|:------|---------:|:---:|:---:|:---:|:---:|:---:|:-----------------|
| 1   | FAIL  | 0.0348   | FAIL | PASS | PASS | FAIL | PASS | 7 reads → 5 previews → assistant message (zero commits) |
| 2   | FAIL  | 0.0126   | FAIL | PASS | PASS | FAIL | PASS | 7 reads → 6 previews → assistant message (zero commits) |
| 3   | FAIL  | 0.0194   | FAIL | PASS | PASS | FAIL | PASS | 7 reads → 1 preview → 1 commit (Lysandra only) → 1 preview (caelynn refused) → assistant message |

**Per-gate counts:** TP1 0/3 · TP2 3/3 · TP3 3/3 · TP4 0/3 · TP5 3/3.

Run-1 had the only `marla` substring hit in `unsure_queue`; runs 2–3 produced empty / off-target queues. Karsemine, Ephanna, Stafl never surfaced. Soft flags: `stuart`/`stacey` only present in run 1.

---

## Observed planner behavior

1. **Preview-only short-circuit (TP1 root cause).** Despite the user message + the runner's eval-only instruction suffix both saying *"stopping at preview is a failure; commit in the same turn"*, the model **stopped at preview** for every NPC append in runs 1 and 2, and only committed Lysandra in run 3. v0's STATUS doc warned about exactly this pattern in the operator-instructed slice ("first N=3 stopped at preview-only"); the autonomous variant inherits the same fragility and is **more** sensitive to it because the contract requires four commits in one turn instead of one.
2. **PC-allowlist hard refusal on Caelynn (every run).** As predicted in the EXPERIMENT "Known design caveats" section, the writer refused the Caelynn append with `"append mode is not allowed for this path (allowed: **/NPCs/<slug>/timeline.md, ...)"`. The model handled this gracefully — it surfaced the failure in its final `message` and (in run 2) proposed a hub-style workaround in `unsure_queue`. **TP1 will not pass for Caelynn until `_TIMELINE_RE` (or a sibling regex) admits `PCs/<slug>/timeline.md`.**
3. **Selectivity drift (TP2 still passes only because TP1 fails).** Runs 1–2 *previewed* timeline appends for **all five** NPC paths including Dustwalker and Torbin Jove — the model did not respect the SKIP cue from the recap. Because previews don't mutate the file, the SKIP gate (TP2) trivially passes today. If the model were to graduate to per-slug commits, TP2 would start failing on Dustwalker/Torbin Jove unless the SKIP cue is taught more forcefully.
4. **TP4 hub-proposal flagging is severely under-spec'd in practice.** Only `marla` was named once across the cohort. The model evidently treats the `unsure_queue` as "things I cannot do" (run 2's only entry was "the PC-path append failed") rather than "prominent NPCs without hubs". Either the substring matcher needs to be tightened (require the literal `hub-proposal:` prefix to count) **or** the prompt needs a more concrete worked example for Karsemine/Ephanna/Stafl. Recommend the latter.

## Per-gate verdict

- **TP1 APPEND completeness — FAIL (0/3).** Root cause: preview-only short-circuit (cf. §1) + PC-allowlist refusal on Caelynn (cf. §2). Even if the model committed all four NPC slugs, TP1 would still fail on Caelynn until the writer allowlist is widened.
- **TP2 SKIP correctness — PASS (3/3), with caveat.** Trivially satisfied because no commits landed on Dustwalker/Torbin Jove. Re-evaluate once TP1 graduates: runs 1–2 *previewed* appends for the SKIP targets, indicating the model would commit them if it stopped short-circuiting.
- **TP3 Tool contract — PASS (3/3).** No `write_corpus_file`, no `assemble_recap_draft`/`build_recap_write_payload`/`get_recap_context`. Per-slug ordering is currently moot (no commits except Lysandra in run 3, where preview→commit ordering was correct).
- **TP4 FLAG completeness — FAIL (0/3).** Only `marla` matched once. `karsemine`, `ephanna`, `stafl` never surfaced.
- **TP5 Hallucination guard — PASS (3/3).** Every `append_timeline_row` call's `npc_slug` was in `allowed_npc_slugs`.

## Surprises / divergences from the gold-first plan

- **PC-allowlist blocker is structural, not a model issue.** Gold says "expect 4 appends including Caelynn"; the writer regex literally cannot accept that path. This is an **architectural follow-up** the parent should sequence before the next live cohort.
- **Preview-only short-circuit is the single largest gate-failure driver.** The instruction suffix that worked for v0 (single NPC, single commit) is not strong enough for this slice (four commits across NPC reads). Suspect the model treats "preview" as a natural "review-and-await" beat when the action surface is wide; needs reinforcement and possibly a structured commit-checklist in the suffix.
- **`unsure_queue` substring matching is too lenient *and* too strict.** Lenient because it would count any `marla` mention (e.g. "Marla in S20 swarm fight" inside a non-hub-proposal item); strict because the model didn't name the prominent NPCs at all in 2/3 runs.

---

## Recommended next actions for the parent (max 5)

1. **[Highest leverage]** File a `[READY]` to widen the writer allowlist so PC timelines are appendable: extend `_TIMELINE_RE` (or add `_PC_TIMELINE_RE`) in `src/agent/corpus_writer.py` to admit `(?:^|/)PCs/[^/]+/timeline\.md$` for `append` mode. Add a `tests/test_corpus_writer.py` case. Re-run this cohort afterwards.
2. **[High leverage]** Strengthen the preview-only short-circuit guard. Options: (a) add a single literal sentence to `_TIMELINE_PASS_INSTRUCTION_SUFFIX` such as *"After every preview, you must immediately re-call `append_timeline_row` with `dry_run=false` and the preview's `confirm_token` before responding."*; (b) add a dispatcher-side warning when a preview is followed by a non-`append_timeline_row` tool. Try (a) first since it's scoped to this slice.
3. **[Medium leverage]** Tighten TP4 substring matching: require the literal `hub-proposal:` prefix in `question` for the must-flag hit to count, and add 1–2 worked examples (Karsemine, Ephanna) inside the runner instruction suffix so the model has a template.
4. **[Medium leverage]** Promote the v0 STATUS doc's "preview-only is a failure" lesson into the cached planner instructions (`corpus_session_planner.py`) — but **scope-guard** that change carefully because v0's STATUS already warned about Round-4-style scope creep regressions when shared prompts are edited. Probably best as a `[READY]` for the parent to triage rather than acting on it from this slice.
5. **[Defer until 1+2 land]** Diversify the cohort to a second session (e.g. S18 or S19) and possibly model upgrade (`gpt-5.4` rather than `mini`). Do not run this until TP1 is at least 1/3 with the current architecture, otherwise the cost-vs-signal trade is poor.

---

## Iteration 2 — 2026-04-21

### Fixes landed

**Fix 1 — Writer allowlist now admits PC timelines.** `_TIMELINE_RE` in `src/agent/corpus_writer.py` was widened from `(?:^|/)NPCs/[^/]+/timeline\.md$` to `(?:^|/)(?:NPCs|PCs)/[^/]+/timeline\.md$`. Scope is strictly `append_timeline_row` — no other allowlist branch touched. The append-mode rejection message also now lists the PC shape. Unit coverage added in `tests/test_corpus_writer.py` (parametrized accepted/rejected cases plus a path-traversal regression).

**Fix 2 — Commit-checklist suffix.** Added a literal commit-checklist paragraph to `_TIMELINE_PASS_INSTRUCTION_SUFFIX` in `evals/session_recap_timeline_pass_vertical_slice/step1_timeline_pass_run.py` ("After every preview that returns `ok=true phase=preview`, you MUST immediately re-call `append_timeline_row` …"). Also seeded two literal worked `hub-proposal:` examples (Karsemine, Ephanna) into the existing hub-proposal paragraph; deliberately did not seed Stafl/Marla so those still need to surface from model judgment.

**Fix 3 — TP4 prefix contract.** `violations_flag_completeness` and `soft_flag_telemetry` in `evals/session_recap_timeline_pass_vertical_slice/grader.py` now require the literal `hub-proposal:` prefix at the start of each `unsure_queue` entry's `question` field (case-insensitive on the token, mandatory colon, leading whitespace tolerated). The must-flag slug/surface name must appear within that same qualifying entry's flattened text. Scenario JSON shape unchanged. Test coverage added in `tests/test_timeline_pass_grader.py` (positive prefix, negative bare-mention, case+whitespace tolerance, qualifying-entry locality, soft-flag prefix parity).

### Cohort

```bash
DUNGEONMIND_PLANNER_ALLOW_WRITES=1 PLANNER_REVIEW_MODE=summary \
  uv run python -m evals.session_recap_timeline_pass_vertical_slice.step1_timeline_pass_run \
  --n 3 --model gpt-5.4-mini
```

Cohort summary artifact:
`evals/session_recap_timeline_pass_vertical_slice/artifacts/runs/2026-04-21/timeline_pass_summary--gpt-5.4-mini--N3--20260421T154354Z.{md,json}`

| Run | Pass? | Cost ($) | TP1 | TP2 | TP3 | TP4 | TP5 | Tool-trace shape |
|----:|:------|---------:|:---:|:---:|:---:|:---:|:---:|:-----------------|
| 1   | FAIL  | 0.0257   | FAIL | PASS | PASS | FAIL | PASS | 7 reads → 6 previews (incl. PCs/caelynn ok=preview) → assistant message (zero commits) |
| 2   | FAIL  | 0.0238   | FAIL | FAIL | PASS | FAIL | PASS | 7 reads → 1 preview (lysandra) → 1 commit → 2 reads → 1 preview (lysandra repeat) → 1 commit → 1 preview (dustwalker) → 1 commit (SKIP violation) → assistant message |
| 3   | FAIL  | 0.0107   | FAIL | PASS | PASS | FAIL | PASS | 7 reads → 1 preview → 1 commit (lysandra only; beat regex did not match) → assistant message |

**Per-gate counts:** TP1 0/3 · TP2 2/3 · TP3 3/3 · TP4 0/3 · TP5 3/3.

**Cost sum:** $0.0601 (mean $0.0200, max $0.0257). Slightly cheaper than iteration 1, still well under the $1.50 / $3.00 budget guards. Cost-as-signal flag: **none** structurally — the model is still short-circuiting after fewer commits than expected, which manifests as low cost rather than runaway loops.

### Per-gate verdict (vs. iteration 1)

- **TP1 APPEND completeness — FAIL (0/3), unchanged.** Fix 1 verifiably removed the Caelynn allowlist blocker (run 1 produced an `ok=true phase=preview` for `PCs/caelynn/timeline.md`), but Fix 2 only marginally moved the model on commit-completion: run 1 reverted to the iteration-1 short-circuit shape (zero commits across six previews); runs 2–3 committed only Lysandra (with run 2 also committing Dustwalker — see TP2 note). Caelynn was never *committed* in any iteration-2 run, so we have no live PASS evidence of the writer accepting a Caelynn append, only that the preview phase succeeds.
- **TP2 SKIP correctness — FAIL (2/3), regressed from PASS.** This is the predicted outcome of partial TP1 progress: run 2 finally committed something beyond Lysandra, and that something was Dustwalker, a SKIP target. The selectivity drift the iteration-1 report flagged ("runs 1–2 *previewed* SKIP-target appends") materialized as soon as the model graduated to commits. Suspect the planner is treating "I previewed a SKIP target" as license to commit it once it gets warmer on the commit-checklist.
- **TP3 Tool contract — PASS (3/3), unchanged.** No `write_corpus_file`, no recap-assembly tools. Per-slug preview→commit ordering correct on every commit landed.
- **TP4 FLAG completeness — FAIL (0/3), unchanged.** Cleaner failure: every iteration-2 run returned `unsure_queue: null` or `[]`. The two literal `hub-proposal:` worked examples in the suffix did not coax the model into producing any hub-proposal entries; combined with Fix 3 (stricter prefix), the gate is now an honest failure rather than the over-permissive substring match that incidentally passed `marla` in iteration 1.
- **TP5 Hallucination guard — PASS (3/3), unchanged.** Every commit's `npc_slug` was in `allowed_npc_slugs`.

### Surprises / divergences

- **Fix 1 was structurally necessary but is not yet sufficient evidence-wise.** We removed the Caelynn allowlist blocker and the writer accepts PC timelines (verified in run 1 preview output and via 4 new `tests/test_corpus_writer.py` cases), but the model never reached the commit phase for Caelynn, so we have no end-to-end PASS for that target.
- **Fix 2 partially worked — and exposed Iteration 1's selectivity caveat.** Going from 0 commits (iter-1 runs 1–2) to 2 commits (iter-2 run 2) is forward motion. But with the model committing more freely, the previously-trivial TP2 PASS broke immediately on Dustwalker. Suggests Fix 2 needs to be paired with a SKIP reinforcement clause ("a preview is not permission to commit if the recap doesn't actually describe a Session-N beat for that NPC").
- **Fix 3 made TP4 honest.** Iteration 1's `marla` substring hit in run 1 was incidental; iteration 2 shows the real picture — the model produces no hub-proposal entries at all. The next intervention for TP4 is probably structural (e.g. *require* an `unsure_queue` of at least N items if certain prominent NPCs are mentioned in the recap but not in the supplied list) or example-richness in the suffix.
- **Run-trace divergence between runs.** The model's behavior differs widely (6 previews / 0 commits, vs. 2 commits, vs. 1 commit) on a near-identical prompt; this is consistent with iteration 1's observation that the action surface (4 commits in one turn) is at the edge of what the small model handles reliably without per-slug structural guidance.

### Recommended next actions for the parent (max 5)

1. **[Highest leverage]** Pair the commit-checklist with an explicit SKIP guard. Add a sentence to the suffix like *"A preview is not permission to commit. Do not commit a Session-N row to a timeline whose NPC has no meaningful beat in the recap; for those, record the skip in your final `message` and move on."* This addresses the new TP2 regression without weakening the commit-checklist.
2. **[High leverage]** Try splitting the turn into one preview→commit pair per slug instead of all six at once. The cohort traces show the model handles a single slug correctly (Lysandra committed in 2/3 runs) but loses track when juggling six. This is a runner-level change (loop the planner per slug) rather than a prompt change, but it tests the hypothesis cleanly.
3. **[Medium leverage]** Force a non-empty `unsure_queue` whenever the recap names NPCs not present in the supplied timeline list. Today the model returns `null`/`[]` and TP4 fails silently. A minimal nudge in the user message ("if the recap names NPCs not in the list, you MUST surface at least one `hub-proposal:` entry") would test whether the model is choosing to skip vs. forgetting the convention.
4. **[Medium leverage]** Promote the v0 STATUS doc's "preview-only is a failure" lesson plus the new "preview is not permission to commit" SKIP guard into the cached planner instructions (`corpus_session_planner.py`) — but **scope-guard** carefully per the iteration-1 report's Round-4 warning. Probably best as a `[READY]` for the parent rather than acting from this slice.
5. **[Defer]** Cohort diversification (S18/S19, model upgrade to non-mini). Do not run until TP1 ≥ 1/3 and TP2 ≥ 3/3 reliably with the current architecture; otherwise cost-vs-signal trade is poor.
