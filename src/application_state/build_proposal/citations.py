"""Resolve proposal citations against the producing writer's admitted saved reads."""
from hashlib import sha256
import json

from pydantic import Field

from application_state.build_proposal.types import BuildProposalCitation, StrictModel


class ProposalCitationSelection(StrictModel):
    source: str
    quote: str = Field(min_length=1, max_length=4000)
    supports: str = Field(min_length=1, max_length=12000)


def offer_citations(schema, packet, *, enabled=True):
    pages = packet.get("surface_work", {}).get("build_work", {}).get("related_pages", ())
    schema["properties"].pop("citations", None)

    for key in ("BuildProposalCitation", "PageReference"):
        schema.get("$defs", {}).pop(key, None)
    if not schema.get("$defs"):
        schema.pop("$defs", None)
    if not enabled or not pages:
        return False
    row = ProposalCitationSelection.model_json_schema()
    row["properties"]["source"]["enum"] = [page["selection"] for page in pages]
    schema["properties"]["citations"] = {"type": "array", "items": row, "maxItems": 16}
    schema["required"].append("citations")
    return True


def normalize_cited_proposal(raw, normalize, *, load_turn, authorization):
    from application_state.agent_conversation.source_writer_output import strict_json

    value = strict_json(raw)
    if "citations" not in value:
        return normalize(raw)
    selections = value.pop("citations")
    if not isinstance(selections, list) or len(selections) > 16:
        raise ValueError("Invalid Build proposal citations")
    result = normalize(json.dumps(value, ensure_ascii=False))
    if not selections:
        return result
    turn = load_turn()
    if turn is None or authorization is None:
        raise ValueError("Build proposal citations require a bound writer")
    from application_state.agent_conversation.native_execution import NATIVE_WRITER_TYPES
    from application_state.agent_conversation.build_primary_context import native_work_frame
    from application_state.agent_conversation.native_build_work_view import semantic_frame, selection_aliases
    from application_state.agent_conversation.build_related_pages import records

    execution = turn.graph_context_execution
    writer, = [event for event in execution.events if type(event) in NATIVE_WRITER_TYPES
        and event.provider_attempt_id == authorization.provider_attempt_id
        and event.envelope_sha256 == authorization.payload_sha256]
    responses = [event for event in execution.events if event.kind == "provider_outcome"
        and event.provider_attempt_id == writer.provider_attempt_id and event.outcome == "response_received"]
    if len(responses) != 1 or responses[0].response_sha256 != sha256(raw.encode()).hexdigest():
        raise ValueError("Build proposal citations differ from the acknowledged writer output")
    prefix = execution.model_copy(update={"events": execution.events[:writer.sequence]})
    frame = native_work_frame(prefix, turn.graph_context_receipt.work_context.source_basis)
    aliases = selection_aliases(frame)
    wire = semantic_frame(frame, prefix)["build_work"]
    offered = {page["selection"]: page["markdown"] for page in wire.get("related_pages", ())}
    sources = {aliases[str(read.read_id)]: read for read in records(prefix)
               if str(read.read_id) in aliases}
    citations = []
    for row in selections:
        selection = ProposalCitationSelection.model_validate(row)
        read = sources.get(selection.source)
        if (read is None or selection.source not in offered or not selection.quote.strip()
                or selection.quote not in offered[selection.source] or selection.quote not in read.markdown
                or not selection.supports.strip() or selection.supports not in result.replacement_markdown):
            raise ValueError("Build proposal citation does not match its offered passage and replacement")
        citation = BuildProposalCitation(read_id=read.read_id, page=read.page,
            quote=selection.quote, supports=selection.supports)
        if citation in citations:
            raise ValueError("Duplicate Build proposal citation")
        citations.append(citation)
    return type(result).model_validate(result.model_dump(mode="python") | {"citations": citations})
