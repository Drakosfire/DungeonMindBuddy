"""Resume immutable reviewed inputs by Core receipts, not local progress flags."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dungeonmind.application.contribution_review_v2 import (
    finalize_contribution_review_v2,
)
from dungeonmind.application.review_materialization_v6 import (
    materialize_finalized_review_v6,
    review_source_refs_v6,
)
from dungeonmind.application.review_publication import publish_finalized_review
from dungeonmind.application.source_admission import (
    admit_source_revision,
    source_admission_command_sha256,
)
from dungeonmind.contracts.capability import CapabilityPolicy
from dungeonmind.contracts.contribution_review import derive_review_id
from dungeonmind.contracts.contribution_review_v2 import ContributionReviewSubmissionV2
from dungeonmind.contracts.evidence import SourceArtifactRecord, SourceRevision
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.domain.errors import (
    CapabilityDeniedError,
    ContributionMaterializationError,
    ContributionReviewValidationError,
    IdempotencyConflictError,
    StaleParentRevisionError,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    ManagedWorldGraphProjectionRequest,
    VerifiedManagedWorldBinding,
    project_managed_world_graph,
    resolve_managed_world_binding,
)
from apps.live_control_server.services.reviewed_corpus_publication_store import (
    PublicationProgressStore,
    ProgressConflict,
)
from graph_memory.retrieval.source_reader import parse_repo_uri


class ProcedureStopped(RuntimeError):
    """Fixed safe code; underlying errors and packet bodies never become CLI text."""


class ReviewedCorpusSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    admission_id: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{1,256}$")
    artifact: SourceArtifactRecord
    revision: SourceRevision


class ReviewedCorpusPacket(BaseModel):
    """Internal transport of existing Core authority; no synthesized approval."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    managed_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    binding_version: int = Field(gt=0, strict=True)
    source_root_relpath: str = Field(min_length=1)
    sources: tuple[ReviewedCorpusSource, ...] = Field(min_length=1, max_length=32)
    submission: ContributionReviewSubmissionV2
    capability_policy: CapabilityPolicy

    @model_validator(mode="after")
    def exact_scope(self) -> ReviewedCorpusPacket:
        intent = self.submission.intent
        scope = self.capability_policy.graph_scope
        if (
            intent.world_id != self.native_world_id
            or scope is None
            or scope.world_id != self.native_world_id
            or str(scope.admissibility) != "gm"
            or scope.campaign_id != intent.campaign_id
            or scope.revision_pin != intent.plan_ref.expected_parent_revision_id
        ):
            raise ValueError("review_scope_mismatch")
        ids = [item.admission_id for item in self.sources]
        artifacts = [item.artifact.source_artifact_id for item in self.sources]
        if len(set(ids)) != len(ids) or len(set(artifacts)) != len(artifacts):
            raise ValueError("duplicate_source_identity")
        for source in self.sources:
            if (
                source.artifact.world_id != self.native_world_id
                or source.artifact.campaign_id not in (None, intent.campaign_id)
                or source.revision.source_artifact_id
                != source.artifact.source_artifact_id
                or source.artifact.current_revision_id
                != source.revision.source_revision_id
            ):
                raise ValueError("source_scope_mismatch")
        return self

    @property
    def operation_id(self) -> str:
        return self.submission.intent.operation_id

    @property
    def review_id(self) -> str:
        return derive_review_id(
            operation_id=self.operation_id,
            review_intent_sha256=self.submission.intent.review_intent_sha256,
            world_id=self.native_world_id,
        )


class CorePublicationBackend:
    """Existing typed Core writes and existing Buddy read adapters only."""

    def __init__(
        self,
        bundle: Any,
        *,
        artifact_root: Path,
        registry_root: Path | None = None,
        binding_resolver: Callable[
            ..., VerifiedManagedWorldBinding
        ] = resolve_managed_world_binding,
    ) -> None:
        self.bundle = bundle
        self.artifact_root = Path(artifact_root).resolve()
        self.registry_root = registry_root
        self.binding_resolver = binding_resolver
        from dungeonmind.application.graph_snapshot import (
            VersionedUnionGraphSnapshotReader,
        )
        from dungeonmind.infrastructure.semantic_profiles import (
            StaticSemanticProfileRegistry,
        )
        from dungeonmind_dnd.application.world_object_vocabulary import (
            load_builtin_v3_descriptor,
        )

        self.reader = VersionedUnionGraphSnapshotReader(
            profile_registry=StaticSemanticProfileRegistry(
                [load_builtin_v3_descriptor()]
            )
        )

    def binding(self, packet: ReviewedCorpusPacket) -> VerifiedManagedWorldBinding:
        actual = self.binding_resolver(packet.managed_world_id, root=self.registry_root)
        expected = VerifiedManagedWorldBinding(
            packet.managed_world_id,
            packet.native_world_id,
            packet.binding_version,
            packet.source_root_relpath,
        )
        if actual != expected:
            raise ProcedureStopped("selected_world_binding_changed")
        return actual

    def source_body(self, source: ReviewedCorpusSource) -> bytes:
        relative = parse_repo_uri(source.artifact.uri or "")
        if not relative or source.revision.body_storage != "external":
            raise ProcedureStopped("unsupported_source_body")
        path = (self.artifact_root / relative).resolve()
        if not path.is_relative_to(self.artifact_root):
            raise ProcedureStopped("source_body_outside_scope")
        try:
            if path.stat().st_size > 16_777_216:
                raise ProcedureStopped("source_body_outside_scope")
            body = path.read_bytes()
        except OSError as exc:
            raise ProcedureStopped("source_body_unavailable") from exc
        if hashlib.sha256(body).hexdigest() != source.revision.content_sha256:
            raise ProcedureStopped("source_bytes_changed")
        return body

    def parent(self, packet: ReviewedCorpusPacket, *, current: bool = False) -> Any:
        plan = packet.submission.intent.plan_ref
        parent = self.bundle.world_graph.get_revision(
            packet.native_world_id, plan.expected_parent_revision_id
        )
        if (
            parent is None
            or canonical_sha256(parent.graph_payload) != plan.base_graph_payload_sha256
            or parent.revision.graph_schema != plan.base_graph_schema
            or parent.graph_payload.get("semantic_profile")
            != plan.semantic_profile.model_dump(mode="json")
        ):
            raise ProcedureStopped("parent_or_profile_changed")
        self.reader.parse(
            graph_schema=parent.revision.graph_schema,
            graph_payload=parent.graph_payload,
        )
        if current:
            head = self.bundle.world_graph.get_head(packet.native_world_id)
            if (
                head is None
                or head.head_revision_id != plan.expected_parent_revision_id
            ):
                raise ProcedureStopped("stale_parent")
        return parent

    def source_probe(
        self, packet: ReviewedCorpusPacket, source: ReviewedCorpusSource
    ) -> Any:
        receipt = self.bundle.sources.get_source_admission(source.admission_id)
        if receipt is None:
            return None
        expected = source_admission_command_sha256(
            world_id=packet.native_world_id,
            expected_head_revision_id=packet.submission.intent.plan_ref.expected_parent_revision_id,
            artifact=source.artifact,
            revision=source.revision,
        )
        if (
            receipt.world_id != packet.native_world_id
            or receipt.command_sha256 != expected
            or receipt.content_sha256 != source.revision.content_sha256
        ):
            raise ProcedureStopped("source_receipt_conflict")
        artifact = self.bundle.sources.get_artifact(source.artifact.source_artifact_id)
        revision = self.bundle.sources.get_revision(source.revision.source_revision_id)
        if (
            artifact is None
            or revision is None
            or (
                canonical_sha256(artifact.model_dump(mode="json"))
                != canonical_sha256(source.artifact.model_dump(mode="json"))
                or canonical_sha256(revision.model_dump(mode="json"))
                != canonical_sha256(source.revision.model_dump(mode="json"))
            )
        ):
            raise ProcedureStopped("source_authority_changed")
        return receipt

    def admit(
        self,
        packet: ReviewedCorpusPacket,
        source: ReviewedCorpusSource,
        body: bytes,
        at: datetime,
    ) -> Any:
        return admit_source_revision(
            world_id=packet.native_world_id,
            admission_id=source.admission_id,
            expected_head_revision_id=packet.submission.intent.plan_ref.expected_parent_revision_id,
            artifact=source.artifact,
            revision=source.revision,
            source_body=body,
            admitted_at=at,
            world_graph_repository=self.bundle.world_graph,
            source_repository=self.bundle.sources,
        )

    def review_probe(self, packet: ReviewedCorpusPacket) -> Any:
        state = self.bundle.contribution_reviews.get(
            packet.native_world_id, packet.review_id
        )
        other = self.bundle.contribution_reviews.get_for_plan(
            packet.native_world_id, packet.submission.intent.plan_ref.source_plan_id
        )
        if state is None:
            if other is not None:
                raise ProcedureStopped("review_identity_conflict")
            return None
        record = state.record
        intent = packet.submission.intent
        candidate = intent.candidate_contribution.model_dump(mode="json")
        candidate["status"] = "superseded"
        if (
            record.operation_id != packet.operation_id
            or record.review_intent_sha256 != intent.review_intent_sha256
            or record.confirmation_id != packet.submission.confirmation.confirmation_id
            or record.plan_ref != intent.plan_ref
            or record.reviewer_id != intent.reviewer_id
            or record.reviewed_at != intent.reviewed_at
            or record.assertion_verdicts != intent.assertion_verdicts
            or record.identity_verdicts != intent.identity_verdicts
            or record.identity_proposals != intent.identity_proposals
            or state.candidate_contribution.model_dump(mode="json") != candidate
        ):
            raise ProcedureStopped("review_receipt_conflict")
        return state

    def finalize(self, packet: ReviewedCorpusPacket) -> Any:
        return finalize_contribution_review_v2(
            packet.submission,
            capability_policy=packet.capability_policy,
            world_graph_repository=self.bundle.world_graph,
            review_repository=self.bundle.contribution_reviews,
        )

    def publication_probe(self, packet: ReviewedCorpusPacket) -> Any:
        result = self.bundle.finalized_review_publications.get(
            packet.native_world_id, packet.operation_id
        )
        if result is None:
            return None
        state = self.review_probe(packet)
        if (
            state is None
            or result.review_id != packet.review_id
            or result.review_intent_sha256
            != packet.submission.intent.review_intent_sha256
            or result.reviewed_contribution_sha256
            != state.record.reviewed_contribution_sha256
            or result.reviewed_contribution_id != state.record.reviewed_contribution_id
            or result.confirmation_id != packet.submission.confirmation.confirmation_id
            or result.expected_parent_revision_id
            != packet.submission.intent.plan_ref.expected_parent_revision_id
        ):
            raise ProcedureStopped("publication_receipt_conflict")
        return result

    def materialization(self, packet: ReviewedCorpusPacket) -> Any:
        state = self.review_probe(packet)
        if state is None:
            raise ProcedureStopped("review_not_committed")
        artifact_ids, revision_ids = review_source_refs_v6(state)
        snapshot = self.bundle.finalized_review_publications.get_provenance_snapshot(
            artifact_ids=artifact_ids, revision_ids=revision_ids
        )
        return materialize_finalized_review_v6(
            state,
            parent=self.parent(packet),
            graph_reader=self.reader,
            source_snapshot=snapshot,
        )

    def publish(self, packet: ReviewedCorpusPacket, at: datetime) -> Any:
        return publish_finalized_review(
            packet.native_world_id,
            packet.review_id,
            published_at=at,
            review_repository=self.bundle.contribution_reviews,
            world_graph_repository=self.bundle.world_graph,
            publication_repository=self.bundle.finalized_review_publications,
            graph_reader=self.reader,
        )

    def effects(self, packet: ReviewedCorpusPacket) -> dict[str, Any]:
        material = self.materialization(packet)
        before, after = self.parent(packet).graph_payload, material.graph_payload

        def rows(payload: dict, name: str, key: str) -> dict:
            return {row[key]: canonical_sha256(row) for row in payload[name]}

        old_objects, new_objects = (
            rows(before, "objects", "object_id"),
            rows(after, "objects", "object_id"),
        )
        old_refs, new_refs = (
            rows(before, "evidence_refs", "evidence_ref_id"),
            rows(after, "evidence_refs", "evidence_ref_id"),
        )
        old_rel, new_rel = (
            rows(before, "relationships", "relationship_id"),
            rows(after, "relationships", "relationship_id"),
        )
        applied: dict[str, list[str]] = {}

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                metadata = value.get("assertion_metadata")
                if isinstance(metadata, dict):
                    applied[metadata["assertion_id"]] = metadata["evidence_ref_ids"]
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        collect(after)
        targets = []
        from dungeonmind.contracts.contribution_review_v2 import (
            NON_MUTATING_IDENTITY_OUTCOMES,
        )

        for assertion in self.review_probe(packet).reviewed_contribution.assertions:
            if (
                str(assertion.acceptance_state) != "accepted"
                or assertion.identity_resolution_outcome
                in NON_MUTATING_IDENTITY_OUTCOMES
            ):
                continue
            value = (
                json.loads(assertion.value or "{}")
                if assertion.assertion_kind == "attribute"
                else {}
            )
            observation = value.get("property_term") == "session_observation"
            if (
                assertion.subject_object_id
                and assertion.assertion_kind in ("attribute", "alias")
                and (observation or assertion.assertion_id in applied)
            ):
                target = {
                    "assertion_id": assertion.assertion_id,
                    "subject_id": assertion.subject_object_id,
                    "kind": "observation" if observation else "assertion",
                    "evidence_ids": sorted(
                        {ref.evidence_ref_id for ref in assertion.evidence_refs}
                        if observation
                        else set(applied[assertion.assertion_id])
                    ),
                }
                if observation:
                    target["text_sha256"] = hashlib.sha256(
                        value["summary"].strip().encode()
                    ).hexdigest()
                targets.append(target)
        changed_relationships = sorted(
            key for key in new_rel if old_rel.get(key) != new_rel[key]
        )
        relationship_support = {
            row["relationship_id"]: sorted(
                set(row["assertion_metadata"]["evidence_ref_ids"])
            )
            for row in after["relationships"]
            if row["relationship_id"] in changed_relationships
        }
        readback_refs = set(new_refs) - set(old_refs)
        for target in targets:
            readback_refs.update(target["evidence_ids"])
        for refs in relationship_support.values():
            readback_refs.update(refs)
        return {
            "graph_payload_sha256": material.graph_payload_sha256,
            "source_pairs": sorted(
                [
                    [s.artifact.source_artifact_id, s.revision.source_revision_id]
                    for s in packet.sources
                ]
            ),
            "introduced_evidence_ids": sorted(set(new_refs) - set(old_refs)),
            "changed_object_ids": sorted(
                key for key in new_objects if old_objects.get(key) != new_objects[key]
            ),
            "changed_relationship_ids": changed_relationships,
            "relationship_support": relationship_support,
            "accepted_assertion_targets": targets,
            "readback_evidence_ids": sorted(readback_refs),
        }

    def verify(self, packet: ReviewedCorpusPacket, publication: Any) -> dict[str, Any]:
        effects = self.effects(packet)
        child = self.bundle.world_graph.get_revision(
            packet.native_world_id, publication.published_revision_id
        )
        if (
            child is None
            or canonical_sha256(child.graph_payload) != effects["graph_payload_sha256"]
            or publication.graph_payload_sha256 != effects["graph_payload_sha256"]
        ):
            raise ProcedureStopped("published_effects_conflict")
        binding = self.binding(packet)
        # Service seam proof is not HTTP authentication, runtime activation or product readiness.
        selected = project_managed_world_graph(
            ManagedWorldGraphProjectionRequest(
                schema_="dmb_managed_world_graph_projection_request_v1",
                managed_world_id=packet.managed_world_id,
                revision_pin=publication.published_revision_id,
            ),
            root=self.registry_root,
            expected_binding=binding,
        )
        if (
            selected.projection.snapshot.revision_id
            != publication.published_revision_id
        ):
            raise ProcedureStopped("selected_world_query_conflict")
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
            direct_services_from_bundle,
            get_object_with_reviewed_sources_direct,
            get_evidence_direct,
            read_source_anchor_direct,
        )
        from graph_memory.retrieval.models import (
            WorldGraphObjectRequest,
            WorldGraphEvidenceRequest,
            WorldGraphSourceAnchorReadRequest,
        )

        services = direct_services_from_bundle(self.bundle, packet.native_world_id)
        common = {
            "worldId": packet.native_world_id,
            "campaignId": "",
            "scopeMode": "world",
            "focus": {"kind": "none"},
            "admissibility": "gm",
            "revisionPin": publication.published_revision_id,
        }
        anchors = {}
        verified_assertions = []
        object_ids = set(effects["changed_object_ids"]) | {
            target["subject_id"] for target in effects["accepted_assertion_targets"]
        }
        for object_id in sorted(object_ids):
            observation_targets = [
                target
                for target in effects["accepted_assertion_targets"]
                if target["subject_id"] == object_id and target["kind"] == "observation"
            ]
            result, observations, gaps, missing = (
                get_object_with_reviewed_sources_direct(
                    services,
                    WorldGraphObjectRequest.model_validate(
                        {
                            **common,
                            "schema": "dmb_world_graph_object_request_v1",
                            "nodeId": object_id,
                        }
                    ),
                )
            )
            unrelated_relationship_bound = result.outcome == "truncated" and set(
                result.coverage.truncated_fields
            ) == {"relationships"}
            unrelated_observation_bound = (
                result.outcome == "truncated"
                and bool(observation_targets)
                and set(gaps) == {"reviewed_source_observation_anchor_bound"}
                and "reviewed_source_observations" in result.coverage.truncated_fields
                and set(result.coverage.truncated_fields).issubset(
                    {"relationships", "reviewed_source_observations"}
                )
            )
            if (
                (
                    result.outcome != "enough"
                    and not unrelated_relationship_bound
                    and not unrelated_observation_bound
                )
                or (gaps and not unrelated_observation_bound)
                or missing
                or result.coverage.missing_seed_node_ids
                or result.coverage.missing_evidence_ref_ids
                or set(result.coverage.truncated_fields)
                - (
                    {"relationships", "reviewed_source_observations"}
                    if unrelated_observation_bound
                    else {"relationships"}
                )
                or object_id not in [node.node_id for node in result.nodes]
            ):
                raise ProcedureStopped("published_object_unavailable")
            for target in observation_targets:
                matches = [
                    row
                    for row in observations
                    if row.assertion_id == target["assertion_id"]
                    and row.subject_node_id == object_id
                    and row.review_id == packet.review_id
                    and row.publication_revision_id == publication.published_revision_id
                    and row.contribution_id == publication.reviewed_contribution_id
                ]
                if (
                    len(matches) != 1
                    or hashlib.sha256(matches[0].text.encode()).hexdigest()
                    != target["text_sha256"]
                ):
                    raise ProcedureStopped("published_observation_unavailable")
                refs = set(matches[0].evidence_ref_ids)
                admitted = {
                    anchor.evidence_ref_id
                    for anchor in result.source_anchors
                    if target["assertion_id"] in anchor.supporting_assertion_ids
                }
                if (
                    not refs
                    or not set(target["evidence_ids"]).issubset(refs)
                    or not refs.issubset(admitted)
                ):
                    raise ProcedureStopped("published_observation_support_unavailable")
                verified_assertions.append(target["assertion_id"])
            for anchor in result.source_anchors:
                if anchor.evidence_ref_id in effects["readback_evidence_ids"]:
                    anchors[anchor.anchor_id] = anchor
        for target in effects["accepted_assertion_targets"]:
            if target["kind"] != "assertion":
                continue
            result = get_evidence_direct(
                services,
                WorldGraphEvidenceRequest.model_validate(
                    {
                        **common,
                        "schema": "dmb_world_graph_evidence_request_v1",
                        "target": {"kind": "attribute", "id": target["assertion_id"]},
                    }
                ),
            )
            matches = [
                row
                for row in result.attributes
                if row.assertion_id == target["assertion_id"]
                and row.subject_node_id == target["subject_id"]
            ]
            refs = set(target["evidence_ids"])
            if (
                result.outcome != "enough"
                or len(matches) != 1
                or not refs
                or not refs.issubset(matches[0].evidence_ref_ids)
                or not refs.issubset({a.evidence_ref_id for a in result.source_anchors})
            ):
                raise ProcedureStopped("published_assertion_unavailable")
            verified_assertions.append(target["assertion_id"])
            for anchor in result.source_anchors:
                if anchor.evidence_ref_id in effects["readback_evidence_ids"]:
                    anchors[anchor.anchor_id] = anchor
        for relationship_id in effects["changed_relationship_ids"]:
            result = get_evidence_direct(
                services,
                WorldGraphEvidenceRequest.model_validate(
                    {
                        **common,
                        "schema": "dmb_world_graph_evidence_request_v1",
                        "target": {"kind": "relationship", "id": relationship_id},
                    }
                ),
            )
            matches = [
                row for row in result.relationships if row.edge_id == relationship_id
            ]
            refs = set(effects["relationship_support"][relationship_id])
            if (
                result.outcome != "enough"
                or result.request_summary
                != {"target_kind": "relationship", "target_id": relationship_id}
                or len(matches) != 1
                or not refs
                or not refs.issubset(matches[0].evidence_ref_ids)
                or not refs.issubset({a.evidence_ref_id for a in result.source_anchors})
            ):
                raise ProcedureStopped("published_relationship_unavailable")
            for anchor in result.source_anchors:
                if anchor.evidence_ref_id in effects["readback_evidence_ids"]:
                    anchors[anchor.anchor_id] = anchor
        opened, unavailable, covered = [], [], set()
        for anchor_id, anchor in sorted(anchors.items()):
            if not anchor.readable:
                continue
            try:
                result = read_source_anchor_direct(
                    services,
                    WorldGraphSourceAnchorReadRequest.model_validate(
                        {
                            **common,
                            "schema": "dmb_world_graph_source_anchor_read_request_v1",
                            "anchorId": anchor_id,
                            "maxChars": 12000,
                        }
                    ),
                    repo_root=self.artifact_root,
                )
            except Exception:
                unavailable.append(
                    {
                        "anchor_id": anchor_id,
                        "outcome": "unavailable",
                        "diagnostic_codes": ["source_read_unavailable"],
                    }
                )
                continue
            if result.outcome not in ("enough", "truncated") or not result.content:
                unavailable.append(
                    {
                        "anchor_id": anchor_id,
                        "outcome": result.outcome,
                        "diagnostic_codes": [d.code for d in result.diagnostics],
                    }
                )
                continue
            covered.add(anchor.evidence_ref_id)
            opened.append(
                {
                    "anchor_id": anchor_id,
                    "content_sha256": hashlib.sha256(
                        result.content.encode()
                    ).hexdigest(),
                    "line_start": result.line_start,
                    "line_end": result.line_end,
                    "truncated": result.truncated,
                }
            )
        self.binding(packet)
        expected_refs = set(effects["readback_evidence_ids"])
        return {
            "core_verified": True,
            "selected_world_service_verified": True,
            "source_open_status": "not_applicable"
            if not expected_refs
            else "verified"
            if expected_refs.issubset(covered)
            else "unavailable"
            if unavailable
            else "incomplete",
            "verified_assertion_ids": sorted(verified_assertions),
            "opened_sources": opened,
            "unavailable_sources": unavailable,
            "effects": effects,
            "buddy_http_route_status": "not_exercised",
            "product_ready": False,
        }


_REJECTED = (
    CapabilityDeniedError,
    ContributionMaterializationError,
    ContributionReviewValidationError,
    IdempotencyConflictError,
    StaleParentRevisionError,
    ValueError,
)


class ReviewedCorpusPublicationProcedure:
    def __init__(
        self,
        backend: CorePublicationBackend,
        store: PublicationProgressStore,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.backend, self.store, self.clock = backend, store, clock

    def run(
        self,
        packet: ReviewedCorpusPacket,
        *,
        selected_world_id: str,
        execute: bool = False,
        schema_ready: bool = False,
        backup_verified: bool = False,
        stop_after: str | None = None,
    ) -> dict[str, Any]:
        # Freeze caller objects; neither Core lifecycle copies nor journal edits can alter approval.
        packet = ReviewedCorpusPacket.model_validate(packet.model_dump(mode="json"))
        if selected_world_id != packet.managed_world_id:
            raise ProcedureStopped("selected_world_mismatch")
        if execute and not (schema_ready and backup_verified):
            raise ProcedureStopped("external_prerequisites_required")
        self.backend.binding(packet)
        self.backend.parent(packet)
        bodies: dict[str, bytes] = {}
        if execute:
            from dungeonmind.domain.capability import evaluate_capability
            from dungeonmind.contracts.capability import CapabilityEffect
            from dungeonmind.contracts.contribution_review_v2 import (
                FINALIZE_REVIEW_V2_TOOL,
            )

            evaluate_capability(
                packet.capability_policy,
                tool_name=FINALIZE_REVIEW_V2_TOOL,
                effect=CapabilityEffect.COMMIT,
            )
        digest = canonical_sha256(packet.model_dump(mode="json"))
        if not execute:
            return self._advance(
                packet, digest, bodies, write=False, stop_after=stop_after
            )
        with self.store.exclusive(packet.operation_id):
            return self._advance(
                packet, digest, bodies, write=True, stop_after=stop_after
            )

    def _advance(
        self,
        packet: ReviewedCorpusPacket,
        digest: str,
        bodies: dict[str, bytes],
        *,
        write: bool,
        stop_after: str | None,
    ) -> dict[str, Any]:
        progress = self.store.read(packet.operation_id)
        identities = {
            "source_admission_ids": [s.admission_id for s in packet.sources],
            "review_id": packet.review_id,
            "confirmation_id": packet.submission.confirmation.confirmation_id,
            "native_world_id": packet.native_world_id,
            "managed_world_id": packet.managed_world_id,
            "binding_version": packet.binding_version,
            "source_root_relpath": packet.source_root_relpath,
            "expected_parent_revision_id": packet.submission.intent.plan_ref.expected_parent_revision_id,
            "profile": packet.submission.intent.plan_ref.semantic_profile.model_dump(
                mode="json"
            ),
        }
        if progress is None:
            progress = {
                "schema": "dmb_reviewed_corpus_progress_v1",
                "operation_id": packet.operation_id,
                "packet_sha256": digest,
                "identities": identities,
                "stages": {},
            }
        elif (
            progress.get("packet_sha256") != digest
            or progress.get("identities") != identities
        ):
            raise ProgressConflict("immutable_input_changed")
        observed = {}

        def answer(status: str, code: str | None = None) -> dict[str, Any]:
            return {
                "operation_id": packet.operation_id,
                "packet_sha256": digest,
                "status": status,
                "code": code,
                "observed_stages": observed,
                "all_stage_atomicity": False,
                "next_action": "probe_exact_receipts"
                if status == "unknown"
                else "resolve_authority_without_rebase"
                if status in ("rejected", "blocked")
                else "resume_same_packet",
                "product_ready": False,
            }

        steps = [
            (
                f"source:{source.admission_id}",
                lambda s=source: self.backend.source_probe(packet, s),
                lambda at, s=source: self.backend.admit(
                    packet, s, bodies[s.admission_id], at
                ),
            )
            for source in packet.sources
        ]
        steps += [
            (
                "review",
                lambda: self.backend.review_probe(packet),
                lambda _at: self.backend.finalize(packet),
            ),
            (
                "publication",
                lambda: self.backend.publication_probe(packet),
                lambda at: self.backend.publish(packet, at),
            ),
        ]
        # Detect already-known identity conflicts before admitting any new source.
        try:
            for _name, probe, _dispatch in steps:
                probe()
        except ProcedureStopped:
            raise
        except Exception:
            return answer("unknown", "receipt_probe_unavailable")
        for name, probe, dispatch in steps:
            self.backend.binding(packet)
            try:
                receipt = probe()
            except ProcedureStopped:
                raise
            except Exception:
                return answer("unknown", "receipt_probe_unavailable")
            stage = progress["stages"].get(name)
            if receipt is None:
                observed[name] = "absent"
                if stage:
                    observed[name] = "unknown"
                    return answer("unknown", "unresolved_previous_attempt")
                if not write:
                    return answer("pending")
                try:
                    self.backend.parent(packet, current=True)
                    bodies.update(
                        {
                            source.admission_id: self.backend.source_body(source)
                            for source in packet.sources
                        }
                    )
                    if name == "publication":
                        for source in packet.sources:
                            if self.backend.source_probe(packet, source) is None:
                                raise ProcedureStopped("source_not_committed")
                        self.backend.effects(packet)
                except ProcedureStopped as exc:
                    return answer("blocked", str(exc))
                except _REJECTED:
                    return answer("rejected", "core_pre_dispatch_rejected")
                at = (
                    datetime.fromisoformat(stage["first_attempt_at"])
                    if stage
                    else self.clock()
                )
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ProcedureStopped("attempt_timestamp_invalid")
                stage = {"first_attempt_at": at.isoformat(), "status": "attempted"}
                progress["stages"][name] = stage
                self.store.write(
                    packet.operation_id, progress
                )  # before the actual dispatch
                try:
                    dispatch(at)
                except Exception as exc:
                    try:
                        receipt = probe()
                    except Exception:
                        receipt = None
                    if receipt is None:
                        stage["status"] = (
                            "rejected" if isinstance(exc, _REJECTED) else "unknown"
                        )
                        observed[name] = stage["status"]
                        self.store.write(packet.operation_id, progress)
                        return answer(
                            stage["status"],
                            "core_stage_rejected"
                            if stage["status"] == "rejected"
                            else "core_stage_outcome_unknown",
                        )
                if receipt is None:
                    try:
                        receipt = probe()
                    except Exception:
                        receipt = None
                if receipt is None:
                    stage["status"] = "unknown"
                    observed[name] = "unknown"
                    self.store.write(packet.operation_id, progress)
                    return answer("unknown", "receipt_probe_unavailable")
            receipt_value = receipt.record if name == "review" else receipt
            receipt_digest = canonical_sha256(receipt_value.model_dump(mode="json"))
            if stage and stage.get("receipt_sha256") not in (None, receipt_digest):
                raise ProgressConflict("progress_receipt_conflict")
            observed[name] = "committed"
            if write:
                progress["stages"][name] = {
                    **(stage or {}),
                    "status": "committed",
                    "receipt_sha256": receipt_digest,
                }
                self.store.write(packet.operation_id, progress)
            if stop_after == name:
                return answer("committed_stage")
        publication = self.backend.publication_probe(packet)
        result = answer("published")
        result["published_revision_id"] = publication.published_revision_id
        try:
            result["verification"] = self.backend.verify(packet, publication)
            if result["verification"]["source_open_status"] == "verified":
                result["status"] = "verified"
        except Exception:
            result["verification"] = {
                "status": "unavailable",
                "product_ready": False,
                "buddy_http_route_status": "not_exercised",
            }
            result["next_action"] = "retry_read_only_verification"
        return result
