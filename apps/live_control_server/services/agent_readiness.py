"""Local configuration checks only: no inference, corpus reads or provider probes."""
from __future__ import annotations

import os
from typing import Literal

from apps.live_control_server.services.build_jev_runtime import PreparedBuildJevRuntime


def agent_readiness(*, surface: Literal["build", "plan", "play"], world_graph: bool,
                    build_runtime: object) -> dict:
    missing = []
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        missing.append("Answer provider is not configured.")
    if (surface == "build" or (surface == "plan" and world_graph)) and not os.environ.get("TYPESAFE_JEV_API_KEY", "").strip():
        missing.append("Decision provider is not configured.")
    if surface == "build" and not (
        isinstance(build_runtime, PreparedBuildJevRuntime)
        and build_runtime.accounting is not None
        and build_runtime.unavailable_reason is None
    ):
        missing.append("Build runtime is not prepared.")
    return {"schema": "dmb_agent_readiness_v1", "surface": surface, "world_graph": world_graph,
            "configured": not missing, "issues": missing}
