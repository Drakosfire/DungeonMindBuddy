"""Versioned plan output contract, bound before the actual writer authorization."""
from uuid import uuid4
from .build_draft_context import digest, context_record
from .collaboration import ProposedPlanV2, ProposedPlanV3

POLICY = 'typed_plan_objective_v1'
SELECTION_POLICY = 'typed_plan_selection_v1'
INTENTIONAL_SELECTION_FORMAT = 'build_intentional_plan_selection_answer_v1'
REVIEWED_SELECTION_FORMAT = 'build_reviewed_plan_selection_answer_v1'
SELECTION_GUIDANCE = '''For every proposed plan step, include selected as a JSON boolean. Preserve the author's explicit include/defer choices. Use selected:false for deferred steps or steps awaiting a prior author decision. selected:true initializes an editable review checkbox; it never authorizes automatic execution. Supply a readable objective before steps.'''
KEY = 'plan_output_contract'
INTENTIONAL_FORMAT = 'build_intentional_response_answer_v2'
REVIEWED_FORMAT = 'build_working_draft_answer_v6'


def schema_digest(selected=False):
    if selected:
        return digest(ProposedPlanV3.model_json_schema())
    return digest({k:v for k,v in ProposedPlanV2.model_json_schema().items() if k != "$defs"})


def contract(execution):
    from .types import BuildPlanOutputContractV1
    rows = [e for e in execution.events if isinstance(e, BuildPlanOutputContractV1)] if execution else []
    if len(rows) > 1:
        raise ValueError('Plan output contract must be unique')
    return rows[0] if rows else None


def create(execution, capability):
    from .types import BuildPlanOutputContractV2, BuildJevActionSelectionV1, BuildReviewedActionSelectionV1
    if getattr(execution.policy, 'collaboration_output_policy', None) is None or capability is None:
        return None
    choices = [e for e in execution.events if isinstance(e, (BuildJevActionSelectionV1, BuildReviewedActionSelectionV1))]
    if len(choices) != 1 or choices[0].operation != 'answer_from_sources':
        return None
    captured = context_record(execution).record
    cap = digest(capability.model_dump(mode='json'))
    if cap != execution.policy.action_capability_sha256:
        raise ValueError("Plan destination differs from its admitted capability")
    return BuildPlanOutputContractV2(kind='build_plan_output_contract_v2',event_id=uuid4(),sequence=len(execution.events),policy=SELECTION_POLICY,
        selection_event_id=choices[0].event_id,selection_sha256=digest(choices[0].model_dump(mode='json',by_alias=True)),
        draft_record_id=captured.record_id,working_snapshot_sha256=captured.snapshot.snapshot_sha256,
        destination_capability_sha256=cap,plan_schema_sha256=schema_digest(True))


def validate_events(execution):
    from .types import BuildRequestedWorkResolutionV1, BuildReviewedActionSelectionV1, ProviderAttemptAuthorizedEventV1, BuildPlanOutputContractV2, BuildJevActionSelectionV1
    event = contract(execution)
    if event is None:
        return
    selection_type = BuildJevActionSelectionV1 if isinstance(event, BuildPlanOutputContractV2) else BuildRequestedWorkResolutionV1
    choices = [e for e in execution.events if isinstance(e, (selection_type, BuildReviewedActionSelectionV1))]
    captured = context_record(execution).record
    if (len(choices) != 1 or choices[0].operation != 'answer_from_sources'
        or choices[0].event_id != event.selection_event_id or choices[0].sequence >= event.sequence
        or digest(choices[0].model_dump(mode='json',by_alias=True)) != event.selection_sha256
        or getattr(execution.policy,'collaboration_output_policy',None) is None
        or event.destination_capability_sha256 != execution.policy.action_capability_sha256
        or event.draft_record_id != captured.record_id or event.working_snapshot_sha256 != captured.snapshot.snapshot_sha256
        or event.plan_schema_sha256 != schema_digest(isinstance(event,BuildPlanOutputContractV2))):
        raise ValueError('Plan output contract differs from its selected work, draft or destination')
    for prior in execution.events[:event.sequence]:
        if isinstance(prior,ProviderAttemptAuthorizedEventV1) and (prior.provider,prior.model,prior.api_mode)==execution.policy.provider_roles.writer.identity():
            raise ValueError('Plan output contract must precede writer authorization')


def validate_packet(packet, execution, auth=None):
    event = contract(execution)
    expected = event.model_dump(mode='json',by_alias=True) if event else None
    if packet.get(KEY) != expected:
        raise ValueError('Writer plan contract differs from its retained event')
    if event and auth is not None and event.sequence >= auth.sequence:
        raise ValueError('Plan contract must precede the producing writer')


def validate_completion(completion, execution, attempt_id):
    from .types import BuildIntentionalResponseCompletionV2, BuildRelationshipReviewCompletionV2, BuildIntentionalResponseCompletionV3, BuildRelationshipReviewCompletionV3, BuildPlanOutputContractV2, ProviderAttemptAuthorizedEventV1
    new = isinstance(completion,(BuildIntentionalResponseCompletionV2,BuildRelationshipReviewCompletionV2))
    event = contract(execution)
    if new:
        selected = isinstance(completion,(BuildIntentionalResponseCompletionV3,BuildRelationshipReviewCompletionV3))
        if selected != isinstance(event,BuildPlanOutputContractV2):
            raise ValueError('Plan selection completion differs from its versioned contract')
        if event is None:
            raise ValueError('Objective-aware completion requires its pre-writer contract')
        writers = [e for e in execution.events if isinstance(e,ProviderAttemptAuthorizedEventV1) and e.provider_attempt_id==attempt_id]
        if len(writers)!=1 or event.sequence >= writers[0].sequence:
            raise ValueError('Objective-aware completion lacks its exact producing writer')
    elif event is not None:
        raise ValueError('Objective-aware writer cannot complete under a historical format')


def selection_packet(packet):
    return isinstance(packet.get(KEY),dict) and packet[KEY].get('kind')=='build_plan_output_contract_v2'


def selected_schema_digest(schema):
    definitions=schema.get('$defs',{})
    plan=definitions.get('ProposedPlanV3')
    step=definitions.get('ProposedStepV2')
    if not isinstance(plan,dict) or not isinstance(step,dict):
        raise ValueError('Selection-aware schema lacks its required plan and step definitions')
    return digest({**plan,'$defs':{'ProposedStepV2':step}})
