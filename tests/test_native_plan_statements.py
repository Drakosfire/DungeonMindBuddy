"""Core-backed query/support characterization; ordinary HTTP integration remains an acceptance gate."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4
import pytest
from tests.test_source_statements import lane, commit, advance, GM, BODY
from apps.live_control_server.services.native_plan_statements import prepare_query, read_selected
from application_state.agent_conversation.native_plan_statements import NativePlanStatementReadAuthorizedV1


def bound(lane):
    return SimpleNamespace(managed_world_id=lane.world.world_id, native_world_id=lane.world.world_id,
        binding_version=1)


def query(lane, text='What did B do?', **kwargs):
    return prepare_query(lane.world.world_id, text, GM, repository=lane.repo,
        resolve_binding=lambda _: bound(lane), **kwargs)


def selected(lane, ctx, statement_ids=None):
    grant = NativePlanStatementReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=ctx.query.sha256,
        statement_ids=statement_ids or tuple(m.statement_id for m in ctx.query.matches))
    return read_selected(ctx, grant, GM, resolve_binding=lambda _: bound(lane))


def test_natural_query_discovers_qualified_statement_without_subject_id(lane):
    prepared, _ = commit(lane)
    ctx, result = query(lane)
    assert result.status == 'complete' and len(result.matches) == 1
    assert result.question == 'What did B do?'
    assert result.matches[0].statement_id != lane.ids['B']
    assert 'quote' not in result.model_dump_json() and 'B fled' not in result.model_dump_json()
    (read,), unavailable = selected(lane, ctx)
    assert not unavailable
    assert read.support.payload == prepared.envelope['payload']
    assert read.support.clause_text == BODY.splitlines(keepends=True)[0]
    assert read.source_body_bytes == len(BODY.encode())
    assert read.support.payload['embedded_content_factive'] is False
    assert read.support.payload['episode'] == 'episode-1'
    assert read.support.payload['reporter'] == lane.ids['A']


def test_identity_only_is_not_qualified_support_and_campaign_scope_is_preserved(lane):
    _, empty = query(lane, 'B')
    assert empty.discovered_entity_ids and not empty.matches
    commit(lane)
    _, hidden = query(lane, scope_mode='campaign', campaign_id='c2')
    assert not hidden.matches and hidden.universal_absence_claimed is False
    ctx, visible = query(lane, scope_mode='campaign', campaign_id='c1')
    assert visible.matches
    assert selected(lane, ctx)[0]


def test_selected_read_rejects_injected_ids_and_authority_changes(lane):
    commit(lane)
    ctx, _ = query(lane)
    with pytest.raises(ValueError, match='not discovered'):
        selected(lane, ctx, ('ent:not-discovered',))
    grant = NativePlanStatementReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=ctx.query.sha256,
        statement_ids=(ctx.query.matches[0].statement_id,))
    with pytest.raises(ValueError, match='binding changed'):
        read_selected(ctx, grant, GM, resolve_binding=lambda _: SimpleNamespace(binding_version=99))
    with pytest.raises(ValueError, match='GM authority'):
        prepare_query(lane.world.world_id, 'B', replace(GM, role='player'), repository=lane.repo,
            resolve_binding=lambda _: bound(lane))


def test_historical_query_support_survives_unrelated_head_advance(lane):
    commit(lane)
    ctx, original = query(lane)
    before, _ = selected(lane, ctx)
    advance(lane)
    after, _ = selected(lane, ctx)
    assert before == after
    assert before[0].support.ancestry[0]['revision_id'] == original.authority.revision_id


def test_missing_active_binding_is_typed_not_a_source_or_graph_fallback(lane):
    from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
    def no_graph(_):
        raise WorldGraphProjectionServiceError('Pending', code='native_graph_provisioning_pending', status_code=409)
    ctx, result = prepare_query(lane.world.world_id, 'B', GM, repository=lane.repo, resolve_binding=no_graph)
    assert ctx is None and result.reason == 'native_graph_binding_unavailable'
    assert result.managed_world_id == lane.world.world_id


def test_world_query_retains_two_campaigns_without_fabricating_common_frame(lane):
    commit(lane)
    # Publish visible identities in the second campaign through the real WK/Core
    # fixture, rather than bypassing the endpoint authority gate.
    from tests.test_source_statements import service, transport, wk, NOW, CAMPAIGN_SCOPE_AXIS
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile
    runtime = transport.runtime(lane.repo, dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_custom_predicate_profile(), now=NOW, operation_id='second-campaign-identities')
    meta = replace(lane.meta, scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, 'c2'),))
    change = wk.WorldChangeIntent(lane.world.world_id, 'query-test', tuple(
        wk.UseExisting(identity, (wk.CreateFact('c2-name-' + name, 'dnd5e:name', wk.LiteralFactValue(name), meta),))
        for name, identity in lane.ids.items()))
    runtime.commit_prepared_change(runtime.prepare_change(change), confirmed_by=GM.subject)
    lane.selection = lane.selection.model_copy(update={
        'campaign_id': 'c2', 'episode': 'episode-c2',
        'expected_parent_revision_id': lane.repo.get_head(lane.world.world_id).head_revision_id})
    commit(lane)
    ctx, result = query(lane)
    assert {m.campaign_id for m in result.matches} == {'c1', 'c2'}
    reads, unavailable = selected(lane, ctx)
    assert not unavailable
    assert {r.support.payload['clause']['campaign'] for r in reads} == {'c1', 'c2'}
    _, scoped = query(lane, scope_mode='campaign', campaign_id='c1')
    assert {m.campaign_id for m in scoped.matches} == {'c1'}


def test_query_does_not_open_clauses_before_selected_read(lane, monkeypatch):
    commit(lane)
    import apps.live_control_server.services.source_statements as statements
    import apps.live_control_server.services.native_statement_answer_context as support
    def forbidden(*_args, **_kwargs):
        pytest.fail('Source body opened during metadata-only native discovery')
    monkeypatch.setattr(statements, 'open_admitted_native_text', forbidden)
    monkeypatch.setattr(support, 'open_admitted_native_text', forbidden)
    ctx, result = query(lane)
    assert ctx is not None and result.matches
