"""Finite Plan output shapes; selectors constrain syntax, never evidence authority."""

from .rules_authority_plan_packet import PlanRulesEvidenceFrameV1
from .source_writer_output import LIMITATIONS
from .rules_authority_types import canonical_bytes
from .surface_evidence_answer import SELECTOR_POLICY

SCHEMA_NAME = "plan_evidence_selectors_v1"


def _object(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _literal(value):
    return {"type": "string", "const": value}


def _enum(values):
    return {"type": "string", "enum": sorted(set(values))}


def _array(items, *, nonempty=False):
    return {"type": "array", "items": items, **({"minItems": 1} if nonempty else {})}


def _values(rows, key):
    if not isinstance(rows, list):
        raise ValueError("Plan output selectors require exposed rows")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Plan output selector row is malformed")
    values = [row.get(key) for row in rows]
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Plan output selector is absent or malformed")
    return sorted(set(values))


def output_schema(frame, rules):
    """Pure projection of the exact exposed selector sets, without new limits."""
    if frame.get("answer_policy") != SELECTOR_POLICY or not isinstance(
        rules, PlanRulesEvidenceFrameV1
    ):
        raise ValueError("Plan output requires its current selector and Rules frames")
    prose = {"type": "string", "minLength": 1}
    # Truncated/insufficient reads remain visible context but carry no citable handle.
    passages = _values(
        [
            row
            for row in frame["opened_passages"]
            if row.get("passage_handle") is not None
        ],
        "passage_handle",
    )
    native = _values(frame["native_source_sections"]["sections"], "section_handle")
    blocks = list(frame["committed_plan_blocks"])
    for session in frame["session_evidence"]:
        for source in session["sources"]:
            blocks.extend(source["text_blocks"])
    selections = _values(
        [row for row in blocks if row.get("selection_id") is not None], "selection_id"
    )
    variants = []
    for kind in ("assertion", "relationship"):
        targets = _values(
            [row for row in frame["graph_records"] if row["kind"] == kind], "target_id"
        )
        if targets:
            handles = (
                _array(_enum(passages))
                if passages
                else {"type": "array", "items": {"type": "string"}, "maxItems": 0}
            )
            variants.append(
                _object(
                    {
                        "kind": _literal("graph_claim"),
                        "claim_id": prose,
                        "text": prose,
                        "target_kind": _literal(kind),
                        "target_id": _enum(targets),
                        "passage_handles": handles,
                    }
                )
            )
    if passages:
        variants.append(
            _object(
                {
                    "kind": _literal("source_passage_claim"),
                    "text": prose,
                    "passage_handles": _array(_enum(passages), nonempty=True),
                }
            )
        )
    if native:
        variants.append(
            _object(
                {
                    "kind": _literal("native_source_claim"),
                    "text": prose,
                    "section_handles": _array(_enum(native), nonempty=True),
                }
            )
        )
    if selections:
        variants.append(
            _object(
                {
                    "kind": _literal("authored_excerpt"),
                    "selection_id": _enum(selections),
                }
            )
        )
    variants.append(
        _object(
            {
                "kind": _literal("proposal"),
                "text": prose,
                "label": _enum(["invented_idea", "image_prompt"]),
            }
        )
    )
    base = _object(
        {
            "schema": _literal(SELECTOR_POLICY),
            "answer_segments": _array({"anyOf": variants}),
            "limitations": _array(_enum(LIMITATIONS)),
            "requested_detail_gaps": _array(_object({"question_phrase": prose})),
        }
    )
    if not rules.lookups:
        return base
    rule_variants = [
        _object(
            {
                "kind": _literal("rules_context"),
                "text": prose,
                "category": _enum(["interpretation", "gap", "connective"]),
            }
        )
    ]
    if rules.supports:
        rule_variants.append(
            _object(
                {
                    "kind": _literal("rules_claim"),
                    "text": prose,
                    "support_ids": _array(
                        _enum(str(row.support_id) for row in rules.supports),
                        nonempty=True,
                    ),
                }
            )
        )
    mixed = _object(
        {
            "schema": _literal("dmb_rules_mixed_answer_v1"),
            "base_output": {"anyOf": [{"$ref": "#/$defs/Base"}, {"type": "null"}]},
            "rules_segments": _array({"anyOf": rule_variants}),
            "ordered_refs": _array(
                _object(
                    {
                        "domain": _enum(["base", "rules"]),
                        "segment_index": {"type": ["integer", "null"], "minimum": 0},
                    }
                )
            ),
        }
    )
    mixed["$defs"] = {"Base": base}
    return mixed


def output_format(frame, rules):
    return {
        "type": "json_schema",
        "name": SCHEMA_NAME,
        "schema": output_schema(frame, rules),
        "strict": True,
    }


def verify_format(body, frame, rules):
    if canonical_bytes(body.get("text", {}).get("format")) != canonical_bytes(
        output_format(frame, rules)
    ):
        raise ValueError(
            "Plan writer output format differs from its exact exposed selectors"
        )
