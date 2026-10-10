from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from apps.live_control_server.services import current_head_recap_preflight as preflight


def _fixtures(tmp_path: Path, *, session: int = 26):
    original_sha = hashlib.sha256(b"original recap").hexdigest()
    normalized_sha = hashlib.sha256(b"normalized derivative").hexdigest()
    entry = {
        "ordinal": 1,
        "campaign_id": "longmont-c2",
        "campaign_number": 2,
        "session": session,
        "session_id": f"longmont-c2/session-{session}",
        "normalized_path": "corpus/normalized.md",
        "normalized_sha256": normalized_sha,
        "original_path": "corpus/original.md",
        "original_sha256": original_sha,
        "source_artifact_id": f"artifact:recap:longmont-c2:session-{session}:test",
    }
    digest = preflight._canonical_sha256(
        {"schema": preflight.ACCEPTED_MANIFEST_SCHEMA, "entries": [entry]}
    )
    manifest = {
        "schema": preflight.ACCEPTED_MANIFEST_SCHEMA,
        "count": 1,
        "digest": digest,
        "entries": [entry],
    }
    ledger = {
        "sessions": [
            {
                "ordinal": 1,
                "campaign_id": entry["campaign_id"],
                "session_id": entry["session_id"],
                "source_artifact_id": entry["source_artifact_id"],
                "source_revision_id": f"sha256:{original_sha}",
                "original_path": entry["original_path"],
                "original_sha256": original_sha,
                "normalized_sha256": normalized_sha,
            }
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    ledger_path = tmp_path / "session_ledger.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    return manifest_path, ledger_path, entry, original_sha, digest


def _expected(tmp_path: Path):
    manifest_path, ledger_path, entry, digest, cohort_digest = _fixtures(tmp_path)
    loaded = preflight.load_accepted_sources(
        manifest_path,
        ledger_path,
        expected_count=1,
        expected_digest=cohort_digest,
    )
    return loaded, entry, digest, cohort_digest


def _native(entry, digest, *, revision=None, content=None):
    return preflight.NativeSource(
        source_artifact_id=entry["source_artifact_id"],
        source_revision_id=revision or f"sha256:{digest}",
        content_sha256=content or digest,
        campaign_id=entry["campaign_id"],
        session_id=entry["session_id"],
        source_domain="session_recap",
    )


def _evidence(entry, digest, *, graph_revision="rev:current"):
    return preflight.GraphEvidence(
        source_artifact_id=entry["source_artifact_id"],
        source_revision_id=f"sha256:{digest}",
        evidence_ref_id="evidence:exact",
        anchor_id="anchor:exact",
        graph_revision=graph_revision,
    )


def _plan(expected, entry, digest, cohort_digest, **kwargs):
    return preflight.build_preflight_plan(
        expected,
        world_id="eldyrwild",
        manifest_digest=cohort_digest,
        pinned_head="rev:current",
        head_after="rev:current",
        **kwargs,
    )["sources"][0]


def test_exact_match_requires_source_pair_digest_and_pinned_graph_evidence(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    row = _plan(
        expected,
        entry,
        digest,
        cohort_digest,
        native_sources=(_native(entry, digest),),
        graph_evidence=(_evidence(entry, digest),),
    )
    assert row["disposition"] == "exact_match"
    assert row["pinned_graph_evidence"][0]["graph_revision"] == "rev:current"
    assert row["mutation_proposed"] is False


def test_different_artifact_for_same_session_does_not_fill_missing_pair(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    alternate = preflight.NativeSource(
        source_artifact_id="artifact:recap:longmont-c2:session-26:other-bytes",
        source_revision_id=f"sha256:{digest}",
        content_sha256=digest,
        campaign_id=entry["campaign_id"],
        session_id=entry["session_id"],
    )
    row = _plan(expected, entry, digest, cohort_digest, native_sources=(alternate,))
    assert row["disposition"] == "missing_source_pair"
    assert (
        row["observed_native_sources"][0]["source_artifact_id"]
        == alternate.source_artifact_id
    )


def test_same_native_pair_with_different_digest_is_conflict(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    conflicting = _native(entry, digest, content="0" * 64)
    row = _plan(
        expected,
        entry,
        digest,
        cohort_digest,
        native_sources=(conflicting,),
        graph_evidence=(_evidence(entry, digest),),
    )
    assert row["disposition"] == "digest_conflict"


def test_divergent_alternate_artifact_for_same_session_is_digest_conflict(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    alternate = preflight.NativeSource(
        source_artifact_id="artifact:recap:longmont-c2:session-26:other",
        source_revision_id="sha256:" + "0" * 64,
        content_sha256="0" * 64,
        campaign_id=entry["campaign_id"],
        session_id=entry["session_id"],
        source_domain="session_recap",
    )
    row = _plan(expected, entry, digest, cohort_digest, native_sources=(alternate,))
    assert row["disposition"] == "digest_conflict"


@pytest.mark.parametrize(
    ("campaign_id", "session_id", "source_domain"),
    [("other-campaign", "longmont-c2/session-26", "session_recap"),
     ("longmont-c2", "other-session", "session_recap"),
     ("longmont-c2", "longmont-c2/session-26", "other-domain")],
)
def test_exact_match_requires_campaign_session_and_domain(
    tmp_path, campaign_id, session_id, source_domain
):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    native = _native(entry, digest)
    native = preflight.NativeSource(
        **{
            **native.__dict__,
            "campaign_id": campaign_id,
            "session_id": session_id,
            "source_domain": source_domain,
        }
    )
    row = _plan(
        expected,
        entry,
        digest,
        cohort_digest,
        native_sources=(native,),
        graph_evidence=(_evidence(entry, digest),),
    )
    assert row["disposition"] == "source_identity_conflict"


def test_exact_source_pair_without_graph_evidence_is_distinct(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    row = _plan(
        expected,
        entry,
        digest,
        cohort_digest,
        native_sources=(_native(entry, digest),),
        graph_evidence=(),
    )
    assert row["disposition"] == "graph_evidence_absent"


def test_evidence_from_another_revision_does_not_satisfy_pinned_head(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    row = _plan(
        expected,
        entry,
        digest,
        cohort_digest,
        native_sources=(_native(entry, digest),),
        graph_evidence=(_evidence(entry, digest, graph_revision="rev:old"),),
    )
    assert row["disposition"] == "graph_evidence_absent"
    assert row["observed_graph_evidence"][0]["graph_revision"] == "rev:old"
    assert row["pinned_graph_evidence"] == []


def test_head_drift_overrides_source_match_and_invalidates_plan(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    report = preflight.build_preflight_plan(
        expected,
        world_id="eldyrwild",
        manifest_digest=cohort_digest,
        pinned_head="rev:before",
        head_after="rev:after",
        native_sources=(_native(entry, digest),),
        graph_evidence=(_evidence(entry, digest, graph_revision="rev:before"),),
    )
    row = report["sources"][0]
    assert row["pinned_head_disposition"] == "exact_match"
    assert row["disposition"] == "parent_head_drift"
    assert report["head_drift"] is True


def test_unavailable_authority_is_not_coerced_to_missing_or_absent(tmp_path):
    expected, _, _, cohort_digest = _expected(tmp_path)
    report = preflight.build_preflight_plan(
        expected,
        world_id="eldyrwild",
        manifest_digest=cohort_digest,
        pinned_head=None,
        head_after=None,
        authority_error="native_head_unavailable",
        source_inventory_complete=False,
        graph_index_complete=False,
    )
    assert report["sources"][0]["disposition"] == "authority_unavailable"
    assert (
        report["sources"][0]["next_action"]
        == preflight._NEXT_ACTION["authority_unavailable"]
    )


def test_overflowed_graph_index_does_not_claim_evidence_absent(tmp_path):
    expected, entry, digest, cohort_digest = _expected(tmp_path)
    row = _plan(
        expected,
        entry,
        digest,
        cohort_digest,
        native_sources=(_native(entry, digest),),
        graph_evidence=(),
        graph_index_complete=False,
    )
    assert row["disposition"] == "graph_evidence_unavailable"


def test_session_29_is_rejected_even_if_manifest_is_rehashed(tmp_path):
    manifest_path, ledger_path, _, _, digest = _fixtures(tmp_path, session=29)
    with pytest.raises(preflight.PreflightInputError, match="Session 29"):
        preflight.load_accepted_sources(
            manifest_path, ledger_path, expected_count=1, expected_digest=digest
        )


def test_session_23_source_revision_uses_original_not_normalized_digest(tmp_path):
    manifest_path, ledger_path, entry, original_sha, digest = _fixtures(
        tmp_path, session=23
    )
    expected = preflight.load_accepted_sources(
        manifest_path, ledger_path, expected_count=1, expected_digest=digest
    )[0]
    assert expected.source_artifact_id == entry["source_artifact_id"]
    assert expected.source_revision_id == f"sha256:{original_sha}"
    assert expected.normalized_sha256 != original_sha


def test_report_never_claims_admission_or_completeness(tmp_path):
    expected, _, _, cohort_digest = _expected(tmp_path)
    report = preflight.build_preflight_plan(
        expected,
        world_id="eldyrwild",
        manifest_digest=cohort_digest,
        pinned_head="rev:current",
        head_after="rev:current",
    )
    assert report["planning_only"] is True
    assert report["admission_proof"] is False
    assert report["completeness_proof"] is False
    assert report["writes_performed"] is False
    assert report["review_plan"]["requires_human_review"] is True
    assert report["review_plan"]["automatic_mutations"] == []
    assert report["review_plan"]["actions"][0]["ordinal"] == 1


def test_operational_preflight_refuses_a_different_world(tmp_path):
    with pytest.raises(preflight.PreflightInputError, match="pinned"):
        preflight.run_current_head_preflight(
            manifest_path=tmp_path / "unused-manifest.json",
            ledger_path=tmp_path / "unused-ledger.json",
            world_id="another-world",
        )


def _reader_dependencies(
    *, index_status="complete", head_after="rev:head", missing_head=False
):
    calls = {}
    artifact = SimpleNamespace(
        source_artifact_id="artifact:recap:longmont-c2:session-26:source",
        campaign_id="longmont-c2",
        session_id="longmont-c2/session-26",
        source_domain="session_recap",
    )
    revision = SimpleNamespace(
        source_revision_id="sha256:" + "a" * 64, content_sha256="a" * 64
    )
    bundle = SimpleNamespace(
        sources=SimpleNamespace(
            list_artifacts_for_world=lambda wid: [artifact],
            list_revisions=lambda artifact_id: [revision],
        ),
        world_graph=SimpleNamespace(
            get_head=lambda wid: SimpleNamespace(head_revision_id=head_after)
        ),
    )
    pin = SimpleNamespace(
        source_artifact_id=artifact.source_artifact_id,
        source_revision_id=revision.source_revision_id,
        evidence_ref_id="evidence:1",
        anchor_id="anchor:1",
        graph_revision="rev:head",
    )
    index = SimpleNamespace(status=index_status, source_pins=[pin])

    def services_factory(got_bundle, world_id):
        calls["world_id"] = world_id
        return SimpleNamespace(
            binding=SimpleNamespace(dungeonmind_head_revision_id="rev:head")
        )

    def request_factory(payload):
        calls["request"] = payload
        return payload

    def index_reader(services, request, *, revision_id):
        calls["index_revision"] = revision_id
        return index

    deps = preflight.CurrentHeadReadDependencies(
        database_url="fake://readonly",
        database_factory=lambda url: url,
        bundle_factory=lambda db: bundle,
        services_factory=(
            lambda got_bundle, world_id: SimpleNamespace(
                binding=SimpleNamespace(dungeonmind_head_revision_id=None)
            )
            if missing_head
            else services_factory(got_bundle, world_id)
        ),
        source_anchor_index=index_reader,
        search_request_factory=request_factory,
    )
    return deps, calls


def test_production_reader_uses_world_scope_pinned_complete_index_and_rereads_head():
    deps, calls = _reader_dependencies()
    before, after, sources, evidence, complete = (
        preflight.read_current_head_observations(dependencies=deps)
    )
    request = calls["request"]
    assert calls["world_id"] == "eldyrwild"
    assert calls["index_revision"] == before == "rev:head"
    assert request["scopeMode"] == "world"
    assert request["revisionPin"] == before
    assert after == "rev:head"
    assert complete is True
    assert sources[0].source_domain == "session_recap"
    assert evidence[0].graph_revision == before


def test_production_reader_fails_closed_on_overflow_and_head_reread_drift():
    deps, _ = _reader_dependencies(index_status="overflow")
    _, _, _, evidence, complete = preflight.read_current_head_observations(
        dependencies=deps
    )
    assert evidence == ()
    assert complete is False

    deps, _ = _reader_dependencies(head_after="rev:changed")
    before, after, _, _, _ = preflight.read_current_head_observations(
        dependencies=deps
    )
    assert before == "rev:head"
    assert after == "rev:changed"

    deps, _ = _reader_dependencies(missing_head=True)
    with pytest.raises(RuntimeError, match="current_head_unavailable"):
        preflight.read_current_head_observations(dependencies=deps)

    deps, _ = _reader_dependencies(index_status="unavailable")
    with pytest.raises(RuntimeError, match="graph_evidence_unavailable"):
        preflight.read_current_head_observations(dependencies=deps)
