"""Independent real-S8 extraction assessment; ordinary reads are provider-free.

Only the leased disposable APP may change. Native/source/evidence state is read
only. A failed source preflight never migrates APP or dispatches a provider.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from functools import wraps
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from uuid import uuid4

from . import q01_native_answer_proof as answer
from . import q01_native_fixture_proof as fixture

AUTHORITY = "94d3a8557a77fcd6fe0c33a4f37d6979894438c5"
BASE = "d479bf566866c3e2171eb47d052dae8a683e11f5"
CASE = "s8-qualified-proposals-v1"
START = "20261029_0092"
END = "20261029_0093"
TABLE = "ingest.statement_proposal_operation"
MIGRATION = (
    "src/application_state/migrations/versions/20261029_0093_statement_proposals.py"
)
require = fixture.require
save = answer.immutable_save


class SourcePrerequisiteError(ValueError):
    pass


@contextmanager
def observe_sdk():
    """Observe the real SDK method; forward every argument/result unchanged."""
    from openai.resources.responses.responses import AsyncResponses
    from unittest.mock import patch

    original = AsyncResponses.create
    observed = {"sdk_entries": 0, "responses": [], "errors": []}

    @wraps(original)
    async def create(self, *args, **kwargs):
        observed["sdk_entries"] += 1
        try:
            response = await original(self, *args, **kwargs)
        except Exception as exc:
            observed["errors"].append(type(exc).__name__)
            raise
        observed["responses"].append(response.model_dump(mode="json"))
        return response

    with patch.object(AsyncResponses, "create", create):
        yield observed


def assert_whole_source(opened):
    require(opened.status == "available", "native source unavailable")
    raw = opened.body_text.encode()
    require(
        len(raw) == 6172 and fixture.sha(raw) == fixture.BODY_SHA,
        "exact S8 source body differs",
    )
    if opened.span_start_byte != 0 or opened.span_end_byte != len(raw):
        raise SourcePrerequisiteError(
            "whole-source admission missing: available body is not full-span authority"
        )


def verify_sdk_output(record, observed):
    require(observed["sdk_entries"] == 1, "exactly one actual SDK entry required")
    if record["state"] != "completed":
        return
    require(
        len(observed["responses"]) == 1 and not observed["errors"],
        "completion has no unique actual SDK response",
    )
    response = observed["responses"][0]
    require(response["status"] == "completed", "actual SDK output incomplete")
    messages = [item for item in response["output"] if item["type"] == "message"]
    finals = [item for item in messages if item.get("phase") == "final_answer"]
    selected = finals or [item for item in messages if item.get("phase") is None]
    require(len(selected) == 1, "ambiguous actual SDK final message")
    message = selected[0]
    require(
        message["role"] == "assistant"
        and message["status"] == "completed"
        and all(part["type"] == "output_text" for part in message["content"]),
        "actual SDK final contains unsupported content",
    )
    require(
        "".join(part["text"] for part in message["content"]) == record["raw_output"],
        "retained proposal text differs from actual SDK output",
    )


def app_conservation(before, after, *, migrated=False, operation=None):
    expected = set(before) | ({TABLE} if migrated else set())
    require(set(after) == expected, "unexpected APP table delta")
    for table in expected:
        if table == "application_state.schema_migrations" and migrated:
            require(
                len(after[table]) == 1
                and after[table][0]["keys"].get("version_num") == END,
                "schema migration target differs",
            )
        elif table == TABLE and operation is not None:
            old, new = (
                Counter(r["sha256"] for r in before.get(table, [])),
                Counter(r["sha256"] for r in after[table]),
            )
            require(
                not old - new and sum((new - old).values()) == 1,
                "only one new proposal operation is allowed",
            )
        else:
            require(
                before.get(table, []) == after[table],
                "retained APP rows changed: " + table,
            )


def verify_record(record, request, source, packet):
    """Validate actual retained input/output, not an HTTP success flag."""
    from graph_memory.extraction.qualified_statement_proposals import (
        INSTRUCTIONS,
        digest,
        parse,
        strict_json,
    )

    require(
        record["intent"] == request
        and record["operation_id"] == request["operation_id"],
        "persisted operation identity differs",
    )
    require(
        record["owner"] == "local_operator"
        and record["intent_digest"] == digest(request),
        "operation owner/intent differs",
    )
    require(
        record["input"] == packet and packet["source"] == source,
        "actual source/context input differs",
    )
    require(not record["reviews"], "extraction assessment cannot select or prepare")
    wire = record["wire"]
    require(
        wire is not None and fixture.sha(wire.encode()) == record["wire_digest"],
        "actual prepared wire missing or changed",
    )
    body = strict_json(wire)
    require(
        body["input"] == [{"role": "user", "content": fixture.canonical(packet)}]
        and body["instructions"] == INSTRUCTIONS
        and not body.get("tools")
        and body["model"] == "gpt-6-luna",
        "provider input differs",
    )
    outcomes = [e["outcome"] for e in record["lifecycle"]]
    require(
        outcomes
        in [
            ["sending", "response_received"],
            ["sending", "outcome_unknown"],
            ["sending", "known_not_sent"],
            ["known_not_sent"],
        ],
        "dispatch lifecycle is not one retained operation",
    )
    if record["state"] == "completed":
        require(
            outcomes == ["sending", "response_received"] and record["failure"] is None,
            "completion lacks actual response",
        )
        require(
            record["result"] == parse(record["raw_output"], source),
            "retained parsed output differs",
        )
    else:
        require(
            record["state"] == "failed" and record["result"] is None,
            "unknown or failed output cannot count as completed extraction",
        )


def runtime_inventory(root=None, ref=BASE):
    """Every runtime package byte, including untracked files, must match base."""
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    result = {}
    for folder in ("apps/live_control_server", "src"):
        entries = subprocess.check_output(
            ["git", "ls-tree", "-rz", ref, "--", folder], cwd=root
        )
        expected = {}
        for entry in entries.split(b"\0"):
            if entry:
                meta, path = entry.split(b"\t", 1)
                mode, kind, oid = meta.decode().split()
                require(
                    kind == "blob" and mode in {"100644", "100755"},
                    "runtime contains unsupported entry",
                )
                expected[path.decode()] = oid
        actual = {}
        import hashlib

        for path in (root / folder).rglob("*"):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            require(not path.is_symlink(), "runtime symlink differs")
            if path.is_file():
                raw = path.read_bytes()
                actual[path.relative_to(root).as_posix()] = hashlib.sha1(
                    b"blob " + str(len(raw)).encode() + b"\0" + raw
                ).hexdigest()
        require(actual == expected, "actual runtime bytes differ: " + folder)
        result[folder] = {"files": len(actual), "digest": fixture.digest(actual)}
    return result


def capture(root):
    connection, donor, files = fixture.retained_inputs(root)
    return {
        "app": answer.row_inventory(connection["app_dsn"]),
        "native": fixture.database_fingerprints(connection["dsn"]),
        "files": fixture.file_fingerprints(files),
        "prior_evidence": {
            name: fixture.file_fingerprints(
                root.parent / "native-review-context-v2" / name
            )
            for name in (
                "q01-fullworld-v1",
                "q01-fullworld-profile2-v1",
                "q01-native-answer-v1",
                "q01-native-answer-v2",
            )
        },
    }


def unchanged(before, after):
    for key in ("native", "files", "prior_evidence"):
        require(before[key] == after[key], "read-only state changed: " + key)


def preflight(root, receipt_path, schema=START):
    import dungeonmind
    import worldkeeper
    from psycopg.conninfo import make_conninfo
    from dungeonmind.application.vnext import open_admitted_native_text

    connection, donor, files = fixture.retained_inputs(root)
    for native, key, database in (
        (True, "dsn", fixture.DATABASE),
        (False, "app_dsn", fixture.APP_DATABASE),
    ):
        answer.validate_identity(
            fixture.check_server(connection[key], database, donor), native
        )
    os.environ["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = (
        answer.app_connection_url(connection["app_dsn"])
    )
    os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = (
        answer.app_connection_url(
            make_conninfo(
                connection["dsn"], options="-c default_transaction_read_only=on"
            )
        )
    )
    os.environ["DMB_MANAGED_WORLD_DATA_ROOT"] = str(files)
    core = Path(dungeonmind.__file__).resolve().parents[1]
    require(core == fixture.CORE_ROOT / "src", "actual Core import differs")
    dependencies = {
        "core": fixture.verify_source_tree(
            core,
            fixture.CORE_ROOT,
            fixture.CORE_REF,
            ("dungeonmind", "dungeonmind_dnd"),
        )
    }
    wk = Path(worldkeeper.__file__).resolve().parents[1]
    dependencies["wk"] = fixture.verify_source_tree(
        wk, wk.parent, "a30ee81ae0e777037c68afea8847b04a2c736ae1", ("worldkeeper",)
    )
    from apps.live_control_server.services import source_statement_proposals as service
    from apps.live_control_server.models.source_statement_proposals import (
        ProposalRequest,
    )
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal

    repo = service.statements.native.repository()
    require(
        repo.get_head(fixture.WORLD).head_revision_id == answer.READ_REVISION,
        "native assessment revision differs",
    )
    receipt = json.loads(receipt_path.read_text())
    actual = repo.get_native_source_admission_receipt(
        fixture.WORLD, receipt["admission_id"]
    )
    from fastapi.encoders import jsonable_encoder

    require(
        jsonable_encoder(actual) == receipt,
        "retained admission receipt differs from native authority",
    )
    require(len(receipt["bindings"]) == 1, "select explicit whole-source binding")
    evidence = receipt["bindings"][0]["evidence_ref_id"]
    _, access, _, _ = service.statements._context(
        repo, fixture.WORLD, answer.READ_REVISION, fixture.CAMPAIGN
    )
    opened = open_admitted_native_text(access, evidence)
    assert_whole_source(opened)
    request = ProposalRequest(
        operation_id=uuid4(),
        managed_world_id=fixture.WORLD,
        campaign_id=fixture.CAMPAIGN,
        read_revision_id=answer.READ_REVISION,
        source_admission_id=receipt["admission_id"],
        evidence_ref_id=evidence,
        source_sha256=fixture.BODY_SHA,
    )
    _, _, packet = service.source(
        request, NativeGraphPrincipal("local_operator", "gm", "local_operator")
    )
    with fixture.readonly(connection["app_dsn"]) as conn:
        require(
            conn.execute(
                "SELECT version_num FROM application_state.schema_migrations"
            ).fetchone()["version_num"]
            == schema,
            "APP schema differs",
        )
        # Exact retained APP source version, not only a file of the same name.
        row = conn.execute(
            "SELECT a.world_id,a.campaign_id,a.session_id,r.content_sha256,r.markdown "
            "FROM source.revision r JOIN source.artifact a USING(source_artifact_id) "
            "WHERE r.source_revision_id=%s AND a.source_artifact_id=%s",
            (fixture.APP_REVISION, fixture.APP_ARTIFACT),
        ).fetchone()
    require(
        row is not None
        and row["world_id"] is None
        and row["campaign_id"] == fixture.CAMPAIGN
        and row["session_id"] == "session-8"
        and row["content_sha256"] == fixture.BODY_SHA
        and row["markdown"] == opened.body_text,
        "retained APP source version differs",
    )
    require(
        (files / fixture.SOURCE_PATH).read_bytes() == opened.body_text.encode(),
        "file/source body differs",
    )
    return {
        "authority": AUTHORITY,
        "base": BASE,
        "harness_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "harness_sha256": fixture.sha(Path(__file__).read_bytes()),
        "runtime": runtime_inventory(),
        "dependencies": dependencies,
        "schema": schema,
        "receipt": receipt,
        "request": request.model_dump(mode="json"),
        "input": packet,
        "state": capture(root),
    }


def freeze_matches(current, frozen, *, migrated=False):
    for key in frozen:
        if key in {"request", "schema", "state"}:
            continue
        require(current[key] == frozen[key], "frozen boundary changed: " + key)
    unchanged(frozen["state"], current["state"])
    app_conservation(frozen["state"]["app"], current["state"]["app"], migrated=migrated)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--clone-root", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--preflight-sha256")
    p.add_argument("--migrate", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--provider", action="store_true")
    args = p.parse_args(argv)
    root = args.clone_root.resolve(strict=True)
    case = root.parent / "native-review-context-v2" / CASE
    if not (args.migrate or args.apply or args.provider):
        require(
            not case.exists()
            or {path.name for path in case.iterdir()}
            == {"preflight-source-span-refusal.json"},
            "fresh assessment output required; only the original source refusal may precede it",
        )
        before = capture(root)
        try:
            result = preflight(root, args.source_receipt)
        except SourcePrerequisiteError as exc:
            after = capture(root)
            require(before == after, "read-only source refusal changed state")
            save(
                case,
                "preflight-source-span-refusal",
                {
                    "authority": AUTHORITY,
                    "runtime_base": BASE,
                    "harness_sha256": fixture.sha(Path(__file__).read_bytes()),
                    "source_receipt": json.loads(args.source_receipt.read_text()),
                    "error": str(exc),
                    "state": before,
                    "state_unchanged": True,
                    "provider_calls": 0,
                    "migration_executed": False,
                },
            )
            print(
                json.dumps(
                    {
                        "status": "source_prerequisite_refused",
                        "provider_calls": 0,
                        "migration_executed": False,
                    }
                )
            )
            return
        save(case, "preflight-" + fixture.digest(result), result)
        print(
            json.dumps(
                {"preflight_sha256": fixture.digest(result), "mode": "read_only"}
            )
        )
        return
    frozen = json.loads(
        (case / ("preflight-" + str(args.preflight_sha256) + ".json")).read_text()
    )
    require(fixture.digest(frozen) == args.preflight_sha256, "preflight digest differs")
    connection, donor, _ = fixture.retained_inputs(root)
    if args.migrate:
        require(
            not args.apply and not args.provider,
            "migration and provider must be separate",
        )
        freeze_matches(preflight(root, args.source_receipt), frozen)
        answer.snapshot_app(connection, donor, case)
        freeze_matches(preflight(root, args.source_receipt), frozen)
        save(case, "migration-intent", {"from": START, "to": END})
        env = dict(os.environ)
        env["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = answer.app_connection_url(
            connection["app_dsn"]
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
                END,
            ],
            env=env,
            check=True,
        )
        after = preflight(root, args.source_receipt, END)
        freeze_matches(after, frozen, migrated=True)
        save(case, "migration-result", {"schema": END, "state": after["state"]})
        print(json.dumps({"schema": END, "original_rows_preserved": True}))
        return
    require(args.apply and args.provider, "explicit apply and provider required")
    require(
        not (case / "provider-intent.json").exists(),
        "original operation retained; no redispatch",
    )
    require((case / "migration-result.json").is_file(), "verified migration required")
    freeze_matches(preflight(root, args.source_receipt, END), frozen, migrated=True)
    _, _, _, token = answer.configure_operation(root, case)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes.source_statements import router

    app = FastAPI()
    app.include_router(router)
    save(
        case,
        "provider-intent",
        {
            "request": frozen["request"],
            "input_digest": fixture.digest(frozen["input"]),
            "no_automatic_redispatch": True,
        },
    )
    with (
        observe_sdk() as observed,
        TestClient(
            app,
            client=("127.0.0.1", 42000),
            headers={"Authorization": "Bearer " + token},
        ) as client,
    ):
        started = perf_counter()
        response = client.post(
            "/api/live/source-statements/proposals", json=frozen["request"]
        )
        save(
            case,
            "produce-http",
            {
                "status": response.status_code,
                "body": response.json(),
                "elapsed_ms": (perf_counter() - started) * 1000,
            },
        )
        save(case, "sdk-observation", observed)
        save(case, "post-operation-state", capture(root))
        require(
            response.status_code == 200,
            "ordinary producer refused; retain original response",
        )
        record = response.json()
        save(case, "operation", record)
        verify_record(
            record, frozen["request"], frozen["input"]["source"], frozen["input"]
        )
        verify_sdk_output(record, observed)
        before = capture(root)
        unchanged(frozen["state"], before)
        app_conservation(
            json.loads((case / "migration-result.json").read_text())["state"]["app"],
            before["app"],
            operation=record["operation_id"],
        )
        url = (
            "/api/live/source-statements/proposals/"
            + record["operation_id"]
            + "?managed_world_id="
            + fixture.WORLD
        )
        read = client.get(url)
        replay = client.post(
            "/api/live/source-statements/proposals", json=frozen["request"]
        )
        save(
            case,
            "read-replay",
            {
                "read_status": read.status_code,
                "read": read.json(),
                "replay_status": replay.status_code,
                "replay": replay.json(),
            },
        )
        require(
            read.status_code == replay.status_code == 200
            and read.json() == replay.json() == record,
            "ordinary reload/replay changed original operation",
        )
        require(
            capture(root) == before, "replay changed persisted state or added lifecycle"
        )
        require(
            observed == json.loads((case / "sdk-observation.json").read_text()),
            "reload/replay added actual provider IO",
        )
    save(
        case,
        "conservation",
        {
            "read_only_state_preserved": True,
            "one_new_operation": True,
            "replay_added_lifecycle": 0,
        },
    )
    save(
        case,
        "run-observation",
        {
            "runtime_base": BASE,
            "authority": AUTHORITY,
            "source_sha256": fixture.BODY_SHA,
            "native_revision": answer.READ_REVISION,
            "operation_id": record["operation_id"],
            "state": record["state"],
            "proposal_count": len(record["result"]["batch"]["proposals"])
            if record["result"]
            else 0,
            "source_availability": {"met": 1, "assessed": 1},
            "semantic_assessment": "pending independent inspection of every proposal",
            "question_stages": {
                q: {
                    "extraction": "unassessed",
                    "identity": "unassessed",
                    "selection": "not executed",
                    "publication": "not executed",
                    "discovery": "not executed",
                    "composition": "not executed",
                    "delivery": "not executed",
                }
                for q in ("Q01", "Q13")
            },
            "original_full_system": {"verified": 0, "questions": 15},
            "next_owner_action": "ADVERSARY inspect every actual proposal against source before any selection",
        },
    )
    print(
        json.dumps(
            {
                "state": record["state"],
                "operation_id": record["operation_id"],
                "evidence": str(case),
            }
        )
    )


if __name__ == "__main__":
    main()
