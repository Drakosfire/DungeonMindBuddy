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


def archive(service, count=3, *, keep_active=False):
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
    if not keep_active:
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
    assert older["next_before_sequence"] is None
    exact = library.read_turns("world-one", old, limit=3)
    assert [r["sequence"] for r in exact["turns"]] == [1, 2, 3]
    assert exact["next_before_sequence"] is None
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
        "list_turn_page",
        lambda *a, **k: ([
            SimpleNamespace(
                envelope=SimpleNamespace(
                    turn_id=tid,
                    sequence=1,
                    status="completed",
                    user_text="Mixed question",
                    provenance=SimpleNamespace(surface_id="plan", primary_work=SimpleNamespace(kind="plan")),
                ),
                assistant_text="Projected mixed answer",
            )
        ], False),
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


def test_unclaimed_mixed_rules_library_keeps_prose_without_reply_object(application_state_dsn):
    from tests.application_state.test_rules_authority_reads import seed_read_fixture

    turn, _ = seed_read_fixture(application_state_dsn, plan=True)
    completed = AgentConversationService().inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert completed.base_projection.kind == "unclaimed"
    row, = library.read_turns(turn.world_id, turn.conversation_id)["turns"]
    assert row["assistant_text"] == completed.assistant_text
    assert row["reply_object"] is None


def test_active_messages_never_select_or_decode_execution_and_keep_exact_cursor(
    application_state_dsn, monkeypatch
):
    from application_state.agent_conversation import repository as repo

    service = AgentConversationService()
    cid = archive(service, 5, keep_active=True)
    pointer = service.get_world_pointer("world-one")

    def forbidden(*a, **k):
        raise AssertionError("Full turn validation on message read")

    monkeypatch.setattr(repo, "_turn_from_row", forbidden)
    original = psycopg.Cursor.execute

    def audited(cursor, query, *args, **kwargs):
        if isinstance(query, str) and query.lstrip().lower().startswith("select"):
            from application_state.agent_conversation.authored_reference_preview import SELECT as reference_select
            assert "graph_context_execution" not in query.replace(reference_select, "").replace(library._SAVED_STATBLOCK_PREVIEW_SELECT, "")
            if "graph_context_execution" in query:
                assert "AS authored_reference_inputs" in query
                assert "jsonb_path_query_array" in query
            if "graph_context_receipt" in query:
                assert query.count("graph_context_receipt") == 1
                assert "graph_context_receipt->'work_context'->'source_basis'" in query
        return original(cursor, query, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(psycopg.Cursor, "execute", audited)
        page = library.read_active_messages("world-one", limit=2)
        older = library.read_active_messages(
            "world-one", limit=2, before_sequence=page["next_before_sequence"]
        )
        archived = library.read_messages("world-one", cid, limit=2)
    assert page["conversation_id"] == page["active_conversation_id"] == str(cid)
    assert page["pointer_revision"] == pointer.revision
    assert [row["sequence"] for row in page["messages"]] == [4, 5]
    assert [row["sequence"] for row in older["messages"]] == [2, 3]
    assert all(
        row["provenance"]["world_id"] == "world-one" and row["idempotency_key"]
        for row in page["messages"]
    )
    assert archived["messages"] == [
        {
            k: v
            for k, v in row.items()
            if k not in {"revision", "idempotency_key", "provenance", "citation_preview", "authored_references", "reply_object"}
        }
        for row in page["messages"]
    ]
    assert service.get_world_pointer("world-one") == pointer


def test_active_message_pointer_and_rows_are_one_snapshot(
    application_state_dsn, monkeypatch
):
    service = AgentConversationService()
    cid = archive(service, 2, keep_active=True)
    read = library._message_page
    successor = []

    def concurrent(conn, *args, **kwargs):
        successor.append(new(service))
        return read(conn, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(library, "_message_page", concurrent)
        old = library.read_active_messages("world-one")
    assert old["conversation_id"] == str(cid) and len(old["messages"]) == 2
    current = library.read_active_messages("world-one")
    assert current["conversation_id"] == str(successor[0]) and current["messages"] == []
    absent = library.read_active_messages("unrelated-world")
    assert (
        absent["conversation_state"] == "absent"
        and absent["messages"] == []
        and absent["pointer_revision"] == 0
    )


def test_retry_history_excludes_unrelated_turns(application_state_dsn):
    service = AgentConversationService()
    cid = archive(service, keep_active=True)
    selected = service.list_turns("world-one", cid)[-1]
    page = library.read_retry_attempts("world-one", cid, selected.turn_id, limit=1)

    assert page["turns"] == []
    assert page["next_before_sequence"] is None
    other = new(service)
    with pytest.raises(ApplicationStateNotFoundError):
        library.read_retry_attempts("world-one", other, selected.turn_id)



def test_retry_history_hydrates_populated_page(application_state_dsn, monkeypatch):
    from application_state.agent_conversation.types import TurnFailure, TurnSubmission
    from tests.application_state.test_agent_conversation_service import _ref, _submitted_intent

    world = "world-one"
    service = AgentConversationService()
    cid = new(service)
    provenance = _provenance().model_copy(update={"surface_id": "build", "primary_work": _ref("build", "draft", "revision")})

    def accept():
        return service.accept_turn(
            TurnSubmission(
                world_id=world,
                conversation_id=cid,
                idempotency_key=uuid4(),
                expected_conversation_revision=service.get_conversation(world, cid).revision,
                user_text="Workshop project",
                provenance=provenance,
                submitted_intent_v1=_submitted_intent(world, "Workshop project", surface_id="build"),
            )
        )

    def interrupt(turn):
        running = service.begin_turn(world, cid, turn.turn_id, expected_revision=turn.revision)
        return service.fail_turn(
            TurnFailure(
                world_id=world,
                conversation_id=cid,
                turn_id=turn.turn_id,
                expected_revision=running.revision,
                failure_code="synthetic_before_dispatch",
            ),
            interrupted=True,
        )

    root = interrupt(accept())
    middle = accept()

    def link(previous, successor, ordinal):
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                """INSERT INTO agent.turn_retry
                   (predecessor_id, successor_id, root_id, world_id, conversation_id,
                    predecessor_revision, ordinal) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (previous.turn_id, successor.turn_id, root.turn_id, world, cid,
                 previous.revision, ordinal),
            )

    link(root, middle, 1)
    middle = interrupt(middle)
    selected = accept()
    link(middle, selected, 2)

    page = library.read_retry_attempts(world, cid, selected.turn_id, limit=2)
    assert [row["turn_id"] for row in page["turns"]] == [
        str(root.turn_id), str(middle.turn_id)
    ]
    first = library.read_retry_attempts(world, cid, selected.turn_id, limit=1)
    assert first["turns"] == page["turns"][1:]
    assert first["next_before_sequence"] == middle.sequence
    older = library.read_retry_attempts(
        world, cid, selected.turn_id, limit=1, before_sequence=middle.sequence
    )
    assert older["turns"] == page["turns"][:1]
    assert older["next_before_sequence"] is None

    contexts = [row["retry_context"] for row in page["turns"]]
    assert [context["ordinal"] for context in contexts] == [0, 1]
    assert [context["successor_id"] for context in contexts] == [
        str(middle.turn_id), str(selected.turn_id)
    ]
    assert all(context["reason"] == "inactive" for context in contexts)
    from application_state.agent_conversation import repository, retry

    page_connections = []
    read_page = repository.list_turn_page
    read_contexts = retry.library_contexts

    def track_page(conn, *args, **kwargs):
        page_connections.append(conn)
        return read_page(conn, *args, **kwargs)

    def check_snapshot(conn, *args, **kwargs):
        assert page_connections == [conn]
        assert conn.execute("SHOW transaction_isolation").fetchone() == ("repeatable read",)
        assert conn.execute("SHOW transaction_read_only").fetchone() == ("on",)
        return read_contexts(conn, *args, **kwargs)

    monkeypatch.setattr(repository, "list_turn_page", track_page)
    monkeypatch.setattr(retry, "library_contexts", check_snapshot)
    transcript = library.read_turns(world, cid)
    assert transcript["turns"][:2] == page["turns"]


def test_transcript_without_build_turns_uses_one_transaction(
    application_state_dsn, monkeypatch,
):
    conversation = archive(AgentConversationService(), 1)

    original_unit_of_work = library.unit_of_work
    transactions = []

    def track_transaction(*args, **kwargs):
        transactions.append(True)
        return original_unit_of_work(*args, **kwargs)

    monkeypatch.setattr(library, "unit_of_work", track_transaction)
    page = library.read_turns("world-one", conversation)
    row, = page["turns"]
    assert row["retry_context"] is None

    empty = library.read_turns("world-one", conversation, before_sequence=1)
    assert empty["turns"] == []
    assert empty["next_before_sequence"] is None
    assert len(transactions) == 2
