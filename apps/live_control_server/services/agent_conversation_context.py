"""Conversation-only working knowledge; retained routes are not graph authority.

Remove prior provider tool traffic from the next request while preserving visible
conversation and exact graph/source handles. New claims still require this turn's
broker to re-admit evidence. No source text is cut in half or silently truncated.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

ROUTE_MARKER = 'DMB_CONVERSATION_ROUTES_V1\n'


@dataclass(frozen=True)
class ConversationContext:
    messages: list[dict[str, str]]
    routes: dict[str, list[dict[str, Any]]]
    decisions: list[dict[str, Any]]
    before_chars: int
    after_chars: int


def _json(value: Any) -> Any:
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except ValueError:
        return None


def _question(content: str) -> str:
    # A prior exact Plan payload is redundant: this turn supplies its own basis.
    payload = _json(content.rsplit('\n', 1)[-1])
    if isinstance(payload, dict) and 'committed_plan_markdown' in payload:
        question = payload.get('user_question')
        if isinstance(question, str):
            return question
    return content


def compact_conversation_context(history: Sequence[Mapping[str, Any]]) -> ConversationContext:
    nodes: dict[tuple[str, str, str], dict[str, Any]] = {}
    sources: dict[tuple[str, str, str], dict[str, Any]] = {}
    messages: list[dict[str, str]] = []
    decisions: list[dict[str, Any]] = []
    before_chars = sum(len(str(m.get('content') or '')) for m in history)

    def remember(route: Mapping[str, Any], *, source: bool) -> None:
        key_name = 'anchor_id' if source else 'node_id'
        identity = route.get(key_name)
        world, revision = route.get('world_id'), route.get('graph_revision')
        if not all(isinstance(x, str) and x for x in (identity, world, revision)):
            return
        fields = ('anchor_id', 'evidence_ref_id', 'source_artifact_id', 'source_revision_id') if source else ('node_id', 'label', 'kind')
        safe = {k: route[k] for k in (*fields, 'world_id', 'graph_revision') if isinstance(route.get(k), str)}
        (sources if source else nodes)[(world, revision, identity)] = safe

    def collect(result: Any) -> None:
        if not isinstance(result, dict):
            return
        if result.get('schema') == 'dmb_read_graph_source_batch_v1':
            for read in result.get('reads', []):
                collect(read)
            return
        snapshot = result.get('snapshot')
        if not isinstance(snapshot, dict):
            return
        scope = {'world_id': snapshot.get('worldId'), 'graph_revision': snapshot.get('revisionId')}
        if result.get('schema') == 'dmb_world_graph_retrieval_result_v1':
            for node in result.get('nodes', []):
                if isinstance(node, dict):
                    remember({**scope, 'node_id': node.get('nodeId'), 'label': node.get('label'), 'kind': node.get('kind')}, source=False)
            for anchor in result.get('sourceAnchors', []):
                if isinstance(anchor, dict):
                    remember({**scope, 'anchor_id': anchor.get('anchorId'), 'evidence_ref_id': anchor.get('evidenceRefId'),
                              'source_artifact_id': anchor.get('sourceArtifactId'), 'source_revision_id': anchor.get('sourceRevisionId')}, source=True)
        elif result.get('schema') == 'dmb_world_graph_source_anchor_read_v1' and result.get('outcome') in {'enough', 'truncated'}:
            remember({**scope, 'anchor_id': result.get('anchorId'), 'evidence_ref_id': result.get('evidenceRefId'),
                      'source_artifact_id': result.get('sourceArtifactId'), 'source_revision_id': result.get('sourceRevisionId')}, source=True)

    for index, message in enumerate(history):
        role = message.get('role')
        content = message.get('content')
        content = content if isinstance(content, str) else ''
        if role == 'user' and content.startswith(ROUTE_MARKER):
            packet = _json(content[len(ROUTE_MARKER):])
            if isinstance(packet, dict):
                for key, source in (('nodes', False), ('sources', True)):
                    for route in packet.get(key, []):
                        if isinstance(route, dict):
                            remember(route, source=source)
            continue
        if role == 'tool':
            collect(_json(content))
            decisions.append({'action': 'prune', 'message_index': index,
                'reason': 'previous_tool_output_replaced_by_recoverable_routes',
                'tool_name': message.get('name') or message.get('tool_name'), 'removed_chars': len(content)})
            continue
        if role == 'assistant' and message.get('tool_calls'):
            decisions.append({'action': 'prune', 'message_index': index,
                              'reason': 'previous_tool_calls_are_not_current_turn_admission'})
            continue
        if role in {'user', 'assistant'} and content:
            retained = _question(content) if role == 'user' else content
            messages.append({'role': role, 'content': retained})
            decisions.append({'action': 'compact' if retained != content else 'retain', 'message_index': index,
                'reason': 'current_turn_supplies_plan_basis' if retained != content else 'visible_conversation_knowledge',
                'removed_chars': len(content) - len(retained)})
    routes = {'nodes': list(nodes.values()), 'sources': list(sources.values())}
    if nodes or sources:
        messages.insert(0, {'role': 'user', 'content': ROUTE_MARKER + json.dumps(routes, ensure_ascii=False, separators=(',', ':'))})
    return ConversationContext(messages, routes, decisions, before_chars,
                               sum(len(m['content']) for m in messages))
