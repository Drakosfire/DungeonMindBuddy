"""Small shared observation and fixed owning-route helpers; no lifecycle or producer."""
import base64
import os
import traceback
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit
from .runner import digest, encoded

HEAD = 'dungeonmind.knowledge_heads'
AUTHORITY = 'dungeonmind.knowledge_native_source_authority'

def redact(buddy, token_env, value):
    secrets = [*buddy.dsns.values(), os.environ.get(token_env, ''),
               os.environ.get('DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY', '')]
    try:
        secrets.append(native_write_dsn(buddy))
    except (KeyError, ValueError):
        pass  # Preserve the original failure; raw configured DSNs are still redacted.
    secrets.extend(os.environ.get(spec['product_env'], '') for spec in buddy.db.values())
    for dsn in buddy.dsns.values():
        try:
            password = urlsplit(dsn).password
        except ValueError:
            continue
        if password:
            secrets.extend([password, unquote(password)])
    for secret in secrets:
        if secret:
            value = value.replace(secret, '[REDACTED]')
    return value

def native_write_dsn(buddy):
    parsed = urlsplit(buddy._dsn('native'))
    query = dict(parse_qsl(parsed.query))
    query['options'] = '-c default_transaction_read_only=off'
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query, quote_via=quote), parsed.fragment))

def read_core(buddy, world):
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from fastapi.encoders import jsonable_encoder
    repo = native.read_repository()
    bound = native.binding(world)
    context, access = native.access_context(repo, bound['native_world_id'])
    entities = digest(encoded(jsonable_encoder(access.parsed.entities_by_id)))
    assertions = digest(encoded({k: native.assertion_contract(v).model_dump(mode='json') for k, v in access.parsed.assertions_by_id.items()}))
    evidence = {k: digest(encoded(jsonable_encoder(v))) for k, v in access.parsed.evidence_by_id.items()}
    return (repo, context, access, {'entities': entities, 'assertions': assertions, 'evidence': evidence})

def mutable_rows(buddy, space):
    from psycopg import sql
    result = {}
    with buddy.connection('native') as conn:
        for table, field, value in ((HEAD, 'space_id', space), (AUTHORITY, 'singleton_id', 1)):
            schema, name = table.split('.')
            query = sql.SQL('SELECT md5(row_to_json(t)::text), row_to_json(t) FROM {} t WHERE {}=%s').format(sql.Identifier(schema, name), sql.Identifier(field))
            rows = conn.execute(query, (value,)).fetchall()
            if len(rows) != 1:
                raise ValueError('Established source authority row required')
            expected = {'space_id', 'head_revision_id', 'updated_at', 'schema_version'} if table == HEAD else {'singleton_id', 'epoch'}
            if set(rows[0][1]) != expected:
                raise ValueError('Unsupported mutable source-head schema; no dispatch')
            result[table] = {'hash': rows[0][0], 'data': rows[0][1]}
    return result

def local_route(buddy, operation, request, operator_token_env, *, run_id=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import httpx
    if operation == 'admit_context':
        from apps.live_control_server.routes.recap_ingest import router
        route = '/api/live/recap-ingest'
    elif operation == 'extend_support':
        from apps.live_control_server.routes.source_statements import router
        route = '/api/live/source-statements/extend-evidence'
    elif operation in ('publication_prepare', 'publication_confirm'):
        from apps.live_control_server.routes.extract_promote import router
        route = '/api/live/extract-promote/native-' + ('prepare' if operation == 'publication_prepare' else 'confirm')
    elif operation in ('correct_types', 'semantic_disposition'):
        from uuid import UUID
        if not isinstance(run_id, str) or str(UUID(run_id)) != run_id:
            raise ValueError('Correction route requires a canonical run UUID')
        from apps.live_control_server.routes.extract_promote import router
        suffix = 'recap-candidate-corrections' if operation == 'correct_types' else 'semantic-disposition'
        route = f'/api/live/extract-promote/runs/{run_id}/{suffix}'
    else:
        raise ValueError('Unsupported owning route')
    app = FastAPI()
    app.include_router(router)
    failures = []

    async def observed(scope, receive, send):
        try:
            await app(scope, receive, send)
        except Exception:
            failures.append(redact(buddy, operator_token_env, traceback.format_exc()))
            raise

    def forbidden(*args, **kwargs):
        raise AssertionError('External HTTP is forbidden for source authority evaluation')
    old_sync, old_async = (httpx.HTTPTransport.handle_request, httpx.AsyncHTTPTransport.handle_async_request)
    try:
        httpx.HTTPTransport.handle_request = forbidden
        httpx.AsyncHTTPTransport.handle_async_request = forbidden
        app_write = operation in ('admit_context', 'correct_types', 'semantic_disposition')
        buddy._bind(read_only=not app_write)
        native_target = (buddy._dsn('native') if operation in ('publication_prepare', 'correct_types', 'semantic_disposition')
                         else native_write_dsn(buddy))
        os.environ[buddy.db['native']['product_env']] = native_target
        token = os.environ[operator_token_env]
        with TestClient(observed, client=('127.0.0.1', 43010), headers={'Authorization': 'Bearer ' + token}, raise_server_exceptions=False) as client:
            if (os.environ.get('DMB_AGENT_GRAPH_LOCAL_PROFILE', '').strip()
                    or os.environ.get('DMB_AGENT_GRAPH_SESSION_STORE') != buddy.auth_path
                    or os.environ[buddy.db['native']['product_env']] != native_target
                    or os.environ[buddy.db['app']['product_env']] != buddy._dsn('app', write=app_write)):
                raise ValueError('Source route startup changed isolation')
            response = client.post(route, json=request)
            return {'status': response.status_code, 'body_base64': base64.b64encode(response.content).decode(), 'body_sha256': digest(response.content), 'asgi_errors': failures}
    finally:
        try:
            buddy._bind(read_only=True)
        finally:
            httpx.HTTPTransport.handle_request, httpx.AsyncHTTPTransport.handle_async_request = (old_sync, old_async)
