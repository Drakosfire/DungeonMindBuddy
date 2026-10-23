from __future__ import annotations

import hashlib
from uuid import UUID

import psycopg
import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.source.service import (
    get_source_markdown,
    persist_source_markdown,
)


def test_source_markdown_is_immutable_and_idempotent(
    application_state_dsn: str,
) -> None:
    markdown = "# Session 25\n\nA durable paragraph.\n"
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    first = persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-25:abc123",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        markdown=markdown,
        content_sha256=f"sha256:{digest}",
        lineage={"adopted_from_run_id": "run-25"},
    )
    second = persist_source_markdown(
        source_artifact_id=first.source_artifact_id,
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        markdown=markdown,
        content_sha256=digest,
        lineage={"adopted_from_run_id": "run-25"},
    )

    assert first.source_revision_id == second.source_revision_id
    assert second.markdown == markdown
    assert second.content_sha256 == digest
    assert get_source_markdown(
        source_artifact_id=first.source_artifact_id,
        content_sha256=digest,
    ) == second

    with psycopg.connect(application_state_dsn) as conn:
        revision_count = conn.execute("SELECT count(*) FROM source.revision").fetchone()
    assert revision_count == (1,)

    with pytest.raises(ApplicationStateConflictError, match="does not match"):
        persist_source_markdown(
            source_artifact_id=first.source_artifact_id,
            source_domain="recap",
            campaign_id="longmont-c2",
            session_id="session-25",
            world_id="eldyrwild",
            markdown="# Different\n",
            content_sha256=digest,
        )


def test_source_lookup_is_exact_artifact_and_digest(
    application_state_dsn: str,
) -> None:
    markdown = "Exact bytes.\n"
    record = persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c1:session-10:abc123",
        source_domain="recap",
        campaign_id="longmont-c1",
        session_id="session-10",
        world_id="eldyrwild",
        markdown=markdown,
    )

    assert get_source_markdown(
        source_artifact_id=record.source_artifact_id,
        content_sha256=record.content_sha256,
        source_revision_id=UUID(str(record.source_revision_id)),
    ) == record
    assert get_source_markdown(
        source_artifact_id=record.source_artifact_id,
        content_sha256="0" * 64,
    ) is None


def test_supplied_source_revision_id_is_an_exact_assertion(
    application_state_dsn: str,
) -> None:
    markdown = "# Exact restore\n"
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    requested = UUID("8ed1e034-23c6-4295-b2ff-05d5cdd643a9")
    kwargs = dict(
        source_artifact_id="artifact:recap:longmont-c2:session-25:fd38b5915b32",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        markdown=markdown,
        content_sha256=digest,
        lineage={"adopted_from_run_id": "graph-ingest:longmont-c2:session-25:20260808T005650Z"},
    )

    preview = persist_source_markdown(
        **kwargs,
        source_revision_id=requested,
        dry_run=True,
    )
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM source.revision").fetchone() == (0,)
    assert preview.source_revision_id == requested

    first = persist_source_markdown(**kwargs, source_revision_id=requested)
    second = persist_source_markdown(**kwargs, source_revision_id=requested)
    assert first.source_revision_id == requested
    assert second.source_revision_id == requested

    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM source.revision").fetchone() == (1,)

    current = persist_source_markdown(
        **kwargs,
        source_revision_id=requested,
        dry_run=True,
    )
    assert current.source_revision_id == requested
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM source.revision").fetchone() == (1,)

    with pytest.raises(ApplicationStateConflictError, match="different source revision"):
        persist_source_markdown(**kwargs, source_revision_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

    other_markdown = "# Other source\n"
    with pytest.raises(ApplicationStateConflictError, match="different source state"):
        persist_source_markdown(
            source_artifact_id="artifact:recap:longmont-c2:session-23:deadbeef",
            source_domain="recap",
            campaign_id="longmont-c2",
            session_id="session-23",
            world_id="eldyrwild",
            markdown=other_markdown,
            content_sha256=hashlib.sha256(other_markdown.encode("utf-8")).hexdigest(),
            source_revision_id=requested,
        )


def test_owned_source_metadata_is_batched_exact_and_read_only(application_state_dsn, monkeypatch):
    from application_state.source import repository, service
    ids = ['owned', 'foreign', 'unowned']
    for identity, owner in zip(ids, ['world:one', 'world:two', None]):
        persist_source_markdown(source_artifact_id=identity, source_domain='worldbuilding',
            world_id=owner, campaign_id=None, session_id=None, markdown='Private body ' + identity, lineage={})
    def snapshot():
        with psycopg.connect(application_state_dsn) as conn:
            return conn.execute('SELECT to_jsonb(a) FROM source.artifact a ORDER BY source_artifact_id').fetchall(), conn.execute('SELECT to_jsonb(r) FROM source.revision r ORDER BY source_artifact_id').fetchall()
    before = snapshot()
    calls = []
    query = repository.owned_source_artifacts
    def observed(conn, **fields):
        assert conn.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        calls.append(fields)
        return query(conn, **fields)
    monkeypatch.setattr(repository, 'owned_source_artifacts', observed)
    monkeypatch.setattr(repository, 'get_source_markdown', lambda *a, **kw: pytest.fail('Metadata must not load bodies'))
    assert service.owned_source_artifacts(source_artifact_ids=['owned', 'foreign', 'unowned', 'missing', 'owned'], world_id='world:one') == {'owned'}
    assert calls == [dict(source_artifact_ids=['owned', 'foreign', 'unowned', 'missing'], world_id='world:one')]
    assert snapshot() == before


def test_empty_owned_source_metadata_needs_no_database(monkeypatch):
    from application_state.source import service
    monkeypatch.setattr(service, 'load_runtime_dsn', lambda: pytest.fail('Empty metadata batch needs no database'))
    assert not service.owned_source_artifacts(source_artifact_ids=[], world_id='world:one')


def test_owned_source_metadata_storage_failure_propagates(application_state_dsn, monkeypatch):
    from application_state.source import repository, service
    def unavailable(*a, **kw):
        raise psycopg.OperationalError('Synthetic metadata store unavailable')
    monkeypatch.setattr(repository, 'owned_source_artifacts', unavailable)
    with pytest.raises(psycopg.OperationalError, match='Synthetic metadata'):
        service.owned_source_artifacts(source_artifact_ids=['owned'], world_id='world:one')
