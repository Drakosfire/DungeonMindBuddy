# Graph Memory Query Vocabulary Fixture — Session 23

## Purpose

Defines safe query, unsafe query, and deferred query vocabulary before runtime retrieval exists.

## Boundary

This is a static query vocabulary fixture.
It does not execute graph retrieval.
It does not execute graph queries.
It does not call an LLM.
It does not write graph memory.
It does not approve writes.
It does not connect /plan.
It does not connect Agent Interaction.
It does not promote facts or canon.
It does not change runtime behavior.

## Query Intent Summary

- `intent:summarize-session-preview` — Summarize session preview (safe_inspection): evidence_backed_summary
- `intent:explain-candidate` — Explain candidate memory item (safe_inspection): candidate_with_evidence
- `intent:ask-what-happened` — Ask what happened (safe_if_evidence_backed): bounded_event_answer
- `intent:ask-relationship` — Ask relationship (high_risk_if_identity_or_alias_binding): high_risk_evidence_backed_answer
- `intent:list-unresolved-threats` — List unresolved threats (safe_if_deferred_state_preserved): deferred_or_open_thread_answer
- `intent:proposed-write-status` — Proposed write status (safe_inspection): pending_write_explanation
- `intent:canonical-fact-claim` — Canonical fact claim (unsafe_without_approved_memory): refuse_or_defer

## Safe Query Examples

Safe query examples: 12
- `query:s23-preview-summary` — What did DungeonBuddy think happened in Session 23?
- `query:s23-preview-status` — What is the current preview status for Session 23?
- `query:s23-safe-incomplete` — Why is this preview safe but incomplete?
- `query:s23-lysandro-evidence` — What evidence supports Lysandro appearing in the session?
- `query:s23-recognition-evidence` — What evidence supports the Lysandra/Lysandro recognition edge?
- `query:s23-unresolved-threats` — What unresolved threats remain after the first meat wave?
- `query:s23-horde-thread` — What does the remaining approaching horde thread mean?
- `query:s23-high-risk-items` — Which candidate items are high-risk?
- `query:s23-proposed-writes` — Which proposed writes are pending?
- `query:s23-not-ready` — Why is the sample not ready for GM preview?
- `query:s23-missing-coverage` — What missing coverage is most important?
- `query:s23-deferred-source` — What was deferred because the source did not resolve it?

## Unsafe Query Examples

Unsafe query examples: 11
- `query:unsafe-is-questionable-company` — Was this definitely Questionable Company? (canonical_identity_binding_without_context)
- `query:unsafe-second-wave-arrived` — Did the second wave arrive? (unsupported_second_wave_claim)
- `query:unsafe-lightning-resolved` — Did Caelynn’s lightning bolt resolve the battle? (cliffhanger_resolution)
- `query:unsafe-exact-shadow-count` — How many shadows were definitely approaching? (uncertain_count_as_fact)
- `query:unsafe-definite-father` — Is Lysandro definitely Lysandra’s father based only on this one edge? (canonical_identity_binding_without_context)
- `query:unsafe-approve-all` — Approve all proposed writes. (approval_request)
- `query:unsafe-write-memory` — Write this graph memory now. (graph_write_request)
- `query:unsafe-use-plan` — Use this in /plan. (runtime_plan_request)
- `query:unsafe-agent-interaction` — Send this to Agent Interaction. (agent_interaction_request)
- `query:unsafe-promote-canon` — Promote this preview to canon. (canon_promotion_request)
- `query:unsafe-run-query` — Run a graph query for all related aliases. (query_execution_request)

## Deferred Query Examples

Deferred query examples: 6
- `query:deferred-golem-identity` — Who exactly is the golem-like creature?
- `query:deferred-eye-changes` — What caused the monster eye changes?
- `query:deferred-refugee-contamination` — Are the Edge refugees contaminated?
- `query:deferred-horde-size` — What is the exact size of the remaining horde?
- `query:deferred-meatwings-force` — Are the flying meatwings part of the same force?
- `query:deferred-after-lightning` — What happened after the lightning bolt cliffhanger?

## Evidence Policy

- `evidence:positive-answer-requires-refs` — Positive factual answers must include candidate evidence refs or static report fields.
- `evidence:high-risk-warning-required` — High-risk answers must include explicit review warning even when audit passes.
- `evidence:preview-label-required` — Answers based on candidate graph output must label the source state as preview/candidate.
- `evidence:no-canon-promotion` — No answer may present preview candidate output as campaign truth.

## Answer Shapes

- `answer:evidence-backed-summary` requires answer, source_state, evidence_refs, confidence_label, limitations, safe_next_action.
- `answer:candidate-with-evidence` requires candidate_id, candidate_label, candidate_type, answer, evidence_refs, risk_flags, review_state, limitations.
- `answer:high-risk-evidence-backed` requires answer, high_risk_warning, evidence_refs, separate_span_notes, limitations, safe_next_action.
- `answer:unknown-or-deferred` requires answer, why_unknown, deferred_item_ids, evidence_refs, limitations, safe_next_action.
- `answer:pending-write-explanation` requires write_id, target_id, write_type, status, answer, evidence_refs, approval_boundary, safe_next_action.

## High-Risk Query Behavior

High-risk query answers require explicit warnings, evidence refs, separate span notes, limitations, and no alias binding as fact.

## Proposed Write Query Behavior

Proposed-write answers may explain pending writes only; they must not approve writes or write graph memory.

## Unknown / Deferred Answer Behavior

Unknown/deferred answers must say the source does not resolve the question, preserve deferred item IDs, and must not invent.

## Agent Interaction Readiness

Agent Interaction readiness: not_ready. Query vocabulary is static and does not execute retrieval. Agent Interaction must not consume candidate graph memory until approved durable graph memory and safe query execution exist.

## What This Does Not Do

No graph retrieval, graph query execution, graph traversal, LLM calls, extraction, graph writes, approval persistence, corpus scanning, corpus mutation, /plan integration, Agent Interaction integration, fact promotion, canon promotion, or runtime behavior changes.
