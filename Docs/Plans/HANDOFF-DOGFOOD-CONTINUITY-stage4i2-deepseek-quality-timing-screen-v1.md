---
pr_body_template: |
  ## Active experiment handoff
  - Workstream: DOGFOOD-CONTINUITY / Stage 4I.2 ingestion convergence
  - PR: #711 experimental notebook
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i2-deepseek-quality-timing-screen-v1.md`
  - Dispatch base: `2eb373757e1a74e48a8e60e072c655a0d3538924`

  ## Forcing question
  On the selected whole-document contract, which cheap execution gives the GM the best usable campaign-memory objects and prose per dollar and per second: Luna Flex, Luna Standard, or DeepSeek V4.1 Flash through OpenRouter?

  #711 remains an unmergeable experimental notebook. The result of this slice is evidence for the Stage 4J full-corpus ingestion decision, not production code to merge by inertia.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 4I.2 DeepSeek quality + timing screen

**Created:** 2026-09-12  
**Status:** READY TO EXECUTE ON PR #711  
**PR / branch:** `#711` / `dogfood-continuity/stage4i-exploratory-model-screen-impl`  
**Dispatch base:** `2eb373757e1a74e48a8e60e072c655a0d3538924`  
**Flow:** DOGFOOD-CONTINUITY / ingestion convergence  
**Direction:** RE-ANCHOR → PROVIDER ADAPTER → DETERMINISTIC GATES → THREE PAID ARMS → QUALITY/TIMING REVIEW → DECISION CHECKPOINT

> Repository law: `AGENTS.md`. This is an explicitly non-merge experimental notebook lane. It exists to produce evidence for `HANDOFF-DOGFOOD-CONTINUITY-stage4j-initial-quality-corpus-materialization-v1.md`; it is not permission to promote experiment plumbing to production.

---

## §0 Steward ruling — experiment notebooks and cleanup

### Current PR roles

```text
PR #710
  role: frozen historical baseline / salvage evidence
  state: keep open temporarily for discoverability
  writes: NO new implementation capability

PR #711
  role: active ingestion-convergence experiment notebook
  state: receives bounded experimental code + paid receipts + interpretation
  merge: NO

Stage 4J
  role: next clean production implementation PR
  base: then-current main
  opens only after an evidence-backed corpus-ingestion decision is frozen
```

### Open-PR budget

At most **two open experimental notebook PRs** may exist at once.

New experiments normally continue on #711. Do not open one PR per paid run.

A new experimental PR is justified only when the next question requires assumptions/runtime plumbing that would make #711's prior experiments materially uninterpretable. Before opening such a PR, close/supersede #710 so the open experimental notebook count remains <=2.

### Mandatory cleanup checkpoint

Immediately after this slice, ask:

> Do we now have enough evidence to choose an initial-quality full-corpus ingestion profile?

If **YES**:

1. post `CORPUS INGESTION DECISION — FROZEN` on #711 (and cross-link #710);
2. record model/provider, prompt/context contract, authority treatment, identity/enrichment strategy, measured quality debt, timing, and projected cost;
3. close #710 and #711 **unmerged / superseded**;
4. re-anchor Stage 4J on current `main`;
5. implement only the selected production capability cleanly from main.

If **NO**:

- keep #711 as the one active notebook;
- name the single unresolved decision question;
- run only evidence-selected follow-up experiments;
- do not open Stage 4J yet.

Experiment code is disposable by default. Useful ideas graduate by being reimplemented/cherry-picked deliberately under the Stage 4J write lease, not because #711 accumulated them.

---

## §1 Mission

Run one controlled, cheap comparison on the **already-selected whole-document semantic-context contract** that separates practical model/provider quality from OpenAI Flex scheduling effects.

Execute exactly three complete seven-source arms on one frozen implementation head:

```text
A. GPT-5.6 Luna      / OpenAI / Flex
B. GPT-5.6 Luna      / OpenAI / Standard (no Flex)
C. DeepSeek V4.1 Flash / OpenRouter / pinned DeepSeek provider
```

All three use the same:

```text
7 frozen Mireward campaign-memory sources
whole-document semantic context
paragraph evidence units for local citation
payload_lean_v1 fact contract
batch size 5
same entity/fact prompts and schemas
same compatibility treatment
same request topology
same local concurrency
same isolated-store/cache policy
same benchmark authorities
```

### Forcing question

> **Which cheap execution gives the GM the highest-quality campaign-memory objects and prose at acceptable end-to-end latency and corpus-scale cost?**

Mechanical anchor recall remains useful but is no longer sufficient as the quality verdict.

---

## §2 What we already learned — do not rerun the previous question

The Luna paragraph-vs-whole-document ablation has answered its directional question.

Selected context direction:

> **Reason globally, cite locally.** Supply the exact frontmatter-stripped authored document as semantic context while retaining granular evidence-unit anchors for provenance.

Current valid Luna/Flex comparison evidence:

```text
                              paragraph      whole document
API calls                         84              84
wall time                     385.4s          333.4s
model-stage time              374.5s          323.3s
input tokens                  254,231         566,197
output tokens                 201,889         173,196
reasoning tokens               67,338          50,773
visible output                134,551         122,423
cost                           $0.1337         $0.1475
```

The seven unique documents are only ~68,383 characters / ~11,193 whitespace words. The 566K input total is cumulative request traffic caused by retransmitting document and prompt context across 84 entity/fact requests. Do not describe it as unique corpus size.

Do **not** optimize the 84-request topology in this slice. Its inefficiency is now known and belongs in the backlog/Stage 4J design decision. Changing topology before DeepSeek would destroy comparability.

First implementation commit must ensure `Backlog.md` contains a concrete item to measure and optimize the relationship among:

```text
system/schema prompt size
unique document size
whole-document retransmission multiplicity
batch/evidence-unit topology
provider prompt caching
service tier
concurrency
reasoning vs visible output
wall time / request latency / effective throughput
cost
```

The backlog item must distinguish **unique corpus size** from **cumulative API token traffic**.

---

## §3 Paid experiment contract

Exactly one repetition per arm:

| Arm | Model | Provider | Tier/routing | Context |
|---|---|---|---|---|
| A | `gpt-5.6-luna` | OpenAI | Flex | whole document |
| B | `gpt-5.6-luna` | OpenAI | Standard / no Flex | whole document |
| C | `deepseek/deepseek-v4.1-flash` | OpenRouter | DeepSeek provider pinned, no fallback | whole document |

Run all three on the same exact executable head after deterministic gates pass.

Recommended order:

```text
DeepSeek
→ Luna Standard
→ Luna Flex
```

DeepSeek is the new information and should not be delayed behind redundant Luna work. Order is not evidence of model rank.

### Luna constants

For both Luna arms:

```text
reasoning effort: medium
same OpenAI Responses seam
same prompts/schema/context
same concurrency
same fresh local store/cache
```

Only `service_tier` may differ between Luna A/B.

### DeepSeek constants

Use the operator-provided environment variable:

```text
DUNGEONBUDDY_OPENROUTER
```

Requirements:

- never print, persist, commit, hash, or include the key in receipts;
- preflight only presence/non-empty state;
- OpenRouter base URL: `https://openrouter.ai/api/v1`;
- model: `deepseek/deepseek-v4.1-flash`;
- use the OpenRouter Responses API where practical so request/usage semantics stay close to the current path;
- pin routing to the **DeepSeek provider**;
- disable provider fallbacks;
- require requested parameters when supported by the routing contract;
- request OpenRouter routing metadata and record the actually selected provider/endpoint identity;
- use the same Pydantic/JSON schema contract as Luna and locally validate every response before persistence;
- do not add an LLM repair/retry model for malformed semantic output.

If provider-side strict schema enforcement differs, that is an observed transport capability difference, not permission to weaken local validation.

Reasoning effort:

- request `medium` if the pinned DeepSeek endpoint accepts an equivalent reasoning control;
- if it does not, record the exact supported/default behavior and continue as a **practical execution comparison**, clearly marking reasoning-contract non-equivalence;
- do not block the whole DeepSeek run merely because provider reasoning controls are not byte-for-byte OpenAI semantics.

---

## §4 Quality is the primary decision surface

The old aggregate anchor score is retained, but final interpretation must prioritize **what the GM would actually want in front of them**.

### 4.1 Frozen mechanical metrics

For each arm report:

```text
entity anchors / 6
fact anchors / 5
persisted entity count
persisted fact count
identity expectation observations
existing temporal witness observations
```

Do not edit gold to improve agreement with any model's wording.

### 4.2 Object-quality witness set

Use the same named human witnesses across all arms:

```text
Brin Holloway
Orik / Orric Tane
Karsemine
Mireward / Mireward Reach
Hesta Bramblewood
Thrin
Tripod creatures / S23 tactical target
one S25 hybrid/threat object with meaningful crisis context
```

Produce a side-by-side review packet containing, for each witness:

```text
canonical/sibling entity IDs
aliases
source/session evidence
all high-signal facts
representative low-signal facts
relationships/entity refs
source authority / truth state
relevant temporal fields
```

No evaluator LLM. The packet is for human review.

### 4.3 Human quality dimensions

For each witness/model, evaluate:

```text
IDENTITY_COHERENCE
  one thing stays one thing; alias/spelling drift does not create needless duplicates

FACTUAL_COMPLETENESS
  the important source-supported campaign memory is present

SPECIFICITY
  facts preserve the answer/payload, not merely "something happened/was learned"

ATOMICITY
  facts are independently useful rather than overloaded keyword paragraphs

PROSE_QUALITY
  labels read naturally, are self-contained, concise, and useful at the table

GM_USEFULNESS
  the stored facts answer "what do I need to remember about this right now?"

CONTINUITY_PROTECTION
  small declared facts that future prep should not casually contradict are retained

AUTHORITY_CORRECTNESS
  prep/planning/played truth remain distinguishable

TEMPORAL_SHAPE
  historical event, durable background, current pressure, and ended state are not flattened together

NOISE
  generic, redundant, implementation-shaped, or low-value facts do not drown useful memory
```

Use small ordinal labels, not fake precision:

```text
GOOD
MIXED
POOR
NOT_EVALUABLE
```

Each rating requires one concrete source/output witness.

### 4.4 Continuity-protection proxy

The literal Stacy example is the product north star but is not currently located in the frozen seven-source benchmark. Do not fabricate it into this corpus.

Within the existing cohort, identify facts that function the same way: minor but durable declarations such as species, role/title, relationships, named identity, stable background, or explicit learned knowledge.

For each arm report:

```text
continuity-critical facts expected from source
recovered
attached to correct identity
contradictory competing values, if any
buried only on sibling/fragmented identity, if any
```

This is a proxy for the future forcing benchmark:

> If a GM later plans something that casually contradicts a previously declared minor fact, is enough structured memory present for DungeonBuddy to warn them?

Do not claim the Stacy benchmark itself has passed until its actual source material is found and frozen.

---

## §5 Deterministic/local enrichment diagnostics — no extra model calls

The comparison is allowed to ask how much useful structure can be recovered **after extraction without a larger model**.

These diagnostics are analysis-only and must not mutate the compared stores before scoring.

### 5.1 Alias/identity candidates

Using existing names/aliases and local deterministic or bounded fuzzy matching, report obvious reconciliation candidates such as:

```text
Orik ↔ Orric
Mireward ↔ Mireward Reach
minor spelling drift
exact alias already present on another minted entity
```

For each arm distinguish:

```text
RAW_MODEL_IDENTITY
POSSIBLE_LOCAL_RECONCILIATION
```

Do not silently merge entities in the experiment store.

### 5.2 Cross-subject composition candidates

Detect cases where useful campaign memory exists across separate facts/entities and could be composed later, e.g.:

```text
Karsemine learned weaknesses/resistances
+
Tripod defenses = resistant to poison / weak to fire
```

Report whether each arm preserves enough source-linked structure to derive the composed memory without another remote LLM call.

### 5.3 Continuity-salience candidates

Using existing fact attributes/value metadata only, produce an experiment-only lens identifying plausible:

```text
continuity constraint
active pressure
callback hook
portrayal anchor
texture
```

This is a diagnostic ranking/classification artifact, not a schema migration and not a DungeonMind write.

Do not add these categories to durable production facts in #711.

---

## §6 Timing and throughput — distinguish pipeline speed from model decode speed

The timing report must not repeat the earlier ambiguity around "tokens/sec".

For each arm capture:

```text
end-to-end wall time
entity-stage wall time
fact-stage wall time
API call count
max configured concurrency
per-request elapsed time: p50 / p95 / max
per-source elapsed time
input tokens
cached input tokens
uncached input tokens
output tokens
reasoning tokens, if exposed
visible output tokens
parsed structured-output bytes
persisted rows
```

Derive and label separately:

```text
PIPELINE EFFECTIVE THROUGHPUT
  cumulative input tokens / wall second
  cumulative output tokens / wall second
  visible output tokens / wall second
  persisted rows / wall second

REQUEST EFFECTIVE RATE
  output tokens / request elapsed second
  report distribution, not just aggregate

PROVIDER-REPORTED INFERENCE METRICS
  TTFT / generation throughput / selected endpoint if OpenRouter exposes them
  never substitute these for pipeline throughput
```

A concurrent 500 output-tokens/sec pipeline is **not** evidence that one request decoded at 500 tokens/sec.

### 6.1 Request amplification

Record the deterministic topology for every source:

```text
unique source bytes
unique evidence units
entity requests containing that document
fact requests containing that document
whole-document retransmission count
cumulative model input tokens attributed to that source when recoverable
```

Report:

> **unique authored corpus size != cumulative API input traffic**

Do not optimize this topology until after the three comparable arms are complete.

### 6.2 Flex interpretation

Luna Flex vs Luna Standard answers a practical service-tier question.

Because provider prompt-cache state is not perfectly isolatable, report each arm's cache fraction beside timing. If the cache fractions differ materially, do not attribute the full wall-time delta to Flex.

One run/arm is directional. No p-value/stability claim.

---

## §7 Cost

Record actual provider-billed or best available measured cost per arm.

For OpenRouter prefer actual response/generation cost metadata when available over a hard-coded calculator. Also record the observed pricing/routing identity used for the run.

At minimum report:

```text
cost/run
cost/API call
cost/evidence unit
cost/persisted useful witness fact where human review can support it
input/cache/output token mix
projected parseable-corpus cost using the existing 5,336-EU census
```

Do not project the 152 currently rejected Markdown sources as though they were successfully ingestible. Report parseable-corpus projection and unresolved-source coverage separately.

Hard paid budget for this slice: **$3 total additional spend**. Expected spend should be far below this. Stop before a call that would knowingly cross the ceiling.

---

## §8 OpenRouter adapter boundary

Implement the smallest experiment-only provider seam necessary to run existing entity/fact extraction through OpenRouter.

Preferred shape:

```text
existing prompt builders + Pydantic schemas
              ↓
provider-neutral experiment request description
          ↙                 ↘
OpenAI Responses          OpenRouter Responses
Luna                      deepseek/deepseek-v4.1-flash
          ↘                 ↙
       same local validation
              ↓
        existing store path
```

Do not duplicate entity/fact semantic prompts for DeepSeek unless the API contract absolutely requires a serialization-only transform.

Do not create a production model router in this PR.

Provider differences that must be surfaced, not hidden:

```text
strict structured-output support
reasoning token reporting
prompt-cache reporting
actual selected endpoint/provider
retry/rate-limit behavior
usage/cost metadata
```

If OpenRouter Responses proves incompatible, a Chat Completions adapter using the exact same system/user text and JSON schema is allowed as a bounded fallback. Record the transport difference prominently. Local Pydantic validation remains mandatory.

---

## §9 Files in scope — exclusive write lease

Expected paths:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i2-deepseek-quality-timing-screen-v1.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-impl-v1.md   # evidence pointer/status only
Backlog.md

extraction_lab/**stage4i* or **campaign_memory*                         # experiment orchestration, timing, quality packet, comparison
src/ingestion/entity_extractor.py                                      # narrow provider-client seam/telemetry only
src/ingestion/fact_extractor.py                                        # narrow provider-client seam/telemetry only
src/llm/api_client.py                                                  # only if existing wrapper must admit OpenRouter Responses cleanly
tools/batch_ingest_corpus.py                                           # experiment provider/tier selection and timing plumbing only
focused tests for touched paths
```

Bounded discovery exception: at most **two additional runtime paths** under `src/llm/**` / `src/ingestion/**` if they are the actual owner of request timing/provider construction. Record why.

Do not modify:

```text
MODEL_POLICY.json
frozen benchmark/gold/temporal authorities
corpus source bytes
DungeonMind schemas or publication
APP-STATE
production identity reconciliation
production temporal model
Stage 4J implementation
```

A need for any of those is a stop/rebrief.

---

## §10 Deterministic gates before paid execution

At minimum prove:

1. `DUNGEONBUDDY_OPENROUTER` is checked for presence without exposing its value;
2. OpenRouter dry-run/preflight performs zero paid generation calls where possible;
3. model slug is exactly `deepseek/deepseek-v4.1-flash`;
4. provider routing is pinned to DeepSeek with fallback disabled;
5. selected provider identity is captured/validated in the real response path;
6. Luna Flex and Standard differ only in tier;
7. all three arms share exact source/prompt/schema/context fingerprints;
8. whole-document mode is selected for all arms;
9. request count/topology is unchanged across arms unless provider failure itself is being reported;
10. local Pydantic validation rejects malformed/missing semantic fields;
11. no automatic LLM response-healing/repair call is introduced;
12. fresh isolated store/local cache/output root per arm;
13. per-call elapsed timing is collected without changing semantic prompts;
14. missing provider reasoning/cache metrics remain null/unknown rather than zero by invention;
15. quality-packet generation makes no evaluator/model API calls;
16. local reconciliation/composition diagnostics do not mutate raw stores;
17. budget guard stops before $3 additional spend;
18. repository/source/eval authority pins are revalidated before and after every paid arm.

Run all focused tests, relevant `tests/extraction_lab`, scoped Ruff, and `git diff --check` before money is spent.

---

## §11 Exact execution sequence

```text
A. RE-ANCHOR / DOCUMENT
1. re-read AGENTS.md + this handoff
2. confirm #710 = frozen evidence, #711 = active notebook
3. add the required prompt/document/topology/tier/latency backlog item
4. preserve corrected four-attempt Luna context-ablation accounting in the #711 evidence record

B. IMPLEMENT / ZERO-COST
5. implement minimal OpenRouter provider seam
6. add per-call/per-source timing telemetry
7. add side-by-side GM object/prose quality packet
8. add local identity/composition/continuity-salience diagnostics
9. run deterministic tests / Ruff / diff-check
10. freeze executable head

C. PAID — SAME HEAD / SAME CONTRACT
11. DeepSeek V4.1 Flash ×1
12. revalidate pins
13. Luna Standard ×1
14. revalidate pins
15. Luna Flex ×1
16. revalidate pins

D. QUALIFY
17. run frozen mechanical benchmark per arm
18. generate object/prose review packet
19. generate timing/request-amplification report
20. generate local deterministic-enrichment diagnostics
21. generate cost + 5,336-EU parseable-corpus projection
22. perform human witness review

E. DECISION CHECKPOINT
23. answer the §0 cleanup question
24. if evidence is sufficient, freeze corpus-ingestion decision and begin notebook cleanup
25. otherwise name exactly one unresolved decision question before any further experiment
```

Documentation-only evidence commits after paid execution are allowed if mechanically proven not to change executable/config/source/eval inputs. Record execution SHA and evidence SHA separately.

---

## §12 Required handback

Return with one compact comparison:

```text
ARM | QUALITY SUMMARY | ENTITY | FACT | OBJECTS | FACTS | WALL | P50 REQ | P95 REQ | OUT TOK/S* | COST
Luna Flex
Luna Standard
DeepSeek V4.1 Flash

* explicitly label as pipeline-effective or request-effective
```

And include:

```text
exact execution SHA
exact provider/model/endpoint identity
prompt/schema/context fingerprints
request topology
source count / unique bytes / evidence units
actual run count including failed/partial attempts
API call count including failed/partial paid calls
actual cumulative spend including failed/partial calls
per-source timing/cost where recoverable
cache behavior
reasoning vs visible output where available
quality packet for named witnesses
continuity-protection proxy results
identity/composition diagnostics
known weaknesses by arm
parseable-corpus cost/time projection
whether evidence is sufficient to freeze Stage 4J ingestion profile
```

Do not collapse failed paid attempts out of total spend/time accounting. Separate `attempted`, `complete`, and `valid-for-comparison` counts.

---

## §13 Interpretation rules

This is a reconnaissance screen, not stability qualification.

One run per arm may support:

- obvious prose/object-quality differences;
- practical latency differences;
- order-of-magnitude price differences;
- obvious provider/schema failures;
- selecting what deserves productionization or one final replication.

It cannot support:

- stochastic stability;
- precise full-corpus runtime guarantees;
- a claim that Flex alone caused all latency difference;
- production routing thresholds;
- perfect continuity protection.

The preferred arm is **not automatically the highest anchor score**.

A cheaper model wins if its raw extraction plus cheap deterministic/local reconciliation provides equivalent or better GM-usable memory.

A more expensive model earns its premium only when it preserves materially better campaign memory that the cheaper path cannot recover deterministically.

---

## §14 Decision gate into Stage 4J

Evidence is sufficient to freeze the initial full-corpus plan when we can state, with concrete witnesses:

```text
1. which model/provider/tier is the default;
2. whether any escalation model is actually necessary;
3. whole-document vs other semantic context contract;
4. current request topology debt and whether it blocks first ingestion;
5. expected parseable-corpus dollars and approximate runtime;
6. known identity/alias debt and bounded local reconciliation plan;
7. known cross-subject composition debt;
8. source-authority/frontmatter handling required before publication;
9. object/prose quality we are willing to call "initial quality";
10. known continuity-protection gaps;
11. exact excluded/rejected source coverage;
12. rollback/idempotency/publication plan handled by Stage 4J.
```

The decision does **not** require perfect objects. It requires known, measured imperfections and a reproducible profile good enough to put one broad corpus into durable DungeonMind for normal dogfood.

---

## §15 Stop conditions

Stop and hand back rather than widening if:

- OpenRouter requires a production-wide model abstraction redesign;
- the DeepSeek adapter needs benchmark/source mutation;
- provider routing cannot be observed well enough to know what served the run;
- provider fails local structured validation repeatedly and a semantic repair model would be needed;
- comparison requires changing the selected whole-document contract;
- a new durable schema field is required;
- cumulative new spend would exceed $3;
- any paid-arm source/prompt/schema/code fingerprint drifts;
- experiment results reveal a new authority boundary that must be resolved before publication.

Quality differences, slower/faster runs, or a poor DeepSeek result are **not** stop conditions. They are the experiment.
