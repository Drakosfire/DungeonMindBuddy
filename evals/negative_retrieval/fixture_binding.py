"""Bind a synthetic case to captured saved-page and complete prior dialogue."""
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from .capture_observation import _body


def verify_fixture(fixture, request, prior_envelope, after_envelope):
    """Return True only for exact matching, owner-validated retained context.

    This validates the capture's fixture binding, not provenance of the capture
    environment, prior citations, runtime source, acquisition or model quality.
    Unavailable/malformed context raises ValueError rather than implying a pass.
    """
    from apps.live_control_server.models.agent_turn import AgentSurfaceNativeContextResponseV1
    from application_state.agent_conversation.native_context import validate_work_context
    from application_state.agent_conversation.types import TurnProvenance

    if prior_envelope.get("http_status") != 200 or after_envelope.get("http_status") != 200:
        raise ValueError("Both history reads must succeed")
    prior, after = _body(prior_envelope), _body(after_envelope)
    draft = request["build_draft_context"]
    snap = draft["snapshot"]
    work = request["primary_work"]
    world = request["owner_scope"]["world_id"]
    if (request.get("message") != fixture["request"]
            or request["surface"]["surface_id"] != "build"
            or prior["world_id"] != world or after["world_id"] != world
            or prior["conversation_id"] != draft["conversation_id"]
            or prior["active_conversation_id"] != draft["conversation_id"]
            or after["conversation_id"] != draft["conversation_id"]
            or after["active_conversation_id"] != draft["conversation_id"]
            or after["pointer_revision"] != draft["expected_pointer_revision"]
            or prior["pointer_revision"] != draft["expected_pointer_revision"]):
        raise ValueError("Fixture request and conversation binding differ")
    markdown = snap["draft_markdown"]
    content_hash = sha256(markdown.encode("utf-8")).hexdigest()
    if (markdown != fixture["page"] or snap["world_id"] != world
            or snap["document_id"] != work["object_id"]
            or request["surface"]["instance_id"] != work["object_id"]
            or snap["registry_revision"] != work["expected_revision"]
            or snap["content_sha256"] != work["expected_content_sha256"]
            or snap["draft_sha256"] != content_hash or snap["content_sha256"] != content_hash):
        raise ValueError("Fixture differs from the exact clean captured page")
    turns = prior["turns"]
    if ("next_before_sequence" not in prior or prior.get("next_before_sequence") is not None or not isinstance(turns, list)
            or any(not isinstance(t, dict) for t in turns)
            or any(not isinstance(t.get("turn_id"), str) or not t["turn_id"] for t in turns)
            or len({t["turn_id"] for t in turns}) != len(turns)
            or [t.get("sequence") for t in turns] != list(range(1, len(turns) + 1))
            or any(t.get("lifecycle_status") != "completed" for t in turns)):
        raise ValueError("Prior conversation is incomplete or not fully completed")
    dialogue = []
    for turn in turns:
        if not isinstance(turn.get("user_text"), str) or not isinstance(turn.get("assistant_text"), str):
            raise ValueError("Prior dialogue is unavailable")
        dialogue.extend(({"role": "user", "content": turn["user_text"]},
                         {"role": "assistant", "content": turn["assistant_text"]}))
    if dialogue != fixture["history"]:
        raise ValueError("Prior dialogue differs from the frozen fixture")
    key = str(uuid5(NAMESPACE_URL, f"dmb-agent-turn:{world}:{request['turn_id']}"))
    matches = [t for t in after["turns"] if t.get("idempotency_key") == key
               and t.get("user_text") == fixture["request"]]
    if len(matches) != 1:
        raise ValueError("No unique captured turn")
    turn = matches[0]
    after_turns = after["turns"]
    if ("next_before_sequence" not in after or after.get("next_before_sequence") is not None or not isinstance(after_turns, list)
            or any(not isinstance(t, dict) for t in after_turns)
            or [t.get("sequence") for t in after_turns] != list(range(1, len(turns) + 2))
            or turn.get("sequence") != len(turns) + 1
            or not isinstance(turn.get("turn_id"), str) or not turn["turn_id"]
            or turn["turn_id"] in {t["turn_id"] for t in turns}):
        raise ValueError("Captured history is incomplete or includes intervening turns")
    keys = ("turn_id", "sequence", "lifecycle_status", "user_text", "assistant_text")
    if any(any(before.get(k) != current.get(k) for k in keys)
           for before, current in zip(turns, after_turns)):
        raise ValueError("Previously captured dialogue changed before delivery")
    if (turn["provenance"]["world_id"] != world
            or turn["provenance"]["surface_id"] != "build"
            or turn["provenance"]["surface_instance_id"] != work["object_id"]):
        raise ValueError("Captured turn belongs to a different page")
    context = AgentSurfaceNativeContextResponseV1.model_validate(turn["knowledge_context"])
    validate_work_context(context.receipt, TurnProvenance.model_validate(turn["provenance"]))
    basis = context.receipt.work_context.source_basis
    if (context.receipt.work_context.surface_id != "build"
            or any(getattr(basis, key) != snap[key] for key in
                   ("world_id", "document_id", "registry_revision", "content_sha256", "visibility"))):
        raise ValueError("Owner-validated source receipt differs from captured page")
    return True


def verify_preflight_snapshot(fixture, template, world, snapshot):
    """Check the pinned editor snapshot before dispatching the benchmark turn."""
    if not isinstance(snapshot, dict):
        raise ValueError("A pinned Build editor snapshot is required")
    work = template["primary_work"]
    body = snapshot["draft_markdown"]
    digest = sha256(body.encode("utf-8")).hexdigest()
    if (body != fixture["page"] or snapshot["world_id"] != world
            or snapshot["document_id"] != work["object_id"]
            or snapshot["registry_revision"] != work["expected_revision"]
            or snapshot["content_sha256"] != work["expected_content_sha256"]
            or snapshot["content_sha256"] != digest or snapshot["draft_sha256"] != digest):
        raise ValueError("Preflight snapshot differs from the frozen fixture")
    return True


def verify_preflight_history(fixture, history, world, conversation):
    """Require a complete matching saved prefix before a subsequent dispatch."""
    if (history.get("world_id") != world or history.get("conversation_id") != conversation
            or history.get("active_conversation_id") != conversation
            or "next_before_sequence" not in history or history.get("next_before_sequence") is not None):
        raise ValueError("Preflight conversation binding is unavailable or incomplete")
    turns = history.get("turns")
    if (not isinstance(turns, list) or any(not isinstance(t, dict) for t in turns)
            or any(not isinstance(t.get("turn_id"), str) or not t["turn_id"] for t in turns)
            or len({t["turn_id"] for t in turns}) != len(turns)
            or [t.get("sequence") for t in turns] != list(range(1, len(turns) + 1))
            or any(t.get("lifecycle_status") != "completed" for t in turns)):
        raise ValueError("Preflight conversation is incomplete")
    dialogue = []
    for turn in turns:
        if not isinstance(turn.get("user_text"), str) or not isinstance(turn.get("assistant_text"), str):
            raise ValueError("Preflight dialogue is unavailable")
        dialogue.extend(({"role": "user", "content": turn["user_text"]},
                         {"role": "assistant", "content": turn["assistant_text"]}))
    if dialogue != fixture["history"]:
        raise ValueError("Preflight dialogue differs from the frozen fixture")
    return True
