#!/usr/bin/env python3
"""Start live-control FastAPI pinned to the accepted current-corpus World.

Loads dotenv for secrets, then overrides World Graph authority to the
acceptance database so main.py's dotenv reload cannot point at a dead DSN.
Evaluation-only helper — not a production entrypoint.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--acceptance-dsn",
        required=True,
        help="Acceptance World Graph Postgres DSN (not logged).",
    )
    parser.add_argument(
        "--live-session-dir",
        required=True,
        help="Isolated copied live-session fixture directory.",
    )
    parser.add_argument(
        "--hermes-model",
        default=None,
        help="Optional DUNGEONMIND_HERMES_GRAPH_MODEL override (e.g. gpt-5.6-luna).",
    )
    args = parser.parse_args()

    from src.bootstrap_env import load_dungeonmindbuddy_dotenv
    import src.bootstrap_env as bootstrap_env

    load_dungeonmindbuddy_dotenv(override=True)
    # Prevent apps.live_control_server.main from re-clobbering the pin.
    bootstrap_env.load_dungeonmindbuddy_dotenv = lambda **_kwargs: None

    def _pin() -> None:
        os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY"] = "dungeonmind"
        os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = args.acceptance_dsn
        os.environ["DUNGEONMIND_DATABASE_URL"] = args.acceptance_dsn
        os.environ["DUNGEONMIND_LIVE_SESSION_DIR"] = args.live_session_dir
        if args.hermes_model:
            os.environ["DUNGEONMIND_HERMES_GRAPH_MODEL"] = args.hermes_model

    _pin()
    from apps.live_control_server.main import app
    _pin()

    from apps.live_control_server import config

    url = config.world_graph_authority_database_url() or ""
    if "dmb_current_corpus_acceptance_v1" not in url:
        print("refusing to start: acceptance DB not selected", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("refusing to start: OPENAI_API_KEY missing", file=sys.stderr)
        return 2
    print("authority_url_ok")
    print(
        "hermes_model",
        os.environ.get("DUNGEONMIND_HERMES_GRAPH_MODEL") or "(policy default)",
    )

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
