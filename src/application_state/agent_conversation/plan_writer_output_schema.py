"""Finite Plan output shapes; selectors constrain syntax, never evidence authority."""

from .rules_authority_plan_packet import PlanRulesEvidenceFrameV1
from .source_writer_output import LIMITATIONS
from .rules_authority_types import canonical_bytes
from .surface_evidence_answer import PLAN_POLICY, SELECTOR_POLICY, BODY_POLICY
from .native_plan_statements import POLICY as STATEMENT_POLICY
from .native_plan_assertions import POLICY as ASSERTION_POLICY

SCHEMA_NAME = "plan_evidence_selectors_v3"


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
    """Current execution uses only the current Plan policy."""
    return _frozen_schema(frame, rules, ASSERTION_POLICY if frame.get("schema") == "dmb_plan_jev_writer_frame_v8" else STATEMENT_POLICY if frame.get("schema") == "dmb_plan_jev_writer_frame_v7" else BODY_POLICY if frame.get("schema") == "dmb_plan_jev_writer_frame_v6" else PLAN_POLICY, target_scoped=True)


def _graph_groups(frame, passages, *, target_scoped):
    if not target_scoped:
        # Exact historical grammar; never used by a current dispatch.
        return [(kind, _values([row for row in frame["graph_records"]
                               if row["kind"] == kind], "target_id"), passages)
                for kind in ("assertion", "relationship")]
    closures = {}
    for row in frame["graph_records"]:
        if row["kind"] not in {"assertion", "relationship"}:
            continue
        target = _values([row], "target_id")[0]
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or any(
            not isinstance(token, str) or not token.strip() for token in evidence
        ):
            raise ValueError("Graph target evidence selectors are malformed")
        closures.setdefault((row["kind"], target), set()).add(tuple(sorted(set(evidence))))
    groups = {}
    for (kind, target), alternatives in sorted(closures.items()):
        # The final target binder requires exactly one evidence closure.
        if len(alternatives) != 1:
            continue
        evidence = next(iter(alternatives))
        handles = tuple(sorted({row["passage_handle"] for row in frame["opened_passages"]
                                if row.get("passage_handle") in passages
                                and row.get("evidence") in evidence}))
        groups.setdefault((kind, handles), []).append(target)
    return [(kind, targets, list(handles))
            for (kind, handles), targets in sorted(groups.items())]


def _native_variants(policy, prose, *, statement_rows=(), body_rows=(), assertion_rows=()):
    """One finite native selector grammar, independent of surface work syntax."""
    variants = []
    if policy in {STATEMENT_POLICY, ASSERTION_POLICY}:
        handles = _values(list(statement_rows), "statement_handle")
        if handles:
            variants.append(_object({"kind": _literal("native_statement_report"), "text": prose,
                "statement_handles": _array(_enum(handles), nonempty=True)}))
    if policy in {BODY_POLICY, STATEMENT_POLICY, ASSERTION_POLICY}:
        body_handles = _values(list(body_rows), 'excerpt_handle')
        if body_handles:
            variants.append(_object({'kind': _literal('native_body_claim'), 'text': prose,
                'excerpt_handles': _array(_enum(body_handles), nonempty=True)}))
    if policy == ASSERTION_POLICY:
        handles = _values(list(assertion_rows), 'assertion_handle')
        if handles:
            variants.append(_object({'kind': _literal('native_assertion_claim'), 'text': prose,
                'assertion_handles': _array(_enum(handles), nonempty=True)}))
    return variants


def _frozen_schema(frame, rules, policy, *, target_scoped=False):
    """One exact projection also verifies retained producer formats during reads."""
    if frame.get("answer_policy") != policy or not isinstance(
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
    for kind, targets, eligible in _graph_groups(frame, passages, target_scoped=target_scoped):
        if targets:
            handles = (
                _array(_enum(eligible))
                if eligible
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
    variants.extend(_native_variants(policy, prose,
        statement_rows=frame["native_statements"]["statements"] if policy in {STATEMENT_POLICY, ASSERTION_POLICY} else (),
        body_rows=frame['native_body_evidence']['excerpts'] if policy in {BODY_POLICY, STATEMENT_POLICY, ASSERTION_POLICY} else (),
        assertion_rows=frame['native_assertions']['assertions'] if policy == ASSERTION_POLICY else ()))
    if selections:
        variants.append(
            _object(
                {
                    "kind": _literal("authored_excerpt"),
                    "selection_id": _enum(selections),
                }
            )
        )
    session_selections = _values([block for session in frame["session_evidence"]
        for source in session["sources"] for block in source["text_blocks"]
        if block.get("selection_id") is not None], "selection_id")
    if session_selections and policy in {PLAN_POLICY, BODY_POLICY, STATEMENT_POLICY, ASSERTION_POLICY}:
        variants.append(_object({"kind": _literal("session_summary"), "text": prose,
                                 "selection_ids": _array(_enum(session_selections), nonempty=True)}))
    return _answer_schema(variants, policy, rules, prose)


def _answer_schema(variants, policy, rules, prose):
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
            "schema": _literal(policy),
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


def native_output_format(frame, rules):
    from .native_writer import SCHEMA
    if (frame.get('schema') != SCHEMA or frame.get('answer_policy') != ASSERTION_POLICY
            or not isinstance(rules, PlanRulesEvidenceFrameV1)):
        raise ValueError('Shared native output requires its actual evidence and Rules frames')
    prose = {'type': 'string', 'minLength': 1}
    variants = _native_variants(ASSERTION_POLICY, prose,
        statement_rows=frame['native_statements']['statements'],
        body_rows=frame['native_body_evidence']['excerpts'],
        assertion_rows=frame['native_assertions']['assertions'] if frame['native_assertions'] is not None else ())
    return {'type': 'json_schema', 'name': 'surface_native_evidence_selectors_v1', 'strict': True,
        'schema': _answer_schema(variants, ASSERTION_POLICY, rules, prose)}


def output_format(frame, rules):
    return {
        "type": "json_schema",
        "name": "plan_evidence_selectors_v6" if frame.get("schema") == "dmb_plan_jev_writer_frame_v8" else "plan_evidence_selectors_v5" if frame.get("schema") == "dmb_plan_jev_writer_frame_v7" else "plan_evidence_selectors_v4" if frame.get('schema') == 'dmb_plan_jev_writer_frame_v6' else SCHEMA_NAME,
        "schema": output_schema(frame, rules),
        "strict": True,
    }


def verify_format(body, frame, rules):
    # The actual immutable producer frame chooses its original read grammar.
    # Current dispatch separately compares the whole current projected frame.
    if frame.get("schema") in {"dmb_plan_jev_writer_frame_v3", "dmb_plan_jev_writer_frame_v4"}:
        expected = {"type": "json_schema", "name": "plan_evidence_selectors_v1",
                    "schema": _frozen_schema(frame, rules, SELECTOR_POLICY), "strict": True}
    elif (frame.get("schema") == "dmb_plan_jev_writer_frame_v5"
          and body.get("text", {}).get("format", {}).get("name") == "plan_evidence_selectors_v2"):
        expected = {"type": "json_schema", "name": "plan_evidence_selectors_v2",
                    "schema": _frozen_schema(frame, rules, PLAN_POLICY), "strict": True}
    else:
        expected = output_format(frame, rules)
    if canonical_bytes(body.get("text", {}).get("format")) != canonical_bytes(expected):
        raise ValueError(
            "Plan writer output format differs from its exact exposed selectors"
        )
