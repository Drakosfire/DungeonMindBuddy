"""Role context bounds: prepared bytes and durable APP are separate invariants."""
import json

import pytest

from application_state.agent_conversation import types as ledger
from apps.live_control_server.services import build_jev_writer as writer


def projection(size):
    return writer.WriterProjection(json.dumps({"source": "x" * size}), 0, "prior")


def wire(staged):
    return json.dumps(staged.kwargs(), ensure_ascii=False, separators=(",", ":"))


def total(raw):
    return len(raw.encode()) + 64 * (1 + writer._json_nodes(json.loads(raw))) + writer.OUTPUT_RESERVE


def test_total_role_boundary_includes_output_and_preserves_legacy_allowance():
    budget = writer.role_budget()
    size = budget["context_limit_tokens"] - total(wire(projection(0)))
    staged = projection(size)
    raw = wire(staged)
    assert total(raw) == 128000
    writer.validate_body(raw, staged, budget=budget)
    with pytest.raises(ValueError, match="context allowance"):
        writer.validate_body(wire(projection(size + 1)), projection(size + 1), budget=budget)
    with pytest.raises(ValueError, match="allowance"):
        writer.validate_body(raw, staged)
    # Existing callers retain the exact old64000 total boundary.
    oldsize = 64000 - total(wire(projection(0)))
    writer.validate_body(wire(projection(oldsize)), projection(oldsize))
    with pytest.raises(ValueError, match="context allowance"):
        writer.validate_body(wire(projection(oldsize + 1)), projection(oldsize + 1))


@pytest.mark.parametrize("key,value", [
    ("provider", "typesafe"), ("model", "other-model"), ("api_mode", "typesafe_decision"),
    ("context_limit_tokens", 256000), ("output_reserve_tokens", 0),
    ("estimator", "unverified-counter"),
])
def test_descriptor_cannot_expand_or_change_provider_role(key, value):
    budget = writer.role_budget()
    budget[key] = value
    with pytest.raises(ValueError):
        writer.validate_body(wire(projection(1)), projection(1), budget=budget)


def test_raw_role_bound_is_independent_and_missing_descriptor_is_not_a_grant():
    staged = projection(128000)
    with pytest.raises(ValueError, match="raw request"):
        writer.validate_body(wire(staged), staged, budget=writer.role_budget())
    with pytest.raises(ValueError):
        writer.validate_body(wire(projection(1)), projection(1), budget={})
    assert "writer_context_budget" not in ledger.BuildJointSupportActionControllerWriterPolicyV1.model_fields
    assert "writer_context_budget" not in ledger.BuildEstimatedActionControllerWriterPolicyV1.model_fields
