# HANDOFF — DOGFOOD-CONTINUITY: Stage 4D isolated extraction experiment pair

**Created:** 2026-09-12  
**Status:** DESIGN READY — NOT IMPLEMENTED  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4d-isolated-experiment-pair-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / Extraction Lab bounded experiment execution  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `29c50b985091f590d2d6212b10cd79dcc8be5288` (main after PR #705 merge)  
**Branch:** `dogfood-continuity/stage4d-isolated-experiment-pair-v1`  
**PR title:** `DOGFOOD-CONTINUITY: run one isolated extraction experiment pair`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). Benchmark authority: [`Docs/Design/DESIGN-benchmark-philosophy-and-goals.md`](../Design/DESIGN-benchmark-philosophy-and-goals.md). Predecessor: [`HANDOFF-DOGFOOD-CONTINUITY-stage4c-experiment-comparability-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-stage4c-experiment-comparability-v1.md).

## §0 Program position

PR #705 / Stage 4C established the measurement boundary: two Extraction Lab runs may be compared across intentionally different pipeline contracts only when they prove the same exact source cohort and the same surface-filtered human gold intent. PR #705 merged at `29c50b985091f590d2d6212b10cd79dcc8be5288`, accepted head `e0b8dd9b363cef3980055ef73c8634a67b2fa9e8`, after 2 review cycles.

The experiment program is now:

```text
P0a  trustworthy cross-contract comparison          DONE — PR #705
P0b1 one bounded isolated baseline/candidate pair   ← THIS PR
P0b2 repetitions + aggregation + resume/budget + async lifecycle
P1   characterize current baseline and failure classes
P2   bounded ablation PRs, one change at a time
P3   frozen validation + qualitative qualification
P4   full-corpus rehearsal into disposable authorities
P5   explicit durable source adoption / governed World publication
P6   baseline-vs-final analysis and remaining product gaps
```

This slice exists to get the repository to a **real smoke test immediately after merge**, not to build the final experiment scheduler.

### Design correction: smoke-sized first

P0b1 deliberately supports only:

- exactly two variants: `baseline` and `candidate`;
- one repetition of each;
- at most **3 exact Markdown source files**;
- synchronous realtime ingestion only;
- fresh disposable FactStores;
- isolated per-store extraction caches;
- no resume;
- no OpenAI Batch API lifecycle;
- no automatic winner/acceptance decision.

A larger cohort, repeated runs, variance, holdouts, budget scheduling, and asynchronous completion are P0b2 or later.

---

## §1 Mission and merge-ready invariant

**Mission:** An operator can take one frozen two-variant extraction experiment manifest, execute exactly one baseline run and one candidate run against the same small exact source cohort in isolated disposable stores, score both through Extraction Lab, compare them through the PR #705 comparator, and receive one truthful experiment receipt so that a real paid smoke can be attempted immediately after merge without touching live APP-STATE or World authority.

**Merge-ready invariant:** The runner executes **only** the manifest-pinned repository revision, exact source locators, gold inputs, and allowed per-variant execution parameters; baseline and candidate use fresh non-overlapping stores/caches; observed model/cost/runtime evidence is recorded from the actual execution; and the final receipt is `completed` only when both variants produced benchmark-qualified Extraction Lab bundles and PR #705 returned `comparable=true`. Any preflight mismatch or partial execution produces a terminal non-success receipt or no execution at all—never a misleading completed experiment.

### Safety stance

The command is **inert by default**. Normal invocation performs preflight / normalized-plan output only. Paid model execution requires an explicit `--execute` flag.

This PR does not mutate model policy. `MODEL_POLICY.json` is an input authority: its exact bytes/fingerprint are recorded before execution and must remain unchanged through both variants.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Preflight, two isolated executions, scoring, comparison, and receipt are all governed by “execute exactly the frozen pair or fail truthfully.” |
| Most likely adversarial sequence | baseline succeeds → candidate fails or policy/source changes → stale baseline artifacts exist → caller mistakes pair for complete. |
| Will §7 detect that failure? | Yes. Failure-injection tests must prove the receipt remains non-success, comparison is not claimed, and partial outputs stay inspectable. |
| Easiest owning boundary to under-test | Actual-execution provenance: the models/cost/cache behavior must come from store logs/report, not merely from what the manifest requested. |
| Fact that forces stop/split | Supporting repetitions, resume, shared caches, OpenAI Batch polling, prompt/model-policy mutation, holdout scheduling, or a larger cohort is P0b2/later. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Stage 4 WOW HOLD from PR #704; Stage 4C / PR #705 trustworthy comparability; benchmark philosophy. |
| Base revision | `29c50b985091f590d2d6212b10cd79dcc8be5288` |
| Predecessor contract | PR #705 cross-contract comparator and benchmark contract. Do not weaken its fail-closed semantics. |
| Existing execution seam | `tools/batch_ingest_corpus.py` already supports exact `--paths-file`, isolated `--store`, batch-size control, per-run ingest artifacts, `batch_ingest_summary.json`, `batch_report.json`, model-call logs, and cost/runtime telemetry. |
| Existing cache behavior | Interactive ingest uses `<store>/.cache`; therefore fresh per-variant stores naturally provide isolated caches. P0b1 must preserve this instead of adding cache sharing. |
| Existing model authority | Runtime model selection is Buddy-root `MODEL_POLICY.json` via `src.model_policy`. P0b1 records and verifies it; it does not edit it or use batch tool policy-mutation flags. |
| Exact input consumed | One JSON pair-experiment manifest; repo HEAD; Buddy-root `MODEL_POLICY.json`; exact corpus files; existing entity/fact gold; batch-ingest outputs; Extraction Lab; PR #705 comparator. |
| Named successor | P0b2 repeated experiment qualification: N repetitions, experiment-level aggregation, explicit cache modes, resume, budget ceilings, failure accounting, OpenAI Batch/event-driven completion. |
| What remains false | No repeated-run statistics; no scheduler; no async batch lifecycle; no model/prompt tuning; no automatic winner; no source adoption; no World publication; no Stage 4 WOW pass. |
| Explicit non-goals | No writes to APP-STATE or DungeonMind; no baseline promotion; no gold edits; no `MODEL_POLICY.json` mutation; no prompt/taxonomy edits; no C2S23 source adoption; no UI work. |
| Branch / isolated checkout | `dogfood-continuity/stage4d-isolated-experiment-pair-v1` from exact base above. Implementation should use isolated worktree/equivalent. |
| Parallel lanes / collision hotspots | `extraction_lab/**`, `tests/extraction_lab/**`, and `tools/batch_ingest_corpus.py` are collision-sensitive. This design expects no production change to the batch tool; if that becomes necessary, stop and re-brief. |
| Runtime/state ownership | New experiment outputs only beneath operator-selected disposable output root. No shared store. No live app runtime. |
| State-authority sync after implementation | Backward-looking update Stage 4C as merged/PASS; set Stage 4D/P0b1 current in the Stage 4C handoff, steward anchor, demo-ready roadmap, and this handoff. Stage 4 WOW remains HOLD. |

### Existing machinery to reuse, not duplicate

Do not rewrite these:

- `tools/batch_ingest_corpus.py` — exact-source execution and telemetry;
- `extraction_lab.run_extraction_lab` — score one completed store and stamp benchmark/pipeline contracts;
- `extraction_lab.compare_experiment_runs` — cross-contract pair comparison;
- `src.model_policy` — Buddy-owned model policy authority.

P0b1 is orchestration around those boundaries.

---

## §3 Public operator contract

### Manifest v1

The runner accepts one JSON manifest with this semantic shape:

```json
{
  "schema": "dmb_extraction_pair_experiment_v1",
  "experiment_id": "stage4d-smoke-s23-batchsize",
  "repository_sha": "<EXACT_HEAD_TO_EXECUTE>",
  "surface": "core_extraction",
  "corpus_root": "corpus/eldyrwild-markdown",
  "sources": [
    "Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate Battle.md"
  ],
  "entity_anchors": "evals/mirathorn_vertical_slice/gold/entity_anchors.json",
  "fact_anchors": "evals/mirathorn_vertical_slice/gold/fact_anchors.json",
  "execution": {
    "mode": "realtime",
    "cache_policy": "isolated",
    "repetitions": 1
  },
  "variants": {
    "baseline": {"batch_size": 5},
    "candidate": {"batch_size": 4}
  }
}
```

The example above is a **post-merge smoke shape**, not a committed run authorization. The live smoke manifest must pin the actual merged implementation SHA.

### P0b1 schema rules

- `schema` must equal `dmb_extraction_pair_experiment_v1`.
- `repository_sha` is required and must equal current `git rev-parse HEAD` before any model call.
- Execute mode requires a clean git worktree; uncommitted source/code changes invalidate the pin.
- `surface` is one Extraction Lab surface.
- `corpus_root` must resolve inside the repository.
- `sources` contains 1–3 unique `.md` paths relative to that corpus root.
- Every source must exist and must not live under managed `_dungeonbuddy` storage.
- Entity/fact gold paths must exist inside the repository.
- `execution.mode` is exactly `realtime` in P0b1.
- `execution.cache_policy` is exactly `isolated` in P0b1.
- `execution.repetitions` is exactly `1`.
- Exactly two variants exist, named `baseline` and `candidate`.
- P0b1 variant config allows only `batch_size` as an intentional execution difference. Reject unknown variant keys.
- `batch_size` must be a positive bounded integer; recommended test range `1..32`.

### CLI shape

Preferred entrypoint:

```bash
uv run python -m extraction_lab.run_pair_experiment \
  --manifest <PAIR_MANIFEST.json> \
  --out-dir <FRESH_OUTPUT_ROOT>
```

Default behavior:

```text
validate manifest
validate repository/source/gold/model-policy preconditions
print normalized execution plan
perform zero model calls
create no FactStore
exit 0 when smoke is executable
```

Paid execution requires:

```bash
uv run python -m extraction_lab.run_pair_experiment \
  --manifest <PAIR_MANIFEST.json> \
  --out-dir <FRESH_OUTPUT_ROOT> \
  --execute
```

Do not add an implicit environment switch that turns a dry run into execution.

---

## §4 Execution semantics

### Preflight — before output/store creation or model calls

The runner must verify:

1. exact repository SHA matches manifest;
2. worktree is clean for `--execute`;
3. source count/path/type/uniqueness constraints;
4. source bytes exist under exact corpus root;
5. gold paths exist and parse through current anchor loaders;
6. output root is absent (or empty only if implementation can prove no stale experiment artifacts can be confused with this run; simplest acceptable contract is **must not exist**);
7. Buddy-root `MODEL_POLICY.json` exists, parses, and its SHA-256 is recorded;
8. `structured_generation` resolves to a concrete current model id;
9. `OPENAI_API_KEY` is present for `--execute` without ever logging the secret.

Any preflight failure performs **zero model calls**.

### Variant execution

For each variant, sequentially baseline then candidate:

```text
<experiment-root>/<variant>/
  store/                 fresh FactStore + store-local .cache
  extraction_lab/        recommendation-grade Extraction Lab run bundle
  stdout.log             batch execution transcript if implementation captures it
```

The runner should execute the existing batch CLI as an argv subprocess, not shell text, using:

```text
--store <variant/store>
--corpus-root <exact corpus root>
--paths-file <generated exact cohort file>
--batch-size <variant batch_size>
```

P0b1 must **not** pass:

```text
--resume
--force
--use-batch-api
--enforce-cheap-pass
--auto-escalate
```

Fresh stores make `--force` unnecessary and preserve a simple one-pass smoke contract.

### Model-policy and observed-model integrity

Before baseline, after baseline, and after candidate:

- recompute Buddy-root `MODEL_POLICY.json` SHA-256;
- if it changed, stop with `model_policy_changed_during_experiment`;
- never rewrite it.

For each variant, actual model identity used for Extraction Lab stamping must be derived from that variant's `store/logs/model_calls.jsonl`, not copied from the manifest. P0b1 may fail closed if a stage used an ambiguous unsupported model set; do not silently choose a “dominant” model for benchmark identity.

At minimum, record observed entity-extraction model id(s) and fact-extraction model id(s). If current normal execution yields exactly one model per stage, pass those exact ids into `run_extraction_lab` as `entity_model` / `fact_model`.

### Scoring and comparison

Only after one variant's batch execution completed successfully:

- run Extraction Lab against that exact store;
- pass manifest surface, gold paths, observed entity/fact model ids, exact variant batch size, exact repository SHA as `pipeline_code_sha`, and exact corpus root;
- require the resulting benchmark contract to prove the source cohort (PR #705 semantics).

Only after **both** variants have qualified run bundles:

- call `compare_experiment_runs` / `write_comparison` from PR #705;
- require `comparable=true` for experiment status `completed`.

`comparable=true` means the experiment is measurable. It does **not** mean candidate is better.

---

## §5 Experiment receipt

Create one durable experiment-local receipt:

```text
<experiment-root>/experiment_receipt.json
```

Minimum semantic content:

```text
schema: dmb_extraction_pair_receipt_v1
experiment_id
manifest_sha256
status: running | failed | completed
started_at / completed_at
repository_sha
worktree_clean_at_start
corpus_root
source locators + source byte sha256
surface
entity/fact gold paths + byte sha256
model_policy_path + model_policy_sha256
cache_policy: isolated
execution_mode: realtime
variants:
  baseline:
    status
    batch_size
    store_path
    ingest summary/report paths
    observed entity/fact model ids
    API/token/cache/cost/runtime telemetry copied or referenced from batch_report
    Extraction Lab run path / benchmark fingerprint / pipeline contract
    failure reason if any
  candidate:
    same
comparison:
  status
  comparison artifact path
  comparable
failure:
  stage
  reason
```

The receipt is descriptive evidence, not a recommendation. It must not contain `winner`, `READY`, automatic promotion, or “accepted candidate.”

### Partial failure behavior

The receipt should be written/updated atomically enough that an interrupted experiment does not leave `completed` behind.

Required examples:

| Failure | Required outcome |
|---|---|
| preflight mismatch | zero model calls; no completed receipt; clear CLI error |
| baseline execution fails | receipt `failed`, baseline failure captured, candidate not started |
| baseline scores but candidate execution fails | receipt `failed`, baseline artifacts preserved, no pair comparison claimed |
| candidate scores but benchmark comparison is non-comparable | receipt `failed`, comparison path/reasons preserved, no quality conclusion |
| policy changes between variants | receipt `failed`; no comparison; preserve completed baseline artifacts |
| both qualify and comparator says comparable | receipt `completed`; no winner claim |

### Replay rule

P0b1 does **not** resume a partial experiment.

- `--execute` requires a fresh experiment output root.
- A retry uses a new fresh root / experiment id or deliberate operator cleanup.
- Do not silently reuse variant stores or caches.

Resume/idempotent continuation is P0b2.

---

## §6 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/pair_experiment_manifest.py` | Parse/validate the bounded P0b1 manifest and normalize exact pinned inputs. |
| Create | `extraction_lab/run_pair_experiment.py` | Dry-run/execute CLI, preflight, isolated variant orchestration, scoring, comparison, and truthful receipt. |
| Create | `tests/extraction_lab/test_pair_experiment_manifest.py` | Manifest/path/revision/source-count/unknown-field fail-closed tests. |
| Create | `tests/extraction_lab/test_run_pair_experiment.py` | Command construction, isolation, partial-failure, policy-change, observed-model, scoring/comparison, and receipt tests with subprocess/model execution faked. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4c-experiment-comparability-v1.md` | Backward-looking PR #705 merge/PASS + successor truth only. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Set Stage 4D/P0b1 current after implementation; Stage 4 remains NOT DONE. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Record PR #705 merged and route evidence lane to bounded live smoke; no Stage 4 completion. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4d-isolated-experiment-pair-v1.md` | Implementation/review handback and exact evidence. |

**Expected no-change predecessor paths:**

- `tools/batch_ingest_corpus.py`
- `extraction_lab/run_extraction_lab.py`
- `extraction_lab/compare_experiment_runs.py`
- `extraction_lab/benchmark_contract.py`
- `src/model_policy.py`
- `MODEL_POLICY.json`

If P0b1 requires changing any of those production/predecessor contracts rather than consuming them, stop and explain why the design seam was insufficient.

**Bounded discovery exception:**

```text
Directory: tests/fixtures/extraction_lab/
Maximum additional paths: 4
Allowed path kinds: tiny manifest / fake batch-report / fake model-calls fixtures only
Decision rule: use committed fixtures only when generated temp fixtures would obscure the contract
```

---

## §7 Explicitly out of scope / collision boundary

| Area | Why this slice must not touch or claim it |
|---|---|
| `tools/batch_ingest_corpus.py` behavior | Existing execution primitive is sufficient for P0b1; modifying it broadens ownership. |
| `MODEL_POLICY.json` and policy mutation | P0b1 observes one stable policy. Controlled model A/B belongs later. |
| `src/ingestion/**` prompts/extractors/taxonomy | First smoke proves the executor, not a quality change. |
| OpenAI Batch submit/poll/complete | P0b2 async/event-driven lifecycle. |
| repetitions > 1 / variance | P0b2. |
| cache sharing/warm/cold matrix | P0b2; P0b1 is isolated only. |
| resume/retry in same root | P0b2. |
| 10–20 document development cohort | P1 after runner qualification. P0b1 is capped at 3. |
| holdout partitioning | P1/P3 protocol. |
| aggregate winner/optimization score | Explicitly prohibited by program design. |
| APP-STATE / DungeonMind publication | P4/P5 authority work, not experimentation. |
| Stage 4 UI fixes | Separate product lane; Stage 4 WOW remains HOLD. |

---

## §8 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| manifest dry-run | manual commands/ad hoc notes | one normalized preflight plan, zero model calls | manifest/runner |
| pair execution | operator manually creates stores/runs/scores | runner owns exact two-variant sequence | runner |
| store/cache isolation | possible manual collision | baseline and candidate have distinct fresh store + `.cache` roots | runner |
| model identity | operator may type intended model into scorer | exact observed model logs become scoring input | runner/log adapter |
| cost/runtime evidence | batch report exists per store | receipt captures/references exact per-variant telemetry | receipt |
| partial failure | scattered artifacts, manual interpretation | explicit terminal failed receipt; no pair completion claim | receipt state machine |
| pair comparison | manually invoked | only after both bundles qualify; must use #705 | runner/comparator |

Adversarial sequences:

| Sequence | Required safe outcome |
|---|---|
| wrong repo SHA → `--execute` | reject before output/model calls |
| dirty worktree → `--execute` | reject before model calls |
| source outside corpus root / missing / duplicate / fourth source | reject preflight |
| output root already exists | reject rather than reuse cache/artifacts |
| baseline succeeds → policy file changes | fail before candidate/comparison; preserve baseline evidence |
| baseline succeeds → candidate subprocess nonzero | failed receipt; comparison absent |
| both stores complete → one Extraction Lab bundle is unqualified | failed receipt; no quality claim |
| both qualify → #705 returns non-comparable | failed receipt with comparator reasons |
| both qualify + comparable | completed receipt; no winner |

---

## §9 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected |
|---|---|---|---|
| Default command is inert | CLI | test dry-run with subprocess spy | zero batch/model execution; normalized plan emitted |
| Execute requires explicit authorization | CLI | omit vs include `--execute` | only explicit flag enters execution path |
| Exact revision is pinned | preflight | wrong SHA fixture | fail before calls |
| Dirty checkout is rejected | preflight | mocked dirty status | fail before calls |
| Cohort is exact and bounded | manifest | missing/outside/duplicate/4-source cases | fail closed |
| Stores/caches are isolated | runner | successful fake pair | distinct variant store roots; no shared `.cache` |
| Existing batch CLI is invoked safely | runner | argv assertion | exact paths-file/store/root/batch-size; forbidden flags absent |
| Model policy is read-only and stable | runner | hash-change injection | failed receipt; no comparison |
| Model stamp comes from observed execution | log adapter | requested vs observed mismatch fixture | receipt/scoring use observed ids or fail closed; never silently trust request |
| Partial execution never looks complete | receipt | baseline-success/candidate-fail test | `status=failed`, baseline retained, comparison absent |
| Successful pair uses #705 | runner | fake qualified bundles/comparator | `completed` only when comparator `comparable=true` |
| No winner introduced | receipt/report | successful pair fixture | no winner/READY/promotion field |
| Existing Extraction Lab remains green | package regression | full lab tests | pass |

Exact verification target:

```bash
uv run pytest tests/extraction_lab/ -q
uv run ruff check extraction_lab/pair_experiment_manifest.py extraction_lab/run_pair_experiment.py tests/extraction_lab/test_pair_experiment_manifest.py tests/extraction_lab/test_run_pair_experiment.py

git diff --check
git diff --name-only 29c50b985091f590d2d6212b10cd79dcc8be5288...HEAD
```

### Required deterministic smoke-ready proof before merge

Using a temp manifest and mocked/fake batch subprocess outputs, prove the entire orchestration path:

```text
manifest preflight
→ baseline fresh store command
→ baseline observed model + telemetry
→ baseline Extraction Lab bundle
→ candidate fresh store command
→ candidate observed model + telemetry
→ candidate Extraction Lab bundle
→ PR #705 comparison comparable=true
→ completed receipt
```

No paid API call is required to merge this implementation PR.

---

## §10 Immediate post-merge live smoke gate

This is an **operator action after merge**, not hidden inside the implementation PR.

Before dispatching P0b2, perform one paid smoke from a clean checkout pinned to the actual Stage 4D merge SHA.

Recommended smallest meaningful cohort:

```text
corpus root:
  corpus/eldyrwild-markdown

source:
  Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate Battle.md

surface:
  core_extraction

baseline:
  batch_size = 5

candidate:
  batch_size = 4

execution:
  realtime
  one repetition each
  isolated caches
  current unchanged Buddy MODEL_POLICY
```

Why Session 23: it directly contains the Brin/Mireward/Orik-era campaign material that exposed the Stage 4 WOW memory gap, while one source keeps the first paid test bounded.

### Smoke PASS means only

- runner executed exactly the pinned one-source pair;
- both isolated stores completed;
- both Extraction Lab bundles proved the same source/gold benchmark identity;
- #705 comparator returned `comparable=true`;
- receipt contains actual models, tokens, cost, cache, and runtime evidence;
- no live APP-STATE/World/model-policy mutation occurred.

Smoke PASS does **not** mean either batch size is better and does not advance the Stage 4 WOW gate.

### Smoke failure routing

- orchestration/receipt/provenance failure → repair Stage 4D before P0b2;
- ingestion pipeline crash common to both variants → classify execution blocker before quality work;
- comparison non-comparable → repair benchmark provenance before tuning;
- quality failures with successful measurable execution → success for P0b1; feed them into P0b2/P1 rather than “fixing” them in the runner.

---

## §11 Required review handback

Record:

1. Review Cycle `<N>`, exact branch/head/base;
2. PR #705 predecessor merge and accepted head;
3. exact implemented manifest schema and dry-run/execute semantics;
4. proof no paid execution occurs without `--execute`;
5. exact variant isolation and cache roots;
6. exact batch argv and proof forbidden flags are absent;
7. model-policy fingerprint/read-only proof;
8. observed-model provenance and ambiguity behavior;
9. partial-failure receipt evidence;
10. successful fake pair → Extraction Lab → #705 comparison → completed receipt;
11. full Extraction Lab tests + Ruff + diff-check;
12. actual changed paths vs §6;
13. backward-looking state authority sync;
14. P0b2 remains false;
15. post-merge live smoke remains an explicit operator gate, not pre-claimed.

---

## §12 Acceptance rubric

- [ ] Exactly one independently useful capability exists: execute one bounded isolated extraction pair and emit truthful measurable evidence.
- [ ] Default invocation cannot spend money or call a model.
- [ ] `--execute` requires exact clean pinned repository state.
- [ ] Source cohort is exact, unique, inside corpus root, and capped at 3.
- [ ] Baseline/candidate stores and caches cannot overlap.
- [ ] P0b1 does not mutate `MODEL_POLICY.json`.
- [ ] Actual observed models, cost, tokens, cache, and runtime are represented in the receipt.
- [ ] Both variants are scored by existing Extraction Lab.
- [ ] Final comparison is the existing PR #705 comparator.
- [ ] Partial failure never yields `completed`.
- [ ] Comparable execution does not imply winner/READY/promotion.
- [ ] APP-STATE and DungeonMind are untouched.
- [ ] Repetitions/resume/async/budgets/holdouts remain deferred to P0b2/later.
- [ ] Stage 4 WOW remains HOLD.

## Stop conditions

Stop and report rather than broadening if:

- existing `tools/batch_ingest_corpus.py` cannot execute an exact 1–3 source pair without production changes;
- scoring requires changing PR #705 comparator/benchmark semantics;
- actual model identity cannot be proven from existing execution logs;
- model selection can only be varied by mutating shared/global policy in this slice;
- reliable execution requires resume or asynchronous Batch lifecycle;
- output/store/cache isolation cannot be guaranteed;
- a required production path falls outside §6;
- implementation starts adding repeated-run statistics, holdout scheduling, automatic winner policy, or publication.

Report:

```text
Stop condition:
Invariant clause affected:
Why P0b1 cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed P0b2/re-brief:
State-authority update needed:
```
