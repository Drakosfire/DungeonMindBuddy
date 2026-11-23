"""Own a local benchmark database from clone creation through teardown."""

from contextlib import contextmanager
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


def _identity(connection, database):
    return connection.execute("""
        SELECT oid::text, (SELECT system_identifier::text FROM pg_control_system())
        FROM pg_database WHERE datname = %s
    """, (database,)).fetchone()


@contextmanager
def disposable_benchmark_database(admin_dsn, template):
    """Yield a new clone's manifest locator, then drop exactly that clone.

    The caller owns its workers and connections and must close them before
    leaving the context. The template is a pinned disposable evaluator fixture.
    """
    endpoint = conninfo_to_dict(admin_dsn)
    if (endpoint.get("host") not in {"127.0.0.1", "::1"} or endpoint.get("hostaddr")
            or endpoint.get("service") or endpoint.get("dbname") != "postgres"
            or (endpoint["host"], endpoint.get("port")) != (template["host"], str(template["port"]))
            or template["database"] in {"postgres", "template0", "template1"}):
        raise ValueError("Benchmark clone requires the pinned local evaluator endpoint")

    name = "benchmark_run_" + uuid4().hex
    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as connection:
        if _identity(connection, template["database"]) != (template["oid"], template["system_identifier"]):
            raise ValueError("Benchmark template identity differs from its pin")
        connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(name), sql.Identifier(template["database"])
        ))
        identity = None
        failure = None
        try:
            identity = _identity(connection, name)
            if identity is None or identity[1] != template["system_identifier"]:
                raise RuntimeError(f"Could not verify created benchmark database {name}")
            yield {**template, "database": name, "oid": identity[0]}
        except BaseException as error:
            failure = error
            raise
        finally:
            try:
                if identity is None or identity[1] != template["system_identifier"]:
                    raise RuntimeError("Clone identity could not be pinned")
                with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=5) as cleanup:
                    if _identity(cleanup, name) != identity:
                        raise RuntimeError("Clone identity changed before teardown")
                    cleanup.execute("SET lock_timeout = '5s'")
                    cleanup.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
            except Exception as cleanup_error:
                detail = f"Benchmark database {name} teardown failed: {type(cleanup_error).__name__}"
                if failure is None:
                    raise RuntimeError(detail) from cleanup_error
                failure.add_note(detail)
