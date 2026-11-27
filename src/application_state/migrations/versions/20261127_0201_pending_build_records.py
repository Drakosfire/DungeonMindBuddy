"""Admit pending Build storage explicitly and fence incompatible readers."""
from importlib import import_module

from alembic import op
from sqlalchemy import text

revision = '20261127_0201'
down_revision = '20261127_0200'
branch_labels = None
depends_on = None

# Keep the existing shared-native lifecycle/completion shapes. Pending context
# has its own exact receipt/policy family and grants no source authority in SQL.
_native = import_module('application_state.migrations.versions.20261101_0103_shared_native_turns')
_PENDING = """
submitted_intent_fingerprint_v2 IS NOT NULL AND submitted_intent_fingerprint_v1 IS NULL
AND surface_resolution='resolved' AND surface_id='build' AND surface_instance_id IS NOT NULL
AND play_context_receipt IS NULL
AND jsonb_typeof(graph_context_receipt)='object'
AND graph_context_receipt ?& ARRAY['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256','work_context','source_observation','conversation_observation','assembled_input']
AND graph_context_receipt - ARRAY['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256','work_context','source_observation','conversation_observation','assembled_input']='{}'::jsonb
AND graph_context_receipt->>'schema'='dmb_build_pending_context_receipt_v1'
AND graph_context_receipt->>'receipt_serializer_version'='canonical-json-utf8-v1'
AND graph_context_receipt->>'context_receipt_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt->>'provenance_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_receipt#>>'{work_context,surface_id}'='build'
AND graph_context_receipt#>>'{work_context,source_basis,world_id}'=world_id
AND graph_context_receipt#>>'{source_observation,schema}'='dmb_build_source_observation_v1'
AND graph_context_receipt#>>'{source_observation,managed_world_id}'=world_id
AND graph_context_receipt#>>'{conversation_observation,conversation_id}'=conversation_id::text
AND graph_context_receipt#>>'{assembled_input,assembler_version}'='native_build_pending_initial_v3'
AND jsonb_typeof(graph_context_execution)='object'
AND graph_context_execution ?& ARRAY['schema','context_receipt_sha256','execution_policy_sha256','policy','events']
AND graph_context_execution - ARRAY['schema','context_receipt_sha256','execution_policy_sha256','policy','events']='{}'::jsonb
AND graph_context_execution->>'schema'='dmb_build_pending_execution_v1'
AND graph_context_execution->>'context_receipt_sha256'=graph_context_receipt->>'context_receipt_sha256'
AND graph_context_execution->>'execution_policy_sha256' ~ '^[a-f0-9]{64}$'
AND graph_context_execution#>>'{policy,policy_version}'='build_pending_execution_v1'
AND graph_context_execution#>>'{policy,action,surface_id}'='build'
AND graph_context_execution#>>'{policy,action,intent,surface_id}'='build'
AND graph_context_execution#>>'{policy,action,intent,surface_instance_id}'=surface_instance_id
AND graph_context_execution#>>'{policy,action,intent,world_id}'=world_id
AND graph_context_execution#>>'{policy,action,intent,message}'=user_text
AND graph_context_execution#>>'{policy,source_observation_sha256}' ~ '^[a-f0-9]{64}$'
AND NOT (graph_context_execution->'policy' ?| ARRAY['source_authority_sha256','native_query_sha256'])
AND jsonb_typeof(graph_context_execution->'events')='array'
AND CASE WHEN status='completed' THEN
""" + _native._NATIVE.split("AND CASE WHEN status='completed' THEN\n", 1)[1]


_shape = import_module('application_state.migrations.versions.20261109_0142_native_storage_json_owner')
_ARGS = (*_shape._ARGS, ('conversation_id', 'uuid'))
_FUNCTION = 'agent.pending_build_storage_shape_once'
_CALL = _FUNCTION + '(' + ','.join(name for name, _ in _ARGS) + ')'


def upgrade():
    parameters = ','.join(name + ' ' + kind for name, kind in _ARGS)
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    conn.exec_driver_sql('CREATE FUNCTION ' + _FUNCTION + '(' + parameters + ''')
RETURNS boolean LANGUAGE plpgsql IMMUTABLE CALLED ON NULL INPUT
PARALLEL SAFE SECURITY INVOKER SET search_path=pg_catalog AS $pending_storage$
BEGIN
    IF jsonb_typeof(graph_context_receipt)='object' THEN
        graph_context_receipt := graph_context_receipt || '{}'::jsonb;
    END IF;
    IF jsonb_typeof(graph_context_execution)='object' THEN
        graph_context_execution := graph_context_execution || '{}'::jsonb;
    END IF;
    RETURN COALESCE((''' + _PENDING + '''),FALSE);
END
$pending_storage$''')
    owner = import_module(
        'application_state.migrations.versions.20261123_0196_turn_lifecycle_write_guard'
    )
    saved = owner._saved_guard(conn)
    lifecycle = 'agent_turn_lifecycle_check'
    definitions = saved['graph'] | {lifecycle: saved['lifecycle']}
    receipt = "graph_context_receipt->>'schema'='dmb_build_pending_context_receipt_v1'"
    execution = "graph_context_execution->>'schema'='dmb_build_pending_execution_v1'"
    pair = f"COALESCE(({receipt} AND {execution}), FALSE)"
    pending = {
        name: f"CASE WHEN {receipt} OR {execution} THEN ({_CALL if name == lifecycle else pair}) ELSE ({previous}) END"
        for name, previous in definitions.items()
    }
    conn.exec_driver_sql(
        "CREATE TEMP TABLE dmb_pending_port_shape (LIKE agent.turn) ON COMMIT DROP"
    )
    for name, expression in pending.items():
        conn.exec_driver_sql(
            f'ALTER TABLE dmb_pending_port_shape ADD CONSTRAINT "{name}" CHECK ({expression})'
        )
    columns = conn.exec_driver_sql("""
        SELECT DISTINCT quote_ident(a.attname)
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.conrelid = 'pg_temp.dmb_pending_port_shape'::regclass AND c.contype = 'c'
        ORDER BY 1
    """).scalars().all()
    if not columns:
        raise RuntimeError("Expected parsed turn check dependencies")
    changed = " OR ".join(f"OLD.{name} IS DISTINCT FROM NEW.{name}" for name in columns)
    owner._replace_guard(
        conn, pending,
        f"CREATE TRIGGER {owner._UPDATE} AFTER UPDATE ON agent.turn FOR EACH ROW "
        f"WHEN ({changed}) EXECUTE FUNCTION {owner._FUNCTION}",
    )
    conn.exec_driver_sql("DROP TABLE dmb_pending_port_shape")


def downgrade():
    raise RuntimeError('Retained pending Build Turns require forward recovery')
