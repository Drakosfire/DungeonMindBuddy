# Graph Memory Static Extractor Output Comparison Report v0

## Purpose

This PR hardens comparison report semantics; it does not implement or execute an extractor. The static report turns the eval-only harness candidate-vs-gold comparison into a reviewer artifact that can be inspected before any live extractor work is admitted.

## Why This Comes After Eval-Only Extractor Harness Fixture

The eval-only harness proves that a checked-in candidate bundle can be validated, parsed, audited, and compared against the Session 23 gold graph. This layer makes that comparison stable and human-readable.

## Static Report Boundary

The static report is a reviewer artifact, not campaign truth and not a graph write.

No live model execution, graph writes, approval mechanics, graph queries, corpus scanning, corpus mutation, `/plan` integration, Agent Interaction integration, fact promotion, or canon promotion are introduced by this PR.

## Source Comparison Report

The source is the eval-only harness expected comparison report fixture for Session 23.

## Static JSON Report Contract

The JSON report records verdict, score bands, coverage counts, missing coverage, hard failures, soft misses, evidence health, high-risk audit status, proposed write safety, GM preview readiness, and static diagnostics.

## Static Markdown Report Contract

The Markdown report is generated deterministically from the JSON report and is intended for PR review without requiring reviewers to inspect the full JSON fixture.

## Verdict Derivation

Unsafe reports have hard failures. Safe complete reports have no hard failures and complete recall. Safe but incomplete reports have no hard failures but at least one recall score below 1.0.

## Score Bands

Scores are grouped into pass, good, partial, weak, and none bands so reviewers can distinguish safety from incomplete coverage.

## Coverage Grouping

Coverage is grouped across nodes, edges, beats, proposed writes, ignored items, and deferred items with gold, candidate, matched, missing, extra, recall, and precision proxy counts.

## Hard Failures

Hard failures represent safety blockers. The report separates hard safety failures from soft quality misses.

## Soft Misses

Soft misses represent missing quality or coverage items that should be improved before future GM-facing preview work.

## Evidence Health

Evidence health summarizes resolved, openable, highlightable, warning, unknown-anchor, and heading-only evidence counts from the harness resolver output.

## High-Risk Audit Summary

The high-risk audit summary records audited objects and forbidden claims absent from the static sample.

## Proposed Write Safety

Candidate proposed writes must remain pending. Approved, promoted, committed, or written statuses are rejected.

## GM Preview Readiness

A candidate output can be safe to inspect while still not ready for GM preview. The current static sample is safe but below the edge and beat coverage thresholds for preview readiness.

## Determinism Requirements

The checked-in JSON report must exactly equal the report builder output, and the checked-in Markdown must exactly equal the Markdown builder output.

## Why This Does Not Execute LLMs Yet

The goal is evaluation visibility before extractor behavior. Live model calls would make this fixture non-deterministic and inappropriate for CI.

## Future Live Extractor Gate

Future live extractor work should use this report shape as a gate before any runtime integration or write path is considered.

## What This Does Not Do

It does not call an LLM, execute a live extractor, generate output from recap text, write graph memory, approve writes, execute graph queries, scan or mutate corpus files, connect `/plan`, connect Agent Interaction, promote facts, promote canon, or change runtime behavior.

## Deferred Work

Deferred work includes a preview graph UX design spec and later gated extractor experiments that still preserve safety boundaries.
