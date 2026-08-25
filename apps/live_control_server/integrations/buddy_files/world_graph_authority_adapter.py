"""Named buddy_files World Graph authority adapter (CUTOVER D.2A / D.3 owner).

Unmounted when ``DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`` on the
production root. Existing Threat filesystem tests use this adapter. D.3
deletes it with the Buddy graph engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import graph_memory.kernel as kernel
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)
from graph_memory.world_supergraph.errors import WorldGraphIntegrityError

# Re-exported for Threat commit tests that patch this adapter's kernel module.

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.ports.world_graph_authority import (
    AuthorityObject,
    AuthorityRelationship,
    WorldGraphAuthorityError,
    WorldGraphExpectedChildFacts,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
    WorldGraphPublishRequest,
    WorldGraphRevisionView,
    WorldGraphVerificationResult,
)

__all__ = ["BuddyFilesWorldGraphAuthorityAdapter", "kernel", "WorldGraphIntegrityError"]


def _graph_root(world_root: Path | None) -> Path:
    return (world_root if world_root is not None else world_graph_root()).resolve()


def _dump_optional(model: Any) -> dict[str, Any] | None:
    if model is None:
        return None
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump(mode="json", by_alias=True)
    return None


def _revision_view_from_store(
    *,
    world_id: str,
    revision_id: str,
    parent_revision_id: str | None,
    store: Any,
) -> WorldGraphRevisionView:
    objects = {}
    for node_id, node in (getattr(store, "nodes", None) or {}).items():
        objects[str(node_id)] = AuthorityObject(
            object_id=str(getattr(node, "node_id", None) or node_id),
            label=str(getattr(node, "label", "") or ""),
            kind=str(getattr(node, "kind", "") or ""),
            role=str(getattr(node, "role", "") or ""),
            aliases=tuple(getattr(node, "aliases", ()) or ()),
            source_domains=tuple(getattr(node, "source_domains", ()) or ()),
            campaign_scope=None,
            summary=None,
            external_resource=_dump_optional(getattr(node, "external_resource", None)),
        )
    relationships = {}
    for edge_id, edge in (getattr(store, "edges", None) or {}).items():
        relationships[str(edge_id)] = AuthorityRelationship(
            relationship_id=str(getattr(edge, "edge_id", None) or edge_id),
            subject_object_id=str(getattr(edge, "source_node_id", "") or ""),
            target_object_id=str(getattr(edge, "target_node_id", "") or ""),
            predicate=str(getattr(edge, "predicate", "") or ""),
            direction=str(getattr(edge, "direction", "") or "outbound"),
            source_domains=tuple(getattr(edge, "source_domains", ()) or ()),
            threat_statblock_binding=_dump_optional(
                getattr(edge, "threat_statblock_binding", None)
            ),
        )
    supported: set[str] = set()
    for assertion_id, raw in (getattr(store, "assertion_support", None) or {}).items():
        if isinstance(raw, dict) and raw.get("support_state") == "supported":
            supported.add(str(assertion_id))
    active: set[str] = set()
    for entry in getattr(store, "contribution_replay_manifest", None) or []:
        if getattr(entry, "status", None) == "active":
            active.add(str(entry.contribution_id))
    digests = {
        str(key): str(value)
        for key, value in (getattr(store, "contribution_source_payload_sha256", None) or {}).items()
    }
    return WorldGraphRevisionView(
        world_id=world_id,
        revision_id=revision_id,
        parent_revision_id=parent_revision_id,
        objects=objects,
        relationships=relationships,
        supported_assertion_ids=frozenset(supported),
        contribution_source_digests=digests,
        active_contribution_ids=frozenset(active),
    )


class BuddyFilesWorldGraphAuthorityAdapter:
    """Kernel-backed adapter for buddy_files tests and unmounted tooling."""

    def __init__(
        self,
        world_root: Path | None = None,
        *,
        merge_fn: Any | None = None,
        lookup_fn: Any | None = None,
    ) -> None:
        self._world_root = _graph_root(world_root)
        self._merge_fn = merge_fn or kernel.merge_contribution_to_revision
        self._lookup_fn = lookup_fn or kernel.find_world_graph_revisions_by_operation_id

    def current_head(self, world_id: str) -> WorldGraphHead:
        try:
            head = kernel.open_world_graph_head(self._world_root, world_id)
        except kernel.WorldGraphNotFoundError as exc:
            raise WorldGraphAuthorityError(str(exc), code="revision_unavailable") from exc
        except OSError as exc:
            raise WorldGraphAuthorityError(str(exc), code="authority_unavailable") from exc
        except Exception as exc:
            raise WorldGraphAuthorityError(str(exc), code="authority_unavailable") from exc
        return WorldGraphHead(
            world_id=world_id,
            revision_id=str(getattr(head, "head_revision_id", None) or getattr(head, "revision_id")),
        )

    def read_revision(self, world_id: str, revision_id: str) -> WorldGraphRevisionView:
        try:
            store = kernel.load_world_graph_revision_with_integrity(
                self._world_root, world_id, revision_id
            )
        except kernel.WorldGraphProjectionError as exc:
            if getattr(exc, "code", "") == "projection_integrity_error":
                raise WorldGraphAuthorityError(str(exc), code="integrity_failure") from exc
            raise WorldGraphAuthorityError(str(exc), code="revision_unavailable") from exc
        except WorldGraphIntegrityError as exc:
            raise WorldGraphAuthorityError(str(exc), code="integrity_failure") from exc
        except OSError as exc:
            raise WorldGraphAuthorityError(str(exc), code="authority_unavailable") from exc
        parent_id = getattr(getattr(store, "revision", None), "parent_revision_id", None)
        if parent_id is None:
            parent_id = getattr(store, "parent_revision_id", None)
        return _revision_view_from_store(
            world_id=world_id,
            revision_id=revision_id,
            parent_revision_id=parent_id,
            store=store,
        )

    def mutation_context(
        self,
        world_id: str,
        revision_id: str,
        *,
        sealed_identity_snapshot: Mapping[str, Any] | None = None,
    ):
        from graph_memory.world_graph_mutation_context import (
            mutation_context_from_store,
            mutation_context_with_sealed_identity,
        )

        try:
            head, _revision, current = kernel.open_current_world_graph(
                self._world_root, world_id
            )
        except kernel.WorldGraphNotFoundError as exc:
            raise WorldGraphAuthorityError(str(exc), code="revision_unavailable") from exc
        except OSError as exc:
            raise WorldGraphAuthorityError(str(exc), code="authority_unavailable") from exc
        head_id = str(head.head_revision_id)
        try:
            store = (
                current
                if revision_id in {head_id, getattr(_revision, "revision_id", "")}
                else kernel.load_world_graph_revision(
                    self._world_root, world_id, revision_id
                )
            )
        except (kernel.WorldGraphNotFoundError, ValueError) as exc:
            raise WorldGraphAuthorityError(str(exc), code="revision_unavailable") from exc
        except OSError as exc:
            raise WorldGraphAuthorityError(str(exc), code="authority_unavailable") from exc
        base = mutation_context_from_store(
            store,
            world_id=world_id,
            revision_id=revision_id,
            head_revision_id=head_id,
        )
        if sealed_identity_snapshot is None:
            return base
        try:
            return mutation_context_with_sealed_identity(base, sealed_identity_snapshot)
        except ValueError as exc:
            raise WorldGraphAuthorityError(
                str(exc),
                code="inexpressible",
                details={"world_id": world_id, "revision_id": revision_id},
            ) from exc

    def publish(self, request: WorldGraphPublishRequest) -> WorldGraphPublicationReceipt:
        try:
            result = self._merge_fn(
                self._world_root,
                world_id=request.world_id,
                contribution=request.contribution,
                expected_parent_revision_id=request.expected_parent_revision_id,
            )
        except Exception as exc:
            raise WorldGraphAuthorityError(str(exc), code="publication_failed") from exc
        published = bool(getattr(result, "published", False))
        child_id = str(getattr(result, "revision_id", "") or "")
        parent_id = str(
            getattr(result, "parent_revision_id", None)
            or request.expected_parent_revision_id
        )
        contribution_ids = list(getattr(result, "contribution_ids", None) or [])
        reviewed_id = (
            contribution_ids[0] if contribution_ids else request.authority_operation_id
        )
        diagnostics = tuple(
            item
            for item in list(getattr(result, "diagnostics", None) or [])
            if isinstance(item, str)
        )
        return WorldGraphPublicationReceipt(
            world_id=str(getattr(result, "world_id", request.world_id)),
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=parent_id,
            published_revision_id=child_id,
            reviewed_contribution_id=reviewed_id,
            accepted_assertion_ids=tuple(
                getattr(result, "accepted_assertion_ids", ()) or ()
            ),
            published=published,
            outcome="published" if published else "already_applied",
            failure_code=getattr(result, "failure_code", None),
            failure_message=getattr(result, "failure_message", None),
            diagnostics=diagnostics,
            contribution_ids=tuple(contribution_ids),
        )

    def recover(
        self,
        world_id: str,
        authority_operation_id: str,
        *,
        expected_parent_revision_id: str | None = None,
        contribution: Any | None = None,
        actor: str | None = None,
        operation_namespace: str = "threat",
    ) -> WorldGraphPublicationReceipt | None:
        lookup_ids = [authority_operation_id]
        contrib_id = str(getattr(contribution, "contribution_id", "") or "")
        if (
            (operation_namespace or "threat") == "worldbuilding"
            and contrib_id
            and contrib_id not in lookup_ids
        ):
            lookup_ids.append(contrib_id)
        matches = ()
        try:
            for lookup_id in lookup_ids:
                matches = self._lookup_fn(self._world_root, world_id, lookup_id)
                if matches:
                    break
        except WorldGraphIntegrityError as exc:
            raise WorldGraphAuthorityError(str(exc), code="integrity_failure") from exc
        except OSError as exc:
            raise WorldGraphAuthorityError(str(exc), code="authority_unavailable") from exc
        if not matches:
            return None
        if len(matches) != 1:
            raise WorldGraphAuthorityError(
                "contradictory World Graph publications for one operation id",
                code="integrity_failure",
                details={
                    "world_id": world_id,
                    "authority_operation_id": authority_operation_id,
                    "match_count": len(matches),
                },
            )
        del actor
        manifest = matches[0]
        parent_id = str(getattr(manifest, "parent_revision_id", "") or "")
        if (
            expected_parent_revision_id is not None
            and parent_id != expected_parent_revision_id
        ):
            raise WorldGraphAuthorityError(
                "recovered publication parent does not match the durable request",
                code="integrity_failure",
                details={
                    "world_id": world_id,
                    "authority_operation_id": authority_operation_id,
                    "stored_parent_revision_id": parent_id,
                    "requested_parent_revision_id": expected_parent_revision_id,
                },
            )
        if contribution is not None and (operation_namespace or "threat") != "worldbuilding":
            contrib_id = str(getattr(contribution, "contribution_id", "") or "")
            if contrib_id and contrib_id != authority_operation_id:
                raise WorldGraphAuthorityError(
                    "recovered publication contribution does not match the durable request",
                    code="integrity_failure",
                    details={
                        "world_id": world_id,
                        "authority_operation_id": authority_operation_id,
                        "requested_contribution_id": contrib_id,
                    },
                )
        return WorldGraphPublicationReceipt(
            world_id=world_id,
            authority_operation_id=authority_operation_id,
            parent_revision_id=parent_id,
            published_revision_id=str(getattr(manifest, "revision_id", "") or ""),
            reviewed_contribution_id=authority_operation_id,
            accepted_assertion_ids=(),
            published=True,
            outcome="already_applied",
        )

    def verify_child(
        self,
        *,
        receipt: WorldGraphPublicationReceipt,
        expected: WorldGraphExpectedChildFacts,
    ) -> WorldGraphVerificationResult:
        codes: list[str] = []
        warnings: list[str] = []
        status = "passed"
        try:
            store = kernel.load_world_graph_revision_with_integrity(
                self._world_root,
                receipt.world_id,
                receipt.published_revision_id,
            )
        except Exception as exc:  # noqa: BLE001
            return WorldGraphVerificationResult(
                status="failed",
                codes=("verification_store_load",),
                warnings=(str(exc)[:180],),
            )

        if expected.threat_node_id not in (store.nodes or {}):
            codes.append("missing_threat_object")
            status = "failed"
        if expected.external_resource_node_id and expected.external_resource_node_id not in (
            store.nodes or {}
        ):
            codes.append("missing_external_resource")
            status = "failed"
        if expected.binding_edge_id and expected.binding_edge_id not in (store.edges or {}):
            codes.append("missing_binding_edge")
            status = "failed"
        for assertion_id in expected.accepted_assertion_ids:
            raw = (getattr(store, "assertion_support", None) or {}).get(assertion_id)
            if not isinstance(raw, dict) or raw.get("support_state") != "supported":
                codes.append(f"unsupported:{assertion_id}")
                status = "failed"

        try:
            rebuild = kernel.rebuild_from_contributions(
                self._world_root,
                world_id=receipt.world_id,
                compare_revision_id=receipt.published_revision_id,
                publish=False,
            )
            if "rebuild_equivalent_to_pinned_revision" not in (rebuild.diagnostics or []):
                codes.append("rebuild_not_equivalent")
                status = "degraded" if status == "passed" else status
        except Exception as exc:  # noqa: BLE001
            codes.append("rebuild_unavailable")
            warnings.append(str(exc)[:180])
            status = "degraded" if status == "passed" else status

        if expected.campaign_id and expected.threat_node_id:
            try:
                kernel.project_world_graph(
                    self._world_root,
                    WorldGraphProjectionRequest(
                        schema=PROJECTION_REQUEST_SCHEMA,
                        world_id=receipt.world_id,
                        campaign_id=expected.campaign_id,
                        focus=WorldGraphProjectionFocus(kind="none"),
                        admissibility="gm",
                        scope_mode="campaign",
                        revision_pin=receipt.published_revision_id,
                        query_text=expected.threat_node_id,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                codes.append("projection_unavailable")
                warnings.append(str(exc)[:180])
                status = "degraded" if status == "passed" else status

        return WorldGraphVerificationResult(
            status=status,  # type: ignore[arg-type]
            codes=tuple(codes),
            warnings=tuple(warnings),
        )
