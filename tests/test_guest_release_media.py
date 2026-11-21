from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin

from apps.live_control_server.services.guest_release_media import GuestReleaseMediaError, sanitize_release_image


def test_copy_preserves_pixels_without_private_metadata():
    source = Image.new("RGB", (2, 2), (12, 34, 56))
    info = PngImagePlugin.PngInfo()
    info.add_text("private-path", "/home/owner/secret")
    original = BytesIO()
    source.save(original, format="PNG", pnginfo=info)
    mime, result = sanitize_release_image(original.getvalue())
    assert mime == "image/png" and b"/home/owner/secret" not in result
    with Image.open(BytesIO(result)) as decoded:
        assert decoded.getpixel((0, 0)) == (12, 34, 56)
        assert "private-path" not in decoded.info


def test_copy_rejects_invalid_and_animated_images():
    with pytest.raises(GuestReleaseMediaError):
        sanitize_release_image(b"not an image")
    frames = [Image.new("RGB", (1, 1), c) for c in ((1, 2, 3), (4, 5, 6))]
    animated = BytesIO()
    frames[0].save(animated, format="PNG", save_all=True, append_images=frames[1:])
    with pytest.raises(GuestReleaseMediaError):
        sanitize_release_image(animated.getvalue())
