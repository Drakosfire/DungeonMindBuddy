"""Worldbuilding authority-port contract with disposable application-state PostgreSQL."""


from __future__ import annotations

from application_state.world_catalog.service import get_world
from tests.application_state.world_catalog_fixtures import store_world, world_snapshot, change_binding


import ast
import hashlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace


import pytest


import apps.live_control_server.config as storage


from apps.live_control_server.ports.world_graph_authority import (
    AuthorityEvidenceRef,
    AuthorityObject,
    AuthorityRelationship,
    WorldGraphAuthorityError,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
    WorldGraphRevisionView,
    WorldGraphVerificationResult,
)
from graph_memory.extract_promote_ops import DEFAULT_WORLD_ID
from apps.live_control_server.models.world_graph_mutation_context import (
    WORLDBUILDING_IDENTITY_SNAPSHOT_SCHEMA,
    MutationObject,
    WorldGraphMutationContext,
    identity_snapshot_from_context,
)
from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
from graph_memory.worldbuilding_write_plan import (
    WorldbuildingWritePlanError,
    build_worldbuilding_write_plan,
)
from graph_memory.extraction.worldbuilding_extraction_profile import (
    DEFAULT_SEMANTIC_STATE,
)
from tests._cutover_d3a_blocker_safe_fixtures import _candidate_graph_payload


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str, monkeypatch) -> str:
    from dungeonmind.infrastructure.memory import InMemorySourceRepository
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports import world_graph_authority_access as access
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(
        sources=InMemorySourceRepository(), world_graph=SimpleNamespace(
            get_head=lambda world: SimpleNamespace(
                head_revision_id=access.get_world_graph_authority().current_head(world).revision_id)),
    )
    monkeypatch.setattr(
        "apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority",
        lambda: adapter,
    )
    return application_state_dsn


REPO_ROOT = Path(__file__).resolve().parents[1]


def _preview() -> object:
    payload = _candidate_graph_payload(session_id=None)
    payload["preview_id"] = "preview:worldbuilding-write-plan"
    payload["source_artifact_ids"] = ["artifact:worldbuilding:test"]
    payload["session_id"] = None
    for index, node in enumerate(payload["nodes"]):
        node["node_id"] = f"wb_node_{index}"
        node["node_type"] = "character" if index == 0 else "location"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for edge in payload["edges"]:
        edge["edge_id"] = "wb_edge_0"
        edge["from_node_id"] = "wb_node_0"
        edge["to_node_id"] = "wb_node_1"
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    return candidate_graph_preview_from_dict(payload)


def _dispositions(*, edge: str = "accept") -> list[dict[str, str]]:
    return [
        {"assertion_id": "wb_node_0", "decision": "create_new"},
        {"assertion_id": "wb_node_1", "decision": "create_new"},
        {"assertion_id": "wb_edge_0", "decision": edge},
    ]
WORLDBUILDING_SERVICE_PATHS = (
    REPO_ROOT / "apps/live_control_server/services/worldbuilding_graph_publication.py",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
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
                    "assertion_kind",
                    "predicate",
                    "subject_node_id",
                    "target_node_id",
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
        self.identity: dict[str, dict[str, object]] = {}
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


    def mutation_context(
        self,
        world_id: str,
        revision_id: str,
        *,
        sealed_identity_snapshot=None,
    ) -> WorldGraphMutationContext:
        view = self.read_revision(world_id, revision_id)
        objects = {
            object_id: MutationObject(
                object_id=obj.object_id,
                label=obj.label,
                kind=obj.kind,
                aliases=obj.aliases,
                canon_state="canonical",
                memory_state="graph_read_model",
            )
            for object_id, obj in view.objects.items()
        }
        head_id = self.heads.get(world_id, revision_id)
        base = WorldGraphMutationContext(
            world_id=world_id,
            revision_id=revision_id,
            head_revision_id=head_id,
            objects=objects,
        )
        if sealed_identity_snapshot is not None:
            from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
                _identity_decision_prefix_key,
            )
            from apps.live_control_server.models.world_graph_mutation_context import (
                mutation_context_with_sealed_identity,
            )


            live_decisions = [
                dict(item)
                for item in list((self.identity.get(world_id) or {}).get("decisions") or [])
                if isinstance(item, dict)
            ]
            sealed_decisions = [
                dict(item)
                for item in list(sealed_identity_snapshot.get("decisions") or [])
                if isinstance(item, dict)
            ]
            if len(sealed_decisions) > len(live_decisions):
                raise WorldGraphAuthorityError(
                    "sealed identity snapshot invents decisions absent from the ledger",
                    code="inexpressible",
                )
            for index, sealed in enumerate(sealed_decisions):
                if _identity_decision_prefix_key(sealed) != _identity_decision_prefix_key(
                    live_decisions[index]
                ):
                    raise WorldGraphAuthorityError(
                        "sealed identity snapshot is not the prepare-time ledger prefix",
                        code="inexpressible",
                    )
            return mutation_context_with_sealed_identity(base, sealed_identity_snapshot)
        live = dict(self.identity.get(world_id) or {})
        redirects = {
            str(source): str(target)
            for source, target in dict(live.get("identity_redirects") or {}).items()
        }
        alias_owners = {
            str(alias): tuple(str(owner) for owner in list(owners))
            for alias, owners in dict(live.get("alias_owners") or {}).items()
        }
        ledger = tuple(dict(item) for item in list(live.get("decisions") or []))
        return WorldGraphMutationContext(
            world_id=world_id,
            revision_id=revision_id,
            head_revision_id=head_id,
            objects=objects,
            alias_owners=alias_owners,
            identity_redirects=redirects,
            identity_ledger_records=ledger,
        )


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
                )
            return replace(existing, outcome="already_applied")
        head = self.current_head(request.world_id)
        if head.revision_id != request.expected_parent_revision_id:
            raise WorldGraphAuthorityError("stale parent", code="stale_parent")
        child = f"rev:child-{self.publish_calls}"
        fingerprint = _contribution_fingerprint(request.contribution)
        receipt = WorldGraphPublicationReceipt(
            world_id=request.world_id,
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=request.expected_parent_revision_id,
            published_revision_id=child,
            reviewed_contribution_id=request.authority_operation_id,
            accepted_assertion_ids=request.accepted_assertion_ids,
            published=True,
            outcome="published",
            reviewed_contribution_sha256=hashlib.sha256(
                fingerprint.encode("utf-8")
            ).hexdigest(),
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
        relationships = dict(parent_view.relationships) if parent_view else {}
        evidence_refs = dict(parent_view.evidence_refs) if parent_view else {}
        contribution_id = str(
            getattr(request.contribution, "contribution_id", "") or receipt.reviewed_contribution_id
        )
        for assertion in list(getattr(request.contribution, "accepted_assertions", None) or []):
            kind = str(getattr(assertion, "assertion_kind", "") or "")
            subject = str(getattr(assertion, "subject_node_id", "") or "")
            target = str(getattr(assertion, "target_node_id", "") or "")
            predicate = str(getattr(assertion, "predicate", "") or "")
            assertion_id = str(getattr(assertion, "assertion_id", "") or "")
            value = getattr(assertion, "value", None) or {}
            if not isinstance(value, dict):
                value = dict(getattr(value, "__dict__", {}) or {})
            if kind == "node" and subject:
                objects[subject] = AuthorityObject(
                    object_id=subject,
                    label=str(value.get("label") or subject),
                    kind=str(value.get("kind") or "object"),
                )
            elif kind == "attribute" and subject:
                existing = objects.get(subject)
                if existing is None:
                    continue
                evidence_ids = [
                    str(item).strip()
                    for item in list(getattr(assertion, "evidence_ref_ids", None) or [])
                    if str(item).strip()
                ]
                if not evidence_ids:
                    evidence_ids = [
                        f"evidence:{receipt.reviewed_contribution_id}:{subject}"
                    ]
                for evidence_id in evidence_ids:
                    evidence_refs[evidence_id] = AuthorityEvidenceRef(
                        evidence_ref_id=evidence_id,
                        evidence_role="support",
                        locator=f"contribution/{contribution_id}/{subject}",
                    )
            elif kind == "alias" and subject:
                existing = objects.get(subject)
                if existing is None:
                    continue
                alias = str(value.get("alias") or getattr(assertion, "label", "") or "")
                aliases = list(existing.aliases)
                if alias and alias not in aliases:
                    aliases.append(alias)
                objects[subject] = replace(existing, aliases=tuple(aliases))
            elif kind == "edge" and subject and target:
                rel_id = assertion_id or f"rel:{subject}:{predicate}:{target}"
                relationships[rel_id] = AuthorityRelationship(
                    relationship_id=rel_id,
                    subject_object_id=subject,
                    target_object_id=target,
                    predicate=predicate,
                )
        self.revisions[(request.world_id, child)] = WorldGraphRevisionView(
            world_id=request.world_id,
            revision_id=child,
            parent_revision_id=request.expected_parent_revision_id,
            objects=objects,
            relationships=relationships,
            evidence_refs=evidence_refs,
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
        operation_namespace: str = "threat",
    ) -> WorldGraphPublicationReceipt | None:
        del actor, operation_namespace
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


    def verify_child(self, *, receipt, expected) -> WorldGraphVerificationResult:
        del expected
        self.read_revision(receipt.world_id, receipt.published_revision_id)
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


def _empty_parent(world_id: str = DEFAULT_WORLD_ID, revision_id: str = "rev:d-a") -> WorldGraphRevisionView:
    return WorldGraphRevisionView(
        world_id=world_id,
        revision_id=revision_id,
        parent_revision_id=None,
        objects={},
        relationships={},
    )


def _memory_context(
    *,
    revision_id: str = "rev:d-a",
    head_revision_id: str | None = None,
    objects: dict[str, MutationObject] | None = None,
    identity_redirects: dict[str, str] | None = None,
    identity_ledger_records: tuple[dict, ...] = (),
    alias_owners: dict[str, tuple[str, ...]] | None = None,
) -> WorldGraphMutationContext:
    return WorldGraphMutationContext(
        world_id=DEFAULT_WORLD_ID,
        revision_id=revision_id,
        head_revision_id=head_revision_id or revision_id,
        objects=objects or {},
        alias_owners=alias_owners or {},
        identity_redirects=identity_redirects or {},
        identity_ledger_records=identity_ledger_records,
    )


def _plan_kwargs(context: WorldGraphMutationContext, dispositions=None):
    return {
        "preview": _preview(),
        "mutation_context": context,
        "world_id": DEFAULT_WORLD_ID,
        "expected_parent_revision_id": context.revision_id,
        "run_id": "extraction-run:worldbuilding-d2b",
        "source_artifact_id": "artifact:worldbuilding:test",
        "source_revision_id": "sha256:abc",
        "source_uri": "repo://Docs/worldbuilding.md",
        "extraction_profile": "worldbuilding_shepherds_flock_v0@0.1",
        "campaign_scope": "longmont-c2",
        "dispositions": dispositions or _dispositions(),
        "require_current_head": True,
    }


def test_static_worldbuilding_service_has_no_identity_checkpoint_registry():
    source = WORLDBUILDING_SERVICE_PATHS[0].read_text(encoding="utf-8")
    assert "worldbuilding_identity_checkpoints" not in source
    assert "out/registries" not in source


def test_static_worldbuilding_services_have_no_direct_buddy_graph_runtime_imports():
    forbidden: dict[str, list[str]] = {}
    for path in WORLDBUILDING_SERVICE_PATHS:
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


def test_create_new_free_id_on_pure_mutation_context():
    plan = build_worldbuilding_write_plan(**_plan_kwargs(_memory_context()))
    assert plan.effect["identity_authority"]["schema"] == WORLDBUILDING_IDENTITY_SNAPSHOT_SCHEMA
    assert plan.effect["node_id_map"]["wb_node_0"] == "wb_node_0"


def test_create_new_object_conflict_on_pure_mutation_context():
    context = _memory_context(
        objects={
            "wb_node_0": MutationObject(
                object_id="wb_node_0",
                label="Taken",
                kind="npc",
                canon_state="canonical",
                memory_state="graph_read_model",
            )
        }
    )
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        build_worldbuilding_write_plan(**_plan_kwargs(context))
    assert exc.value.code == "new_node_id_conflict"


def test_create_new_active_redirect_conflict_on_pure_mutation_context():
    context = _memory_context(identity_redirects={"wb_node_0": "npc:canonical"})
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        build_worldbuilding_write_plan(**_plan_kwargs(context))
    assert exc.value.code == "new_node_id_conflict"


def test_bind_existing_success_and_kind_mismatch_on_pure_mutation_context():
    target = MutationObject(
        object_id="npc:exact-target",
        label="Exact",
        kind="npc",
        aliases=("Exact",),
        canon_state="canonical",
        memory_state="graph_read_model",
    )
    ok = _memory_context(objects={target.object_id: target}, alias_owners={"Exact": (target.object_id,)})
    dispositions = [
        {"assertion_id": "wb_node_0", "decision": "bind_existing", "target_node_id": target.object_id},
        {"assertion_id": "wb_node_1", "decision": "create_new"},
        {"assertion_id": "wb_edge_0", "decision": "accept"},
    ]
    plan = build_worldbuilding_write_plan(**_plan_kwargs(ok, dispositions=dispositions))
    assert plan.effect["node_id_map"]["wb_node_0"] == target.object_id


    missing = _memory_context()
    with pytest.raises(WorldbuildingWritePlanError) as missing_exc:
        build_worldbuilding_write_plan(**_plan_kwargs(missing, dispositions=dispositions))
    assert missing_exc.value.code == "bind_target_missing"


    wrong_kind = MutationObject(
        object_id="loc:wrong",
        label="Place",
        kind="location",
        canon_state="canonical",
        memory_state="graph_read_model",
    )
    mismatched = _memory_context(objects={wrong_kind.object_id: wrong_kind})
    wrong_dispositions = [
        {"assertion_id": "wb_node_0", "decision": "bind_existing", "target_node_id": wrong_kind.object_id},
        {"assertion_id": "wb_node_1", "decision": "create_new"},
        {"assertion_id": "wb_edge_0", "decision": "accept"},
    ]
    with pytest.raises(WorldbuildingWritePlanError) as kind_exc:
        build_worldbuilding_write_plan(**_plan_kwargs(mismatched, dispositions=wrong_dispositions))
    assert kind_exc.value.code == "bind_target_kind_mismatch"


def test_bind_redirected_merged_rejected_and_provisional_targets_fail_closed():
    redirected = _memory_context(
        objects={
            "npc:source": MutationObject(
                object_id="npc:source",
                label="Source",
                kind="npc",
                canon_state="canonical",
                memory_state="graph_read_model",
            )
        },
        identity_redirects={"npc:source": "npc:canonical"},
    )
    dispositions = [
        {"assertion_id": "wb_node_0", "decision": "bind_existing", "target_node_id": "npc:source"},
        {"assertion_id": "wb_node_1", "decision": "create_new"},
        {"assertion_id": "wb_edge_0", "decision": "defer"},
    ]
    with pytest.raises(WorldbuildingWritePlanError) as redirected_exc:
        build_worldbuilding_write_plan(**_plan_kwargs(redirected, dispositions=dispositions))
    assert redirected_exc.value.code == "bind_target_not_canonical"


    for canon, memory in (
        ("merged_away", "merged_away"),
        ("rejected", "rejected"),
        ("noncanonical_provisional", "graph_read_model"),
    ):
        context = _memory_context(
            objects={
                "npc:bad": MutationObject(
                    object_id="npc:bad",
                    label="Bad",
                    kind="npc",
                    canon_state=canon,
                    memory_state=memory,
                )
            }
        )
        bad_dispositions = [
            {"assertion_id": "wb_node_0", "decision": "bind_existing", "target_node_id": "npc:bad"},
            {"assertion_id": "wb_node_1", "decision": "create_new"},
            {"assertion_id": "wb_edge_0", "decision": "defer"},
        ]
        with pytest.raises(WorldbuildingWritePlanError) as exc:
            build_worldbuilding_write_plan(**_plan_kwargs(context, dispositions=bad_dispositions))
        assert exc.value.code == "bind_target_not_canonical"


def test_stale_expected_parent_from_context_head_mismatch():
    context = _memory_context(revision_id="rev:d-a", head_revision_id="rev:later")
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        build_worldbuilding_write_plan(**_plan_kwargs(context))
    assert exc.value.code == "stale_parent_revision"


def test_identity_snapshot_is_in_canonical_plan_digest():
    empty = build_worldbuilding_write_plan(**_plan_kwargs(_memory_context()))
    drifted = build_worldbuilding_write_plan(
        **_plan_kwargs(
            _memory_context(
                identity_ledger_records=(
                    {
                        "decision_id": "id-1",
                        "world_id": DEFAULT_WORLD_ID,
                        "decision_kind": "merge",
                        "subject_object_ids": ["unrelated-a"],
                        "target_object_ids": ["unrelated-b"],
                        "status": "active",
                        "actor": "system",
                        "reason": "drift",
                        "reversible": True,
                        "supersedes_decision_ids": [],
                        "created_at": "1970-01-01T00:00:00Z",
                    },
                )
            )
        )
    )
    assert empty.plan_digest != drifted.plan_digest
    assert drifted.effect["identity_authority"]["decisions"]


def test_threat_operation_mapping_is_unchanged_by_worldbuilding_dispatch():
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        derive_authority_review_operation_id,
        derive_threat_review_operation_id,
        derive_worldbuilding_review_operation_id,
    )


    threat = derive_threat_review_operation_id(
        world_id="eldyrwild", authority_operation_id="contrib:abc"
    )
    assert (
        derive_authority_review_operation_id(
            world_id="eldyrwild",
            authority_operation_id="contrib:abc",
            operation_namespace="threat",
        )
        == threat
    )
    worldbuilding = derive_worldbuilding_review_operation_id(
        world_id="eldyrwild", authority_operation_id="contrib:abc"
    )
    assert worldbuilding != threat
    assert worldbuilding.startswith("reviewop:")


def _install_fake_authority(monkeypatch, fake: FakeWorldGraphAuthority) -> None:
    from apps.live_control_server.ports import world_graph_authority_access as access
    from apps.live_control_server.services import worldbuilding_graph_publication as wb_svc


    monkeypatch.setattr(wb_svc, "get_world_graph_authority", lambda **_kwargs: fake)
    monkeypatch.setattr(access, "get_world_graph_authority", lambda **_kwargs: fake)


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
        if name == "graph_memory" and fromlist:
            for item in fromlist:
                candidate = f"graph_memory.{item}"
                if any(candidate == p or candidate.startswith(p + ".") for p in forbidden):
                    raise AssertionError(
                        f"Buddy World Graph runtime must not run: import {candidate}"
                    )
        return real_import(name, globals, locals, fromlist, level)


    monkeypatch.setattr(builtins, "__import__", _guarded_import)


def _install_worldbuilding_repo(monkeypatch, tmp_path: Path, native_id=DEFAULT_WORLD_ID) -> Path:


    import apps.live_control_server.config as live_config
    import apps.live_control_server.services.extract_promote as promote_svc
    import apps.live_control_server.services.promotable_ingest_run as promotable_mod
    from apps.live_control_server.services.graph_ingest_run_registry import (
        GRAPH_INGEST_RUNS_ENV,
    )


    repo = tmp_path / "repo"
    repo.mkdir()
    from apps.live_control_server.services.world_container_registry import create_world_container
    world = create_world_container(name="Publication Managed")
    store_world(world.model_copy(update={"native_graph_binding": {
        "native_world_id": native_id, "binding_version": 1,
        "status": "active", "validated_at": "2026-10-14T00:00:00Z",
        "validated_head_revision_id": "rev:fixture",
    }}))
    absent = tmp_path / "buddy-world-graph-absent"
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(absent))
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)
    monkeypatch.setattr(live_config, "world_graph_root", lambda: absent)
    from apps.live_control_server.services import graph_run_registry
    from graph_memory.extraction.graph_preview_runner import _build_prepared_components
    from graph_memory.extraction.source_adapter import NormalizedExtractionSource
    original_update = graph_run_registry.update_extraction_run_status
    def update_with_frozen_source(root, run_id, **kwargs):
        components = kwargs.get("components")
        if components and "source_artifact" in components:
            run = graph_run_registry.get_extraction_run(run_id)
            source_component = components["source_artifact"]
            _artifact, body = graph_run_registry.load_run_source_input(root, run)
            frozen_components, _ = _build_prepared_components(NormalizedExtractionSource(
                run.source_artifact_id, "worldbuilding", body.decode("utf-8"), source_component.sha256,
                source_component.uri, run.campaign_id, None), run=run)
            kwargs["components"] = {**components, **frozen_components}
        return original_update(root, run_id, **kwargs)
    monkeypatch.setattr(graph_run_registry, "update_extraction_run_status", update_with_frozen_source)
    return repo


@pytest.mark.parametrize("native_id", ["native-alpha", "native-beta"])
def test_prepare_succeeds_with_buddy_graph_physically_absent(tmp_path, monkeypatch, native_id):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=native_id)
    fake = FakeWorldGraphAuthority()
    fake.heads[native_id] = parent
    fake.revisions[(native_id, parent)] = _empty_parent(world_id=native_id, revision_id=parent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
    from apps.live_control_server.services.source_artifact_registry import get_source_artifact
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    from apps.live_control_server.services.tiptap_markdown_write import (
        prepare_tiptap_markdown_write, commit_tiptap_markdown_write,
        TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest,
    )
    frozen = resolve_promotable_ingest_run(run_id, root=repo)
    artifact = get_source_artifact(frozen.source_artifact_id)
    before = get_workspace_document_snapshot(repo, artifact.workspace_document_id)
    updated_text = before.markdown + "\nLater document edit, absent from the frozen extraction.\n"
    prepared_write = prepare_tiptap_markdown_write(root=repo, request=TiptapMarkdownWritePrepareRequest(
        document_id=before.record.document_id, markdown=updated_text,
        expected_revision=before.loaded_revision, write_mode="authoring"))
    commit_tiptap_markdown_write(root=repo, request=TiptapMarkdownWriteCommitRequest(
        document_id=before.record.document_id, markdown=updated_text,
        expected_revision=before.loaded_revision, write_mode="authoring",
        writer_confirm_token=prepared_write.writer_confirm_token))
    request = WorldbuildingWritePlanPrepareRequest.model_validate(
        {
            "runId": run_id,
            "expectedParentRevisionId": parent,
            "dispositions": [
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        }
    )
    plan = prepare_worldbuilding(request)
    assert plan.parent_revision_id == parent
    assert plan.schema_ == "dmb_worldbuilding_write_plan_v2"
    assert plan.effect.identity_authority is not None
    assert plan.effect.identity_authority.schema_ == WORLDBUILDING_IDENTITY_SNAPSHOT_SCHEMA
    assert plan.prepare_binding
    assert plan.prepare_binding.startswith("v1.")
    assert not (tmp_path / "buddy-world-graph-absent").exists()
    assert not (repo / "out/registries/worldbuilding_identity_checkpoints.json").exists()


    assert plan.publication_binding.document_revision == artifact.workspace_document_revision
    assert plan.publication_binding.source_sha256 == artifact.content_sha256
    assert get_workspace_document_snapshot(repo, before.record.document_id).loaded_revision > artifact.workspace_document_revision
    assert plan.world_id == native_id
    assert plan.publication_binding.managed_world_id == "publication-managed"
    from apps.live_control_server.models.extract_promote import WorldbuildingWritePlanConfirmRequest
    from apps.live_control_server.services.worldbuilding_graph_publication import confirm_worldbuilding
    forged = plan.model_copy(update={"publication_binding": plan.publication_binding.model_copy(
        update={"document_revision": plan.publication_binding.document_revision + 1})})
    with pytest.raises(Exception) as forged_error:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=forged))
    assert forged_error.value.code == "identity_snapshot_inexpressible"
    assert fake.publish_calls == 0
    original_world = get_world("publication-managed").record
    for binding_state in ("missing", "inactive"):
        if binding_state == "missing":
            store_world(original_world.model_copy(update={"native_graph_binding": None}))
        else:
            store_world(original_world.model_copy(update={"native_graph_binding": original_world.native_graph_binding.model_copy(update={"status": "inactive"})}))
        with pytest.raises(Exception) as unavailable_error:
            confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
        assert unavailable_error.value.code == "worldbuilding_source_binding_changed"
        assert unavailable_error.value.status_code == 409
        assert fake.publish_calls == 0
    store_world(original_world)
    change_binding(original_world.world_id, binding_version=original_world.native_graph_binding.binding_version + 1)
    with pytest.raises(Exception) as binding_error:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert binding_error.value.code == "worldbuilding_source_binding_changed"
    assert fake.publish_calls == 0
    store_world(original_world)
    seeded = _seed_worldbuilding_unit_history(monkeypatch, plan, fake)
    first = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert first.outcome == "already_applied"
    assert first.world_id == native_id
    def change_binding_during_read():
        change_binding(original_world.world_id, binding_version=original_world.native_graph_binding.binding_version + 1)
    seeded.store.on_read = change_binding_during_read
    with pytest.raises(Exception) as recovery_error:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert recovery_error.value.code == "worldbuilding_source_binding_changed"
    assert fake.publish_calls == 0
    store_world(original_world)
    seeded.store.on_read = None
    retry = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert retry.outcome == "already_applied"
    assert fake.publish_calls == 0
    assert DEFAULT_WORLD_ID not in fake.heads


@pytest.mark.parametrize(
    ("source_kind", "target_kind", "accepted"),
    [("organization", "location", True), ("location", "organization", False)],
)
def test_worldbuilding_governs_uses_pinned_v6_at_prepare_and_confirm(
    tmp_path, monkeypatch, source_kind, target_kind, accepted
):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import (
        _mutate_extraction_candidate,
        _write_bld08_reviewable_run,
    )

    parent = "rev:governs-parent"
    native_id = "native-governs"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=native_id)
    fake = FakeWorldGraphAuthority()
    fake.heads[native_id] = parent
    fake.revisions[(native_id, parent)] = _empty_parent(
        world_id=native_id, revision_id=parent
    )
    _install_fake_authority(monkeypatch, fake)
    run_id, _source = _write_bld08_reviewable_run(
        repo, world_id="publication-managed", campaign_id="publication-managed"
    )

    def make_governance_edge(candidate):
        candidate["nodes"][0]["node_type"] = source_kind
        candidate["nodes"][1]["node_type"] = target_kind
        edge = next(item for item in candidate["edges"] if item["edge_id"] == "e33")
        edge.update(
            from_node_id=candidate["nodes"][0]["node_id"],
            to_node_id=candidate["nodes"][1]["node_id"],
            relationship_type="governs",
            label="governs",
        )

    _mutate_extraction_candidate(repo, run_id, make_governance_edge)
    request = WorldbuildingWritePlanPrepareRequest.model_validate(
        {
            "runId": run_id,
            "expectedParentRevisionId": parent,
            "dispositions": [
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        }
    )

    if not accepted:
        with pytest.raises(Exception) as rejected:
            prepare_worldbuilding(request)
        assert rejected.value.code == "worldbuilding_native_relation_inexpressible"
        assert fake.publish_calls == 0
        return

    plan = prepare_worldbuilding(request)
    binding = plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True)
    object_vocabulary_key = "worldObjectVocabulary"
    property_vocabulary_key = "worldPropertyVocabulary"
    assert binding[object_vocabulary_key]["vocabulary_revision"] == "world-object-v6"
    assert binding[property_vocabulary_key]["vocabulary_revision"] == "world-property-v4"
    accepted_edge = next(
        item for item in plan.effect.accepted_proposals if item.assertion_kind == "edge"
    )
    assert accepted_edge.predicate == "governs"

    forged_binding = dict(binding)
    forged_binding[object_vocabulary_key] = {
        **binding[object_vocabulary_key],
        "vocabulary_revision": "world-object-v5",
    }
    forged_model = plan.native_vocabulary_binding.model_copy(
        update={"world_object_vocabulary": forged_binding[object_vocabulary_key]}
    )
    forged = plan.model_copy(update={"native_vocabulary_binding": forged_model})
    with pytest.raises(Exception) as stale_contract:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=forged))
    assert stale_contract.value.code == "identity_snapshot_inexpressible"
    assert fake.publish_calls == 0

    seeded = _seed_worldbuilding_unit_history(monkeypatch, plan, fake)
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert receipt.outcome == "already_applied"
    assert receipt.committed_revision_id == seeded.history.publication.published_revision_id
    relation = next(item for item in seeded.history.review.candidate_contribution.assertions if item.assertion_kind == "edge")
    assert relation.predicate == "dnd5e:governs"
    assert fake.publish_calls == 0
    assert DEFAULT_WORLD_ID not in fake.heads


def test_identity_drift_without_graph_head_advance_uses_sealed_snapshot(
    tmp_path, monkeypatch
):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    request = WorldbuildingWritePlanPrepareRequest.model_validate(
        {
            "runId": run_id,
            "expectedParentRevisionId": parent,
            "dispositions": [
                {"assertionId": "obj_session22_vial", "decision": "create_new"},
                {"assertionId": "mystery_puddles", "decision": "create_new"},
                {"assertionId": "e33", "decision": "accept"},
            ],
        }
    )
    plan = prepare_worldbuilding(request)
    sealed = identity_snapshot_from_context(
        fake.mutation_context(DEFAULT_WORLD_ID, parent)
    )
    assert plan.effect.identity_authority is not None
    assert plan.effect.identity_authority.identity_redirects == sealed["identity_redirects"]


    _seed_worldbuilding_unit_history(monkeypatch, plan, fake)
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {"obj_session22_vial": "npc:occupied-after-prepare"},
        "decisions": [],
        "alias_owners": {},
    }
    with pytest.raises(Exception) as live_exc:
        prepare_worldbuilding(request)
    assert getattr(live_exc.value, "code", "") == "new_node_id_conflict"


    def revoked():
        raise PermissionError("World ownership revoked")

    with pytest.raises(PermissionError, match="ownership revoked"):
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan), authorize_write=revoked)
    assert fake.publish_calls == 0
    assert fake.heads[DEFAULT_WORLD_ID] == parent

    receipt = confirm_worldbuilding(
        WorldbuildingWritePlanConfirmRequest(plan=plan)
    )
    assert receipt.outcome == "already_applied"
    assert receipt.parent_revision_id == parent
    assert receipt.committed_revision_id != parent
    assert fake.heads[DEFAULT_WORLD_ID] == parent
    assert fake.publish_calls == 0


def test_malformed_sealed_identity_fails_closed(tmp_path, monkeypatch):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": [
                    {"assertionId": "obj_session22_vial", "decision": "create_new"},
                    {"assertionId": "mystery_puddles", "decision": "create_new"},
                    {"assertionId": "e33", "decision": "accept"},
                ],
            }
        )
    )
    dumped = plan.model_dump(mode="json", by_alias=True)
    dumped["effect"]["identityAuthority"]["schema"] = "dmb_worldbuilding_identity_snapshot_v0"
    with pytest.raises(Exception):
        WorldbuildingWritePlanConfirmRequest.model_validate({"plan": dumped})


    from apps.live_control_server.integrations.dungeonmind import historical_worldbuilding_recovery as recovery
    malformed = plan.model_copy(update={"effect": plan.effect.model_copy(update={
        "identity_authority": plan.effect.identity_authority.model_copy(update={"alias_owners": {"forged": ["npc:other"]}})
    })})
    def no_history_read():
        pytest.fail("unauthenticated identity reached trusted history")
    monkeypatch.setattr(recovery, "_bare_readers", no_history_read)
    with pytest.raises(Exception) as exc:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=malformed))
    assert exc.value.code == "plan_verification_failed"
    assert fake.publish_calls == 0


def test_v1_confirm_is_unsupported_without_fresh_publication(tmp_path, monkeypatch):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": [
                    {"assertionId": "obj_session22_vial", "decision": "create_new"},
                    {"assertionId": "mystery_puddles", "decision": "create_new"},
                    {"assertionId": "e33", "decision": "accept"},
                ],
            }
        )
    )
    dumped = plan.model_dump(mode="json", by_alias=True)
    dumped["schema"] = "dmb_worldbuilding_write_plan_v1"
    dumped["version"] = 1
    dumped["effect"].pop("identityAuthority", None)
    v1 = WorldbuildingWritePlanConfirmRequest.model_validate({"plan": dumped})
    with pytest.raises(Exception) as exc:
        confirm_worldbuilding(v1)
    assert getattr(exc.value, "code", "") == "publication_history_unsupported"


def test_exact_retry_is_already_applied_with_zero_second_publish(
    tmp_path, monkeypatch
):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": [
                    {"assertionId": "obj_session22_vial", "decision": "create_new"},
                    {"assertionId": "mystery_puddles", "decision": "create_new"},
                    {"assertionId": "e33", "decision": "accept"},
                ],
            }
        )
    )
    _seed_worldbuilding_unit_history(monkeypatch, plan, fake)
    first = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert first.outcome == "already_applied"
    retry = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert retry.outcome == "already_applied"
    assert retry.committed_revision_id == first.committed_revision_id
    assert fake.publish_calls == 0


def test_stale_distinct_plan_fails_closed_after_unrelated_head_advance(
    tmp_path, monkeypatch
):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": [
                    {"assertionId": "obj_session22_vial", "decision": "create_new"},
                    {"assertionId": "mystery_puddles", "decision": "create_new"},
                    {"assertionId": "e33", "decision": "accept"},
                ],
            }
        )
    )
    unrelated = WorldGraphPublishRequest(
        world_id=DEFAULT_WORLD_ID,
        expected_parent_revision_id=parent,
        authority_operation_id="op:unrelated",
        actor="gm",
        contribution=SimpleNamespace(
            accepted_assertions=[], contribution_id="unrelated"
        ),
        accepted_assertion_ids=(),
        operation_namespace="worldbuilding",
    )
    fake.publish(unrelated)
    assert fake.heads[DEFAULT_WORLD_ID] != parent
    with pytest.raises(Exception) as exc:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert getattr(exc.value, "code", "") == "publication_receipt_unavailable"
    assert all(
        not str(operation_id).startswith("wbop:")
        for _world_id, operation_id in fake.publications
    )


def test_native_verify_accepts_dungeonmind_mapped_edge_predicate():
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        _relationship_predicate_matches,
    )


    assert _relationship_predicate_matches("associated_with", "linked_to")
    assert _relationship_predicate_matches("dnd5e:associated_with", "linked_to")
    assert _relationship_predicate_matches("linked_to", "linked_to")
    assert not _relationship_predicate_matches("located_in", "linked_to")


_SEED_MERGE = {
    "decision_id": "identity-decision:d2b-seed-merge",
    "world_id": DEFAULT_WORLD_ID,
    "decision_kind": "merge",
    "subject_object_ids": ["npc:seed-source", "npc:seed-target"],
    "target_object_ids": ["npc:seed-target"],
    "status": "active",
    "actor": "system",
    "reason": "seeded prepare-time identity",
    "reversible": True,
    "supersedes_decision_ids": [],
    "created_at": "1970-01-01T00:00:00Z",
    "merge_side_effects": None,
    "alias": None,
    "source_candidate_id": None,
}


def _standard_dispositions() -> list[dict[str, str]]:
    return [
        {"assertionId": "obj_session22_vial", "decision": "create_new"},
        {"assertionId": "mystery_puddles", "decision": "create_new"},
        {"assertionId": "e33", "decision": "accept"},
    ]


def _wrap_built_plan(built) -> object:
    from apps.live_control_server.models.extract_promote import (
        WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        WorldbuildingWritePlanResponse,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        _worldbuilding_native_vocabulary_binding,
    )


    return WorldbuildingWritePlanResponse(
        schema=WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        version=2,
        plan_id=built.plan_id,
        plan_digest=built.plan_digest,
        decision_digest=built.decision_digest,
        world_id=built.world_id,
        parent_revision_id=built.parent_revision_id,
        run_id=built.run_id,
        source_artifact_id=built.source_artifact_id,
        source_revision_id=built.source_revision_id,
        extraction_profile=built.extraction_profile,
        candidate_preview_id=built.candidate_preview_id,
        candidate_schema=built.candidate_schema,
        candidate_version=built.candidate_version,
        effect=built.effect,
        summary=built.summary,
        diagnostics=built.diagnostics,
        native_vocabulary_binding=_worldbuilding_native_vocabulary_binding(),
    )


def test_publication_provenance_keeps_threat_strings_and_splits_worldbuilding():
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        THREAT_PUBLISH_POLICY_ID,
        THREAT_SOURCE_PLAN_SCHEMA,
        WORLDBUILDING_PUBLISH_POLICY_ID,
        WORLDBUILDING_SOURCE_PLAN_SCHEMA,
        _publication_provenance,
        _threat_publish_capability_policy,
    )


    assert THREAT_SOURCE_PLAN_SCHEMA == "dmb_threat_publication_contribution_v1"
    assert THREAT_PUBLISH_POLICY_ID == "cutover:threat-publication-confirm"
    assert WORLDBUILDING_SOURCE_PLAN_SCHEMA == (
        "dmb_worldbuilding_publication_contribution_v1"
    )
    assert WORLDBUILDING_PUBLISH_POLICY_ID == "cutover:worldbuilding-publication-confirm"
    assert _publication_provenance("threat") == (
        THREAT_SOURCE_PLAN_SCHEMA,
        THREAT_PUBLISH_POLICY_ID,
    )
    assert _publication_provenance("worldbuilding") == (
        WORLDBUILDING_SOURCE_PLAN_SCHEMA,
        WORLDBUILDING_PUBLISH_POLICY_ID,
    )
    policy = _threat_publish_capability_policy(
        world_id="eldyrwild",
        campaign_id=None,
        parent_revision_id="rev:parent",
    )
    assert policy.policy_id == THREAT_PUBLISH_POLICY_ID


def test_tampered_identity_snapshot_fails_even_after_recompute(tmp_path, monkeypatch):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.extract_promote import (
        _load_worldbuilding_publication_input,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        _identity_snapshot_payload,
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from apps.live_control_server.models.world_graph_mutation_context import (
        mutation_context_with_sealed_identity,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {"npc:seed-source": "npc:seed-target"},
        "decisions": [_SEED_MERGE],
        "alias_owners": {"Seed": ("npc:seed-target",)},
    }
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    honest = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": _standard_dispositions(),
            }
        )
    )
    assert honest.effect.identity_authority is not None
    assert honest.effect.identity_authority.decisions


    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    publication_input = _load_worldbuilding_publication_input(resolved)
    typed_preview, expected_profile = publication_input.preview, publication_input.profile_id
    graph_base = fake.mutation_context(DEFAULT_WORLD_ID, parent)
    snapshot = _identity_snapshot_payload(honest)
    attacks = {
        "drop_trailing_merge": {**snapshot, "decisions": []},
        "modify_merge": {
            **snapshot,
            "decisions": [
                {**dict(snapshot["decisions"][0]), "decision_kind": "split"}
            ],
        },
        "invent_merge": {
            **snapshot,
            "decisions": [
                *list(snapshot["decisions"]),
                {
                    **_SEED_MERGE,
                    "decision_id": "identity-decision:invented",
                    "subject_object_ids": ["npc:invented-a", "npc:invented-b"],
                    "target_object_ids": ["npc:invented-b"],
                },
            ],
        },
        "steal_alias": {
            **snapshot,
            "alias_owners": {"Stolen": ["npc:other-owner"]},
        },
    }
    for name, mutated in attacks.items():
        rebuilt = build_worldbuilding_write_plan(
            preview=typed_preview,
            mutation_context=mutation_context_with_sealed_identity(graph_base, mutated),
            world_id=DEFAULT_WORLD_ID,
            expected_parent_revision_id=parent,
            run_id=resolved.run_id,
            source_artifact_id=resolved.source_artifact_id,
            source_revision_id=resolved.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            extraction_profile=expected_profile,
            campaign_scope=resolved.campaign_id or None,
            dispositions=[
                {"assertion_id": item["assertionId"], "decision": item["decision"]}
                for item in _standard_dispositions()
            ],
            require_current_head=False,
        )
        attack_plan = _wrap_built_plan(rebuilt).model_copy(
            update={"prepare_binding": honest.prepare_binding, "publication_binding": honest.publication_binding,
                    "source_admission": honest.source_admission, "native_vocabulary_binding": honest.native_vocabulary_binding}
        )
        with pytest.raises(Exception) as exc:
            confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=attack_plan))
        code = getattr(exc.value, "code", "")
        assert code in {
            "identity_snapshot_inexpressible",
            "dungeonmind_inexpressible",
        }, name


def test_identity_drift_appends_i1_without_changing_sealed_confirm(
    tmp_path, monkeypatch
):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {},
        "decisions": [],
        "alias_owners": {},
    }
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": _standard_dispositions(),
            }
        )
    )
    _seed_worldbuilding_unit_history(monkeypatch, plan, fake)
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {},
        "decisions": [
            {
                **_SEED_MERGE,
                "decision_id": "identity-decision:d2b-i1",
                "subject_object_ids": ["npc:later-a", "npc:later-b"],
                "target_object_ids": ["npc:later-b"],
            },
        ],
        "alias_owners": {},
    }
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert receipt.outcome == "already_applied"
    assert fake.publish_calls == 0


def test_recomputed_plan_after_i1_cannot_reuse_prepare_binding(tmp_path, monkeypatch):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.extract_promote import (
        _load_worldbuilding_publication_input,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        _identity_snapshot_payload,
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from apps.live_control_server.models.world_graph_mutation_context import (
        mutation_context_with_sealed_identity,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = _empty_parent(revision_id=parent)
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {},
        "decisions": [],
        "alias_owners": {},
    }
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    prepared = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": _standard_dispositions(),
            }
        )
    )
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {},
        "decisions": [
            {
                **_SEED_MERGE,
                "decision_id": "identity-decision:d2b-i1",
                "subject_object_ids": ["npc:later-a", "npc:later-b"],
                "target_object_ids": ["npc:later-b"],
            }
        ],
        "alias_owners": {},
    }
    resolved = resolve_promotable_ingest_run(run_id, root=repo)
    publication_input = _load_worldbuilding_publication_input(resolved)
    typed_preview, expected_profile = publication_input.preview, publication_input.profile_id
    graph_base = fake.mutation_context(DEFAULT_WORLD_ID, parent)
    snapshot = _identity_snapshot_payload(prepared)
    rebuilt = build_worldbuilding_write_plan(
        preview=typed_preview,
        mutation_context=mutation_context_with_sealed_identity(graph_base, snapshot),
        world_id=DEFAULT_WORLD_ID,
        expected_parent_revision_id=parent,
        run_id=resolved.run_id,
        source_artifact_id=resolved.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        source_uri=resolved.sealed_source_uri,
        extraction_profile=expected_profile,
        campaign_scope=resolved.campaign_id or None,
        dispositions=[
            {"assertion_id": "obj_session22_vial", "decision": "reject"},
            {"assertion_id": "mystery_puddles", "decision": "create_new"},
            {"assertion_id": "e33", "decision": "defer"},
        ],
        require_current_head=False,
    )
    attack_plan = _wrap_built_plan(rebuilt).model_copy(
        update={"prepare_binding": prepared.prepare_binding, "publication_binding": prepared.publication_binding,
                "source_admission": prepared.source_admission, "native_vocabulary_binding": prepared.native_vocabulary_binding}
    )
    assert attack_plan.plan_id != prepared.plan_id
    with pytest.raises(Exception) as exc:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=attack_plan))
    assert getattr(exc.value, "code", "") == "identity_snapshot_inexpressible"
    assert fake.publish_calls == 0


def test_bind_existing_native_verify_proves_attribute_and_alias(tmp_path, monkeypatch):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import (
        _mutate_extraction_candidate,
        _write_bld08_reviewable_run,
    )


    parent = "rev:d-a"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path)
    target = AuthorityObject(
        object_id="npc:exact-target",
        label="Exact",
        kind="npc",
        aliases=("Exact",),
    )
    fake = FakeWorldGraphAuthority()
    fake.heads[DEFAULT_WORLD_ID] = parent
    fake.revisions[(DEFAULT_WORLD_ID, parent)] = WorldGraphRevisionView(
        world_id=DEFAULT_WORLD_ID,
        revision_id=parent,
        parent_revision_id=None,
        objects={target.object_id: target},
        relationships={},
    )
    fake.identity[DEFAULT_WORLD_ID] = {
        "identity_redirects": {},
        "decisions": [],
        "alias_owners": {"Exact": (target.object_id,)},
    }
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)
    run_id, _source = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")

    def add_alias(candidate):
        candidate["nodes"][0]["aliases"] = ["Witness Alias"]

    _mutate_extraction_candidate(repo, run_id, add_alias)

    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent,
                "dispositions": [
                    {
                        "assertionId": "obj_session22_vial",
                        "decision": "bind_existing",
                        "targetNodeId": target.object_id,
                    },
                    {"assertionId": "mystery_puddles", "decision": "create_new"},
                    {"assertionId": "e33", "decision": "accept"},
                ],
            }
        )
    )
    seeded = _seed_worldbuilding_unit_history(monkeypatch, plan, fake)
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert receipt.outcome == "already_applied"
    assert receipt.committed_revision_id == seeded.history.publication.published_revision_id
    candidate = seeded.history.review.candidate_contribution
    attributes = [item for item in candidate.assertions if item.assertion_kind == "attribute"]
    aliases = [item for item in candidate.assertions if item.assertion_kind == "alias"]
    assert any(item.subject_object_id == target.object_id and item.evidence_refs for item in attributes)
    assert any(item.subject_object_id == target.object_id and "Witness Alias" in item.value for item in aliases)
    assert any(item.subject_object_id == "mystery_puddles" for item in candidate.assertions)
    assert fake.publish_calls == 0
    assert fake.heads[DEFAULT_WORLD_ID] == parent


def test_registered_publication_binding_uses_native_target_without_latest_revision_requirement(monkeypatch):
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    artifact = SimpleNamespace(workspace_document_id="doc-a", workspace_document_revision=2,
                               world_id="managed-a", source_artifact_id="source-a", content_sha256="a" * 64)
    document = SimpleNamespace(kind="worldbuilding_source", world_id="managed-a", status="active", revision=3)
    monkeypatch.setattr(service, "get_source_artifact", lambda *args: artifact)
    monkeypatch.setattr(service, "get_workspace_document", lambda *args: document)
    monkeypatch.setattr(service, "resolve_managed_world_binding", lambda *args: SimpleNamespace(
        managed_world_id="managed-a", native_world_id="native-a", binding_version=4))
    resolved = SimpleNamespace(source_artifact_id="source-a", world_id="managed-a",
                               source_domain="worldbuilding", session_id="", source_revision_id="a" * 64)
    result = service._registered_publication_binding(resolved)
    assert result.native_world_id == "native-a"
    assert result.document_revision == 2
    assert result.binding_version == 4


def test_registered_publication_binding_rejects_cross_world_document(monkeypatch):
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    artifact = SimpleNamespace(workspace_document_id="doc-a", workspace_document_revision=2,
                               world_id="managed-a", source_artifact_id="source-a", content_sha256="a" * 64)
    monkeypatch.setattr(service, "get_source_artifact", lambda *args: artifact)
    monkeypatch.setattr(service, "get_workspace_document", lambda *args: SimpleNamespace(
        kind="worldbuilding_source", world_id="managed-b", status="active"))
    resolved = SimpleNamespace(source_artifact_id="source-a", world_id="managed-a",
                               source_domain="worldbuilding", session_id="", source_revision_id="a" * 64)
    with pytest.raises(service.ExtractPromoteError) as error:
        service._registered_publication_binding(resolved)
    assert error.value.code == "worldbuilding_source_binding_changed"


def test_publication_binding_normalizes_missing_source_without_path_leak(monkeypatch):
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    def missing(*args):
        raise service.SourceArtifactRegistryError("private-path-detail", status_code=404)
    monkeypatch.setattr(service, "get_source_artifact", missing)
    with pytest.raises(service.ExtractPromoteError) as error:
        service._registered_publication_binding(SimpleNamespace(source_artifact_id="missing"))
    assert error.value.status_code == 409
    assert error.value.code == "worldbuilding_source_binding_missing"
    assert "private-path-detail" not in str(error.value)


def test_two_registered_managed_worlds_publish_only_to_their_native_worlds(
    tmp_path, monkeypatch
):
    """Concurrent managed bindings must keep preparation and publication isolated."""
    import copy
    import json

    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanConfirmRequest,
        WorldbuildingWritePlanPrepareRequest,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
        load_source_span_index,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document,
    )
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )
    from apps.live_control_server.services import source_artifact_registry as registry
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding,
        prepare_worldbuilding,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import (
        _mutate_extraction_candidate,
        _write_bld08_reviewable_run,
    )

    repo = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id="native-alpha")
    managed_a = "publication-managed"
    managed_b = create_world_container(name="Second Publication Managed").world_id
    managed_to_native = {
        managed_a: "native-alpha",
        managed_b: "native-beta",
    }
    parent_by_native = {
        "native-alpha": "rev:parent-alpha",
        "native-beta": "rev:parent-beta",
    }
    for stored in world_snapshot():
        row = stored.record
        native_id = managed_to_native[row.world_id]
        store_world(row.model_copy(update={"native_graph_binding": {
            "native_world_id": native_id,
            "binding_version": 1,
            "status": "active",
            "validated_at": "2026-10-14T00:00:00Z",
            "validated_head_revision_id": parent_by_native[native_id],
        }}))

    fake = FakeWorldGraphAuthority()
    for native_id, parent_id in parent_by_native.items():
        fake.heads[native_id] = parent_id
        fake.revisions[(native_id, parent_id)] = _empty_parent(
            world_id=native_id, revision_id=parent_id
        )
    _install_fake_authority(monkeypatch, fake)
    _explode_buddy_graph_runtime(monkeypatch)

    marker_by_managed: dict[str, str] = {}
    register_source = registry.create_source_artifact_from_workspace_document

    from tests.page_fixtures import page_text, save_page

    def register_with_world_marker(root, *, document_id, expected_revision):
        document = get_workspace_document(root, document_id)
        assert document.revision == expected_revision
        marker = f"World isolation marker: {document.world_id}."
        marker_by_managed[document.world_id] = marker
        saved = save_page(root, document_id, page_text(root, document_id) + "\n\n" + marker + "\n")
        return register_source(root, document_id=document_id, expected_revision=saved.revision)

    monkeypatch.setattr(
        registry,
        "create_source_artifact_from_workspace_document",
        register_with_world_marker,
    )

    def create_run_and_marker(managed_id: str) -> tuple[str, str]:
        run_id, _source = _write_bld08_reviewable_run(
            repo, world_id=managed_id, campaign_id=managed_id
        )
        from apps.live_control_server.services.promotable_ingest_run import (
            resolve_promotable_ingest_run,
        )

        resolved = resolve_promotable_ingest_run(run_id, root=repo)
        artifact = get_source_artifact(resolved.source_artifact_id)
        marker = marker_by_managed[managed_id]
        from graph_memory.source_span import source_span_index_to_dict
        index = source_span_index_to_dict(load_source_span_index(repo, artifact.source_artifact_id))
        source_text = resolved.data.source_bytes.decode("utf-8")
        source_lines = source_text.splitlines()
        marker_span = next(
            span for span in index["spans"]
            if marker in "\n".join(
                source_lines[int(span["start_line"]) - 1 : int(span["end_line"])]
            )
        )

        def add_marker_node(candidate):
            node = copy.deepcopy(candidate["nodes"][0])
            node["node_id"] = f"world-marker:{managed_id}"
            node["label"] = marker
            node["node_type"] = "location"
            node["description"] = marker
            span_id = marker_span["source_span_id"]
            node["evidence_refs"] = [
                {
                    **node["evidence_refs"][0],
                    "source_ref_id": f"ref:{artifact.source_artifact_id}:{span_id}",
                    "source_artifact_id": artifact.source_artifact_id,
                    "source_anchor_id": (
                        f"anchor:{artifact.source_artifact_id}:{span_id}"
                    ),
                    "label": "world-isolation marker source span",
                    "source_span_ref_id": span_id,
                    "anchor_quotes": [marker],
                }
            ]
            candidate["nodes"].append(node)

        _mutate_extraction_candidate(repo, run_id, add_marker_node)
        return run_id, artifact.source_artifact_id

    def prepare_run(run_id: str, parent_id: str, managed_id: str, native_id: str):
        from apps.live_control_server.services.promotable_ingest_run import (
            resolve_promotable_ingest_run,
        )
        from graph_memory.candidate_graph_to_contribution import (
            load_typed_candidate_graph,
        )

        resolved = resolve_promotable_ingest_run(run_id, root=repo)
        candidate = load_typed_candidate_graph(
            json.loads(resolved.data.candidate_bytes)
        )
        plan = prepare_worldbuilding(
            WorldbuildingWritePlanPrepareRequest.model_validate({
                "runId": run_id,
                "expectedParentRevisionId": parent_id,
                "dispositions": [
                    {"assertionId": node.node_id, "decision": "create_new"}
                    for node in candidate.nodes
                ] + [
                    {"assertionId": edge.edge_id, "decision": "accept"}
                    for edge in candidate.edges
                ],
            })
        )
        assert plan.world_id == native_id
        assert plan.publication_binding.managed_world_id == managed_id
        return plan

    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )

    run_a, source_a = create_run_and_marker(managed_a)
    original_a = resolve_promotable_ingest_run(run_a, root=repo)
    source_bytes_a = original_a.data.source_bytes
    candidate_bytes_a = original_a.data.candidate_bytes
    run_b, source_b = create_run_and_marker(managed_b)
    resolved_b = resolve_promotable_ingest_run(run_b, root=repo)
    resolved_a = resolve_promotable_ingest_run(run_a, root=repo)
    source_bytes_b = resolved_b.data.source_bytes
    assert resolved_a.data.run.run_id != resolved_b.data.run.run_id
    assert resolved_a.source_artifact_id != resolved_b.source_artifact_id
    assert resolved_a.data.candidate_bytes == candidate_bytes_a
    assert resolved_a.data.source_bytes == source_bytes_a
    assert source_bytes_a != source_bytes_b

    # A corrupted run/source World association must fail before either publication.
    with monkeypatch.context() as tamper:
        tamper.setattr(service, "resolve_promotable_ingest_run", lambda *args, **kwargs:
                       replace(resolved_a, world_id=managed_b))
        with pytest.raises(service.ExtractPromoteError) as error:
            prepare_run(run_a, parent_by_native["native-alpha"], managed_a, "native-alpha")
        assert error.value.code == "run_scope_mismatch", error.value.code
        assert error.value.status_code == 409, (error.value.code, error.value.status_code)
    assert fake.publish_calls == 0
    assert fake.heads == parent_by_native

    # A parent revision from the other World cannot select that World implicitly.
    with pytest.raises(service.ExtractPromoteError) as error:
        prepare_run(run_a, parent_by_native["native-beta"], managed_a, "native-alpha")
    assert error.value.code == "stale_parent_revision"
    assert fake.publish_calls == 0
    assert fake.heads == parent_by_native

    plan_a = prepare_run(run_a, parent_by_native["native-alpha"], managed_a, "native-alpha")
    plan_b = prepare_run(run_b, parent_by_native["native-beta"], managed_b, "native-beta")
    for forged in (
        plan_a.model_copy(update={"publication_binding": plan_b.publication_binding}),
        plan_a.model_copy(update={"run_id": run_b}),
        plan_a.model_copy(update={"source_artifact_id": source_b}),
        plan_a.model_copy(update={"world_id": DEFAULT_WORLD_ID}),
    ):
        with pytest.raises(service.ExtractPromoteError):
            confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=forged))
        assert fake.publish_calls == 0
        assert fake.heads == parent_by_native

    seeded_a = _seed_worldbuilding_unit_history(monkeypatch, plan_a, fake)
    seeded_b = _seed_worldbuilding_unit_history(monkeypatch, plan_b, fake)
    for plan, seeded, other_managed in ((plan_a, seeded_a, managed_b), (plan_b, seeded_b, managed_a)):
        receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
        assert receipt.outcome == "already_applied"
        assert receipt.world_id == plan.world_id
        assert receipt.committed_revision_id == seeded.history.publication.published_revision_id
        own_marker = "world-marker:" + plan.publication_binding.managed_world_id
        subjects = {item.subject_object_id for item in seeded.history.review.candidate_contribution.assertions}
        assert own_marker in subjects
        assert "world-marker:" + other_managed not in subjects
    assert seeded_a.operation != seeded_b.operation
    assert seeded_a.store.reads[-2:] == [(plan_a.world_id, seeded_a.operation), (plan_b.world_id, seeded_b.operation)]
    assert fake.heads == parent_by_native
    assert DEFAULT_WORLD_ID not in fake.heads
    assert fake.publish_calls == 0
    assert resolve_promotable_ingest_run(run_a, root=repo).data.source_bytes == source_bytes_a
    assert resolve_promotable_ingest_run(run_b, root=repo).data.source_bytes == source_bytes_b

pytestmark = pytest.mark.usefixtures("application_state_dsn")



def _immutable_worldbuilding_plan(monkeypatch, *, mode="create", with_producer_inputs=False):
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingPublicationBinding, WorldbuildingSourceAdmissionBinding,
    )
    from apps.live_control_server.services import worldbuilding_graph_publication as service

    monkeypatch.setenv(service._PREPARE_BINDING_KEY_ENV, "immutable-worldbuilding-fixture-key")
    context = _memory_context()
    dispositions = _dispositions()
    if mode in {"bind", "bind_alias"}:
        target = MutationObject(object_id="npc:exact", label="Existing", kind="npc",
                                canon_state="canonical", memory_state="graph_read_model")
        context = _memory_context(objects={target.object_id: target})
        dispositions[0] = {"assertion_id": "wb_node_0", "decision": "bind_existing", "target_node_id": target.object_id}
    elif mode == "reject_node":
        dispositions[0] = {"assertion_id": "wb_node_0", "decision": "reject"}
        dispositions[2] = {"assertion_id": "wb_edge_0", "decision": "defer"}
    elif mode == "reject":
        dispositions[2] = {"assertion_id": "wb_edge_0", "decision": "reject"}
    elif mode == "defer":
        dispositions[1] = {"assertion_id": "wb_node_1", "decision": "defer"}
        dispositions[2] = {"assertion_id": "wb_edge_0", "decision": "defer"}
    kwargs = _plan_kwargs(context, dispositions=dispositions)
    kwargs.update(campaign_scope=None, source_revision_id="sha256:" + "ab" * 32)
    kwargs["preview"] = replace(kwargs["preview"], campaign_id=None)
    if mode == "bind_alias":
        preview = kwargs["preview"]
        kwargs["preview"] = replace(preview,
            nodes=(replace(preview.nodes[0], aliases=("Historical alias",)), *preview.nodes[1:]))
    if mode == "governs":
        preview = kwargs["preview"]
        kwargs["preview"] = replace(preview,
            nodes=(replace(preview.nodes[0], node_type="organization"), *preview.nodes[1:]),
            edges=tuple(replace(edge, relationship_type="governs", label="governs") for edge in preview.edges))
    if mode == "observation":
        from graph_memory.candidate_graph_preview import CandidateSourceObservation
        node = kwargs["preview"].nodes[0]
        observation = CandidateSourceObservation(
            observation_id="wb_observation_0", subject_candidate_node_id=node.node_id,
            title="A source observation", description="A retained statement about the subject.",
            semantic_state=node.semantic_state, evidence_refs=node.evidence_refs, confidence=node.confidence,
        )
        from graph_memory.extraction.worldbuilding_definition_observations import GAZETTEER_DEFINITION_OBSERVATION_PROFILE
        kwargs["preview"] = replace(kwargs["preview"], version="0.2", source_observations=(observation,))
        kwargs["extraction_profile"] = GAZETTEER_DEFINITION_OBSERVATION_PROFILE.qualified_id
        dispositions.append({"assertion_id": observation.observation_id, "decision": "accept"})
    built = build_worldbuilding_write_plan(**kwargs)
    plan = _wrap_built_plan(built)
    plan = plan.model_copy(update={
        "publication_binding": WorldbuildingPublicationBinding(
            managed_world_id="managed-history", native_world_id=plan.world_id,
            binding_version=1, document_id="doc:retained", document_revision=1,
            source_artifact_id=plan.source_artifact_id, source_sha256="ab" * 32,
        ),
        "source_admission": WorldbuildingSourceAdmissionBinding(
            source_artifact_id=plan.source_artifact_id, source_revision_id="revision:admitted-history",
            content_sha256="ab" * 32, buddy_source_revision_id=plan.source_revision_id,
            source_locator="object://retained-worldbuilding-revision", artifact_uri="object://original-source",
            catalog_fingerprint_sha256="cd" * 32,
        ),
    })
    signature = service._sign_prepare_binding(
        world_id=plan.world_id, parent_revision_id=plan.parent_revision_id,
        plan_id=plan.plan_id, plan_digest=plan.plan_digest,
        identity_snapshot_digest=service._identity_snapshot_digest(service._identity_snapshot_payload(plan)),
        publication_binding=plan.publication_binding.model_dump(mode="json"),
        source_admission=plan.source_admission.model_dump(mode="json"),
        native_vocabulary_binding=plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True),
    )
    sealed = plan.model_copy(update={"prepare_binding": signature})
    return (sealed, kwargs) if with_producer_inputs else sealed


def test_immutable_worldbuilding_plan_authenticates_complete_real_builder_effect(monkeypatch):
    from graph_memory.worldbuilding_write_plan import _canonical_effect
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import authenticate_original_plan
    from apps.live_control_server.services import worldbuilding_graph_publication as service

    plan = _immutable_worldbuilding_plan(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail("original plan authentication consulted mutable authority")
    for name in ("resolve_promotable_ingest_run", "_registered_publication_binding",
                 "_worldbuilding_native_vocabulary_binding", "_reprove_source_admission"):
        monkeypatch.setattr(service, name, forbidden)
    assert authenticate_original_plan(plan) == _canonical_effect(plan.effect.model_dump(mode="json", by_alias=True))


@pytest.mark.parametrize("change", [
    "digest", "id", "decision_digest", "effect", "identity", "admitted_revision", "binding_version",
    "rehashed_effect", "missing_admission", "missing_identity", "legacy_schema", "legacy_version", "lost_key",
])
def test_immutable_worldbuilding_plan_rejects_changed_or_unsupported_original(monkeypatch, change):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import authenticate_original_plan
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from graph_memory.worldbuilding_write_plan import _canonical_effect, _digest

    plan = _immutable_worldbuilding_plan(monkeypatch).model_copy(deep=True)
    if change == "digest":
        plan.plan_digest = "sha256:" + "ef" * 32
    elif change == "id":
        plan.plan_id = "worldbuilding-write-plan:" + "1" * 24
    elif change == "decision_digest":
        plan.decision_digest = "sha256:" + "ef" * 32
    elif change in {"effect", "rehashed_effect"}:
        plan.effect.accepted_proposals[0].label = "Changed after prepare"
        if change == "rehashed_effect":
            effect = _canonical_effect(plan.effect.model_dump(mode="json", by_alias=True))
            identity = {key: getattr(plan, key) for key in (
                "world_id", "parent_revision_id", "run_id", "source_domain", "source_artifact_id",
                "source_revision_id", "extraction_profile", "candidate_preview_id", "candidate_schema", "candidate_version",
            )}
            identity.update(decision_snapshot=effect["decision_snapshot"], effect=effect)
            plan.plan_digest = _digest(identity)
            plan.plan_id = "worldbuilding-write-plan:" + plan.plan_digest.removeprefix("sha256:")[:24]
    elif change == "identity":
        plan.effect.identity_authority.identity_redirects["old"] = "different"
    elif change == "admitted_revision":
        plan.source_admission.source_revision_id = "revision:foreign"
    elif change == "binding_version":
        plan.publication_binding.binding_version = 2
    elif change == "missing_admission":
        plan.source_admission = None
    elif change == "missing_identity":
        plan.effect.identity_authority = None
    elif change == "legacy_schema":
        plan.schema_ = "dmb_worldbuilding_write_plan_v1"
    elif change == "legacy_version":
        plan.version = 1
    else:
        monkeypatch.setenv(service._PREPARE_BINDING_KEY_ENV, "different-process-key")
    with pytest.raises(ExtractPromoteError) as error:
        authenticate_original_plan(plan)
    assert error.value.status_code == 409



def _reseal_immutable_worldbuilding_plan(plan):
    """Sign a deliberately inconsistent effect to reach producer crosslink checks."""
    from graph_memory.worldbuilding_write_plan import _canonical_effect, _digest
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    effect = _canonical_effect(plan.effect.model_dump(mode="json", by_alias=True))
    identity = {key: getattr(plan, key) for key in (
        "world_id", "parent_revision_id", "run_id", "source_domain", "source_artifact_id",
        "source_revision_id", "extraction_profile", "candidate_preview_id", "candidate_schema", "candidate_version",
    )}
    identity.update(decision_snapshot=effect["decision_snapshot"], effect=effect)
    plan.plan_digest = _digest(identity)
    plan.plan_id = "worldbuilding-write-plan:" + plan.plan_digest.removeprefix("sha256:")[:24]
    plan.decision_digest = _digest(effect["decision_snapshot"])
    plan.prepare_binding = service._sign_prepare_binding(
        world_id=plan.world_id, parent_revision_id=plan.parent_revision_id,
        plan_id=plan.plan_id, plan_digest=plan.plan_digest,
        identity_snapshot_digest=service._identity_snapshot_digest(service._identity_snapshot_payload(plan)),
        publication_binding=plan.publication_binding.model_dump(mode="json"),
        source_admission=plan.source_admission.model_dump(mode="json"),
        native_vocabulary_binding=plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True),
    )
    return plan


@pytest.mark.parametrize("mode", ["create", "bind", "defer", "observation"])
def test_immutable_worldbuilding_real_producer_decision_shapes(monkeypatch, mode):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import authenticate_original_plan
    plan = _immutable_worldbuilding_plan(monkeypatch, mode=mode)
    effect = authenticate_original_plan(plan)
    assert effect["decision_snapshot"]
    if mode == "observation":
        assert "wb_observation_0" not in effect["identity_outcome_snapshot"]
    if mode == "bind":
        assert effect["node_id_map"]["wb_node_0"] == "npc:exact"


@pytest.mark.parametrize("change", ["new_target", "bind_target", "extra_node", "duplicate_owner", "outcome"])
def test_immutable_worldbuilding_signed_inconsistent_crosslinks_fail(monkeypatch, change):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import authenticate_original_plan
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    plan = _immutable_worldbuilding_plan(monkeypatch, mode="bind" if change == "bind_target" else "create")
    if change in {"new_target", "bind_target"}:
        plan.effect.node_id_map["wb_node_0"] = "node:forged"
        ids = plan.effect.candidate_effect_map["wb_node_0"]
        for assertion in plan.effect.accepted_proposals:
            if assertion.assertion_id in ids:
                assertion.subject_node_id = "node:forged"
    elif change == "extra_node":
        plan.effect.node_id_map["not-a-decision"] = "node:extra"
    elif change == "duplicate_owner":
        plan.effect.candidate_effect_map["wb_edge_0"] += plan.effect.candidate_effect_map["wb_node_0"]
    else:
        plan.effect.identity_outcome_snapshot["wb_node_0"] = "human_override"
    plan = _reseal_immutable_worldbuilding_plan(plan)
    with pytest.raises(ExtractPromoteError) as error:
        authenticate_original_plan(plan)
    assert error.value.code == "plan_verification_failed"


@pytest.mark.parametrize("mode", ["create", "bind", "bind_alias", "defer", "observation", "reject", "reject_node", "governs"])
def test_immutable_worldbuilding_typed_mapping_uses_only_authenticated_evidence(monkeypatch, mode):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import reconstruct_original_mapping
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    plan = _immutable_worldbuilding_plan(monkeypatch, mode=mode)
    def forbidden(*args, **kwargs):
        pytest.fail("typed historical mapping reopened current source evidence")
    monkeypatch.setattr(writes, "_recap_extraction_evidence_view", forbidden)
    contribution, mapped = reconstruct_original_mapping(plan)
    assert mapped.schema_version == "dm_graph_contribution_v3"
    assert len(mapped.assertions) == len(contribution.accepted_assertions) + len(contribution.rejected_assertions)
    for assertion in mapped.assertions:
        for ref in assertion.evidence_refs:
            assert ref.source_revision_id == plan.source_admission.source_revision_id
            assert ref.source_domain_key == "worldbuilding"
            assert ref.can_open_source and ref.can_highlight_span and ref.source_span_ref_id
            assert ref.locator is None and ref.uri is None and ref.source_locator is None



@pytest.mark.parametrize("conflict", [False, True])
def test_immutable_worldbuilding_operation_wide_evidence_identity(monkeypatch, conflict):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import reconstruct_original_mapping
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    plan = _immutable_worldbuilding_plan(monkeypatch)
    first, second = plan.effect.accepted_proposals[:2]
    row = dict(first.value["evidence"][0])
    raw_id = row["evidence_ref_id"]
    if conflict:
        row["source_span_ref_id"] = "span:conflicting-retained-binding"
    second.value["evidence"][0] = row
    second.evidence_ref_ids[0] = raw_id
    plan = _reseal_immutable_worldbuilding_plan(plan)
    if conflict:
        with pytest.raises(ExtractPromoteError) as error:
            reconstruct_original_mapping(plan)
        assert error.value.code == "plan_verification_failed"
    else:
        _, mapped = reconstruct_original_mapping(plan)
        assert mapped.assertions


def test_immutable_worldbuilding_governs_matches_original_qualification_without_preview_replay(monkeypatch):
    from graph_memory.worldbuilding_write_plan import _canonical_effect, materialize_worldbuilding_contribution
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import reconstruct_original_mapping
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    plan = _immutable_worldbuilding_plan(monkeypatch, mode="governs")
    preview = _preview()
    preview = replace(preview, campaign_id=None,
        nodes=(replace(preview.nodes[0], node_type="organization"), *preview.nodes[1:]),
        edges=tuple(replace(edge, relationship_type="governs", label="governs") for edge in preview.edges))
    expected_effect = service._qualify_worldbuilding_native_edges(
        preview=preview, effect=_canonical_effect(plan.effect.model_dump(mode="json", by_alias=True)),
        native_vocabulary_binding=plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True),
    )
    expected = materialize_worldbuilding_contribution(world_id=plan.world_id, plan_digest=plan.plan_digest, effect=expected_effect)
    monkeypatch.setattr(service, "_qualify_worldbuilding_native_edges",
                        lambda *a, **k: pytest.fail("recovery repeated fresh preview admission"))
    actual, mapped = reconstruct_original_mapping(plan)
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    assert any(item.predicate == "dnd5e:governs" for item in mapped.assertions)



@pytest.mark.parametrize("change", ["edge_kind", "rejected_node_kind"])
def test_immutable_worldbuilding_signed_candidate_kind_ownership(monkeypatch, change):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import authenticate_original_plan
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    plan = _immutable_worldbuilding_plan(monkeypatch, mode="reject_node" if change == "rejected_node_kind" else "create")
    if change == "edge_kind":
        decision = next(item for item in plan.effect.decision_snapshot if item.assertion_id == "wb_node_0")
        decision.candidate_kind = "edge"
        decision.decision = "accept"
        plan.effect.node_id_map.pop("wb_node_0")
        plan.effect.identity_outcome_snapshot["wb_node_0"] = "accepted_by_operator"
        order = {"node": 0, "edge": 1, "source_observation": 2}
        plan.effect.decision_snapshot.sort(key=lambda item: (order[item.candidate_kind], item.assertion_id))
    else:
        plan.effect.rejected_assertions[0].assertion_kind = "attribute"
    plan = _reseal_immutable_worldbuilding_plan(plan)
    with pytest.raises(ExtractPromoteError) as error:
        authenticate_original_plan(plan)
    assert error.value.code == "plan_verification_failed"
    assert "decision/effect ownership" in str(error.value)


@pytest.mark.parametrize("mode", ["create", "bind", "bind_alias", "defer", "observation", "reject", "reject_node", "governs"])
def test_immutable_worldbuilding_complete_typed_mapping_matches_original_producer(monkeypatch, mode):
    from graph_memory.worldbuilding_write_plan import _canonical_effect, materialize_worldbuilding_contribution
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import _worldbuilding_expressible
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import map_worldbuilding_extraction_contribution_v3
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import reconstruct_original_mapping
    plan, inputs = _immutable_worldbuilding_plan(monkeypatch, mode=mode, with_producer_inputs=True)
    effect = service._qualify_worldbuilding_native_edges(
        preview=inputs["preview"], effect=_canonical_effect(plan.effect.model_dump(mode="json", by_alias=True)),
        native_vocabulary_binding=plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True),
    )
    original = materialize_worldbuilding_contribution(world_id=plan.world_id, plan_digest=plan.plan_digest, effect=effect)
    wire = _worldbuilding_expressible(original)
    pairs = {(plan.source_artifact_id, plan.source_revision_id): plan.source_admission.source_revision_id}
    # Exercise the original producer's catalog-reading evidence path against
    # immutable fixture metadata before forbidding it for recovery.
    view = writes._recap_extraction_evidence_view(wire, pair_to_dm=pairs, sources=SimpleNamespace(
        get_artifact=lambda _: SimpleNamespace(source_domain="worldbuilding"),
        get_revision=lambda _: SimpleNamespace(locator=plan.source_admission.source_locator),
    ))
    expected = map_worldbuilding_extraction_contribution_v3(view, wire, pairs)
    def forbidden(*args, **kwargs):
        pytest.fail("immutable reconstruction replayed source/preview admission")
    monkeypatch.setattr(writes, "_recap_extraction_evidence_view", forbidden)
    monkeypatch.setattr(service, "_qualify_worldbuilding_native_edges", forbidden)
    actual_original, actual = reconstruct_original_mapping(plan)
    assert actual_original.model_dump(mode="json") == original.model_dump(mode="json")
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    if mode == "bind_alias":
        assert any(item.assertion_kind == "alias" for item in actual.assertions)



def _immutable_worldbuilding_original_staging(monkeypatch, *, mode="create", mutation=None, prepared_plan=None, producer_inputs=None):
    """Real historical staging/review builder; fake envelope is unit evidence only."""
    import json
    from datetime import UTC, datetime, timedelta
    from graph_memory.worldbuilding_write_plan import _canonical_effect, materialize_worldbuilding_contribution
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import _worldbuilding_expressible
    from dungeonmind.application.contribution_review_v3 import _build_review_state
    from dungeonmind.contracts.contribution import AcceptanceState
    from dungeonmind.contracts.contribution_review import ContributionAssertionVerdict, ContributionPlanRef, derive_confirmation_id
    from dungeonmind.contracts.contribution_review_v3 import (
        CommitConfirmationReceiptV3, ContributionReviewIntentV3, ContributionReviewSubmissionV3,
        contribution_v3_payload_sha256, derive_review_intent_sha256_v3,
    )
    from dungeonmind.domain.canonical import canonical_json, canonical_sha256
    plan, inputs = ((prepared_plan, producer_inputs) if prepared_plan is not None else
                    _immutable_worldbuilding_plan(monkeypatch, mode=mode, with_producer_inputs=True))
    effect = service._qualify_worldbuilding_native_edges(
        preview=inputs["preview"], effect=_canonical_effect(plan.effect.model_dump(mode="json", by_alias=True)),
        native_vocabulary_binding=plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True),
    )
    original = materialize_worldbuilding_contribution(world_id=plan.world_id, plan_digest=plan.plan_digest, effect=effect)
    pairs = {(plan.source_artifact_id, plan.source_revision_id): plan.source_admission.source_revision_id}
    sources = SimpleNamespace(get_artifact=lambda _: SimpleNamespace(source_domain="worldbuilding"),
                              get_revision=lambda _: SimpleNamespace(locator=plan.source_admission.source_locator))
    stamp = datetime(2025, 1, 1, tzinfo=UTC)
    review_time = stamp + timedelta(seconds=1) if mutation == "timestamp" else stamp
    candidate, states = writes._build_v2_candidate(
        _worldbuilding_expressible(original), context=inputs["mutation_context"],
        pair_to_dm=pairs, produced_at=review_time, sources=sources,
    )
    if mutation in {"value", "evidence", "extra_assertion"}:
        items = list(candidate.assertions)
        item = items[0]
        if mutation == "value":
            value = json.loads(item.value)
            value["summary"] = "An alternate coherent meaning"
            items[0] = item.model_copy(update={"value": canonical_json(value)})
        elif mutation == "evidence":
            value = json.loads(item.value)
            value["evidence"][0]["source_span_ref_id"] = "span:alternate"
            refs = list(item.evidence_refs)
            ref = refs[0].model_copy(update={"source_span_ref_id": "span:alternate"})
            binding = ref.model_dump(mode="json", exclude={"evidence_ref_id"})
            raw = ref.evidence_ref_id.split(":dm-extraction-v3:")[0]
            refs[0] = ref.model_copy(update={"evidence_ref_id": raw + ":dm-extraction-v3:" + canonical_sha256(binding)})
            items[0] = item.model_copy(update={"value": canonical_json(value), "evidence_refs": refs})
        else:
            extra = item.model_copy(update={"assertion_id": "assertion:extra", "subject_object_id": "node:extra"})
            items.append(extra)
            states[extra.assertion_id] = AcceptanceState.ACCEPTED
        candidate = candidate.model_copy(update={"assertions": items})
    if mutation == "verdict":
        edge = next(item for item in candidate.assertions if item.assertion_kind == "edge")
        states[edge.assertion_id] = AcceptanceState.REJECTED
    actor = "other-reviewer" if mutation == "actor" else str(plan.run_id)
    proposals, verdicts = writes._build_identity_dispositions(candidate, states)
    assertion_verdicts = [ContributionAssertionVerdict(assertion_id=item.assertion_id, acceptance_state=states[item.assertion_id])
                          for item in sorted(candidate.assertions, key=lambda item: item.assertion_id)]
    profile = dict(schema_version="dm_semantic_profile_ref_v1", profile_id="dnd5e.default",
                   profile_revision="1", descriptor_sha256="12" * 32)
    payload = {"semantic_profile": profile}
    parent = SimpleNamespace(revision=SimpleNamespace(world_id=plan.world_id, revision_id=plan.parent_revision_id,
        status="published", graph_schema="dm_union_graph_v6", graph_payload_sha256=canonical_sha256(payload), created_at=stamp),
        graph_payload=payload)
    operation = writes.derive_authority_review_operation_id(world_id=plan.world_id,
        authority_operation_id=writes.worldbuilding_authority_operation_id(world_id=plan.world_id,
            plan_id=plan.plan_id, plan_digest=plan.plan_digest), operation_namespace="worldbuilding")
    plan_ref = ContributionPlanRef(
        source_plan_schema=writes.WORLDBUILDING_SOURCE_PLAN_SCHEMA, source_plan_id=operation,
        source_plan_sha256=canonical_sha256({"operation_id": operation, "contribution_id": original.contribution_id}),
        source_input_sha256=canonical_sha256({"contribution_id": original.contribution_id}),
        preview_content_sha256=canonical_sha256({}), candidate_contribution_sha256=contribution_v3_payload_sha256(candidate),
        expected_parent_revision_id=plan.parent_revision_id, base_graph_schema=parent.revision.graph_schema,
        base_graph_payload_sha256=parent.revision.graph_payload_sha256, semantic_profile=profile,
    )
    if mutation == "plan_ref":
        plan_ref = plan_ref.model_copy(update={"source_input_sha256": "34" * 32})
    fields = dict(operation_id=operation, world_id=plan.world_id, campaign_id=None, plan_ref=plan_ref,
        candidate_contribution=candidate, identity_proposals=proposals, identity_verdicts=verdicts,
        assertion_verdicts=assertion_verdicts, reviewer_id=actor, reviewed_at=review_time)
    digest = derive_review_intent_sha256_v3(**fields)
    intent = ContributionReviewIntentV3(**fields, review_intent_sha256=digest)
    confirmation = CommitConfirmationReceiptV3(
        confirmation_id=derive_confirmation_id(operation_id=operation, review_intent_sha256=digest, actor=actor, confirmed_at=review_time),
        operation_id=operation, review_intent_sha256=digest, actor=actor, world_id=plan.world_id,
        campaign_id=None, expected_parent_revision_id=plan.parent_revision_id, confirmed_at=review_time,
    )
    review = _build_review_state(ContributionReviewSubmissionV3(intent=intent, confirmation=confirmation))
    review = type(review).model_validate(review.model_dump(mode="json"))
    history = SimpleNamespace(review=review, publication=SimpleNamespace(
        expected_parent_revision_id=plan.parent_revision_id, parent_graph_payload_sha256=parent.revision.graph_payload_sha256,
        graph_schema="dm_union_graph_v6", published_at=review_time,
        published_revision_id="revision:historical:" + operation.removeprefix("reviewop:"),
    ), revision=SimpleNamespace(created_at=review_time))
    return plan, original, candidate, states, history, parent, operation


@pytest.mark.parametrize("mode", ["create", "bind", "bind_alias", "defer", "observation", "reject", "reject_node", "governs"])
def test_immutable_worldbuilding_complete_candidate_and_review_match_original_producer(monkeypatch, mode):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import (
        reconstruct_original_mapping, reconstruct_candidate, verify_review_correspondence,
    )
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    plan, original, expected, states, history, parent, operation = _immutable_worldbuilding_original_staging(monkeypatch, mode=mode)
    def forbidden(*args, **kwargs):
        pytest.fail("historical verification repeated fresh endpoint/parent admission")
    monkeypatch.setattr(writes, "_assert_edge_endpoint_admission", forbidden)
    monkeypatch.setattr(writes, "_candidate_endpoint_kinds", forbidden)
    reconstructed, mapped = reconstruct_original_mapping(plan)
    actual, actual_states = reconstruct_candidate(mapped, produced_at=parent.revision.created_at)
    assert reconstructed.model_dump(mode="json") == original.model_dump(mode="json")
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    assert actual_states == states
    verify_review_correspondence(plan, original=reconstructed, mapped=mapped, history=history, parent=parent, operation_id=operation)


@pytest.mark.parametrize("mutation", ["value", "evidence", "extra_assertion", "verdict", "actor", "plan_ref", "timestamp"])
def test_immutable_worldbuilding_valid_alternate_core_history_fails_complete_correspondence(monkeypatch, mutation):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import reconstruct_original_mapping, verify_review_correspondence
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    plan, _, _, _, history, parent, operation = _immutable_worldbuilding_original_staging(monkeypatch, mutation=mutation)
    original, mapped = reconstruct_original_mapping(plan)
    with pytest.raises(ExtractPromoteError) as error:
        verify_review_correspondence(plan, original=original, mapped=mapped, history=history, parent=parent, operation_id=operation)
    assert error.value.code == "publication_integrity_failure"



def _immutable_worldbuilding_reader_case(monkeypatch, *, mode="create"):
    from apps.live_control_server.integrations.dungeonmind import historical_worldbuilding_recovery as recovery
    plan, original, _, _, history, parent, operation = _immutable_worldbuilding_original_staging(monkeypatch, mode=mode)
    calls = []
    def read(world, actual_operation, *, reader):
        assert world == plan.world_id and actual_operation == operation
        calls.append("terminal")
        return history
    def get_parent(world, revision):
        assert world == plan.world_id and revision == plan.parent_revision_id
        calls.append("parent")
        return parent
    def binding(actual):
        assert actual is plan
        calls.append("binding")
        return (plan.publication_binding.managed_world_id, plan.world_id, plan.publication_binding.binding_version)
    monkeypatch.setattr(recovery, "_bare_readers", lambda: (object(), SimpleNamespace(get_revision=get_parent)))
    monkeypatch.setattr(recovery, "authorize_current_binding", binding)
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", read)
    return plan, original, history, parent, calls


@pytest.mark.parametrize("mode", ["create", "bind_alias", "reject", "defer", "observation", "governs"])
def test_immutable_worldbuilding_reader_returns_original_receipt_before_mutable_preflight(monkeypatch, mode):
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import recover_original_publication
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    plan, original, history, _, calls = _immutable_worldbuilding_reader_case(monkeypatch, mode=mode)
    before = plan.model_dump(mode="json", by_alias=True)
    def forbidden(*args, **kwargs):
        pytest.fail("immutable reader entered current-source/head/publisher preflight")
    for name in ("resolve_promotable_ingest_run", "_load_worldbuilding_publication_input", "_registered_publication_binding",
                 "_reprove_source_admission", "_worldbuilding_native_vocabulary_binding", "_verify_worldbuilding_child"):
        monkeypatch.setattr(service, name, forbidden)
    for name in ("_direct_services", "_build_pair_to_dm", "_recap_extraction_evidence_view", "publish_contribution_via_dungeonmind"):
        monkeypatch.setattr(writes, name, forbidden)
    receipt = recover_original_publication(plan, authorize_write=lambda: calls.append("owner"))
    assert calls == ["owner", "binding", "terminal", "parent", "owner", "binding"]
    assert (receipt.outcome, receipt.world_id, receipt.parent_revision_id, receipt.committed_revision_id) == (
        "already_applied", plan.world_id, plan.parent_revision_id, history.publication.published_revision_id,
    )
    assert receipt.head_advanced is True
    assert receipt.contribution_id == original.contribution_id
    assert receipt.accepted_assertion_ids == [item.assertion_id for item in original.accepted_assertions]
    assert receipt.rejected_assertion_ids == [item.assertion_id for item in original.rejected_assertions]
    assert receipt.unresolved_mention_ids == [item.mention_id for item in original.unresolved_mentions]
    assert plan.model_dump(mode="json", by_alias=True) == before


@pytest.mark.parametrize("outcome,code,status", [
    ("absent", "publication_receipt_unavailable", 409),
    ("integrity", "publication_integrity_failure", 409),
    ("unavailable", "authority_unavailable", 503),
    ("missing_parent", "publication_integrity_failure", 409),
    ("malformed_parent", "publication_integrity_failure", 409),
    ("unavailable_parent", "authority_unavailable", 503),
])
def test_immutable_worldbuilding_reader_failure_classes_preserve_packet(monkeypatch, outcome, code, status):
    from apps.live_control_server.integrations.dungeonmind import historical_worldbuilding_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from dungeonmind.domain.errors import PersistenceIntegrityError, PersistenceUnavailableError
    plan, _, _, _, calls = _immutable_worldbuilding_reader_case(monkeypatch)
    packet = plan.model_dump(mode="json", by_alias=True)
    if outcome in {"absent", "integrity", "unavailable"}:
        def terminal(*args, **kwargs):
            if outcome == "absent":
                return None
            if outcome == "integrity":
                raise PersistenceIntegrityError("stored terminal invalid")
            raise PersistenceUnavailableError("terminal store unavailable")
        monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", terminal)
    else:
        def parent(*args):
            if outcome == "missing_parent":
                return None
            if outcome == "malformed_parent":
                raise TypeError("stored parent JSON is null")
            raise PersistenceUnavailableError("parent store unavailable")
        monkeypatch.setattr(recovery, "_bare_readers", lambda: (object(), SimpleNamespace(get_revision=parent)))
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_publication(plan)
    assert (error.value.code, error.value.status_code) == (code, status)
    assert calls == (["binding"] if outcome in {"absent", "integrity", "unavailable"} else ["binding", "terminal"])
    assert plan.model_dump(mode="json", by_alias=True) == packet


def test_immutable_worldbuilding_owner_refusal_precedes_receipt_read(monkeypatch):
    from fastapi import HTTPException
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import recover_original_publication
    plan, _, _, _, calls = _immutable_worldbuilding_reader_case(monkeypatch)
    def deny():
        raise HTTPException(status_code=403, detail="owner changed")
    with pytest.raises(HTTPException):
        recover_original_publication(plan, authorize_write=deny)
    assert calls == []


def test_immutable_worldbuilding_late_owner_transfer_never_discloses_receipt(monkeypatch):
    from fastapi import HTTPException
    from apps.live_control_server.integrations.dungeonmind.historical_worldbuilding_recovery import recover_original_publication
    plan, _, _, _, calls = _immutable_worldbuilding_reader_case(monkeypatch)
    checks = []
    def authorize():
        checks.append("owner")
        if len(checks) == 2:
            raise HTTPException(status_code=403, detail="owner transferred")
    with pytest.raises(HTTPException):
        recover_original_publication(plan, authorize_write=authorize)
    assert checks == ["owner", "owner"] and calls == ["binding", "terminal", "parent"]



@pytest.fixture(autouse=True)
def _historical_worldbuilding_unit_store(monkeypatch):
    """Configured empty trusted history port unless a test explicitly seeds it.

    It never fabricates history from confirm. Core contracts and complete host
    correspondence still execute; real persistence/materialization is SQL-owned.
    """
    from apps.live_control_server.integrations.dungeonmind import historical_worldbuilding_recovery as recovery
    from dungeonmind.application.compatibility import read_historical_finalized_publication
    store = SimpleNamespace(entries={}, parents={}, reads=[], on_read=None,
                            real_readers=recovery._bare_readers, real_read=read_historical_finalized_publication)
    def read(world, operation, *, reader):
        reader.reads.append((world, operation))
        entry = reader.entries.get((world, operation))
        if reader.on_read is not None:
            reader.on_read()
        return entry
    monkeypatch.setattr(recovery, "_bare_readers", lambda: (
        store, SimpleNamespace(get_revision=lambda world, revision: store.parents.get((world, revision))),
    ))
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", read)
    return store


def _seed_worldbuilding_unit_history(monkeypatch, plan, authority):
    """Retain real producer/Core review state BEFORE calling receipt-only confirm."""
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.integrations.dungeonmind import historical_worldbuilding_recovery as recovery
    from apps.live_control_server.models.world_graph_mutation_context import wire_kind
    resolved = service.resolve_promotable_ingest_run(plan.run_id, root=service.live_config.repo_root())
    publication = service._load_worldbuilding_publication_input(resolved)
    preview = service._world_scoped_preview(publication.preview, plan.publication_binding)
    view = authority.revisions[(plan.world_id, plan.parent_revision_id)]
    context = WorldGraphMutationContext(world_id=plan.world_id, revision_id=plan.parent_revision_id,
        head_revision_id=plan.parent_revision_id, objects={key: MutationObject(
            object_id=key, label=obj.label, kind=wire_kind(obj.kind), aliases=tuple(obj.aliases),
            canon_state=getattr(obj, "canon_state", "canonical"), memory_state=getattr(obj, "memory_state", "graph_read_model"),
        ) for key, obj in view.objects.items()})
    _, original, _, _, history, parent, operation = _immutable_worldbuilding_original_staging(
        monkeypatch, prepared_plan=plan, producer_inputs={"preview": preview, "mutation_context": context},
    )
    store, _ = recovery._bare_readers()
    store.entries[(plan.world_id, operation)] = history
    store.parents[(plan.world_id, plan.parent_revision_id)] = parent
    return SimpleNamespace(store=store, original=original, history=history, parent=parent, operation=operation)


@pytest.fixture
def worldbuilding_history_core_dsn(monkeypatch, record_property):
    from tests.test_database_graph_object_authoring_evidence import historical_manual_core_dsn
    yield from historical_manual_core_dsn.__wrapped__(monkeypatch, record_property)


@pytest.mark.parametrize("terminal", ["present", "absent", "corrupt_child"])
def test_real_postgres_worldbuilding_history_after_descendant_and_withdrawal(
    tmp_path, monkeypatch, application_state_dsn, worldbuilding_history_core_dsn,
    _historical_worldbuilding_unit_store, terminal,
):
    from datetime import UTC, datetime, timedelta
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.contracts.evidence import SourceStatus
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle, PostgresSourceRepository, PostgresWorldGraphRepository
    from dungeonmind.infrastructure.postgres.database import jsonb
    from dungeonmind.infrastructure.postgres.serialization import model_fingerprint
    from dungeonmind.infrastructure.postgres.review_publication import PostgresFinalizedReviewPublicationRepository
    from graph_memory.worldbuilding_write_plan import _canonical_effect, materialize_worldbuilding_contribution
    from apps.live_control_server.models.extract_promote import WorldbuildingWritePlanPrepareRequest, WorldbuildingWritePlanConfirmRequest
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind import historical_worldbuilding_recovery as recovery
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import _worldbuilding_expressible
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import DungeonMindWorldGraphSourceAdmissionAdapter
    from tests._cutover_direct_dungeonmind_read_helpers import _payload
    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run
    from tests.test_database_graph_object_authoring_evidence import _database_rows_fingerprint

    dsn = worldbuilding_history_core_dsn
    world = "world:historical-worldbuilding-sql"
    repo = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=world)
    bundle = PostgresRepositoryBundle(PostgresDatabase(dsn))
    stamp = datetime(2025, 1, 1, tzinfo=UTC)
    payload = _payload()
    payload.update(world_id=world, objects=[], relationships=[], evidence_refs=[])
    parent = bundle.world_graph.publish_revision(PublishRevisionCommand(
        world_id=world, parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=["fixture:worldbuilding-history-parent"], graph_schema="dm_union_graph_v6",
        graph_payload=payload, created_at=stamp,
    ))
    # Only the historical preparation's mutation view is a unit port. Actual
    # source admission, staging, review, publication and subsequent reads are SQL.
    authority = FakeWorldGraphAuthority()
    authority.heads[world] = parent.revision_id
    authority.revisions[(world, parent.revision_id)] = _empty_parent(world_id=world, revision_id=parent.revision_id)
    _install_fake_authority(monkeypatch, authority)
    admission = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn)
    monkeypatch.setattr("apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority", lambda: admission)
    run, _ = _write_bld08_reviewable_run(repo, world_id="publication-managed", campaign_id="publication-managed")
    plan = service.prepare_worldbuilding(WorldbuildingWritePlanPrepareRequest.model_validate({
        "runId": run, "expectedParentRevisionId": parent.revision_id, "dispositions": _standard_dispositions(),
    }))
    original_packet = plan.model_dump(mode="json", by_alias=True)
    resolved = service.resolve_promotable_ingest_run(run, root=repo)
    source = service._load_worldbuilding_publication_input(resolved)
    effect = service._qualify_worldbuilding_native_edges(
        preview=source.preview, effect=_canonical_effect(plan.effect.model_dump(mode="json", by_alias=True)),
        native_vocabulary_binding=plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True),
    )
    original = materialize_worldbuilding_contribution(world_id=world, plan_digest=plan.plan_digest, effect=effect)
    operation = writes.derive_authority_review_operation_id(world_id=world,
        authority_operation_id=writes.worldbuilding_authority_operation_id(world_id=world, plan_id=plan.plan_id, plan_digest=plan.plan_digest),
        operation_namespace="worldbuilding")
    with monkeypatch.context() as publishing:
        publishing.setattr(writes, "_direct_services", lambda *_: SimpleNamespace(bundle=bundle))
        published = writes.publish_contribution_via_dungeonmind(world_id=world,
            expected_parent_revision_id=parent.revision_id, operation_id=operation, actor=str(run),
            contribution=_worldbuilding_expressible(original), database_url=dsn, publication_family="worldbuilding")
    child_id = published["committed_revision_id"]
    child = bundle.world_graph.get_revision(world, child_id)
    descendant = bundle.world_graph.publish_revision(PublishRevisionCommand(
        world_id=world, parent_revision_id=child_id, expected_parent_revision_id=child_id,
        operation_ids=["fixture:worldbuilding-history-descendant"], graph_schema=child.revision.graph_schema,
        graph_payload=child.graph_payload, created_at=stamp + timedelta(days=1),
    ))
    artifact = bundle.sources.get_artifact(plan.source_admission.source_artifact_id).model_copy(update={"status": SourceStatus.RETRACTED})
    with bundle.database.transaction() as conn:
        conn.execute("UPDATE dungeonmind.source_artifacts SET status=%s,payload=%s,record_fingerprint=%s WHERE source_artifact_id=%s",
            (artifact.status.value, jsonb(artifact.model_dump(mode="json")), model_fingerprint(artifact), artifact.source_artifact_id))
        if terminal == "absent":
            conn.execute("DELETE FROM dungeonmind.finalized_review_publications WHERE published_revision_id=%s", (child_id,))
        elif terminal == "corrupt_child":
            conn.execute("UPDATE dungeonmind.graph_revisions SET graph_payload='null'::jsonb WHERE revision_id=%s", (child_id,))
    assert bundle.sources.get_artifact(artifact.source_artifact_id).status is SourceStatus.RETRACTED
    assert bundle.world_graph.get_head(world).head_revision_id == descendant.revision_id != child_id
    monkeypatch.setattr(storage, "world_graph_authority_database_url", lambda: dsn)
    monkeypatch.setattr(recovery, "_bare_readers", _historical_worldbuilding_unit_store.real_readers)
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", _historical_worldbuilding_unit_store.real_read)
    before = (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn))
    def forbidden(*args, **kwargs):
        pytest.fail("receipt-only Worldbuilding recovery touched mutable source/head or publication")
    for name in ("resolve_promotable_ingest_run", "_load_worldbuilding_publication_input", "_worldbuilding_native_vocabulary_binding", "_reprove_source_admission"):
        monkeypatch.setattr(service, name, forbidden)
    for name in ("_direct_services", "_build_pair_to_dm", "publish_contribution_via_dungeonmind"):
        monkeypatch.setattr(writes, name, forbidden)
    for path in (
        "apps.live_control_server.services.graph_run_registry.get_extraction_run",
        "apps.live_control_server.services.graph_run_registry.load_reviewable_extraction_data",
        "apps.live_control_server.services.workspace_document_registry.get_workspace_document",
        "apps.live_control_server.services.source_artifact_registry.get_source_artifact",
        "apps.live_control_server.services.source_artifact_registry.load_source_input_bytes",
        "apps.live_control_server.services.worldbuilding_source_span_read.read_admitted_worldbuilding_span",
        "dungeonmind.application.contribution_review_v3.finalize_contribution_review_v3",
        "dungeonmind.application.review_publication.publish_finalized_review",
    ):
        monkeypatch.setattr(path, forbidden)
    monkeypatch.setattr(PostgresSourceRepository, "get_artifact", forbidden)
    monkeypatch.setattr(PostgresWorldGraphRepository, "get_head", forbidden)
    monkeypatch.setattr(PostgresWorldGraphRepository, "publish_revision", forbidden)
    monkeypatch.setattr(PostgresFinalizedReviewPublicationRepository, "publish", forbidden)
    for _ in range(2):
        if terminal == "present":
            receipt = service.confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
            assert receipt.outcome == "already_applied"
            assert (receipt.world_id, receipt.parent_revision_id, receipt.committed_revision_id) == (world, parent.revision_id, child_id)
            assert receipt.committed_revision_id != descendant.revision_id
        else:
            with pytest.raises(service.ExtractPromoteError) as error:
                service.confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
            assert error.value.code == ("publication_receipt_unavailable" if terminal == "absent" else "publication_integrity_failure")
        assert plan.model_dump(mode="json", by_alias=True) == original_packet
        assert (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn)) == before
    assert authority.publish_calls == 0
