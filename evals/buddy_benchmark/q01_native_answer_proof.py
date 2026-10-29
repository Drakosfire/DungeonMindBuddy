"""Q01 selected-subject answer proof; default inspection is read-only.

The only mutable authority is the leased disposable APP database. Primary and
native authority stay read-only. Evidence checkpoints never replace APP receipts.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from . import q01_native_fixture_proof as fixture

AUTHORITY = "504c1d67b7bb244628de4b86c51cd7b3c045fd8c"
BASE = "c731056c8e7351a372f65be8ee2ad9719c181d86"
CHECKPOINT = "q01-native-answer-v1"
READ_REVISION = "rev:738443ee1f86e2485134a12d6695b0fc"
SUBJECT = "ent:6c8019cf4fe118ee7ae8411bb60469a1"
OLD_CONVERSATION = "1c8ee3dd-f0d8-43e5-bfa1-fb17578dfee5"
COMMAND_ID = "338dd1ba-4e2a-4cc7-adcb-f024193ab745"
QUESTION = "What did the party's arcana check reveal about the strange meat found beneath the guardhouse?"
START_SCHEMA = "20261028_0087"
END_SCHEMA = "20261029_0091"
MIGRATIONS = (
    "20261028_0088_play_session_summary.py",
    "20261028_0089_build_page_body.py",
    "20261029_0090_build_page_end.py",
    "20261029_0091_native_statement_answers.py",
)
require = fixture.require


def app_connection_url(dsn):
    """Render retained libpq options as the URL required by ordinary APP."""
    from psycopg.conninfo import conninfo_to_dict
    from urllib.parse import quote, urlencode

    values = conninfo_to_dict(dsn)
    user = values.pop("user", "")
    password = values.pop("password", None)
    host = values.pop("host")
    port = values.pop("port", None)
    database = values.pop("dbname")
    authority = quote(user, safe="")
    if password is not None:
        authority += ":" + quote(password, safe="")
    host = "[" + host + "]" if ":" in host else host
    result = (
        "postgresql://"
        + authority
        + "@"
        + host
        + (":" + str(int(port)) if port else "")
        + "/"
        + quote(database, safe="")
    )
    return result + ("?" + urlencode(values, quote_via=quote) if values else "")


def validate_identity(value, native=False):
    fixture.validate_connected(
        value, fixture.DATABASE if native else fixture.APP_DATABASE
    )
    require(
        value["database_oid"] == ("148023" if native else "148024"),
        "leased database OID differs",
    )


def immutable_save(directory, name, value):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / (name + ".json")
    if target.exists():
        require(
            json.loads(target.read_text()) == value, "checkpoint collision: " + name
        )
        return
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def row_inventory(dsn):
    """Hash every logical row, retaining only routing keys for exact delta checks."""
    from psycopg import sql

    result = {}
    with fixture.readonly(dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        tables = conn.execute(
            "SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"
        ).fetchall()
        for table in tables:
            name = table["table_schema"] + "." + table["table_name"]
            rows = conn.execute(
                sql.SQL("SELECT row_to_json(t)::text AS body FROM {}.{} t").format(
                    sql.Identifier(table["table_schema"]),
                    sql.Identifier(table["table_name"]),
                )
            ).fetchall()
            inventory = []
            for row in rows:
                body = json.loads(row["body"])
                inventory.append(
                    {
                        "sha256": fixture.sha(row["body"].encode()),
                        "keys": {
                            k: body[k]
                            for k in (
                                "world_id",
                                "conversation_id",
                                "turn_id",
                                "command_id",
                                "reference_role",
                                "ordinal",
                                "version_num",
                            )
                            if k in body
                        },
                    }
                )
            result[name] = sorted(inventory, key=lambda r: r["sha256"])
    return result


def validate_pointer(pointer, old):
    require(
        pointer is not None
        and pointer["world_id"] == fixture.WORLD
        and pointer["active_conversation_id"] == OLD_CONVERSATION
        and pointer["pointer_revision"] == 72,
        "original active pointer differs",
    )
    require(
        old is not None
        and old["conversation_id"] == OLD_CONVERSATION
        and old["world_id"] == fixture.WORLD
        and old["status"] == "active",
        "original conversation differs",
    )


def command(pointer):
    return {
        "command_id": COMMAND_ID,
        "expected_pointer_revision": 72,
        "expected_active_conversation_id": pointer["active_conversation_id"],
    }


def request_body():
    return {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": CHECKPOINT,
        "turn_id": CHECKPOINT + "-q01",
        "surface": {"surface_id": "plan", "instance_id": CHECKPOINT},
        "owner_scope": {"kind": "world", "world_id": fixture.WORLD},
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "native_statement_selection": {
            "schema": "dmb_native_statement_selection_v1",
            "managedWorldId": fixture.WORLD,
            "campaignId": fixture.CAMPAIGN,
            "revisionId": READ_REVISION,
            "subjectId": SUBJECT,
            "domainRef": {
                "authority_id": "dungeonbuddy.world",
                "revision": "2",
                "descriptor_sha256": "d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd",
            },
            "profileRef": {
                "authority_id": "dungeonbuddy.dnd5e",
                "revision": "2",
                "descriptor_sha256": "d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339",
            },
        },
        "message": QUESTION,
    }


def migration_inventory():
    root = Path(__file__).resolve().parents[2]
    result = {}
    for name in MIGRATIONS:
        relative = "src/application_state/migrations/versions/" + name
        expected = subprocess.run(
            ["git", "show", BASE + ":" + relative],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        require(
            (root / relative).read_bytes() == expected,
            "accepted migration file differs",
        )
        result[relative] = fixture.sha(expected)
    return result


def preflight(root, expected_schema=START_SCHEMA):
    import dungeonmind
    import worldkeeper

    connection, donor, files = fixture.retained_inputs(root)
    from psycopg.conninfo import make_conninfo

    os.environ["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = app_connection_url(
        connection["app_dsn"]
    )
    os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = app_connection_url(
        make_conninfo(connection["dsn"], options="-c default_transaction_read_only=on")
    )
    os.environ["DMB_MANAGED_WORLD_DATA_ROOT"] = str(files)
    native = fixture.check_server(connection["dsn"], fixture.DATABASE, donor)
    app = fixture.check_server(connection["app_dsn"], fixture.APP_DATABASE, donor)
    validate_identity(native, True)
    validate_identity(app)
    core = Path(dungeonmind.__file__).resolve().parents[1]
    require(core == fixture.CORE_ROOT / "src", "actual fixture Core import differs")
    core_integrity = fixture.verify_source_tree(
        core, fixture.CORE_ROOT, fixture.CORE_REF, ("dungeonmind", "dungeonmind_dnd")
    )
    wk = Path(worldkeeper.__file__).resolve().parents[1]
    wk_integrity = fixture.verify_source_tree(
        wk, wk.parent, "a30ee81ae0e777037c68afea8847b04a2c736ae1", ("worldkeeper",)
    )
    from psycopg.conninfo import make_conninfo

    repo = fixture.repository(
        make_conninfo(connection["dsn"], options="-c default_transaction_read_only=on"),
        native,
    )
    require(
        repo.get_head(fixture.WORLD).head_revision_id == READ_REVISION,
        "native fixture head changed",
    )
    snapshot = repo.get_revision(fixture.WORLD, READ_REVISION)
    require(
        any(e["entity_id"] == SUBJECT for e in snapshot.graph_payload["entities"]),
        "native subject missing",
    )
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        descriptors,
    )

    _, profile = descriptors(repo, fixture.WORLD, READ_REVISION)
    require(
        profile.profile_revision == "2"
        and fixture.digest(profile.model_dump(mode="json"))
        == request_body()["native_statement_selection"]["profileRef"][
            "descriptor_sha256"
        ],
        "native profile differs",
    )
    require(
        snapshot.revision.domain_contract_ref.descriptor_sha256
        == request_body()["native_statement_selection"]["domainRef"][
            "descriptor_sha256"
        ],
        "native domain differs",
    )
    registry = json.loads((files / "out/registries/world_containers.json").read_text())
    bound = next(
        r["native_graph_binding"]
        for r in registry["records"]
        if r["world_id"] == fixture.WORLD
    )
    require(
        bound["native_world_id"] == fixture.WORLD
        and bound["binding_version"] == 3
        and bound["status"] == "active",
        "native binding differs",
    )
    with fixture.readonly(connection["app_dsn"]) as conn:
        schema = conn.execute(
            "SELECT version_num FROM application_state.schema_migrations"
        ).fetchone()["version_num"]
        require(schema == expected_schema, "starting APP schema differs")
        pointer = conn.execute(
            "SELECT world_id,active_conversation_id::text,pointer_revision,updated_at::text FROM agent.world_state WHERE world_id=%s",
            (fixture.WORLD,),
        ).fetchone()
        old = conn.execute(
            "SELECT row_to_json(c) AS body FROM agent.conversation c WHERE conversation_id=%s",
            (OLD_CONVERSATION,),
        ).fetchone()
    old = None if old is None else old["body"]
    validate_pointer(pointer, old)
    require(
        fixture.validate_source((files / fixture.SOURCE_PATH).read_bytes())[
            "body_sha256"
        ]
        == fixture.BODY_SHA,
        "source differs",
    )
    return {
        "authority": AUTHORITY,
        "runner_sha256": fixture.sha(Path(__file__).read_bytes()),
        "native_identity": native,
        "app_identity": app,
        "schema": schema,
        "core": core_integrity,
        "wk": wk_integrity,
        "migrations": migration_inventory(),
        "pointer": pointer,
        "old_conversation": old,
        "new_conversation_command": command(pointer),
        "question_request": request_body(),
        "allowlist": {
            "application_state.schema_migrations": "0087→0091 only",
            "agent.conversation": {
                "append": 1,
                "archive_existing": OLD_CONVERSATION,
                "archive_columns": ["status", "revision", "archived_at", "updated_at"],
            },
            "agent.world_state": {"world": fixture.WORLD, "pointer": 73},
            "agent.command_receipt": {"append": 1, "command_id": COMMAND_ID},
            "agent.turn": {
                "append": 1,
                "world": fixture.WORLD,
                "single_owned_conversation": True,
            },
            "agent.turn_reference": {
                "append": 3,
                "roles": ["primary", "supporting", "selected"],
                "single_owned_turn": True,
            },
        },
        "native_tables": fixture.database_fingerprints(connection["dsn"]),
        "app_tables": row_inventory(connection["app_dsn"]),
        "files": fixture.file_fingerprints(files),
    }


def migration_conservation(before, after):
    require(set(before) == set(after), "migration table inventory changed")
    for table in before:
        if table == "application_state.schema_migrations":
            require(
                len(after[table]) == 1
                and after[table][0]["keys"].get("version_num") == END_SCHEMA,
                "migration schema head differs",
            )
        else:
            require(
                before[table] == after[table],
                "migration changed retained rows: " + table,
            )


def snapshot_app(connection, donor, evidence):
    from psycopg.conninfo import conninfo_to_dict

    target = evidence / "app-before.dump"
    require(not target.exists(), "original APP snapshot already exists")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        subprocess.run(
            [
                "docker",
                "exec",
                donor["container"],
                "pg_dump",
                "-U",
                conninfo_to_dict(connection["app_dsn"])["user"],
                "-d",
                fixture.APP_DATABASE,
                "-Fc",
            ],
            stdout=output,
            stderr=subprocess.PIPE,
            check=True,
        )
        output.flush()
        os.fsync(output.fileno())
    with target.open("rb") as stream:
        listed = subprocess.run(
            ["docker", "exec", "-i", donor["container"], "pg_restore", "--list"],
            stdin=stream,
            capture_output=True,
            check=True,
        )
    immutable_save(
        evidence,
        "snapshot",
        {
            "database": fixture.APP_DATABASE,
            "sha256": fixture.sha(target.read_bytes()),
            "readable": True,
            "toc_entries": sum(
                bool(x) and not x.startswith(b";") for x in listed.stdout.splitlines()
            ),
            "restore_executed": False,
        },
    )


def configure_operation(root, evidence):
    """Only fixture configuration; all ordinary resolvers/transports remain real."""
    from dotenv import dotenv_values
    from psycopg.conninfo import make_conninfo

    connection, donor, files = fixture.retained_inputs(root)
    protected = {
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL": app_connection_url(
            connection["app_dsn"]
        ),
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": app_connection_url(
            make_conninfo(
                connection["dsn"], options="-c default_transaction_read_only=on"
            )
        ),
        "DMB_MANAGED_WORLD_DATA_ROOT": str(files),
        "DUNGEONMIND_LIVE_SESSION_DIR": str(evidence / "session"),
    }
    code_root = Path(__file__).resolve().parents[2]
    for candidate in (
        code_root / ".env",
        code_root / ".env.development",
        code_root.parent / ".env.development",
    ):
        if candidate.is_file():
            values = dotenv_values(candidate)
            require(
                all(k not in values or values[k] == v for k, v in protected.items()),
                "ordinary dotenv would override isolated database configuration",
            )
    secrets = dotenv_values(
        "/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/.env"
    )
    configured_key = secrets.get("OPENAI_API_KEY") or secrets.get("DUNGEONBUDDY_OPENAI")
    if configured_key:
        os.environ["OPENAI_API_KEY"] = configured_key
    require(
        bool(os.environ.get("OPENAI_API_KEY")),
        "configured OpenAI credential unavailable",
    )
    import secrets as secure

    token = secure.token_urlsafe(48)
    os.environ.update(
        protected
        | {
            "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
            "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
            "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": token,
        }
    )
    os.environ.pop("DMB_AGENT_GRAPH_LOCAL_PROFILE", None)
    return connection, donor, files, token


def validate_archive(old, after):
    allowed = {"status", "revision", "archived_at", "updated_at"}
    require(
        {k: v for k, v in old.items() if k not in allowed}
        == {k: v for k, v in after.items() if k not in allowed},
        "old conversation content changed",
    )
    require(
        after["status"] == "archived"
        and after["revision"] == old["revision"] + 1
        and after["archived_at"] is not None
        and after["updated_at"] == after["archived_at"],
        "old conversation archive differs",
    )


def app_conservation(before, after, *, conversation, turn, old_conversation):
    """All deltas must belong to the exact newly receipted operation and archive."""
    require(set(before) == set(after), "APP table inventory changed")
    counts = {}
    for table in before:
        prior = {row["sha256"]: row for row in before[table]}
        later = {row["sha256"]: row for row in after[table]}
        # Retain multiplicity independently of keys.
        from collections import Counter

        removed = Counter(r["sha256"] for r in before[table]) - Counter(
            r["sha256"] for r in after[table]
        )
        added = Counter(r["sha256"] for r in after[table]) - Counter(
            r["sha256"] for r in before[table]
        )
        if not removed and not added:
            continue
        counts[table] = {"removed": sum(removed.values()), "added": sum(added.values())}
        if table == "agent.conversation":
            require(
                sum(removed.values()) == 1 and sum(added.values()) == 2,
                "conversation delta differs",
            )
            require(
                all(
                    prior[h]["keys"].get("conversation_id") == old_conversation
                    for h in removed
                ),
                "unrelated conversation removed",
            )
            require(
                {later[h]["keys"].get("conversation_id") for h in added}
                == {old_conversation, conversation},
                "unrelated conversation added",
            )
        elif table == "agent.world_state":
            require(
                sum(removed.values()) == sum(added.values()) == 1
                and all(
                    prior[h]["keys"].get("world_id") == fixture.WORLD for h in removed
                )
                and all(
                    later[h]["keys"].get("world_id") == fixture.WORLD for h in added
                ),
                "unrelated pointer changed",
            )
        elif table in ("agent.command_receipt", "agent.turn", "agent.turn_reference"):
            n = {
                "agent.command_receipt": 1,
                "agent.turn": 1,
                "agent.turn_reference": 3,
            }[table]
            require(
                not removed and sum(added.values()) == n,
                "unexpected append count: " + table,
            )
            if table == "agent.turn_reference":
                require(
                    {later[h]["keys"].get("reference_role") for h in added}
                    == {"primary", "supporting", "selected"}
                    and all(later[h]["keys"].get("ordinal") == 0 for h in added),
                    "owned reference roles differ",
                )
            for h in added:
                keys = later[h]["keys"]
                if table == "agent.turn_reference":
                    require(keys.get("turn_id") == turn, "unrelated turn reference")
                else:
                    require(
                        keys.get("world_id") == fixture.WORLD
                        and keys.get("conversation_id") == conversation,
                        "unrelated owned row",
                    )
                if table == "agent.command_receipt":
                    require(
                        keys.get("command_id") == COMMAND_ID,
                        "wrong conversation command",
                    )
                if table == "agent.turn":
                    require(keys.get("turn_id") == turn, "wrong turn appended")
        else:
            require(False, "forbidden APP table delta: " + table)
    require(
        set(counts)
        == {
            "agent.conversation",
            "agent.world_state",
            "agent.command_receipt",
            "agent.turn",
            "agent.turn_reference",
        },
        "required APP lifecycle rows missing",
    )
    return counts


def provider_counts(turn):
    execution = turn.get("graph_context_execution") or {}
    events = execution.get("events", [])
    return {
        "authorizations": sum(
            e["kind"] == "provider_attempt_authorized" for e in events
        ),
        "sdk_entered": sum(
            e["kind"] == "provider_outcome" and e.get("outcome") == "sdk_entered"
            for e in events
        ),
    }


def require_delivered(turn, reply, history, opened, replay, after_replay):
    require(
        turn.get("status") == "completed",
        "writer did not complete; original outcome retained",
    )
    counts = provider_counts(turn)
    require(
        counts == {"authorizations": 1, "sdk_entered": 1},
        "exact single provider operation not proved",
    )
    require(
        provider_counts(after_replay) == counts and after_replay == turn,
        "replay changed producing turn or dispatched again",
    )
    receipt = turn.get("graph_context_receipt") or {}
    frame = receipt.get("frame") or {}
    require(
        frame.get("subject_id") == SUBJECT
        and frame.get("revision_id") == READ_REVISION
        and frame.get("role") == "gm"
        and frame.get("supports"),
        "selected subject support missing",
    )
    inputs = [
        e
        for e in turn["graph_context_execution"]["events"]
        if e["kind"] == "native_statement_input_v1"
    ]
    require(len(inputs) == 1, "writer input evidence missing")
    request = json.loads(inputs[0]["prepared_request_json"])
    content = json.loads(request["input"][0]["content"])
    require(
        content == {"question": QUESTION, "native_statement_context": frame},
        "provider did not receive exact qualified support",
    )
    require(
        fixture.sha(inputs[0]["prepared_request_json"].encode())
        == inputs[0]["envelope_sha256"],
        "producing request hash differs",
    )
    completion = turn.get("completion") or {}
    citations = completion.get("native_clause_citations") or []
    require(
        citations and len(opened) == len(citations), "citation opening evidence missing"
    )
    for citation, value in zip(citations, opened, strict=True):
        require(
            value.get("content") == fixture.QUOTE and value.get("citation") == citation,
            "historical citation content differs",
        )
        require(
            citation["read_revision_id"] == READ_REVISION
            and citation["body_sha256"] == fixture.BODY_SHA
            and citation["clause_sha256"] == fixture.CLAUSE_SHA
            and (citation["start_byte"], citation["end_byte"]) == (4868, 4939),
            "citation source version/extent differs",
        )
    native = reply.get("native_statement_context") or {}
    require(
        native.get("completion") == completion
        and replay.get("answer", {}).get("text") == reply.get("answer", {}).get("text"),
        "completion delivery/replay differs",
    )
    matches = [
        t for t in history.get("turns", []) if t.get("turn_id") == turn["turn_id"]
    ]
    require(
        len(matches) == 1
        and matches[0].get("native_statement_context", {}).get("completion")
        == completion,
        "ordinary history completion missing",
    )
    return {
        "selected_subject_provider_inclusion": "pass",
        "answer_delivery_persistence_replay": "pass",
        "exact_citation_opening": "pass",
        "semantic_support": "unassessed",
        "autonomous_discovery": "unassessed",
        "provider": request["model"],
        "provider_counts": counts,
    }


def apply_answer(root, evidence, frozen):
    require(
        not (evidence / "provider-operation-intent.json").exists(),
        "original operation retained; no automatic redispatch",
    )
    connection, donor, files, token = configure_operation(root, evidence)
    # All normal runtime imports occur after explicit isolated configuration.
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import (
        ConversationCommand,
        request_fingerprint,
    )
    from application_state.config import load_runtime_dsn
    from apps.live_control_server import config
    from psycopg.conninfo import conninfo_to_dict
    from uuid import UUID

    require(
        conninfo_to_dict(load_runtime_dsn())["dbname"] == fixture.APP_DATABASE,
        "ordinary APP repository target differs",
    )
    require(
        conninfo_to_dict(config.world_graph_authority_database_url())["options"]
        == "-c default_transaction_read_only=on",
        "ordinary native connections not read-only",
    )
    current = preflight(root, expected_schema=END_SCHEMA)
    for key in frozen:
        if key not in {"schema", "app_tables"}:
            require(
                current[key] == frozen[key], "post-migration authority drift: " + key
            )
    migration_conservation(frozen["app_tables"], current["app_tables"])
    require(
        not (evidence / "provider-operation-intent.json").exists(),
        "original operation retained; no automatic redispatch",
    )
    typed = ConversationCommand(
        world_id=fixture.WORLD,
        command_id=UUID(COMMAND_ID),
        expected_pointer_revision=72,
        expected_active_conversation_id=UUID(OLD_CONVERSATION),
    )
    immutable_save(
        evidence,
        "conversation-command",
        {
            "request": frozen["new_conversation_command"],
            "request_fingerprint": request_fingerprint(typed),
            "old_row": frozen["old_conversation"],
        },
    )
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")
    service = AgentConversationService()
    client = TestClient(
        app, client=("127.0.0.1", 42000), headers={"Authorization": "Bearer " + token}
    )
    started = client.post(
        f"/api/live/agent/worlds/{fixture.WORLD}/conversation/new",
        json=frozen["new_conversation_command"],
    )
    immutable_save(
        evidence,
        "conversation-http",
        {"status": started.status_code, "body": started.json()},
    )
    require(started.status_code == 200, "ordinary conversation command failed")
    owned = started.json()["conversation_id"]
    again = client.post(
        f"/api/live/agent/worlds/{fixture.WORLD}/conversation/new",
        json=frozen["new_conversation_command"],
    )
    require(
        again.status_code == 200 and again.json() == started.json(),
        "exact conversation command replay differs",
    )
    immutable_save(
        evidence,
        "provider-operation-intent",
        {
            "request": frozen["question_request"],
            "auth": "controlled_local_operator",
            "no_automatic_redispatch": True,
        },
    )
    response = client.post("/api/live/agent/turn", json=frozen["question_request"])
    immutable_save(
        evidence,
        "answer-http",
        {"status": response.status_code, "body": response.json()},
    )
    turns = service.list_turns(fixture.WORLD, UUID(owned))
    require(len(turns) == 1, "single owned turn missing")
    turn = turns[0].model_dump(mode="json", by_alias=True)
    immutable_save(evidence, "persisted-turn", turn)
    # Always audit rows, even when the provider outcome is interrupted.
    with fixture.readonly(connection["app_dsn"]) as conn:
        old = conn.execute(
            "SELECT row_to_json(c) AS body FROM agent.conversation c WHERE conversation_id=%s",
            (OLD_CONVERSATION,),
        ).fetchone()["body"]
        pointer = conn.execute(
            "SELECT active_conversation_id::text,pointer_revision FROM agent.world_state WHERE world_id=%s",
            (fixture.WORLD,),
        ).fetchone()
        command_receipt = conn.execute(
            "SELECT row_to_json(r) AS body FROM agent.command_receipt r WHERE world_id=%s AND command_id=%s",
            (fixture.WORLD, COMMAND_ID),
        ).fetchone()["body"]
    validate_archive(frozen["old_conversation"], old)
    require(
        pointer == {"active_conversation_id": owned, "pointer_revision": 73},
        "new conversation pointer differs",
    )
    require(
        command_receipt["request_fingerprint"] == request_fingerprint(typed),
        "durable command request binding differs",
    )
    immutable_save(evidence, "conversation-receipt", command_receipt)
    before_reads = row_inventory(connection["app_dsn"])
    deltas = app_conservation(
        current["app_tables"],
        before_reads,
        conversation=owned,
        turn=turn["turn_id"],
        old_conversation=OLD_CONVERSATION,
    )
    require(
        fixture.database_fingerprints(connection["dsn"]) == frozen["native_tables"]
        and fixture.file_fingerprints(files) == frozen["files"],
        "native/files changed during answer",
    )
    immutable_save(
        evidence,
        "conservation",
        {"app_deltas": deltas, "native_unchanged": True, "files_unchanged": True},
    )
    require(
        response.status_code == 200 and turn["status"] == "completed",
        "original writer outcome retained; no redispatch",
    )
    history = client.get(
        f"/api/live/agent/worlds/{fixture.WORLD}/conversation?include_turn_correlation=true"
    )
    immutable_save(
        evidence,
        "history-http",
        {"status": history.status_code, "body": history.json()},
    )
    require(history.status_code == 200, "ordinary history failed")
    reopened = []
    for index in range(len(turn["completion"]["native_clause_citations"])):
        opened = client.get(
            f"/api/live/agent/worlds/{fixture.WORLD}/conversation/turns/{turn['turn_id']}/native-source-clauses/{index}"
        )
        immutable_save(
            evidence,
            "citation-http-" + str(index),
            {"status": opened.status_code, "body": opened.json()},
        )
        require(opened.status_code == 200, "ordinary historical clause opening failed")
        reopened.append(opened.json())
    replay = client.post("/api/live/agent/turn", json=frozen["question_request"])
    immutable_save(
        evidence, "replay-http", {"status": replay.status_code, "body": replay.json()}
    )
    after_replay = service.list_turns(fixture.WORLD, UUID(owned))[0].model_dump(
        mode="json", by_alias=True
    )
    require(replay.status_code == 200, "completed replay failed")
    require(
        row_inventory(connection["app_dsn"]) == before_reads,
        "read/replay changed APP state",
    )
    verdict = require_delivered(
        turn, response.json(), history.json(), reopened, replay.json(), after_replay
    )
    immutable_save(
        evidence,
        "assessment",
        verdict
        | {
            "answer_text": response.json()["answer"]["text"],
            "fixture_publication": "independently_verified_predecessor",
            "full_system_verified": False,
        },
    )
    print(
        json.dumps(
            {
                "status": "selected_subject_http_proof",
                "assessment": verdict,
                "answer_text": response.json()["answer"]["text"],
            }
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clone-root", type=Path, required=True)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--resume-migration", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--provider", action="store_true")
    parser.add_argument("--preflight-sha256")
    args = parser.parse_args(argv)
    root = args.clone_root.resolve(strict=True)
    evidence = root.parent / "native-review-context-v2" / CHECKPOINT
    if args.apply or args.provider:
        require(
            args.apply and args.provider and not args.migrate,
            "explicit apply and provider switches required",
        )
        frozen = json.loads(
            (
                evidence / ("preflight-" + str(args.preflight_sha256) + ".json")
            ).read_text()
        )
        require(
            fixture.digest(frozen) == args.preflight_sha256, "frozen preflight differs"
        )
        require(
            (evidence / "migration-result.json").is_file(),
            "verified migration required before provider",
        )
        apply_answer(root, evidence, frozen)
        return
    current = preflight(root)
    if not args.migrate:
        immutable_save(evidence, "preflight-" + fixture.digest(current), current)
        print(
            json.dumps(
                {
                    "mode": "read_only_preflight",
                    "sha256": fixture.digest(current),
                    "schema": current["schema"],
                    "evidence": str(evidence),
                }
            )
        )
        return
    frozen = json.loads(
        (evidence / ("preflight-" + str(args.preflight_sha256) + ".json")).read_text()
    )
    require(
        fixture.digest(current) == fixture.digest(frozen) == args.preflight_sha256,
        "frozen preflight changed",
    )
    connection, donor, files = fixture.retained_inputs(root)
    if args.resume_migration:
        recorded = json.loads((evidence / "snapshot.json").read_text())
        require(
            recorded["database"] == fixture.APP_DATABASE
            and recorded["readable"] is True
            and fixture.sha((evidence / "app-before.dump").read_bytes())
            == recorded["sha256"],
            "original migration snapshot differs",
        )
        priors = [
            json.loads(path.read_text()) for path in evidence.glob("preflight-*.json")
        ]
        require(
            all(
                old["app_tables"] == current["app_tables"]
                and old["native_tables"] == current["native_tables"]
                and old["files"] == current["files"]
                and old["app_identity"] == current["app_identity"]
                for old in priors
            ),
            "pre-write migration refusal no longer has unchanged authority",
        )
    else:
        snapshot_app(connection, donor, evidence)
    require(
        fixture.digest(preflight(root)) == args.preflight_sha256,
        "boundary changed during snapshot",
    )
    # A subprocess gets only the explicit leased APP target, never native/primary fallback.
    env = dict(os.environ)
    env["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = app_connection_url(
        connection["app_dsn"]
    )
    import sys

    immutable_save(
        evidence,
        "migration-intent",
        {"from": START_SCHEMA, "to": END_SCHEMA, "migrations": current["migrations"]},
    )
    subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "alembic",
            "-c",
            "src/application_state/alembic.ini",
            "upgrade",
            END_SCHEMA,
        ],
        env=env,
        check=True,
    )
    after = row_inventory(connection["app_dsn"])
    migration_conservation(current["app_tables"], after)
    require(
        fixture.database_fingerprints(connection["dsn"]) == current["native_tables"]
        and fixture.file_fingerprints(files) == current["files"],
        "migration unrelated state changed",
    )
    immutable_save(
        evidence,
        "migration-result",
        {
            "schema": END_SCHEMA,
            "app_tables": after,
            "retained_rows_unchanged": True,
            "native_unchanged": True,
            "files_unchanged": True,
        },
    )
    print(
        json.dumps(
            {"mode": "migration_verified", "provider_calls": 0, "schema": END_SCHEMA}
        )
    )


if __name__ == "__main__":
    main()
