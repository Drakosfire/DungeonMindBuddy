#!/usr/bin/env python3
"""Capture SBW07a create/read Server transcripts from a clean DungeonMindServer checkout.

Run from a DungeonMindServer checkout (uv env with statblocks_v1 installed):

  uv run python /path/to/DungeonMindBuddy/scripts/capture_sbw07a_server_create_transcripts.py \\
    --buddy-repo /path/to/DungeonMindBuddy \\
    --server-repo /path/to/DungeonMindServer

Hard requirements:
- Server worktree must be clean (no staged/unstaged/untracked changes that affect capture).
- Imported ``statblocks_v1`` package path must resolve inside ``--server-repo``.
- Recorded OpenAPI fingerprint must match Buddy's vendored OPENAPI_FINGERPRINT unless
  ``--allow-fingerprint-mismatch`` is set (escape hatch only).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _assert_clean_worktree(server_repo: Path) -> None:
    status = _git(server_repo, "status", "--porcelain")
    if status:
        raise SystemExit(
            "Server worktree is dirty; refuse to capture provenance-bearing transcripts.\n"
            f"git status --porcelain:\n{status}\n"
            "Use a clean detached worktree of the intended commit."
        )


def _assert_package_from_checkout(server_repo: Path) -> Path:
    import statblocks_v1

    package_file = Path(statblocks_v1.__file__).resolve()
    package_root = package_file.parent.resolve()
    server_root = server_repo.resolve()
    try:
        package_root.relative_to(server_root)
    except ValueError as exc:
        raise SystemExit(
            "Imported statblocks_v1 is not from --server-repo.\n"
            f"  server_repo={server_root}\n"
            f"  package={package_file}\n"
            "Run the capture script with PYTHONPATH/cwd pointing at the clean checkout."
        ) from exc
    return package_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--buddy-repo", type=Path, required=True)
    parser.add_argument("--server-repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--out-subdir",
        type=str,
        default="tests/fixtures/statblocks/v1/server_transcripts",
    )
    parser.add_argument(
        "--allow-fingerprint-mismatch",
        action="store_true",
        help="Escape hatch only; do not use for SBW07a merge evidence.",
    )
    args = parser.parse_args()

    server_repo = args.server_repo.resolve()
    buddy_repo = args.buddy_repo.resolve()
    _assert_clean_worktree(server_repo)
    package_file = _assert_package_from_checkout(server_repo)

    openapi_path = server_repo / "openapi" / "dungeonbuddy-statblocks-v1.json"
    if not openapi_path.is_file():
        raise SystemExit(f"Missing Server OpenAPI artifact: {openapi_path}")
    server_openapi_fingerprint = _sha256_file(openapi_path)

    # Import Buddy fingerprint without importing the live Buddy app stack.
    sys.path.insert(0, str(buddy_repo))
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
        OPENAPI_FINGERPRINT as BUDDY_OPENAPI_FINGERPRINT,
    )

    if (
        server_openapi_fingerprint != BUDDY_OPENAPI_FINGERPRINT
        and not args.allow_fingerprint_mismatch
    ):
        raise SystemExit(
            "Server OpenAPI fingerprint does not match Buddy vendored contract.\n"
            f"  server={server_openapi_fingerprint}\n"
            f"  buddy ={BUDDY_OPENAPI_FINGERPRINT}\n"
            "Land the structural HP/AC/Phases contract sync first, or capture from a "
            "clean Server revision that matches the currently vendored Buddy OpenAPI."
        )

    import os

    from fastapi.testclient import TestClient

    from statblocks_v1.api.dependencies import (
        INTERNAL_KEY_ENV,
        INTERNAL_KEY_HEADER,
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

    out_dir = buddy_repo / args.out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    fixture_root = server_repo / "Docs/Design/fixtures/dungeonbuddy-statblock-v1"
    simple_bruiser_path = fixture_root / "simple_bruiser.json"
    unknown_pool_path = fixture_root / "unknown_resource_pool.json"
    definition = json.loads(simple_bruiser_path.read_text())
    invalid = json.loads(unknown_pool_path.read_text())

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

    create_req = create_payload(definition, "sbw07a-create-1")
    create_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=create_req,
        headers=headers,
    )
    assert create_res.status_code == 200, create_res.text
    create_body = create_res.json()
    transcripts["create_success"] = {
        "request": {
            "method": "POST",
            "path": "/api/internal/dungeonbuddy/v1/statblocks",
            "json": create_req,
        },
        "response": {"status": create_res.status_code, "json": create_body},
    }

    replay_res = client.post(
        "/api/internal/dungeonbuddy/v1/statblocks",
        json=create_req,
        headers=headers,
    )
    assert replay_res.status_code == 200, replay_res.text
    replay_body = replay_res.json()
    assert replay_body["revision"]["revision_id"] == create_body["revision"]["revision_id"]
    assert (
        replay_body["revision"]["definition_digest"]
        == create_body["revision"]["definition_digest"]
    )
    assert replay_body["statblock"]["statblock_id"] == create_body["statblock"]["statblock_id"]
    transcripts["same_key_same_body_replay"] = {
        "request": {
            "method": "POST",
            "path": "/api/internal/dungeonbuddy/v1/statblocks",
            "json": create_req,
        },
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
        "conflict_response": {
            "status": conflict_res.status_code,
            "json": conflict_res.json(),
        },
    }

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
        "server_source_fixture": str(
            unknown_pool_path.relative_to(server_repo)
        ),
    }

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

    # Prove create request body is an untransformed copy of the source fixture definition.
    if create_req["definition"] != definition:
        raise SystemExit(
            "Capture mutated simple_bruiser definition before create; refuse to write transcripts."
        )

    manifest = {
        "schema": "sbw07a_server_create_transcript_manifest_v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "dungeonmind_server": {
            "commit": _git(server_repo, "rev-parse", "HEAD"),
            "subject": _git(server_repo, "log", "-1", "--format=%s"),
            "repo_path_at_capture": str(server_repo),
            "worktree_clean": True,
            "statblocks_v1_package_path": str(package_file),
            "openapi_path": str(openapi_path.relative_to(server_repo)),
            "openapi_fingerprint": server_openapi_fingerprint,
        },
        "buddy_vendored_openapi_fingerprint": BUDDY_OPENAPI_FINGERPRINT,
        "openapi_fingerprint_match": server_openapi_fingerprint == BUDDY_OPENAPI_FINGERPRINT,
        "server_source_fixtures": [
            {
                "path": str(simple_bruiser_path.relative_to(server_repo)),
                "sha256": _sha256_file(simple_bruiser_path),
            },
            {
                "path": str(unknown_pool_path.relative_to(server_repo)),
                "sha256": _sha256_file(unknown_pool_path),
            },
        ],
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
        "capture_script": "scripts/capture_sbw07a_server_create_transcripts.py",
        "transcripts": sorted(transcripts.keys()),
        "leaf_fixtures": sorted(leaf.keys()),
        "leaf_fixture_sha256": {
            name: _sha256_bytes(
                json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
            )
            for name, payload in leaf.items()
        },
        "notes": [
            "Transcripts were recorded from a clean DungeonMindServer checkout TestClient.",
            "Capture refuses dirty worktrees and imported packages outside --server-repo.",
            "Create request definition bytes match the cited simple_bruiser source fixture.",
            "Buddy client tests must consume these recorded bodies; mocks may only replay them.",
            "validation_failed is terminal only when details.is_persistence_ready is exactly false.",
        ],
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "server_commit": manifest["dungeonmind_server"]["commit"],
                "openapi_fingerprint": server_openapi_fingerprint,
                "fingerprint_match": manifest["openapi_fingerprint_match"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
