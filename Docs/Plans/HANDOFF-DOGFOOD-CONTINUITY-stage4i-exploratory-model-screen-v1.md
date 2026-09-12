---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program
  - Flow: DOGFOOD-CONTINUITY / Stage 4I / P2a exploratory screen
  - Direction: DESIGN → CODE → PAID SCREEN → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-v1.md

  ## Verification pointer
  - Base/head: re-anchor after PR #710 disposition; design authored from main 0aa77bf791efa00cb51f45f3c7acd273ac3f351f
  - Verification: zero-API corpus workload census + one Luna/Terra/Sol paid run each + deterministic comparison artifact

  This handoff supersedes the earlier Stage 4I 18-run qualification-style matrix design. This slice is reconnaissance: one run per model, one frozen improved contract, directional conclusions only.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 4I exploratory Luna/Terra/Sol ingestion screen

**Created:** 2026-09-12  
**Status:** DESIGN READY — BLOCKED ON PR #710 DISPOSITION / RE-ANCHOR  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW recovery / ingestion-quality experiment program`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / Stage 4I / P2a exploratory model screen  
**Direction:** DESIGN → CODE → PAID SCREEN → REVIEW  
**Design base revision:** `0aa77bf791efa00cb51f45f3c7acd273ac3f351f` (main after #709; implementation MUST re-anchor after #710 disposition)  
**Design branch:** `dogfood-continuity/stage4i-payload-output-model-ablation-v1`  
**PR title:** `DOGFOOD-CONTINUITY: screen Luna, Terra, and Sol for campaign-memory ingestion`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Frozen benchmark authorities: Stage 4F (#708) and Stage 4G (#709). PR #710 is historical experiment evidence until formally dispositioned.

## §0 Why this supersedes the larger Stage 4I design

The previous design proposed a repeated 2-model × 3-contract matrix. That is too expensive and too qualification-like for the question we need answered next.

The steward wants a cheap reconnaissance screen:

```text
one improved ingestion contract
one run on GPT-5.6 Luna
one run on GPT-5.6 Terra
one run on GPT-5.6 Sol
```

The purpose is not to prove stability. It is to discover whether model choice and output-contract economics separate strongly enough to make the next experiment obvious.

PR #710 already supplied useful historical evidence on Sol/Flex:

```text
execution head: 6a61b63dca555d3d70cac3e38eb3e48c6fc690da
entity recall: 1.0 / 1.0 / 1.0
fact recall:   0.6 / 0.6 / 0.6
stable misses:
  - Karsemine learned the tripod creature is weak to fire
  - Mireward is under active siege/refugee pressure
identity witness:
  - Brin recap/reference coalesced
  - Orik/Orric split in all three runs
mean Sol/Flex cost: about $2.75 per seven-source run
3-run output tokens: 750,827
3-run cached input tokens: 428,678
```

Those results are **historical context**, not a same-head control arm for this screen.

The current output contract also predates this quality/cost program and has never received a responsibility audit. At least one model-emitted field is already known to be redundant: the fact model emits `fact_id`, but persistence deterministically recomputes the durable fact ID from subject + attribute + label.

The current usage helper records aggregate output tokens but not `output_tokens_details.reasoning_tokens`. Therefore #710 does not tell us how much output spend came from visible structured JSON versus model reasoning.

## §1 Mission and invariant

**Mission:** Run one controlled, exploratory ingestion of the frozen seven-source campaign-memory cohort on GPT-5.6 Luna, Terra, and Sol using the same improved fact-extraction/output contract, while measuring enough output composition and real corpus workload to make the next model/contract/cost decision from evidence.

**Merge-ready invariant:** The three paid runs differ only by model identity. They consume identical source bytes, benchmark/gold/temporal authorities, prompt/schema variant, batch size, service tier, compatibility treatment, and execution mechanics; each run reports scored quality, unscored identity/temporal witnesses, token/cache/reasoning/output-density telemetry, and measured cost; no result is promoted as stable from one repetition.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Why only one run per model? | This is reconnaissance. The expected total paid cost is low enough to identify promising model/contract direction before replication. |
| What can one run prove? | Relative shape, obvious failures, output composition, approximate cost, and whether a model is worth replicating. It cannot prove stochastic stability. |
| Why bundle payload preservation + lean output? | We are screening the **candidate ingestion contract** that we might use at corpus scale. #710 remains historical context for the old contract. If attribution between semantic and lean changes later matters, a focused follow-up can isolate it. |
| Biggest confound | Different reasoning volume by model. Capture reasoning tokens separately and keep reasoning effort equivalent. |
| What forces stop? | #710 disposition materially changes the predecessor contract; candidate output fields cannot be proven redundant; or the three models cannot be executed under one equivalent reasoning/service-tier contract. |

## §2 Exact paid screen: 1 × 1 × 1

Exactly three paid arms:

| Arm | Model | Repetitions | Fact contract | Service tier |
|---|---|---:|---|---|
| Luna | `gpt-5.6-luna` | 1 | `payload_lean_v1` | Flex |
| Terra | `gpt-5.6-terra` | 1 | `payload_lean_v1` | Flex |
| Sol | `gpt-5.6-sol` | 1 | `payload_lean_v1` | Flex |

Run in ascending expected cost:

```text
Luna → Terra → Sol
```

Do not stop after a quality result unless there is an infrastructure/provenance failure or paid-budget stop. The value is the three-way comparison.

### Reasoning-effort comparability

As of design time, current OpenAI model documentation reports `medium` as the default reasoning effort for Luna, Terra, and Sol. Prefer explicitly pinning `medium` for all three arms if the post-#710 execution seam supports an experiment-only override without changing production behavior.

If equivalent reasoning effort cannot be pinned or truthfully verified without a new shared production capability, stop and report rather than silently compare non-equivalent requests.

Record actual reasoning-token usage per request/run regardless.

## §3 Frozen input authority

The paid screen consumes exactly the existing Stage 4F/4G development authority:

```text
benchmark_id: c2-mireward-campaign-memory-dev-v1
sources: exactly 7
entity anchors: 6
fact anchors: 5
identity expectations: 2, unscored
temporal expectations: 7, unscored
batch size: 5
fresh isolated store/cache per model
OpenAI Batch API: false
resume: false
force: false
auto-escalate: false
```

Implementation MUST re-anchor after #710 disposition and recompute/pin the exact corpus, gold, temporal, model-policy, prompt/schema, and compatibility-contract fingerprints.

No benchmark/gold/source mutation is permitted.

## §4 Candidate semantic contract — `payload_lean_v1`

The candidate is motivated by #710's repeated failure shape.

Current bad abstraction:

```text
Karsemine used Hunter's Mark to learn the creature's weaknesses and resistances.
```

Required candidate behavior:

```text
When the source states the concrete result of a discovery, investigation,
conclusion, diagnosis, revelation, tactical observation, or current threat,
preserve the answer/payload itself. Do not replace the payload with the mere
fact that learning, discovery, or danger occurred.
```

Illustrative target:

```text
Karsemine learned the tripod creature is resistant to poison and weak to fire.
```

For operational state, preserve direct table-usable truths such as active siege/attack pressure instead of only surrounding symptoms when the source supports the direct assertion.

### Hard semantic boundaries

The candidate must NOT:

- add new fact attributes;
- change entity extraction behavior for quality purposes;
- change benchmark gold;
- inject gold phrases into runtime generation;
- infer unsupported vulnerabilities/threats merely to satisfy anchors;
- implement identity merging;
- implement temporal reasoning;
- change DungeonMind/World publication behavior.

The benchmark remains evaluator-only.

## §5 Output-responsibility audit before paid execution

Before defining the lean structured-output schema, inspect every model-emitted entity and fact field and classify it:

```text
SEMANTIC_REQUIRED
DERIVED_DETERMINISTIC
RUNTIME_CONSTANT
UNUSED
AUTHORITY_SENSITIVE
DEFER_UNCLEAR
```

For each field record:

```text
field name
model-facing schema location
where/if it is consumed
where/if it is persisted
whether a deterministic function can reproduce it
whether removing it changes semantic responsibility
classification
evidence path/test
```

A field may be removed from model responsibility in `payload_lean_v1` only when its classification is one of:

```text
DERIVED_DETERMINISTIC
RUNTIME_CONSTANT
UNUSED
```

and an owning-boundary test proves stored behavior remains semantically equivalent.

Known candidate:

```text
fact_id
current model responsibility: emit a string ID
current persistence behavior: discard/recompute durable ID from subject + attribute + label
expected classification: DERIVED_DETERMINISTIC
```

Do not assume `normalized`, `kind`, confidence, aliases, entity IDs, subject IDs, attributes, interpretation fields, or other fields are redundant. Prove each independently or leave it model-owned.

### Entity contract boundary

Audit entity output fields for future work, but **do not simplify entity model output in this paid screen** unless a field is purely runtime/deterministic and removal is required to make the shared telemetry truthful. Entity recall is already a useful control signal; changing entity semantics would contaminate the model screen.

## §6 Output-token composition telemetry

Extend experiment telemetry so each arm records at minimum:

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

If the API reports another output-token detail relevant to billed output, retain it in the raw receipt and sanitize it into the comparison artifact.

Do not infer reasoning tokens by guessing. Missing reasoning detail must be reported as unavailable.

This telemetry exists to answer:

> Are we paying primarily for semantic structured output, redundant serialization, too many rows, or model reasoning?

## §7 Zero-API full-corpus workload census

Before paid execution, run a deterministic, model-free census over the current original Markdown corpus using the exact ingestion/chunking/compatibility path that the paid screen will use.

No model calls. No World/APP-STATE mutation. No semantic publication.

Report:

```text
Markdown file count
raw source bytes
parseable source count
compatibility-normalized source count
unparseable/rejected source count + failure buckets
evidence-unit count
evidence-unit text bytes
expected entity batches at batch_size=5
expected fact batches at batch_size=5
source/evidence-unit size distribution
largest sources by evidence-unit count
```

This replaces #710's crude `seven-file mean × file count` budget projection with a workload-based planning estimate.

If the exact paid compatibility path cannot census the full original corpus, that is itself a result. Do not silently skip failed files.

## §8 Cost projection

For each model arm, calculate:

```text
measured seven-source cost
measured input/output/reasoning/cache profile
cost per source (diagnostic only)
cost per evidence unit
cost per API call
cost per persisted entity
cost per persisted fact
```

Then project the model's observed workload onto the §7 full-corpus evidence-unit/batch census.

The projection must state its assumptions. In particular:

- the seven-source cohort is not representative of all semantic content;
- model output per evidence unit may change on other document classes;
- cache behavior may change at corpus scale;
- one run is not a variance estimate;
- model quality may change by source type;
- this is planning math, not a budget guarantee.

### Design-time budget prior

Using #710's observed Sol/Flex workload as a rough prior, one seven-source run was about `$2.75`. At comparable token volume, current model price ratios imply an approximate three-run screen on the order of:

```text
Luna:  ~$0.16
Terra: ~$1.62
Sol:   ~$2.75
TOTAL: ~$4.5
```

The improved/lean contract may move those values. Treat `$6` as the expected operational budget and `$8` as a hard stop/rebrief ceiling for the three paid runs unless the steward explicitly authorizes more.

Do not optimize away semantic payload merely to meet the estimate.

## §9 Scored and unscored evidence

### Existing scored authority

For each model report individually:

```text
entity anchor recall: 6 anchors
fact anchor recall: 5 anchors
per-anchor pass/fail
failure bucket for every failure
entity count
fact count
```

No mean or standard deviation is meaningful because there is one repetition per model.

### Mandatory target witnesses

Inspect at least:

```text
Karsemine fire weakness discovery
Mireward active siege/refugee pressure
Brin cook from Edge
Brin refugee leadership
Orik mayor role
```

The first two are #710's known failure witnesses. The latter three are non-regression witnesses.

### Identity + temporal witnesses remain unscored

Continue exposing the two identity and seven temporal witness packets from #708/#709.

Especially record:

```text
Brin recap/reference: same or different resolved identity?
Orik/Orric: same or different resolved identity?
Karsemine discovery: what temporal/evidence representation survived?
North Gate battle vs broader Mireward pressure: what remains distinguishable?
```

Do not create identity or temporal percentages in this slice.

## §10 Candidate-delta audit against #710 historical evidence

Because #710 is not a same-head control, do not present formal deltas as causal proof.

However, for the two known #710 stable failures, the report should place historical and exploratory representations side by side:

```text
source evidence
#710 historical Sol representation
Stage 4I Luna representation
Stage 4I Terra representation
Stage 4I Sol representation
human note: payload retained / payload flattened / unsupported / absent
```

This is qualitative learning evidence, not a scored cross-head experiment.

If Stage 4I Sol recovers both known failures while #710 Sol did not, that strongly motivates a later same-head payload-vs-control replication, but does not itself prove the prompt/output change caused the improvement.

## §11 Decision rubric after the screen

The screen succeeds if it makes the next paid experiment smaller and more obvious.

Illustrative outcomes:

### Luna is surprisingly strong

```text
entities: 6/6
facts: 4/5 or 5/5
known decisive payloads retained
no obvious witness collapse
cost roughly an order of magnitude below Sol
```

Then: replicate Luna + candidate 3× before making corpus-scale claims. Terra/Sol become escalation paths rather than default ingestion models.

### Terra is the quality/cost knee

```text
Terra materially outperforms Luna on important anchors/witnesses
Terra is near Sol on the same evidence
Terra cost is meaningfully below Sol
```

Then: replicate Terra + candidate 3×; keep Sol as escalation for hard source classes.

### Sol is uniquely reliable

```text
Sol recovers important payloads that Terra/Luna miss or distort
```

Then: retain Sol for quality-critical extraction while using the census/output audit to decide whether selective escalation can avoid whole-corpus Sol cost.

### All three fail the same way

Then model scale is probably not the primary bottleneck. Return to extraction/output contract design before paying for repeated model comparisons.

### All three succeed similarly

Then cost dominates. Luna becomes the first candidate for repeated qualification and large-corpus rehearsal.

These are directional decision rules. One run per model cannot establish stochastic reliability.

## §12 Large-corpus architecture question this slice should illuminate

The result should explicitly discuss whether future full-corpus ingestion should likely be:

```text
single-model Luna
single-model Terra
single-model Sol
cheap-first with escalation
source-class routing
or unresolved
```

Do not implement routing in this slice.

The strongest possible outcome is not merely choosing a model. It is learning whether a cheap-first architecture is credible:

```text
Luna handles ordinary extraction cheaply
→ deterministic/eval checks identify misses or risky source classes
→ Terra/Sol are reserved for escalation
```

That hypothesis must be supported by observed benchmark behavior before it becomes architecture.

## §13 Compatibility/frontmatter boundary

#710 exposed a real mismatch between legacy source metadata and current ingestion metadata authority.

For this exploratory screen, use exactly whatever compatibility behavior is formally accepted when #710 is dispositioned/re-anchored. Freeze it across Luna/Terra/Sol.

Do not redesign metadata/frontmatter semantics inside Stage 4I.

The comparison report must preserve the warning that experiment compatibility behavior is not automatically accepted durable World-authority behavior.

If #710 is closed/split such that no accepted exact-seven-source compatibility path exists, Stage 4I is blocked. Do not recreate the lossy adapter silently.

## §14 Suggested implementation shape after re-anchor

The exact lease MUST be rewritten against the post-#710 base before dispatch. Preferred owning paths, assuming #710 lands equivalent experiment infrastructure:

| Action | Path | Purpose |
|---|---|---|
| Create | `extraction_lab/campaign_memory_exploratory_screen_manifest.py` | Strict three-model/one-run manifest. |
| Create | `extraction_lab/run_campaign_memory_exploratory_screen.py` | Sequential Luna→Terra→Sol execution with isolated stores and fail-closed provenance. |
| Create | `extraction_lab/campaign_memory_exploratory_qualification.py` | Quality/cost/output-density comparison + census projection. |
| Create | `extraction_lab/campaign_memory_output_contract_audit.py` | Deterministic field-responsibility ledger/census helpers. |
| Create | focused tests under `tests/extraction_lab/` | Manifest, three-arm identity, telemetry, census, budget, fail-fast, and qualification behavior. |
| Modify | `src/ingestion/fact_extractor.py` | One experiment-selectable `payload_lean_v1` fact prompt/output contract; production default unchanged unless separately accepted. |
| Modify | shared usage telemetry owner if required | Preserve reasoning-token details without changing extraction semantics. |
| Modify | Stage 4I handoff/state docs | Evidence handback only. |

### Expected no-change authority

```text
evals/campaign_memory_development/benchmark.json
evals/campaign_memory_development/gold/**
evals/campaign_memory_development/temporal_expectations.json
corpus/eldyrwild-markdown/**
MODEL_POLICY.json
DungeonMind / APP-STATE / World publication schemas
identity reconciliation semantics
temporal semantics
```

If implementation needs to modify entity extraction semantics, benchmark gold, source corpus, publication, or identity/temporal behavior, stop and split.

## §15 Provenance and execution requirements

The paid manifest must pin at least:

```text
exact repository SHA
three exact model IDs
fact-contract variant/fingerprint
prompt fingerprint
structured-output schema fingerprint
benchmark ID + corpus/gold fingerprints
temporal-intent fingerprint
all seven source SHA-256 values
model-policy SHA
compatibility-mode identity
batch size 5
service tier Flex
reasoning-effort contract
one repetition/model
```

Each model receives a new absent output/store/cache root.

Revalidate source/gold/prompt/schema/policy/repository pins before and after each model run and before final qualification.

Any drift fails the screen. Do not continue later arms after a provenance/infrastructure failure.

A quality failure is data, not a runtime failure: continue to later models when an anchor misses.

## §16 Evidence required before paid execution

At minimum prove deterministically:

```text
dry-run makes zero API calls
exact models are Luna/Terra/Sol and each appears exactly once
run order is Luna → Terra → Sol
same prompt/schema fingerprints across models
same source/gold/temporal fingerprints across models
fresh store/cache root per model
batch size 5
Flex requested equally
reasoning-effort contract equivalent
output audit cannot remove unclassified/unclear fields
fact_id derivation round-trips after model responsibility removal if selected
reasoning-token telemetry handles present and absent details truthfully
full-corpus census makes zero model calls and silently skips zero source failures
budget stop blocks additional paid work above authorized ceiling
benchmark gold is never passed to generation
identity/temporal witnesses remain unscored
```

Then run the zero-API census and inspect it before authorizing the three paid calls.

## §17 Paid evidence record

After the exact implementation head is frozen:

1. dry-run;
2. full-corpus zero-API census;
3. paid Luna run;
4. provenance revalidation;
5. paid Terra run;
6. provenance revalidation;
7. paid Sol run;
8. final qualification;
9. human witness review;
10. sanitized PR record.

Record one compact comparison table:

```text
MODEL | ENTITIES | FACTS | KARSEMINE | MIREWARD | OUTPUT | REASONING | CACHE | COST | TIME
Luna
Terra
Sol
```

Also record projected full-corpus cost from the workload census for each model, clearly labeled as planning estimates.

## §18 Acceptance

Stage 4I PASS means:

- the zero-API corpus census is complete/truthful;
- all three single-run arms completed on one exact implementation head;
- only model identity differed among paid arms;
- `payload_lean_v1` was frozen before paid execution;
- output-field removals were proven deterministic/unused, not guessed;
- reasoning vs visible output is measured when available;
- existing entity/fact benchmark results are reported individually;
- identity/temporal witnesses remain qualitative;
- actual cost/cache/runtime is reported;
- full-corpus planning projections are workload-based and caveated;
- no production publication/model-policy/identity/temporal authority was mutated;
- the report explicitly says one run/model is exploratory and not stability evidence.

There is **no minimum recall threshold required to merge an honest exploratory screen**.

A bad result is successful reconnaissance if it is trustworthy and narrows the next decision.

## Stop conditions

Stop and report rather than broadening if:

- #710 disposition leaves no accepted seven-source execution/compatibility seam;
- re-anchor materially invalidates this design;
- Luna, Terra, and Sol cannot run under equivalent execution/reasoning conditions;
- candidate output simplification requires removing a semantic/authority-sensitive field;
- the semantic payload intervention requires a new fact schema/taxonomy;
- full-corpus census requires mutating original source bytes;
- benchmark/gold must change to make the candidate pass;
- identity or temporal scoring becomes required;
- an independently useful production routing/escalation capability appears;
- paid cost reaches `$8` before all three arms complete;
- provenance/input/prompt/schema identity drifts between model arms.

Report:

```text
Stop condition:
Invariant clause affected:
Why exploratory screen cannot absorb it:
Required evidence missing:
Affected paths/authority:
Proposed successor/re-brief:
State-authority update needed:
```

## §19 Named successor

Do **not** preselect the next model or architecture.

The immediate successor is chosen from the screen:

```text
replicate Luna candidate 3×
OR
replicate Terra candidate 3×
OR
replicate Sol candidate 3×
OR
isolate payload-vs-lean contract causally
OR
return to extraction/output design
```

Only after repeated qualification should the program authorize a full-corpus disposable paid rehearsal.
