"""Connected-page origin selectors from exact acquired, producer-included saved reads."""
from .build_draft_context import resolve_body_aliases

KEY = 'connected_page_origin_policy'
POLICY = 'acquired_saved_page_origins_v1'
FORMAT = 'build_intentional_response_answer_v3'


def eligible(packet):
    from .build_primary_context import packet_rows
    contract = packet.get('response_contract', {})
    return (contract.get('requested_work') == 'review_connected_page'
        and contract.get('barrier') is None
        and packet.get('connected_page_review_policy') == 'typed_connected_page_review_v1'
        and bool(packet_rows(packet)))


def _primary_rows(rows, basis):
    return [{'read_id':str(r['read_id']), 'markdown':r['text'],
        '_line_offset':r['line_start']-1,
        'page':{'document_id':basis['document_id'], 'registry_revision':basis['registry_revision'],
            'content_sha256':basis['content_sha256']}} for r in rows]


def packet_rows(packet):
    from .build_primary_context import packet_rows as primary_rows
    packet = resolve_body_aliases(packet)
    primary=[]
    if KEY in packet:
        if packet[KEY] != POLICY or not eligible(packet):
            raise ValueError('Connected origin marker lacks its resolved work and saved reads')
        primary=primary_rows(packet)
    return selected_rows(packet.get('related_authored_pages',{}).get('pages',[]),primary,packet.get('source_basis'))


def selected_rows(related, primary, basis):
    """One saved-origin selector domain from actual supplied related/primary rows."""
    rows=list(related)
    if primary:
        rows += _primary_rows(primary,basis)
    if len({str(r['read_id']) for r in rows}) != len(rows):
        raise ValueError('Connected origin read selectors are ambiguous')
    return rows


def validate_packet(packet, execution, auth):
    if KEY not in packet:
        return  # Historical captured packets retain their exact selector domain.
    from . import types as t
    from .build_primary_context import project
    choices = [e for e in execution.events if isinstance(e, t.BuildRequestedWorkResolutionV1)]
    if (len(choices) != 1 or choices[0].requested_work != 'review_connected_page'
        or choices[0].resolution.get('barrier') is not None or packet[KEY] != POLICY):
        raise ValueError('Connected origin capability differs from its actual selected work')
    packet = resolve_body_aliases(packet)
    basis = packet['source_basis']
    primary = project(execution)
    if (not eligible(packet) or packet.get('artifact_under_edit') != primary
        or any(e.source_basis.model_dump(mode='json',by_alias=True) != basis
            for e in execution.events if isinstance(e, t.ValidatedBuildSectionReadV1))):
        raise ValueError('Connected primary origin differs from exact acquired saved context')
    # Prove every offered primary selector was supplied to this exact writer.
    supplied = {str(r['read_id']) for r in packet_rows(packet)}
    actual = {str(r['read_id']) for r in execution_rows(execution,basis,auth.provider_attempt_id)}
    if supplied != actual:
        raise ValueError('Connected origin selectors differ from producer inclusion')


def execution_rows(execution, basis, attempt_id):
    from . import types as t
    from .build_related_pages import RelatedPageRead, RelatedPageInclusion
    from .build_primary_context import records
    if hasattr(basis,'model_dump'):
        basis = basis.model_dump(mode='json',by_alias=True)
    auths = [e for e in execution.events if isinstance(e,t.ProviderAttemptAuthorizedEventV3)
        and e.provider_attempt_id == attempt_id]
    outcomes = [e.outcome for e in execution.events if isinstance(e,t.ProviderOutcomeEventV1)
        and e.provider_attempt_id == attempt_id]
    if (len(auths) != 1 or outcomes[-1:] != ['response_received']
        or (auths[0].provider,auths[0].model,auths[0].api_mode) != execution.policy.provider_roles.writer.identity()):
        raise ValueError('Connected origin lacks its successful producing writer')
    auth = auths[0]
    related = [e for e in execution.events if isinstance(e,RelatedPageInclusion)
        and e.provider_attempt_id == attempt_id and e.envelope_sha256 == auth.envelope_sha256]
    if len(related)>1:
        raise ValueError('Connected related origin inclusion is ambiguous')
    related_ids = set(related[0].read_ids) if related else set()
    rows = [e.model_dump(mode='json') for e in execution.events
        if isinstance(e,RelatedPageRead) and e.read_id in related_ids]
    choices = [e for e in execution.events if isinstance(e,t.BuildRequestedWorkResolutionV1)]
    if len(choices)==1 and choices[0].requested_work=='review_connected_page' and choices[0].resolution.get('barrier') is None:
        inclusions = [e for e in execution.events if isinstance(e,t.BuildSectionProviderInclusionV1)
            and e.provider_attempt_id == attempt_id and e.envelope_sha256 == auth.envelope_sha256]
        if len(inclusions)>1:
            raise ValueError('Connected primary origin inclusion is ambiguous')
        ids = set(inclusions[0].section_event_ids) if inclusions else set()
        primary = [e for e in records(execution) if e.event_id in ids]
        if any(e.source_basis.model_dump(mode='json',by_alias=True) != basis for e in primary):
            raise ValueError('Connected primary origin belongs to a different saved basis')
        rows += _primary_rows([e.model_dump(mode='json') for e in primary],basis)
    if len({str(r['read_id']) for r in rows}) != len(rows):
        raise ValueError('Connected origin producer selectors are ambiguous')
    return rows
