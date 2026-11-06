"""Actual correction creation and exact retry must need no local packages."""
import json
from pathlib import Path

import pytest

from application_state.ingest.components import get_component_bytes
from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV8
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import recap_semantic_candidate_correction as owner
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures('application_state_dsn')


def _actual_request(monkeypatch, tmp_path):
    _, result = _run_recap_extraction(tmp_path, client=FixtureClient())
    parent = result.run
    data = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
    payload = json.loads(data.candidate_bytes)
    node = payload['nodes'][0]
    request = RecapCandidateCorrectionRequestV8.model_validate({
        "schema": "dmb_recap_candidate_correction_request_v8",
        "expected_parent_revision": parent.revision,
        "profile_id": parent.profile_id,
        "source_revision_sha256": owner._sha(data.source_bytes),
        "span_index_sha256": owner._sha(data.span_bytes),
        'parent_run_id': parent.run_id,
        'parent_candidate_sha256': owner._sha(data.candidate_bytes),
        'node_description_replacements': [{
            'node_id': node['node_id'], 'original_description': node['description'],
            'replacement_description': 'Mirathorn is a river city.'}],
    })
    monkeypatch.setattr(owner, 'repo_root', lambda: tmp_path)
    return parent, payload, request


def test_actual_correction_create_retry_and_replay_without_files(monkeypatch, tmp_path):
    parent, payload, request = _actual_request(monkeypatch, tmp_path)
    for path in tmp_path.rglob('*'):
        if path.is_file():
            path.unlink()
    original_open = Path.open
    def guarded_open(path, *args, **kwargs):
        # Installed vocabulary resources are code/configuration, not run evidence.
        if path.is_relative_to(tmp_path):
            pytest.fail('correction opened a local run artifact')
        return original_open(path, *args, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail('correction created a local directory')
    monkeypatch.setattr(Path, 'open', guarded_open)
    monkeypatch.setattr(Path, 'mkdir', forbidden)
    first = owner.correct_recap_candidate(request)
    child = registry.get_extraction_run(tmp_path, first.run_id)
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert first.semantic_state == 'held'
    assert owner.verify_child_replay(child, parent, tmp_path)
    actual = json.loads(get_component_bytes(run_id=child.run_id,
        kind='candidate_graph', content_sha256=child.components['candidate_graph'].sha256))
    payload['nodes'][0]['description'] = 'Mirathorn is a river city.'
    assert actual == payload
    assert owner.correct_recap_candidate(request) == first
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize('violation', ['missing', 'corrupt'])
def test_frozen_child_db_evidence_cannot_be_repaired_by_retry(application_state_dsn, monkeypatch, tmp_path, violation):
    import psycopg
    parent, _, request = _actual_request(monkeypatch, tmp_path)
    first = owner.correct_recap_candidate(request)
    with psycopg.connect(application_state_dsn) as conn:
        if violation == 'missing':
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind='candidate_graph'", (first.run_id,))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='candidate_graph'", (b'corrupt', first.run_id))
    with pytest.raises(Exception, match='stored correction component unavailable'):
        owner.correct_recap_candidate(request)
    child = registry.get_extraction_run(tmp_path, first.run_id)
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert not owner.verify_child_replay(child, parent, tmp_path)


def test_retry_preserves_recorded_acceptance(monkeypatch, tmp_path):
    from application_state.ingest import service
    parent, _, request = _actual_request(monkeypatch, tmp_path)
    first = owner.correct_recap_candidate(request)
    child = registry.get_extraction_run(tmp_path, first.run_id)
    basis = service.RecapSemanticBasisV12.model_validate(child.lineage['semantic_source_binding_basis_v12'])
    decided = service.record_recap_semantic_disposition(child.run_id,
        expected_revision=child.revision, basis=basis,
        decision=service.RecapSemanticDispositionCommandV1(state='accepted',
            reviewer_id='synthetic:test-operator', review_decision_ref='synthetic:review'))
    retried = owner.correct_recap_candidate(request)
    assert retried.semantic_state == 'accepted'
    assert registry.get_extraction_run(tmp_path, child.run_id) == decided
    assert owner.verify_child_replay(decided, parent, tmp_path)


def test_parent_lease_serializes_and_releases(application_state_dsn):
    import concurrent.futures
    import threading
    from application_state.ingest.components import correction_parent_lease
    attempting, acquired = threading.Event(), threading.Event()
    def waiter():
        attempting.set()
        with correction_parent_lease('synthetic:parent'):
            acquired.set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        with correction_parent_lease('synthetic:parent'):
            future = executor.submit(waiter)
            assert attempting.wait(2)
            assert not acquired.wait(.1)
            # Different parent has a distinct namespace within the same DB.
            with correction_parent_lease('synthetic:other-parent'):
                pass
        future.result(timeout=5)
        assert acquired.is_set()
    with pytest.raises(RuntimeError):
        with correction_parent_lease('synthetic:parent'):
            raise RuntimeError('injected interruption')
    with correction_parent_lease('synthetic:parent'):
        pass


@pytest.mark.parametrize('fault', ['after_draft', 'after_candidate', 'after_prepared', 'after_reviewable'])
def test_actual_exact_retry_recovers_owned_interruption(monkeypatch, tmp_path, fault):
    from application_state.ingest import components
    parent, _, request = _actual_request(monkeypatch, tmp_path)
    original_create = owner.create_extraction_run
    original_persist = components.persist_component_payload
    original_update = owner.update_extraction_run_status
    fired = False
    def create(*args, **kwargs):
        nonlocal fired
        result = original_create(*args, **kwargs)
        if fault == 'after_draft' and not fired:
            fired = True
            raise RuntimeError('injected interruption')
        return result
    def persist(**kwargs):
        nonlocal fired
        result = original_persist(**kwargs)
        if fault == 'after_candidate' and kwargs['kind'] == 'candidate_graph' and not fired:
            fired = True
            raise RuntimeError('injected interruption')
        return result
    def update(*args, **kwargs):
        nonlocal fired
        result = original_update(*args, **kwargs)
        if fault == 'after_' + kwargs['status'].value and not fired:
            fired = True
            raise RuntimeError('injected interruption')
        return result
    with monkeypatch.context() as injected:
        injected.setattr(owner, 'create_extraction_run', create)
        injected.setattr(owner, 'update_extraction_run_status', update)
        injected.setattr(components, 'persist_component_payload', persist)
        with pytest.raises(RuntimeError, match='injected interruption'):
            owner.correct_recap_candidate(request)
    assert fired
    response = owner.correct_recap_candidate(request)
    child = registry.get_extraction_run(tmp_path, response.run_id)
    assert response.semantic_state == 'held'
    assert owner.verify_child_replay(child, parent, tmp_path)
    assert owner.correct_recap_candidate(request) == response


def test_actual_v8_type_change_preserves_all_other_bytes(monkeypatch, tmp_path):
    parent, payload, request = _actual_request(monkeypatch, tmp_path)
    node = payload['nodes'][0]
    typed = request.model_copy(update={
        'node_description_replacements': [],
        'node_type_replacements': [],
    }).model_dump(mode='json', by_alias=True)
    typed['nodeTypeReplacements'] = [{'node_id': node['node_id'],
        'expected_node_type': node['node_type'], 'replacement_node_type': 'event'}]
    request = RecapCandidateCorrectionRequestV8.model_validate(typed)
    first = owner.correct_recap_candidate(request)
    child = registry.get_extraction_run(tmp_path, first.run_id)
    actual = json.loads(get_component_bytes(run_id=child.run_id,
        kind='candidate_graph', content_sha256=child.components['candidate_graph'].sha256))
    payload['nodes'][0]['node_type'] = 'event'
    assert actual == payload
    assert first.semantic_state == 'held'
    assert owner.verify_child_replay(child, parent, tmp_path)


@pytest.mark.parametrize('state', ['exact','stranded_draft','mismatched_manifest','missing_payload','corrupt_payload'])
def test_legacy_child_reuse_is_database_owned(application_state_dsn, monkeypatch, tmp_path, state):
    from uuid import NAMESPACE_URL, uuid5
    from application_state.ingest import service
    from application_state.ingest.components import persist_component_payload
    from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
    parent, _, request = _actual_request(monkeypatch, tmp_path)
    response = owner.correct_recap_candidate(request)
    bound = registry.get_extraction_run(tmp_path, response.run_id)
    outer = service.RecapSemanticBasisV12.model_validate(bound.lineage['semantic_source_binding_basis_v12'])
    legacy_id = str(uuid5(NAMESPACE_URL,
        f'dmb:{owner.DERIVATION_V8}:{parent.run_id}:{response.parent_candidate_sha256}:{response.manifest_sha256}'))
    refs = dict(bound.components)
    refs['source_artifact'] = parent.components['source_artifact']
    refs['candidate_graph'] = refs['candidate_graph'].model_copy(update={'uri':'historical:never-open'})
    lineage = {key: value for key, value in bound.lineage.items()
        if key not in {'operation_derivation','operation_manifest_schema','semantic_source_binding_basis_v12'}}
    lineage['derivation'] = owner.DERIVATION_V8
    operation = outer.operation_basis.model_copy(update={'child_run_id':legacy_id,
        'candidate_uri':refs['candidate_graph'].uri})
    lineage['semantic_disposition'] = {'version':1,'state':'held','basis_sha256':operation.digest()}
    legacy = registry.create_extraction_run(tmp_path, run_id=legacy_id,
        source_artifact_id=parent.source_artifact_id, source_domain='recap',
        campaign_id=parent.campaign_id, session_id=parent.session_id,
        profile_id=parent.profile_id, status=ExtractionRunStatus.VALIDATED,
        components=refs, lineage=lineage)
    for kind in ('candidate_graph','source_span_index'):
        persist_component_payload(run_id=legacy_id, expected_revision=legacy.revision, kind=kind,
            payload=get_component_bytes(run_id=bound.run_id,kind=kind,content_sha256=refs[kind].sha256))
    legacy = registry.update_extraction_run_status(tmp_path, legacy_id,
        status=ExtractionRunStatus.REVIEWABLE,expected_revision=legacy.revision)
    assert owner.verify_child_replay(legacy,parent,tmp_path)
    assert assess_recap_semantics(legacy,parent=parent,
        source_revision_id=outer.source_revision_sha256,root=tmp_path).basis_sha256 == operation.digest()
    for path in tmp_path.rglob('*'):
        if path.is_file(): path.unlink()
    import psycopg
    with psycopg.connect(application_state_dsn) as conn:
        before = conn.execute('SELECT count(*) FROM ingest.run').fetchone()[0]
        if state == 'stranded_draft':
            conn.execute("UPDATE ingest.run SET status='draft' WHERE run_id=%s", (legacy_id,))
        elif state == 'mismatched_manifest':
            conn.execute("UPDATE ingest.run SET lineage=jsonb_set(lineage,'{manifest_sha256}',to_jsonb(%s::text)) WHERE run_id=%s", ('0'*64,legacy_id))
        elif state == 'missing_payload':
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind='candidate_graph'", (legacy_id,))
        elif state == 'corrupt_payload':
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='candidate_graph'", (b'corrupt',legacy_id))
    if state == 'exact':
        retried = owner.correct_recap_candidate(request)
        assert retried.run_id == legacy_id
        assert retried.semantic_state == 'held'
    else:
        with pytest.raises(owner.ExtractPromoteError, match=legacy_id):
            owner.correct_recap_candidate(request)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM ingest.run').fetchone()[0] == before


def test_disposition_during_final_resolution_is_preserved(monkeypatch, tmp_path):
    from application_state.ingest import service
    parent, _, request = _actual_request(monkeypatch, tmp_path)
    original = owner.resolve_promotable_ingest_run
    decided = None
    def resolve(run_id, **kwargs):
        nonlocal decided
        result = original(run_id, **kwargs)
        if run_id != parent.run_id and decided is None:
            child = registry.get_extraction_run(tmp_path, run_id)
            basis = service.RecapSemanticBasisV12.model_validate(child.lineage['semantic_source_binding_basis_v12'])
            decided = service.record_recap_semantic_disposition(run_id,
                expected_revision=child.revision, basis=basis,
                decision=service.RecapSemanticDispositionCommandV1(state='accepted',
                    reviewer_id='synthetic:test-operator', review_decision_ref='synthetic:concurrent-review'))
        return result
    monkeypatch.setattr(owner,'resolve_promotable_ingest_run',resolve)
    response = owner.correct_recap_candidate(request)
    assert decided is not None
    assert response.semantic_state == 'accepted'
    assert registry.get_extraction_run(tmp_path,response.run_id) == decided
