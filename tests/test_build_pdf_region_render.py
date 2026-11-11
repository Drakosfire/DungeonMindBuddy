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
