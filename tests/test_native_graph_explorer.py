"""Managed native graph explorer contracts against a synthetic Core repository."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from worldkeeper.application import contracts as wk
from worldkeeper.application.commit import CommittedChangeOutcomeUnknown

from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from apps.live_control_server.routes.native_graph_explorer import router
from apps.live_control_server.services import native_graph_explorer as service
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)
from graph_memory.vnext.domain_runtime import (
    GM_LABEL,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_dnd5e_semantic_profile,
)
from tests.test_native_recap_preparation import lane as recap_lane, TOKEN  # noqa: F401


class InMemoryExplorerStore:
    """Test journal with the same operation scope and integrity checks as APP-STATE."""

    rows: dict[tuple[str, str, str], dict] = {}
    locks_guard = threading.Lock()
    locks: dict[tuple[str, str], threading.RLock] = {}

    def __init__(self, principal_subject, managed_world_id, *, max_operations=512):
        self.principal_subject = principal_subject
        self.managed_world_id = managed_world_id
        self.max_operations = max_operations
        self.scope = principal_subject, managed_world_id
        with self.locks_guard:
            self.lock = self.locks.setdefault(self.scope, threading.RLock())

    @contextmanager
    def atomic(self):
        with self.lock:
            yield self

    def close(self):
        return None

    def checkpoint(self):
        return None

    def operation_count(self):
        return sum(1 for key in self.rows if key[:2] == self.scope)

    def _key(self, operation_id):
        return (*self.scope, operation_id)

    def get_operation(self, operation_id):
        row = self.rows.get(self._key(operation_id))
        if row is None:
            return None
        result = copy.deepcopy(row)
        request_json = result["request_json"]
        if (
            hashlib.sha256(request_json.encode()).hexdigest()
            != result["request_sha256"]
        ):
            raise ValueError("operation request journal integrity check failed")
        result["request"] = json.loads(request_json)
        for field in ("source_receipt", "prepared", "committed", "rejected"):
            raw = result.get(field + "_json")
            digest = result.get(field + "_sha256")
            if raw is None:
                result[field] = None
            else:
                if hashlib.sha256(raw.encode()).hexdigest() != digest:
                    raise ValueError(
                        f"{field} operation journal integrity check failed"
                    )
                result[field] = json.loads(raw)
        return result

    def reserve_operation(
        self,
        *,
        operation_id,
        native_world_id,
        binding_version,
        expected_revision_id,
        request_json,
        updated_at,
    ):
        if self.operation_count() >= self.max_operations:
            raise OverflowError("operation journal full")
        digest = hashlib.sha256(request_json.encode()).hexdigest()
        self.rows[self._key(operation_id)] = {
            "principal_subject": self.principal_subject,
            "managed_world_id": self.managed_world_id,
            "operation_id": operation_id,
            "native_world_id": native_world_id,
            "binding_version": binding_version,
            "expected_revision_id": expected_revision_id,
            "parent_revision_id": None,
            "request_json": request_json,
            "request_sha256": digest,
            "source_admission_id": None,
            "source_receipt_json": None,
            "source_receipt_sha256": None,
            "prepared_json": None,
            "prepared_sha256": None,
            "committed_json": None,
            "committed_sha256": None,
            "rejected_json": None,
            "rejected_sha256": None,
            "status": "reserved",
            "created_at": updated_at,
            "updated_at": updated_at,
        }

    def mark_unknown(self, operation_id, *, updated_at):
        self.rows[self._key(operation_id)]["status"] = "unknown"
        self.rows[self._key(operation_id)]["updated_at"] = updated_at

    def mark_prepared(
        self,
        operation_id,
        *,
        source_admission_id,
        source_receipt_json,
        parent_revision_id,
        prepared_json,
        updated_at,
    ):
        row = self.rows[self._key(operation_id)]
        row.update(
            status="prepared",
            source_admission_id=source_admission_id,
            source_receipt_json=source_receipt_json,
            source_receipt_sha256=hashlib.sha256(
                source_receipt_json.encode()
            ).hexdigest(),
            parent_revision_id=parent_revision_id,
            prepared_json=prepared_json,
            prepared_sha256=hashlib.sha256(prepared_json.encode()).hexdigest(),
            updated_at=updated_at,
        )

    def mark_committed(self, operation_id, *, committed_json, updated_at):
        row = self.rows[self._key(operation_id)]
        row.update(
            status="committed",
            committed_json=committed_json,
            committed_sha256=hashlib.sha256(committed_json.encode()).hexdigest(),
            rejected_json=None,
            rejected_sha256=None,
            updated_at=updated_at,
        )

    def mark_rejected(self, operation_id, *, code, error, updated_at):
        payload = json.dumps(
            {"code": code, "error": error}, sort_keys=True, separators=(",", ":")
        )
        row = self.rows[self._key(operation_id)]
        row.update(
            status="rejected",
            rejected_json=payload,
            rejected_sha256=hashlib.sha256(payload.encode()).hexdigest(),
            committed_json=None,
            committed_sha256=None,
            updated_at=updated_at,
        )


@pytest.fixture
def explorer(monkeypatch, request):
    lane = request.getfixturevalue("recap_lane")
    InMemoryExplorerStore.rows.clear()
    InMemoryExplorerStore.locks.clear()
    bound = {"managed_world_id": "managed", **lane.bound}

    def binding(managed_world_id):
        if managed_world_id != bound["managed_world_id"]:
            raise service.WorldGraphProjectionServiceError(
                "not found", code="managed_world_not_found", status_code=404
            )
        return copy.deepcopy(bound)

    monkeypatch.setattr(service.native, "binding", binding)
    monkeypatch.setattr(service.native, "repository", lambda: lane.repo)
    monkeypatch.setattr(service.native, "read_repository", lambda: lane.repo)
    monkeypatch.setattr(service, "NativeGraphExplorerStore", InMemoryExplorerStore)
    app = FastAPI()
    app.include_router(router)
    principal = NativeGraphPrincipal("local_operator", "gm", "local_operator")
    app.dependency_overrides[native_graph_gm_dependency] = lambda: principal
    client = TestClient(app, client=("127.0.0.1", 50000))
    return SimpleNamespace(**locals())


def _snapshot(repo):
    return copy.deepcopy(
        {key: value for key, value in repo.__dict__.items() if key != "_lock"}
    )


def _read(x, managed_world_id="managed"):
    return x.client.post(
        "/api/live/native-graph-explorer/graph",
        json={"managed_world_id": managed_world_id},
    )


def _prepare(x, kind, **extra):
    response = x.client.post(
        "/api/live/native-graph-explorer/prepare",
        json={
            "managed_world_id": "managed",
            "native_world_id": x.bound["native_world_id"],
            "binding_version": x.bound["binding_version"],
            "expected_revision_id": _read(x).json()["graph"]["revision_id"],
            "operation_id": str(uuid4()),
            "kind": kind,
            **extra,
        },
    )
    return response


def _seed_objects(x):
    repo = x.lane.repo
    space = x.bound["native_world_id"]
    head = repo.get_head(space).head_revision_id
    domain, profile = service.native.descriptors(repo, space, head)
    metadata = wk.AssertionMetadata(
        scope=(),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(x.lane.support_ids["first"],),
    )
    operations = (
        wk.CreateObject(
            "alice",
            (
                wk.CreateFact(
                    "alice-name",
                    "dnd5e:name",
                    wk.LiteralFactValue.from_json("Alice"),
                    metadata,
                ),
                wk.CreateFact(
                    "alice-kind",
                    "dnd5e:classification",
                    wk.TermRefFactValue("dnd5e:npc"),
                    metadata,
                ),
            ),
        ),
        wk.CreateObject(
            "tower",
            (
                wk.CreateFact(
                    "tower-kind",
                    "dnd5e:classification",
                    wk.TermRefFactValue("dnd5e:location"),
                    metadata,
                ),
            ),
        ),
    )
    now = datetime.now(UTC)
    runtime = transport.runtime(
        repo, domain, profile, now=now, operation_id="synthetic-explorer-seed"
    )
    result = runtime.commit_prepared_change(
        runtime.prepare_change(
            wk.WorldChangeIntent(space, "test:native-graph-explorer", operations)
        ),
        confirmed_by="local_operator",
    )
    return {item.client_op_id: item.durable_object_id for item in result.object_results}


def test_read_is_exact_native_projection_without_any_writes(explorer):
    x = explorer
    before = _snapshot(x.lane.repo)
    response = _read(x)
    assert response.status_code == 200, response.text
    envelope = response.json()
    assert envelope["schema"] == "dmb_native_graph_explorer_v1"
    assert envelope["managed_world_id"] == "managed"
    assert envelope["native_world_id"] == x.bound["native_world_id"]
    assert envelope["binding_version"] == x.bound["binding_version"]
    graph = envelope["graph"]
    assert graph["world_id"] == x.bound["native_world_id"]
    assert (
        graph["revision_id"]
        == x.lane.repo.get_head(x.bound["native_world_id"]).head_revision_id
    )
    assert graph["nodes"] == [] and graph["edges"] == []
    assert graph["capabilities"]["object_kinds"] == ["person", "location"]
    assert graph["capabilities"]["allowed_predicates"] == ["allied_with", "located_in"]
    assert graph["capabilities"]["allows_custom_predicates"] is True
    assert graph["completeness"] == {
        "status": "complete",
        "listed_entities": 0,
        "omitted_entities": 0,
        "unexamined_entities": 0,
        "listed_assertions": 0,
        "omitted_assertions": 0,
        "unexamined_assertions": 0,
        "reasons": [],
    }
    assert _snapshot(x.lane.repo) == before


def test_create_review_confirm_replay_and_created_id_come_from_native_receipt(explorer):
    x = explorer
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Ariadne",
        "object_kind": "person",
    }
    prepared = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert prepared.status_code == 200, prepared.text
    p = prepared.json()
    assert p["status"] == "prepared" and p["operation_id"] == request["operation_id"]
    assert p["schema"] == "dmb_native_graph_explorer_v1"
    assert p["managed_world_id"] == "managed"
    assert p["native_world_id"] == x.bound["native_world_id"]
    assert p["binding_version"] == x.bound["binding_version"]
    assert p["review"]["summary"] == "Create person “Ariadne” in the selected World."
    source_id = service._source_admission_id(
        request["operation_id"], x.principal.subject, x.bound
    )
    receipt = x.lane.repo.get_native_source_admission_receipt(
        x.bound["native_world_id"], source_id
    )
    assert (
        receipt is not None
        and receipt.publication_receipt.expected_parent_revision_id
        == graph["revision_id"]
    )
    assert _read(x).json()["graph"]["nodes"] == []

    body = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    confirmed = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert confirmed.status_code == 200, confirmed.text
    first = confirmed.json()
    assert first["status"] == "committed"
    created_id = first["created_node_id"]
    assert created_id.startswith("ent:")
    assert created_id in {node["id"] for node in first["graph"]["graph"]["nodes"]}
    publication = x.lane.repo.get_prospective_publication(
        x.bound["native_world_id"],
        service._publication_id(request["operation_id"], x.principal.subject, x.bound),
    )
    result = next(
        row
        for row in publication.prospective_result.results
        if row.client_op_id == "new-object"
    )
    assert result.durable_id == created_id

    replay = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json()["created_node_id"] == created_id
    operation = x.client.post(
        "/api/live/native-graph-explorer/operations/read", json=body
    )
    assert operation.status_code == 200, operation.text
    assert operation.json()["status"] == "committed"
    assert operation.json()["schema"] == "dmb_native_graph_explorer_v1"
    assert operation.json()["created_node_id"] == created_id
    assert (
        len(
            [
                node
                for node in operation.json()["graph"]["graph"]["nodes"]
                if node["id"] == created_id
            ]
        )
        == 1
    )
    assert (
        x.lane.repo.get_head(x.bound["native_world_id"]).head_revision_id
        == first["graph"]["graph"]["revision_id"]
    )


def test_registered_connection_is_published_as_exact_native_predicate(explorer):
    x = explorer
    ids = _seed_objects(x)
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "connect",
        "source_id": ids["alice"],
        "target_id": ids["tower"],
        "predicate": "located_in",
    }
    prepared = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == "prepared"
    stored = InMemoryExplorerStore.rows[
        (x.principal.subject, "managed", request["operation_id"])
    ]
    admitted = x.lane.repo.get_native_source_admission_receipt(
        x.bound["native_world_id"], stored["source_admission_id"]
    )
    _, source_access, _, _ = service.native.read_context(
        x.lane.repo,
        x.bound["native_world_id"],
        admitted.published_revision_id,
        None,
        x.principal.role,
        scope_mode="world",
    )
    authored = service.open_admitted_native_text(
        source_access, admitted.bindings[0].evidence_ref_id
    )
    assert ids["alice"] not in authored.body_text
    assert ids["tower"] not in authored.body_text
    assert "located_in" in authored.body_text
    prepared_packet = InMemoryExplorerStore(
        x.principal.subject, "managed"
    ).get_operation(request["operation_id"])["prepared"]
    prepared_value = service.transport.decode_prepared(prepared_packet)
    relationship = prepared_value.prepared_operations[0]
    assert relationship.source.durable_object_id == ids["alice"]
    assert relationship.target.durable_object_id == ids["tower"]
    assert relationship.predicate == "dnd5e:located_in"
    body = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    result = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "committed"
    assert "created_node_id" not in result.json()
    edge = next(
        edge
        for edge in result.json()["graph"]["graph"]["edges"]
        if edge["predicate"] == "located_in"
    )
    assert edge["source_id"] == ids["alice"] and edge["target_id"] == ids["tower"]
    publication = x.lane.repo.get_prospective_publication(
        x.bound["native_world_id"],
        service._publication_id(request["operation_id"], x.principal.subject, x.bound),
    )
    native_result = next(
        row
        for row in publication.prospective_result.results
        if row.client_op_id == "new-relationship"
    )
    assertion = x.lane.repo.get_revision(
        x.bound["native_world_id"], publication.prospective_result.published_revision_id
    )
    row = next(
        item
        for item in assertion.graph_payload["assertions"]
        if item["assertion_id"] == native_result.durable_id
    )
    assert row["predicate"] == "dnd5e:located_in"


def test_opted_in_custom_connection_uses_only_actual_open_namespace(explorer):
    x = explorer
    ids = _seed_objects(x)
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "connect",
        "source_id": ids["alice"],
        "target_id": ids["tower"],
        "predicate": "works_at",
    }
    prepared = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == "prepared"
    body = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    committed = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    edge = next(
        item
        for item in committed.json()["graph"]["graph"]["edges"]
        if item["source_id"] == ids["alice"] and item["target_id"] == ids["tower"]
    )
    assert edge["predicate"] == "works_at"
    publication = x.lane.repo.get_prospective_publication(
        x.bound["native_world_id"],
        service._publication_id(request["operation_id"], x.principal.subject, x.bound),
    )
    native_result = next(
        row
        for row in publication.prospective_result.results
        if row.client_op_id == "new-relationship"
    )
    revision = x.lane.repo.get_revision(
        x.bound["native_world_id"], publication.prospective_result.published_revision_id
    )
    assertion = next(
        row
        for row in revision.graph_payload["assertions"]
        if row["assertion_id"] == native_result.durable_id
    )
    assert assertion["predicate"] == "dungeonbuddy.custom:works_at"


def test_custom_connection_rejects_caller_namespace_prefix(explorer):
    x = explorer
    ids = _seed_objects(x)
    graph = _read(x).json()["graph"]
    response = x.client.post(
        "/api/live/native-graph-explorer/prepare",
        json={
            "managed_world_id": "managed",
            "native_world_id": x.bound["native_world_id"],
            "binding_version": x.bound["binding_version"],
            "expected_revision_id": graph["revision_id"],
            "operation_id": str(uuid4()),
            "kind": "connect",
            "source_id": ids["alice"],
            "target_id": ids["tower"],
            "predicate": "story:knows",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_predicate"


def test_already_exists_response_has_verified_world_and_operation_identity(explorer):
    x = explorer
    ids = _seed_objects(x)
    graph = _read(x).json()["graph"]
    first_request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "connect",
        "source_id": ids["alice"],
        "target_id": ids["tower"],
        "predicate": "located_in",
    }
    assert (
        x.client.post(
            "/api/live/native-graph-explorer/prepare", json=first_request
        ).json()["status"]
        == "prepared"
    )
    committed = x.client.post(
        "/api/live/native-graph-explorer/confirm",
        json={
            "managed_world_id": "managed",
            "operation_id": first_request["operation_id"],
        },
    )
    assert committed.status_code == 200 and committed.json()["status"] == "committed"
    current = committed.json()["graph"]["graph"]["revision_id"]
    duplicate_id = str(uuid4())
    duplicate = x.client.post(
        "/api/live/native-graph-explorer/prepare",
        json={
            **first_request,
            "expected_revision_id": current,
            "operation_id": duplicate_id,
        },
    )
    assert duplicate.status_code == 200
    result = duplicate.json()
    assert result["status"] == "already_exists"
    assert result["schema"] == "dmb_native_graph_explorer_v1"
    assert result["operation_id"] == duplicate_id
    assert result["managed_world_id"] == "managed"
    assert result["native_world_id"] == x.bound["native_world_id"]
    assert result["binding_version"] == x.bound["binding_version"]


def test_operation_id_reuse_and_cross_principal_read_fail_closed(explorer, monkeypatch):
    x = explorer
    graph = _read(x).json()["graph"]
    operation_id = str(uuid4())
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": operation_id,
        "kind": "create_object",
        "name": "One",
        "object_kind": "person",
    }
    first = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert first.status_code == 200 and first.json()["status"] == "prepared"
    changed = {**request, "name": "Two"}
    conflict = x.client.post("/api/live/native-graph-explorer/prepare", json=changed)
    assert (
        conflict.status_code == 409
        and conflict.json()["detail"]["code"] == "operation_id_conflict"
    )

    original_source_id = service._source_admission_id(
        operation_id, x.principal.subject, x.bound
    )
    other = NativeGraphPrincipal("other-gm", "gm", "local_operator")
    x.app.dependency_overrides[native_graph_gm_dependency] = lambda: other
    not_found = x.client.post(
        "/api/live/native-graph-explorer/operations/read",
        json={"managed_world_id": "managed", "operation_id": operation_id},
    )
    assert not_found.status_code == 200 and not_found.json()["status"] == "not_found"
    assert not_found.json()["schema"] == "dmb_native_graph_explorer_v1"
    assert not_found.json()["native_world_id"] == x.bound["native_world_id"]
    current_revision = _read(x).json()["graph"]["revision_id"]
    other_prepare = x.client.post(
        "/api/live/native-graph-explorer/prepare",
        json={**request, "expected_revision_id": current_revision},
    )
    assert (
        other_prepare.status_code == 200
        and other_prepare.json()["status"] == "prepared"
    )
    other_source_id = service._source_admission_id(operation_id, other.subject, x.bound)
    assert other_source_id != original_source_id
    assert service._publication_id(
        operation_id, other.subject, x.bound
    ) != service._publication_id(operation_id, x.principal.subject, x.bound)
    assert (
        x.lane.repo.get_native_source_admission_receipt(
            x.bound["native_world_id"], original_source_id
        )
        is not None
    )
    assert (
        x.lane.repo.get_native_source_admission_receipt(
            x.bound["native_world_id"], other_source_id
        )
        is not None
    )


def test_forged_world_binding_and_unbound_world_do_not_select_native_authority(
    explorer,
):
    x = explorer
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": "another-native-world",
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Forged",
        "object_kind": "person",
    }
    forged = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert (
        forged.status_code == 409
        and forged.json()["detail"]["code"] == "binding_changed"
    )
    unbound = _read(x, "foreign")
    assert (
        unbound.status_code == 404
        and unbound.json()["detail"]["code"] == "managed_world_not_found"
    )


def test_binding_change_after_prepare_is_unknown_and_never_retargets(
    explorer, monkeypatch
):
    x = explorer
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Never retarget",
        "object_kind": "location",
    }
    prepared = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert prepared.status_code == 200 and prepared.json()["status"] == "prepared"
    x.bound["native_world_id"] = "native-new-binding"
    x.bound["binding_version"] += 1
    body = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    result = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert result.status_code == 200 and result.json()["status"] == "unknown"
    assert "different World" in result.json()["message"]
    assert (
        x.lane.repo.get_prospective_publication(
            x.lane.bound["native_world_id"],
            service._publication_id(
                request["operation_id"], x.principal.subject, x.bound
            ),
        )
        is None
    )


def test_interrupted_prepare_retries_exact_request_without_repeating_source_admission(
    explorer, monkeypatch
):
    x = explorer
    initial = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": initial["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Recovered review",
        "object_kind": "person",
    }
    original = InMemoryExplorerStore.mark_prepared

    def interrupted(*args, **kwargs):
        raise RuntimeError("lost journal write before review was stored")

    monkeypatch.setattr(InMemoryExplorerStore, "mark_prepared", interrupted)
    first = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert first.status_code == 200 and first.json()["status"] == "unknown"
    after_admission = _snapshot(x.lane.repo)
    lookup = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    for _ in range(2):
        result = x.client.post(
            "/api/live/native-graph-explorer/operations/read", json=lookup
        )
        assert result.status_code == 200
        assert result.json()["status"] == "unknown"
        assert result.json()["recovery_action"] == "retry_prepare"
    assert _snapshot(x.lane.repo) == after_admission
    changed = x.client.post(
        "/api/live/native-graph-explorer/prepare",
        json={**request, "name": "Different request"},
    )
    assert changed.status_code == 409
    assert changed.json()["detail"]["code"] == "operation_id_conflict"
    monkeypatch.setattr(InMemoryExplorerStore, "mark_prepared", original)
    recovered = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert recovered.status_code == 200 and recovered.json()["status"] == "prepared"
    assert recovered.json()["operation_id"] == request["operation_id"]
    assert _snapshot(x.lane.repo) == after_admission
    row = next(iter(InMemoryExplorerStore.rows.values()))
    row["status"] = "unknown"
    uncertain = x.client.post(
        "/api/live/native-graph-explorer/operations/read", json=lookup
    )
    assert uncertain.json()["status"] == "unknown"
    assert "recovery_action" not in uncertain.json()
    committed = x.client.post("/api/live/native-graph-explorer/confirm", json=lookup)
    assert committed.status_code == 200 and committed.json()["status"] == "committed"
    assert (
        sum(
            node["name"] == request["name"]
            for node in committed.json()["graph"]["graph"]["nodes"]
        )
        == 1
    )


@pytest.mark.parametrize(
    "status,partial",
    [
        ("reserved", {}),
        ("unknown", {}),
        ("prepared", {}),
        ("committed", {}),
        ("unknown", {"parent_revision_id": "saved-review-parent"}),
        ("unknown", {"source_admission_id": "saved-admission"}),
        ("unknown", {"source_receipt": {"saved": True}}),
        ("unknown", {"committed": {"saved": True}}),
    ],
)
def test_prepare_retry_action_requires_an_intact_pre_review_journal(status, partial):
    record = {
        "status": status,
        "prepared": None,
        "operation_id": "same-operation",
        "managed_world_id": "managed",
        "native_world_id": "native",
        "binding_version": 1,
        **partial,
    }
    result = service._operation_lookup(record, {}, None, None)
    expected = status in {"reserved", "unknown"} and not partial
    assert (result.get("recovery_action") == "retry_prepare") is expected


def test_lost_commit_response_recovers_receipt_and_same_created_node_id(
    explorer, monkeypatch
):
    x = explorer
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Lost reply",
        "object_kind": "person",
    }
    prepared = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert prepared.status_code == 200 and prepared.json()["status"] == "prepared"
    real_runtime = service.transport.runtime
    fired = False

    def commit_then_lose_response(*args, **kwargs):
        nonlocal fired
        runtime = real_runtime(*args, **kwargs)

        class RuntimeProxy:
            def __getattr__(self, name):
                return getattr(runtime, name)

            def commit_prepared_change(self, *commit_args, **commit_kwargs):
                nonlocal fired
                result = runtime.commit_prepared_change(*commit_args, **commit_kwargs)
                if not fired:
                    fired = True
                    prepared = commit_args[0]
                    raise CommittedChangeOutcomeUnknown(
                        prepared_change_id=prepared.prepared_change_id,
                        publication_id=prepared.dungeonmind_publication_id,
                        expected_published_revision_id=result.child_revision_id,
                    )
                return result

        return RuntimeProxy()

    monkeypatch.setattr(service.transport, "runtime", commit_then_lose_response)
    body = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    first = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert first.status_code == 200 and first.json()["status"] == "unknown"
    assert fired is True
    monkeypatch.setattr(service.transport, "runtime", real_runtime)
    recovered = x.client.post(
        "/api/live/native-graph-explorer/operations/read", json=body
    )
    assert recovered.status_code == 200 and recovered.json()["status"] == "committed"
    created_id = recovered.json()["created_node_id"]
    assert created_id in {
        node["id"] for node in recovered.json()["graph"]["graph"]["nodes"]
    }
    again = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert again.status_code == 200 and again.json()["created_node_id"] == created_id
    assert (
        x.lane.repo.get_head(x.bound["native_world_id"]).head_revision_id
        == recovered.json()["graph"]["graph"]["revision_id"]
    )


@pytest.mark.parametrize("journal_status", ["unknown", "committed"])
def test_mutated_native_aggregate_never_becomes_committed_on_recovery(
    explorer, journal_status
):
    x = explorer
    graph = _read(x).json()["graph"]
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": graph["revision_id"],
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Aggregate integrity",
        "object_kind": "person",
    }
    prepared = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert prepared.status_code == 200 and prepared.json()["status"] == "prepared"
    body = {"managed_world_id": "managed", "operation_id": request["operation_id"]}
    committed = x.client.post("/api/live/native-graph-explorer/confirm", json=body)
    assert committed.status_code == 200 and committed.json()["status"] == "committed"
    expected_head = committed.json()["graph"]["graph"]["revision_id"]
    row = InMemoryExplorerStore.rows[
        (x.principal.subject, "managed", request["operation_id"])
    ]
    if journal_status == "unknown":
        row["status"] = "unknown"

    from dungeonmind.domain.canonical import canonical_sha256

    publication_id = service._publication_id(
        request["operation_id"], x.principal.subject, x.bound
    )
    publication_key = (x.bound["native_world_id"], publication_id)
    original_result = x.lane.repo._prospective_results[publication_key]
    changed_result = original_result.model_copy(
        update={"prospective_request_sha256": "f" * 64}
    )
    x.lane.repo._prospective_results[publication_key] = changed_result
    x.lane.repo._prospective_fingerprints[publication_key] = canonical_sha256(
        changed_result.model_dump(mode="json")
    )
    recovered = x.client.post(
        "/api/live/native-graph-explorer/operations/read", json=body
    )
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "unknown"
    assert "created_node_id" not in recovered.json()
    assert (
        x.lane.repo.get_head(x.bound["native_world_id"]).head_revision_id
        == expected_head
    )
    assert row["status"] == "unknown"


def test_v2_and_v3_predicate_capabilities_follow_immutable_profiles():
    standard = dungeonbuddy_dnd5e_semantic_profile()
    opted_in = dungeonbuddy_dnd5e_custom_predicate_profile()
    standard_caps = service._profile_capabilities(standard)
    opted_in_caps = service._profile_capabilities(opted_in)
    assert standard_caps["object_kinds"] == ["person", "location"]
    assert standard_caps["allowed_predicates"] == ["allied_with", "located_in"]
    assert standard_caps["allows_custom_predicates"] is False
    assert service._native_predicate("located_in", standard) == "dnd5e:located_in"
    with pytest.raises(service.NativeGraphExplorerError) as error:
        service._native_predicate("arbitrary_label", standard)
    assert error.value.code == "unsupported_predicate"
    assert opted_in_caps["allows_custom_predicates"] is True
    assert (
        service._native_predicate("works_at", opted_in)
        == "dungeonbuddy.custom:works_at"
    )


def test_ambiguous_registered_predicate_suffix_is_not_selected():
    profile = dungeonbuddy_dnd5e_semantic_profile()
    original = next(
        item for item in profile.predicates if item.term == "dnd5e:located_in"
    )
    duplicate = original.model_copy(update={"term": "other:located_in"})
    ambiguous = profile.model_copy(
        update={"predicates": [*profile.predicates, duplicate]}
    )
    capabilities = service._profile_capabilities(ambiguous)
    assert "located_in" not in capabilities["allowed_predicates"]
    with pytest.raises(service.NativeGraphExplorerError) as error:
        service._native_predicate("located_in", ambiguous)
    assert error.value.code == "ambiguous_predicate"


def test_stale_expected_revision_is_rejected_before_operation_reservation(explorer):
    x = explorer
    request = {
        "managed_world_id": "managed",
        "native_world_id": x.bound["native_world_id"],
        "binding_version": x.bound["binding_version"],
        "expected_revision_id": "rev:stale-forged",
        "operation_id": str(uuid4()),
        "kind": "create_object",
        "name": "Stale",
        "object_kind": "person",
    }
    response = x.client.post("/api/live/native-graph-explorer/prepare", json=request)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "stale_revision"
    assert InMemoryExplorerStore.rows == {}


def test_non_gm_and_unconfigured_auth_cannot_read_or_write(
    explorer, monkeypatch, tmp_path
):
    x = explorer
    x.app.dependency_overrides[native_graph_gm_dependency] = lambda: (
        NativeGraphPrincipal("player", "player", "local_operator")
    )
    denied = _read(x)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "graph_gm_required"

    from apps.live_control_server.services import agent_graph_local_session as session

    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv(
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
        "synthetic-local-operator-token-0123456789",
    )
    monkeypatch.setenv(session.ORIGIN_ENV, "http://127.0.0.1:5202")
    monkeypatch.setenv(session.HOST_ENV, "127.0.0.1:8000")
    monkeypatch.setenv(session.STORE_ENV, str(tmp_path / "graph-sessions.json"))
    session_app = FastAPI()
    session_app.include_router(router)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/live/native-graph-explorer/graph",
        "raw_path": b"/api/live/native-graph-explorer/graph",
        "query_string": b"",
        "headers": [
            (b"host", b"127.0.0.1:8000"),
            (b"origin", b"http://127.0.0.1:5202"),
            (b"sec-fetch-site", b"same-origin"),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "app": session_app,
    }
    session_id, csrf = session.issue_session(Request(scope))
    headers = {
        "host": "127.0.0.1:8000",
        "origin": "http://127.0.0.1:5202",
        "sec-fetch-site": "same-origin",
    }
    client = TestClient(session_app, client=("127.0.0.1", 50000))
    client.cookies.set(session.session_cookie_name(), session_id)
    csrf_rejected = client.post(
        "/api/live/native-graph-explorer/graph",
        json={"managed_world_id": "managed"},
        headers=headers,
    )
    assert csrf_rejected.status_code == 403
    assert csrf_rejected.json()["detail"]["code"] == "graph_auth_csrf_rejected"
    csrf_accepted = client.post(
        "/api/live/native-graph-explorer/graph",
        json={"managed_world_id": "managed"},
        headers={**headers, "x-dmb-graph-csrf": csrf},
    )
    assert csrf_accepted.status_code == 200, csrf_accepted.text

    for name in (
        "DMB_AGENT_GRAPH_AUTH_MODE",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    unauthed = FastAPI()
    unauthed.include_router(router)
    response = TestClient(unauthed, client=("127.0.0.1", 50000)).post(
        "/api/live/native-graph-explorer/graph",
        json={"managed_world_id": "managed"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "graph_auth_unavailable"
