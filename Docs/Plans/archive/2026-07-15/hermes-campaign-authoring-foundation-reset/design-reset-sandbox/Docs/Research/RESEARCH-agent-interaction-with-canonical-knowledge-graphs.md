# Research — agent interaction with canonical knowledge graphs

**Date:** 2026-07-14  
**Scope:** primary-source patterns relevant to DungeonBuddy’s graph planning, provenance, observability, source coupling, and claim authority.

## Executive findings

Public GraphRAG systems mostly treat graphs as indexes derived from documents, not as GM-governed canonical world state. They are useful for retrieval planning and iterative graph/document cooperation but do not directly answer DungeonBuddy’s authority question.

The strongest applicable patterns are:

1. use explicit claims rather than presentation summaries as answer support;
2. preserve claim-level provenance and revision/activity lineage;
3. couple graph traversal and source retrieval iteratively rather than forcing one to replace the other;
4. share the retrieved subgraph with the user instead of hiding it behind prose;
5. trace tool/retrieval operations as first-class spans/events;
6. separate asserted graph propositions, inferred conclusions, and source text.

## Sources reviewed

### Microsoft GraphRAG query engine

Primary documentation: [GraphRAG Query Engine overview](https://microsoft.github.io/graphrag/query/overview/)

Relevant design:

- Local Search combines AI-extracted knowledge-graph data with raw text chunks for entity-specific questions.
- Global Search uses community summaries for corpus-wide questions.
- DRIFT expands local search using community information and follow-up questions.

Applicable to DungeonBuddy:

- query mode should vary by user intent;
- entity lookup, global sensemaking, and iterative expansion are not one generic top-k operation;
- graph and source text can be complementary.

Not directly applicable:

- GraphRAG’s graph is an AI-extracted document index; its summaries and edges do not have DungeonBuddy’s governed canon authority.
- community summaries should not be imported as factual authority.

### From Local to Global: A Graph RAG Approach to Query-Focused Summarization

Primary paper: [arXiv:2404.16130](https://arxiv.org/abs/2404.16130)

Relevant design:

- entity graph plus community summaries supports different scales of question;
- partial responses are synthesized into a global answer.

Applicable:

- retrieval planning should distinguish exact object, neighborhood, and campaign-wide sensemaking;
- intermediate retrieval products should remain inspectable.

Limit:

- the paper evaluates document-derived graph summaries, not governed graph claims or human corrections.

### Think-on-Graph 2.0

Primary paper: [arXiv:2407.10805](https://arxiv.org/abs/2407.10805)

Relevant design:

- alternates between graph retrieval and unstructured context retrieval;
- graph entities guide document retrieval, while documents improve reliable graph exploration;
- iterative retrieval supports multi-hop reasoning.

Applicable:

- a shared retrieval state should allow Hermes to alternate graph expansions and source reads;
- graph and source are distinct but cooperating substrates;
- one-shot preflight plus unrelated agent retrieval is weaker than an iterative ledger.

Limit:

- factual authority still originates in benchmark documents/knowledge bases; the paper does not define GM-authored graph-native assertions.

### G-Retriever

Primary paper: [arXiv:2402.07630](https://arxiv.org/abs/2402.07630)

Relevant design:

- “chat with a graph” responses are paired with highlighted relevant graph portions;
- retrieves a compact explanatory subgraph rather than serializing the whole graph;
- explicit subgraph selection supports scale and hallucination reduction.

Applicable:

- the panel should highlight the exact claims/subgraph used by the answer;
- candidate graph context and answer-used graph context must be distinguishable;
- graph retrieval should optimize an explanatory support set, not merely a list of nodes.

Limit:

- the method’s learned/optimization machinery is unnecessary for DungeonBuddy’s current graph size and typed domain constraints.

### W3C PROV

Primary specification family: [PROV Overview](https://www.w3.org/TR/prov-overview/)

Relevant design:

- provenance records entities, activities, and agents involved in producing data;
- supports derivation, versioning, procedures, reproducibility, and provenance of provenance;
- separates the thing asserted from how it was produced.

Applicable:

DungeonBuddy’s claim ledger should explicitly model:

```text
claim/assertion as entity
contribution/extraction/human review as activity
GM/agent/pipeline as agent
source artifact as used entity
revision publication as generation activity
```

This is stronger than using a source-anchor ID as a universal grounding boolean.

Limit:

- full PROV-O/RDF adoption is not required. The conceptual separation is useful even in Pydantic/JSON contracts.

### RDF 1.2 concepts

Primary specification: [RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)

Relevant design:

- an asserted triple is explicitly a claim that a proposition is true;
- graphs may contain asserted propositions, contradictions, and entailments;
- RDF 1.2 supports triple terms, enabling statements about statements.

Applicable:

- the system should identify explicit graph claims as the authority-bearing unit;
- support, provenance, confidence, and review state belong on/around claims;
- arbitrary node summaries are not equivalent to asserted propositions;
- graph/source conflicts and inference should be first-class.

Limit:

- RDF 1.2 was a Candidate Recommendation snapshot in April 2026; DungeonBuddy should not block on RDF serialization or standards conformance.

### OpenAI Agents SDK tracing

Primary documentation: [Tracing](https://openai.github.io/openai-agents-python/tracing/)

Relevant design:

- agent runs are represented as traces with spans for LLM generations, tool calls, handoffs, guardrails, and custom events;
- observability is useful in both development and production;
- sensitive data handling must be deliberate.

Applicable:

- retrieval operations and source reads should be explicit trace events/spans;
- product traces should derive from real execution state, not generic empty `steps` fields;
- custom claim-acceptance events should record what supported the answer;
- secrets, hidden reasoning, and unbounded source content should remain excluded.

Limit:

- OpenAI’s SDK is not the runtime being selected here; the trace model is a reference, not a dependency recommendation.

### Pinned Hermes Agent 0.18.2 source

Primary source: `NousResearch/hermes-agent@861d69c7bba8d2ea6a1cd170e989c901c74d32d1`

Relevant findings:

- `run_conversation` accepts caller-owned conversation history;
- automatic tool calling loops until completion;
- `tool_complete_callback` receives raw function result before optional tool-result persistence/truncation;
- callbacks are best-effort and exceptions are swallowed/logged.

Applicable:

- raw result summarization is a valid current observability boundary;
- DungeonBuddy must still own a durable retrieval ledger because callback-only summaries are too lossy and callback failure is nonfatal upstream;
- persistent Hermes sessions are not required for safe same-thread intent context.

## Synthesized architecture lessons

### 1. Canonical graph claims and document-derived graph summaries are different

Most GraphRAG literature assumes the graph is a retrieval index extracted from text. DungeonBuddy additionally has accepted GM-authored assertions, identity decisions, corrections, and revisions. It should therefore not inherit “documents are always the only factual authority” by default.

### 2. Graph and source should cooperate, not compete

Microsoft GraphRAG and ToG-2 both combine graph structure with text. DungeonBuddy should let accepted claims answer ordinary factual questions while source reads provide exact detail, quotation, provenance inspection, and conflict detection.

### 3. The support unit should be a claim/subgraph, not an anchor count

RDF’s asserted-proposition model and G-Retriever’s highlighted subgraph both point toward explicit answer support. A source anchor is metadata about support, not the supported proposition itself.

### 4. Iterative retrieval needs one shared state

ToG-2’s alternating retrieval and agent tracing patterns are inconsistent with two unrelated retrieval pipelines. A retrieval session/ledger gives the model and UI one inspectable evolving state.

### 5. Provenance is a graph of production, not a badge

W3C PROV suggests preserving contribution, source, reviewer, activity, and revision lineage. DungeonBuddy already has much of this data; the read product should expose it through claim references instead of flattening it to “has anchor.”

### 6. Product observability must answer causal questions

A useful trace should reveal candidate resolution, operations, claim additions, source-read states, and acceptance decisions. Tool names and IDs alone do not explain why an answer was withheld.

## Recommendations adopted

- claim-oriented retrieval representation;
- deterministic entity resolution plus agent-directed bounded traversal;
- iterative graph/source retrieval in one session;
- answer-used subgraph/claims highlighted in UI;
- W3C-PROV-inspired production metadata;
- graph references separated from opened source citations;
- trace operations and acceptance as explicit events;
- no framework/backend adoption solely because it is popular.

## Recommendations explicitly not adopted

- GraphRAG community summaries as canon;
- unrestricted natural-language-to-Cypher/SPARQL model execution;
- a GNN/PCST retrieval stack for the current graph scale;
- full RDF/PROV serialization migration;
- OpenAI Agents SDK migration;
- automatic inference promotion into the canonical graph.
