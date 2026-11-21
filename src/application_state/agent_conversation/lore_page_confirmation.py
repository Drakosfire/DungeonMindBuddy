"""Confirm exactly one retained native lore draft inside the APP transaction."""

import re
from urllib.parse import quote
from uuid import UUID

from pydantic import Field

from application_state.content import pages
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.unit_of_work import unit_of_work

from . import repository
from .collaboration import Closed
from .lore_page_review import ProposedLorePage
from .native_completion import SurfaceNativeCompletionV1
from .rules_authority_types import canonical_sha256
from .types import LoreSaveReviewReference, Turn


_SAVE_FOLLOWUP = re.compile(r"(?:please\s+)?create\s+(?:the|this)\s+page[.!]?", re.IGNORECASE)


def is_lore_save_followup(message: str) -> bool:
    return _SAVE_FOLLOWUP.fullmatch(message.strip()) is not None


class LorePageConfirmation(Closed):
    conversation_id: UUID
    turn_id: UUID
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LorePageReceipt(Closed):
    document_id: UUID
    revision_id: UUID
    review_sha256: str


def _body(turn: Turn) -> str:
    citations = {}
    prefix = (
        f"/api/live/agent/worlds/{quote(turn.world_id, safe='')}/conversation/turns/"
        f"{turn.turn_id}/native-body-excerpts"
    )
    for ordinal, citation in enumerate(turn.completion.native_body_citations):
        citations.setdefault(citation.segment_index, []).append(
            f"[Source {ordinal + 1}]({prefix}/{ordinal})"
        )
    paragraphs = []
    for index, segment in enumerate(turn.completion.answer_segments):
        if segment.kind == "limitation":
            continue
        if segment.kind == "proposal":
            paragraphs.append(f"**Proposed**\n\n{segment.text}")
        elif index in citations:
            paragraphs.append(f"{segment.text}\n\n{' '.join(citations[index])}")
        else:
            raise ApplicationStateConflictError("Lore review has no reopenable passage for a claim")
    questions = turn.completion.collaboration.open_questions
    if questions:
        lines = [re.sub(r"([\\`*_{}\[\]()<>#~!|&+\-.])", r"\\\1", question.strip())
                 for question in questions]
        paragraphs.append("## Open questions\n\n" + "\n".join(f"- {line}" for line in lines))
    return "\n\n".join(paragraphs)


def _locked_review(conn, world_id: str, confirmation: LorePageConfirmation) -> Turn:
    pointer = repository.lock_world_state(conn, world_id)
    conversation = repository.lock_conversation(conn, world_id, confirmation.conversation_id)
    if conversation is None or pointer.active_conversation_id != confirmation.conversation_id:
        raise ApplicationStateNotFoundError("Active lore review conversation not found")
    turn = repository.get_turn(conn, world_id, confirmation.turn_id)
    if (not isinstance(turn, Turn) or turn.conversation_id != confirmation.conversation_id
            or turn.status != "completed" or not isinstance(turn.completion, SurfaceNativeCompletionV1)
            or not isinstance(turn.completion.collaboration, ProposedLorePage)):
        raise ApplicationStateNotFoundError("Completed lore review not found")
    if canonical_sha256(turn.completion) != confirmation.review_sha256:
        raise ApplicationStateConflictError("Confirm the exact displayed lore revision")
    return turn


def admit_lore_save_followup(
    dsn: str, *, world_id: str, idempotency_key: UUID, conversation_id: UUID | None,
    surface_instance_id: str, document_id: str, revision: int, content_sha256: str,
) -> bool:
    """Select local routing only for the active matching review or its retained result."""
    with unit_of_work(dsn) as conn:
        retained = repository.get_turn_by_world_key(conn, world_id, idempotency_key)
        if retained is not None:
            turn, _, _, v1, v2 = retained
            return (isinstance(turn, Turn) and v1 is not None and v2 is None
                    and turn.provenance.surface_id == "build" and is_lore_save_followup(turn.user_text)
                    and (turn.status != "completed" or isinstance(turn.completion, LoreSaveReviewReference)))
        pointer = repository.get_world_state(conn, world_id)
        active_id = pointer.active_conversation_id if pointer else None
        if active_id is None or (conversation_id is not None and conversation_id != active_id):
            return False
        prior_id = conn.execute(
            """SELECT turn_id FROM agent.turn
               WHERE world_id = %s AND conversation_id = %s
                 AND status NOT IN ('failed', 'interrupted')
               ORDER BY sequence DESC LIMIT 1""",
            (world_id, active_id),
        ).fetchone()
        if prior_id is None:
            return False
        prior = repository.get_turn(conn, world_id, prior_id[0])
        if (not isinstance(prior, Turn) or prior.status != "completed"
                or prior.provenance.surface_id != "build"
                or prior.provenance.surface_instance_id != surface_instance_id
                or not isinstance(prior.completion, SurfaceNativeCompletionV1)
                or not isinstance(prior.completion.collaboration, ProposedLorePage)):
            return False
        work = prior.provenance.primary_work
        return (work.resolution == "resolved" and work.kind == "build" and work.object_id == document_id
                and work.revision == str(revision) and work.content_sha256 == content_sha256)


def resolve_lore_save_followup(
    dsn: str, *, world_id: str, conversation_id: UUID, current_turn_id: UUID,
) -> LoreSaveReviewReference | None:
    """Find the reviewed page the current Build turn can refer back to."""
    with unit_of_work(dsn) as conn:
        return resolve_lore_save_followup_locked(
            conn, world_id=world_id, conversation_id=conversation_id, current_turn_id=current_turn_id,
        )


def resolve_lore_save_followup_locked(
    conn, *, world_id: str, conversation_id: UUID, current_turn_id: UUID,
) -> LoreSaveReviewReference | None:
    pointer = repository.lock_world_state(conn, world_id)
    conversation = repository.lock_conversation(conn, world_id, conversation_id)
    if conversation is None or pointer.active_conversation_id != conversation_id:
        return None

    current = repository.get_turn(conn, world_id, current_turn_id)
    if (not isinstance(current, Turn) or current.conversation_id != conversation_id
            or current.status not in {"accepted", "running"}
            or not is_lore_save_followup(current.user_text)
            or current.provenance.surface_id != "build"
            or current.provenance.primary_work.resolution != "resolved"):
        return None

    prior_id = conn.execute(
        """SELECT turn_id FROM agent.turn
           WHERE world_id = %s AND conversation_id = %s AND sequence < %s
             AND status NOT IN ('failed', 'interrupted')
           ORDER BY sequence DESC LIMIT 1""",
        (world_id, conversation_id, current.sequence),
    ).fetchone()
    if prior_id is None:
        return None

    prior = repository.get_turn(conn, world_id, prior_id[0])
    if (not isinstance(prior, Turn) or prior.status != "completed"
            or prior.provenance.surface_id != "build"
            or prior.provenance.surface_instance_id != current.provenance.surface_instance_id
            or prior.provenance.primary_work != current.provenance.primary_work
            or not isinstance(prior.completion, SurfaceNativeCompletionV1)
            or not isinstance(prior.completion.collaboration, ProposedLorePage)):
        return None
    try:
        _require_current_review(conn, prior)
    except ApplicationStateConflictError:
        return None
    return LoreSaveReviewReference(
        conversation_id=conversation_id, turn_id=prior.turn_id,
        review_sha256=canonical_sha256(prior.completion),
        title=prior.completion.collaboration.destination.title,
    )


def prepare_lore_save_review(dsn: str, *, world_id: str, principal_subject: str,
                             confirmation: LorePageConfirmation) -> None:
    with unit_of_work(dsn) as conn:
        turn = _locked_review(conn, world_id, confirmation)
        _require_current_review(conn, turn)
        conn.execute(
            """INSERT INTO agent.lore_page_save_review (turn_id, principal_subject, review_sha256)
               VALUES (%s, %s, %s) ON CONFLICT (turn_id, principal_subject) DO NOTHING""",
            (turn.turn_id, principal_subject, confirmation.review_sha256),
        )


def confirm_lore_page(dsn: str, *, world_id: str, principal_subject: str,
                      confirmation: LorePageConfirmation, verify_source) -> LorePageReceipt:
    with unit_of_work(dsn) as conn:
        turn = _locked_review(conn, world_id, confirmation)
        existing = conn.execute(
            """SELECT principal_subject, review_sha256, document_id, revision_id
               FROM agent.lore_page_confirmation WHERE turn_id = %s""",
            (turn.turn_id,),
        ).fetchone()
        if existing is not None:
            subject, digest, document_id, revision_id = existing
            if subject != principal_subject or digest != confirmation.review_sha256:
                raise ApplicationStateConflictError("Lore confirmation differs from its original receipt")
            return LorePageReceipt(document_id=document_id, revision_id=revision_id, review_sha256=digest)

        _require_current_review(conn, turn)
        presented = conn.execute(
            """SELECT review_sha256 FROM agent.lore_page_save_review
               WHERE turn_id = %s AND principal_subject = %s""",
            (turn.turn_id, principal_subject),
        ).fetchone()
        if presented != (confirmation.review_sha256,):
            raise ApplicationStateConflictError("Open the exact lore save review before confirming")
        title = turn.completion.collaboration.destination.title
        for ordinal, citation in enumerate(turn.completion.native_body_citations):
            if verify_source(turn.turn_id, ordinal).citation != citation:
                raise ApplicationStateConflictError("Lore review source differs from its exact citation")
        page, revision = pages.create_committed_lore_page(
            conn, world_id=world_id, title=title, markdown=_body(turn),
        )
        receipt = LorePageReceipt(
            document_id=page.page.work_object_id, revision_id=revision.work_revision_id,
            review_sha256=confirmation.review_sha256,
        )
        conn.execute(
            """INSERT INTO agent.lore_page_confirmation
               (turn_id, review_sha256, principal_subject, document_id, revision_id)
               VALUES (%s, %s, %s, %s, %s)""",
            (turn.turn_id, receipt.review_sha256, principal_subject, receipt.document_id, receipt.revision_id),
        )
        return receipt


def _require_current_review(conn, turn: Turn) -> None:
    title = turn.completion.collaboration.destination.title
    later = conn.execute(
        """SELECT 1 FROM agent.turn
           WHERE world_id = %s AND conversation_id = %s AND sequence > %s
             AND status = 'completed'
             AND completion->'collaboration'->>'kind' = 'lore_page'
             AND lower(completion->'collaboration'->'destination'->>'title') = lower(%s)
           LIMIT 1""",
        (turn.world_id, turn.conversation_id, turn.sequence, title),
    ).fetchone()
    if later is not None:
        raise ApplicationStateConflictError("This lore draft has been superseded")
