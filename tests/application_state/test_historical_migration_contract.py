"""Real historical schemas, strict current-head fixtures and irreversible fences."""

from urllib.parse import urlparse

import psycopg
import pytest
from alembic import command
from alembic.util.exc import CommandError

from application_state import cli
from tests.application_state import conftest as owner
from tests.application_state.historical_migrations import _project_owned_rows

REVISION = "20261007_0018"


def _exists(admin, name):
    with psycopg.connect(admin) as conn:
        return (
            conn.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", (name,)
            ).fetchone()
            is not None
        )


def test_historical_template_cached_once_but_each_clone_is_independent(
    historical_templates, historical_database
):
    template = historical_templates(REVISION)
    assert historical_templates(REVISION) is template
    # Historical opt-in must never relax the ordinary current-head clone contract.
    with pytest.raises(RuntimeError, match="another installed schema head"):
        with owner._cloned_test_database(template):
            pytest.fail("Historical schema escaped through current-head fixture")
    with historical_database(REVISION) as first:
        assert cli._read_current_revision(first) == REVISION
        with psycopg.connect(first) as conn:
            conn.execute("CREATE SCHEMA isolation_probe")
            conn.execute("CREATE TABLE isolation_probe.marker(value text)")
            conn.execute("INSERT INTO isolation_probe.marker VALUES ('first-only')")
        with historical_database(REVISION) as second:
            assert first != second
            assert cli._read_current_revision(second) == REVISION
            with psycopg.connect(second) as conn:
                assert conn.execute(
                    "SELECT to_regnamespace('isolation_probe')"
                ).fetchone() == (None,)
    for dsn in (first, second):
        assert not _exists(template.admin_dsn, urlparse(dsn).path[1:])
    with psycopg.connect(
        owner._replace_database(template.admin_dsn, template.name)
    ) as conn:
        assert conn.execute("SELECT to_regnamespace('isolation_probe')").fetchone() == (
            None,
        )


@pytest.mark.parametrize("revision", [None, "head", "20261007_001", "not-a-revision"])
def test_historical_alias_or_unknown_revision_refuses_before_allocation(
    historical_templates, monkeypatch, revision
):
    monkeypatch.setattr(
        owner, "_create_database", lambda *a, **k: pytest.fail("Unpinned allocation")
    )
    with pytest.raises((ValueError, CommandError)):
        historical_templates(revision)


def test_historical_projection_refuses_unknown_populated_table_and_cleans_clone(
    application_state_dsn, historical_templates, historical_database
):
    template = historical_templates(REVISION)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("CREATE SCHEMA unreviewed_seed")
        conn.execute("CREATE TABLE unreviewed_seed.payload(value text)")
        conn.execute("INSERT INTO unreviewed_seed.payload VALUES ('must-not-be-lost')")
    with psycopg.connect(template.admin_dsn) as conn:
        before = conn.execute(
            "SELECT datname FROM pg_database WHERE datname LIKE 'dungeonbuddy_app_state_test_%' ORDER BY datname"
        ).fetchall()
    with pytest.raises(ValueError, match="Populated source table absent"):
        with historical_database(REVISION, source_dsn=application_state_dsn):
            pytest.fail("Unknown data silently omitted")
    with psycopg.connect(template.admin_dsn) as conn:
        assert (
            conn.execute(
                "SELECT datname FROM pg_database WHERE datname LIKE 'dungeonbuddy_app_state_test_%' ORDER BY datname"
            ).fetchall()
            == before
        )


@pytest.mark.parametrize(
    "source,target",
    [
        (
            "postgresql://localhost/operator",
            "postgresql://localhost/dungeonbuddy_app_state_test_0123456789ab",
        ),
        (
            "postgresql://localhost/dungeonbuddy_app_state_test_0123456789ab",
            "postgresql://localhost/operator",
        ),
        (
            "postgresql://localhost/dungeonbuddy_app_state_test_template_0123456789ab",
            "postgresql://localhost/dungeonbuddy_app_state_test_0123456789ab",
        ),
    ],
)
def test_projection_rejects_nonowned_database_before_connect(
    source, target, monkeypatch
):
    with monkeypatch.context() as patch:
        patch.setattr(
            psycopg, "connect", lambda *a, **k: pytest.fail("Unowned database access")
        )
        with pytest.raises(ValueError, match="owned test databases"):
            _project_owned_rows(source, target, expected_omissions={})


def test_current_production_downgrade_fence_preserves_revision_and_rows(
    application_state_dsn,
):
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("CREATE SCHEMA fence_probe")
        conn.execute("CREATE TABLE fence_probe.marker(value text)")
        conn.execute("INSERT INTO fence_probe.marker VALUES ('unchanged')")
    before = cli._current_and_head(application_state_dsn)
    assert before[0] == before[1]
    with pytest.raises(
        RuntimeError,
        match="Older readers cannot reconstruct Plan connected-page reviews",
    ):
        command.downgrade(cli.alembic_config(), "20261108_0140")
    assert cli._current_and_head(application_state_dsn) == before
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT value FROM fence_probe.marker").fetchall() == [
            ("unchanged",)
        ]
    cli.assert_at_head(dsn=application_state_dsn)


def test_corrupt_historical_template_refuses_without_repair():
    admin = owner._admin_dsn()
    with owner._migrated_test_template(admin, revision=REVISION) as template:
        with psycopg.connect(owner._replace_database(admin, template.name)) as conn:
            conn.execute(
                "UPDATE application_state.schema_migrations SET version_num='corrupt-historical-version'"
            )
        with pytest.raises(RuntimeError, match="differs from its pinned template"):
            with owner._cloned_test_database(template, revision=REVISION):
                pytest.fail("Corrupt historical template reached witness")
        with psycopg.connect(owner._replace_database(admin, template.name)) as conn:
            assert conn.execute(
                "SELECT version_num FROM application_state.schema_migrations"
            ).fetchone() == ("corrupt-historical-version",)


def test_missing_owning_refusal_is_failure_and_ddl_rolls_back(
    application_state_dsn, monkeypatch
):
    from alembic import op
    from alembic.script import ScriptDirectory
    from tests.application_state.historical_migrations import assert_historical_refusal

    script = ScriptDirectory.from_config(cli.alembic_config()).get_revision(
        "20261002_0012"
    )

    def broken_downgrade():
        op.execute("CREATE TABLE public.must_rollback_historical_probe(value text)")

    with monkeypatch.context() as patch:
        patch.setattr(script.module, "downgrade", broken_downgrade)
        patch.setattr(ScriptDirectory, "get_revision", lambda self, revision: script)
        with pytest.raises(AssertionError):
            assert_historical_refusal(
                application_state_dsn, script.revision, match="owning refusal required"
            )
    cli.assert_at_head(dsn=application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT to_regclass('public.must_rollback_historical_probe')"
        ).fetchone() == (None,)


@pytest.mark.parametrize(
    "expected_omissions",
    [{}, {"agent.world_state": {"unreviewed_payload": ["wrong-value"]}}],
)
def test_populated_column_projection_requires_exact_audited_values(
    application_state_dsn, historical_database, expected_omissions
):
    from uuid import uuid4
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import ConversationCommand

    AgentConversationService().new_conversation(
        ConversationCommand(
            world_id="projection-contract-guard",
            command_id=uuid4(),
            expected_pointer_revision=0,
            expected_active_conversation_id=None,
        )
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "ALTER TABLE agent.world_state ADD COLUMN unreviewed_payload text NOT NULL DEFAULT 'must-not-be-lost'"
        )
    with pytest.raises(ValueError, match="differs from its audited contract"):
        with historical_database(
            REVISION,
            source_dsn=application_state_dsn,
            expected_omissions=expected_omissions,
        ):
            pytest.fail("Unreviewed populated data was silently projected away")


def test_historical_admin_change_refuses_before_new_template_allocation(
    historical_templates, monkeypatch
):
    from application_state.config import TEST_ADMIN_DSN_ENV

    original = owner._admin_dsn()
    with monkeypatch.context() as patch:
        patch.setenv(TEST_ADMIN_DSN_ENV, original + "?application_name=changed-server")
        patch.setattr(
            owner,
            "_create_database",
            lambda *a, **k: pytest.fail("Changed-server allocation"),
        )
        with pytest.raises(RuntimeError, match="server changed during the session"):
            historical_templates("20261002_0012")
