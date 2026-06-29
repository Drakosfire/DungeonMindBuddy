# Graph Memory Multi-Pass Extraction Contract v0

## Purpose

This PR defines the contract a future extractor must satisfy; it does not implement or execute an extractor.

## Why This Comes After The Session 23 Gold Fixture

The Session 23 hand-authored gold fixture is the comparison target for future extractor output, not a source of campaign truth.

## Contract-Only Boundary

No pass may promote facts, write graph memory, approve proposed writes, or resolve the Session 23 cliffhanger.

## Source Fixture Dependency

The contract targets the Session 23 normalized recap and source-span seed refs.

## Gold Fixture Dependency

The future comparison target is the hand-authored Candidate Graph Preview gold fixture for Session 23.

## Pass Architecture

The contract defines nine ordered passes: source span selection, session beat extraction, named entity candidate extraction, unnamed-important concept extraction, relationship edge proposal, ignored/deferred detection, evidence alignment, candidate graph assembly, and gold comparison report.

## Pass 1: Source Span Selection

Selects only known source-span seed refs, preserving source ref, source artifact, and source anchor identity without copying raw source text.

## Pass 2: Session Beat Extraction

Defines ordered beat output requirements and evidence gates without extracting live beats.

## Pass 3: Named Entity Candidate Extraction

Defines named candidate fields and identity policies, including directly named, role-only, separate-span binding, deferred identity, and canonical alias deferred.

## Pass 4: Unnamed-Important Concept Extraction

Defines important non-name concepts that matter to GM memory while forbidding generated lore, statblocks, and unsupported second-wave wording.

## Pass 5: Relationship Edge Proposal

Defines source-grounded edge candidates, relationship types, endpoint gates, and evidence requirements.

## Pass 6: Ignored / Deferred Detection

The contract must preserve ignored and deferred material as first-class extraction outputs, because restraint is part of trustworthy graph memory.

## Pass 7: Evidence Alignment

Requires resolver-compatible evidence refs for every candidate object and rejects unknown, unresolved, unopenable, unhighlightable, or heading-only evidence.

## Pass 8: Candidate Graph Assembly

Defines assembly into Candidate Graph Preview IR v0 with preview status, pending writes, preserved ignored/deferred items, and no promoted lifecycle.

## Pass 9: Gold Comparison Report

Defines future report dimensions, issue categories, hard failures, and soft misses without comparing live extractor output in this PR.

## Evidence Alignment Requirements

Every candidate object must carry evidence refs that resolve, open, highlight, and point to known Session 23 anchors.

## High-Risk Claim Audit Requirements

High-risk claim audit exists to prevent the future extractor from being rewarded for unsupported identity binding, alias binding, future-wave language, or outcome resolution.

## Gold Comparison Policy

Future output will be compared against the Session 23 gold fixture using contract-defined matching policies for nodes, edges, beats, writes, ignored items, and deferred items.

## Hard Failures vs Soft Misses

Hard failures include dangerous diagnostics, promoted lifecycle, approved writes, unknown evidence anchors, unresolved evidence, source leakage, runtime leakage, corpus mutation, and LLM execution requirements. Soft misses include optional omissions and low-importance wording differences.

## Why This Does Not Execute LLMs Yet

The workstream needs a stable scoring shape before any extractor harness is allowed to run.

## Future Eval-Only LLM Extractor Harness

A later eval-only harness may load contract-shaped extractor output and compare it to the Session 23 gold fixture, gated so CI does not require live LLM execution unless explicitly enabled.

## What This Does Not Do

It does not call an LLM, execute extraction, run the planner, write graph memory, approve writes, execute graph queries, scan or mutate corpus files, connect `/plan`, connect Agent Interaction, promote facts, promote canon, or change runtime behavior.

## Deferred Work

Deferred work includes the eval-only extractor harness fixture, candidate output loading, gold comparison execution, and any explicitly gated live-model experiments.
