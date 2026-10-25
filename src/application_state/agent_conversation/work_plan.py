"""Author-reviewed plans; execution is projected from actual APP receipts."""

from hashlib import sha256
import json
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
    dispatches: list[Dispatch] = Field(default_factory=list)

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
        or not turn.assistant_text
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
    p = Plan.model_validate(row[0])
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
            "schema": "dmb_work_plan_response_v1",
            "world_id": world,
            "conversation_id": str(conversation),
            "source_turn_id": str(source),
            "plan": _projection(conn, p) if p else None,
        }


def save(world, conversation, source, review: Review):
    with unit_of_work(_ready_dsn()) as conn:
        turn = _source(conn, world, conversation, source, writing=True)
        old = _load(conn, world, conversation, source, lock=True)
        if old and old.steps == review.steps:
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
                    and changed.get(s.step_id) != s
                ):
                    raise ApplicationStateConflictError(
                        "Retain the exact reviewed step after continuation; add a new step to change it"
                    )
        p = Plan(
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
                "dispatch": prior.model_dump(mode="json"),
            }
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
                        "dispatch": d.model_dump(mode="json"),
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
        context.pop(
            "dispatches"
        )  # Carry results, never recursively embed earlier prepared requests.
        instruction = (
            "Discuss this step in conversation; do not insert a work plan or page content."
            if step.kind == "discuss"
            else "Prepare actual page-ready content for this step as an editable on-page insertion. Do not return a planning checklist. Nothing is kept or saved without my page controls."
        )
        message = (
            "Continue only this explicitly selected step of my saved reviewed plan. Other steps, including selected ones, are context and are not authorized for automatic execution.\n\n"
            + json.dumps(
                {
                    "reviewed_plan": context,
                    "current_step": step.model_dump(mode="json"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n\n"
            + instruction
        )
        d = Dispatch(
            command_id=command.command_id,
            step_id=step.step_id,
            client_thread_id=uuid4(),
            client_turn_id=uuid4(),
            message=message,
        )
        updated = Plan.model_validate(
            p.model_dump(mode="python", by_alias=True)
            | {
                "revision": p.revision + 1,
                "dispatches": [x.model_dump() for x in p.dispatches] + [d.model_dump()],
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
            "dispatch": d.model_dump(mode="json"),
        }
