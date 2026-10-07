"""Focused tests for Graph Review DungeonMind source admission (D.2C4)."""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
    DungeonMindWorldGraphSourceAdmissionAdapter,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    WorldGraphSourceAdmissionError,
    WorldGraphSourceAdmissionRequest,
)
from dungeonmind.infrastructure.memory.repositories import InMemorySourceRepository

REPO_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(1970, 1, 1, tzinfo=UTC)
WORLD_ID = "the-glass-orchard"
CAMPAIGN_ID = "the-glass-orchard"
ARTIFACT_A = "artifact:worldbuilding:a"
ARTIFACT_B = "artifact:worldbuilding:b"
TOKEN = "sha256:" + ("ab" * 32)
ADAPTER_PATH = (
    REPO_ROOT
    / "apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py"
)
FORBIDDEN_IMPORT_PREFIXES = (
    "apps.live_control_server.integrations.dungeonmind.world_graph_writes",
    "apps.live_control_server.integrations.dungeonmind_kernel",
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
)
LEGACY_GRAPH_ENGINE_PREFIXES = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
)


def _buddy_artifact(*, artifact_id: str, world_id: str = WORLD_ID, campaign_id: str = CAMPAIGN_ID):
    return SimpleNamespace(
        source_artifact_id=artifact_id,
        source_domain="worldbuilding",
        campaign_id=campaign_id,
        session_id=None,
        uri=f"object://{artifact_id}",
        content_sha256="ab" * 32,
        artifact_kind="markdown",
        document_class="lore",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=world_id,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )


def _request(*, artifact_id: str, token: str = TOKEN) -> WorldGraphSourceAdmissionRequest:
    return WorldGraphSourceAdmissionRequest(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        source_artifact=_buddy_artifact(artifact_id=artifact_id),
        source_revision_token=token,
        source_uri=f"object://{artifact_id}",
    )


def test_prove_or_admit_writes_missing_pair_and_is_idempotent() -> None:
    sources = InMemorySourceRepository()
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(sources=sources)
    request = _request(artifact_id=ARTIFACT_A)
    first = adapter.prove_or_admit(request)
    assert first.source_artifact_id == ARTIFACT_A
    assert first.source_revision_id == TOKEN
    assert sources.get_artifact(ARTIFACT_A) is not None
    assert sources.get_revision(TOKEN) is not None
    snapshot = sources.get_provenance_snapshot(
        artifact_ids=[ARTIFACT_A],
        revision_ids=[first.source_revision_id],
    )
    assert snapshot.get_artifact(ARTIFACT_A) is not None
    assert snapshot.get_revision(first.source_revision_id) is not None
    second = adapter.prove_or_admit(request)
    assert second.source_revision_id == first.source_revision_id
    assert sources.get_artifact(ARTIFACT_A) is not None


def test_prove_or_admit_collision_seals_as_token_suffix() -> None:
    sources = InMemorySourceRepository()
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(sources=sources)
    first = adapter.prove_or_admit(_request(artifact_id=ARTIFACT_A))
    assert first.source_revision_id == TOKEN
    second = adapter.prove_or_admit(_request(artifact_id=ARTIFACT_B))
    assert second.source_revision_id == f"{TOKEN}::{ARTIFACT_B}"
    assert sources.get_revision(TOKEN).source_artifact_id == ARTIFACT_A
    assert sources.get_revision(second.source_revision_id).source_artifact_id == ARTIFACT_B
    proven = adapter.prove(
        world_id=WORLD_ID,
        source_artifact_id=ARTIFACT_B,
        source_revision_id=second.source_revision_id,
        source_revision_token=TOKEN,
    )
    assert proven.source_revision_id == second.source_revision_id


def test_prove_or_admit_fingerprint_conflict_fails_closed() -> None:
    sources = InMemorySourceRepository()
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(sources=sources)
    adapter.prove_or_admit(_request(artifact_id=ARTIFACT_A))
    conflict = WorldGraphSourceAdmissionRequest(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        source_artifact=_buddy_artifact(artifact_id=ARTIFACT_A),
        source_revision_token=TOKEN,
        source_uri="object://different-locator",
    )
    with pytest.raises(WorldGraphSourceAdmissionError) as exc:
        adapter.prove_or_admit(conflict)
    assert exc.value.code == "source_identity_conflict"


def test_prove_missing_pair_fails_closed() -> None:
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(sources=InMemorySourceRepository())
    with pytest.raises(WorldGraphSourceAdmissionError) as exc:
        adapter.prove(
            world_id=WORLD_ID,
            source_artifact_id=ARTIFACT_A,
            source_revision_id=TOKEN,
            source_revision_token=TOKEN,
        )
    assert exc.value.code == "source_not_admitted"


def test_source_admission_adapter_has_no_legacy_graph_engine_or_writes_imports() -> None:
    tree = ast.parse(ADAPTER_PATH.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = [
        name
        for name in imported
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        )
    ]
    assert forbidden == []


def test_prove_or_admit_works_when_legacy_graph_engine_imports_are_blocked() -> None:
    """Fresh interpreter: install blocker BEFORE importing the mounted adapter."""
    script = textwrap.dedent(
        f"""
        import sys
        from datetime import UTC, datetime
        from types import SimpleNamespace

        LEGACY = {LEGACY_GRAPH_ENGINE_PREFIXES!r}

        class _Block:
            def find_spec(self, fullname, path=None, target=None):
                if any(
                    fullname == p or fullname.startswith(p + ".")
                    for p in LEGACY
                ):
                    raise ImportError(f"blocked legacy graph engine import: {{fullname}}")
                return None

        sys.meta_path.insert(0, _Block())

        # Prove a fresh import of the mounted adapter does not pull kernel.
        from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
            DungeonMindWorldGraphSourceAdmissionAdapter,
        )
        from apps.live_control_server.ports.world_graph_source_admission import (
            WorldGraphSourceAdmissionRequest,
        )
        from dungeonmind.infrastructure.memory.repositories import InMemorySourceRepository

        for name in list(sys.modules):
            if any(name == p or name.startswith(p + ".") for p in LEGACY):
                raise SystemExit(f"legacy module loaded during adapter import: {{name}}")

        now = datetime(1970, 1, 1, tzinfo=UTC)
        world_id = {WORLD_ID!r}
        campaign_id = {CAMPAIGN_ID!r}
        artifact_id = {ARTIFACT_A!r}
        token = {TOKEN!r}
        artifact = SimpleNamespace(
            source_artifact_id=artifact_id,
            source_domain="worldbuilding",
            campaign_id=campaign_id,
            session_id=None,
            uri=f"object://{{artifact_id}}",
            content_sha256="ab" * 32,
            artifact_kind="markdown",
            document_class="lore",
            authority_state="reviewed",
            visibility_state="internal",
            world_id=world_id,
            workspace_document_id=None,
            workspace_document_revision=None,
            lineage={{}},
            status="active",
            created_at=now,
            updated_at=now,
        )
        request = WorldGraphSourceAdmissionRequest(
            world_id=world_id,
            campaign_id=campaign_id,
            source_artifact=artifact,
            source_revision_token=token,
            source_uri=f"object://{{artifact_id}}",
        )
        sources = InMemorySourceRepository()
        adapter = DungeonMindWorldGraphSourceAdmissionAdapter(sources=sources)
        admitted = adapter.prove_or_admit(request)
        assert admitted.source_artifact_id == artifact_id
        assert admitted.source_revision_id == token
        proven = adapter.prove(
            world_id=world_id,
            source_artifact_id=artifact_id,
            source_revision_id=admitted.source_revision_id,
            source_revision_token=token,
        )
        assert proven.source_revision_id == admitted.source_revision_id
        for name in list(sys.modules):
            if any(name == p or name.startswith(p + ".") for p in LEGACY):
                raise SystemExit(f"legacy module loaded during prove_or_admit: {{name}}")
        print("ok")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"fresh-import tripwire failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ok" in result.stdout


def test_internal_source_read_uses_the_same_resolved_revision_and_v1_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult

    result = WorldGraphSourceAnchorReadResult(
        outcome="enough", anchor_id="anchor:one", evidence_ref_id="evidence:one",
        source_artifact_id="artifact:one", source_span_ref_id="span:one",
        content="bound text", content_sha256="a" * 64,
    )
    resolution = SimpleNamespace(
        found=True, anchor=SimpleNamespace(
            source_revision_id="source-revision:one", can_open_source=True,
            evidence_ref_id="evidence:one", source_artifact_id="artifact:one",
            locator_identity="span:one",
        ), snapshot=SimpleNamespace(revision_id="graph:one"),
    )
    services = SimpleNamespace(
        binding=object(),
        retrieval=SimpleNamespace(resolve_source_anchor=lambda *_args, **_kwargs: resolution),
    )
    digests: list[str] = []
    monkeypatch.setattr(direct, "_map_retrieval_context", lambda *_args: object())
    monkeypatch.setattr(direct, "_dnd_anchor_id", lambda anchor_id: anchor_id)
    monkeypatch.setattr(direct, "_classify_locator_kind", lambda _anchor: "source_span")
    monkeypatch.setattr(direct, "_product_source_span_ref_id", lambda _anchor: "span:one")

    def digest(_services: object, revision_id: str) -> str:
        digests.append(revision_id)
        return "a" * 64

    monkeypatch.setattr(direct, "_source_revision_digest", digest)
    monkeypatch.setattr(
        direct, "_anchor_read_view",
        lambda *_args, revision_digest, **_kwargs: (
            result if revision_digest == "a" * 64 else pytest.fail("wrong digest")
        ),
    )
    request = SimpleNamespace(anchor_id="anchor:one")
    internal = direct.read_source_anchor_direct_v2(
        services, request, repo_root=REPO_ROOT,
    )
    assert internal.result is result
    assert internal.source_revision_id == "source-revision:one"
    assert internal.source_revision_sha256 == "a" * 64
    assert internal.evidence_ref_id == "evidence:one"
    assert internal.source_artifact_id == "artifact:one"
    assert internal.source_span_ref_id == "span:one"
    assert internal.locator_kind == "source_span"
    assert internal.locator_identity == "span:one"
    assert internal.graph_revision == "graph:one"
    assert digests == ["source-revision:one"]
    assert direct.read_source_anchor_direct(services, request, repo_root=REPO_ROOT) is result


def test_internal_source_read_receipt_binds_executors_id_and_rejects_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from graph_memory.interaction import expansion_executor as executor
    from graph_memory.interaction.session import (
        GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
    )
    from graph_memory.interaction.session_store import clear_sessions, create_session
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult

    clear_sessions()
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:one", campaign_id="", revision_id="graph:one",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)],
    )
    create_session(session)
    result = WorldGraphSourceAnchorReadResult.model_validate({
        "outcome": "truncated", "anchorId": "anchor:one",
        "evidenceRefId": "evidence:one", "sourceArtifactId": "artifact:one",
        "sourceSpanRefId": "span:one", "locatorKind": "source_span",
        "content": "bound text",
        "contentSha256": "a" * 64, "truncated": True,
        "snapshot": {
            "worldId": "world:one", "campaignId": "", "revisionId": "graph:one",
            "headRevisionId": "graph:one", "isHead": True,
            "focus": {"kind": "none"}, "admissibility": "gm", "scopeMode": "world",
        },
    })
    resolved = SimpleNamespace(
        result=result, source_revision_id="source-revision:one",
        source_revision_sha256="a" * 64,
        evidence_ref_id="evidence:one", source_artifact_id="artifact:one",
        source_span_ref_id="span:one", locator_kind="source_span",
        locator_identity="span:one", graph_revision="graph:one",
    )
    monkeypatch.setattr(
        executor.retrieval_service, "read_source_anchor_internal_v2",
        lambda *_args, **_kwargs: resolved,
    )
    request = {
        "retrievalSessionId": session.id, "anchorIds": ["anchor:one"],
        "maxChars": 12,
    }
    output = executor.execute_read_graph_source(request, receipt_version=2)
    item = output["reads"][0]
    receipt = item["receipt"]
    assert output["schema"] == "dmb_internal_read_graph_source_batch_v2"
    assert receipt["source_read_id"] == item["sourceReadId"]
    assert receipt["source_revision_id"] == "source-revision:one"
    assert receipt["source_revision_sha256"] == "a" * 64
    assert receipt["read_content_sha256"] == "a" * 64
    assert receipt["retrieval_session_id"] == session.id
    assert receipt["graph_revision"] == "graph:one"
    assert receipt["evidence_ref_id"] == "evidence:one"
    assert receipt["source_span_ref_id"] == "span:one"
    assert receipt["locator_kind"] == "source_span"
    assert receipt["locator_identity"] == "span:one"
    assert receipt["truncated"] is True
    assert session.source_reads[-1].receipt_v2 is not None
    assert session.source_reads[-1].receipt_v2.source_read_id == item["sourceReadId"]
    assert session.source_anchors[0].opened is True
    forged = executor.execute_read_graph_source({**request, "sourceRevisionId": "forged"})
    assert forged["code"] == "invalid_arguments"
    monkeypatch.setattr(
        executor.retrieval_service, "read_source_anchor",
        lambda *_args, **_kwargs: result,
    )
    legacy = executor.execute_read_graph_source(request)
    assert legacy == {
        **result.model_dump(mode="json", by_alias=True),
        "retrievalSessionId": session.id,
    }
    assert "receipt_v2" not in session.source_reads[-1].model_dump()
    clear_sessions()


@pytest.mark.parametrize(
    "tamper",
    ["graph_revision", "evidence_ref_id", "source_artifact_id", "source_span_ref_id", "source_revision_id", "locator_identity", "content_sha256"],
)
def test_internal_source_read_rejects_mismatched_authoritative_binding(
    monkeypatch: pytest.MonkeyPatch, tamper: str,
) -> None:
    from graph_memory.interaction import expansion_executor as executor
    from graph_memory.interaction.session import (
        GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
    )
    from graph_memory.interaction.session_store import clear_sessions, create_session
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult

    clear_sessions()
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:one", campaign_id="", revision_id="graph:one",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)],
    )
    create_session(session)
    result = WorldGraphSourceAnchorReadResult.model_validate({
        "outcome": "enough", "anchorId": "anchor:one",
        "evidenceRefId": "evidence:one", "sourceArtifactId": "artifact:one",
        "sourceSpanRefId": "span:one", "locatorKind": "source_span",
        "content": "bound text",
        "contentSha256": "a" * 64,
        "snapshot": {
            "worldId": "world:one", "campaignId": "", "revisionId": "graph:one",
            "headRevisionId": "graph:one", "isHead": True,
            "focus": {"kind": "none"}, "admissibility": "gm", "scopeMode": "world",
        },
    })
    resolved = {
        "result": result, "source_revision_id": "source-revision:one",
        "source_revision_sha256": "a" * 64,
        "evidence_ref_id": "evidence:one", "source_artifact_id": "artifact:one",
        "source_span_ref_id": "span:one", "locator_kind": "source_span",
        "locator_identity": "span:one", "graph_revision": "graph:one",
    }
    if tamper == "content_sha256":
        resolved["result"] = result.model_copy(update={"content_sha256": "b" * 64})
    else:
        resolved[tamper] = (
            None if tamper in {"source_revision_id", "locator_identity"} else "foreign"
        )
    monkeypatch.setattr(
        executor.retrieval_service, "read_source_anchor_internal_v2",
        lambda *_args, **_kwargs: SimpleNamespace(**resolved),
    )
    output = executor.execute_read_graph_source({
        "retrievalSessionId": session.id, "anchorIds": ["anchor:one"],
    }, receipt_version=2)
    assert output["reads"][0]["receipt"] is None
    assert output["reads"][0]["result"]["code"] == "source_receipt_unverifiable"
    assert session.source_anchors[0].opened is False
    clear_sessions()


def test_internal_json_pointer_read_keeps_revision_and_excerpt_digests_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from graph_memory.interaction import expansion_executor as executor
    from graph_memory.interaction.session import (
        GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
    )
    from graph_memory.interaction.session_store import clear_sessions, create_session
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult

    clear_sessions()
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:one", campaign_id="", revision_id="graph:one",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id="anchor:json", readable=True)],
    )
    create_session(session)
    result = WorldGraphSourceAnchorReadResult.model_validate({
        "outcome": "enough", "anchorId": "anchor:json",
        "evidenceRefId": "evidence:json", "sourceArtifactId": "artifact:json",
        "locatorKind": "json_pointer", "content": '{"fact": true}',
        "contentSha256": "b" * 64,
        "snapshot": {
            "worldId": "world:one", "campaignId": "", "revisionId": "graph:one",
            "headRevisionId": "graph:one", "isHead": True,
            "focus": {"kind": "none"}, "admissibility": "gm", "scopeMode": "world",
        },
    })
    monkeypatch.setattr(
        executor.retrieval_service, "read_source_anchor_internal_v2",
        lambda *_args, **_kwargs: SimpleNamespace(
            result=result, source_revision_id="source-revision:json",
            source_revision_sha256="a" * 64,
            evidence_ref_id="evidence:json", source_artifact_id="artifact:json",
            source_span_ref_id=None, locator_kind="json_pointer",
            locator_identity="/fact", graph_revision="graph:one",
        ),
    )
    output = executor.execute_read_graph_source({
        "retrievalSessionId": session.id, "anchorIds": ["anchor:json"],
    }, receipt_version=2)
    receipt = output["reads"][0]["receipt"]
    assert receipt["source_revision_sha256"] == "a" * 64
    assert receipt["read_content_sha256"] == "b" * 64
    assert receipt["source_span_ref_id"] is None
    assert receipt["locator_identity"] == "/fact"
    clear_sessions()


def test_internal_source_read_fails_closed_on_missing_or_stale_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from graph_memory.interaction import expansion_executor as executor
    from graph_memory.interaction.session import (
        GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
    )
    from graph_memory.interaction.session_store import clear_sessions, create_session
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult

    clear_sessions()
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:one", campaign_id="", revision_id="graph:one",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)],
    )
    create_session(session)
    result = WorldGraphSourceAnchorReadResult.model_validate({
        "outcome": "enough", "anchorId": "anchor:one", "content": "text",
        "contentSha256": "b" * 64, "locatorKind": "source_span",
        "snapshot": {
            "worldId": "world:one", "campaignId": "", "revisionId": "graph:stale",
            "headRevisionId": "graph:stale", "isHead": False,
            "focus": {"kind": "none"}, "admissibility": "gm", "scopeMode": "world",
        },
    })
    monkeypatch.setattr(
        executor.retrieval_service, "read_source_anchor_internal_v2",
        lambda *_args, **_kwargs: SimpleNamespace(
            result=result, source_revision_id=None, source_revision_sha256=None,
            evidence_ref_id=None, source_artifact_id=None,
            source_span_ref_id=None, locator_kind="source_span",
            locator_identity="span:one", graph_revision="graph:stale",
        ),
    )
    output = executor.execute_read_graph_source({
        "retrievalSessionId": session.id, "anchorIds": ["anchor:one"],
    }, receipt_version=2)
    assert output["reads"][0]["receipt"] is None
    assert output["reads"][0]["result"]["code"] == "source_receipt_unverifiable"
    assert session.source_anchors[0].opened is False
    assert session.source_reads[-1].receipt_v2 is None
    assert "receipt_v2" not in session.source_reads[-1].model_dump()
    denied = executor.execute_read_graph_source({
        "retrievalSessionId": session.id, "anchorIds": ["anchor:foreign"],
    }, receipt_version=2)
    assert denied["reads"][0]["receipt"] is None
    assert denied["reads"][0]["sourceReadId"] is None
    with pytest.raises(ValueError, match="unknown retrieval session"):
        executor.execute_read_graph_source({
            "retrievalSessionId": "grs:stale", "anchorIds": ["anchor:one"],
        }, receipt_version=2)
    clear_sessions()
