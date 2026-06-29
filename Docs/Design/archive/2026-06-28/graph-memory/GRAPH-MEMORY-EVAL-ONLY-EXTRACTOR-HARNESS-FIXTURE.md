# Graph Memory Eval-Only Extractor Harness Fixture v0

## Purpose

This PR adds a harness for static, checked-in, contract-shaped candidate output; it does not implement or execute an extractor.

## Why This Comes After Multi-Pass Extraction Contract

The Multi-Pass Extraction Contract v0 defines pass order, pass schemas, dependencies, and safety boundaries. This harness makes those contract shapes loadable and comparable against Session 23 gold.

## Eval-Only Boundary

No live model execution, graph writes, approval mechanics, graph queries, corpus scanning, corpus mutation, `/plan` integration, Agent Interaction integration, fact promotion, or canon promotion are introduced by this PR.

## Static Candidate Output Bundle

The candidate output bundle is not gold and is not campaign truth.

## Relationship To Session 23 Source Fixture

The harness resolves candidate evidence against the Session 23 normalized recap source span seed refs.

## Relationship To Session 23 Gold Fixture

The harness compares exact candidate IDs against the hand-authored Candidate Graph Preview gold fixture.

## Relationship To Multi-Pass Extraction Contract

Candidate pass outputs must follow the contract pass order, schemas, and dependency graph.

## Candidate Pass Output Validation

The validator checks selected spans, beats, entity candidates, important concept candidates, relationship proposals, ignored/deferred detection, evidence alignment, graph assembly, and the no-execution gold-comparison pass.

## Candidate Graph Preview Validation

The assembled graph parses as Candidate Graph Preview IR v0, remains `preview`, and keeps proposed writes `pending`.

## Evidence Resolution

Every candidate evidence ref must use known Session 23 source refs and source anchors, resolve, open, and highlight.

## High-Risk Claim Audit

The harness reuses the Session 23 high-risk audit for Lysandro evidence, Heroes / party naming, and remaining approaching horde wording.

## Gold Comparison v0

Gold comparison v0 uses deterministic exact ID matching for nodes, edges, beats, proposed writes, ignored items, and deferred items.

## Hard Failures

Hard failures represent safety boundary violations such as runtime leakage, unknown evidence, promoted lifecycle, approved writes, source leakage, corpus mutation, or LLM execution requirements.

## Soft Misses

A candidate output can be structurally valid and still low quality. The report separates hard safety failures from soft quality misses.

## Expected Comparison Report Fixture

The checked-in expected comparison report is a regression lock: changing candidate output requires changing the expected report.

## Why This Does Not Execute LLMs Yet

The harness exists so future extractor output can be evaluated deterministically before live LLM execution is allowed.

## Future Live Extractor Gate

A future gated design may add live extraction only behind explicit controls after static comparison reporting is trusted.

## What This Does Not Do

No live model execution, graph writes, approval mechanics, graph queries, corpus scanning, corpus mutation, `/plan` integration, Agent Interaction integration, fact promotion, or canon promotion are introduced by this PR.

## Deferred Work

Deferred work includes richer human-readable comparison reports, fuzzy matching, GM trust notes, and any separately gated live extractor harness.
