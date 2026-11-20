"""Shared parent-owned Graph-anchor reads; exact pins are attempted once per turn."""

import json
from application_state.agent_conversation import types as t


def read_operation_sources(adapter, operations, attempted_pins, gaps):
    a = adapter
    pins = a._broker_execution().effective_source_pins()
    pending = {}
    for event_id in operations:
        packet = json.loads(a.operation_payloads[event_id])
        for row in packet.get("sourceAnchors", []):
            anchor = row.get("anchorId")
            if not row.get("readable") or anchor not in pins:
                continue
            pin = pins[anchor]
            identity = (
                pin.anchor_id,
                pin.evidence_ref_id,
                pin.source_artifact_id,
                pin.source_revision_id,
            )
            if identity not in attempted_pins:
                pending[anchor] = identity
    anchors = sorted(pending)
    if not anchors:
        return

    def exhausted(unread):
        # A host refusal is terminal for these exact pins in this turn.
        # Persist its qualification through the same protected trace the
        # writer uses; an in-memory diagnostic is not producing authority.
        attempted_pins.update(pending[anchor] for anchor in unread)
        if "source_read_over_budget" not in gaps:
            gaps.append("source_read_over_budget")
            a.context_capture.observe(
                {
                    "kind": "failure",
                    "phase": "source_read",
                    "code": "source_read_over_budget",
                }
            )

    execution = a._broker_execution()
    if (
        t.source_read_character_usage(execution.policy, execution.events)
        >= execution.policy.max_source_read_chars
    ):
        exhausted(anchors)
        return
    with a.source_read_acquisition(anchors):
        while anchors:
            execution = a._broker_execution()
            remaining = (
                execution.policy.max_source_read_chars
                - t.source_read_character_usage(execution.policy, execution.events)
            )
            if remaining <= 0:
                exhausted(anchors)
                break
            max_chars = min(execution.policy.max_chars_per_source_read, remaining)
            count = min(8, len(anchors), remaining // max_chars)
            batch, anchors = anchors[:count], anchors[count:]
            attempted_pins.update(pending[anchor] for anchor in batch)
            before = set(a.source_payloads)
            reply = a.broker_source_read(
                {
                    "toolName": "read_graph_source",
                    "arguments": {
                        "retrievalSessionId": a.bootstrap.retrieval_session.id,
                        "anchorIds": batch,
                        "maxChars": max_chars,
                    },
                },
                bundle_internal=True,
            )
            if a.failure is not None:
                raise a.failure
            if not set(a.source_payloads) - before:
                gaps.append(
                    json.loads(reply["resultJson"]).get(
                        "code", "source_read_unavailable"
                    )
                )
