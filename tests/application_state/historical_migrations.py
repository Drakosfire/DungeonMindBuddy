"""Real historical schemas for migration witnesses, never serving-state repair."""

from urllib.parse import urlparse
import json
import re

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb


def _project_owned_rows(source_dsn, target_dsn, *, expected_omissions):
    """Project actual owned test rows into the historical schema's real columns.

    Constraints stay enabled. Missing populated tables or cyclic dependencies fail
    explicitly; no data-loss fallback, fabricated version marker or old writer.
    """
    source, target = urlparse(source_dsn), urlparse(target_dsn)
    for parsed in (source, target):
        if not re.fullmatch(
            r"dungeonbuddy_app_state_test_[0-9a-f]{12}", parsed.path.removeprefix("/")
        ):
            raise ValueError("Historical witnesses only accept owned test databases")
    if source.netloc != target.netloc or source.path == target.path:
        raise ValueError(
            "Historical witness requires distinct databases on its owned server"
        )
    with psycopg.connect(source_dsn) as before, psycopg.connect(target_dsn) as after:
        tables = before.execute(
            "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"
        ).fetchall()
        rows = {}
        omissions = {}
        for schema, table in tables:
            if (schema, table) == ("application_state", "schema_migrations"):
                continue
            identifier = sql.Identifier(schema, table)
            data = before.execute(
                sql.SQL("SELECT row_to_json(t) FROM {} t").format(identifier)
            ).fetchall()
            if data:
                if (
                    after.execute(
                        "SELECT to_regclass(%s)", (identifier.as_string(after),)
                    ).fetchone()[0]
                    is None
                ):
                    raise ValueError(
                        f"Populated source table absent from historical schema: {schema}.{table}"
                    )
                columns = {
                    r[0]
                    for r in after.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
                        (schema, table),
                    ).fetchall()
                }
                omitted = {
                    column
                    for (row,) in data
                    for column, value in row.items()
                    if column not in columns and value is not None
                }
                if omitted:
                    omissions[f"{schema}.{table}"] = {}
                    for column in sorted(omitted):
                        values = {
                            json.dumps(row[column], sort_keys=True): row[column]
                            for (row,) in data
                            if row.get(column) is not None
                        }
                        omissions[f"{schema}.{table}"][column] = [
                            values[key] for key in sorted(values)
                        ]
                rows[(schema, table)] = [row[0] for row in data]
        if omissions != expected_omissions:
            raise ValueError(
                f"Historical populated-column projection differs from its audited contract: {omissions!r}"
            )
        dependencies = {(schema, table): set() for schema, table in rows}
        for child_schema, child, parent_schema, parent in after.execute("""
            SELECT cn.nspname,c.relname,pn.nspname,p.relname
            FROM pg_constraint fk JOIN pg_class c ON c.oid=fk.conrelid
            JOIN pg_namespace cn ON cn.oid=c.relnamespace
            JOIN pg_class p ON p.oid=fk.confrelid JOIN pg_namespace pn ON pn.oid=p.relnamespace
            WHERE fk.contype='f'
        """).fetchall():
            child_key, parent_key = (child_schema, child), (parent_schema, parent)
            if child_key in rows and parent_key in rows and child_key != parent_key:
                dependencies[child_key].add(parent_key)
        while rows:
            ready = sorted(
                key for key in rows if not dependencies[key].intersection(rows)
            )
            if not ready:
                raise ValueError(
                    "Historical seed has cyclic table dependencies; explicit fixture required"
                )
            for key in ready:
                identifier = sql.Identifier(*key)
                data = rows.pop(key)
                # One INSERT also preserves real self-referential FK semantics:
                # all rows are present by this statement's constraint check.
                after.execute(
                    sql.SQL(
                        "INSERT INTO {} SELECT * FROM jsonb_populate_recordset(NULL::{}, %s)"
                    ).format(identifier, identifier),
                    (Jsonb(data),),
                )

                columns = [
                    r[0]
                    for r in after.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
                        key,
                    ).fetchall()
                ]
                expected = sorted(
                    json.dumps(
                        {column: row.get(column) for column in columns}, sort_keys=True
                    )
                    for row in data
                )
                actual = sorted(
                    json.dumps(row[0], sort_keys=True)
                    for row in after.execute(
                        sql.SQL("SELECT row_to_json(t) FROM {} t").format(identifier)
                    ).fetchall()
                )
                if actual != expected:
                    raise AssertionError(
                        f"Historical seed changed projected rows: {key}"
                    )


def assert_historical_refusal(dsn, revision, *, match):
    """Exercise one owning refusal against modern rows, never rewind later fences.

    The downgrade runs inside a real transaction on a disposable clone. A missing
    refusal is itself raised inside that transaction so even broken DDL rolls back.
    Verify all rows and the actual revision are unchanged, not just error wording.
    """
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine
    import pytest
    from application_state import cli
    from application_state.engine import sqlalchemy_url

    if not re.fullmatch(
        r"dungeonbuddy_app_state_test_[0-9a-f]{12}",
        urlparse(dsn).path.removeprefix("/"),
    ):
        raise ValueError("Historical refusal requires an owned test database")
    script = ScriptDirectory.from_config(cli.alembic_config()).get_revision(revision)
    if script is None or script.revision != revision:
        raise ValueError("Historical refusal requires an exact installed revision")

    def rows():
        with psycopg.connect(dsn) as conn:
            tables = conn.execute(
                "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"
            ).fetchall()
            return {
                key: conn.execute(
                    sql.SQL(
                        "SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text"
                    ).format(sql.Identifier(*key))
                ).fetchall()
                for key in tables
            }

    before, version = rows(), cli._read_current_revision(dsn)
    engine = create_engine(sqlalchemy_url(dsn))
    try:
        with pytest.raises(Exception, match=match):
            with (
                engine.begin() as conn,
                Operations.context(MigrationContext.configure(conn)),
            ):
                script.module.downgrade()
                raise AssertionError("historical_downgrade_did_not_refuse")
    finally:
        engine.dispose()
    assert cli._read_current_revision(dsn) == version
    assert rows() == before
