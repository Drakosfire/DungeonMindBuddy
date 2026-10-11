"""Internal mixed reconciliation with source-proven binding-only endpoints."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence, Any

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringObjectRefPayload,
)
from apps.live_control_server.services.recap_source_subject_proof import (
    _source_run,
    prove_source_subject,
    SourceSubjectProofError,
)
from graph_memory.extract_promote_proposal import (
    compute_proposal_digest,
    validate_source_proven_endpoint_basis,
)

KEY = "source_proven_endpoint_basis"
SCHEMA = "dmb_source_proven_endpoint_basis_v1"


class SourceProvenEndpointError(ValueError):
    code = "source_proven_endpoint_invalid"


@dataclass(frozen=True)
class HistoricalEndpointReference:
    raw_node_id: str
    subject: GraphObjectAuthoringObjectRefPayload
    publication_revision_id: str
    package_bytes: bytes


def _require(condition, message):
    if not condition:
        raise SourceProvenEndpointError(message)


def _prove_refs(*, bundle, world_id, parent_id, resolved, preview, references):
    rows = []
    packages = {}
    for reference in references:
        old = json.loads(reference.package_bytes)
        _require(
            old["effect"]["world_id"] == world_id
            and compute_proposal_digest(old["effect"]) == old["proposal_digest"],
            "historical package World/seal drift",
        )
        basis = {
            key: value
            for key, value in old["effect"]["identity_basis"].items()
            if key != "nodes"
        }
        try:
            proven = prove_source_subject(
                bundle=bundle,
                world_id=world_id,
                parent_id=parent_id,
                historical_id=reference.publication_revision_id,
                basis=basis,
                resolved=resolved,
                preview=preview,
                ref=reference.subject,
            )
        except SourceSubjectProofError as exc:
            raise SourceProvenEndpointError(str(exc)) from exc
        package_sha = hashlib.sha256(reference.package_bytes).hexdigest()
        _require(
            package_sha == proven.common["historical_prepared_package_sha256"],
            "historical package bytes differ from finalized review",
        )
        _require(
            proven.row["raw_node_id"] == reference.raw_node_id,
            "historical raw-to-qualified endpoint map drift",
        )
        rows.append(
            {**proven.row, "history": proven.common, "package_sha256": package_sha}
        )
        packages[package_sha] = reference.package_bytes.decode("utf-8")
    _require(
        len({row["raw_node_id"] for row in rows}) == len(rows)
        and len({row["subject_id"] for row in rows}) == len(rows)
        and rows,
        "duplicate or empty endpoint references",
    )
    return {
        "schema": SCHEMA,
        "purpose": "endpoint_binding_only",
        "world_id": world_id,
        "parent_revision_id": parent_id,
        "source_run_id": resolved.run_id,
        "source_artifact_id": resolved.source_artifact_id,
        "source_revision_id": resolved.source_revision_id,
        "subjects": rows,
        "historical_packages": packages,
    }


class _ExistingCatalogOnly:
    """Reuse the existing source proof port without granting registration."""

    def __init__(self, bundle, resolved):
        from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
            DungeonMindWorldGraphSourceAdmissionAdapter,
        )

        self.adapter = DungeonMindWorldGraphSourceAdmissionAdapter(
            sources=bundle.sources
        )
        self.resolved = resolved

    def prove_or_admit(self, request):
        return self.adapter.prove(
            world_id=request.world_id,
            source_artifact_id=self.resolved.source_artifact_id,
            source_revision_id=self.resolved.source_revision_id,
            source_revision_token=self.resolved.source_revision_id,
        )


def prepare_source_proven_endpoints(
    *,
    bundle: Any,
    managed_world_id: str,
    source_run_id: str,
    endpoints: Sequence[HistoricalEndpointReference],
    new_node_ids: Sequence[str],
    repo_root: Path,
    include_edges: bool = True,
):
    from apps.live_control_server.services.managed_world_graph_projection import (
        resolve_managed_world_binding,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        prepare_candidate_graph_admission,
        canonical_candidate_digest,
    )
    from apps.live_control_server.services.extract_promote import (
        _seal_publication_target,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_writes as writes,
    )

    root = artifact_data_root(repo_root)
    run, resolved, raw, preview = _source_run(root, source_run_id)
    target = resolve_managed_world_binding(managed_world_id)
    _require(
        resolved.world_id in (None, target.native_world_id),
        "source declares a foreign World",
    )
    context = writes.load_production_mutation_context(target.native_world_id)
    parent_id = context.head_revision_id
    _require(
        bundle.world_graph.get_head(target.native_world_id).head_revision_id
        == parent_id,
        "caller repository differs from native authority",
    )
    proof = _prove_refs(
        bundle=bundle,
        world_id=target.native_world_id,
        parent_id=parent_id,
        resolved=resolved,
        preview=preview,
        references=endpoints,
    )
    raw_ids = {node.node_id for node in preview.nodes}
    endpoint_ids = {row["raw_node_id"] for row in proof["subjects"]}
    _require(
        set(new_node_ids) <= raw_ids and not set(new_node_ids) & endpoint_ids,
        "new-node selection overlaps proven endpoints or invents a raw ID",
    )
    digest = canonical_candidate_digest(raw)
    trusted = {
        row["raw_node_id"]: {
            **row,
            "world_id": target.native_world_id,
            "parent_revision_id": parent_id,
            "source_artifact_id": resolved.source_artifact_id,
            "source_revision_id": resolved.source_revision_id,
            "candidate_digest": digest,
        }
        for row in proof["subjects"]
    }
    result = prepare_candidate_graph_admission(
        candidate_graph=raw,
        source_uri=resolved.sealed_source_uri,
        source_revision_id=resolved.source_revision_id,
        world_id=target.native_world_id,
        source_artifact_id=resolved.source_artifact_id,
        source_artifact=get_source_artifact(root, resolved.source_artifact_id),
        campaign_scope=resolved.campaign_id,
        extraction_profile=resolved.extraction_profile,
        prepared_by="service:buddy:source-endpoint-prepare",
        candidate_graph_path=str(resolved.candidate_graph_path),
        repo_root=root,
        mutation_context=context,
        node_ids=sorted(set(new_node_ids) | endpoint_ids),
        include_edges=include_edges,
        source_proven_endpoints=trusted,
        source_admission=_ExistingCatalogOnly(bundle, resolved),
    )
    package = result.review_package
    package["effect"][KEY] = proof
    package["proposal_digest"] = compute_proposal_digest(package["effect"])
    package = writes.bind_identity_ledger_to_package(package, context)
    package = _seal_publication_target(package, target)
    _require(
        bundle.world_graph.get_head(target.native_world_id).head_revision_id
        == parent_id,
        "parent changed during endpoint preparation",
    )
    validate_source_proven_endpoint_basis(package["effect"])
    reprove_source_proven_endpoints(bundle=bundle, package=package, repo_root=root)
    _require(
        canonical_candidate_digest(raw) == digest
        and hashlib.sha256(resolved.candidate_graph_path.read_bytes()).hexdigest()
        == run.components["candidate_graph"].sha256,
        "FULL candidate bytes changed",
    )
    return {
        "review_package": package,
        "review_items": result.review_items,
        "review_summary": result.review_summary,
        "confirmable": result.confirmable,
    }


def reprove_source_proven_endpoints(*, bundle, package, repo_root):
    effect = package.get("effect", {})
    proof = effect.get(KEY)
    if proof is None:
        return
    validate_source_proven_endpoint_basis(effect)
    _, resolved, raw, preview = _source_run(
        artifact_data_root(repo_root), proof["source_run_id"]
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
    )

    _require(
        canonical_candidate_digest(raw)
        == effect["candidate_admission"]["candidate_digest"],
        "FULL candidate digest drift",
    )
    references = []
    for row in proof["subjects"]:
        text = proof["historical_packages"][row["package_sha256"]]
        references.append(
            HistoricalEndpointReference(
                raw_node_id=row["raw_node_id"],
                subject=GraphObjectAuthoringObjectRefPayload(
                    refKind="existing_graph_node",
                    nodeId=row["subject_id"],
                    label="exact historical subject",
                    kind=row["subject_kind"],
                ),
                publication_revision_id=row["history"][
                    "historical_publication_revision_id"
                ],
                package_bytes=text.encode("utf-8"),
            )
        )
    actual = _prove_refs(
        bundle=bundle,
        world_id=proof["world_id"],
        parent_id=proof["parent_revision_id"],
        resolved=resolved,
        preview=preview,
        references=references,
    )
    _require(actual == proof, "historical/current endpoint proof drift")
