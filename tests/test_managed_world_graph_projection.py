from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from types import SimpleNamespace

from pydantic import ValidationError
import pytest

from apps.live_control_server.services import (
    managed_world_graph_projection as managed_projection,
)
from apps.live_control_server.services.world_container_registry import (
    NativeGraphBindingRecord,
    WorldContainerRecord,
    WorldContainerRegistryError,
    create_world_container,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
)


def _request(
    **overrides: object,
) -> managed_projection.ManagedWorldGraphProjectionRequest:
    payload: dict[str, object] = {
        "schema": "dmb_managed_world_graph_projection_request_v1",
        "managedWorldId": "the-glass-orchard",
    }
    payload.update(overrides)
    return managed_projection.ManagedWorldGraphProjectionRequest.model_validate(payload)


def _record_with_binding(
    record: WorldContainerRecord,
    *,
    native_world_id: str = "eldyrwild",
    binding_version: int = 1,
    status: str = "active",
) -> WorldContainerRecord:
    binding = NativeGraphBindingRecord(
        native_world_id=native_world_id,
        binding_version=binding_version,
        status=status,
        validated_at="2026-10-02T00:00:00Z",
        validated_head_revision_id="rev:binding-head",
    )
    return record.model_copy(update={"native_graph_binding": binding})


def _native_projection(world_id: str = "eldyrwild") -> WorldGraphProjection:
    return WorldGraphProjection.model_validate(
        {
            "schema": "dmb_world_graph_projection_v1",
            "snapshot": {
                "worldId": world_id,
                "campaignId": "",
                "revisionId": "rev:read",
                "headRevisionId": "rev:head",
                "isHead": True,
                "focus": {"kind": "none"},
                "admissibility": "gm",
                "scopeMode": "world",
            },
            "summary": {
                "nodeCount": 0,
                "relationshipCount": 0,
                "attributeCount": 0,
                "evidenceCount": 0,
                "sourceArtifactCount": 0,
            },
            "trustBoundary": {"canTrust": [], "cannotTrust": []},
        }
    )



def _native_projection_stub(monkeypatch, *, on_read=None):
    """Orchestration fixture; actual Core/HTTP provenance is proved separately."""
    from apps.live_control_server.integrations.dungeonmind import vnext_world_projection as adapter

    seen, outputs = [], []
    context, source_access = object(), object()
    def read(binding, revision_pin):
        seen.append((binding.native_world_id, revision_pin))
        if on_read is not None:
            on_read()
        revision = revision_pin or "rev:head"
        support = SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id=revision)))
        return "rev:head", context, source_access, support
    def project(actual_context, support, snapshot, *, access: object, managed_world_id):
        assert actual_context is context and access is source_access
        assert managed_world_id == "the-glass-orchard"
        assert snapshot.revision_id == support.listing.identity.revision_id
        projection = _native_projection(snapshot.world_id)
        projection.snapshot = snapshot
        outputs.append(projection)
        return projection
    monkeypatch.setattr(managed_projection, "_read_native_projection_support", read)
    monkeypatch.setattr(adapter, "project_native_world", project)
    return seen, outputs


def test_active_binding_reads_native_world_and_returns_unchanged_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    managed = create_world_container(name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(
        managed_projection,
        "get_world_container",
        lambda _world_id: bound,
    )
    seen, outputs = _native_projection_stub(monkeypatch)
    result = managed_projection.project_managed_world_graph(
        _request(revisionPin="rev:requested", queryText="keeper"), root=tmp_path
    )
    assert seen == [("eldyrwild", "rev:requested")]
    assert result.managed_world_id == managed.world_id
    assert result.native_world_id == "eldyrwild" and result.binding_version == 1
    assert result.projection is outputs[0]
    assert result.projection.snapshot.world_id == "eldyrwild"
    assert result.projection.snapshot.revision_id == "rev:requested"
    assert result.projection.snapshot.head_revision_id == "rev:head"
    assert not result.projection.snapshot.is_head
    assert result.projection.snapshot.focus.kind == "none"
    assert result.projection.snapshot.admissibility == "gm"
    assert result.projection.snapshot.scope_mode == "world"
    assert result.projection.query_context.query_text == "keeper"


def test_shared_binding_resolver_does_not_read_native_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = create_world_container(name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(
        managed_projection, "get_world_container", lambda _world_id: bound
    )
    monkeypatch.setattr(
        managed_projection, "_read_native_projection_support",
        lambda *_args: pytest.fail("binding resolution read the native Graph"),
    )
    binding = managed_projection.resolve_managed_world_binding(
        managed.world_id, root=tmp_path
    )
    assert binding.managed_world_id == managed.world_id
    assert binding.native_world_id == "eldyrwild"
    assert binding.binding_version == 1
    assert binding.source_root_relpath == f"corpus/{managed.world_id}-markdown"


@pytest.mark.parametrize(
    "state", ["missing-record", "unbound", "inactive", "wrong-world", "provisioning"]
)
def test_unresolvable_or_unverified_binding_fails_before_native_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    managed = create_world_container(name="The Glass Orchard")
    record = managed
    if state == "unbound":
        record = managed.model_copy(update={"native_graph_binding": None})
    elif state == "inactive":
        record = _record_with_binding(managed, status="inactive")
    elif state == "wrong-world":
        record = _record_with_binding(managed).model_copy(update={"world_id": "other-world"})

    def resolve(_world_id: str) -> WorldContainerRecord:
        if state == "missing-record":
            raise WorldContainerRegistryError("not found", status_code=404)
        return record

    monkeypatch.setattr(managed_projection, "get_world_container", resolve)
    reader_calls = []
    monkeypatch.setattr(managed_projection, "_read_native_projection_support",
                        lambda *args: reader_calls.append(args) or pytest.fail("invalid binding reached native read"))

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        managed_projection.project_managed_world_graph(_request(), root=tmp_path)

    assert reader_calls == []
    expected_codes = {
        "missing-record": "managed_world_not_found",
        "unbound": "native_graph_binding_missing",
        "inactive": "native_graph_binding_inactive",
        "wrong-world": "managed_world_identity_mismatch",
        "provisioning": "native_graph_provisioning_pending",
    }
    assert exc_info.value.code == expected_codes[state]


def test_binding_change_during_projection_discards_native_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    managed = create_world_container(name="The Glass Orchard")
    initial = _record_with_binding(
        managed, native_world_id="eldyrwild", binding_version=1
    )
    changed = _record_with_binding(
        managed, native_world_id="new-native-world", binding_version=2
    )
    records = iter([initial, changed])
    monkeypatch.setattr(
        managed_projection,
        "get_world_container",
        lambda _world_id: next(records),
    )
    _native_projection_stub(monkeypatch)

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        managed_projection.project_managed_world_graph(_request(), root=tmp_path)

    assert exc_info.value.code == "native_graph_binding_changed"
    assert exc_info.value.status_code == 409


def test_client_cannot_select_native_identity_or_authority_fields() -> None:
    with pytest.raises(ValidationError):
        _request(nativeWorldId="client-selected")
    with pytest.raises(ValidationError):
        _request(bindingVersion=7)
    with pytest.raises(ValidationError):
        _request(admissibility="gm")

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.mark.parametrize("revision_pin", [None, "historical"])
def test_native_projection_support_uses_exact_revision(monkeypatch, revision_pin):
    from types import SimpleNamespace

    from dungeonmind.application.vnext import EntityReadService

    from apps.live_control_server.integrations.dungeonmind import native_registry_source

    binding = SimpleNamespace(native_world_id="elderwyld")
    repository = SimpleNamespace(
        get_head=lambda space: SimpleNamespace(head_revision_id="current")
    )
    context = object()
    support = object()

    def read_context(repo, space, revision, campaign, *, scope_mode, parsed_cache):
        assert parsed_cache is not None
        assert repo is repository
        assert (space, revision, campaign, scope_mode) == (
            "elderwyld", revision_pin or "current", None, "world"
        )
        return context, None, None, None

    def list_support(self, read_context):
        assert read_context is context
        return support

    monkeypatch.setattr(managed_projection.config, "world_graph_authority_database_url", lambda: "postgresql://unused-fixture/not-opened")
    monkeypatch.setattr(native_registry_source, "read_repository", lambda: repository)
    monkeypatch.setattr(native_registry_source, "read_context", read_context)
    monkeypatch.setattr(EntityReadService, "list_entities_with_support", list_support)
    assert managed_projection._read_native_projection_support(binding, revision_pin) == (
        "current", context, None, support
    )


def test_source_views_do_not_copy_producer_session_to_unmatched_revision(monkeypatch):
    from types import SimpleNamespace as Record

    from apps.live_control_server.integrations.dungeonmind import vnext_world_projection as adapter

    artifact = Record(
        source_artifact_id="artifact", source_classification="buddy:recap",
        domain_metadata=[], uri=None,
    )
    source_reader = Record(get_provenance_snapshot=lambda **_: Record(
        get_artifact=lambda _: artifact,
    ))
    support = Record(evidence=[
        Record(evidence_ref_id=key, source_artifact_id="artifact", locator=None,
               source_span_ref_id=None)
        for key in ("matched", "older")
    ])
    selected = Record(source_artifact=artifact, evidence_ref_ids=("matched",))

    def select(access, *, evidence_ref_ids):
        assert evidence_ref_ids == ["matched", "older"]
        return Record(sources=(selected,))

    monkeypatch.setattr(adapter, "list_admitted_native_text_sources", select)
    monkeypatch.setattr(adapter, "source_display_metadata", lambda items, world: [
        {"origin_matches_current_metadata": True, "campaign_id": "campaign",
         "session_id": "session-9"}
    ])
    evidence, artifacts = adapter.project_source_views(
        Record(source_reader=source_reader), support, access=object(), managed_world_id="world"
    )
    assert artifacts[0].session_id == "session-9"
    assert [(row.campaign_id, row.session_id) for row in evidence] == [
        ("campaign", "session-9"), (None, None)
    ]


@pytest.mark.parametrize("message, status", [
    ("native source context revision is missing", 404),
    ("native source context domain pin mismatch", None),
])
def test_native_projection_distinguishes_missing_pin_from_integrity_failure(
    monkeypatch, message, status
):
    from types import SimpleNamespace

    from dungeonmind.application.vnext.errors import KnowledgeReadContextIntegrityError

    from apps.live_control_server.integrations.dungeonmind import native_registry_source

    repository = SimpleNamespace(
        get_head=lambda space: SimpleNamespace(head_revision_id="current")
    )
    failure = KnowledgeReadContextIntegrityError(message)

    def read_context(*args, **kwargs):
        raise failure

    monkeypatch.setattr(managed_projection.config, "world_graph_authority_database_url", lambda: "postgresql://unused-fixture/not-opened")
    monkeypatch.setattr(native_registry_source, "read_repository", lambda: repository)
    monkeypatch.setattr(native_registry_source, "read_context", read_context)
    binding = SimpleNamespace(native_world_id="elderwyld")
    if status is None:
        with pytest.raises(KnowledgeReadContextIntegrityError) as caught:
            managed_projection._read_native_projection_support(binding, "missing")
        assert caught.value is failure
    else:
        with pytest.raises(managed_projection.WorldGraphProjectionServiceError) as caught:
            managed_projection._read_native_projection_support(binding, "missing")
        assert caught.value.status_code == status
        assert caught.value.code == "native_graph_revision_unavailable"


@pytest.mark.parametrize("kind,code,status", [
    ("unavailable", "native_graph_authority_unavailable", 503),
    ("integrity", "native_graph_integrity_failure", 500),
])
def test_native_managed_projection_failures_remain_typed_without_empty_success(tmp_path, monkeypatch, kind, code, status):
    from dungeonmind.domain.errors import PersistenceIntegrityError, PersistenceUnavailableError
    from apps.live_control_server.services import world_graph_projection as classic
    managed = create_world_container(name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(managed_projection, "get_world_container", lambda _: bound)
    exception = (PersistenceUnavailableError if kind == "unavailable" else PersistenceIntegrityError)("private infrastructure detail")
    def fail_read():
        raise exception
    seen, outputs = _native_projection_stub(monkeypatch, on_read=fail_read)
    monkeypatch.setattr(classic, "project_world_graph", lambda *_args, **_kwargs: pytest.fail("native failure fell back to classic"))
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        managed_projection.project_managed_world_graph(_request(), root=tmp_path)
    assert error.value.code == code and error.value.status_code == status
    assert error.value.__cause__ is exception
    assert "private infrastructure detail" not in str(error.value)
    assert seen == [("eldyrwild", None)] and outputs == []


def test_expected_managed_binding_change_refuses_before_native_io(tmp_path, monkeypatch):
    managed = create_world_container(name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(managed_projection, "get_world_container", lambda _: bound)
    monkeypatch.setattr(managed_projection, "_read_native_projection_support",
                        lambda *_args: pytest.fail("changed expected binding reached native IO"))
    expected = managed_projection.VerifiedManagedWorldBinding(managed.world_id, "old-native", 1, bound.source_root_relpath)
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        managed_projection.project_managed_world_graph(_request(), root=tmp_path, expected_binding=expected)
    assert error.value.code == "native_graph_binding_changed" and error.value.status_code == 409


@pytest.mark.parametrize("module_name", [
    "apps.live_control_server.integrations.dungeonmind.native_projection_presentation",
    "apps.live_control_server.integrations.dungeonmind.vnext_world_projection",
    "apps.live_control_server.services.managed_world_graph_projection",
])
def test_cold_native_projection_import_does_not_load_classic_runtime(module_name):
    blocked = (
        "apps.live_control_server.integrations.dungeonmind.world_graph_reads",
        "dungeonmind.application.graph_snapshot",
        "dungeonmind.application.world_graph_projection",
        "dungeonmind.application.world_graph_retrieval",
        "dungeonmind.application.review_publication",
        "dungeonmind.application.contribution_review",
        "dungeonmind.application.contribution_review_v2",
        "dungeonmind.application.contribution_review_v3",
        "dungeonmind.application.contribution_review_v4",
        "dungeonmind.application.existing_world_adoption",
        "dungeonmind.application.reviewed_world_initialization",
        "dungeonmind.infrastructure.postgres.graph",
        "dungeonmind.infrastructure.postgres.review_publication",
        "dungeonmind.infrastructure.postgres.existing_world_adoption",
    )
    script = textwrap.dedent(f"""
        import importlib
        import importlib.abc
        import sys
        import psycopg
        blocked = {blocked!r}
        class RejectClassic(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == name or fullname.startswith(name + '.') for name in blocked):
                    raise AssertionError('Native projection loaded classic runtime: ' + fullname)
        sys.meta_path.insert(0, RejectClassic())
        def forbidden(*args, **kwargs):
            raise AssertionError('Projection import constructed or connected a database')
        psycopg.connect = forbidden
        from dungeonmind.infrastructure.postgres import PostgresDatabase
        PostgresDatabase.__init__ = forbidden
        importlib.import_module({module_name!r})
        assert not any(name == prefix or name.startswith(prefix + '.')
                       for name in sys.modules for prefix in blocked)
    """)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-c", script], env=env,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_expansion_ranking_preserves_complete_ordered_dtos_and_input():
    from apps.live_control_server.integrations.dungeonmind.native_projection_presentation import (
        _expansion_views,
    )
    from graph_memory.projection.world_projection import WorldGraphProjectionAdjacencyCandidate

    def candidate(identity, label, *, focused=False, evidence=()):
        return WorldGraphProjectionAdjacencyCandidate(
            edge_id="edge:" + identity, node_id=identity, label=label,
            kind="npc", predicate="knows", direction="outgoing",
            anchored_to_focus_session=focused, evidence_ref_ids=list(evidence),
            source_domains=["session"], session_ids=["session:exact"],
            edge_label="Exact edge", campaign_scope="campaign:exact",
            related_summary="Exact summary", source_excerpt="Exact cited bytes.\r\n",
            source_excerpt_is_full_paragraph=True,
        )

    rows = [
        candidate("sharp-s", "ß"),
        candidate("tie-first", "Alpha"),
        candidate("degree", "Zulu"),
        candidate("double-s", "ss"),
        candidate("tie-second", "alpha"),
        candidate("evidence", "Zulu", evidence=("ev:one", "ev:one")),
        candidate("focus", "Zulu", focused=True),
        candidate("evidence-degree", "Zulu", evidence=("ev:one", "ev:two")),
    ]
    before = [row.model_dump(mode="json", by_alias=True) for row in rows]
    degree = {"degree": 100, "evidence-degree": 3}
    result = _expansion_views(rows, degree_by_node=degree)
    expected_order = [6, 7, 5, 2, 1, 4, 3, 0]
    expected_reasons = ["current session", "more evidence", "more evidence",
                        "connected hub", "connected thread", "connected thread",
                        "connected thread", "connected thread"]
    expected = [dict(before[index], rank=rank, rankReason=reason)
                for rank, (index, reason) in enumerate(zip(expected_order, expected_reasons), 1)]
    assert [row.model_dump(mode="json", by_alias=True) for row in result] == expected
    actual_bytes = b"[" + b",".join(row.model_dump_json(by_alias=True).encode() for row in result) + b"]"
    assert actual_bytes == json.dumps(expected, ensure_ascii=False, separators=(",", ":")).encode()
    assert [row.model_dump(mode="json", by_alias=True) for row in rows] == before
    assert degree == {"degree": 100, "evidence-degree": 3}
    assert _expansion_views([], degree_by_node={}) == []


def test_historical_expansion_alias_is_same_presentation_function():
    from apps.live_control_server.integrations.dungeonmind import (
        native_projection_presentation as presentation,
        world_graph_reads as historical,
    )
    assert historical._expansion_views is presentation._expansion_views


@pytest.mark.parametrize("scope_mode,campaign", [("world", None), ("campaign", "campaign-a")])
def test_internal_scoped_projection_reads_exact_native_context(monkeypatch, tmp_path, scope_mode, campaign):
    """Real orchestration/read helper; Core context and presentation are explicit seams."""
    from dungeonmind.application.vnext import EntityReadService
    from apps.live_control_server.integrations.dungeonmind import native_registry_source
    from apps.live_control_server.integrations.dungeonmind import vnext_world_projection as adapter
    from apps.live_control_server.services import world_graph_projection as classic

    managed = create_world_container(name="The Glass Orchard")
    record = _record_with_binding(managed, native_world_id="distinct-native-space", binding_version=7)
    monkeypatch.setattr(managed_projection, "get_world_container", lambda _: record)
    context, access = object(), object()
    support = SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id="rev:old")))
    calls = []
    repository = SimpleNamespace(get_head=lambda space: (
        calls.append(("head", space)) or SimpleNamespace(head_revision_id="rev:advanced")))

    def read_context(repo, space, revision, selected_campaign, *, scope_mode, parsed_cache):
        assert repo is repository and parsed_cache is not None
        calls.append(("context", space, revision, scope_mode, selected_campaign))
        return context, access, None, None

    def list_entities(self, actual):
        assert actual is context
        return support

    def project(actual, selected, snapshot, *, access: object, managed_world_id):
        assert actual is context and selected is support
        assert managed_world_id == managed.world_id
        assert access is source_access
        projection = _native_projection(snapshot.world_id)
        projection.snapshot = snapshot
        return projection

    source_access = access
    monkeypatch.setattr(managed_projection.config, "world_graph_authority_database_url", lambda: "postgresql://fixture/not-opened")
    monkeypatch.setattr(native_registry_source, "read_repository", lambda: repository)
    monkeypatch.setattr(native_registry_source, "read_context", read_context)
    monkeypatch.setattr(EntityReadService, "list_entities_with_support", list_entities)
    monkeypatch.setattr(adapter, "project_native_world", project)
    monkeypatch.setattr(classic, "project_world_graph", lambda *_a, **_k: pytest.fail("classic projection fallback"))
    result = managed_projection.project_managed_scoped_graph(
        managed_world_id=managed.world_id, revision_pin="rev:old", scope_mode=scope_mode,
        campaign_id=campaign, query_text="keeper", root=tmp_path,
    )
    assert calls == [("head", "distinct-native-space"),
                     ("context", "distinct-native-space", "rev:old", scope_mode, campaign)]
    assert (result.managed_world_id, result.native_world_id, result.binding_version) == (
        managed.world_id, "distinct-native-space", 7)
    snapshot = result.projection.snapshot
    assert (snapshot.world_id, snapshot.revision_id, snapshot.head_revision_id, snapshot.is_head) == (
        "distinct-native-space", "rev:old", "rev:advanced", False)
    assert (snapshot.scope_mode, snapshot.campaign_id) == (scope_mode, campaign or "")
    assert snapshot.focus.kind == "none" and snapshot.admissibility == "gm"
    assert result.projection.query_context.query_text == "keeper"


@pytest.mark.parametrize("changes", [
    {"managed_world_id": ""}, {"managed_world_id": " managed"},
    {"revision_pin": ""}, {"revision_pin": " rev:old"},
    {"scope_mode": "other"}, {"scope_mode": "campaign", "campaign_id": None},
    {"scope_mode": "campaign", "campaign_id": ""},
    {"scope_mode": "campaign", "campaign_id": " campaign"},
    {"scope_mode": "world", "campaign_id": "campaign"},
])
def test_internal_scoped_projection_rejects_invalid_scope_before_io(monkeypatch, changes):
    monkeypatch.setattr(managed_projection, "resolve_managed_world_binding",
                        lambda *_a, **_k: pytest.fail("invalid scope reached binding IO"))
    args = dict(managed_world_id="managed", revision_pin="rev:old", scope_mode="world", campaign_id=None)
    args.update(changes)
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        managed_projection.project_managed_scoped_graph(**args)
    assert (error.value.code, error.value.status_code) == ("native_graph_scope_invalid", 422)


@pytest.mark.parametrize("scope_mode,campaign", [("world", None), ("campaign", "campaign-a")])
@pytest.mark.parametrize("phase", ["before", "during"])
def test_internal_scoped_projection_preserves_binding_fences(monkeypatch, tmp_path, scope_mode, campaign, phase):
    from apps.live_control_server.integrations.dungeonmind import vnext_world_projection as adapter

    initial = managed_projection.VerifiedManagedWorldBinding("managed", "native", 1, "source")
    changed = managed_projection.VerifiedManagedWorldBinding("managed", "native", 2, "source")
    resolutions = iter([changed] if phase == "before" else [initial, changed])
    monkeypatch.setattr(managed_projection, "resolve_managed_world_binding", lambda *_a, **_k: next(resolutions))
    reads = []

    def read(*args, **kwargs):
        reads.append((args, kwargs))
        return "rev:head", None, None, SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id="rev:old")))

    def project(_context, _support, snapshot, **_kwargs):
        projection = _native_projection(snapshot.world_id)
        projection.snapshot = snapshot
        return projection

    monkeypatch.setattr(managed_projection, "_read_native_projection_support", read)
    monkeypatch.setattr(adapter, "project_native_world", project)
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        managed_projection.project_managed_scoped_graph(
            managed_world_id="managed", revision_pin="rev:old", scope_mode=scope_mode,
            campaign_id=campaign, expected_binding=initial, root=tmp_path,
        )
    assert (error.value.code, error.value.status_code) == ("native_graph_binding_changed", 409)
    assert len(reads) == (0 if phase == "before" else 1)


def test_internal_scoped_projection_rejects_substituted_revision(monkeypatch, tmp_path):
    binding = managed_projection.VerifiedManagedWorldBinding("managed", "native", 1, "source")
    monkeypatch.setattr(managed_projection, "resolve_managed_world_binding", lambda *_a, **_k: binding)
    monkeypatch.setattr(managed_projection, "_read_native_projection_support", lambda *_a, **_k: (
        "rev:head", None, None, SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id="rev:other")))))
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        managed_projection.project_managed_scoped_graph(
            managed_world_id="managed", revision_pin="rev:old", scope_mode="campaign", campaign_id="campaign", root=tmp_path)
    assert (error.value.code, error.value.status_code) == ("native_graph_revision_mismatch", 500)
