"""Admitted source → private proposals → explicit review → existing WK preparation."""

from hashlib import sha256

from dungeonmind.application.vnext import EntityReadService, open_admitted_native_text
from fastapi.encoders import jsonable_encoder

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from application_state.statement_proposals import service as store
from apps.live_control_server.models.source_statement_proposals import ProposalRequest
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from graph_memory.extraction.qualified_statement_proposals import (
    INSTRUCTIONS,
    ProposalBatch,
    canonical,
    digest,
    parse,
    strict_json,
)
from graph_memory.extraction.statement_source_catalog import CONTRACT, catalog

from . import source_statements as statements

MODEL = "gpt-6-luna"
SCHEMA_NAME = "qualified_source_propositions_v3"


def _provider_schema(frozen_schema):
    """Restore declared root generation order without relying on JSONB key order."""
    schema = strict_json(canonical(frozen_schema))
    required = schema.get("required")
    properties = schema.get("properties")
    if (
        schema.get("type") != "object"
        or required != ProposalBatch.model_json_schema()["required"]
        or not isinstance(properties, dict)
        or set(required) != set(properties)
    ):
        raise ValueError("Qualified producer root schema order differs")
    schema["properties"] = {key: properties[key] for key in required}
    return schema


def _producer_budget():
    from .agent_turn_service import _policy_request_budget

    budget = dict(_policy_request_budget())
    if budget["model"] != MODEL or budget["provider"] != "openai-api":
        raise ValueError("Unsupported qualified producer model")
    # Whole-source structured extraction uses the verified model output ceiling.
    # https://developers.openai.com/api/docs/models/gpt-6-luna
    return budget | {"outputReserveTokens": 128_000}


def _acquire(request, principal):
    require_native_graph_gm(principal)
    if not principal.subject:
        raise ValueError("Authenticated proposal owner required")
    bound = statements.native.binding(request.managed_world_id)
    if bound["managed_world_id"] != request.managed_world_id:
        raise ValueError("Managed World binding differs from request")
    repo = statements.native.repository()
    space = bound["native_world_id"]
    read, access, _, _ = statements._context(
        repo, space, request.read_revision_id, request.campaign_id
    )
    opened = open_admitted_native_text(access, request.evidence_ref_id)
    if opened.status != "available" or opened.body_sha256 != request.source_sha256:
        raise ValueError("Admitted source is unavailable or changed")
    raw = opened.body_text.encode()
    if sha256(raw).hexdigest() != request.source_sha256:
        raise ValueError("Authorized source body digest changed")
    logical, _anchor = statements._source(
        repo,
        space,
        access,
        {
            "source_admission_id": request.source_admission_id,
            "evidence_ref_id": request.evidence_ref_id,
        },
        request.source_sha256,
        opened.span_start_byte,
        opened.span_end_byte,
        opened.span_sha256,
    )
    body = opened.body_text
    identities = []
    for entity_id in sorted(read.parsed.entities_by_id):
        admitted = EntityReadService().get_entity(read, entity_id)
        names = [a for a in admitted.assertions if a.predicate == "dnd5e:name"]
        if admitted.found and names:
            identities.append(
                {
                    "entity": jsonable_encoder(admitted.entity),
                    "name_assertions": jsonable_encoder(names),
                    "completeness": jsonable_encoder(admitted.completeness),
                }
            )
    snapshot = repo.get_revision(space, request.read_revision_id)
    authority = {
        "binding": {
            key: bound[key]
            for key in ("managed_world_id", "native_world_id", "binding_version")
        },
        "domain": jsonable_encoder(snapshot.revision.domain_contract_ref),
        "profile": jsonable_encoder(snapshot.revision.semantic_profile_ref),
    }
    packet = {
        "source": body,
        "logical_source": logical,
        "authority": authority,
        "world_identity_context": {
            "kind": "authorized_native_name_context",
            "coverage": "not_semantic_completeness",
            "entities": identities,
        },
        "scope": request.model_dump(mode="json", exclude={"operation_id"}),
    }
    extent = {
        "start_byte": opened.span_start_byte,
        "end_byte": opened.span_end_byte,
        "span_sha256": opened.span_sha256,
    }
    return repo, space, packet, extent


def _render(material):
    identity = {key: material[key] for key in ("logical_source", "authority", "scope")}
    return {key: value for key, value in material.items() if key != "source"} | {
        "contract": CONTRACT,
        "source_catalog": catalog(material["source"], identity),
        "output_schema": ProposalBatch.model_json_schema(),
    }


def source(request, principal, *, include_extent=False):
    repo, space, material, extent = _acquire(request, principal)
    packet = _render(material)
    return (repo, space, packet, extent) if include_extent else (repo, space, packet)


def _view(record, extent):
    eligibility = {}
    if record["result"] is not None:
        for key, passages in record["result"]["passages"].items():
            candidates = [
                {
                    "unit_id": unit["unit_id"],
                    "start_byte": max(unit["start_byte"], extent["start_byte"]),
                    "end_byte": min(unit["end_byte"], extent["end_byte"]),
                }
                for unit in passages["primary"]
                if max(unit["start_byte"], extent["start_byte"])
                < min(unit["end_byte"], extent["end_byte"])
            ]
            eligibility[key] = {
                "status": "requires_explicit_clause_selection"
                if candidates
                else "outside_registered_evidence",
                "candidate_extents": candidates,
                "semantic_acceptance": "not_established",
            }
    return {**record, "review_eligibility": eligibility}


def get(operation_id, world, principal):
    require_native_graph_gm(principal)
    record = store.read(operation_id, principal.subject, world)
    if record is None:
        raise ApplicationStateNotFoundError("Proposal operation is unavailable")
    request = ProposalRequest.model_validate_json(canonical(record["intent"]))
    _, _, material, extent = _acquire(request, principal)
    saved = record["input"]
    if record["state"] == "failed":
        if "contract" not in saved:
            valid = set(saved) == set(material) | {"output_schema"} and all(
                saved[key] == value for key, value in material.items()
            )
        elif saved["contract"] in {"qualified_source_handles_v2", CONTRACT}:
            identity = {
                key: material[key] for key in ("logical_source", "authority", "scope")
            }
            valid = (
                set(saved)
                == (set(material) - {"source"})
                | {"contract", "source_catalog", "output_schema"}
                and all(
                    saved[key] == value
                    for key, value in material.items()
                    if key != "source"
                )
                and saved["source_catalog"] == catalog(material["source"], identity)
            )
        else:
            valid = False
        if not valid or not isinstance(saved.get("output_schema"), dict):
            raise ValueError("Retained failed proposal source correspondence changed")
    elif saved != _render(material):
        raise ValueError("Retained proposal source correspondence changed")
    if record["wire"] is not None:
        if strict_json(record["wire"]).get("input") != [
            {"role": "user", "content": canonical(saved)}
        ]:
            raise ValueError("Retained proposal wire/input correspondence changed")
    if (
        record["state"] == "completed"
        and parse(record["raw_output"], saved["source_catalog"]) != record["result"]
    ):
        raise ValueError("Retained proposal output changed")
    return _view(record, extent)


async def produce(request, principal, *, transport=None):
    require_native_graph_gm(principal)
    if not principal.subject:
        raise ValueError("Authenticated proposal owner required")
    old = store.read(request.operation_id, principal.subject, request.managed_world_id)
    if old is not None:
        if old["intent"] != request.model_dump(mode="json"):
            raise ApplicationStateConflictError("Proposal key has a different intent")
        return get(request.operation_id, request.managed_world_id, principal)
    _, _, packet, extent = source(request, principal, include_extent=True)
    record, fresh = store.claim(
        request.operation_id, principal.subject, request.model_dump(mode="json"), packet
    )
    if not fresh:
        return get(request.operation_id, request.managed_world_id, principal)
    from generationengine import GenerationClient, TextRequest
    from generationengine.text_dispatch import TextDispatchGate
    from generationengine.utils.schema_utils import make_schema_strict

    from .plan_jev_writer import PlanWriterProvider

    provider_schema = None
    output_format = None
    messages = [{"role": "user", "content": canonical(packet)}]
    prepared_request = None
    raw_output = None

    async def authorize(prepared):
        nonlocal record, prepared_request
        if prepared_request is not None:
            raise ValueError("One proposal dispatch only")
        if (
            prepared.provider,
            prepared.model,
            prepared.api_mode,
            prepared.method,
            prepared.url,
        ) != (
            "openai",
            MODEL,
            "responses",
            "POST",
            "https://api.openai.com/v1/responses",
        ):
            raise ValueError("Proposal transport differs")
        wire = prepared.body.decode()
        body = strict_json(wire)
        if (
            len(prepared.body) != prepared.body_size
            or sha256(prepared.body).hexdigest() != prepared.body_sha256
            or body.get("model") != MODEL
            or body.get("input") != messages
            or body.get("instructions") != INSTRUCTIONS
            or body.get("text") != {"format": output_format}
            or list(body["text"]["format"]["schema"]["properties"])
            != list(provider_schema["properties"])
            or body.get("tools")
            or body.get("max_output_tokens") != budget["outputReserveTokens"]
        ):
            raise ValueError("Prepared proposal request differs")
        from application_state.agent_conversation.native_statement_input import (
            native_input_tokens,
        )

        if (
            len(prepared.body) > budget["maxProviderRequestBytes"]
            or native_input_tokens(wire, body) + budget["outputReserveTokens"]
            > budget["contextLimitTokens"]
        ):
            raise ValueError(
                "Complete proposal input exceeds the verified model envelope"
            )
        record = store.change(record, state="entered", wire=wire)
        prepared_request = prepared
        return True

    async def lifecycle(event):
        nonlocal record
        if prepared_request is None or event.request != prepared_request:
            raise ValueError("Proposal lifecycle differs from prepared request")
        record = store.change(
            record, event={"outcome": event.outcome, "http_status": event.http_status}
        )
        return True

    provider = client = None
    budget = None
    try:
        budget = _producer_budget()
        # JSONB preserves the explicit required array, unlike object-key order.
        provider_schema = _provider_schema(packet["output_schema"])
        output_format = {
            "type": "json_schema",
            "name": SCHEMA_NAME,
            "schema": make_schema_strict(provider_schema),
            "strict": True,
        }
        provider = PlanWriterProvider(
            dispatch_gate=TextDispatchGate(authorize, lifecycle), transport=transport
        )
        client = GenerationClient(text_providers={"openai": provider})
        result = await client.generate_structured(
            TextRequest(
                provider="openai",
                model=MODEL,
                user_prompt=canonical(messages),
                system_prompt=INSTRUCTIONS,
                temperature=None,
                reasoning_effort="none",
                max_output_tokens=budget["outputReserveTokens"],
                json_schema=provider_schema,
                schema_name=SCHEMA_NAME,
                max_conformance_retries=0,
                max_transport_retries=0,
            )
        )
        response = provider.actual_response
        if response is not None:
            raw_output = canonical(response.model_dump(mode="json"))
        if (
            response is None
            or response.status != "completed"
            or response.model != MODEL
        ):
            raise ValueError("Proposal provider did not complete")
        raw_output = provider.consume_selected_text(response)
        for item in response.output:
            if item.type == "reasoning":
                continue
            if (
                item.type != "message"
                or item.role != "assistant"
                or item.status != "completed"
                or any(part.type != "output_text" for part in item.content)
            ):
                raise ValueError("Proposal response contains unsupported content")
        if (
            result.text != raw_output
            or result.observation.provider_attempt_count != 1
            or result.observation.retry_count != 0
        ):
            raise ValueError(
                "Proposal response does not match original provider output"
            )
        if source(request, principal)[2] != packet:
            raise ValueError("Source authority changed during proposal generation")
        record = store.change(
            record,
            state="completed",
            raw_output=raw_output,
            result=parse(raw_output, packet["source_catalog"]),
        )
        return _view(record, extent)
    except Exception:
        if (
            raw_output is None
            and provider is not None
            and provider.actual_response is not None
        ):
            raw_output = canonical(provider.actual_response.model_dump(mode="json"))
        # An entered failed operation remains non-retryable. No invented completion.
        if record["state"] in {"claimed", "entered"}:
            record = store.change(
                record,
                state="failed",
                raw_output=raw_output,
                failure="proposal_generation_failed_after_entry"
                if prepared_request
                else "proposal_generation_not_dispatched",
            )
        return _view(record, extent)
    finally:
        if client is not None:
            await client.aclose()


def _ancestry(repo, space, original, selected):
    seen, cursor = set(), selected
    while cursor is not None:
        if cursor == original:
            return
        if cursor in seen:
            raise ValueError("Native ancestry cycle")
        seen.add(cursor)
        snapshot = repo.get_revision(space, cursor)
        if snapshot is None:
            break
        cursor = snapshot.revision.parent_revision_id
    raise ValueError("Review parent does not descend from extraction revision")


def review(operation_id, world, request, principal):
    record = get(operation_id, world, principal)
    intent = {
        "proposal_id": request.proposal_id,
        "selection": request.selection.model_dump(
            mode="json",
            exclude={"source_evidence_extension_id"}
            if request.selection.source_evidence_extension_id is None else set(),
        ),
    }
    key, fingerprint = str(request.decision_id), digest(intent)
    old = next((r for r in record["reviews"] if r["decision_id"] == key), None)
    if old:
        if old["intent_digest"] != fingerprint:
            raise ApplicationStateConflictError("Review key has a different decision")
        return old
    if (
        record["state"] != "completed"
        or record["revision"] != request.expected_revision
    ):
        raise ApplicationStateConflictError(
            "Review revision is stale or proposals unavailable"
        )
    extraction = ProposalRequest.model_validate_json(canonical(record["intent"]))
    selected = request.selection
    for field in (
        "managed_world_id",
        "campaign_id",
        "source_sha256",
    ):
        if getattr(extraction, field) != getattr(selected, field):
            raise ValueError("Review changed the extraction source/scope")
    proposal = next(
        (
            p
            for p in record["result"]["batch"]["proposals"]
            if p["proposal_id"] == request.proposal_id
        ),
        None,
    )
    if proposal is None:
        raise ValueError("Unknown source proposal")
    repo, space, material, _ = _acquire(extraction, principal)
    if selected.source_evidence_extension_id is None:
        if (selected.source_admission_id, selected.evidence_ref_id) != (
            extraction.source_admission_id, extraction.evidence_ref_id,
        ):
            raise ValueError("Review changed the extraction source proof")
    else:
        extension = repo.get_native_source_evidence_extension_receipt(
            space, selected.source_evidence_extension_id
        )
        root = repo.get_native_source_admission_receipt(space, extraction.source_admission_id)
        if (
            extension is None or root is None
            or extension.original_admission_id != extraction.source_admission_id
            or extension.source_artifact_id != root.source_artifact_id
            or extension.source_revision_id != root.source_revision_id
        ):
            raise ValueError("Review extension belongs to another original source")
        # This relation is necessary, never sufficient: statements.prepare below
        # authenticates Core's root fingerprint/publication, current access,
        # extension membership and exact selected source bytes before any review save.
    raw = material["source"].encode("utf-8")
    if not any(
        unit["start_byte"]
        <= selected.start_byte
        < selected.end_byte
        <= unit["end_byte"]
        for unit in record["result"]["passages"][request.proposal_id]["primary"]
    ):
        raise ValueError("Reviewed clause must be contained in one primary source unit")
    clause = raw[selected.start_byte : selected.end_byte]
    clause.decode("utf-8")
    if sha256(clause).hexdigest() != selected.clause_sha256:
        raise ValueError("Reviewed clause digest differs from exact source bytes")
    _ancestry(
        repo, space, extraction.read_revision_id, selected.expected_parent_revision_id
    )
    packet = jsonable_encoder(statements.prepare(selected, principal))
    decision = {
        "decision_id": key,
        "intent": intent,
        "intent_digest": fingerprint,
        "prepared_packet": packet,
        "packet_digest": digest(packet),
    }
    saved = store.change(record, review=decision)
    return next(r for r in saved["reviews"] if r["decision_id"] == key)
