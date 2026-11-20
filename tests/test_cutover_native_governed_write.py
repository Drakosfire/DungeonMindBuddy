"""CUTOVER D.1: native governed write context (no Buddy hydration)."""


from __future__ import annotations


import ast
from pathlib import Path
from types import SimpleNamespace


import pytest


from apps.live_control_server.models.world_graph_identity_models import IdentityCandidate
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    endpoint_available,
    resolve_identity_against_context,
    wire_kind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WRITES_PATH = (
    REPO_ROOT
    / "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py"
)
FORBIDDEN_IMPORT_PREFIXES = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
)


def _context(*objects: MutationObject) -> WorldGraphMutationContext:
    alias_owners: dict[str, tuple[str, ...]] = {}
    by_id = {obj.object_id: obj for obj in objects}
    for obj in objects:
        for alias in obj.aliases:
            prior = alias_owners.get(alias, ())
            if obj.object_id not in prior:
                alias_owners[alias] = (*prior, obj.object_id)
    return WorldGraphMutationContext(
        world_id="eldyrwild",
        revision_id="rev:public-dnd-parent",
        head_revision_id="rev:public-dnd-parent",
        objects=by_id,
        alias_owners=alias_owners,
    )


def test_legacy_package_only_replays_exact_terminal_publication(monkeypatch, tmp_path):
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes

    package = {
        "proposal_id": "proposal:legacy",
        "proposal_digest": "a" * 64,
        "effect": {
            "world_id": "eldyrwild", "parent_revision_id": "rev:parent",
            "contribution_meta": {"source_kind": "source_extraction"},
        },
    }
    operation_id = writes._derive_confirm_operation_id(
        world_id="eldyrwild", package=package, assertion_ids=None,
    )
    receipt = SimpleNamespace(
        world_id="eldyrwild", operation_id=operation_id,
        expected_parent_revision_id="rev:parent",
        published_revision_id="rev:child", reviewed_contribution_id="contribution:old",
    )
    present = True
    def lookup(_world, _operation):
        assert _world == "eldyrwild" and _operation == operation_id
        return receipt if present else None
    bundle = SimpleNamespace(finalized_review_publications=SimpleNamespace(get=lookup))
    monkeypatch.setattr(writes, "_direct_services", lambda *_: SimpleNamespace(bundle=bundle, binding=None))
    monkeypatch.setattr(writes, "_receipt_ids_from_reviewed_contribution", lambda **_: (["assertion:old"], ["object:old"]))
    request = SimpleNamespace(review_package=package)
    def confirm():
        return writes.confirm_extract_promote_via_dungeonmind(
            request, database_url="memory://synthetic", confirming_principal="gm@test",
            assertion_ids=None, repo_root=tmp_path,
        )

    assert confirm()["outcome"] == "already_applied"
    receipt.expected_parent_revision_id = "rev:wrong"
    with pytest.raises(writes.WorldGraphWriteError, match="does not match"):
        confirm()
    receipt.expected_parent_revision_id = "rev:parent"
    present = False
    with pytest.raises(writes.WorldGraphWriteError, match="source-local identity basis"):
        confirm()


def test_static_write_module_has_no_direct_buddy_graph_runtime_imports():
    """Direct import scan only. Transitive reach into adoption/extract_promote_ops
    (which import kernel/UnionSupergraph) is recorded D.2/D.3 cleanup, not a D.1
    runtime construction of those types.
    """
    tree = ast.parse(WRITES_PATH.read_text())
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


def test_wire_kind_strips_dungeonmind_vocabulary_prefix():
    assert wire_kind("dnd5e:npc") == "npc"
    assert wire_kind("pc") == "pc"
    assert wire_kind(None) == ""


def test_identity_resolves_existing_object():
    context = _context(
        MutationObject(
            object_id="node:caelynn",
            label="Caelynn",
            kind="pc",
            aliases=("Caelynn Vexalia",),
        )
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:caelynn",
            label="Caelynn",
            object_kind="pc",
            aliases=["Caelynn"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "node:caelynn"


def test_identity_creates_new_when_no_match():
    context = _context(
        MutationObject(object_id="node:caelynn", label="Caelynn", kind="pc")
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:tinker",
            label="Cutover Tinker",
            object_kind="npc",
            aliases=["Cutover Tinker"],
            evidence_ref_ids=["span:1"],
            proposed_node_id="node:cutover-tinker",
        ),
    )
    assert resolution.outcome == "created_new"
    assert resolution.created_node_id == "node:cutover-tinker"


def test_identity_infers_pc_kind_from_existing_object():
    from graph_memory.candidate_graph_preview import (
        CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        CANDIDATE_GRAPH_PREVIEW_VERSION,
        candidate_graph_preview_from_dict,
    )
    from graph_memory.extract_identity_gate import _infer_object_kind


    context = _context(
        MutationObject(object_id="node:caelynn", label="Caelynn", kind="pc")
    )
    preview = candidate_graph_preview_from_dict(
        {
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
            "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
            "preview_id": "preview:kind",
            "session_id": "session-26",
            "campaign_id": "longmont-c2",
            "source_artifact_ids": ["artifact:recap:x"],
            "status": "preview",
            "nodes": [
                {
                    "node_id": "extract:caelynn",
                    "label": "Caelynn",
                    "node_type": "character",
                    "description": "Caelynn.",
                    "importance": "low",
                    "semantic_state": {
                        "canon_state": "played_canon",
                        "lifecycle_state": "candidate",
                        "evidence_role": "source_evidence",
                        "authority_state": "system_derived",
                        "visibility_state": "gm_private",
                    },
                    "evidence_refs": [],
                    "proposed_action": "create",
                    "confidence": "medium",
                    "warnings": [],
                }
            ],
            "edges": [],
            "beats": [],
            "proposed_writes": [],
            "ignored_items": [],
            "deferred_items": [],
            "diagnostics": {
                "preview_only": True,
                "extraction_performed": False,
                "llm_used": False,
                "runtime_connected": False,
                "plan_connected": False,
                "agent_interaction_connected": False,
                "corpus_scanned": False,
                "corpus_mutated": False,
                "facts_promoted": False,
                "canon_promoted": False,
                "unresolved_evidence_refs": 0,
                "missing_evidence_objects": 0,
                "warning_count": 0,
            },
        }
    )
    assert _infer_object_kind(preview.nodes[0], context) == "pc"


def test_identity_ambiguous_same_kind_fails_closed():
    context = _context(
        MutationObject(object_id="node:a", label="Mireward Guard", kind="npc"),
        MutationObject(object_id="node:b", label="Mireward Guard", kind="npc"),
    )
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:guard",
            label="Mireward Guard",
            object_kind="npc",
            aliases=["Mireward Guard"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "ambiguous"
    assert resolution.requires_human_review is True


def test_native_producer_honors_reject_and_human_override():
    from types import SimpleNamespace


    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        mutation_context_from_revision_payload,
    )


    stored = SimpleNamespace(
        graph_payload={
            "objects": [
                {
                    "object_id": "npc_hester_b",
                    "label": "Hester Bright",
                    "kind": "npc",
                    "aliases": [{"value": "Hester Bright"}],
                    "assertion_metadata": {"canon_state": "canonical"},
                }
            ]
        },
        revision=SimpleNamespace(revision_id="rev:parent"),
    )
    reject = SimpleNamespace(
        decision_id="identity-decision:reject-noise",
        world_id="eldyrwild",
        decision_kind="reject_candidate",
        subject_object_ids=["extract:noise"],
        target_object_ids=[],
        alias=None,
        actor="gm",
        reason="Not a durable campaign identity",
        reversible=True,
        supersedes_decision_ids=[],
        status="active",
        created_at="2026-08-01T00:00:00Z",
        source_candidate_id=None,
    )
    override = SimpleNamespace(
        decision_id="identity-decision:hester-override",
        world_id="eldyrwild",
        decision_kind="human_override",
        subject_object_ids=["extract:hester"],
        target_object_ids=["npc_hester_b"],
        alias=None,
        actor="gm",
        reason="Hester Bright is the intended match",
        reversible=True,
        supersedes_decision_ids=[],
        status="active",
        created_at="2026-08-01T00:00:01Z",
        source_candidate_id=None,
    )
    context = mutation_context_from_revision_payload(
        stored,
        world_id="eldyrwild",
        head_revision_id="rev:parent",
        dungeonmind_decisions=[reject, override],
    )
    rejected = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:noise",
            label="Background Extra",
            object_kind="npc",
            aliases=["Extra"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert rejected.outcome == "rejected"
    assert rejected.decision_id == reject.decision_id
    overridden = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:hester",
            label="Hester",
            object_kind="npc",
            aliases=["Hester"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert overridden.outcome == "human_override"
    assert overridden.target_node_id == "npc_hester_b"
    assert overridden.decision_id == override.decision_id


def test_native_producer_follows_merge_redirect_not_merged_away_source():
    from types import SimpleNamespace


    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        mutation_context_from_revision_payload,
    )


    stored = SimpleNamespace(
        graph_payload={
            "objects": [
                {
                    "object_id": "item_enormous_boulder",
                    "label": "Enormous boulder",
                    "kind": "item",
                    "aliases": [{"value": "Enormous boulder"}],
                    "assertion_metadata": {"canon_state": "canonical"},
                },
                {
                    "object_id": "item_foot_of_statue",
                    "label": "Foot of a once enormous statue",
                    "kind": "item",
                    "aliases": [{"value": "Foot of a once enormous statue"}],
                    "assertion_metadata": {"canon_state": "canonical"},
                },
            ]
        },
        revision=SimpleNamespace(revision_id="rev:parent"),
    )
    merge = SimpleNamespace(
        decision_id="identity-decision:boulder-merge",
        world_id="eldyrwild",
        decision_kind="merge",
        subject_object_ids=["item_enormous_boulder", "item_foot_of_statue"],
        target_object_ids=["item_foot_of_statue"],
        alias=None,
        actor="gm",
        reason="boulder resolves into the statue foot",
        reversible=True,
        supersedes_decision_ids=[],
        status="active",
        created_at="2026-08-12T16:32:34Z",
        source_candidate_id=None,
    )
    context = mutation_context_from_revision_payload(
        stored,
        world_id="eldyrwild",
        head_revision_id="rev:parent",
        dungeonmind_decisions=[merge],
    )
    assert context.identity_redirects["item_enormous_boulder"] == "item_foot_of_statue"
    assert context.objects["item_enormous_boulder"].memory_state == "merged_away"
    resolution = resolve_identity_against_context(
        context,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:boulder",
            label="Enormous boulder",
            object_kind="item",
            aliases=["Enormous boulder"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert resolution.outcome == "resolved_existing"
    assert resolution.target_node_id == "item_foot_of_statue"


def test_sealed_identity_ledger_ignores_later_live_decisions():
    from types import SimpleNamespace


    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        bind_identity_ledger_to_package,
        mutation_context_from_revision_payload,
        _hydrate_identity_decisions,
        _require_sealed_identity_ledger,
    )


    stored = SimpleNamespace(
        graph_payload={
            "objects": [
                {
                    "object_id": "npc_hester_b",
                    "label": "Hester Bright",
                    "kind": "npc",
                    "aliases": [{"value": "Hester Bright"}],
                    "assertion_metadata": {"canon_state": "canonical"},
                }
            ]
        },
        revision=SimpleNamespace(revision_id="rev:parent"),
    )
    override = SimpleNamespace(
        decision_id="identity-decision:hester-override",
        world_id="eldyrwild",
        decision_kind="human_override",
        subject_object_ids=["extract:hester"],
        target_object_ids=["npc_hester_b"],
        alias=None,
        actor="gm",
        reason="intended match",
        reversible=True,
        supersedes_decision_ids=[],
        status="active",
        created_at="2026-08-01T00:00:01Z",
        source_candidate_id=None,
    )
    prepared = mutation_context_from_revision_payload(
        stored,
        world_id="eldyrwild",
        head_revision_id="rev:parent",
        dungeonmind_decisions=[override],
    )
    package = bind_identity_ledger_to_package(
        {"effect": {"world_id": "eldyrwild", "parent_revision_id": "rev:parent"}},
        prepared,
    )
    later_reject = SimpleNamespace(
        decision_id="identity-decision:hester-reject",
        world_id="eldyrwild",
        decision_kind="reject_candidate",
        subject_object_ids=["extract:hester"],
        target_object_ids=[],
        alias=None,
        actor="gm",
        reason="later reject without graph advance",
        reversible=True,
        supersedes_decision_ids=[],
        status="active",
        created_at="2026-08-24T00:00:00Z",
        source_candidate_id=None,
    )
    live = mutation_context_from_revision_payload(
        stored,
        world_id="eldyrwild",
        head_revision_id="rev:parent",
        dungeonmind_decisions=[override, later_reject],
    )
    live_resolution = resolve_identity_against_context(
        live,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:hester",
            label="Hester",
            object_kind="npc",
            aliases=["Hester"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert live_resolution.outcome == "rejected"


    sealed = mutation_context_from_revision_payload(
        stored,
        world_id="eldyrwild",
        head_revision_id="rev:parent",
        dungeonmind_decisions=_hydrate_identity_decisions(
            package["effect"]["identity_ledger"]["decisions"]
        ),
    )
    sealed_resolution = resolve_identity_against_context(
        sealed,
        IdentityCandidate(
            world_id="eldyrwild",
            candidate_id="extract:hester",
            label="Hester",
            object_kind="npc",
            aliases=["Hester"],
            evidence_ref_ids=["span:1"],
        ),
    )
    assert sealed_resolution.outcome == "human_override"
    assert sealed_resolution.target_node_id == "npc_hester_b"
    assert package["proposal_digest"]
    with pytest.raises(Exception) as excinfo:
        _require_sealed_identity_ledger({"effect": {"parent_revision_id": "rev:parent"}})
    assert getattr(excinfo.value, "code", "") == "governed_write_legacy_package"


def test_receipt_ids_from_dungeonmind_reviewed_contribution():
    from types import SimpleNamespace


    from dungeonmind.contracts.contribution import AcceptanceState


    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _affected_ids_from_contribution,
    )


    reviewed = SimpleNamespace(
        assertions=[
            SimpleNamespace(
                assertion_id="assert:keep",
                assertion_kind="node",
                subject_object_id="node:keep",
                object_object_id=None,
                acceptance_state=AcceptanceState.ACCEPTED,
            ),
            SimpleNamespace(
                assertion_id="assert:drop",
                assertion_kind="node",
                subject_object_id="node:drop",
                object_object_id=None,
                acceptance_state=AcceptanceState.REJECTED,
            ),
            SimpleNamespace(
                assertion_id="assert:edge",
                assertion_kind="edge",
                subject_object_id="node:keep",
                object_object_id="node:other",
                acceptance_state=AcceptanceState.ACCEPTED,
            ),
        ]
    )
    reviewed.partition_assertions = lambda state: [
        item
        for item in reviewed.assertions
        if item.acceptance_state is state
    ]
    accepted, affected = _affected_ids_from_contribution(reviewed)
    assert accepted == ["assert:keep", "assert:edge"]
    assert affected == ["node:keep", "node:other"]


def test_endpoint_existence_parent_same_batch_and_missing():
    context = _context(
        MutationObject(object_id="node:existing", label="Keep", kind="location")
    )
    selected = {"node:new"}
    assert endpoint_available(
        "node:existing", selected_node_subjects=selected, context=context
    )
    assert endpoint_available(
        "node:new", selected_node_subjects=selected, context=context
    )
    assert not endpoint_available(
        "node:absent", selected_node_subjects=selected, context=context
    )


def test_dnd_prepare_does_not_open_buddy_graph(monkeypatch, tmp_path):
    import hashlib


    from graph_memory.candidate_graph_preview import (
        CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        CANDIDATE_GRAPH_PREVIEW_VERSION,
    )
    from graph_memory.extract_promote_ops import prepare_extract_promote


    def _explode(*_args, **_kwargs):
        raise AssertionError("Buddy graph open must not run on DND prepare")


    monkeypatch.setattr(
        "apps.live_control_server.models.world_graph_mutation_context.mutation_context_from_world_root",
        _explode,
    )


    source = tmp_path / "recap.md"
    source.write_text("Cutover Tinker arrives in Mireward.\n")
    digest = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    context = _context()
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:d1-prepare",
        "session_id": "session-26",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:d1-prepare"],
        "status": "preview",
        "nodes": [
            {
                "node_id": "node:cutover-tinker",
                "label": "Cutover Tinker",
                "node_type": "character",
                "description": "Cutover Tinker.",
                "importance": "low",
                "semantic_state": {
                    "canon_state": "played_canon",
                    "lifecycle_state": "candidate",
                    "evidence_role": "source_evidence",
                    "authority_state": "system_derived",
                    "visibility_state": "gm_private",
                },
                "evidence_refs": [
                    {
                        "source_ref_id": "ref:node:cutover-tinker",
                        "source_artifact_id": "artifact:recap:longmont-c2:d1-prepare",
                        "source_anchor_id": "anchor:node:cutover-tinker",
                        "label": "span",
                        "evidence_role": "source_evidence",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": "session-26:recap:paragraph:001",
                        "anchor_quotes": ["Cutover Tinker"],
                    }
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    result = prepare_extract_promote(
        candidate_graph=graph,
        source_uri=str(source),
        source_body=source.read_bytes(),
        source_revision_id=digest,
        prepared_by="gm@prepare",
        world_id="eldyrwild",
        source_artifact_id="artifact:recap:longmont-c2:d1-prepare",
        campaign_scope="longmont-c2",
        repo_root=tmp_path,
        disclose_source_digest=False,
        mutation_context=context,
    )
    assert result.parent_revision_id == "rev:public-dnd-parent"
    assert result.review_package["effect"]["parent_revision_id"] == (
        "rev:public-dnd-parent"
    )
    assert not result.review_package.get("world_root")


def test_dnd_prepare_fails_closed_when_authority_unavailable(monkeypatch):
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WorldGraphWriteError,
        load_production_mutation_context,
    )


    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY", "dungeonmind")
    monkeypatch.delenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", raising=False)
    with pytest.raises(WorldGraphWriteError) as excinfo:
        load_production_mutation_context("eldyrwild", database_url="")
    assert excinfo.value.code == "authority_unavailable"


def test_file_mode_producer_still_opens_explicit_root(tmp_path):
    """buddy_files compatibility is retained and must not be a DND fallback."""
    from apps.live_control_server.models.world_graph_mutation_context import mutation_context_from_world_root


    with pytest.raises(Exception):
        mutation_context_from_world_root(tmp_path / "missing-graph", "eldyrwild")


def _original_extract_packet(tmp_path, *, mode="basic"):
    from tests.test_candidate_graph_admission_contract import _prepare, _candidate
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import bind_identity_ledger_to_package
    from apps.live_control_server.services.extract_promote import _seal_publication_target
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
    context = _context()
    candidate = _candidate(unsupported=mode == "edges")
    if mode == "edges":
        candidate["nodes"][1]["node_type"] = "location"
        candidate["edges"][0]["relationship_type"] = "located_in"
    if mode == "aliases":
        candidate["nodes"][0]["aliases"] = ["Exact historical alias"]
    if mode in {"multispan", "rejected_multispan"}:
        from tests.test_candidate_graph_admission_contract import _evidence
        candidate["nodes"][0]["evidence_refs"] = [_evidence("ordered-z"), _evidence("ordered-a")]
    result = _prepare(tmp_path, candidate, mutation_context=context)
    packet = result.review_package
    if mode in {"rejected", "rejected_multispan", "v3"}:
        from graph_memory.extract_promote_proposal import seal_promote_proposal, compute_proposal_digest
        from apps.live_control_server.models.world_graph_contribution_models import GraphContributionAssertion
        effect = packet["effect"]
        accepted = [GraphContributionAssertion.model_validate(item) for item in effect["accepted_proposals"]]
        rejected_assertions = []
        if mode != "v3":
            rejected = next(item for item in accepted if item.assertion_kind == "attribute")
            accepted = [item for item in accepted if item.assertion_id != rejected.assertion_id]
            rejected_assertions = [rejected.model_copy(update={"acceptance_state": "rejected", "predicate": None})]
        # The original public sealer supports explicit rejected assertions. This
        # is a historical producer contract recipe, not a mounted UI assertion.
        packet = seal_promote_proposal(**{key: effect[key] for key in (
            "world_id", "parent_revision_id", "source_revision_id", "source_artifact_id", "verified_source_uri",
            "candidate_preview_id", "candidate_schema", "candidate_version", "contribution_meta", "node_id_map",
            "identity_outcome_snapshot", "identity_basis")},
            accepted_proposals=accepted, rejected_assertions=rejected_assertions,
            unresolved_mentions=[], prepared_by=result.review_package["prepared_by"], proposal_version=3 if mode == "v3" else 2)
        for key in ("candidate_admission", "source_admission"):
            packet["effect"][key] = effect[key]
        packet["proposal_digest"] = compute_proposal_digest(packet["effect"])
    packet = bind_identity_ledger_to_package(packet, context)
    packet = _seal_publication_target(packet, VerifiedManagedWorldBinding(
        managed_world_id="managed-history", native_world_id="eldyrwild", binding_version=1,
        source_root_relpath="retained-unused",
    ))
    selected = [item["assertion_id"] for item in packet["effect"]["accepted_proposals"]]
    if mode == "partial":
        selected = selected[:1]
    if mode == "campaign":
        from apps.live_control_server.services.extract_promote import _seal_recap_ingest_context
        parent, _ = _original_extract_parent_and_source(packet)
        packet = _seal_recap_ingest_context(packet, {
            "schema": "dm_world_campaign_ingest_context_v1", "managed_world_id": "managed-history",
            "native_world_id": parent.revision.world_id, "binding_version": 1,
            "campaign_id": "longmont-c2", "head_revision_id": parent.revision.revision_id,
            "graph_schema": parent.revision.graph_schema, "graph_payload_sha256": parent.revision.graph_payload_sha256,
        })
    return packet, selected


def test_original_extract_integrity_uses_real_producer_without_authority_reads(tmp_path, monkeypatch):
    import copy
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet
    from apps.live_control_server.services import extract_promote
    packet, selected = _original_extract_packet(tmp_path)
    original = copy.deepcopy(packet)
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda *_: pytest.fail("pure integrity read current World"))
    value = validate_original_packet(packet, selected)
    assert value["selection"] == tuple(selected)
    assert value["verified"]["proposal_digest"] == packet["proposal_digest"]
    assert value["operation_id"].startswith("reviewop:")
    assert packet == original


@pytest.mark.parametrize("selection", [[], ["missing"], ["a", "a"]])
def test_original_extract_empty_foreign_or_duplicate_selection_refuses(tmp_path, selection):
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, _ = _original_extract_packet(tmp_path)
    with pytest.raises(ExtractPromoteError) as error:
        validate_original_packet(packet, selection)
    assert error.value.code == "plan_verification_failed"


@pytest.mark.parametrize("reseal", [False, True])
def test_original_extract_digest_is_integrity_not_original_authentication(tmp_path, reseal):
    import copy
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path)
    original = validate_original_packet(packet, selected)
    changed = copy.deepcopy(packet)
    changed["effect"]["accepted_proposals"][0]["label"] = "A changed retained meaning"
    for part in changed["effect"].get("contributions", []):
        part["accepted_proposals"][0]["label"] = "A changed retained meaning"
    if not reseal:
        with pytest.raises(ExtractPromoteError) as error:
            validate_original_packet(changed, selected)
        assert error.value.code == "plan_verification_failed"
    else:
        changed["proposal_digest"] = compute_proposal_digest(changed["effect"])
        result = validate_original_packet(changed, selected)
        assert result["operation_id"] != original["operation_id"]
        # Successful unkeyed integrity checking is deliberately NOT historical
        # authentication. The terminal+complete-review proof is still required.


def test_original_extract_malformed_ledger_is_typed_and_does_not_mutate_packet(tmp_path):
    import copy
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path)
    packet["effect"]["identity_ledger"] = {"decisions": ["invalid"]}
    packet["proposal_digest"] = compute_proposal_digest(packet["effect"])
    before = copy.deepcopy(packet)
    with pytest.raises(ExtractPromoteError) as error:
        validate_original_packet(packet, selected)
    assert error.value.code == "plan_verification_failed"
    assert packet == before


def _original_extract_parent_and_source(packet):
    from datetime import UTC, datetime
    from dungeonmind.domain.canonical import canonical_sha256
    from tests._cutover_direct_dungeonmind_read_helpers import _payload
    effect = packet["effect"]
    payload = _payload()
    payload.update(world_id=effect["world_id"], objects=[], relationships=[], evidence_refs=[])
    parent = SimpleNamespace(revision=SimpleNamespace(world_id=effect["world_id"],
        revision_id=effect["parent_revision_id"], status="published", graph_schema="dm_union_graph_v6",
        graph_payload_sha256=canonical_sha256(payload), created_at=datetime(2025, 1, 1, tzinfo=UTC)),
        graph_payload=payload)
    admitted = effect["source_admission"]
    source = SimpleNamespace(source_revision_id=admitted["source_revision_id"],
        source_artifact_id=admitted["source_artifact_id"], content_sha256=admitted["content_sha256"],
        locator=effect["verified_source_uri"])
    return parent, source


def test_original_extract_candidate_matches_actual_pure_producer(tmp_path, monkeypatch):
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
    from apps.live_control_server.models.extract_promote import SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, reconstruct_original_candidate
    packet, selected = _original_extract_packet(tmp_path)
    carried = validate_original_packet(packet, selected)
    parent, source = _original_extract_parent_and_source(packet)
    context = writes._mutation_context_from_sealed_package(stored=parent, package=packet,
        world_id=parent.revision.world_id, head_revision_id=parent.revision.revision_id)
    _, original = resolve_merged_contribution_from_package(review_package=packet,
        confirming_principal=SERVER_CONFIRMING_PRINCIPAL, world_id_hint=parent.revision.world_id,
        expected_parent_revision_id=parent.revision.revision_id, assertion_ids=selected, mutation_context=context)
    pair = (source.source_artifact_id, packet["effect"]["source_revision_id"])
    expected, states = writes._build_v2_candidate(original, context=context,
        pair_to_dm={pair: source.source_revision_id}, produced_at=parent.revision.created_at,
        sources=SimpleNamespace(get_artifact=lambda _: SimpleNamespace(source_domain="session_recap"), get_revision=lambda _: source))
    def forbidden(*args, **kwargs):
        pytest.fail("pure reconstruction opened current authority")
    monkeypatch.setattr(writes, "_direct_services", forbidden)
    monkeypatch.setattr(writes, "_build_pair_to_dm", forbidden)
    monkeypatch.setattr(writes, "load_production_mutation_context", forbidden)
    raw, actual, actual_states, _ = reconstruct_original_candidate(carried, parent=parent, source_revision=source)
    assert raw.model_dump(mode="json") == original.model_dump(mode="json")
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
    assert actual_states == states
    assert all(ref.uri == source.locator and ref.can_open_source for item in actual.assertions for ref in item.evidence_refs)


def _original_extract_review_history(packet, selected, *, mutation=None):
    """Independent original producer staging and actual Core contract builder.

    The terminal envelope is unit-only; real SQL publication remains required.
    """
    from datetime import timedelta
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
    from dungeonmind.application.contribution_review_v2 import _build_review_state
    from dungeonmind.contracts.contribution_review import ContributionAssertionVerdict, ContributionPlanRef, derive_confirmation_id
    from dungeonmind.contracts.contribution_review_v2 import (
        CommitConfirmationReceiptV2, ContributionReviewIntentV2, ContributionReviewSubmissionV2,
        FINALIZE_REVIEW_V2_TOOL, contribution_v2_payload_sha256, derive_review_intent_sha256_v2,
    )
    from dungeonmind.domain.canonical import canonical_sha256, canonical_json
    from apps.live_control_server.models.extract_promote import SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    parent, source = _original_extract_parent_and_source(packet)
    context = writes._mutation_context_from_sealed_package(stored=parent, package=packet,
        world_id=parent.revision.world_id, head_revision_id=parent.revision.revision_id)
    _, original = resolve_merged_contribution_from_package(review_package=packet,
        confirming_principal=SERVER_CONFIRMING_PRINCIPAL, world_id_hint=parent.revision.world_id,
        expected_parent_revision_id=parent.revision.revision_id, assertion_ids=selected, mutation_context=context)
    at = parent.revision.created_at + timedelta(seconds=1) if mutation == "timestamp" else parent.revision.created_at
    candidate, states = writes._build_v2_candidate(original, context=context,
        pair_to_dm={(source.source_artifact_id, packet["effect"]["source_revision_id"]): source.source_revision_id},
        produced_at=at, sources=SimpleNamespace(get_artifact=lambda _: SimpleNamespace(source_domain="session_recap"), get_revision=lambda _: source))
    if mutation == "semantic_binding":
        candidate = candidate.model_copy(update={"diagnostics": {
            **dict(candidate.diagnostics or {}), "reviewed_extract_confirmation": {"historical_generation": "separate"},
        }})
    if mutation == "evidence_order":
        import json
        items = list(candidate.assertions)
        value = json.loads(items[0].value)
        value["evidence"] = list(reversed(value["evidence"]))
        items[0] = items[0].model_copy(update={"value": canonical_json(value), "evidence_refs": list(reversed(items[0].evidence_refs))})
        candidate = candidate.model_copy(update={"assertions": items})
    if mutation == "value":
        import json
        items = list(candidate.assertions)
        value = json.loads(items[0].value)
        value["summary"] = "A coherent alternate meaning"
        items[0] = items[0].model_copy(update={"value": canonical_json(value)})
        candidate = candidate.model_copy(update={"assertions": items})
    proposals, verdicts = writes._build_identity_dispositions(candidate, states)
    plan_ref = ContributionPlanRef(source_plan_schema=packet["schema"], source_plan_id=packet["proposal_id"],
        source_plan_sha256=packet["proposal_digest"], source_input_sha256=canonical_sha256(packet["effect"]),
        preview_content_sha256=canonical_sha256({"changed": True} if mutation == "preview" else packet.get("preview") or {}),
        candidate_contribution_sha256=contribution_v2_payload_sha256(candidate),
        expected_parent_revision_id=parent.revision.revision_id, base_graph_schema=parent.revision.graph_schema,
        base_graph_payload_sha256=parent.revision.graph_payload_sha256, semantic_profile=parent.graph_payload["semantic_profile"])
    actor = "other-service" if mutation == "actor" else SERVER_CONFIRMING_PRINCIPAL
    fields = dict(operation_id=writes._derive_confirm_operation_id(world_id=parent.revision.world_id,
        package=packet, assertion_ids=tuple(selected)), world_id=parent.revision.world_id,
        campaign_id=original.campaign_scope or None, plan_ref=plan_ref, candidate_contribution=candidate,
        identity_proposals=proposals, identity_verdicts=verdicts,
        assertion_verdicts=[ContributionAssertionVerdict(assertion_id=item.assertion_id, acceptance_state=states[item.assertion_id])
                            for item in sorted(candidate.assertions, key=lambda item: item.assertion_id)],
        reviewer_id=actor, reviewed_at=at)
    intent_type = ContributionReviewIntentV2
    if mutation == "guarded_v2":
        from dungeonmind.contracts.contribution_review_v2 import GuardedContributionReviewIntentV2, ReviewedIdentityPublicationPreconditionsV1
        intent_type = GuardedContributionReviewIntentV2
        fields["reviewed_identity_preconditions"] = ReviewedIdentityPublicationPreconditionsV1(
            world_id=parent.revision.world_id, campaign_id=original.campaign_scope,
            expected_parent_revision_id=parent.revision.revision_id, decision_id="decision:historical-guard",
            decision_sha256="12" * 32, target_object_id=candidate.assertions[0].subject_object_id,
            target_object_sha256="34" * 32, existence_evidence_sha256="56" * 32,
            sources=[dict(source_artifact_id=source.source_artifact_id, source_revision_id=source.source_revision_id,
                source_artifact_sha256="78" * 32, source_revision_sha256="90" * 32)],
        )
    digest = derive_review_intent_sha256_v2(**fields)
    intent = intent_type(**fields, review_intent_sha256=digest)
    confirmation = CommitConfirmationReceiptV2(confirmation_id=derive_confirmation_id(
        operation_id=fields["operation_id"], review_intent_sha256=digest, actor=actor, confirmed_at=at),
        operation_id=fields["operation_id"], review_intent_sha256=digest, actor=actor, tool_name=FINALIZE_REVIEW_V2_TOOL,
        effect="commit", world_id=parent.revision.world_id, campaign_id=original.campaign_scope or None,
        expected_parent_revision_id=parent.revision.revision_id, confirmed_at=at)
    state = _build_review_state(ContributionReviewSubmissionV2(intent=intent, confirmation=confirmation))
    state = type(state).model_validate(state.model_dump(mode="json"))
    history = SimpleNamespace(review=state, publication=SimpleNamespace(
        expected_parent_revision_id=parent.revision.revision_id, parent_graph_payload_sha256=parent.revision.graph_payload_sha256,
        graph_schema=parent.revision.graph_schema, published_at=at), revision=SimpleNamespace(created_at=at))
    return original, history, parent, source


def test_original_extract_complete_review_matches_original_producer(tmp_path):
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, verify_original_review
    packet, selected = _original_extract_packet(tmp_path)
    original, history, parent, source = _original_extract_review_history(packet, selected)
    actual = verify_original_review(validate_original_packet(packet, selected), history=history, parent=parent, source_revision=source)
    assert actual.model_dump(mode="json") == original.model_dump(mode="json")


@pytest.mark.parametrize("mutation", ["value", "actor", "preview", "timestamp"])
def test_original_extract_coherent_alternate_review_fails_correspondence(tmp_path, mutation):
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, verify_original_review
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path)
    _, history, parent, source = _original_extract_review_history(packet, selected, mutation=mutation)
    with pytest.raises(ExtractPromoteError) as error:
        verify_original_review(validate_original_packet(packet, selected), history=history, parent=parent, source_revision=source)
    assert error.value.code == "publication_integrity_failure"


def _original_extract_reader_case(tmp_path, monkeypatch):
    from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    packet, selected = _original_extract_packet(tmp_path)
    original, history, parent, source = _original_extract_review_history(packet, selected)
    history.publication.published_revision_id = "revision:original-history-child"
    calls = []
    def binding(_):
        calls.append("binding")
        return ("managed-history", parent.revision.world_id, 1)
    def read(world, operation, *, reader):
        assert world == parent.revision.world_id
        assert operation == recovery.validate_original_packet(packet, selected)["operation_id"]
        calls.append("terminal")
        return history
    def get_parent(world, revision):
        assert (world, revision) == (parent.revision.world_id, parent.revision.revision_id)
        calls.append("parent")
        return parent
    def get_source(revision):
        assert revision == source.source_revision_id
        calls.append("source_revision")
        return source
    monkeypatch.setattr(recovery, "authorize_current_target", binding)
    monkeypatch.setattr(recovery, "_bare_readers", lambda: (object(), SimpleNamespace(get_revision=get_parent), SimpleNamespace(get_revision=get_source)))
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", read)
    return ExtractPromoteConfirmRequest(review_package=packet, assertion_ids=selected), original, history, calls


def test_original_extract_reader_shapes_original_receipt_without_mutable_preflight(tmp_path, monkeypatch):
    import copy
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.services import extract_promote as service
    request, original, history, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    packet = copy.deepcopy(request.review_package)
    def forbidden(*args, **kwargs):
        pytest.fail("historical extract entered mutable preflight or writer")
    for name in ("load_bound_extraction_run", "_assert_current_recap_ingest_context", "_assert_recap_semantics_at_confirm", "world_graph_root"):
        monkeypatch.setattr(service, name, forbidden)
    for name in ("_direct_services", "_build_pair_to_dm", "confirm_extract_promote_via_dungeonmind"):
        monkeypatch.setattr(writes, name, forbidden)
    receipt = recovery.recover_original_confirmation(request)
    assert calls == ["binding", "terminal", "parent", "source_revision", "binding"]
    assert receipt.outcome == "already_applied"
    assert receipt.committed_revision_id == history.publication.published_revision_id
    assert (receipt.proposal_id, receipt.proposal_digest) == (packet["proposal_id"], packet["proposal_digest"])
    assert receipt.selected_assertion_ids == request.assertion_ids
    assert receipt.accepted_assertion_ids == [a.assertion_id for a in original.accepted_assertions]
    assert receipt.head_advanced is False and receipt.audit_status == "ok"
    assert request.review_package == packet


@pytest.mark.parametrize("mode,code,status", [("absent", "publication_receipt_unavailable", 409),
    ("corrupt", "publication_integrity_failure", 409), ("unavailable", "authority_unavailable", 503)])
def test_original_extract_reader_terminal_failures_never_fallback(tmp_path, monkeypatch, mode, code, status):
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from dungeonmind.domain.errors import PersistenceIntegrityError, PersistenceUnavailableError
    request, _, _, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    def read(*args, **kwargs):
        if mode == "absent":
            return None
        raise (PersistenceIntegrityError("fixture corrupt") if mode == "corrupt" else PersistenceUnavailableError("fixture unavailable"))
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", read)
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(request)
    assert (error.value.code, error.value.status_code) == (code, status)
    assert calls == ["binding"]


@pytest.mark.parametrize("mode", ["edges", "aliases", "multispan", "partial", "campaign", "rejected", "rejected_multispan", "v3"])
def test_original_extract_complete_recipe_correspondence(tmp_path, mode):
    import json
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, verify_original_review
    packet, selected = _original_extract_packet(tmp_path, mode=mode)
    original, history, parent, source = _original_extract_review_history(packet, selected)
    actual = verify_original_review(validate_original_packet(packet, selected), history=history, parent=parent, source_revision=source)
    assert actual.model_dump(mode="json") == original.model_dump(mode="json")
    reviewed = history.review.reviewed_contribution
    if mode == "edges":
        edge = next(item for item in reviewed.assertions if item.assertion_kind == "edge")
        assert edge.subject_object_id == packet["effect"]["node_id_map"]["candidate:brin"]
        assert edge.object_object_id == packet["effect"]["node_id_map"]["candidate:medical-wing"]
    elif mode == "aliases":
        node = next(item for item in reviewed.assertions if item.assertion_kind == "node")
        assert "Exact historical alias" in json.loads(node.value)["aliases"]
    elif mode == "multispan":
        assert all([ref.locator for ref in item.evidence_refs] == ["session-9:recap:paragraph:ordered-z", "session-9:recap:paragraph:ordered-a"]
                   for item in reviewed.assertions)
    elif mode == "partial":
        assert {item.assertion_id for item in reviewed.assertions} == set(selected)
    elif mode in {"rejected", "rejected_multispan"}:
        from dungeonmind.contracts.contribution import AcceptanceState
        assert original.rejected_assertions
        rejected_ids = {item.assertion_id for item in original.rejected_assertions}
        assert {item.assertion_id for item in reviewed.assertions if item.acceptance_state is AcceptanceState.REJECTED} == rejected_ids
        if mode == "rejected_multispan":
            assert all([ref.locator for ref in item.evidence_refs] == ["session-9:recap:paragraph:ordered-z", "session-9:recap:paragraph:ordered-a"]
                       for item in reviewed.assertions)



@pytest.mark.parametrize("field", ["source_revision_id", "source_artifact_id", "content_sha256", "locator"])
def test_original_extract_changed_immutable_source_metadata_fails_closed(tmp_path, field):
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, verify_original_review
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path)
    _, history, parent, source = _original_extract_review_history(packet, selected)
    setattr(source, field, "changed-original-metadata")
    with pytest.raises(ExtractPromoteError) as error:
        verify_original_review(validate_original_packet(packet, selected), history=history, parent=parent, source_revision=source)
    assert error.value.code == "publication_integrity_failure"


@pytest.mark.parametrize("generation", ["v3", "guarded_v3"])
def test_original_extract_reader_refuses_real_other_generations_before_companions(tmp_path, monkeypatch, generation):
    from tests.test_graph_object_authoring_commit import _coherent_historical_manual_review
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    request, _, _, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    history = _coherent_historical_manual_review(generation=generation)["history"]
    assert type(history.review).model_validate(history.review.model_dump(mode="json")) == history.review
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", lambda *a, **k: history)
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(request)
    assert error.value.code == "publication_history_unsupported"
    assert calls == ["binding"]


def test_original_extract_semantic_correction_is_explicitly_deferred_before_authority(tmp_path, monkeypatch):
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path)
    packet["effect"]["recap_semantic_disposition"] = {"version": 1, "run_id": "retained-corrected-run"}
    packet["proposal_digest"] = compute_proposal_digest(packet["effect"])
    monkeypatch.setattr(recovery, "_bare_readers", lambda: pytest.fail("unsupported correction read private history"))
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(ExtractPromoteConfirmRequest(review_package=packet, assertion_ids=selected))
    assert error.value.code == "publication_history_unsupported"


def test_original_extract_late_binding_transfer_never_discloses_receipt(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    request, _, _, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    count = 0
    def binding(_):
        nonlocal count
        count += 1
        if count == 2:
            raise ExtractPromoteError("binding changed", code="publication_target_changed", status_code=409)
        return ("managed-history", "eldyrwild", 1)
    monkeypatch.setattr(recovery, "authorize_current_target", binding)
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(request)
    assert error.value.code == "publication_target_changed"
    assert count == 2 and calls == ["terminal", "parent", "source_revision"]


@pytest.fixture
def extract_history_core_dsn(monkeypatch, record_property):
    from tests.test_database_graph_object_authoring_evidence import historical_manual_core_dsn
    yield from historical_manual_core_dsn.__wrapped__(monkeypatch, record_property)


@pytest.mark.parametrize("terminal", ["present", "absent", "corrupt_child", "non_recap", "wrong_valid_source"])
def test_real_postgres_original_extract_recovery_after_descendant_and_withdrawal(
    tmp_path, monkeypatch, application_state_dsn, extract_history_core_dsn, terminal,
):
    import hashlib
    import json
    from datetime import UTC, datetime, timedelta
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.contracts.evidence import SourceStatus
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle, PostgresSourceRepository, PostgresWorldGraphRepository
    from dungeonmind.infrastructure.postgres.database import jsonb
    from dungeonmind.infrastructure.postgres.serialization import model_fingerprint
    from dungeonmind.infrastructure.postgres.review_publication import PostgresFinalizedReviewPublicationRepository
    from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest, SERVER_CONFIRMING_PRINCIPAL
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import DungeonMindWorldGraphSourceAdmissionAdapter
    from apps.live_control_server.services.candidate_graph_admission import prepare_candidate_graph_admission, confirm_candidate_graph_admission
    from apps.live_control_server.services import extract_promote as service
    from apps.live_control_server.services.world_container_registry import create_world_container
    from tests.application_state.world_catalog_fixtures import store_world
    from tests.test_candidate_graph_admission_contract import _candidate, _recap_source_artifact
    from tests._cutover_direct_dungeonmind_read_helpers import _payload
    from tests.test_database_graph_object_authoring_evidence import _database_rows_fingerprint
    from apps.live_control_server import config

    dsn = extract_history_core_dsn
    bundle = PostgresRepositoryBundle(PostgresDatabase(dsn))
    world = "world:extract-history-sql"
    stamp = datetime(2025, 1, 1, tzinfo=UTC)
    payload = _payload()
    payload.update(world_id=world, objects=[], relationships=[], evidence_refs=[])
    parent = bundle.world_graph.publish_revision(PublishRevisionCommand(world_id=world,
        parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=["fixture:extract-history-parent"], graph_schema="dm_union_graph_v6", graph_payload=payload, created_at=stamp))
    stored = bundle.world_graph.get_revision(world, parent.revision_id)
    context = writes.mutation_context_from_revision_payload(stored, world_id=world, head_revision_id=parent.revision_id)
    managed = create_world_container(name="Extract history fixture")
    store_world(managed.model_copy(update={"native_graph_binding": {
        "native_world_id": world, "binding_version": 1, "status": "active",
        "validated_at": stamp.isoformat(), "validated_head_revision_id": parent.revision_id,
    }}))
    source_path = tmp_path / "original-recap.md"
    source_path.write_text("Brin visits the Medical Wing.\n", encoding="utf-8")
    token = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
    artifact = _recap_source_artifact(source_path, token)
    artifact.world_id = world
    if terminal == "non_recap":
        artifact.source_domain = "other"
    candidate = _candidate()
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    admission = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn)
    def prepare_original():
        return prepare_candidate_graph_admission(source_body=source_path.read_bytes(), candidate_graph=candidate,
            source_uri=str(source_path), source_revision_id=token, prepared_by="fixture-local-operator", world_id=world,
            source_artifact_id=artifact.source_artifact_id, source_artifact=artifact, campaign_scope="longmont-c2",
            repo_root=tmp_path, mutation_context=context, candidate_graph_path=str(candidate_path), source_admission=admission)
    if terminal == "non_recap":
        from apps.live_control_server.models.candidate_graph_admission import CandidateAdmissionNotConfirmableError
        before = (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn))
        with pytest.raises(CandidateAdmissionNotConfirmableError, match="requires a recap source artifact"):
            prepare_original()
        assert (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn)) == before
        return  # Original admission refused: do not fabricate a historical publication.
    prepared = prepare_original()
    packet = writes.bind_identity_ledger_to_package(prepared.review_package, context)
    monkeypatch.setattr(config, "world_graph_authority_database_url", lambda: dsn)
    packet = service._seal_publication_target(packet, service._resolve_publication_target(managed.world_id))
    packet = service._seal_recap_ingest_context(packet, {"schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": managed.world_id, "native_world_id": world, "binding_version": 1,
        "campaign_id": "longmont-c2", "head_revision_id": parent.revision_id,
        "graph_schema": stored.revision.graph_schema, "graph_payload_sha256": stored.revision.graph_payload_sha256})
    selected = [item["assertion_id"] for item in packet["effect"]["accepted_proposals"]]
    request = ExtractPromoteConfirmRequest(review_package=packet, assertion_ids=selected)
    frozen = request.model_dump(mode="json")
    with monkeypatch.context() as publishing:
        publishing.setattr(writes, "_direct_services", lambda *_: SimpleNamespace(bundle=bundle, binding=SimpleNamespace(legacy_buddy_revision_id=None)))
        published = confirm_candidate_graph_admission(review_package=packet, candidate_graph=candidate, source_admission=admission,
            governed_confirm=lambda: writes.confirm_extract_promote_via_dungeonmind(request, database_url=dsn,
                confirming_principal=SERVER_CONFIRMING_PRINCIPAL, assertion_ids=tuple(selected), repo_root=tmp_path, candidate_graph=candidate))
    child_id = published["committed_revision_id"]
    child = bundle.world_graph.get_revision(world, child_id)
    descendant = bundle.world_graph.publish_revision(PublishRevisionCommand(world_id=world,
        parent_revision_id=child_id, expected_parent_revision_id=child_id, operation_ids=["fixture:extract-history-descendant"],
        graph_schema=child.revision.graph_schema, graph_payload=child.graph_payload, created_at=stamp + timedelta(days=1)))
    admitted = packet["effect"]["source_admission"]
    original_artifact = bundle.sources.get_artifact(admitted["source_artifact_id"])
    from dungeonmind.contracts.evidence import SourceDomain
    assert original_artifact.source_domain is SourceDomain.SESSION_RECAP
    withdrawn = original_artifact.model_copy(update={"status": SourceStatus.RETRACTED})
    with bundle.database.transaction() as conn:
        conn.execute("UPDATE dungeonmind.source_artifacts SET status=%s,payload=%s,record_fingerprint=%s WHERE source_artifact_id=%s",
            (withdrawn.status.value, jsonb(withdrawn.model_dump(mode="json")), model_fingerprint(withdrawn), withdrawn.source_artifact_id))
        if terminal == "absent":
            conn.execute("DELETE FROM dungeonmind.finalized_review_publications WHERE published_revision_id=%s", (child_id,))
        elif terminal == "corrupt_child":
            conn.execute("UPDATE dungeonmind.graph_revisions SET graph_payload='null'::jsonb WHERE revision_id=%s", (child_id,))
    assert bundle.sources.get_artifact(withdrawn.source_artifact_id).status is SourceStatus.RETRACTED
    assert bundle.world_graph.get_head(world).head_revision_id == descendant.revision_id != child_id
    # These are exact reproducible fixture files created above, not cleanup of
    # another lane or live source. Their absence is part of the recovery proof.
    source_path.unlink()
    candidate_path.unlink()
    assert not source_path.exists() and not candidate_path.exists()
    before = (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn))
    def forbidden(*args, **kwargs):
        pytest.fail("historical extract entered mutable preflight or publication")
    for name in ("load_bound_extraction_run", "_assert_current_recap_ingest_context", "_assert_recap_semantics_at_confirm", "world_graph_root"):
        monkeypatch.setattr(service, name, forbidden)
    for name in ("_direct_services", "_build_pair_to_dm", "confirm_extract_promote_via_dungeonmind"):
        monkeypatch.setattr(writes, name, forbidden)
    for path in ("dungeonmind.application.contribution_review_v2.finalize_contribution_review_v2",
        "dungeonmind.application.review_publication.publish_finalized_review",
        "apps.live_control_server.services.graph_run_registry.get_extraction_run",
        "apps.live_control_server.services.workspace_document_registry.get_workspace_document",
        "apps.live_control_server.services.source_artifact_registry.load_source_input_bytes"):
        monkeypatch.setattr(path, forbidden)
    if terminal == "wrong_valid_source":
        original_get = PostgresSourceRepository.get_revision
        def wrong_revision(self, revision_id):
            actual = original_get(self, revision_id)
            assert actual is not None
            changed = actual.model_copy(update={"source_revision_id": actual.source_revision_id + ":other"})
            return type(changed).model_validate(changed.model_dump(mode="json"))
        monkeypatch.setattr(PostgresSourceRepository, "get_revision", wrong_revision)
    monkeypatch.setattr(PostgresSourceRepository, "get_artifact", forbidden)
    monkeypatch.setattr(PostgresSourceRepository, "list_artifacts_for_world", forbidden)
    monkeypatch.setattr(PostgresWorldGraphRepository, "get_head", forbidden)
    monkeypatch.setattr(PostgresWorldGraphRepository, "publish_revision", forbidden)
    monkeypatch.setattr(PostgresFinalizedReviewPublicationRepository, "publish", forbidden)
    for _ in range(2):
        if terminal == "present":
            result = service.confirm(request)
            assert result.outcome == "already_applied" and result.head_advanced is False
            assert (result.world_id, result.parent_revision_id, result.committed_revision_id) == (world, parent.revision_id, child_id)
            assert (result.proposal_id, result.proposal_digest) == (packet["proposal_id"], packet["proposal_digest"])
            assert result.selected_assertion_ids == selected
            assert result.accepted_assertion_ids == published["accepted_assertion_ids"]
            assert result.affected_object_ids == published["affected_object_ids"]
            assert result.audit_status == "ok" and result.applied_assertion_count == len(result.accepted_assertion_ids)
        else:
            with pytest.raises(service.ExtractPromoteError) as error:
                service.confirm(request)
            assert error.value.code == ("publication_receipt_unavailable" if terminal == "absent" else "publication_integrity_failure")
        assert request.model_dump(mode="json") == frozen
        assert (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn)) == before



def test_original_extract_reader_explicitly_defers_independent_semantic_review(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    request, _, _, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    _, history, _, _ = _original_extract_review_history(request.review_package, request.assertion_ids, mutation="semantic_binding")
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", lambda *a, **k: history)
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(request)
    assert error.value.code == "publication_history_unsupported"
    assert calls == ["binding"]



def test_original_extract_guarded_v2_is_rejected_before_immutable_companions(tmp_path, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from dungeonmind.contracts.contribution_review_v2 import GuardedContributionReviewRecordV2
    request, _, _, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    _, history, _, _ = _original_extract_review_history(request.review_package, request.assertion_ids, mutation="guarded_v2")
    assert type(history.review.record) is GuardedContributionReviewRecordV2
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", lambda *a, **k: history)
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(request)
    assert error.value.code == "publication_history_unsupported"
    assert calls == ["binding"]



def test_original_extract_coherent_evidence_order_change_is_integrity_failure(tmp_path):
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, verify_original_review
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path, mode="multispan")
    _, history, parent, source = _original_extract_review_history(packet, selected, mutation="evidence_order")
    with pytest.raises(ExtractPromoteError) as error:
        verify_original_review(validate_original_packet(packet, selected), history=history, parent=parent, source_revision=source)
    assert error.value.code == "publication_integrity_failure"


def test_original_extract_conflicting_operation_wide_evidence_id_is_invalid(tmp_path):
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    from apps.live_control_server.integrations.dungeonmind.historical_extract_recovery import validate_original_packet, reconstruct_original_candidate
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    packet, selected = _original_extract_packet(tmp_path)
    attribute = next(item for item in packet["effect"]["accepted_proposals"] if item["assertion_kind"] == "attribute")
    attribute["value"]["evidence"][0]["source_span_ref_id"] = "span:conflicting"
    packet["proposal_digest"] = compute_proposal_digest(packet["effect"])
    parent, source = _original_extract_parent_and_source(packet)
    with pytest.raises(ExtractPromoteError) as error:
        reconstruct_original_candidate(validate_original_packet(packet, selected), parent=parent, source_revision=source)
    assert error.value.code == "plan_verification_failed"


@pytest.mark.parametrize("mode,code,status", [("missing_parent", "publication_integrity_failure", 409),
    ("malformed_parent", "publication_integrity_failure", 409), ("unavailable_parent", "authority_unavailable", 503),
    ("missing_source", "publication_integrity_failure", 409)])
def test_original_extract_immutable_companion_failures_are_typed(tmp_path, monkeypatch, mode, code, status):
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from dungeonmind.domain.errors import PersistenceUnavailableError
    request, _, _, _ = _original_extract_reader_case(tmp_path, monkeypatch)
    reader, graph, sources = recovery._bare_readers()
    def get_parent(*args):
        if mode == "missing_parent":
            return None
        if mode == "malformed_parent":
            raise ValueError("corrupt immutable companion")
        raise PersistenceUnavailableError("fixture unavailable")
    if mode == "missing_source":
        sources.get_revision = lambda _: None
    else:
        graph.get_revision = get_parent
    monkeypatch.setattr(recovery, "_bare_readers", lambda: (reader, graph, sources))
    with pytest.raises(ExtractPromoteError) as error:
        recovery.recover_original_confirmation(request)
    assert (error.value.code, error.value.status_code) == (code, status)
