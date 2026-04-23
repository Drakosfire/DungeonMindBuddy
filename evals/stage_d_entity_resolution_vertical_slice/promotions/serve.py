#!/usr/bin/env python3
"""Tiny dev server for the Stage D proposal review component.

Serves the `promotions/` directory and exposes a single JSON endpoint —
`/api/sidecars` — that lists every `*_stage_d_promotion_*.json` file on
disk, newest first, with the campaign id / generated_at / item counts
already extracted. The viewer.html harness calls this on load so the user
never has to hand-pick a file.

Usage:

    cd evals/stage_d_entity_resolution_vertical_slice/promotions
    python serve.py            # binds http://localhost:8765
    python serve.py --port 9000

Then open http://localhost:8765/viewer.html and start reviewing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PORT = 8765


def _list_sidecars():
    """Return sidecar metadata sorted newest-first."""
    out = []
    for path in HERE.glob("*_stage_d_promotion_*.json"):
        entry = {
            "filename": path.name,
            "mtime": path.stat().st_mtime,
        }
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            entry.update(
                campaign_id=data.get("campaign_id"),
                generated_at=data.get("generated_at"),
                counts={
                    "records": len(data.get("proposed_new_records") or []),
                    "aliases": len(data.get("proposed_aliases") or []),
                    "unresolvable": len(data.get("unresolvable") or []),
                },
                cost_usd=(data.get("cost") or {}).get("total_usd"),
            )
        except Exception as exc:  # noqa: BLE001 - report read errors to UI
            entry["error"] = f"{type(exc).__name__}: {exc}"
        out.append(entry)
    out.sort(key=lambda e: e.get("mtime", 0), reverse=True)
    return out


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter than the default
        sys.stderr.write("[serve] " + (fmt % args) + "\n")

    def end_headers(self):
        # No-cache so the viewer always sees the latest disk state.
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def do_GET(self):  # noqa: N802 - http.server API
        if self.path.split("?", 1)[0] == "/api/sidecars":
            body = json.dumps({"sidecars": _list_sidecars()}, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    os.chdir(HERE)
    print(
        f"[serve] {HERE}\n"
        f"[serve] open http://{args.host}:{args.port}/viewer.html",
        file=sys.stderr,
    )
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[serve] stopped", file=sys.stderr)
