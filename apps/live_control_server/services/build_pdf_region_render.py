"""Render a region from PDF bytes already authorized by DungeonMind."""
from io import BytesIO
from math import ceil, floor
from subprocess import PIPE, SubprocessError, run

from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PyPdfError


def render_region(pdf: bytes, region) -> bytes:
    page = str(region.page)
    try:
        source = PdfReader(BytesIO(pdf)).pages[region.page - 1]
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
        with Image.open(BytesIO(rendered.stdout), formats=["PNG"]) as image:
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
