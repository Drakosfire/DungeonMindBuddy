"""Confirm exactly one retained native lore draft inside the APP transaction."""

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
from .types import Turn


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
