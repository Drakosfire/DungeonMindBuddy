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


def semantic_frame(host, *, project_managed_images=False, alias_campaign_scope=False):
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
    campaigns = set()
    if alias_campaign_scope:
        for row in statement_rows:
            campaign = row["payload"]["clause"]["campaign"]
            if campaign is not None:
                if not isinstance(campaign, str) or not campaign:
                    raise ValueError("Unclassified statement campaign identity")
                campaigns.add(campaign)
        for row in assertion_rows:
            for binding in row["assertion"]["metadata"]["scope"]:
                if binding.get("axis") == "dungeonbuddy.scope:campaign":
                    if set(binding) != {"axis", "value"} or not isinstance(binding["value"], str) or not binding["value"]:
                        raise ValueError("Unclassified campaign scope identity")
                    campaigns.add(binding["value"])
    campaign_aliases = {}
    alias_number = 0
    for campaign in sorted(campaigns):
        while f"campaign{alias_number}" in campaigns:
            alias_number += 1
        campaign_aliases[campaign] = f"campaign{alias_number}"
        alias_number += 1
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
        scope = deepcopy(metadata["scope"])
        if alias_campaign_scope:
            for binding in scope:
                if binding.get("axis") == "dungeonbuddy.scope:campaign":
                    binding["value"] = campaign_aliases[binding["value"]]
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
                                "epistemic_basis",
                                "claim_mode",
                                "standing",
                                "temporal_scope",
                            )
                        },
                        "scope": scope,
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
                    "campaign": (campaign_aliases[payload["clause"]["campaign"]]
                        if alias_campaign_scope and payload["clause"]["campaign"] is not None
                        else payload["clause"]["campaign"]),
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
    from .model_markdown import project_model_markdown

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
        if project_managed_images:
            bodies[-1]["text"] = project_model_markdown(row["text"])
        if "prior_claim" in row:
            bodies[-1]["prior_claim"] = row["prior_claim"]
        if "planning_line_ranges" in row:
            bodies[-1]["planning_line_ranges"] = deepcopy(row["planning_line_ranges"])
    body_evidence = dict(
        source_access=host["native_body_evidence"]["source_authority_status"],
        excerpts=bodies,
        universal_absence_claimed=False,
    )
    if any("planning_line_ranges" in body for body in bodies):
        body_evidence["planning_line_ranges_meaning"] = (
            "Inclusive source line ranges identify explicit recap planning. "
            "Use those lines as plans. Establish played events from their own evidence."
        )
    return dict(
        input_status=host["input_status"],
        user_question=host["user_question"],
        native_body_evidence=body_evidence,
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


def expected_semantic_frame(host, actual, *, project_managed_images=False, alias_campaign_scope=False):
    """Reconstruct retained producing bytes by their closed actual slot shape.

    Current producers always use semantic_frame. This reader does not try hashes
    or emit alternate prompts; original request and frame bindings remain exact.
    """
    expected = semantic_frame(host, project_managed_images=project_managed_images,
                              alias_campaign_scope=alias_campaign_scope)
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


PLAN_EVIDENCE_HEADING = "# Plan evidence\n\n"


def _recap_prose_key(row):
    if row.get("planning_line_ranges") or "prior_claim" in row:
        return None
    text = row["text"]
    lines = text.splitlines(keepends=True)
    # Only isolated trailing spaces in plain prose may compare as identical.
    # Keep indentation, Markdown hard breaks, code, and all source bytes intact.
    if not any(mark in text for mark in ("`", "<", "\\", "~~~")) and not any(
        line.startswith(("    ", "\t")) for line in lines
    ):
        text = "".join(
            line[:-2] + "\n"
            if line.endswith(" \n") and len(line) > 2 and not line[-3].isspace()
            else line for line in lines
        )
    return row["campaign_scope"], text


def render_plan_evidence(frame, work, *, compact_graph_qualifications=False, deduplicate_recap_prose=False):
    """Render the admitted evidence with the same aliases as the output schema."""
    def words(value):
        if isinstance(value, dict):
            return "; ".join(f"{key.replace('_', ' ')}: {words(item)}"
                             for key, item in sorted(value.items()) if item is not None)
        if isinstance(value, (list, tuple)):
            return "; ".join(words(item) for item in value)
        return str(value)

    parts = [PLAN_EVIDENCE_HEADING.rstrip()]
    if frame["input_status"] == "partial":
        parts.append("Some evidence was unavailable.")
    bodies = frame["native_body_evidence"]
    if bodies["source_access"] != "available":
        parts.append("Recap source access was limited.")
    sessions = {}
    for row in bodies["excerpts"]:
        sessions.setdefault((row["campaign_scope"], row["session_scope"]), []).append(row)
    first_passages = {}
    for (campaign, session), rows in sorted(
        sessions.items(), key=lambda entry: (str(entry[0][0]),
            entry[0][1] if isinstance(entry[0][1], int) else float("inf"))
    ):
        heading = f"Session {session}" if isinstance(session, int) else "Undated material"
        parts.append(f"## {campaign} · {heading}")
        for row in sorted(rows, key=lambda item: (item["source_name"], item["line_start"])):
            label = f"[{row['excerpt_handle']}] {row['source_name']}"
            planning = row.get("planning_line_ranges")
            if planning:
                ranges = ", ".join(f"{start}–{stop}" for start, stop in planning)
                label += f" (planning on source lines {ranges}; excerpt starts at line {row['line_start']})"
            prior = f"Earlier cited claim: {row['prior_claim']}\n" if "prior_claim" in row else ""
            key = _recap_prose_key(row) if deduplicate_recap_prose else None
            if key is not None:
                first = first_passages.setdefault(key, row["excerpt_handle"])
                if first != row["excerpt_handle"]:
                    parts.append(f"{label} · Same passage as [{first}].")
                    continue
            parts.append(f"{label}\n{prior}{row['text']}")
    statements = frame["native_statements"]["statements"]
    if statements:
        parts.append("## Recorded statements")
        for row in statements:
            parts.append(f"[{row['statement_handle']}] {words(row['payload'])}")
    graph = frame["native_assertions"]
    if graph and graph["assertions"]:
        parts.append("## Graph knowledge")
        groups = {}
        for row in graph["assertions"]:
            claim = row["assertion"]
            groups.setdefault(claim["qualification"], []).append(row)
        for qualification, rows in groups.items():
            rendered = graph["qualifications"][qualification]
            if compact_graph_qualifications:
                rendered = rendered.copy()
                if rendered.get("domain_metadata") == []:
                    del rendered["domain_metadata"]
                mode = rendered.get("claim_mode")
                if isinstance(mode, str):
                    rendered["claim_mode"] = mode.removeprefix("dungeonbuddy.claim:")
            parts.append(words(rendered))
            for row in rows:
                claim = row["assertion"]
                predicate = claim["predicate"].split(":")[-1].replace("_", " ")
                value = claim["value"]
                content = value.get("entity") if value["kind"] == "entity_ref" else words({
                    key: item for key, item in value.items() if key != "kind"
                })
                parts.append(f"[{row['assertion_handle']}] {claim['subject']} · {predicate} · {content}")
    def blocks(rows):
        for row in rows:
            handle = row.get("selection_id")
            parts.append(f"[{handle}] {row['text']}" if handle else row["text"])

    if work["committed_plan_blocks"]:
        parts.append("## Saved Plan")
        blocks(work["committed_plan_blocks"])
    for session in work["session_evidence"]:
        parts.append(f"## Authored session material · {session.get('title', 'Untitled session')}")
        for source in session["sources"]:
            parts.append(source["kind"])
            blocks(source["text_blocks"])
    if work["dialogue_reference"]:
        parts.append("## Prior dialogue")
        parts.extend(words(turn) for turn in work["dialogue_reference"])
    if work.get('citation_policy') == 'supplied_source_references_v1':
        parts.append('## Saved-page citations\nSelect the supplied local page reference. Do not regenerate supporting quotes.')
    for page in work.get("related_authored_pages", {}).get("pages", ()):
        parts.append(f"## Saved reference · [{page['read_id']}] {page['title']}\n{page['markdown']}")
    for key in ("current_page_draft", "focused_edit_target", "selected_references"):
        if work.get(key):
            parts.append(f"## {key.replace('_', ' ').capitalize()}\n{words(work[key])}")
    parts.extend(("# Question", frame["user_question"]))
    return "\n\n".join(parts)
