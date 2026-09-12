---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program
  - Flow: DOGFOOD-CONTINUITY / Stage 4I / P2a
  - Direction: DESIGN → CODE → PAID EXPERIMENT → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-payload-output-model-ablation-v1.md

  ## Verification pointer
  - Base/head: re-anchor after PR #710 disposition; design was authored from 0aa77bf791efa00cb51f45f3c7acd273ac3f351f
  - Verification: exact-head six-arm paid matrix + deterministic qualification artifact + field-responsibility audit

  The checked-in handoff, cumulative diff, exact experiment manifest, paid receipts, and independently rerun deterministic evidence are the review contract.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 4I decisive-payload + output-density model ablation

**Created:** 2026-09-12  
**Status:** DESIGN READY — BLOCKED ON PR #710 DISPOSITION / RE-ANCHOR  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-payload-output-model-ablation-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / Stage 4I / P2a  
**Direction:** DESIGN → CODE → PAID EXPERIMENT → REVIEW  
**Design base revision:** `0aa77bf791efa00cb51f45f3c7acd273ac3f351f` (main after PR #709; implementation MUST re-anchor after #710 disposition)  
**Design branch:** `dogfood-continuity/stage4i-payload-output-model-ablation-v1`  
**PR title:** `DOGFOOD-CONTINUITY: compare payload preservation and output density across Sol and Terra`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Predecessor authorities: Stage 4F campaign-memory benchmark (#708) and Stage 4G temporal intent (#709). PR #710 is historical experiment evidence only until formally dispositioned.

## §0 Program position and predecessor evidence

```text
P0a    trustworthy cross-contract comparison              DONE — #705
P0b1   bounded isolated A/B execution                     DONE — #706
P0b2a  repeated-run variability qualification             DONE — #707
P1a    campaign-memory entity/fact benchmark              DONE — #708
P1a.1  identity + temporal requirement intent             DONE — #709
P1b    Sol/Flex baseline characterization                 PR #710 — HOLD / disposition required
P2a    decisive-payload + output-density model ablation   ← THIS DESIGN
P3     frozen candidate qualification                     later
P4     full-corpus disposable rehearsal                   later
P5     governed durable publication                       later
```

PR #710 produced useful paid historical evidence on implementation head `6a61b63dca555d3d70cac3e38eb3e48c6fc690da`, but review held the PR because implementation crossed predecessor stop conditions and retroactively widened the write lease. Do not treat #710 as accepted repository authority unless/until its disposition says so.

Historical #710 evidence may guide this design:

```text
model: gpt-5.6-sol
service tier: Flex
cohort: exact seven-source Mireward campaign-memory benchmark
repetitions: 3
batch size: 5
entity recall: [1.0, 1.0, 1.0]
fact recall:   [0.6, 0.6, 0.6]
stable fact failures:
  - Karsemine fire-weakness discovery payload
  - Mireward active siege/refugee pressure
identity witness:
  - Brin recap/reference coalesced
  - Orik/Orric remained split 3/3
3-run spend: $8.2405
3-run output tokens: 750,827
3-run cached input tokens: 428,678
```

The current code-level fact contract also exposes an output-efficiency smell: the model emits `fact_id`, but persistence recomputes the durable fact ID from `subject_entity_id + attribute + label`. That field is therefore a known candidate for removal from model responsibility. The current usage helper records aggregate output tokens but not `output_tokens_details.reasoning_tokens`, so the visible-JSON share of #710's output cost is not yet known.

## §1 Mission and merge-ready invariant

**Mission:** Produce one controlled, gold-backed quality/cost experiment that separates (a) model choice, (b) the specific decisive-payload extraction correction motivated by #710, and (c) a bounded reduction in redundant fact-model output, so the steward can choose the next ingestion contract from evidence rather than intuition.

**Merge-ready invariant:** Every paid arm consumes the same frozen campaign-memory corpus/gold/identity/temporal authorities and the same execution mechanics; the only allowed arm differences are the manifest-pinned model (`gpt-5.6-sol` vs `gpt-5.6-terra`) and fact-contract variant (`control`, `payload`, `payload_lean`); all usage, scored quality, unscored identity/temporal witnesses, output-token composition, cache behavior, cost, and persisted fact deltas are reported without benchmark leakage or automatic promotion.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. This is one causal characterization capability with six frozen arms. |
| Most likely adversarial sequence | Candidate reuses a control cache, or gold intent leaks into generation, or lean output silently drops semantic information while headline recall improves. |
| Will §7 detect it? | Yes: variant-specific cache identity, prompt/input audit, persisted-delta review, per-anchor stability, and field-responsibility proofs are merge gates. |
| Easiest owning boundary to under-test | Model output → parsed candidate schema → persisted FactStore record. |
| Fact that forces stop/split | Output simplification requires changing authority semantics, entity identity semantics, fact taxonomy, or benchmark gold rather than removing demonstrably redundant fact-output responsibility. |

## §2 Re-anchor gate — DO NOT IMPLEMENT FROM THIS DESIGN BASE

This handoff was authored while #710 is open on HOLD. Before implementation:

1. disposition #710;
2. re-anchor to the exact accepted successor base;
3. verify the accepted base contains (or intentionally replaces) the experiment-only model/Flex execution seam and the seven-source compatibility behavior needed to reproduce the predecessor conditions;
4. update this handoff's implementation base, predecessor SHA, and write lease to the actual accepted paths;
5. verify #708 corpus/gold fingerprints and #709 temporal fingerprint still reproduce.

If #710 is closed/split and those execution seams are not on the accepted base, do **not** silently recreate them inside Stage 4I. Rebrief the prerequisite first.

PR #710's paid run remains historical evidence; it is not a substitute for same-head Stage 4I control arms.

## §3 The experiment: 2 models × 3 fact contracts

Run exactly these six arms, each for three fresh-store repetitions:

| Arm | Model | Fact contract | Purpose |
|---|---|---|---|
| `sol_control` | `gpt-5.6-sol` | current accepted contract | same-head Sol control |
| `terra_control` | `gpt-5.6-terra` | current accepted contract | pure model effect |
| `sol_payload` | `gpt-5.6-sol` | payload-preserving prompt only | pure semantic prompt effect on Sol |
| `terra_payload` | `gpt-5.6-terra` | payload-preserving prompt only | whether semantic correction generalizes down-model |
| `sol_payload_lean` | `gpt-5.6-sol` | same payload prompt + audited lean fact output | output-contract effect on Sol |
| `terra_payload_lean` | `gpt-5.6-terra` | same payload prompt + audited lean fact output | output-contract effect on Terra |

Total paid repetitions: **18**.

All arms keep constant:

```text
exact seven #708 sources
#708 entity/fact gold
#708 identity expectations (unscored)
#709 temporal expectations (unscored)
Flex service tier
batch size 5
realtime Responses API
fresh isolated store + local cache each repetition
no retry-on-quality
no auto escalation
no production MODEL_POLICY mutation
same accepted source/frontmatter compatibility behavior
same entity-extraction contract
same fact taxonomy / persistent FactStore schema
same default reasoning configuration
same provider caching behavior
```

Do not use #710's historical Sol results as one of the six arms. The matrix must be same-head.

### Expected budget

Using #710's measured Sol/Flex workload as planning evidence, a six-arm/three-repetition matrix is expected to be approximately **$40** before candidate token-volume changes. Set a **$50 paid-execution ceiling**. If deterministic preflight or running telemetry projects crossing $50, stop and rebrief; do not silently continue.

## §4 Candidate A — decisive-payload preservation

The `payload` variant changes **fact extraction instructions only**. No schema/taxonomy/persistence change.

The intended rule:

> When the evidence states the concrete result of a discovery, investigation, diagnosis, tactical observation, revelation, test, or conclusion, preserve the concrete answer/payload. Do not emit only the meta-event that something was learned when the learned truth is present in the source.

Required positive examples in the prompt/tests should express the principle without benchmark-specific names:

```text
Source: the ranger determines the creature resists poison and is weak to fire.
Bad:    The ranger learned the creature's weaknesses and resistances.
Good:   The ranger learned the creature resists poison and is weak to fire.

Source: the town is under active siege and refugees are overwhelming capacity.
Bad:    The town faces ongoing danger.
Good:   The town is under active siege and refugee pressure.
```

Guardrails:

- preserve direct source detail, not added inference;
- keep one distinct proposition per fact where practical;
- shorter is still preferred **only when the decisive payload survives**;
- do not add new attributes or change persistent fact schema;
- do not mention Karsemine, Mireward, exact gold keywords, anchor IDs, or benchmark expectations in the generation prompt.

The benchmark is evaluator-only. Gold must never become generation context.

## §5 Output-density audit — measure before optimizing

Before freezing `payload_lean`, produce a deterministic **field responsibility ledger** for the current entity and fact model outputs.

For every model-emitted field record:

```text
field
stage: entity | fact
who currently emits it
who consumes it
whether it reaches persistent store
whether it is ignored
whether it is overwritten/recomputed
whether it is a runtime-known constant
whether deriving it requires semantic inference
whether it is authority-sensitive
candidate disposition
proof
```

Classify each field as exactly one of:

```text
SEMANTIC_REQUIRED
DERIVED_DETERMINISTIC
RUNTIME_CONSTANT
UNUSED
AUTHORITY_SENSITIVE
DEFER_UNCLEAR
```

Only `DERIVED_DETERMINISTIC`, `RUNTIME_CONSTANT`, or `UNUSED` fact-output fields may be removed from model responsibility in `payload_lean`.

Known starting witness:

```text
ExtractedFact.fact_id
  model emits: yes
  durable ID: recomputed from subject + attribute + label
  candidate classification: DERIVED_DETERMINISTIC
```

Do **not** assume other fields are removable until traced through real consumers.

### Ground-truth anti-leakage rule

The existence of an already-known entity/node may be used only where the production pipeline genuinely possesses that identity/context before the model call. Runtime-known IDs/constants may replace model-generated boilerplate when deterministic.

The #708/#709 gold expectations may **never** be used to infer or synthesize a fact, fill a missing payload, choose a subject, or derive a value. Gold is scoring authority only. Any candidate that uses evaluation truth as generation input invalidates the experiment.

### Scope boundary for lean output

Stage 4I may **audit entity output**, but `payload_lean` may change only the **fact-model output contract**. Entity-output simplification is a named successor if the audit finds meaningful savings.

Do not combine identity/coalescence changes with this experiment.

## §6 Output-token and cache telemetry contract

The predecessor telemetry is insufficient because `output_tokens` combines visible output and reasoning. The Responses API exposes `output_tokens_details.reasoning_tokens`; Stage 4I must retain that breakdown.

For every model call capture when available:

```text
model
stage: entity | fact
arm
repetition
input_tokens
cached_input_tokens
cache_write_tokens
output_tokens
reasoning_tokens
visible_output_tokens = output_tokens - reasoning_tokens
API call count
parsed payload UTF-8 byte length
parsed entity/fact row count
```

Aggregate per arm and stage:

```text
total / mean / min / max / pstdev
cached-input fraction
reasoning-output fraction
visible-output tokens per persisted row
total-output tokens per persisted row
parsed bytes per persisted row
estimated cost
runtime
```

Do not change prompt-cache keys, provider cache policy, reasoning effort, output verbosity, service tier, batching, or local-cache behavior in this slice merely to improve the number. Measure current behavior first. Cache optimization and reasoning-effort ablations are successors if telemetry shows they dominate.

Variant identity MUST be part of any local extraction cache key/prompt ID so `control`, `payload`, and `payload_lean` cannot reuse one another's model outputs.

## §7 Lean fact-output contract

Freeze `payload_lean` only after the §5 ledger is reviewed in-code and tests prove each removed field is non-semantic.

`payload_lean` must use the **same semantic instruction text** as `payload`; its only difference is the model-facing fact output shape/responsibility.

Minimum expected candidate:

```text
remove model responsibility for fact_id
recompute durable fact_id exactly as today after parse
```

Additional fact fields may be removed only if §5 proves they are deterministic/constant/unused and fixture-level persistence equivalence holds.

Forbidden in this slice:

```text
new persistent fact schema
new fact attribute taxonomy
changing truth-state/source-authority semantics
moving source authority decisions into a lossy derivation
entity output/schema simplification
identity merge/alias correction
temporal inference/scoring
using benchmark gold to fill omitted model fields
```

For a representative fixture set, parsing `payload_lean` then deterministic enrichment must produce the same persistent semantic fact record as the equivalent `payload` output except for generated IDs/timestamps that are already intentionally deterministic/runtime-owned.

## §8 Quality and causality outputs

Existing scored benchmark output remains primary quality evidence:

```text
entity_anchor_recall
fact_anchor_recall
per-anchor pass/fail + fail bucket
entity/fact counts
3-run stability for all 11 anchors
```

Pay particular attention to—but do not special-case in generation—the two historical #710 failures:

```text
Karsemine fire-weakness discovery
Mireward active siege/refugee pressure
```

Protect the historical stable passes:

```text
Brin cook from Edge
Brin refugee leadership
Orik mayor role
all 6 entity anchors
```

No arm is promoted merely because aggregate recall increases.

### Required pairwise comparisons

```text
terra_control      vs sol_control
  → model effect under current contract

sol_payload        vs sol_control
terra_payload      vs terra_control
  → semantic payload-instruction effect within model

sol_payload_lean   vs sol_payload
terra_payload_lean vs terra_payload
  → output-contract effect while semantic prompt is held fixed

terra_payload_lean vs sol_payload_lean
  → quality/cost tradeoff after both intended contract changes
```

Do not collapse these into one scalar winner score.

## §9 Candidate-delta audit

For each candidate arm, emit an inspectable delta packet for facts touching the benchmark subjects/sources:

```text
source/evidence identity
control fact(s)
candidate fact(s)
linked anchor result if any
persisted subject / attribute / value
source evidence excerpt or source-span pointer
```

The packet exists to distinguish:

```text
desired specificity recovered
same truth rephrased
new unsupported inference
fact duplication/explosion
semantic payload lost
subject misattachment
```

A human review must inspect at least the Karsemine and Mireward target deltas plus one stable-pass non-regression example.

## §10 Identity, temporal, and authority witnesses remain unscored

Carry forward the #708 identity and #709 temporal witness packets for every arm.

They are observational controls only. In particular:

- Brin same-identity behavior should remain visible;
- Orik/Orric fragmentation should remain visible;
- if Terra or a candidate changes identity behavior incidentally, record it but do not optimize or score it here;
- temporal requirements remain inspectable, not numerically scored;
- accepted source/frontmatter compatibility behavior is frozen across all arms and is **not** endorsed as final publication semantics.

Any attempt to fix identity, temporal representation, or authority semantics is a split.

## §11 Paid execution and provenance

One strict manifest owns the complete six-arm matrix.

At minimum pin:

```text
exact repository SHA
worktree cleanliness
manifest SHA
#708 benchmark ID + corpus/gold fingerprints
#709 temporal fingerprint
all seven source byte hashes
MODEL_POLICY bytes even though experiment models are explicit
model IDs per arm
fact-contract variant IDs and prompt/schema fingerprints
service tier Flex
batch size 5
repetitions 3
compatibility/frontmatter mode
$50 budget ceiling
```

Fresh root per arm/repetition. No resume, retries, Batch API, escalation, or winner-driven extra calls.

Revalidate pins before and after every arm/repetition and before final qualification. Fail closed on drift.

A documentation-only evidence-recording commit after the paid run may preserve paid evidence **only if** a deterministic tree/path comparison proves that no executable/config/prompt/schema/benchmark/corpus/model-policy/runtime-authority bytes changed. Otherwise rerun the matrix. Record the distinction explicitly rather than spending money solely for SHA cosmetics.

## §12 Expected implementation write lease after re-anchor

**This lease is provisional until #710 is dispositioned. Update it before dispatch.**

Expected paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/campaign_memory_payload_model_manifest.py` | Strict six-arm matrix authority. |
| Create | `extraction_lab/run_campaign_memory_payload_model_ablation.py` | Paid/dry-run orchestration and provenance. |
| Create | `extraction_lab/campaign_memory_payload_model_qualification.py` | Causal quality/cost/output-density qualification. |
| Create | `extraction_lab/output_contract_audit.py` | Deterministic field-responsibility ledger. |
| Create | `tests/extraction_lab/test_campaign_memory_payload_model_manifest.py` | Matrix/pin/anti-leakage contract tests. |
| Create | `tests/extraction_lab/test_run_campaign_memory_payload_model_ablation.py` | Six-arm execution/fail-closed tests. |
| Create | `tests/extraction_lab/test_campaign_memory_payload_model_qualification.py` | Pairwise metrics and delta packet tests. |
| Create | `tests/extraction_lab/test_output_contract_audit.py` | Consumer tracing / removable-field evidence. |
| Modify | `src/ingestion/fact_extractor.py` | Experiment-selectable payload prompt and lean fact output only; production default unchanged. |
| Modify | `src/ingestion/entity_extractor.py` | Usage-detail capture only if this remains the owning helper after #710 disposition. |
| Modify | `tools/batch_ingest_corpus.py` | Aggregate reasoning/cache-write/output-density telemetry only if this remains the accepted owning path. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-payload-output-model-ablation-v1.md` | Re-anchor + implementation/review handback. |
| Modify | state-authority docs identified after #710 disposition | Accepted predecessor/current-active facts only. |

Bounded discovery exception:

```text
Directory: tests/ingestion/ and tests/extraction_lab/
Maximum additional paths: 3
Allowed path kinds: focused regression fixtures/tests for model-output schema equivalence or usage telemetry
Decision rule: only when an existing owning test file is clearly the correct boundary
```

Any production path not named above is a stop/rebrief.

## §13 Explicitly out of scope

```text
#708/#709 benchmark/gold mutation
corpus source edits
MODEL_POLICY mutation
DungeonMind graph/schema changes
APP-STATE / World publication
identity merge implementation
identity scoring
new temporal ontology or temporal scorer
source-authority/frontmatter semantic redesign
entity-output optimization beyond audit
reasoning-effort tuning
explicit prompt-cache-key/caching optimization
OpenAI Batch API/resume lifecycle
whole-corpus ingestion
candidate promotion to production default
```

## §14 Evidence required to merge

Deterministic evidence before paid execution:

```text
re-anchored accepted predecessor
all #708/#709 fingerprints reproduce
six arms exactly; 3 reps each
control/payload/payload_lean prompt+schema identities distinct where required
local cache keys include contract variant
production default extraction behavior unchanged
field-responsibility ledger generated
fact_id redundancy proved from actual consumer path
lean enrichment → persistent fact equivalence fixtures
benchmark/gold unavailable to generation prompt construction
usage parser records reasoning_tokens and cache_write_tokens when provider supplies them
visible_output_tokens arithmetic tested
$50 budget guard tested
pin/TOCTOU mutation failures tested
```

Paid evidence on exact executable head:

```text
18/18 repetitions complete, or truthful failed receipt
same exact seven-source cohort every arm
all benchmark contracts qualify
actual model identity matches arm
Flex + batch size 5 everywhere
per-arm scored recall/stability/failure buckets
per-arm entity/fact counts
per-arm input/cached/cache-write/output/reasoning/visible token telemetry
per-arm parsed-output bytes/rows
per-arm cost/runtime/API calls
required pairwise comparisons
candidate-delta packet
identity/temporal witnesses for every arm
no authority mutation
no automatic winner/promotion
```

Required human audit:

```text
Karsemine target delta
Mireward target delta
one stable-pass non-regression delta
field-responsibility ledger
any field removed in payload_lean
reasoning-vs-visible output composition
Terra-vs-Sol quality/cost interpretation
```

No minimum score is required for this PR to succeed. A failed candidate is useful evidence if the experiment is trustworthy.

## §15 Acceptance questions

The review must be able to answer all of these without guessing:

1. Was #710's 60% fact recall primarily a contract problem, a model-capability problem, or both?
2. Does explicit payload preservation recover table-useful truths without increasing unsupported facts or regressing stable anchors?
3. Does Terra preserve the same correction, and at what actual cost/runtime/token tradeoff versus Sol?
4. How much API output spend is visible structured data versus hidden reasoning?
5. Which fact-output fields are the model currently generating even though code can safely derive/ignore them?
6. Does removing those fields reduce visible/total output without changing persisted semantic facts or benchmark outcomes?
7. Is input caching already material, and is output/reasoning still the dominant cost center?
8. What should the next bounded capability be: promote payload semantics for qualification, deeper output-contract work, reasoning-effort/caching optimization, identity scoring, or model selection?

## §16 Named successors — remain false

Possible evidence-selected successors:

```text
payload candidate qualifies → P3 frozen candidate qualification
Terra matches Sol quality materially cheaper → model-selection qualification
reasoning tokens dominate → reasoning-effort ablation
visible schema overhead dominates → deeper output-contract simplification, including entity output
cache misses dominate → explicit prompt-cache optimization
identity fragmentation remains dominant → executable identity scoring + Orik/Orric correction
source authority remains unsafe → metadata/authority semantics slice before publication
```

Do not preselect one before evidence.

## Stop conditions

Stop and report instead of expanding when:

- #710 disposition does not provide a trustworthy accepted execution seam for the frozen seven-source experiment;
- accepted source/frontmatter behavior changes across arms;
- Terra/Sol cannot run through the same extraction/runtime contract;
- benchmark gold would need to enter generation context;
- `payload_lean` requires semantic inference in code rather than deterministic enrichment;
- removing a field changes persistent semantic facts in equivalence fixtures;
- output optimization requires authority/identity/temporal changes;
- prompt/schema variant can reuse another arm's local cached model output;
- actual/projected paid cost crosses $50;
- provider usage does not expose enough detail to distinguish reasoning from visible output and no truthful fallback metric can be defined;
- a second independently useful production behavior appears;
- any corpus, benchmark, gold, production model policy, DungeonMind, APP-STATE, or publication mutation becomes necessary.

Report:

```text
Stop condition:
Invariant clause affected:
Why Stage 4I cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/rebrief:
State-authority update needed:
```
