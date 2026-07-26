"""SBW06a Server revise transcript provenance proofs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    OPENAPI_FINGERPRINT,
    ReviseCandidateRequestV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    ErrorEnvelopeV1,
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.models.statblock_candidate_revision import (
    source_definition_digest_from_body,
)

TRANSCRIPT_DIR = (
    Path(__file__).parent / "fixtures" / "statblocks" / "v1" / "server_revise_transcripts"
)


def _load(name: str) -> dict:
    return json.loads((TRANSCRIPT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_manifest_cites_server_commit_fingerprint_and_fixture_hashes() -> None:
    manifest = json.loads((TRANSCRIPT_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "sbw06a_server_revise_transcript_manifest_v1"
    assert manifest["provenance"] == "copied_reviewed_server_fixtures"
    server = manifest["dungeonmind_server"]
    assert server["commit"] == "2c7d2566baa744f2b1a4667761775c1dec87a2d4"
    assert server["reviewed_head"] == "1ad8de2baf0431c7ddb401cdd72389afc730519a"
    assert server["openapi_fingerprint"] == OPENAPI_FINGERPRINT
    assert manifest["buddy_vendored_openapi_fingerprint"] == OPENAPI_FINGERPRINT
    assert manifest["openapi_fingerprint_match"] is True
    for key, digest in manifest["transcripts"].items():
        path = TRANSCRIPT_DIR / f"{key}.json"
        assert path.is_file()
        observed = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        assert observed == digest


def test_revise_request_replay_and_digest_coherence() -> None:
    request = ReviseCandidateRequestV1.model_validate(_load("revise-request"))
    response = GeneratedStatblockCandidateV1.model_validate(
        _load("revise-replay-response")
    )
    assert request.request_id == "fixture-revise-source-def-1"
    assert request.actor == "fixture"
    assert response.generation_receipt is not None
    assert response.generation_receipt.request_id == request.request_id
    assert response.generation_receipt.actor == request.actor
    raw_request = _load("revise-request")
    expected_digest = source_definition_digest_from_body(raw_request["source_definition"])
    receipt_digest = response.generation_receipt.source_definition_digest
    observed = receipt_digest.root if receipt_digest is not None else None
    assert observed == expected_digest


def test_revise_changed_body_conflict_envelope() -> None:
    envelope = ErrorEnvelopeV1.model_validate(_load("revise-conflict-response"))
    assert envelope.error.code == "idempotency_conflict"
    assert envelope.error.details.get("idempotency_key") == "fixture-revise-source-def-1"
