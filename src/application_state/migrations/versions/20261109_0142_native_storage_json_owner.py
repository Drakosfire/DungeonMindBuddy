"""Materialize large native JSON inputs once at the existing storage-check owner."""
from importlib import import_module

from alembic import op
from sqlalchemy import text

revision = '20261109_0142'
down_revision = '20261108_0141'
branch_labels = None
depends_on = None

_FUNCTION = 'agent.native_turn_storage_shape_once'
_ARGS = (
    ('graph_context_receipt', 'jsonb'),
    ('graph_context_execution', 'jsonb'),
    ('completion', 'jsonb'),
    ('submitted_intent_fingerprint_v2', 'text'),
    ('submitted_intent_fingerprint_v1', 'text'),
    ('surface_resolution', 'text'),
    ('surface_id', 'text'),
    ('surface_instance_id', 'text'),
    ('world_id', 'text'),
    ('status', 'text'),
    ('completed_at', 'timestamp with time zone'),
    ('answer_composition_kind', 'text'),
    ('assistant_text', 'text'),
    ('user_text', 'text'),
    ('play_context_receipt', 'jsonb'),
    ('claim_expires_at', 'timestamp with time zone'),
)
_CALL = _FUNCTION + '(' + ','.join(name for name, _ in _ARGS) + ')'
_SIGNATURE = _FUNCTION + '(' + ','.join(kind for _, kind in _ARGS) + ')'


def upgrade():
    conn = op.get_bind()
    owner = import_module('application_state.migrations.versions.20261101_0103_shared_native_turns')
    # Check the actual column contract before installing a new function identity.
    columns = conn.execute(text("SELECT attname,format_type(atttypid,atttypmod) AS type,attcollation "
        "FROM pg_attribute WHERE attrelid='agent.turn'::regclass AND attnum>0 AND NOT attisdropped")).mappings().all()
    actual = {row['attname']: row for row in columns}
    if any(name not in actual or actual[name]['type'] != kind for name, kind in _ARGS):
        raise RuntimeError('Native storage input column contract changed')
    if len({actual[name]['attcollation'] for name, kind in _ARGS if kind == 'text'}) != 1:
        raise RuntimeError('Native storage text inputs have incompatible collations')
    conn.exec_driver_sql('CREATE TEMP TABLE dmb_native_json_owner_shape (LIKE agent.turn) ON COMMIT DROP')
    conn.exec_driver_sql('ALTER TABLE dmb_native_json_owner_shape ADD CONSTRAINT native_shape CHECK (COALESCE(('
        + owner._NATIVE + '),FALSE))')
    native = conn.execute(text("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
        "WHERE conrelid='pg_temp.dmb_native_json_owner_shape'::regclass AND conname='native_shape'")).scalar_one()
    expression = conn.execute(text("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
        "WHERE conrelid='agent.turn'::regclass AND conname='agent_turn_lifecycle_check'")).scalar_one()
    anchor = native.split('\n', 1)[0]
    start = expression.find(anchor)
    tail = expression[start + len(anchor) + 1:] if start >= 0 else ''
    indent = tail[:len(tail) - len(tail.lstrip(' '))]
    fragment = native.replace('\n', '\n' + indent)
    if expression.count(anchor) != 1 or expression.count(fragment) != 1:
        raise RuntimeError('Native lifecycle predicate changed before JSON owner migration')
    # CREATE deliberately refuses an unexpected preexisting function. This pure
    # owner is invoked on NULLs: STRICT would allow CHECK's NULL acceptance to
    # bypass the original COALESCE(native,FALSE) contract.
    parameters = ','.join(name + ' ' + kind for name, kind in _ARGS)
    conn.exec_driver_sql('CREATE FUNCTION ' + _FUNCTION + '(' + parameters + ''')
RETURNS boolean LANGUAGE plpgsql IMMUTABLE CALLED ON NULL INPUT
PARALLEL SAFE SECURITY INVOKER SET search_path=pg_catalog AS $native_storage$
BEGIN
    IF jsonb_typeof(graph_context_receipt)='object' THEN
        graph_context_receipt := graph_context_receipt || '{}'::jsonb;
    END IF;
    IF jsonb_typeof(graph_context_execution)='object' THEN
        graph_context_execution := graph_context_execution || '{}'::jsonb;
    END IF;
    RETURN COALESCE((''' + owner._NATIVE + '''),FALSE);
END
$native_storage$''')
    expression = expression.replace(fragment, _CALL, 1)
    conn.exec_driver_sql('ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_lifecycle_check')
    conn.exec_driver_sql('ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_lifecycle_check CHECK (' + expression + ')')
    conn.exec_driver_sql('DROP TABLE pg_temp.dmb_native_json_owner_shape')


def downgrade():
    raise RuntimeError('Retained native storage ownership requires a reviewed forward migration')
