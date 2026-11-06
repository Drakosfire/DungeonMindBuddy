"""One-shot evaluation of existing source APIs. Never a source or claim producer."""
import json
from .runner import digest, read_pin
from . import authority


HEAD = 'dungeonmind.knowledge_heads'
AUTHORITY = 'dungeonmind.knowledge_native_source_authority'
COMMON_NATIVE = {HEAD, AUTHORITY, 'dungeonmind.knowledge_head_events',
                 'dungeonmind.knowledge_publication_receipts', 'dungeonmind.knowledge_revisions'}
OWNED_NATIVE = {
    'admit_context': COMMON_NATIVE | {'dungeonmind.knowledge_native_source_admissions',
                                    'dungeonmind.knowledge_native_source_spans'},
    'extend_support': COMMON_NATIVE | {'dungeonmind.knowledge_native_source_extensions'},
}


def conserve_source_rows(before, after, operation, old_mutable, new_mutable):
    """Permit only exact head-row replacements, never blanket table exemptions."""
    for role in ('app', 'native'):
        if before[role].keys() != after[role].keys():
            raise ValueError('Source operation changed database table inventory')
        for table, rows in before[role].items():
            new = after[role][table]
            allowed = ({'ingest.run'} if operation == 'admit_context' else set()) if role == 'app' else OWNED_NATIVE[operation]
            if table not in allowed and rows != new:
                raise ValueError(f'Source operation changed unowned table: {role}.{table}')
            old_counts, new_counts = dict(rows), dict(new)
            if role == 'native' and table in (HEAD, AUTHORITY):
                old_hash, new_hash = old_mutable[table]['hash'], new_mutable[table]['hash']
                if old_counts.get(old_hash) != 1 or new_counts.get(new_hash) != 1:
                    raise ValueError('Expected mutable source row is absent or ambiguous')
                old_counts.pop(old_hash)
                new_counts.pop(new_hash)
                if old_counts != new_counts:
                    raise ValueError('Another World/head row changed')
            elif any(new_counts.get(key, 0) < count for key, count in old_counts.items()):
                raise ValueError(f'Prior source-operation rows lost: {role}.{table}')
    before_count = sum(dict(before['app']['ingest.run']).values())
    after_count = sum(dict(after['app']['ingest.run']).values())
    if after_count - before_count != int(operation == 'admit_context'):
        raise ValueError('Unexpected APP source intent count')


from .governed_operation import GovernedOperationRunner


class SourceAuthorityRunner(GovernedOperationRunner):
    """Existing source record names and semantics are retained by the shared lifecycle."""


class SourceAuthorityBackend:
    def __init__(self, manifest):
        from .buddy import Buddy
        self.manifest = manifest
        self.buddy = Buddy(manifest)
        self.item = manifest['items'][0]
        self.operation = manifest['source_authority']['operation']
        self.request = json.loads(read_pin(self.item['request']))

    def snapshot(self):
        return self.buddy.snapshot()

    def lease(self):
        return self.buddy.capture_lease()

    def redact(self, value):
        return authority.redact(self.buddy, self.manifest['operator_token_env'], value)

    def _native_write_dsn(self):
        return authority.native_write_dsn(self.buddy)

    def _source(self):
        from apps.live_control_server import config
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
        from apps.live_control_server.services.native_recap_source_admission import _selected_source
        from graph_memory.ingestion.native_recap_source import SourceScope, SourceSelection
        bound = native.binding(self.manifest['world_id'])
        data = load_reviewable_extraction_data(config.artifact_data_root(), self.item['retained_run_id'])
        if (data.run.revision != self.item['expected_run_revision']
                or data.run.campaign_id != self.item['campaign_id']
                or data.run.session_id != self.item['session_id']
                or data.source_artifact.source_artifact_id != self.item['source_artifact_id']):
            raise ValueError('Exact ingestion/source binding changed')
        selection = SourceSelection(source_artifact_id=self.item['source_artifact_id'],
                                    source_revision_id=self.item['source_revision_id'],
                                    content_sha256=self.item['effective_sha256'])
        scope = SourceScope(managed_world_id=self.manifest['world_id'],
                            native_world_id=bound['native_world_id'], binding_version=bound['binding_version'],
                            campaign_id=self.item['campaign_id'])
        source = _selected_source(selection, scope, int(self.item['session_id'].removeprefix('session-')))
        if source.markdown.encode() != data.source_bytes:
            raise ValueError('Database source differs from actual ingestion')
        return source, bound

    def _core(self):
        return authority.read_core(self.buddy, self.manifest['world_id'])

    def _mutable(self, space):
        return authority.mutable_rows(self.buddy, space)

    def _admission(self, source, bound):
        from apps.live_control_server import config
        from apps.live_control_server.services.native_recap_source_admission import inspect_saved_source
        return inspect_saved_source(config.artifact_data_root(), scope={
            **bound, 'campaign_id': self.item['campaign_id'], 'session_id': self.item['session_id']}, source=source)

    def preflight(self):
        from dungeonmind.application.vnext import open_admitted_native_text
        from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
        from apps.live_control_server.models.source_statements import ExtendSourceEvidence
        from apps.live_control_server.routes.recap_ingest import RecapIngestRequest, _source_only
        from apps.live_control_server.services.native_recap_source_admission import admission_id_for_source, _execution_mode
        source, bound = self._source()
        repo, context, access, core = self._core()
        if context != self.manifest['native_context']:
            raise ValueError('Native source context drift')
        if self.request.get('managed_world_id') != self.manifest['world_id']:
            raise ValueError('Source request World differs')
        admitted = self._admission(source, bound)
        operation_id = admission_id_for_source(
            managed_world_id=self.manifest['world_id'], native_world_id=bound['native_world_id'],
            campaign_id=self.item['campaign_id'], session_id=self.item['session_id'],
            app_source_artifact_id=source.source_artifact_id,
            app_source_revision_id=source.source_revision_id, app_body_sha256=source.content_sha256)
        if self.operation == 'admit_context':
            body = RecapIngestRequest.model_validate(self.request)
            if (not _source_only(body) or body.native_recap_source is None
                    or body.native_recap_resume is not None or body.native_recap_run_id is not None
                    or body.campaign_id != self.item['campaign_id']
                    or body.session != int(self.item['session_id'].removeprefix('session-'))
                    or body.native_recap_source.source_artifact_id != source.source_artifact_id
                    or body.native_recap_source.source_revision_id != source.source_revision_id
                    or body.native_recap_source.content_sha256 != source.content_sha256):
                raise ValueError('Only exact source-only admission is allowed')
            if admitted is not None:
                raise ValueError('Exact source intent already exists; inspect, never redispatch')
            _execution_mode()
        else:
            body = ExtendSourceEvidence.model_validate(self.request)
            NativeSourceEvidenceExtensionV1(space_id=bound['native_world_id'],
                                           **body.model_dump(exclude={'managed_world_id'}))
            operation_id = body.extension_id
            if admitted is None or admitted.state != 'admitted' or admitted.opening.state != 'verified':
                raise ValueError('Exact source must already be admitted')
            if (body.original_admission_id != admitted.admission_id
                    or body.source_artifact_id != admitted.source_artifact_id
                    or body.source_revision_id != admitted.source_revision_id
                    or body.expected_body_sha256 != source.content_sha256
                    or body.expected_parent_revision_id != context['revision_id']
                    or body.expected_source_authority_epoch != context['source_epoch']):
                raise ValueError('Extension source/parent/epoch binding differs')
            if repo.get_native_source_evidence_extension_receipt(bound['native_world_id'], body.extension_id):
                raise ValueError('Extension already exists; inspect, never redispatch')
            available = set()
            for evidence in access.parsed.evidence_by_id.values():
                if (evidence.source_artifact_id == admitted.source_artifact_id
                        and evidence.source_revision_id == admitted.source_revision_id
                        and evidence.evidence_role == 'support'):
                    opened = open_admitted_native_text(access, evidence.evidence_ref_id)
                    if opened.status == 'available':
                        available.add((opened.span_start_byte, opened.span_end_byte))
            raw = source.markdown.encode()
            for span in body.spans:
                key = (span.start_byte, span.end_byte)
                if (span.evidence_role != 'support' or key in available or span.end_byte > len(raw)
                        or digest(raw[span.start_byte:span.end_byte]) != span.expected_slice_sha256):
                    raise ValueError('Only new distinct exact SUPPORT intervals are allowed')
                raw[span.start_byte:span.end_byte].decode('utf-8')
        mutable = self._mutable(bound['native_world_id'])
        if (mutable[AUTHORITY]['data']['epoch'] != context['source_epoch']
                or mutable[HEAD]['data']['head_revision_id'] != context['revision_id']):
            raise ValueError('Source authority snapshot differs')
        return {'operation': self.operation, 'context': context, 'core': core, 'mutable': mutable,
                'binding': bound, 'operation_id': operation_id, 'source_sha256': source.content_sha256,
                'request_sha256': digest(read_pin(self.item['request']))}

    def dispatch(self):
        return authority.local_route(self.buddy, self.operation, self.request, self.manifest['operator_token_env'])

    def committed(self, prepared):
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        repo = native.read_repository()
        space = prepared['context']['space_id']
        if self.operation == 'admit_context':
            return repo.get_native_source_admission_receipt(space, prepared['operation_id']) is not None
        return repo.get_native_source_evidence_extension_receipt(space, prepared['operation_id']) is not None

    def verify(self, qualified, after):
        from dungeonmind.application.vnext import open_admitted_native_text
        from fastapi.encoders import jsonable_encoder
        source, bound = self._source()
        repo, context, access, core = self._core()
        prior = qualified['prepared']
        if bound != prior['binding'] or source.content_sha256 != prior['source_sha256']:
            raise ValueError('Qualified source/binding changed')
        status = self._admission(source, bound)
        if status is None or status.state != 'admitted' or status.opening.state != 'verified':
            raise ValueError('Source admission is not verified')
        if self.operation == 'admit_context':
            receipt = repo.get_native_source_admission_receipt(bound['native_world_id'], status.admission_id)
            if receipt is None or jsonable_encoder(receipt) != jsonable_encoder(status.native_receipt):
                raise ValueError('APP/Core source admission receipts differ')
            expected = [(status.evidence_ref_id, 'context', 0, len(source.markdown.encode()))]
        else:
            from dungeonmind.application.vnext.native_source_extension import extension_intent
            from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
            from dungeonmind.domain.canonical import canonical_sha256
            from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
            receipt = repo.get_native_source_evidence_extension_receipt(bound['native_world_id'], self.request['extension_id'])
            if receipt is None:
                raise ValueError('Source extension receipt missing; outcome unknown')
            original = repo.get_native_source_admission_receipt(bound['native_world_id'], status.admission_id)
            command = NativeSourceEvidenceExtensionV1(
                space_id=bound['native_world_id'], **{k: v for k, v in self.request.items() if k != 'managed_world_id'})
            domain, profile = native.descriptors(repo, bound['native_world_id'], prior['context']['revision_id'])
            if (original is None or receipt.intent_sha256 != extension_intent(command, domain, profile)
                    or receipt.original_admission_sha256 != canonical_sha256(original.model_dump(mode='json'))
                    or receipt.origin != original.origin or receipt.original_admission_id != status.admission_id
                    or receipt.source_artifact_id != status.source_artifact_id
                    or receipt.source_revision_id != status.source_revision_id):
                raise ValueError('Extension receipt source differs')
            by_client = {b.client_ref: b.evidence_ref_id for b in receipt.bindings}
            if set(by_client) != {s['client_ref'] for s in self.request['spans']}:
                raise ValueError('Extension binding inventory differs')
            expected = [(by_client[s['client_ref']], 'support', s['start_byte'], s['end_byte']) for s in self.request['spans']]
        publication = receipt.publication_receipt
        if (receipt.space_id != bound['native_world_id']
                or publication.space_id != bound['native_world_id']
                or publication.publication_id != prior['operation_id']
                or publication.expected_parent_revision_id != prior['context']['revision_id']
                or publication.published_revision_id != context['revision_id']
                or publication.graph_payload_sha256 != context['graph_sha256']
                or context['source_epoch'] != prior['context']['source_epoch'] + 1
                or context['domain_ref'] != prior['context']['domain_ref']
                or context['profile_ref'] != prior['context']['profile_ref']
                or receipt.source_authority_epoch != context['source_epoch']
                or repo.get_publication_receipt(bound['native_world_id'], publication.publication_id) != publication):
            raise ValueError('Exact source publication parent/child/epoch proof differs')
        if core['entities'] != prior['core']['entities'] or core['assertions'] != prior['core']['assertions']:
            raise ValueError('Source operation changed semantic entities/assertions')
        if (any(core['evidence'].get(k) != v for k, v in prior['core']['evidence'].items())
                or set(core['evidence']) - set(prior['core']['evidence']) != {e[0] for e in expected}):
            raise ValueError('Prior evidence changed or unexpected evidence was added')
        openings = []
        for identifier, role, start, end in expected:
            evidence = access.parsed.get_evidence(identifier)
            opened = open_admitted_native_text(access, identifier)
            if (evidence is None or evidence.evidence_role != role or opened.status != 'available'
                    or opened.body_text != source.markdown or opened.body_sha256 != source.content_sha256
                    or opened.source_artifact_id != status.source_artifact_id
                    or opened.source_revision_id != status.source_revision_id
                    or (opened.span_start_byte, opened.span_end_byte) != (start, end)):
                raise ValueError('Exact source role/body/interval opening failed')
            value = jsonable_encoder(opened)
            value.pop('body_text', None)  # Bytes remain authoritative in APP/Core, not a response file.
            openings.append(value)
        mutable = self._mutable(bound['native_world_id'])
        if (mutable[HEAD]['data']['head_revision_id'] != context['revision_id']
                or mutable[HEAD]['data']['schema_version'] != prior['mutable'][HEAD]['data']['schema_version']
                or mutable[AUTHORITY]['data'] != {**prior['mutable'][AUTHORITY]['data'], 'epoch': context['source_epoch']}):
            raise ValueError('Mutable source-head payload differs')
        conserve_source_rows(qualified['snapshot'], after, self.operation, prior['mutable'], mutable)
        if self.snapshot() != after:
            raise ValueError('State changed during source verification')
        return {'context': context, 'receipt': jsonable_encoder(receipt), 'openings': openings,
                'prior_rows_entities_assertions_evidence_preserved': True,
                'new_evidence_count': len(expected), 'semantic_claims_added': 0, 'provider_calls': 0,
                'scope': 'Exact source authority only; no semantic publication or Gold acceptance'}
