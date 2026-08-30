"""CUTOVER D.2A: World Graph authority port contract (no PostgreSQL)."""


from __future__ import annotations


import ast
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace


import pytest


import apps.live_control_server.config as storage


from apps.live_control_server.models.threat_statblock_binding import (
    external_statblock_node_id,
)
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


def _contribution_fingerprint(contribution: object) -> str:
    if contribution is None:
        return ""
    if isinstance(contribution, dict):
        return repr(sorted(contribution.items()))
    parts = [str(getattr(contribution, "contribution_id", "") or "")]
    for item in list(getattr(contribution, "accepted_assertions", None) or []):
        if isinstance(item, dict):
            parts.append(repr(sorted(item.items())))
            continue
        parts.append(
            "|".join(
                str(getattr(item, key, "") or "")
                for key in (
                    "assertion_id",
                    "predicate",
                    "label",
                    "subject_object_id",
                    "target_object_id",
                )
            )
        )
    return "\n".join(parts)


class FakeWorldGraphAuthority:
    def __init__(self) -> None:
        self.heads: dict[str, str] = {}
        self.revisions: dict[tuple[str, str], WorldGraphRevisionView] = {}
        self.publications: dict[tuple[str, str], WorldGraphPublicationReceipt] = {}
        self._bindings: dict[tuple[str, str], tuple[str, str]] = {}
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
            stored_parent, stored_fp = self._bindings.get(key, (existing.parent_revision_id, ""))
            request_fp = _contribution_fingerprint(request.contribution)
            if stored_parent != request.expected_parent_revision_id or (
                stored_fp and stored_fp != request_fp
            ):
                raise WorldGraphAuthorityError(
                    "existing publication does not match the current request",
                    code="integrity_failure",
                    details={
                        "stored_parent_revision_id": stored_parent,
                        "requested_parent_revision_id": request.expected_parent_revision_id,
                    },
                )
            return replace(existing, outcome="already_applied")
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
        self._bindings[key] = (
            request.expected_parent_revision_id,
            _contribution_fingerprint(request.contribution),
        )
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
        self,
        world_id: str,
        authority_operation_id: str,
        *,
        expected_parent_revision_id: str | None = None,
        contribution: object | None = None,
        actor: str | None = None,
    ) -> WorldGraphPublicationReceipt | None:
        del actor
        existing = self.publications.get((world_id, authority_operation_id))
        if existing is None:
            return None
        stored_parent, stored_fp = self._bindings.get(
            (world_id, authority_operation_id),
            (existing.parent_revision_id, ""),
        )
        if (
            expected_parent_revision_id is not None
            and stored_parent != expected_parent_revision_id
        ):
            raise WorldGraphAuthorityError(
                "recovered publication parent does not match the durable request",
                code="integrity_failure",
            )
        if contribution is not None and stored_fp:
            if stored_fp != _contribution_fingerprint(contribution):
                raise WorldGraphAuthorityError(
                    "recovered publication contribution does not match the durable request",
                    code="integrity_failure",
                )
        return existing


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
    """Assert Buddy graph packages stay unimportable (physical deletion)."""
    import builtins


    real_import = builtins.__import__
    forbidden = (
        "graph_memory.kernel",
        "graph_memory.world_supergraph",
        "graph_memory.union_supergraph",
        "apps.live_control_server.integrations.buddy_files",
        "apps.live_control_server.integrations.dungeonmind_kernel",
    )


    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        full = name
        if any(full == p or full.startswith(p + ".") for p in forbidden):
            raise AssertionError(f"Buddy World Graph runtime must not run: import {full}")
        # also catch from graph_memory import kernel style via fromlist
        if name == "graph_memory" and fromlist:
            for item in fromlist:
                candidate = f"graph_memory.{item}"
                if any(candidate == p or candidate.startswith(p + ".") for p in forbidden):
                    raise AssertionError(
                        f"Buddy World Graph runtime must not run: import {candidate}"
                    )
        return real_import(name, globals, locals, fromlist, level)


    monkeypatch.setattr(builtins, "__import__", _guarded_import)


def test_mounted_threat_lifecycle_with_buddy_graph_physically_absent(tmp_path, monkeypatch):
    """Handoff §16.10: begin → identity → proposal → confirm with no Buddy graph."""
    import uuid


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
    from tests._threat_publication_helpers import (
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


def _publish_request(
    *,
    operation_id: str,
    parent: str,
    contribution: object,
    threat_node_id: str = "node:t1",
) -> WorldGraphPublishRequest:
    return WorldGraphPublishRequest(
        world_id="world_1",
        expected_parent_revision_id=parent,
        authority_operation_id=operation_id,
        actor="gm@test",
        contribution=contribution,
        threat_node_id=threat_node_id,
    )


def test_fake_publish_rejects_same_operation_id_with_changed_parent():
    fake = FakeWorldGraphAuthority()
    fake.heads["world_1"] = "rev:d-a"
    contrib = SimpleNamespace(contribution_id="op:1", accepted_assertions=[])
    first = fake.publish(_publish_request(operation_id="op:1", parent="rev:d-a", contribution=contrib))
    with pytest.raises(WorldGraphAuthorityError) as excinfo:
        fake.publish(
            _publish_request(
                operation_id="op:1",
                parent=first.published_revision_id,
                contribution=contrib,
            )
        )
    assert excinfo.value.code == "integrity_failure"
    assert fake.heads["world_1"] == first.published_revision_id


def test_fake_publish_rejects_same_operation_id_with_changed_contribution():
    fake = FakeWorldGraphAuthority()
    fake.heads["world_1"] = "rev:d-a"
    first_contrib = SimpleNamespace(
        contribution_id="op:1",
        accepted_assertions=[SimpleNamespace(assertion_id="a1", predicate="exists")],
    )
    first = fake.publish(
        _publish_request(operation_id="op:1", parent="rev:d-a", contribution=first_contrib)
    )
    changed = SimpleNamespace(
        contribution_id="op:1",
        accepted_assertions=[SimpleNamespace(assertion_id="a2", predicate="exists")],
    )
    with pytest.raises(WorldGraphAuthorityError) as excinfo:
        fake.publish(_publish_request(operation_id="op:1", parent="rev:d-a", contribution=changed))
    assert excinfo.value.code == "integrity_failure"
    retry = fake.publish(
        _publish_request(operation_id="op:1", parent="rev:d-a", contribution=first_contrib)
    )
    assert retry.outcome == "already_applied"
    assert retry.published_revision_id == first.published_revision_id


def test_fake_recover_rejects_changed_parent_and_contribution_bindings():
    fake = FakeWorldGraphAuthority()
    fake.heads["world_1"] = "rev:d-a"
    contrib = SimpleNamespace(
        contribution_id="op:1",
        accepted_assertions=[SimpleNamespace(assertion_id="a1", predicate="exists")],
    )
    first = fake.publish(_publish_request(operation_id="op:1", parent="rev:d-a", contribution=contrib))
    recovered = fake.recover(
        "world_1",
        "op:1",
        expected_parent_revision_id="rev:d-a",
        contribution=contrib,
        actor="gm@test",
    )
    assert recovered is not None
    assert recovered.published_revision_id == first.published_revision_id
    with pytest.raises(WorldGraphAuthorityError) as excinfo:
        fake.recover(
            "world_1",
            "op:1",
            expected_parent_revision_id=first.published_revision_id,
            contribution=contrib,
        )
    assert excinfo.value.code == "integrity_failure"
    changed = SimpleNamespace(
        contribution_id="op:1",
        accepted_assertions=[SimpleNamespace(assertion_id="a9", predicate="exists")],
    )
    with pytest.raises(WorldGraphAuthorityError) as excinfo:
        fake.recover(
            "world_1",
            "op:1",
            expected_parent_revision_id="rev:d-a",
            contribution=changed,
        )
    assert excinfo.value.code == "integrity_failure"


def test_derive_threat_review_operation_id_is_deterministic_reviewop():
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        derive_threat_review_operation_id,
    )


    first = derive_threat_review_operation_id(
        world_id="eldyrwild", authority_operation_id="contrib:abc"
    )
    again = derive_threat_review_operation_id(
        world_id="eldyrwild", authority_operation_id="contrib:abc"
    )
    assert first == again
    assert first.startswith("reviewop:")
    assert len(first) == len("reviewop:") + 32
    assert derive_threat_review_operation_id(
        world_id="eldyrwild", authority_operation_id=first
    ) == first
    assert derive_threat_review_operation_id(
        world_id="eldyrwild", authority_operation_id="contrib:other"
    ) != first


def test_replay_identity_helper_fails_closed_on_parent_or_digest_mismatch():
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WorldGraphWriteError,
        _assert_publication_replay_identity,
    )


    existing = SimpleNamespace(
        expected_parent_revision_id="rev:a",
        review_intent_sha256="intent-a",
        reviewed_contribution_sha256="hash-a",
        world_id="world_1",
        operation_id="op:1",
    )
    _assert_publication_replay_identity(
        existing=existing, expected_parent_revision_id="rev:a"
    )
    with pytest.raises(WorldGraphWriteError) as parent_exc:
        _assert_publication_replay_identity(
            existing=existing, expected_parent_revision_id="rev:other"
        )
    assert parent_exc.value.code == "governed_write_idempotency_conflict"
    with pytest.raises(WorldGraphWriteError) as digest_exc:
        _assert_publication_replay_identity(
            existing=existing,
            expected_parent_revision_id="rev:a",
            expected_review_intent_sha256="intent-other",
        )
    assert "review_intent_sha256" in digest_exc.value.details["mismatches"]


def test_world_graph_expressible_strips_resource_and_binding_assertions():
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        _world_graph_expressible,
    )


    class _Contribution:
        def __init__(self, assertions):
            self.accepted_assertions = assertions


        def model_copy(self, update):
            return _Contribution(update["accepted_assertions"])


    threat = SimpleNamespace(predicate="exists", value={"kind": "threat"})
    resource = SimpleNamespace(
        predicate="external_resource", value={"kind": "external_resource"}
    )
    binding = SimpleNamespace(
        predicate="uses_statblock", value={"threat_statblock_binding": {"id": "b1"}}
    )
    out = _world_graph_expressible(_Contribution([threat, resource, binding]))
    assert out.accepted_assertions == [threat]


def test_native_verify_child_proves_threat_object_not_resource_binding(monkeypatch):
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )


    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url="postgresql://unused")
    view = WorldGraphRevisionView(
        world_id="world_1",
        revision_id="rev:child",
        parent_revision_id="rev:parent",
        objects={
            "node:threat": AuthorityObject(
                object_id="node:threat",
                label="Threat",
                kind="threat",
                role="threat",
            )
        },
        relationships={},
    )
    monkeypatch.setattr(adapter, "read_revision", lambda *_args, **_kwargs: view)
    result = adapter.verify_child(
        receipt=WorldGraphPublicationReceipt(
            world_id="world_1",
            authority_operation_id="op:1",
            parent_revision_id="rev:parent",
            published_revision_id="rev:child",
            reviewed_contribution_id="op:1",
            accepted_assertion_ids=(),
            published=True,
            outcome="already_applied",
        ),
        expected=WorldGraphExpectedChildFacts(
            threat_node_id="node:threat",
            decision="create_new",
            external_resource_node_id="node:resource",
            binding_edge_id="edge:binding",
        ),
    )
    assert result.status == "passed"
    assert result.codes == ()


def test_exact_parent_preflight_still_rejects_incompatible_resource_on_revision_view():


    from apps.live_control_server.services.threat_publication_proposals import (
        _run_exact_parent_preflight,
    )


    resource_id = external_statblock_node_id("sb_abc")
    view = WorldGraphRevisionView(
        world_id="world_1",
        revision_id="rev:parent",
        parent_revision_id=None,
        objects={
            resource_id: AuthorityObject(
                object_id=resource_id,
                label="Wrong resource",
                kind="external_resource",
                role="statblock",
                external_resource={"provider": "other"},
            )
        },
        relationships={},
    )
    operation = SimpleNamespace(
        source_snapshot=SimpleNamespace(
            accepted_mechanics_ref=SimpleNamespace(statblock_id="sb_abc")
        )
    )
    resolution = SimpleNamespace(created_node_id="node:new-threat", selected_target=None)
    reason = _run_exact_parent_preflight(
        view,
        operation=operation,
        resolution=resolution,
        decision="create_new",
    )
    assert reason == "incompatible external resource already present"


def test_effect_summary_records_resource_binding_ids_from_accepted_mechanics():
    from apps.live_control_server.models.statblock_mechanics_acceptance import (
        AcceptedMechanicsRefV1,
    )
    from apps.live_control_server.services.threat_publication_proposals import (
        _effect_summary,
    )
    from tests._threat_publication_helpers import _locator


    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(),
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
    )
    summary = _effect_summary(
        decision="create_new",
        threat_node_id="node:threat",
        accepted_ref=ref,
        assertions=[],
    )
    assert summary.threat_node_id == "node:threat"
    assert summary.external_resource_node_id
    assert summary.binding_edge_id
    assert summary.external_resource_node_id != summary.binding_edge_id


def test_receipt_to_merge_result_keeps_buddy_operation_identity():
    from apps.live_control_server.services.threat_publication_commits import (
        _receipt_to_merge_result,
    )


    receipt = WorldGraphPublicationReceipt(
        world_id="eldyrwild",
        authority_operation_id="contrib:buddy-op",
        parent_revision_id="rev:d-a",
        published_revision_id="rev:d-b",
        reviewed_contribution_id="reviewop:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        accepted_assertion_ids=("assert:threat",),
        published=True,
        outcome="published",
    )
    result = _receipt_to_merge_result(
        receipt,
        fallback_assertion_ids=("assert:threat", "assert:resource", "assert:binding"),
    )
    assert result.contribution_ids == ["contrib:buddy-op"]
    assert result.accepted_assertion_ids == [
        "assert:threat",
        "assert:resource",
        "assert:binding",
    ]
    assert result.revision_id == "rev:d-b"


def test_qualified_assertion_update_clears_attribute_predicate():
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _qualified_assertion_update,
    )


    assertion = SimpleNamespace(
        assertion_kind="attribute",
        predicate="description",
        value={"text": "A brutal enforcer.", "source_domains": ["worldbuilding"]},
    )
    update = _qualified_assertion_update(assertion, endpoint_kinds={})
    assert update["predicate"] is None
    assert '"property_term":"description"' in update["value"]
    assert "brutal enforcer" in update["value"]
