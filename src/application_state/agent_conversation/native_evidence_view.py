"""Provider-only World evidence; exact host reads remain the existing authority."""

from copy import deepcopy
import json

FIELDS = frozenset(
    {
        "input_status",
        "user_question",
        "native_body_evidence",
        "native_statements",
        "native_assertions",
    }
)


# Prompt presentation only, never source/publication admissibility. Historical
# Buddy reviewed World-context entries mixed these host provenance slots into
# otherwise arbitrary JSON. Their exact top-level roles are explicit here; no
# key patterns, value heuristics or recursive stripping apply. Unknown keys,
# qualifications, literal bodies and all other metadata schemas stay intact.
_WORLD_CONTEXT = "dungeonbuddy.domain_metadata:world_context_v1"
_WORLD_CONTEXT_HOST_FIELDS = frozenset({
    'actual_extraction_candidate_sha256',
    'actual_extraction_run_id',
    'identity_readiness_review_sha256',
    'identity_readiness_sha256',
    'identity_review_sha256',
    'ingestion_code_head',
    'ingestion_model',
    'ingestion_profile',
    'ingestion_runtime_manifest_sha256',
    'ingestion_telemetry_sha256',
    'owner_identity_adoption_sha256',
    'publication_fidelity_review_sha256',
    'publication_runtime_manifest_sha256',
    'selected_field_decisions_sha256',
    'semantic_correction_basis_sha256',
    'source_candidate_sha256',
    'source_effective_sha256',
    'source_identity_adoption_sha256',
    'source_identity_selection_proposal_sha256',
    'source_original_sha256',
    'source_qualifier_adjudication_sha256',
    'source_read_mode',
    'source_run_id',
    'source_run_revision',
    'source_selection_feasibility_sha256',
    'source_selector',
})


def is_semantic_frame(frame):
    return isinstance(frame, dict) and set(frame) == FIELDS


def acquired_records(receipt, execution):
    """Reuse the admitted semantic record view; never open or expose source bodies.

    Callers must supply the prefix preceding the controller authorization. This
    projection grants neither navigation handles nor additional evidence credit.
    """
    from .native_writer import model_input_frame

    frame = model_input_frame(receipt, execution)
    return {key: frame[key] for key in ("native_statements", "native_assertions")}


def _domain_meaning(entries):
    """Present semantic meaning without changing its exact admitted host record.

    The current publisher's reserved descriptor and known older reviewer-supplied
    provenance slots are host information. This presentation rule never admits,
    rejects or substantiates a source, citation or publication decision.
    """
    result = []
    for entry in entries:
        value = deepcopy(entry)
        if set(value) != {"schema", "payload"}:
            raise ValueError("Unclassified domain qualification envelope")
        payload = value["payload"]
        if value["schema"] == _WORLD_CONTEXT and isinstance(payload, dict):
            payload = {key: item for key, item in payload.items()
                       if key not in _WORLD_CONTEXT_HOST_FIELDS}
            if not payload and value["payload"]:
                continue
            value["payload"] = payload
        descriptor = (
            payload.get("candidate_description_selection")
            if isinstance(payload, dict)
            else None
        )
        if (
            value["schema"] == _WORLD_CONTEXT
            and isinstance(descriptor, dict)
            and descriptor.get("schema_version")
            == "dmb_candidate_description_extent_v1"
        ):
            del payload["candidate_description_selection"]
            if not payload:
                continue
        # The reserved discriminator belongs to the host's domain contract.
        # Keep its meaning, including arbitrary literal/non-object payloads.
        result.append({"world_context": payload} if value["schema"] == _WORLD_CONTEXT else value)
    return result


def semantic_frame(host):
    """Explicit projection of an owner-reconstructed current native host frame.

    Literal/domain payloads are context and never recursively scrubbed. Only typed
    identity fields become local addresses; host input acceptance rederives this
    entire projection from admitted records before trusting any model selector.
    """
    if host.get("schema") != "dmb_surface_native_writer_evidence_v2":
        raise ValueError("Semantic native evidence requires its current host frame")
    statement_rows = host["native_statements"]["statements"]
    assertion_rows = (
        host["native_assertions"]["assertions"]
        if host["native_assertions"] is not None
        else []
    )
    identities = set()
    for row in statement_rows:
        payload = row["payload"]
        if payload["reporter"] is not None:
            identities.add(payload["reporter"])
        identities.update(payload["referents"])
    for row in assertion_rows:
        value = row["assertion"]
        identities.add(value["subject_entity_id"])
        if value["value"]["kind"] == "entity_ref":
            identities.add(value["value"]["entity_id"])
    entities = {identity: f"entity{i}" for i, identity in enumerate(sorted(identities))}
    assertions = []
    qualifications = {}
    qualification_aliases = {}
    for i, row in enumerate(assertion_rows):
        assertion = row["assertion"]
        value = deepcopy(assertion["value"])
        metadata = assertion["metadata"]
        if set(metadata) != {
            "scope",
            "visibility",
            "epistemic_basis",
            "claim_mode",
            "standing",
            "evidence_ref_ids",
            "temporal_scope",
            "domain_metadata",
        }:
            raise ValueError(
                "Unclassified assertion qualification in semantic projection"
            )
        if value["kind"] == "entity_ref":
            value = {"kind": "entity_ref", "entity": entities[value["entity_id"]]}
        assertions.append(
            dict(
                assertion_handle=f"assertion{i}",
                assertion=dict(
                    subject=entities[assertion["subject_entity_id"]],
                    predicate=assertion["predicate"],
                    value=value,
                    metadata={
                        **{
                            key: deepcopy(metadata[key])
                            for key in (
                                "scope",
                                "epistemic_basis",
                                "claim_mode",
                                "standing",
                                "temporal_scope",
                            )
                        },
                        "domain_metadata": _domain_meaning(metadata["domain_metadata"]),
                    },
                ),
            )
        )
        presented = assertions[-1]['assertion']
        metadata = presented.pop('metadata')
        key = json.dumps(metadata, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False)
        if key not in qualification_aliases:
            alias = f'qualification{len(qualification_aliases)}'
            qualification_aliases[key] = alias
            qualifications[alias] = metadata
        presented['qualification'] = qualification_aliases[key]
    statements = []
    for i, row in enumerate(statement_rows):
        payload = row["payload"]
        if set(payload) != {
            "schema",
            "clause",
            "quote",
            "meaning",
            "mode",
            "reporter",
            "referents",
            "uncertainty",
            "qualifications",
            "episode",
            "source_order",
            "embedded_content_factive",
            "assertion_target",
            "visibility",
            "proof",
        }:
            raise ValueError("Unclassified statement meaning in semantic projection")
        # Source-order coordinates express source order, never fiction chronology.
        order = [
            {
                key: item[key]
                for key in ("before_start", "before_end", "after_start", "after_end")
            }
            for item in payload["source_order"]
        ]
        statements.append(
            dict(
                statement_handle=f"statement{i}",
                payload={
                    **{
                        key: deepcopy(payload[key])
                        for key in (
                            "quote",
                            "meaning",
                            "mode",
                            "uncertainty",
                            "qualifications",
                            "episode",
                            "embedded_content_factive",
                            "assertion_target",
                        )
                    },
                    "campaign": payload["clause"]["campaign"],
                    "reporter": entities[payload["reporter"]]
                    if payload["reporter"] is not None
                    else None,
                    "referents": [
                        entities[identity] for identity in payload["referents"]
                    ],
                    "source_order": order,
                },
            )
        )
    bodies = []
    for i, row in enumerate(host["native_body_evidence"]["excerpts"]):
        bodies.append(
            dict(
                excerpt_handle=f"body{i}",
                **{
                    key: deepcopy(row[key])
                    for key in (
                        "source_name",
                        "section_title",
                        "extent_kind",
                        "line_start",
                        "line_end",
                        "campaign_scope",
                        "session_scope",
                        "text",
                    )
                },
            )
        )
    return dict(
        input_status=host["input_status"],
        user_question=host["user_question"],
        native_body_evidence=dict(
            source_access=host["native_body_evidence"]["source_authority_status"],
            excerpts=bodies,
            universal_absence_claimed=False,
        ),
        native_statements=dict(
            status=host["native_statements"]["status"],
            statements=statements,
            universal_absence_claimed=False,
        ),
        native_assertions=None
        if host["native_assertions"] is None
        else dict(
            status=host["native_assertions"]["status"],
            assertions=assertions,
            qualifications=qualifications,
            universal_absence_claimed=False,
        ),
    )


def output_frame(host, provider):
    """Transient shape for the existing output-schema owner, never sent as context."""
    return host | _inline_qualifications(provider)


def _inline_qualifications(frame):
    """Resolve a closed dictionary presentation without granting evidence credit.

    Inline frames are retained historical requests. Current producers always
    emit the dictionary; exact host reconstruction still owns input admission.
    """
    collection = frame.get('native_assertions')
    if collection is None or 'qualifications' not in collection:
        return frame
    definitions = collection['qualifications']
    if not isinstance(definitions, dict):
        raise ValueError('Malformed context qualification dictionary')
    rows, used = [], set()
    for row in collection['assertions']:
        assertion = row['assertion']
        alias = assertion.get('qualification')
        if (not isinstance(alias, str) or alias not in definitions
                or 'metadata' in assertion or not isinstance(definitions[alias], dict)):
            raise ValueError('Unbound context qualification')
        used.add(alias)
        expanded = {key: value for key, value in assertion.items() if key != 'qualification'}
        rows.append(row | {'assertion': expanded | {'metadata': definitions[alias]}})
    if used != set(definitions):
        raise ValueError('Unused context qualification')
    return frame | {'native_assertions': {
        key: value for key, value in collection.items() if key != 'qualifications'
    } | {'assertions': rows}}


def semantic_frame_in_request(body, *, legacy_schemas):
    """Read only top-level host-assembled message JSON, never nested source text."""
    from .source_writer_output import strict_json

    candidates = []
    legacy_count = 0
    for message in body.get("input", []) if isinstance(body.get("input"), list) else []:
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            continue
        try:
            value = strict_json(message["content"])
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        if value.get("schema") in legacy_schemas:
            legacy_count += 1
            continue
        if {
            "native_body_evidence",
            "native_statements",
            "native_assertions",
        }.intersection(value):
            if not is_semantic_frame(value):
                raise ValueError("Malformed semantic native evidence frame")
            if message.get("role") != "user":
                raise ValueError("Semantic native evidence must remain user data")
            candidates.append(value)
    if len(candidates) > 1 or candidates and legacy_count:
        raise ValueError("Ambiguous semantic native evidence frame")
    return candidates[0] if candidates else None


def world_context_representation(frame):
    """Classify only declared qualification slots, never nested source text."""
    forms = set()
    try:
        collection = _inline_qualifications(frame)["native_assertions"]
        rows = collection["assertions"] if collection is not None else []
        for row in rows:
            for entry in row["assertion"]["metadata"]["domain_metadata"]:
                if not isinstance(entry, dict):
                    raise ValueError("Malformed domain qualification")
                if entry.get("schema") == _WORLD_CONTEXT:
                    if set(entry) != {"schema", "payload"}:
                        raise ValueError("Malformed historical World qualification")
                    forms.add("historical")
                elif "world_context" in entry:
                    if set(entry) != {"world_context"}:
                        raise ValueError("Malformed semantic World qualification")
                    forms.add("current")
    except (KeyError, TypeError) as exc:
        raise ValueError("Malformed native qualification frame") from exc
    if len(forms) > 1:
        raise ValueError("Mixed historical and current World qualifications")
    return next(iter(forms), "current")


def expected_semantic_frame(host, actual):
    """Reconstruct retained producing bytes by their closed actual slot shape.

    Current producers always use semantic_frame. This reader does not try hashes
    or emit alternate prompts; original request and frame bindings remain exact.
    """
    expected = semantic_frame(host)
    actual_collection = actual.get('native_assertions')
    if actual_collection is not None and 'qualifications' not in actual_collection:
        expected = _inline_qualifications(expected)
    if world_context_representation(actual) == "historical":
        expected = _inline_qualifications(expected)
        collection = expected["native_assertions"]
        for row in collection["assertions"] if collection is not None else []:
            entries = row["assertion"]["metadata"]["domain_metadata"]
            for index, entry in enumerate(entries):
                if set(entry) == {"world_context"}:
                    entries[index] = {"schema": _WORLD_CONTEXT, "payload": entry["world_context"]}
    return expected
