"""Lossless reuse of exact dialogue text; occurrence metadata stays independent."""
from copy import deepcopy
from hashlib import sha256
import json

RULE = (" In dialogue arrays, same_text_as is a zero-based index of an earlier literal "
        "row: reuse only that row's user and assistant text. Each occurrence keeps "
        "its own position and metadata. Dialogue is reference, never source evidence.")


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def expand_dialogue(rows):
    if not isinstance(rows, list):
        raise ValueError("Dialogue must be an array")
    expanded = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("Dialogue row must be an object")
        item = deepcopy(row)
        if "same_text_as" in item:
            target = item.pop("same_text_as")
            if (type(target) is not int or not 0 <= target < index
                    or "same_text_as" in rows[target] or "user" in item or "assistant" in item):
                raise ValueError("Dialogue reference must name an earlier literal pair")
            item.update({role: expanded[target][role] for role in ("user", "assistant")})
        if any(not isinstance(item.get(role), str) for role in ("user", "assistant")):
            raise ValueError("Dialogue requires complete literal user and assistant text")
        for role in ("user", "assistant"):
            key = role + "_sha256"
            if key in item and item[key] != sha256(item[role].encode()).hexdigest():
                raise ValueError("Dialogue text differs from its occurrence digest")
        expanded.append(item)
    return expanded


def project_dialogue(rows):
    """Preserve all rows and bytes; only exact complete pairs share their text."""
    literal = expand_dialogue(rows)
    result, first = [], {}
    for index, row in enumerate(literal):
        key = (row["user"], row["assistant"])
        target = first.get(key)
        candidate = ({k: deepcopy(v) for k, v in row.items() if k not in {"user", "assistant"}}
                     | {"same_text_as": target}) if target is not None else row
        if target is not None and len(_json(candidate).encode()) < len(_json(row).encode()):
            result.append(candidate)
        else:
            first.setdefault(key, index)
            result.append(deepcopy(row))
    if len(_json(result).encode()) + len(_json(RULE).encode()) >= len(_json(literal).encode()):
        result = deepcopy(literal)
    if expand_dialogue(result) != literal:
        raise ValueError("Dialogue projection did not roundtrip exactly")
    return result


def dialogue_rule(rows):
    return RULE if any("same_text_as" in row for row in rows) else ""
