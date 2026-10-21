"""Display-only labels from already captured source reads, never new evidence."""
from collections import defaultdict


def source_names_for_turns(turns, *, service=None):
    from application_state.agent_conversation import AgentConversationService
    groups = defaultdict(list)
    for value in turns:
        base = getattr(value, 'base_projection', None)
        turn = base.turn if base is not None and base.kind == 'approved' else getattr(value, 'envelope', value)
        execution = getattr(turn, 'graph_context_execution', None)
        completion = getattr(turn, 'completion', None)
        citations = getattr(getattr(completion, 'citation_map', None), 'entries', ())
        if any(getattr(entry, 'source_read_ids', ()) for entry in citations) and execution is not None and any(getattr(event, 'kind', None) == 'validated_source_read_v2'
                                         for event in execution.events):
            groups[(turn.world_id, turn.conversation_id)].append(turn.turn_id)
    owner = service or AgentConversationService()
    labels = []
    for (world_id, conversation_id), identities in groups.items():
        try:
            labels.extend(owner.source_name_labels(world_id, conversation_id, list(dict.fromkeys(identities))))
        except Exception:  # Optional display metadata cannot change citation authority.
            continue
    return labels


def source_name_for_read(turn, event_id, read, labels):
    expected = {'turn_id': str(turn.turn_id), 'source_read_event_id': str(event_id),
        'source_read_id': read.source_read_id, 'anchor_id': read.anchor_id,
        'evidence_ref_id': read.evidence_ref_id, 'source_artifact_id': read.source_artifact_id,
        'source_revision_id': read.source_revision_id, 'content_sha256': read.content_sha256,
        'graph_revision': turn.graph_context_receipt.graph_authority.graph_revision}
    matches = [row for row in labels if isinstance(row, dict)
        and all(row.get(key) == value for key, value in expected.items())]
    if len(matches) != 1:
        return None
    name = matches[0].get('source_name')
    return name if isinstance(name, str) and name.strip() else None
