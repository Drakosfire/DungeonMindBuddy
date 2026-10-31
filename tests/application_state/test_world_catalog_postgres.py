"""Real APP World metadata storage and explicit adoption; native authority untouched."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier

import psycopg
import pytest

from application_state.errors import (
    ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateValidationError,
)
from application_state.world_catalog import service
from application_state.world_catalog.types import (
    NativeGraphBindingRecord, NativeGraphProvisioningRecord, WorldAccessGrant,
    WorldContainerRecord, WorldContainerRegistryDocument,
)
from scripts.adopt_world_catalog import adopt_file


pytestmark = pytest.mark.usefixtures('application_state_dsn')


def _world(world_id='elderwyld', *, binding=None, owner='subject:owner'):
    return WorldContainerRecord(world_id=world_id, name='Elderwyld',
        source_root_relpath='corpus/' + world_id + '-markdown',
        created_at='2026-10-20T01:02:03.123456Z', owner_subject=owner,
        native_graph_binding=binding, access_grants=([
            WorldAccessGrant(subject='subject:writer', permissions=('write',), granted_by_subject=owner),
            WorldAccessGrant(subject='subject:reader', permissions=('read',), granted_by_subject=owner),
        ] if owner else []))


def _catalog():
    binding = NativeGraphBindingRecord(native_world_id='native:eldyrwild', status='active',
        binding_version=7, validated_at='2026-10-20T04:05:06Z', validated_head_revision_id=' rev:exact ')
    return WorldContainerRegistryDocument(records=[
        _world(binding=binding),
        _world('unowned', owner=None),
        _world('inactive', binding=binding.model_copy(update={'status': 'inactive', 'binding_version': 8})),
        _world('provisioning', binding=NativeGraphProvisioningRecord(
            native_world_id='world:' + 'a' * 32, provisioning_id='provision:' + 'b' * 32)),
        _world('reviewed', binding=binding.model_copy(update={'native_world_id': 'native:reviewed',
            'provisioning_id': 'provision:' + 'c' * 32, 'initialization_revision_id': 'rev:genesis'})),
    ])


def test_dry_run_adoption_and_exact_replay_preserve_all_metadata_without_files(monkeypatch):
    document = _catalog()
    monkeypatch.setattr(Path, 'open', lambda *_a, **_k: pytest.fail('World store opened a file'))
    report = service.adopt_world_catalog(document)
    assert report.status == 'would_adopt' and report.world_count == 5
    assert service.list_worlds() == []
    assert service.adopt_world_catalog(document, dry_run=False).status == 'adopted'
    expected = sorted(document.records, key=lambda record: record.world_id)
    assert [row.record for row in service.list_worlds()] == expected
    assert {row.revision for row in service.list_worlds()} == {1}
    assert service.adopt_world_catalog(document, dry_run=False).status == 'already_present'
    assert service.get_world('absent') is None


def test_metadata_cas_preserves_identity_and_rejects_stale_writer():
    first = service.save_world(_world(), expected_revision=0)
    changed = first.record.model_copy(update={'name': 'Renamed without identity change'})
    second = service.save_world(changed, expected_revision=first.revision)
    assert second.revision == 2 and second.record.world_id == first.record.world_id
    for expected in (0, 1):
        with pytest.raises(ApplicationStateConflictError):
            service.save_world(first.record, expected_revision=expected)
    assert service.get_world(first.record.world_id) == second


def test_concurrent_first_writers_cannot_overwrite_each_other(monkeypatch):
    barrier = Barrier(2)
    write = service._write
    def simultaneous(*args, **kwargs):
        barrier.wait(timeout=10)
        return write(*args, **kwargs)
    monkeypatch.setattr(service, '_write', simultaneous)
    def attempt(name):
        try:
            return service.save_world(_world().model_copy(update={'name': name}), expected_revision=0)
        except ApplicationStateConflictError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['first', 'second']))
    winners = [row for row in results if row is not None]
    assert len(winners) == 1
    assert service.get_world('elderwyld') == winners[0]


def test_native_claim_conflict_rolls_back_metadata_and_grants():
    document = _catalog()
    original = document.records[0]
    service.save_world(original, expected_revision=0)
    other = service.save_world(_world('other'), expected_revision=0)
    conflicting = other.record.model_copy(update={'name': 'must roll back',
        'native_graph_binding': original.native_graph_binding, 'access_grants': []})
    with pytest.raises(ApplicationStateConflictError):
        service.save_world(conflicting, expected_revision=other.revision)
    assert service.get_world('other') == other
    assert service.get_world('elderwyld').record == original


def test_populated_catalog_is_never_merged_or_repaired_by_adoption():
    before = service.save_world(_world(), expected_revision=0)
    with pytest.raises(ApplicationStateConflictError):
        service.adopt_world_catalog(_catalog(), dry_run=False)
    assert service.list_worlds() == [before]


def test_failed_adoption_rolls_back_every_world(monkeypatch):
    write = service._write
    count = 0
    def failing(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise ApplicationStateConflictError('injected interruption')
        return write(*args, **kwargs)
    monkeypatch.setattr(service, '_write', failing)
    with pytest.raises(ApplicationStateConflictError, match='interruption'):
        service.adopt_world_catalog(_catalog(), dry_run=False)
    assert service.list_worlds() == []


@pytest.mark.parametrize('violation', ['duplicate-world', 'legacy', 'invalid-owner'])
def test_invalid_catalog_cannot_create_authority(violation):
    world = _world()
    document = WorldContainerRegistryDocument(records=[world])
    if violation == 'duplicate-world':
        document = document.model_copy(update={'records': [world, world]})
    elif violation == 'legacy':
        document = document.model_copy(update={'schema_version': 'dmb_world_container_registry_v2'})
    else:
        document = document.model_copy(update={'records': [world.model_copy(update={'owner_subject': None})]})
    with pytest.raises(ApplicationStateValidationError):
        service.adopt_world_catalog(document, dry_run=False)
    assert service.list_worlds() == []


def test_corrupt_stored_access_metadata_is_reported_not_recovered(application_state_dsn):
    service.save_world(_world(), expected_revision=0)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('UPDATE workspace.managed_world SET owner_subject=NULL')
    with pytest.raises(ApplicationStateIntegrityError):
        service.list_worlds()


def test_offline_file_input_requires_exact_reviewed_hash_and_defaults_to_dry_run(tmp_path):
    path = tmp_path / 'explicit-input.json'
    raw = _catalog().model_dump_json().encode()
    path.write_bytes(raw)
    assert adopt_file(path, expected_sha256=sha256(raw).hexdigest()).status == 'would_adopt'
    assert service.list_worlds() == []
    path.write_bytes(raw + b'\n')
    with pytest.raises(ApplicationStateValidationError, match='reviewed SHA-256'):
        adopt_file(path, expected_sha256=sha256(raw).hexdigest(), apply=True)
    assert service.list_worlds() == []
    assert adopt_file(path, expected_sha256=sha256(path.read_bytes()).hexdigest(), apply=True).status == 'adopted'


@pytest.mark.parametrize('expected', [True, -1, '0'])
def test_cas_requires_an_exact_revision(expected):
    with pytest.raises(ApplicationStateValidationError):
        service.save_world(_world(), expected_revision=expected)
    assert service.list_worlds() == []


def test_provisioning_operation_cannot_be_claimed_by_another_world():
    reviewed = _catalog().records[-1]
    service.save_world(reviewed, expected_revision=0)
    other_binding = reviewed.native_graph_binding.model_copy(update={'native_world_id': 'native:distinct'})
    with pytest.raises(ApplicationStateConflictError):
        service.save_world(_world('another', binding=other_binding), expected_revision=0)
    assert service.get_world('another') is None
    assert service.get_world(reviewed.world_id).record == reviewed
