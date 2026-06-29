# Recap-Ingestion Dogfood Evaluation Report v0

Date: 2026-06-22

Audience: design / implementation agent for the next Graph Memory recap-ingestion slice.

## Executive Summary

The current recap-ingestion dogfood fixture proves that the pipeline can preserve a small explicit artifact set through materialization, diagnostics, projection readiness, and payload shaping without obvious safety leaks. It does not yet prove GM-facing value.

The strongest dogfood conclusion is that the next slice should stop optimizing text reports about payload counts and instead exercise the actual intended product loop:

1. Ingest a real recap.
2. Extract graph candidates over multiple LLM passes.
3. Produce an interactive preview graph.
4. Let the GM visually confirm that the recap was understood.
5. Approve or defer writes into graph memory.
6. Query the written graph through a constrained query vocabulary.
7. Feed evidence-backed results into the Agent Interaction layer, with markdown chips / deeplinks / hover cards.

The current fixture is best understood as a wrapper/safety check, not a meaningful dogfood of recap ingestion.

## What Was Evaluated

The dogfood chain under inspection was:

- explicit dogfood manifest
- recap-ingestion source artifact materializer
- materializer diagnostics report
- projection-readiness report
- projection payload shape
- human GM evaluation

The fixture directory under `evals/graph_memory_layer/examples/recap_ingestion_real_artifact_dogfood/` contains five artifact inputs plus a manifest:

- normalized recap markdown
- breadcrumbed recap markdown
- frontmatter seed markdown
- session memory metadata
- corpus impact proof
- dogfood manifest

The generated reports showed:

- 5 dogfood artifact inputs
- 5 source artifacts
- 5 source anchors
- 5 source units
- 5 source refs
- 5 projection payload units
- readiness status: ready
- no reported raw text leakage
- no reported absolute path leakage
- no adapter/runtime payload leakage
- no `/plan` or Agent Interaction payload leakage

## Main GM Observation

Alan's first GM reaction was:

> Nothing yet as a GM is useful here.

This is the key evaluation result. The pipeline shape may be internally coherent, but the visible reports do not yet create a feeling that a recap was understood, remembered, or made useful.

## Fixture Adequacy Finding

The current dogfood directory appears to contain one very small synthetic recap fragment expanded into multiple artifact families. As GM-facing content, the meaningful input is essentially:

- one beat about returning to an archive and comparing a warning against prior notes
- one beat about an unresolved courier/motive breadcrumb that should not be promoted into extracted facts

That is too thin to judge a GM-facing recap-ingestion system.

What the fixture proves:

- artifact family typing can survive the pipeline
- semantic state envelopes can be assigned
- safety boundaries can be checked
- projection payload units can be emitted
- diagnostic reports can count expected shapes

What it does not prove:

- that a real recap can become a useful graph
- that graph candidates are understandable to the GM
- that provenance is actionable
- that source references can resolve to evidence spans
- that graph memory can answer useful session-recall questions
- that Agent Interaction can consume the result

Design implication: the next dogfood fixture should be a real recap slice, not another minimal synthetic artifact fixture.

## Provenance And Trust Finding

The existing reports mention source refs as counts, but Alan did not see source ref IDs or raw text in a way that supported trust evaluation.

Important clarification from Alan:

If `source_ref_id` is intended to provide GM trust, it does not need to be human readable. Its job is to be machine-readable and parseable enough for the UI to turn it into a link that renders the source and highlights the exact piece of information being referenced.

Therefore, the requirement is not:

- "make opaque IDs readable to humans"

The requirement is:

- every source ref must be resolvable by the product surface
- every graph fact / node / relationship that claims evidence must be able to open the relevant source
- the UI should highlight the exact span or structured field that supports the claim
- reports should prove resolvability, not merely count refs

This reframes the safety boundary. Avoiding raw text leaks is necessary, but the system must still expose enough safe, resolvable evidence structure for a GM-facing UI.

## Product Direction

The useful next product artifact is not a markdown diagnostics report. It is an interactive graph projection.

The first useful preview should help the GM look at the result and feel:

> Yes, that is the session I wrote.

The preview does not need full editing workflows at v0. It does need to show the recap transformed into a believable graph.

Minimum preview contents:

- named people / places / items as nodes
- unnamed but important things as nodes
- session beats as nodes
- relationships between entities and beats
- source snippets attached to each node / relationship
- clear distinction between canon, candidate, breadcrumb-only, diagnostic, and ignored material

Examples of unnamed-but-important nodes that should be allowed:

- the courier
- the warning
- the archive return
- the unresolved motive
- the prior notes

This is important because Alan expects LLM-based ingestion over multiple passes. The extraction should not be limited to named entities. It should also capture important clues, hooks, motives, warnings, unresolved threads, groups, and events.

## Write Policy

Initial write policy should be preview-only.

The first graph-ingestion loop should be:

1. Recap goes in.
2. LLM performs multi-pass extraction and organization.
3. System produces an interactive graph preview.
4. GM inspects whether it feels right.
5. Writes happen only after approval.

A later toggle may allow skipping preview for trusted or lower-risk flows. That toggle should not be the v0 default.

Design implication: preview payloads must preserve enough write intent to become commits later:

- proposed node IDs
- labels
- node types
- relationship types
- source refs / spans
- candidate/canon states
- provenance metadata
- proposed write operations or equivalent diff structure

## End-To-End Success Bar

The success bar is not just "the graph looks like the session."

Alan wants the graph to become queryable memory that can feed the corpus and Agent Interaction layer.

The desired loop is:

1. recap
2. extracted graph preview
3. approved graph memory write
4. queryable graph memory
5. corpus / agent context integration
6. evidence-backed Agent Interaction response

If the next slice stops at visualization, it is still incomplete. Visualization is the first GM trust surface, but queryability is the product value.

## Query Vocabulary Target

Alan expects a constrained query vocabulary that an LLM can be prompted to use. The user asks in natural language. The Agent Interaction layer or planner decides what memory it needs. An LLM writes a structured graph query using allowed operations. Graph memory returns scoped facts, relationships, source evidence, and unresolved threads.

Initial query operations should support common session recall questions:

- What are the named characters in this session?
- Give me a concise outline of the sessions.
- What were the last few things that happened?
- Who did Lysandra talk to?

Candidate v0 query operations:

- `list_named_characters(session_id)`
- `outline_sessions(scope)`
- `recent_events(limit, scope)`
- `entity_interactions(entity_id_or_name, filters)`

These should return supporting evidence, not just final text.

## Evidence-Backed Answers And Agent Interaction

Query results must include supporting evidence.

The ideal Agent Interaction surface is not plain markdown. It is markdown with known entities and evidence references detected and decorated as interactive chips / deeplinks, similar to the markdown edit-field chip work already underway.

Example target behavior:

- The generated response mentions "Lysandra."
- The UI recognizes `Lysandra` as a known graph entity.
- The rendered answer attaches a hover/click chip config.
- The chip can reveal entity context, source evidence, graph relationships, and provenance.

Initial evidence card should be information-rich:

- entity / node card
- source recap snippet
- relationship or fact that caused the answer
- session timeline context
- graph/source refs needed for deeplink and highlighting
- advanced/internal metadata available but visually secondary

Over time, advanced layers can be hidden behind toggles. At v0, transparency is preferred because the team needs to learn which layers GMs actually use.

## Report Noise / Ceremony

The current reports contain useful internal checks, but they are not a GM-facing dogfood surface.

Likely useful for developers:

- artifact family distinctions
- semantic states
- safety checks
- source ref counts
- readiness status
- leakage checks

Likely ceremony for GM evaluation:

- repeated count tables
- opaque payload unit IDs without resolvability proof
- generic "ready" statuses
- display summaries that say "Synthetic..." rather than reflecting source meaning
- diagnostics that prove the wrapper but not the memory value

The next dogfood report can keep diagnostics as a secondary appendix, but the main artifact should be the graph preview and query results.

## Proposed Next Dogfood Slice

Mission:

Build a recap-ingestion dogfood that takes a richer recap slice and produces a preview-only graph projection plus a small evidence-backed query demo.

Inputs:

- one real or realistic recap slice with multiple named entities
- multiple session beats
- at least one relationship between named entities
- at least one unnamed-but-important node
- at least one unresolved thread / breadcrumb
- at least one detail that should be ignored or not promoted

Outputs:

- interactive or inspectable graph preview
- source-linked node and relationship evidence
- proposed write set, still preview-only
- small query vocabulary demonstration
- evidence-backed answer payloads suitable for Agent Interaction chips
- developer diagnostics in an appendix or sidecar

## Acceptance Criteria For The Next Slice

The next dogfood should pass these human/product checks:

- The GM can look at the graph preview and recognize the recap.
- Named characters, places, and items appear as nodes when present.
- Important unnamed concepts, clues, or threads can also appear as nodes.
- Session beats are visible as first-class graph objects or clearly inspectable structure.
- Relationships between entities/beats are visible.
- Each proposed node/relationship/fact has resolvable source evidence.
- Source refs can drive UI deep links and source-span highlighting.
- The preview is read-only by default.
- The write intent is preserved so approval can later commit the graph changes.
- Query operations can answer at least the four initial recall questions.
- Query answers return supporting evidence.
- Agent Interaction can receive enough metadata to render entity/evidence hover chips.

## Suggested Technical Shape

The designing agent should consider separating the system into these layers:

1. Recap source adapter
   - Accepts a recap artifact.
   - Produces bounded source units with stable source refs and span metadata.

2. Multi-pass LLM extractor
   - Extracts named entities.
   - Extracts unnamed important nodes.
   - Extracts beats.
   - Extracts relationships.
   - Extracts unresolved threads and breadcrumbs.
   - Marks ignored / non-promoted details.

3. Graph candidate model
   - Holds preview nodes, edges, evidence refs, semantic states, and write intent.
   - Does not commit by default.

4. Preview projection
   - Renders graph candidates for GM inspection.
   - Prioritizes "does this feel like the recap?" over internal metrics.

5. Query vocabulary
   - Provides constrained operations an LLM can call.
   - Returns structured evidence-bearing results.

6. Agent Interaction bridge
   - Converts query results into answer context.
   - Emits chip/deeplink configs for known entities and source evidence.

## Open Design Questions

The next agent should answer or prototype these:

- What graph visualization library is light enough for the dogfood preview?
- What is the minimal source span model needed for highlightable evidence?
- Should session beats be nodes, edge annotations, or both?
- How should unnamed important nodes be typed and later merged/renamed?
- What is the preview payload schema that can later become a commit payload?
- What query result schema best supports Agent Interaction chips?
- How much diagnostic metadata should be visible by default versus hidden behind advanced toggles?
- How should ignored / non-promoted recap details be represented so the GM can verify restraint?

## Strong Recommendation

Do not spend the next slice improving the current text reports unless doing so directly supports preview graph or query validation.

The current report format has already answered its useful question: the artifact wrapper can survive and safety checks can pass. The next unknown is whether a real recap can become inspectable, queryable, evidence-backed graph memory that improves Agent Interaction.

That is the next dogfood target.
