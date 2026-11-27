"""Render a PDF evidence record after the caller verifies Graph admission."""

from hashlib import sha256

from dungeonmind.application.vnext.native_source_admission import allocate_native_source_id

from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
from dungeonmind.application.vnext.native_pdf_access import open_native_pdf_region
from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1
from apps.live_control_server.services.build_pdf_region_render import render_region


PDF_REGION_TEXT_CLIENT_REF = "reviewed-region"


def pdf_region_text_admission_id(region):
    locator_digest = sha256(region.model_dump_json().encode()).hexdigest()
    return f"dmb:pdf-region-text:v1:{locator_digest}"


def pdf_region_text_evidence_id(space_id, region):
    return allocate_native_source_id(
        space_id=space_id,
        admission_id=pdf_region_text_admission_id(region),
        identity_kind="evidence",
        client_ref=PDF_REGION_TEXT_CLIENT_REF,
    )


def open_admitted_pdf_evidence(evidence, *, space_id, load):
    region = NativePdfRegionV1.model_validate_json(evidence.source_locator)
    if region.source_revision_id != evidence.source_revision_id:
        raise ValueError("PDF evidence revision differs from its locator")
    pdf = open_native_pdf_region(
        region,
        authorized_space_id=space_id,
        audience=frozenset(),
        declared_labels=frozenset(),
        load=load,
    )
    if pdf is None:
        raise ValueError("Retained PDF unavailable")
    return region, pdf


def render_admitted_pdf_evidence(evidence, *, space_id, load):
    region, pdf = open_admitted_pdf_evidence(evidence, space_id=space_id, load=load)
    return region, render_region(pdf, region)


def reviewed_pdf_regions(resource, *, world_id):
    """Read the exact saved mechanics revision's PDF review locators."""
    through = (resource.get("provenance") or {}).get("accepted_through") or {}
    review = through.get(PDF_REVIEW_PROVENANCE)
    if review is None:
        return ()
    if review["world_id"] != world_id:
        raise ValueError("Saved statblock PDF review belongs to another World")
    return tuple(NativePdfRegionV1.model_validate(region) for region in review["regions"])


class _PdfEvidenceRegistrationRepository:
    def __init__(self, repository, authorize_write):
        self._repository = repository
        self._authorize_write = authorize_write

    def __getattr__(self, name):
        return getattr(self._repository, name)

    def get_revision(self, space_id, revision_id):
        revision = self._repository.get_revision(space_id, revision_id)
        self._authorize_write()
        return revision


def register_pdf_regions(repo, space_id, regions, context, access, created_at, *, authorize_write=None):
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from dungeonmind.application.vnext.native_pdf_access import bind_native_pdf_evidence, register_native_pdf_evidence

    def load_for_registration(space, revision):
        source = repo.get_native_pdf_source(space, revision)
        if authorize_write is not None:
            authorize_write()
        return source

    registration_repository = (
        repo if authorize_write is None else _PdfEvidenceRegistrationRepository(repo, authorize_write)
    )
    evidence_ids = []
    reviewed_regions = []
    for region in regions:
        source_access = dict(
            authorized_space_id=space_id, audience=frozenset(),
            declared_labels=frozenset(), load=repo.get_native_pdf_source,
        )
        evidence = bind_native_pdf_evidence(region, **source_access)
        if evidence is None:
            raise ApplicationStateConflictError("The selected PDF region is unavailable")
        if evidence.evidence_ref_id in evidence_ids:
            continue
        existing_ref = access.parsed.get_evidence(evidence.evidence_ref_id)
        if existing_ref is None:
            parent = context["revision_id"]
            if authorize_write is not None:
                authorize_write()
            register_native_pdf_evidence(
                region, **(source_access | {"load": load_for_registration}), repository=registration_repository,
                expected_parent_revision_id=parent,
                publication_id=f"{evidence.evidence_ref_id}:{parent}", created_at=created_at,
            )
            context, access = native.access_context(repo, space_id)
            existing_ref = access.parsed.get_evidence(evidence.evidence_ref_id)
        if (
            existing_ref is None
            or existing_ref.source_artifact_id != evidence.source_artifact_id
            or existing_ref.source_revision_id != evidence.source_revision_id
            or existing_ref.source_locator != evidence.source_locator
        ):
            raise ApplicationStateConflictError("The registered PDF evidence differs from the selected region")
        evidence_ids.append(evidence.evidence_ref_id)
        reviewed_regions.append(region)
    return context, access, tuple(evidence_ids), tuple(reviewed_regions)


def register_reviewed_region_text(repo, space_id, regions, context, access, created_at, *, authorize_write=None):
    """Admit extracted text during explicit PDF review, for later text-only retrieval."""
    from dungeonmind.application.vnext import open_admitted_native_text, publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.common import LabelsAllVisibility
    from dungeonmind.contracts.vnext.native_source import (
        NativeTextEvidenceSpanRequestV1, NativeTextSourceAdmissionV1, NativeTextSourceOriginV1,
    )

    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import AuthorizedTextAdmissionRepository
    from apps.live_control_server.services.build_pdf_region_render import read_region_text
    from graph_memory.vnext.domain_runtime import GM_LABEL

    admission_repository = repo if authorize_write is None else AuthorizedTextAdmissionRepository(repo, authorize_write)
    evidence_ids = []
    for region in regions:
        admission_id = pdf_region_text_admission_id(region)
        evidence_id = pdf_region_text_evidence_id(space_id, region)
        origin = NativeTextSourceOriginV1(
            namespace="dungeonbuddy.pdf-region", object_id=admission_id,
            revision_id=region.source_revision_id,
        )
        receipt = repo.get_native_source_admission_receipt(space_id, admission_id)
        if receipt is None:
            locator_id = "pdf-region:" + sha256(region.model_dump_json().encode()).hexdigest()
            locator = access.parsed.get_evidence(locator_id)
            if locator is None:
                raise ApplicationStateConflictError("The reviewed PDF locator is unavailable")
            _, pdf = open_admitted_pdf_evidence(locator, space_id=space_id, load=repo.get_native_pdf_source)
            body = read_region_text(pdf, region)
            if not body.strip():
                continue
            encoded = body.encode()
            digest = sha256(encoded).hexdigest()
            domain, profile = native.descriptors(repo, space_id, context["revision_id"])
            if authorize_write is not None:
                authorize_write()
            receipt = publish_native_text_source_evidence(
                repository=admission_repository, domain_contract=domain, semantic_profile=profile,
                request=NativeTextSourceAdmissionV1(
                    space_id=space_id, admission_id=admission_id,
                    expected_parent_revision_id=context["revision_id"], created_at=created_at,
                    body_text=body, expected_body_sha256=digest,
                    source_classification="dungeonbuddy.source:worldbuilding",
                    authority="derived", visibility=LabelsAllVisibility(labels=[GM_LABEL]), origin=origin,
                    spans=[NativeTextEvidenceSpanRequestV1(
                        client_ref=PDF_REGION_TEXT_CLIENT_REF, evidence_role="support",
                        start_byte=0, end_byte=len(encoded), expected_slice_sha256=digest,
                    )],
                ),
            )
            context, access = native.access_context(repo, space_id)
        if (receipt.space_id != space_id or receipt.admission_id != admission_id
                or receipt.origin != origin or len(receipt.bindings) != 1
                or receipt.bindings[0].client_ref != PDF_REGION_TEXT_CLIENT_REF
                or receipt.bindings[0].evidence_ref_id != evidence_id
                or open_admitted_native_text(access, evidence_id).status != "available"):
            raise ApplicationStateConflictError("The exact reviewed PDF passage is unavailable")
        evidence_ids.append(evidence_id)
    return context, access, tuple(evidence_ids)
