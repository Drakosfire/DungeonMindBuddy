"""PLAY-2 proof of Buddy -> WorldKeeper -> persistent DungeonMind authority."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from dungeonmind.application.vnext.materialization import (
    NATIVE_VNEXT_GRAPH_SCHEMA,
    encode_native_graph_payload,
)
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from dungeonmind.contracts.vnext import DomainContractRef, Entity, EvidenceRefV3
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.postgres.database import PostgresDatabase
from dungeonmind.infrastructure.postgres.vnext_knowledge import (
    PostgresKnowledgeRevisionRepository,
)
from worldkeeper.application import InvalidWorldChange
from worldkeeper.application.commit import PreparedChangeConflict, PreparedChangeStale
from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime

from apps.live_control_server.integrations.worldkeeper import (
    PlayAuthoringContext,
    WorldKeeperGraphAuthoringConsumer,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringProposalPayload,
)
from graph_memory.vnext import (
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_world_domain_contract,
)

pytestmark = pytest.mark.integration
PIN = "0f709d76fdc53bac9c9258d1751463ae2c76ca71"
NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)
EVIDENCE = "ev:play-session-note"


def _dbname(dsn: str) -> str:
    return urlsplit(dsn).path.removeprefix("/")


def _replace_db(dsn: str, name: str) -> str:
    p = urlsplit(dsn)
    if p.scheme not in {"postgres", "postgresql"} or not p.hostname:
        raise ValueError("PLAY-2 requires a PostgreSQL URL with a host")
    return urlunsplit((p.scheme, p.netloc, f"/{name}", p.query, ""))


def _assert_safe_admin(dsn: str) -> None:
    live = {
        os.getenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "").strip(),
        os.getenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", "").strip(),
    }
    if not dsn or dsn in live:
        raise ValueError("admin DSN must not be a configured live authority")
    if _dbname(dsn) not in {"postgres", "template1"}:
        raise ValueError("admin DSN must target an administrative database")


@pytest.fixture(scope="module")
def play2_db() -> Iterator[str]:
    admin = os.getenv("DMB_PLAY2_PG_ADMIN_DSN", "").strip()
    raw_source = os.getenv("DMB_PLAY2_DUNGEONMIND_SOURCE", "").strip()
    if not admin or not raw_source:
        pytest.skip(
            "explicit PLAY-2 PostgreSQL authority and migration source required"
        )
    _assert_safe_admin(admin)
    source = Path(raw_source).resolve()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "alembic.ini", "migrations"],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if (
        head != PIN
        or dirty
        or not (source / "alembic.ini").is_file()
        or not (source / "migrations").is_dir()
    ):
        raise ValueError("DungeonMind migration source is not the clean exact pin")
    name = f"dmb_play2_test_{uuid.uuid4().hex}"
    dsn = _replace_db(admin, name)
    with psycopg.connect(admin, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{name}"')
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=source,
            env={**os.environ, "DUNGEONMIND_DATABASE_URL": dsn},
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            pytest.fail(
                f"exact-pin migration failed: {result.stdout[-1000:]} {result.stderr[-1000:]}"
            )
        yield dsn
    finally:
        with psycopg.connect(admin, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()",
                (name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{name}"')


def _repo(dsn: str) -> PostgresKnowledgeRevisionRepository:
    return PostgresKnowledgeRevisionRepository(PostgresDatabase(dsn))


def _seed(dsn: str, space: str, *, evidence: bool = True, v3: bool = True) -> str:
    domain = dungeonbuddy_world_domain_contract()
    profile = (
        dungeonbuddy_dnd5e_custom_predicate_profile()
        if v3
        else dungeonbuddy_dnd5e_semantic_profile()
    )
    payload = encode_native_graph_payload(
        entities={"ent:pippa": Entity(entity_id="ent:pippa")},
        assertions={},
        aliases={},
        evidence={
            EVIDENCE: EvidenceRefV3(
                evidence_ref_id=EVIDENCE,
                source_artifact_id="art:play-session-note",
                source_revision_id="srcrev:play-session-note",
                evidence_role="support",
                can_open_source=True,
                can_highlight_span=False,
                locator="session-note",
            )
        }
        if evidence
        else {},
    )
    stored = _repo(dsn).publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=space,
            operation_ids=[f"op:genesis:{space}"],
            graph_schema=NATIVE_VNEXT_GRAPH_SCHEMA,
            graph_payload=payload,
            domain_contract_ref=DomainContractRef(
                domain_id=domain.domain_id,
                domain_revision=domain.domain_revision,
                descriptor_sha256=canonical_sha256(domain.model_dump(mode="json")),
            ),
            semantic_profile_ref=SemanticProfileRef(
                profile_id=profile.profile_id,
                profile_revision=profile.profile_revision,
                descriptor_sha256=canonical_sha256(profile.model_dump(mode="json")),
            ),
            created_at=NOW,
        )
    )
    return stored.revision.revision_id


def _consumer(dsn: str, prepared_id: str) -> WorldKeeperGraphAuthoringConsumer:
    runtime = DungeonMindWorldKeeperRuntime(
        repository=_repo(dsn),
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
        clock=lambda: NOW,
        prepared_id_factory=lambda: prepared_id,
    )
    return WorldKeeperGraphAuthoringConsumer(runtime)


def _context(space: str) -> PlayAuthoringContext:
    return PlayAuthoringContext(
        space_id=space,
        campaign_id="campaign:play-witness",
        evidence_ref_ids=(EVIDENCE,),
    )


def _proposal(**fields: object) -> GraphObjectAuthoringProposalPayload:
    return GraphObjectAuthoringProposalPayload.model_validate(
        {
            "localProposalId": fields.pop("localProposalId"),
            "proposalKind": fields.pop("proposalKind"),
            "status": "staged_local",
            "visibility": {"visibility": "gm_private", "revealState": "unrevealed"},
            "provenancePreview": {"origin": "human_authored"},
            **fields,
        }
    )


def _proposals(
    summary: str = "A brewery by the tower",
) -> tuple[GraphObjectAuthoringProposalPayload, ...]:
    brewery = _proposal(
        localProposalId="brewery",
        proposalKind="object",
        objectRef={
            "label": "The Wizard's Tower Brewing Co",
            "kind": "location",
            "summary": summary,
        },
    )
    relationship = _proposal(
        localProposalId="rel-pippa-brewery",
        proposalKind="relationship",
        sourceObjectRef={
            "refKind": "existing_graph_node",
            "nodeId": "ent:pippa",
            "label": "Pippa",
        },
        targetObjectRef={
            "refKind": "local_proposal",
            "localProposalId": "brewery",
            "label": "The Wizard's Tower Brewing Co",
        },
        relationshipType="works_at",
        direction="directed",
    )
    return relationship, brewery


def _counts(dsn: str, space: str) -> tuple[int, int, int, int]:
    with PostgresDatabase(dsn).connect() as connection:
        row = connection.execute(
            "SELECT (SELECT count(*) FROM dungeonmind.knowledge_revisions WHERE space_id=%s) revisions, (SELECT count(*) FROM dungeonmind.knowledge_head_events WHERE space_id=%s) events, (SELECT count(*) FROM dungeonmind.knowledge_publication_receipts WHERE space_id=%s) receipts, (SELECT count(*) FROM dungeonmind.knowledge_prospective_publication_results WHERE space_id=%s) results",
            (space, space, space, space),
        ).fetchone()
    assert row is not None
    return tuple(
        int(row[key]) for key in ("revisions", "events", "receipts", "results")
    )  # type: ignore[return-value]


def test_persistent_prepare_confirm_restart_replay_and_concurrency(
    play2_db: str,
) -> None:
    space = "space:play2:canonical"
    parent = _seed(play2_db, space)
    prepared = _consumer(play2_db, "prepared:canonical").prepare(
        context=_context(space), proposals=_proposals()
    )
    assert _counts(play2_db, space) == (1, 1, 0, 0)
    committed = _consumer(play2_db, "unused").commit(prepared, confirmed_by="user:gm")
    assert committed.expected_parent_revision_id == parent
    assert committed.verification.exact_child_read_back
    assert _counts(play2_db, space) == (2, 2, 1, 1)
    entity_id = next(
        x.durable_object_id
        for x in committed.object_results
        if x.client_op_id == "brewery"
    )
    assertion_id = next(
        x.durable_assertion_id
        for x in committed.assertion_results
        if x.client_op_id == "rel-pippa-brewery"
    )
    repo = _repo(play2_db)
    head, receipt, aggregate, child = (
        repo.get_head(space),
        repo.get_publication_receipt(space, prepared.prepared_change_id),
        repo.get_prospective_publication(space, prepared.prepared_change_id),
        repo.get_revision(space, committed.child_revision_id),
    )
    assert head and head.head_revision_id == committed.child_revision_id
    assert receipt and receipt.published_revision_id == committed.child_revision_id
    assert (
        aggregate
        and aggregate.prospective_result.published_revision_id
        == committed.child_revision_id
    )
    assert child and child.graph_payload_sha256 == committed.child_graph_payload_sha256
    relation = next(
        x
        for x in child.graph_payload["assertions"]
        if x["assertion_id"] == assertion_id
    )
    assert (
        relation["subject_entity_id"] == "ent:pippa"
        and relation["value"]["entity_id"] == entity_id
    )
    assert relation["predicate"] == "dungeonbuddy.custom:works_at"
    assert relation["metadata"]["evidence_ref_ids"] == [EVIDENCE]
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "from dungeonmind.infrastructure.postgres.database import PostgresDatabase; from dungeonmind.infrastructure.postgres.vnext_knowledge import PostgresKnowledgeRevisionRepository as R; import json,os; r=R(PostgresDatabase(os.environ['D'])); h=r.get_head(os.environ['S']); x=r.get_revision(os.environ['S'],h.head_revision_id); print(json.dumps([h.head_revision_id,x.graph_payload_sha256]))",
        ],
        env={**os.environ, "D": play2_db, "S": space},
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(probe.stdout) == [
        committed.child_revision_id,
        child.graph_payload_sha256,
    ]
    assert (
        _consumer(play2_db, "unused").commit(prepared, confirmed_by="user:gm")
        == committed
    )
    assert _counts(play2_db, space) == (2, 2, 1, 1)

    for duplicate in (False, True):
        race_space = f"space:play2:{'duplicate' if duplicate else 'race'}"
        _seed(play2_db, race_space)
        left = _consumer(
            play2_db, "prepared:same" if duplicate else "prepared:left"
        ).prepare(context=_context(race_space), proposals=_proposals("Left"))
        right = (
            left
            if duplicate
            else _consumer(play2_db, "prepared:right").prepare(
                context=_context(race_space), proposals=_proposals("Right")
            )
        )
        barrier, wins, errors = threading.Barrier(2), [], []

        def commit(value: object) -> None:
            try:
                barrier.wait(timeout=5)
                wins.append(
                    _consumer(play2_db, "unused").commit(value, confirmed_by="user:gm")
                )  # type: ignore[arg-type]
            except BaseException as error:
                errors.append(error)

        threads = [threading.Thread(target=commit, args=(x,)) for x in (left, right)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        assert all(not thread.is_alive() for thread in threads)
        if duplicate:
            assert errors == [] and len(wins) == 2 and wins[0] == wins[1]
        else:
            assert (
                len(wins) == 1
                and len(errors) == 1
                and isinstance(errors[0], PreparedChangeStale)
            )
        assert _counts(play2_db, race_space) == (2, 2, 1, 1)


def test_negative_admission_identity_and_stale_paths_are_atomic(play2_db: str) -> None:
    for space, evidence, v3, match in (
        ("space:missing", False, True, "evidence_ref_absent"),
        ("space:v2", True, False, "semantic_profile_mismatch"),
    ):
        _seed(play2_db, space, evidence=evidence, v3=v3)
        with pytest.raises(InvalidWorldChange, match=match):
            _consumer(play2_db, f"prepared:{space}").prepare(
                context=_context(space), proposals=_proposals()
            )
        assert _counts(play2_db, space) == (1, 1, 0, 0)
    space = "space:changed"
    _seed(play2_db, space)
    first = _consumer(play2_db, "prepared:changed").prepare(
        context=_context(space), proposals=_proposals("First")
    )
    changed = _consumer(play2_db, "prepared:changed").prepare(
        context=_context(space), proposals=_proposals("Changed")
    )
    _consumer(play2_db, "unused").commit(first, confirmed_by="user:gm")
    with pytest.raises(PreparedChangeConflict, match="already bound"):
        _consumer(play2_db, "unused").commit(changed, confirmed_by="user:gm")
    assert _counts(play2_db, space) == (2, 2, 1, 1)
    space = "space:stale"
    _seed(play2_db, space)
    stale = _consumer(play2_db, "prepared:stale").prepare(
        context=_context(space), proposals=_proposals("Stale")
    )
    fresh = _consumer(play2_db, "prepared:fresh").prepare(
        context=_context(space), proposals=_proposals("Fresh")
    )
    _consumer(play2_db, "unused").commit(fresh, confirmed_by="user:gm")
    with pytest.raises(PreparedChangeStale):
        _consumer(play2_db, "unused").commit(stale, confirmed_by="user:gm")
    assert _counts(play2_db, space) == (2, 2, 1, 1)


def test_live_or_non_admin_dsn_is_rejected_before_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = "postgresql://user:secret@127.0.0.1:5432/live_world"
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", live)
    with pytest.raises(ValueError, match="live authority"):
        _assert_safe_admin(live)
    with pytest.raises(ValueError, match="administrative database"):
        _assert_safe_admin("postgresql://user:secret@127.0.0.1:5432/shared_test")
