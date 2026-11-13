"""Render a PDF evidence record after the caller verifies Graph admission."""

from dungeonmind.application.vnext.native_pdf_access import open_native_pdf_region
from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1
from apps.live_control_server.services.build_pdf_region_render import render_region


def render_admitted_pdf_evidence(evidence, *, space_id, load):
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
    return region, render_region(pdf, region)
