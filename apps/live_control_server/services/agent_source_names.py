"""Display-only labels from already captured source reads, never new evidence."""
from collections import defaultdict


def source_names_for_turns(turns, *, service=None):
    from application_state.agent_conversation import AgentConversationService
    groups = defaultdict(list)
    saved_bases = {}
    from application_state.agent_conversation.types import BuildGraphContextReceiptV1
    for value in turns:
        base = getattr(value, 'base_projection', None)
        turn = base.turn if base is not None and base.kind == 'approved' else getattr(value, 'envelope', value)
        execution = getattr(turn, 'graph_context_execution', None)
        completion = getattr(turn, 'completion', None)
        citations = getattr(getattr(completion, 'citation_map', None), 'entries', ())
        receipt = getattr(turn, 'graph_context_receipt', None)
        if isinstance(receipt, BuildGraphContextReceiptV1) and any(
            getattr(segment, 'kind', None) == 'saved_source_claim'
            for segment in getattr(completion, 'answer_segments', ())
        ):
            basis = receipt.source_basis
            if basis.world_id == turn.world_id:
                saved_bases[tuple(basis.model_dump().values())] = basis
        if any(getattr(entry, 'source_read_ids', ()) for entry in citations) and execution is not None and any(getattr(event, 'kind', None) in {'validated_source_read_v2', 'source_passage_reused_v1'}
                                         for event in execution.events):
            groups[(turn.world_id, turn.conversation_id)].append(turn.turn_id)
    owner = service or AgentConversationService()
    labels = []
    for (world_id, conversation_id), identities in groups.items():
        try:
            labels.extend(owner.source_name_labels(world_id, conversation_id, list(dict.fromkeys(identities))))
        except Exception:  # Optional display metadata cannot change citation authority.
            continue
    labels.extend(_saved_source_names(saved_bases.values()))
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


def _saved_source_names(bases):
    from apps.live_control_server import config
    from .source_artifact_registry import get_source_artifacts
    from graph_memory.evidence.source_artifact import build_worldbuilding_source_artifact_id
    requested = {}
    for basis in bases:
        artifact_id = build_worldbuilding_source_artifact_id(workspace_document_id=basis.document_id,
            workspace_document_revision=basis.registry_revision, content_sha256=basis.content_sha256)
        requested.setdefault(artifact_id, []).append(basis)
    if not requested:
        return []
    try:
        artifacts = get_source_artifacts(config.repo_root(), set(requested))
    except Exception:  # Display-only metadata never changes source/answer authority.
        return []
    labels = []
    for artifact_id, bases in requested.items():
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            continue
        name = artifact.lineage.get('source_name')
        for basis in bases:
            if (artifact.source_artifact_id != artifact_id or artifact.source_domain != 'worldbuilding'
                or artifact.world_id != basis.world_id or artifact.workspace_document_id != basis.document_id
                or artifact.workspace_document_revision != basis.registry_revision
                or artifact.content_sha256 != basis.content_sha256 or artifact.visibility_state != basis.visibility
                or not isinstance(name, str) or not name.strip()):
                continue
            labels.append({'kind': 'saved_build_source', **basis.model_dump(), 'source_name': name})
    return labels


def source_name_for_saved_basis(basis, labels):
    expected = {'kind': 'saved_build_source', **basis.model_dump()}
    matches = [row for row in labels if isinstance(row, dict)
               and all(row.get(key) == value for key, value in expected.items())]
    if len(matches) != 1:
        return None
    name = matches[0].get('source_name')
    return name if isinstance(name, str) and name.strip() else None
