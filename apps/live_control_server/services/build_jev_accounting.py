"""Experimental host accounting; explicitly not an exact Jev tokenizer contract."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Callable

from application_state.agent_conversation.build_decision_context import (
    POLICY, SELECTION, LONG_LIMIT, selected_mode, phase,
)
RAW_WIRE_LIMIT = 256_000


class DecisionCapacityError(ValueError):
    """Content-free refusal of a prepared decision at its configured capacity."""

    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExperimentalAccounting:
    """Trusted caller supplies an already loaded, offline o200k counter.

    No tokenizer installation, network loading, fallback or provider invocation
    occurs here. This opt-in estimate must not populate guaranteed-bound fields.
    """

    tokenizer_version: str
    count_tokens: Callable[[str], int] = field(repr=False, compare=False)

    def __post_init__(self):
        if (
            not isinstance(self.tokenizer_version, str)
            or not self.tokenizer_version.strip()
            or not callable(self.count_tokens)
        ):
            raise ValueError("offline tokenizer implementation required")

    @property
    def descriptor(self) -> dict:
        return {
            "policy": POLICY,
            "tokenizer": "tiktoken",
            "tokenizer_version": self.tokenizer_version,
            "encoding": "o200k_base",
            "multiplier": 2,
            "reserve": 4096,
            "raw_wire_limit_bytes": RAW_WIRE_LIMIT,
            "question_limit_tokens": 32_000,
            "request_limit_tokens": 64_000,
            "guaranteed_upper_bound": False,
            "long_question_limit_tokens": LONG_LIMIT,
            "long_request_limit_tokens": LONG_LIMIT,
            "context_selection_policy": SELECTION,
        }

    def estimate(self, value: object) -> int:
        text = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        count = self.count_tokens(text)
        if type(count) is not int or count < 0:
            raise ValueError("invalid offline tokenizer count")
        return 2 * count + 4096

    def question_estimate(self, body: dict) -> int:
        return max(self.estimate({"model": body["model"], "state": body["state"],
            "questions": {name: question}}) for name, question in body["questions"].items())

    def context_mode(self, body: dict) -> str:
        return selected_mode(phase(body), self.estimate(body), self.question_estimate(body), policy=POLICY)

    def validate(self, body: dict, raw: bytes, *, context_mode: str = "default") -> None:
        if len(raw) > RAW_WIRE_LIMIT:
            raise DecisionCapacityError("Decision raw wire exceeds experimental byte limit", code="decision_wire_capacity_exceeded")
        if body["state"].get("context_accounting") != self.descriptor:
            raise ValueError("Decision experimental accounting descriptor differs")
        if context_mode not in {"default", "long_context"}:
            raise ValueError("Invalid decision context mode")
        if context_mode == "long_context" and self.context_mode(body) != context_mode:
            raise ValueError("Long context differs from exact phase/capacity policy")
        question_limit = LONG_LIMIT if context_mode == "long_context" else 32_000
        request_limit = LONG_LIMIT if context_mode == "long_context" else 64_000
        for name, question in body["questions"].items():
            projected = {
                "model": body["model"],
                "state": body["state"],
                "questions": {name: question},
            }
            if self.estimate(projected) > question_limit:
                raise DecisionCapacityError(
                    "Decision per-question context exceeds experimental estimate",
                    code="decision_question_capacity_exceeded",
                )
        if self.estimate(body) > request_limit:
            raise DecisionCapacityError("Decision request context exceeds experimental estimate", code="decision_request_capacity_exceeded")
