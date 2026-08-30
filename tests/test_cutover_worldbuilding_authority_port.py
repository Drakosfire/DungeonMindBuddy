"""CUTOVER D.2B: worldbuilding authority-port contract (no PostgreSQL)."""



from __future__ import annotations



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

from src.graph_memory.extraction.worldbuilding_extraction_profile import (

    DEFAULT_SEMANTIC_STATE,

)

from tests._cutover_d3a_blocker_safe_fixtures import _candidate_graph_payload



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





def _install_worldbuilding_repo(monkeypatch, tmp_path: Path) -> Path:



    import apps.live_control_server.config as live_config

    import apps.live_control_server.services.extract_promote as promote_svc

    import apps.live_control_server.services.promotable_ingest_run as promotable_mod

    from apps.live_control_server.services.graph_ingest_run_registry import (

        GRAPH_INGEST_RUNS_ENV,

    )



    repo = tmp_path / "repo"

    repo.mkdir()

    absent = tmp_path / "buddy-world-graph-absent"

    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)

    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(absent))

    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")

    monkeypatch.setattr(live_config, "repo_root", lambda: repo)

    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)

    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)

    monkeypatch.setattr(live_config, "world_graph_root", lambda: absent)

    return repo





def test_prepare_succeeds_with_buddy_graph_physically_absent(tmp_path, monkeypatch):

    from apps.live_control_server.models.extract_promote import (

        WorldbuildingWritePlanPrepareRequest,

    )

    from apps.live_control_server.services.worldbuilding_graph_publication import (

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

    run_id, _source = _write_bld08_reviewable_run(repo)

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

    run_id, _source = _write_bld08_reviewable_run(repo)

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



    fake.identity[DEFAULT_WORLD_ID] = {

        "identity_redirects": {"obj_session22_vial": "npc:occupied-after-prepare"},

        "decisions": [],

        "alias_owners": {},

    }

    with pytest.raises(Exception) as live_exc:

        prepare_worldbuilding(request)

    assert getattr(live_exc.value, "code", "") == "new_node_id_conflict"



    receipt = confirm_worldbuilding(

        WorldbuildingWritePlanConfirmRequest(plan=plan)

    )

    assert receipt.outcome == "committed"

    assert receipt.parent_revision_id == parent

    assert receipt.committed_revision_id != parent

    assert fake.heads[DEFAULT_WORLD_ID] == receipt.committed_revision_id

    assert fake.publish_calls == 1





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

    run_id, _source = _write_bld08_reviewable_run(repo)

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



    real_context = FakeWorldGraphAuthority.mutation_context



    def _bad_sealed(self, world_id, revision_id, *, sealed_identity_snapshot=None):

        if sealed_identity_snapshot is not None:

            raise WorldGraphAuthorityError(

                "bad snapshot",

                code="inexpressible",

            )

        return real_context(

            self,

            world_id,

            revision_id,

            sealed_identity_snapshot=sealed_identity_snapshot,

        )



    monkeypatch.setattr(FakeWorldGraphAuthority, "mutation_context", _bad_sealed)

    with pytest.raises(Exception) as exc:

        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))

    assert getattr(exc.value, "code", "") == "dungeonmind_inexpressible"





def test_v1_confirm_requires_reprepare(tmp_path, monkeypatch):

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

    run_id, _source = _write_bld08_reviewable_run(repo)

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

    assert getattr(exc.value, "code", "") == "legacy_plan_reprepare_required"





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

    run_id, _source = _write_bld08_reviewable_run(repo)

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

    first = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))

    assert first.outcome == "committed"

    retry = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))

    assert retry.outcome == "already_applied"

    assert retry.committed_revision_id == first.committed_revision_id

    assert fake.publish_calls == 1





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

    run_id, _source = _write_bld08_reviewable_run(repo)

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

    assert getattr(exc.value, "code", "") == "stale_parent_revision"

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

        _load_typed_worldbuilding_preview_for_run,

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

    run_id, _source = _write_bld08_reviewable_run(repo)

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

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(resolved)

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

            update={"prepare_binding": honest.prepare_binding}

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

    run_id, _source = _write_bld08_reviewable_run(repo)

    plan = prepare_worldbuilding(

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

            },

        ],

        "alias_owners": {},

    }

    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))

    assert receipt.outcome == "committed"

    assert fake.publish_calls == 1





def test_recomputed_plan_after_i1_cannot_reuse_prepare_binding(tmp_path, monkeypatch):

    from apps.live_control_server.models.extract_promote import (

        WorldbuildingWritePlanConfirmRequest,

        WorldbuildingWritePlanPrepareRequest,

    )

    from apps.live_control_server.services.extract_promote import (

        _load_typed_worldbuilding_preview_for_run,

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

    run_id, _source = _write_bld08_reviewable_run(repo)

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

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(resolved)

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

        update={"prepare_binding": prepared.prepare_binding}

    )

    assert attack_plan.plan_id != prepared.plan_id

    with pytest.raises(Exception) as exc:

        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=attack_plan))

    assert getattr(exc.value, "code", "") == "identity_snapshot_inexpressible"

    assert fake.publish_calls == 0





def test_bind_existing_native_verify_proves_attribute_and_alias(tmp_path, monkeypatch):

    import json



    from apps.live_control_server.models.extract_promote import (

        WorldbuildingWritePlanConfirmRequest,

        WorldbuildingWritePlanPrepareRequest,

    )

    from apps.live_control_server.services.graph_run_registry import (

        extraction_runs_path,

        get_extraction_run,

    )

    from apps.live_control_server.services.promotable_ingest_run import (

        _resolve_extraction_component_path,

    )

    from apps.live_control_server.services.worldbuilding_graph_publication import (

        confirm_worldbuilding,

        prepare_worldbuilding,

    )

    from src.live_play.live_store import load_json, write_json

    from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run



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

    run_id, _source = _write_bld08_reviewable_run(repo)

    run = get_extraction_run(repo, run_id)

    candidate_path = _resolve_extraction_component_path(

        repo,

        run.components["candidate_graph"].uri,

        label="candidate_graph",

    )

    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    candidate["nodes"][0]["aliases"] = ["Witness Alias"]

    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")

    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()

    registry_path = extraction_runs_path(repo)

    registry = load_json(registry_path)

    for record in registry["records"]:

        if record["run_id"] == run_id:

            record["components"]["candidate_graph"]["sha256"] = digest

            break

    write_json(registry_path, registry)



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

    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))

    assert receipt.outcome == "committed"

    child = fake.read_revision(DEFAULT_WORLD_ID, receipt.committed_revision_id)

    bound = child.objects[target.object_id]

    attribute_assertions = [

        item

        for item in plan.effect.accepted_proposals

        if item.assertion_kind == "attribute"

    ]

    assert attribute_assertions

    published = next(iter(fake.publications.values()))

    expected_evidence = [

        *attribute_assertions[0].evidence_ref_ids,

        f"evidence:{published.reviewed_contribution_id}:{target.object_id}",

    ]

    assert any(item in child.evidence_refs for item in expected_evidence if item)

    assert "Witness Alias" in bound.aliases

    assert "mystery_puddles" in child.objects
