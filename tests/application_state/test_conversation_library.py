from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import importlib
import psycopg
import pytest
from pydantic import ValidationError
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import library
from application_state.agent_conversation.types import (
    ConversationCommand,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from tests.application_state.test_agent_conversation_service import _provenance


def new(service, world="world-one"):
    p = service.get_world_pointer(world)
    return service.new_conversation(
        ConversationCommand(
            world_id=world,
            command_id=uuid4(),
            expected_pointer_revision=p.revision,
            expected_active_conversation_id=p.active_conversation_id,
        )
    ).conversation_id


def archive(service, count=3):
    from application_state.agent_conversation.types import TurnSubmission
    from tests.application_state.test_agent_conversation_service import (
        _submitted_intent,
    )

    cid = new(service)
    for n in range(count):
        question = f"Workshop project {n}"
        service.accept_turn(
            TurnSubmission(
                world_id="world-one",
                conversation_id=cid,
                idempotency_key=uuid4(),
                expected_conversation_revision=service.get_conversation(
                    "world-one", cid
                ).revision,
                user_text=question,
                provenance=_provenance(),
                submitted_intent_v1=_submitted_intent("world-one", question),
            )
        )
    new(service)
    return cid


def test_names_are_independent_cas_and_exact_retry(application_state_dsn):
    service = AgentConversationService()
    cid = new(service)
    pointer = service.get_world_pointer("world-one")
    original = service.get_conversation("world-one", cid)
    renamed = library.rename(
        "world-one",
        cid,
        library.NameChange(title="Brin — shop work", expected_revision=0),
    )
    assert renamed.title == "Brin — shop work" and renamed.name_revision == 1
    assert (
        library.rename(
            "world-one",
            cid,
            library.NameChange(title=renamed.title, expected_revision=0),
        )
        == renamed
    )
    with pytest.raises(ApplicationStateConflictError):
        library.rename(
            "world-one", cid, library.NameChange(title="Overwrite", expected_revision=0)
        )
    assert (
        service.get_world_pointer("world-one") == pointer
        and service.get_conversation("world-one", cid) == original
    )
    assert library.get_name("world-one", cid).title == renamed.title


def test_competing_names_do_not_overwrite(application_state_dsn):
    cid = new(AgentConversationService())

    def change(title):
        try:
            return library.rename(
                "world-one", cid, library.NameChange(title=title, expected_revision=0)
            ).title
        except ApplicationStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(change, ["First", "Second"]))
    assert len([r for r in results if r]) == 1
    assert library.get_name("world-one", cid).name_revision == 1


def test_archived_names_and_pagination_never_activate(application_state_dsn):
    service = AgentConversationService()
    new(service)
    old = archive(service, 3)
    archive(service, 1)
    pointer = service.get_world_pointer("world-one")
    first = library.list_library("world-one", status="archived", limit=1)
    assert len(first["items"]) == 1 and first["next_before"]
    second = library.list_library(
        "world-one",
        status="archived",
        limit=1,
        before=first["items"][0]["conversation_id"],
    )
    assert first["items"][0]["conversation_id"] != second["items"][0]["conversation_id"]
    page = library.read_turns("world-one", old, limit=2)
    assert [r["sequence"] for r in page["turns"]] == [2, 3]
    older = library.read_turns(
        "world-one", old, limit=2, before_sequence=page["next_before_sequence"]
    )
    assert [r["sequence"] for r in older["turns"]] == [1]
    assert library.get_name("world-one", old).title == "Workshop project 0"
    library.rename(
        "world-one",
        old,
        library.NameChange(title="Old workshop project", expected_revision=0),
    )
    assert library.get_name("world-one", old).status == "archived"
    assert service.get_world_pointer("world-one") == pointer


def test_foreign_world_reads_renames_and_cursor_refuse(application_state_dsn):
    service = AgentConversationService()
    cid = new(service)
    for call in [
        lambda: library.get_name("world-two", cid),
        lambda: library.rename(
            "world-two", cid, library.NameChange(title="Foreign", expected_revision=0)
        ),
        lambda: library.read_turns("world-two", cid),
        lambda: library.list_library("world-two", before=cid),
    ]:
        with pytest.raises(ApplicationStateNotFoundError):
            call()


def test_uses_mixed_projection_answer_not_raw_completion(
    application_state_dsn, monkeypatch
):
    service = AgentConversationService()
    cid = new(service)
    tid = uuid4()
    monkeypatch.setattr(
        AgentConversationService,
        "list_turns",
        lambda *a, **k: [
            SimpleNamespace(
                envelope=SimpleNamespace(
                    turn_id=tid,
                    sequence=1,
                    status="completed",
                    user_text="Mixed question",
                ),
                assistant_text="Projected mixed answer",
            )
        ],
    )
    result = library.read_turns("world-one", cid)
    assert result["turns"][0]["assistant_text"] == "Projected mixed answer"


@pytest.mark.parametrize("title", ["", "   ", "two\nlines", "a\x01b", "x" * 161])
def test_invalid_names_refuse(title):
    with pytest.raises(ValidationError):
        library.NameChange(title=title, expected_revision=0)


def test_migration_preserves_old_rows_and_refuses_lossy_downgrade(
    application_state_dsn, monkeypatch
):
    cid = new(AgentConversationService())
    library.rename(
        "world-one", cid, library.NameChange(title="Retained name", expected_revision=0)
    )
    migration = importlib.import_module(
        "application_state.migrations.versions.20261024_0062_conversation_names"
    )
    with psycopg.connect(application_state_dsn) as conn:

        class Operations:
            def execute(self, query):
                return conn.execute(query)

            def get_bind(self):
                return self

            def exec_driver_sql(self, query):
                row = conn.execute(query).fetchone()
                return SimpleNamespace(scalar_one=lambda: row[0])

        monkeypatch.setattr(migration, "op", Operations())
        with pytest.raises(RuntimeError, match="recovery forward"):
            migration.downgrade()
    assert library.get_name("world-one", cid).title == "Retained name"


def test_additive_name_table_keeps_existing_agent_rows(
    application_state_dsn, monkeypatch
):
    from psycopg import sql

    service = AgentConversationService()
    new(service)
    archive(service, 2)
    migration = importlib.import_module(
        "application_state.migrations.versions.20261024_0062_conversation_names"
    )
    with psycopg.connect(application_state_dsn) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='agent' AND tablename<>'conversation_name' ORDER BY 1"
            )
        ]

        def old_rows():
            return {
                table: conn.execute(
                    sql.SQL(
                        "SELECT md5(to_jsonb(t)::text) FROM agent.{} t ORDER BY 1"
                    ).format(sql.Identifier(table))
                ).fetchall()
                for table in tables
            }

        before = old_rows()

        class Operations:
            def execute(self, query):
                return conn.execute(query)

            def get_bind(self):
                return self

            def exec_driver_sql(self, query):
                value = conn.execute(query).fetchone()[0]
                return SimpleNamespace(scalar_one=lambda: value)

        monkeypatch.setattr(migration, "op", Operations())
        migration.downgrade()
        migration.upgrade()
        assert old_rows() == before
        assert (
            conn.execute("SELECT count(*) FROM agent.conversation_name").fetchone()[0]
            == 0
        )
