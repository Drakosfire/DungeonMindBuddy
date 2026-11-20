"""Human source input reuses actual Core membership and exact native body selectors."""
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from dungeonmind.application.vnext import list_admitted_native_text_sources
from application_state.agent_conversation.authored_graph_references import (
    AuthoredGraphReferenceV1, AuthoredSourceReferenceV1, AuthoredReferencesV2,
    effective_references,
)
from application_state.agent_conversation.native_source_catalog import section_catalog
from apps.live_control_server.integrations.dungeonmind import native_corpus_source as owner
from tests.test_native_corpus_source_access import lane as native_source_lane, admit, GM  # noqa: F401

BODY = "# Opening\r\nA proposed note.\r\n# Episode\r\n🌿 The source describes a source-local episode.\r\n"


@pytest.fixture
def source_case(request):
    return request.getfixturevalue('native_source_lane')


def selected(lane, *, kind="section"):
    admit(lane, body=BODY)
    context = owner.prepare_native_source_context(managed_world_id="managed", principal=GM,
        repository=lane.repo, resolve_identity=lambda _: lane.bound)
    row, = list_admitted_native_text_sources(context.access).sources
    sections = section_catalog(BODY, source_artifact_id=row.source_artifact.source_artifact_id,
        native_source_revision_id=row.source_revision.source_revision_id, content_sha256=sha256(BODY.encode()).hexdigest())
    ref = AuthoredSourceReferenceV1(managed_world_id="managed", native_world_id="world:test",
        binding_version=1, knowledge_revision=context.authority.revision_id,
        source_artifact_id=row.source_artifact.source_artifact_id,
        source_revision_id=row.source_revision.source_revision_id,
        evidence_ref_id=row.evidence_ref_ids[0], content_sha256=row.source_revision.content_sha256,
        selection_kind=kind, section_id=sections[1].section_id if kind == 'section' else None,
        label="Display only, never claim authority")
    return context, ref, sections


@pytest.mark.parametrize("kind", ["section", "full_document"])
def test_human_selected_source_reads_only_its_exact_body_through_core(source_case, monkeypatch, kind):
    context, ref, sections = selected(source_case, kind=kind)
    before = source_case.repo.get_head("world:test")
    actual = owner.open_admitted_native_text
    opened = []
    def opening(access, evidence):
        opened.append(evidence)
        return actual(access, evidence)
    monkeypatch.setattr(owner, 'open_admitted_native_text', opening)
    catalog, excerpt = owner.read_authored_source(context, ref)
    expected = BODY if kind == 'full_document' else BODY[sections[1].char_start:sections[1].char_end]
    assert excerpt.text == expected
    assert excerpt.excerpt_sha256 == sha256(expected.encode()).hexdigest()
    assert catalog.source.revision.source_revision_id == ref.source_revision_id
    assert opened == [ref.evidence_ref_id]
    assert source_case.repo.get_head("world:test") == before


@pytest.mark.parametrize("field,value", [
    ('managed_world_id','foreign'), ('native_world_id','world:foreign'),
    ('binding_version',2), ('knowledge_revision','rev:missing'),
    ('source_artifact_id','source:missing'), ('source_revision_id','rev:missing'),
    ('evidence_ref_id','evidence:missing'), ('content_sha256','f'*64),
])
def test_foreign_or_stale_source_selection_is_refused_before_body_opening(source_case, monkeypatch, field, value):
    context, ref, _ = selected(source_case)
    monkeypatch.setattr(owner, 'open_admitted_native_text', lambda *_: pytest.fail('Invalid selection opened source bytes'))
    with pytest.raises(ValueError):
        owner.read_authored_source(context, ref.model_copy(update={field:value}))


def test_unavailable_source_and_player_scope_never_substitute_other_material(source_case, monkeypatch):
    context, ref, _ = selected(source_case)
    with pytest.raises(ValueError):
        owner.read_authored_source(replace(context, principal=SimpleNamespace(role='player')), ref)
    monkeypatch.setattr(owner, 'open_admitted_native_text', lambda *args: SimpleNamespace(status='unavailable'))
    with pytest.raises(ValueError, match='exact selected source is unavailable'):
        owner.read_authored_source(context, ref)


def test_source_origin_stays_exact_after_later_admission(source_case):
    original, ref, _ = selected(source_case)
    admit(source_case, 'later', body='# Later\nA different later source.\n')
    current = owner.prepare_native_source_context(managed_world_id='managed', principal=GM,
        repository=source_case.repo, resolve_identity=lambda _:source_case.bound)
    catalog, excerpt = owner.read_authored_source(current, ref)
    assert catalog.authority.revision_id == current.authority.revision_id != original.authority.revision_id
    assert catalog.source.revision.source_revision_id == ref.source_revision_id
    assert 'source-local episode' in excerpt.text and 'different later' not in excerpt.text


def test_generic_bundle_retains_distinct_source_extents_and_refuses_conflicting_snapshots(source_case):
    _, ref, _ = selected(source_case)
    object_ref = AuthoredGraphReferenceV1(managed_world_id='managed',native_world_id='world:test',
        binding_version=1,graph_revision='rev:selected',node_id='entity:example',label='Example')
    full = ref.model_copy(update={'selection_kind':'full_document','section_id':None})
    refs = AuthoredReferencesV2(references=(object_ref,ref,full))
    assert type(refs).model_validate_json(refs.model_dump_json(by_alias=True)) == refs
    assert effective_references((object_ref,ref),(ref,full)) == refs.references
    with pytest.raises(ValueError, match='conflicting'):
        effective_references((ref,), (ref.model_copy(update={'knowledge_revision':'rev:other'}),))
    with pytest.raises(ValueError):
        refs.require_world('foreign')


def test_installed_reviewed_intent_guard_keeps_unknown_bundles_and_nonarrays_closed(application_state_dsn):
    import json
    import psycopg
    with psycopg.connect(application_state_dsn) as conn:
        expression, = conn.execute(
            "SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
            "WHERE conrelid='agent.turn_reviewed_action'::regclass "
            "AND conname='turn_reviewed_action_intent_version_check'").fetchone()
        for schema, references, expected in [
            ('dmb_authored_graph_references_v1', [], True),
            ('dmb_authored_references_v2', [], True),
            ('unknown_bundle', [], False),
            ('dmb_authored_references_v2', {}, False),
            ('dmb_authored_references_v2', None, False),
        ]:
            value=dict(schema='dmb_build_graph_intent_v2',
                authored_references=dict(schema=schema,references=references))
            allowed, = conn.execute('SELECT '+expression+' FROM (SELECT %s::jsonb AS intent) AS candidate',
                (json.dumps(value),)).fetchone()
            assert allowed is expected
