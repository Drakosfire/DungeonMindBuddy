"""Guarded, provider-free Q01 proof in the explicitly leased existing clone.

CLI defaults to read-only preflight. No primary/donor/APP/classic writes, no
new database or service, no automatic rollback. Apply requires the exact frozen
preflight digest. A manual fixture is not an extraction or answer-quality pass.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from .source_statement_capture_v2 import (
    canonical,
    digest,
    capture_native_lifecycle,
    evaluate_lifecycle,
)

WORLD = "elderwyld"
CAMPAIGN = "longmont-c1"
DATABASE = "benchmark_ingestion_native_e785f5a2e2"
APP_DATABASE = "benchmark_ingestion_app_e785f5a2e2"
INITIAL_HEAD = "rev:dfbd4025e3638a751afd276c511fe3e4"
SYSTEM_ID = "7701521766801596454"
CONTROL_HEAD = "066c22165e7d1817d35563380bb76151ee544b06"
SIGNING_KEY = "native-review-context-v2/dossier-standing-v1/test-signing-key"
BODY_SHA = "a5a1a534941b01c3a5b422a9b0f0504d309c6eb06da2a485454c027f265c7ac1"
CLAUSE_SHA = "3256990becae288400b705809901d258a074dcce39313fb6d3d236cc4ba93cb2"
APP_ARTIFACT = "artifact:recap:longmont-c1:session-8:a5a1a534941b"
APP_REVISION = "2db415b4-b14c-492c-adab-3c738f97a241"
QUOTE = "An arcana check reveals the meat to be from another plane of existence."
SOURCE_PATH = (
    "out/registries/source_content/recap/longmont-c1/session-8/" + BODY_SHA + ".md"
)
NOW = datetime(2026, 10, 29, tzinfo=UTC)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def supports_statement_kernel(profile):
    return any(
        rule.namespace == "dungeonbuddy.custom"
        and "entity_ref" in rule.allowed_value_kinds
        for rule in getattr(profile, "open_predicate_namespaces", [])
    )


def validate_source(body, body_sha=BODY_SHA, start=4868, end=4939):
    require(sha(body) == body_sha, "source body changed")
    require(body[start:end] == QUOTE.encode(), "reviewed Q01 clause changed")
    require(body.count(QUOTE.encode()) == 1, "ambiguous Q01 clause")
    return {
        "body_sha256": body_sha,
        "start_byte": start,
        "end_byte": end,
        "clause_sha256": sha(body[start:end]),
    }


def validate_connected(identity, expected_database, expected_system=SYSTEM_ID):
    require(
        identity["database"] == expected_database,
        "connected database differs from lease",
    )
    require(
        identity["system_identifier"] == expected_system,
        "connected PostgreSQL server differs from retained clone",
    )
    require(
        identity["server_address"].split("/")[0] == "172.17.0.5"
        and identity["server_port"] == 5432,
        "connected server endpoint differs from retained clone",
    )


def identity(conn):
    row = conn.execute(
        "SELECT current_database() AS database, inet_server_addr()::text AS server_address, "
        "inet_server_port() AS server_port, system_identifier::text, "
        "(SELECT oid::text FROM pg_database WHERE datname=current_database()) AS database_oid FROM pg_control_system()"
    ).fetchone()
    return dict(row)


@contextmanager
def readonly(dsn):
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(
        dsn, options="-c default_transaction_read_only=on", row_factory=dict_row
    ) as conn:
        yield conn


def database_fingerprints(dsn):
    """Record logical rows, preserving multiplicity without copying story rows."""
    from psycopg import sql

    tables = {}
    with readonly(dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        names = conn.execute(
            "SELECT table_schema,table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') "
            "ORDER BY table_schema,table_name"
        ).fetchall()
        for name in names:
            schema, table = name["table_schema"], name["table_name"]
            rows = conn.execute(
                sql.SQL("SELECT row_to_json(t)::text AS body FROM {}.{} t").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
            ).fetchall()
            hashes = sorted(sha(r["body"].encode()) for r in rows)
            owners = {
                sha(r["body"].encode()): json.loads(r["body"]).get(
                    "space_id", json.loads(r["body"]).get("world_id")
                )
                for r in rows
            }
            tables[schema + "." + table] = {
                "count": len(hashes),
                "sha256": digest(hashes),
                "row_hashes": hashes,
                "owners": owners,
            }
    return tables


def file_fingerprints(root):
    return {
        str(p.relative_to(root)): sha(p.read_bytes())
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def reviewed_selection(world, parent, source, meat_id, pins):
    """The reviewed meaning is frozen independently of generated output."""
    from apps.live_control_server.models.source_statements import StatementSelection

    return StatementSelection(
        managed_world_id=world,
        campaign_id=CAMPAIGN,
        expected_parent_revision_id=parent,
        source_admission_id=source.admission_id,
        evidence_ref_id=source.bindings[0].evidence_ref_id,
        source_sha256=pins["body_sha256"],
        start_byte=pins["start_byte"],
        end_byte=pins["end_byte"],
        clause_sha256=pins["clause_sha256"],
        meaning=QUOTE,
        mode="narrator",
        reporter=None,
        referents=[meat_id],
        uncertainty=[],
        qualifications={
            "source_section": "Recap",
            "basis": "narrated Arcana check",
            "plane_identity": "unnamed",
        },
        episode="session-8:meat-arcana-check",
        source_order=[],
        embedded_content_factive=False,
    )


def frozen_payload(selection, world, origin, source, meat_id, pins):
    fields = selection.model_dump(mode="json")
    return {
        "schema": "dmb_source_statement_v1",
        "clause": {
            "world": world,
            "campaign": CAMPAIGN,
            "logical_source": {
                "namespace": origin.namespace,
                "object_id": origin.object_id,
            },
            "source_sha256": pins["body_sha256"],
            "start_byte": pins["start_byte"],
            "end_byte": pins["end_byte"],
            "clause_sha256": pins["clause_sha256"],
        },
        "quote": QUOTE,
        **{
            k: fields[k]
            for k in (
                "meaning",
                "mode",
                "reporter",
                "referents",
                "uncertainty",
                "qualifications",
                "episode",
                "source_order",
                "embedded_content_factive",
                "assertion_target",
            )
        },
        "visibility": "gm",
        "proof": {
            "source_admission_id": source.admission_id,
            "evidence_ref_id": source.bindings[0].evidence_ref_id,
        },
    }


def execute_native_proof(repo, body, pins, binding, save, initial_head=INITIAL_HEAD):
    """Only exported governed source/WK APIs and merged signed statement service.

    ``save`` durably checkpoints original requests/packets before their calls.
    Unknown outcomes leave those artifacts intact. The caller must not rerun
    from a new identity or rewind the retained native head.
    """
    from fastapi.encoders import jsonable_encoder
    from dungeonmind.application.vnext import publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.native_source import (
        NativeTextSourceAdmissionV1,
        NativeTextSourceOriginV1,
        NativeTextEvidenceSpanRequestV1,
    )
    from graph_memory.vnext.domain_runtime import (
        CAMPAIGN_SCOPE_AXIS,
        GM_LABEL,
    )
    from worldkeeper.application import contracts as wk
    from apps.live_control_server.integrations.worldkeeper import (
        registry_standing_consumer as transport,
    )
    from apps.live_control_server.services import source_statements as statements
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.models.source_statements import ConfirmStatement
    from unittest.mock import patch

    world = binding["native_world_id"]
    require(
        repo.get_head(world).head_revision_id == initial_head,
        "native head changed before source admission",
    )
    before = deepcopy(repo.get_revision(world, initial_head).graph_payload)
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        descriptors,
    )

    domain, profile = descriptors(repo, world, initial_head)
    require(
        supports_statement_kernel(profile),
        "current native parent cannot admit statement kernel; governed descriptor transition required",
    )
    origin = NativeTextSourceOriginV1(
        namespace="dungeonbuddy.benchmark.q01-app-version-bridge:v1",
        object_id=canonical(
            {
                "artifact": APP_ARTIFACT,
                "app_revision": APP_REVISION,
                "body_sha256": pins["body_sha256"],
            }
        ),
        revision_id=pins["body_sha256"],
    )
    request = NativeTextSourceAdmissionV1(
        space_id=world,
        admission_id="q01-fixture-source:v1:"
        + digest({"world": world, "origin": origin.model_dump(mode="json")}),
        expected_parent_revision_id=initial_head,
        created_at=NOW,
        body_text=body.decode(),
        expected_body_sha256=pins["body_sha256"],
        source_classification="dungeonbuddy.source:session_recap",
        authority="primary",
        visibility={"kind": "labels_any", "labels": [GM_LABEL]},
        origin=origin,
        spans=[
            NativeTextEvidenceSpanRequestV1(
                client_ref="q01-clause",
                evidence_role="support",
                start_byte=pins["start_byte"],
                end_byte=pins["end_byte"],
                expected_slice_sha256=pins["clause_sha256"],
            )
        ],
    )
    save(
        "source-request",
        {k: v for k, v in request.model_dump(mode="json").items() if k != "body_text"},
    )
    source = publish_native_text_source_evidence(
        repository=repo,
        domain_contract=domain,
        semantic_profile=profile,
        request=request,
    )
    save("source-receipt", jsonable_encoder(source))
    meta = wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, CAMPAIGN),),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        evidence_ref_ids=(source.bindings[0].evidence_ref_id,),
        temporal_scope=wk.TemporalScope(kind="unknown"),
    )
    runtime = transport.runtime(
        repo,
        domain,
        profile,
        now=NOW,
        operation_id="q01-fixture-meat:v1:" + digest(origin.model_dump(mode="json")),
    )
    intent = wk.WorldChangeIntent(
        world,
        "dungeonbuddy:reviewed-q01-fixture-v1",
        (
            wk.CreateObject(
                "meat",
                (
                    wk.CreateFact(
                        "meat-name", "dnd5e:name", wk.LiteralFactValue("meat"), meta
                    ),
                ),
            ),
        ),
    )
    prepared_identity = runtime.prepare_change(intent)
    save("identity-prepared", transport.encode_prepared(prepared_identity))
    identity_result = runtime.commit_prepared_change(
        prepared_identity, confirmed_by="benchmark-q01-reviewed-operator"
    )
    save("identity-result", jsonable_encoder(identity_result))
    meat_id = next(
        r.durable_object_id
        for r in identity_result.object_results
        if r.client_op_id == "meat"
    )
    selection = reviewed_selection(
        world, identity_result.child_revision_id, source, meat_id, pins
    )
    principal = NativeGraphPrincipal(
        "benchmark-q01-reviewed-operator", "gm", "local_operator"
    )
    expected_payload = frozen_payload(selection, world, origin, source, meat_id, pins)
    save("reviewed-statement-payload", expected_payload)
    # Explicit dependency injection in this offline fixture process; no server or
    # persistent runtime configuration is changed.
    with (
        patch.object(statements.native, "repository", lambda: repo),
        patch.object(statements.native, "binding", lambda _: deepcopy(binding)),
    ):
        staged = statements.prepare(selection, principal)
        require(
            staged["envelope"]["payload"] == expected_payload,
            "prepared payload differs from frozen review",
        )
        save("statement-prepared", staged)
        confirmed = statements.confirm(
            ConfirmStatement(
                **{k: staged[k] for k in ("envelope", "prepared", "token")}
            ),
            principal,
        )
        save("statement-result", confirmed)
        revision = repo.get_head(world).head_revision_id
        read = statements.read_subject(
            managed_world_id=binding["managed_world_id"],
            campaign_id=CAMPAIGN,
            revision_id=revision,
            entity_id=meat_id,
            principal=principal,
        )
        save("subject-read", read)
        capture = capture_native_lifecycle(
            repo, [{"prepare": staged, "confirm": confirmed}], read, principal
        )
    parent = repo.get_revision(world, identity_result.child_revision_id).revision
    review = [
        {
            "payload": expected_payload,
            "parent_context": {
                "authority": "native_vnext",
                "world": world,
                "campaign": CAMPAIGN,
                "visibility": "gm",
                "revision": identity_result.child_revision_id,
                "domain_ref": parent.domain_contract_ref.model_dump(mode="json"),
                "profile_ref": parent.semantic_profile_ref.model_dump(mode="json"),
            },
        }
    ]
    evaluation = evaluate_lifecycle(review, capture)
    after = repo.get_revision(world, revision).graph_payload
    preservation = {
        section: all(row in after[section] for row in before[section])
        for section in before
        if isinstance(before[section], list)
    }
    save("evaluation", evaluation)
    return {
        "source_receipt": jsonable_encoder(source),
        "identity_result": jsonable_encoder(identity_result),
        "statement_result": confirmed,
        "read": read,
        "evaluation": evaluation,
        "prior_graph_preserved": preservation,
        "initial_revision": initial_head,
        "final_revision": revision,
        "baseline_entities": len(before["entities"]),
        "baseline_assertions": len(before["assertions"]),
        "final_entities": len(after["entities"]),
        "final_assertions": len(after["assertions"]),
        "model_extraction_verified": False,
        "answer_quality_verified": False,
        "full_system_ingestion_verified": False,
    }


def retained_inputs(root):
    """Resolve the existing authority from its manifests; never print secrets."""
    from psycopg.conninfo import conninfo_to_dict

    root = root.resolve(strict=True)
    status = json.loads((root / "status.json").read_text())
    connection = json.loads((root / "clone-connection.json").read_text())
    donor = Path(status["source_baseline"]).resolve(strict=True)
    donor_manifest = json.loads((donor / "clone-connection.json").read_text())
    require(
        Path(status["root"]).resolve() == root, "working clone manifest root changed"
    )
    files = Path(connection["file_state_root"]).resolve(strict=True)
    require(files == root / "file-state", "working file authority changed")
    for key, database in (("dsn", DATABASE), ("app_dsn", APP_DATABASE)):
        parsed = conninfo_to_dict(connection[key])
        require(
            parsed.get("dbname") == database
            and parsed.get("host") == "127.0.0.1"
            and int(parsed.get("port", 0)) == donor_manifest["port"] == 55447,
            "configured database endpoint differs from retained clone",
        )
    return connection, donor_manifest, files


def check_server(dsn, database, donor):
    with readonly(dsn) as conn:
        connected = identity(conn)
        validate_connected(connected, database)
    network = json.loads(
        subprocess.run(
            [
                "docker",
                "inspect",
                donor["container"],
                "--format",
                "{{json .NetworkSettings}}",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    require(
        any(
            p["HostIp"] == "127.0.0.1" and p["HostPort"] == str(donor["port"])
            for p in network["Ports"]["5432/tcp"]
        ),
        "retained container port differs",
    )
    require(
        any(
            n["IPAddress"] == connected["server_address"].split("/")[0]
            for n in network["Networks"].values()
        ),
        "connected server is not retained container",
    )
    control = subprocess.run(
        [
            "docker",
            "exec",
            donor["container"],
            "pg_controldata",
            "/var/lib/postgresql/data",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    found = next(
        line.split(":", 1)[1].strip()
        for line in control.splitlines()
        if line.startswith("Database system identifier:")
    )
    require(
        found == connected["system_identifier"],
        "container/server control identity differs",
    )
    return connected


def repository(dsn, expected_identity=None):
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresNativeSourceEvidenceRepository,
    )

    class GuardedDatabase(PostgresDatabase):
        def connect(self):
            conn = super().connect()
            try:
                live = identity(conn)
                validate_connected(live, DATABASE)
                if expected_identity is not None:
                    require(
                        live == expected_identity,
                        "live database identity changed during fixture operation",
                    )
                conn.rollback()  # factory validation is not the publication transaction
                return conn
            except Exception:
                conn.close()
                raise

    return PostgresNativeSourceEvidenceRepository(GuardedDatabase(dsn))


def preflight(root):
    import dungeonmind
    import worldkeeper
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        access_context,
    )

    connection, donor, files = retained_inputs(root)
    keyfile = root.parent / SIGNING_KEY
    require(
        keyfile.is_file() and keyfile.stat().st_mode & 0o777 == 0o600,
        "existing private fixture signing key unavailable or not private",
    )
    native_identity = check_server(connection["dsn"], DATABASE, donor)
    app_identity = check_server(connection["app_dsn"], APP_DATABASE, donor)
    require(
        "runtime-dependencies/core-4ccd39a/" in dungeonmind.__file__,
        "actual Core import is not explicit serving pin",
    )
    # Compare source tree bytes, not the installed metadata of a different package.
    wkroot = Path(worldkeeper.__file__).resolve().parents[1]
    require(wkroot.name == "src", "explicit WK source import required")
    wk_repo = wkroot.parent
    subprocess.run(
        [
            "git",
            "-C",
            str(wk_repo),
            "diff",
            "--exit-code",
            "a30ee81ae0e777037c68afea8847b04a2c736ae1",
            "HEAD",
            "--",
            "src",
        ],
        check=True,
        capture_output=True,
    )
    registry = json.loads((files / "out/registries/world_containers.json").read_text())
    record = next(r for r in registry["records"] if r["world_id"] == WORLD)
    bound = record["native_graph_binding"]
    require(
        bound["native_world_id"] == WORLD
        and bound["binding_version"] == 3
        and bound["status"] == "active",
        "managed/native binding changed",
    )
    body = (files / SOURCE_PATH).read_bytes()
    pins = validate_source(body)
    require(
        len(body) == 6172 and pins["clause_sha256"] == CLAUSE_SHA,
        "reviewed source pins differ",
    )
    with readonly(connection["app_dsn"]) as conn:
        row = conn.execute(
            "SELECT a.world_id,a.campaign_id,a.session_id,r.content_sha256,r.markdown "
            "FROM source.revision r JOIN source.artifact a USING(source_artifact_id) "
            "WHERE r.source_revision_id=%s AND a.source_artifact_id=%s",
            (APP_REVISION, APP_ARTIFACT),
        ).fetchone()
        require(
            row is not None
            and row["world_id"] is None
            and row["campaign_id"] == CAMPAIGN
            and row["session_id"] == "session-8"
            and row["content_sha256"] == BODY_SHA
            and row["markdown"].encode() == body,
            "reviewed immutable APP source differs",
        )
    repo = repository(connection["dsn"], native_identity)
    head = repo.get_head(WORLD)
    require(
        head.head_revision_id == INITIAL_HEAD,
        "initial native head changed; review retained checkpoint before retry",
    )
    native_graph = repo.get_revision(WORLD, INITIAL_HEAD).graph_payload
    parent_revision = repo.get_revision(WORLD, INITIAL_HEAD).revision
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        descriptors,
    )

    _, profile = descriptors(repo, WORLD, INITIAL_HEAD)
    require(
        len(native_graph["entities"]) == 6 and len(native_graph["assertions"]) == 12,
        "native baseline differs",
    )
    result = {
        "schema": "buddy_q01_fixture_preflight_v1",
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "control_head": CONTROL_HEAD,
        "native_identity": native_identity,
        "app_identity": app_identity,
        "container": donor["container"],
        "file_root": str(files),
        "native_head": INITIAL_HEAD,
        "domain_ref": parent_revision.domain_contract_ref.model_dump(mode="json"),
        "profile_ref": parent_revision.semantic_profile_ref.model_dump(mode="json"),
        "statement_kernel_available": supports_statement_kernel(profile),
        "source_epoch": access_context(repo, WORLD)[0]["source_epoch"],
        "binding": {
            "managed_world_id": WORLD,
            "native_world_id": WORLD,
            "binding_version": 3,
        },
        "source": pins,
        "app_artifact": APP_ARTIFACT,
        "app_revision": APP_REVISION,
        "core_module": dungeonmind.__file__,
        "wk_module": worldkeeper.__file__,
        "native_tables": database_fingerprints(connection["dsn"]),
        "app_tables": database_fingerprints(connection["app_dsn"]),
        "files": file_fingerprints(files),
    }
    return result


APPENDS = {
    "dungeonmind.knowledge_revisions": 3,
    "dungeonmind.knowledge_head_events": 3,
    "dungeonmind.knowledge_publication_receipts": 3,
    "dungeonmind.knowledge_prospective_publication_results": 2,
    "dungeonmind.knowledge_native_source_admissions": 1,
    "dungeonmind.knowledge_native_source_spans": 1,
}


def conservation(before, after):
    failures = []
    if set(before) != set(after):
        failures.append("table inventory changed")
    deltas = {}
    for table in set(before) & set(after):
        old, new = before[table], after[table]
        removed = Counter(old["row_hashes"]) - Counter(new["row_hashes"])
        added = Counter(new["row_hashes"]) - Counter(old["row_hashes"])
        if not (removed or added):
            continue
        deltas[table] = {
            "before": old["count"],
            "after": new["count"],
            "removed_or_changed": sum(removed.values()),
            "added_or_changed": sum(added.values()),
        }
        if table in APPENDS:
            if (
                removed
                or sum(added.values()) != APPENDS[table]
                or any(new["owners"].get(h) != WORLD for h in added)
            ):
                failures.append(table + ": unexpected append or prior-row mutation")
        elif table == "dungeonmind.knowledge_heads":
            if (
                sum(removed.values()) != 1
                or sum(added.values()) != 1
                or any(old["owners"].get(h) != WORLD for h in removed)
                or any(new["owners"].get(h) != WORLD for h in added)
            ):
                failures.append(table + ": unrelated head changed")
        elif table == "dungeonmind.knowledge_native_source_authority":
            if (
                old["count"] != 1
                or new["count"] != 1
                or sum(removed.values()) != 1
                or sum(added.values()) != 1
            ):
                failures.append(table + ": unexpected authority delta")
        else:
            failures.append(table + ": outside permitted delta")
    for table in APPENDS:
        if table not in deltas:
            failures.append(table + ": required publication rows missing")
    return {"passed": not failures, "failures": failures, "table_deltas": deltas}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clone-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preflight-sha256")
    args = parser.parse_args(argv)
    root = args.clone_root.resolve(strict=True)
    evidence = root.parent / "native-review-context-v2/q01-fullworld-v1"
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence.chmod(0o700)

    def save(name, value):
        target = evidence / (name + ".json")
        temporary = target.with_suffix(".json.pending")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        directory = os.open(evidence, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    current = preflight(root)
    if not args.apply:
        prior_incident = (evidence / "source-request.json").exists()
        save(
            "preflight-observation-" + digest(current)
            if prior_incident
            else "preflight",
            current,
        )
        print(
            json.dumps(
                {
                    "mode": "read_only_preflight",
                    "sha256": digest(current),
                    "evidence": str(evidence),
                    "prior_apply_checkpoint": prior_incident,
                    "statement_kernel_available": current["statement_kernel_available"],
                    "apply_ready": current["statement_kernel_available"]
                    and not prior_incident,
                }
            )
        )
        return
    frozen = json.loads((evidence / "preflight.json").read_text())
    require(
        current["statement_kernel_available"],
        "current native parent lacks statement kernel; no writes or transition authorized",
    )
    require(
        args.preflight_sha256 == digest(frozen) == digest(current),
        "explicit preflight/server/database/source/head pins changed",
    )
    require(
        not (evidence / "native-before.dump").exists(),
        "snapshot already exists; original incident must be inspected, not reminted",
    )
    connection, donor, files = retained_inputs(root)
    # Snapshot the SAME database through the already verified retained container.
    from psycopg.conninfo import conninfo_to_dict

    user = conninfo_to_dict(connection["dsn"])["user"]
    snapshot = evidence / "native-before.dump"
    snapshot_fd = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(snapshot_fd, "wb") as output:
        subprocess.run(
            [
                "docker",
                "exec",
                donor["container"],
                "pg_dump",
                "-U",
                user,
                "-d",
                DATABASE,
                "-Fc",
            ],
            stdout=output,
            stderr=subprocess.PIPE,
            check=True,
        )
        output.flush()
        os.fsync(output.fileno())
    require(
        snapshot.read_bytes().startswith(b"PGDMP"),
        "native rollback snapshot is not custom pg_dump",
    )
    save(
        "snapshot",
        {
            "database": DATABASE,
            "server": current["native_identity"],
            "sha256": sha(snapshot.read_bytes()),
            "restore_requires_stopped_consumers": True,
            "automatic_restore": False,
        },
    )
    # Revalidate the entire boundary after the snapshot and before source IO.
    require(
        digest(preflight(root)) == args.preflight_sha256,
        "boundary changed during snapshot",
    )
    keyfile = root.parent / SIGNING_KEY
    require(keyfile.is_file(), "existing private fixture signing key unavailable")
    from unittest.mock import patch

    with patch.dict(
        os.environ,
        {"DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY": keyfile.read_text().strip()},
    ):
        try:
            result = execute_native_proof(
                repository(connection["dsn"], current["native_identity"]),
                (files / SOURCE_PATH).read_bytes(),
                current["source"],
                current["binding"],
                save,
            )
            save("proof", result)
        except Exception as exc:
            save(
                "incident",
                {
                    "error_type": type(exc).__name__,
                    "retry_original_artifacts_only": True,
                    "automatic_restore": False,
                },
            )
            try:
                save(
                    "incident-conservation",
                    {
                        "native": conservation(
                            current["native_tables"],
                            database_fingerprints(connection["dsn"]),
                        ),
                        "app_unchanged": current["app_tables"]
                        == database_fingerprints(connection["app_dsn"]),
                        "files_unchanged": current["files"] == file_fingerprints(files),
                        "native_after": database_fingerprints(connection["dsn"]),
                    },
                )
            except Exception as audit_error:
                save(
                    "incident-conservation-unassessed",
                    {"error_type": type(audit_error).__name__},
                )
            raise
    check_server(connection["dsn"], DATABASE, donor)
    after_native = database_fingerprints(connection["dsn"])
    after_app = database_fingerprints(connection["app_dsn"])
    after_files = file_fingerprints(files)
    guard = conservation(current["native_tables"], after_native)
    guard.update(
        {
            "app_unchanged": current["app_tables"] == after_app,
            "files_unchanged": current["files"] == after_files,
        }
    )
    save("conservation", guard)
    require(
        guard["passed"] and guard["app_unchanged"] and guard["files_unchanged"],
        "unexpected fixture delta; preserve evidence and stop",
    )
    require(all(result["prior_graph_preserved"].values()), "prior native graph changed")
    require(
        result["final_entities"] == result["baseline_entities"] + 2
        and result["final_assertions"] == result["baseline_assertions"] + 3,
        "unexpected native entity/assertion delta",
    )
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        access_context,
    )

    require(
        access_context(
            repository(connection["dsn"], current["native_identity"]), WORLD
        )[0]["source_epoch"]
        == current["source_epoch"] + 1,
        "unexpected source authority epoch delta",
    )
    require(
        result["evaluation"]["counts"]["fail"] == 0,
        "independent lifecycle evaluation failed",
    )
    print(
        json.dumps(
            {
                "status": "manual_q01_fixture_proven",
                "final_revision": result["final_revision"],
                "evaluation": result["evaluation"]["counts"],
                "conservation": guard,
                "full_system_ingestion_verified": False,
            }
        )
    )


if __name__ == "__main__":
    main()
