"""Exact related authored pages, separate from World evidence and write authority."""

from __future__ import annotations
from hashlib import sha256
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

POLICY = "selected_exact_related_authored_pages_v1"
ROLE = "saved_authored_reference_not_world_or_played_truth"


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PagePointer(Frozen):
    world_id: str = Field(min_length=1)
    document_id: UUID
    registry_revision: int = Field(strict=True, ge=1)
    title: str = Field(min_length=1)
    visibility: Literal["internal", "player_safe"]


class PageReference(PagePointer):
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RelatedPagesSelection(Frozen):
    kind: Literal["build_related_pages_selected_v1"] = "build_related_pages_selected_v1"
    event_id: UUID
    sequence: int = Field(strict=True, ge=0)
    controller_attempt_id: UUID
    controller_envelope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    controller_response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    document_ids: list[UUID]

    @model_validator(mode="after")
    def unique(self):
        if self.document_ids != sorted(set(self.document_ids), key=str):
            raise ValueError("Related page choices must be sorted and distinct")
        return self


class RelatedPageRead(Frozen):
    kind: Literal["build_related_page_read_v1"] = "build_related_page_read_v1"
    event_id: UUID
    sequence: int = Field(strict=True, ge=0)
    read_id: UUID
    selection_event_id: UUID
    page: PageReference
    role: Literal["saved_authored_reference_not_world_or_played_truth"] = ROLE
    markdown: str

    @model_validator(mode="after")
    def exact(self):
        if (
            sha256(self.markdown.encode("utf-8")).hexdigest()
            != self.page.content_sha256
        ):
            raise ValueError(
                "Related authored page differs from its exact saved digest"
            )
        return self


class RelatedPageInclusion(Frozen):
    kind: Literal["build_related_page_inclusion_v1"] = "build_related_page_inclusion_v1"
    event_id: UUID
    sequence: int = Field(strict=True, ge=0)
    provider_attempt_id: UUID
    envelope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    read_ids: list[UUID]


class RelatedPageDraftClaim(Frozen):
    kind: Literal["related_page_claim"]
    text: str = Field(min_length=1)
    read_id: UUID


class RelatedPageClaim(RelatedPageDraftClaim):
    page: PageReference


def question_name(index):
    return f"related_page_{index}"


def question_text(page):
    return f"Read this exact saved authored page to serve the current request: {page.title} (revision {page.registry_revision})? Read requested existing pages before choosing people or shops. Skip unrelated pages. A title is navigation, not evidence."


def catalog(policy):
    if getattr(policy, "related_page_context_policy", None) != POLICY:
        return None
    return policy.related_page_catalog


def records(execution):
    return [e for e in execution.events if isinstance(e, RelatedPageRead)]


def project(execution):
    if catalog(execution.policy) is None:
        return None
    choices = [e for e in execution.events if isinstance(e, RelatedPagesSelection)]
    empty_reviewed = not catalog(execution.policy) and not choices and any(e.kind == "build_reviewed_action_selected_v1" for e in execution.events)
    if not empty_reviewed and (len(choices) != 1 or set(choices[0].document_ids) != {
        e.page.document_id for e in records(execution)
    }):
        raise ValueError("Related authoring context requires all selected saved reads")
    return {
        "policy": POLICY,
        "role": ROLE,
        "catalog_scope": "active_committed_worldbuilding_pages_in_this_world_excluding_current",
        "absence_authority": "not_proven_by_this_saved_page_catalog",
        "availability": [
            {
                "page": p.model_dump(mode="json"),
                "acquisition": "read"
                if p.document_id in choices[0].document_ids
                else "not_read",
            }
            for p in catalog(execution.policy)
        ],
        "pages": [
            {
                "read_id": str(e.read_id),
                "page": e.page.model_dump(mode="json"),
                "markdown": e.markdown,
            }
            for e in records(execution)
        ],
    }


def validate_events(execution):
    from .types import (
        ProviderAttemptAuthorizedEventV3,
        ProviderOutcomeEventV1,
        BuildWriterEvidenceSelectionV1,
    )

    offered = catalog(execution.policy)
    events = [
        e
        for e in execution.events
        if isinstance(e, (RelatedPagesSelection, RelatedPageRead))
    ]
    inclusions = [e for e in execution.events if isinstance(e, RelatedPageInclusion)]
    if offered is None:
        if events or inclusions:
            raise ValueError("Related pages lack their frozen capability")
        return
    selections = [e for e in events if isinstance(e, RelatedPagesSelection)]
    if len(selections) > 1:
        raise ValueError("A turn selects related authored pages once")
    pointers = {p.document_id: p for p in offered or []}
    if len(pointers) != len(offered or []):
        raise ValueError("Duplicate related page catalog identity")
    for inclusion in inclusions:
        if offered is None or inclusion.read_ids != sorted(
            {e.read_id for e in records(execution) if e.sequence < inclusion.sequence},
            key=str,
        ):
            raise ValueError(
                "Related page inclusion differs from complete acquired reads"
            )
    for auth in [
        e
        for e in execution.events
        if isinstance(e, ProviderAttemptAuthorizedEventV3)
        and (e.provider, e.model, e.api_mode)
        == execution.policy.provider_roles.writer.identity()
    ]:
        included = [
            e
            for e in inclusions
            if e.provider_attempt_id == auth.provider_attempt_id
            and e.sequence < auth.sequence
        ]
        if offered is not None and (
            len(included) != 1 or included[0].envelope_sha256 != auth.envelope_sha256
        ):
            raise ValueError(
                "Related authored page writer lacks its producing exact input"
            )
    seen = set()
    read_ids = set()
    for event in events:
        if any(
            isinstance(e, BuildWriterEvidenceSelectionV1)
            or isinstance(e, ProviderAttemptAuthorizedEventV3)
            and (e.provider, e.model, e.api_mode)
            == execution.policy.provider_roles.writer.identity()
            for e in execution.events[: event.sequence]
        ):
            raise ValueError(
                "Related authoring reads cannot change after writer selection"
            )
        if isinstance(event, RelatedPagesSelection):
            auths = [
                e
                for e in execution.events[: event.sequence]
                if isinstance(e, ProviderAttemptAuthorizedEventV3)
            ]
            if (
                not auths
                or auths[-1].provider_attempt_id != event.controller_attempt_id
                or auths[-1].envelope_sha256 != event.controller_envelope_sha256
                or (auths[-1].provider, auths[-1].model, auths[-1].api_mode)
                != execution.policy.provider_roles.controller.identity()
                or not any(
                    isinstance(e, ProviderOutcomeEventV1)
                    and e.provider_attempt_id == event.controller_attempt_id
                    and e.outcome == "response_received"
                    for e in execution.events[: event.sequence]
                )
                or not set(event.document_ids) <= set(pointers)
            ):
                raise ValueError(
                    "Related page selection lacks its exact acknowledged controller"
                )
        else:
            selected = next(
                (
                    s
                    for s in selections
                    if s.event_id == event.selection_event_id
                    and s.sequence < event.sequence
                ),
                None,
            )
            if (
                selected is None
                or event.page.document_id not in selected.document_ids
                or event.page.model_dump(exclude={"content_sha256"})
                != pointers[event.page.document_id].model_dump()
                or event.page.document_id in seen
                or event.read_id in read_ids
            ):
                raise ValueError(
                    "Related page read differs from its selected exact catalog pointer"
                )
            seen.add(event.page.document_id)
            read_ids.add(event.read_id)


def validate_selection(turn, event, proof, trace):
    import math
    from generationengine.types import DecisionResult
    from .source_writer_output import strict_json

    offered = catalog(turn.graph_context_execution.policy)
    if (
        offered is None
        or not isinstance(proof, dict)
        or set(proof) != {"request_json", "response_json"}
    ):
        raise ValueError(
            "Related page selection requires its producing request and response"
        )
    request = strict_json(proof["request_json"])
    response = DecisionResult.model_validate(strict_json(proof["response_json"]))
    state = request["state"]
    if (
        sha256(proof["request_json"].encode()).hexdigest()
        != event.controller_envelope_sha256
        or sha256(proof["response_json"].encode()).hexdigest()
        != event.controller_response_sha256
        or state.get("interaction", {}).get("related_page_catalog")
        != [p.model_dump(mode="json") for p in offered]
        or any(
            p.world_id != turn.world_id
            or str(p.document_id) == turn.provenance.primary_work.object_id
            for p in offered
        )
    ):
        raise ValueError("Related page selection differs from frozen World catalog")
    captured = [
        m
        for o in (trace or {}).get("observations", [])
        if o["kind"] == "context_snapshot"
        for m in o["materials"]
        if m["item_id"].startswith(
            f"unvalidated-controller-decision:{event.controller_attempt_id}:"
        )
    ]
    if len(captured) != 1 or captured[0].get("text") != proof["response_json"]:
        raise ValueError(
            "Related page selection response was not captured for this attempt"
        )
    chosen = []
    for i, page in enumerate(offered):
        key = question_name(i)
        q = request["questions"][key]
        answer = response.answers[key]
        probs = answer.probabilities
        if (
            q.get("instructions") != question_text(page)
            or set(q.get("criteria", {})) != {"read", "skip"}
            or answer.selected not in {"read", "skip"}
            or set(probs) != {"read", "skip"}
            or any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values())
            or abs(sum(probs.values()) - 1) > 0.02
            or probs[answer.selected] != max(probs.values())
            or sum(v == probs[answer.selected] for v in probs.values()) != 1
        ):
            raise ValueError("Unresolved related page choice")
        if answer.selected == "read":
            chosen.append(page.document_id)
    if sorted(chosen, key=str) != event.document_ids:
        raise ValueError("Related page selection differs from actual controller votes")


def validate_packet(packet, execution):
    expected = project(execution)
    if expected is None:
        if "related_authored_pages" in packet:
            raise ValueError("Historical input cannot gain related authored pages")
    elif packet.get("related_authored_pages") != expected:
        raise ValueError("Related authored pages differ from exact admitted reads")


def validate_claims(completion, execution):
    rows = {e.read_id: e for e in records(execution)}
    for claim in completion.answer_segments:
        if isinstance(claim, RelatedPageClaim) and (
            claim.read_id not in rows or claim.page != rows[claim.read_id].page
        ):
            raise ValueError("Related page claim selects an unincluded exact page")


def validate_inclusion(event, execution, request_json):
    from .source_writer_output import strict_json

    if (
        not isinstance(request_json, str)
        or sha256(request_json.encode()).hexdigest() != event.envelope_sha256
    ):
        raise ValueError("Related pages require their exact producing envelope")
    request = strict_json(request_json)
    packet = (
        strict_json(request["input"])
        if isinstance(request.get("input"), str)
        else request.get("input")
    )
    if not isinstance(packet, dict):
        raise ValueError("Related authored writer input must be an object")
    validate_packet(packet, execution)
