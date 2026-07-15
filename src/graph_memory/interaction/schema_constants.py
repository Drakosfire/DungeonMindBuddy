"""Schema identifiers for Hermes × World Graph interaction contracts."""

from __future__ import annotations

GRAPH_CLAIM_SCHEMA = "dmb_graph_claim_v1"
GRAPH_REFERENCE_SCHEMA = "dmb_graph_reference_v1"
SOURCE_CITATION_SCHEMA = "dmb_source_citation_v1"
INFERENCE_REFERENCE_SCHEMA = "dmb_inference_reference_v1"
GRAPH_RETRIEVAL_SESSION_SCHEMA = "dmb_graph_retrieval_session_v1"
GRAPH_RETRIEVAL_SESSION_REQUEST_SCHEMA = "dmb_graph_retrieval_session_request_v1"
EXPAND_GRAPH_RETRIEVAL_SCHEMA = "dmb_expand_graph_retrieval_request_v1"
READ_GRAPH_SOURCE_SCHEMA = "dmb_read_graph_source_request_v1"
STRUCTURED_ANSWER_DRAFT_SCHEMA = "dmb_structured_answer_draft_v1"
FORENSIC_ENVELOPE_SCHEMA = "dmb_hermes_graph_forensic_envelope_v1"
DIGEST_AUDIT_SCHEMA = "dmb_world_contribution_digest_audit_v1"

# Product grounding vocabulary (replaces anchor-presence grounded label).
TURN_OUTCOME_GRAPH_GROUNDED = "graph_grounded"
TURN_OUTCOME_SOURCE_VERIFIED = "source_verified"
TURN_OUTCOME_PARTIAL = "partial_coverage"
TURN_OUTCOME_INFERRED = "inferred_from_graph"
TURN_OUTCOME_CONFLICT = "conflicting_authority"
TURN_OUTCOME_UNSUPPORTED = "unsupported"
TURN_OUTCOME_ABSTAINED = "abstained"
TURN_OUTCOME_EXECUTION_ERROR = "execution_error"

__all__ = [
    "DIGEST_AUDIT_SCHEMA",
    "EXPAND_GRAPH_RETRIEVAL_SCHEMA",
    "FORENSIC_ENVELOPE_SCHEMA",
    "GRAPH_CLAIM_SCHEMA",
    "GRAPH_REFERENCE_SCHEMA",
    "GRAPH_RETRIEVAL_SESSION_REQUEST_SCHEMA",
    "GRAPH_RETRIEVAL_SESSION_SCHEMA",
    "INFERENCE_REFERENCE_SCHEMA",
    "READ_GRAPH_SOURCE_SCHEMA",
    "SOURCE_CITATION_SCHEMA",
    "STRUCTURED_ANSWER_DRAFT_SCHEMA",
    "TURN_OUTCOME_ABSTAINED",
    "TURN_OUTCOME_CONFLICT",
    "TURN_OUTCOME_EXECUTION_ERROR",
    "TURN_OUTCOME_GRAPH_GROUNDED",
    "TURN_OUTCOME_INFERRED",
    "TURN_OUTCOME_PARTIAL",
    "TURN_OUTCOME_SOURCE_VERIFIED",
    "TURN_OUTCOME_UNSUPPORTED",
]
