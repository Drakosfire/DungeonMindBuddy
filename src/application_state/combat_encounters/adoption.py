"""Atomic exact-version overrides and cancellation fences; no producer IO."""
from datetime import UTC,datetime
from uuid import UUID
from psycopg.types.json import Jsonb
from pydantic import ValidationError
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError,ApplicationStateIntegrityError,ApplicationStateNotFoundError,ApplicationStateValidationError
from application_state.unit_of_work import unit_of_work
from application_state.mechanics_revisions.types import RevisionOperation,digest
from application_state.world_mechanics.types import WorldMechanicsAssociation
from . import repository as repo
from .service import _require_integrity
from .types import CombatEncounterDraft,CombatMechanicsSnapshot,AcceptedCombatMechanicsSnapshot,SavedCombatMechanicsSnapshot
from .adoption_types import AdoptMechanicsRequest,AdoptionReceipt,AdoptionOutcome,AdoptionTransition,AdoptionHistoryPage


def _dsn():
    dsn=load_runtime_dsn();assert_at_head(dsn=dsn);return dsn


def intent_digest(world_id,encounter_id,request):
    return digest(dict(world_id=world_id,encounter_id=str(encounter_id),request=request.model_dump(mode='json',by_alias=True)))


def _encounter(conn,world_id,encounter_id):
    record=repo.get_encounter(conn,world_id=world_id,encounter_id=UUID(str(encounter_id)))
    if record is None:raise ApplicationStateNotFoundError('Encounter not found in this World')
    _require_integrity(record);return record


def _validated_receipt(row):
    try:
        receipt=AdoptionReceipt.model_validate(row[4])
        if (receipt.operation_id,receipt.world_id,receipt.encounter_id,receipt.created_at)!=tuple(row[:4]):
            raise ValueError('Receipt differs from routing columns')
        return receipt
    except ValueError as exc:raise ApplicationStateIntegrityError('Stored adoption receipt is invalid') from exc


def _receipt(conn,operation_id):
    row=conn.execute('SELECT operation_id,world_id,encounter_id,created_at,payload FROM combat.mechanics_adoption WHERE operation_id=%s',(operation_id,)).fetchone()
    return None if row is None else _validated_receipt(row)


def history(*,world_id,encounter_id,before_operation_id=None,limit=20,scope=None):
    """Read immutable receipts; cursor pagination never executes an adoption."""
    if type(limit) is not int or not 1<=limit<=100:
        raise ApplicationStateValidationError('History page size must be between 1 and 100')
    with unit_of_work(_dsn()) as conn:
        from application_state.combat_encounters.access import guard
        guard(conn,world_id=world_id,encounter_id=encounter_id,scope=scope)
        _encounter(conn,world_id,encounter_id)
        args=[world_id,encounter_id]
        cursor=''
        if before_operation_id is not None:
            before=_receipt(conn,before_operation_id)
            if before is None:raise ApplicationStateNotFoundError('Adoption history cursor not found')
            _scope(before,world_id,encounter_id)
            cursor=' AND (created_at,operation_id)<(%s,%s)'
            args.extend([before.created_at,before.operation_id])
        rows=conn.execute('SELECT operation_id,world_id,encounter_id,created_at,payload FROM combat.mechanics_adoption WHERE world_id=%s AND encounter_id=%s'+cursor+' ORDER BY created_at DESC,operation_id DESC LIMIT %s',(*args,limit+1)).fetchall()
        receipts=[_validated_receipt(row) for row in rows]
        return AdoptionHistoryPage(world_id=world_id,encounter_id=encounter_id,receipts=receipts[:limit],
            next_before_operation_id=receipts[limit-1].operation_id if len(receipts)>limit else None)


def _scope(receipt,world_id,encounter_id,request=None):
    if receipt.world_id!=world_id or receipt.encounter_id!=UUID(str(encounter_id)):
        raise ApplicationStateConflictError('Adoption operation belongs to another encounter')
    if request and receipt.request_digest!=intent_digest(world_id,encounter_id,request):
        raise ApplicationStateConflictError('Adoption key already belongs to different choices')


def _outcome(conn,receipt):
    current=_encounter(conn,receipt.world_id,receipt.encounter_id)
    return AdoptionOutcome(receipt=receipt,encounter=current,
        advanced_since_apply=receipt.committed_revision is not None and current.revision>receipt.committed_revision)


def inspect(*,world_id,encounter_id,operation_id,request=None,scope=None):
    with unit_of_work(_dsn()) as conn:
        from application_state.combat_encounters.access import guard
        guard(conn, world_id=world_id, encounter_id=encounter_id, scope=scope)
        receipt=_receipt(conn,operation_id)
        if receipt is None:return None
        _scope(receipt,world_id,encounter_id,request)
        return _outcome(conn,receipt)


def _lock(conn,operation_id):
    conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('combat-adoption:'+str(operation_id),))


def _insert(conn,receipt):
    conn.execute('INSERT INTO combat.mechanics_adoption(operation_id,world_id,encounter_id,created_at,payload) VALUES(%s,%s,%s,%s,%s)',
        (receipt.operation_id,receipt.world_id,receipt.encounter_id,receipt.created_at,Jsonb(receipt.model_dump(mode='json',by_alias=True))))


def cancel(*,world_id,encounter_id,request:AdoptMechanicsRequest,scope=None):
    with unit_of_work(_dsn()) as conn:
        from application_state.combat_encounters.access import guard
        guard(conn, world_id=world_id, encounter_id=encounter_id, scope=scope)
        _lock(conn,request.operation_id)
        existing=_receipt(conn,request.operation_id)
        if existing:
            _scope(existing,world_id,encounter_id,request);return _outcome(conn,existing)
        _encounter(conn,world_id,encounter_id)
        receipt=AdoptionReceipt(operation_id=request.operation_id,world_id=world_id,encounter_id=encounter_id,
            request_digest=intent_digest(world_id,encounter_id,request),state='canceled',source=request.locator,
            expected_revision=request.expected_revision,committed_revision=None,transitions=[],created_at=datetime.now(UTC))
        _insert(conn,receipt);return _outcome(conn,receipt)


def _historical_association(conn,world_id,snapshot,row_cache=None):
    """Validate the exact retained slot and predecessor chain, never current head."""
    key=snapshot.association_id;version=snapshot.association_version;first=None
    row_cache={} if row_cache is None else row_cache
    while key is not None:
        if key not in row_cache:
            row=conn.execute('SELECT payload FROM world_mechanics.association WHERE world_id=%s AND association_id=%s',(world_id,key)).fetchone()
            try:row_cache[key]=WorldMechanicsAssociation.model_validate(row[0]) if row else None
            except ValueError as exc:raise ApplicationStateIntegrityError('Historical association is invalid') from exc
        record=row_cache[key]
        if record is None or record.version!=version or record.request.target.managed_world_id!=world_id:
            raise ApplicationStateConflictError('Historical mechanics association is missing or changed')
        if first is None:
            first=record
            if record.request.target.model_dump()!=snapshot.target.model_dump() or record.proof.locator!=snapshot.locator:
                raise ApplicationStateConflictError('Actor differs from its historical association')
        elif record.request.target.node_id!=first.request.target.node_id:
            raise ApplicationStateIntegrityError('Historical association chain changed target')
        key=record.previous_association_id;version-=1
    if first is None or version!=0:raise ApplicationStateIntegrityError('Historical association chain is incomplete')
    return first


def _source_proof(conn,world_id,snapshot,origin):
    if snapshot.managed_world_id!=world_id:raise ApplicationStateConflictError('Saved mechanics belong to another World')
    if snapshot.revision_operation_id is None:
        if snapshot.locator!=origin:raise ApplicationStateIntegrityError('Original source locator changed')
    else:
        row=conn.execute('SELECT payload FROM mechanics_revision.operation WHERE operation_id=%s',(snapshot.revision_operation_id,)).fetchone()
        try:record=RevisionOperation.model_validate(row[0]) if row else None
        except ValueError as exc:raise ApplicationStateIntegrityError('Saved revision proof is invalid') from exc
        if (record is None or record.state!='committed' or record.world_id!=world_id or record.draft_id!=snapshot.draft_id
            or record.origin!=origin or str(record.origin_acceptance_operation_id)!=snapshot.origin_acceptance_operation_id
            or record.result!=snapshot.locator):raise ApplicationStateConflictError('Saved revision has no matching committed proof')


def numeric_defaults(snapshot):
    definition=snapshot.resource['definition'];profiles=definition['defenses']['armor_classes']
    profile=next((p for p in profiles if p.get('default')),profiles[0] if profiles else {})
    ac=profile.get('value');hp=definition['vitality']['hit_points'];maximum=None
    if hp.get('method')=='fixed':maximum=hp.get('fixed_value')
    elif hp.get('method')=='formula' and hp.get('formula'):
        formula=hp['formula'];maximum=formula['count']*(formula['die']+1)//2+(formula.get('modifier') or 0)
    return (ac if type(ac) is int else None,maximum if type(maximum) is int else None)


def _replace(conn,world_id,record,request,snapshot,origin):
    _source_proof(conn,world_id,snapshot,origin)
    selected={item.actor_id:item for item in request.actors};found=set();entities=[];transitions=[]
    historical_rows={};verified_saved={snapshot.snapshot_digest}
    ac,maximum=numeric_defaults(snapshot)
    for entity in record.draft.entities:
        choice=selected.get(entity.id)
        if choice is None:entities.append(entity);continue
        found.add(entity.id);prior=entity.mechanics_snapshot
        if prior is None or prior.snapshot_digest!=choice.expected_snapshot_digest:
            raise ApplicationStateConflictError(f'{entity.name}: source mechanics changed; preview again')
        if (prior.locator.statblock_id,prior.locator.contract,prior.locator.contract_version)!=(snapshot.locator.statblock_id,snapshot.locator.contract,snapshot.locator.contract_version):
            raise ApplicationStateConflictError(f'{entity.name}: select a version of the same statblock')
        if prior.resource['definition']['ruleset']!=snapshot.resource['definition']['ruleset']:
            raise ApplicationStateConflictError(f'{entity.name}: ruleset differs')
        if isinstance(prior,CombatMechanicsSnapshot):
            association=_historical_association(conn,world_id,prior,historical_rows)
            if association.request.draft_id!=snapshot.draft_id or str(association.proof.acceptance_operation_id)!=snapshot.origin_acceptance_operation_id or association.proof.locator!=origin:
                raise ApplicationStateConflictError(f'{entity.name}: original mechanics anchor differs')
        elif isinstance(prior,AcceptedCombatMechanicsSnapshot):
            if prior.managed_world_id!=world_id or prior.draft_id!=snapshot.draft_id or prior.acceptance_operation_id!=snapshot.origin_acceptance_operation_id or prior.locator!=origin:
                raise ApplicationStateConflictError(f'{entity.name}: original mechanics anchor differs')
        elif isinstance(prior,SavedCombatMechanicsSnapshot):
            if prior.snapshot_digest not in verified_saved:
                _source_proof(conn,world_id,prior,origin);verified_saved.add(prior.snapshot_digest)
            if prior.managed_world_id!=world_id or prior.draft_id!=snapshot.draft_id or prior.origin_acceptance_operation_id!=snapshot.origin_acceptance_operation_id:
                raise ApplicationStateConflictError(f'{entity.name}: saved mechanics lineage differs')
        patch={'mechanics_snapshot':snapshot}
        if choice.ac_policy=='use_saved':
            if ac is None:raise ApplicationStateValidationError(f'{entity.name}: saved AC is not numeric')
            patch['ac']=ac
        if choice.hp_policy!='keep':
            if maximum is None:raise ApplicationStateValidationError(f'{entity.name}: saved maximum HP is not numeric')
            patch['max_hp']=maximum
            if choice.hp_policy=='clamp_current':
                if type(entity.hp) is not int:raise ApplicationStateValidationError(f'{entity.name}: clamping requires numeric current HP')
                patch['hp']=min(entity.hp,maximum)
            elif choice.hp_policy=='reset_full':patch['hp']=maximum
        changed=entity.model_copy(update=patch);entities.append(changed)
        transitions.append(AdoptionTransition(actor_id=entity.id,before_snapshot_digest=prior.snapshot_digest,after_snapshot_digest=snapshot.snapshot_digest,
            ac_policy=choice.ac_policy,hp_policy=choice.hp_policy,before_ac=entity.ac,after_ac=changed.ac,
            before_hp=entity.hp,after_hp=changed.hp,before_max_hp=entity.max_hp,after_max_hp=changed.max_hp))
    if found!=set(selected):raise ApplicationStateConflictError('Selected actor is no longer in the encounter')
    try:updated=CombatEncounterDraft.model_validate(record.draft.model_dump(mode='json')|{'entities':[e.model_dump(mode='json') for e in entities]})
    except ValidationError as exc:raise ApplicationStateValidationError('Adoption exceeds encounter capacity or produces invalid tracker values; no actor changed') from exc
    return updated,transitions


def apply_verified(*,world_id,encounter_id,request,snapshot,origin,scope=None):
    with unit_of_work(_dsn()) as conn:
        from application_state.combat_encounters.access import guard
        owned_run=guard(conn, world_id=world_id, encounter_id=encounter_id, scope=scope)
        _lock(conn,request.operation_id)
        existing=_receipt(conn,request.operation_id)
        if existing:
            _scope(existing,world_id,encounter_id,request);return _outcome(conn,existing)
        if owned_run is not None:
            from application_state.combat_encounters.access import require_mutable_session
            require_mutable_session(conn, owned_run)
        before=_encounter(conn,world_id,encounter_id)
        if before.revision!=request.expected_revision:raise ApplicationStateConflictError('Encounter changed; reload and preview adoption again')
        if request.draft_id!=snapshot.draft_id or request.locator!=snapshot.locator:
            raise ApplicationStateIntegrityError('Verified mechanics differ from the selected version')
        draft,transitions=_replace(conn,world_id,before,request,snapshot,origin)
        saved=repo.cas_replace_draft(conn,world_id=world_id,encounter_id=before.encounter_id,expected_revision=request.expected_revision,
            draft=draft.model_dump(mode='json',by_alias=True),updated_at=datetime.now(UTC))
        if saved is None:raise ApplicationStateConflictError('Encounter changed; reload and preview adoption again')
        receipt=AdoptionReceipt(operation_id=request.operation_id,world_id=world_id,encounter_id=before.encounter_id,
            request_digest=intent_digest(world_id,encounter_id,request),state='applied',source=snapshot.locator,
            expected_revision=request.expected_revision,committed_revision=saved.revision,transitions=transitions,created_at=datetime.now(UTC))
        _insert(conn,receipt)
        return AdoptionOutcome(receipt=receipt,encounter=saved,advanced_since_apply=False)
