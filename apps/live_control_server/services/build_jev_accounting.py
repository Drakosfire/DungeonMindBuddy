"""Experimental host accounting; explicitly not an exact Jev tokenizer contract."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Callable

POLICY = "o200k_double_plus_4096_experimental_v1"
RAW_WIRE_LIMIT = 256_000


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
        }

    def estimate(self, value: object) -> int:
        text = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        count = self.count_tokens(text)
        if type(count) is not int or count < 0:
            raise ValueError("invalid offline tokenizer count")
        return 2 * count + 4096

    def validate(self, body: dict, raw: bytes) -> None:
        if len(raw) > RAW_WIRE_LIMIT:
            raise ValueError("Decision raw wire exceeds experimental byte limit")
        if body["state"].get("context_accounting") != self.descriptor:
            raise ValueError("Decision experimental accounting descriptor differs")
        for name, question in body["questions"].items():
            projected = {
                "model": body["model"],
                "state": body["state"],
                "questions": {name: question},
            }
            if self.estimate(projected) > 32_000:
                raise ValueError(
                    "Decision per-question context exceeds experimental estimate"
                )
        if self.estimate(body) > 64_000:
            raise ValueError("Decision request context exceeds experimental estimate")
