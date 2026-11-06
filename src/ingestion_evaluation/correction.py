"""Bounded evaluation of existing Buddy correction/review APIs; no producer."""
from collections import Counter

from .governed_operation import GovernedOperationRunner


class CorrectionRunner(GovernedOperationRunner):
    mode = 'reviewed_correction_v1'
    prefix = 'correction'
    qualification_scope = 'Exact reviewed correction operation; no providers or native publication'
    outcome_scope = 'Correction/review effect only; raw quality, Gold and publication remain separate'
    report_scope = 'Retained correction evidence only; no automatic replay or semantic acceptance'


def conserve_correction_rows(before, after, operation, owned_before, owned_after):
    """Subtract only separately inspected exact child rows, never whole tables."""
    if operation not in {'correct_types', 'semantic_disposition'}:
        raise ValueError('Unsupported correction operation')
    if before.keys() != after.keys() or set(before) != {'app', 'native'}:
        raise ValueError('Correction database inventory changed')
    if before['native'] != after['native']:
        raise ValueError('Correction changed native state')
    allowed = {'ingest.run', 'ingest.component_payload'} if operation == 'correct_types' else {'ingest.run'}
    if set(owned_before) != allowed or set(owned_after) != allowed:
        raise ValueError('Correction ownership exceeds exact operation scope')
    if before['app'].keys() != after['app'].keys():
        raise ValueError('Correction APP table inventory changed')
    if operation == 'correct_types':
        if any(owned_before.values()):
            raise ValueError('Correction requires an absent prospective child')
        if sum(dict(owned_after['ingest.run']).values()) != 1 or sum(dict(owned_after['ingest.component_payload']).values()) != 2:
            raise ValueError('Correction requires one exact child and two immutable output rows')
    elif any(sum(dict(value['ingest.run']).values()) != 1 for value in (owned_before, owned_after)):
        raise ValueError('Disposition requires one exact child CAS')
    for table, old in before['app'].items():
        new = after['app'][table]
        if table not in allowed:
            if old != new:
                raise ValueError(f'Correction changed unowned table: {table}')
            continue
        old_counts, new_counts = Counter(dict(old)), Counter(dict(new))
        for counts, owned in ((old_counts, owned_before[table]), (new_counts, owned_after[table])):
            for row, count in owned:
                if count <= 0 or counts[row] < count:
                    raise ValueError('Exact owned correction row is absent or ambiguous')
                counts[row] -= count
        if +old_counts != +new_counts:
            raise ValueError(f'Correction changed another row: {table}')


class CorrectionBackend:
    def __init__(self, manifest):
        import json
        from .buddy import Buddy
        from .runner import read_pin
        self.manifest, self.item = manifest, manifest['items'][0]
        self.spec = manifest['correction']
        self.operation = self.spec['operation']
        self.buddy = Buddy(manifest)
        self.request = json.loads(read_pin(self.item['request']))

    def snapshot(self):
        return self.buddy.snapshot()

    def lease(self):
        return self.buddy.capture_lease()

    def redact(self, text):
        from . import authority
        return authority.redact(self.buddy, self.manifest['operator_token_env'], text)

    def _configuration(self):
        import os
        from .runner import digest, encoded
        token = os.environ.get(self.manifest['operator_token_env'], '')
        if (self.spec['principal'] != 'local_operator'
                or os.environ.get('DMB_AGENT_GRAPH_AUTH_MODE') != 'local_operator'
                or os.environ.get('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT') not in {'local','development','dev'}
                or not token):
            raise ValueError('Explicit isolated local operator required')
        return digest(encoded({'principal':self.spec['principal'], 'token_sha256':digest(token.encode()),
                               'environment':os.environ['DMB_AGENT_GRAPH_AUTH_ENVIRONMENT']}))

    def _data(self):
        from apps.live_control_server import config
        from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
        from .runner import digest
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        binding = native.binding(self.manifest['world_id'])
        data = load_reviewable_extraction_data(config.artifact_data_root(), self.item['retained_run_id'])
        if (data.source_artifact.world_id != binding['native_world_id']
                or data.run.revision != self.item['expected_run_revision']
                or data.run.campaign_id != self.item['campaign_id']
                or data.run.session_id != self.item['session_id']
                or data.run.profile_id != self.item['profile_id']
                or data.run.source_artifact_id != self.item['source_artifact_id']
                or digest(data.source_bytes) != self.item['effective_sha256']
                or digest(data.span_bytes) != self.item['span_index_sha256']
                or digest(data.candidate_bytes) != self.item['candidate_sha256']):
            raise ValueError('Exact correction run/source/index/profile binding changed')
        return data

    def _owned(self, child_id):
        from psycopg import sql
        tables = ['ingest.run','ingest.component_payload'] if self.operation == 'correct_types' else ['ingest.run']
        result = {}
        with self.buddy.connection('app') as conn:
            for table in tables:
                schema,name = table.split('.')
                query = sql.SQL('SELECT md5(row_to_json(t)::text),count(*) FROM {} t WHERE run_id=%s GROUP BY 1 ORDER BY 1').format(sql.Identifier(schema,name))
                result[table] = [list(row) for row in conn.execute(query,(child_id,))]
        return result

    def _run_row(self, run_id):
        with self.buddy.connection('app') as conn:
            rows = conn.execute('SELECT row_to_json(t) FROM ingest.run t WHERE run_id=%s',(run_id,)).fetchall()
        if len(rows) != 1:
            raise ValueError('Exact correction child row absent or ambiguous')
        return rows[0][0]

    def _types(self, data):
        import json
        from uuid import NAMESPACE_URL, uuid5
        from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV8
        from apps.live_control_server.services import recap_semantic_candidate_correction as owner
        request = RecapCandidateCorrectionRequestV8.model_validate(self.request)
        if (request.parent_run_id != data.run.run_id
                or request.expected_parent_revision != data.run.revision
                or request.parent_candidate_sha256 != owner._sha(data.candidate_bytes)
                or request.source_revision_sha256 != owner._sha(data.source_bytes)
                or request.span_index_sha256 != owner._sha(data.span_bytes)
                or request.profile_id != data.run.profile_id):
            raise ValueError('Type correction request pins differ')
        manifest = request.model_dump(mode='json',exclude={'schema_','parent_run_id','parent_candidate_sha256'})
        manifest['schema'] = owner.MANIFEST_SCHEMA_V8
        if not manifest['node_type_replacements'] or any(manifest[key] for key in (
                'node_description_replacements','node_label_replacements','edge_tuple_replacements',
                'edge_omissions','evidence_replacements','node_omissions')):
            raise ValueError('Evaluator permits existing V8 type-only corrections')
        manifest['node_type_replacements'].sort(key=lambda row:row['node_id'])
        candidate = owner.replay_candidate(json.loads(data.candidate_bytes),manifest,
            source_bytes=data.source_bytes,span_bytes=data.span_bytes)
        manifest_sha = owner._sha(owner._canonical_bytes(manifest))
        child_id = str(uuid5(NAMESPACE_URL,
            f'dmb:{owner.SOURCE_BINDING_DERIVATION_V11}:{data.run.run_id}:{request.parent_candidate_sha256}:{manifest_sha}'))
        legacy_id = str(uuid5(NAMESPACE_URL,
            f'dmb:{owner.DERIVATION_V8}:{data.run.run_id}:{request.parent_candidate_sha256}:{manifest_sha}'))
        if any(self._owned(legacy_id).values()):
            raise ValueError('Legacy child exists; fresh correction dispatch is forbidden')
        expected = {'run_id':child_id,'candidate_sha256':owner._sha(owner._canonical_bytes(candidate)),
                    'manifest_sha256':manifest_sha}
        if self.spec['expected_child'] != expected:
            raise ValueError('Prospective correction child pin mismatch')
        return expected

    def _decision(self, data):
        from apps.live_control_server import config
        from apps.live_control_server.models.extract_promote import RecapSemanticDecisionRequest
        from apps.live_control_server.services.graph_run_registry import get_extraction_run
        from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
        from .runner import read_pin, digest
        import json
        request = RecapSemanticDecisionRequest.model_validate(self.request)
        basis_pin = json.loads(read_pin(self.spec['child_basis']))
        from apps.live_control_server.services import recap_semantic_candidate_correction as owner
        manifest = data.run.lineage.get('semantic_candidate_manifest', {})
        if (basis_pin.get('request_version') != 8
                or basis_pin.get('derivation') != owner.SOURCE_BINDING_DERIVATION_V11
                or basis_pin.get('operation_derivation') != owner.DERIVATION_V8
                or basis_pin.get('operation_manifest_schema') != owner.MANIFEST_SCHEMA_V8
                or manifest.get('schema') != owner.MANIFEST_SCHEMA_V8
                or not manifest.get('node_type_replacements')
                or any(manifest.get(key) for key in ('node_description_replacements','node_label_replacements',
                    'edge_tuple_replacements','edge_omissions','evidence_replacements','node_omissions'))):
            raise ValueError('Disposition is limited to an actual V12-wrapped V8 type-only child')
        parent = get_extraction_run(config.artifact_data_root(),data.run.lineage['parent_run_id'])
        assessment = assess_recap_semantics(data.run,parent=parent,
            source_revision_id=digest(data.source_bytes),root=config.artifact_data_root())
        if (request.expected_revision != data.run.revision or request.candidate_sha256 != digest(data.candidate_bytes)
                or data.run.lineage.get('semantic_disposition',{}).get('state') != 'held'
                or assessment.basis != basis_pin or assessment.basis_sha256 != self.spec['basis_sha256']
                or data.run.run_id != self.spec['expected_child']['run_id']
                or request.review_decision_ref != self.spec['review_decision_ref']):
            raise ValueError('Actual child review/disposition pins differ')
        return {'run_id':data.run.run_id,'candidate_sha256':digest(data.candidate_bytes),
                'basis_sha256':assessment.basis_sha256,'decision':request.decision,
                'review_decision_ref':request.review_decision_ref}

    def preflight(self):
        from . import authority
        data = self._data()
        _,context,_,_ = authority.read_core(self.buddy,self.manifest['world_id'])
        if context != self.manifest['native_context']:
            raise ValueError('Correction native context drift')
        expected = self._types(data) if self.operation == 'correct_types' else self._decision(data)
        owned = self._owned(expected['run_id'])
        if self.operation == 'correct_types' and any(owned.values()):
            raise ValueError('Prospective child already exists; inspect without dispatch')
        return {'operation':self.operation,'configuration_sha256':self._configuration(),
                'expected':expected,'owned_before':owned,
                'child_row_before':self._run_row(expected['run_id']) if self.operation == 'semantic_disposition' else None}

    def dispatch(self):
        from . import authority
        return authority.local_route(self.buddy,self.operation,self.request,
            self.manifest['operator_token_env'],run_id=self.item['retained_run_id'])

    def verify(self, qualified, after):
        from apps.live_control_server import config
        from apps.live_control_server.services.graph_run_registry import get_extraction_run
        from apps.live_control_server.services import recap_semantic_candidate_correction as owner
        from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
        from .runner import digest
        prepared = qualified['prepared']
        expected = prepared['expected']
        child = get_extraction_run(config.artifact_data_root(),expected['run_id'])
        parent_id = self.item['retained_run_id'] if self.operation == 'correct_types' else child.lineage['parent_run_id']
        parent = get_extraction_run(config.artifact_data_root(),parent_id)
        if (child.status.value != 'reviewable'
                or child.source_artifact_id != parent.source_artifact_id
                or child.campaign_id != parent.campaign_id or child.session_id != parent.session_id
                or child.profile_id != parent.profile_id
                or not owner.verify_child_replay(child,parent,config.artifact_data_root())):
            raise ValueError('Actual child owner replay failed')
        if child.components['candidate_graph'].sha256.removeprefix('sha256:') != expected['candidate_sha256']:
            raise ValueError('Actual child candidate differs')
        if self.operation == 'correct_types':
            if (child.revision != 5
                    or child.lineage.get('derivation') != owner.SOURCE_BINDING_DERIVATION_V11
                    or child.lineage.get('operation_derivation') != owner.DERIVATION_V8
                    or child.lineage.get('manifest_sha256') != expected['manifest_sha256']
                    or child.lineage.get('semantic_disposition',{}).get('state') != 'held'):
                raise ValueError('Actual correction child lineage/state differs')
        else:
            assessment = assess_recap_semantics(child,parent=parent,
                source_revision_id=self.item['effective_sha256'],root=config.artifact_data_root())
            decision = assessment.disposition or {}
            if (assessment.basis_sha256 != expected['basis_sha256']
                    or decision.get('state') != expected['decision']
                    or decision.get('reviewer_id') != self.spec['principal']
                    or decision.get('review_decision_ref') != expected['review_decision_ref']
                    or child.revision != self.item['expected_run_revision']+1):
                raise ValueError('Actual semantic decision receipt differs')
        if self.operation == 'semantic_disposition':
            import copy
            old_row = copy.deepcopy(prepared['child_row_before'])
            new_row = copy.deepcopy(self._run_row(child.run_id))
            for key in ('revision','updated_at'):
                old_row.pop(key,None)
                new_row.pop(key,None)
            old_disposition = old_row['lineage'].pop('semantic_disposition')
            new_disposition = new_row['lineage'].pop('semantic_disposition')
            if old_row != new_row or old_disposition.get('state') != 'held':
                raise ValueError('Disposition changed fields outside exact child CAS')
            expected_receipt = {**old_disposition,'state':expected['decision'],
                'reviewer_id':self.spec['principal'],'review_decision_ref':expected['review_decision_ref'],
                'from_revision':self.item['expected_run_revision']}
            timestamp = new_disposition.pop('decided_at',None)
            if not isinstance(timestamp,str) or not timestamp or new_disposition != expected_receipt:
                raise ValueError('Disposition receipt contains unexpected changes')
        owned_after = self._owned(child.run_id)
        conserve_correction_rows(qualified['snapshot'],after,self.operation,prepared['owned_before'],owned_after)
        return {'run_id':child.run_id,'run_revision':child.revision,'candidate_sha256':expected['candidate_sha256'],
                'owned_after':owned_after,'semantic_state':child.lineage['semantic_disposition']['state'],
                'native_unchanged':True,'prior_rows_preserved':True}

    def committed(self, prepared):
        rows = self._owned(prepared['expected']['run_id'])['ingest.run']
        if self.operation == 'correct_types':
            return bool(rows)
        if not rows:
            return False
        row = self._run_row(prepared['expected']['run_id'])
        receipt = row['lineage'].get('semantic_disposition',{})
        expected = prepared['expected']
        return (row['revision'] == self.item['expected_run_revision']+1
                and receipt.get('state') == expected['decision']
                and receipt.get('basis_sha256') == expected['basis_sha256']
                and receipt.get('review_decision_ref') == expected['review_decision_ref']
                and receipt.get('reviewer_id') == self.spec['principal']
                and receipt.get('from_revision') == self.item['expected_run_revision'])
