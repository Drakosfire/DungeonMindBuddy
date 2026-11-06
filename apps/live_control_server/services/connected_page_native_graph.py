"""Connected author declarations through existing native Core and WorldKeeper owners."""
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from dungeonmind.application.vnext import (
    EntityReadService, get_prospective_publication, open_admitted_native_text,
    publish_native_source_evidence_extension,
)
from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
from fastapi.encoders import jsonable_encoder
from worldkeeper.application import contracts as wk

from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import admit_native_world_source, NativeWorldSourceAdmissionError
from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from apps.live_control_server.services.graph_object_authoring_prepare import sign_publication_intent, decode_publication_intent
from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot
from graph_memory.vnext.domain_runtime import GM_LABEL, PLAYER_LABEL

from dungeonmind.domain.errors import DungeonMindError
from worldkeeper.application.preparation import InvalidWorldChange
from worldkeeper.application.commit import (
    PreparedChangeIntegrityFailure, PreparedChangeStale, PreparedChangeConflict,
    CommitAuthorityIntegrityFailure, CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationUnavailable, CommittedChangeVerificationIntegrityFailure,
)

NATIVE_ERRORS = (DungeonMindError, NativeWorldSourceAdmissionError, InvalidWorldChange,
    PreparedChangeIntegrityFailure, PreparedChangeStale, PreparedChangeConflict,
    CommitAuthorityIntegrityFailure, CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationUnavailable, CommittedChangeVerificationIntegrityFailure)

SCHEMA = 'dmb_connected_page_operation_v3'
PURPOSE = 'dmb_connected_page_native_review_v1'
PRODUCER = 'dungeonbuddy:connected-page-v1'
PERSON_CLASSES = {'dnd5e:npc', 'dungeonbuddy:character'}


class ConnectedGraphError(ValueError):
    status_code = 409


def require(condition, message):
    if not condition:
        raise ConnectedGraphError(message)


def _parent(prepared, context):
    try:
        transport.verify_prepared_parent(prepared, context)
    except ValueError as exc:
        raise ConnectedGraphError('The native Graph changed; retry the original page review') from exc


def publication_id(intent):
    return 'dmb-connected-page:v1:' + str(intent.operation_id)


def validate_identities(intent, principal, *, repository=None):
    require_native_graph_gm(principal)
    bound = native.binding(intent.world_id)
    selected = [obj for obj in (intent.place, intent.person) if obj and obj.node_id]
    if selected:
        repo = repository or native.read_repository()
        head = repo.get_head(bound['native_world_id'])
        require(head is not None, 'The selected native identities have no readable World revision')
        read, _, _, _ = native.read_context(repo, bound['native_world_id'], head.head_revision_id,
                                           None, principal.role, scope_mode='world')
        for obj in selected:
            entity = EntityReadService().get_complete_entity(read, obj.node_id)
            require(entity.found and entity.completeness.status == 'complete',
                    'An existing person or location is unavailable in this World')
            names = {a.value.value for a in entity.assertions if a.predicate == 'dnd5e:name'
                     and a.value.kind == 'literal' and isinstance(a.value.value, str)}
            classes = {a.value.term for a in entity.assertions if a.predicate == 'dnd5e:classification'
                       and a.value.kind == 'term_ref'}
            allowed = PERSON_CLASSES if obj.kind == 'npc' else {'dnd5e:location'}
            require(obj.label in names and bool(classes & allowed),
                    'The selected native identity or classification changed; review it again')
    require(native.binding(intent.world_id) == bound, 'The World binding changed during identity review')
    return bound


def _source(root, state):
    selector = state['saved_source']
    snapshot = get_committed_page_snapshot(root, state['page_id'])
    require(snapshot.record.document_id == state['page_id']
            and snapshot.record.world_id == state['intent']['world_id']
            and selector['documentId'] == state['page_id']
            and snapshot.loaded_revision == selector['revision']
            and snapshot.content_sha256 == selector['contentSha256']
            and snapshot.markdown == state['initial_markdown'],
            'The created page has newer writing. It is retained; review it before publishing connections')
    return snapshot


def _intent(intent, packet):
    bindings = packet['extension_receipt']['bindings']
    evidence = {b['client_ref']: b['evidence_ref_id'] for b in bindings}
    def metadata(index=0):
        return wk.AssertionMetadata(
            scope=(), visibility=wk.Visibility('labels_any', (GM_LABEL,)),
            epistemic_basis='asserted', claim_mode='dungeonbuddy.claim:fact', standing='established',
            evidence_ref_ids=(evidence[f'declaration:{index}'],), temporal_scope=wk.TemporalScope(kind='unknown'))
    operations = []
    def endpoint(obj, key):
        facts = (wk.CreateFact(key+'.name', 'dnd5e:name', wk.LiteralFactValue(obj.label), metadata()),)
        if obj.node_id:
            # A mention adds its new authored source; it does not reclassify an
            # existing character or copy another assertion's qualifications.
            operations.append(wk.UseExisting(obj.node_id, facts))
            return wk.DurableObjectRef(obj.node_id)
        facts += (wk.CreateFact(key+'.kind', 'dnd5e:classification',
                               wk.TermRefFactValue('dnd5e:'+obj.kind), metadata()),)
        operations.append(wk.CreateObject(key, facts))
        return wk.ResultOf(key)
    place = endpoint(intent.place, 'place')
    if intent.person:
        person = endpoint(intent.person, 'person')
        for index, predicate in enumerate(intent.relationships):
            operations.append(wk.CreateRelationship(predicate, person, 'dungeonbuddy.custom:'+predicate,
                                                     place, metadata(index)))
    return wk.WorldChangeIntent(packet['binding']['native_world_id'], PRODUCER, tuple(operations))


def _committed(repo, intent, bound):
    return get_prospective_publication(bound['native_world_id'], publication_id(intent), repository=repo)


def prepare(root, state, intent, principal, declarations, persist):
    require_native_graph_gm(principal)
    repo = native.repository()
    bound = native.binding(intent.world_id)
    packet = state['graph_request']
    prior = state['prepared']
    if prior:
        require(prior['envelope']['principal'] == principal.subject,
                'The connection review belongs to a different operator')
        require(packet['binding'] == bound, 'The reviewed World binding changed')
        if _committed(repo, intent, bound) is not None:
            return prior
        head = repo.get_head(bound['native_world_id'])
        prepared = transport.decode_prepared(prior['native_prepared'])
        if (head and head.head_revision_id == prepared.expected_parent_revision_id
                and datetime.fromisoformat(prior['envelope']['expires_at']) > datetime.now(UTC)):
            return prior
    validate_identities(intent, principal, repository=repo)
    snapshot = _source(root, state)
    if packet is None:
        admitted = admit_native_world_source(root, state['page_id'],
            expected_revision=snapshot.loaded_revision, expected_body_sha256=snapshot.content_sha256)
        require(admitted.state == 'admitted' and admitted.world_id == intent.world_id
                and admitted.space_id == bound['native_world_id'] and admitted.document_id == state['page_id'],
                'The exact initial page source is not admitted to this native World')
        context, _ = native.access_context(repo, bound['native_world_id'])
        raw = snapshot.markdown.encode()
        blocks = raw.split(b'\n\n')
        offset = len(blocks[0]) + 2
        spans = []
        for index, sentence in enumerate(declarations):
            quote = sentence.encode()
            require(blocks[index+1] == quote, 'The initial declaration interval changed')
            spans.append(dict(client_ref=f'declaration:{index}', evidence_role='support',
                start_byte=offset, end_byte=offset+len(quote), expected_slice_sha256=sha256(quote).hexdigest()))
            offset += len(quote) + 2
        extension = NativeSourceEvidenceExtensionV1(
            space_id=bound['native_world_id'], extension_id=publication_id(intent)+':source',
            original_admission_id=admitted.admission_id, source_artifact_id=admitted.source_artifact_id,
            source_revision_id=admitted.source_revision_id, expected_body_sha256=admitted.body_sha256,
            expected_parent_revision_id=context['revision_id'], expected_source_authority_epoch=context['source_epoch'],
            created_at=datetime.now(UTC), spans=spans)
        packet = {'schema': PURPOSE, 'binding': bound, 'admission': admitted.model_dump(mode='json'),
                  'extension_request': extension.model_dump(mode='json'), 'extension_receipt': None}
        state['graph_request'] = packet
        persist(state)
    require(packet['schema'] == PURPOSE and packet['binding'] == bound, 'The retained native connection request changed')
    if packet['extension_receipt'] is None:
        extension = NativeSourceEvidenceExtensionV1.model_validate(packet['extension_request'])
        prior_extension = repo.get_native_source_evidence_extension_receipt(extension.space_id, extension.extension_id)
        if prior_extension is None:
            context, _ = native.access_context(repo, bound['native_world_id'])
            extension = extension.model_copy(update={
                'expected_parent_revision_id': context['revision_id'],
                'expected_source_authority_epoch': context['source_epoch']})
            packet['extension_request'] = extension.model_dump(mode='json')
            persist(state)
        domain, profile = native.descriptors(repo, bound['native_world_id'], extension.expected_parent_revision_id)
        receipt = publish_native_source_evidence_extension(repository=repo, request=extension,
            domain_contract=domain, semantic_profile=profile, audience_labels=(GM_LABEL, PLAYER_LABEL))
        packet['extension_receipt'] = receipt.model_dump(mode='json')
        persist(state)
    context, _ = native.access_context(repo, bound['native_world_id'])
    domain, profile = native.descriptors(repo, bound['native_world_id'], context['revision_id'])
    desired = _intent(intent, packet)
    now = datetime.now(UTC)
    prepared = transport.runtime(repo, domain, profile, now=now, operation_id=publication_id(intent)).prepare_change(desired)
    _parent(prepared, context)
    require(prepared.prepared_operations == desired.operations, 'Native preparation changed the reviewed connections')
    require(native.binding(intent.world_id) == bound, 'The World binding changed during preparation')
    encoded = transport.encode_prepared(prepared)
    envelope = dict(schema=PURPOSE, purpose=PURPOSE, principal=principal.subject, binding=bound,
                    operation_id=str(intent.operation_id), intent_sha256=state['intent_sha256'],
                    prepared_digest=transport.digest(encoded), expires_at=(now+timedelta(hours=1)).isoformat())
    return {'confirm_token': sign_publication_intent(envelope), 'envelope': envelope, 'native_prepared': encoded,
            'assertions_preview': [{'summary': f'Connect this page to {intent.place.label}'}]
                + [{'summary': f'{intent.person.label} {p} {intent.place.label}'} for p in intent.relationships]}


def confirm(root, state, intent, principal):
    require_native_graph_gm(principal)
    review, packet = state['prepared'], state['graph_request']
    signed = decode_publication_intent(review['confirm_token'], allow_expired_recovery=True)
    require(signed == review['envelope'] and signed['schema'] == PURPOSE
            and signed['principal'] == principal.subject and signed['operation_id'] == str(intent.operation_id)
            and signed['intent_sha256'] == state['intent_sha256']
            and signed['prepared_digest'] == transport.digest(review['native_prepared']),
            'The native connection confirmation differs from its exact review')
    bound = native.binding(intent.world_id)
    require(bound == signed['binding'] == packet['binding'], 'The reviewed World binding changed')
    repo = native.repository()
    prepared = transport.decode_prepared(review['native_prepared'])
    require(prepared.space_id == bound['native_world_id'] and prepared.producer == PRODUCER
            and prepared.prepared_change_id == prepared.dungeonmind_publication_id == publication_id(intent)
            and prepared.prepared_operations == _intent(intent, packet).operations,
            'The prepared native connections differ from the reviewed intent')
    if _committed(repo, intent, bound) is None:
        decode_publication_intent(review['confirm_token'])
        _source(root, state)
        validate_identities(intent, principal, repository=repo)
        context, access = native.access_context(repo, bound['native_world_id'])
        _parent(prepared, context)
        for witness in prepared.evidence_witnesses:
            opened = open_admitted_native_text(access, witness.evidence_ref_id)
            require(opened.status == 'available'
                    and opened.source_artifact_id == packet['admission']['source_artifact_id']
                    and opened.source_revision_id == packet['admission']['source_revision_id'],
                    'The exact authored source evidence is unavailable')
        require(repo.open_native_source_view(bound['native_world_id']).epoch == context['source_epoch'],
                'Source authority changed during confirmation; retry the original request')
    domain, profile = native.descriptors(repo, bound['native_world_id'], prepared.expected_parent_revision_id)
    result = transport.runtime(repo, domain, profile, now=prepared.prepared_at,
                               operation_id=publication_id(intent)).commit_prepared_change(prepared, confirmed_by=principal.subject)
    return {'committed': True, 'created_node_ids': {o.client_op_id:o.durable_object_id for o in result.object_results},
            'native_world_id': bound['native_world_id'], 'published_revision_id': result.child_revision_id,
            'publication_id': result.dungeonmind_publication_id, 'verified_result': jsonable_encoder(result)}
