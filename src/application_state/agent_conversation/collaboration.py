"""Typed proposed work. Suggestions grant no execution or knowledge authority."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

POLICY = "typed_author_review_collaboration_v1"
FORMAT = "build_working_draft_answer_v2"


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProposedStep(Closed):
    text: str = Field(min_length=1)
    kind: Literal["discuss", "prepare_insertion"]

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip():
            raise ValueError("A proposed step must be readable")
        return self


class ProposedQuestion(Closed):
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip():
            raise ValueError("A proposed question must be readable")
        return self


class ProposedPlan(Closed):
    kind: Literal["plan"]
    steps: list[ProposedStep] = Field(min_length=1)


class ProposedQuestions(Closed):
    kind: Literal["questions"]
    questions: list[ProposedQuestion] = Field(min_length=1)


Collaboration = ProposedPlan | ProposedQuestions


CONNECTED_POLICY = "typed_connected_page_review_v1"
CONNECTED_FORMAT = "build_working_draft_answer_v3"


class ProposedConnectedPage(Closed):
    kind: Literal["connected_page"]
    title: str = Field(min_length=1, max_length=200, pattern=r"^[^\n\r]+$")
    read_id: str = Field(pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    quote: str = Field(min_length=1, max_length=4000)
    person_label: str | None
    relationships: list[Literal["owns", "operates"]] = Field(max_length=2)
    instructions: str = Field(max_length=8000)

    @model_validator(mode="after")
    def coherent(self):
        if (
            not self.title.strip()
            or self.title != self.title.strip()
            or not self.quote.strip()
            or self.person_label is not None
            and (
                not self.person_label.strip()
                or self.person_label != self.person_label.strip()
                or len(self.person_label) > 200
                or "\n" in self.person_label
                or "\r" in self.person_label
            )
            or bool(self.person_label) != bool(self.relationships)
            or len(set(self.relationships)) != len(self.relationships)
        ):
            raise ValueError(
                "A page review needs a title, exact quote and coherent proposed person/relationships"
            )
        return self


ConnectedCollaboration = ProposedPlan | ProposedQuestions | ProposedConnectedPage


def saved_excerpt(proposal, rows):
    """Locate a unique quoted occurrence in actual supplied material, never count model offsets."""
    matches = [row for row in rows if str(row["read_id"]) == str(proposal.read_id)]
    if len(matches) != 1:
        raise ValueError("Page review selects an unread related page")
    row = matches[0]
    body = row["markdown"]
    start = body.find(proposal.quote)
    if start < 0 or body.find(proposal.quote, start + 1) >= 0:
        raise ValueError(
            "Page review quote must select one exact occurrence in its included page"
        )
    end = start + len(proposal.quote)
    first = body.count("\n", 0, start) + 1
    last = body.count("\n", 0, end - 1) + 1
    excerpt = "\n".join(body.splitlines()[first - 1 : last])
    if not excerpt.strip() or len(excerpt) > 4000:
        raise ValueError(
            "Page review excerpt exceeds the existing connected-page source capacity"
        )
    return {
        "kind": "saved_page_excerpt",
        "document_id": str(row["page"]["document_id"]),
        "revision": row["page"]["registry_revision"],
        "content_sha256": row["page"]["content_sha256"],
        "line_start": first,
        "line_end": last,
        "selected_text": excerpt,
    }


class ProposedPlanV2(Closed):
    kind: Literal["plan"]
    objective: str = Field(min_length=1)
    steps: list[ProposedStep] = Field(min_length=1)

    @model_validator(mode="after")
    def readable_objective(self):
        if not self.objective.strip():
            raise ValueError("A plan needs a readable expected outcome")
        return self


CollaborationV2 = ProposedPlanV2 | ProposedQuestions
ConnectedCollaborationV2 = ProposedPlanV2 | ProposedQuestions | ProposedConnectedPage
