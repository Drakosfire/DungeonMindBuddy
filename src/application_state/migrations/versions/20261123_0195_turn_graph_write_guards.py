"""Skip Graph predicates when a turn update leaves their inputs unchanged."""

import json

from alembic import op
from sqlalchemy import text

revision = "20261123_0195"
down_revision = "20261123_0194"
branch_labels = None
depends_on = None

_CHECKS = (
    "agent_turn_graph_completion_check",
    "agent_turn_graph_context_execution_check",
    "agent_turn_graph_context_receipt_check",
)
_FUNCTION = "validate_turn_graph_write"
_TRIGGERS = ("turn_graph_validate_insert", "turn_graph_validate_update")


def upgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    predicates = conn.execute(text("""
        SELECT conname, pg_get_expr(conbin, conrelid) AS expression,
               conkey, convalidated
        FROM pg_constraint
        WHERE conrelid = 'agent.turn'::regclass AND contype = 'c'
    """)).mappings()
    checks = {row["conname"]: row for row in predicates}
    if any(name not in checks or not checks[name]["convalidated"] for name in _CHECKS):
        raise RuntimeError("Expected validated Graph CHECK constraints before installing guards")

    columns = dict(conn.exec_driver_sql("""
        SELECT attnum, quote_ident(attname)
        FROM pg_attribute
        WHERE attrelid = 'agent.turn'::regclass AND attnum > 0 AND NOT attisdropped
    """).tuples().all())
    dependencies = set()
    statements = []
    for name in _CHECKS:
        check = checks[name]
        dependencies.update(check["conkey"])
        statements.append(
            f'IF (SELECT ({check["expression"]}) IS FALSE FROM (SELECT NEW.*) AS candidate) '
            f"THEN RAISE check_violation USING SCHEMA = 'agent', TABLE = 'turn', "
            f"CONSTRAINT = '{name}', MESSAGE = 'Turn violates {name}'; END IF;"
        )
    if not dependencies or not dependencies <= columns.keys():
        raise RuntimeError("Graph CHECK dependencies must be ordinary turn columns")
    changed = " OR ".join(
        f"OLD.{columns[column]} IS DISTINCT FROM NEW.{columns[column]}"
        for column in sorted(dependencies)
    )
    body = "\n".join(statements)
    conn.exec_driver_sql(
        f"CREATE FUNCTION agent.{_FUNCTION}() RETURNS trigger LANGUAGE plpgsql "
        f"AS $guard$ BEGIN\n{body}\nRETURN NULL; END; $guard$"
    )
    conn.exec_driver_sql(
        f"CREATE TRIGGER {_TRIGGERS[0]} AFTER INSERT ON agent.turn "
        f"FOR EACH ROW EXECUTE FUNCTION agent.{_FUNCTION}()"
    )
    # Observe the final value, including changes made by BEFORE triggers.
    conn.exec_driver_sql(
        f"CREATE TRIGGER {_TRIGGERS[1]} AFTER UPDATE ON agent.turn FOR EACH ROW "
        f"WHEN ({changed}) EXECUTE FUNCTION agent.{_FUNCTION}()"
    )
    # Retain the exact deparsed expressions for transactional downgrade.
    definitions = json.dumps({name: checks[name]["expression"] for name in _CHECKS})
    literal = conn.execute(text("SELECT quote_literal(:definitions)"),
                           {"definitions": definitions}).scalar_one()
    conn.exec_driver_sql(f"COMMENT ON FUNCTION agent.{_FUNCTION}() IS {literal}")
    for name in _TRIGGERS:
        conn.exec_driver_sql(f"ALTER TABLE agent.turn ENABLE ALWAYS TRIGGER {name}")
    for name in _CHECKS:
        conn.exec_driver_sql(f"ALTER TABLE agent.turn DROP CONSTRAINT {name}")


def downgrade():
    conn = op.get_bind()
    conn.exec_driver_sql("LOCK TABLE agent.turn IN ACCESS EXCLUSIVE MODE")
    saved = conn.execute(text(
        "SELECT obj_description(to_regprocedure(:guard), 'pg_proc')"
    ), {"guard": f"agent.{_FUNCTION}()"}).scalar_one()
    if not saved:
        raise RuntimeError("Missing prior Graph CHECK definitions")
    definitions = json.loads(saved)
    if set(definitions) != set(_CHECKS):
        raise RuntimeError("Unexpected prior Graph CHECK definitions")
    for name in _CHECKS:
        conn.exec_driver_sql(f"ALTER TABLE agent.turn ADD CONSTRAINT {name} CHECK ({definitions[name]})")
    for name in _TRIGGERS:
        conn.exec_driver_sql(f"DROP TRIGGER {name} ON agent.turn")
    conn.exec_driver_sql(f"DROP FUNCTION agent.{_FUNCTION}()")
