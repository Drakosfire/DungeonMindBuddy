# Graph Memory Preview Graph UX Component Contract v0

This is a design contract for future conceptual components. It is not a TypeScript implementation and does not add runtime UI, React components, API endpoints, approval persistence, graph writes, or query execution.

## PreviewSummaryCard

Purpose:
Show the top-level candidate graph memory summary for a session.

Inputs:
- session_id
- session_title
- verdict
- gm_preview_readiness
- score_summary
- coverage_summary
- evidence_health
- high_risk_audit_summary
- proposed_write_summary
- hard_failure_summary
- soft_miss_summary

Visible states:
- safe_and_complete
- safe_but_incomplete
- unsafe
- invalid
- not_ready_for_gm_preview
- ready_for_gm_preview

Disabled states:
- disabled_due_to_hard_failure
- disabled_due_to_not_ready_for_preview

Future actions:
- open candidate explorer
- open missing coverage
- open proposed writes
- open hard failures

Out of scope:
No runtime navigation or action handler is implemented.

## SafetyGateBadge

Purpose:
Display whether hard failures block trust.

Inputs:
- verdict
- hard_failure_count
- hard_failure_categories

Visible states:
- pass
- warning
- fail
- invalid

Disabled states:
- disables_approval_like_actions

Future actions:
- open hard failure panel

Out of scope:
No safety computation is implemented.

## GMPreviewReadinessBadge

Purpose:
Show whether the candidate graph is ready for GM preview.

Inputs:
- gm_preview_readiness
- disabled_reason
- coverage_summary
- safety_gate

Visible states:
- ready_for_gm_preview
- not_ready_for_gm_preview
- unsafe_for_preview
- invalid

Disabled states:
- disabled_due_to_not_ready_for_preview
- disabled_due_to_unsafe_for_preview
- disabled_due_to_invalid_report

Future actions:
- open readiness explanation

Out of scope:
No readiness calculation is implemented.

## CoverageScoreGrid

Purpose:
Show coverage for candidate graph nodes, edges, beats, proposed writes, ignored items, and deferred items.

Inputs:
- coverage_summary
- missing_gold_coverage
- extra_candidate_coverage

Visible states:
- strong
- partial
- weak
- missing

Disabled states:
- disables_bulk_approval_when_weak

Future actions:
- filter explorer by weak coverage
- open missing coverage panel

Out of scope:
No scoring logic is implemented.

## EvidenceHealthPanel

Purpose:
Summarize evidence health and source evidence link resolution.

Inputs:
- evidence_health
- resolved_evidence_refs
- unresolved_evidence_refs
- heading_only_refs
- source_leakage_blocks

Visible states:
- pass
- warning
- fail
- unknown

Disabled states:
- disabled_due_to_unresolved_evidence
- disabled_due_to_source_leakage

Future actions:
- open evidence list
- highlight source

Out of scope:
No source resolver or deeplink runtime is implemented.

## HighRiskAuditPanel

Purpose:
Expose high-risk audit status and review warnings.

Inputs:
- high_risk_audit_summary
- risk_flags
- candidate_ids
- evidence_refs

Visible states:
- high_risk_audit_passed
- high_risk_audit_missing_evidence
- high_risk_audit_failed
- high_risk_claim_deferred

Disabled states:
- disabled_due_to_high_risk_claim
- disabled_due_to_failed_audit

Future actions:
- open risky candidate
- filter high-risk candidates

Out of scope:
No audit computation or approval gating is implemented.

## CandidateGraphExplorer

Purpose:
Provide structured review of candidate graph memory without requiring a graph visualization first.

Inputs:
- candidate_nodes
- candidate_edges
- candidate_beats
- ignored_items
- deferred_items
- filters
- sort

Visible states:
- nodes
- edges
- beats
- threads
- npcs
- locations
- groups
- threats
- ignored
- deferred

Disabled states:
- disabled_review_controls

Future actions:
- select candidate
- filter by risk
- filter by evidence state

Out of scope:
No live graph query or runtime UI is implemented.

## CandidateNodeCard

Purpose:
Summarize one proposed node.

Inputs:
- candidate_id
- label
- type
- evidence_count
- risk_flags
- proposed_write_status
- linked_beats
- review_state

Visible states:
- unreviewed
- high_risk
- evidence_warning
- proposed_write_pending
- deferred

Disabled states:
- disabled_due_to_not_ready_for_preview
- disabled_due_to_hard_failure

Future actions:
- open detail
- mark review intent

Out of scope:
No state persistence is implemented.

## CandidateEdgeCard

Purpose:
Summarize one proposed relationship.

Inputs:
- candidate_id
- source_node
- target_node
- edge_type
- evidence_count
- risk_flags
- linked_beats
- proposed_write_status

Visible states:
- unreviewed
- relationship_inference_warning
- alias_binding_warning
- evidence_warning

Disabled states:
- disabled_due_to_high_risk_claim
- disabled_due_to_insufficient_evidence

Future actions:
- open detail
- inspect related nodes

Out of scope:
No relationship inference or graph write is implemented.

## CandidateBeatCard

Purpose:
Summarize one candidate session beat.

Inputs:
- candidate_id
- label
- beat_type
- evidence_count
- risk_flags
- proposed_write_status

Visible states:
- unreviewed
- cliffhanger_warning
- uncertain_count_warning
- evidence_resolved

Disabled states:
- disabled_due_to_not_ready_for_preview
- disabled_due_to_hard_failure

Future actions:
- open detail
- inspect source snippets

Out of scope:
No beat persistence is implemented.

## CandidateDetailDrawer

Purpose:
Show evidence-backed detail for a selected candidate.

Inputs:
- candidate_id
- candidate_type
- label
- description
- rationale
- evidence_refs
- related_nodes
- related_edges
- related_beats
- high_risk_warnings
- proposed_write_preview

Visible states:
- evidence_resolved
- evidence_warning
- evidence_unresolved
- high_risk_review_carefully

Disabled states:
- disabled_review_controls
- disabled_due_to_unresolved_evidence

Future actions:
- open evidence
- highlight source
- mark review intent

Out of scope:
No drawer UI or action handler is implemented.

## EvidenceSnippetCard

Purpose:
Display one source evidence snippet and its resolution state.

Inputs:
- evidence_ref_id
- source_anchor_id
- snippet
- resolution_state
- source_label

Visible states:
- resolved
- openable
- highlightable
- warning
- unresolved
- unknown_anchor
- heading_only
- source_leakage_blocked

Disabled states:
- disabled_open_source
- disabled_highlight_source

Future actions:
- open source
- highlight source

Out of scope:
No source opening or highlighting runtime is implemented.

## SourceDeeplinkButton

Purpose:
Represent future source-open and source-highlight actions.

Inputs:
- source_anchor_id
- evidence_ref_id
- resolution_state

Visible states:
- open_enabled
- highlight_enabled
- warning
- disabled

Disabled states:
- disabled_due_to_unknown_anchor
- disabled_due_to_heading_only
- disabled_due_to_source_leakage_blocked

Future actions:
- open source
- highlight source

Out of scope:
No deeplink behavior is implemented.

## ProposedWritesQueue

Purpose:
Show proposed writes grouped by write type.

Inputs:
- proposed_writes
- proposed_write_summary
- gm_preview_readiness
- hard_failure_state
- high_risk_audit_summary

Visible states:
- pending
- disabled
- grouped_by_type
- no_writes

Disabled states:
- disabled_due_to_design_only_rung
- disabled_due_to_hard_failure
- disabled_due_to_not_ready_for_preview

Future actions:
- inspect write
- filter by write type

Out of scope:
No graph write, approval persistence, or mutation is implemented.

## ProposedWriteCard

Purpose:
Show one proposed write and why approval is disabled or eligible in a future workflow.

Inputs:
- write_id
- target_id
- write_type
- status
- candidate_source
- evidence_count
- risk_flags
- approval_eligibility
- disabled_reason

Visible states:
- pending
- eligible_future
- disabled
- high_risk
- evidence_warning

Disabled states:
- disabled_due_to_design_only_rung
- disabled_due_to_high_risk_claim
- disabled_due_to_insufficient_evidence

Future actions:
- open candidate
- inspect evidence
- approve in future gated implementation

Out of scope:
No write execution is implemented.

## MissingCoveragePanel

Purpose:
Translate eval misses into user-legible missing coverage.

Inputs:
- soft_miss_summary
- missing_gold_coverage
- coverage_summary

Visible states:
- critical
- important
- nice_to_have
- no_missing_coverage

Disabled states:
- disables_bulk_approval_when_critical

Future actions:
- filter explorer by missing type
- open coverage detail

Out of scope:
No eval execution is implemented.

## HardFailurePanel

Purpose:
Show safety blocks and why they prevent approval-like actions.

Inputs:
- hard_failure_summary
- affected_objects
- suggested_next_actions

Visible states:
- no_failures
- failures_present
- unsafe_for_preview
- invalid

Disabled states:
- disabled_due_to_hard_failure
- disabled_due_to_invalid_report

Future actions:
- inspect affected object
- reject
- defer

Out of scope:
No auto-fix or mutation is implemented.

## SoftMissPanel

Purpose:
Explain quality and coverage misses separately from safety failures.

Inputs:
- soft_miss_summary
- coverage_summary
- missing_gold_coverage
- extra_candidate_coverage

Visible states:
- no_soft_misses
- soft_misses_present
- weak_edges
- weak_beats
- incomplete_writes

Disabled states:
- disabled_bulk_approval_when_incomplete

Future actions:
- inspect missing nodes
- inspect missing edges
- inspect missing beats

Out of scope:
No coverage computation is implemented.

## ReviewIntentControls

Purpose:
Show future approve/reject/defer controls for a candidate item.

Inputs:
- candidate_id
- candidate_type
- risk_flags
- evidence_health
- proposed_write_status
- gm_preview_readiness
- hard_failure_state

Visible states:
- unreviewed
- disabled_due_to_hard_failure
- disabled_due_to_insufficient_evidence
- disabled_due_to_high_risk_claim
- disabled_due_to_not_ready_for_preview

Disabled states:
- disabled_due_to_design_only_rung
- disabled_due_to_hard_failure
- disabled_due_to_insufficient_evidence
- disabled_due_to_high_risk_claim
- disabled_due_to_not_ready_for_preview

Future actions:
- approve
- reject
- defer
- needs_more_evidence
- campaign_context_required

Out of scope:
This PR does not implement any action handler or persistence.
