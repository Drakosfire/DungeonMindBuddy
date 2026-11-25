"""Run the existing lifecycle check under the final-row Graph dependency guard."""

import json

from alembic import op
from sqlalchemy import text

revision = "20261123_0196"
down_revision = "20261123_0195"
branch_labels = None
depends_on = None

_LIFECYCLE = "agent_turn_lifecycle_check"
_FUNCTION = "agent.validate_turn_graph_write()"
_UPDATE = "turn_graph_validate_update"


def _replace_guard(conn, definitions, update_trigger):
    checks = "\n".join(
        f"IF (SELECT ({expression}) IS FALSE FROM (SELECT NEW.*) AS candidate) "
        f"THEN RAISE check_violation USING SCHEMA = 'agent', TABLE = 'turn', "
        f"CONSTRAINT = '{name}', MESSAGE = 'Turn violates {name}'; END IF;"
        for name, expression in definitions.items()
    )
    conn.exec_driver_sql(
        f"CREATE OR REPLACE FUNCTION {_FUNCTION} RETURNS trigger LANGUAGE plpgsql "
        f"AS $guard$ BEGIN\n{checks}\nRETURN NULL; END; $guard$"
    )
    conn.exec_driver_sql(f"DROP TRIGGER {_UPDATE} ON agent.turn")
    conn.exec_driver_sql(update_trigger)
    conn.exec_driver_sql(f"ALTER TABLE agent.turn ENABLE ALWAYS TRIGGER {_UPDATE}")


def _comment(conn, value):
    quoted = conn.execute(text("SELECT quote_literal(:value)"), {"value": json.dumps(value)}).scalar_one()
    conn.exec_driver_sql(f"COMMENT ON FUNCTION {_FUNCTION} IS {quoted}")


def _saved_guard(conn):
    return json.loads(conn.execute(
        text("SELECT obj_description(to_regprocedure(:function), 'pg_proc')"),
        {"function": _FUNCTION},
    ).scalar_one())


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    graph = _saved_guard(conn)
    lifecycle = conn.execute(text("""
        SELECT pg_get_expr(conbin, conrelid) FROM pg_constraint
        WHERE conrelid = 'agent.turn'::regclass AND conname = :name
          AND contype = 'c' AND convalidated
    """), {"name": _LIFECYCLE}).scalar_one()
    prior_trigger = conn.execute(text("""
        SELECT pg_get_triggerdef(oid) FROM pg_trigger
        WHERE tgrelid = 'agent.turn'::regclass AND tgname = :name AND tgenabled = 'A'
    """), {"name": _UPDATE}).scalar_one()
    definitions = graph | {_LIFECYCLE: lifecycle}
    # Ask PostgreSQL for the actual parsed dependencies of the exact checks.
    conn.exec_driver_sql("CREATE TEMP TABLE dmb_turn_guard_shape (LIKE agent.turn) ON COMMIT DROP")
    for name, expression in definitions.items():
        conn.exec_driver_sql(f"ALTER TABLE dmb_turn_guard_shape ADD CONSTRAINT {name} CHECK ({expression})")
    columns = conn.exec_driver_sql("""
        SELECT DISTINCT quote_ident(a.attname) FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.conrelid = 'pg_temp.dmb_turn_guard_shape'::regclass AND c.contype = 'c'
        ORDER BY 1
    """).scalars().all()
    if not columns:
        raise RuntimeError("Expected parsed turn check dependencies")
    # Compare the final row, including writes made by BEFORE triggers.
    changed = " OR ".join(f"OLD.{name} IS DISTINCT FROM NEW.{name}" for name in columns)
    _replace_guard(conn, definitions,
                   f"CREATE TRIGGER {_UPDATE} AFTER UPDATE ON agent.turn FOR EACH ROW "
                   f"WHEN ({changed}) EXECUTE FUNCTION {_FUNCTION}")
    _comment(conn, {"graph": graph, "lifecycle": lifecycle, "update_trigger": prior_trigger})
    conn.exec_driver_sql(f"ALTER TABLE agent.turn DROP CONSTRAINT {_LIFECYCLE}")
    conn.exec_driver_sql("DROP TABLE dmb_turn_guard_shape")


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    saved = _saved_guard(conn)
    conn.exec_driver_sql(f"ALTER TABLE agent.turn ADD CONSTRAINT {_LIFECYCLE} CHECK ({saved['lifecycle']})")
    _replace_guard(conn, saved["graph"], saved["update_trigger"])
    _comment(conn, saved["graph"])
