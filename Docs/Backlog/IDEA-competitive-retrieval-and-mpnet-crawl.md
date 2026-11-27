---
document_id: dmb-idea-competitive-retrieval-and-mpnet-crawl
title: Competitive retrieval benchmark and MPNet-guided decision-model graph crawl
status: research_input
document_class: research_proposal
created_at: "2026-11-27"
authority: none
---

# Competitive retrieval benchmark and MPNet-guided decision-model graph crawl

**Captured:** 2026-11-27, operator discussion of whether DungeonMind/Buddy's retrieval earns its custom complexity.

**Status:** Research capture only. No implementation, production selection, provider spend, external data transfer or write lease is authorized by this note. The [root backlog's deferred controller comparison](../../Backlog.md#deferred-compare-retrieval-controllers-using-existing-native-actions) retains its existing status and promotion conditions; [#3845](https://github.com/Drakosfire/DungeonMindBuddy/issues/3845) is related typed-decision-model work, not an assignment to replace the controller. Re-anchor and select a bounded slice before execution. This capture is independent of current retrieval optimization and release lanes.

## Research question

Can an off-the-shelf retrieval system achieve equal or better evidence acquisition than ordinary Buddy, on the same genuinely novel fictional-world knowledge, at lower cost, latency, maintenance burden or complexity? Separately, can a local MPNet semantic retriever feeding a small typed decision model make graph exploration more effective than the ordinary controller?

Distinguish retrieval performance from DungeonMind's value as a governed, revision-addressable knowledge authority. A competing retriever winning does not establish that it can replace semantic admission, identity, atomic publication, exact revision reads, visibility, or source provenance. Those are separate contracts.

## Hypotheses (all falsifiable)

- H1: A strong hybrid passage baseline or existing GraphRAG system may match or beat Buddy on ordinary questions; a graph is not presumed necessary.
- H2: Reviewed entities, relationships and qualified evidence may improve retrieval specifically on temporal, event-mediated, contradictory, or multi-hop cases relative to passage-only retrieval.
- H3: MPNet ranking may improve seed discovery and bounded frontier selection; an inexpensive decision model may recover more evidence per unit of compute by choosing useful expansion and stopping actions.
- H4: Improvements may come from better extraction, ranking, action policy, or a larger budget rather than the graph itself. Factor these apart; retain negative results.

## Comparators and two evaluation tracks

| Arm | Purpose |
| --- | --- |
| Ordinary Buddy / Jev at pinned revision | Production control; same native actions and ordinary context-ready capture |
| BM25 passage search | Lexical floor |
| Dense passage retrieval (MPNet) | Semantic floor; same encoder as the proposed graph arm |
| Hybrid BM25 + dense + reranker | Strong conventional baseline; disclose reranker model and cost |
| [Graphiti](https://github.com/getzep/graphiti) | Incremental/temporal KG candidate |
| [HippoRAG 2](https://github.com/OSU-NLP-Group/HippoRAG) | Associative graph retrieval and multi-hop candidate |
| [LightRAG](https://github.com/HKUDS/LightRAG) | General graph/vector retrieval candidate, if budget permits |
| MPNet + typed decision model + native graph expansion | Proposed controller/retriever combination |

Optional Microsoft GraphRAG global-question baseline or Neo4j retrieval substrate only if the question being investigated warrants the additional complexity. Pin versions, settings, embedding models, corpus preprocessing and resources; do not assume every framework can import identical graph semantics.

**Track A — end-to-end:** same frozen source bytes, eligible source scope and chronology; each system may build its own representation. Count extraction/indexing, correction/update and serving costs as well as retrieval. Preserve source identities and map returned evidence back to original spans. Do not silently repair failed competitor citations using gold.

**Track B — retrieval isolation:** same pinned, already admitted DungeonMind entities, qualified assertions, links and evidence, with equivalent authorized read access and evidence budget. Compare rankers/controllers over this representation. Export only a scoped read-only fixture if a comparator cannot consume native actions. Document representation losses; exclude incompatible comparisons rather than claiming semantic equivalence. Neither track grants external frameworks write authority. Report results separately.

## MPNet -> decision model -> bounded graph crawl

Use the existing native query, object/claim, neighborhood and selected evidence actions; do not create a new parallel exploration environment. Candidate initial encoder: SentenceTransformers `sentence-transformers/all-mpnet-base-v2`, exact revision pinned before execution. MPNet is a semantic encoder/ranker, not the decision model or an assertion validator. It produces dense vectors for the request and eligible candidate descriptions, not answers.

```text
ordinary question + authorized world/revision/scope
  -> MPNet top-k seed ranking over admitted discovery candidates
  -> bounded candidate IDs + scores + qualification/coverage summaries
  -> typed decision model chooses legal next action(s)
       expand object / neighborhood / read admitted support /
       reformulate search / finish / insufficient evidence
  -> host validates action, scope, identity and source admission
  -> execute existing native actions; collect frontier and evidence
  -> MPNet reranks newly discovered candidates against the original
     question and, optionally, an explicit unresolved subquestion
  -> decision model sees updated coverage, frontier and remaining budget
  -> repeat until sufficient, exhausted or budget-limited
  -> existing writer-ready evidence packet (no writer invocation)
```

Initial discovery should compare embeddings of short entity labels/aliases and typed reviewed observation or assertion descriptions; separate these from source-span embeddings. Retain candidate IDs, exact revision and claim/source linkage. Compare question-only ranking versus bounded controller-generated subqueries; retain original-question scoring to detect drift. Use vectors as ordering signals only, never authority or proof of relevance/entailment. Do not rank hidden or inadmissible text and filter it afterward. Index keys must bind exact source/graph identity, encoder/preprocessing version and authorization scope; no cross-turn reuse of admission decisions.

The controller consumes question, compact ranked legal candidates, selected evidence, visited frontier, coverage gaps and remaining budget. It emits typed existing action arguments or stop/abstain; host validates, deduplicates visited IDs/spans, executes and records all results. No free-form SQL, arbitrary graph writes, new production actions or oracle access. Reserve lexical/exact alias and mandatory authorized support operations as explicit controls so MPNet cannot hide graph evidence. Use current Jev as controller control; optionally compare a small locally hosted typed decision model through the same action contract, without assuming a trained policy exists. Record actual model revision, quantization, device, prompt/schema, batching, and validation failures.

### Ablations

Hold graph snapshot, legal action surface, seed/frontier size, evidence/token budget and maximum rounds constant; tune only on development questions.

| Ranking | Controller | What it isolates |
| --- | --- | --- |
| Current native ranking | Ordinary Jev | Native control |
| MPNet-assisted | Ordinary Jev | Semantic ranking contribution |
| Current native ranking | Local typed decision model | Controller contribution |
| MPNet-assisted | Local typed decision model | Combined candidate |
| MPNet top-k without crawl | None / deterministic stop | Benefit of expansion vs dense retrieval |
| MPNet ranking + bounded deterministic BFS or score-first expansion | Deterministic | Benefit of learned decisions vs cheap graph traversal |

Ablate semantic seed only vs seed + frontier reranking and optional query reformulation once the initial comparison is meaningful. Test fixed-evidence-budget quality and equal-quality cost/latency; separate cold index/encoder setup from warm query time. No hidden additional model calls or gold-aware actions.

## Corpus and benchmark design

Use a private, frozen authorized Elderwyld world/source snapshot as the corpus. Check no-context performance and possible exposure rather than asserting that all models have never seen every fact. Include recently authored or randomized counterfactual facts in a separate controlled fixture if testing novelty. No private story bytes, gold, embeddings, graph exports or credentials in this public repository. Keep private evaluation inputs and artifacts in the existing local lab storage; third-party provider use requires explicit authorization.

The current 70/72 regression reference and the historical opening-batch 72/72, 15/15, 6.54-second median are historical controls, not an independent holdout, interchangeable cohorts, or current release claims. Re-measure ordinary Jev on the same fresh cohort. Use the existing [lab guide](../../evals/README.md), [ordinary benchmark workflow](../Guides/ordinary-benchmark-workflow.md) and existing assessment rather than inventing a second harness.

Construct a fresh independent set with simple direct facts, paraphrases, entity ambiguity, event-mediated multi-hop relations, cross-session state changes (including out-of-order sources), planned vs occurred and source-authority conflicts, and unanswerable/negative questions. Include adversarial but plausible wrong paths and easy questions where a graph may be needless. Gold is independent, source-anchored, private and excluded from candidate construction, prompts, controller traces supplied at inference, and tuning. Split by question and where feasible entity/arc to reduce leakage; record split and source revision. Pre-register sample size, budgets and non-inferiority margin before the held-out run; report uncertainty and paired per-question deltas.

## Measures and adoption logic

Primary retrieval-only outcome: independently assessed required evidence coverage and unsupported/irrelevant evidence at the authorized writer-ready boundary. Use capture-context and exact reopened source spans; report precision/recall, support/qualification errors, abstention and permission/canon failures. A later separately authorized end-to-end run may hold writer/prompt and answer budget fixed to score correctness and citation faithfulness. Do not conflate retrieval quality with writer behavior.

Record median/p95 (and max when sample size is small), cold/warm setup, request-to-context latency, model calls and tokens, local embedding time, DB/tool time, frontier size and redundant expansions, retrieved tokens/spans, indexing/ingestion cost, update latency, resource footprint and maintenance/operational constraints. Preserve trajectories including seeds, scores, selected/rejected actions, stop reason, acquired evidence and unresolved gaps. Separate absent source facts, extraction/admission gaps, rank misses, policy misses, context packaging and citation reopening failures. Record configuration, commit/graph/source pins, seeds, repeated runs where stochastic, and exact assessment.

Do not promote on aggregate speed alone: no permission, provenance or canon regression; no material loss on hard temporal/multi-hop and negative cases relative to pre-registered criteria. If a simpler retriever wins, adopt only the useful component after verifying integration/authority contracts. If deterministic expansion beats a decision model, prefer the simpler policy. If no method wins, keep the existing controller and retain the failure traces.

## First bounded slice when selected

1. Pin one ordinary question and source/graph/admission view in the existing isolated lab, capture the ordinary Jev writer-ready packet and independently reopen its evidence.
2. Compare MPNet-ranked eligible seed candidates with native ranking, then run a bounded crawl using the existing typed actions (ordinary Jev first). Retain rank/crawl traces, coverage, resource and timing results; no production or writer changes.
3. Only after the one-case path is reproducible, select a separate comparative cohort and local decision-model arm; external end-to-end competitors are separate bounded slices.

Exit proof for the first slice: same authorized input, exact source reopening, paired results and failures visible in the existing report format, no gold exposure or new write authority. The larger proposal is not a mandate to implement all arms.

## Relationship to latent memory research

This is a retrieval experiment, not a demonstration of universal latent/Hebbian memory or the Platonic Representation Hypothesis. The same original, source-backed world corpus and independent gold could later support a separate frozen-model external associative-memory study. Establish conventional retrieval baselines first; do not interpret semantic similarity or successful graph crawling as cross-model activation interoperability.

Related historical input: [Graph exploration controller lab](BACKLOG-graph-exploration-system-one-controller-lab.md); its superseded exploration environment is not revived.
