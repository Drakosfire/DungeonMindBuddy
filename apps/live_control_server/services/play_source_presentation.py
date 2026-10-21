"""Project immutable Play identity for Graph-off replies/history; no source reads."""
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.agent_conversation.types import Turn, PlayRunTurnContextReceiptV2, validate_play_context_receipt
from apps.live_control_server.models.agent_turn import AgentPlaySourceBasisV1, AgentPlaySourceContextV1


def project_play_source_context(turn, *, delivery_replay: bool):
    if isinstance(turn, MixedCompletedTurnV1):
        turn = MixedCompletedTurnV1.model_validate_json(turn.model_dump_json(by_alias=True))
        if turn.base_projection.kind != "absent":
            raise ValueError("Graph-off Play source projection cannot hide a Graph base")
        owner = turn.envelope
    else:
        owner = Turn.model_validate_json(turn.model_dump_json(by_alias=True))
        if owner.graph_context_receipt is not None or owner.graph_context_execution is not None:
            raise ValueError("Graph-off Play source projection cannot hide Graph scope")
    receipt = owner.play_context_receipt
    if not isinstance(receipt, PlayRunTurnContextReceiptV2) or owner.provenance.surface_id != "play":
        raise ValueError("Graph-off Play requires its full durable source receipt")
    validate_play_context_receipt(receipt,owner.world_id,owner.provenance)
    basis = AgentPlaySourceBasisV1.model_validate({
        **receipt.model_dump(mode="python",by_alias=True,exclude={"scene_note"}),
        "schema":"dmb_agent_play_source_basis_v1"})
    return AgentPlaySourceContextV1(basis=basis,basis_sha256=canonical_sha256(basis),delivery_replay=delivery_replay)
