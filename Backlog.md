# DungeonMindBuddy — Backlog

Project-specific learnings, ideas, and follow-ups for the DungeonMindBuddy repo and the Eldyrwild corpus it serves. Cross-project / AI-tooling items live in `~/.cursor/learnings/Backlog.md` instead.

**Format:** see `~/.cursor/skills/capture-learning/SKILL.md`.
**Status legend:** `IDEA` → `READY` → `DOING`. Terminal states (`DONE` / `DROPPED`) are archived to `Backlog-DONE.md` to keep this file focused on what's still worth doing.

Sort newest → oldest within each status; promote with `/promote`; archive with `/done` or `/drop`.

**Grounding alignment pass (2026-04-20):** The `[READY]` entries titled `(grounding P1)` … `(grounding P6)` immediately below are intentionally ordered **P1 (highest) → P6** as one stack; the rest of `[READY]` follows the usual newest-first convention.

---

## [READY] Recap-write perturbation suite — stress Scope-B before Session 21 ingest (grounding P1) — captured 2026-04-20

**Context:** **Grounding cleanup stack position P1 (2026-04-20).** Session 20 recap ingest is currently 5/5 PASS on Scope-B and the post-fix verification on 2026-04-20 was a clean PASS in one shot. But the system has only been exercised on the **happy path** (well-formed prep doc, present recent recap, valid paths). Before pushing forward with Session 21 ingestion (or any new session), we want confidence the dispatch guards + grader actually catch adversarial inputs — not just that they don't trigger on clean ones.
**Insight:** A passing happy-path benchmark proves the system *can* succeed; a passing perturbation suite proves the system *fails safely* when the inputs are wrong. Our recent grader fix (soft vs hard distinction for guard-caught reads, Round 5+6 of the 2026-04-20 sweep) was specifically motivated by a bug where guard-caught events were double-penalized. We have no evidence yet that the grader correctly catches the *opposite* failure mode: a chaos input the guard misses entirely or the model fails to recover from.
**Action:** Author 4–6 perturbation scenarios in `evals/session_recap_ingest_vertical_slice/scope_b_scenarios/`: (a) prep doc with a malformed frontmatter block, (b) `recent_recaps` empty (fresh campaign), (c) `_ingest_staging/` path containing junk to test the guard fires + model recovers, (d) prep doc that contradicts itself across paragraphs (test dedup grader), (e) `target_session` already exists in corpus (test write_corpus_file create-mode rejection), (f) a path traversal attempt in a tool-call argument. For each: define expected `gates_passed`, expected hard violations, expected soft observations. Run cohort N=3 and confirm grader output matches the expected shape. **No model retraining; this is pure contract verification.**
**Surfaces when:** Before any new-session ingest; planning Session 21 work; touching `scope_b_grader.py` or `planner_skill_dispatch_guards.py`; designing a "chaos" benchmark category.
**Refs:** `evals/session_recap_ingest_vertical_slice/scope_b_grader.py`, `src/agent/planner_skill_dispatch_guards.py`, `Docs/Plans/SCOPE-B-GOLD-Session-20-Ingest.md`, `Backlog-DONE.md` `[DONE] Session recap Scope-B — staging-path read allowlist false-positives` for the grader contract.

## [READY] Session recap ingest slice — wire B7 unsure_queue grader into runner pass/fail (grounding P3) — captured 2026-04-20

**Context:** The slice includes grader code for B7 (`unsure_queue`), but STATUS reports it is not wired into the Step-1 runner exit status — scenarios that only need unsure-queue hygiene cannot graduate PARTIAL → PASS on that contract alone.
**Action:** Wire `step3_unsure_queue_grading.py` (or equivalent) into the main runner pass/fail with explicit expected shape in Scope-B scenarios; update STATUS "what each gate means" + last verified row. Prefer one PR with the step2 stub/README cleanup so onboarding docs stay consistent.
**Refs:** `evals/session_recap_ingest_vertical_slice/step3_unsure_queue_grading.py`, `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md`, recap-ingest Step 1 runner entrypoint.

## [READY] Docs — STATUS-style ledger for Pipeline A (CLI ingest / FactStore / mirathorn) (grounding P4) — captured 2026-04-20

**Context:** Pipeline B (session recap ingest) has `STATUS-Session-Recap-Ingest-Benchmark.md`; Pipeline A (CLI ingest, mirathorn vertical slice) lacks a single "what each gate means + last verified" ledger comparable to that doc. **Folded (option A, 2026-04-20):** the former standalone "apply-wait vs benchmark `commit_required`" doc gap is not its own ticket — readers confuse recap-write **SKILL** (wait for GM `apply` after preview) with Scope-B gold (`commit_required: true` forces preview→commit in one turn for grading). Both are intentional; Pipeline B's STATUS should name that asymmetry in a short paragraph when this work runs.
**Action:** Author or extend a plan doc mirroring the recap STATUS structure for CLI ingest: gates, runner commands, known caveats, freshness block. **Same doc pass:** add that apply-wait vs `commit_required` paragraph to `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md` (e.g. under Scope-B intro) so Pipeline A and B ledgers stay coherent.
**Refs:** `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md`, `.cursor/skills/recap-write/SKILL.md`, `evals/mirathorn_vertical_slice/`, `src/cli.py` ingest path, `Docs/Plans/EXPERIMENT-Session-Recap-Ingest-Benchmark.md` as structural template only.

## [READY] Session recap ingest benchmark — C4–C7: ship gates or formally close in STATUS (grounding P5) — captured 2026-04-20

**Context:** STATUS lists C4–C7 as OPEN/PARTIAL (read-allowlist surfacing, fingerprint parity, tmpdir diff, etc.). They risk permanent limbo between "promised benchmark work" and "actually covered elsewhere."
**Action:** For each item: implement and wire into the runner, **or** mark DEFERRED/CLOSED with one-line rationale (e.g. "covered by unit tests + dispatch guard; not Scope-B surface") so the ledger is honest.
**Refs:** `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md`, `Docs/Plans/BACKLOG-session-recap-benchmarking.md`, `evals/session_recap_ingest_vertical_slice/scope_b_grader.py`.

## [READY] Grounding pass P6 — execute existing hygiene READY after P1–P5 (OpenAI key loader + recap step2/B7 README) — captured 2026-04-20

**Context:** Lowest urgency in the same grounding stack; avoids duplicating the long-form bodies already in this file.
**Action:** After P1–P5 are done or parked, pick up the later READY entries titled `OpenAI client — collapse three _load_api_key copies…` and `Recap-ingest — step2_grade_against_gold.py…` — ideally coordinated with **grounding P3** if one pass touches runner + README + STATUS.
**Surfaces when:** After recap-doc/gate alignment; any OpenAI client refactor.
**Refs:** Search this file for those titles; `evals/session_recap_ingest_vertical_slice/step2_grade_against_gold.py`.

## [INVESTIGATED] Recap-write — model leaves judgment fields empty under happy path despite SKILL guidance — captured 2026-04-21

**Context:** Live Scope-B cohort N=3 on Session 20 (post B7/B9 wiring + post SKILL §6.5 addition guiding `unsure_queue` and `notes_for_gm` population) returned 0/3 PASS. The model emits `unsure_queue: null`, `notes_for_gm: ""` (or a single generic prep-doc sentence), AND `npc_audit.*` and `plot_artifacts` 0/0/0 across all 6 failing runs (zero attempts). The mechanical fields (`recap_preview`, `duplicate_paragraphs`, `prep_pointer_proposal`) are populated correctly.
**Insight (2026-04-21 investigation):** Four questions answered:

- **SKILL §6.5 does NOT reach the planner LLM.** `build_corpus_session_planner_instructions` concatenates only `_SESSION_PLANNER_INSTRUCTIONS_TEMPLATE + _UNSURE_QUEUE_ADDENDUM + _WRITE_TOOLS_ADDENDUM`. SKILL.md is a Cursor-IDE-layer artifact gating parent-agent skill activation; it never reaches `gpt-5.4-mini`. Every prior assumption that "editing the SKILL fixes planner behavior" was wrong.
- **B9 tokens (`Sara`, `Tealeaf`, `allowlist`) were unachievable.** `Sara`/`Tealeaf` appear only in `NPCs/<slug>/README.md` and dossier files which the dispatch guard hard-blocks for recap-write. `allowlist` appears in zero corpus files (only in `_WRITE_TOOLS_ADDENDUM` itself). The model could never satisfy B9 from permitted reads.
- **B7 gold was content-rigid.** Exact verbatim IDs (`tower_blueprint_placement` etc.), specific question regex, specific `default_summary` substrings — a model surfacing the same ambiguities under different (equally valid) slugs always fails.
- **Root cause of `unsure_queue: null`:** `_UNSURE_QUEUE_ADDENDUM` (the only text actually reaching the model about `unsure_queue`) says *"Sparse: at most 4 items per turn; prefer 0 when you can proceed with high confidence"* — actively biasing the model to emit the empty output we see on the happy path.
**Status:** This commit (2026-04-21) makes B7/B9 **achievable in principle** by refactoring B7 to support `mode: "shape"` (no exact-ID rigidity) and replacing B9 tokens with names derivable from permitted reads (`Brambleback`, `Stuart`, `Stacey`, `Marla`). The canonical Session 20 scenario remains opted out (`require_unsure_queue: false`, `require_findings: false`) pending the architectural decisions in the two new READY entries below. The gold refactor does NOT re-enable the gates; it removes the blocks that made them permanently unachievable.
**Next steps:** See new entries `Recap-write planner — SKILL.md body has no injection path…` (architectural) and `Recap-write planner — _UNSURE_QUEUE_ADDENDUM "prefer 0" line contradicts B7…` (addendum/gold fork).
**Refs:** `.cursor/skills/recap-write/SKILL.md` §6 + §6.5 (dead text for planner), `src/prompts/corpus_session_planner.py` lines 197-222 (`build_corpus_session_planner_instructions`), `src/prompts/corpus_session_planner.py` lines 76-98 (`_UNSURE_QUEUE_ADDENDUM`), `evals/session_recap_ingest_vertical_slice/gold/scope_b_session_20_unsure_queue.json` (now `mode: "exact"` explicit + shape-mode example), `evals/session_recap_ingest_vertical_slice/gold/scope_b_session_20_findings.json` (refactored tokens), `evals/session_recap_ingest_vertical_slice/step3_unsure_queue_grading.py` (new shape mode).

## [READY] Recap-write planner — SKILL.md body has no injection path into planner instructions (architectural) — captured 2026-04-21

**Context:** SKILL.md files in `.cursor/skills/<id>/SKILL.md` are read by the parent Cursor agent to gate skill activation but never reach the planner LLM (`gpt-5.4-mini`). The planner sees only `_SESSION_PLANNER_INSTRUCTIONS_TEMPLATE + _UNSURE_QUEUE_ADDENDUM + _WRITE_TOOLS_ADDENDUM` from `src/prompts/corpus_session_planner.py`. This means every prior assumption that "we can fix planner behavior by editing the SKILL" was wrong. Verified by reading `build_corpus_session_planner_instructions` (lines 197-222), `src/agent/skill_pipeline.py`, and `src/agent/planner_skill_dispatch_guards.py`.
**Action:** Decide whether to (a) leave SKILL.md as parent-agent-only docs and write planner-facing guidance directly in `corpus_session_planner.py` addendum strings, or (b) introduce a new `_RECAP_WRITE_SKILL_ADDENDUM` block (or generic per-skill loader) that reads the relevant SKILL.md body at runtime and concatenates it into `instructions` when `active_skill_id` matches. Option (b) needs careful thought re: prompt-cache invalidation, `INSTRUCTIONS_TEMPLATE_ID` regeneration, token cost (SKILL.md is ~20kB), and what subset of SKILL.md should reach the planner vs stay parent-only. **Do NOT just bolt this on.** Design first, ticket the implementation separately.
**Surfaces when:** Planning the next round of judgment-field work; touching `corpus_session_planner.py` addendum assembly; reviewing `INSTRUCTIONS_TEMPLATE_ID` semantics.
**Refs:** `src/prompts/corpus_session_planner.py` (lines 197-222), `src/agent/skill_pipeline.py`, `src/agent/planner_skill_dispatch_guards.py`, `src/agent/planner.py` (lines 1042-1115 for the instructions wiring), `.cursor/skills/recap-write/SKILL.md` (the dead-text source of truth).

## [READY] Recap-write planner — _UNSURE_QUEUE_ADDENDUM "prefer 0" line contradicts B7 happy-path expectations — captured 2026-04-21

**Context:** `_UNSURE_QUEUE_ADDENDUM` in `src/prompts/corpus_session_planner.py` (lines ~76-98) contains: *"Sparse: at most 4 items per turn; prefer 0 when you can proceed with high confidence."* On the Session 20 happy-path recap-ingest, the model interprets this correctly and emits `unsure_queue: null`. B7 gold expects 2-4 items. The two are mutually inconsistent — either the addendum needs a recap-write-specific carve-out ("when the recap-write skill is active and you encountered any prep-vs-recap delta or no-hub NPC, populate at least 2 items"), OR the B7 gold needs to accept null/empty as valid for happy-path scenarios.
**Action:** Make this an explicit fork. Either (a) restructure `_UNSURE_QUEUE_ADDENDUM` so non-recap-write skills keep the "prefer 0" guidance but recap-write turns get an explicit "populate when [list]" override (preferred — keeps the gate meaningful); or (b) downgrade B7 from a hard gate to a soft observation on happy-path scenarios and only enforce on perturbation scenarios where ambiguities are designed in. Whichever path: this file is the same one that Round 4 silently regressed; treat any edit with extreme care, scope it to recap-write only, and add `tests/test_corpus_session_planner_recap_write_order.py`-style anti-regression coverage.
**Surfaces when:** Enabling B7 on canonical Session 20 again; any Scope-B perturbation scenario authoring; touching `_UNSURE_QUEUE_ADDENDUM`.
**Refs:** `src/prompts/corpus_session_planner.py` lines 76-98 (`_UNSURE_QUEUE_ADDENDUM`), `evals/session_recap_ingest_vertical_slice/gold/scope_b_session_20_unsure_queue.json`, `evals/session_recap_ingest_vertical_slice/step3_unsure_queue_grading.py`, `tests/test_corpus_session_planner_recap_write_order.py` (test pattern to mirror).

## [READY] Recap-ingest — cohort flake on `commit_required` (planner stops at preview without apply cue) — captured 2026-04-20

**Context:** One run in the post-B7/B9 cohort previewed the recap but never committed (the Scope-B `commit_required` gold field requires preview → commit in the same graded turn). The other cohort members committed normally. This suggests the planner occasionally stops at the dry-run preview without receiving the synthetic `apply` followup that should trigger the second `write_corpus_file` call.
**Action:** Inspect `evals/session_recap_ingest_vertical_slice/step1_recap_ingest_run.py` followup-turn handling: confirm the synthetic `apply` message is always injected after a successful dry-run preview, that the planner's tool loop continues rather than halting, and that `gold/scope_b_session_20.json::followup_turn` matches the injected text exactly. If the cue is sometimes missing or the planner exits before consuming it, add a guard that re-injects the cue and asserts `commit_required` is satisfied before marking the run complete.
**Surfaces when:** Any Scope-B cohort run where one trial lands PARTIAL while others land PASS; touching the followup-turn injection logic in the Step 1 runner.
**Refs:** `evals/session_recap_ingest_vertical_slice/step1_recap_ingest_run.py` (followup_turn handling), `evals/session_recap_ingest_vertical_slice/gold/scope_b_session_20.json` (`followup_turn` field), `.cursor/skills/recap-write/SKILL.md` §7 (two-phase commit contract).

## [READY] Recap-ingest — cosmetic: violation duplication in step1 verbose output — captured 2026-04-20

**Context:** When a Scope-B violation is added to multiple grader buckets (e.g. `scope_b_unsure_queue` mirrored into `scope_b_payload` and `scope_b`), the Step 1 verbose runner prints the same violation message 3–4 times. Pass/fail logic is unaffected; only the display is noisy and makes triage harder.
**Action:** Dedupe by violation message text inside the `_vlog` violation-iteration loop in `step1_recap_ingest_run.py` around lines 850–900: collect messages into a set per run before printing, or emit each unique message once and annotate which buckets it appeared in. No change to grader logic or scoring.
**Surfaces when:** Triaging a Scope-B FAIL from verbose cohort output; any edit to the Step 1 runner's reporting loop.
**Refs:** `evals/session_recap_ingest_vertical_slice/step1_recap_ingest_run.py` lines ~850–900 (`_vlog` / violation iteration), `evals/session_recap_ingest_vertical_slice/scope_b_grader.py` bucket structure.

## [READY] Lysandra deterministic Step 2 — clarifier over-triggers + `power_axis: unknown` — captured 2026-04-20

**Context:** Surfaced as a follow-up note inside the (now-archived) `[DONE] Lysandra step0 G0.2 fingerprint + G0.3 statblock URL gate` entry. After the step0 gold/runner fix, the deterministic Lysandra slice still exits 1 — but from **Step 2 (intent classifier)**, not Step 0. Specifically: `clarifier_required` over-triggers and `power_axis` returns `unknown` for several scenarios. Same family as the 2026-04-20 NPC voice clarify failures (`torbin_clarify_bump_cr`, `flock_clarify_baddie_with_hat`) which were fixed by tightening `src/prompts/corpus_session_planner.py` (preamble, `_UNSURE_QUEUE_ADDENDUM`, "trait-only who-is" rule, two-checks block). Open question: did the NPC voice prompt tightening generalize, or does Lysandra Step 2 use a different prompt path that still has the original loose behavior?
**Insight:** If the Lysandra failures are downstream of the same prompt edits, this is a single-class problem and verification is a re-run. If Lysandra Step 2 lives in a separate prompt template, our recent fix was scenario-local and we have a class of clarifier scenarios still mis-classified across the suite. Either way, this is the cheapest data point to confirm whether our prompt tightening was global or local.
**Action:** (a) Map Step 2's prompt — does it import `corpus_session_planner.py` or does it have its own intent-classifier prompt? (b) Re-run `evals/lysandra_vertical_slice/run_deterministic_slice.py` with `LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE=1`, capture the failing scenario IDs and the actual `(user_intent, power_axis)` returned. (c) If the prompt is shared, the fix is likely a tighter `power_axis: unknown → clarifier_required` rule with a mini-example. (d) Apply the smallest prompt change, verify with ≥3 trials per failing scenario, plus a no-regression spot-check on the previously-fixed NPC voice scenarios.
**Surfaces when:** Any clarifier-classification work; new slice that depends on Step 2 intent; revisiting the prompt tightening from Round 4 of the 2026-04-20 sweep.
**Refs:** `Backlog-DONE.md` `[DONE] Lysandra step0 G0.2 fingerprint + G0.3 statblock URL gate` (open follow-up section), `evals/lysandra_vertical_slice/run_deterministic_slice.py`, `src/prompts/corpus_session_planner.py` (current clarifier prompts), `evals/npc_voice_vertical_slice/gold/scenarios/torbin_clarify_bump_cr.json` and `flock_clarify_baddie_with_hat.json` for spot-check.

## [READY] CLI ingest vs direct fact-extractor parity — Phase A measured 2026-04-20, prior hypothesis falsified

**Phase A results** (`evals/mirathorn_vertical_slice/output/parity_experiment_20260420T214522Z/parity_results.md`, ~32min, gpt-5.4-mini, 126 evidence units from `The City of Mirathorn.md`):


| Cell | Path   | bs  | facts (extracted) | facts (post-store) |
| ---- | ------ | --- | ----------------- | ------------------ |
| A    | direct | 1   | 349               | —                  |
| B    | direct | 5   | 359               | —                  |
| C    | cli    | 1   | 600               | 600                |
| D    | cli    | 5   | 382               | 382                |


**What the data falsifies:**

- Original hypothesis (direct ≈441 / CLI ≈289 → CLI drops 35% of facts) **does not reproduce on current corpus + code.** Headline A→D gap is +9.5% (CLI bs=5 produces *more* facts than direct bs=1), not the predicted -34%. Either the prior measurement was on a different corpus snapshot or the code path has shifted since.
- "FactStore dedup is the culprit" is **innocent** — pre-store == post-store on both CLI cells.
- "Slot-drop warnings explain the gap" is **insufficient** — only Cell D has slot warnings (1 entity_missing + 1 fact_missing) yet C→D drops 218 facts; warnings cannot account for that.
- Direct path is essentially batch-size-invariant (+2.9% A→B = LLM noise floor).

**What the data surfaces (the *real* anomalies):**

1. **CLI bs=1 produces 71.9% more facts than direct bs=1** (600 vs 349) on identical evidence units. Same chunker, same models. Something in the CLI's call shape (likely the entity payload it passes to the fact extractor — CLI uses `self.store.list_entities()`, direct passes the raw `entity_bundle["entities"]`) materially changes what the fact extractor produces. **This is the new top question.**
2. **CLI batching causes a 36% fact loss** (600 → 382 going bs=1 → bs=5) without slot-drop warnings to explain it. Direct path doesn't show this. Suggests a CLI-side prompt/payload difference at bs>1 that quietly suppresses fact yield. Not a slot-bookkeeping bug.
3. **D1 floors are stale** — `eval_synthesis.py` MIN_FACTS=205 was anchored to a measured CLI bs=5 baseline of 293; current measurement is 382 (+30%). Floors are still safe (382 > 205) but no longer represent `floor(0.7 × current_baseline)`. Re-anchor when the code path stabilizes.

**Phase B1 (code-reading, completed 2026-04-20):** read both call sites to find the structural difference at bs=1. **Result: no material structural difference.**

- `known_entities=None` and `known_entities=[]` are normalized identically (`entity_extractor.py:1190`: `known_entities = known_entities or []`).
- `recap_artifacts is not None` checks only gate output collection (lines 1230, 1282, 1452); the LLM prompt is unaffected.
- Sync `OpenAIResponsesEntityClient` and `AsyncOpenAIResponsesEntityClient` both call `responses.parse[_async]` with identical `model`, `input` (system + user prompt strings), and `text_format=EntityExtractionResult`. HTTP body to OpenAI is identical.
- Same conclusion holds for fact extractor: identical request bodies between sync and async clients at bs=1.

**Implication:** the +34% entity / +71.9% fact deltas between cells A and C cannot be code-side. They are most parsimoniously **LLM stochasticity from independent trials** (separate cache dirs → 126 fresh LLM calls per cell, gpt-5.4 reasoning models have nontrivial sampling variance). **B3 is therefore mandatory before any code work.**

**Phase B candidates (revised):**

- **B3 (now top priority): 3-trial repeat at cells A and C** to measure the LLM noise envelope at bs=1. Cost ~$3–5 and ~3h sequential, or ~1.5h with cache-sharing trick. Without this, every other measurement we make is noise. If envelopes overlap, the entire +71.9% story dissolves and the only real anomaly left to investigate is the **CLI bs=1 → bs=5 drop (-36%)** — and even that needs noise-floor calibration at bs=5 first.
- **B2 (after B3): -36% CLI batching loss.** Print the actual system+user prompts at bs=1 vs bs=5 for unit_index=0 and structurally diff. Hypothesis: bs=5 prompt structure causes the model to dedupe across units inside a single call. This *is* a likely structural difference because batched and single modes use different prompt builders (`_build_batched_fact_user_prompt` vs `_build_fact_user_prompt`).
- **B1 (now retired):** ruled out by code reading; recorded above for traceability.

**Surfaces when:** any change to `_cmd_ingest`, `extract_facts_batch`, `OpenAIResponsesFactClient`, the fact extractor prompt, or D1 thresholds. Re-run `parity_experiment.py` after any such change.

**Refs:** `evals/mirathorn_vertical_slice/parity_experiment.py`, `evals/mirathorn_vertical_slice/output/parity_experiment_20260420T214522Z/`, `src/cli.py:_cmd_ingest`, `src/ingestion/fact_extractor.py`, `src/ingestion/entity_extractor.py`, `evals/mirathorn_vertical_slice/eval_synthesis.py:33-44` (D1 floors).

## [READY] CLI ingest vs direct fact-extractor parity gap — captured 2026-04-20 — SUPERSEDED BY ABOVE PHASE A ENTRY

**Original hypothesis (now falsified by Phase A measurement above; kept for traceability):** CLI ingest yields ~289 facts vs direct ~441 facts → CLI drops 22–34% on same input.
**Why kept:** The current Phase A measurement contradicts the prior baseline numbers. Either (a) the corpus or extractor code drifted between the prior measurement and now, (b) the prior numbers came from a different model/version, or (c) the prior measurement counted something different (e.g. raw `extracted_facts.json` vs post-store). This entry documents the original observation so the historical record stays intact.
**Surfaces when:** New ingest CLI work; D1 threshold updates; any user report that "the CLI loses information vs direct ingest."
**Refs:** `evals/mirathorn_vertical_slice/eval_synthesis.py` (D1 baseline comment), `src/cli.py` ingest command, `src/ingestion/batch_pipeline.py`, `src/ingestion/fact_extractor.py` (`run_fact_extraction`), `evals/mirathorn_vertical_slice/output/phase_d_summary.json`, `evals/mirathorn_vertical_slice/output/extracted_facts.json`.

## [READY] Fact extractor batched call drops/duplicates `unit_index` slots — captured 2026-04-20

**Context:** Surfaced in round 3 (2026-04-20 conversation) while running `eval_synthesis.py`. Stdout shows: `entity_extractor batched call missing unit_index slots: [1, 2, 3, 4]` and `fact_extractor batched call missing unit_index slots: [4]` plus duplicate `unit_index=4` in fact prompt. This is a quiet warning today, not an error, but it suggests batched extraction silently drops or doubles up evidence units.
**Insight:** If batched calls drop slots, the CLI ingest path systematically under-extracts vs `batch_size=1` — which would explain part of the parity gap above.
**Action:** Locate the warning emitter, add a structured log + fail-closed option (e.g. error in test runs, warn in prod). Add a unit test that drives a 5-unit batch and asserts every `unit_index` appears in the response.
**Surfaces when:** Working on `src/ingestion/entity_extractor.py` or `fact_extractor.py` batching; investigating fact-count delta between CLI and direct paths.
**Refs:** `src/ingestion/entity_extractor.py`, `src/ingestion/fact_extractor.py` (search for `missing unit_index slots`).

## [READY] Faction-vs-event entity rollup in extractor — captured 2026-04-20

**Context:** Mirathorn fact-quality C3 fix (2026-04-20 conversation, round 2). Gold expected goals on `ent_shepherds_flock`; model materialized goals on `ent_shepherds_flock_protest` (event subentity). Resolved by realigning gold + `C3_REQUIRED_ENTITY_ATTRS` to point at the event entity, with a `notes` rationale. The underlying pattern — extractor splits faction goals onto sub-entities like `*_protest`, `*_meeting`, `*_attack` — is likely to recur as world bibles grow. There is currently **no** `*_protest → parent` merge rule in `FactStore._resolve_entity_match` (alias/display_name overlap only).
**Insight:** Each gold-realignment buys one slice but slowly drifts C3 from "what the model should do" toward "what the model does." Repeated enough times, the gate stops being a contract and becomes a description. A principled fix is option (A): merge or attribution-rollup at extractor or projection time so org-level facts surface under the org entity even when the model writes them under an event subentity.
**Action:** (a) Survey other slice gold files for `*_protest`, `*_meeting`, `*_event` attributions vs. parent org. (b) Decide between (1) extractor-side: post-process Pass 1 entities to flag `<parent>_<event>` patterns and route their attributes to parent, or (2) projection-side: add a rollup layer in `canon_projection.project_entity_state` that merges event-subentity attrs into the parent under documented attrs. (c) Add a small unit test fixture exercising the Mirathorn case and at least one other.
**Surfaces when:** Adding a new vertical-slice C3 contract; >2 gold realignments of the "subentity has the attr" shape across slices; any noticeable C2/C3 skew on faction goals.
**Refs:** `evals/mirathorn_vertical_slice/eval_fact_quality.py:44-50`, `evals/mirathorn_vertical_slice/gold/gold_facts.json` (`ent_shepherds_flock_protest/goals` entry with `notes`), `src/store.py` (FactStore.add_entities / _resolve_entity_match), `src/reducer/canon_projection.py`.

---

## [READY] Extraction Lab — pipeline contract field-name drift vs Section 9 — captured 2026-04-19

**Context:** Top-to-bottom audit (2026-04-19 conversation). `Docs/Plans/HANDOFF-extraction-lab-design-from-retrieval-lab-learnings.md` §9.1 names a single `corpus_sha256` field. The shipped implementation uses `**store_sha256`** (hash of serialized entities+facts) plus an optional `**corpus_source_sha256`** (from `ingest_index.json` or a passed `--corpus-source-root`). Older runs on disk under `out/extraction_lab/real_smoke_*` only have `corpus_sha256`, so manifests across the dated run dirs do not share a schema.
**Insight:** This is real spec drift — the lab actually distinguishes "store hash" from "source-corpus hash" (which is the better factoring) but the handoff still claims one field. Either rename in code or update §9.1 to lock in both fields.
**Action:** Either (a) update §9.1 to `store_sha256` + optional `corpus_source_sha256` and add a one-line "what each answers" note, or (b) rename `store_sha256` → `corpus_sha256` and absorb `corpus_source_sha256` as the canonical optional field. Then run a single fresh extraction_lab run and confirm the new contract round-trips through `contracts_equal`.
**Surfaces when:** Any Extraction Lab work; introducing a new contract field; debugging a regression that turns out to be store vs corpus drift.
**Refs:** `extraction_lab/pipeline_contract.py` (`compute_pipeline_contract`), `extraction_lab/run_extraction_lab.py:16-19`, `Docs/Plans/HANDOFF-extraction-lab-design-from-retrieval-lab-learnings.md` §9.1.

## [READY] Extraction Lab — `contracts_equal` is unused; no drift_report.json — captured 2026-04-19

**Context:** §9.1 defines a contract-equal regression rule: if two runs share an identical pipeline contract you compare metrics directly; if they don't, you emit a `drift_report.json` and skip hard regression. `contracts_equal()` exists in `extraction_lab/pipeline_contract.py:73-85` but is never called from `assert_regression.py` or `run_extraction_lab.py`, and no `drift_report.json` is ever written.
**Insight:** Without this check, a model swap or prompt change can silently masquerade as a metric regression and waste an investigation. The function is one import away from the only place it matters.
**Action:** In `assert_regression.evaluate_regression`, load the baseline's `pipeline_contract.json`, compare to the current contract via `contracts_equal`, and either (i) downgrade hard fails to warnings + write `drift_report.json`, or (ii) refuse to evaluate and exit with a clear "contract changed; promote a fresh baseline" message. Add a test that flips one contract field and asserts the new behavior.
**Surfaces when:** Promoting a baseline; bumping `entity_extractor` / `fact_extractor` prompt IDs; changing the taxonomy.
**Refs:** `extraction_lab/pipeline_contract.py:73-85`, `extraction_lab/assert_regression.py`, handoff §9.1.

## [READY] Recap-ingest — `step2_grade_against_gold.py` is a stub; STATUS doc claims grader supersession — captured 2026-04-19

**Context:** `evals/session_recap_ingest_vertical_slice/step2_grade_against_gold.py` is a placeholder ("Grader not wired"). The STATUS ledger and EXPERIMENT doc both reference grading via `scope_b_grader.py`. Anyone reading the slice top-down will hit the stub and assume there is a second grading path that doesn't exist.
**Action:** Delete `step2_grade_against_gold.py` (or rename to `step2_grade_against_gold.deprecated.py` with a one-line "see scope_b_grader.py" pointer). Same pass: review `step3_unsure_queue_grading.py` (standalone, not wired into pass/fail) and decide whether to wire it or label it explicitly experimental in the README.
**Surfaces when:** Onboarding to the recap-ingest slice; cleaning the evals tree; deciding whether B7 (unsure_queue) becomes a hard gate.
**Refs:** `evals/session_recap_ingest_vertical_slice/step2_grade_against_gold.py`, `evals/session_recap_ingest_vertical_slice/step3_unsure_queue_grading.py`, `Docs/Plans/STATUS-Session-Recap-Ingest-Benchmark.md`.

## [READY] OpenAI client — collapse three `_load_api_key` copies and stop passing `api_key=` — captured 2026-04-19

**Context:** `src/agent/synthesis.py:153-165`, `src/agent/document_planner.py:139-147`, and `src/agent/query_planner.py:220-228` each implement a `_load_api_key` that loads only `.env.development` (two paths) — they don't match the canonical `bootstrap_env.load_dungeonmindbuddy_dotenv` order (`.env` → `.env.development` → parent). Many call sites then construct `OpenAI(api_key=api_key)` despite the rule in `.cursor/rules/dungeonbuddy-environment.mdc` that says env-only.
**Insight:** This is the same anti-pattern in three places. Fixing it once removes a class of "key loaded from wrong file" bugs and aligns library code with the CLI/test-conftest behavior.
**Action:** Make every `_load_api_key` site call `load_dungeonmindbuddy_dotenv()` first (or import from a single shared helper), and replace `OpenAI(api_key=api_key)` with bare `OpenAI()` everywhere except where the `DungeonMindApiClient.wrap` boundary already covers it. Update the env-loading rule to say "if you find yourself writing `_load_api_key`, you're already wrong — call `load_dungeonmindbuddy_dotenv()`."
**Surfaces when:** Any new entrypoint that talks to OpenAI; any debugging of "key not found"; touching `synthesis.py` / `document_planner.py` / `query_planner.py` / `wiki_compiler.py` / `entity_extractor.py` / `fact_extractor.py`.
**Refs:** `src/agent/synthesis.py:153-165`, `src/agent/document_planner.py:139-147`, `src/agent/query_planner.py:220-228`, `src/bootstrap_env.py:16-30`, `.cursor/rules/dungeonbuddy-environment.mdc`.

## [IDEA] Hoist a shared `evals/reporting/` module — captured 2026-04-19

**Context:** Per-run+cohort report writers exist independently in `evals/planner_slice/live_report.py`, `evals/session_recap_ingest_vertical_slice/recap_ingest_run_report.py`, `evals/npc_voice_vertical_slice/npc_voice_planner_trace.write_npc_voice_suite_report`, `evals/llm_ingestion_slice/`, and `evals/canon_layering/run_benchmarks.py`. Each duplicates the "write JSON sidecar + MD with header + cohort rollup" pattern.
**Action:** Lift a tiny helper (timestamped filename, header block with `corpus_fprint`/`model_id`/`gates_passed`, JSON+MD pair, cohort min/mean/max/sum). Don't refactor existing call sites in one go — adopt module-by-module as new slices land.
**Surfaces when:** Adding a new vertical slice; touching any per-run report writer; the next time someone copies a report writer.
**Refs:** the report writers above.

## [IDEA] Hoist a shared `evals/common/step0_corpus_environment.py` — captured 2026-04-19

**Context:** `evals/lysandra_vertical_slice/step0_corpus_environment.py` is the de facto helper imported by NPC voice and recap Step 1. `evals/session_recap_ingest_vertical_slice/step0_corpus_environment.py` is a duplicate that nothing imports.
**Action:** Move the canonical helper into `evals/common/` (or `evals/__init__.py` exports), update the two consumers, delete the unused duplicate.
**Surfaces when:** Adding a new slice that needs corpus-root resolution; cleaning the recap-ingest slice (above).

## [IDEA] Top-level evals/ HANDOFF cleanup — captured 2026-04-19

**Context:** `evals/HANDOFF-phase1-…` through `HANDOFF-phase8-openai-batch-api.md`, `MODEL_AB_COMPARISON.md`, `AUTO_ESCALATION_FULL_CORPUS_REPORT.md`, and `HANDOFF-commit-and-model-ab.md` describe completed work. Active playbooks: `HANDOFF-e2e-smoke-and-quality-validation.md`, `HANDOFF-next-agent-ingestion-temporal-gates.md`. Mixed: `HANDOFF-gold-scoring-eval.md` (some sections still open), `HANDOFF-taxonomy-rework.md` (Phases A–C done, follow-ups linger).
**Action:** Move the eight phase HANDOFFs + `MODEL_AB_COMPARISON.md` + `AUTO_ESCALATION_FULL_CORPUS_REPORT.md` + `HANDOFF-commit-and-model-ab.md` into `Docs/Plans/archive/` with a one-line README pointer. Leave the active two in place.
**Surfaces when:** Onboarding to the evals tree; cleaning Docs/Plans/.
**Refs:** `evals/HANDOFF-phase*.md`, `Docs/Plans/archive/`.

---

## [READY] Roll-lookup as `grep`, not LLM call — captured 2026-04-18

**Context:** Live-play workflow analysis (Session 21 prep). The user typed *"Tell me what 28 on the traveling d100"* (transcript line 4765) — a deterministic line-of-file fetch that went through the full LLM round-trip.
**Insight:** Every die-result lookup against a corpus markdown table is `read line N of file F`. Zero model needed. The current behavior burns latency and tokens for a `sed -n '28p'`-equivalent operation.
**Action:** Add a `/roll <table-name-or-path> <n>` shortcut (skill or hook) that grep/reads the matching row from `Elderwyld/Roads/*.md`, `Elderwyld/Wilderness/*.md`, etc., and returns the row text plus the file:line ref. No LLM call.
**Surfaces when:** Building any d100/d20 table the user will roll on at the table; designing live-play tooling; corpus-search shortcuts.
**Refs:** `canvases/live-play-workflow-analysis.canvas.tsx` (DungeonMindBuddy canvas), corpus files under `corpus/eldyrwild-markdown/Elderwyld/Roads/` and `Elderwyld/Wilderness/`

## [IDEA] Mirathorn — what is happening while the party is away? — captured 2026-04-18

**Context:** Closing aside in the live-play workflow analysis: *"The question of what is happening in Mirathorn is one I need to think more about and have very clear ideas about."* This is the canonical example of a side-thought that needed a parking lot.
**Insight:** The party is multi-day-travel out from Mirathorn, but the city has multiple live threads (tainted jerky / supply chain, Sara's *"who can I trust"* wobble, Tealeaf line still hanging, Lysandra reunion, Dustwalker decoy fallout, curfew council, Stormbark Tea / Mossford handoff). Without a clear authored state, the city goes flat the moment the party turns around.
**Action:** Author a `Longmont Campaign/Campaign 2/Mirathorn — While You Were Away.md` doc that timelines what happens in the city across the party's travel days. Pull from the existing threads in `Elderwyld_Narrative_Ledger_Campaign2.md` and the Sara / Lysandra dossiers. Result should answer: *"if the party scries / sends / asks Sara on the rockie-talkie at any point during the journey, what truthful state can the GM relay?"*
**Surfaces when:** Prepping any session where a Mirathorn check-in is plausible; party uses a rockie-talkie; party reaches Mossford or further; building the swamp-arc bridge.
**Refs:** `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_Campaign2.md`, `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/`, `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/`, `canvases/live-play-workflow-analysis.canvas.tsx`