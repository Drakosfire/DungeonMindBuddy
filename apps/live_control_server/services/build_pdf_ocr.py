"""Submit a validated Build crop to the configured GenerationEngine worker."""
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

import httpx
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


def read_remote_text(raw: bytes, url: str, token: str) -> str:
    endpoint = httpx.URL(url)
    if (
        endpoint.scheme not in {"http", "https"}
        or not endpoint.host
        or endpoint.userinfo
        or endpoint.path != "/ocr"
        or endpoint.query
        or endpoint.fragment
    ):
        raise ValueError("Invalid private OCR endpoint")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/png",
        "Accept-Encoding": "identity",
    }
    with httpx.stream(
        "POST", endpoint, content=raw, headers=headers,
        timeout=httpx.Timeout(135, connect=5), trust_env=False, follow_redirects=False,
    ) as response:
        response.raise_for_status()
        if response.headers.get("Content-Encoding", "identity") != "identity":
            raise ValueError("Unexpected OCR response encoding")
        output = bytearray()
        for chunk in response.iter_raw(chunk_size=65536):
            if len(output) + len(chunk) > 1_000_000:
                raise ValueError("OCR response too large")
            output.extend(chunk)
    return json.loads(output)["text"]


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
    remote_url = os.getenv("BUDDY_OCR_REMOTE_URL")
    remote_token = os.getenv("BUDDY_OCR_REMOTE_TOKEN")
    remote_configured = remote_url is not None or remote_token is not None
    if remote_configured and not (remote_url and remote_token):
        raise HTTPException(503, "Private OCR is not configured.")
    if not remote_configured and not all(command):
        raise HTTPException(503, "Local OCR is not configured.")
    python, script, checkpoint = command
    if not _worker.acquire(blocking=False):
        raise HTTPException(503, "Local OCR is busy. Try again when the current capture finishes.")
    try:
        if remote_url and remote_token:
            text = read_remote_text(raw, remote_url, remote_token)
        else:
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
    except (OSError, httpx.HTTPError, httpx.InvalidURL, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        message = "Private OCR could not read this capture." if remote_configured else "Local OCR could not read this capture."
        raise HTTPException(503, message) from exc
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
