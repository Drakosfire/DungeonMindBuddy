"""Submit a validated Build crop to the configured local GenerationEngine worker."""
import base64
import binascii
import io
import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

from fastapi import HTTPException
from PIL import Image
from pydantic import BaseModel, Field

_worker = Lock()


_MAX_BASE64_LENGTH = 6_000_000
_MAX_PNG_BYTES = _MAX_BASE64_LENGTH // 4 * 3


class PdfCropRequest(BaseModel):
    png_base64: str = Field(max_length=_MAX_BASE64_LENGTH)


def read_crop(body: PdfCropRequest) -> dict[str, str]:
    try:
        raw = base64.b64decode(body.png_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(422, "Provide a valid PNG capture from Build.") from exc
    return read_crop_png(raw)


def read_crop_png(raw: bytes, *, allow_empty: bool = False) -> dict[str, str]:
    try:
        if len(raw) > _MAX_PNG_BYTES:
            raise ValueError("Unexpected crop size")
        with Image.open(io.BytesIO(raw), formats=["PNG"]) as image:
            if max(image.size) > 1024 or getattr(image, "n_frames", 1) != 1:
                raise ValueError("Unexpected crop dimensions or frame count")
            image.load()
    except (ValueError, OSError, binascii.Error, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Provide a valid PNG capture from Build.") from exc

    command = [os.getenv(name) for name in (
        "BUDDY_OCR_PYTHON", "BUDDY_OCR_COMMAND", "BUDDY_OCR_CHECKPOINT",
    )]
    if not all(command):
        raise HTTPException(503, "Local OCR is not configured.")
    python, script, checkpoint = command
    if not _worker.acquire(blocking=False):
        raise HTTPException(503, "Local OCR is busy. Try again when the current capture finishes.")
    try:
        with TemporaryDirectory(prefix="buddy-ocr-") as scratch:
            path = Path(scratch) / "capture.png"
            path.write_bytes(raw)
            result = subprocess.run(
                [python, script, "--checkpoint", checkpoint, "--image", str(path)],
                capture_output=True, check=True, timeout=120,
            )
        text = json.loads(result.stdout)["text"]
        if not isinstance(text, str) or (not allow_empty and not text.strip()):
            raise ValueError("Empty OCR transcription")
        return {"text": text}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, "Local OCR could not read this capture.") from exc
    finally:
        _worker.release()

_IMAGE_GROUNDING = re.compile(r"<\|ref\|>image<\|/ref\|>\s*<\|det\|>([\d,\[\] \t]+)<\|/det\|>")


def read_grounded_artwork(png: bytes, text: str) -> dict | None:
    """Crop the largest valid image region from the pixels submitted to OCR."""
    regions = []
    for match in _IMAGE_GROUNDING.finditer(text):
        try:
            boxes = json.loads(match[1])
        except (ValueError, RecursionError):
            continue
        if not isinstance(boxes, list):
            continue
        for box in boxes:
            if not isinstance(box, list) or len(box) != 4:
                continue
            if any(type(value) is not int or not 0 <= value <= 999 for value in box):
                continue
            left, top, right, bottom = box
            if left < right and top < bottom:
                regions.append(box)
    if not regions:
        return None
    bounds = max(regions, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]))
    with Image.open(io.BytesIO(png), formats=["PNG"]) as image:
        width, height = image.size
        pixels = tuple(value * dimension // 999 for value, dimension in zip(bounds, (width, height, width, height)))
        if pixels[0] == pixels[2] or pixels[1] == pixels[3]:
            return None
        output = io.BytesIO()
        image.crop(pixels).convert("RGB").save(output, format="JPEG", quality=88)
    return {"bounds": bounds, "jpeg_base64": base64.b64encode(output.getvalue()).decode("ascii")}
