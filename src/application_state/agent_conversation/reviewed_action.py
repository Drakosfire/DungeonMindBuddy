"""Closed references to author-reviewed actions; APP owns their resolution."""
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .authored_graph_references import AuthoredGraphReferencesV1


class ReviewedStepReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    conversation_id: UUID
    source_turn_id: UUID
    command_id: UUID


class ReviewedStepBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference: ReviewedStepReference
    step_id: UUID
    kind: Literal["discuss", "prepare_insertion"]
    source_answer_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dispatch_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @property
    def operation(self):
        return "answer_from_sources" if self.kind == "discuss" else "propose_build_insertion"


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def admission_manifest(intent):
    """The existing model-free admission manifest, shared by its stored codecs."""
    return {"schema": "dmb_reviewed_action_admission_v1",
        "intent": intent.model_dump(mode="json", by_alias=True)}


class ReviewedStepBindingV2(ReviewedStepBinding):
    schema_: Literal['dmb_reviewed_step_binding_v2'] = Field(default='dmb_reviewed_step_binding_v2', alias='schema')
    authored_references: AuthoredGraphReferencesV1


class ReviewedDiscussionTask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    step_id: UUID
    kind: Literal['discuss']
    text: str = Field(min_length=1)


class ReviewedSiblingContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    step_id: UUID
    text: str = Field(min_length=1)
    kind: Literal['discuss', 'prepare_insertion']
    selected: bool
    status: str
    earlier_reply: str | None


class ReviewedDiscussionScopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_: Literal['dmb_reviewed_discussion_scope_v1'] = Field(default='dmb_reviewed_discussion_scope_v1', alias='schema')
    task: ReviewedDiscussionTask
    objective_context: str = Field(min_length=1)
    sibling_context: tuple[ReviewedSiblingContext, ...]

    @model_validator(mode='after')
    def isolated_task(self):
        ids=[step.step_id for step in self.sibling_context]
        if len(set(ids))!=len(ids) or self.task.step_id in ids:
            raise ValueError('Selected task and sibling context must be distinct')
        if not self.task.text.strip() or not self.objective_context.strip():
            raise ValueError('Reviewed scope requires a readable task and objective')
        return self


class ReviewedStepBindingV3(ReviewedStepBinding):
    schema_: Literal['dmb_reviewed_step_binding_v3'] = Field(default='dmb_reviewed_step_binding_v3', alias='schema')
    kind: Literal['discuss']
    authored_references: AuthoredGraphReferencesV1 | None
    scope: ReviewedDiscussionScopeV1


SCOPE_KEY = 'reviewed_discussion_scope'
SCOPE_FORMAT = 'build_reviewed_discussion_answer_v1'
SCOPE_GUIDANCE = """
reviewed_discussion_scope is the host-bound immutable selection for this continuation.
Its scope.task is the only assignment. Discuss that selected question with useful comparisons
or clarifying questions in prose. objective_context and sibling_context are reference only,
including any selected or deferred future writing. Do not draft that future writing, a page-ready
sentence, a work plan or another page review object as part of this Discuss reply.
Use collaboration:null unless an author choice needs the offered inline questions object.
Clarifying questions stay in conversation. Explain options and tradeoffs without carrying out another step or claiming a save.
"""


def writer_scope(execution):
    from .types import BuildReviewedActionSelectionV1
    selections = [e for e in execution.events if isinstance(e, BuildReviewedActionSelectionV1)]
    if len(selections) > 1:
        raise ValueError('Reviewed task requires a unique admitted selection')
    if not selections or not isinstance(selections[0].intent.reviewed_step, ReviewedStepBindingV3):
        return None
    selection = selections[0]
    binding = selection.intent.reviewed_step
    return {'selection_event_id': str(selection.event_id),
        'binding_sha256': digest(binding.model_dump(mode='json', by_alias=True)),
        'scope': binding.scope.model_dump(mode='json', by_alias=True)}


def validate_writer_scope(packet, execution):
    if packet.get(SCOPE_KEY) != writer_scope(execution):
        raise ValueError('Writer task scope differs from its immutable reviewed dispatch')
