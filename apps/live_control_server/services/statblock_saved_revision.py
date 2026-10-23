"""Explicit manual revision Save, producer CAS and durable exact-key recovery."""
from datetime import UTC,datetime
from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import ValidationStatus,ValidationSeverity,AssetBindingV1Input
from uuid import UUID
from application_state.errors import ApplicationStateConflictError,ApplicationStateIntegrityError,ApplicationStateUnavailableError
from application_state.mechanics_revisions import service as operations
from application_state.mechanics_revisions.types import RevisionOperation,digest
from application_state.world_mechanics.types import MechanicsLocator
from apps.live_control_server.integrations.dungeonmind_statblocks.client import build_statblock_v1_client,verify_exact_revision_mechanics_integrity
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import source_definition_digest_from_body
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import locator_from_exact_revision,same_mechanics_locator
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
from apps.live_control_server.services.threat_draft_store import get_threat_draft
from apps.live_control_server.services.statblock_acceptance_reconciliation import list_acceptance_operations_for_draft
from apps.live_control_server.services.statblock_definition_validation import validate_definition


def _origin(root,world_id,draft_id):
    draft=get_threat_draft(root,str(draft_id))
    if draft.schema_name!='dmb_threat_draft_v2' or draft.world_id!=world_id or draft.workflow_state!='mechanics_saved' or draft.accepted_mechanics_ref is None:
        raise ApplicationStateConflictError('Select saved mechanics from this World')
    ref=draft.accepted_mechanics_ref
    matches=[op for op in list_acceptance_operations_for_draft(root,draft_id=draft.draft_id) if (
        op.authority_state=='reconciled' and op.materialization.draft_ref=='attached' and op.locator is not None
        and same_mechanics_locator(op.locator,ref.to_mechanics_locator())
        and op.source_draft_version==ref.accepted_from_draft_version
        and op.source_candidate_id==ref.accepted_from_candidate_id
        and op.validation_receipt_digest==ref.definition_digest
        and source_definition_digest_from_body(op.request_body['definition'])==ref.definition_digest)]
    if len(matches)!=1:raise ApplicationStateIntegrityError('Original mechanics have no unique acceptance proof')
    return draft,MechanicsLocator.model_validate(ref.to_mechanics_locator().model_dump()),matches[0].operation_id


def _selected(root,world_id,draft_id,revision_id):
    draft,origin,anchor=_origin(root,world_id,draft_id)
    if revision_id==origin.revision_id:return draft,origin,anchor,origin
    record=operations.find_revision(world_id=world_id,draft_id=draft_id,revision_id=revision_id)
    if record is None or record.origin!=origin or record.origin_acceptance_operation_id!=anchor:
        raise ApplicationStateConflictError('That version has no saved revision proof for this creature')
    return draft,origin,anchor,record.result


def _exact(client,locator):
    exact=client.get_exact_revision(locator.statblock_id,locator.revision_id)
    verify_exact_revision_mechanics_integrity(exact)
    if not same_mechanics_locator(locator_from_exact_revision(exact),locator.model_dump(mode='json')):
        raise ApplicationStateIntegrityError('Exact mechanics differ from their saved identity')
    return exact


def summary(record):
    return dict(operation_id=str(record.operation_id),state=record.state,base=record.base.model_dump(mode='json'),
        result=record.result.model_dump(mode='json') if record.result else None,refusal_code=record.refusal_code,
        change_summary=record.change_summary,created_at=record.created_at.isoformat())


def list_versions(root,*,world_id,draft_id,limit=50,offset=0):
    draft,origin,anchor=_origin(root,world_id,draft_id)
    rows=operations.list_operations(world_id=world_id,draft_id=draft_id,limit=limit,offset=offset)
    if any(row.origin!=origin or row.origin_acceptance_operation_id!=anchor for row in rows):
        raise ApplicationStateIntegrityError('Revision history has changed origin proof')
    pending=operations.unresolved(world_id=world_id,draft_id=draft_id)
    return dict(world_id=world_id,draft_id=draft.draft_id,name=draft.name,original=origin.model_dump(mode='json'),
        operations=[summary(row) for row in rows],pending=summary(pending) if pending else None,
        next_offset=offset+limit if len(rows)==limit else None)


def open_version(root,*,world_id,draft_id,revision_id,client=None):
    draft,_origin_locator,_anchor,locator=_selected(root,world_id,draft_id,revision_id)
    owns=client is None;active=client or build_statblock_v1_client()
    try:
        exact=_exact(active,locator)
        return dict(world_id=world_id,draft_id=draft.draft_id,locator=locator.model_dump(mode='json'),resource=exact.model_dump(mode='json'))
    finally:
        if owns:active.close()


def _resume(record,client):
    if record.state in {'committed','refused'}:return record
    if record.state=='prepared':record=operations.settle(record,state='outcome_unknown')
    try:
        result=client.append_revision(record.base.statblock_id,record.request_body)
        verify_exact_revision_mechanics_integrity(result)
        if (result.statblock_id!=record.base.statblock_id or getattr(result.parent_revision_id,"root",result.parent_revision_id)!=record.base.revision_id
            or result.definition_digest!=record.definition_digest
            or result.validation_receipt.status==ValidationStatus.invalid
            or any(issue.severity==ValidationSeverity.error for issue in result.validation_receipt.issues or [])
            or (result.provenance or {}).get('accepted_through',{}).get('buddy_manual_revision')!=str(record.operation_id)
            or result.definition.ruleset.model_dump(mode='json')!=record.request_body['definition']['ruleset']
            or [b.model_dump(mode='json',exclude_none=True) for b in result.asset_bindings or []]
                != [AssetBindingV1Input.model_validate(b).model_dump(mode='json',exclude_none=True) for b in record.request_body['asset_bindings']]):
            raise ApplicationStateIntegrityError('Appended result differs from its exact saved intent')
        locator=MechanicsLocator.model_validate(locator_from_exact_revision(result).model_dump())
        return operations.settle(record,state='committed',result=locator)
    except StatblockIntegrationError as exc:
        # These exact producer CAS errors are proven non-writes. A generic409/422
        # or uncertain/malformed success never becomes an alleged refusal.
        if exc.status_code==409 and exc.error_code in {'stale_parent_revision','parent_revision_mismatch'}:
            return operations.settle(record,state='refused',refusal_code=exc.error_code)
        return record
    except ApplicationStateIntegrityError:
        return record


def save(root,*,draft_id,request,client=None):
    intent=request.model_dump(mode='json')
    existing=operations.read(world_id=request.world_id,draft_id=draft_id,operation_id=request.operation_id)
    if existing and existing.input_digest!=digest(intent):
        raise ApplicationStateConflictError('Save key already belongs to different edits; recover its original outcome')
    if existing and existing.state in {'committed','refused'}:return summary(existing)
    owns=client is None;active=client or build_statblock_v1_client()
    try:
        if existing:return summary(_resume(existing,active))
        if operations.unresolved(world_id=request.world_id,draft_id=draft_id):
            raise ApplicationStateConflictError('Recover the unresolved Save before making another version')
        draft,origin,anchor,base=_selected(root,request.world_id,draft_id,request.base.revision_id)
        if not same_mechanics_locator(base.model_dump(),request.base):
            raise ApplicationStateConflictError('Selected source version changed')
        exact=_exact(active,base)
        if request.definition.ruleset.model_dump(mode='json')!=exact.definition.ruleset.model_dump(mode='json'):
            raise ApplicationStateConflictError('Manual revision cannot change the creature ruleset')
        validation=validate_definition(definition=request.definition,client=active)
        if validation.outcome!='success' or validation.validation_receipt is None:
            raise ApplicationStateUnavailableError('Mechanics validation is unavailable. Your edits are retained; try again when it is available.')
        if (validation.validation_receipt.status==ValidationStatus.invalid
            or any(issue.severity==ValidationSeverity.error for issue in validation.validation_receipt.issues or [])):
            raise ApplicationStateConflictError('Validate and correct the mechanics before saving')
        expected=source_definition_digest_from_body(intent['definition'])
        if validation.definition_digest!=expected or validation.validation_receipt.definition_digest!=expected:
            raise ApplicationStateIntegrityError('Validation receipt differs from the edited definition')
        from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import AppendRevisionRequestV1
        body=AppendRevisionRequestV1(idempotency_key=str(request.operation_id),parent_revision_id=base.revision_id,
            definition=request.definition,change_summary=request.change_summary,
            asset_bindings=[b.model_dump(mode='json') for b in exact.asset_bindings or []],accepted_through={'buddy_manual_revision':str(request.operation_id)})
        payload=body.model_dump(mode='json',by_alias=True,exclude_none=False)
        now=datetime.now(UTC)
        record=RevisionOperation(operation_id=request.operation_id,world_id=request.world_id,draft_id=UUID(draft.draft_id),
            origin=origin,origin_acceptance_operation_id=anchor,base=base,input_digest=digest(intent),request_body=payload,
            request_digest=digest(payload),definition_digest=expected,created_at=now,updated_at=now)
        record,_=operations.claim(record)
        return summary(_resume(record,active))
    finally:
        if owns:active.close()


def recover(root,*,world_id,draft_id,operation_id,client=None):
    record=operations.cancel_if_absent(world_id=world_id,draft_id=draft_id,operation_id=operation_id)
    if record is None:return None
    if record.state in {'committed','refused'}:return summary(record)
    owns=client is None;active=client or build_statblock_v1_client()
    try:return summary(_resume(record,active))
    finally:
        if owns:active.close()


def inspect_operation(root,*,world_id,draft_id,operation_id):
    record=operations.read(world_id=world_id,draft_id=draft_id,operation_id=operation_id)
    return dict(operation=summary(record) if record else None)


def resolve_saved_source(root,*,world_id,draft_id,locator,client=None):
    """Exact owned source plus original/successor proof for explicit consumers."""
    draft,origin,anchor,selected=_selected(root,world_id,draft_id,locator.revision_id)
    if selected!=locator:raise ApplicationStateConflictError('Selected mechanics identity changed')
    record=None if selected==origin else operations.find_revision(world_id=world_id,draft_id=draft_id,revision_id=selected.revision_id)
    owns=client is None;active=client or build_statblock_v1_client()
    try:return draft,origin,anchor,record.operation_id if record else None,_exact(active,selected)
    finally:
        if owns:active.close()
