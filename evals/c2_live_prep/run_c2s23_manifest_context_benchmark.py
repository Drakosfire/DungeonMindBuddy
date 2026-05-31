#!/usr/bin/env python3
"""Compatibility entrypoint for the C2S23 trace adapter.

Deprecated name kept for continuity with earlier artifacts. The active
implementation lives in adapt_c2s23_dogfood_traces_to_context_packets.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_main():
    here = Path(__file__).resolve().parent
    target = here / "adapt_c2s23_dogfood_traces_to_context_packets.py"
    spec = importlib.util.spec_from_file_location("c2s23_trace_adapter", target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load adapter module from {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


main = _load_main()


if __name__ == "__main__":
    raise SystemExit(main())
