---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program
  - Flow: DOGFOOD-CONTINUITY / Stage 4I / P2a exploratory model screen
  - Direction: DESIGN → CODE → PAID SCREEN → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-impl-v1.md
  - Branch: dogfood-continuity/stage4i-exploratory-model-screen-impl

  ## Verification pointer
  - Stacked base: PR #710 head 34cc1ded9e98082491a00612ae030b33d2479105
  - Paid screen: exactly one Luna + one Terra + one Sol run on one frozen implementation head
  - Human hypothesis: immutable preregistration at commit 8839ca08b82ee727e9959ad808ee912de3e97ccb

  This is a stacked experimental lane. It may execute before #710 is mergeable, but it MUST NOT merge to main until #710 is accepted or equivalent prerequisite infrastructure is landed independently.
---

# HANDOFF — DOGFOOD-CONTINUITY: execute Stage 4I exploratory Luna/Terra/Sol ingestion screen

**Created:** 2026-09-12  
**Status:** ACTIVE — rebriefed after initial reconnaissance; whole-document ablation next
**Canonical handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-impl-v1.md`  
**Branch:** `dogfood-continuity/stage4i-exploratory-model-screen-impl`  
**Stacked base:** `34cc1ded9e98082491a00612ae030b33d2479105` — exact current head of PR #710 at dispatch  
**Target PR title:** `DOGFOOD-CONTINUITY: screen Luna, Terra, and Sol for campaign-memory ingestion`  
**Direction:** DESIGN → CODE → PAID SCREEN → REVIEW

### 2026-09-12 operator rebrief — this section supersedes conflicting model/context clauses below

The initial Luna/Terra/Sol reconnaissance is retained as historical evidence, but it exposed an
uncontrolled assumption: the extraction model receives paragraph evidence units rather than the
whole authored document. Repository history contains no controlled ingestion-quality experiment
showing that paragraph-local extraction beats whole-document semantic context. The operator has
therefore changed the next experiment contract:

```text
Phase A — context ablation, Luna only
  current evidence-unit context × 1
  exact whole-document semantic context × 1

Phase B — model screen on the selected context contract
  gpt-5.6-luna × 1
  deepseek/deepseek-v4.1-flash × 1
```

Terra and Sol are dropped from future paid arms. There is no automatic escalation. Phase B must
not run until Phase A is scored and the human selects the context contract. The old three-model
results remain directional historical evidence and must not be rewritten as this ablation.

Whole-document means: preserve the existing paragraph evidence units and exact source anchors for
provenance, while supplying the exact frontmatter-stripped Markdown body as shared semantic context
to entity and fact extraction. Outputs remain attributed to individual evidence units. In short:
**reason globally, cite locally**.

The experiment-only context seam must default to `evidence_unit`; production behavior cannot change
implicitly. Context mode and document-context bytes are part of cache identity, execution receipts,
and pipeline provenance. Documents exceeding a provider/model context limit fail closed for this
ablation; they are not silently chunked or truncated.

This rebrief extends the §10 write lease to:

- `src/ingestion/chunker.py` — expose exact normalized document body without changing evidence units;
- `src/cli.py` — thread an explicit experiment-only extraction-context mode;
- focused CLI/chunker tests required to prove default preservation and exact-body handling.

DeepSeek provider plumbing is a separate boundary inside this experimental lane. If the existing
OpenAI-compatible client cannot execute `deepseek/deepseek-v4.1-flash` with equivalent structured
output, Flex/service-tier, and reasoning telemetry, stop after Phase A and rebrief that provider
adapter rather than disguising unequal executions as a model comparison.

> Repository law: `AGENTS.md`. Steward process: `Docs/Process/STEWARD-CYCLE.md`. This lane is intentionally stacked on held PR #710 because Stage 4I needs the experiment-only Sol/Flex/model override and legacy-source compatibility infrastructure #710 introduced. Do not merge this lane directly to `main` until #710 is dispositioned or equivalent prerequisite changes are landed separately.

## §1 Mission and merge-ready invariant

**Mission:** Build and execute one cheap, controlled reconnaissance screen that runs the same improved campaign-memory ingestion contract once on GPT-5.6 Luna, once on GPT-5.6 Terra, and once on GPT-5.6 Sol, while measuring quality, output density, reasoning volume, cache behavior, real cost, and projected full-corpus economics.

**Merge-ready invariant:** The three paid arms differ only by model identity. They consume identical source bytes, benchmark/gold/temporal authorities, candidate fact prompt/output schema, compatibility treatment, batch size, service tier, reasoning-effort contract, and execution code. Results are reported truthfully as single-run directional evidence, never as stability proof.

A poor model result is not a failed slice. Provenance drift, gold leakage, unequal execution contracts, silent source skipping, or mutation of production authority are failures.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| One independently useful capability? | Yes: a trustworthy three-model quality/cost reconnaissance screen for the candidate ingestion contract. |
| Most likely false-positive success | 5/5 anchor recall achieved by keyword-shaped output that loses authority/temporal meaning or hallucinates unsupported detail. |
| Most likely experimental confound | Different prompt/schema/reasoning/service-tier behavior between models, or using preregistered target text as generation context. |
| Easiest boundary to under-test | Model-output token composition and field responsibility: aggregate output tokens are insufficient. |
| Stop/split trigger | Candidate requires new semantic fact taxonomy, entity-reconciliation change, source-authority redesign, or any benchmark/gold/source mutation. |

## §2 Authorities and immutable inputs

### 2.1 Frozen scored benchmark

Use exactly:

```text
evals/campaign_memory_development/benchmark.json
evals/campaign_memory_development/gold/entity_anchors.json
evals/campaign_memory_development/gold/fact_anchors.json
evals/campaign_memory_development/temporal_expectations.json
benchmark_id: c2-mireward-campaign-memory-dev-v1
sources: exactly 7
entity anchors: 6
fact anchors: 5
identity expectations: 2, unscored
temporal expectations: 7, unscored
```

Do not edit any of these files.

### 2.2 Frozen human preregistration

Human hypothesis authority is the exact file:

```text
commit: 8839ca08b82ee727e9959ad808ee912de3e97ccb
path: Docs/Plans/PREREGISTRATION-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-v1.md
```

Read it before implementation and again during final human-witness handback.

**Critical leakage rule:** this preregistration is evaluator-only. It MUST NOT be passed into model prompts, runtime generation, deterministic enrichment, scoring, source preprocessing, or candidate construction. Its phrases are not gold. It exists only so review can compare observed output with a target registered before execution.

### 2.3 Historical #710 evidence

#710 historical Sol/Flex characterization is context, not a same-head control:

```text
historical execution head: 6a61b63dca555d3d70cac3e38eb3e48c6fc690da
entity recall: 1.0 / 1.0 / 1.0
fact recall: 0.6 / 0.6 / 0.6
stable misses:
  - Karsemine concrete tripod fire-weakness payload
  - Mireward direct active siege/refugee pressure
identity:
  - Brin coalesced
  - Orik/Orric split 3/3
mean seven-source Sol/Flex cost: about $2.75
```

Do not claim causal improvement versus #710 from a cross-head comparison. It is qualitative historical evidence only.

## §3 Exact experiment contract

Exactly three paid arms, one repetition each:

| Order | Model | Repetitions | Fact contract | Service tier |
|---:|---|---:|---|---|
| 1 | `gpt-5.6-luna` | 1 | `payload_lean_v1` | Flex |
| 2 | `gpt-5.6-terra` | 1 | `payload_lean_v1` | Flex |
| 3 | `gpt-5.6-sol` | 1 | `payload_lean_v1` | Flex |

Execution constants:

```text
seven frozen benchmark sources
batch size = 5
fresh isolated store per model
fresh isolated application cache per model
resume = false
Batch API = false
auto-escalation = false
same compatibility mode for all arms
same prompt fingerprint for all arms
same structured-output schema fingerprint for all arms
same code SHA for all arms
same reasoning effort for all arms
```

Prefer explicit `reasoning.effort = medium` for all three if the Responses API seam supports a narrow experiment-only setting. If equivalent reasoning effort cannot be requested and verified for all three without introducing a broader production capability, STOP and report rather than comparing unequal requests.

Quality misses are data. Continue to the next model. Infrastructure/provenance drift is a stop.

## §4 Candidate semantic contract — `payload_lean_v1`

The only intended semantic intervention is **preserve decisive payloads**.

Current failure form:

```text
Karsemine learned the creature's weaknesses and resistances.
```

Candidate rule:

```text
When the source states the concrete result of a discovery, investigation,
conclusion, diagnosis, revelation, tactical observation, or active threat,
preserve the answer/payload itself. Do not replace the payload with the mere
fact that learning, discovery, or danger occurred.
```

Representative behavior:

```text
GOOD: Karsemine learned the tripod is resistant to poison and weak to fire.
BAD:  Karsemine learned the tripod's weaknesses and resistances.
```

For operational state, preserve direct source-supported table truth such as active siege/attack/refugee pressure rather than only nearby symptoms.

Do NOT:

- add new fact attributes;
- change entity extraction semantics for quality;
- add benchmark words/anchors to generation;
- add identity reconciliation;
- add temporal inference;
- infer unsupported weaknesses/threats;
- change World/DungeonMind/APP-STATE publication;
- mutate source frontmatter/corpus.

The candidate should be selectable for the experiment while leaving the existing production/default fact contract unchanged.

## §5 Output-responsibility audit — zero API calls

Before finalizing `payload_lean_v1`, audit **every model-emitted fact field** and record a machine-readable/human-readable ledger with one classification:

```text
SEMANTIC_REQUIRED
DERIVED_DETERMINISTIC
RUNTIME_CONSTANT
UNUSED
AUTHORITY_SENSITIVE
DEFER_UNCLEAR
```

For every field record:

```text
field
model-facing schema location
consumer(s)
persisted destination, if any
deterministic replacement, if any
classification
evidence/test proving classification
```

Removal rule: a field may leave model responsibility only when proven `DERIVED_DETERMINISTIC`, `RUNTIME_CONSTANT`, or `UNUSED`, and an owning-boundary regression test proves persisted semantic equivalence.

Known required audit case:

```text
fact_id
model currently emits it
persistence recomputes durable fact ID from subject + attribute + label
expected classification: DERIVED_DETERMINISTIC
```

Do not assume `subject_entity_id`, `attribute`, `value.kind`, `label`, `normalized`, `entity_id`, set values, interpretation fields, or any other field is redundant. Prove or retain.

Audit entity-output fields for future learning, but **do not simplify entity output in this slice**. Entity recall is a control signal.

The output audit itself must not change the frozen scorer or benchmark.

## §6 Usage/output telemetry

#710 only preserved aggregate output tokens. Stage 4I must distinguish visible structured output from model reasoning when the API exposes that detail.

Extend experiment telemetry to capture at minimum:

```text
input_tokens
cached_input_tokens
uncached_input_tokens
output_tokens
reasoning_tokens
visible_output_tokens = output_tokens - reasoning_tokens
API calls
parsed structured-output bytes
persisted entity count
persisted fact count
visible output tokens / persisted row
total output tokens / persisted row
reasoning fraction of output
cache-hit fraction
measured USD cost
wall time
```

Requirements:

- Read `output_tokens_details.reasoning_tokens` from the response when present.
- Missing details must remain `null`/unavailable, not guessed as zero unless the provider explicitly reports zero.
- Preserve aggregate compatibility with existing callers/tests.
- Raw receipts may contain provider response metadata but the PR record must be sanitized.
- Do not reduce semantic output just to lower token counts.

## §7 Full-corpus workload census — zero API calls

Before any paid model execution, deterministically census the current original Markdown corpus through the **same parsing/chunking/compatibility path** used by this experiment.

No model calls. No source mutation. No World/APP-STATE writes.

Report:

```text
Markdown source count
raw source bytes
parseable source count
compatibility-normalized source count
rejected/unparseable source count
rejection buckets
evidence-unit count
evidence-unit text bytes
expected entity batches at batch_size=5
expected fact batches at batch_size=5
source/evidence-unit size distribution
largest sources by evidence-unit count
```

Do not silently skip any Markdown source. A source that cannot pass the chosen compatibility path belongs in a failure bucket.

This census replaces file-count scaling as the basis for whole-corpus price estimates.

## §8 Workload-based cost projection

For each model record observed:

```text
seven-source cost
cost / evidence unit
cost / API call
cost / persisted entity
cost / persisted fact
input / cached / visible output / reasoning token mix
```

Project whole-corpus cost using the §7 evidence-unit/batch census and the observed per-model workload. The projection must clearly state:

- single-run uncertainty;
- seven-source semantic mix may not represent all source classes;
- output/evidence-unit can vary by document type;
- cache behavior can vary at corpus scale;
- this is planning math, not a guaranteed invoice.

Budget authority for this slice:

```text
expected three-arm total: approximately $6 or less
hard paid stop/rebrief ceiling: $8 total Stage 4I spend
```

If cumulative Stage 4I paid execution would exceed $8 before all three arms complete, stop before the call that crosses the ceiling and hand back the partial record.

## §9 Preregistered human witness review

After scoring, compare each store against the immutable preregistration. Do not feed the preregistration into any automated generation/scoring step.

At minimum inspect these registered witnesses:

```text
Brin
  - one actor across recap/reference?
  - cook from Edge retained?
  - refugee leadership retained through S25?
  - S25 quarantine/housing role visible?

Orric / Orik
  - one or two identities?
  - mayor role retained?
  - no invented "became mayor in S23" claim?

Karsemine
  - S23 tripod: resistant to poison + weak to fire retained?
  - S24 golem: immune to poison and charm + weak to fire retained?
  - tripod/golem payloads not conflated?
  - knowledge source/session still inspectable?

Mireward
  - North Gate battle can end in S24 while broader pressure remains in S25?
  - refugee/quarantine/housing pressure visible?
  - renewed S25 hybrid attack visible?
  - Thrin dragged underground/disappears retained as unresolved campaign thread?

Authority
  - planning-only scaffold material remains distinguishable from played recap evidence?
  - no silent promotion of every scaffold assertion to table canon?

Additional actor
  - Hesta Bramblewood and sleep-potion help recovered as table-useful memory?
```

Human outcome categories should be small and explicit, for example:

```text
PRESENT_GOOD
PRESENT_FLATTENED
PRESENT_UNSUPPORTED
ABSENT
IDENTITY_FRAGMENTED
AUTHORITY_WRONG
TEMPORAL_SHAPE_WRONG
```

These are qualitative review notes, not new benchmark scores.

## §10 Files in scope — exclusive write lease

Expected changed paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/campaign_memory_exploratory_screen_manifest.py` | Strict three-model, one-run manifest + pins. |
| Create | `extraction_lab/run_campaign_memory_exploratory_screen.py` | Luna → Terra → Sol orchestration, isolation, provenance, budget stop. |
| Create | `extraction_lab/campaign_memory_exploratory_qualification.py` | Per-model benchmark + operations + witness/cost comparison. |
| Create | `extraction_lab/campaign_memory_output_contract_audit.py` | Field-responsibility ledger and output-density helpers. |
| Create | `extraction_lab/campaign_memory_corpus_census.py` | Zero-API full-corpus workload census. |
| Create | focused `tests/extraction_lab/test_campaign_memory_exploratory_*.py` | Manifest/orchestration/qualification/census/output-audit tests. |
| Modify | `src/ingestion/fact_extractor.py` | Experiment-selectable `payload_lean_v1`; default production contract unchanged. |
| Modify | `src/ingestion/entity_extractor.py` | Usage-detail capture only if this is the existing shared helper owner. No entity semantic changes. |
| Modify | `tools/batch_ingest_corpus.py` | Thread experiment-only reasoning/contract/telemetry flags only if required; preserve defaults. |
| Modify | focused existing tests for touched ingestion/batch behavior | Default-preservation and usage-detail regression. |
| Modify | this handoff | Exact-head evidence handback. |

### Bounded discovery exception

If one additional file is the true owner of Responses API reasoning settings or model-call usage telemetry, you may modify **at most two** additional runtime/test paths under:

```text
src/llm/**
tests/**
```

Decision rule: only if required to set equivalent reasoning effort or preserve provider-reported reasoning token detail for the experiment. Record the path and why the listed owner was insufficient.

Anything beyond that is a stop/rebrief.

## §11 Explicitly out of scope / no-change authority

Do not change:

```text
evals/campaign_memory_development/benchmark.json
evals/campaign_memory_development/gold/**
evals/campaign_memory_development/temporal_expectations.json
corpus/eldyrwild-markdown/**
MODEL_POLICY.json
DungeonMind / World schemas or publication paths
APP-STATE
identity reconciliation semantics
production temporal semantics
entity extraction prompt/quality semantics
source metadata/frontmatter semantics beyond using #710's frozen compatibility path
```

Do not add a production model router or escalation system. The experiment may recommend one; it may not implement one.

## §12 Implementation contract

```text
Input:
  #710 exact stacked base
  frozen #708 benchmark/gold
  frozen #709 temporal overlay
  immutable human preregistration (review only)

Output:
  one deterministic experiment manifest
  one output-field audit
  one zero-API corpus census
  three isolated paid stores/receipts
  one per-model benchmark result
  one comparison/qualification artifact
  one human preregistration witness handback
  one workload-based full-corpus cost projection per model

Invariant:
  model identity is the only paid-arm difference

Failure behavior:
  quality miss -> record and continue
  budget ceiling -> stop before violating ceiling
  provenance drift -> fail closed and stop
  source/gold/prompt/schema mismatch -> fail closed and stop
  missing equivalent reasoning/service-tier contract -> stop before paid execution
  source parse failure during census -> bucket/report, do not skip

Replay:
  every paid arm requires a new absent output/store/cache root
  no resume
  no reuse of previous model outputs

Trust boundary:
  benchmark/preregistration are evaluators only
  model output is untrusted until parsed/persisted/scored
  model pricing projection is planning evidence, not authority
```

## §13 Required deterministic tests before spending money

At minimum prove:

1. manifest rejects any model list other than exactly Luna/Terra/Sol once each;
2. run order is Luna → Terra → Sol;
3. exactly one repetition/model;
4. dry-run sends zero API calls;
5. each model gets a fresh store/cache/output root;
6. same seven source SHAs, benchmark/gold/temporal fingerprints across arms;
7. same candidate prompt and structured-output schema fingerprints across arms;
8. gold/preregistration paths/content are never passed to runtime generation;
9. default fact extractor behavior is unchanged when candidate mode is absent;
10. `payload_lean_v1` contains the decisive-payload instruction;
11. every removed output field has an audit classification and deterministic/unused proof;
12. `fact_id`, if removed from model responsibility, still persists deterministically and stably;
13. reasoning-token telemetry records provider detail when present and truthfully handles absence;
14. corpus census executes no model calls;
15. corpus census does not silently omit source failures;
16. budget guard blocks the next paid call before cumulative projected/actual spend crosses $8;
17. compatibility mode and Flex are identical for all arms;
18. equivalent reasoning effort is set/verified for all arms;
19. qualification refuses partial/provenance-invalid results unless explicitly rendering a truthful stopped receipt;
20. identity/temporal human witnesses are not converted into fake numeric scores.

Run focused tests plus all `tests/extraction_lab` and relevant touched ingestion/batch tests. Run scoped Ruff and `git diff --check`.

## §14 Exact execution sequence

Do not improvise this order.

```text
A. IMPLEMENTATION / ZERO-COST
1. re-read this handoff + AGENTS.md
2. read immutable preregistration at 8839ca08...
3. audit current fact/entity output responsibilities
4. implement payload_lean_v1
5. implement reasoning/output telemetry
6. implement manifest/orchestrator/qualification/census
7. run deterministic tests + Ruff + diff-check
8. freeze implementation head

B. ZERO-API PREFLIGHT
9. dry-run exact manifest
10. execute full original-Markdown workload census
11. inspect census for silent skips / compatibility failure buckets
12. record exact repository/prompt/schema/corpus/gold/temporal/policy fingerprints

C. PAID SCREEN — SAME FROZEN HEAD
13. run Luna once
14. revalidate all pins
15. run Terra once
16. revalidate all pins
17. run Sol once
18. revalidate all pins

D. QUALIFICATION
19. run frozen benchmark separately for each model
20. generate cost/output-density comparison
21. perform human preregistration witness review
22. produce sanitized Characterization Record in PR/handoff
23. do not change executable code after paid execution without invalidating the paid receipt
```

If a documentation-only evidence commit is needed after paid execution, it may preserve paid evidence only when a mechanical diff proves no executable/config/source/eval authority used by the experiment changed. Record both execution SHA and evidence-record SHA. Do not spend money solely to make a docs-only SHA match.

## §15 Paid evidence record format

Produce one compact comparison table:

```text
MODEL | ENTITY ANCHORS | FACT ANCHORS | KARSEMINE | MIREWARD | VISIBLE OUTPUT | REASONING | CACHE | COST | TIME
Luna
Terra
Sol
```

Also record:

```text
exact execution SHA
manifest SHA/fingerprint
candidate prompt fingerprint
candidate schema fingerprint
benchmark corpus/gold fingerprints
temporal fingerprint
model-policy SHA
compatibility mode
reasoning effort
source SHAs
per-model entity/fact counts
per-model API calls
per-model input/cached/output/reasoning token totals
per-model visible-output/persisted-row ratio
full-corpus census summary
projected full-corpus cost per model
human preregistration witness categories
```

Keep raw model outputs/stores outside the repository unless existing repository law explicitly permits a sanitized artifact. The PR/handoff should contain compact sanitized evidence, not large generated stores.

## §16 Interpretation discipline

One run per model can support:

- obvious quality separation;
- obvious cost separation;
- output composition;
- candidate plausibility;
- deciding what deserves replication.

It cannot support:

- stochastic stability;
- final model selection;
- production routing thresholds;
- whole-corpus quality guarantees.

The final handback must explicitly evaluate preregistered hypotheses H1–H8 as:

```text
SUPPORTED DIRECTIONALLY
WEAKENED
FALSIFIED
UNRESOLVED
```

No hypothesis may be rewritten after results are known.

## §17 Acceptance

Stage 4I is reviewable when:

- deterministic gates pass;
- census is truthful and zero-API;
- exactly three paid arms completed or a truthful budget/infrastructure stop is recorded;
- paid arms differ only by model identity;
- no benchmark/gold/corpus/preregistration leakage occurred;
- candidate output reduction is proven rather than guessed;
- reasoning vs visible output is measured where available;
- per-model scored results are reported individually;
- human preregistration witnesses are reviewed qualitatively;
- cost projections are workload-based and caveated;
- production defaults/policies/publication/identity/temporal semantics remain unchanged.

There is **no minimum recall threshold** required for an honest exploratory PASS.

## §18 Stop conditions

Stop and report instead of broadening if:

- stacked #710 infrastructure changes materially underneath this branch;
- candidate needs a new fact schema/taxonomy;
- output audit suggests removing an authority-sensitive or semantic field;
- entity-quality changes become necessary;
- identity reconciliation becomes necessary;
- temporal reasoning becomes necessary;
- source metadata/frontmatter semantics need redesign;
- Luna/Terra/Sol cannot share equivalent Flex/reasoning execution;
- census needs source mutation;
- benchmark/gold/preregistration would need changing;
- cumulative paid spend would exceed $8;
- any input/prompt/schema/code fingerprint drifts between arms;
- an additional production model-routing capability appears.

Hand back:

```text
Stop condition:
Invariant affected:
What was learned:
Paid spend so far:
Evidence produced:
Missing evidence:
Required successor/rebrief:
```

## §19 Required review handback

Return with:

1. exact PR/branch/head and exact paid execution SHA;
2. actual changed paths versus §10;
3. nano-commit story;
4. deterministic test/Ruff/diff-check evidence;
5. field-responsibility audit summary;
6. full-corpus workload census;
7. Luna/Terra/Sol comparison table;
8. actual total paid spend;
9. full-corpus model cost projections;
10. frozen benchmark per-anchor results;
11. human preregistration witness evaluation;
12. H1–H8 disposition;
13. any stop conditions/waivers;
14. explicit statement that single runs are directional only;
15. recommended next slice, chosen from evidence rather than preselected.

## §20 Named successors — all remain false until results exist

Possible immediate successors:

```text
replicate Luna candidate 3×
replicate Terra candidate 3×
replicate Sol candidate 3×
isolate semantic-payload vs lean-output effects on one chosen model
resolve source-authority/frontmatter semantics
score/fix Orik/Orric identity
full-corpus disposable rehearsal
```

Do not implement any successor in this PR.

## §21 Characterization record — paid execution

**Status:** paid screen completed; evidence-only record  
**Execution SHA:** `9e0fb271b554433ef3d669d424d388954b2b9bd7`  
**Stacked base:** `34cc1ded9e98082491a00612ae030b33d2479105` (PR #710, still unmerged)  
**This lane must not merge to main while #710 remains unresolved.**  
**Single-run directional only.** No stability, routing, or whole-corpus quality claim.

### Pins

```text
repository_sha: 9e0fb271b554433ef3d669d424d388954b2b9bd7
benchmark_id: c2-mireward-campaign-memory-dev-v1
corpus_fingerprint: 925ad24a54d888e2f1d3673919d126767b39cdeaf885c07057bfb5da346ba8c1
gold_fingerprint: de072c175cc00a1dc7ed672cdaca317ee0f8cb381a8186e9cfc53a5885a4cd23
temporal_intent_fingerprint: ed3596e4fd7d75029534c19e5017f4905840347356bf5323b30c365f906c56c4
prompt_sha256: 6a70e6c4f4d961ce72a273e1a4994f397ef7047bade68acede0125ffcf992df0
schema_sha256: aaa7fb3e4e16da36d22e90f8c46a4f1d3e149dd6e361add13a9b5530e639ba46
default_prompt_sha256: 9f724157a4763aad85acab980f8476d411e05e3fc4e2e6b779facff78e01b19e
compatibility: --normalize-legacy-frontmatter
reasoning_effort: medium
service_tier: flex
batch_size: 5
fact_contract: payload_lean_v1
```

### Output-field audit

Only `fact_id` left model responsibility (`DERIVED_DETERMINISTIC`). Persistence still recomputes a stable ID from subject + attribute + label. All other fact fields retained as `SEMANTIC_REQUIRED` or `AUTHORITY_SENSITIVE`. Entity output unchanged.

### Full-corpus census (zero API)

```text
markdown sources: 434
raw bytes: 2,437,735
parseable: 282
compatibility-normalized: 138
rejected: 152 (FrontmatterValidationError 97, FrontmatterParseError 28, ValueError 27)
silent skips: 0
evidence units (parseable): 5,336
expected entity calls @5: 1,996
expected fact calls @5: 1,178
seven-source evidence units: 130 (all 7 parseable; 4 needed compatibility)
scale factor: 41.05×
```

Rejected sources are bucketed, not skipped. Projections below cover the parseable 282-file workload, not the 152 failures.

### Paid comparison

Raw stores remain outside the repository (`/tmp/stage4i-screen-9e0fb271`).

```text
MODEL | ENTITY | FACT | KARSEMINE | MIREWARD | VISIBLE OUT | REASONING | CACHE | COST | TIME
Luna  | 6/6    | 2/5  | payload on tripod, Karsemine flattened | siege phrase on Mireward not Reach | 129,483 | 66,844 (34%) | 0.56 | $0.13 | 528s
Terra | 6/6    | 3/5  | payload on tripod, Karsemine flattened | siege phrase on Mireward not Reach | 112,917 | 49,370 (30%) | 0.55 | $1.10 | 347s
Sol   | 6/6    | 3/5  | payload on Karsemine event_outcome     | meat-monster flank on Mireward    | 130,981 | 99,734 (43%) | 0.54 | $2.56 | 562s
```

Fact-anchor misses:

```text
Luna:  brin_refugee_leadership, karsemine_fire_weakness_discovery, mireward_siege_pressure
Terra: karsemine_fire_weakness_discovery, mireward_siege_pressure
Sol:   brin_refugee_leadership, mireward_siege_pressure
```

All three used 84 API calls. Total paid spend: **$3.79**. Budget ceiling $8 not reached.

### Full-corpus cost projections (planning math)

```text
Luna  $0.13 × 41.05 ≈ $5.34
Terra $1.10 × 41.05 ≈ $45.13
Sol   $2.56 × 41.05 ≈ $105.14
```

Caveats: single-run; seven-source mix ≠ all classes; 152 parse failures excluded; cache/output density will vary.

### Human preregistration witnesses (evaluator-only)

Preregistration read from immutable commit `8839ca08…`; none of its target language entered prompts, enrichment, or scoring.

| Witness | Luna | Terra | Sol |
|---|---|---|---|
| Brin one actor | PRESENT_GOOD (1 entity) | IDENTITY_FRAGMENTED (Brin Holloway + Brin) | PRESENT_GOOD (1 entity) |
| Cook from Edge | PRESENT_GOOD | PRESENT_GOOD | PRESENT_GOOD |
| Refugee leadership through S25 | PRESENT_GOOD (role facts S23+S25; scorer miss on keyword) | PRESENT_GOOD (scored pass) | PRESENT_GOOD (role facts; scorer miss) |
| S25 quarantine/housing | PRESENT_GOOD (warehouse, eye split, sleep potion) | PRESENT_GOOD | PRESENT_GOOD |
| Orik/Orric one identity | IDENTITY_FRAGMENTED (Orik Tane, Orik, Mayor Orric Tane) | IDENTITY_FRAGMENTED | IDENTITY_FRAGMENTED |
| Mayor role, no invented S23 start | PRESENT_GOOD; no “became mayor” | PRESENT_GOOD; none | PRESENT_GOOD; none |
| S23 tripod poison/fire | PRESENT_GOOD on tripod; PRESENT_FLATTENED on Karsemine | PRESENT_GOOD on tripod; PRESENT_FLATTENED on Karsemine | PRESENT_GOOD on Karsemine + tripod |
| S24 golem immune poison/charm + fire | PRESENT_GOOD on golem | PRESENT_GOOD on golem | PRESENT_GOOD on golem |
| Payloads not conflated | PRESENT_GOOD (distinct S23/S24 rows) | PRESENT_GOOD | PRESENT_GOOD |
| North Gate end vs S25 pressure | TEMPORAL_SHAPE_WRONG (end not explicit); S25 pressure PRESENT_GOOD | same | same |
| Thrin underground unresolved | PRESENT_GOOD | PRESENT_GOOD | ABSENT as underground pull; search-for-Thrin present |
| Hesta sleep-potion help | PRESENT_GOOD | PRESENT_GOOD | PRESENT_GOOD |
| Scaffold vs played authority | PRESENT_GOOD (seed_prep vs observed_recap distinguishable) | PRESENT_GOOD | PRESENT_GOOD |

### H1–H8

| Hypothesis | Disposition | Note |
|---|---|---|
| H1 lossy compression, not noticing | SUPPORTED DIRECTIONALLY | Concrete poison/fire payloads exist in all three stores. Luna/Terra still emit the flattened “learned weaknesses” sentence on Karsemine; Sol attributes the payload to Karsemine. |
| H2 semantic contract > model size on five facts | FALSIFIED | No model hit 5/5. Sol/Terra 3/5, Luna 2/5. The candidate did not repair both #710 misses across sizes. |
| H3 Luna close in quality, far in price | SUPPORTED DIRECTIONALLY | Qualitative memory is close; scored recall is 2/5 vs 3/5. Luna is ~8× cheaper than Terra and ~20× cheaper than Sol on this run. |
| H4 Orik/Orric stays split | SUPPORTED DIRECTIONALLY | All three kept separate Orik/Orric identities. |
| H5 Brin easy positive control | SUPPORTED DIRECTIONALLY | Luna/Sol coalesced; Terra kept a second `Brin` alias entity. Not a serious regression. |
| H6 temporal inspectable, not complete | SUPPORTED DIRECTIONALLY | Session tags and S23/S24/S25 facts exist; North Gate battle-end vs broader S25 threat is not a clean stored distinction. |
| H7 paying for unneeded model-owned fields | WEAKENED | Only `fact_id` proven removable. Visible structured output still dominates Luna/Terra tokens. |
| H8 reasoning may dwarf JSON trimming | MIXED | Reasoning is 30–43% of output tokens, highest on Sol (43%). Material lever, not the only one. Visible JSON remains large. |

### Recommended next slice (from this evidence, still false here)

`replicate Luna candidate 3×` is the leading cheap follow-up: the payloads are already in the Luna store, spend is $0.13/run, and one run cannot prove whether Karsemine-attribution flattening is stable.

Independent later slices, not this PR: `score/fix Orik/Orric identity`; `resolve source-authority/frontmatter semantics` for the 152 census failures; `isolate semantic-payload vs lean-output` only if Luna replication shows the remaining miss is prompt-attribution rather than noise.

## 2026-09-12 Luna context ablation handback

Implementation head for paid extraction: `1e63d6130bb0aa9c6e85e7886da3f0bb3283e514`.
Provenance-stamping analysis head: `f91829cc91bcb9e17982af79b75fdf5d6d83b1af`.

The first whole-document attempt stopped after 3/7 sources because the context loader
revalidated raw legacy frontmatter instead of using the compatibility treatment already applied
by ingestion. It spent approximately `$0.05`; it is failed infrastructure evidence and is excluded
from comparison. Commit `1e63d613` repaired this by mechanically removing the frontmatter envelope
while preserving exact Markdown body bytes. Both compared arms then completed 7/7 on that head.

| Measure | Evidence-unit control | Whole-document semantic context |
|---|---:|---:|
| Model / tier / reasoning | Luna / Flex / medium | Luna / Flex / medium |
| Evidence units persisted | 130 | 130 |
| Entity anchors | 6/6 | 6/6 |
| Mechanical fact anchors | 4/5 | 3/5 |
| Persisted entities | 133 | 119 |
| Persisted facts | 702 | 674 |
| API calls | 84 | 84 |
| Input tokens | 254K | 566K |
| Output tokens | 202K | 173K |
| Estimated cost | `$0.13` | `$0.15` |
| Model time | 374.5s | 323.3s |

The apparent 4/5 → 3/5 regression is not a trustworthy semantic regression. Whole-document output
contains two clean Brin facts, `A cook from Edge` and `Leader of the survivors from Edge`. The
leadership anchor accepts `survivor leader` but not the semantically equivalent inverse wording.
The evidence-unit arm happened to combine both concepts into one longer fact containing the exact
accepted phrase `clear leader`.

Both arms mechanically miss Mireward pressure. The whole-document store nevertheless contains
materially stronger table context on the correct Mireward subject, including:

```text
Mireward Reach is undergoing a new refugee influx and becoming more crowded this month.
Mireward Reach is experiencing a crisis of capacity and fen displacement.
A refugee crush breaks the town's working mix all at once.
The approaching meat-monster flank is depicted as wrong, stitched meat...
```

The anchor accepts exact phrases such as `refugee pressure`, `under siege`, or
`meat-monster flank`; the last fact is categorized as portrayal rather than the allowed
operational/event attributes. The scored miss therefore exposes scorer/representation sensitivity,
not absent campaign memory.

Both arms recover Karsemine's concrete weak-to-fire discovery. Both retain the cross-document
Orik/Orric split; whole-document context cannot reconcile identities across separate documents.

### Disposition

Select **whole-document semantic context** as the leading contract for the Luna-vs-DeepSeek screen.
It preserved local evidence anchors, produced cleaner decomposed Brin facts, exposed substantially
richer Mireward context, reduced entity/fact volume, cost only `$0.02` more in this single run, and
did not increase observed model time. This is directional one-run evidence, not stability proof.

Before treating exact anchor recall as model-selection authority, add a scorer test for semantically
equivalent subject-predicate wording (`leader of the survivors` versus `survivor leader`) and review
whether the Mireward requirement is one compound fact or multiple independently scored expectations.
Do not edit gold to mirror this output. Orik/Orric remains separate identity-reconciliation work.

Phase B remains blocked on an equivalent DeepSeek provider adapter. The current ingestion clients
are OpenAI Responses clients; no repository evidence proves that `deepseek/deepseek-v4.1-flash`
can receive the same structured schema, reasoning contract, service tier, and telemetry through
that seam. Do not label unequal provider executions a controlled model comparison.
