"""Read display metadata for subjects already retained in one replay."""

import re

from application_state.agent_conversation.service import _ready_dsn
from application_state.unit_of_work import unit_of_work
from dungeonmind.application.vnext import EntityReadService

from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import map_entity_result
from apps.live_control_server.models.native_graph_inspection import InspectionPin
from apps.live_control_server.services.native_graph_inspection import (
    InspectionUnavailable, _pinned, _response, _shared_parsed_cache,
)

MAX_REPLAY_IDENTITIES = 128


def _has_recorded_name(label):
    return bool(label and label.strip() and not re.match(
        r"^(?:(?:ent|entity|asrt):|Unnamed object(?: \d+)?$)", label, re.IGNORECASE,
    ))


def replay_identities(*, service, principal, world_id, turn_id, trace_id, offset=0):
    attempts = service.list_context_trace_attempts(world_id=world_id, turn_id=turn_id)
    trace = next((item for item in attempts if item.trace_id == trace_id
                  and item.world_id == world_id and item.turn_id == turn_id), None)
    if trace is None:
        raise InspectionUnavailable("replay_trace_unavailable")
    subjects = dict.fromkeys(
        identity for step in trace.native_assertion_steps or () for identity in step.subject_ids
        if not _has_recorded_name(step.subject_labels.get(identity)) or identity not in step.subject_kinds
    )
    discovery = trace.native_discovery_replay
    if discovery is not None:
        for identity in discovery.seed_ids:
            if not _has_recorded_name(discovery.labels.get(identity)):
                subjects.setdefault(identity, None)
        for hop in discovery.hops:
            for identity in (hop.from_node_id, hop.to_node_id):
                if not _has_recorded_name(discovery.labels.get(identity)):
                    subjects.setdefault(identity, None)
    if type(offset) is not int or offset < 0 or offset > len(subjects):
        raise InspectionUnavailable("replay_identity_page_unavailable")
    page = list(subjects)[offset:offset + MAX_REPLAY_IDENTITIES]
    next_offset = offset + len(page) if offset + len(page) < len(subjects) else None
    identities = []
    if subjects:
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute(
                """SELECT graph_context_receipt->'native_query'->'authority'
                   FROM agent.turn WHERE world_id=%s AND turn_id=%s AND conversation_id=%s""",
                (world_id, turn_id, trace.conversation_id),
            ).fetchone()
        authority = row[0] if row else None
        if (not authority or authority["managed_world_id"] != world_id
                or any(step.revision_id != authority["revision_id"] for step in trace.native_assertion_steps or ())
                or discovery is not None and discovery.revision_id != authority["revision_id"]):
            raise InspectionUnavailable("replay_graph_pin_unavailable")
        pin = InspectionPin(
            managed_world_id=world_id, native_world_id=authority["native_world_id"],
            binding_version=authority["binding_version"], revision_id=authority["revision_id"],
            scope_mode=authority["scope_mode"], campaign_id=authority["campaign_id"],
        )
        bound, read, _, _, _ = _pinned(pin, principal, parsed_cache=_shared_parsed_cache)
        reader = EntityReadService()
        for identity in page:
            result = reader.get_entity(read, identity)
            if result.found:
                node = map_entity_result(result, identity, allow_multiple=True)
                identities.append({"node_id": identity, "label": node.label, "kind": node.kind})
        _response(bound, pin)
    return {"world_id": world_id, "turn_id": str(turn_id), "trace_id": str(trace_id), "identities": identities, "next_offset": next_offset}
