"""Owning proof for the internal pinned extract confirmation and recovery."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from dungeonmind.application.contribution_review_v2 import (
    finalize_contribution_review_v2,
)
from dungeonmind.application.graph_snapshot import VersionedUnionGraphSnapshotReader
from dungeonmind.contracts.contribution_review import derive_confirmation_id
from dungeonmind.contracts.contribution_review_v2 import (
    CommitConfirmationReceiptV2,
    ContributionReviewSubmissionV2,
    contribution_v2_payload_sha256,
    derive_review_intent_sha256_v2,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.memory import (
    InMemoryContributionRepository,
    InMemoryContributionReviewRepository,
    InMemoryFinalizedReviewPublicationRepository,
)

from apps.live_control_server.integrations.dungeonmind import world_graph_writes
from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest
from apps.live_control_server.models.reviewed_extract_confirmation import (
    ReviewedExtractBinding,
    TrustedGMExtractContext,
)
from apps.live_control_server.services import reviewed_extract_confirmation as subject
from apps.live_control_server.services.candidate_graph_admission import (
    canonical_candidate_digest,
)
from tests.test_reviewed_existing_relation_prepare import (
    CAMPAIGN,
    NOW,
    WORLD,
    _case,
    _policy,
    _prepare,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inputs(case: dict, *, disposition: str = "accept") -> tuple[bytes, str, bytes]:
    assertion_id = "assertion:synthetic-scout"
    effect = {
        "world_id": case["context"].native_world_id,
        "parent_revision_id": case["parent"].revision_id,
        "source_artifact_id": case["review"].source_artifact_id,
        "source_revision_id": case["review"].source_revision_id,
        "source_admission": {"content_sha256": case["review"].source_body_sha256},
        "candidate_admission": {
            "candidate_digest": canonical_candidate_digest(
                json.loads(case["candidate_path"].read_bytes())
            ),
            "candidate_locator": str(case["candidate_path"]),
        },
        "contribution_meta": {"campaign_scope": case["context"].campaign_id},
        "verified_source_uri": "repo://synthetic/source.md",
        "accepted_proposals": [
            {
                "assertion_id": assertion_id,
                "acceptance_state": "accepted",
                "value": {
                    "evidence": [
                        {
                            "source_artifact_id": case["review"].source_artifact_id,
                            "source_span_ref_id": case["span_id"],
                        }
                    ]
                },
            }
        ],
    }
    package = {
        "proposal_id": "proposal:synthetic",
        "proposal_digest": "a" * 64,
        "effect": effect,
    }
    package_bytes = json.dumps(package, sort_keys=True).encode()
    review = {
        "schema_version": "dmb_reviewed_extract_confirmation_v1",
        "semantic_reviewer_kind": "agent_steward",
        "semantic_reviewer_id": "steward:synthetic",
        "reviewed_at": (NOW + timedelta(days=1)).isoformat(),
        "proposal_id": package["proposal_id"],
        "proposal_digest": package["proposal_digest"],
        "prepared_package_sha256": _sha(package_bytes),
        "source_run_id": case["resolved"].run_id,
        "source_artifact_id": case["review"].source_artifact_id,
        "source_revision_id": case["review"].source_revision_id,
        "source_body_sha256": case["review"].source_body_sha256,
        "source_span_index_sha256": case["review"].source_span_index_sha256,
        "candidate_graph_sha256": case["review"].candidate_graph_sha256,
        "candidate_admission_digest": effect["candidate_admission"]["candidate_digest"],
        "expected_parent_revision_id": case["parent"].revision_id,
        "expected_parent_payload_sha256": case["review"].expected_parent_payload_sha256,
        "decisions": [{"assertion_id": assertion_id, "disposition": disposition}],
        "selected_assertion_ids": [assertion_id],
    }
    artifact_bytes = json.dumps(review, sort_keys=True).encode()
    return artifact_bytes, _sha(artifact_bytes), package_bytes


def _context(case: dict) -> TrustedGMExtractContext:
    return TrustedGMExtractContext(
        managed_world_id="buddy-world",
        native_world_id=case["context"].native_world_id,
        campaign_id=case["context"].campaign_id,
        expected_parent_revision_id=case["parent"].revision_id,
    )


def test_denied_capability_prevents_source_and_core_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    artifact, digest, package = _inputs(case)
    monkeypatch.setattr(
        subject, "_read_review_and_package", lambda **_: pytest.fail("read input")
    )
    monkeypatch.setattr(
        world_graph_writes, "_direct_services", lambda *_: pytest.fail("Core access")
    )
    with pytest.raises(subject.ReviewedExtractConfirmationError) as exc:
        subject.confirm_reviewed_extract(
            context=_context(case),
            artifact_bytes=artifact,
            artifact_sha256=digest,
            sealed_package_bytes=package,
            gm_capability_policy=None,
            database_url="unused",
            repo_root=tmp_path,
        )
    assert exc.value.code == "confirm_capability_denied"


@pytest.mark.parametrize("disposition", ["reject", "defer"])
def test_selection_must_be_explicitly_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disposition: str
) -> None:
    case = _case(tmp_path, monkeypatch)
    artifact, digest, package = _inputs(case, disposition=disposition)
    with pytest.raises(subject.ReviewedExtractConfirmationError) as exc:
        subject.confirm_reviewed_extract(
            context=_context(case),
            artifact_bytes=artifact,
            artifact_sha256=digest,
            sealed_package_bytes=package,
            gm_capability_policy=_policy(case["parent"].revision_id),
            database_url="unused",
            repo_root=tmp_path,
        )
    assert exc.value.code == "review_invalid"


def test_trusted_service_closes_bytes_and_passes_actual_review_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services import extract_promote
    from apps.live_control_server.services import candidate_graph_admission
    from apps.live_control_server.services import (
        graph_run_registry,
        promotable_ingest_run,
    )

    case = _case(tmp_path, monkeypatch)
    artifact, digest, package = _inputs(case)
    monkeypatch.setattr(
        graph_run_registry, "get_extraction_run", lambda *_: case["run"]
    )
    monkeypatch.setattr(
        promotable_ingest_run,
        "resolve_promotable_ingest_run",
        lambda *_a, **_k: case["resolved"],
    )
    monkeypatch.setattr(
        extract_promote,
        "_assert_current_publication_target",
        lambda *_: SimpleNamespace(
            managed_world_id="buddy-world", native_world_id=WORLD
        ),
    )
    monkeypatch.setattr(
        extract_promote, "assert_sealed_source_uri_allowed", lambda *_: None
    )
    monkeypatch.setattr(
        extract_promote, "_assert_recap_semantics_at_confirm", lambda *_: None
    )
    monkeypatch.setattr(
        candidate_graph_admission,
        "confirm_candidate_graph_admission",
        lambda **kw: kw["governed_confirm"](),
    )

    writer_calls = 0

    def writer(_request, **kwargs):
        nonlocal writer_calls
        writer_calls += 1
        binding = kwargs["semantic_binding"]
        assert binding.artifact_sha256 == digest
        assert binding.reviewed_at == NOW + timedelta(days=1)
        assert kwargs["confirming_principal"] == subject.SERVICE_PRINCIPAL
        assert kwargs["assertion_ids"] == ("assertion:synthetic-scout",)
        return {"outcome": "committed"}

    monkeypatch.setattr(
        world_graph_writes, "confirm_extract_promote_via_dungeonmind", writer
    )
    assert subject.confirm_reviewed_extract(
        context=_context(case),
        artifact_bytes=artifact,
        artifact_sha256=digest,
        sealed_package_bytes=package,
        gm_capability_policy=_policy(case["parent"].revision_id),
        database_url="unused",
        repo_root=tmp_path,
    ) == {"outcome": "committed"}
    original_candidate = case["candidate_path"].read_bytes()
    case["candidate_path"].write_bytes(b"{}")
    with pytest.raises(subject.ReviewedExtractConfirmationError) as drift:
        subject.confirm_reviewed_extract(
            context=_context(case),
            artifact_bytes=artifact,
            artifact_sha256=digest,
            sealed_package_bytes=package,
            gm_capability_policy=_policy(case["parent"].revision_id),
            database_url="unused",
            repo_root=tmp_path,
        )
    assert drift.value.code == "source_digest_drift"
    case["candidate_path"].write_bytes(original_candidate)
    case["resolved"].world_id = "foreign-world"
    with pytest.raises(subject.ReviewedExtractConfirmationError) as foreign:
        subject.confirm_reviewed_extract(
            context=_context(case),
            artifact_bytes=artifact,
            artifact_sha256=digest,
            sealed_package_bytes=package,
            gm_capability_policy=_policy(case["parent"].revision_id),
            database_url="unused",
            repo_root=tmp_path,
        )
    assert foreign.value.code == "source_digest_drift"
    assert writer_calls == 1


def _finalized_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    case = _case(tmp_path, monkeypatch)
    original = _prepare(case)
    selection = sorted(verdict.assertion_id for verdict in original.assertion_verdicts)
    effect = {"synthetic": "exact pinned effect"}
    package = {
        "proposal_id": "proposal:synthetic",
        "proposal_digest": "a" * 64,
        "effect": effect,
    }
    artifact, digest, package_bytes = _inputs(case)
    review = json.loads(artifact)
    binding = ReviewedExtractBinding(
        artifact_sha256=digest,
        prepared_package_sha256=_sha(package_bytes),
        semantic_reviewer_kind="agent_steward",
        semantic_reviewer_id="steward:synthetic",
        reviewed_at=NOW + timedelta(days=1),
        service_principal=subject.SERVICE_PRINCIPAL,
        proposal_id=package["proposal_id"],
        proposal_digest=package["proposal_digest"],
        source_artifact_id=review["source_artifact_id"],
        source_revision_id=review["source_revision_id"],
        source_body_sha256=review["source_body_sha256"],
        source_span_index_sha256=review["source_span_index_sha256"],
        candidate_graph_sha256=review["candidate_graph_sha256"],
        candidate_admission_digest=review["candidate_admission_digest"],
        expected_parent_revision_id=case["parent"].revision_id,
        expected_parent_payload_sha256=case["review"].expected_parent_payload_sha256,
        selected_assertion_ids=selection,
    )
    candidate = original.candidate_contribution.model_copy(
        update={
            "produced_at": binding.reviewed_at,
            "authored_by": subject.SERVICE_PRINCIPAL,
            "diagnostics": {
                "reviewed_extract_confirmation": binding.model_dump(mode="json")
            },
        }
    )
    candidate_sha = contribution_v2_payload_sha256(candidate)
    plan = original.plan_ref.model_copy(
        update={
            "source_plan_id": binding.proposal_id,
            "source_plan_sha256": binding.proposal_digest,
            "source_input_sha256": canonical_sha256(effect),
            "candidate_contribution_sha256": candidate_sha,
        }
    )
    operation_id = world_graph_writes._derive_confirm_operation_id(
        world_id=WORLD, package=package, assertion_ids=tuple(selection)
    )
    review_sha = derive_review_intent_sha256_v2(
        operation_id=operation_id,
        world_id=WORLD,
        campaign_id=CAMPAIGN,
        plan_ref=plan,
        candidate_contribution=candidate,
        identity_proposals=[],
        identity_verdicts=[],
        assertion_verdicts=original.assertion_verdicts,
        reviewer_id=subject.SERVICE_PRINCIPAL,
        reviewed_at=binding.reviewed_at,
    )
    intent = original.model_copy(
        update={
            "operation_id": operation_id,
            "plan_ref": plan,
            "candidate_contribution": candidate,
            "reviewer_id": subject.SERVICE_PRINCIPAL,
            "reviewed_at": binding.reviewed_at,
            "review_intent_sha256": review_sha,
        }
    )
    confirmation = CommitConfirmationReceiptV2(
        confirmation_id=derive_confirmation_id(
            operation_id=operation_id,
            review_intent_sha256=review_sha,
            actor=subject.SERVICE_PRINCIPAL,
            confirmed_at=binding.reviewed_at,
        ),
        operation_id=operation_id,
        review_intent_sha256=review_sha,
        actor=subject.SERVICE_PRINCIPAL,
        world_id=WORLD,
        campaign_id=CAMPAIGN,
        expected_parent_revision_id=case["parent"].revision_id,
        confirmed_at=binding.reviewed_at,
    )
    contributions = InMemoryContributionRepository()
    reviews = InMemoryContributionReviewRepository(contributions)
    publications = InMemoryFinalizedReviewPublicationRepository(reviews, case["graph"])
    state = finalize_contribution_review_v2(
        ContributionReviewSubmissionV2(intent=intent, confirmation=confirmation),
        capability_policy=_policy(case["parent"].revision_id),
        world_graph_repository=case["graph"],
        review_repository=reviews,
    )
    bundle = SimpleNamespace(
        world_graph=case["graph"],
        contribution_reviews=reviews,
        finalized_review_publications=publications,
        contributions=contributions,
    )
    monkeypatch.setattr(
        world_graph_writes,
        "_build_graph_reader",
        lambda: VersionedUnionGraphSnapshotReader(profile_registry=case["profiles"]),
    )
    return case, package, binding, bundle, state


def test_lost_finalize_response_recovers_stored_review_and_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, package, binding, bundle, state = _finalized_case(tmp_path, monkeypatch)
    assert (
        bundle.finalized_review_publications.get(WORLD, state.record.operation_id)
        is None
    )
    result = world_graph_writes._recover_reviewed_extract_confirmation(
        bundle=bundle,
        world_id=WORLD,
        package=package,
        operation_id=state.record.operation_id,
        binding=binding,
    )
    assert result["outcome"] == "already_applied"
    assert result["accepted_assertion_ids"] == binding.selected_assertion_ids
    assert (
        bundle.world_graph.get_head(WORLD).head_revision_id
        == result["committed_revision_id"]
    )
    stored = bundle.contribution_reviews.get_for_plan(WORLD, binding.proposal_id)
    assert stored.record.reviewed_at == binding.reviewed_at != NOW


def test_concurrent_exact_retry_and_drift_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, package, binding, bundle, state = _finalized_case(tmp_path, monkeypatch)

    def retry(_):
        return world_graph_writes._recover_reviewed_extract_confirmation(
            bundle=bundle,
            world_id=WORLD,
            package=package,
            operation_id=state.record.operation_id,
            binding=binding,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(retry, range(4)))
    assert len({result["committed_revision_id"] for result in results}) == 1
    assert all(result["outcome"] == "already_applied" for result in results)
    for change in (
        {"artifact_sha256": "b" * 64},
        {"selected_assertion_ids": ["assertion:other"]},
        {"service_principal": "service:buddy:other"},
        {"reviewed_at": binding.reviewed_at + timedelta(seconds=1)},
        {"source_body_sha256": "c" * 64},
    ):
        with pytest.raises(world_graph_writes.WorldGraphWriteError) as exc:
            world_graph_writes._recover_reviewed_extract_confirmation(
                bundle=bundle,
                world_id=WORLD,
                package=package,
                operation_id=state.record.operation_id,
                binding=binding.model_copy(update=change),
            )
        assert exc.value.code == "governed_write_idempotency_conflict"


@pytest.mark.parametrize("lost_response", [None, "finalize", "publish"])
def test_writer_uses_frozen_review_time_and_recovers_lost_responses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lost_response: str | None
) -> None:
    from dungeonmind.application import contribution_review_v2, review_publication
    from graph_memory import extract_promote_proposal

    # This recovery test uses a synthetic package with no recap contribution.
    # The source-local identity basis is exercised by admission/confirm tests.
    monkeypatch.setattr(
        extract_promote_proposal, "verify_source_local_identity_basis", lambda *_a, **_k: None
    )

    case, _package, binding, _old_bundle, _state = _finalized_case(
        tmp_path, monkeypatch
    )
    prepared = _prepare(case)
    contributions = InMemoryContributionRepository()
    reviews = InMemoryContributionReviewRepository(contributions)
    publications = InMemoryFinalizedReviewPublicationRepository(reviews, case["graph"])
    bundle = SimpleNamespace(
        world_graph=case["graph"],
        contribution_reviews=reviews,
        finalized_review_publications=publications,
        contributions=contributions,
        sources=case["sources"],
    )
    package = {
        "schema": "dmb_extract_promote_proposal_v1",
        "proposal_id": binding.proposal_id,
        "proposal_digest": binding.proposal_digest,
        "effect": {
            "world_id": WORLD,
            "parent_revision_id": case["parent"].revision_id,
            "contribution_meta": {"campaign_scope": CAMPAIGN},
        },
    }
    request = ExtractPromoteConfirmRequest(
        review_package=package, assertion_ids=binding.selected_assertion_ids
    )
    monkeypatch.setattr(
        world_graph_writes,
        "_direct_services",
        lambda *_: SimpleNamespace(
            bundle=bundle, binding=SimpleNamespace(legacy_buddy_revision_id=None)
        ),
    )
    monkeypatch.setattr(
        world_graph_writes,
        "_mutation_context_from_sealed_package",
        lambda **_: SimpleNamespace(),
    )
    monkeypatch.setattr(
        world_graph_writes,
        "_verify_reviewed_corpus_binding_authority",
        lambda _b, _p, context, **_: context,
    )
    monkeypatch.setattr(
        world_graph_writes,
        "_reconstruct_selected_contribution",
        lambda **_: (
            None,
            SimpleNamespace(
                contribution_id="contrib:synthetic", campaign_scope=CAMPAIGN
            ),
        ),
    )
    monkeypatch.setattr(
        world_graph_writes,
        "_affected_ids_from_contribution",
        lambda *_: (binding.selected_assertion_ids, ["npc:scout", "loc:gate"]),
    )
    monkeypatch.setattr(
        world_graph_writes, "_reprove_source_extraction", lambda *_a, **_k: None
    )
    monkeypatch.setattr(world_graph_writes, "_build_pair_to_dm", lambda *_: {})
    monkeypatch.setattr(
        world_graph_writes, "_reviewed_identity_publication_guard", lambda **_: None
    )

    def build_candidate(_contribution, *, produced_at, **_):
        candidate = prepared.candidate_contribution.model_copy(
            update={
                "produced_at": produced_at,
                "authored_by": subject.SERVICE_PRINCIPAL,
            }
        )
        return candidate, {
            item.assertion_id: item.acceptance_state
            for item in prepared.assertion_verdicts
        }

    monkeypatch.setattr(world_graph_writes, "_build_v2_candidate", build_candidate)
    original_finalize = contribution_review_v2.finalize_contribution_review_v2
    original_publish = review_publication.publish_finalized_review
    if lost_response == "finalize":

        def lose_finalize(*args, **kwargs):
            original_finalize(*args, **kwargs)
            raise RuntimeError("synthetic response loss after finalize")

        monkeypatch.setattr(
            contribution_review_v2, "finalize_contribution_review_v2", lose_finalize
        )
    elif lost_response == "publish":

        def lose_publish(*args, **kwargs):
            original_publish(*args, **kwargs)
            raise RuntimeError("synthetic response loss after publish")

        monkeypatch.setattr(
            review_publication, "publish_finalized_review", lose_publish
        )

    def confirm():
        return world_graph_writes.confirm_extract_promote_via_dungeonmind(
            request,
            database_url="memory://synthetic",
            confirming_principal=subject.SERVICE_PRINCIPAL,
            assertion_ids=tuple(binding.selected_assertion_ids),
            repo_root=tmp_path,
            semantic_binding=binding,
            semantic_gm_policy=_policy(case["parent"].revision_id),
        )

    if lost_response == "publish":
        with pytest.raises(RuntimeError, match="synthetic response loss"):
            confirm()
        monkeypatch.setattr(
            review_publication, "publish_finalized_review", original_publish
        )
        result = confirm()
        assert result["outcome"] == "already_applied"
    else:
        result = confirm()
        assert result["outcome"] == (
            "already_applied" if lost_response else "published"
        )
    replay = confirm()
    assert replay["committed_revision_id"] == result["committed_revision_id"]
    stored = reviews.get_for_plan(WORLD, binding.proposal_id)
    assert stored.record.reviewed_at == binding.reviewed_at != NOW
    assert (
        stored.candidate_contribution.diagnostics["reviewed_extract_confirmation"][
            "artifact_sha256"
        ]
        == binding.artifact_sha256
    )
    assert (
        publications.get(WORLD, stored.record.operation_id).review_id
        == stored.record.review_id
    )


@pytest.mark.integration
def test_postgres_recovers_exact_finalized_review_after_repository_recreation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )

    dsn = os.environ.get("DMB_REVIEWED_EXTRACT_TEST_DATABASE_URL", "").strip()
    if not dsn:
        pytest.skip("DMB_REVIEWED_EXTRACT_TEST_DATABASE_URL is required")
    parsed = urlparse(dsn)
    if parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    } or not parsed.path.removeprefix("/").startswith("dmb_reviewed_extract_test_"):
        pytest.fail(
            "refusing PostgreSQL writes outside a loopback disposable reviewed-extract database"
        )

    case, package, binding, _memory_bundle, state = _finalized_case(
        tmp_path, monkeypatch
    )
    bundle = PostgresRepositoryBundle(PostgresDatabase(dsn))
    assert bundle.world_graph.get_head(WORLD) is None, (
        "disposable database must be unused"
    )
    parent = bundle.world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["init:test-relations"],
            graph_schema="dm_union_graph_v6",
            graph_payload=case["graph_payload"],
            created_at=NOW,
        )
    )
    assert parent.revision_id == case["parent"].revision_id
    bundle.sources.put_artifact(
        case["sources"].get_artifact(case["review"].source_artifact_id)
    )
    bundle.sources.put_revision(
        case["sources"].get_revision(case["review"].source_revision_id)
    )
    bundle.contribution_reviews.finalize(state)
    assert (
        bundle.finalized_review_publications.get(WORLD, state.record.operation_id)
        is None
    )

    def concurrent_retry(_index: int) -> dict:
        separate = PostgresRepositoryBundle(PostgresDatabase(dsn))
        return world_graph_writes._recover_reviewed_extract_confirmation(
            bundle=separate,
            world_id=WORLD,
            package=package,
            operation_id=state.record.operation_id,
            binding=binding,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(pool.map(concurrent_retry, range(4)))
    assert len({result["committed_revision_id"] for result in concurrent}) == 1
    first = concurrent[0]
    fresh = PostgresRepositoryBundle(PostgresDatabase(dsn))
    replay = world_graph_writes._recover_reviewed_extract_confirmation(
        bundle=fresh,
        world_id=WORLD,
        package=package,
        operation_id=state.record.operation_id,
        binding=binding,
    )
    assert first["committed_revision_id"] == replay["committed_revision_id"]
    assert (
        fresh.world_graph.get_head(WORLD).head_revision_id
        == first["committed_revision_id"]
    )
    assert (
        fresh.contribution_reviews.get_for_plan(
            WORLD, binding.proposal_id
        ).record.reviewed_at
        == binding.reviewed_at
    )
