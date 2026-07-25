#!/usr/bin/env python3
"""Capture SBW07a create/read Server transcripts from DungeonMindServer TestClient.

Run from a DungeonMindServer checkout (uv env with statblocks_v1 installed):

  uv run python /path/to/DungeonMindBuddy/scripts/capture_sbw07a_server_create_transcripts.py \\
    --buddy-repo /path/to/DungeonMindBuddy \\
    --out-subdir tests/fixtures/statblocks/v1/server_transcripts

Writes request/response pairs plus MANIFEST.json citing this Server commit and the
server-owned tests that already prove the same behaviors.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _git_rev_parse(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _git_subject(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%s"], cwd=repo, text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--buddy-repo",
        type=Path,
        required=True,
        help="DungeonMindBuddy repo root (fixture destination)",
    )
    parser.add_argument(
        "--server-repo",
        type=Path,
        default=Path.cwd(),
        help="DungeonMindServer repo root (default: cwd)",
    )
    parser.add_argument(
        "--out-subdir",
        type=str,
        default="tests/fixtures/statblocks/v1/server_transcripts",
    )
    args = parser.parse_args()

    # Import Server test stack only after resolving paths.
    from fastapi.testclient import TestClient

    from statblocks_v1.api.dependencies import (
        get_candidate_repository,
        get_clock,
        get_persistence_repository,
        get_revision_service,
    )
    from statblocks_v1.application.revisions import RevisionServiceV1
    from statblocks_v1.infrastructure.memory_repositories import (
        DeterministicIdFactory,
        InMemoryCandidateRepository,
        InMemoryStatblockPersistenceRepository,
    )
    from statblocks_v1.testing import create_test_app

    server_repo = args.server_repo.resolve()
    buddy_repo = args.buddy_repo.resolve()
    out_dir = buddy_repo / args.out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    fixture_root = server_repo / "Docs/Design/fixtures/dungeonbuddy-statblock-v1"
    definition = json.loads((fixture_root / "simple_bruiser.json").read_text())
    invalid = json.loads((fixture_root / "unknown_resource_pool.json").read_text())

    import os

    from statblocks_v1.api.dependencies import INTERNAL_KEY_ENV, INTERNAL_KEY_HEADER

    auth_key = "sbw07a-capture-internal-key"
    os.environ[INTERNAL_KEY_ENV] = auth_key
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candidates = InMemoryCandidateRepository(clock=lambda: now)
    persistence = InMemoryStatblockPersistenceRepository(
        clock=lambda: now, id_factory=DeterministicIdFactory()
    )
    service = RevisionServiceV1(
        persistence=persistence, candidates=candidates, clock=lambda: now
    )
    app = create_test_app()
    app.dependency_overrides[get_candidate_repository] = lambda: candidates
    app.dependency_overrides[get_persistence_repository] = lambda: persistence
    app.dependency_overrides[get_revision_service] = lambda: service
    app.dependency_overrides[get_clock] = lambda: (lambda: now)
    client = TestClient(app)
    headers = {INTERNAL_KEY_HEADER: auth_key}

    def create_payload(defn: dict, key: str = "sbw07a-create-1", **extra) -> dict:
        payload = {
            "idempotency_key": key,
            "definition": defn,
            "change_summary": "Accepted after DungeonBuddy review.",
            "actor": "user_123",
            "accepted_through": {"surface": "review_panel"},
        }
        payload.update(extra)
        return payload

    transcripts: dict[str, object] = {}

    # 1) First create
    create_req = create_payload(definition, "sbw07a-create-1")
    create_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=create_req,
        headers=headers,
    )
    assert create_res.status_code == 200, create_res.text
    create_body = create_res.json()
    transcripts["create_success"] = {
        "request": {"method": "POST", "path": "/api/internal/dungeonbuddy/v1/statblocks", "json": create_req},
        "response": {"status": create_res.status_code, "json": create_body},
    }

    # 2) Same-key same-body replay
    replay_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=create_req,
        headers=headers,
    )
    assert replay_res.status_code == 200, replay_res.text
    replay_body = replay_res.json()
    assert replay_body["revision"]["revision_id"] == create_body["revision"]["revision_id"]
    assert replay_body["revision"]["definition_digest"] == create_body["revision"]["definition_digest"]
    assert replay_body["statblock"]["statblock_id"] == create_body["statblock"]["statblock_id"]
    transcripts["same_key_same_body_replay"] = {
        "request": {"method": "POST", "path": "/api/internal/dungeonbuddy/v1/statblocks", "json": create_req},
        "first_response": {"status": 200, "json": create_body},
        "second_response": {"status": replay_res.status_code, "json": replay_body},
        "asserted_equal_fields": [
            "statblock.statblock_id",
            "revision.revision_id",
            "revision.definition_digest",
            "revision.contract",
            "revision.contract_version",
        ],
    }

    # 3) Same-key changed-body conflict (new key space so we don't collide with above)
    conflict_key = "sbw07a-conflict-1"
    original_req = create_payload(definition, conflict_key)
    original_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=original_req,
        headers=headers,
    )
    assert original_res.status_code == 200, original_res.text
    changed_req = copy.deepcopy(original_req)
    changed_req["change_summary"] = "A changed acceptance decision."
    conflict_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=changed_req,
        headers=headers,
    )
    assert conflict_res.status_code == 409, conflict_res.text
    assert conflict_res.json()["error"]["code"] == "idempotency_conflict"
    transcripts["same_key_changed_body_conflict"] = {
        "original_request": {
            "method": "POST",
            "path": "/api/internal/dungeonbuddy/v1/statblocks",
            "json": original_req,
        },
        "original_response": {"status": 200, "json": original_res.json()},
        "changed_request": {
            "method": "POST",
            "path": "/api/internal/dungeonbuddy/v1/statblocks",
            "json": changed_req,
        },
        "conflict_response": {"status": conflict_res.status_code, "json": conflict_res.json()},
    }

    # 4) Exact revision read of first create
    sid = create_body["statblock"]["statblock_id"]
    rid = create_body["revision"]["revision_id"]
    read_path = f"/api/internal/dungeonbuddy/v1/statblocks/{sid}/revisions/{rid}"
    read_res = client.get(read_path, headers=headers)
    assert read_res.status_code == 200, read_res.text
    read_body = read_res.json()
    assert read_body["statblock_id"] == sid
    assert read_body["revision_id"] == rid
    assert read_body["definition_digest"] == create_body["revision"]["definition_digest"]
    transcripts["create_to_exact_read"] = {
        "create_response": {"status": 200, "json": create_body},
        "exact_read_request": {"method": "GET", "path": read_path},
        "exact_read_response": {"status": read_res.status_code, "json": read_body},
    }

    # 5) Persistence validation failed (non-begin)
    invalid_req = create_payload(invalid, "sbw07a-invalid-persist")
    invalid_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=invalid_req,
        headers=headers,
    )
    assert invalid_res.status_code == 422, invalid_res.text
    invalid_body = invalid_res.json()
    assert invalid_body["error"]["code"] == "validation_failed"
    assert invalid_body["error"]["details"]["is_persistence_ready"] is False
    transcripts["persistence_validation_failed"] = {
        "request": {
            "method": "POST",
            "path": "/api/internal/dungeonbuddy/v1/statblocks",
            "json": invalid_req,
        },
        "response": {"status": invalid_res.status_code, "json": invalid_body},
        "server_source_fixture": "Docs/Design/fixtures/dungeonbuddy-statblock-v1/unknown_resource_pool.json",
    }

    # 6) invalid_request before handler (open provenance rejected)
    spoofed = create_payload(definition, "sbw07a-invalid-request")
    spoofed["provenance"] = {
        "candidate": {
            "candidate_id": "cand_forged",
            "accepted_definition_changed": False,
        }
    }
    bad_req_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=spoofed,
        headers=headers,
    )
    assert bad_req_res.status_code == 422, bad_req_res.text
    assert bad_req_res.json()["error"]["code"] == "invalid_request"
    transcripts["request_validation_failed"] = {
        "request": {
            "method": "POST",
            "path": "/api/internal/dungeonbuddy/v1/statblocks",
            "json": spoofed,
        },
        "response": {"status": bad_req_res.status_code, "json": bad_req_res.json()},
        "server_owned_test": (
            "tests/statblocks_v1/api/test_statblock_resource_routes.py::"
            "test_open_provenance_field_rejected_and_actor_is_not_created_by"
        ),
    }

    # Write individual leaf fixtures used by Buddy client tests (stable names).
    leaf = {
        "create-request.json": create_req,
        "create-response.json": create_body,
        "create-replay-second-response.json": replay_body,
        "create-idempotency-conflict.json": conflict_res.json(),
        "create-conflict-original-response.json": original_res.json(),
        "create-conflict-changed-request.json": changed_req,
        "exact-revision-response.json": read_body,
        "create-persistence-validation-failed.json": invalid_body,
        "create-invalid-request.json": bad_req_res.json(),
    }
    fixtures_dir = buddy_repo / "tests/fixtures/statblocks/v1"
    for name, payload in leaf.items():
        (fixtures_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    for name, payload in transcripts.items():
        (out_dir / f"{name}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )

    manifest = {
        "schema": "sbw07a_server_create_transcript_manifest_v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "dungeonmind_server": {
            "commit": _git_rev_parse(server_repo),
            "subject": _git_subject(server_repo),
            "repo_path_at_capture": str(server_repo),
        },
        "server_owned_tests": [
            {
                "path": "tests/statblocks_v1/api/test_statblock_resource_routes.py",
                "names": [
                    "test_create_append_and_exact_replay",
                    "test_create_idempotent_replay_binds_observability",
                    "test_write_idempotency_parent_stale_and_exact_locator_errors",
                    "test_persistence_validation_failure_returns_receipt",
                    "test_open_provenance_field_rejected_and_actor_is_not_created_by",
                    "test_idempotency_conflict_before_validation_for_changed_invalid_payload",
                ],
                "proves": [
                    "same-key same-body replay returns identical revision identity",
                    "same-key changed-body returns idempotency_conflict 409",
                    "exact revision read matches create locator/digest",
                    "persistence validation_failed includes is_persistence_ready=false",
                    "invalid_request occurs before create persistence",
                ],
            }
        ],
        "server_source_fixtures": [
            "Docs/Design/fixtures/dungeonbuddy-statblock-v1/simple_bruiser.json",
            "Docs/Design/fixtures/dungeonbuddy-statblock-v1/unknown_resource_pool.json",
        ],
        "capture_script": "scripts/capture_sbw07a_server_create_transcripts.py",
        "transcripts": sorted(transcripts.keys()),
        "leaf_fixtures": sorted(leaf.keys()),
        "notes": [
            "Transcripts were recorded from DungeonMindServer create_test_app() TestClient, not invented by Buddy mocks.",
            "Buddy client tests must consume these recorded bodies; mocks may only replay recorded Server responses.",
            "validation_failed is terminal only when details.is_persistence_ready is exactly false.",
        ],
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"out_dir": str(out_dir), "server_commit": manifest["dungeonmind_server"]["commit"]}, indent=2))


if __name__ == "__main__":
    main()
