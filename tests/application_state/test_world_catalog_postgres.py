"""Real APP World metadata storage and explicit adoption; native authority untouched."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier, Event
from time import monotonic

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


def test_create_world_is_file_free_and_reuses_exact_null_owner_reservation(monkeypatch):
    monkeypatch.setattr(Path, 'open', lambda *_a, **_k: pytest.fail('World creation opened a file'))
    first = service.create_world(name='  Glass   Orchard  ', owner_subject=None)
    second = service.create_world(name='GLASS ORCHARD', owner_subject=None)
    assert first == second
    assert first.record.name == 'Glass Orchard'
    assert first.record.world_id == 'glass-orchard'
    assert first.record.owner_subject is None
    assert first.revision == 1
    assert isinstance(first.record.native_graph_binding, NativeGraphProvisioningRecord)
    assert service.list_worlds() == [first]


def test_concurrent_create_uses_normalized_name_not_only_derived_id():
    barrier = Barrier(4)
    def attempt(name):
        barrier.wait(timeout=10)
        return service.create_world(name=name, owner_subject='subject:owner')
    # casefold names match even though ASCII-derived slugs differ.
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(attempt, ['Straße', 'STRASSE', '  Straße ', 'strasse']))
    assert all(row == rows[0] for row in rows)
    assert rows[0].revision == 1
    assert service.list_worlds() == [rows[0]]


def test_create_equal_names_keep_owners_distinct_and_idempotent():
    local = service.create_world(name='Test Realm', owner_subject=None)
    barrier = Barrier(2)
    def attempt(owner):
        barrier.wait(timeout=10)
        return service.create_world(name='TEST REALM', owner_subject=owner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        owned = list(pool.map(attempt, ['subject:one', 'subject:two']))
    rows = [local, *owned]
    assert len({row.record.world_id for row in rows}) == 3
    assert len({row.record.native_graph_binding.native_world_id for row in rows}) == 3
    assert len({row.record.native_graph_binding.provisioning_id for row in rows}) == 3
    for row in rows:
        assert service.create_world(name=' test   realm ', owner_subject=row.record.owner_subject) == row
    assert len(service.list_worlds()) == 3


def test_create_different_names_with_same_slug_conflict_without_new_rows():
    first = service.create_world(name='Glass Orchard')
    with pytest.raises(ApplicationStateConflictError):
        service.create_world(name='Glass-Orchard')
    assert service.list_worlds() == [first]


def test_create_null_owner_cannot_adopt_an_owned_name():
    first = service.create_world(name='Owned World', owner_subject='subject:one')
    with pytest.raises(ApplicationStateConflictError):
        service.create_world(name='Owned World')
    assert service.list_worlds() == [first]


def test_create_ambiguous_retained_names_never_selects_or_merges_them():
    first = service.save_world(_world(), expected_revision=0)
    second = service.save_world(_world('another-id'), expected_revision=0)
    before = service.list_worlds()
    with pytest.raises(ApplicationStateConflictError, match='ambiguous'):
        service.create_world(name=' ELDERWYLD ', owner_subject='subject:owner')
    assert service.list_worlds() == before
    assert set(row.record.world_id for row in before) == {first.record.world_id, second.record.world_id}


def test_create_reuses_retained_unbound_record_and_all_grants_without_rewriting():
    first = service.save_world(_world(), expected_revision=0)
    assert first.record.native_graph_binding is None
    assert service.create_world(name='elderwyld', owner_subject='subject:owner') == first
    assert service.get_world(first.record.world_id) == first


def test_create_partial_write_failure_rolls_back_world_and_reservation(monkeypatch):
    write = service._write
    def interrupted(*args, **kwargs):
        write(*args, **kwargs)
        raise ApplicationStateConflictError('injected create interruption')
    monkeypatch.setattr(service, '_write', interrupted)
    with pytest.raises(ApplicationStateConflictError, match='interruption'):
        service.create_world(name='Interrupted World', owner_subject='subject:owner')
    assert service.list_worlds() == []


@pytest.mark.parametrize('name,owner', [('', None), ('  ', None), ('World', ' bad-owner')])
def test_create_invalid_input_cannot_allocate_metadata(name, owner):
    with pytest.raises(ApplicationStateValidationError):
        service.create_world(name=name, owner_subject=owner)
    assert service.list_worlds() == []


def test_create_native_reservation_conflict_rolls_back_the_new_metadata(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(service, 'uuid4', lambda: SimpleNamespace(hex='a' * 32))
    first = service.create_world(name='First World')
    with pytest.raises(ApplicationStateConflictError, match='reservation'):
        service.create_world(name='Second World')
    assert service.list_worlds() == [first]
    assert service.get_world('second-world') is None


@pytest.mark.parametrize('writer', ['save', 'adoption'])
def test_create_serializes_with_other_metadata_writers_without_lock_upgrade(writer, monkeypatch, application_state_dsn):
    base = _world()
    if writer == 'save':
        service.save_world(base, expected_revision=0)
    entered = Event()
    release = Event()
    write = service._write
    writer_pid = []

    def paused(conn, record, **kwargs):
        if record.world_id == base.world_id:
            writer_pid.append(conn.info.backend_pid)
            entered.set()
            if not release.wait(timeout=10):
                raise RuntimeError('test did not release metadata writer')
        return write(conn, record, **kwargs)

    monkeypatch.setattr(service, '_write', paused)
    def ordinary_writer():
        if writer == 'save':
            return service.save_world(base, expected_revision=1)
        return service.adopt_world_catalog(WorldContainerRegistryDocument(records=[base]), dry_run=False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        saving = pool.submit(ordinary_writer)
        creating = None
        try:
            assert entered.wait(timeout=10)
            creating = pool.submit(service.create_world, name='Concurrent Create')
            # Observe the actual conflicting table-lock request, not elapsed time
            # or thread scheduling. The bounded deadline is test supervision only.
            with psycopg.connect(application_state_dsn, autocommit=True) as observer:
                deadline = monotonic() + 10
                while True:
                    waiting = observer.execute("""SELECT count(*) FROM pg_locks
                        WHERE relation='workspace.managed_world'::regclass
                        AND mode='ExclusiveLock' AND NOT granted""").fetchone()[0]
                    if waiting:
                        break
                    assert monotonic() < deadline, 'create never reached its table lock'
                    Event().wait(0.01)
                locks = {row[0] for row in observer.execute("""SELECT mode FROM pg_locks
                    WHERE relation='workspace.managed_world'::regclass
                    AND pid=%s AND granted""", (writer_pid[0],))}
            expected = 'RowExclusiveLock' if writer == 'save' else 'ExclusiveLock'
            assert expected in locks, 'writer would upgrade its table lock behind waiting create'
        finally:
            release.set()
        assert saving.result(timeout=10) is not None
        assert creating is not None
        created = creating.result(timeout=10)
    assert created.record.world_id == 'concurrent-create'
    assert {row.record.world_id for row in service.list_worlds()} == {'elderwyld', 'concurrent-create'}


def test_grant_transform_cannot_change_identity_or_binding_and_noop_keeps_revision():
    initial = service.save_world(_world(), expected_revision=0)
    def mutate_copy(record):
        record.name = "Must not persist"
        record.owner_subject = "subject:other"
        record.native_graph_binding = None
        return record.access_grants
    assert service.update_world_grants(initial.record.world_id, mutate_copy) == initial
    assert service.get_world(initial.record.world_id) == initial


def test_invalid_grant_transform_rolls_back_and_missing_world_fails_closed():
    from application_state.errors import ApplicationStateNotFoundError
    initial = service.save_world(_world(), expected_revision=0)
    with pytest.raises(ApplicationStateValidationError):
        service.update_world_grants(initial.record.world_id, lambda _: [{"subject": "bad"}])
    assert service.get_world(initial.record.world_id) == initial
    with pytest.raises(ApplicationStateNotFoundError):
        service.update_world_grants("absent", lambda _: [])


def test_grant_transforms_read_latest_serialized_state(monkeypatch):
    initial = service.save_world(_world(), expected_revision=0)
    first_inside, release_first, second_started = Event(), Event(), Event()
    seen = []
    def first(record):
        first_inside.set()
        assert release_first.wait(timeout=10)
        return record.access_grants + [WorldAccessGrant(subject="subject:first", permissions=("read",), granted_by_subject=record.owner_subject)]
    def second(record):
        seen.extend(grant.subject for grant in record.access_grants)
        return record.access_grants + [WorldAccessGrant(subject="subject:second", permissions=("read",), granted_by_subject=record.owner_subject)]
    def second_call():
        second_started.set()
        return service.update_world_grants(initial.record.world_id, second)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(service.update_world_grants, initial.record.world_id, first)
        assert first_inside.wait(timeout=10)
        b = pool.submit(second_call)
        assert second_started.wait(timeout=10)
        release_first.set()
        assert a.result(timeout=10).revision == initial.revision + 1
        assert b.result(timeout=10).revision == initial.revision + 2
    assert "subject:first" in seen
    assert {g.subject for g in service.get_world(initial.record.world_id).record.access_grants} == {"subject:writer", "subject:reader", "subject:first", "subject:second"}
