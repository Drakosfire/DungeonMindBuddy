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
CONTROL_HEAD = "a6292c2112ef96a89f658504f9a7611c7c90b6df"
CORE_REF = "38c87bc78bcd05a538bd89fdbb928fca54c3a283"
CORE_ROOT = Path(
    "/home/drakosfire/Projects/.codex/native-profile-transition/worktrees/DungeonMind"
)
CHECKPOINT = "q01-fullworld-profile2-v1"
TRANSITION_CHILD = "rev:5e8dda8979518632f905cd53d7c622aa"
TRANSITION_COMMAND = "2c102971fc8a47575e9b4edefd0408632bdc1fc93954e9736ab7fe9c32af6bc0"
TRANSITION_GRAPH = "2b20e71e56fc251433f66bfd7b0bc7564ecdd0ee4e231b230ec4d3160fdd6e42"
TRANSITION_ID = "q01-fullworld-profile-1-to-2-v1"
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


def require_complete_evaluation(evaluation):
    checks = evaluation["checks"]
    recovery = "executed_original_packet_recovery"
    globals_ = {
        "capture_schema",
        "selected_clause_inventory",
        "unique_headers",
        "distinct_native_statements",
        "exact_typed_edge_inventory",
        "complete_discovery",
        "no_false_absence",
    }
    suffixes = {
        "selected_payload",
        "signed_selection",
        "parent_context",
        "prepared_parent_binding",
        "native_header_context",
        "publication_parent",
        "original_receipt",
        "publication_context",
        "native_publication_identity",
        "published_payload",
        "native_semantic_digest",
        "native_mappings",
        "valid_data_preserved",
        "no_direct_event_leakage",
        "read_descends_from_child",
        "read_context",
        "read_payload",
        "read_mapping_identity",
        "authorized_about_discovery",
        "source_bytes",
    }
    prefixes = [
        name[: -len("selected_payload")]
        for name in checks
        if name.endswith(":selected_payload")
    ]
    require(len(prefixes) == 1, "required Q01 evaluation inventory missing")
    expected = globals_ | {prefixes[0] + suffix for suffix in suffixes}
    require(
        set(checks) == expected | {recovery},
        "required Q01 evaluation inventory differs",
    )
    require(
        all(checks[name]["status"] == "pass" for name in expected),
        "required lifecycle evaluation not assessed and passing",
    )
    require(
        checks[recovery]["status"] in {"pass", "unassessed"},
        "executed recovery evaluation failed",
    )


def verify_source_tree(import_root, repository_root, ref, packages):
    """Compare actual imported package bytes, including untracked additions, to Git."""
    import_root, repository_root = Path(import_root), Path(repository_root)
    tree = subprocess.run(
        [
            "git",
            "-C",
            str(repository_root),
            "ls-tree",
            "-rz",
            ref,
            "--",
            *["src/" + package for package in packages],
        ],
        check=True,
        capture_output=True,
    ).stdout
    expected = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        require(
            kind == "blob" and mode in {"100644", "100755"},
            "unsupported dependency tree entry",
        )
        expected[path.decode().removeprefix("src/")] = oid
    require(bool(expected), "pinned dependency source missing")
    actual = {}
    for package in packages:
        for path in (import_root / package).rglob("*"):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            require(not path.is_symlink(), "dependency symlink not permitted")
            if path.is_file():
                body = path.read_bytes()
                actual[path.relative_to(import_root).as_posix()] = hashlib.sha1(
                    b"blob " + str(len(body)).encode() + b"\0" + body
                ).hexdigest()
    require(
        actual == expected, "actual dependency source differs from accepted Git ref"
    )
    return {"ref": ref, "files": len(expected), "tree_digest": digest(expected)}


def transition_authority(repo):
    """Derive commitments only; this function cannot publish."""
    from dungeonmind.contracts.vnext.profile_transition import (
        KnowledgeProfileTransitionV1,
    )
    from dungeonmind.application.vnext.authority import revision_from_command
    from dungeonmind.application.vnext.publication import _command_from_stored
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        descriptors,
    )
    from graph_memory.vnext.domain_runtime import (
        dungeonbuddy_dnd5e_custom_predicate_profile,
    )

    parent = repo.get_revision(WORLD, INITIAL_HEAD)
    require(parent is not None, "transition immutable parent missing")
    domain, current = descriptors(repo, WORLD, INITIAL_HEAD)
    target = dungeonbuddy_dnd5e_custom_predicate_profile()
    require(
        parent.graph_payload_sha256 == TRANSITION_GRAPH, "transition graph hash differs"
    )
    require(
        current.profile_revision == "1"
        and canonical_sha256(current.model_dump(mode="json"))
        == "51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14",
        "transition from ref differs",
    )
    require(
        domain.domain_revision == "2"
        and canonical_sha256(domain.model_dump(mode="json"))
        == "d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd",
        "transition domain ref differs",
    )
    require(
        canonical_sha256(target.model_dump(mode="json"))
        == "d40a352d1c6cbd24df68be887be6dc65a470e4cea8fb64970ef9ad89b96a3339",
        "transition target ref differs",
    )
    request = KnowledgeProfileTransitionV1(
        space_id=WORLD,
        expected_parent_revision_id=INITIAL_HEAD,
        domain_contract_ref=parent.revision.domain_contract_ref,
        from_profile_ref=parent.revision.semantic_profile_ref,
        to_profile_ref={
            "profile_id": target.profile_id,
            "profile_revision": target.profile_revision,
            "descriptor_sha256": canonical_sha256(target.model_dump(mode="json")),
        },
        publication_id=TRANSITION_ID,
        created_at=datetime(2026, 10, 29, 16, 34, 32, tzinfo=UTC),
    )
    command = _command_from_stored(parent).model_copy(
        update={
            "parent_revision_id": INITIAL_HEAD,
            "expected_parent_revision_id": INITIAL_HEAD,
            "operation_ids": [TRANSITION_ID],
            "semantic_profile_ref": request.to_profile_ref,
            "created_at": request.created_at,
        }
    )
    require(
        canonical_sha256(command.model_dump(mode="json")) == TRANSITION_COMMAND,
        "transition command commitment differs",
    )
    require(
        revision_from_command(command).revision_id == TRANSITION_CHILD,
        "transition child commitment differs",
    )
    return request, domain, current, target


def verify_transition_receipt(
    repo,
    request,
    receipt,
    *,
    child=TRANSITION_CHILD,
    command_sha=TRANSITION_COMMAND,
    graph_sha=TRANSITION_GRAPH,
):
    require(receipt is not None, "transition receipt missing")
    require(
        receipt.space_id == request.space_id
        and receipt.publication_id == request.publication_id
        and receipt.expected_parent_revision_id == request.expected_parent_revision_id
        and receipt.published_revision_id == child
        and receipt.command_sha256 == command_sha
        and receipt.graph_payload_sha256 == graph_sha,
        "transition receipt differs",
    )
    parent = repo.get_revision(request.space_id, request.expected_parent_revision_id)
    after = repo.get_revision(request.space_id, child)
    require(parent is not None and after is not None, "transition revision missing")
    require(
        parent.graph_payload == after.graph_payload
        and after.graph_payload_sha256 == graph_sha,
        "transition graph changed",
    )
    require(
        after.revision.parent_revision_id == parent.revision.revision_id
        and after.revision.domain_contract_ref == request.domain_contract_ref
        and parent.revision.semantic_profile_ref == request.from_profile_ref
        and after.revision.semantic_profile_ref == request.to_profile_ref
        and after.revision.migration_origin_ref == parent.revision.migration_origin_ref,
        "transition revision authority differs",
    )
    cursor, seen = repo.get_head(request.space_id).head_revision_id, set()
    while cursor != child:
        require(
            cursor is not None and cursor not in seen,
            "transition descendant lineage differs",
        )
        seen.add(cursor)
        node = repo.get_revision(request.space_id, cursor)
        require(
            node is not None
            and node.revision.domain_contract_ref == request.domain_contract_ref
            and node.revision.semantic_profile_ref == request.to_profile_ref,
            "transition descendant authority differs",
        )
        cursor = node.revision.parent_revision_id
    return receipt


def execute_transition(
    repo,
    authority,
    save,
    *,
    expected_epoch=26,
    child=TRANSITION_CHILD,
    command_sha=TRANSITION_COMMAND,
    graph_sha=TRANSITION_GRAPH,
    epoch_reader=None,
):
    from dungeonmind.application.vnext import transition_knowledge_semantic_profile
    from dungeonmind.application.vnext.publication import get_publication_receipt
    from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
        access_context,
    )

    request, domain, current, target = authority
    epoch_reader = epoch_reader or (
        lambda: access_context(repo, request.space_id)[0]["source_epoch"]
    )
    save(
        "transition-request",
        {
            "request": request.model_dump(mode="json"),
            "domain": domain.model_dump(mode="json"),
            "current_profile": current.model_dump(mode="json"),
            "target_profile": target.model_dump(mode="json"),
        },
    )
    # Recover exact publication before considering the mutable head.
    receipt = get_publication_receipt(
        request.space_id, request.publication_id, repository=repo
    )
    require(epoch_reader() == expected_epoch, "transition source epoch differs")
    if receipt is None:
        require(
            repo.get_head(request.space_id).head_revision_id
            == request.expected_parent_revision_id,
            "fresh transition parent changed",
        )
        receipt = transition_knowledge_semantic_profile(
            repository=repo,
            request=request,
            domain_contract=domain,
            current_profile=current,
            target_profile=target,
        )
    verify_transition_receipt(
        repo,
        request,
        receipt,
        child=child,
        command_sha=command_sha,
        graph_sha=graph_sha,
    )
    require(epoch_reader() == expected_epoch, "transition source epoch changed")
    save("transition-receipt", receipt.model_dump(mode="json"))
    return receipt


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


def execute_native_proof(
    repo,
    body,
    pins,
    binding,
    save,
    initial_head=INITIAL_HEAD,
    operation_namespace="q01-fullworld-v1",
):
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
        namespace="dungeonbuddy.benchmark.q01-app-version-bridge:"
        + operation_namespace,
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
        admission_id="q01-fixture-source:"
        + operation_namespace
        + ":"
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
        operation_id="q01-fixture-meat:"
        + operation_namespace
        + ":"
        + digest(origin.model_dump(mode="json")),
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
    save("evaluation", evaluation)
    require_complete_evaluation(evaluation)
    after = repo.get_revision(world, revision).graph_payload
    preservation = {
        section: all(row in after[section] for row in before[section])
        for section in before
        if isinstance(before[section], list)
    }
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
        Path(dungeonmind.__file__).resolve().parent.parent == CORE_ROOT / "src",
        "actual Core import differs from fixture dependency",
    )
    core_integrity = verify_source_tree(
        Path(dungeonmind.__file__).resolve().parent.parent,
        CORE_ROOT,
        CORE_REF,
        ("dungeonmind", "dungeonmind_dnd"),
    )
    wkroot = Path(worldkeeper.__file__).resolve().parents[1]
    require(wkroot.name == "src", "explicit WK source import required")
    wk_integrity = verify_source_tree(
        wkroot,
        wkroot.parent,
        "a30ee81ae0e777037c68afea8847b04a2c736ae1",
        ("worldkeeper",),
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
    from dungeonmind.application.vnext.publication import get_publication_receipt

    authority = transition_authority(repo)
    receipt = get_publication_receipt(WORLD, TRANSITION_ID, repository=repo)
    if receipt is not None:
        verify_transition_receipt(repo, authority[0], receipt)
    head = repo.get_head(WORLD)
    require(
        receipt is not None or head.head_revision_id == INITIAL_HEAD,
        "initial native head changed without transition receipt",
    )
    old_checkpoint = root.parent / "native-review-context-v2/q01-fullworld-v1"
    old_request = json.loads((old_checkpoint / "source-request.json").read_text())
    require(
        repo.get_native_source_admission_receipt(WORLD, old_request["admission_id"])
        is None,
        "original refused source request has admission receipt",
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
        "native_head": head.head_revision_id,
        "transition_request": authority[0].model_dump(mode="json"),
        "transition_ready": receipt is None and head.head_revision_id == INITIAL_HEAD,
        "transition_receipt": receipt.model_dump(mode="json") if receipt else None,
        "original_checkpoint": file_fingerprints(old_checkpoint),
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
        "core_integrity": core_integrity,
        "wk_integrity": wk_integrity,
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


def conservation(before, after, *, appends=None, source_epoch_change=True):
    appends = APPENDS if appends is None else appends
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
        if table in appends:
            if (
                removed
                or sum(added.values()) != appends[table]
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
        elif (
            table == "dungeonmind.knowledge_native_source_authority"
            and source_epoch_change
        ):
            if (
                old["count"] != 1
                or new["count"] != 1
                or sum(removed.values()) != 1
                or sum(added.values()) != 1
            ):
                failures.append(table + ": unexpected authority delta")
        else:
            failures.append(table + ": outside permitted delta")
    for table in appends:
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
    evidence = root.parent / "native-review-context-v2" / CHECKPOINT
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence.chmod(0o700)

    def save(name, value):
        target = evidence / (name + ".json")
        if target.exists():
            require(
                json.loads(target.read_text()) == value,
                "checkpoint collision: preserve original " + name,
            )
            return
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
        save("preflight-observation-" + digest(current), current)
        if not (evidence / "preflight.json").exists():
            save("preflight", current)
        print(
            json.dumps(
                {
                    "mode": "read_only_preflight",
                    "sha256": digest(current),
                    "evidence": str(evidence),
                    "prior_apply_checkpoint": prior_incident,
                    "statement_kernel_available": current["statement_kernel_available"],
                    "apply_ready": (
                        current.get("transition_ready", False)
                        or current["statement_kernel_available"]
                    )
                    and not prior_incident,
                }
            )
        )
        return
    selected = evidence / (
        "preflight-observation-" + str(args.preflight_sha256) + ".json"
    )
    frozen = json.loads(
        (selected if selected.exists() else evidence / "preflight.json").read_text()
    )
    require(
        current.get("transition_ready", False) or current["statement_kernel_available"],
        "current native parent lacks statement kernel or pinned transition authority",
    )
    require(
        args.preflight_sha256 == digest(frozen) == digest(current),
        "explicit preflight/server/database/source/head pins changed",
    )
    require(
        not (evidence / "native-before.dump").exists(),
        "snapshot already exists; original incident must be inspected, not reminted",
    )
    require(
        current["native_head"] == INITIAL_HEAD and current["source_epoch"] == 26,
        "fresh profile2 proof requires original head and source epoch",
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
            repo = repository(connection["dsn"], current["native_identity"])
            execute_transition(repo, transition_authority(repo), save)
            transition_after = database_fingerprints(connection["dsn"])
            transition_guard = conservation(
                current["native_tables"],
                transition_after,
                appends={
                    "dungeonmind.knowledge_revisions": 1,
                    "dungeonmind.knowledge_head_events": 1,
                    "dungeonmind.knowledge_publication_receipts": 1,
                },
                source_epoch_change=False,
            )
            require(transition_guard["passed"], "transition conservation failed")
            require(
                database_fingerprints(connection["app_dsn"]) == current["app_tables"]
                and file_fingerprints(files) == current["files"],
                "transition unrelated state changed",
            )
            save("transition-conservation", transition_guard)
            save(
                "post-transition-head",
                {
                    "parent": INITIAL_HEAD,
                    "child": TRANSITION_CHILD,
                    "publication_id": TRANSITION_ID,
                    "source_epoch": 26,
                },
            )
            result = execute_native_proof(
                repo,
                (files / SOURCE_PATH).read_bytes(),
                current["source"],
                current["binding"],
                save,
                initial_head=TRANSITION_CHILD,
                operation_namespace=CHECKPOINT,
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
    guard = conservation(
        current["native_tables"],
        after_native,
        appends=APPENDS
        | {
            "dungeonmind.knowledge_revisions": 4,
            "dungeonmind.knowledge_head_events": 4,
            "dungeonmind.knowledge_publication_receipts": 4,
        },
    )
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
        file_fingerprints(root.parent / "native-review-context-v2/q01-fullworld-v1")
        == current["original_checkpoint"],
        "original refused checkpoint changed",
    )
    require_complete_evaluation(result["evaluation"])
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
