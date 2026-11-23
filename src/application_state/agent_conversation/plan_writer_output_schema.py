"""Finite Plan output shapes; selectors constrain syntax, never evidence authority."""

from .rules_authority_plan_packet import PlanRulesEvidenceFrameV1, ModelRulesFrame
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
        rules, (PlanRulesEvidenceFrameV1, ModelRulesFrame)
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
    variants.extend(_authored_variants(frame,policy,prose))
    return _answer_schema(variants, policy, rules, prose)



def _authored_variants(frame, policy, prose):
    blocks = ([block for source in frame["current_play"] for block in source["text_blocks"]]
        if "current_play" in frame else list(frame["committed_plan_blocks"]))
    for session in frame["session_evidence"]:
        for source in session["sources"]:
            blocks.extend(source["text_blocks"])
    selections = _values(
        [row for row in blocks if row.get("selection_id") is not None], "selection_id"
    )
    variants=[]
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
    return variants

def _answer_schema(variants, policy, rules, prose, *, proposal_labels=("invented_idea", "image_prompt")):
    variants.append(
        _object(
            {
                "kind": _literal("proposal"),
                "text": prose,
                "label": _enum(proposal_labels),
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
            **({"kind": _literal("rules_answer")} if isinstance(rules, ModelRulesFrame)
               else {"schema": _literal("dmb_rules_mixed_answer_v1")}),
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


def native_output_format(frame, rules, work_frame, *, build_local=False, format_version=2, execution=None):
    from .native_writer import SCHEMA, LEGACY_SCHEMA
    if type(format_version) is not int or format_version not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}:
        raise ValueError('Unknown native writer output format version')
    if (frame.get('schema') not in {SCHEMA, LEGACY_SCHEMA} or frame.get('answer_policy') != ASSERTION_POLICY
            or not isinstance(rules, (PlanRulesEvidenceFrameV1, ModelRulesFrame))):
        raise ValueError('Shared native output requires its actual evidence and Rules frames')
    if execution is not None:
        from .plan_contextual_questions import output_format as question_format
        question = question_format(execution)
        if question is not None:
            from .plan_jev_graph_packet import NATIVE_WORK_SCHEMA
            if rules.lookups or work_frame.get('schema') != NATIVE_WORK_SCHEMA or work_frame.get('requested_work') != 'clarify':
                raise ValueError('Question-only Plan work cannot carry a factual Rules answer')
            return question
    prose = {'type': 'string', 'minLength': 1}
    variants = _native_variants(ASSERTION_POLICY, prose,
        statement_rows=frame['native_statements']['statements'],
        body_rows=frame['native_body_evidence']['excerpts'],
        assertion_rows=frame['native_assertions']['assertions'] if frame['native_assertions'] is not None else ())
    from .plan_jev_graph_packet import NATIVE_WORK_SCHEMA as PLAN_WORK_SCHEMA
    from .build_primary_context import NATIVE_WORK_SCHEMA as BUILD_WORK_SCHEMA
    if work_frame.get('schema') == PLAN_WORK_SCHEMA:
        variants.extend(_authored_variants(work_frame,ASSERTION_POLICY,prose))
        related = work_frame.get('related_authored_pages', {}).get('pages', [])
        if related:
            variants.append(_object({'kind': _literal('related_page_claim'), 'text': prose,
                'read_id': _enum(_values(related, 'read_id')),
                'supporting_quotes': _array(prose, nonempty=True)}))
            if work_frame.get('citation_policy') == 'supplied_source_references_v1':
                claim = variants[-1]
                del claim['properties']['supporting_quotes']
                claim['required'].remove('supporting_quotes')
                claim['properties']['read_id']['description'] = ('Select the ONE supplied page supporting every factual clause. '
                    'Split claims from different pages into separate segments.')
    elif work_frame.get('schema') == 'dmb_native_play_work_v1':
        variants.extend(_authored_variants(work_frame,ASSERTION_POLICY,prose))
    elif work_frame.get('schema') == BUILD_WORK_SCHEMA:
        from .build_draft_answer import native_variants
        variants.extend(native_variants(work_frame,prose,local=build_local))
    else:
        raise ValueError('Shared output requires its actual supported work frame')
    schema=_answer_schema(variants,ASSERTION_POLICY,rules,prose,
        proposal_labels=("invented_idea", "image_prompt") if format_version == 1 else ("invented_idea",))
    if format_version == 7:
        if work_frame.get("schema") != BUILD_WORK_SCHEMA or not build_local or rules.lookups:
            raise ValueError("Discussion-only format requires Build discussion without Rules lookups")
        schema["properties"]["answer_segments"]["items"] = _object({
            "kind": _literal("discussion"), "text": prose,
        })
    if work_frame.get('schema')==BUILD_WORK_SCHEMA:
        from .build_intentional_response import native_review_enabled, native_review_schema
        if native_review_enabled(work_frame):
            review,definitions=native_review_schema(work_frame,local=build_local)
            destination = work_frame.get("build_work", {}).get("lore_page_destination")
            base=schema['$defs']['Base'] if rules.lookups else schema
            if destination is not None:
                from .lore_page_review import explicit_blank_lore_page

                definitions["LorePageTitleWitness"]["properties"]["title"]["enum"] = [destination["title"]]
                answer_segments = base["properties"]["answer_segments"]
                if explicit_blank_lore_page(destination["instruction"]):
                    answer_segments["maxItems"] = 0
                    review = review["anyOf"][0]
                else:
                    items = answer_segments["items"]
                    items["anyOf"] = [
                        variant for variant in items["anyOf"]
                        if variant["properties"]["kind"].get("const") in {"native_body_claim", "proposal"}
                    ]
            base['properties']['collaboration']=review
            base['required'].append('collaboration')
            if definitions:
                schema.setdefault('$defs',{}).update(definitions)
    if format_version in {3, 4, 5, 6, 8, 9, 10, 11}:
        from .native_build_work_view import variant_sources
        sources = variant_sources(work_frame)
        if rules.lookups or work_frame.get("schema") != BUILD_WORK_SCHEMA or not sources:
            raise ValueError("Variant writer format requires a grounded draft without Rules lookups")
        if sources:
            from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input

            from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import RuleElementInput

            model = RuleElementInput if format_version >= 4 else StatblockDefinitionV1Input
            mechanics = model.model_json_schema(ref_template="#/$defs/Variant_{model}")
            definitions = mechanics.pop("$defs", {})
            schema.setdefault("$defs", {}).update(
                {f"Variant_{name}": entry for name, entry in definitions.items()}
            )
            properties = {"source": _enum(list(sources))}
            if format_version in {6, 8, 9, 10, 11}:
                witnesses = _array({
                    **prose,
                    "description": "Quote the exact authored condition, including any exception.",
                })
                witnesses["description"] = (
                    "Select exact conditions from current_draft for this rule before drafting it. "
                    "Use an empty list for original design without authored conditions."
                )
                if "working_draft_context" not in work_frame:
                    witnesses["maxItems"] = 0
                fields = {}
                if format_version in {8, 9, 10, 11}:
                    fields["carried_condition"] = {
                        "type": ["string", "null"] if "working_draft_context" in work_frame else "null",
                        "description": (
                            "For an unchanged authored trigger, select its exact unique sentence "
                            "from current_draft. Buddy inserts it into the playable trigger and "
                            "displayed rule. Use null for original or explicitly changed conditions."
                        ),
                    }
                witness_field = "authored_quotes"
                if format_version == 11:
                    from .native_build_work_view import variant_draft_passages

                    witness_field = "authored_passages"
                    witnesses = _array(_enum(list(variant_draft_passages(work_frame))))
                mechanics = _object({**fields, witness_field: witnesses, "rule": mechanics})
                mechanics["description"] = (
                    "Pair section and activation.kind as follows: action → action; "
                    "bonus_action → bonus_action; reaction → reaction; "
                    "legendary_action → legendary; lair_action → lair_initiative. "
                    "Use passive, triggered, or special only with trait or regional_effect. "
                    "A rule governed by an ongoing situation or a scene trigger does not "
                    "consume a combat action unless its mechanics specify one."
                )
                if format_version in {8, 9, 10, 11}:
                    mechanics["description"] += (
                        " With carried_condition, provide a typed trigger and write only "
                        "consequences in rule.rules_text. Do not restate or add another trigger."
                    )
            if format_version in {9, 10, 11}:
                from .native_build_work_view import variant_draft_passages

                passages = variant_draft_passages(work_frame)
                if not passages:
                    raise ValueError("Variant passage review requires a nonempty authored draft")
                if format_version in {10, 11}:
                    review = _object({
                        handle: _enum(["retain", "change", "omit", "retain_trigger"]) for handle in passages
                    })
                    review["description"] = (
                        "Review every authored passage before drafting. Use retain_trigger for an existing "
                        "activation condition that governs these mechanics. Every retain_trigger requires "
                        "an exact carried_condition from that passage in its corresponding rule. "
                        "Retain other relevant effects and qualifications. Change only where the GM explicitly "
                        "asked to change that source behavior. Omit unrelated material."
                    )
                    fields["carried_condition"]["description"] = (
                        "Select the exact activation sentence from a retain_trigger passage. Keep every exception. "
                        "For this carried trigger, set activation.timing_text and activation.trigger.source_element_key "
                        "to null. Put consequences only in rules_text. Null here is for an original or explicitly "
                        "changed trigger."
                    )
                else:
                    review = _object({handle: _enum(["retain", "change", "omit"]) for handle in passages})
                    review["description"] = (
                        "Review each authored passage before drafting. Retain existing behavior needed "
                        "by the requested variant, including all trigger exceptions and consequences. "
                        "Change only where the GM asked for it. Omit unrelated material."
                    )
                    fields["carried_condition"]["description"] = (
                        "Select the exact source sentence from a retained passage for an existing trigger. "
                        "Use null for original or explicitly changed mechanics."
                    )
                witnesses["description"] = (
                    "Select passage handles for authored text that establishes this rule. "
                    "Use an empty list for original design." if format_version == 11 else
                    "Quote the exact authored passages that establish the retained effects of this rule."
                )
                properties = {"passage_review": review, **properties}
            if format_version >= 4:
                properties.update({
                    "add_rules": {"type": "array", "items": mechanics},
                    "replace_rules": {"type": "array", "items": mechanics},
                })
            else:
                properties["definition"] = mechanics
            schema["properties"]["statblock_variant"] = {
                "anyOf": [_object(properties), {"type": "null"}],
            }
            schema["required"].append("statblock_variant")
            if format_version >= 5:
                schema["properties"]["answer_segments"]["minItems"] = 1
    if work_frame.get('schema')==PLAN_WORK_SCHEMA and work_frame.get('requested_work')=='review_connected_page':
        from .collaboration import ProposedConnectedPage
        rows=work_frame.get('related_authored_pages',{}).get('pages',[])
        review={'type':'null'}
        if rows:
            proposal=ProposedConnectedPage.model_json_schema()
            proposal['properties']['read_id']={'type':'string','enum':_values(rows,'read_id')}
            review={'anyOf':[proposal,{'type':'null'}]}
        base=schema['$defs']['Base'] if rules.lookups else schema
        base['properties']['collaboration']=review
        base['required'].append('collaboration')
    if execution is not None:
        from .native_execution import NATIVE_PLAN_ACTION_TYPES
        from .plan_placement import PlanPlacementCatalogV2
        action = execution.policy.action
        if (isinstance(action, NATIVE_PLAN_ACTION_TYPES)
                and type(action.placement_catalog) is PlanPlacementCatalogV2
                and work_frame.get('schema') == PLAN_WORK_SCHEMA
                and work_frame.get('requested_work') == 'clarify'):
            base = schema['$defs']['Base'] if rules.lookups else schema
            base['properties']['answer_segments']['minItems'] = 1
    from generationengine.utils.schema_utils import make_schema_strict
    from .native_plan_work_view import SOURCE_REFERENCE_FORMAT, SOURCE_REFERENCE_POLICY
    plan_references = work_frame.get('schema') == PLAN_WORK_SCHEMA and work_frame.get('citation_policy') == SOURCE_REFERENCE_POLICY
    return {'type': 'json_schema', 'name': SOURCE_REFERENCE_FORMAT if plan_references else f'surface_native_evidence_selectors_v{format_version}', 'strict': True,
        'schema':make_schema_strict(schema)}


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
