# Anchor: DungeonBuddy Graph Retrieval, Ontology, and DOM Graph RAG Direction

Version: 0.1
Status: Working anchor
Purpose: Establish the durable thesis, design direction, skepticism, and migration path for moving DungeonBuddy from route-indexed, source-grounded retrieval toward a graph-aware knowledge layer.

## 1. Core Thesis

DungeonBuddy should not chase “Graph RAG” as a branding layer. It should evolve its existing retrieval architecture into a source-grounded, provenance-preserving knowledge graph system whose purpose is high-precision context enrichment for GM planning, recap reasoning, campaign memory, and evidence-backed answers.

The current system is already closer to a graph architecture than a naive vector RAG system. It has source-grounded units, normalized campaign routes, session memory, breadcrumbs, manifest retrieval, hub routing, evidence admission, and citation discipline. The missing layer is not “graph vibes.” The missing layer is an explicit, queryable topology of entities, source units, routes, sessions, facts, claims, locations, artifacts, threats, player actions, unresolved hooks, and evidence roles.

The long-term direction is a hybrid neuro-symbolic retrieval architecture: lexical and vector retrieval remain useful, but they become semantic helper systems. The graph becomes the authority-preserving structure that decides what things are, how they relate, what source supports them, when they were true, and whether they are admissible for a given planning or answer task.

## 2. The Important Distinction

There are at least four related but different ideas in play:

1. Baseline RAG: retrieve chunks by vector similarity, BM25, reranking, or hybrid search, then send the chunks to an LLM.

2. Microsoft-style GraphRAG: extract entities and relationships from a corpus, cluster them into communities, summarize those communities, and use local/global graph search to answer entity-specific or corpus-wide questions.

3. DOM Graph RAG: exploit pre-existing document structure, especially structured topic/component content, by converting the document object model and metadata into a graph. Retrieval uses the graph as the source of content truth, with vectors as a semantic helper.

4. Formal semantic web architecture: represent knowledge using RDF triples, RDFS/SKOS/OWL ontologies, SHACL validation, named graphs, provenance models, and SPARQL queries.

DungeonBuddy’s best path is not to imitate any one of these wholesale. The right path is a DungeonBuddy graph IR that can eventually serialize to RDF/JSON-LD and be queried through SPARQL-like patterns, while preserving the system’s current strengths: source grounding, route normalization, session-bounded recall, evidence admission, and answer traceability.

## 3. What Is Already Proven Enough

Graph-augmented retrieval is useful when the question requires relationship traversal, multi-hop reasoning, entity-centered recall, or corpus-level synthesis. Baseline vector retrieval is weakest when the answer depends on connecting facts that are not semantically similar in isolation.

Ontology-guided knowledge graphs can improve retrieval when they preserve chunk/source information and when the schema is explicit enough to guide retrieval. The strongest evidence does not support “LLMs can magically create perfect ontologies.” It supports a more modest claim: LLMs can assist extraction, schema suggestion, ontology drafting, and entity resolution, especially when constrained by explicit schemas, validation, feedback loops, and human review.

DOM Graph RAG demonstrates a crucial architectural lesson: if the corpus already has meaningful structure, do not destroy that structure through arbitrary chunking. Preserve authored structure, metadata, hierarchy, identity, and state. Use embeddings to find candidate nodes, but retrieve the authoritative content through the graph.

For DungeonBuddy, this is especially relevant. Campaign corpora are not random text blobs. They are already semi-structured by session, route, character, location, faction, artifact, encounter, recap, plan, and unresolved hook. The system should treat those structures as first-class graph objects.

## 4. What Is Not Proven Enough

The unproven fantasy is a fully self-maintaining ontology that can ingest any new corpus, dynamically generate a stable taxonomy, update itself continuously, resolve entities perfectly, avoid drift, detect contradictions, preserve provenance, and improve retrieval without governance.

That is aspirational. It is not the safe foundation.

LLMs can propose structure. They can extract candidates. They can cluster aliases. They can suggest relation types. They can produce draft triples. They can classify evidence roles. They can detect likely contradictions. But they are not, by themselves, a reliable authority layer.

The durable system must distinguish between asserted source evidence, inferred graph edges, LLM-suggested candidates, validated relationships, rejected relationships, and deprecated claims. A graph that cannot distinguish those states becomes another hallucination surface.

## 5. The DungeonBuddy-Specific Insight

DungeonBuddy’s retrieval problem is not only “find the right text.” It is “admit the right evidence for the right planning lane while preserving campaign truth.”

That means the graph needs to represent more than entities and relationships. It needs to represent source authority, session chronology, player-facing truth, GM-only truth, planned-but-not-played material, retcons, rumors, contradictions, unresolved hooks, and evidence roles.

This makes DungeonBuddy different from many enterprise GraphRAG demos. The campaign corpus contains many kinds of truth:

Played truth: what happened at the table.

Canonical recap truth: what the system has promoted as campaign memory.

GM prep truth: what might happen but has not happened yet.

World truth: stable setting facts.

Rumor or unreliable truth: things NPCs said or believed.

Mechanical truth: statblocks, rules, encounter math, clocks, and constraints.

Retrieval truth: navigation sections, breadcrumbs, tags, hubs, and index hints that help recall but should not be treated as evidence.

A true graph layer must model these distinctions directly.

## 6. Current Architecture, Reframed as a Proto-Graph

The current pipeline can be understood as an implicit graph:

Raw source and played notes become canonical recaps.

Canonical recaps become normalized recaps.

Normalized recaps become breadcrumbed recaps.

Breadcrumbed recaps become session-memory records.

Session-memory records and support records are loaded through manifests.

The query system performs route-aware candidate generation, classification, admission, context rendering, and grounded answering.

This already encodes graph-like behavior: sessions connect to PCs, NPCs, locations, factions, events, and unresolved hooks. Routes are implicit edges. Hubs are high-degree routing nodes. Breadcrumbs are semantic aliases and traversal hints. Evidence roles act like admissibility constraints.

The next step is to stop treating those graph properties as incidental metadata and start materializing them as explicit nodes and edges.

## 7. Proposed Graph Model

DungeonBuddy should introduce a graph IR with three layers.

### Layer A: Source Graph

This is the authority layer.

Primary nodes:

SourceDocument
SourceSection
SentenceUnit
Session
Campaign
Artifact
Plan
Recap
SupportCard
ManifestRecord

Primary edges:

CONTAINS
PRECEDES
FOLLOWS
DERIVED_FROM
PROMOTED_TO
CITES
HAS_SECTION
HAS_SENTENCE
BELONGS_TO_SESSION
BELONGS_TO_CAMPAIGN

Key properties:

source_path
source_reference
line_range or section_id
created_at
updated_at
source_kind
source_layer
authority_level
visibility
evidence_role
promotion_state
admissibility

This layer answers: “Where did this come from, and can we use it as evidence?”

### Layer B: Campaign Knowledge Graph

This is the domain layer.

Primary nodes:

PC
NPC
Faction
Location
Settlement
Region
Threat
Monster
Item
Artifact
Quest
Event
Encounter
Clock
Rumor
Secret
Relationship
UnresolvedHook
Decision
Consequence
RuleReference

Primary edges:

APPEARED_IN
MENTIONED_IN
LOCATED_IN
ALLIED_WITH
OPPOSED_TO
MEMBER_OF
OWNS
SEEKS
THREATENS
PROTECTS
KILLED_BY
CREATED_BY
CAUSED
RESULTED_IN
FORESHADOWS
RESOLVES
CONTRADICTS
RETCONS
DEPENDS_ON
HAS_STATUS
HAS_ALIAS
HAS_ROUTE

Key properties:

canonical_name
aliases
entity_type
campaign_id
first_seen_session
last_seen_session
truth_state
confidence
source_support
gm_visibility
player_visibility
temporal_scope

This layer answers: “What exists in the campaign, how is it connected, and what state is it in?”

### Layer C: Retrieval/Planning Graph

This is the operational layer.

Primary nodes:

Query
QueryIntent
PlanningLane
RetrievalCandidate
ContextPacket
EvidenceBundle
AnswerClaim
EvaluationCase
FailureTrace

Primary edges:

MATCHED
ADMITTED
REJECTED
EXPANDED_TO
ROUTED_TO
SUPPORTED_BY
MISSING_EVIDENCE_FOR
FAILED_BECAUSE
RERANKED_ABOVE
RERANKED_BELOW

Key properties:

query_text
lane
retrieval_mode
score_components
admission_reason
rejection_reason
context_budget
answer_claims
citation_coverage
evaluation_result

This layer answers: “Why did the system retrieve this, why did it admit it, and did the answer use it correctly?”

## 8. RDF/OWL/SPARQL Decision

The recommendation is: design the graph IR to be RDF-compatible, but do not make full RDF/OWL/SPARQL the first implementation requirement unless it proves cheap.

Why not RDF-first immediately?

DungeonBuddy has narrative ambiguity, temporality, campaign-specific truth states, retcons, planned-vs-played distinctions, and evidence admission rules. RDF can represent these, especially with named graphs and provenance vocabularies, but the modeling overhead is real. A premature RDF-first implementation could slow the practical retrieval loop.

Why not ignore RDF?

Because RDF, OWL, SHACL, SKOS, and SPARQL solve many problems DungeonBuddy will otherwise reinvent badly: stable identifiers, controlled vocabularies, ontology validation, graph interchange, triple stores, named relationships, constraint checking, semantic query, and reasoner-compatible models.

The practical compromise:

Use a typed graph IR internally.

Assign stable URIs/IRIs from the beginning.

Represent edges in subject-predicate-object form even if stored in Postgres, SQLite, DuckDB, NetworkX, Neo4j, or JSON.

Keep a property graph projection for fast development.

Keep an RDF/JSON-LD/Turtle export path.

Add SHACL-like validation rules early, even if implemented in Python first.

Adopt SKOS-style taxonomy concepts for route families, entity classes, evidence roles, and planning lanes.

Only adopt OWL reasoning where it gives clear value, such as class hierarchy, inverse properties, transitive containment, equivalence, and disjointness.

This keeps the door open to Apache Jena/Fuseki, Oxigraph, QLever, RDFLib, GraphDB, Stardog, or other triplestores later without forcing them into the first experimental slice.

## 9. Role of LLMs

LLMs should be graph assistants, not graph authorities.

Good LLM uses:

Extract candidate entities from source units.

Suggest aliases and canonical names.

Suggest relation candidates.

Classify evidence roles.

Propose taxonomy additions.

Draft ontology changes.

Detect likely contradictions.

Generate competency questions.

Translate natural-language queries into graph query plans.

Summarize graph neighborhoods into context packets.

Explain why evidence was admitted or rejected.

Dangerous LLM uses:

Automatically promoting ontology changes without validation.

Collapsing entities without source-backed evidence.

Creating facts without source spans.

Treating inferred relationships as canonical.

Silently rewriting taxonomy.

Using graph summaries as evidence without preserving their source trail.

Replacing source citations with graph-derived abstractions.

The rule should be: the LLM may propose; the system validates; sources authorize.

## 10. Maintenance Model

The graph should be maintained through explicit lifecycle states.

For extracted entities and edges:

candidate
validated
canonical
deprecated
rejected
conflicted
retconned

For facts and claims:

source_asserted
llm_inferred
human_confirmed
system_promoted
superseded
contradicted
not_admissible_as_evidence

For taxonomy concepts:

proposed
active
merged
split
deprecated

Every graph update should preserve provenance. No entity merge, alias addition, relation promotion, taxonomy change, or contradiction resolution should be untraceable.

The system should support “promotion gates.” For example:

A sentence unit can mention “Hester.”

The extractor can propose Hester as an NPC.

Entity resolution can connect Hester to an existing canonical Hester node.

A relation extractor can propose Hester APPEARED_IN Session 23.

A validator can attach supporting sentence units.

Only after validation does the edge become admissible for retrieval.

This is slower than blind extraction, but it is how the graph earns trust.

## 11. Retrieval Pattern

The target retrieval flow:

1. Parse query into intent, entities, constraints, time scope, campaign scope, and planning lane.

2. Use lexical and vector retrieval to find candidate source units and graph nodes.

3. Use graph traversal to expand from candidate nodes to adjacent entities, sessions, locations, unresolved hooks, related plans, and source sections.

4. Apply admissibility rules based on evidence role, authority level, visibility, temporal scope, and lane.

5. Build a context packet from source-grounded units, not from graph summaries alone.

6. Use the graph to explain why the packet was assembled.

7. Require answer claims to cite source units.

8. Record the trace as a retrieval/planning graph artifact for evaluation and debugging.

This makes the graph both a retrieval engine and a debugging surface.

## 12. Evaluation Standard

A graph layer is successful only if it improves measured retrieval and planning behavior. It should not be accepted because it is architecturally elegant.

Success metrics:

Higher recall of required campaign facts.

Lower admission of navigation-only or non-evidence sections.

Better entity disambiguation.

Better multi-hop retrieval.

Better session-bounded recall.

Better unresolved-hook resurfacing.

Better planner lane coverage.

Lower hallucinated campaign claims.

Better citation coverage.

Better debuggability of why context was included.

No major regression in latency or operator comprehensibility.

The benchmark should include adversarial cases:

Same-name NPCs.

Rumors versus canonical truth.

GM prep versus played truth.

Location hierarchy ambiguity.

Long-tail session references.

Hub over-attraction.

Unresolved hooks with no obvious lexical match.

Entities that changed status over time.

Contradictions and retcons.

Questions that should not retrieve certain sources.

The graph earns promotion only by beating the current system on these cases.

## 13. Migration Path

### Phase 1: Materialize the Implicit Graph

Start by converting existing records into explicit nodes and edges.

Do not begin with LLM extraction. Begin with deterministic structure already available:

sessions
source files
sections
routes
breadcrumbs
manifest records
support cards
evidence roles
planning lanes
source references
known entity routes

Output a graph debug view and graph export.

Goal: make the current system visible as a graph before adding new intelligence.

### Phase 2: Add Entity Layer

Extract candidate entities from existing canonical recaps, normalized recaps, and breadcrumbed recaps.

Use strict schemas.

Attach every entity mention to source spans.

Resolve aliases conservatively.

Do not auto-merge ambiguous entities.

Goal: entity-centered retrieval without losing source authority.

### Phase 3: Add Relationship Layer

Extract relation candidates:

appeared in
located in
member of
allied with
opposed to
threatens
caused
resolved
foreshadows
owns
seeks
knows
killed by
created by

Require supporting source units.

Keep relation confidence and validation status.

Goal: enable reliable multi-hop retrieval.

### Phase 4: Add Taxonomy/Ontology Layer

Define controlled vocabularies for:

entity types
source kinds
evidence roles
truth states
visibility states
planning lanes
route families
relationship predicates
clock/threat statuses

Use LLMs to suggest additions, but require validation.

Goal: stable semantics for retrieval and planning.

### Phase 5: Add Query Planner

Translate user queries into graph-aware retrieval plans.

The planner should choose between:

direct lookup
route expansion
entity neighborhood expansion
temporal/session traversal
location hierarchy traversal
threat/clock traversal
unresolved hook resurfacing
support knowledge retrieval
global campaign synthesis

Goal: graph-guided retrieval rather than graph as decoration.

### Phase 6: RDF-Compatible Export

Add JSON-LD/Turtle export.

Map internal types to RDF-compatible predicates.

Add SHACL validation for core constraints.

Evaluate whether a triplestore and SPARQL improve development speed, query power, validation, or interoperability enough to justify adopting them directly.

Goal: preserve optionality without premature commitment.

## 14. Recommended Near-Term Technical Direction

The next practical slice should be small and decisive:

Build a graph materialization pass for the existing retrieval universe.

Represent SourceDocument, SourceSection, SentenceUnit, Session, Route, EntityCandidate, SupportCard, PlanningLane, and EvidenceRole.

Emit both a property graph JSON and an RDF-ish triples file.

Create a graph query/debug CLI that can answer:

What source units mention this entity?

What sessions connect to this route?

What evidence supports this NPC/location/threat?

Which sections are navigation-only?

What graph neighbors would be added to this query?

Why was this candidate admitted or rejected?

Then compare current retrieval against graph-expanded retrieval on known hard benchmark questions.

The goal is not to prove graphs are good. The goal is to discover whether explicit topology improves the exact failure modes DungeonBuddy already has.

## 15. Guardrails

Do not let graph summaries replace source evidence.

Do not auto-promote LLM-extracted facts.

Do not merge entities without provenance.

Do not treat taxonomy as stable if it is generated without governance.

Do not optimize around happy-path demos.

Do not let high-degree hubs dominate retrieval.

Do not make RDF purity more important than campaign retrieval quality.

Do not erase uncertainty, rumor, retcon, or planned-vs-played distinctions.

Do not allow graph edges without source support unless they are explicitly marked as inferred or system-generated.

## 16. The Working Decision

DungeonBuddy should build toward a true graph retrieval layer, but the graph should emerge from the current authority-preserving retrieval architecture rather than replace it.

The preferred architecture is:

source-grounded corpus
plus deterministic structural graph
plus conservative entity graph
plus validated relationship graph
plus controlled taxonomy
plus optional RDF/OWL/SPARQL compatibility
plus hybrid lexical/vector retrieval
plus graph-based admission and context packet assembly

This is the bridge from the current system to something very like DOM Graph RAG, adapted to campaign memory rather than enterprise technical documentation.

The strongest version of this system is not “LLM builds a graph from scratch.” It is “LLM assists a governed graph compiler.”

That compiler turns campaign artifacts into queryable, validated, source-grounded knowledge structures.

That is the path most likely to equal or exceed the current system.
