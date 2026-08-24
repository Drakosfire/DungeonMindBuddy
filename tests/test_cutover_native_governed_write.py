"""CUTOVER D.1: native governed write context (no Buddy hydration)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from graph_memory.kernel.identity_models import IdentityCandidate
from graph_memory.world_graph_mutation_context import (
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


def test_static_write_module_has_no_buddy_graph_runtime_imports():
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

    import graph_memory.kernel as kernel
    from graph_memory.candidate_graph_preview import (
        CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        CANDIDATE_GRAPH_PREVIEW_VERSION,
    )
    from graph_memory.extract_promote_ops import prepare_extract_promote

    def _explode(*_args, **_kwargs):
        raise AssertionError("Buddy graph open must not run on DND prepare")

    monkeypatch.setattr(kernel, "open_current_world_graph", _explode)
    monkeypatch.setattr(kernel, "load_world_graph_revision", _explode)
    monkeypatch.setattr(
        "graph_memory.world_graph_mutation_context.mutation_context_from_world_root",
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
    from graph_memory.world_graph_mutation_context import mutation_context_from_world_root

    with pytest.raises(Exception):
        mutation_context_from_world_root(tmp_path / "missing-graph", "eldyrwild")
