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
