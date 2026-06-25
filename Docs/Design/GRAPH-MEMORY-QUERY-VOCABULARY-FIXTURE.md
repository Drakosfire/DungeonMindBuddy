# Graph Memory Query Vocabulary Fixture v0

## Purpose

This PR defines static query vocabulary only. It does not execute graph retrieval or graph queries. The fixture records safe, unsafe, and deferred graph-memory question types before retrieval exists.

## Why This Comes After Static Preview Graph UI Prototype

The static preview graph UI made candidate graph output inspectable. Query vocabulary is the next safety layer because future answers must not treat preview candidates as durable truth.

## Static Query Boundary

Preview candidate memory is not durable campaign truth. A safe answer must preserve evidence, uncertainty, and source state.

## Source Inputs

The fixture references the Session 23 static preview graph UI prototype, static extractor output comparison report, eval-only candidate output bundle, and candidate graph gold fixture.

## Query Intent Taxonomy

The taxonomy covers preview summaries, candidate explanations, bounded event questions, high-risk relationship questions, unresolved threat questions, proposed-write status questions, and unsafe canonical fact claims.

## Safe Query Examples

Safe examples inspect preview/report state with evidence requirements and preview labels.

## Unsafe Query Examples

Unsafe examples block canonical identity binding, unsupported cliffhanger resolution, approval/write requests, `/plan`, Agent Interaction, and canon promotion.

## Deferred Query Examples

Deferred examples preserve unknowns such as the golem-like creature identity, monster eye changes, refugee contamination risk, exact horde size, meatwing relationship, and post-lightning-bolt outcome.

## Evidence Policy

Every positive factual answer requires evidence refs or report summary fields. High-risk answers require warnings. Preview answers must be labeled as preview/candidate. No answer may promote preview output into approved memory.

## Answer Shape Contracts

Answer shapes define required fields for evidence-backed summaries, candidate-with-evidence answers, high-risk answers, unknown/deferred answers, and pending-write explanations.

## High-Risk Query Behavior

High-risk relationship or identity answers must warn, cite evidence, keep separate span notes, and avoid blind alias or identity merges.

## Proposed Write Query Behavior

Proposed-write queries can explain pending writes only. They cannot approve writes, persist review state, or write graph memory.

## Unknown / Deferred Query Behavior

Unknown and deferred answers must say the source does not resolve the question and must not invent missing facts.

## Agent Interaction Readiness

Agent Interaction remains blocked until approved durable graph memory and safe query execution exist.

## Determinism Requirements

The checked-in Markdown report must equal the deterministic report builder output from the helper module.

## Why This Is Not Runtime Retrieval

No live model execution, live extraction, graph retrieval, graph traversal, graph writes, approval persistence, graph queries, corpus scanning, corpus mutation, /plan integration, Agent Interaction integration, fact promotion, canon promotion, or runtime behavior changes are introduced by this PR.

## Future Query Execution Gate

Future query execution needs approved memory contracts, source-cited answer contracts, and explicit safe execution harnesses.

## What This Does Not Do

It does not execute graph retrieval, execute graph queries, call an LLM, write graph memory, approve writes, connect `/plan`, connect Agent Interaction, promote facts, promote canon, or change runtime behavior.

## Deferred Work

Recommended next PR: `graph-memory: add agent interaction chip payload contract v0`.
