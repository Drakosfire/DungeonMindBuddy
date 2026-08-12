"""CR03A — exact admitted worldbuilding SourceSpan reads via read_graph_source."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
    get_source_artifact,
    load_source_span_index,
    source_span_index_path,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
    get_object_evidence,
    read_source_anchor,
)
from apps.live_control_server.services.worldbuilding_source_span_read import (
    read_admitted_worldbuilding_span,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.interaction.answer_validator import validate_structured_answer
from graph_memory.interaction.expansion_executor import (
    ReadGraphSourceRequest,
    execute_read_graph_source,
)
from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.session import (
    GraphRetrievalSession,
    SessionSnapshot,
    SourceAnchorState,
)
from graph_memory.interaction.session_store import clear_sessions, create_session, get_session
from graph_memory.kernel.contribution_merge import _ensure_evidence
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.retrieval.models import (
    RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    WorldGraphEvidenceRequest,
    WorldGraphSourceAnchorReadRequest,
)
from graph_memory.retrieval.source_reader import SourceReadError, read_repo_line_span_text
from graph_memory.union_supergraph.model import (
    UnionSupergraphEvidence,
    UnionSupergraphSourceArtifact,
)
from src.live_play.live_store import load_json, write_json

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ACTOR = "gm"
GLASS_ORCHARD_WORLD_ID = "the-glass-orchard"

ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]

HESTA_NODE_ID = "npc:glass-orchard:hesta"
HESTA_MARKDOWN = (
    "---\n"
    'title: "Hesta"\n'
    "world: the-glass-orchard\n"
    "---\n"
    "\n"
    "Hesta tends the first orchard terrace near the glass kiln.\n"
    "\n"
    "She keeps a copper pruning knife etched with the harvest moon.\n"
    "\n"
    "Visitors rarely notice the knife until dusk.\n"
)


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _attestation() -> WorldInitializationApprovalAttestation:
    return WorldInitializationApprovalAttestation(
        bundle_id=BUNDLE_ID,
        bundle_digest=BUNDLE_DIGEST,
        approved_bundle_merge_sha=APPROVED_MERGE_SHA,
    )


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=_attestation(),
    )


def _initialize(root: Path, bundle) -> None:
    initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _commit_markdown(
    root: Path,
    *,
    document_id: str,
    markdown: str,
    expected_revision: int,
) -> None:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=expected_revision,
            write_mode="source_import",
        ),
    )
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=expected_revision,
            write_mode="source_import",
        ),
    )


def _setup_hesta_registry(root: Path) -> tuple[str, str, str, str]:
    """Return artifact_id, s1, s2, digest for Glass Orchard Hesta markdown.

    S1/S2 are body paragraphs selected by content (frontmatter also yields spans).
    """
    (root / "corpus" / "the-glass-orchard-markdown").mkdir(parents=True, exist_ok=True)
    record = create_workspace_document(
        root,
        title="Hesta Source",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        kind="worldbuilding_source",
        world_id=GLASS_ORCHARD_WORLD_ID,
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    _commit_markdown(
        root,
        document_id=record.document_id,
        markdown=HESTA_MARKDOWN,
        expected_revision=1,
    )
    artifact = create_source_artifact_from_workspace_document(
        root,
        document_id=record.document_id,
        expected_revision=2,
    )
    index = load_source_span_index(root, artifact.source_artifact_id)
    assert len(index.spans) >= 2
    artifact_path = root / artifact.uri.removeprefix("repo://")
    lines = artifact_path.read_text(encoding="utf-8").splitlines()

    def _span_text(span) -> str:
        return "\n".join(lines[span.start_line - 1 : span.end_line])

    body_spans = [
        span
        for span in index.spans
        if "copper pruning knife" in _span_text(span)
        or "first orchard terrace" in _span_text(span)
    ]
    assert len(body_spans) >= 2
    s1 = next(
        span.source_span_id
        for span in body_spans
        if "first orchard terrace" in _span_text(span)
    )
    s2 = next(
        span.source_span_id
        for span in body_spans
        if "copper pruning knife" in _span_text(span)
    )
    assert s1 != s2
    digest = (artifact.content_sha256 or "").lower()
    assert len(digest) == 64
    return artifact.source_artifact_id, s1, s2, digest


def _merge_hesta_worldbuilding(
    root: Path,
    *,
    artifact_id: str,
    digest: str,
    span_ids: list[str],
    uri: str | None = None,
    locator_only: bool = False,
) -> None:
    artifact = get_source_artifact(root, artifact_id)
    relative_uri = uri if uri is not None else artifact.uri
    evidence_rows = []
    for span_id in span_ids:
        row = {
            "evidence_ref_id": f"evidence:{artifact_id}:{span_id}",
            "source_artifact_id": artifact_id,
            "source_domain": "worldbuilding",
            "locator": span_id,
        }
        if not locator_only:
            row["source_span_ref_id"] = span_id
        evidence_rows.append(row)
    node_assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=HESTA_NODE_ID,
        label="Hesta",
        campaign_scope=CAMPAIGN_ID,
        source_artifact_id=artifact_id,
        value={
            "kind": "npc",
            "role": "npc",
            "source_domains": ["worldbuilding"],
            "aliases": ["Hesta"],
            "canon_state": "canonical",
            "evidence": evidence_rows,
            "source_artifacts": [
                {
                    "source_artifact_id": artifact_id,
                    "source_domain": "worldbuilding",
                    "campaign_id": CAMPAIGN_ID,
                    "uri": relative_uri,
                    "content_sha256": digest,
                }
            ],
        },
        evidence_ref_ids=[],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=artifact_id,
        source_revision_id=f"sha256:{digest}",
        accepted_assertions=[node_assertion],
        campaign_scope=CAMPAIGN_ID,
    )
    merged = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True


def _context() -> dict:
    return {
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "focus": {"kind": "none"},
        "admissibility": "gm",
        "revisionPin": None,
    }


def _anchor_read_request(
    anchor_id: str, *, max_chars: int = 4000
) -> WorldGraphSourceAnchorReadRequest:
    return WorldGraphSourceAnchorReadRequest.model_validate(
        {
            "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
            "anchorId": anchor_id,
            "maxChars": max_chars,
            **_context(),
        }
    )


def _hesta_anchors(root: Path):
    result = get_object_evidence(
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "target": {"kind": "node", "id": HESTA_NODE_ID},
                **_context(),
            }
        ),
        root=root,
    )
    return result.source_anchors


def test_sessionless_ensure_evidence_preserves_source_span_ref_id() -> None:
    evidence: dict[str, UnionSupergraphEvidence] = {}
    artifacts: dict[str, UnionSupergraphSourceArtifact] = {}
    span_id = "artifact:worldbuilding:doc:r1:abcdef:span:001"
    _ensure_evidence(
        evidence,
        artifacts,
        evidence_ref_id="evidence:test:sessionless-span",
        source_artifact_id="artifact:worldbuilding:doc:r1:abcdef",
        source_domain="worldbuilding",
        campaign_id="the-glass-orchard",
        session_id=None,
        locator=span_id,
        source_span_ref_id=span_id,
    )
    row = evidence["evidence:test:sessionless-span"]
    assert row.locator == span_id
    assert row.source_span_ref_id == span_id


def test_sessionless_ensure_evidence_does_not_invent_span() -> None:
    evidence: dict[str, UnionSupergraphEvidence] = {}
    artifacts: dict[str, UnionSupergraphSourceArtifact] = {}
    _ensure_evidence(
        evidence,
        artifacts,
        evidence_ref_id="evidence:test:no-span",
        source_artifact_id="artifact:worldbuilding:doc:r1:abcdef",
        source_domain="worldbuilding",
        campaign_id="the-glass-orchard",
        session_id=None,
        locator="contribution/evidence:test:no-span",
        source_span_ref_id=None,
    )
    row = evidence["evidence:test:no-span"]
    assert row.source_span_ref_id is None
    assert row.locator == "contribution/evidence:test:no-span"


def test_legacy_locator_as_span_reads_exact_s2(tmp_path: Path, loaded_bundle) -> None:
    """#567 sessionless graphs stored S only in locator; recover without inventing."""
    _initialize(tmp_path, loaded_bundle)
    artifact_id, s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path,
        artifact_id=artifact_id,
        digest=digest,
        span_ids=[s1, s2],
        locator_only=True,
    )
    anchors = _hesta_anchors(tmp_path)
    assert len(anchors) >= 2
    for anchor in anchors:
        assert anchor.locator_kind == "source_span"
        assert anchor.readable is True
        assert anchor.source_span_ref_id in {s1, s2}
    g2 = next(a for a in anchors if a.source_span_ref_id == s2)
    result = read_source_anchor(
        _anchor_read_request(g2.anchor_id),
        root=tmp_path,
        repo_root=tmp_path,
    )
    assert result.outcome == "enough"
    assert result.source_span_ref_id == s2
    assert "copper pruning knife" in (result.content or "")
    assert "first orchard terrace" not in (result.content or "")


def test_g2_reads_exact_s2_not_s1(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_id, s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s1, s2]
    )
    anchors = _hesta_anchors(tmp_path)
    assert len(anchors) >= 2
    for anchor in anchors:
        assert anchor.locator_kind == "source_span"
        assert anchor.readable is True
        assert anchor.source_span_ref_id in {s1, s2}
    g2 = next(a for a in anchors if a.source_span_ref_id == s2)
    result = read_source_anchor(
        _anchor_read_request(g2.anchor_id),
        root=tmp_path,
        repo_root=tmp_path,
    )
    assert result.outcome == "enough"
    assert result.source_span_ref_id == s2
    assert "copper pruning knife" in (result.content or "")
    assert "first orchard terrace" not in (result.content or "")
    assert result.content_sha256 == digest
    assert result.line_start is not None and result.line_start > 3


def test_foreign_revision_denied(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_id, s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s1, s2]
    )
    g2 = next(a for a in _hesta_anchors(tmp_path) if a.source_span_ref_id == s2)
    request = WorldGraphSourceAnchorReadRequest.model_validate(
        {
            "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
            "anchorId": g2.anchor_id,
            "maxChars": 4000,
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "focus": {"kind": "none"},
            "admissibility": "gm",
            "revisionPin": "revision:does-not-exist",
        }
    )
    with pytest.raises(WorldGraphRetrievalServiceError) as exc_info:
        read_source_anchor(request, root=tmp_path, repo_root=tmp_path)
    assert "revision" in str(exc_info.value).lower() or exc_info.value.code


def test_caller_extras_rejected() -> None:
    with pytest.raises(ValidationError):
        ReadGraphSourceRequest.model_validate(
            {
                "schema": "dmb_read_graph_source_request_v1",
                "retrievalSessionId": "sess:1",
                "anchorIds": ["anchor:1"],
                "sourceArtifactId": "artifact:forged",
            }
        )
    with pytest.raises(ValidationError):
        ReadGraphSourceRequest.model_validate(
            {
                "schema": "dmb_read_graph_source_request_v1",
                "retrievalSessionId": "sess:1",
                "anchorIds": ["anchor:1"],
                "path": "corpus/secret.md",
            }
        )
    with pytest.raises(ValidationError):
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "anchorId": "anchor:1",
                "sourceSpanRefId": "span:forged",
                **_context(),
            }
        )


def test_graph_vs_registry_digest_mismatch_fail_closed(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_id, _s1, s2, digest = _setup_hesta_registry(tmp_path)
    forged = "a" * 64
    assert forged != digest
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=forged, span_ids=[s2]
    )
    g = _hesta_anchors(tmp_path)[0]
    with pytest.raises(WorldGraphRetrievalServiceError) as exc_info:
        read_source_anchor(
            _anchor_read_request(g.anchor_id),
            root=tmp_path,
            repo_root=tmp_path,
        )
    assert exc_info.value.code == "source_integrity_error"


def test_span_belongs_to_other_artifact_fail_closed(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_a, _s1_a, _s2_a, digest_a = _setup_hesta_registry(tmp_path)
    other_md = (
        "---\ntitle: \"Other\"\n---\n\n"
        "Foreign paragraph one.\n\nForeign paragraph two with knife lore.\n"
    )
    record = create_workspace_document(
        tmp_path,
        title="Other Source",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        kind="worldbuilding_source",
        world_id=GLASS_ORCHARD_WORLD_ID,
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    _commit_markdown(
        tmp_path,
        document_id=record.document_id,
        markdown=other_md,
        expected_revision=1,
    )
    artifact_b = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=2,
    )
    index_b = load_source_span_index(tmp_path, artifact_b.source_artifact_id)
    s_b = index_b.spans[0].source_span_id
    _merge_hesta_worldbuilding(
        tmp_path,
        artifact_id=artifact_a,
        digest=digest_a,
        span_ids=[s_b],
    )
    g = _hesta_anchors(tmp_path)[0]
    with pytest.raises(WorldGraphRetrievalServiceError) as exc_info:
        read_source_anchor(
            _anchor_read_request(g.anchor_id),
            root=tmp_path,
            repo_root=tmp_path,
        )
    assert exc_info.value.code in {
        "source_span_not_found",
        "source_integrity_error",
    }


def test_span_index_digest_mismatch_fail_closed(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_id, _s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s2]
    )
    index_path = source_span_index_path(tmp_path, artifact_id)
    payload = load_json(index_path)
    payload["content_sha256"] = "b" * 64
    write_json(index_path, payload)
    g = _hesta_anchors(tmp_path)[0]
    with pytest.raises(WorldGraphRetrievalServiceError) as exc_info:
        read_source_anchor(
            _anchor_read_request(g.anchor_id),
            root=tmp_path,
            repo_root=tmp_path,
        )
    assert exc_info.value.code in {"source_span_index_error", "source_integrity_error"}


def test_current_source_digest_drift_no_content(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_id, _s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s2]
    )
    artifact = get_source_artifact(tmp_path, artifact_id)
    relative = artifact.uri.removeprefix("repo://")
    path = tmp_path / relative
    path.write_text(path.read_text(encoding="utf-8") + "\nDrifted prose.\n", encoding="utf-8")
    g = next(a for a in _hesta_anchors(tmp_path) if a.source_span_ref_id == s2)
    with pytest.raises(WorldGraphRetrievalServiceError) as exc_info:
        read_source_anchor(
            _anchor_read_request(g.anchor_id),
            root=tmp_path,
            repo_root=tmp_path,
        )
    assert exc_info.value.code == "source_integrity_error"


def test_path_escape_rejected(tmp_path: Path) -> None:
    with pytest.raises(SourceReadError) as exc_info:
        read_repo_line_span_text(
            repo_root=tmp_path,
            relative_path="../etc/passwd",
            start_line=1,
            end_line=1,
            max_chars=100,
            expected_content_sha256="a" * 64,
        )
    assert exc_info.value.code == "unsupported_locator"


def test_max_chars_truncation(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    artifact_id, _s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s2]
    )
    g2 = next(a for a in _hesta_anchors(tmp_path) if a.source_span_ref_id == s2)
    result = read_source_anchor(
        _anchor_read_request(g2.anchor_id, max_chars=12),
        root=tmp_path,
        repo_root=tmp_path,
    )
    assert result.outcome == "truncated"
    assert result.truncated is True
    assert result.content is not None
    assert len(result.content) == 12
    assert result.line_start == result.line_end


def test_foreign_session_anchor_denied(tmp_path: Path, loaded_bundle) -> None:
    clear_sessions()
    _initialize(tmp_path, loaded_bundle)
    artifact_id, s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s1, s2]
    )
    g2 = next(a for a in _hesta_anchors(tmp_path) if a.source_span_ref_id == s2)
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            revision_id="revision:test",
        ),
        question="What knife does Hesta keep?",
        source_anchors=[
            SourceAnchorState(
                anchor_id="source-anchor:v1:" + "f" * 64,
                readable=True,
                locator_kind="source_span",
            )
        ],
    )
    create_session(session)
    result = execute_read_graph_source(
        {
            "schema": "dmb_read_graph_source_request_v1",
            "retrievalSessionId": session.id,
            "anchorIds": [g2.anchor_id],
        },
        root=tmp_path,
    )
    assert result["outcome"] == "denied"
    assert result.get("content") is None
    codes = {d.get("code") for d in result.get("diagnostics") or []}
    assert "anchor_not_in_session" in codes


def test_successful_source_citation_and_no_claim_mutation(
    tmp_path: Path, loaded_bundle
) -> None:
    clear_sessions()
    _initialize(tmp_path, loaded_bundle)
    artifact_id, s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s1, s2]
    )
    g2 = next(a for a in _hesta_anchors(tmp_path) if a.source_span_ref_id == s2)
    evidence = get_object_evidence(
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "target": {"kind": "node", "id": HESTA_NODE_ID},
                **_context(),
            }
        ),
        root=tmp_path,
    )
    revision_id = evidence.snapshot.revision_id if evidence.snapshot else "revision:test"
    identity_claim = GraphClaim(
        claim_id="assertion:hesta-identity",
        claim_kind="identity",
        authority_class="gm_authored_accepted_assertion",
        revision_id=revision_id,
        subject_node_id=HESTA_NODE_ID,
        subject_label="Hesta",
        predicate="identity",
        value_text="Hesta",
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            revision_id=revision_id,
        ),
        question="What knife does Hesta keep?",
        source_anchors=[
            SourceAnchorState(
                anchor_id=g2.anchor_id,
                readable=True,
                locator_kind="source_span",
            )
        ],
        claims=[identity_claim],
    )
    create_session(session)
    claims_before = [c.model_dump(mode="json") for c in session.claims]
    result = execute_read_graph_source(
        {
            "schema": "dmb_read_graph_source_request_v1",
            "retrievalSessionId": session.id,
            "anchorIds": [g2.anchor_id],
        },
        root=tmp_path,
    )
    assert result["outcome"] in {"enough", "truncated"}
    assert "copper pruning knife" in (result.get("content") or "")
    assert result.get("sourceSpanRefId") == s2
    refreshed = get_session(session.id)
    assert refreshed is not None
    claims_after = [c.model_dump(mode="json") for c in refreshed.claims]
    assert claims_after == claims_before
    assert len(refreshed.source_reads) == 1
    assert refreshed.source_reads[0].outcome in {"enough", "truncated"}
    validated = validate_structured_answer(
        refreshed,
        None,
        model_prose="Hesta keeps a copper pruning knife etched with the harvest moon.",
    )
    assert validated.source_citations
    assert validated.source_citations[0].source_artifact_id == artifact_id
    assert validated.outcome == "source_verified"


def test_failed_read_produces_no_source_citation(tmp_path: Path, loaded_bundle) -> None:
    clear_sessions()
    _initialize(tmp_path, loaded_bundle)
    artifact_id, _s1, s2, digest = _setup_hesta_registry(tmp_path)
    _merge_hesta_worldbuilding(
        tmp_path, artifact_id=artifact_id, digest=digest, span_ids=[s2]
    )
    artifact = get_source_artifact(tmp_path, artifact_id)
    relative = artifact.uri.removeprefix("repo://")
    path = tmp_path / relative
    path.write_text(path.read_text(encoding="utf-8") + "\nChanged.\n", encoding="utf-8")
    g2 = next(a for a in _hesta_anchors(tmp_path) if a.source_span_ref_id == s2)
    evidence = get_object_evidence(
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "target": {"kind": "node", "id": HESTA_NODE_ID},
                **_context(),
            }
        ),
        root=tmp_path,
    )
    revision_id = evidence.snapshot.revision_id if evidence.snapshot else "revision:test"
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            revision_id=revision_id,
        ),
        question="What knife?",
        source_anchors=[
            SourceAnchorState(
                anchor_id=g2.anchor_id,
                readable=True,
                locator_kind="source_span",
            )
        ],
        claims=[],
    )
    create_session(session)
    result = execute_read_graph_source(
        {
            "schema": "dmb_read_graph_source_request_v1",
            "retrievalSessionId": session.id,
            "anchorIds": [g2.anchor_id],
        },
        root=tmp_path,
    )
    assert result.get("content") is None
    refreshed = get_session(session.id)
    assert refreshed is not None
    validated = validate_structured_answer(
        refreshed, None, model_prose="No trustworthy source detail."
    )
    assert validated.source_citations == []


def test_registry_reader_frontmatter_line_numbers(tmp_path: Path) -> None:
    (tmp_path / "corpus" / "the-glass-orchard-markdown").mkdir(parents=True)
    artifact_id, _s1, s2, digest = _setup_hesta_registry(tmp_path)
    index = load_source_span_index(tmp_path, artifact_id)
    span2 = next(s for s in index.spans if s.source_span_id == s2)
    assert span2.start_line > 3
    result = read_admitted_worldbuilding_span(
        root=tmp_path,
        source_artifact_id=artifact_id,
        source_span_ref_id=s2,
        graph_content_sha256=digest,
        max_chars=4000,
        anchor_id="source-anchor:v1:" + "1" * 64,
    )
    assert result.line_start == span2.start_line
    assert result.line_end == span2.end_line
    assert "copper pruning knife" in (result.content or "")


def test_hermes_tool_description_mentions_worldbuilding_spans() -> None:
    from apps.live_control_server.services.hermes_graph_interaction_tools import (
        hermes_graph_interaction_tool_definitions,
    )

    tools = hermes_graph_interaction_tool_definitions()
    read_tool = next(t for t in tools if t["function"]["name"] == "read_graph_source")
    description = read_tool["function"]["description"].lower()
    assert "worldbuilding" in description
    assert "path" in description
