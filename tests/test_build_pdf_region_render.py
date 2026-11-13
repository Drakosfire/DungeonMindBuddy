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
