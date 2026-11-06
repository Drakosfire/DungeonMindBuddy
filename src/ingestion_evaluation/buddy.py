"""Ordinary Buddy route adapter. No provider producer or semantic scoring lives here."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.metadata
import base64
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from .runner import conserve, digest, encoded, read_pin, retain_bytes, seal


class Buddy:
    def __init__(self, manifest):
        self.manifest = manifest
        root = Path(manifest['_runtime_root'])
        if os.environ.get('DMB_AGENT_GRAPH_LOCAL_PROFILE', '').strip() or manifest['environment'].get('DMB_AGENT_GRAPH_LOCAL_PROFILE', '').strip():
            raise ValueError('Implicit local profile is prohibited')
        for path in (root / '.env', root / '.env.development', root.parent / '.env.development'):
            if path.exists():
                raise ValueError('Implicit runtime environment file would defeat isolation')
        sys.path[:0] = [str(root), str(root / 'src')]
        os.chdir(root)
        if manifest.get('isolation') != 'isolated' or set(manifest['databases']) != {'app', 'native'}:
            raise ValueError('Explicit isolated APP/native database identities required')
        for name, pin in manifest['dependencies'].items():
            actual = json.loads(importlib.metadata.distribution(name).read_text('direct_url.json'))
            if actual['vcs_info']['commit_id'] != pin:
                raise ValueError('Installed dependency pin mismatch')
        self.db = manifest['databases']
        expected_envs = {'app': 'DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL',
                         'native': 'DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL'}
        if any(spec['product_env'] != expected_envs[role] for role, spec in self.db.items()):
            raise ValueError('Database binding must use the owning product environment')
        allowed_appends = {'source.artifact', 'source.revision', 'ingest.run', 'ingest.component_payload'}
        if not set(manifest['app_append_tables']) <= allowed_appends:
            raise ValueError('Append scope exceeds ordinary source/ingest owners')
        if self.db['app']['database'] == self.db['native']['database']:
            raise ValueError('APP and native must be distinct isolated databases')
        # Each destination is allowlisted by identity before any product import.
        self.dsns = {role: os.environ[spec['dsn_env']] for role, spec in self.db.items()}
        self._bind(read_only=True)
        for key, value in manifest['environment'].items():
            if key in {s['product_env'] for s in self.db.values()} or any(t in key for t in ('KEY', 'TOKEN', 'PASSWORD', 'DATABASE_URL')):
                raise ValueError('Secrets/database overrides must not be manifest values')
            os.environ[key] = value
        os.environ['DMB_AGENT_GRAPH_SESSION_STORE'] = str(Path(manifest['_output']) / 'auth.json')
        self.auth_path = os.environ['DMB_AGENT_GRAPH_SESSION_STORE']
        self.snapshot()  # verifies destinations before product imports or application startup
        from application_state.cli import assert_at_head
        assert_at_head()

    def _dsn(self, role, *, write=False):
        parsed = urlsplit(self.dsns[role])
        spec = self.db[role]
        if (parsed.hostname, parsed.port, parsed.path) != (spec['host'], spec['port'], '/' + spec['database']):
            raise ValueError('Database address pin mismatch')
        if write and role != 'app':
            raise ValueError('Native writes are prohibited')
        query = dict(parse_qsl(parsed.query))
        query['options'] = '-c default_transaction_read_only=' + ('off' if write else 'on')
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query, quote_via=quote), parsed.fragment))

    def _bind(self, *, read_only):
        for role, spec in self.db.items():
            os.environ[spec['product_env']] = self._dsn(role, write=(role == 'app' and not read_only))

    @contextmanager
    def connection(self, role):
        import psycopg
        with psycopg.connect(self._dsn(role)) as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            spec = self.db[role]
            if conn.execute('SHOW transaction_read_only').fetchone() != ('on',):
                raise ValueError('Evaluator observation must be read-only')
            actual = conn.execute('SELECT current_database(), (SELECT oid FROM pg_database WHERE datname=current_database()), system_identifier::text FROM pg_control_system()').fetchone()
            if actual != (spec['database'], spec['oid'], spec['cluster']):
                raise ValueError('Database identity pin mismatch')
            yield conn

    def snapshot(self):
        from psycopg import sql
        result = {}
        for role in self.db:
            with self.connection(role) as conn:
                tables = {}
                for schema, table in conn.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"):
                    query = sql.SQL('SELECT md5(row_to_json(t)::text),count(*) FROM {} t GROUP BY 1 ORDER BY 1').format(sql.Identifier(schema, table))
                    tables[schema + '.' + table] = [list(row) for row in conn.execute(query)]
                result[role] = tables
        return result

    def check_conservation(self, before):
        after = self.snapshot()
        if before['native'] != after['native']:
            raise ValueError('Native graph/database changed')
        conserve(before['app'], after['app'], set(self.manifest['app_append_tables']))

    @contextmanager
    def capture_lease(self):
        import psycopg
        # Session lock coordinates all standardized cohorts sharing this evaluator,
        # independently of their output directories; it changes no database rows.
        with psycopg.connect(self._dsn('app'), autocommit=True) as conn:
            locked = conn.execute("SELECT pg_try_advisory_lock(hashtextextended('dmb:ingestion-evaluation',0))").fetchone()[0]
            if not locked:
                raise ValueError('Another evaluator capture owns the database lease')
            try:
                self._assert_no_active_transactions()
                yield
            finally:
                conn.execute("SELECT pg_advisory_unlock(hashtextextended('dmb:ingestion-evaluation',0))")

    def _assert_no_active_transactions(self):
        with self.connection('app') as conn:
            active = conn.execute("SELECT pid FROM pg_stat_activity WHERE datname IN (%s,%s) AND pid<>pg_backend_pid() AND (state<>'idle' OR xact_start IS NOT NULL)",
                                  (self.db['app']['database'], self.db['native']['database'])).fetchall()
            if active:
                raise ValueError('Concurrent evaluator transaction detected before dispatch')

    def _runs(self, item):
        from application_state.ingest import service
        return service.list_extraction_runs(world_id=self.manifest['world_id'], source_domain='recap', campaign_id=item['campaign_id'], session_id=item['session_id'])

    def qualify(self, item):
        from application_state.source import service as sources
        from apps.live_control_server.services.recap_ingest_context import resolve_recap_source_scope
        from apps.live_control_server.services.recap_name_review import prepare_name_review
        from apps.live_control_server.services.source_artifact_registry import _normalize_source_text
        from src.graph_memory.extraction.name_review import apply_review
        from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
        from src.graph_memory.extraction.bounded_recap_execution import DEEPSEEK_MODEL
        from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
        from graph_memory.evidence.source_artifact import build_world_scoped_recap_source_artifact_id
        context, _ = native.access_context(native.read_repository(), self.manifest['world_id'])
        if json.loads(encoded(context)) != self.manifest['native_context']:
            raise ValueError('Native revision context drift')
        if (RECAP_EXTRACTION_PROFILE.qualified_id, DEEPSEEK_MODEL) != (self.manifest['profile_id'], self.manifest['model_id']):
            raise ValueError('Effective model/profile drift')
        request = json.loads(read_pin(item['request']))
        raw = read_pin(item['source']).decode()
        if request['raw_text'] != raw or request['managed_world_id'] != self.manifest['world_id'] or request['campaign_id'] != item['campaign_id'] or 'session-' + str(request['session']) != item['session_id']:
            raise ValueError('Ordinary request/source scope mismatch')
        if request.get('session_evidence') or not request.get('force_graph_run') or not request.get('include_graph_extraction') or request.get('operation') != 'generate_recap_memory':
            raise ValueError('This evaluator requires an ordinary fresh source-only recap request')
        source = sources.get_source_markdown(source_artifact_id=item['source_artifact_id'], source_revision_id=item['source_revision_id'], content_sha256=item['source']['sha256'], world_id=self.manifest['world_id'])
        if source.markdown != raw or (source.campaign_id, source.session_id) != (item['campaign_id'], item['session_id']):
            raise ValueError('Retained source revision differs')
        scope = resolve_recap_source_scope(managed_world_id=self.manifest['world_id'], campaign_id=item['campaign_id'])
        original, _catalog, review = prepare_name_review(raw, scope, session_id=item['session_id'])
        corrected, lineage = apply_review(original, review, request['name_review'])
        if digest(_normalize_source_text(corrected).encode()) != item['effective_sha256']:
            raise ValueError('Reviewed effective source pin differs')
        prior = {r.run_id: r.model_dump(mode='json') for r in self._runs(item)}
        effective_artifact = build_world_scoped_recap_source_artifact_id(world_id=self.manifest['world_id'], campaign_id=item['campaign_id'], session_id=item['session_id'], content_sha256=item['effective_sha256'])
        unresolved = [rid for rid, run in prior.items() if run['status'] in {'prepared', 'running'} and run['source_artifact_id'] == effective_artifact]
        return {'id': item['id'], 'prior_runs': prior, 'unresolved_prior_runs': unresolved,
                'name_review': lineage, 'source_sha256': item['source']['sha256'],
                'effective_sha256': item['effective_sha256'], 'request_sha256': item['request']['sha256'],
                'pass_instruction_sha256': {p.pass_id: digest(p.instruction.encode()) for p in
                    [*RECAP_EXTRACTION_PROFILE.node_passes, RECAP_EXTRACTION_PROFILE.beat_pass, RECAP_EXTRACTION_PROFILE.edge_pass] if p}}

    def capture(self, item, qualified, prefix):
        from fastapi.testclient import TestClient
        from apps.live_control_server.main import create_app
        from application_state.ingest.components import get_component_bytes
        request = json.loads(read_pin(item['request']))
        # Credentials are environment-only. No model-specific retry or call cap here.
        token = os.environ[self.manifest['operator_token_env']]
        before = self.snapshot()
        error = None
        response = None
        try:
            self._assert_no_active_transactions()
            app = create_app()
            failures = []

            async def observed(scope, receive, send):
                try:
                    await app(scope, receive, send)
                except Exception:
                    import traceback
                    failures.append(traceback.format_exc())
                    raise

            self._bind(read_only=False)
            with TestClient(observed, client=('127.0.0.1', 43001), headers={'Authorization': 'Bearer ' + token}, raise_server_exceptions=False) as client:
                if os.environ.get('DMB_AGENT_GRAPH_LOCAL_PROFILE', '').strip() or os.environ.get('DMB_AGENT_GRAPH_SESSION_STORE') != self.auth_path:
                    raise ValueError('Product startup changed profile/auth isolation')
                for role, spec in self.db.items():
                    if os.environ.get(spec['product_env']) != self._dsn(role, write=(role == 'app')):
                        raise ValueError('Product startup changed database isolation')
                response = client.post('/api/live/recap-ingest', json=request)
                # Preserve response before parsing, including non-JSON/error responses.
                seal(prefix.with_suffix('.http.json'), {'status': response.status_code,
                     'body_base64': base64.b64encode(response.content).decode(), 'body_sha256': digest(response.content)})
            if failures:
                error = '\n'.join(failures)
                for secret in [token, *self.dsns.values(), *[os.environ.get(name, '') for name in self.manifest.get('provider_credential_envs', [])]]:
                    if secret:
                        error = error.replace(secret, '[REDACTED]')
                seal(prefix.with_suffix('.asgi-errors.json'), {'tracebacks': error})
        except Exception as exc:
            # Exception strings may contain DSNs/headers. Retain a scrubbed traceback.
            import traceback
            error = traceback.format_exc()
            for secret in [token, *self.dsns.values(), *[os.environ.get(name, '') for name in self.manifest.get('provider_credential_envs', [])]]:
                if secret:
                    error = error.replace(secret, '[REDACTED]')
            seal(prefix.with_suffix('.error.json'), {'type': type(exc).__name__, 'traceback': error})
        finally:
            self._bind(read_only=True)
        self.check_conservation(before)
        runs = self._runs(item)
        old = qualified['prior_runs']
        current = {r.run_id: r.model_dump(mode='json') for r in runs}
        if {key: current.get(key) for key in old} != old:
            raise ValueError('Prior run contracts changed')
        fresh = [r for r in runs if r.run_id not in old]
        if len(fresh) != 1:
            return {'state': 'unknown', 'new_run_ids': [r.run_id for r in fresh], 'transport_error': bool(error)}
        run = fresh[0]
        components = {}
        for kind, ref in run.components.items():
            kind = str(getattr(kind, 'value', kind))
            if kind == 'source_artifact' or not ref or not ref.exists:
                continue
            body = get_component_bytes(run_id=run.run_id, kind=kind, content_sha256=ref.sha256)
            if digest(body) != ref.sha256:
                raise ValueError('Retained component hash mismatch')
            path = prefix.parent / (prefix.name + '.' + kind + '.json')
            # Export exact DB bytes, not a reserialized approximation.
            retain_bytes(path, body)
            components[kind] = {'path': str(path), 'sha256': ref.sha256}
        state = str(run.status) if not error and response is not None and response.status_code < 400 else 'transport_unproven'
        return {'state': state, 'run': run.model_dump(mode='json'), 'components': components,
                'transport_error': bool(error)}

    def observe(self, item):
        # Read actual product status; never reconciliation, provider dispatch or guessed liveness.
        return [r.model_dump(mode='json') for r in self._runs(item)]

    def audit(self, item, qualified, output):
        from application_state.ingest.components import get_component_bytes
        from apps.live_control_server.services.extraction_usage import summarize
        from apps.live_control_server.services.source_artifact_registry import load_registered_source_artifact_bytes
        from src.graph_memory.extraction.recap_quote_integrity import validate_and_defer_nonliteral_recap_items
        runs = self._runs(item)
        current = {r.run_id: r.model_dump(mode='json') for r in runs}
        if {key: current.get(key) for key in qualified['prior_runs']} != qualified['prior_runs']:
            raise ValueError('Prior run contracts changed during audit')
        retained_id = item.get('retained_run_id')
        fresh = [r for r in runs if r.run_id == retained_id] if retained_id else [r for r in runs if r.run_id not in qualified['prior_runs']]
        if len(fresh) != 1:
            return {'failed_boundary': 'capture_attribution', 'actual_run_ids': [r.run_id for r in fresh]}
        run = fresh[0]
        expected_lineage = {**qualified['name_review'], 'original_source_artifact_id': item['source_artifact_id'],
                            'original_source_sha256': item['source']['sha256']}
        if run.lineage.get('name_review') != expected_lineage:
            raise ValueError('Actual source/name-review lineage mismatch')
        payloads, pins = {}, []
        for kind, ref in run.components.items():
            kind = str(getattr(kind, 'value', kind))
            if kind == 'source_artifact' or not ref or not ref.exists:
                continue
            body = get_component_bytes(run_id=run.run_id, kind=kind, content_sha256=ref.sha256)
            if digest(body) != ref.sha256:
                raise ValueError('Component integrity failure')
            payloads[kind] = json.loads(body)
            path = output / (item['id'] + '.audit-' + kind + '.json')
            retain_bytes(path, body)
            pins.append({'kind': kind, 'sha256': ref.sha256, 'path': str(path)})
        required = {'candidate_graph', 'source_span_index', 'raw_model_response', 'pass_telemetry', 'consolidation_diagnostics'}
        missing = sorted(required - payloads.keys())
        boundary = None if str(run.status) == 'reviewable' and not missing else 'capture'
        source, body = load_registered_source_artifact_bytes(Path(self.manifest['environment']['DMB_ARTIFACT_DATA_ROOT']), run.source_artifact_id)
        if digest(body) != item['effective_sha256']:
            raise ValueError('Actual run source lineage mismatch')
        from application_state.source import service as sources
        corrected = sources.get_source_markdown(source_artifact_id=run.source_artifact_id, content_sha256=item['effective_sha256'], world_id=self.manifest['world_id'])
        revisions = sources.get_source_revision_metadata(bindings=[(run.source_artifact_id, item['effective_sha256'])], world_id=self.manifest['world_id'])
        if corrected.markdown.encode() != body or (corrected.world_id, corrected.campaign_id, corrected.session_id) != (self.manifest['world_id'], item['campaign_id'], item['session_id']) or len(revisions) != 1 or str(corrected.source_revision_id) != str(revisions[0].source_revision_id):
            raise ValueError('Corrected APP source revision/scope mismatch')
        literal = 'unproven'
        independent = None
        if 'candidate_graph' in payloads:
            graph = payloads['candidate_graph']
            guarded, _ = validate_and_defer_nonliteral_recap_items(graph, source_text=body.decode(), source_artifact_id=run.source_artifact_id, source_sha256=item['effective_sha256'], source_span_index=payloads['source_span_index'])
            if guarded != graph:
                boundary = 'literal_evidence'
            else:
                literal = 'verified_by_owner'
            from .evidence import inspect_quotes
            independent = inspect_quotes(graph, payloads['source_span_index'], body.decode(), payloads.get('consolidation_diagnostics', {}), set(qualified['pass_instruction_sha256']))
            if independent['issues']:
                boundary = 'literal_evidence'
        accounting = None
        if 'pass_telemetry' in payloads:
            telemetry = payloads['pass_telemetry']
            if (telemetry['run_id'], telemetry['source_artifact_id'], telemetry['source_sha256']) != (run.run_id, run.source_artifact_id, item['effective_sha256']):
                raise ValueError('Usage attribution mismatch')
            if any(telemetry['limits'].get(k) != v for k, v in self.manifest['expected_limits'].items()):
                raise ValueError('Effective inference settings differ from qualification')
            usage, passes = summarize(telemetry)
            accounting = {'summary': usage.model_dump(mode='json'), 'passes': [p.model_dump(mode='json') for p in passes]}
        # Retain every private attempt using the DB records; don't infer attempts from pass count.
        with self.connection('app') as conn:
            rows = conn.execute("SELECT kind,content_sha256,payload FROM ingest.component_payload WHERE run_id=%s AND kind IN ('raw_model_response','pass_telemetry')", (run.run_id,)).fetchall()
        private = []
        events = {}
        bundle = payloads.get('raw_model_response', {}).get('execution_evidence', {})
        binding = bundle.get('binding')
        for kind, sha, payload in rows:
            raw = bytes(payload)
            if digest(raw) != sha:
                raise ValueError('Private execution record hash mismatch')
            event = json.loads(raw)
            if 'execution_binding' not in event:
                continue
            actual_binding = event['execution_binding']
            if (actual_binding.get('run_id'), actual_binding.get('source_artifact_id'), actual_binding.get('source_sha256'), actual_binding.get('profile_id'), actual_binding.get('model_id')) != (run.run_id, run.source_artifact_id, item['effective_sha256'], self.manifest['profile_id'], self.manifest['model_id']):
                raise ValueError('Private execution binding mismatch')
            if binding and actual_binding != binding:
                raise ValueError('Private execution differs from retained bundle binding')
            response = event.get('response', {})
            if response.get('text') is not None and digest(response['text'].encode()) != response['sha256']:
                raise ValueError('Raw/normalized response digest mismatch')
            events[kind, sha] = event
            path = output / (item['id'] + '.private-' + sha + '.json')
            retain_bytes(path, raw)
            private.append({'kind': kind, 'sha256': sha, 'path': str(path)})
        for record in bundle.get('records', []):
            if events.get((record['kind'], record['sha256'])) != record['envelope']:
                raise ValueError('Raw bundle differs from retained execution event')
        return {'run_id': run.run_id, 'status': str(run.status), 'failed_boundary': boundary,
                'missing_components': missing, 'components': pins, 'literal_evidence': literal,
                'independent_receipt_checks': independent,
                'accounting': accounting, 'missing_accounting_is_not_zero': True, 'private_attempts': private,
                'semantic_gold': 'unproven', 'publication': 'unproven'}
