"""Typed ordinary native answer and exact historical source projection."""

from typing import Literal
from pydantic import Field
from application_state.agent_conversation.native_statement_input import (
    Strict,
    NativeStatementContextReceiptV1,
)
from application_state.agent_conversation.native_statement_answer import (
    NativeStatementCompletionV1,
    NativeStatementClauseCitationV1,
)


class NativeStatementAnswerContextV1(Strict):
    schema_: Literal["dmb_native_statement_answer_context_v1"] = Field(
        default="dmb_native_statement_answer_context_v1", alias="schema"
    )
    receipt: NativeStatementContextReceiptV1
    completion: NativeStatementCompletionV1 | None
    delivery_replay: bool


class NativeStatementClauseReadV1(Strict):
    schema_: Literal["dmb_native_statement_clause_read_v1"] = Field(
        default="dmb_native_statement_clause_read_v1", alias="schema"
    )
    world_id: str
    turn_id: str
    citation_index: int
    citation: NativeStatementClauseCitationV1
    content: str


from application_state.agent_conversation.native_plan_assertions import NativeAssertionCitationV1


class NativeAssertionSourceReadV1(Strict):
    schema_: Literal['dmb_native_assertion_source_read_v1'] = Field(default='dmb_native_assertion_source_read_v1', alias='schema')
    world_id: str
    turn_id: str
    citation_index: int
    citation: NativeAssertionCitationV1
    content: str
