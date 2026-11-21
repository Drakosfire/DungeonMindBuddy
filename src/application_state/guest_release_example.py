"""Closed, plain-text saved example inside an immutable guest copy."""
from __future__ import annotations

import re

from application_state.errors import ApplicationStateValidationError

_DOMAIN = re.compile(r"(?i)(?:[a-z0-9-]+\.)+[a-z]{2,}(?:\b|$)")
_CHOICE_DOMAIN = re.compile(r"(?:[a-z0-9-]+\.)+[a-z]{2,}(?:\b|$)", re.ASCII)
_TRIM = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def _ascii_fold(value: str) -> str:
    return "".join(chr(ord(char) + 32) if "A" <= char <= "Z" else char for char in value)


def _choice_text(value: object, limit: int, *, multiline: bool = False) -> bool:
    """A portable code-point, whitespace and ASCII-destination contract."""
    if not isinstance(value, str) or not value.strip(_TRIM) or len(value) > limit:
        return False
    if any(char in value for char in "[]<>/\\@:") or _CHOICE_DOMAIN.search(_ascii_fold(value)):
        return False
    return not any((ord(char) < 32 and not (multiline and char == "\n"))
                   or 0x7f <= ord(char) <= 0x9f or 0x202a <= ord(char) <= 0x202e
                   or 0x2066 <= ord(char) <= 0x2069 or 0xd800 <= ord(char) <= 0xdfff for char in value)


def _text(value: object, limit: int, *, multiline: bool = False) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return False
    if any(c in value for c in "[]<>/\\@:") or _DOMAIN.search(value):
        return False
    return not any((ord(c) < 32 and not (multiline and c == "\n"))
                   or 0x7f <= ord(c) <= 0x9f or 0x202a <= ord(c) <= 0x202e
                   or 0x2066 <= ord(c) <= 0x2069 for c in value)


def validate_example(manifest: dict, source_bindings: list[tuple]) -> None:
    """Reject malformed examples and references outside this exact copy.

    Excerpts are related material, not machine-verified support for scene prose.
    """
    if "saved_example" not in manifest:
        if "saved_choice" in manifest:
            raise ApplicationStateValidationError("Saved choice requires a saved example")
        return
    example = manifest["saved_example"]
    if (not isinstance(example, dict)
        or set(example) != {"version", "title", "body", "references", "image"}
        or example["version"] != "owner_saved_scene_v1"
        or not _text(example["title"], 120)
        or not _text(example["body"], 10_000, multiline=True)):
        raise ApplicationStateValidationError("Invalid saved example")
    references = example["references"]
    bindings = {str(item[0]): item for item in source_bindings}
    if (not isinstance(references, list) or not 2 <= len(references) <= 10
        or any(not isinstance(item, str) or item not in bindings for item in references)
        or len(set(references)) != len(references)):
        raise ApplicationStateValidationError("Invalid saved example references")
    spans = [(str(bindings[item][1]), bindings[item][4], bindings[item][6], bindings[item][7]) for item in references]
    if len(set(spans)) != len(spans):
        raise ApplicationStateValidationError("Saved example references must use distinct spans")
    image = example["image"]
    if image is not None:
        assets = manifest.get("assets", [])
        if (not isinstance(image, dict) or set(image) != {"id", "description"}
            or not isinstance(image["id"], str)
            or not any(isinstance(asset, dict) and asset.get("id") == image["id"] for asset in assets)
            or not _text(image["description"], 240)):
            raise ApplicationStateValidationError("Invalid saved example image")
    if "saved_choice" not in manifest:
        return
    choice = manifest["saved_choice"]
    if (not isinstance(choice, dict) or set(choice) != {"version", "prompt", "options"}
        or choice["version"] != "owner_saved_choice_v1" or not _choice_text(choice["prompt"], 240)
        or not isinstance(choice["options"], list) or len(choice["options"]) != 2):
        raise ApplicationStateValidationError("Invalid saved choice")
    options = choice["options"]
    if (any(not isinstance(option, dict) or set(option) != {"label", "outcome"}
            or not _choice_text(option["label"], 80) or not _choice_text(option["outcome"], 2000, multiline=True)
            for option in options)
        or _ascii_fold(options[0]["label"].strip(_TRIM)) == _ascii_fold(options[1]["label"].strip(_TRIM))):
        raise ApplicationStateValidationError("Invalid saved choice options")
