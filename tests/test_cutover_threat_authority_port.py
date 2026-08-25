"""CUTOVER D.2A: World Graph authority port contract (no PostgreSQL)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from apps.live_control_server.ports.world_graph_authority import (
    AuthorityObject,
    WorldGraphAuthorityError,
    WorldGraphExpectedChildFacts,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
    WorldGraphRevisionView,
    WorldGraphVerificationResult,
)
from apps.live_control_server.services import threat_publication_identity as identity_svc
from apps.live_control_server.services import threat_publication_operations as ops_svc
from apps.live_control_server.services.threat_publication_operations import (
    GraphHeadUnavailable,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
THREAT_SERVICE_PATHS = (
    REPO_ROOT / "apps/live_control_server/services/threat_publication_operations.py",
    REPO_ROOT / "apps/live_control_server/services/threat_publication_identity.py",
    REPO_ROOT / "apps/live_control_server/services/threat_publication_proposals.py",
    REPO_ROOT / "apps/live_control_server/services/threat_publication_commits.py",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
)


class FakeWorldGraphAuthority:
    def __init__(self) -> None:
        self.heads: dict[str, str] = {}
        self.revisions: dict[tuple[str, str], WorldGraphRevisionView] = {}
        self.publications: dict[tuple[str, str], WorldGraphPublicationReceipt] = {}
        self.publish_calls = 0
        self.unavailable = False

    def current_head(self, world_id: str) -> WorldGraphHead:
        if self.unavailable:
            raise WorldGraphAuthorityError("authority down", code="authority_unavailable")
        revision_id = self.heads.get(world_id)
        if not revision_id:
            raise WorldGraphAuthorityError("no head", code="revision_unavailable")
        return WorldGraphHead(world_id=world_id, revision_id=revision_id)

    def read_revision(self, world_id: str, revision_id: str) -> WorldGraphRevisionView:
        if self.unavailable:
            raise WorldGraphAuthorityError("authority down", code="authority_unavailable")
        view = self.revisions.get((world_id, revision_id))
        if view is None:
            raise WorldGraphAuthorityError("missing revision", code="revision_unavailable")
        return view

    def publish(self, request: WorldGraphPublishRequest) -> WorldGraphPublicationReceipt:
        self.publish_calls += 1
        key = (request.world_id, request.authority_operation_id)
        existing = self.publications.get(key)
        if existing is not None:
            return existing
        head = self.current_head(request.world_id)
        if head.revision_id != request.expected_parent_revision_id:
            raise WorldGraphAuthorityError("stale parent", code="stale_parent")
        child = f"rev:child-{self.publish_calls}"
        receipt = WorldGraphPublicationReceipt(
            world_id=request.world_id,
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=request.expected_parent_revision_id,
            published_revision_id=child,
            reviewed_contribution_id=request.authority_operation_id,
            accepted_assertion_ids=request.accepted_assertion_ids,
            published=True,
            outcome="published",
        )
        self.publications[key] = receipt
        self.heads[request.world_id] = child
        parent_view = self.revisions.get(
            (request.world_id, request.expected_parent_revision_id)
        )
        objects = dict(parent_view.objects) if parent_view is not None else {}
        if request.threat_node_id:
            objects[request.threat_node_id] = AuthorityObject(
                object_id=request.threat_node_id,
                label=request.threat_node_id,
                kind="threat",
                role="threat",
            )
        self.revisions[(request.world_id, child)] = WorldGraphRevisionView(
            world_id=request.world_id,
            revision_id=child,
            parent_revision_id=request.expected_parent_revision_id,
            objects=objects,
            relationships=dict(parent_view.relationships) if parent_view else {},
        )
        return receipt

    def recover(
        self, world_id: str, authority_operation_id: str
    ) -> WorldGraphPublicationReceipt | None:
        return self.publications.get((world_id, authority_operation_id))

    def verify_child(
        self,
        *,
        receipt: WorldGraphPublicationReceipt,
        expected: WorldGraphExpectedChildFacts,
    ) -> WorldGraphVerificationResult:
        view = self.read_revision(receipt.world_id, receipt.published_revision_id)
        if expected.threat_node_id not in view.objects:
            return WorldGraphVerificationResult(
                status="failed", codes=("missing_threat_object",)
            )
        return WorldGraphVerificationResult(status="passed")


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def test_static_threat_services_have_no_direct_buddy_graph_runtime_imports():
    """Mounted Threat services must not import kernel/world_supergraph runtime."""
    forbidden: dict[str, list[str]] = {}
    for path in THREAT_SERVICE_PATHS:
        hits = [
            name
            for name in _imported_modules(path)
            if any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            )
        ]
        if hits:
            forbidden[str(path.relative_to(REPO_ROOT))] = hits
    assert forbidden == {}


def test_current_head_maps_typed_authority_failures(monkeypatch):
    fake = FakeWorldGraphAuthority()
    fake.unavailable = True
    monkeypatch.setattr(
        ops_svc, "get_world_graph_authority", lambda **_kwargs: fake
    )
    with pytest.raises(GraphHeadUnavailable):
        ops_svc._read_graph_head(Path("/tmp"), "world_1")


def test_current_head_returns_exact_revision(monkeypatch):
    fake = FakeWorldGraphAuthority()
    fake.heads["world_1"] = "rev:d-a"
    monkeypatch.setattr(
        ops_svc, "get_world_graph_authority", lambda **_kwargs: fake
    )
    assert ops_svc._read_graph_head(Path("/tmp"), "world_1") == "rev:d-a"


def test_occupancy_uses_exact_revision_not_projection(monkeypatch):
    hidden_id = "node:hidden-create-new"
    view = WorldGraphRevisionView(
        world_id="world_1",
        revision_id="rev:parent",
        parent_revision_id=None,
        objects={
            hidden_id: AuthorityObject(
                object_id=hidden_id,
                label="Hidden",
                kind="threat",
                role="threat",
            )
        },
        relationships={},
    )
    fake = FakeWorldGraphAuthority()
    fake.revisions[("world_1", "rev:parent")] = view
    monkeypatch.setattr(
        identity_svc, "get_world_graph_authority", lambda **_kwargs: fake
    )

    class _Snapshot:
        world_id = "world_1"

    class _Operation:
        source_snapshot = _Snapshot()
        expected_parent_revision_id = "rev:parent"

    assert identity_svc._exact_revision_contains_node_id(
        _Operation(), hidden_id, world_root=None
    )
    assert not identity_svc._exact_revision_contains_node_id(
        _Operation(), "node:absent", world_root=None
    )


def test_preflight_conflicting_resource_and_missing_connect_target():
    from types import SimpleNamespace

    from apps.live_control_server.services.threat_publication_proposals import (
        _run_exact_parent_preflight,
    )

    view = WorldGraphRevisionView(
        world_id="world_1",
        revision_id="rev:parent",
        parent_revision_id=None,
        objects={},
        relationships={},
    )
    operation = SimpleNamespace(
        source_snapshot=SimpleNamespace(
            accepted_mechanics_ref=SimpleNamespace(statblock_id="sb_abc")
        )
    )
    resolution = SimpleNamespace(
        selected_target=SimpleNamespace(
            node_id="node:missing-threat",
            label="Missing",
            kind="threat",
            role="threat",
            aliases=[],
            source_domains=[],
        ),
        created_node_id=None,
    )
    reason = _run_exact_parent_preflight(
        view,
        operation=operation,
        resolution=resolution,
        decision="connect_existing",
    )
    assert reason == "connect target missing at expected parent"


def test_publish_request_is_storage_neutral():
    request = WorldGraphPublishRequest(
        world_id="world_1",
        expected_parent_revision_id="rev:parent",
        authority_operation_id="contribution:abc",
        actor="gm@test",
        contribution={"contribution_id": "contribution:abc"},
    )
    dumped = request.__dict__
    assert "Postgres" not in str(dumped)
    assert "database" not in str(dumped).casefold()


def _install_fake_authority(monkeypatch, fake: FakeWorldGraphAuthority) -> None:
    def factory(**_kwargs):
        return fake

    monkeypatch.setattr(ops_svc, "get_world_graph_authority", factory)
    monkeypatch.setattr(identity_svc, "get_world_graph_authority", factory)
    from apps.live_control_server.services import threat_publication_proposals as proposal_svc
    from apps.live_control_server.services import threat_publication_commits as commit_svc
    from apps.live_control_server.ports import world_graph_authority_access as access

    monkeypatch.setattr(proposal_svc, "get_world_graph_authority", factory)
    monkeypatch.setattr(commit_svc, "get_world_graph_authority", factory)
    monkeypatch.setattr(access, "get_world_graph_authority", factory)


def _explode_buddy_graph_runtime(monkeypatch) -> None:
    import graph_memory.kernel as kernel
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority as wga,
    )
    from apps.live_control_server.services import threat_publication_commits as commit_svc

    def _explode(*_args, **_kwargs):
        raise AssertionError("Buddy World Graph runtime must not run on D.2A port path")

    monkeypatch.setattr(kernel, "open_current_world_graph", _explode)
    monkeypatch.setattr(kernel, "open_world_graph_head", _explode)
    monkeypatch.setattr(kernel, "load_world_graph_revision", _explode)
    monkeypatch.setattr(kernel, "load_world_graph_revision_with_integrity", _explode)
    monkeypatch.setattr(kernel, "merge_contribution_to_revision", _explode)
    monkeypatch.setattr(kernel, "find_world_graph_revisions_by_operation_id", _explode)
    monkeypatch.setattr(kernel, "rebuild_from_contributions", _explode)
    monkeypatch.setattr(kernel, "project_world_graph", _explode)
    monkeypatch.setattr(commit_svc.kernel, "open_current_world_graph", _explode)
    monkeypatch.setattr(wga, "hydrate_world_graph", _explode)
    monkeypatch.setattr(wga, "ensure_hydrated_authority", _explode)


def test_mounted_threat_lifecycle_with_buddy_graph_physically_absent(tmp_path, monkeypatch):
    """Handoff §16.10: begin → identity → proposal → confirm with no Buddy graph."""
    import uuid

    from graph_memory.world_supergraph import storage

    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.models.threat_publication import (
        BeginThreatPublicationOperationRequestV1,
    )
    from apps.live_control_server.models.threat_publication_commit import (
        ConfirmThreatPublicationRequestV1,
    )
    from apps.live_control_server.services import threat_publication_commits as commit_svc
    from apps.live_control_server.services import threat_publication_proposals as proposal_svc
    from apps.live_control_server.services.threat_draft_store import (
        attach_accepted_mechanics_ref,
    )
    from tests.test_threat_publication_proposals import (
        _create_draft,
        _create_new_resolution,
        _locator,
        _prepare_request,
    )
    parent = "rev:d-a"
    absent = tmp_path / "buddy-world-graph-absent"
    fake = FakeWorldGraphAuthority()
    fake.heads["world_1"] = parent
    fake.revisions[("world_1", parent)] = WorldGraphRevisionView(
        world_id="world_1",
        revision_id=parent,
        parent_revision_id=None,
        objects={},
        relationships={},
    )
    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setattr(
        "apps.live_control_server.config.world_graph_root", lambda: absent
    )
    monkeypatch.setattr(ops_svc, "world_graph_root", lambda: absent)
    monkeypatch.setattr(identity_svc, "world_graph_root", lambda: absent)
    monkeypatch.setattr(proposal_svc, "world_graph_root", lambda: absent)
    monkeypatch.setattr(commit_svc, "world_graph_root", lambda: absent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)

    draft = _create_draft(tmp_path)
    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(),
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    draft = attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=draft.version,
        locator=ref,
    )
    op_id = str(uuid.uuid4())
    begin = ops_svc.begin_publication_operation(
        tmp_path,
        draft.draft_id,
        BeginThreatPublicationOperationRequestV1.model_validate(
            {
                "operation_id": op_id,
                "expected_draft_version": draft.version,
                "expected_parent_revision_id": parent,
                "actor": "gm",
            }
        ),
    )
    assert begin.response.result_label == "publication_ready"
    assert not absent.exists()

    resolution_id, _resolution = _create_new_resolution(
        tmp_path, draft, op_id, parent
    )
    proposal_id = str(uuid.uuid4())
    prepared = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=absent,
    )
    assert prepared.response.result_label == "publication_proposal_ready"
    proposal = prepared.response.proposal
    assert proposal is not None

    first = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal.proposal_id,
        ConfirmThreatPublicationRequestV1.model_validate(
            {
                "commit_id": str(uuid.uuid4()),
                "sealed_proposal_digest": proposal.sealed_proposal_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "actor": "gm",
            }
        ),
        world_root=absent,
    )
    assert first.response.commit is not None
    assert first.response.result_label in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }
    child = first.response.commit.committed_revision_id
    assert child
    assert fake.publish_calls == 1

    retry = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal.proposal_id,
        ConfirmThreatPublicationRequestV1.model_validate(
            {
                "commit_id": first.response.commit.commit_id,
                "sealed_proposal_digest": proposal.sealed_proposal_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "actor": "gm",
            }
        ),
        world_root=absent,
    )
    assert retry.response.commit is not None
    assert retry.response.commit.committed_revision_id == child
    assert fake.publish_calls == 1
    assert not absent.exists()
