# Experimental Plan: DungeonBuddy Graph Memory Fork

Status: proposed
Mode: separate fork / branch stack
Intent: prove or falsify whether a graph-memory layer improves DungeonBuddy retrieval, entity continuity, ontology/taxonomy maintenance, and context enrichment without regressing current source-grounded behavior.

## 0. Strategic Frame

This should be an experiment fork, not a production migration.

The goal is not to “convert DungeonBuddy to Graph RAG.” The goal is to prove whether an explicit graph layer improves known retrieval and reasoning failures while preserving the current strengths:

source-grounded sentence units
breadcrumb/route discipline
manifest-backed evidence admission
session-bounded retrieval
citation and provenance
debuggable benchmark traces

The experiment should start as a shadow system that reads existing artifacts and emits graph artifacts. It should not mutate canonical corpus files until later spikes prove value.

The guiding question:

Can a graph materialization and graph-aware retrieval adapter beat or match the current retrieval system on known hard cases, while making entity/relationship/taxonomy state easier to inspect, maintain, and reason over?

## 1. Fork / Branch Strategy

Create a separate fork or long-running branch:

`experiment/graph-memory-layer`

Inside that branch, use stacked PRs. Each PR should be mergeable into the experiment branch independently. Nothing should be merged back to main until the experiment passes explicit gates.

Recommended branch stack:

`graph-exp/00-baseline-freeze`
`graph-exp/01-graph-ir-schema`
`graph-exp/02-materialize-existing-session-memory`
`graph-exp/03-graph-debug-cli`
`graph-exp/04-rdf-compatible-export`
`graph-exp/05-graph-retrieval-shadow`
`graph-exp/06-entity-resolution-candidates`
`graph-exp/07-relationship-candidates`
`graph-exp/08-taxonomy-governance`
`graph-exp/09-query-planner-adapter`
`graph-exp/10-live-context-shadow`
`graph-exp/11-promotion-report`

The merge-back strategy should be conservative:

First merge docs and read-only graph materialization.
Then merge shadow retrieval behind flags.
Then merge tests and reports.
Only then consider production retrieval changes.

No production retrieval path should depend on the graph until the graph beats the current system on the agreed benchmark set.

## 2. Spike 0: Baseline Freeze and Experiment Harness

Purpose: lock the current system’s behavior before adding graph logic.

### PR 0.1 — Add graph experiment README and branch contract

Create:

`Docs/Experiments/EXPERIMENT-Graph-Memory-Layer.md`

Content:

experiment thesis
non-goals
safety constraints
benchmark gates
promotion criteria
rollback criteria
branch strategy
feature flag policy

Done when:

The experiment has a clear written contract.

### PR 0.2 — Freeze current benchmark baseline

Create a baseline report folder:

`evals/graph_memory_layer/artifacts/baseline/`

Capture or reference the latest known current-system reports:

C1S1 routing/retrieval
C1S2 clean control
C1S3 location hierarchy failure
C1S13 alias/identity failure
C2S22 “last thing that happened” live query issue
Session 20 breadcrumb natural query baseline, if still relevant

The baseline report should distinguish:

retrieval pass
semantic answer pass
citation pass
failure family
cost
context size
latency if available

Done when:

There is a committed baseline artifact describing what the graph must beat or preserve.

### PR 0.3 — Add graph experiment smoke runner shell

Create:

`evals/graph_memory_layer/run_smoke.py`

At first, this runner may only print baseline availability and validate expected files exist.

Done when:

`uv run python -m evals.graph_memory_layer.run_smoke` succeeds without requiring an LLM key.

Kill criteria:

If the baseline cannot be reproduced or described, pause. The graph experiment cannot prove value without a frozen comparison point.

## 3. Spike 1: Graph IR Schema

Purpose: define a DungeonBuddy graph model without yet changing retrieval.

### PR 1.1 — Define graph node and edge schema

Create:

`src/graph_memory/schema.py`

Core dataclasses or Pydantic models:

GraphNode
GraphEdge
GraphBundle
SourceRef
GraphProvenance
GraphConfidence
GraphLifecycleState

Initial node kinds:

Campaign
Session
SourceDocument
SourceSection
SentenceUnit
Route
Hub
Entity
Location
PC
NPC
Party
NewHubCandidate
EvidenceRole
ManifestRecord

Initial edge kinds:

CONTAINS
BELONGS_TO_CAMPAIGN
BELONGS_TO_SESSION
DERIVED_FROM
HAS_ROUTE
ROUTES_TO
MENTIONS
APPEARED_IN
HAS_SOURCE
HAS_EVIDENCE_ROLE
HAS_AUTHORITY
HAS_VISIBILITY
PARENT_LOCATION_OF
ALIAS_OF
SAME_AS_CANDIDATE
RELATED_TO

Do not overbuild. The schema should support current artifacts first.

Done when:

The graph schema can serialize to deterministic JSON.

### PR 1.2 — Add stable ID / URI policy

Create:

`src/graph_memory/ids.py`

Define stable IDs for:

source documents
sessions
sentence units
routes
entities
edges
manifest records

Use predictable IDs, not random IDs. Every ID should be reproducible from source path, campaign id, session number, unit id, and route when possible.

Example style:

`dmb:campaign/longmont-c2`
`dmb:session/longmont-c2/22`
`dmb:source/sha256-or-pathslug`
`dmb:unit/longmont-c2/session-22/u-L0042-01`
`dmb:route/longmont-campaign/campaign-2/npcs/lysandra-ironveil`

Done when:

IDs are deterministic and unit-tested.

### PR 1.3 — Add graph validation rules

Create:

`src/graph_memory/validate.py`

Initial validation:

every edge source/target exists
every SentenceUnit has a SourceDocument
every SentenceUnit has line_start/line_end
every ROUTES_TO edge points to a Route/Hub/Entity node
every extracted/inferred edge has provenance
no unknown node kind
no unknown edge kind
no duplicate node id with conflicting payload
no duplicate edge id with conflicting payload

Done when:

Invalid graph bundles fail closed with clear messages.

## 4. Spike 2: Deterministic Graph Materialization from Existing Artifacts

Purpose: materialize the implicit graph that already exists, without LLM extraction.

### PR 2.1 — Materialize graph from session-memory JSONL

Create:

`src/graph_memory/materialize_session_memory.py`

Input:

`*.records_meta.jsonl` or existing session-memory JSONL

Output:

`GraphBundle`

For each record:

SourceDocument node
Session node
SentenceUnit node
Route nodes for each route attachment
Entity/Hub placeholder node for each route
edges:
Session CONTAINS SentenceUnit
SentenceUnit HAS_SOURCE SourceDocument
SentenceUnit ROUTES_TO Route
Route REPRESENTS Hub/Entity placeholder
SentenceUnit HAS_EVIDENCE_ROLE EvidenceRole if available

Done when:

The materializer can read one existing session-memory JSONL and emit graph JSON.

### PR 2.2 — Materialize graph from planning corpus manifest

Create:

`src/graph_memory/materialize_manifest.py`

Input:

planning corpus manifest JSON

Output nodes:

ManifestRecord
SourceDocument
EvidenceRole
PlanningLane
AuthorityState

Output edges:

ManifestRecord POINTS_TO SourceDocument
SourceDocument HAS_EVIDENCE_ROLE EvidenceRole
SourceDocument HAS_AUTHORITY AuthorityState
ManifestRecord BELONGS_TO_LANE PlanningLane

Done when:

Manifest routes and evidence roles become inspectable graph nodes/edges.

### PR 2.3 — Materialize graph from breadcrumbed recap frontmatter

Create:

`src/graph_memory/materialize_breadcrumb_frontmatter.py`

Extract:

entity index
party policy
locations
new hub candidates
unresolved/open questions
source recap metadata

Output nodes:

EntityCandidate
UnresolvedHook
Party
Location
Route
Session

Output edges:

UnresolvedHook MENTIONED_IN Session
EntityCandidate HAS_ROUTE Route
Party HAS_ROUTE Route
Location HAS_ROUTE Route

Done when:

The frontmatter metadata currently used for retrieval becomes graph material, not only lexical metadata.

### PR 2.4 — Add graph materialization runner

Create:

`evals/graph_memory_layer/materialize_graph.py`

CLI examples:

`uv run python -m evals.graph_memory_layer.materialize_graph --records-jsonl PATH --output graph.json`

`uv run python -m evals.graph_memory_layer.materialize_graph --manifest PATH --output manifest_graph.json`

Done when:

A graph artifact can be generated from current repo artifacts with no LLM calls.

Kill criteria:

If deterministic materialization is too brittle, stop before adding LLM extraction. The graph must first represent what already exists.

## 5. Spike 3: Graph Debug CLI and Reports

Purpose: make the graph useful to inspect before using it for retrieval.

### PR 3.1 — Add graph query CLI

Create:

`src/graph_memory/query.py`
`evals/graph_memory_layer/graph_query.py`

Support simple queries:

show node
neighbors of route
units for route
routes for unit
sessions for entity route
units in session
open hooks in session
source units by line range
entity candidates by type
location children
aliases/same-as candidates

Done when:

A human can inspect the graph without reading JSON manually.

### PR 3.2 — Add graph report generator

Create:

`evals/graph_memory_layer/graph_report.py`

Report:

node counts by type
edge counts by type
orphan nodes
routes with no units
units with no routes
high-degree hubs
new hub candidates
unresolved hooks
authority/evidence-role distribution
session coverage
known failure family coverage

Done when:

A markdown report can summarize a graph artifact.

### PR 3.3 — Add graph diff utility

Create:

`src/graph_memory/diff.py`

Compare two graph bundles:

added nodes
removed nodes
changed nodes
added edges
removed edges
changed edge confidence/state
new orphan nodes
new validation violations

Done when:

Graph changes are reviewable in PRs.

## 6. Spike 4: RDF-Compatible Export, But Not RDF-First

Purpose: preserve a path to RDF/OWL/SPARQL without forcing full semantic-web infrastructure immediately.

### PR 4.1 — Add JSON-LD/Turtle export skeleton

Create:

`src/graph_memory/rdf_export.py`

Export:

nodes as resources
edges as triples
source references as provenance properties
node kinds as RDF classes
edge kinds as RDF predicates

Use simple namespaces:

`dmb:` for DungeonBuddy concepts
`prov:` for provenance-like concepts where practical
`skos:` for taxonomy concepts where practical
`rdf:` / `rdfs:` basics

Done when:

A graph bundle can export to JSON-LD and/or Turtle.

### PR 4.2 — Add SHACL-like Python validation

Create:

`src/graph_memory/constraints.py`

Model constraints in Python first:

SentenceUnit requires source path and line range
ROUTES_TO requires Route target
SAME_AS requires same high-level entity kind or explicit override
PARENT_LOCATION_OF requires Location nodes
Canonical edge cannot lack source/provenance
LLM candidate edge cannot be canonical without promotion

Done when:

The experiment has semantic validation without depending on an RDF stack.

### PR 4.3 — Optional RDFLib smoke test

If dependency cost is acceptable, add an optional dev extra:

`graph-rdf`

Use RDFLib only in tests or CLI export validation.

Done when:

Exported Turtle can be parsed by RDFLib.

Do not block the experiment on this.

## 7. Spike 5: Graph-Aware Retrieval Shadow Adapter

Purpose: test whether graph expansion improves current retrieval without replacing it.

### PR 5.1 — Build graph expansion from session-memory query hits

Create:

`src/graph_memory/retrieval_expand.py`

Input:

current session-memory hits
graph bundle
query constraints

Expansion types:

adjacent sentence units
same route
route family
same session
same entity
parent/child location
alias candidate
unresolved hook attached to same route
party membership

Output:

expanded candidate units with expansion reason

Done when:

Given current hits, the graph can propose additional source units.

### PR 5.2 — Add graph shadow retrieval report

Create:

`evals/graph_memory_layer/graph_retrieval_shadow.py`

Run current retrieval and graph-expanded retrieval side by side.

Report:

current top hits
graph-expanded hits
new units added
units dropped
must-include coverage
must-exclude violations
context size
why each graph unit was added

Done when:

Known hard cases can be audited without changing answer generation.

### PR 5.3 — Add hard-case retrieval fixtures

Add graph-shadow cases for:

C1S1 roster/identity bundle
C1S3 Stonebridge / Rivers Edge Pub location hierarchy
C1S13 necromancer / Draven alias bridge
C2S22 “last thing that happened in Session 22”
Session 20 pronoun-heavy Lysandra/Marla/gnat-swarm style query if still useful

Done when:

Graph expansion has to prove value on named failure families, not cherry-picked examples.

Kill criteria:

If graph expansion mostly adds noise or only wins by over-broad expansion, do not proceed to live integration.

## 8. Spike 6: Entity Candidate Extraction

Purpose: add LLM-assisted graph construction, but only as candidate generation.

### PR 6.1 — Define entity candidate schema

Create:

`src/graph_memory/extraction_schema.py`

EntityCandidate fields:

candidate_id
canonical_name_guess
entity_type_guess
aliases
source_unit_ids
source_spans
confidence
rationale
lifecycle_state = candidate
extraction_model
extraction_prompt_id

Done when:

Entity extraction has a strict, reviewable output format.

### PR 6.2 — Add entity extraction runner

Create:

`evals/graph_memory_layer/extract_entity_candidates.py`

Input:

sentence units from session-memory JSONL or normalized recap

Output:

entity candidate graph nodes and MENTIONS edges

Use small batches.

Require:

source unit ids
no free-floating entities
no canonical promotion
no merges

Done when:

The runner can produce entity candidates from one session.

### PR 6.3 — Add entity extraction grader

Gold should check:

expected entity candidate exists
source unit attached
no forbidden entity candidate
no unsupported canonical promotion
no route hallucination

Done when:

Entity extraction quality can be measured.

### PR 6.4 — Add entity review report

Create:

`evals/graph_memory_layer/entity_candidate_review.md` generator

Group candidates by:

likely new canonical entity
likely alias of existing route
ambiguous
low confidence
rejected by validator

Done when:

A human can review extraction output efficiently.

## 9. Spike 7: Alias and Identity Resolution

Purpose: address one of the core current failures: alias/identity bridges.

### PR 7.1 — Define identity edge states

Add edge kinds or properties:

ALIAS_OF_CANDIDATE
SAME_AS_CANDIDATE
SAME_AS_VALIDATED
DISTINCT_FROM
TITLE_OR_ROLE_OF
TEMPORARY_NAME_FOR

Lifecycle states:

candidate
validated
rejected
conflicted

Done when:

The graph can represent uncertainty instead of forcing merges.

### PR 7.2 — Add deterministic alias candidates from routes

Generate aliases from:

route leaf names
frontmatter labels
known route equivalence manifests
breadcrumb frontmatter entity names
manifest lexical terms

Done when:

Existing curated alias material becomes graph edges.

### PR 7.3 — Add LLM-assisted identity candidate runner

Input:

new entity candidates
existing route/hub nodes
source units

Output:

candidate identity edges only.

Never auto-merge.

Done when:

The C1S13 Draven/necromancer family can be represented as an identity candidate with supporting source.

### PR 7.4 — Add identity resolution retrieval test

Test:

query uses role name
source uses canonical name
source uses alias
graph expansion bridges them
must not bridge unrelated entities

Done when:

Alias graph expansion improves recall without broadening unrelated hits.

## 10. Spike 8: Location Hierarchy and Spatial Graph

Purpose: address location hierarchy failures deliberately.

### PR 8.1 — Add location hierarchy model

Node kinds:

Location
Sublocation
Region
RouteLocation

Edges:

LOCATED_IN
CONTAINS_LOCATION
NEAR
PART_OF_ROUTE
TRAVELED_TO
TRAVELED_FROM

Done when:

The graph can represent Rivers Edge Pub located in Stonebridge without duplicating every fact onto both routes.

### PR 8.2 — Deterministic hierarchy extraction from paths/routes

Infer location parentage from:

route folders
frontmatter location lists
known hub paths
location route conventions

Mark deterministic-but-structural edges separately from source-asserted edges.

Done when:

The system can distinguish “path hierarchy suggests” from “recap says.”

### PR 8.3 — Location retrieval expansion policy

Implement controlled expansion:

exact location first
then contained sublocations
then parent location
then sibling locations only if query asks broadly

Done when:

C1S3 location failure improves without making parent locations over-attract every sublocation fact.

## 11. Spike 9: Relationship Candidate Extraction

Purpose: move beyond entity indexing toward useful graph reasoning.

### PR 9.1 — Define relation predicate vocabulary v0

Start small:

APPEARED_IN
LOCATED_IN
MEMBER_OF
ALLIED_WITH
OPPOSED_TO
THREATENS
SEEKS
OWNS
KILLED_BY
CAUSED
RESOLVED
FORESHADOWS
HAS_STATUS
HAS_SECRET
KNOWS
REVEALED_IN
UNRESOLVED_AFTER

Do not attempt a universal ontology.

Done when:

There is a controlled predicate vocabulary.

### PR 9.2 — Add relationship candidate extraction runner

Input:

sentence units with entity candidates/routes

Output:

relationship candidate edges with source unit support.

Done when:

The graph can extract a small relation set from one session.

### PR 9.3 — Add relationship validation constraints

Examples:

KILLED_BY requires actor-ish and victim-ish nodes or explicit unknown
LOCATED_IN target must be location-like
MEMBER_OF target must be party/faction/group-like
UNRESOLVED_AFTER must point to session or hook
REVEALED_IN must point to source/session/event

Done when:

Bad relation candidates fail validation.

### PR 9.4 — Add relation retrieval test

Example query families:

Why is Lysandra important right now?
Which threats are unresolved after Session 22?
Who is connected to Mireward?
What locations are tied to the swamp threat?
What changed about this NPC over time?

Done when:

Graph relationships improve context assembly beyond lexical/route overlap.

## 12. Spike 10: Taxonomy and Ontology Governance

Purpose: prevent dynamic ontology drift.

### PR 10.1 — Add taxonomy registry

Create:

`corpus/_graph/taxonomy_v1.json` or `src/graph_memory/taxonomy.py`

Controlled concepts:

entity types
source kinds
authority levels
evidence roles
visibility states
truth states
planning lanes
relationship predicates
lifecycle states

Done when:

The graph does not rely on free-text type names.

### PR 10.2 — Add taxonomy proposal schema

LLMs may propose:

new entity type
new relation predicate
new evidence role
new route family
new planning lane

But proposals must include:

why existing concepts do not fit
source examples
risk of overuse
suggested validation rule
migration impact

Done when:

Ontology changes are reviewable artifacts, not silent prompt drift.

### PR 10.3 — Add taxonomy lint

Lint:

unknown type
deprecated type
too many one-off proposed types
new relation with no validation rule
new relation with no retrieval use case
taxonomy concept unused after N runs

Done when:

The taxonomy can evolve without becoming sludge.

## 13. Spike 11: Graph Query Planner

Purpose: turn graph structure into retrieval decisions.

### PR 11.1 — Define graph query plan schema

Query plan fields:

intent
campaign_scope
session_scope
entity_constraints
location_constraints
time_constraints
evidence_authority_required
visibility_required
retrieval_lanes
graph_expansion_steps
must_include_node_ids
must_exclude_node_ids
context_budget

Done when:

A natural query can be represented as a graph-aware retrieval plan.

### PR 11.2 — Deterministic graph query planner v0

No LLM first.

Rules:

if query mentions session N, include session scope
if query asks “last/final,” prioritize late units in that session
if query mentions known route alias, resolve to route node
if query asks “who/where connected,” use entity/location neighborhood
if query asks unresolved/next, include unresolved hooks and prep lanes
if query asks play fact, restrict to canon/derived memory

Done when:

The planner can produce useful plans for known benchmark queries.

### PR 11.3 — LLM query planner candidate mode

Only after deterministic planner exists.

LLM output must be strict JSON and validated.

The LLM may propose:

intent
entity aliases
relationship predicates
expansion mode
answer constraints

It may not directly choose hidden source files unless those are graph-resolved after validation.

Done when:

LLM query planning improves recall or precision over deterministic planning on hard cases.

## 14. Spike 12: Live Manifest Integration in Shadow Mode

Purpose: compare graph-aware retrieval to live manifest retrieval without changing production behavior.

### PR 12.1 — Add graph packet adapter

Create:

`src/live_play/graph_context_adapter.py`

Input:

QueryRequest
manifest
graph bundle

Output:

candidate graph context packet

This should not replace `manifest_context_query.py`. It should run in shadow and emit comparable traces.

Done when:

For a live query, the system can produce both manifest packet and graph packet.

### PR 12.2 — Add live query graph shadow trace

For each query, record:

manifest top candidates
graph top candidates
manifest admitted evidence
graph proposed evidence
overlap
graph-only evidence
manifest-only evidence
known gold coverage
admission compatibility

Done when:

The Session 22 drift example can be compared cleanly.

### PR 12.3 — Add graph-assisted admission experiment

Graph can propose candidates, but existing admission policy still decides.

This tests:

Can graph retrieval find better evidence while preserving authority gates?

Done when:

Graph-assisted candidates improve accepted evidence without bypassing policy.

Kill criteria:

If graph candidates require weakening authority/admission policy to win, reject the approach.

## 15. Spike 13: Merge-Back Preparation

Purpose: convert successful experiment code into mainline-safe PRs.

### PR 13.1 — Promotion report

Create:

`Docs/Reports/REPORT-Graph-Memory-Layer-Experiment.md`

Include:

what was built
what was measured
where graph won
where graph lost
cost/latency impact
failure analysis
recommended merge subset
recommended abandoned pieces
production risks

Done when:

A reviewer can decide whether to merge without reading every artifact.

### PR 13.2 — Mainline merge plan

Split merge-back into safe chunks:

1. graph schema and deterministic materializer
2. graph reports and CLI
3. RDF/JSON-LD export
4. graph shadow retrieval tests
5. optional graph-assisted retrieval behind feature flag
6. any production retrieval changes last

Done when:

The experiment branch has a clear path back into main.

## 16. Promotion Gates

The graph experiment is successful only if it meets these gates.

### Gate A — Safety

No source-grounding regression.
No generated graph fact without provenance.
No graph summary admitted as source evidence.
No production retrieval change without a feature flag.
No silent ontology mutation.

### Gate B — Retrieval

Graph-shadow retrieval must improve or preserve:

C1S1 roster/identity bundle
C1S2 clean control
C1S3 location hierarchy
C1S13 alias/identity bridge
C2S22 session-title/final-beat retrieval
at least one current live-prep query

### Gate C — Precision

Graph expansion must not cause broad hub flooding.

Track:

context size
must-exclude violations
high-degree hub over-attraction
irrelevant sibling expansion
wrong alias merges
wrong parent-location expansion

### Gate D — Debuggability

For every graph-added context unit, the trace must answer:

what node caused this expansion?
what edge caused this expansion?
what source supports the edge?
what lifecycle/confidence state does the edge have?
why was it admitted or rejected?

### Gate E — Operator Value

The graph report/CLI must make the corpus easier to understand.

It should expose:

orphan routes
unresolved hooks
entity candidates
ambiguous aliases
location hierarchy
high-degree hubs
candidate relationships
admission reasons
source-support gaps

If the graph only helps machines and is unreadable to the GM/operator, it is not ready.

## 17. First Minimal Vertical Slice

The smallest valuable proof is:

Materialize existing session-memory JSONL into graph JSON.

Add graph query CLI.

Implement route-family/location/alias expansion.

Run graph shadow retrieval on C1S3 and C1S13.

Show that:

C1S3 retrieves Stonebridge through Rivers Edge Pub without duplicating tags.

C1S13 retrieves Draven through necromancer identity/alias bridge without overmatching unrelated necromancer text.

C1S2 remains clean.

This is the first “yes/no” moment.

If this fails, pause LLM extraction work. The deterministic graph must help before dynamic graph construction is worth pursuing.

## 18. Suggested PR Order

Recommended first 10 PRs:

1. `docs: add graph memory experiment contract`
2. `evals: freeze graph experiment baseline reports`
3. `graph-memory: add graph IR schema and stable IDs`
4. `graph-memory: add graph bundle validation`
5. `graph-memory: materialize session-memory JSONL`
6. `graph-memory: materialize planning manifest`
7. `graph-memory: add graph query CLI`
8. `graph-memory: add graph report and diff tools`
9. `graph-memory: add RDF-compatible export`
10. `evals: add graph shadow retrieval for C1S3/C1S13`

Only after those should LLM entity extraction begin.

## 19. Working Rule

Do not start by asking, “Can an LLM build our ontology?”

Start by asking, “Can we make the ontology already implicit in our corpus visible, queryable, and measurably useful?”

Then ask whether LLMs can safely maintain and extend it.

That sequence protects the experiment from becoming an expensive hallucination machine.
