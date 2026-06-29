# Graph Memory Session 23 Candidate Graph Gold Fixture v0

## Purpose

The gold fixture defines what a good future extractor should produce; it is not produced by an extractor. The hand-authored graph should make the Session 23 recap recognizable to a GM.

## Why This Comes After Session 23 Recap Ingest Fixture

The Session 23 recap ingest fixture established the normalized recap, paragraph index, and source-span seed refs that this gold target depends on.

## Gold Fixture Is Not Extractor Output

This fixture is manually authored as a preview-only expected Candidate Graph Preview.

## Session 23 Source Surface

The fixture uses the mechanically normalized Session 23 recap and existing source-span seed refs from the recap ingest fixture.

## Gold Graph Authoring Principles

The graph captures recognizable Session 23 concepts without promoting canon or writing graph memory.

## Node Selection Principles

Nodes include named characters, groups, locations, threats, clues, and threads that a GM would expect to see.

## Unnamed-Important Concept Principles

The gold graph must include unnamed-important concepts, unresolved threads, ignored details, and deferred details, not only named entities.

## Edge Selection Principles

Edges are selected only when the recap directly supports the relationship with source evidence.

## Session Beat Principles

Session beats summarize the played sequence in order and make the wall arrival, Edge warning, refugee crisis, battle escalation, and cliffhanger scannable.

## Proposed Write Intent

Proposed writes are pending intent only. They are not approved, committed, written, or promoted.

## Ignored And Deferred Items

Ignored items prevent unsupported exact counts or invented identities from becoming facts. Deferred items preserve unresolved choices, risks, and creature identities for later evidence.

## Evidence Requirements

Every meaningful gold node, edge, beat, proposed write, ignored item, and deferred item must carry resolver-compatible evidence refs.

## Semantic State Requirements

Semantic states may describe played source authority, but lifecycle state remains candidate because this is only a preview.

## Relationship To Future Multi-Pass Extraction Contract

The next backend rung should define a multi-pass extraction contract that can target this gold graph without requiring live LLM execution in CI.

## Relationship To Future Extractor Evaluation

Future extractor evaluation can compare model-produced Candidate Graph Preview output against this hand-authored gold fixture.

## What This Does Not Do

This PR does not call an LLM, does not run the live planner, does not extract entities automatically, does not infer relationships automatically, does not write graph memory, does not approve writes, does not execute queries, does not scan or mutate corpus files, does not promote facts, does not promote canon, does not connect `/plan`, and does not connect Agent Interaction.

## Deferred Work

Future work should define the multi-pass extraction contract, scoring shape, and comparison report against this fixture.
