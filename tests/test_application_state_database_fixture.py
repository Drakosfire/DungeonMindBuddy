"""Real PostgreSQL proof of fresh clones, source ownership and failure cleanup."""

from dataclasses import replace
from uuid import uuid4

import psycopg
import pytest

from application_state import cli
from application_state.config import APPLICATION_STATE_DSN_ENV, TEST_ADMIN_DSN_ENV
from application_state.errors import ApplicationStateMigrationError
from application_state.naming import database_name_from_dsn
from tests.application_state import conftest as owner


def database_exists(admin, name):
    with psycopg.connect(admin) as c:
        return (
            c.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone()
            is not None
        )


def idle_connections(admin, name):
    with psycopg.connect(admin) as c:
        return c.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname=%s", (name,)
        ).fetchone()[0]


def test_fixture_is_a_fresh_clone_at_real_head(
    application_state_dsn, application_state_template
):
    seed = application_state_template
    assert database_name_from_dsn(application_state_dsn) != seed.name
    assert (
        cli._read_current_revision(application_state_dsn)
        == seed.revision
        == cli._alembic_head()
    )
    assert idle_connections(seed.admin_dsn, seed.name) == 0


def test_clones_keep_rows_and_schema_isolated(application_state_template):
    seed = application_state_template
    names = []
    with owner._cloned_test_database(seed) as first:
        names.append(database_name_from_dsn(first))
        with psycopg.connect(first) as c:
            c.execute("CREATE SCHEMA fixture_probe")
            c.execute("CREATE TABLE fixture_probe.marker(value text)")
            c.execute("INSERT INTO fixture_probe.marker VALUES ('only-first-clone')")
        with owner._cloned_test_database(seed) as second:
            names.append(database_name_from_dsn(second))
            assert names[0] != names[1]
            with psycopg.connect(second) as c:
                assert (
                    c.execute("SELECT to_regnamespace('fixture_probe')").fetchone()[0]
                    is None
                )
    with psycopg.connect(owner._replace_database(seed.admin_dsn, seed.name)) as c:
        assert (
            c.execute("SELECT to_regnamespace('fixture_probe')").fetchone()[0] is None
        )
    assert all(not database_exists(seed.admin_dsn, name) for name in names)


def test_failed_test_body_still_drops_clone(application_state_template):
    seed = application_state_template
    with pytest.raises(RuntimeError, match="body failed"):
        with owner._cloned_test_database(seed) as dsn:
            name = database_name_from_dsn(dsn)
            raise RuntimeError("body failed")
    assert not database_exists(seed.admin_dsn, name)


def test_failed_template_migration_drops_owned_database(monkeypatch):
    names = []
    original = owner._create_database

    def create(admin, name, **kwargs):
        original(admin, name, **kwargs)
        names.append(name)

    def fail(**kwargs):
        raise RuntimeError("migration failed")

    monkeypatch.setattr(owner, "_create_database", create)
    monkeypatch.setattr(cli, "upgrade_to_head", fail)
    with pytest.raises(RuntimeError, match="migration failed"):
        with owner._migrated_test_template(owner._admin_dsn()):
            pytest.fail("Failed template must not be published to tests")
    assert len(names) == 1 and not database_exists(owner._admin_dsn(), names[0])


@pytest.mark.parametrize("fault", ["admin", "name", "revision"])
def test_changed_template_refuses_before_database_creation(
    application_state_template, monkeypatch, fault
):
    seed = application_state_template
    if fault == "admin":
        monkeypatch.setenv(
            TEST_ADMIN_DSN_ENV, seed.admin_dsn + "?application_name=changed-admin"
        )
    elif fault == "name":
        seed = replace(seed, name="dungeonbuddy_application_state")
    else:
        seed = replace(seed, revision="different-schema")
    monkeypatch.setattr(
        owner, "_create_database", lambda *a, **k: pytest.fail("Unbound clone creation")
    )
    with pytest.raises((RuntimeError, ValueError)):
        with owner._cloned_test_database(seed):
            pytest.fail("Changed template must not be supplied to a test")


def test_corrupt_template_refuses_without_repair_or_leaked_clone(monkeypatch):
    admin = owner._admin_dsn()
    with owner._migrated_test_template(admin) as seed:
        with psycopg.connect(owner._replace_database(admin, seed.name)) as c:
            c.execute(
                "UPDATE application_state.schema_migrations SET version_num='changed-head'"
            )
        names = []
        original = owner._create_database

        def create(admin, name, **kwargs):
            original(admin, name, **kwargs)
            names.append(name)

        monkeypatch.setattr(owner, "_create_database", create)
        monkeypatch.setattr(
            cli,
            "upgrade_to_head",
            lambda **k: pytest.fail("No per-test migration repair"),
        )
        with pytest.raises(ApplicationStateMigrationError):
            with owner._cloned_test_database(seed):
                pytest.fail("Corrupt clone must not reach its test")
        assert len(names) == 1 and not database_exists(admin, names[0])
        assert (
            cli._read_current_revision(owner._replace_database(admin, seed.name))
            == "changed-head"
        )


def test_migration_failure_closes_owned_engine(monkeypatch):
    from alembic.runtime.environment import EnvironmentContext

    admin = owner._admin_dsn()
    name = "dungeonbuddy_app_state_test_" + uuid4().hex[:12]
    owner._create_database(admin, name)
    try:
        dsn = owner._replace_database(admin, name)

        def fail(*args, **kwargs):
            raise RuntimeError("injected migration failure")

        with monkeypatch.context() as patch:
            patch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
            patch.setattr(EnvironmentContext, "run_migrations", fail)
            with pytest.raises(RuntimeError, match="injected migration failure"):
                cli.upgrade_to_head(dsn=dsn)
        assert idle_connections(admin, name) == 0
    finally:
        owner._drop_database(admin, name)
