"""Render a region from PDF bytes already authorized by DungeonMind."""
from functools import lru_cache
from io import BytesIO
from math import ceil, floor
from subprocess import PIPE, SubprocessError, run

from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PyPdfError


def _render_page(pdf: bytes, page_number: int) -> bytes:
    page = str(page_number)
    try:
        source = PdfReader(BytesIO(pdf)).pages[page_number - 1]
        media = source.mediabox
        crop = source.cropbox
        overlaps = (
            max(media.left, crop.left) < min(media.right, crop.right)
            and max(media.bottom, crop.bottom) < min(media.top, crop.top)
        )
        box = ["-cropbox"] if overlaps else []
        rendered = run(
            ["pdftoppm", "-f", page, "-l", page, "-singlefile", *box,
             "-scale-to", "1000", "-png", "-"],
            input=pdf, stdout=PIPE, stderr=PIPE, check=True, timeout=10,
        )
        return rendered.stdout
    except (IndexError, OSError, PyPdfError, SubprocessError) as exc:
        raise ValueError("Unable to render retained PDF region") from exc


def request_page_renderer():
    """Reuse only the most recent exact PDF page within an extraction request."""
    return lru_cache(maxsize=1)(_render_page)


def render_region(pdf: bytes, region, *, render_page=_render_page) -> bytes:
    try:
        with Image.open(BytesIO(render_page(pdf, region.page)), formats=["PNG"]) as image:
            bounds = (
                floor(region.left * image.width),
                floor(region.top * image.height),
                ceil(region.right * image.width),
                ceil(region.bottom * image.height),
            )
            output = BytesIO()
            image.crop(bounds).save(output, format="PNG")
            return output.getvalue()
    except (IndexError, OSError, PyPdfError, SubprocessError) as exc:
        raise ValueError("Unable to render retained PDF region") from exc


def read_region_text(pdf: bytes, region) -> str:
    """Read the embedded text inside the same normalized page crop as the render."""
    try:
        source = PdfReader(BytesIO(pdf)).pages[region.page - 1]
        media = source.mediabox
        crop = source.cropbox
        # Leave unusual page geometry to the rendered OCR path.
        if source.rotation or source.user_unit != 1 or tuple(media) != tuple(crop):
            return ""
        left = floor(region.left * media.width)
        top = floor(region.top * media.height)
        width = ceil(region.right * media.width) - left
        height = ceil(region.bottom * media.height) - top
        page = str(region.page)
        result = run(
            ["pdftotext", "-f", page, "-l", page, "-r", "72", "-layout",
             "-x", str(left), "-y", str(top), "-W", str(width), "-H", str(height), "-", "-"],
            input=pdf, stdout=PIPE, stderr=PIPE, check=True, timeout=10,
        )
        return result.stdout.decode("utf-8").strip()
    except (IndexError, OSError, PyPdfError, SubprocessError, UnicodeError):
        return ""
