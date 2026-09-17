"""Recap source-read continuity: canonical span identity survives write → read.

Localization: the frozen candidate and contribution already carry a first-class
``source_span_ref_id``. ``_recap_extraction_evidence_view`` was dropping it and
stamping the revision file URI onto both ``locator`` and ``uri``. DungeonMind's
v1→v2 lift copies those fields and hardcodes ``source_span_ref_id=None``.
Ordinary source-read then classified the replay-shaped anchor as
``unsupported_locator``.

This module never treats ``evidence_ref_id`` as a hidden locator protocol.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    _map_contribution_evidence_ref,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    _classify_locator_kind,
    _product_source_span_ref_id,
    _read_admitted_repo_span,
    _source_anchor_views,
    extract_span_from_revision_bound_text,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    _recap_extraction_evidence_view,
)
from dungeonmind.application.graph_snapshot import GraphEvidenceRecord
from dungeonmind.application.world_graph_retrieval import SourceAnchorMetadata
from dungeonmind.contracts.evidence import SourceDomain
from graph_memory.retrieval.models import (
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    WorldGraphRetrievalTrustBoundary,
    WorldGraphSourceAnchorReadRequest,
)
from graph_memory.source_span import build_stable_source_span_id
from tests.test_candidate_graph_admission_contract import _candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ID = "artifact:recap:longmont-c2:session-22:ad4ecd013dad"
SPAN_ID = f"{ARTIFACT_ID}:span:ad4ecd013dad:16-16"
EVIDENCE_ID = f"evidence:{ARTIFACT_ID}:{SPAN_ID}"
REPO_URI = (
    "repo://out/registries/source_content/recap/longmont-c2/"
    "session-22/ad4ecd013dad.md"
)
TOKEN = "sha256:" + ("ab" * 32)

pytest_plugins = ("tests.application_state.conftest",)


def _digest_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _assertion(
    *,
    evidence_ref_id: str = EVIDENCE_ID,
    span_id: str | None = SPAN_ID,
    artifact_id: str = ARTIFACT_ID,
    include_embedded: bool = True,
) -> SimpleNamespace:
    embedded: list[dict[str, Any]] = []
    if include_embedded:
        row: dict[str, Any] = {
            "evidence_ref_id": evidence_ref_id,
            "source_artifact_id": artifact_id,
            "source_domain": "recap",
        }
        if span_id is not None:
            row["source_span_ref_id"] = span_id
        embedded.append(row)
    return SimpleNamespace(
        source_artifact_id=artifact_id,
        source_revision_id=TOKEN,
        evidence_ref_ids=[evidence_ref_id],
        value={"evidence": embedded} if include_embedded else {},
    )


def _contribution(assertion: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        accepted_assertions=[assertion],
        candidate_assertions=[],
        rejected_assertions=[],
    )


class _FakeSources:
    def __init__(self, locator: str = REPO_URI, digest: str | None = None) -> None:
        self.locator = locator
        self.digest = digest

    def get_revision(self, revision_id: str) -> SimpleNamespace | None:
        if self.digest is None and self.locator is None:
            return None
        return SimpleNamespace(locator=self.locator, content_sha256=self.digest)


def _mapped_recap_evidence(
    *,
    span_id: str | None = SPAN_ID,
    include_embedded: bool = True,
    evidence_ref_id: str = EVIDENCE_ID,
) -> Any:
    assertion = _assertion(
        evidence_ref_id=evidence_ref_id,
        span_id=span_id,
        include_embedded=include_embedded,
    )
    view = _recap_extraction_evidence_view(
        _contribution(assertion),
        pair_to_dm={(ARTIFACT_ID, TOKEN): TOKEN},
        sources=_FakeSources(),
    )
    return _map_contribution_evidence_ref(
        view,
        evidence_ref_id,
        fallback_source_artifact_id=ARTIFACT_ID,
        source_revision_id=TOKEN,
    )


def _evidence_record(
    *,
    domain: str = "session_recap",
    evidence_ref_id: str = EVIDENCE_ID,
) -> GraphEvidenceRecord:
    return GraphEvidenceRecord(
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=ARTIFACT_ID,
        source_revision_id=TOKEN,
        source_domain=domain,
        can_open_source=True,
        can_highlight_span=True,
        locator=SPAN_ID,
        uri=REPO_URI,
    )


def _anchor(
    *,
    locator_identity: str,
    source_span_ref_id: str | None = None,
    uri: str = REPO_URI,
    domain: str = "session_recap",
    evidence_ref_id: str = EVIDENCE_ID,
    can_open_source: bool = True,
) -> SourceAnchorMetadata:
    return SourceAnchorMetadata(
        anchor_id="source-anchor:v1:test-recap-span",
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=ARTIFACT_ID,
        source_revision_id=TOKEN,
        locator_identity=locator_identity,
        source_span_ref_id=source_span_ref_id,
        can_open_source=can_open_source,
        can_highlight_span=bool(source_span_ref_id or locator_identity),
        supporting_object_ids=(),
        supporting_relationship_ids=(),
        supporting_assertion_ids=(),
        evidence=_evidence_record(domain=domain, evidence_ref_id=evidence_ref_id),
        artifact=SimpleNamespace(uri=uri),
    )


def _read_request() -> WorldGraphSourceAnchorReadRequest:
    return WorldGraphSourceAnchorReadRequest.model_validate(
        {
            "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
            "worldId": "world:recap-source-read-continuity",
            "campaignId": "longmont-c2",
            "anchorId": "source-anchor:v1:test-recap-span",
            "maxChars": 4000,
        }
    )


def _read_base(**overrides: Any) -> dict[str, Any]:
    payload = {
        "snapshot": None,
        "anchor_id": "source-anchor:v1:test-recap-span",
        "evidence_ref_id": EVIDENCE_ID,
        "source_artifact_id": ARTIFACT_ID,
        "source_domain": "session_recap",
        "source_span_ref_id": SPAN_ID,
        "locator_kind": "source_span",
        "trust_boundary": WorldGraphRetrievalTrustBoundary(),
    }
    payload.update(overrides)
    return payload


def test_write_stamps_canonical_span_onto_locator_not_file_uri() -> None:
    mapped = _mapped_recap_evidence()
    assert mapped.source_domain == SourceDomain.SESSION_RECAP
    assert mapped.locator == SPAN_ID
    assert mapped.uri == REPO_URI
    assert mapped.can_highlight_span is True
    assert mapped.can_open_source is True


def test_write_does_not_parse_span_out_of_evidence_ref_id() -> None:
    mapped = _mapped_recap_evidence(span_id=None, include_embedded=True)
    assert mapped.locator == REPO_URI
    assert mapped.uri == REPO_URI
    assert mapped.can_highlight_span is False


def test_write_without_embedded_evidence_does_not_invent_span() -> None:
    mapped = _mapped_recap_evidence(include_embedded=False)
    assert mapped.locator == REPO_URI
    assert mapped.can_highlight_span is False


def test_classifier_uses_locator_identity_for_recap_digest_bound_span() -> None:
    anchor = _anchor(locator_identity=SPAN_ID, source_span_ref_id=None)
    assert _product_source_span_ref_id(anchor) == SPAN_ID
    assert _classify_locator_kind(anchor) == "source_span"
    views = _source_anchor_views([anchor], revision_id="rev:child")
    assert views[0].source_span_ref_id == SPAN_ID
    assert views[0].locator_kind == "source_span"
    assert views[0].readable is True


def test_classifier_keeps_replay_shaped_file_uri_unsupported() -> None:
    anchor = _anchor(locator_identity=REPO_URI, source_span_ref_id=None)
    assert _product_source_span_ref_id(anchor) is None
    assert _classify_locator_kind(anchor) == "unsupported"


def test_classifier_ignores_span_syntax_inside_evidence_ref_id() -> None:
    decoy = f"evidence:{ARTIFACT_ID}:{SPAN_ID}"
    anchor = _anchor(
        locator_identity=REPO_URI,
        source_span_ref_id=None,
        evidence_ref_id=decoy,
    )
    assert SPAN_ID in decoy
    assert _product_source_span_ref_id(anchor) is None
    assert _classify_locator_kind(anchor) == "unsupported"


def test_heading_and_json_pointer_locators_are_unchanged() -> None:
    heading = _anchor(
        locator_identity="heading:Mireward",
        source_span_ref_id=None,
        uri="repo://corpus/notes.md",
    )
    assert _classify_locator_kind(heading) == "heading"
    pointer = _anchor(
        locator_identity="jsonptr:/nodes/0",
        source_span_ref_id=None,
        uri="graph-data://payload.json",
    )
    assert _classify_locator_kind(pointer) == "json_pointer"
    unknown = _anchor(
        locator_identity="https://example.invalid/recap",
        source_span_ref_id=None,
        uri="https://example.invalid/recap",
    )
    assert _classify_locator_kind(unknown) == "unsupported"


def test_worldbuilding_still_requires_explicit_source_span_ref_id() -> None:
    anchor = _anchor(
        locator_identity=SPAN_ID,
        source_span_ref_id=None,
        domain="worldbuilding",
    )
    assert _classify_locator_kind(anchor) == "unsupported"


def test_extract_span_returns_exact_digest_bound_line() -> None:
    digest = "ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f"
    lines = [f"line-{index}" for index in range(1, 20)]
    text = "\n".join(lines) + "\n"
    extracted = extract_span_from_revision_bound_text(
        text=text, span_id=SPAN_ID, digest=digest
    )
    assert extracted == ("line-16", 16, 16)


def test_extract_span_rejects_unknown_and_mismatched_identities() -> None:
    digest = "ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f"
    text = "only one line\n"
    assert (
        extract_span_from_revision_bound_text(
            text=text, span_id=SPAN_ID, digest=digest
        )
        is None
    )
    other = f"{ARTIFACT_ID}:span:ffffffffffff:1-1"
    assert (
        extract_span_from_revision_bound_text(
            text=text, span_id=other, digest=digest
        )
        is None
    )
    assert (
        extract_span_from_revision_bound_text(
            text=text,
            span_id="session-9:recap:paragraph:009",
            digest=digest,
        )
        is None
    )


def test_admitted_repo_span_read_is_digest_verified(tmp_path: Path) -> None:
    relative = "out/registries/source_content/recap/longmont-c2/session-22/ad4ecd013dad.md"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    lines = [f"line-{index}" for index in range(1, 20)]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    digest = _digest_hex(payload)
    span = build_stable_source_span_id(
        source_artifact_id=ARTIFACT_ID,
        content_sha256=digest,
        start_line=16,
        end_line=16,
    )
    services = SimpleNamespace(
        bundle=SimpleNamespace(sources=_FakeSources(locator=f"repo://{relative}", digest=digest))
    )
    anchor = _anchor(
        locator_identity=span,
        source_span_ref_id=None,
        uri=f"repo://{relative}",
    )
    result = _read_admitted_repo_span(
        services,
        anchor,
        request=_read_request(),
        repo_root=tmp_path,
        base=_read_base(source_span_ref_id=span),
    )
    assert result.outcome == "enough"
    assert result.content == "line-16"
    assert result.content_sha256 == digest
    assert result.line_start == 16
    assert result.line_end == 16


def test_admitted_repo_span_fails_closed_on_tampered_bytes(tmp_path: Path) -> None:
    relative = "out/registries/source_content/recap/longmont-c2/session-22/ad4ecd013dad.md"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    original = b"The marsh town sits on the river.\n"
    path.write_bytes(original)
    digest = _digest_hex(original)
    span = build_stable_source_span_id(
        source_artifact_id=ARTIFACT_ID,
        content_sha256=digest,
        start_line=1,
        end_line=1,
    )
    services = SimpleNamespace(
        bundle=SimpleNamespace(sources=_FakeSources(locator=f"repo://{relative}", digest=digest))
    )
    path.write_bytes(b"tampered recap bytes\n")
    result = _read_admitted_repo_span(
        services,
        _anchor(locator_identity=span, source_span_ref_id=None, uri=f"repo://{relative}"),
        request=_read_request(),
        repo_root=tmp_path,
        base=_read_base(),
    )
    assert result.outcome == "unavailable"
    assert result.content is None
    assert result.content_sha256 is None
    assert [item.code for item in result.diagnostics] == ["source_integrity_error"]


def test_admitted_repo_span_fails_closed_when_revision_missing(tmp_path: Path) -> None:
    services = SimpleNamespace(
        bundle=SimpleNamespace(sources=_FakeSources(locator=REPO_URI, digest=None))
    )
    services.bundle.sources.get_revision = lambda _rid: None  # type: ignore[method-assign]
    result = _read_admitted_repo_span(
        services,
        _anchor(locator_identity=SPAN_ID, source_span_ref_id=None),
        request=_read_request(),
        repo_root=tmp_path,
        base=_read_base(),
    )
    assert result.outcome == "unavailable"
    assert result.content is None
    assert result.diagnostics[0].code == "unsupported_locator"


def _span_candidate(*, artifact_id: str, span_id: str, node_id: str, campaign_id: str, session_id: str) -> dict:
    candidate = copy.deepcopy(_candidate())
    candidate["campaign_id"] = campaign_id
    candidate["session_id"] = session_id
    candidate["source_artifact_ids"] = [artifact_id]
    node = candidate["nodes"][0]
    node["node_id"] = node_id
    node["label"] = node_id.rsplit(":", 1)[-1].replace("-", " ").title()
    node["node_type"] = "location" if "mireward" in node_id else "character"
    ref = node["evidence_refs"][0]
    ref["source_artifact_id"] = artifact_id
    ref["source_span_ref_id"] = span_id
    ref["source_ref_id"] = f"{artifact_id}:text"
    return candidate


def _artifact(
    *,
    uri: str,
    content_sha256: str,
    source_artifact_id: str,
    campaign_id: str,
    session_id: str,
    world_id: str,
) -> SimpleNamespace:
    from datetime import UTC, datetime

    return SimpleNamespace(
        source_artifact_id=source_artifact_id,
        source_domain="recap",
        campaign_id=campaign_id,
        session_id=session_id,
        uri=uri,
        content_sha256=content_sha256,
        artifact_kind="markdown",
        document_class="recap",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=world_id,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


def _confirm_via_product_seam(prepared: SimpleNamespace) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        confirm_extract_promote_via_dungeonmind,
    )
    from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest
    from apps.live_control_server.services.candidate_graph_admission import (
        confirm_candidate_graph_admission,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )

    assertion_ids = [
        str(item["assertion_id"])
        for item in (prepared.package.get("effect") or {}).get("accepted_proposals")
        or []
        if item.get("assertion_id")
    ]
    request = ExtractPromoteConfirmRequest(
        review_package=prepared.package,
        assertion_ids=assertion_ids,
    )
    return confirm_candidate_graph_admission(
        review_package=prepared.package,
        candidate_graph=prepared.candidate,
        source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(
            database_url=prepared.dsn
        ),
        governed_confirm=lambda: confirm_extract_promote_via_dungeonmind(
            request,
            database_url=prepared.dsn,
            confirming_principal="recap-source-read-continuity",
            assertion_ids=tuple(assertion_ids),
            repo_root=prepared.repo,
        ),
    )


def _prepare_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
    *,
    world_id: str,
    campaign_id: str,
    session_id: str,
    node_id: str,
    recap_text: str,
    parent_revision_id: str | None = None,
    genesis: SimpleNamespace | None = None,
) -> SimpleNamespace:
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        bind_identity_ledger_to_package,
    )
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        prepare_candidate_graph_admission,
    )
    from apps.live_control_server.services.recap_world_genesis import (
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import (
        TRUNCATE_SQL,
        ensure_migrated,
        require_test_dsn,
    )
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn
    )
    dsn = require_test_dsn()
    ensure_migrated(dsn)
    database = PostgresDatabase(dsn)
    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    if genesis is None:
        with database.connect() as conn:
            conn.execute(TRUNCATE_SQL)
            conn.commit()
        repo.mkdir()
        world_root.mkdir()
        from apps.live_control_server import config as wg_config

        monkeypatch.setenv(
            wg_config.WORLD_GRAPH_AUTHORITY_ENV,
            wg_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
        )
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
        registry = (
            repo
            / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
        )
        registry.parent.mkdir(parents=True)
        shutil.copyfile(
            REPO_ROOT
            / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json",
            registry,
        )
        genesis_authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
        genesis_plan = prepare_recap_world_genesis(
            RecapWorldGenesisPrepareRequest(
                world_id=world_id,
                campaign_id="longmont-c1",
                baseline_roster_key="1",
                requested_by="recap-source-read-continuity",
            ),
            repo=repo,
            authority=genesis_authority,
        )
        published_genesis = confirm_recap_world_genesis(
            RecapWorldGenesisConfirmRequest(
                plan=genesis_plan, confirming_principal="recap-source-read-continuity"
            ),
            repo=repo,
            authority=genesis_authority,
        )
        parent = published_genesis.published_revision_id
    else:
        dsn = genesis.dsn
        repo = genesis.repo
        parent = parent_revision_id or genesis.d0

    digest = _digest_hex(recap_text.encode("utf-8"))
    artifact_id = f"artifact:recap:{campaign_id}:{session_id}:{digest[:12]}"
    relative = (
        f"out/registries/source_content/recap/{campaign_id}/{session_id}/{digest}.md"
    )
    source = repo / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(recap_text, encoding="utf-8")
    uri = f"repo://{relative}"
    span_id = build_stable_source_span_id(
        source_artifact_id=artifact_id,
        content_sha256=digest,
        start_line=1,
        end_line=1,
    )
    candidate = _span_candidate(
        artifact_id=artifact_id,
        span_id=span_id,
        node_id=node_id,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    candidate_path = tmp_path / f"{campaign_id}-{session_id}.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    graph_authority = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    context = graph_authority.mutation_context(world_id, parent)
    recap = _artifact(
        uri=uri,
        content_sha256=digest,
        source_artifact_id=artifact_id,
        campaign_id=campaign_id,
        session_id=session_id,
        world_id=world_id,
    )
    result = prepare_candidate_graph_admission(
        candidate_graph=candidate,
        source_uri=uri,
        source_revision_id=f"sha256:{digest}",
        prepared_by="recap-source-read-continuity",
        world_id=world_id,
        source_artifact_id=artifact_id,
        source_artifact=recap,
        campaign_scope=campaign_id,
        repo_root=repo,
        mutation_context=context,
        candidate_graph_path=str(candidate_path),
        source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn),
    )
    package = bind_identity_ledger_to_package(result.review_package, context)
    return SimpleNamespace(
        dsn=dsn,
        repo=repo,
        world_id=world_id,
        d0=parent if genesis is None else genesis.d0,
        parent=parent,
        graph_authority=graph_authority,
        candidate=candidate,
        package=package,
        result=result,
        artifact_id=artifact_id,
        span_id=span_id,
        digest=digest,
        node_id=node_id,
        campaign_id=campaign_id,
        uri=uri,
    )


@pytest.mark.integration
def test_fresh_recap_publication_source_read_is_digest_verified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        build_direct_world_graph_read_services,
        get_evidence_direct,
        get_object_direct,
        read_source_anchor_direct,
    )
    from graph_memory.retrieval.models import (
        RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
        RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        WorldGraphEvidenceRequest,
        WorldGraphObjectRequest,
        WorldGraphSourceAnchorReadRequest,
    )

    world_id = "world:recap-source-read-continuity"
    c2 = _prepare_session(
        tmp_path,
        monkeypatch,
        application_state_dsn,
        world_id=world_id,
        campaign_id="longmont-c2",
        session_id="session-22",
        node_id="node:location:mireward",
        recap_text="The marsh town of Mireward sits on the river.\n",
    )
    assert c2.result.confirmable is True
    published_c2 = _confirm_via_product_seam(c2)
    c2_rev = published_c2["committed_revision_id"]
    services = build_direct_world_graph_read_services(c2.dsn, world_id)
    found = get_object_direct(
        services,
        WorldGraphObjectRequest.model_validate(
            {
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "nodeId": "node:location:mireward",
            }
        ),
    )
    assert found.outcome != "empty"
    evidence = get_evidence_direct(
        services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "node:location:mireward"},
            }
        ),
    )
    assert evidence.source_anchors
    anchor = evidence.source_anchors[0]
    assert anchor.source_span_ref_id == c2.span_id
    assert anchor.locator_kind == "source_span"
    read = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "anchorId": anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert read.outcome in {"enough", "truncated"}
    assert read.content_sha256 == c2.digest
    assert read.content is not None
    assert "Mireward sits on the river" in read.content
    assert read.source_span_ref_id == c2.span_id

    replay = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "anchorId": anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert replay.content == read.content
    assert replay.content_sha256 == read.content_sha256

    c1 = _prepare_session(
        tmp_path,
        monkeypatch,
        application_state_dsn,
        world_id=world_id,
        campaign_id="longmont-c1",
        session_id="session-10",
        node_id="node:character:torbin",
        recap_text="Torbin keeps the historical pin honest.\n",
        parent_revision_id=c2_rev,
        genesis=c2,
    )
    published_c1 = _confirm_via_product_seam(c1)
    c1_rev = published_c1["committed_revision_id"]
    assert c1_rev != c2_rev
    historical = get_evidence_direct(
        services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "node:location:mireward"},
            }
        ),
    )
    historical_anchor = historical.source_anchors[0]
    historical_read = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "anchorId": historical_anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert historical_read.outcome in {"enough", "truncated"}
    assert historical_read.content_sha256 == c2.digest
    assert historical_read.snapshot is not None
    assert historical_read.snapshot.revision_id == c2_rev
    assert historical_read.snapshot.head_revision_id == c1_rev
    assert "Torbin" not in (historical_read.content or "")

    c1_services = build_direct_world_graph_read_services(c1.dsn, world_id)
    c1_evidence = get_evidence_direct(
        c1_services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c1",
                "revisionPin": c1_rev,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "node:character:torbin"},
            }
        ),
    )
    c1_anchor = c1_evidence.source_anchors[0]
    c1_read = read_source_anchor_direct(
        c1_services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c1",
                "revisionPin": c1_rev,
                "scopeMode": "world",
                "anchorId": c1_anchor.anchor_id,
            }
        ),
        repo_root=c1.repo,
    )
    assert c1_read.outcome in {"enough", "truncated"}
    assert c1_read.content_sha256 == c1.digest
    assert "Torbin keeps the historical pin honest" in (c1_read.content or "")

    foreign = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c1",
                "revisionPin": c1_rev,
                "scopeMode": "world",
                "anchorId": anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert foreign.outcome in {"empty", "partial", "unavailable", "denied"}
    assert foreign.content is None
