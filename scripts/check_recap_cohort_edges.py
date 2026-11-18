#!/usr/bin/env python3
"""Validate and publish reviewed recap cohorts through the governed Buddy API.

Use --publish with the reviewed candidate, edge manifest, and base request.
This replaces the Event-only rehearsal publisher publish-reviewed-cohort-events.py.
Set BUDDY_AUTH_TOKEN to the authorized Buddy GM bearer token.
"""

import argparse
import json
import os
from pathlib import Path

import httpx

from apps.live_control_server.models.native_recap_preparation import NativeRecapPrepareRequest
from graph_memory.ingestion.cohort_edge_review import build_prepare_request, validate, validate_prepare


def publish_cohort(client, candidate, manifest, base):
    request = NativeRecapPrepareRequest.model_validate(
        build_prepare_request(candidate, manifest, base)
    ).model_dump(mode="json")
    prepared = client.post("/api/live/extract-promote/native-prepare", json=request)
    prepared.raise_for_status()
    result = prepared.json()
    if result["status"] == "held":
        return result
    if result["status"] != "prepared" or result["envelope"]["review"] != request:
        raise ValueError("Server did not prepare the reviewed cohort")
    packet = {field: result[field] for field in ("envelope", "prepared", "token")}
    confirmed = client.post("/api/live/extract-promote/native-confirm", json=packet)
    confirmed.raise_for_status()
    return confirmed.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("manifest", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-request", type=Path)
    mode.add_argument("--build-prepare-request", type=Path, metavar="BASE_REQUEST")
    mode.add_argument("--publish", type=Path, metavar="BASE_REQUEST")
    parser.add_argument("--base-url", help="Buddy origin for --publish")
    args = parser.parse_args()
    try:
        candidate = json.loads(args.candidate.read_text())
        manifest = json.loads(args.manifest.read_text())
        if args.publish:
            if not args.base_url:
                parser.error("--publish requires --base-url")
            base = json.loads(args.publish.read_text())
            with httpx.Client(
                base_url=args.base_url,
                headers={"Authorization": f"Bearer {os.environ['BUDDY_AUTH_TOKEN']}"},
                timeout=60,
            ) as client:
                print(json.dumps(publish_cohort(client, candidate, manifest, base), indent=2))
            return
        if args.build_prepare_request:
            base = json.loads(args.build_prepare_request.read_text())
            print(json.dumps(build_prepare_request(candidate, manifest, base), indent=2))
            return
        count = (validate_prepare(candidate, manifest, json.loads(args.prepare_request.read_text()))
                 if args.prepare_request else validate(candidate, manifest))
    except (KeyError, TypeError, ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Checked {count} explicit edge decisions.")


if __name__ == "__main__":
    main()
