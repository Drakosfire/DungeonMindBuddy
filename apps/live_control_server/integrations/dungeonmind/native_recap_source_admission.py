"""Exact APP recap source composition over Core's owning native source contracts."""

from __future__ import annotations
from dungeonmind.application.vnext import (
    open_admitted_native_text,
    open_native_text_source_access_context,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.common import LabelsAllVisibility
from dungeonmind.contracts.vnext.native_source import (
    NativeTextSourceAdmissionV1,
    NativeTextSourceOriginV1,
    NativeTextEvidenceSpanRequestV1,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresNativeSourceEvidenceRepository,
)
from graph_memory.vnext.domain_runtime import GM_LABEL, resolve_dungeonbuddy_descriptors
from graph_memory.ingestion.native_recap_source import Command, Opening
from apps.live_control_server import config
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_source_identity,
)

CLASSIFICATION = "dungeonbuddy.source:session_recap"
SPAN = "whole-canonical-recap-v1"


class NativeRecapError(RuntimeError):
    def __init__(self, code, *, status_code=409):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class NativeRecapAuthority:
    def __init__(self, managed_root, repository=None):
        self.managed_root = managed_root
        self.repository = repository or PostgresNativeSourceEvidenceRepository(
            PostgresDatabase(config.world_graph_authority_database_url())
        )

    def check_binding(self, record):
        binding = resolve_managed_source_identity(
            record.managed_world_id, root=self.managed_root
        )
        if (
            binding.native_world_id != record.native_world_id
            or binding.binding_version != record.binding_version
        ):
            raise NativeRecapError("native_recap_binding_changed")

    def prepare(self, record, markdown):
        self.check_binding(record)
        head = self.repository.get_head(record.native_world_id)
        if head is None:
            raise NativeRecapError("native_recap_head_unavailable", status_code=503)
        snapshot = self.repository.get_revision(
            record.native_world_id, head.head_revision_id
        )
        if snapshot is None:
            raise NativeRecapError("native_recap_revision_unavailable", status_code=503)
        domain_ref, profile_ref = (
            snapshot.revision.domain_contract_ref,
            snapshot.revision.semantic_profile_ref,
        )
        resolve_dungeonbuddy_descriptors(domain_ref=domain_ref, profile_ref=profile_ref)
        request = NativeTextSourceAdmissionV1(
            space_id=record.native_world_id,
            admission_id=record.admission_id,
            expected_parent_revision_id=head.head_revision_id,
            created_at=record.created_at,
            body_text=markdown,
            expected_body_sha256=record.app_body_sha256,
            source_classification=CLASSIFICATION,
            authority="primary",
            visibility=LabelsAllVisibility(labels=[GM_LABEL]),
            origin=NativeTextSourceOriginV1(
                namespace="dungeonbuddy.app-recap-source.v1",
                object_id=record.app_source_artifact_id,
                revision_id=str(record.app_source_revision_id),
            ),
            spans=[
                NativeTextEvidenceSpanRequestV1(
                    client_ref=SPAN,
                    evidence_role="context",
                    start_byte=0,
                    end_byte=len(markdown.encode()),
                    expected_slice_sha256=record.app_body_sha256,
                )
            ],
        )
        wire = request.model_dump(mode="json")
        sha = canonical_sha256(
            {
                "request": wire,
                "domain_ref": domain_ref.model_dump(mode="json"),
                "profile_ref": profile_ref.model_dump(mode="json"),
            }
        )
        return Command(
            request={k: v for k, v in wire.items() if k != "body_text"},
            domain_ref=domain_ref,
            profile_ref=profile_ref,
            sha256=sha,
        )

    def receipt(self, record):
        return self.repository.get_native_source_admission_receipt(
            record.native_world_id, record.admission_id
        )

    def dispatch(self, record, markdown):
        self.check_binding(record)
        command = record.command
        domain, profile = resolve_dungeonbuddy_descriptors(
            domain_ref=command.domain_ref, profile_ref=command.profile_ref
        )
        return publish_native_text_source_evidence(
            repository=self.repository,
            request=command.resolve(markdown),
            domain_contract=domain,
            semantic_profile=profile,
        )

    def verify(self, record, markdown, receipt):
        self.check_binding(record)
        origin = {
            "namespace": "dungeonbuddy.app-recap-source.v1",
            "object_id": record.app_source_artifact_id,
            "revision_id": str(record.app_source_revision_id),
        }
        commands = [
            c
            for c in record.commands
            if c.request["expected_parent_revision_id"]
            == receipt.publication_receipt.expected_parent_revision_id
        ]
        if (
            receipt.admission_id != record.admission_id
            or receipt.space_id != record.native_world_id
            or receipt.origin is None
            or receipt.origin.model_dump() != origin
            or len(receipt.bindings) != 1
            or receipt.bindings[0].client_ref != SPAN
            or len(commands) != 1
        ):
            raise NativeRecapError("native_recap_receipt_mismatch")
        command = commands[0]
        command.resolve(markdown)
        domain, _ = resolve_dungeonbuddy_descriptors(
            domain_ref=command.domain_ref, profile_ref=command.profile_ref
        )
        context = open_native_text_source_access_context(
            repository=self.repository,
            space_id=record.native_world_id,
            revision_id=receipt.published_revision_id,
            domain_contract=domain,
            audience_labels=[GM_LABEL],
        )
        binding = receipt.bindings[0]
        opened = open_admitted_native_text(context, binding.evidence_ref_id)
        if opened.status != "available":
            return Opening(
                state="unavailable", read_revision_id=receipt.published_revision_id
            )
        stored = context.source_view.get_native_text_source(
            source_artifact_id=receipt.source_artifact_id,
            source_revision_id=receipt.source_revision_id,
            span_id=binding.span_id,
        )
        if (
            stored is None
            or stored.source_artifact.source_classification != CLASSIFICATION
            or stored.source_artifact.authority != "primary"
            or stored.source_artifact.visibility
            != LabelsAllVisibility(labels=[GM_LABEL])
            or opened.body_text != markdown
            or opened.body_sha256 != record.app_body_sha256
            or opened.span_start_byte != 0
            or opened.span_end_byte != len(markdown.encode())
            or opened.span_sha256 != record.app_body_sha256
            or opened.source_artifact_id != receipt.source_artifact_id
            or opened.source_revision_id != receipt.source_revision_id
        ):
            raise NativeRecapError("native_recap_opening_mismatch")
        self.check_binding(record)
        return Opening(
            state="verified",
            body_sha256=opened.body_sha256,
            span_start_byte=0,
            span_end_byte=opened.span_end_byte,
            span_sha256=opened.span_sha256,
            read_revision_id=receipt.published_revision_id,
            acquisition_epoch=opened.source_authority_epoch,
        )
