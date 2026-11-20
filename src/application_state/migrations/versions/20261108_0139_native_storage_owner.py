"""Evaluate the shared native Turn storage predicate at its lifecycle owner once."""
from importlib import import_module

from alembic import op
from sqlalchemy import text

revision = '20261108_0139'
down_revision = '20261108_0138'
branch_labels = None
depends_on = None

_LIFECYCLE = 'agent_turn_lifecycle_check'
_DUPLICATES = (
    'agent_turn_graph_context_receipt_check',
    'agent_turn_graph_context_execution_check',
    'agent_turn_graph_completion_check',
)


def upgrade():
    conn = op.get_bind()
    owner = import_module('application_state.migrations.versions.20261101_0103_shared_native_turns')
    # Let the same PostgreSQL deparser identify the predicate; no SQL text parser
    # or permanent function is needed. This table never contains retained rows.
    conn.exec_driver_sql('CREATE TEMP TABLE dmb_native_storage_shape (LIKE agent.turn) ON COMMIT DROP')
    conn.exec_driver_sql('ALTER TABLE dmb_native_storage_shape ADD CONSTRAINT native_shape CHECK (COALESCE(('
        + owner._NATIVE + '), FALSE))')
    native = conn.execute(text("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
        "WHERE conrelid='pg_temp.dmb_native_storage_shape'::regclass AND conname='native_shape'")).scalar_one()
    definitions = {}
    for name in (_LIFECYCLE, *_DUPLICATES):
        expression = conn.execute(text("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
            "WHERE conrelid='agent.turn'::regclass AND conname=:name"), {'name': name}).scalar_one()
        # pg_get_expr indents nested CASE expressions relative to their outer
        # CASE. Account for that formatting only, then require the entire exact
        # fragment (including all literals/operators), not a partial match.
        anchor = native.split('\n', 1)[0]
        start = expression.find(anchor)
        tail = expression[start + len(anchor) + 1:] if start >= 0 else ''
        indent = tail[:len(tail) - len(tail.lstrip(' '))]
        fragment = native.replace('\n', '\n' + indent)
        # Migration120 copied the previous completion predicate into both
        # branches of its Play selector. These two exact copies are known.
        expected = 2 if name == 'agent_turn_graph_completion_check' else 1
        if expression.count(anchor) != expected or expression.count(fragment) != expected:
            raise RuntimeError('Native storage predicate changed before single-owner migration: ' + name)
        definitions[name] = (expression, fragment, expected)
    # Migration103 uses the same receipt-OR-execution dispatch in each owner.
    # Lifecycle continues requiring COALESCE(native,FALSE), so skipping only the
    # other identical native predicates cannot admit a row lifecycle rejects.
    for name in _DUPLICATES:
        expression, fragment, expected = definitions[name]
        expression = expression.replace(fragment, 'TRUE', expected)
        conn.exec_driver_sql(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
        conn.exec_driver_sql(f'ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK ({expression})')
    conn.exec_driver_sql('DROP TABLE pg_temp.dmb_native_storage_shape')


def downgrade():
    raise RuntimeError('Restore the previous native storage checks through a reviewed forward migration')
