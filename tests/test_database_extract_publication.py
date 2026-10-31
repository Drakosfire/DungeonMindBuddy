"""Exact database run ownership survives removal of operational promotion files."""
import copy
import json
from pathlib import Path

import psycopg
import pytest

from apps.live_control_server.services import extract_promote as product
from apps.live_control_server.services import graph_run_registry as runs
from apps.live_control_server.services import promotable_ingest_run as owner
from apps.live_control_server.services.candidate_graph_admission import canonical_candidate_digest
from graph_memory.extract_promote_proposal import compute_proposal_digest
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytest_plugins = ("tests.application_state.conftest",)
pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _case(root):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    data = runs.load_reviewable_extraction_data(root, result.run.run_id)
    package = owner.seal_extraction_run({"effect": {
        "world_id": data.source_artifact.world_id,
        "source_artifact_id": data.run.source_artifact_id,
        "source_revision_id": "sha256:" + data.source_artifact.content_sha256,
        "contribution_meta": {"campaign_scope": data.run.campaign_id},
        "candidate_admission": {"candidate_digest":canonical_candidate_digest(json.loads(data.candidate_bytes))},
    }}, data)
    return data, package


def _remove_files(root):
    for path in root.rglob("*"):
        if path.is_file():
            path.unlink()


def test_resolution_and_bound_run_need_no_files(tmp_path, monkeypatch):
    data, package = _case(tmp_path)
    _remove_files(tmp_path)
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("promotion reopened a file"))
        resolved = owner.resolve_promotable_ingest_run(data.run.run_id, root=tmp_path)
        reopened = owner.load_bound_extraction_run(package, root=tmp_path)
    assert reopened == data == resolved.data
    assert not resolved.normalized_recap_path.exists()
    assert not resolved.candidate_graph_path.exists()


@pytest.mark.parametrize("pin", ["run_id", "run_revision", "source_revision_id", "profile_id", "source_domain", "campaign_id", "session_id", "world_id", "components"])
def test_changed_run_pins_fail_even_with_rehashed_effect(tmp_path, pin):
    _, package = _case(tmp_path)
    binding = package["effect"][owner.EXTRACTION_RUN_BINDING_KEY]
    binding[pin] = 999 if pin == "run_revision" else {} if pin == "components" else "changed"
    package["proposal_digest"] = compute_proposal_digest(package["effect"])
    with pytest.raises(owner.PromotableIngestRunError):
        owner.load_bound_extraction_run(package, root=tmp_path)


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_valid_mirrors_never_rescue_database_failure(tmp_path, application_state_dsn, kind, violation):
    data, package = _case(tmp_path)
    # Untrusted files must not rescue missing/corrupt authoritative output.
    for name, raw in (("candidate_graph", data.candidate_bytes), ("source_span_index", data.span_bytes)):
        (tmp_path / data.run.components[name].uri.removeprefix("repo://")).write_bytes(raw)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (data.run.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (data.run.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (data.run.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", data.run.run_id, kind))
    with pytest.raises(owner.PromotableIngestRunError):
        owner.load_bound_extraction_run(package, root=tmp_path)


def test_missing_binding_and_effect_scope_cannot_fall_back_to_candidate_file(tmp_path):
    _, package = _case(tmp_path)
    missing = copy.deepcopy(package)
    del missing["effect"][owner.EXTRACTION_RUN_BINDING_KEY]
    for changed in (missing, {**package, "effect":{**package["effect"], "world_id":"foreign"}}):
        changed["proposal_digest"] = compute_proposal_digest(changed["effect"])
        with pytest.raises(owner.PromotableIngestRunError):
            owner.load_bound_extraction_run(changed, root=tmp_path)


@pytest.mark.integration
def test_product_prepare_confirm_native_publication_without_files(tmp_path, monkeypatch, application_state_dsn):
    from tests.test_recap_source_read_continuity import _prepare_session
    from apps.live_control_server.services.managed_world_graph_projection import VerifiedManagedWorldBinding
    from apps.live_control_server.models.extract_promote import ExtractPromotePrepareRequest, ExtractPromoteConfirmRequest
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle

    # Reuse the existing isolated native fixture to supply legitimate baseline
    # identity context. The actual tested candidate is produced by extraction.
    native_root = tmp_path / "native"
    native_root.mkdir()
    native = _prepare_session(native_root, monkeypatch, application_state_dsn,
        world_id="world:elderwyld", campaign_id="longmont-c2", session_id="session-22",
        node_id="node:location:baseline", recap_text="Synthetic baseline source.\n")
    root = tmp_path / "actual-extraction"
    root.mkdir()
    data, _ = _case(root)
    binding = VerifiedManagedWorldBinding(managed_world_id="managed-world", native_world_id="world:elderwyld",
        binding_version=1, source_root_relpath="unused-presentation-path")
    monkeypatch.setattr(product, "_artifact_root", lambda: root)
    monkeypatch.setattr(product, "_resolve_publication_target", lambda _: binding)
    # Test native binding changes separately from file removal. This seam does
    # not bypass native head, source admission or publication authority checks.
    monkeypatch.setattr(product, "resolve_managed_world_binding", lambda *a, **k: binding)
    _remove_files(root)
    prepared = product.prepare(ExtractPromotePrepareRequest(run_id=data.run.run_id, managed_world_id="managed-world"))
    assert prepared.confirmable
    selected = [row["assertion_id"] for row in prepared.review_package["effect"]["accepted_proposals"]]
    assert selected
    request = ExtractPromoteConfirmRequest(review_package=prepared.review_package, assertion_ids=selected)
    first = product.confirm(request)
    assert first.outcome == "committed"
    second = product.confirm(request)
    assert second.outcome == "already_applied"
    bundle = PostgresRepositoryBundle(PostgresDatabase(native.dsn))
    assert bundle.world_graph.get_head(binding.native_world_id).head_revision_id == first.committed_revision_id
    assert owner.load_bound_extraction_run(prepared.review_package, root=root).candidate_bytes == data.candidate_bytes
    assert not list(root.rglob("*.json"))
