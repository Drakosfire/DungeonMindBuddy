"""Current empty Plan projection for isolated Rules-owner proof tests."""

from application_state.agent_conversation.plan_jev_graph_packet import SCHEMA
from application_state.agent_conversation.surface_evidence_answer import PLAN_POLICY as SELECTOR_POLICY
from application_state.agent_conversation.plan_writer_output_schema import output_format
from application_state.agent_conversation.rules_authority_types import canonical_bytes


def with_plan_schema(body, rules):
    frame = {
        "schema": SCHEMA,
        "answer_policy": SELECTOR_POLICY,
        "graph_records": [],
        "opened_passages": [],
        "committed_plan_blocks": [],
        "session_evidence": [],
        "native_source_sections": {
            "schema": "dmb_native_source_sections_frame_v1",
            "sections": [],
        },
    }
    return {
        **body,
        "input": [
            *body["input"],
            {"role": "user", "content": canonical_bytes(frame).decode()},
        ],
        "text": {"format": output_format(frame, rules)},
    }
