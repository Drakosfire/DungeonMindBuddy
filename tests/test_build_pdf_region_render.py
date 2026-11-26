from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import RectangleObject

from apps.live_control_server.services.build_pdf_region_render import render_region


@pytest.mark.parametrize(("rotation", "expected"), [(0, (667, 500)), (90, (1000, 334))])
def test_disjoint_cropbox_uses_rotated_mediabox(rotation, expected):
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=300)
    page.cropbox = RectangleObject((300, 350, 500, 600))
    page.rotate(rotation)
    pdf = BytesIO()
    writer.write(pdf)

    region = SimpleNamespace(page=1, left=0, top=0, right=1, bottom=0.5)
    with Image.open(BytesIO(render_region(pdf.getvalue(), region))) as image:
        assert image.format == "PNG"
        assert image.size == expected


def test_graph_pdf_crop_rejects_locator_revision_mismatch():
    import json
    from types import SimpleNamespace

    import pytest

    from apps.live_control_server.services.native_pdf_evidence import render_admitted_pdf_evidence

    evidence = SimpleNamespace(
        source_revision_id="srev:other",
        source_locator=json.dumps({
            "schema_version": "dm_native_pdf_region_v1",
            "source_revision_id": "srev:reviewed",
            "content_sha256": "a" * 64,
            "page": 1,
            "left": 0.1,
            "top": 0.2,
            "right": 0.7,
            "bottom": 0.8,
        }),
    )

    def load(*args):
        pytest.fail("A mismatched locator must be rejected before loading PDF bytes")

    with pytest.raises(ValueError, match="PDF evidence revision differs from its locator"):
        render_admitted_pdf_evidence(evidence, space_id="fixture-world", load=load)


def test_statblock_pdf_quote_must_match_the_selected_crop():
    from application_state.agent_conversation.native_build_work_view import resolve_statblock_pdf_quote

    pin = {"revision_id": "rev:fixture"}
    work = {"saved_statblocks": [{"pdf_support": {"scope": pin, "support": [
        {"text": "Hit Points 207", "assertion_id": "assertion:fixture", "evidence_ref_id": "pdf-region:hp"},
        {"text": "Seeping Miasma", "assertion_id": "assertion:fixture", "evidence_ref_id": "pdf-region:action"},
    ]}}]}
    assert resolve_statblock_pdf_quote(work, "pdf0:0", "Hit Points 207") == (
        pin, "assertion:fixture", "pdf-region:hp",
    )
    with pytest.raises(ValueError):
        resolve_statblock_pdf_quote(work, "pdf0:1", "Hit Points 207")
    with pytest.raises(ValueError, match="not offered"):
        resolve_statblock_pdf_quote(work, "pdf0:2", "Hit Points 207")


@pytest.mark.parametrize("has_stored_passage", [False, True])
def test_statblock_support_reads_only_the_exact_stored_passage(monkeypatch, has_stored_passage):
    from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1

    from apps.live_control_server.services import native_graph_inspection as inspection

    region = NativePdfRegionV1(
        schema_version="dm_native_pdf_region_v1",
        source_revision_id="srev:reviewed",
        content_sha256="a" * 64,
        page=1,
        left=0.1,
        top=0.2,
        right=0.7,
        bottom=0.8,
    )
    region_text_id = inspection.pdf_region_text_evidence_id("native", region)
    ids = ["pdf-region:reviewed"]
    if has_stored_passage:
        ids.append(region_text_id)
    access = object()
    reference = SimpleNamespace(
        managed_world_id="world", native_world_id="native", binding_version=1,
        graph_revision="rev:graph", node_id="creature",
    )
    monkeypatch.setattr(inspection, "_pinned", lambda pin, principal: (None, None, access, pin, None))
    monkeypatch.setattr(inspection, "_response", lambda bound, pin, **payload: payload)
    monkeypatch.setattr(inspection, "_repository", lambda: SimpleNamespace(
        get_native_pdf_source=lambda *args: pytest.fail("Retrieval tried to load a PDF"),
    ))
    monkeypatch.setattr(inspection, "EntityReadService", lambda: SimpleNamespace(
        get_complete_entity=lambda *args: SimpleNamespace(
            found=True, completeness=SimpleNamespace(status="complete"),
            assertions=[SimpleNamespace(subject_entity_id="creature", assertion_id="assertion:reviewed")],
        ),
    ))
    monkeypatch.setattr(inspection, "EvidenceReadService", lambda: SimpleNamespace(
        get_assertion_evidence=lambda *args: SimpleNamespace(
            available=True, completeness=SimpleNamespace(status="complete"),
            evidence=[SimpleNamespace(evidence_ref_id=ref, evidence_role="support") for ref in ids],
        ),
    ))
    reads = []

    def open_text(context, ref_id):
        reads.append(ref_id)
        return SimpleNamespace(
            status="available", body_text="é Stored passage. Trailing text.",
            span_start_byte=3, span_end_byte=18,
        )

    monkeypatch.setattr(inspection, "open_admitted_native_text", open_text)
    result = inspection.statblock_pdf_support(reference, (region,), object())
    if has_stored_passage:
        assert reads == [region_text_id]
        assert result["support"] == [{
            "assertion_id": "assertion:reviewed",
            "evidence_ref_id": region_text_id,
            "text": "Stored passage.",
        }]
    else:
        assert reads == []
        assert result["support"] == []
