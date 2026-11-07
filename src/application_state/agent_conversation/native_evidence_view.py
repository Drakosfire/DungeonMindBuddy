"""Provider-only World evidence; exact host reads remain the existing authority."""

from copy import deepcopy

FIELDS = frozenset(
    {
        "input_status",
        "user_question",
        "native_body_evidence",
        "native_statements",
        "native_assertions",
    }
)


def is_semantic_frame(frame):
    return isinstance(frame, dict) and set(frame) == FIELDS


def _domain_meaning(entries):
    """Separate the publisher's tagged host descriptor from semantic payload.

    native_recap_preparation._metadata owns this reserved, versioned descriptor.
    Do not match arbitrary keys/text or reinterpret admission/provenance here.
    """
    result = []
    for entry in entries:
        value = deepcopy(entry)
        if set(value) != {"schema", "payload"}:
            raise ValueError("Unclassified domain qualification envelope")
        payload = value["payload"]
        descriptor = (
            payload.get("candidate_description_selection")
            if isinstance(payload, dict)
            else None
        )
        if (
            value["schema"] == "dungeonbuddy.domain_metadata:world_context_v1"
            and isinstance(descriptor, dict)
            and descriptor.get("schema_version")
            == "dmb_candidate_description_extent_v1"
        ):
            del payload["candidate_description_selection"]
            if not payload:
                continue
        result.append(value)
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
            universal_absence_claimed=False,
        ),
    )


def output_frame(host, provider):
    """Transient shape for the existing output-schema owner, never sent as context."""
    return host | provider


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
