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
