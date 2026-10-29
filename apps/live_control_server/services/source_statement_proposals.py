"""Admitted source → private proposals → explicit review → existing WK preparation."""
from hashlib import sha256
from fastapi.encoders import jsonable_encoder
from dungeonmind.application.vnext import open_admitted_native_text, EntityReadService
from application_state.statement_proposals import service as store
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from graph_memory.extraction.qualified_statement_proposals import (
    canonical, digest, strict_json, parse, ProposalBatch, INSTRUCTIONS,
)
from apps.live_control_server.models.source_statement_proposals import ProposalRequest
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm
from . import source_statements as statements

MODEL = "gpt-6-luna"


def _producer_budget():
    from .agent_turn_service import _policy_request_budget
    budget = dict(_policy_request_budget())
    if budget["model"] != MODEL or budget["provider"] != "openai-api":
        raise ValueError("Unsupported qualified producer model")
    # Whole-source structured extraction uses the verified model output ceiling.
    # https://developers.openai.com/api/docs/models/gpt-6-luna
    return budget | {"outputReserveTokens": 128_000}


def source(request, principal, *, include_extent=False):
    require_native_graph_gm(principal)
    if not principal.subject:
        raise ValueError("Authenticated proposal owner required")
    bound = statements.native.binding(request.managed_world_id)
    if bound["managed_world_id"] != request.managed_world_id:
        raise ValueError("Managed World binding differs from request")
    repo = statements.native.repository()
    space = bound["native_world_id"]
    read, access, _, _ = statements._context(repo, space, request.read_revision_id, request.campaign_id)
    opened = open_admitted_native_text(access, request.evidence_ref_id)
    if opened.status != "available" or opened.body_sha256 != request.source_sha256:
        raise ValueError("Admitted source is unavailable or changed")
    raw = opened.body_text.encode()
    if sha256(raw).hexdigest() != request.source_sha256:
        raise ValueError("Authorized source body digest changed")
    logical, _anchor = statements._source(repo, space, access,
        {"source_admission_id": request.source_admission_id, "evidence_ref_id": request.evidence_ref_id},
        request.source_sha256, opened.span_start_byte, opened.span_end_byte, opened.span_sha256)
    body = opened.body_text
    identities = []
    for entity_id in sorted(read.parsed.entities_by_id):
        admitted = EntityReadService().get_entity(read, entity_id)
        names = [a for a in admitted.assertions if a.predicate == "dnd5e:name"]
        if admitted.found and names:
            identities.append({"entity": jsonable_encoder(admitted.entity),
                               "name_assertions": jsonable_encoder(names),
                               "completeness": jsonable_encoder(admitted.completeness)})
    snapshot = repo.get_revision(space, request.read_revision_id)
    authority = {"binding": {key: bound[key] for key in ("managed_world_id", "native_world_id", "binding_version")},
                 "domain": jsonable_encoder(snapshot.revision.domain_contract_ref),
                 "profile": jsonable_encoder(snapshot.revision.semantic_profile_ref)}
    packet = {"source": body, "logical_source": logical, "authority": authority,
                        "world_identity_context": {"kind": "authorized_native_name_context",
                           "coverage": "not_semantic_completeness", "entities": identities},
                        "scope": request.model_dump(mode="json", exclude={"operation_id"}),
                        "output_schema": ProposalBatch.model_json_schema()}
    extent = {"start_byte": opened.span_start_byte, "end_byte": opened.span_end_byte,
              "span_sha256": opened.span_sha256}
    return (repo, space, packet, extent) if include_extent else (repo, space, packet)


def _view(record, extent):
    eligibility = {}
    if record["result"] is not None:
        for key, location in record["result"]["locations"].items():
            matches = [{**match, "eligibility": "eligible_for_review" if
                extent["start_byte"] <= match["start_byte"] < match["end_byte"] <= extent["end_byte"]
                else "outside_registered_evidence"} for match in location["matches"]]
            eligibility[key] = {"status": "ambiguous" if len(matches) != 1 else matches[0]["eligibility"],
                                "matches": matches, "semantic_acceptance": "not_established"}
    return {**record, "review_eligibility": eligibility}


def get(operation_id, world, principal):
    require_native_graph_gm(principal)
    record = store.read(operation_id, principal.subject, world)
    if record is None:
        raise ApplicationStateNotFoundError("Proposal operation is unavailable")
    request = ProposalRequest.model_validate_json(canonical(record["intent"]))
    _, _, packet, extent = source(request, principal, include_extent=True)
    if packet != record["input"]:
        raise ValueError("Retained proposal source correspondence changed")
    if record["state"] == "completed" and parse(record["raw_output"], packet["source"]) != record["result"]:
        raise ValueError("Retained proposal output changed")
    return _view(record, extent)


async def produce(request, principal, *, transport=None):
    _, _, packet, extent = source(request, principal, include_extent=True)
    record, fresh = store.claim(request.operation_id, principal.subject,
                                request.model_dump(mode="json"), packet)
    if not fresh:
        return get(request.operation_id, request.managed_world_id, principal)
    from generationengine import GenerationClient, TextRequest
    from generationengine.text_dispatch import TextDispatchGate
    from .plan_jev_writer import PlanWriterProvider
    messages = [{"role": "user", "content": canonical(packet)}]
    prepared_request = None
    raw_output = None

    async def authorize(prepared):
        nonlocal record, prepared_request
        if prepared_request is not None:
            raise ValueError("One proposal dispatch only")
        if (prepared.provider, prepared.model, prepared.api_mode, prepared.method, prepared.url) != (
            "openai", MODEL, "responses", "POST", "https://api.openai.com/v1/responses"):
            raise ValueError("Proposal transport differs")
        wire = prepared.body.decode()
        body = strict_json(wire)
        if (len(prepared.body) != prepared.body_size or sha256(prepared.body).hexdigest() != prepared.body_sha256
            or body.get("model") != MODEL or body.get("input") != messages
            or body.get("instructions") != INSTRUCTIONS or body.get("tools")
            or body.get("max_output_tokens") != budget["outputReserveTokens"]):
            raise ValueError("Prepared proposal request differs")
        from application_state.agent_conversation.native_statement_input import native_input_tokens
        if len(prepared.body) > budget["maxProviderRequestBytes"] or native_input_tokens(wire, body) + budget["outputReserveTokens"] > budget["contextLimitTokens"]:
            raise ValueError("Complete proposal input exceeds the verified model envelope")
        record = store.change(record, state="entered", wire=wire)
        prepared_request = prepared
        return True

    async def lifecycle(event):
        nonlocal record
        if prepared_request is None or event.request != prepared_request:
            raise ValueError("Proposal lifecycle differs from prepared request")
        record = store.change(record, event={"outcome": event.outcome, "http_status": event.http_status})
        return True

    provider = client = None
    budget = None
    try:
        budget = _producer_budget()
        provider = PlanWriterProvider(dispatch_gate=TextDispatchGate(authorize, lifecycle), transport=transport)
        client = GenerationClient(text_providers={"openai": provider})
        result = await client.generate_text(TextRequest(
            provider="openai", model=MODEL, user_prompt=canonical(messages),
            system_prompt=INSTRUCTIONS, temperature=None, reasoning_effort="none",
            max_output_tokens=budget["outputReserveTokens"], max_conformance_retries=0, max_transport_retries=0))
        response = provider.actual_response
        if response is not None:
            raw_output = canonical(response.model_dump(mode="json"))
        if response is None or response.status != "completed" or response.model != MODEL:
            raise ValueError("Proposal provider did not complete")
        raw_output = provider.consume_selected_text(response)
        for item in response.output:
            if item.type == "reasoning":
                continue
            if item.type != "message" or item.role != "assistant" or item.status != "completed" or any(
                part.type != "output_text" for part in item.content):
                raise ValueError("Proposal response contains unsupported content")
        if result.text != raw_output or result.observation.provider_attempt_count != 1 or result.observation.retry_count != 0:
            raise ValueError("Proposal response does not match original provider output")
        if source(request, principal)[2] != packet:
            raise ValueError("Source authority changed during proposal generation")
        record = store.change(record, state="completed", raw_output=raw_output,
                              result=parse(raw_output, packet["source"]))
        return _view(record, extent)
    except Exception:
        if raw_output is None and provider is not None and provider.actual_response is not None:
            raw_output = canonical(provider.actual_response.model_dump(mode="json"))
        # An entered failed operation remains non-retryable. No invented completion.
        if record["state"] in {"claimed", "entered"}:
            record = store.change(record, state="failed", raw_output=raw_output,
                                  failure="proposal_generation_failed_after_entry" if prepared_request else "proposal_generation_not_dispatched")
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
    intent = {"proposal_id": request.proposal_id,
              "selection": request.selection.model_dump(mode="json")}
    key, fingerprint = str(request.decision_id), digest(intent)
    old = next((r for r in record["reviews"] if r["decision_id"] == key), None)
    if old:
        if old["intent_digest"] != fingerprint:
            raise ApplicationStateConflictError("Review key has a different decision")
        return old
    if record["state"] != "completed" or record["revision"] != request.expected_revision:
        raise ApplicationStateConflictError("Review revision is stale or proposals unavailable")
    extraction = ProposalRequest.model_validate_json(canonical(record["intent"]))
    selected = request.selection
    for field in ("managed_world_id", "campaign_id", "source_admission_id", "evidence_ref_id", "source_sha256"):
        if getattr(extraction, field) != getattr(selected, field):
            raise ValueError("Review changed the extraction source/scope")
    proposal = next((p for p in record["result"]["batch"]["proposals"] if p["proposal_id"] == request.proposal_id), None)
    if proposal is None:
        raise ValueError("Unknown source proposal")
    location = {"start_byte": selected.start_byte, "end_byte": selected.end_byte,
                "clause_sha256": selected.clause_sha256}
    if location not in record["result"]["locations"][request.proposal_id]["matches"]:
        raise ValueError("Review clause is not an exact occurrence of the proposal")
    repo, space, _ = source(extraction, principal)
    _ancestry(repo, space, extraction.read_revision_id, selected.expected_parent_revision_id)
    packet = jsonable_encoder(statements.prepare(selected, principal))
    decision = {"decision_id": key, "intent": intent, "intent_digest": fingerprint,
                "prepared_packet": packet, "packet_digest": digest(packet)}
    saved = store.change(record, review=decision)
    return next(r for r in saved["reviews"] if r["decision_id"] == key)
