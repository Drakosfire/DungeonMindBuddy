"""One-shot evaluation of existing source APIs. Never a source or claim producer."""
from contextlib import contextmanager
import base64
import fcntl
import json
import os
from pathlib import Path
import time
import traceback
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from .runner import digest, encoded, read_pin, seal


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


class SourceAuthorityRunner:
    def __init__(self, manifest, manifest_sha, backend):
        if manifest.get('mode') != 'source_authority_v1':
            raise ValueError('An explicit source-authority manifest is required')
        self.manifest, self.sha, self.backend = manifest, manifest_sha, backend
        self.output = Path(manifest['_output'])
        if self.output.stat().st_mode & 0o077:
            raise ValueError('Source evidence directory must be private')

    @contextmanager
    def locked(self):
        with (self.output / 'lifecycle.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def record(self, name, value):
        path = self.output / name
        result = seal(path, value)
        path.chmod(0o600)
        return result

    def qualification(self, expected=None):
        raw = (self.output / 'source-qualification.json').read_bytes()
        if expected is not None and digest(raw) != expected:
            raise ValueError('Source qualification pin mismatch')
        value = json.loads(raw)
        if value['manifest_sha256'] != self.sha:
            raise ValueError('Source manifest differs from qualification')
        execution = self.output / 'source-execution.json'
        if execution.exists():
            intent = json.loads(execution.read_bytes())
            if (intent.get('manifest_sha256') != self.sha
                    or intent.get('qualification_sha256') != digest(raw)):
                raise ValueError('Source execution/qualification pins differ')
        return value

    def qualify(self):
        with self.locked(), self.backend.lease():
            if (self.output / 'source-execution.json').exists():
                raise ValueError('Already dispatched; inspect without replay')
            before = self.backend.snapshot()
            prepared = self.backend.preflight()
            if self.backend.snapshot() != before:
                raise ValueError('State changed during source qualification')
            pin = self.record('source-qualification.json', {
                'manifest_sha256': self.sha, 'snapshot': before, 'prepared': prepared,
                'scope': 'Source authority only; no semantic claims or model execution'})
            return {'qualification_sha256': pin, 'operation': prepared['operation']}

    def execute(self, qualification_sha):
        if not qualification_sha:
            raise ValueError('Source qualification SHA is required')
        with self.locked(), self.backend.lease():
            qualified = self.qualification(qualification_sha)
            if (self.output / 'source-execution.json').exists():
                raise ValueError('Already dispatched; inspect without replay')
            if (self.backend.snapshot() != qualified['snapshot']
                    or self.backend.preflight() != qualified['prepared']):
                raise ValueError('Source qualification drift; no dispatch')
            self.record('source-execution.json', {'manifest_sha256': self.sha,
                        'qualification_sha256': qualification_sha,
                        'operation': qualified['prepared']['operation']})
            transport_error = False
            try:
                self.record('source-http.json', self.backend.dispatch())
            except Exception:
                transport_error = True
                self.record('source-dispatch-error.json', {'traceback': self.backend.redact(traceback.format_exc())})
            return self._inspect(qualified, 'source-outcome.json', transport_error)

    def _inspect(self, qualified, filename, transport_error=False):
        details = {}
        try:
            after = self.backend.snapshot()
            details['snapshot_sha256'] = self.record(filename + '.snapshot.json', after)
            proof = self.backend.verify(qualified, after)
            proof_sha = self.record(filename + '.proof.json', proof)
            state = 'verified'
            details['proof_sha256'] = proof_sha
        except Exception:
            details['verification_error'] = self.backend.redact(traceback.format_exc())
            try:
                committed = self.backend.committed(qualified['prepared'])
            except Exception:
                committed = False
            state = 'committed_unverified' if committed else 'outcome_unknown'
        result = {'state': state, 'manifest_sha256': self.sha,
                  'transport_error': transport_error, **details,
                  'scope': 'Source authority only; semantic publication and Gold unproven',
                  'retry': 'Never redispatch this intent; inspect owner evidence read-only'}
        self.record(filename, result)
        return result

    def inspect(self):
        with self.locked(), self.backend.lease():
            qualified = self.qualification()
            return self._inspect(qualified, f'source-inspection-{time.time_ns()}.json')

    def report(self):
        def optional(name):
            path = self.output / name
            value = json.loads(path.read_bytes()) if path.exists() else None
            if value is not None and value.get('manifest_sha256') != self.sha:
                raise ValueError('Retained source record uses another manifest')
            return value
        execution, outcome = optional('source-execution.json'), optional('source-outcome.json')
        if execution is not None:
            self.qualification(execution['qualification_sha256'])
        inspections = [p.name for p in sorted(self.output.glob('source-inspection-*.json'))
                       if not p.name.endswith(('.proof.json', '.snapshot.json'))]
        latest = optional(inspections[-1]) if inspections else outcome
        return {'execution': execution, 'outcome': outcome,
                'latest_assessment': latest,
                'state': latest['state'] if latest else ('outcome_unknown' if execution else 'not_dispatched'),
                'inspections': inspections,
                'scope': 'Source authority only; no automatic replay or semantic acceptance'}


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
        secrets = [*self.buddy.dsns.values(), os.environ.get(self.manifest['operator_token_env'], '')]
        secrets.extend(os.environ.get(spec['product_env'], '') for spec in self.buddy.db.values())
        secrets.append(self._native_write_dsn())
        for dsn in self.buddy.dsns.values():
            password = urlsplit(dsn).password
            if password:
                secrets.extend([password, unquote(password)])
        for secret in secrets:
            if secret:
                value = value.replace(secret, '[REDACTED]')
        return value

    def _native_write_dsn(self):
        parsed = urlsplit(self.buddy._dsn('native'))
        query = dict(parse_qsl(parsed.query))
        query['options'] = '-c default_transaction_read_only=off'
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path,
                           urlencode(query, quote_via=quote), parsed.fragment))

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
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        from fastapi.encoders import jsonable_encoder
        repo = native.read_repository()
        bound = native.binding(self.manifest['world_id'])
        context, access = native.access_context(repo, bound['native_world_id'])
        entities = digest(encoded(jsonable_encoder(access.parsed.entities_by_id)))
        assertions = digest(encoded({k: native.assertion_contract(v).model_dump(mode='json')
                                     for k, v in access.parsed.assertions_by_id.items()}))
        evidence = {k: digest(encoded(jsonable_encoder(v))) for k, v in access.parsed.evidence_by_id.items()}
        return repo, context, access, {'entities': entities, 'assertions': assertions, 'evidence': evidence}

    def _mutable(self, space):
        from psycopg import sql
        result = {}
        with self.buddy.connection('native') as conn:
            for table, field, value in ((HEAD, 'space_id', space), (AUTHORITY, 'singleton_id', 1)):
                schema, name = table.split('.')
                # Probes real table/column names before dispatch and binds exact row hashes.
                query = sql.SQL('SELECT md5(row_to_json(t)::text), row_to_json(t) FROM {} t WHERE {}=%s').format(
                    sql.Identifier(schema, name), sql.Identifier(field))
                rows = conn.execute(query, (value,)).fetchall()
                if len(rows) != 1:
                    raise ValueError('Established source authority row required')
                expected = ({'space_id', 'head_revision_id', 'updated_at', 'schema_version'}
                            if table == HEAD else {'singleton_id', 'epoch'})
                if set(rows[0][1]) != expected:
                    raise ValueError('Unsupported mutable source-head schema; no dispatch')
                result[table] = {'hash': rows[0][0], 'data': rows[0][1]}
        return result

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import httpx
        if self.operation == 'admit_context':
            from apps.live_control_server.routes.recap_ingest import router
            route = '/api/live/recap-ingest'
        else:
            from apps.live_control_server.routes.source_statements import router
            route = '/api/live/source-statements/extend-evidence'
        app = FastAPI()
        app.include_router(router)
        failures = []
        async def observed(scope, receive, send):
            try:
                await app(scope, receive, send)
            except Exception:
                failures.append(self.redact(traceback.format_exc()))
                raise
        def forbidden(*args, **kwargs):
            raise AssertionError('External HTTP is forbidden for source authority evaluation')
        old_sync, old_async = httpx.HTTPTransport.handle_request, httpx.AsyncHTTPTransport.handle_async_request
        try:
            httpx.HTTPTransport.handle_request = forbidden
            httpx.AsyncHTTPTransport.handle_async_request = forbidden
            self.buddy._bind(read_only=self.operation != 'admit_context')
            native_write = self._native_write_dsn()  # Ordinary Buddy native-write ban remains intact.
            os.environ[self.buddy.db['native']['product_env']] = native_write
            token = os.environ[self.manifest['operator_token_env']]
            with TestClient(observed, client=('127.0.0.1', 43010), headers={'Authorization': 'Bearer ' + token},
                            raise_server_exceptions=False) as client:
                if (os.environ.get('DMB_AGENT_GRAPH_LOCAL_PROFILE', '').strip()
                        or os.environ.get('DMB_AGENT_GRAPH_SESSION_STORE') != self.buddy.auth_path
                        or os.environ[self.buddy.db['native']['product_env']] != native_write
                        or os.environ[self.buddy.db['app']['product_env']] != self.buddy._dsn('app', write=self.operation == 'admit_context')):
                    raise ValueError('Source route startup changed isolation')
                response = client.post(route, json=self.request)
                return {'status': response.status_code, 'body_base64': base64.b64encode(response.content).decode(),
                        'body_sha256': digest(response.content), 'asgi_errors': failures}
        finally:
            self.buddy._bind(read_only=True)
            httpx.HTTPTransport.handle_request, httpx.AsyncHTTPTransport.handle_async_request = old_sync, old_async

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
