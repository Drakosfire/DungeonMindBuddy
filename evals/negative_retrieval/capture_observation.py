"""Read ordinary benchmark HTTP artifacts without inferring missing evidence."""

from hashlib import sha256
import json
from uuid import NAMESPACE_URL, uuid5

from .trace_observation import controller_observations, native_activity_counts, observed_acquisitions


def _body(envelope):
    if not isinstance(envelope, dict) or type(envelope.get("http_status")) is not int:
        raise ValueError("Invalid HTTP envelope")
    try:
        raw = bytes.fromhex(envelope["raw_body_hex"])
        body = json.loads(raw)
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid retained HTTP bytes") from exc
    if sha256(raw).hexdigest() != envelope.get("raw_body_sha256") or body != envelope.get("body"):
        raise ValueError("Retained HTTP bytes and body differ")
    return body


def observe(request, history_envelope, trace_envelope, answer_envelope, *, related_labels=None, source_labels=None):
    """Correlate one ordinary Build request with its saved history and trace.

    Only typed saved questions identify clarification here; prose and HTTP
    errors are not silently promoted to successful clarifications. Page mutation,
    semantic quality, UI interaction and exhaustive acquisition require separate
    evidence and remain unknown.
    """
    history = _body(history_envelope)
    trace = _body(trace_envelope)
    answer = _body(answer_envelope)
    if history_envelope["http_status"] != 200 or trace_envelope["http_status"] != 200:
        raise ValueError("Saved history and trace must be available")
    if request.get("surface", {}).get("surface_id") != "build":
        raise ValueError("This observer only handles ordinary Build requests")
    world = request["owner_scope"]["world_id"]
    key = str(uuid5(NAMESPACE_URL, f"dmb-agent-turn:{world}:{request['turn_id']}"))
    turns = [turn for turn in history["turns"] if turn.get("idempotency_key") == key
             and turn.get("user_text") == request["message"]]
    if len(turns) != 1:
        raise ValueError("No unique saved turn for the request")
    turn = turns[0]
    provenance = turn["provenance"]
    if (history["world_id"] != world or trace["world_id"] != world
            or trace["turn_id"] != turn["turn_id"] or provenance["world_id"] != world
            or provenance["surface_id"] != "build"
            or provenance["surface_instance_id"] != request["surface"]["instance_id"]):
        raise ValueError("Request, saved turn and trace are not bound")
    attempts = trace.get("attempts")
    if not isinstance(attempts, list) or len(attempts) != 1:
        raise ValueError("Exactly one retained attempt is required; retries need separate scoring")
    attempt = attempts[0]
    if (attempt.get("world_id") != world or attempt.get("turn_id") != turn["turn_id"]
            or attempt.get("conversation_id") != history["conversation_id"]):
        raise ValueError("Trace attempt belongs to another turn")
    projected = observed_acquisitions(attempt, related_labels=related_labels, source_labels=source_labels)
    http_ok = answer_envelope["http_status"] == 200
    if http_ok and (answer.get("turn_id") != request["turn_id"]
                    or answer.get("client_thread_id") != request["client_thread_id"]):
        raise ValueError("Response belongs to another request")
    status = turn.get("lifecycle_status")
    completed = http_ok and status == "completed" and attempt.get("terminal_status") == "completed"
    completion = (turn.get("knowledge_context") or {}).get("completion") or {}
    collaboration = completion.get("collaboration") or {}
    typed_questions = False
    if completed and isinstance(collaboration, dict) and collaboration.get("kind") == "questions":
        from application_state.agent_conversation.collaboration import ProposedQuestions
        from application_state.agent_conversation import types as t
        from application_state.agent_conversation.native_completion import SurfaceNativeCompletionV1
        completion_types = {
            "dmb_surface_native_completion_v1": SurfaceNativeCompletionV1,
            "dmb_build_collaboration_completion_v1": t.BuildCollaborationCompletionV1,
            "dmb_build_connected_page_review_completion_v1": t.BuildConnectedPageReviewCompletionV1,
            "dmb_build_relationship_review_completion_v1": t.BuildRelationshipReviewCompletionV1,
            "dmb_build_relationship_review_completion_v2": t.BuildRelationshipReviewCompletionV2,
            "dmb_build_relationship_review_completion_v3": t.BuildRelationshipReviewCompletionV3,
            "dmb_build_intentional_response_completion_v1": t.BuildIntentionalResponseCompletionV1,
            "dmb_build_intentional_response_completion_v2": t.BuildIntentionalResponseCompletionV2,
            "dmb_build_intentional_response_completion_v3": t.BuildIntentionalResponseCompletionV3,
        }
        try:
            ProposedQuestions.model_validate(collaboration)
            completion_type = completion_types.get(completion.get("schema"))
            if completion_type is not None:
                parsed = completion_type.model_validate(completion)
                typed_questions = (getattr(parsed, "surface_id", "build") == "build"
                                   and (answer.get("knowledge_context") or {}).get("completion") == completion)
        except (ValueError, TypeError):
            pass
    typed_proposal = False
    if completed and completion.get("schema") == "dmb_build_authoring_completion_v1":
        from application_state.agent_conversation.types import BuildAuthoringCompletionV1
        try:
            BuildAuthoringCompletionV1.model_validate(completion)
            typed_proposal = ((answer.get("knowledge_context") or {}).get("completion") == completion)
        except (ValueError, TypeError):
            pass
    typed_answer = False
    if completed and completion.get("schema") == "dmb_surface_native_completion_v1":
        from application_state.agent_conversation.native_completion import SurfaceNativeCompletionV1
        try:
            native = SurfaceNativeCompletionV1.model_validate(completion)
            typed_answer = (native.surface_id == "build" and bool(native.answer_segments)
                            and native.collaboration is None
                            and (answer.get("knowledge_context") or {}).get("completion") == completion)
        except (ValueError, TypeError):
            pass
    return {"reads": [row["label"] for row in projected["observed"]],
            "observed_acquisitions": projected["observed"], "journal_complete": None,
            "outcome": "clarification" if typed_questions else "proposal" if typed_proposal else "answer" if typed_answer else None,
            "completed_turn": completed, "http_status": answer_envelope["http_status"],
            "terminal_status": status, "trace_capture_status": projected["trace_capture_status"],
            "decision_observations": controller_observations(attempt),
            "native_activity": native_activity_counts(attempt)}
