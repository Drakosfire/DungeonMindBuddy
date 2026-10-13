import json

from apps.live_control_server.services.agent_conversation_context import (
    ROUTE_MARKER, compact_conversation_context,
)
from apps.live_control_server.services.agent_turn_service import (
    _PLAN_GRAPH_ANSWER_INSTRUCTIONS,
    _plan_message,
)


def test_compaction_keeps_questions_answers_and_exact_source_routes_without_old_tool_traffic():
    snapshot = {'worldId': 'world-a', 'revisionId': 'revision-a'}
    source = {'schema': 'dmb_world_graph_source_anchor_read_v1', 'outcome': 'enough',
              'snapshot': snapshot, 'anchorId': 'anchor-a', 'evidenceRefId': 'evidence-a',
              'sourceArtifactId': 'source-a', 'sourceRevisionId': 'sha256:a', 'content': 'large passage ' * 1000}
    history = [
        {'role': 'user', 'content': 'Instructions\n' + json.dumps({'user_question': 'Tell me about the city.', 'committed_plan_markdown': 'Plan' * 1000})},
        {'role': 'assistant', 'tool_calls': [{'id': 'old-call'}], 'reasoning': 'PRIVATE'},
        {'role': 'tool', 'tool_name': 'read_graph_source', 'content': json.dumps(source)},
        {'role': 'assistant', 'content': 'Sara runs the city communications.'},
    ]
    compacted = compact_conversation_context(history)
    assert [m['role'] for m in compacted.messages] == ['user', 'user', 'assistant']
    assert compacted.messages[1]['content'] == 'Tell me about the city.'
    assert compacted.messages[-1]['content'] == 'Sara runs the city communications.'
    assert compacted.routes['sources'][0]['anchor_id'] == 'anchor-a'
    assert compacted.routes['sources'][0]['graph_revision'] == 'revision-a'
    assert compacted.after_chars < compacted.before_chars / 5
    encoded = json.dumps(compacted.messages)
    assert 'large passage' not in encoded
    assert 'PRIVATE' not in encoded
    assert 'old-call' not in encoded
    # A second compaction retains the source handle even after the passage has left context.
    repeated = compact_conversation_context(compacted.messages)
    assert repeated.routes == compacted.routes
    assert repeated.messages == compacted.messages


def test_same_ids_in_different_worlds_or_revisions_are_not_merged():
    def source(world, revision):
        return {'role': 'tool', 'content': json.dumps({
            'schema': 'dmb_world_graph_source_anchor_read_v1', 'outcome': 'enough',
            'snapshot': {'worldId': world, 'revisionId': revision}, 'anchorId': 'same-anchor',
            'content': 'A source passage.'})}
    compacted = compact_conversation_context([source('a', '1'), source('a', '2'), source('b', '1')])
    assert len(compacted.routes['sources']) == 3
    assert compacted.messages[0]['content'].startswith(ROUTE_MARKER)


def test_production_plan_message_strips_plan_and_appended_graph_instructions():
    history = [
        {
            'role': 'user',
            'content': _plan_message(
                'Tell me about Mirathorn.', 'SYNTHETIC_PLAN_SENTINEL'
            ) + '\n\n' + _PLAN_GRAPH_ANSWER_INSTRUCTIONS,
        },
        {'role': 'assistant', 'content': 'A short answer.'},
    ]

    compacted = compact_conversation_context(history)

    assert compacted.messages[0]['content'] == 'Tell me about Mirathorn.'
    assert 'SYNTHETIC_PLAN_SENTINEL' not in json.dumps(compacted.messages)
    assert _PLAN_GRAPH_ANSWER_INSTRUCTIONS not in json.dumps(compacted.messages)


def test_partial_source_read_keeps_exact_recoverable_route():
    partial = {
        'role': 'tool',
        'tool_name': 'read_graph_source',
        'content': json.dumps({
            'schema': 'dmb_world_graph_source_anchor_read_v1',
            'outcome': 'partial',
            'snapshot': {'worldId': 'world-a', 'revisionId': 'revision-a'},
            'anchorId': 'anchor-partial',
            'evidenceRefId': 'evidence-partial',
            'sourceArtifactId': 'source-a',
            'sourceRevisionId': 'source-revision-a',
            'content': 'Verified partial passage.',
        }),
    }

    compacted = compact_conversation_context([partial])

    assert compacted.routes['sources'] == [{
        'anchor_id': 'anchor-partial',
        'evidence_ref_id': 'evidence-partial',
        'source_artifact_id': 'source-a',
        'source_revision_id': 'source-revision-a',
        'world_id': 'world-a',
        'graph_revision': 'revision-a',
    }]
    assert 'Verified partial passage.' not in json.dumps(compacted.messages)


def test_unreadable_or_unscoped_source_is_not_retained_as_a_verified_read():
    compacted = compact_conversation_context([{'role': 'tool', 'content': json.dumps({
        'schema': 'dmb_world_graph_source_anchor_read_v1', 'outcome': 'unavailable',
        'anchorId': 'missing', 'snapshot': {'worldId': 'a', 'revisionId': '1'}})}])
    assert compacted.routes['sources'] == []
