"""Scripted ``OpenAI`` client for planner end-to-end evals (fail loud if script runs out)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def _output_item_from_spec(item: dict[str, Any]) -> Any:
    t = item.get("type")
    if t == "function_call":
        return SimpleNamespace(
            type="function_call",
            name=item["name"],
            call_id=item["call_id"],
            arguments=item.get("arguments", "{}"),
        )
    if t == "message":
        contents: list[Any] = []
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                contents.append(SimpleNamespace(type="output_text", text=c.get("text", "")))
        return SimpleNamespace(type="message", content=contents)
    raise ValueError(f"Unknown mock output item type: {t!r} in {item!r}")


class FakeResponse:
    """Minimal Responses ``response`` object matching planner usage."""

    def __init__(self, rid: str, output_specs: list[dict[str, Any]]) -> None:
        self.id = rid
        self.output = [_output_item_from_spec(s) for s in output_specs]

    @property
    def output_text(self) -> str:
        parts: list[str] = []
        for o in self.output:
            if getattr(o, "type", None) == "message":
                for c in getattr(o, "content", []) or []:
                    if getattr(c, "type", None) == "output_text":
                        parts.append(getattr(c, "text", ""))
        return "".join(parts)


class ScriptedOpenAI:
    """
    ``client.responses.create(**kwargs)`` returns the next scripted ``FakeResponse``.

    Raises ``RuntimeError`` if the harness calls ``create`` more times than scripted
    (fail loud).
    """

    def __init__(self, response_specs: list[dict[str, Any]]) -> None:
        self._queue: list[dict[str, Any]] = list(response_specs)
        self.calls: list[dict[str, Any]] = []

    def remaining_script_steps(self) -> int:
        """How many ``responses.create`` results are left (should be 0 after a full eval turn)."""
        return len(self._queue)

    @property
    def responses(self) -> ScriptedOpenAI:
        return self

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        if not self._queue:
            raise RuntimeError(
                "ScriptedOpenAI: exhausted scripted responses (model called responses.create "
                f"more times than expected; got {len(self.calls)} calls)"
            )
        spec = self._queue.pop(0)
        return FakeResponse(str(spec["id"]), list(spec.get("output", [])))
