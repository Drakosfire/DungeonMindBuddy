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
from time import perf_counter
from uuid import uuid4

from . import q01_native_answer_proof as answer
from . import q01_native_fixture_proof as fixture

AUTHORITY = "52056b8e3bf0ae00558c5cce772281f8f386b93f"
BASE = "958f2bed133687a02976c1cff4ad739603239725"
SOURCE_ACCESS_AUTHORITY = "178f43153e4e13c1444e693a8830d3306fa96ff0"
CASE = "s8-qualified-proposals-v4"
START = "20261029_0093"
END = "20261029_0093"
OUTPUT_RESERVE = 128_000
V2_PREFLIGHT = "237a23221e439102735bccb9d7ffef87c8b89314a724f6a14bd681d79c4f1f63"
V3_PREFLIGHT = "c27c66e4e34b05457c19e4ae41847a12d75c0700fb9c86af0ed3d2602619a557"
GE_REF = "e9366efad89b76ad0a62b1efacb0d8353120af0d"
GE_ROOT = Path(
    "/home/drakosfire/.local/state/dungeonmindbuddy/runtime-dependencies/generationengine-e9366ef"
)
GE_REPOSITORY = Path(
    "/home/drakosfire/Projects/DungeonOverMind/GenerationEngine/GenerationEngine"
)
SDK_ROOT = Path(
    "/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy/.venv/lib/python3.13/site-packages/openai"
)
TABLE = "ingest.statement_proposal_operation"
MIGRATION = (
    "src/application_state/migrations/versions/20261029_0093_statement_proposals.py"
)
require = fixture.require
save = answer.immutable_save


def verify_ge_import(
    import_root=None, *, repository=GE_REPOSITORY, ref=GE_REF, expected_root=GE_ROOT
):
    """Reject the installed fallback, missing files and drift before any action."""
    if import_root is None:
        import generationengine

        import_root = Path(generationengine.__file__).resolve().parents[1]
    actual = Path(import_root).resolve(strict=True)
    require(
        actual == Path(expected_root).resolve(strict=True),
        "actual GenerationEngine import origin differs from declared immutable runtime",
    )
    inventory = fixture.verify_source_tree(
        actual, repository, ref, ("generationengine",)
    )
    return {"actual_import_root": str(actual), **inventory}


def declared_ge_inventory():
    import tomllib

    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    declarations = [
        value
        for value in project["project"]["dependencies"]
        if value.startswith("generationengine[")
    ]
    require(
        len(declarations) == 1 and declarations[0].endswith("@" + GE_REF),
        "declared GenerationEngine pin differs",
    )
    lock = tomllib.loads((root / "uv.lock").read_text())
    packages = [
        value for value in lock["package"] if value["name"] == "generationengine"
    ]
    require(
        len(packages) == 1 and packages[0]["source"]["git"].endswith("#" + GE_REF),
        "locked GenerationEngine pin differs",
    )
    return verify_ge_import()


def verify_sdk_package(
    root, expected, *, version, locked_version, expected_root=SDK_ROOT
):
    root = Path(root).resolve(strict=True)
    require(
        root == Path(expected_root).resolve(strict=True) and version == locked_version,
        "actual OpenAI SDK origin/version differs",
    )
    actual = {}
    for path in root.rglob("*"):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        require(not path.is_symlink(), "SDK package symlink differs")
        if path.is_file():
            actual[path.relative_to(root).as_posix()] = fixture.sha(path.read_bytes())
    require(
        actual == expected and bool(actual),
        "actual SDK package bytes differ from wheel RECORD",
    )
    return {
        "actual_import_root": str(root),
        "version": version,
        "files": len(actual),
        "tree_digest": fixture.digest(actual),
        "expected_hash_authority": "installed wheel RECORD, version pinned by uv.lock",
    }


def declared_sdk_inventory():
    import base64
    from importlib.metadata import distribution
    import openai
    import tomllib

    root = Path(__file__).resolve().parents[2]
    lock = tomllib.loads((root / "uv.lock").read_text())
    packages = [p for p in lock["package"] if p["name"] == "openai"]
    require(len(packages) == 1, "locked SDK package is ambiguous")
    dist = distribution("openai")
    require(
        dist.version == openai.__version__, "SDK module/distribution version differs"
    )
    expected = {}
    for file in dist.files:
        name = str(file)
        if (
            not name.startswith("openai/")
            or "__pycache__" in file.parts
            or name.endswith(".pyc")
        ):
            continue
        require(
            file.hash is not None and file.hash.mode == "sha256",
            "SDK wheel file lacks SHA256",
        )
        expected[name.removeprefix("openai/")] = base64.urlsafe_b64decode(
            file.hash.value + "=" * (-len(file.hash.value) % 4)
        ).hex()
    result = verify_sdk_package(
        Path(openai.__file__).resolve().parent,
        expected,
        version=openai.__version__,
        locked_version=packages[0]["version"],
    )
    return result | {
        "wheel_record_sha256": fixture.sha(dist.read_text("RECORD").encode())
    }


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
    """Historical producer prerequisite; retained to prove the original refusal."""
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


def assert_source_inspection(opened):
    require(opened.status == "available", "native source unavailable")
    raw = opened.body_text.encode()
    require(
        len(raw) == 6172 and fixture.sha(raw) == fixture.BODY_SHA,
        "exact S8 source body differs",
    )
    start, end = opened.span_start_byte, opened.span_end_byte
    require(
        0 <= start < end <= len(raw)
        and fixture.sha(raw[start:end]) == opened.span_sha256,
        "registered source anchor differs",
    )
    return {"start_byte": start, "end_byte": end, "span_sha256": opened.span_sha256}


def verify_eligibility(record, extent):
    expected = {}
    if record["result"] is not None:
        for key, location in record["result"]["locations"].items():
            matches = [
                {
                    **match,
                    "eligibility": "eligible_for_review"
                    if extent["start_byte"]
                    <= match["start_byte"]
                    < match["end_byte"]
                    <= extent["end_byte"]
                    else "outside_registered_evidence",
                }
                for match in location["matches"]
            ]
            expected[key] = {
                "status": "ambiguous"
                if len(matches) != 1
                else matches[0]["eligibility"],
                "matches": matches,
                "semantic_acceptance": "not_established",
            }
    require(
        record.get("review_eligibility") == expected,
        "host review eligibility differs from actual registered span",
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
            added = new - old
            rows = [row for row in after[table] if row["sha256"] in added]
            require(
                len(rows) == 1
                and rows[0]["keys"].get("operation_id") == operation
                and rows[0]["keys"].get("world_id") == fixture.WORLD,
                "new proposal row is not the authorized operation/World",
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
        and body["model"] == "gpt-6-luna"
        and body.get("max_output_tokens") == OUTPUT_RESERVE,
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


def verify_stored_operation(row, record):
    require(
        row is not None
        and row["operation_id"] == record["operation_id"]
        and row["owner"] == record["owner"]
        and row["world_id"] == fixture.WORLD,
        "actual stored operation identity differs",
    )
    expected = {
        key: value for key, value in record.items() if key != "review_eligibility"
    }
    require(
        row["payload"] == expected,
        "actual stored operation payload differs from readback",
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


def instruction_contrast(current_wire, old_wire):
    from graph_memory.extraction.qualified_statement_proposals import (
        strict_json,
        INSTRUCTIONS,
    )

    old, current = strict_json(old_wire), strict_json(current_wire)
    require(
        old.get("max_output_tokens") == OUTPUT_RESERVE, "v3 capacity baseline differs"
    )
    require(
        old.get("instructions") != INSTRUCTIONS,
        "v4 must use the delivered literal-copy instruction change",
    )
    require(
        current == old | {"instructions": INSTRUCTIONS},
        "literal-copy experiment changed something besides declared instructions",
    )


def row_inventory(dsn):
    """One repeatable-read snapshot, retaining exact operation identity too."""
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
                            key: body[key]
                            for key in (
                                "world_id",
                                "operation_id",
                                "conversation_id",
                                "turn_id",
                                "command_id",
                                "reference_role",
                                "ordinal",
                                "version_num",
                            )
                            if key in body
                        },
                    }
                )
            result[name] = sorted(inventory, key=lambda row: row["sha256"])
    return result


def capture(root):
    connection, donor, files = fixture.retained_inputs(root)
    return {
        "app": row_inventory(connection["app_dsn"]),
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
                "s8-qualified-proposals-v1",
                "s8-qualified-proposals-v2",
                "s8-qualified-proposals-v3",
            )
        },
    }


def unchanged(before, after):
    for key in ("native", "files", "prior_evidence"):
        require(before[key] == after[key], "read-only state changed: " + key)


def preflight(root, receipt_path, schema=START):
    ge = declared_ge_inventory()
    sdk = declared_sdk_inventory()
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
    dependencies["generationengine"] = ge
    dependencies["openai_sdk"] = sdk
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
    extent = assert_source_inspection(opened)
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
    v2_case = root.parent / "native-review-context-v2/s8-qualified-proposals-v2"
    previous = json.loads(
        (v2_case / ("preflight-" + V2_PREFLIGHT + ".json")).read_text()
    )
    require(
        fixture.digest(previous) == V2_PREFLIGHT and packet == previous["input"],
        "v4 source/context/model schema input differs from frozen v2",
    )
    previous_v3 = json.loads(
        (
            root.parent
            / "native-review-context-v2/s8-qualified-proposals-v3"
            / ("preflight-" + V3_PREFLIGHT + ".json")
        ).read_text()
    )
    require(
        fixture.digest(previous_v3) == V3_PREFLIGHT and packet == previous_v3["input"],
        "v4 source/context/model schema input differs from frozen v3",
    )
    budget = service._producer_budget()
    require(
        budget["outputReserveTokens"] == OUTPUT_RESERVE,
        "producer output capacity differs",
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
        "source_access_authority": SOURCE_ACCESS_AUTHORITY,
        "base": BASE,
        "harness_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "harness_sha256": fixture.sha(Path(__file__).read_bytes()),
        "runtime": runtime_inventory(),
        "dependencies": dependencies,
        "schema": schema,
        "receipt": receipt,
        "registered_extent": extent,
        "producer_budget": budget,
        "v2_preflight_sha256": V2_PREFLIGHT,
        "v3_preflight_sha256": V3_PREFLIGHT,
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
    p.add_argument("--snapshot", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--provider", action="store_true")
    args = p.parse_args(argv)
    declared_ge_inventory()
    declared_sdk_inventory()
    root = args.clone_root.resolve(strict=True)
    case = root.parent / "native-review-context-v2" / CASE
    if not (args.snapshot or args.apply or args.provider):
        require(not case.exists(), "fresh assessment case required")
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
    if args.snapshot:
        require(
            not args.apply and not args.provider,
            "snapshot and provider must be separate",
        )
        freeze_matches(preflight(root, args.source_receipt), frozen)
        answer.snapshot_app(connection, donor, case)
        freeze_matches(preflight(root, args.source_receipt), frozen)
        after = preflight(root, args.source_receipt, END)
        freeze_matches(after, frozen)
        save(
            case,
            "snapshot-result",
            {"schema": END, "state": after["state"], "migration_executed": False},
        )
        print(
            json.dumps(
                {
                    "schema": END,
                    "original_rows_preserved": True,
                    "migration_executed": False,
                }
            )
        )
        return
    require(args.apply and args.provider, "explicit apply and provider required")
    require(
        not (case / "provider-intent.json").exists(),
        "original operation retained; no redispatch",
    )
    require((case / "snapshot-result.json").is_file(), "verified snapshot required")
    freeze_matches(preflight(root, args.source_receipt, END), frozen)
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
        post_dependencies = {
            "generationengine": declared_ge_inventory(),
            "openai_sdk": declared_sdk_inventory(),
        }
        save(case, "post-provider-dependencies", post_dependencies)
        require(
            all(
                post_dependencies[key] == frozen["dependencies"][key]
                for key in post_dependencies
            ),
            "provider dependency identity changed during the operation",
        )
        old_wire = json.loads(
            (
                root.parent
                / "native-review-context-v2/s8-qualified-proposals-v3/operation.json"
            ).read_text()
        )["wire"]
        instruction_contrast(record["wire"], old_wire)
        save(
            case,
            "instruction-contrast",
            {
                "only_wire_change": "instructions",
                "output_reserve_unchanged": OUTPUT_RESERVE,
                "v3_preflight_sha256": V3_PREFLIGHT,
            },
        )
        with fixture.readonly(connection["app_dsn"]) as conn:
            stored = conn.execute(
                "SELECT operation_id::text,owner,world_id,payload FROM ingest.statement_proposal_operation WHERE operation_id=%s",
                (frozen["request"]["operation_id"],),
            ).fetchone()
        save(case, "stored-operation", stored)
        verify_stored_operation(stored, record)
        verify_record(
            record, frozen["request"], frozen["input"]["source"], frozen["input"]
        )
        verify_eligibility(record, frozen["registered_extent"])
        verify_sdk_output(record, observed)
        before = capture(root)
        unchanged(frozen["state"], before)
        app_conservation(
            json.loads((case / "snapshot-result.json").read_text())["state"]["app"],
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
