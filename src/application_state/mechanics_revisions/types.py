"""Closed, immutable intent and versioned append-operation outcomes."""
from datetime import datetime
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from application_state.world_mechanics.types import MechanicsLocator


def digest(value):
    return 'sha256:' + sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


class RevisionOperation(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    schema_: Literal['dmb_mechanics_revision_operation_v1']=Field(default='dmb_mechanics_revision_operation_v1',alias='schema')
    operation_id: UUID
    world_id: str=Field(pattern=r'^[a-z][a-z0-9_-]{0,62}$')
    draft_id: UUID
    origin: MechanicsLocator
    origin_acceptance_operation_id: str=Field(min_length=1)
    base: MechanicsLocator
    input_digest: str=Field(pattern=r'^sha256:[0-9a-f]{64}$')
    request_body: dict
    request_digest: str=Field(pattern=r'^sha256:[0-9a-f]{64}$')
    definition_digest: str=Field(pattern=r'^sha256:[0-9a-f]{64}$')
    state: Literal['prepared','outcome_unknown','committed','refused']='prepared'
    result: MechanicsLocator | None=None
    refusal_code: str | None=None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='after')
    def exact_intent(self):
        if self.base.statblock_id!=self.origin.statblock_id:
            raise ValueError('Revision parent changed logical statblock')
        if self.request_body.get('parent_revision_id')!=self.base.revision_id or self.request_body.get('idempotency_key')!=str(self.operation_id):
            raise ValueError('Revision request changed parent or operation key')
        submitted=dict(operation_id=str(self.operation_id),world_id=self.world_id,base=self.base.model_dump(mode='json'),
            definition=self.request_body.get('definition'),change_summary=self.request_body.get('change_summary'))
        if digest(submitted)!=self.input_digest:
            raise ValueError('Submitted input digest changed')
        if digest(self.request_body)!=self.request_digest:
            raise ValueError('Revision request digest changed')
        if (self.state=='committed')!=(self.result is not None) or (self.state=='refused')!=(self.refusal_code is not None):
            raise ValueError('Revision outcome disagrees with state')
        if self.result and (self.result.statblock_id!=self.base.statblock_id or self.result.definition_digest!=self.definition_digest
            or self.result.revision_id==self.base.revision_id or self.result.contract!=self.base.contract
            or self.result.contract_version!=self.base.contract_version):
            raise ValueError('Revision result changed requested identity')
        return self


    @property
    def change_summary(self):
        return self.request_body['change_summary']


class RevisionOperationSummary(BaseModel):
    """Metadata page only; never loads a submitted definition to list versions."""
    model_config=ConfigDict(extra='forbid',frozen=True)
    schema_: Literal['dmb_mechanics_revision_summary_v1']=Field(alias='schema')
    operation_id: UUID
    world_id: str
    draft_id: UUID
    origin: MechanicsLocator
    origin_acceptance_operation_id: str
    base: MechanicsLocator
    definition_digest: str
    state: Literal['prepared','outcome_unknown','committed','refused']
    result: MechanicsLocator | None
    refusal_code: str | None
    change_summary: str
    created_at: datetime

    @model_validator(mode='after')
    def exact_outcome(self):
        if (self.state=='committed')!=(self.result is not None) or (self.state=='refused')!=(self.refusal_code is not None):
            raise ValueError('Revision summary outcome disagrees with state')
        if self.base.statblock_id!=self.origin.statblock_id or (self.result and (
            self.result.statblock_id!=self.base.statblock_id or self.result.definition_digest!=self.definition_digest)):
            raise ValueError('Revision summary has inconsistent identity')
        return self
