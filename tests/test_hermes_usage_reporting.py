"""Pinned Hermes→observer→Buddy reporting, with no provider dispatch."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.live_control_server.services.agent_turn_trace import (
    estimate_model_call_cost, normalize_model_call_usage,
)

ROOT = Path(__file__).resolve().parents[1]


def _reported_usage(details):
    # The explicit override isolates preparation from the serving dependency;
    # both paths must carry the exact same checked-in patch identity.
    prepared = Path(os.environ.get("BUDDY_HERMES_USAGE_TEST_ROOT", str(ROOT)))
    source = prepared / "out/hermes-agent"
    manifest = json.loads((prepared / "out/hermes-agent-manifest.json").read_text())
    assert manifest["patch_sha256"] == hashlib.sha256(
        (ROOT / "patches/hermes-agent/0001-pre-dispatch-budget-veto.patch").read_bytes()
    ).hexdigest()
    probe = '''
import json,sys
from pathlib import Path
from types import SimpleNamespace
from openai.types.responses.response_usage import ResponseUsage
from run_agent import AIAgent
from agent.usage_pricing import normalize_usage
import agent.usage_pricing as usage_module
raw = ResponseUsage.model_validate(json.loads(sys.stdin.read()))
canonical = normalize_usage(raw,provider="openai-api",api_mode="codex_responses")
observer = AIAgent._usage_summary_for_api_request_hook(
    SimpleNamespace(provider="openai-api",api_mode="codex_responses"),
    SimpleNamespace(usage=raw),
)
print(json.dumps({"observer":observer,"canonical_prompt":canonical.prompt_tokens,
                  "canonical_input":canonical.input_tokens,"module":str(Path(usage_module.__file__).resolve())}))
'''
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(source)
    completed = subprocess.run(
        [sys.executable,"-B","-c",probe],cwd=source,env=env,
        input=json.dumps({"input_tokens":1000,"output_tokens":10,"total_tokens":1010,
                          "input_tokens_details":details,"output_tokens_details":{"reasoning_tokens":0}}),
        text=True,capture_output=True,check=True,
    )
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert Path(result["module"]).is_relative_to(source)
    return result


@pytest.mark.parametrize("writes", [200,0,None])
def test_actual_pinned_normalizer_and_hook_preserve_writes_and_missingness(writes):
    details = {"cached_tokens":100}
    if writes is not None:
        details["cache_write_tokens"] = writes
    result = _reported_usage(details)
    usage = normalize_model_call_usage(result["observer"])
    assert usage["input_tokens"] == result["canonical_prompt"] == 1000
    assert usage["output_tokens"] == 10
    assert usage["total_tokens"] == 1010
    assert usage.get("cache_write_input_tokens") == writes
    assert usage["uncached_input_tokens"] == 900 - (writes or 0)
    cost = estimate_model_call_cost(model="gpt-6-luna",usage=usage)
    if writes:
        assert cost["status"] == "unavailable" and "usd" not in cost
    else:
        assert cost["status"] == "estimated"


def test_current_responses_field_has_no_obsolete_creation_alias():
    result = _reported_usage({"cached_tokens":100,"cache_creation_tokens":200})
    usage = normalize_model_call_usage(result["observer"])
    assert "cache_write_input_tokens" not in usage
    assert usage["input_tokens"] == 1000 and usage["uncached_input_tokens"] == 900
