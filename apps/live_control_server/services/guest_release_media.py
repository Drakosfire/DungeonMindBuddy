"""Prepare release-owned image bytes without retaining source metadata."""
from __future__ import annotations

from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


class GuestReleaseMediaError(ValueError):
    """An image cannot be safely copied into a guest release."""


def sanitize_release_image(content: bytes) -> tuple[str, bytes]:
    """Decode one bounded image and re-encode pixels into a fresh PNG.

    Orientation is applied before metadata is dropped. The caller must still
    authorize and explicitly select the source asset and bind these output
    bytes into the reviewed release manifest.
    """
    if not isinstance(content, bytes) or not 0 < len(content) <= 10_000_000:
        raise GuestReleaseMediaError("Image bytes are invalid")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in {"PNG", "JPEG", "WEBP"} or getattr(source, "n_frames", 1) != 1:
                    raise GuestReleaseMediaError("Image format or animation is unsupported")
                width, height = source.size
                if width <= 0 or height <= 0 or width * height > 16_000_000:
                    raise GuestReleaseMediaError("Image dimensions exceed release limits")
                source.load()
                oriented = ImageOps.exif_transpose(source)
                # Allocate a new image rather than preserving info, EXIF, ICC,
                # comments, or source encoder options through a copy/save.
                mode = "RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB"
                pixels = oriented.convert(mode)
                clean = Image.new(mode, pixels.size)
                clean.paste(pixels)
                output = BytesIO()
                clean.save(output, format="PNG", optimize=False)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning, ValueError) as exc:
        if isinstance(exc, GuestReleaseMediaError):
            raise
        raise GuestReleaseMediaError("Image could not be safely decoded") from exc
    result = output.getvalue()
    if not result or len(result) > 10_000_000:
        raise GuestReleaseMediaError("Sanitized image exceeds release limits")
    return "image/png", result
