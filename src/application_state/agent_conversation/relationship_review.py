"""A proposed review is not a published relationship or resolved identity."""
from typing import Literal
from pydantic import Field, model_validator
from .collaboration import Closed, ProposedPlan, ProposedQuestions, ProposedConnectedPage

POLICY = "typed_saved_relationship_review_v1"
FORMAT = "build_working_draft_answer_v5"
KEY = "relationship_review_policy"

class ProposedEndpoint(Closed):
    label: str = Field(min_length=1)
    kind: str = Field(min_length=1)

    @model_validator(mode="after")
    def readable(self):
        if not self.label.strip() or not self.kind.strip():
            raise ValueError("Relationship endpoints need readable labels and kinds")
        return self

class ProposedRelationship(Closed):
    kind: Literal["relationship"]
    read_id: str = Field(pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    quote: str = Field(min_length=1)
    source: ProposedEndpoint
    target: ProposedEndpoint
    predicate: str = Field(min_length=1)
    label: str = Field(min_length=1)
    context: str = Field(min_length=1)

    @model_validator(mode="after")
    def readable(self):
        if any(not getattr(self, k).strip() for k in ("quote", "predicate", "label", "context")):
            raise ValueError("Relationship review needs exact support and explicit context")
        return self

RelationshipCollaboration = ProposedPlan | ProposedQuestions | ProposedConnectedPage | ProposedRelationship

def validate_quote(proposal, rows):
    matches = [r for r in rows if str(r["read_id"]) == proposal.read_id]
    if len(matches) != 1:
        raise ValueError("Relationship review selects an unread current saved section")
    text = matches[0]["text"]
    start = text.find(proposal.quote)
    if start < 0 or text.find(proposal.quote, start + 1) >= 0:
        raise ValueError("Relationship review needs one exact quote in its saved section")

from .collaboration import ProposedPlanV2
RelationshipCollaborationV2 = ProposedPlanV2 | ProposedQuestions | ProposedConnectedPage | ProposedRelationship
