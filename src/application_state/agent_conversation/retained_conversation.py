"""Reuse existing conversation records; this module acquires no external source.

APP freezes one closure under the current turn's transaction. Presentation uses
local aliases only; original identities stay in the host-owned admission.
"""
from dataclasses import dataclass
import json

from .rules_authority_types import canonical_bytes, canonical_sha256


def admission(execution):
    from .types import BuildPriorBodyEvidenceAdmittedV2
    rows = [e for e in execution.events if isinstance(e, BuildPriorBodyEvidenceAdmittedV2)]
    if len(rows) > 1:
        raise ValueError("Duplicate retained conversation closure")
    return rows[0] if rows else None


def proposal_context(completion):
    """Explicit semantic projection of the existing visible review families."""
    value = getattr(completion, "collaboration", None)
    if value is None:
        return ()
    kind = value.kind
    if kind == "questions":
        return ("Proposed questions", *(q.text for q in value.questions))
    if kind == "plan":
        objective = getattr(value, "objective", None)
        return ("Proposed plan, not executed", *((objective,) if isinstance(objective, str) else ()),
                *(("Selected proposed step: " if getattr(step, "selected", None) is True
                   else "Unselected proposed step: " if getattr(step, "selected", None) is False
                   else "Proposed step: ") + step.text for step in value.steps))
    if kind == "lore_page":
        return ("Proposed page: " + value.destination.title, *value.open_questions)
    if kind == "connected_page":
        return ("Proposed connected page: " + value.title, value.quote, value.instructions,
                *((value.person_label,) if value.person_label else ()), *value.relationships)
    if kind == "relationship":
        return ("Proposed relationship, not published", value.source.label, value.source.kind,
                value.target.label, value.target.kind, value.predicate, value.label, value.context, value.quote)
    raise ValueError("Unclassified retained conversation review")


def capture(current, turns, *, event_id, work_event_id, pointer_revision, seed=None, discussion=False):
    from . import types as t
    from . import native_corpus as bodies
    from .rules_authority_reads import MixedCompletedTurnV1
    from .build_related_pages import RelatedPageRead

    def authored_key(basis, role, title, text):
        return canonical_sha256([basis.model_dump(mode="json"), role, title, text])

    def native_key(catalog, read):
        return canonical_sha256([catalog.model_dump(mode="json"), read.excerpt.model_dump(mode="json")])

    history, authored, native = [], {}, {}
    # A completed prior V2 is already the immutable exact prefix, not a model
    # summary. Reopen that one owner-validated closure rather than recursively
    # decoding every older closure on each follow-up synthesis.
    if seed is not None:
        if not turns:
            raise ValueError("Retained prefix requires its producing row")
        first = turns[0]
        first = first.base_projection.turn if isinstance(first, MixedCompletedTurnV1) and first.base_projection.kind == "approved" else first
        validate_binding(seed, world_id=current.world_id, conversation_id=current.conversation_id,
            turn_id=first.turn_id, attempt=first.attempt)
        if seed.conversation_sequence != first.sequence or first.status != "completed":
            raise ValueError("Retained prefix lacks its completed producing owner")
        history.extend(seed.history)
        for row in seed.authored_context:
            authored[authored_key(row.source_basis, row.role, row.title, row.text)] = dict(
                source_basis=row.source_basis, role=row.role, title=row.title, text=row.text,
                occurrences=list(row.occurrences))
        for row in seed.native_context:
            native[native_key(row.catalog, row.read)] = dict(catalog=row.catalog, read=row.read,
                occurrences=list(row.occurrences))
    for stored in turns:
        envelope = stored.envelope if isinstance(stored, MixedCompletedTurnV1) else stored
        if (envelope.world_id != current.world_id or envelope.conversation_id != current.conversation_id
                or envelope.sequence >= current.sequence or envelope.turn_id == current.turn_id):
            raise ValueError("Retained conversation escaped its frozen prior scope")
        if envelope.status not in {"completed", "failed", "interrupted"}:
            raise ValueError("In-flight work is not retained conversation context")
        approved = envelope.status == "completed"
        prior = stored
        if isinstance(stored, MixedCompletedTurnV1):
            approved = approved and stored.base_projection.kind == "approved"
            prior = stored.base_projection.turn if approved else envelope
        completion = getattr(prior, "completion", None) if approved else None
        if isinstance(stored, MixedCompletedTurnV1) and not approved:
            # The mixed owner admits only a validated object-only review here;
            # retaining its visible proposal does not admit the unclaimed reads.
            completion = getattr(stored.base_projection, "completion", None)
        history.append(t.RetainedConversationTurnV1(
            turn_id=envelope.turn_id, sequence=envelope.sequence, attempt=envelope.attempt,
            user_text=envelope.user_text,
            assistant_text=(stored.assistant_text or "") if envelope.status == "completed" else None,
            base_approved=approved,
            proposal_context=proposal_context(completion) if envelope.status == "completed" else ()))
        if not approved or prior.graph_context_execution is None:
            continue
        execution = prior.graph_context_execution
        catalogs = bodies.acquired_body_catalogs(execution)
        for event in execution.events:
            occurrence = t.RetainedContextOccurrenceV1(
                turn_id=envelope.turn_id, attempt=envelope.attempt, event_id=event.event_id)
            if isinstance(event, (bodies.NativeBodyReadObservedV1, bodies.NativeAuthoredSourceReadV1)):
                if event.excerpt is None:
                    continue
                catalog = catalogs.get(event.excerpt.catalog_sha256)
                if catalog is None or catalog.authority.managed_world_id != current.world_id:
                    raise ValueError("Retained read lacks its original owned catalog")
                key = native_key(catalog, event)
                if key not in native:
                    native[key] = dict(catalog=catalog, read=event, occurrences=[])
                native[key]["occurrences"].append(occurrence)
                continue
            title = None
            if isinstance(event, t.ValidatedBuildSectionReadV1):
                basis, text, role = event.source_basis, event.text, "saved_authored"
            elif isinstance(event, t.BuildDraftContextCapturedV1):
                snapshot = event.record.snapshot
                basis = t.BuildSourceContextBasisV1.model_validate(snapshot.saved_basis())
                text, role = snapshot.draft_markdown, "working_draft"
            elif isinstance(event, RelatedPageRead):
                basis = t.BuildSourceContextBasisV1(world_id=event.page.world_id,
                    document_id=str(event.page.document_id), registry_revision=event.page.registry_revision,
                    content_sha256=event.page.content_sha256, visibility=event.page.visibility)
                text, role, title = event.markdown, "related_authored", event.page.title
            else:
                continue
            if basis.world_id != current.world_id:
                raise ValueError("Retained authored context crossed World ownership")
            key = authored_key(basis, role, title, text)
            if key not in authored:
                authored[key] = dict(source_basis=basis, role=role, title=title, text=text, occurrences=[])
            authored[key]["occurrences"].append(occurrence)
    admission_type = t.BuildPriorBodyEvidenceAdmittedV3 if discussion else t.BuildPriorBodyEvidenceAdmittedV2
    return admission_type(
        event_id=event_id, sequence=len(current.graph_context_execution.events),
        work_event_id=work_event_id, supports=(), world_id=current.world_id,
        conversation_id=current.conversation_id, turn_id=current.turn_id, attempt=current.attempt,
        conversation_sequence=current.sequence, pointer_revision=pointer_revision,
        presentation_policy="retained_conversation_semantic_v2",
        history=tuple(history), authored_context=tuple(t.RetainedAuthoredContextV1(**row) for row in authored.values()),
        native_context=tuple(t.RetainedNativeContextV1(**row) for row in native.values()))


def dialogue_messages(execution):
    value = admission(execution)
    if value is None:
        return None
    messages = []
    for index, row in enumerate(value.history):
        for role, text in (("user", row.user_text), ("assistant", row.assistant_text)):
            if text is None:
                continue
            content = dict(conversation_turn=f"turn{index}", conversation=text)
            if role == "assistant" and row.proposal_context:
                content["proposed_review_context"] = list(row.proposal_context)
            messages.append(dict(role=role, content=canonical_bytes(content).decode()))
    return messages


def validate_dialogue_request(execution, body):
    expected = dialogue_messages(execution)
    if expected is None:
        return
    messages = body.get("input")
    if not isinstance(messages, list) or messages[:len(expected)] != expected:
        raise ValueError("Writer omitted or changed its frozen full conversation")
    for message in messages[len(expected):]:
        try:
            content = json.loads(message.get("content", ""))
        except (TypeError, ValueError):
            continue
        if isinstance(content, dict) and {"conversation", "conversation_turn"} & content.keys():
            raise ValueError("Writer appended unadmitted conversation context")


def authored_frame(execution):
    value = admission(execution)
    if value is None:
        return None
    turns = {row.turn_id: f"turn{i}" for i, row in enumerate(value.history)}
    from .model_markdown import project_model_markdown, project_retained_source_markdown
    project = (project_retained_source_markdown if value.presentation_policy == "retained_conversation_semantic_v2"
               else project_model_markdown)
    return [dict(context=f"context{i}", role=row.role + "_historical_not_played_truth",
        **({"title": row.title} if row.title is not None else {}), text=project(row.text),
        from_turns=list(dict.fromkeys(turns[o.turn_id] for o in row.occurrences)))
        for i, row in enumerate(value.authored_context)]


def validate_binding(value, *, world_id, conversation_id, turn_id, attempt):
    if (value.world_id, value.conversation_id, value.turn_id, value.attempt) != (
            world_id, conversation_id, turn_id, attempt):
        raise ValueError("Retained closure differs from its producing turn")


@dataclass(frozen=True)
class RetainedBodySupport:
    handle: str
    read: object
    catalog: object
    admission: object
    selected_lines: tuple[int, int] | None = None

    def passage(self):
        from .native_corpus import NativeBodySupport
        return NativeBodySupport(self.handle, self.read, self.catalog, self.selected_lines).passage()


def native_supports(execution):
    value = admission(execution)
    return (() if value is None else tuple(RetainedBodySupport(f"retained{i}", row.read, row.catalog, value)
                                           for i, row in enumerate(value.native_context)))


def require_current_presentation(execution):
    value = admission(execution)
    if value is not None and value.presentation_policy != "retained_conversation_semantic_v2":
        raise ValueError("Historical retained presentation is replay-only; start a fresh turn")


def native_frame_rows(execution, source_authority, selector):
    from .native_corpus import model_body_frame_rows
    from .model_markdown import project_retained_source_markdown
    rows = model_body_frame_rows(source_authority, (), selector,
        passage_supports=native_supports(execution))["excerpts"]
    value = admission(execution)
    if value is not None and value.presentation_policy == "retained_conversation_semantic_v2":
        rows = [row | {"text": project_retained_source_markdown(row["text"])} for row in rows]
    return rows
