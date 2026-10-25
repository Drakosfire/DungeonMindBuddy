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
