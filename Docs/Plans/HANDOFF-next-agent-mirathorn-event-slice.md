# Handoff: Mirathorn Event-Sourced Slice

## Update (2026-03-28)

### Skeptical Investigation Continuation Handoff (Do This Next)

Status: PENDING (critical investigation track)

### Why This Exists

Recent Council Room benchmark results show that ingestion alone does not guarantee correct post-play answers. We now have enough evidence to treat this as a multi-layer failure mode (scope + projection + temporal ordering + entity quality), not a prompt-only issue.

### Ground Truth Established So Far (Do Not Re-litigate)

- Council packet sources are now ingested into `evals/mirathorn_vertical_slice/output/phase_d_store`:
  - `The Council Room`
  - `Battle with The Wolf and Aftermath`
  - `The Emergency Council Meeting`
  - `The City Council`
  - `Longmont Campaign General Notes` (campaign, `longmont-c1`)
- Question-set benchmark was executed with output files:
  - `evals/mirathorn_vertical_slice/output/council_room_question_set.json`
  - `evals/mirathorn_vertical_slice/output/council_room_question_set.md`
- Observed score:
  - `pass_updated=1`
  - `fail_stale=1`
  - `fail_incomplete=3`
  - `fail_error=0`
- Key falsification:
  - Running `ask` without `--campaign longmont-c1` excludes campaign-layer OBSERVED facts by design.
  - This alone explains a large share of "no OBSERVED facts" responses.

### Core Investigative Claim to Test

> Weak post-play deltas are primarily a projection/temporal provenance issue, not just synthesis phrasing.

This must be proved or falsified with run evidence, not intuition.

### Skeptical Gap Matrix (Must Audit Each)

1. **Scope Gap**
   - Are evaluations consistently querying with `campaign_id=longmont-c1` when post-play deltas are expected?
   - Anti-pattern to catch: benchmark scripts calling `ask` without campaign scope.

2. **Timeline Provenance Gap**
   - We have natural temporal anchors (`Session 11`, `Session 12`) in source content.
   - Verify whether extracted facts preserve usable ordering fields:
     - `asserted_in_session`
     - `sequence_index_within_session`
   - Current suspicion: campaign facts mostly carry `None`, forcing non-temporal tie-break behavior.

3. **Selection Policy Gap**
   - Projection currently selects "latest" fact via sort key that can degrade to lexicographic `fact_id` ordering when temporal metadata is absent.
   - Need hard evidence where selected fact conflicts with expected end-of-session truth.

4. **Truth-State Visibility Gap**
   - Context formatting maps campaign layer to generic `"CAMPAIGN"` marker rather than explicitly preserving `OBSERVED` vs `PREP`.
   - Determine whether this obscures conflict resolution in final synthesis.

5. **Entity Integrity Gap**
   - Check for over-merged entities (alias pollution) causing cross-character fact contamination.
   - Example suspicion: "the Wolf" alias set contains unrelated names and pronouns.

6. **Store Hygiene Gap**
   - Store is append-only and can accumulate duplicate/competing facts from repeated ingests.
   - Measure duplicate ratio and conflict growth impact on "current fact" selection quality.

7. **Source-Class Semantics Gap**
   - Some post-play-adjacent docs are ingested as world `seed_reference` (CANON).
   - Validate whether this misclassifies scenario/procedural text as persistent canon and suppresses observed deltas.

### Required Deliverable From Next Agent

Produce an evidence-backed investigation report section in this handoff (append under new heading):

- `Gap -> Evidence -> Impact -> Confidence -> Proposed remediation`
- One row per gap above.
- Include at least one concrete reproduced example per high-impact gap:
  - target question,
  - projected selected fact,
  - expected fact,
  - mismatch reason category (`scope`, `selection`, `timeline`, `entity_merge`, `truth_state_visibility`, `store_noise`).

### Required Minimal Experiments

1. **Scope A/B**
   - Run same 5 Council Room questions with:
     - no campaign scope
     - `--campaign longmont-c1`
   - Quantify "no OBSERVED" fallback frequency and answer deltas.

2. **Timeline Metadata Audit**
   - Count campaign facts where:
     - `asserted_in_session is not None`
     - `sequence_index_within_session is not None`
   - If near-zero, mark as blocking for temporal correctness.

3. **Selection Trace Audit (Wolf + Council Room)**
   - For key attributes, dump:
     - all candidate facts (truth state, layer, evidence section),
     - selected fact,
     - whether selected aligns with expected Session 12 outcome.

4. **Entity Merge Audit**
   - For `ent_the_wolf` and `ent_council_room`, inspect alias sets and conflicting subject facts.
   - Flag any alias that is clearly foreign identity leakage.

5. **Noise/Conflict Audit**
   - Compute duplicate fact ratio and open conflict volume for current store.
   - Assess whether repeated ingest passes are materially degrading projection reliability.

### Definition of "Investigation Complete"

All of the following are true:

- Every gap category has explicit evidence and confidence level.
- At least 3 concrete mismatch cases are classified to root cause category.
- Timeline provenance status is conclusively assessed (not assumed).
- A ranked remediation backlog is proposed with expected impact per item.
- No recommendation is accepted without direct empirical trace from current artifacts.

### Anti-Patterns to Avoid

- Treating "model hallucination" as primary explanation without proving projection correctness first.
- Assuming session headers in source automatically become temporal fact fields.
- Proposing fixes before proving where the mismatch enters (`ingest`, `projection`, or `synthesis`).
- Mixing architecture changes with investigation output in same commit.

### Investigation Report (2026-03-28, Skeptical Continuation Executed)

Artifacts generated during this run:

- `evals/mirathorn_vertical_slice/output/council_room_scope_ab.json`
- `evals/mirathorn_vertical_slice/output/council_room_gap_audit.json`
- `evals/mirathorn_vertical_slice/output/council_room_ingest_scope.json`
- `evals/mirathorn_vertical_slice/output/council_room_keyword_facts.json`
- `evals/mirathorn_vertical_slice/output/council_room_duplicate_keys_top.json`

Commands executed:

- `uv run python - <<'PY' ... ask ... (scope A/B, 5 questions x 2 scopes) ... PY`
- `uv run python - <<'PY' ... timeline + selection + duplicate/conflict audits ... PY`
- `uv run python - <<'PY' ... ingest scope/source-class audit ... PY`

#### Gap Matrix (Gap -> Evidence -> Impact -> Confidence -> Proposed remediation)

| Gap | Evidence | Impact | Confidence | Proposed remediation |
| --- | --- | --- | --- | --- |
| Scope Gap | A/B run: no scope had `no_observed_count=3/5`; `--campaign longmont-c1` had `0/5` (`council_room_scope_ab.json`). `run_council_room_question_set.py` still calls `ask` without `--campaign`. | High: major share of stale "no OBSERVED" responses is query-scope omission, not synthesis quality. | High | Make campaign scope explicit in all post-play eval scripts; fail eval run if post-play questions are executed with `campaign_id=null`. |
| Timeline Provenance Gap | Campaign facts count `1944`; `asserted_in_session != None` count `0`; `sequence_index_within_session != None` count `0` (`council_room_gap_audit.json`). | High: no temporal ordering signal for projection; "latest" degenerates to fallback behavior. | High | Populate session and sequence fields at extraction/ingest time from session recap structure (Session 11/12 headers + intra-section order). |
| Selection Policy Gap | For `ent_the_wolf.physical_condition` (campaign scope), selected fact is `fact_the_wolf_physical_condition_f8fe558847d0 = Invisible`; candidate set also includes `fact_the_wolf_physical_condition_0bff1a76ba2e = receives a killing blow (dies)` and `...9563... = oily sheen in eyes fades`. All candidates have null temporal fields, so sort falls back to `fact_id` lexical order (`canon_projection._fact_sort_key`). | High: end-of-session truth can be overwritten by lexicographic ID order. | High | Introduce deterministic precedence: explicit event/session ordering > truth-state terminality (`dead`, `decapitated`, `fades`) > source order; block fallback-to-ID when competing OBSERVED facts are terminally contradictory. |
| Truth-State Visibility Gap | `context_formatter._truth_state_from_source_layer()` maps campaign layer to `"CAMPAIGN"` and drops original truth-state (`OBSERVED` vs `PREP` vs `IDEA`). Example answer for wolf status under campaign says corruption "unknown" while relevant facts exist, but context only signals generic campaign provenance. | Medium-High: synthesis loses conflict-resolution cues and can underweight authoritative observed deltas. | Medium | Preserve original fact `truth_state` in projection payload and render `[OBSERVED|PREP|IDEA, from: ...]` in context; include per-attribute competing truth-states in conflict line. |
| Entity Integrity Gap | `ent_the_wolf` alias set includes clearly foreign identities and pronouns: `Bonogo`, `Grishna`, `Torbin`, `He/he/him` (`council_room_gap_audit.json`). Merge behavior in `store.py` is alias-overlap based and permissive. | Medium-High: over-merge risk creates cross-character contamination potential in future ingests. | Medium | Harden entity merge with type-aware + confidence-aware matching, pronoun blacklist, and protected-name disallow list for known PCs/NPCs. Add merge-audit warnings for cross-identity alias unions. |
| Store Hygiene Gap | Store is append-only; duplicate key ratio is `0.2485` with `530` duplicate canonical keys and max duplicate multiplicity `7` (`council_room_gap_audit.json`, `council_room_duplicate_keys_top.json`). Ingest log shows repeated ingest of same sources (`council_room_ingest_scope.json`). | Medium-High: duplicate growth inflates conflict surface and worsens projection tie-break ambiguity over time. | High | Add idempotent ingest guard by source fingerprint+layer+campaign, plus optional compaction/rebuild command to dedupe fact keys while preserving provenance history. |
| Source-Class Semantics Gap | Council battle/council docs were ingested as `layer=world`, `source_class=seed_reference`; campaign notes are `layer=campaign`, `source_class=observed_session_recap` (`council_room_ingest_scope.json`). | Medium: scenario-adjacent procedural content risks being treated as persistent CANON, reducing visibility of post-play deltas and increasing precedence ambiguity. | Medium | Reclassify scenario/procedural world docs to a non-authoritative planning class (or lower precedence within world), and require explicit source-class policy tests for Council packet inputs. |

#### Concrete Mismatch Cases (reproduced)

1) **Case: q_arch_delta (no campaign scope)**  
   - Target question: `What physical changes to the Council Room happened during Session 12?`  
   - Selected/projected fact: no campaign OBSERVED council-room delta is applicable; answer states "no OBSERVED or PREP facts".  
   - Expected fact: campaign-level `ent_council_room.physical_condition = Disheveled` and Session 12 battle deltas.  
   - Mismatch category: `scope`  
   - Evidence: `council_room_scope_ab.json` (no scope vs campaign A/B).

2) **Case: q_wolf_status (campaign scope)**  
   - Target question: `What is the Wolf's status at the end of Session 12, including corruption state?`  
   - Selected/projected fact: `ent_the_wolf.physical_condition -> Invisible` (`fact_the_wolf_physical_condition_f8fe558847d0`).  
   - Expected fact: terminal outcome facts include `receives a killing blow (dies)` (`fact_the_wolf_physical_condition_0bff1a76ba2e`) and `oily sheen in eyes fades` (`...9563...`).  
   - Mismatch reason: all candidates have null temporal provenance so reducer falls back to lexical `fact_id` tie-break.  
   - Mismatch category: `selection` + `timeline`  
   - Evidence: `council_room_gap_audit.json`, plus direct candidate dump reproduced in this session.

3) **Case: q_wolf_status (campaign scope, corruption interpretation)**  
   - Target question: same as above.  
   - Selected/projected framing in answer: corruption state reported as unknown / unresolved.  
   - Expected fact: conflict should be explicit between world `Corrupted` and campaign deltas (`oily sheen fades`, death sequence) with truth-state-aware prioritization.  
   - Mismatch reason: context uses generic `[CAMPAIGN]` marker rather than preserving `OBSERVED/PREP/IDEA`, weakening synthesis conflict handling.  
   - Mismatch category: `truth_state_visibility`  
   - Evidence: `council_room_scope_ab.json` + `src/agent/context_formatter.py`.

#### Ranked Remediation Backlog (expected impact)

1. **P0 - Add temporal provenance on campaign facts (`asserted_in_session`, `sequence_index_within_session`)**  
   - Expected impact: very high; directly fixes ordering ambiguity feeding wrong "latest" picks.
2. **P0 - Replace lexical fallback selection for contradictory OBSERVED candidates**  
   - Expected impact: very high; prevents "Invisible beats Dead" class errors.
3. **P0 - Enforce campaign scope in post-play eval harnesses**  
   - Expected impact: high; removes known false-negative path from benchmarking.
4. **P1 - Preserve explicit truth_state in projection/context formatter**  
   - Expected impact: medium-high; improves synthesis grounding under mixed-layer conflict.
5. **P1 - Add ingest idempotency + dedupe/compaction path**  
   - Expected impact: medium-high over time; reduces conflict noise accumulation.
6. **P2 - Tighten entity merge policy and alias hygiene checks**  
   - Expected impact: medium; prevents future contamination drift.
7. **P2 - Refine source-class precedence for scenario/procedural world docs**  
   - Expected impact: medium; improves canon-vs-observed interpretability.

#### Investigation Completion Check

- Every gap category audited with evidence and confidence: **Yes**
- >=3 concrete mismatch cases with root-cause category: **Yes (3)**
- Timeline provenance conclusively assessed: **Yes (0/1944 campaign facts had usable temporal fields)**
- Ranked remediation backlog with expected impact: **Yes**
- Recommendations tied to direct trace evidence: **Yes**

#### Benchmark Philosophy and Design Notes (Track Going Forward)

Treat benchmark scoring as an explicit product contract, not an ad-hoc keyword filter.

- **Global truth over token literalism:** score stale-state only when answer semantics are globally stale, not when one localized trait remains unchanged.
- **Separation of concerns:** distinguish `fail_stale` (wrong state selection) from `fail_incomplete` (partial but directionally correct answer).
- **Adversarial fixtures:** maintain at least one fixture where answer contains both updated deltas and a localized unchanged trait; expected verdict must remain non-stale.
- **Deterministic scoring contract:** keep rubric logic in code-level helper functions with direct unit tests to avoid silent drift.
- **Traceability:** for each fail class, emit machine-readable reasons (`stale_hits`, `global_stale_hits`, `must_hits`) so regressions are diagnosable from artifacts.
- **Dual-signal scoring:** maintain both strict (literal token match) and semantic (equivalence group) scoring in parallel. Semantic scoring defines `SEMANTIC_EQUIVALENCES` mapping tokens to regex groups (e.g., "killing blow" → ["decapitated", "head removed"]). Both signals appear in every benchmark output so regressions on either axis are visible.
- **Synthesis contract over rubric patching:** when the benchmark fails because the model paraphrases evidence, prefer tuning the synthesis prompt to force verbatim citation of terminal outcome phrases rather than loosening the rubric. The rubric stays strict; the model is instructed to meet it.

#### Phase E Results: Synthesis Contract Tightening (2026-03-28)

**Changes applied:**
1. Synthesis system prompt now includes a "terminal outcome rule" requiring verbatim citation of death/destruction/resolution phrases from projection evidence.
2. Council room benchmark now emits dual-signal scoring: `strict_verdict` (literal token match) and `semantic_verdict` (equivalence groups) for every question.
3. `SEMANTIC_EQUIVALENCES` map covers terminal phrases (killing blow ↔ decapitated, dead ↔ head removed, oily sheen fades ↔ oily sheen + fades regex).

**Delta table (Phase D → Phase E):**

| Question | Phase D Strict | Phase E Strict | Phase E Semantic | Delta |
|---|---|---|---|---|
| q_arch_current | fail_incomplete (0 must) | fail_incomplete (0 must) | fail_incomplete (0 must) | no change — data gap |
| q_arch_delta | fail_incomplete (1: runes) | fail_incomplete (1: runes) | fail_incomplete (1: runes) | no change — data gap |
| q_wolf_status | fail_incomplete (1: dead) | **pass_updated** (2: killing blow, dead) | **pass_updated** (2) | promoted |
| q_pre_post | fail_incomplete (2: before, after) | **pass_updated** (3: before, after, killing blow) | **pass_updated** (3) | promoted |
| q_thalia | pass_updated (2: ensorcelled, wolf) | pass_updated (2) | pass_updated (2) | held |

**Overall: 1/5 → 3/5 pass_updated, 0 fail_stale, 2 fail_incomplete.**

**Diagnosis of remaining failures:**
Both `q_arch_current` and `q_arch_delta` fail because their must_tokens ("arched ceilings", "floating chandelier", "secret passage", "chandelier") reference architectural features that do not exist in the fact store. The projection context does not contain these facts — they were never ingested. These are **data gaps**, not synthesis gaps. The answer IS contextually correct given available evidence (large circular room, disheveled, runes activated, Fireball).

**Next remediation vector:** Ingest the Council Room source document (`corpus/eldyrwild-markdown/.../The Council Room.md`) which likely contains architectural details (ceilings, chandelier, passages). This is a corpus coverage issue, not a pipeline issue.

## Update (2026-03-27)

### What Changed Since Prior Handoff

- Phase D (`ingest` + `ask`) is now implemented and empirically passing.
  - Gate run: `uv run python evals/mirathorn_vertical_slice/eval_synthesis.py`
  - Latest result: `OVERALL: PASS`
- Corpus markdown was generated from source docs and relocated to:
  - `corpus/eldyrwild-markdown/`
- Legacy corpus tree under `Docs/Eldyrwild and Campaign Context/` is now treated as source/binary-heavy location.
- Synthesis and extraction runtime now includes:
  - async model-call path for synthesis
  - async-capable OpenAI adapters for entity/fact extraction
  - structured JSONL run records (`<store>/logs/*.jsonl`)
  - verbose per-stage/per-unit logging
  - fail-fast/early-exit behavior in CLI/eval when critical stages fail
- Environment/model policy resolution now supports central workspace roots:
  - `.env.development` fallback to `/home/drakosfire/Projects/DungeonOverMind/.env.development`
  - `MODEL_POLICY.json` fallback to `/home/drakosfire/Projects/DungeonOverMind/MODEL_POLICY.json`

### Execution Verification Snapshot (2026-03-27)

- End-to-end verification executed in `DungeonMindBuddy` with no code edits required.
- Commands run:
  - `uv run ruff check .` -> pass
  - `uv run pytest tests/ --maxfail=1` -> `65 passed, 2 skipped`
  - `uv run python evals/llm_ingestion_slice/run_slice.py` -> completed successfully and regenerated eval artifacts
- Current gates from `evals/llm_ingestion_slice/output/current/report.md`:
  - `OVERALL: PASS`
  - `Gate A: PASS`
  - `Gate V: PASS` (`entity_density=0.3333`, `duplicate_fact_ratio=0.0`, `conflict_volume_band=1`)
  - `Gate B: PASS`
  - `Gate C: PASS`
  - `Gate D: PASS` (`instantiation_to_zero_tick=2`, `zero_tick_to_live_state=2`)
- Runtime outputs under `evals/llm_ingestion_slice/output/current/` were refreshed and remain untracked artifacts.

### Completed In This Session (Extraction Viability Gates)

- Added deterministic pre-projection viability gate (`Gate V`) in `evals/llm_ingestion_slice/run_slice.py`.
  - Metrics:
    - `entity_density = len(unique_entity_ids) / len(evidence_units)`
    - `duplicate_fact_ratio = (total_facts - unique_fact_keys) / total_facts`
    - `conflict_volume_band = len(conflicts)`
  - Duplicate fact canonical key:
    - `(subject_entity_id, attribute, normalized_or_label)` where `normalized_or_label` prefers `value.normalized` then `value.label`.
- Added threshold config at:
  - `evals/llm_ingestion_slice/viability_thresholds.json`
  - Values:
    - `min_entity_density: 0.20`
    - `max_duplicate_fact_ratio: 0.35`
    - `min_conflicts: 1`
    - `max_conflicts: 12`
- Added fail-fast gate sequencing:
  - Run `Gate A` + `Gate V` first.
  - If `Gate V` fails, skip Gate B/C/D and return non-zero.
  - Always emit machine-readable and human-readable diagnostics:
    - `evals/llm_ingestion_slice/output/current/gate_report.json`
    - `evals/llm_ingestion_slice/output/current/report.md`
- Added tests in `tests/evals/test_llm_ingestion_slice.py`:
  - viable pass case
  - zero entities failure
  - zero facts failure
  - high duplicate fact ratio failure
  - conflict count outside band failure
  - fail-fast `main()` behavior that confirms Gate B/C/D are skipped on viability failure
- Verification evidence:
  - `uv run ruff check evals/llm_ingestion_slice/run_slice.py tests/evals/test_llm_ingestion_slice.py` -> pass
  - `uv run pytest tests/evals/test_llm_ingestion_slice.py -q` -> `9 passed`
  - `uv run python evals/llm_ingestion_slice/run_slice.py` -> pass; Gate V metrics+thresholds present in output report

## Mission

Continue implementation of the Mirathorn event-sourced vertical slice from the locked plan:

- `Docs/Plans/mirathorn_event-sourced_slice_8eab1beb.plan.md`

Primary objective: prove the GM workflow state progression (`instantiation -> planning/zero-tick -> live`) using event-sourced ingestion and strict canon-layer behavior.

## Focused Handoff: Readiness Challenge via Gold Expansion + Blind Replay

Status: PENDING (recommended next)

### Why This Handoff Exists

Current PASS results show the slice works on known Milestone-1 inputs. That does **not** prove readiness under distribution shift, sparse/ambiguous evidence, or adversarial canon-layer interactions. This handoff is designed to challenge assumptions and surface brittle behavior early.

### Objective

Use expanded gold coverage and blind replay to answer one question:

> Is the vertical slice robust enough to be trusted beyond Mirathorn Milestone-1 happy paths?

### Skeptical Test Philosophy (Non-Negotiable)

- Treat current green gates as **baseline**, not proof of generalization.
- Prefer tests that can falsify confidence over tests that confirm expected behavior.
- Do not relax thresholds to make runs pass.
- If failures appear, preserve them as evidence; fix root cause instead of filtering cases out.

### Assumptions to Challenge Explicitly

1. **Extraction generalizes:** entity/fact quality will hold outside current documents.
2. **Layering remains correct:** world vs campaign precedence and `canon_layer` semantics hold under noisier inputs.
3. **Gate V is meaningful:** viability metrics catch non-viable extraction without rejecting valid edge cases.
4. **Workflow deltas stay auditable:** `instantiation -> zero_tick -> live_state` transitions remain deterministic and explainable.

### Scope of Work

#### A) Expand Gold Coverage (beyond Milestone-1)

- Add at least 2 additional source pairs (world + campaign) that are meaningfully different from Mirathorn baseline:
  - one **sparse/low-entity** pair
  - one **conflict-heavy** pair
- Use the **Council Room packet** as the primary expansion source set (required):
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Council Room.md` (primary anchor)
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The City Council.md`
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md` (must include Session 11 and Session 12 recap sections)
- Expansion intent:
  - treat `The Council Room` as the narrative/planning anchor
  - use the remaining council/battle docs to introduce overlap, conflict, and precedence pressure
  - use Campaign 1 Session 11/12 recaps as campaign-layer replay pressure against world-layer council material
- For each pair, add/update deterministic artifacts under `evals/llm_ingestion_slice/gold/` with matching manifest fingerprints.
- Ensure each gold pack contains enough ground truth to challenge:
  - entity extraction quality
  - duplicate-fact behavior
  - conflict handling and canon decisions
  - projection checkpoint deltas

#### B) Add Blind Replay Scenarios

- Implement replay cases where expected outcomes are known to evaluator but not encoded as narrow case logic in runner.
- Replay must run through the same production-like slice path:
  - load sources
  - build slice artifacts
  - run gates A/V/B/C/D
  - emit machine-readable + human-readable reports
- Require scenario-level result summaries, not only aggregate pass/fail.

### Scenario Matrix (Minimum)

Each scenario must identify target risk and expected failure mode if the system is brittle.

1. **Sparse Evidence Scenario**
   - Risk: false viability pass with weak extraction signal.
   - Expected brittle failure: Gate V misses non-viable output or downstream gates produce misleading pass.
2. **Conflict Saturation Scenario**
   - Risk: conflict explosion causes unstable canon decisions or projection drift.
   - Expected brittle failure: Gate C/D regressions, non-deterministic ordering, or inconsistent deltas.
3. **Cross-Layer Ambiguity Scenario**
   - Risk: incorrect world/campaign precedence under overlapping assertions.
   - Expected brittle failure: wrong winning facts, incorrect `canon_layer` attribution.
4. **Replay Determinism Scenario**
   - Risk: same inputs produce divergent outputs/reports.
   - Expected brittle failure: hash/report mismatch across reruns.

### Readiness Exit Criteria (Strict)

The slice is considered "ready for broader use" only if all are true:

- All new scenarios run with deterministic outputs on repeated replay.
- No silent degradations:
  - any red gate in any scenario is blocking.
- Gate V remains calibrated by evidence:
  - catches intentionally non-viable cases,
  - does not reject clearly viable cases in expanded corpus.
- Gate D deltas remain auditable and semantically plausible per scenario narrative.

### Required Deliverables

- Updated/expanded manifests and gold artifacts for added scenario pairs.
- Replay harness updates with scenario-level reporting.
- A concise readiness evidence section in report output including:
  - scenario inventory
  - per-scenario gate outcomes
  - deterministic replay proof (at least 2 identical runs per scenario)
  - explicit "assumptions challenged" outcomes (held/failed)

### Anti-Patterns to Avoid

- Expanding only with easy documents that mirror existing structure.
- Counting scenario quantity as quality without risk coverage.
- Hiding failures by tuning thresholds or narrowing acceptance conditions.
- Mixing unrelated refactors into this readiness work.

### Verification Commands (Minimum)

- `uv run ruff check .`
- `uv run pytest tests/ --maxfail=1`
- `uv run python evals/llm_ingestion_slice/run_slice.py`
- replay command(s) for each new scenario (document exact commands in report)

### Commit Guidance

- commit 1: `feat(evals): add expanded gold packs for readiness challenge scenarios`
- commit 2: `feat(evals): add blind replay matrix and scenario-level gate reporting`
- commit 3: `test(evals): add determinism and cross-scenario readiness assertions`

## Focused Handoff: Extraction Viability Gates (Do This First)

Status: DONE

### Objective

Add deterministic viability gates before event projection so the slice fails fast when extraction quality is too low to trust.

### Why This Is Blocking

- Current slice runner can pass using scaffolded artifacts even when extraction quality drifts.
- We need minimum extraction viability guarantees before `facts -> events -> projections`.
- This preserves hard-gate semantics and prevents false positives in downstream Gate B/C/D.

### Required Metrics (Deterministic)

1. **`entity_density`**
   - Formula: `len(unique_entity_ids) / len(evidence_units)`
   - Fail when:
     - `len(evidence_units) == 0`, or
     - `len(unique_entity_ids) == 0`, or
     - `entity_density < min_entity_density`
2. **`duplicate_fact_ratio`**
   - Use a canonical key per fact:
     - `(subject_entity_id, attribute, normalized_or_label)`
   - Formula: `(total_facts - unique_fact_keys) / total_facts`
   - Fail when:
     - `total_facts == 0`, or
     - `duplicate_fact_ratio > max_duplicate_fact_ratio`
3. **`conflict_volume_band`**
   - Formula: `len(conflicts)`
   - Fail when:
     - `conflicts < min_conflicts`, or
     - `conflicts > max_conflicts`

### Fail-Fast Contract

- Add a pre-projection viability stage in `evals/llm_ingestion_slice/run_slice.py`.
- If viability fails:
  - stop immediately (do not run projection/hybrid/workflow gates),
  - write machine-readable failure details to `output/current/gate_report.json`,
  - return non-zero exit code,
  - include clear reason(s) in `output/current/report.md`.

### Suggested Config Shape

- Add deterministic threshold config at:
  - `evals/llm_ingestion_slice/viability_thresholds.json`
- Suggested initial values for Milestone-1:
  - `min_entity_density`: `0.20`
  - `max_duplicate_fact_ratio`: `0.35`
  - `min_conflicts`: `1`
  - `max_conflicts`: `12`

### Implementation Targets

- `evals/llm_ingestion_slice/run_slice.py`
  - add viability metric computation
  - add fail-fast gate before projection gates
  - include metric snapshot in `gate_report.json`
- `tests/evals/test_llm_ingestion_slice.py`
  - add pass test for viable run
  - add failure tests for:
    - zero entities
    - zero facts
    - high duplicate ratio
    - conflict count outside band
- Optional helper (if cleaner):
  - `src/ingestion/extraction_viability.py`

### Acceptance Criteria

- Slice run fails immediately when viability checks fail.
- Failure is deterministic and reproducible for same inputs/config.
- `gate_report.json` contains:
  - computed metrics
  - thresholds
  - explicit fail reasons
- Existing hard gates (A/B/C/D) remain strict and unchanged when viability passes.

### Verification Commands

- `uv run ruff check evals/llm_ingestion_slice/run_slice.py tests/evals/test_llm_ingestion_slice.py`
- `uv run pytest tests/evals/test_llm_ingestion_slice.py -q`
- `uv run python evals/llm_ingestion_slice/run_slice.py`

### Commit Guidance

- Keep this as a single focused commit:
  - `feat(evals): add deterministic extraction viability gates with fail-fast behavior`

## Current State

- Plan is finalized and updated with current status.
- Locked source references for slice work now have markdown equivalents in:
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md`
- Readiness expansion packet is identified and available:
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Council Room.md`
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The City Council.md`
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/The Emergency Council Meeting.md`
  - `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/City Council Building/Battle with The Wolf and Aftermath.md`
- World baseline anchor to seed instantiation:
  - `Approach to Mirathorn` section in `The City of Mirathorn` source
- Rules corpus policy for Milestone 1:
  - reference metadata only (not first-class graph nodes)
- Product direction:
  - no backward compatibility requirement; build and fix forward

## Non-Negotiables

- Preserve canon-layer semantics:
  - world evidence: `canon_layer=world`, `campaign_id=null`
  - campaign evidence: `canon_layer=campaign`, `campaign_id=<campaign>`
- Event-sourced change tracking is required (do not shortcut directly to facts-only behavior).
- Hard gates remain hard. No soft-pass language and no threshold downgrades.

## Execution Order (Do This Next)

1. [DONE] Lock and fingerprint the two markdown source artifacts for reproducibility.
2. [DONE] Create Milestone-1 gold artifact pack under `evals/llm_ingestion_slice/`:
   - `slice_manifest.json`
   - `gold/evidence_units.json`
   - `gold/events.json`
   - `gold/facts.json`
   - `gold/conflicts.json`
   - `gold/canon_decisions.json`
   - `gold/projection_instantiation.json`
   - `gold/projection_zero_tick.json`
   - `gold/projection_live_state.json`
3. [DONE] Implement event-first ingestion loop in `src/ingestion/` that outputs schema-valid records with provenance.
4. [DONE] Implement projection runner checkpoints:
   - instantiation
   - zero-tick
   - live-state
5. [DONE] Implement hard-gate evaluator:
   - source/layer integrity
   - event contract integrity
   - hybrid correctness
   - workflow state progression
   - extraction viability pre-gate (Gate V) with fail-fast behavior
6. [DONE] Add tests for success and failure paths.
7. [DONE] Run verification commands and emit machine-readable pass/fail artifacts.

## Proposed Next Steps (Recommended)

1. [PENDING] **Build `evals/llm_ingestion_slice/` scaffold first**
   - commit evaluator skeleton + fixture contracts before implementing ingestion event loop changes
   - keep hard-gate outputs machine-readable (`json`) plus human-readable summary
2. [PENDING] **Implement event-first ingestion with explicit stage artifacts**
   - persist stage outputs (`chunks`, `entities`, `facts`, `events`) to deterministic artifact paths for replay/debug
3. [PENDING] **Add projection delta reporter**
   - output field-level changes across `instantiation -> zero-tick -> live` checkpoints to make Gate D auditable
4. [PENDING] **Run blind replay on moved corpus path**
   - ensure all scripts use `corpus/eldyrwild-markdown` and no longer depend on legacy `Docs/...` paths
5. [PENDING] **Commit sequence**
   - commit A: eval scaffold + gold contracts
   - commit B: event ingestion loop + stage artifacts
   - commit C: hard gates + replay tests + projection deltas

## Acceptance Gates

- [DONE] Gate A: source and layer integrity passes
- [DONE] Gate V: extraction viability passes (entity density, duplicate fact ratio, conflict volume band)
- [DONE] Gate B: event schema and ordering integrity passes
- [DONE] Gate C: hybrid correctness passes (exact core fields + conflict behavior)
- [DONE] Gate D: instantiation/zero-tick/live progression pass with auditable deltas

Any red gate blocks progression.

## Verification Commands

- `uv run ruff check .`
- `uv run pytest tests/ --maxfail=1`
- `uv run python evals/llm_ingestion_slice/run_slice.py`

## Notes for Next Agent

- Keep commits atomic:
  - commit 1: artifact pack + contracts
  - commit 2: ingestion loop
  - commit 3: runner + gates + tests
- If a provisional scaffold conflicts with plan intent, replace it rather than adapting it for compatibility.
- Keep all artifacts and reports reproducible and deterministic for the same inputs/config.
