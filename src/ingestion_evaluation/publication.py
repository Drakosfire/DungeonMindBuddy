"""Review existing Buddy packets; only its authenticated confirmation can write."""
from contextlib import contextmanager
from datetime import datetime, timezone
import base64
import fcntl
import json
import os
from pathlib import Path
import time
import traceback

from . import authority
from .runner import digest, encoded, read_pin, seal

OWNED = {authority.HEAD, 'dungeonmind.knowledge_head_events',
         'dungeonmind.knowledge_prospective_publication_results',
         'dungeonmind.knowledge_publication_receipts', 'dungeonmind.knowledge_revisions'}


def conserve_publication(before, after, old_head, new_head):
    if before['app'] != after['app'] or before['native'].keys() != after['native'].keys():
        raise ValueError('Publication changed APP or native table inventory')
    for table, rows in before['native'].items():
        newer = after['native'][table]
        if table not in OWNED:
            if rows != newer:
                raise ValueError(f'Publication changed unowned table: {table}')
            continue
        old, new = dict(rows), dict(newer)
        if table == authority.HEAD:
            if old.pop(old_head['hash'], None) != 1 or new.pop(new_head['hash'], None) != 1 or old != new:
                raise ValueError('Publication changed another head row')
        elif any(new.get(k, 0) < count for k, count in old.items()) or sum(new.values()) != sum(old.values()) + 1:
            raise ValueError(f'Publication lost prior rows or added unexpected rows: {table}')


class PublicationRunner:
    def __init__(self, manifest, manifest_sha, backend):
        if manifest.get('mode') != 'reviewed_publication_v1':
            raise ValueError('Explicit publication manifest required')
        self.manifest, self.sha, self.backend = manifest, manifest_sha, backend
        self.output = Path(manifest['_output'])
        if self.output.stat().st_mode & 0o077:
            raise ValueError('Publication evidence directory must be private')

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

    def packet(self):
        pin = self.manifest['items'][0].get('retained_packet')
        if pin:
            raw = read_pin(pin)
            path = Path(pin['path'])
        else:
            path = self.output / 'publication-packet.json'
            raw = path.read_bytes()
        if path.stat().st_mode & 0o077:
            raise ValueError('Signed publication packet must be private')
        return json.loads(raw), digest(raw)

    def prepare(self):
        if self.manifest['items'][0].get('retained_packet'):
            raise ValueError('Retained publication is inspect-only')
        with self.locked(), self.backend.lease():
            self.backend.prepare_preflight()  # signing configuration before any route
            before = self.backend.snapshot()
            self.record('publication-prepare-intent.json', {'manifest_sha256': self.sha})
            try:
                response = self.backend.prepare()
                self.record('publication-prepare-http.json', response)
            except Exception:
                self.record('publication-prepare-error.json', {'error': self.backend.redact(traceback.format_exc())})
                raise
            finally:
                after = self.backend.snapshot()
                self.record('publication-prepare-window.json', {'before': before, 'after': after})
                if before != after:
                    raise ValueError('Read-only preparation changed database state')
            if response['status'] != 200:
                raise ValueError('Owning preparation refused; inspect retained HTTP without replay')
            packet = json.loads(base64.b64decode(response['body_base64']))
            if packet.get('status') == 'held':
                result = {'state': 'held', 'publication': 'not_performed', 'manifest_sha256': self.sha}
                self.record('publication-preparation.json', result)
                return result
            self.backend.check_packet(packet)
            sha = self.record('publication-packet.json', packet)
            result = {'packet_sha256': sha, 'state': 'prepared', 'publication': 'not_performed',
                      'manifest_sha256': self.sha}
            self.record('publication-preparation.json', result)
            return result

    def qualify(self):
        if self.manifest['items'][0].get('retained_packet'):
            raise ValueError('Retained publication is inspect-only')
        with self.locked(), self.backend.lease():
            if (self.output / 'publication-execution.json').exists():
                raise ValueError('Already dispatched; inspect without replay')
            packet, sha = self.packet()
            if self.manifest['publication'].get('reviewed_packet_sha256') != sha:
                raise ValueError('Exact independently reviewed packet SHA required')
            before = self.backend.snapshot()
            prepared = self.backend.preflight(packet)
            if before != self.backend.snapshot():
                raise ValueError('State changed during publication qualification')
            qsha = self.record('publication-qualification.json', {
                'manifest_sha256': self.sha, 'packet_sha256': sha,
                'snapshot': before, 'prepared': prepared})
            return {'qualification_sha256': qsha, 'packet_sha256': sha}

    def qualification(self, expected=None):
        raw = (self.output / 'publication-qualification.json').read_bytes()
        if expected is not None and digest(raw) != expected:
            raise ValueError('Publication qualification pin mismatch')
        q = json.loads(raw)
        if q['manifest_sha256'] != self.sha or q['packet_sha256'] != self.packet()[1]:
            raise ValueError('Publication manifest/packet qualification drift')
        execution = self.output / 'publication-execution.json'
        if execution.exists():
            intent = json.loads(execution.read_bytes())
            if intent.get('manifest_sha256') != self.sha or intent.get('qualification_sha256') != digest(raw):
                raise ValueError('Publication execution/qualification pins differ')
        return q

    def execute(self, qualification_sha):
        if self.manifest['items'][0].get('retained_packet'):
            raise ValueError('Retained publication is inspect-only')
        if not qualification_sha:
            raise ValueError('Publication qualification SHA required')
        with self.locked(), self.backend.lease():
            q = self.qualification(qualification_sha)
            if (self.output / 'publication-execution.json').exists():
                raise ValueError('Already dispatched; inspect without replay')
            packet, _ = self.packet()
            if self.backend.snapshot() != q['snapshot'] or self.backend.preflight(packet) != q['prepared']:
                raise ValueError('Publication qualification drift; no dispatch')
            self.record('publication-execution.json', {'manifest_sha256': self.sha,
                        'qualification_sha256': qualification_sha, 'packet_sha256': q['packet_sha256']})
            try:
                self.record('publication-http.json', self.backend.confirm(packet))
            except Exception:
                self.record('publication-dispatch-error.json', {'error': self.backend.redact(traceback.format_exc())})
            # Save the execution window independently of success classification.
            try:
                window = self.backend.window()
                self.record('publication-window.json', window)
            except Exception:
                self.record('publication-window-error.json', {'error': self.backend.redact(traceback.format_exc())})
            return self._inspect(packet, q, 'publication-outcome.json')

    def _inspect(self, packet, q, filename):
        details = {}
        try:
            before = self.backend.snapshot()
            try:
                proof = self.backend.verify(packet)
            finally:
                after = self.backend.snapshot()
                details['observation_sha256'] = self.record(filename + '.observation.json',
                                                            {'before': before, 'after': after})
            if before != after:
                raise ValueError('Database changed during read-only publication inspection')
            details['core_proof_sha256'] = self.record(filename + '.core.proof.json', proof)
            if q is not None:
                window = json.loads((self.output / 'publication-window.json').read_bytes())
                self.backend.verify_window(q, window, proof)
                proof['execution_window_verified'] = True
            else:
                proof['execution_window_verified'] = False
            details['proof_sha256'] = self.record(filename + '.proof.json', proof)
            state = 'verified' if q is not None else 'verified_core'
        except Exception:
            details['verification_error'] = self.backend.redact(traceback.format_exc())
            try:
                committed = self.backend.committed(packet)
            except Exception:
                committed = False
            state = 'committed_unverified' if committed else 'outcome_unknown'
        result = {'state': state, 'manifest_sha256': self.sha, **details,
                  'scope': 'Technical publication only; no Gold, retrieval or goal acceptance',
                  'retry': 'Never redispatch; inspect actual Core evidence read-only'}
        self.record(filename, result)
        return result

    def inspect(self):
        with self.locked(), self.backend.lease():
            packet, _ = self.packet()
            q = None if self.manifest['items'][0].get('retained_packet') else self.qualification()
            return self._inspect(packet, q, f'publication-inspection-{time.time_ns()}.json')

    def report(self):
        names = ['publication-outcome.json', *sorted(p.name for p in self.output.glob('publication-inspection-*.json')
                 if p.name.removeprefix('publication-inspection-').removesuffix('.json').isdigit())]
        records = []
        for name in names:
            path = self.output / name
            if path.exists():
                value = json.loads(path.read_bytes())
                if value['manifest_sha256'] != self.sha:
                    raise ValueError('Publication report manifest differs')
                records.append(value)
        execution = (self.output / 'publication-execution.json').exists()
        if execution:
            self.qualification()
        prepared_path = self.output / 'publication-preparation.json'
        preparation = json.loads(prepared_path.read_bytes()) if prepared_path.exists() else None
        return {'state': records[-1]['state'] if records else ('outcome_unknown' if execution else
                preparation['state'] if preparation else 'not_dispatched'),
                'preparation': preparation,
                'latest_assessment': records[-1] if records else None,
                'original_outcome': (json.loads((self.output / 'publication-outcome.json').read_bytes())
                                     if (self.output / 'publication-outcome.json').exists() else None),
                'scope': 'Technical publication only; retained inspection does not establish historic DB window'}


class PublicationBackend:
    def __init__(self, manifest):
        from .buddy import Buddy
        self.manifest, self.item = manifest, manifest['items'][0]
        self.buddy = Buddy(manifest)
        from apps.live_control_server.models.native_recap_preparation import NativeRecapPrepareRequest
        self.request = NativeRecapPrepareRequest.model_validate(json.loads(read_pin(self.item['request'])))

    def snapshot(self):
        return self.buddy.snapshot()

    def lease(self):
        return self.buddy.capture_lease()

    def redact(self, text):
        text = authority.redact(self.buddy, self.manifest['operator_token_env'], text)
        token = getattr(self, '_active_token', None)
        return text.replace(token, '[REDACTED_PACKET_TOKEN]') if isinstance(token, str) and token else text

    def _configuration(self):
        from apps.live_control_server.services.graph_object_authoring_prepare import _prepare_binding_key
        key = _prepare_binding_key()
        token = os.environ.get(self.manifest['operator_token_env'], '')
        if (os.environ.get('DMB_AGENT_GRAPH_AUTH_MODE') != 'local_operator'
                or self.manifest['publication']['principal'] != 'local_operator'
                or os.environ.get('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT') not in {'local', 'development', 'dev'}
                or not token):
            raise ValueError('Explicit isolated local operator required')
        return digest(encoded({'signing_key': digest(key), 'operator_token': digest(token.encode()),
                               'auth_environment': os.environ['DMB_AGENT_GRAPH_AUTH_ENVIRONMENT']}))

    def _data(self):
        from apps.live_control_server import config
        from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
        data = load_reviewable_extraction_data(config.artifact_data_root(), self.request.run_id)
        if (self.request.managed_world_id != self.manifest['world_id']
                or self.request.run_id != self.item['retained_run_id']
                or data.run.revision != self.request.expected_run_revision
                or data.run.revision != self.item['expected_run_revision']
                or data.run.campaign_id != self.item['campaign_id']
                or data.run.session_id != self.item['session_id']
                or data.source_artifact.source_artifact_id != self.item['source_artifact_id']
                or digest(data.source_bytes) != self.item['effective_sha256']
                or digest(data.candidate_bytes) != self.request.candidate_sha256):
            raise ValueError('Exact publication run/source/candidate binding changed')
        return data

    def prepare_preflight(self):
        self._configuration()
        data = self._data()
        from apps.live_control_server.services import native_recap_preparation as owner
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        from apps.live_control_server import config
        source, _ = owner._resolve_source(self.request, config.artifact_data_root(),
                                          native.binding(self.manifest['world_id']), data)
        if str(source.source_revision_id) != self.item['source_revision_id']:
            raise ValueError('Exact APP source revision changed')
        _, context, _, _ = authority.read_core(self.buddy, self.manifest['world_id'])
        if (context != self.manifest['native_context']
                or context['revision_id'] != self.request.expected_parent_revision_id
                or context['source_epoch'] != self.request.expected_source_authority_epoch):
            raise ValueError('Publication preparation context drift')

    def prepare(self):
        return authority.local_route(self.buddy, 'publication_prepare', self.request.model_dump(mode='json'),
                                     self.manifest['operator_token_env'])

    def check_packet(self, packet):
        self._active_token = packet.get('token')
        self._configuration()
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
        from apps.live_control_server.services.graph_object_authoring_prepare import decode_publication_intent
        from apps.live_control_server.models.native_recap_preparation import NativeRecapConfirmRequest
        from apps.live_control_server.services import native_recap_preparation as owner
        from graph_memory.candidate_document_integrity import classify_candidate_document_integrity
        from apps.live_control_server import config
        confirm = NativeRecapConfirmRequest.model_validate({k: packet[k] for k in ('envelope', 'prepared', 'token')})
        env = confirm.envelope
        if (decode_publication_intent(confirm.token, allow_expired_recovery=True) != env.model_dump(mode='json')
                or env.review.model_dump(mode='json') != self.request.model_dump(mode='json')
                or env.principal != self.manifest['publication']['principal']
                or env.producer != owner.PRODUCER or env.purpose != 'dmb_native_recap_confirm_v1'
                or env.binding != native.binding(self.manifest['world_id'])
                or env.prepared_digest != transport.digest(packet['prepared'])):
            raise ValueError('Publication signed packet/request/binding differs')
        prepared = transport.decode_prepared(packet['prepared'])
        if (prepared.prepared_change_id != env.prepared_change_id
                or prepared.dungeonmind_publication_id != env.prepared_change_id
                or prepared.space_id != env.binding['native_world_id']
                or prepared.producer != env.producer
                or prepared.expected_parent_revision_id != self.request.expected_parent_revision_id
                or env.parent_context['source_epoch'] != self.request.expected_source_authority_epoch
                or env.expires_at != prepared.prepared_at + owner.PREPARE_TTL):
            raise ValueError('Publication prepared identity/expiry differs')
        transport.verify_prepared_parent(prepared, env.parent_context)
        data = self._data()
        repo = native.read_repository()
        _, access, _, _ = native.read_context(repo, prepared.space_id, prepared.expected_parent_revision_id,
                                            self.request.campaign_id)
        source, admitted = owner._resolve_source(self.request, config.artifact_data_root(), env.binding, data)
        if str(source.source_revision_id) != self.item['source_revision_id']:
            raise ValueError('Exact APP source revision changed')
        classified = classify_candidate_document_integrity(json.loads(data.candidate_bytes))
        if classified.is_document_integrity_failure:
            raise ValueError('Candidate document integrity failed')
        intent, inventory = owner._intent(classified.preview, self.request.selections, prepared.space_id,
            self.request.campaign_id, admitted, data, access, candidate_sha256=self.request.candidate_sha256,
            producer=owner.PRODUCER)
        if prepared.prepared_operations != intent.operations or packet['records'] != inventory:
            raise ValueError('Owning compiler differs from signed publication')
        return prepared, env, source

    def preflight(self, packet):
        prepared, env, _ = self.check_packet(packet)
        repo, context, _, _ = authority.read_core(self.buddy, self.manifest['world_id'])
        if context != env.parent_context or env.expires_at < datetime.now(timezone.utc):
            raise ValueError('Publication parent/epoch drift or expiry')
        if repo.get_publication_receipt(prepared.space_id, prepared.dungeonmind_publication_id):
            raise ValueError('Publication receipt exists; inspect without redispatch')
        mutable = authority.mutable_rows(self.buddy, prepared.space_id)
        if (mutable[authority.HEAD]['data']['head_revision_id'] != context['revision_id']
                or mutable[authority.AUTHORITY]['data']['epoch'] != context['source_epoch']):
            raise ValueError('Publication mutable authority differs from Core context')
        if not OWNED <= self.snapshot()['native'].keys():
            raise ValueError('Required publication tables missing')
        return {'context': context, 'mutable': mutable, 'configuration_fingerprint': self._configuration()}

    def confirm(self, packet):
        return authority.local_route(self.buddy, 'publication_confirm',
            {k: packet[k] for k in ('envelope', 'prepared', 'token')}, self.manifest['operator_token_env'])

    def window(self):
        _, context, _, _ = authority.read_core(self.buddy, self.manifest['world_id'])
        mutable = authority.mutable_rows(self.buddy, context['space_id'])
        return {'snapshot': self.snapshot(), 'mutable': mutable, 'context': context}

    def committed(self, packet):
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        env = packet['envelope']
        return native.read_repository().get_publication_receipt(env['binding']['native_world_id'],
                                                               env['prepared_change_id']) is not None

    def verify_window(self, q, window, proof):
        before, after = q['prepared']['mutable'], window['mutable']
        if (window['context']['revision_id'] != proof['receipt']['published_revision_id']
                or window['context']['source_epoch'] != q['prepared']['context']['source_epoch']
                or before[authority.AUTHORITY] != after[authority.AUTHORITY]
                or after[authority.HEAD]['data'] != {**before[authority.HEAD]['data'],
                    'head_revision_id': proof['receipt']['published_revision_id'],
                    'updated_at': after[authority.HEAD]['data']['updated_at']}):
            raise ValueError('Publication execution window context/epoch/head differs')
        conserve_publication(q['snapshot'], window['snapshot'], before[authority.HEAD], after[authority.HEAD])

    def verify(self, packet):
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        from worldkeeper.integrations.dungeonmind.vnext_prepare import compile_prepared_change_to_dungeonmind
        from dungeonmind.application.vnext import open_admitted_native_text
        from dungeonmind.application.vnext.prospective import resolve_prospective_contribution
        from fastapi.encoders import jsonable_encoder
        prepared, env, source = self.check_packet(packet)
        repo, current, _, _ = authority.read_core(self.buddy, self.manifest['world_id'])
        publication = repo.get_prospective_publication(prepared.space_id, prepared.dungeonmind_publication_id)
        if publication is None:
            raise ValueError('Actual publication result missing')
        receipt, result = publication.publication_receipt, publication.prospective_result
        if (receipt.space_id != prepared.space_id or result.space_id != prepared.space_id
                or result.status != 'published' or receipt.publication_id != prepared.dungeonmind_publication_id
                or receipt.expected_parent_revision_id != prepared.expected_parent_revision_id
                or receipt.status != 'published' or receipt.published_revision_id != result.published_revision_id
                or result.publication_id != receipt.publication_id
                or repo.get_publication_receipt(prepared.space_id, receipt.publication_id) != receipt):
            raise ValueError('Actual publication receipt/result differs')
        _, child, _, _ = native.read_context(repo, prepared.space_id, receipt.published_revision_id,
                                           self.request.campaign_id)
        _, parent, _, _ = native.read_context(repo, prepared.space_id, prepared.expected_parent_revision_id,
                                            self.request.campaign_id)
        if (child.parsed.graph_payload_sha256 != receipt.graph_payload_sha256
                or child.parsed.domain_contract_ref != parent.parsed.domain_contract_ref
                or child.parsed.semantic_profile_ref != parent.parsed.semantic_profile_ref):
            raise ValueError('Actual receipted child hash differs')
        bindings = {r.client_op_id: r for r in result.results}
        if len(bindings) != len(result.results):
            raise ValueError('Duplicate publication result binding')
        compiled = compile_prepared_change_to_dungeonmind(prepared)
        items = {item.client_op_id: item for item in compiled.prospective_contribution.items}
        if items.keys() != bindings.keys():
            raise ValueError('Publication result operation inventory differs')
        if any(bindings[key].result_kind != ('assertion' if hasattr(item, 'metadata') else 'entity')
               for key, item in items.items()):
            raise ValueError('Publication result kind differs from compiled operation')
        resolved = resolve_prospective_contribution(
            prospective_contribution=compiled.prospective_contribution, dispositions=compiled.dispositions,
            publication_id=compiled.publication_id, publication=compiled.publication, parent=parent.parsed)
        if (tuple(result.results) != resolved.committed_result_bindings
                or result.prospective_request_sha256 != resolved.prospective_request_sha256):
            raise ValueError('Core prospective request/result differs from owning resolution')
        entities = {k: r.durable_id for k, r in bindings.items() if r.result_kind == 'entity'}
        assertions = {k: r.durable_id for k, r in bindings.items() if r.result_kind == 'assertion'}
        if (len(entities) + len(assertions) != len(bindings)
                or len(set(entities.values())) != len(entities) or len(set(assertions.values())) != len(assertions)):
            raise ValueError('Publication results collapse distinct operations')
        def resolve(endpoint):
            if endpoint['kind'] == 'durable_entity':
                return endpoint['entity_id']
            if endpoint['kind'] == 'result_of':
                return entities[endpoint['client_op_id']]
            raise ValueError('Unsupported compiled endpoint')
        def metadata(value):
            value = dict(value)
            refs = value['evidence_ref_ids']
            if len(set(refs)) != len(refs):
                raise ValueError('Duplicate evidence reference')
            value['evidence_ref_ids'] = sorted(refs)
            return value
        actual = {k: native.assertion_contract(v).model_dump(mode='json')
                  for k, v in child.parsed.assertions_by_id.items()}
        old = {k: native.assertion_contract(v).model_dump(mode='json')
               for k, v in parent.parsed.assertions_by_id.items()}
        for key, aid in assertions.items():
            item = items[key]
            if not hasattr(item, 'metadata'):
                raise ValueError('Wrong publication result kind')
            wire = item.model_dump(mode='json')
            value = wire['value']
            if value['kind'] == 'entity_ref':
                value = {'kind': 'entity_ref', 'entity_id': resolve(value['entity'])}
            row = actual[aid]
            if (row['subject_entity_id'] != resolve(wire['subject']) or row['predicate'] != wire['predicate']
                    or row['value'] != value or metadata(row['metadata']) != metadata(wire['metadata'])):
                raise ValueError('Published assertion value/metadata/endpoint differs')
        if (set(actual) - set(old) != set(assertions.values())
                or any(actual.get(k) != v for k, v in old.items())
                or set(child.parsed.entities_by_id) - set(parent.parsed.entities_by_id) != set(entities.values())
                or any(child.parsed.entities_by_id.get(k) != v for k, v in parent.parsed.entities_by_id.items())
                or child.parsed.evidence_by_id != parent.parsed.evidence_by_id):
            raise ValueError('Prior graph payload changed or unexpected payload added')
        for eid in entities.values():
            if jsonable_encoder(child.parsed.entities_by_id[eid]) != {'entity_id': eid}:
                raise ValueError('New entity payload differs')
        expected_refs = {eid for key in assertions for eid in items[key].metadata.evidence_ref_ids}
        if (expected_refs != {w.evidence_ref_id for w in prepared.evidence_witnesses}
                or len(expected_refs) != len(prepared.evidence_witnesses)):
            raise ValueError('Publication evidence witness inventory differs')
        openings = []
        for witness in prepared.evidence_witnesses:
            opening = open_admitted_native_text(child, witness.evidence_ref_id)
            evidence = child.parsed.get_evidence(witness.evidence_ref_id)
            if (opening.status != 'available' or evidence.evidence_role != 'support' or witness.evidence_role != 'support'
                    or opening.body_sha256 != source.content_sha256 or opening.body_text.encode() != source.markdown.encode()
                    or opening.source_artifact_id != witness.source_artifact_id
                    or opening.source_revision_id != witness.source_revision_id
                    or evidence.source_span_ref_id != witness.source_span_ref_id):
                raise ValueError('Publication SUPPORT opening differs')
            row = jsonable_encoder(opening)
            row.pop('body_text', None)
            openings.append(row)
        return {'run_id': self.request.run_id, 'run_revision': self.request.expected_run_revision,
                'receipt': receipt.model_dump(mode='json'), 'result': result.model_dump(mode='json'),
                'current_context': current, 'new_objects': len(entities), 'new_assertions': len(assertions),
                'support_openings': openings, 'prior_graph_payloads_preserved': True,
                'scope': 'Exact technical claim publication; independent source/Gold judgment remains separate'}
