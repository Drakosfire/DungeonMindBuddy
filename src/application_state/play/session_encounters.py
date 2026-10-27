"""Exact session preparation capture. All writes share the Run creation transaction."""
from uuid import UUID

from psycopg.types.json import Jsonb

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.unit_of_work import unit_of_work
from application_state.content.playable_admission import admit_playable_revision
from application_state.combat_encounters.scene_templates import _row, digest, read_snapshot
from application_state.errors import (
    ApplicationStateConflictError, ApplicationStateIntegrityError,
    ApplicationStateValidationError,
)
from application_state.play import repository as repo
from application_state.play.types import PlayRun, PlayRunManifest, WorldPlayRunAggregate
from application_state.play.session_encounter_types import (
    WorldSessionCreateRequest, WorldSessionCreationResult,
)
from apps.live_control_server.services.play_run_edition_structure import structure_signature


def _intent(world_id, request):
    return digest({'world_id': world_id, 'request': request.model_dump(mode='json')})


def _lock_creation(conn, run_id):
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                 ('world-session:' + str(run_id),))


def _receipt(conn, world_id, run_id, request=None):
    row = _row(conn, 'SELECT * FROM play.session_preparation WHERE run_id=%s', (run_id,))
    if row is None:
        return None
    payload = row['payload']
    if row['world_id'] != world_id:
        raise ApplicationStateConflictError('Session creation key belongs to another World')
    stored = WorldSessionCreateRequest.model_validate(payload['request'])
    if (_intent(world_id, stored) != row['request_digest']
            or payload['request_digest'] != row['request_digest']
            or payload['world_id'] != world_id or payload['run_id'] != str(run_id)
            or digest(payload['preparation']) != payload['preparation_digest']):
        raise ApplicationStateIntegrityError('Session creation receipt is inconsistent')
    if request is not None and stored != request:
        raise ApplicationStateConflictError('Session creation key already has a different intent')
    return payload


def _result(conn, world_id, run_id, receipt):
    from application_state.play.service import _readable_aggregate, _resolve_world_run_owner
    run = repo.get_run(conn, run_id)
    if run is None:
        raise ApplicationStateIntegrityError('Session receipt has no retained Run')
    _resolve_world_run_owner(conn, run, world_id=world_id)
    aggregate = _readable_aggregate(run, repo.get_manifest(conn, run_id))
    require_receipt_run(run, receipt)
    return WorldSessionCreationResult(
        aggregate=WorldPlayRunAggregate(run=aggregate.run, manifest=aggregate.manifest, world_id=world_id),
        receipt=receipt,
    )



def require_receipt_run(run, receipt):
    request = WorldSessionCreateRequest.model_validate(receipt['request'])
    if (run.playable_work_object_id != request.playable_artifact_id
            or run.playable_revision_n != request.expected_playable_revision
            or run.playable_work_revision_id != request.expected_playable_work_revision_id
            or run.playable_content_sha256 != request.expected_playable_content_sha256):
        raise ApplicationStateIntegrityError('Session receipt differs from its Run source')

def _canceled(conn, world_id, run_id, request=None):
    row = _row(conn, 'SELECT * FROM play.session_creation_cancellation WHERE run_id=%s', (run_id,))
    if row is None:
        return None
    stored = WorldSessionCreateRequest.model_validate(row['request'])
    if row['world_id'] != world_id or (request is not None and stored != request):
        raise ApplicationStateConflictError('Session creation key already has a different intent')
    if _intent(world_id, stored) != row['request_digest']:
        raise ApplicationStateIntegrityError('Session cancellation receipt is inconsistent')
    return {'state': 'canceled', 'world_id': world_id, 'run_id': str(run_id),
            'request_digest': row['request_digest'], 'request': stored.model_dump(mode='json')}


def capture(conn, *, world_id, request):
    """Lock the exact source, then template heads in deterministic order."""
    admitted = admit_playable_revision(
        conn, request.playable_artifact_id, request.expected_playable_revision,
        request.expected_playable_content_sha256, expected_world_id=world_id,
        require_current=True, require_clean=True,
    )
    if admitted.work_revision.work_revision_id != request.expected_playable_work_revision_id:
        raise ApplicationStateConflictError('Session source WorkRevision changed')
    try:
        membership = structure_signature(admitted.work_revision.markdown)['membership']
    except ValueError as exc:
        raise ApplicationStateValidationError('New sessions require canonical v2 structure') from exc
    scenes = membership['scenes']
    ids = {scene['scene_id'] for scene in scenes}
    if {item.scene_id for item in request.encounters} != ids:
        raise ApplicationStateConflictError('Choose an encounter or explicit none for every source scene')
    if (ids and request.entry_scene_id not in ids) or (not ids and request.entry_scene_id is not None):
        raise ApplicationStateConflictError('Choose a source scene as the session entry')
    with conn.cursor() as cur:
        cur.execute('SELECT encounter_id FROM combat.scene_template WHERE world_id=%s AND document_id=%s ORDER BY encounter_id',
                    (world_id, request.playable_artifact_id))
        template_ids = [row[0] for row in cur.fetchall()]
    for encounter_id in template_ids:
        conn.execute('SELECT encounter_id FROM combat.encounter WHERE encounter_id=%s FOR SHARE', (encounter_id,))
    snapshots = []
    for choice in request.encounters:
        if choice.template is None:
            snapshots.append({'scene_id': choice.scene_id, 'template': None})
            continue
        if admitted.work_object.kind != 'plan':
            raise ApplicationStateConflictError('Runbook scenes cannot select Plan encounter templates')
        record = read_snapshot(conn, world_id=world_id, document_id=request.playable_artifact_id,
                               scene_id=choice.scene_id, pin=choice.template, require_head=True)
        snapshots.append({'scene_id': choice.scene_id, 'template': choice.template.model_dump(mode='json'),
                          'title': record.draft.title,
                          'enemies': [actor.name for actor in record.draft.entities]})
    return admitted, membership, {'scenes': snapshots}


def create_session(*, world_id: str, run_id: UUID | str, request: WorldSessionCreateRequest):
    from application_state.play.service import _require_world_id, _as_uuid, _derive_manifest_document, EMPTY_PROGRESS
    from apps.live_control_server.services.play_run_registry import derive_v2_opening_beat_id
    world_id = _require_world_id(world_id)
    run_id = _as_uuid(run_id, field_name='run_id')
    dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        _lock_creation(conn, run_id)
        receipt = _receipt(conn, world_id, run_id, request)
        if receipt is not None:
            return _result(conn, world_id, run_id, receipt)
        if _canceled(conn, world_id, run_id, request):
            raise ApplicationStateConflictError('Session creation was canceled')
        if repo.get_run(conn, run_id) is not None:
            raise ApplicationStateConflictError('Run already exists without this creation receipt')
        admitted, membership, preparation = capture(conn, world_id=world_id, request=request)
        revision = admitted.work_revision
        now = repo.now_utc()
        document = _derive_manifest_document(revision.markdown, run_id=run_id,
            playable_artifact_id=request.playable_artifact_id, playable_revision=revision.revision_n,
            playable_content_sha256=revision.content_sha256, sealed_at=now)
        progress = dict(EMPTY_PROGRESS)
        progress['current_scene_id'] = request.entry_scene_id
        progress['current_beat_id'] = next((scene['beat_id'] for scene in membership['scenes']
            if scene['scene_id'] == request.entry_scene_id), None) if request.entry_scene_id else derive_v2_opening_beat_id(revision.markdown)
        if progress['current_beat_id'] is None:
            raise ApplicationStateValidationError('Session source has no authored entry Beat')
        run = repo.insert_run(conn, PlayRun(run_id=run_id, campaign_id=None, world_id=world_id,
            playable_work_object_id=request.playable_artifact_id, playable_revision_n=revision.revision_n,
            playable_work_revision_id=revision.work_revision_id, playable_content_sha256=revision.content_sha256,
            run_revision=1, progress=progress, created_at=now, updated_at=now))
        repo.insert_manifest(conn, PlayRunManifest(run_id=run_id,
            playable_work_object_id=run.playable_work_object_id, playable_revision_n=run.playable_revision_n,
            playable_work_revision_id=run.playable_work_revision_id, playable_content_sha256=run.playable_content_sha256,
            manifest=document, sealed_at=now))
        receipt = {'schema_version': 'dmb_session_preparation_v1', 'world_id': world_id,
            'run_id': str(run_id), 'request': request.model_dump(mode='json'),
            'request_digest': _intent(world_id, request), 'preparation': preparation,
            'preparation_digest': digest(preparation), 'created_at': now.isoformat()}
        conn.execute('INSERT INTO play.session_preparation(run_id,world_id,request_digest,payload) VALUES(%s,%s,%s,%s)',
            (run_id, world_id, receipt['request_digest'], Jsonb(receipt)))
        return _result(conn, world_id, run_id, receipt)


def inspect_creation(*, world_id, run_id):
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        _lock_creation(conn, run_id)
        receipt = _receipt(conn, world_id, run_id)
        return _result(conn, world_id, run_id, receipt) if receipt else _canceled(conn, world_id, run_id)


def cancel_creation(*, world_id, run_id, request):
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        _lock_creation(conn, run_id)
        receipt = _receipt(conn, world_id, run_id, request)
        if receipt:
            return _result(conn, world_id, run_id, receipt)
        canceled = _canceled(conn, world_id, run_id, request)
        if canceled:
            return canceled
        if repo.get_run(conn, run_id) is not None:
            raise ApplicationStateConflictError('Run already exists without this creation receipt')
        conn.execute('INSERT INTO play.session_creation_cancellation(run_id,world_id,request_digest,request) VALUES(%s,%s,%s,%s)',
            (run_id, world_id, _intent(world_id, request), Jsonb(request.model_dump(mode='json'))))
        return _canceled(conn, world_id, run_id, request)


def initialize_draft(record, *, fresh_ids=False):
    """Preview and initialize with the same policy; only typed maximum HP heals."""
    from uuid import uuid4
    from application_state.combat_encounters.types import CombatEncounterDraft
    body = record.draft.model_dump(mode='json')
    actor_map = {actor['id']: str(uuid4()) if fresh_ids else actor['id'] for actor in body['entities']}
    changes = []
    for actor in body['entities']:
        maximum = actor['max_hp']
        if type(maximum) is int and maximum < 0:
            raise ApplicationStateValidationError('Negative maximum HP requires a revised preparation and a new session')
        previous_hp = actor['hp']
        if type(maximum) is int:
            actor['hp'] = maximum
        changes.append({'actor_id': actor['id'], 'name': actor['name'], 'hp_before': previous_hp,
                        'hp_after': actor['hp'], 'typed_maximum': type(maximum) is int,
                        'temp_hp_before': actor['temp_hp'], 'conditions_before': actor['conditions'],
                        'defeated_before': actor['defeated']})
        actor.update(id=actor_map[actor['id']], temp_hp=0, conditions=[], defeated=False)
    for group in body['groups']:
        group['member_ids'] = [actor_map[member] for member in group['member_ids']]
    body.update(round=1, active_turn_entity_id=None, round_start_entity_id=None, provenance=[])
    return CombatEncounterDraft.model_validate(body), actor_map, changes


def _captured_template(conn, *, world_id, run_id, scene_id, receipt):
    if receipt is None:
        raise ApplicationStateConflictError('This historical session has no captured encounter preparation')
    request = WorldSessionCreateRequest.model_validate(receipt['request'])
    choice = next((choice for choice in request.encounters if choice.scene_id == scene_id), None)
    if choice is None or choice.template is None:
        raise ApplicationStateConflictError('This session scene has no captured encounter')
    record = read_snapshot(conn, world_id=world_id, document_id=request.playable_artifact_id,
                           scene_id=scene_id, pin=choice.template)
    draft, _, changes = initialize_draft(record)
    preview = {'schema_version': 'dmb_scene_encounter_preview_v1', 'world_id': world_id,
        'run_id': str(run_id), 'scene_id': scene_id, 'preparation_digest': receipt['preparation_digest'],
        'template': choice.template.model_dump(mode='json'), 'initialization_policy': 'dmb_fresh_scene_encounter_v1',
        'title': draft.title, 'actors': changes,
        'round_before': record.draft.round, 'active_actor_before': record.draft.active_turn_entity_id}
    return record, preview


def preview_encounter(*, world_id, run_id, scene_id):
    from application_state.combat_encounters.access import lock_session
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        locked = lock_session(conn, world_id=world_id, run_id=run_id)
        _, preview = _captured_template(conn, world_id=world_id, run_id=run_id, scene_id=scene_id, receipt=locked.preparation)
        return {**preview, 'preview_digest': digest(preview)}


def _materialization_intent(world_id, run_id, scene_id, request):
    return {'world_id': world_id, 'run_id': str(run_id), 'scene_id': scene_id,
            'request': request.model_dump(mode='json')}


def _operation_lock(conn, operation_id):
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                 ('run-scene-encounter:' + str(operation_id),))


def _existing_materialization(conn, *, world_id, run_id, scene_id, request, preparation):
    from application_state.combat_encounters import repository as encounters
    intent = _materialization_intent(world_id, run_id, scene_id, request)
    prior = _row(conn, 'SELECT * FROM combat.run_scene_encounter WHERE operation_id=%s', (request.operation_id,))
    if prior:
        from application_state.combat_encounters.access import validate_binding
        validate_binding(prior, preparation)
        if prior['request_digest'] != digest(intent) or prior['payload']['intent'] != intent:
            raise ApplicationStateConflictError('Encounter creation key already has a different intent')
        record = encounters.get_encounter(conn, world_id=world_id, encounter_id=prior['encounter_id'])
        if record is None:
            raise ApplicationStateIntegrityError('Encounter creation receipt has no fight')
        from application_state.combat_encounters.service import _require_integrity
        _require_integrity(record)
        if prior['payload']['encounter_id'] != str(record.encounter_id):
            raise ApplicationStateIntegrityError('Encounter receipt identity is inconsistent')
        return {'state': 'applied', 'encounter': record, 'receipt': prior['payload']}
    canceled = _row(conn, 'SELECT * FROM combat.run_scene_cancellation WHERE operation_id=%s', (request.operation_id,))
    if canceled:
        if canceled['request_digest'] != digest(intent) or canceled['request'] != intent:
            raise ApplicationStateConflictError('Encounter creation key already has a different intent')
        return {'state': 'canceled', **intent}
    return None


def materialize_encounter(*, world_id, run_id, scene_id, request):
    from uuid import uuid4
    from application_state.combat_encounters import repository as encounters
    from application_state.combat_encounters.access import lock_session
    from application_state.combat_encounters.types import CombatEncounterRecord
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        owned_run = lock_session(conn, world_id=world_id, run_id=run_id)
        _operation_lock(conn, request.operation_id)
        existing = _existing_materialization(conn, world_id=world_id, run_id=run_id, scene_id=scene_id, request=request, preparation=owned_run.preparation)
        if existing:
            if existing['state'] == 'canceled':
                raise ApplicationStateConflictError('Encounter creation was canceled')
            return existing
        from application_state.combat_encounters.access import require_mutable_session
        require_mutable_session(conn, owned_run.run)
        if _row(conn, 'SELECT encounter_id FROM combat.run_scene_encounter WHERE world_id=%s AND run_id=%s AND scene_id=%s',
                (world_id, run_id, scene_id)):
            raise ApplicationStateConflictError('This session scene already has an encounter; reopen it')
        source, preview = _captured_template(conn, world_id=world_id, run_id=run_id, scene_id=scene_id, receipt=owned_run.preparation)
        if (request.expected_preparation_digest != preview['preparation_digest']
                or request.template.model_dump(mode='json') != preview['template']
                or request.preview_digest != digest(preview)):
            raise ApplicationStateConflictError('Encounter initialization differs from the confirmed preview')
        draft, actor_map, _ = initialize_draft(source, fresh_ids=True)
        now = repo.now_utc()
        record = CombatEncounterRecord(encounter_id=uuid4(), world_id=world_id, revision=1,
            ruleset=source.ruleset, ruleset_digest=source.ruleset_digest, draft=draft, created_at=now, updated_at=now)
        encounters.insert_encounter(conn, record)
        intent = _materialization_intent(world_id, run_id, scene_id, request)
        receipt = {'schema_version': 'dmb_run_scene_encounter_v1', 'intent': intent,
                   'encounter_id': str(record.encounter_id), 'actor_map': actor_map,
                   'preview': preview, 'created_at': now.isoformat()}
        conn.execute('''INSERT INTO combat.run_scene_encounter
            (encounter_id,world_id,run_id,scene_id,operation_id,template_encounter_id,template_revision,request_digest,payload)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (record.encounter_id, world_id, run_id, scene_id, request.operation_id, source.encounter_id,
             source.revision, digest(intent), Jsonb(receipt)))
        return {'state': 'applied', 'encounter': record, 'receipt': receipt}


def cancel_materialization(*, world_id, run_id, scene_id, request):
    from application_state.combat_encounters.access import lock_session
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        owned_run = lock_session(conn, world_id=world_id, run_id=run_id)
        _operation_lock(conn, request.operation_id)
        existing = _existing_materialization(conn, world_id=world_id, run_id=run_id, scene_id=scene_id, request=request, preparation=owned_run.preparation)
        if existing:
            return existing
        intent = _materialization_intent(world_id, run_id, scene_id, request)
        conn.execute('''INSERT INTO combat.run_scene_cancellation(operation_id,world_id,run_id,scene_id,request_digest,request)
            VALUES(%s,%s,%s,%s,%s,%s)''', (request.operation_id, world_id, run_id, scene_id, digest(intent), Jsonb(intent)))
        return {'state': 'canceled', **intent}


def preparation_preview(*, world_id, request, entry_scene_id=None):
    """Propose explicit choices; callers must confirm and retain the complete body."""
    from markdown_it import MarkdownIt
    from apps.live_control_server.services.plan_playable_body_target import (
        _strip_frontmatter, _line_blocks, _root_markers, _attached_heading, _heading_text,
    )
    dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        admitted = admit_playable_revision(conn, request.playable_artifact_id,
            request.expected_playable_revision, request.expected_playable_content_sha256,
            expected_world_id=world_id, require_current=True, require_clean=True)
        if admitted.work_revision.work_revision_id != request.expected_playable_work_revision_id:
            raise ApplicationStateConflictError('Session source WorkRevision changed')
        markdown = admitted.work_revision.markdown
        try:
            scenes = structure_signature(markdown)['membership']['scenes']
        except ValueError as exc:
            raise ApplicationStateValidationError('New sessions require canonical v2 structure') from exc
        source = _strip_frontmatter(markdown.lstrip('\ufeff')).replace('\r\n', '\n').replace('\r', '\n')
        tokens = MarkdownIt('commonmark', {'html': True}).parse(source)
        blocks = _line_blocks(tokens)
        attached = _attached_heading(tokens, blocks, _root_markers(tokens, blocks, source.split('\n')), source.split('\n'))
        labels = {marker.id: _heading_text(tokens, block) for block in blocks
                  if (marker := attached.get(block.token_index)) is not None and marker.kind == 'scene'}
        ids = {scene['scene_id'] for scene in scenes}
        if set(labels) != ids:
            raise ApplicationStateIntegrityError('Source scene order disagrees with admitted membership')
        with conn.cursor() as cur:
            cur.execute('SELECT scene_id,encounter_id FROM combat.scene_template WHERE world_id=%s AND document_id=%s ORDER BY encounter_id',
                        (world_id, request.playable_artifact_id))
            bindings = dict(cur.fetchall())
        for encounter_id in sorted(bindings.values()):
            conn.execute('SELECT encounter_id FROM combat.encounter WHERE encounter_id=%s FOR SHARE', (encounter_id,))
        choices = []; display = []
        for scene in scenes:
            scene_id = scene['scene_id']; pin = None; encounter = None
            if scene_id in bindings and admitted.work_object.kind == 'plan':
                from application_state.combat_encounters import repository as encounters
                encounter = encounters.get_encounter(conn, world_id=world_id, encounter_id=bindings[scene_id])
                if encounter is None:
                    raise ApplicationStateIntegrityError('Prepared scene encounter is missing')
                version = _row(conn, 'SELECT digest FROM combat.scene_template_version WHERE encounter_id=%s AND revision=%s',
                               (encounter.encounter_id, encounter.revision))
                if version is None:
                    raise ApplicationStateIntegrityError('Prepared scene encounter history is missing')
                pin = {'encounter_id': str(encounter.encounter_id), 'revision': encounter.revision, 'digest': version['digest']}
            choices.append({'scene_id': scene_id, 'template': pin})
            display.append({'scene_id': scene_id, 'name': labels[scene_id],
                            'encounter_name': encounter.draft.title if encounter else None,
                            'enemies': [actor.name for actor in encounter.draft.entities] if encounter else [],
                            'template': pin})
        # Membership and encounter choices retain canonical identity order. The
        # author-facing list and unspecified entry use the existing root traversal.
        display_by_id = {scene['scene_id']: scene for scene in display}
        display = [display_by_id[scene_id] for scene_id in labels]
        if entry_scene_id is not None and entry_scene_id not in ids:
            raise ApplicationStateConflictError('Selected entry scene is absent from saved source')
        selected = entry_scene_id if entry_scene_id is not None else next(iter(labels), None)
        body = WorldSessionCreateRequest(**request.model_dump(), schema_version='dmb_world_session_create_v1',
                                         entry_scene_id=selected, encounters=choices)
        return {'request': body.model_dump(mode='json'), 'scenes': display,
                'excluded_orphan_count': len(set(bindings)-ids)}


def read_encounter(*, world_id, run_id, scene_id):
    from application_state.combat_encounters.access import lock_session
    from application_state.combat_encounters import repository as encounters
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        locked = lock_session(conn, world_id=world_id, run_id=run_id)
        row = _row(conn, 'SELECT * FROM combat.run_scene_encounter WHERE world_id=%s AND run_id=%s AND scene_id=%s',
                   (world_id, run_id, scene_id))
        if row is None:
            return None
        from application_state.combat_encounters.access import validate_binding
        validate_binding(row, locked.preparation)
        record = encounters.get_encounter(conn, world_id=world_id, encounter_id=row['encounter_id'])
        if record is None:
            raise ApplicationStateIntegrityError('Session encounter binding has no fight')
        return {'state': 'applied', 'encounter': record, 'receipt': row['payload']}


def inspect_materialization(*, world_id, run_id, scene_id, request):
    from application_state.combat_encounters.access import lock_session
    run_id = UUID(str(run_id)); dsn = load_runtime_dsn(); assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        owned_run = lock_session(conn, world_id=world_id, run_id=run_id)
        _operation_lock(conn, request.operation_id)
        return _existing_materialization(conn, world_id=world_id, run_id=run_id, scene_id=scene_id, request=request, preparation=owned_run.preparation)
