"""Golden projection comparison helpers for benchmarks and tests."""

from __future__ import annotations

from typing import Any

# Keys intentionally excluded from golden JSON but allowed on live projection payloads.
STRIPPED_ATTRIBUTE_KEYS = frozenset({"source_class", "source_truth_state", "all_value_labels"})


def normalize_projection_for_compare(projection: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaign_id": projection.get("campaign_id"),
        "entities": {},
        "conflicts": projection.get("conflicts", []),
        "metrics": projection.get("metrics", {}),
    }
    for entity_id, entity_payload in projection.get("entities", {}).items():
        attrs: dict[str, Any] = {}
        for attr_name, attr_payload in entity_payload.get("attributes", {}).items():
            cleaned = dict(attr_payload)
            for key in STRIPPED_ATTRIBUTE_KEYS:
                cleaned.pop(key, None)
            attrs[attr_name] = cleaned
        payload["entities"][entity_id] = {"attributes": attrs}
    return payload


def assert_attribute_keys_match_golden_contract(
    *,
    actual_projection: dict[str, Any],
    expected_projection: dict[str, Any],
    label: str,
) -> None:
    """Fail if live attribute dicts contain keys not present in golden + strip list.

    Prevents silently widening normalization strips while golden files stay frozen.
    """
    expected_entities = expected_projection.get("entities") or {}
    for entity_id, entity_payload in (actual_projection.get("entities") or {}).items():
        exp_entity = expected_entities.get(entity_id)
        if exp_entity is None:
            raise AssertionError(f"{label}: unexpected entity {entity_id!r} in actual projection")
        exp_attrs = exp_entity.get("attributes") or {}
        for attr_name, attr_payload in (entity_payload.get("attributes") or {}).items():
            exp_attr = exp_attrs.get(attr_name)
            if exp_attr is None:
                raise AssertionError(
                    f"{label}: unexpected attribute {entity_id}.{attr_name!r} in actual projection"
                )
            allowed = set(exp_attr.keys()) | STRIPPED_ATTRIBUTE_KEYS
            extra = set(attr_payload.keys()) - allowed
            if extra:
                raise AssertionError(
                    f"{label}: unexpected keys on {entity_id}.{attr_name}: "
                    f"{sorted(extra)} (allowed golden + {sorted(STRIPPED_ATTRIBUTE_KEYS)})"
                )
