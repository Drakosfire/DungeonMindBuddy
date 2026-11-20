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


def _original_extract_packet(tmp_path):
    from tests.test_candidate_graph_admission_contract import _prepare, _candidate
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import bind_identity_ledger_to_package
    from apps.live_control_server.services.extract_promote import _seal_publication_target
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
    context = _context()
    result = _prepare(tmp_path, _candidate(), mutation_context=context)
    packet = bind_identity_ledger_to_package(result.review_package, context)
    packet = _seal_publication_target(packet, VerifiedManagedWorldBinding(
        managed_world_id="managed-history", native_world_id="eldyrwild", binding_version=1,
        source_root_relpath="retained-unused",
    ))
    selected = [item["assertion_id"] for item in packet["effect"]["accepted_proposals"]]
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
