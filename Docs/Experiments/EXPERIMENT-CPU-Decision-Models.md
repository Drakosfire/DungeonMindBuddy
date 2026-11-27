# CPU decision models for Buddy

- **Experiment ID** `buddy.cpu-decision-models.v1`
- **Status** Registered, unrun
- **Owner** Buddy decision and benchmark harness

## Questions

1. Can a local open-weight model match Jev on first action, target choice and
   acquisition intent within the CPU and memory Buddy can afford?
2. With Jev held fixed, can MPNet passage candidates reduce or better seed
   Graph crawls at the same evidence budget?
3. If both changes qualify independently, does their combination preserve
   evidence quality while improving latency?

Stock checkpoints come first. Fine-tuning, production routing, writer quality
and deployment are outside this experiment.

## A · Decision model comparison

Run Jev 1.14.0 as control, then Laya (~420M, ONNX), Kev 0.8B and Perplexity
Decider Flash v1.3 (~5B). These published weights use Apache 2.0. Pin the
upstream revision, weight digest, tokenizer, typed adapter, runtime, precision
and quantization before capture. Use the publisher checkpoint as the numerical
reference for a converted build. Verify decision-head support and compare its
outputs on a development subset before timing a quantized candidate. Record
unsupported formats as such. Publisher Flash v1.2 GGUF may enter as a separate
arm with its own results. The larger Decider and generative models are outside
the initial CPU cohort.

- [Laya CPU packaging](https://huggingface.co/verdict-models/laya)
- [Kev 0.8B](https://huggingface.co/jaredpalmer/kev-0.8b)
- [Decider Flash v1.3](https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.3)
- [Publisher Flash v1.2 GGUF](https://huggingface.co/perplexity-ai/pplx-decider-flash-gguf-v1.2)

Freeze the [Right Action baseline](../../evals/right-action-baseline.md)
and build a case manifest from its ordinary decision inputs. Account for all
90 specifications and list each exclusion with its reason. A case qualifies
for this comparison when the exact decision-time state, offered options and a
reviewed expected decision can be recovered. Operator-only controls remain
execution evidence. The 25 known first-choice observations are starting
evidence. Reuse a retained Jev result only when its version, input, option
order and decision contract match. Record missing controls explicitly and
capture a fresh matching control only for that gap. A case with an unavailable
execution owner can still enter the offline decision test if its valid choices
and exact input are available.

Pin the user turn, earlier context available at dispatch, legitimate surface
and selection, offered actions, and local aliases for targets. Freeze expected
acceptable action, target and acquisition choices before inspecting model
results. Allow legitimate alternatives and explicitly label when clarification,
deferral or refusal is required. Keep Gold and evaluator annotations outside
every model input. For each model translate the same state and option meanings
to its native typed format. Preserve option order in the primary comparison.
Use one fixed permutation on a development subset to measure order sensitivity.
The first-turn route runs before any catalog or Graph acquisition. Use a
separate continuation stratum for turns with already loaded context.

Report paired action, target and acquisition correctness by action and tier,
with confusion counts, invalid or unsupported results, abstention, wrong
retrieval skips, unnecessary acquisition and Jev agreement. Count every
attempted case, including failures. If calibration is tested, fit thresholds on
development families and freeze them before evaluating untouched families.
Report accepted coverage and error together. Keep the initial comparison
single-model per arm, including turns a candidate cannot resolve.

## CPU envelope and timing

Run on the local Ryzen 9 9950X host. Capture the serving host profile read-only
before freezing the primary envelope: CPU model and instruction flags, physical
cores and SMT topology, Buddy's effective CPU quota and cpuset, available model
memory after leaving Buddy and database headroom, and representative concurrency.
Record the source and date. If the profile is unavailable, use a provisional
sensitivity profile of **2 physical cores / 4 GiB** and **4 physical cores /
8 GiB**. Label those runs as local capacity tests. Server-equivalent latency
claims require matching the resource profile and explicitly accounting for
differences in CPU architecture and memory bandwidth.

Apply limits with a cgroup or container cpuset, CPU quota and hard memory cap,
with swap disabled for the worker. Pin physical cores using topology, avoiding
accidental SMT siblings in the single-thread-per-core profile. Fix runtime
threads to the allocation and disable GPU offload and accelerator access.
Record effective limits, precision, threads, model file size, peak RSS and
cgroup memory, host load, CPU throttling and any OOM. Keep Buddy/database workload
and threading fixed across paired runs. Run arms serially to avoid competing
model workers. Check per-case concurrency at **1 and 2** simultaneous requests;
reuse the same seeded schedule across candidates.

Measure request ingress to validated typed decision, separating queue,
tokenization, inference and validation. Warm each model with an excluded
request, then record three timed passes over the same cases in counterbalanced
order. Record one cold process start separately, including model load; state
whether files were already in the OS cache. Report p50 and p95, throughput and
raw per-attempt durations, stratified by input length. Jev uses the same
measurement boundary and submission schedule; its network time is part of the
control. Runs that exceed the resource cap or fail schema validation stay in
the report. Do not silently retry failed trials.

## B · MPNet candidates before optional crawl

Freeze the prior ordinary Jev retrieval control, eligible corpus and Graph
revisions, exact passage/citation locators, and writer evidence budget. Use the
same writer-off harness and Q/D/F cases, plus the
[different-source control](../../evals/negative_retrieval/fixtures/development.json).
Reuse comparable retained runs. Pin the MPNet revision, tokenizer and chunking,
index digest, distance and tie order. Freeze **top 10 unique passage candidates**
as the initial treatment, with bounded excerpts and host-resolved entity/Event
aliases. Embed corpus chunks once. Measure indexing time and size separately
from online query encoding, lookup and admission. Turns already decidable from
conversation stop before embedding search.

| Arm | Behavior |
| --- | --- |
| Control | Ordinary Jev retrieval |
| Treatment | MPNet candidates, then Jev chooses passage-only, open a missing source, or crawl from a selected anchor |
| Diagnostic | MPNet passage selection within the same delivery budget, with no Graph expansion |

At writer-ready, measure required Gold items, every delivered citation reopen,
evidence tokens, crawl frequency, Graph reads and elapsed time. Count wrong
skips, unnecessary crawls, wrong start anchors and stage of evidence loss.
Separate unindexed or inadmissible inputs from ranking misses and controller
misses. Use the ordinary context builder. Compare budget compliance and measure
both p50 and p95 end to end, including the semantic search and decision calls.

## Acceptance and experiment record

- **A advances** when the candidate matches or exceeds Jev's paired joint
  action/target/acquisition result and introduces no new wrong write targets,
  forbidden actions or missed required retrieval on the held-out cohort. Under
  the primary CPU envelope, warm p95 at concurrency 2 must improve at least 20%
  over Jev with no OOM. Report paired wins and losses and exact denominators.
  If confidence intervals are too wide to establish an improvement, mark the
  result inconclusive. Inspect abstentions and unavailable cases separately.
- **B advances** when the treatment preserves every control-covered Gold item
  per case, reopens all delivered citations, stays within the same budget and
  improves median writer-ready time by at least 15% without worsening p95.
  The different-source control must still open the required different source.
  Record partial findings even when the whole arm fails.
- **Combination** runs only after both pass independently. Compare it against
  their individual winners and ordinary Jev on the same frozen inputs, applying
  both quality gates at their owning boundaries.
- **Fine-tuning** is a separately registered experiment if the stock candidates
  are fast enough and show a repeatable, correctable error class. Fit only on
  reviewed development cases and preserve held-out scenario families.

Use the [shared harness](../../evals/README.md) and its retained report format.
Keep one owned App clone for the mounted run, shared Core read-only, Gold
local, and primary data untouched. Store the manifest, hardware profile, paired
results, failures and teardown proof on Projects. Record hashes, run order,
missing measurements, dispositions and exact commands. A deployment claim
requires a later check on the serving hardware.
