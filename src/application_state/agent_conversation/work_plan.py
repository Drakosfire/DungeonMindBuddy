"""Author-reviewed plans; execution is projected from actual APP receipts."""

from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from pydantic import BaseModel, ConfigDict, Field, model_validator
from psycopg.types.json import Jsonb
from application_state.unit_of_work import unit_of_work
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from .service import _ready_dsn, _lock_pointer
from . import repository as repo
from .types import Turn
from .reviewed_action import ReviewedDiscussionScopeV1, ReviewedDiscussionTask, ReviewedSiblingContext
from .authored_graph_references import AuthoredGraphReferenceV1, AuthoredGraphReferencesV1, effective_references, source_references


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Step(Closed):
    step_id: UUID
    text: str = Field(min_length=1)
    selected: bool = Field(strict=True)
    kind: Literal["discuss", "prepare_insertion"] = "discuss"

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip():
            raise ValueError("Use a nonempty step")
        return self


class Review(Closed):
    expected_revision: int = Field(strict=True, ge=0)
    steps: list[Step] = Field(min_length=1)

    @model_validator(mode="after")
    def distinct(self):
        if len({s.step_id for s in self.steps}) != len(self.steps):
            raise ValueError("Step identities must be distinct")
        return self


class Continue(Closed):
    expected_revision: int = Field(strict=True, ge=1)
    step_id: UUID
    command_id: UUID


class Dispatch(Closed):
    command_id: UUID
    step_id: UUID
    client_thread_id: UUID
    client_turn_id: UUID
    message: str


class DispatchV2(Dispatch):
    schema_: Literal['dmb_work_plan_dispatch_v2'] = Field(default='dmb_work_plan_dispatch_v2', alias='schema')
    authored_references: AuthoredGraphReferencesV1


class DispatchV3(Dispatch):
    schema_: Literal['dmb_work_plan_dispatch_v3'] = Field(default='dmb_work_plan_dispatch_v3', alias='schema')
    scope: ReviewedDiscussionScopeV1
    authored_references: AuthoredGraphReferencesV1 | None


class Plan(Closed):
    schema_: Literal["dmb_reviewed_work_plan_v1"] = Field(
        default="dmb_reviewed_work_plan_v1", alias="schema"
    )
    world_id: str
    conversation_id: UUID
    source_turn_id: UUID
    source_answer_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    document_id: str
    revision: int = Field(strict=True, ge=1)
    steps: list[Step] = Field(min_length=1)
    dispatches: list[DispatchV3 | DispatchV2 | Dispatch] = Field(default_factory=list)

    @model_validator(mode="after")
    def references(self):
        ids = {s.step_id for s in self.steps}
        if len(ids) != len(self.steps) or any(
            d.step_id not in ids for d in self.dispatches
        ):
            raise ValueError("Plan dispatches require distinct retained steps")
        if len({d.command_id for d in self.dispatches}) != len(self.dispatches) or len(
            {d.client_turn_id for d in self.dispatches}
        ) != len(self.dispatches):
            raise ValueError("Plan dispatch identities must be unique")
        return self


class ReviewV2(Review):
    schema_: Literal['dmb_reviewed_work_plan_review_v2'] = Field(default='dmb_reviewed_work_plan_review_v2', alias='schema')
    objective: str = Field(min_length=1)

    @model_validator(mode='after')
    def readable_objective(self):
        if not self.objective.strip():
            raise ValueError('A plan needs an expected outcome')
        return self


class PlanV2(Plan):
    schema_: Literal['dmb_reviewed_work_plan_v2'] = Field(default='dmb_reviewed_work_plan_v2', alias='schema')
    objective: str = Field(min_length=1)

    @model_validator(mode='after')
    def readable_objective(self):
        if not self.objective.strip():
            raise ValueError('A plan needs an expected outcome')
        return self



class StepV2(Step):
    references: tuple[AuthoredGraphReferenceV1, ...]


class ReviewV3(ReviewV2):
    schema_: Literal['dmb_reviewed_work_plan_review_v3'] = Field(default='dmb_reviewed_work_plan_review_v3', alias='schema')
    root_references: tuple[AuthoredGraphReferenceV1, ...]
    steps: list[StepV2] = Field(min_length=1)


class PlanV3(PlanV2):
    schema_: Literal['dmb_reviewed_work_plan_v3'] = Field(default='dmb_reviewed_work_plan_v3', alias='schema')
    root_references: tuple[AuthoredGraphReferenceV1, ...]
    steps: list[StepV2] = Field(min_length=1)
    dispatches: list[DispatchV3 | DispatchV2 | Dispatch] = Field(default_factory=list)

    @model_validator(mode='after')
    def reference_worlds(self):
        AuthoredGraphReferencesV1(references=self.root_references).require_world(self.world_id)
        for step in self.steps:
            AuthoredGraphReferencesV1(references=step.references).require_world(self.world_id)
            effective_references(self.root_references, step.references)
        for dispatch in self.dispatches:
            if isinstance(dispatch, (DispatchV2, DispatchV3)) and dispatch.authored_references is not None:
                dispatch.authored_references.require_world(self.world_id)
        return self


def parse_plan(value):
    return {'dmb_reviewed_work_plan_v1': Plan, 'dmb_reviewed_work_plan_v2': PlanV2,
            'dmb_reviewed_work_plan_v3': PlanV3}[value.get('schema')].model_validate(value)


def step_content(step):
    # Explicit upgrade preserves legacy locked steps with an empty reference set.
    return step.model_dump(mode='json') | {'references': [r.model_dump(mode='json', by_alias=True) for r in getattr(step, 'references', ())]}

def _source(conn, world, conversation, source, *, writing=False):
    if writing:
        p = _lock_pointer(conn, world)
        if p.active_conversation_id != conversation:
            raise ApplicationStateConflictError(
                "Open the original active conversation before changing its plan"
            )
    turn = repo.get_turn(conn, world, source)
    if (
        not isinstance(turn, Turn)
        or turn.conversation_id != conversation
        or turn.status != "completed"
        or turn.provenance.surface_id != "build"
        or turn.provenance.primary_work.kind != "build"
        or (not turn.assistant_text and not (
            turn.assistant_text == '' and getattr(turn.completion, 'schema_', None) in {'dmb_build_intentional_response_completion_v1','dmb_build_intentional_response_completion_v2','dmb_build_intentional_response_completion_v3'}
            and not turn.completion.answer_segments and getattr(turn.completion.collaboration, 'kind', None) == 'plan'))
    ):
        raise ApplicationStateNotFoundError(
            "A completed Build reply in this conversation is required"
        )
    return turn


def _load(conn, world, conversation, source, *, lock=False):
    row = conn.execute(
        "SELECT payload FROM agent.work_plan WHERE world_id=%s AND conversation_id=%s AND source_turn_id=%s"
        + (" FOR UPDATE" if lock else ""),
        (world, conversation, source),
    ).fetchone()
    if row is None:
        return None
    p = parse_plan(row[0])
    if (p.world_id, p.conversation_id, p.source_turn_id) != (
        world,
        conversation,
        source,
    ):
        raise ApplicationStateConflictError("Retained plan scope differs")
    return p


def _result(conn, p, dispatch):
    key = uuid5(NAMESPACE_URL, f"dmb-agent-turn:{p.world_id}:{dispatch.client_turn_id}")
    found = repo.get_turn_by_world_key(conn, p.world_id, key)
    if found is None:
        return {
            "status": "awaiting_dispatch",
            "turn_id": None,
            "attempt": None,
            "result": None,
        }
    turn = found[0]
    if (
        turn.conversation_id != p.conversation_id
        or turn.provenance.world_id != p.world_id
        or turn.provenance.surface_id != "build"
        or turn.provenance.primary_work.object_id != p.document_id
        or turn.user_text != dispatch.message
    ):
        return {
            "status": "needs_attention",
            "turn_id": None,
            "attempt": None,
            "result": None,
        }
    status = turn.status
    result = None
    step = next(s for s in p.steps if s.step_id == dispatch.step_id)
    if status == "completed":
        if not isinstance(turn, Turn):
            status = "needs_attention"
        elif step.kind == "discuss":
            status = "completed"
            result = {"kind": "reply", "text": turn.assistant_text}
        elif (
            getattr(turn.completion, "schema_", None)
            == "dmb_build_authoring_completion_v1"
        ):
            # A staged proposal is not proof of insertion or a saved page revision.
            status = "prepared"
            result = {
                "kind": "page_proposal",
                "action_id": str(turn.completion.action_id),
            }
        else:
            status = "needs_attention"
            result = {"kind": "reply", "text": turn.assistant_text}
    return {
        "status": status,
        "turn_id": str(turn.turn_id),
        "attempt": turn.attempt,
        "result": result,
    }


def _projection(conn, p):
    payload = p.model_dump(mode="json", by_alias=True)
    results = {str(d.command_id): _result(conn, p, d) for d in p.dispatches}
    payload["execution"] = [
        {
            "command_id": str(d.command_id),
            "step_id": str(d.step_id),
            **results[str(d.command_id)],
        }
        for d in p.dispatches
    ]
    return payload


def read(world, conversation, source):
    with unit_of_work(_ready_dsn()) as conn:
        turn = _source(conn, world, conversation, source)
        p = _load(conn, world, conversation, source)
        if (
            p
            and p.source_answer_sha256
            != sha256(turn.assistant_text.encode()).hexdigest()
        ):
            raise ApplicationStateConflictError(
                "The source reply differs from its retained review"
            )
        return {
            "schema": "dmb_work_plan_response_v3" if isinstance(p, PlanV3) or source_references(turn) else "dmb_work_plan_response_v2",
            **({"source_references": [r.model_dump(mode="json", by_alias=True) for r in source_references(turn)]} if isinstance(p, PlanV3) or source_references(turn) else {}),
            "world_id": world,
            "conversation_id": str(conversation),
            "source_turn_id": str(source),
            "plan": _projection(conn, p) if p else None,
        }


def save(world, conversation, source, review: Review):
    with unit_of_work(_ready_dsn()) as conn:
        turn = _source(conn, world, conversation, source, writing=True)
        old = _load(conn, world, conversation, source, lock=True)
        if old and (old.source_answer_sha256 != sha256(turn.assistant_text.encode()).hexdigest()
                    or old.document_id != turn.provenance.primary_work.object_id):
            raise ApplicationStateConflictError('The retained plan has a different source or page')
        if not isinstance(review, ReviewV2):
            if (type(old) is Plan and old.steps == review.steps and old.revision == review.expected_revision):
                return _projection(conn, old)
            raise ApplicationStateConflictError('Add an expected outcome and Save the objective-aware review; legacy writes cannot create or change a plan')
        if isinstance(old, PlanV3) and not isinstance(review, ReviewV3):
            raise ApplicationStateConflictError("Retain this plan’s Graph references with the reference-aware review")
        if (isinstance(old, PlanV2) and old.steps == review.steps and old.objective == review.objective
            and getattr(old, "root_references", ()) == getattr(review, "root_references", ())):
            return _projection(conn, old)
        if (old.revision if old else 0) != review.expected_revision:
            raise ApplicationStateConflictError(
                "The saved plan changed; reload it before editing"
            )
        if old:
            changed = {s.step_id: s for s in review.steps}
            for s in old.steps:
                if (
                    any(d.step_id == s.step_id for d in old.dispatches)
                    and (changed.get(s.step_id) is None or step_content(changed[s.step_id]) != step_content(s))
                ):
                    raise ApplicationStateConflictError(
                        "Retain the exact reviewed step after continuation; add a new step to change it"
                    )
        p = (PlanV3 if isinstance(review, ReviewV3) else PlanV2)(
            **({"root_references": review.root_references} if isinstance(review, ReviewV3) else {}),
            objective=review.objective,
            world_id=world,
            conversation_id=conversation,
            source_turn_id=source,
            source_answer_sha256=sha256(turn.assistant_text.encode()).hexdigest(),
            document_id=turn.provenance.primary_work.object_id,
            revision=(old.revision + 1 if old else 1),
            steps=review.steps,
            dispatches=old.dispatches if old else [],
        )
        if old:
            conn.execute(
                "UPDATE agent.work_plan SET payload=%s,revision=%s WHERE world_id=%s AND conversation_id=%s AND source_turn_id=%s",
                (
                    Jsonb(p.model_dump(mode="json", by_alias=True)),
                    p.revision,
                    world,
                    conversation,
                    source,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO agent.work_plan(world_id,conversation_id,source_turn_id,revision,payload) VALUES(%s,%s,%s,%s,%s)",
                (
                    world,
                    conversation,
                    source,
                    p.revision,
                    Jsonb(p.model_dump(mode="json", by_alias=True)),
                ),
            )
        return _projection(conn, p)


def continue_step(world, conversation, source, command: Continue):
    with unit_of_work(_ready_dsn()) as conn:
        _source(conn, world, conversation, source, writing=True)
        p = _load(conn, world, conversation, source, lock=True)
        if p is None:
            raise ApplicationStateNotFoundError(
                "Save the reviewed plan before continuing"
            )
        prior = next(
            (d for d in p.dispatches if d.command_id == command.command_id), None
        )
        if prior:
            if prior.step_id != command.step_id:
                raise ApplicationStateConflictError(
                    "This continuation command belongs to a different step"
                )
            return {
                "plan": _projection(conn, p),
                "dispatch": prior.model_dump(mode="json", by_alias=True),
                "reviewed_step": _reference_for_dispatch(conn, p, prior),
            }
        if not isinstance(p, PlanV2):
            raise ApplicationStateConflictError('Add an expected outcome and Save before continuing a new step')
        if p.revision != command.expected_revision:
            raise ApplicationStateConflictError("The plan changed before continuation")
        step = next((s for s in p.steps if s.step_id == command.step_id), None)
        if step is None or not step.selected:
            raise ApplicationStateConflictError("Choose a selected saved step")
        for d in p.dispatches:
            status = _result(conn, p, d)["status"]
            if status in {
                "awaiting_dispatch",
                "accepted",
                "running",
                "needs_attention",
            }:
                if d.step_id == step.step_id and status == "awaiting_dispatch":
                    return {
                        "plan": _projection(conn, p),
                        "dispatch": d.model_dump(mode="json", by_alias=True),
                        "reviewed_step": _reference_for_dispatch(conn, p, d),
                    }
                raise ApplicationStateConflictError(
                    "Resolve the existing continuation before starting another"
                )
        previous = [d for d in p.dispatches if d.step_id == step.step_id]
        if previous and _result(conn, p, previous[-1])["status"] in {
            "completed",
            "prepared",
        }:
            raise ApplicationStateConflictError(
                "This step already has a result; add a new step to revise it"
            )
        context = _projection(conn, p)
        results = {r["step_id"]: r for r in context["execution"]}
        labels = {
            "awaiting_dispatch": "ready to resume",
            "accepted": "queued",
            "running": "in progress",
            "completed": "reply received",
            "prepared": "suggestion prepared; review and Save on the page",
            "failed": "failed",
            "interrupted": "interrupted",
            "needs_attention": "needs attention",
        }
        lines = []
        for i, reviewed in enumerate(p.steps, 1):
            result = results.get(str(reviewed.step_id))
            status = (
                labels[result["status"]]
                if result
                else "pending"
                if reviewed.selected
                else "deferred"
            )
            choice = "Selected" if reviewed.selected else "Deferred"
            action = "Discuss" if reviewed.kind == "discuss" else "Prepare an insertion"
            lines.append(f"{i}. {choice} · {action} · {status}: {reviewed.text}")
            if result and result["result"] and result["result"]["kind"] == "reply":
                lines.append(
                    "Earlier reply: "
                    + (result["result"]["text"] or "No reply text recorded.")
                )
        instruction = (
            "Discuss this step in conversation; do not insert a work plan or page content."
            if step.kind == "discuss"
            else "Prepare actual page-ready content for this step as an editable on-page insertion. Do not return a planning checklist. Nothing is kept or saved without my page controls."
        )
        message = (
            "Continue only this explicitly selected step of my saved reviewed plan:\n\n"
            + step.text
            + "\n\nExpected outcome (authored context):\n" + p.objective
            + "\n\nMy reviewed plan and earlier results (authored context):\n"
            + "\n".join(lines)
            + "\n\nOther steps, including selected ones, are context and are not authorized for automatic execution.\n"
            + instruction
        )
        scope = None
        if step.kind == 'discuss':
            siblings = []
            for reviewed in p.steps:
                if reviewed.step_id == step.step_id:
                    continue
                result = results.get(str(reviewed.step_id))
                prior_reply = result.get('result') if result else None
                siblings.append(ReviewedSiblingContext(step_id=reviewed.step_id, text=reviewed.text,
                    kind=reviewed.kind, selected=reviewed.selected,
                    status=result['status'] if result else 'pending' if reviewed.selected else 'deferred',
                    earlier_reply=prior_reply.get('text') if prior_reply and prior_reply['kind']=='reply' else None))
            scope = ReviewedDiscussionScopeV1(task=ReviewedDiscussionTask(step_id=step.step_id,kind='discuss',text=step.text),
                objective_context=p.objective,sibling_context=tuple(siblings))
            message = 'Discuss only this selected reviewed step:\n\n' + step.text
        d = (DispatchV3 if scope else DispatchV2 if isinstance(p, PlanV3) else Dispatch)(
            **({'scope': scope, 'authored_references': AuthoredGraphReferencesV1(references=effective_references(p.root_references,step.references)) if isinstance(p,PlanV3) else None} if scope else {}),
            **({"authored_references": AuthoredGraphReferencesV1(references=effective_references(p.root_references, step.references))} if isinstance(p, PlanV3) and scope is None else {}),
            command_id=command.command_id,
            step_id=step.step_id,
            client_thread_id=uuid4(),
            client_turn_id=uuid4(),
            message=message,
        )
        updated = type(p).model_validate(
            p.model_dump(mode="python", by_alias=True)
            | {
                "revision": p.revision + 1,
                "dispatches": [x.model_dump(by_alias=True) for x in p.dispatches] + [d.model_dump(by_alias=True)],
            }
        )
        conn.execute(
            "UPDATE agent.work_plan SET payload=%s,revision=%s WHERE world_id=%s AND conversation_id=%s AND source_turn_id=%s",
            (
                Jsonb(updated.model_dump(mode="json", by_alias=True)),
                updated.revision,
                world,
                conversation,
                source,
            ),
        )
        return {
            "plan": _projection(conn, updated),
            "dispatch": d.model_dump(mode="json", by_alias=True),
            "reviewed_step": _reference_for_dispatch(conn, updated, d),
        }


def resolve_action(conn, world, reference, *, document_id, client_thread_id, client_turn_id, message):
    """Resolve immutable author authority, including during completed archived replay."""
    from .reviewed_action import ReviewedStepBinding, ReviewedStepBindingV2, ReviewedStepBindingV3, digest
    turn = _source(conn, world, reference.conversation_id, reference.source_turn_id)
    p = _load(conn, world, reference.conversation_id, reference.source_turn_id)
    if (p is None or p.document_id != document_id
        or p.source_answer_sha256 != sha256(turn.assistant_text.encode()).hexdigest()):
        raise ApplicationStateConflictError("The reviewed action has a different source or page")
    dispatch = next((d for d in p.dispatches if d.command_id == reference.command_id), None)
    step = next((s for s in p.steps if dispatch and s.step_id == dispatch.step_id), None)
    if (dispatch is None or step is None or not step.selected
        or str(dispatch.client_thread_id) != client_thread_id
        or str(dispatch.client_turn_id) != client_turn_id or dispatch.message != message):
        raise ApplicationStateConflictError("The reviewed action differs from its retained dispatch")
    if isinstance(dispatch, DispatchV3) and dispatch.scope.task != ReviewedDiscussionTask(step_id=step.step_id, kind=step.kind, text=step.text):
        raise ApplicationStateConflictError('The scoped task differs from its immutable selected step')
    # Reference editing must not alter the binding of an older dispatch.
    bound_step = step.model_dump(mode="json")
    if not isinstance(dispatch, DispatchV2) and not (isinstance(dispatch,DispatchV3) and dispatch.authored_references is not None):
        bound_step.pop("references", None)
    return (ReviewedStepBindingV3 if isinstance(dispatch, DispatchV3) else ReviewedStepBindingV2 if isinstance(dispatch, DispatchV2) else ReviewedStepBinding)(
        **({'scope':dispatch.scope, 'authored_references':dispatch.authored_references} if isinstance(dispatch,DispatchV3) else {}),
        **({"authored_references": dispatch.authored_references} if isinstance(dispatch, DispatchV2) else {}),
        reference=reference, step_id=step.step_id, kind=step.kind,
        source_answer_sha256=p.source_answer_sha256,
        dispatch_sha256=digest({"step": bound_step, "dispatch": dispatch.model_dump(mode="json")}))


def resolve_request_action(request, world):
    reference = request.reviewed_step
    if reference is None:
        return None
    draft = request.build_draft_context
    if (draft is None or draft.conversation_id != reference.conversation_id
        or request.primary_work is None or request.graph_request.mode != "world"):
        raise ApplicationStateConflictError("The reviewed action requires its current page and conversation")
    with unit_of_work(_ready_dsn()) as conn:
        binding = resolve_action(conn, world, reference, document_id=request.primary_work.object_id,
            client_thread_id=request.client_thread_id, client_turn_id=request.turn_id, message=request.message)
    expected_refs = getattr(binding, 'authored_references', None)
    if getattr(request, "build_authored_references", None) != expected_refs:
        raise ApplicationStateConflictError('The step references differ from its immutable dispatch')
    if binding.kind == "prepare_insertion" and request.build_write_capability is None:
        raise ApplicationStateConflictError("The reviewed insertion has no captured page placement; retain this step and restore its page target")
    return binding


def validate_bound_intent(conn, world, intent, key):
    """APP rechecks retained authority at admission and action append."""
    binding = getattr(intent, "reviewed_step", None)
    if binding is None:
        return
    p = _load(conn, world, binding.reference.conversation_id, binding.reference.source_turn_id)
    d = next((d for d in p.dispatches if d.command_id == binding.reference.command_id), None) if p else None
    if d is None or key != uuid5(NAMESPACE_URL, f"dmb-agent-turn:{world}:{d.client_turn_id}"):
        raise ApplicationStateConflictError("Reviewed action does not own this turn identity")
    actual = resolve_action(conn, world, binding.reference, document_id=intent.primary_work.object_id,
        client_thread_id=intent.client_thread_id, client_turn_id=str(d.client_turn_id), message=intent.message)
    if actual != binding:
        raise ApplicationStateConflictError("Reviewed action binding differs from retained author authority")


def retain_bound_intent(conn, turn, intent):
    if getattr(intent, "reviewed_step", None) is not None:
        conn.execute("INSERT INTO agent.turn_reviewed_action(turn_id,intent) VALUES(%s,%s)",
            (turn.turn_id, Jsonb(intent.model_dump(mode="json", by_alias=True))))


def retained_bound_intent(conn, turn):
    from .types import BuildGraphIntentV1, submitted_turn_intent_fingerprint_v2
    row = conn.execute("SELECT intent FROM agent.turn_reviewed_action WHERE turn_id=%s", (turn.turn_id,)).fetchone()
    if row is None:
        return None
    from .types import BuildGraphIntentV2
    intent = (BuildGraphIntentV2 if row[0].get("schema") == "dmb_build_graph_intent_v2" else BuildGraphIntentV1).model_validate(row[0])
    if intent.reviewed_step is None or submitted_turn_intent_fingerprint_v2(intent) != turn.submitted_intent_fingerprint_v2:
        raise ApplicationStateConflictError("Retained reviewed intent differs from the turn fingerprint")
    return intent


def _reference_for_dispatch(conn, p, dispatch):
    from .reviewed_action import ReviewedStepReference
    found = repo.get_turn_by_world_key(conn, p.world_id, uuid5(NAMESPACE_URL, f"dmb-agent-turn:{p.world_id}:{dispatch.client_turn_id}"))
    # Pre-upgrade admitted turns keep their original intent and recovery request.
    if found is not None and retained_bound_intent(conn, found[0]) is None:
        return None
    return ReviewedStepReference(conversation_id=p.conversation_id, source_turn_id=p.source_turn_id,
        command_id=dispatch.command_id).model_dump(mode="json")
