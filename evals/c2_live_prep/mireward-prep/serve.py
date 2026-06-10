#!/usr/bin/env python3
"""Legacy dev server for Mireward prep static HTML.

Prefer the consolidated live-control UI dev server on port 5173. Vite serves
these static pages plus repo markdown links there; this script remains as a
fallback for opening the legacy HTML pages without the React app.

Corpus and artifact links resolve under /corpus/... and /Docs/... because the
document root is the DungeonMindBuddy repo root, not this folder.

Usage:

    cd evals/c2_live_prep/mireward-prep
    python serve.py              # http://localhost:8765/ -> index
    python serve.py --port 9000

From repo root:

    python evals/c2_live_prep/mireward-prep/serve.py
"""

from __future__ import annotations

import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
INDEX_PAGE = "/evals/c2_live_prep/mireward-prep/index.html"
ROUTE_ALIASES = {
    "/live-play": "/evals/c2_live_prep/mireward-prep/live-play.html",
    "/live-play/": "/evals/c2_live_prep/mireward-prep/live-play.html",
    "/retrieval": "/evals/c2_live_prep/mireward-prep/retrieval.html",
    "/retrieval/": "/evals/c2_live_prep/mireward-prep/retrieval.html",
}
DEFAULT_PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[mireward-prep] " + (fmt % args) + "\n")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def _redirect_root_if_needed(self) -> bool:
        path = self.path.split("?", 1)[0]
        if path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", INDEX_PAGE)
            self.end_headers()
            return True
        return False

    def _rewrite_known_route_if_needed(self) -> None:
        path, sep, query = self.path.partition("?")
        target = ROUTE_ALIASES.get(path)
        if target:
            self.path = target + (sep + query if sep else "")

    def do_HEAD(self):  # noqa: N802 - http.server API
        if self._redirect_root_if_needed():
            return
        self._rewrite_known_route_if_needed()
        super().do_HEAD()

    def do_GET(self):  # noqa: N802 - http.server API
        if self._redirect_root_if_needed():
            return
        self._rewrite_known_route_if_needed()
        super().do_GET()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    os.chdir(REPO_ROOT)
    url = f"http://{args.host}:{args.port}/"
    print(
        f"[mireward-prep] repo root: {REPO_ROOT}\n"
        f"[mireward-prep] legacy static server: open {url} (redirects to index)\n"
        f"[mireward-prep] preferred UI server: apps/live-control-ui on port 5173",
        file=sys.stderr,
    )
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[mireward-prep] stopped", file=sys.stderr)
