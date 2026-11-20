#!/usr/bin/env python3
"""Run the local Play application-state bootstrap."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from application_state.local_play_bootstrap import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
