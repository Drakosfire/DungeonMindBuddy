# HANDOFF — DOGFOOD-CONTINUITY: Stage 4C trustworthy extraction experiment comparison

**Created:** 2026-09-12  
**Status:** IMPLEMENTED — REVIEW READY
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4c-experiment-comparability-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / Extraction Lab comparison evidence  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `a90f5e81355952d80ad5dba24bd4d27d5eedd930` (main after PR #704 merge)  
**Branch:** `dogfood-continuity/stage4c-experiment-comparability-v1`  
**PR title:** `DOGFOOD-CONTINUITY: make extraction variants comparably measurable`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Benchmark authority: [`Docs/Design/DESIGN-benchmark-philosophy-and-goals.md`](../Design/DESIGN-benchmark-philosophy-and-goals.md).

## §0 Program correction from PR #704 dogfood

PR #704 proved that better presentation alone cannot pass the Stage 4 WOW gate when the available campaign memory is incomplete or poorly accumulated. The interaction grammar is worth keeping; the next critical path is evidence quality.

The broader ingestion-improvement program is accepted with these corrections:

1. **Grow from Extraction Lab rather than creating a parallel experiment framework.** Extraction Lab already owns run manifests, pipeline fingerprints, anchor scoring, promoted baselines, regression thresholds, and failure buckets.
2. **Separate experimentation, APP-STATE source adoption, and World publication.** They are three different authority boundaries. An experiment never writes live World or APP-STATE.
3. **Do not equate structural validity with semantic publication approval.** Exact digest-bound source adoption may later be automated under the existing APP-STATE contract. New World facts, aliases, identity merges, and relationships require an explicit publication policy/quarantine boundary.
4. **Do not optimize one composite score.** Correctness gates and failure transitions come first. Cost, latency, counts, and taxonomy are explicit constraints/tradeoffs. Human product witnesses remain separate evidence.
5. **Do not clone live World/APP-STATE in the first scaffold.** Early extraction experiments can and should run entirely against disposable FactStore/output roots. Authority clones belong to later rehearsal/publication phases.
6. **Holdouts are a protocol, not magic.** Existing gold is finite. Later orchestration must identify development vs frozen validation cohorts, preserve untouched validation evidence, and avoid pretending a small holdout has statistical power it does not have.
7. **Repetitions must state cache policy.** Reusing deterministic caches can make stochastic variance appear to be zero. Later repeated-run orchestration must record whether model caches are shared, isolated, or deliberately cold.

### Program horizon (not this PR's lease)

```text
P0a  trustworthy cross-contract comparison          ← THIS PR
P0b  isolated experiment runner + repetitions + execution telemetry
P1   characterize current baseline and failure classes
P2   bounded ablation PRs, one change at a time
P3   candidate qualification + frozen validation + qualitative probes
P4   full-corpus rehearsal into disposable authorities
P5   explicit durable source adoption / governed World publication operator
P6   final baseline-vs-final analysis and remaining product gaps
```

The Stage 4 product witness remains concrete: accumulated campaign memory should explain objects such as Brin, Orik/Orric, Karsemine, and Mireward from admitted corpus evidence rather than merely returning names, ingestion metadata, or one arbitrary current-session edge.

---

## §1 Mission and merge-ready invariant

**Mission:** An operator can compare one baseline Extraction Lab run bundle with one candidate run bundle produced from the **same benchmark corpus and same human-authored gold intent**, even when prompt/model/taxonomy/pipeline contracts intentionally differ, and receive a deterministic fail-closed comparison artifact showing what improved, regressed, or changed without mutating any store, baseline, APP-STATE, or World authority.

**Merge-ready invariant:** A comparison is labeled `comparable=true` only when both run bundles prove the same benchmark surface, the same path-independent corpus content identity, and the same surface-filtered gold intent. Pipeline-contract differences are expected experimental variables and must be enumerated rather than rejected. Any benchmark-identity ambiguity or mismatch produces `comparable=false`, explicit reasons, and **no quality ranking/acceptance claim**.

### Why this is the first experimental slice

The existing production regression rule correctly says incompatible pipeline contracts are drift diagnostics rather than direct regressions. An A/B experiment, however, intentionally changes prompt/model/taxonomy/config. Before automating variant execution, the repository needs a trustworthy evidence boundary that answers:

> Are these two runs evaluating the same human task and source cohort, and if so exactly which anchors improved or regressed while the pipeline changed?

Without that boundary, a sophisticated experiment runner would automate untrustworthy comparisons.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. Run-bundle stamping, comparison eligibility, metric deltas, and anchor transitions all serve one comparability contract. |
| Most likely adversarial sequence | Baseline and candidate live in different worktrees with identical corpus bytes but different absolute paths; candidate changes model/prompt; comparison must remain eligible and enumerate the intended pipeline differences. |
| Will §7 detect that failure? | Yes. A path-independence test must build identical source cohorts beneath different temp roots and prove identical benchmark corpus fingerprints. |
| Easiest owning boundary to under-test | Gold identity. Counts/path names are insufficient; semantic changes to current-surface anchors must invalidate comparison while unrelated-surface edits must not. |
| Fact that forces stop/split | Reliable comparison requires executing LLM ingestion, managing repetitions/caches, mutating MODEL_POLICY, publishing World, or inventing a new gold rubric. Those are successors. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Stage 4 WOW dogfood from PR #704; `DESIGN-benchmark-philosophy-and-goals.md`; current `extraction_lab/` run-manifest/contract/anchor model. |
| Base revision | `a90f5e81355952d80ad5dba24bd4d27d5eedd930` |
| Completed predecessor | PR #704 merged at `a90f5e81355952d80ad5dba24bd4d27d5eedd930`, head `02b2529176703b3f8b69ad9fcb594f401c1c5f6b`. Its product-owner dogfood disposition remained **WOW HOLD**: presentation improved, but representative source availability and accumulated World truth are insufficient. |
| Exact inputs consumed | Existing Extraction Lab run directories: `run_manifest.json`, `pipeline_contract.json`, `aggregate_metrics.json`, `entity_results.json`, `fact_results.json`; the entity/fact anchor sets already loaded by `run_extraction_lab.py`. |
| Named successor | P0b isolated experiment runner: frozen cohort spec, baseline/candidate execution, repetitions, explicit cache policy, batch cost/latency capture, and event-driven completion. |
| What remains false | No prompt tuning loop; no automatic experiment proposal/ranking; no development/holdout scheduler; no new precision/temporal rubric; no corpus re-ingestion; no source adoption; no World publication; Stage 4 WOW gate remains HOLD. |
| Explicit non-goals | No writes to `54330`/`54331`; no MODEL_POLICY mutation; no OpenAI calls; no batch job submission; no baseline promotion; no threshold change; no gold edits; no alias/Orik repair; no C2S23 adoption; no UI changes. |
| Branch / isolated checkout | `dogfood-continuity/stage4c-experiment-comparability-v1` from exact base above; worker uses isolated worktree/equivalent. |
| Parallel lanes / collision hotspots | `extraction_lab/**` and `tests/extraction_lab/**` are collision paths. Before implementation, re-check open PRs/worktrees; any active Extraction Lab lane requires serialization/split. |
| Runtime/state ownership | Offline/local artifact comparison only. Tests use temp dirs/committed fixtures. `out/extraction_lab/**` may be read during optional smoke but is not authority and is not committed. |
| Backward-looking state-authority sync | Record PR #704 as merged with human WOW HOLD in `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4b-recap-world-reference-glance-v1.md`, `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`, and `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`. Set this comparison slice as current without claiming Stage 4 complete. |

### Existing machinery to preserve

Do not duplicate these existing responsibilities:

- `extraction_lab/run_extraction_lab.py` already scores prebuilt stores and emits recommendation-grade run bundles.
- `extraction_lab/pipeline_contract.py` already fingerprints prompt IDs, models, taxonomy, heuristics, store, and corpus inputs.
- `extraction_lab/assert_regression.py` remains the same-contract production regression gate.
- `extraction_lab/promote_baseline.py` remains explicit human baseline-promotion authority.
- `tools/batch_ingest_corpus.py` remains the corpus execution/cost/resume mechanism; this PR does not wrap or change it.

The new comparator is complementary: **cross-contract experimental comparison**, not replacement regression policy.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| New Extraction Lab run | Manifest records surface, counts, store path, and pipeline contract, but not a durable surface-filtered gold identity. | Run bundle records a benchmark contract sufficient to prove corpus + current-surface gold identity independent of checkout path. | Yes | `run_extraction_lab` / benchmark-contract helper |
| Same corpus in different worktrees | Existing corpus hash may include resolved filesystem paths. | Benchmark corpus identity is based on stable logical locators + bytes (or an equally path-independent deterministic representation). Same cohort under different checkout roots hashes identically. | Yes | benchmark-contract helper |
| Gold file formatting/unrelated surface changes | Raw file bytes/counts are not adequate intent identity. | Fingerprint canonicalized anchors **filtered to the run surface**. Formatting/order changes or unrelated-surface anchors do not invalidate; semantic changes to evaluated anchors do. | Yes | benchmark-contract helper |
| Baseline vs candidate with changed model/prompt/taxonomy | Existing same-contract regression semantics do not treat this as ordinary regression. | Comparator allows intentional pipeline differences, lists them explicitly, and compares benchmark outcomes because benchmark identity is unchanged. | Yes | comparator |
| Corpus/gold/surface mismatch | Could be compared manually by mistake. | Fail closed: `comparable=false`, reasons emitted, no “winner”, no promotion recommendation. | Yes | comparator |
| Comparable pair | Operator manually inspects two reports. | Emit machine-readable and human-readable deltas plus anchor-level pass/fail transitions/failure-bucket changes. | Yes | comparator/report |
| Legacy run missing new benchmark identity | Ambiguous. | Fail closed with an explicit rerun-required reason; never infer equality from paths/counts. | Yes | comparator |

### Required adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| identical corpus copied to temp root A and B → same gold → different model IDs | comparator says comparable; corpus/gold fingerprints equal; pipeline diff lists model change | unit + CLI fixture test |
| same run surface → candidate gold anchor meaning changed | not comparable; reason identifies gold-intent mismatch | benchmark-contract test |
| unrelated `working_set` anchor changes while comparing `core_extraction` | still comparable for core surface | benchmark-contract test |
| candidate corpus byte changes but path/name remains | not comparable; corpus mismatch | benchmark-contract test |
| baseline anchor passes / candidate fails with new failure bucket | report records regression transition with anchor ID and before/after buckets | comparator test |
| candidate improves recall but total entity count explodes | report exposes both deltas; no composite “winner” hides tradeoff | comparator fixture |

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/benchmark_contract.py` | Compute deterministic path-independent corpus identity and canonical surface-filtered gold identity for experiment comparability. |
| Modify | `extraction_lab/run_extraction_lab.py` | Stamp recommendation-grade run bundles with the benchmark contract using the exact corpus/gold actually scored. |
| Modify | `extraction_lab/run_manifest.py` | Persist benchmark-contract identity separately from pipeline-contract identity. |
| Create | `extraction_lab/compare_experiment_runs.py` | Pairwise fail-closed comparator + CLI; emit comparison JSON and Markdown report without mutation/promotion. |
| Modify | `tests/extraction_lab/test_run_extraction_lab.py` | Prove run bundles contain correct benchmark identity. |
| Create | `tests/extraction_lab/test_benchmark_contract.py` | Path independence, surface-filtered gold semantics, corpus/gold mismatch proofs. |
| Create | `tests/extraction_lab/test_compare_experiment_runs.py` | Cross-contract comparable case, fail-closed mismatches, metric/failure transitions, no-winner semantics. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4b-recap-world-reference-glance-v1.md` | Backward-looking #704 merge + human WOW HOLD truth only. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Move current forcing function from merged #704 presentation slice to Stage 4C evidence-quality comparability. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record #704 merged/WOW HOLD and route Stage 4 critical path through evidence quality; do not mark Stage 4 done. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4c-experiment-comparability-v1.md` | Implementation evidence/review handback only. |

**Bounded discovery exception:**

```text
Directory: tests/fixtures/extraction_lab/
Maximum additional paths: 4
Allowed path kinds: tiny deterministic comparator/run-bundle fixtures only
Decision rule: use fixtures only when temp-generated payloads would obscure the contract being proved
```

A production path outside this lease is a stop report. In particular, do not modify ingestion prompts, taxonomy, batch execution, publication code, or gold data to make comparator tests pass.

---

## §5 Explicitly out of scope / collision boundary

| Path / area | Why this PR must not touch or claim it |
|---|---|
| `tools/batch_ingest_corpus.py` | Execution orchestration/cost telemetry is P0b. Comparator consumes completed run bundles only. |
| `src/ingestion/**` prompts/extractors | Tuning starts only after trustworthy comparison exists. |
| `MODEL_POLICY.json` | No global policy mutation in comparison infrastructure. |
| `evals/**/gold/**` | Gold intent is input authority; this PR fingerprints it but does not rewrite it. |
| `extraction_lab/regression_thresholds.json` | Existing same-contract gates remain unchanged. |
| `extraction_lab/promote_baseline.py` | Baseline promotion remains explicit and separate. |
| APP-STATE adoption/import code | Source adoption is later and digest-bound. |
| DungeonMind prepare/confirm/publication code | World publication is later governed work; structural extraction pass is not semantic acceptance. |
| UI / graph projection | The next evidence program is fixing what the UI has to show, not adding another presentation workaround. |

---

## §6 Implementation contract

```text
Input:
  baseline Extraction Lab run directory
  candidate Extraction Lab run directory

Each run must contain:
  run_manifest.json
  pipeline_contract.json
  aggregate_metrics.json
  entity_results.json
  fact_results.json
  benchmark contract stamped by current Extraction Lab

Benchmark identity:
  surface
  path-independent corpus content fingerprint
  canonical fingerprint of entity anchors filtered to surface
  canonical fingerprint of fact anchors filtered to surface

Pipeline identity:
  preserved separately; differences are experimental variables

Output:
  comparison.json
  report.md

Invariant:
  same benchmark intent/source cohort is required;
  different pipeline contract is allowed and enumerated;
  ambiguous benchmark identity fails closed.

Mutation:
  none — no stores, baselines, gold, APP-STATE, World, prompts, or policy files change.
```

### Benchmark fingerprint rules

**Corpus identity** must not depend on absolute checkout/worktree paths. Prefer a deterministic sorted sequence like:

```text
logical_source_locator + NUL + sha256(source_bytes)
```

where the logical locator is relative to the explicit corpus root / stable ingest locator. If the tool cannot derive a stable locator, it must record benchmark corpus identity as unavailable rather than silently hashing machine-local absolute paths.

**Gold identity** must fingerprint the canonical parsed anchor content used for the selected `surface`, not raw file bytes. Therefore:

- JSON formatting/key order changes do not create a new intent identity;
- anchors for another surface do not invalidate this surface;
- changing expected names/classes/attributes/keywords/minimums for an evaluated anchor does invalidate comparison.

### Comparison artifact minimum shape

`comparison.json` must include at least:

```text
schema/version
baseline run_id
candidate run_id
comparable: bool
non_comparable_reasons[]
benchmark_identity baseline/candidate
pipeline_contract_differences[]
metric_deltas:
  entity_anchor_recall
  fact_anchor_recall
  unresolved_core_anchors
  total_entity_count
  total_fact_count
anchor_transitions:
  entity improved/regressed/unchanged
  fact improved/regressed/unchanged
  before/after fail_bucket where relevant
```

The Markdown report should make regressions and improved anchors readable, but it must not output a single scalar score, `winner`, `READY`, or promotion recommendation.

### Compatibility rule

Current run bundles created before this benchmark contract are **legacy-unqualified for cross-contract comparison**. The comparator should report a clear rerun-required reason. Do not infer gold equality from anchor counts or corpus equality from store paths.

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Same corpus is path-independent | benchmark contract | adversarial unit | identical temp corpus under two roots | equal corpus fingerprint | absolute path changes identity |
| Current-surface gold intent is canonical | benchmark contract | adversarial unit | reorder/format JSON + modify unrelated surface | same evaluated-surface fingerprint | irrelevant edit breaks comparison |
| Evaluated gold semantic change blocks comparison | benchmark contract | negative unit | alter expected entity/fact anchor meaning | different fingerprint / comparator fail-closed | comparator remains eligible |
| Intentional pipeline changes are allowed | comparator | contract unit | same benchmark, model/prompt/taxonomy diff | `comparable=true`, differences listed | comparator rejects merely because pipeline differs |
| Corpus mismatch fails closed | comparator | negative unit | one source byte changed | `comparable=false`, no ranking | deltas presented as qualified result |
| Legacy/missing benchmark identity fails closed | comparator | compatibility unit | old-style run manifest | rerun-required reason | guessed equality |
| Anchor regressions are explanatory | comparator | regression unit | pass→fail / fail→pass fixtures | anchor IDs + before/after buckets | only aggregate delta emitted |
| No hidden weighted winner | comparator/report | contract unit | recall rises while counts balloon | both deltas visible; no winner/READY field | composite ranking appears |
| Existing Extraction Lab still works | package | regression | full `tests/extraction_lab/` | green | existing regression/promotion semantics break |

Exact verification:

```bash
uv run pytest tests/extraction_lab/ -q
uv run python -m extraction_lab.run_extraction_lab \
  --surface core_extraction \
  --store tests/fixtures/extraction_lab/sample_store \
  --out-dir <TEMP_OUT> \
  --run-id baseline_fixture \
  --corpus-source-root <FIXTURE_OR_TEMP_CORPUS_ROOT>

uv run python -m extraction_lab.compare_experiment_runs \
  --baseline <BASELINE_RUN_DIR> \
  --candidate <CANDIDATE_RUN_DIR> \
  --out-dir <TEMP_COMPARISON_DIR>

git diff --check
git diff --name-only a90f5e81355952d80ad5dba24bd4d27d5eedd930...HEAD
```

### Minimal live/dogfood proof

No paid LLM run is required for this PR. A deterministic fixture pair must prove:

```text
same corpus/gold + changed pipeline contract → comparable
changed corpus or evaluated gold → not comparable
report explains specific anchor transitions
comparison performs no promotion or store mutation
```

If implementation cannot prove useful comparison without running ingestion/model calls, stop and re-brief P0b rather than absorbing orchestration into this PR.

---

## §8 Required review handback

### Implementation handback

- `benchmark_contract_v1` is stamped both in `run_manifest.json` and as `benchmark_contract.json`. It keeps `surface`, path-independent corpus identity, and surface-filtered semantic gold identity separate from the existing pipeline contract.
- Corpus identity hashes sorted logical paths relative to the explicit corpus root plus source-byte hashes. Missing roots, missing sources, or sources outside that root make identity unavailable instead of falling back to absolute paths.
- Gold identity canonicalizes only anchors for the evaluated surface, including set-like anchor fields; JSON formatting, anchor ordering, and unrelated-surface changes do not create false drift, while evaluated semantic changes do.
- `compare_experiment_runs` accepts changed pipeline contracts and enumerates field-level differences. It emits metric deltas plus entity/fact improved, regressed, and unchanged transitions with before/after failure buckets.
- Legacy, unsupported, unavailable, divergent-stamp, surface, corpus, and gold identities fail closed. Non-comparable artifacts omit metric deltas and anchor transitions; neither JSON nor Markdown emits a winner, READY state, composite score, or promotion recommendation.
- Full Extraction Lab regression: `32 passed`. Scoped Ruff checks and `git diff --check` pass.
- CLI smoke emitted two independently stamped runs with different entity/fact model IDs, then produced `comparable=true` and enumerated both model differences without any LLM, store, baseline, APP-STATE, or World mutation.
- Changed paths remain within §4; the bounded fixture exception was not used. P0b execution orchestration, repetitions, cache policy, and cost/latency capture remain false.
- Backward-looking authority now records PR #704 merged at `a90f5e81355952d80ad5dba24bd4d27d5eedd930`, accepted head `02b2529176703b3f8b69ad9fcb594f401c1c5f6b`, 1 formal review cycle, with the human Stage 4 WOW gate still HOLD.

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. exact benchmark-contract schema and compatibility behavior;
4. proof that corpus identity survives different absolute roots;
5. proof that gold identity is surface-filtered semantic intent rather than raw file bytes/counts;
6. comparable cross-contract fixture and fail-closed mismatch fixtures;
7. pipeline differences emitted for the comparable case;
8. metric and anchor-transition evidence;
9. full Extraction Lab regression result;
10. changed paths vs §4 and any bounded-discovery use;
11. backward-looking #704 merge/WOW-HOLD authority sync;
12. named P0b orchestration successor remains false.

---

## §9 Acceptance rubric

- [x] Exactly one capability is delivered: trustworthy pairwise cross-contract experiment comparison.
- [x] Comparison eligibility is governed by benchmark identity, not pipeline identity.
- [x] Benchmark corpus fingerprint is independent of absolute checkout/worktree path.
- [x] Gold fingerprint represents canonical anchors filtered to the evaluated surface.
- [x] Pipeline prompt/model/taxonomy/config differences remain visible experimental variables.
- [x] Corpus/gold/surface ambiguity fails closed and produces no winner/promotion claim.
- [x] Comparable reports include aggregate deltas and anchor-level improved/regressed transitions.
- [x] No composite winner score or hidden acceptance policy is introduced.
- [x] Existing same-contract regression and explicit baseline-promotion semantics remain unchanged.
- [x] No LLM execution, gold editing, source adoption, APP-STATE mutation, or World publication is added.
- [x] PR #704 is synchronized as merged with the Stage 4 WOW gate still HOLD.
- [x] P0b orchestration/repetition/cost-latency successor remains unimplemented.

## Stop conditions

Stop and report instead of expanding if:

- comparison requires changing extraction/gold semantics rather than measuring them;
- stable corpus identity cannot be computed without machine-local path dependence;
- current run artifacts are insufficient and fixing them requires ingestion execution changes outside §4;
- a second public workflow (variant execution, holdout scheduler, baseline promotion, publication) appears necessary;
- any live APP-STATE/World mutation is proposed;
- another active lane owns `extraction_lab/**` or overlapping tests;
- the implementation attempts to derive a single optimization score/winner that was not authorized.

Report:

```text
Stop condition:
Invariant clause affected:
Why P0a cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/re-brief:
State-authority update needed:
```
