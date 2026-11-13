"""Render a PDF evidence record after the caller verifies Graph admission."""

from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
from dungeonmind.application.vnext.native_pdf_access import open_native_pdf_region
from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1
from apps.live_control_server.services.build_pdf_region_render import render_region


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
