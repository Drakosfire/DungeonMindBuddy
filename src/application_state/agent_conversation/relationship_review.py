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


from .collaboration import ProposedPlanV3
RelationshipCollaborationV3 = ProposedPlanV3 | ProposedQuestions | ProposedConnectedPage | ProposedRelationship


OUTPUT_KEY = "relationship_output_policy"
OUTPUT_POLICY = "resolved_current_saved_relationship_v1"
OUTPUT_SUFFIX = "_rel_v2"


def output_eligible(packet):
    from .build_intentional_response import POLICY as RESPONSE_POLICY, Capabilities, resolve, canonical
    contract = packet.get("response_contract")
    if not isinstance(contract, dict) or contract.get("policy") != RESPONSE_POLICY:
        return False
    caps = contract["capabilities"]
    expected = resolve(contract["requested_work"], Capabilities(tuple(caps["operations"]),
        tuple(caps["reviews"]) if caps["reviews"] is not None else None,
        caps["plan_surface"], caps["author_save"]))
    if canonical(contract) != canonical(expected):
        raise ValueError("Relationship output requires the exact resolved contract")
    return (contract["requested_work"] == "review_relationship" and contract["barrier"] is None
        and packet.get(KEY) == POLICY)


def output_enabled(packet):
    if OUTPUT_KEY not in packet:
        return False
    if packet[OUTPUT_KEY] != OUTPUT_POLICY or not output_eligible(packet):
        raise ValueError("Unknown or unadmitted relationship output policy")
    return True


def output_format_name(name, packet):
    return name + OUTPUT_SUFFIX if output_enabled(packet) else name


def restrict_output(schema, packet):
    if output_enabled(packet):
        # The finite saved-section selector is already derived by draft_schema.
        # No acquired current section means no relationship object is offered.
        schema["properties"]["collaboration"]["anyOf"] = (
            [{"$ref": "#/$defs/ProposedRelationship"}] if "ProposedRelationship" in schema["$defs"] else []
        ) + [{"type": "null"}]
    return schema
