"""Render a region from PDF bytes already authorized by DungeonMind."""
from io import BytesIO
from math import ceil, floor
from subprocess import PIPE, SubprocessError, run

from PIL import Image


def render_region(pdf: bytes, region) -> bytes:
    page = str(region.page)
    try:
        rendered = run(
            ["pdftoppm", "-f", page, "-l", page, "-singlefile", "-cropbox",
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
    except (OSError, SubprocessError) as exc:
        raise ValueError("Unable to render retained PDF region") from exc
