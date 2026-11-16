"""Compact replay metadata derived from the saved native execution ledger."""

from pydantic import BaseModel

ASSERTION_READ_KINDS = frozenset({
    "native_plan_assertion_read_observed_v1",
    "native_plan_assertion_read_observed_v2",
})


class NativeReplayAssertionStep(BaseModel):
    sequence: int
    revision_id: str
    assertion_ids: list[str]
    subject_ids: list[str]
    unavailable_count: int
    writer_evidence: bool


def native_assertion_steps(execution, receipt, *, start: int, stop: int | None):
    """Keep ledger sequence and identify the completed writer's exact read events."""
    if not isinstance(execution, dict) or not isinstance(receipt, dict):
        return []
    revision = (receipt.get("native_query") or {}).get("authority", {}).get("revision_id")
    if not revision:
        return []
    events = [
        event for event in execution.get("events", [])
        if event["sequence"] >= start and (stop is None or event["sequence"] < stop)
    ]
    bindings = [event for event in events if event["kind"] == "completion_binding"]
    writers = [
        event for event in events
        if len(bindings) == 1
        and event["kind"] in {"native_writer_authorized_v1", "native_build_writer_authorized_v2",
                              "plan_native_writer_authorized_v2"}
        and event["provider_attempt_id"] == bindings[0]["provider_attempt_id"]
        and event["sequence"] < bindings[0]["sequence"]
    ]
    included = set()
    if len(writers) == 1:
        included.update(writers[0].get("native_read_event_ids", ()))
        included.update(writers[0].get("native_assertion_read_event_ids", ()))
    steps = []
    for event in events:
        if event["kind"] not in ASSERTION_READ_KINDS:
            continue
        assertions = [read["assertion"] for read in event["reads"]]
        steps.append(NativeReplayAssertionStep(
            sequence=event["sequence"],
            revision_id=revision,
            assertion_ids=[assertion["assertion_id"] for assertion in assertions],
            subject_ids=list(dict.fromkeys(assertion["subject_entity_id"] for assertion in assertions)),
            unavailable_count=len(event["unavailable_assertion_ids"]),
            writer_evidence=event["event_id"] in included,
        ))
    return steps
