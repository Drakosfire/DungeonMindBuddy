# Static Extractor Output Comparison Report — Session 23 Sample
## Verdict
- Status: `safe_but_incomplete`
- Merge gate: `pass`
- Blocking issues: 0
- Soft issues: 45
- Summary: The sample candidate output has no hard failures and passes evidence/high-risk/safety gates, but misses substantial Session 23 gold coverage.
## Safety Gate
- Overall safety: 1.0 (`pass`)
- Evidence alignment: 1.0
- High-risk audit: 1.0
## Score Summary

| Score | Value | Band |
|---|---:|---|
| node_recall | 0.7857 | good |
| edge_recall | 0.3478 | weak |
| beat_recall | 0.4286 | partial |
| proposed_write_recall | 0.4 | partial |
| ignored_item_recall | 0.6667 | partial |
| deferred_item_recall | 0.5 | partial |
| node_precision_proxy | 1.0 | pass |
| edge_precision_proxy | 1.0 | pass |

## Coverage Summary

| Type | Gold | Candidate | Matched | Missing | Extra | Recall | Precision Proxy |
|---|---:|---:|---:|---:|---:|---:|---:|
| nodes | 42 | 33 | 33 | 9 | 0 | 0.7857 | 1.0 |
| edges | 23 | 8 | 8 | 15 | 0 | 0.3478 | 1.0 |
| beats | 14 | 6 | 6 | 8 | 0 | 0.4286 | 1.0 |
| proposed_writes | 15 | 6 | 6 | 9 | 0 | 0.4 | 1.0 |
| ignored_items | 3 | 2 | 2 | 1 | 0 | 0.6667 | 1.0 |
| deferred_items | 6 | 3 | 3 | 3 | 0 | 0.5 | 1.0 |

## Missing Gold Coverage

| Type | Missing Count | Example IDs |
|---|---:|---|
| nodes | 9 | node:baergrom, node:bonogo, node:meat-flank-attackers, node:north-wall, node:ogonob |
| edges | 15 | edge:boy-warns-shadows-at-north-gate, edge:caelynn-unleashes-lightning-bolt, edge:ephanna-casts-hunger-of-hadar, edge:ephanna-summons-ogonob, edge:karsemine-casts-spike-growth |
| beats | 8 | beat:caelynn-hit-and-lysandra-counterattack, beat:eye-check-and-south-gate-plan, beat:hunger-of-hadar-and-readied-attacks, beat:karsemine-learns-fire-weakness, beat:lysandra-commanding-shout |
| proposed_writes | 9 | write:create-caelynn-lightning-bolt-cliffhanger, write:create-edge-refugees, write:create-edge-warning-message, write:create-first-meat-wave, write:create-flying-meatwings |
| ignored_items | 1 | ignored:experienced-adventurers-identities |
| deferred_items | 3 | deferred:edge-refugee-contamination-risk, deferred:golem-like-creature-identity, deferred:monster-eye-changes-source |

## Soft Misses By Category

| Issue | Count |
|---|---:|
| missing_deferred_item | 3 |
| missing_ignored_item | 1 |
| missing_proposed_write | 9 |
| missing_required_beat | 8 |
| missing_required_edge | 15 |
| missing_required_node | 9 |

## Hard Failures
- Total: 0
- Blocking: false
- Note: No hard safety failures were found in the static sample candidate output.
## Evidence Health
- Evidence refs: 206
- Resolved: 206
- Openable: 206
- Highlightable: 206
- Warnings: 0
- Summary: All candidate evidence refs resolve, open, and highlight against the Session 23 source-span fixture.
## High-Risk Audit
- Status: `pass`
- Audited objects: edge:lysandra-recognizes-lysandro, node:heroes-party, node:lysandro, node:thread-remaining-approaching-horde
- Summary: High-risk claims are present where expected and pass source-grounding audit.
## Proposed Writes
- Candidate total: 6
- Pending: 6
- Approved: 0
- Promoted: 0
- Unsafe statuses: 0
- Summary: All candidate proposed writes remain pending; the sample omits several gold proposed writes.
## GM Preview Readiness
- Status: `not_ready_for_gm_preview`
- Safe to inspect: true
- Safe to write: false
- Sufficient coverage for preview: false
- Reason: The static sample is safe but misses too many Session 23 edges, beats, proposed writes, and deferred items to be useful as a GM-facing preview.
## Boundary Statement

This is a static comparison report fixture.
It does not call an LLM.
It does not execute a live extractor.
It does not generate output from recap text.
It does not write graph memory.
It does not approve writes.
It does not execute graph queries.
It does not scan or mutate corpus files.
It does not connect /plan.
It does not connect Agent Interaction.
It does not promote facts or canon.
It does not change runtime or production behavior.
