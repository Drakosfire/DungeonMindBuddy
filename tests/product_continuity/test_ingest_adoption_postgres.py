"""PostgreSQL owning-boundary witnesses for DFC-2c Ingest adoption."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from application_state.errors import ApplicationStateUnavailableError
from application_state.ingest.import_legacy import import_extraction_runs_from_registry
from application_state.ingest.service import (
    create_extraction_run,
    get_extraction_run,
    list_extraction_runs,
)
from apps.live_control_server.services.ingest_run_catalog import (
    list_canonical_extraction_runs,
)
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestArtifactRef,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
    GraphIngestSource,
    adapt_recap_manifest_to_extraction_run,
)
from product_continuity import ingest_adoption as ingest_adoption_mod
from product_continuity.ingest_adoption import (
    apply_ingest_adoption,
    historical_roots_digest,
    preview_ingest_adoption,
)
from product_continuity.inventory import _durable_run_fingerprint


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _manifest(
    *,
    run_id: str,
    campaign_id: str = "longmont-c2",
    session_id: str = "session-27",
    source_artifact_id: str | None = None,
    graph_sha: str = "c" * 64,
    candidate_uri: str = "runs/graph.json",
) -> GraphIngestRunManifest:
    if source_artifact_id is None:
        source_artifact_id = f"artifact:recap:{campaign_id}:{session_id}:{run_id}"
    return GraphIngestRunManifest(
        run_id=run_id,
        campaign_id=campaign_id,
        session_id=session_id,
        status=GraphIngestRunStatus.READY_FOR_PROJECTION,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        source=GraphIngestSource(
            source_artifact_id=source_artifact_id,
            source_domain="recap",
            input_path_record="corpus/recap.md",
            normalized_recap_sha256="a" * 64,
        ),
        artifacts={
            "source_span_index": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
                uri="runs/spans.json",
                sha256="b" * 64,
                exists=True,
            ),
            "candidate_graph": GraphIngestArtifactRef(
                kind=GraphIngestArtifactKind.CANDIDATE_GRAPH,
                uri=candidate_uri,
                sha256=graph_sha,
                exists=True,
            ),
        },
    )


def _write_manifest(root: Path, manifest: GraphIngestRunManifest) -> Path:
    path = (
        root
        / "out/graph_memory/runs"
        / manifest.run_id
        / "graph_ingest_run_manifest.json"
    )
    _write_json(path, manifest.model_dump(mode="json", by_alias=True))
    return path


def _rewrite_graph_sha(root: Path, run_id: str, sha: str) -> None:
    path = root / "out/graph_memory/runs" / run_id / "graph_ingest_run_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["artifacts"]["candidate_graph"]["sha256"] = sha
    _write_json(path, payload)


def _catalog_ids() -> set[str]:
    return {str(row.get("run_id")) for row in (list_canonical_extraction_runs().get("runs") or [])}


def test_w1_preview_does_not_write(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-preview-only"))
    before_digest = historical_roots_digest(
        ingest_adoption_mod.normalize_historical_roots([("hist", hist)])
    )
    before_count = len(list_extraction_runs())
    report = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-preview-only"],
        all_historical=False,
    )
    assert report.mode == "preview"
    assert report.applied is False
    assert report.blocked is False
    assert report.dispositions[0].action == "adopt"
    assert report.dispositions[0].classification == "RECOVERABLE_EXACT"
    assert report.importer_imported == 0
    assert len(list_extraction_runs()) == before_count == 0
    after_digest = historical_roots_digest(
        ingest_adoption_mod.normalize_historical_roots([("hist", hist)])
    )
    assert after_digest == before_digest


def test_w4_exact_batch_and_mixed_current(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    first = _manifest(run_id="run-c1-exact", campaign_id="longmont-c1", session_id="session-10")
    second = _manifest(run_id="run-c2-exact", campaign_id="longmont-c2", session_id="session-27")
    _write_manifest(hist, first)
    _write_manifest(hist, second)
    expected_first = adapt_recap_manifest_to_extraction_run(first)
    expected_second = adapt_recap_manifest_to_extraction_run(second)

    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-c1-exact", "run-c2-exact"],
        all_historical=False,
    )
    assert preview.blocked is False
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-c1-exact", "run-c2-exact"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is False
    assert report.applied is True
    assert report.importer_imported == 2
    assert report.importer_noop == 0
    assert report.product_verification == "passed"
    loaded_first = get_extraction_run("run-c1-exact")
    loaded_second = get_extraction_run("run-c2-exact")
    assert loaded_first.run_id == "run-c1-exact"
    assert loaded_first.source_artifact_id == expected_first.source_artifact_id
    assert loaded_second.source_artifact_id == expected_second.source_artifact_id
    assert loaded_first.model_dump(mode="json") == expected_first.model_dump(mode="json")
    assert loaded_second.model_dump(mode="json") == expected_second.model_dump(mode="json")
    assert _durable_run_fingerprint(loaded_first) == _durable_run_fingerprint(expected_first)
    assert {run.run_id for run in list_extraction_runs()} == {
        "run-c1-exact",
        "run-c2-exact",
    }

    third = _manifest(run_id="run-c2-new", campaign_id="longmont-c2", session_id="session-28")
    _write_manifest(hist, third)
    mixed_preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-c1-exact", "run-c2-new"],
        all_historical=False,
    )
    mixed = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-c1-exact", "run-c2-new"],
        all_historical=False,
        expected_set_sha256=mixed_preview.target_set_sha256,
    )
    by_id = {row.run_id: row for row in mixed.dispositions}
    assert mixed.blocked is False
    assert mixed.applied is True
    assert by_id["run-c1-exact"].action == "noop"
    assert by_id["run-c1-exact"].classification == "CURRENT_EXACT"
    assert by_id["run-c2-new"].action == "adopt"
    assert mixed.importer_imported == 1
    assert mixed.importer_noop == 0
    assert get_extraction_run("run-c2-new").run_id == "run-c2-new"


def test_w5_payload_changes_before_pin_blocks(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-pin-mutate"))
    original_pin = ingest_adoption_mod._pin_selected_adoptions

    def mutate_then_pin(roots, dispositions, inventory):
        _rewrite_graph_sha(hist, "run-pin-mutate", "9" * 64)
        return original_pin(roots, dispositions, inventory)

    monkeypatch.setattr(ingest_adoption_mod, "_pin_selected_adoptions", mutate_then_pin)
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-pin-mutate"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-pin-mutate"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert list_extraction_runs() == []
    assert "does not match" in (report.detail or "")


def test_w5_live_change_after_pin_blocks(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-revalidate"))
    original_revalidate = ingest_adoption_mod._revalidate_pinned_evidence

    def mutate_then_revalidate(roots, pins):
        _rewrite_graph_sha(hist, "run-revalidate", "8" * 64)
        return original_revalidate(roots, pins)

    monkeypatch.setattr(
        ingest_adoption_mod, "_revalidate_pinned_evidence", mutate_then_revalidate
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-revalidate"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-revalidate"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert list_extraction_runs() == []


def test_w5_live_delete_after_pin_blocks(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-revalidate-del"))
    original_revalidate = ingest_adoption_mod._revalidate_pinned_evidence

    def delete_then_revalidate(roots, pins):
        target = (
            hist
            / "out/graph_memory/runs/run-revalidate-del/graph_ingest_run_manifest.json"
        )
        target.unlink()
        return original_revalidate(roots, pins)

    monkeypatch.setattr(
        ingest_adoption_mod, "_revalidate_pinned_evidence", delete_then_revalidate
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-revalidate-del"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-revalidate-del"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is True
    assert report.applied is False
    assert list_extraction_runs() == []


def test_w5_importer_consumes_pinned_snapshot_not_live_root(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    original = _manifest(run_id="run-pinned-snapshot")
    _write_manifest(hist, original)
    original_fp = _durable_run_fingerprint(adapt_recap_manifest_to_extraction_run(original))
    captured: dict[str, object] = {}
    real_import = import_extraction_runs_from_registry

    def spy(root: Path, *, dry_run: bool = False):
        captured["root"] = str(Path(root).resolve())
        captured["hist"] = str(hist.resolve())
        registry = Path(root) / "out/registries/extraction_runs.json"
        payload = json.loads(registry.read_text(encoding="utf-8"))
        captured["pinned_run_id"] = payload["records"][0]["run_id"]
        captured["pinned_sha"] = payload["records"][0]["components"]["candidate_graph"][
            "sha256"
        ]
        _rewrite_graph_sha(hist, "run-pinned-snapshot", "7" * 64)
        return real_import(root, dry_run=dry_run)

    monkeypatch.setattr(ingest_adoption_mod, "import_extraction_runs_from_registry", spy)
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-pinned-snapshot"],
        all_historical=False,
    )
    committed = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-pinned-snapshot"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert committed.blocked is False
    assert committed.applied is True
    assert captured["root"] != captured["hist"]
    assert captured["pinned_sha"] == "c" * 64
    loaded = get_extraction_run("run-pinned-snapshot")
    assert _durable_run_fingerprint(loaded) == original_fp
    mutated = json.loads(
        (
            hist
            / "out/graph_memory/runs/run-pinned-snapshot/graph_ingest_run_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert mutated["artifacts"]["candidate_graph"]["sha256"] == "7" * 64


def test_w5_expected_hash_mismatch_blocks(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-hash-a"))
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-hash-a"],
        all_historical=False,
    )
    _rewrite_graph_sha(hist, "run-hash-a", "1" * 64)
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-hash-a"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert "does not match --expected-set-sha256" in (report.detail or "")
    assert list_extraction_runs() == []


def test_w6_unsafe_sibling_blocks_entire_set(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-safe-sibling"))
    _write_manifest(
        hist,
        GraphIngestRunManifest(
            run_id="run-adapt-failed",
            campaign_id="longmont-c2",
            session_id="session-22",
            source=GraphIngestSource(source_domain="recap"),
        ),
    )
    before = historical_roots_digest(
        ingest_adoption_mod.normalize_historical_roots([("hist", hist)])
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-safe-sibling", "run-adapt-failed"],
        all_historical=False,
    )
    assert preview.blocked is True
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-safe-sibling", "run-adapt-failed"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.importer_imported == 0
    assert list_extraction_runs() == []
    assert historical_roots_digest(
        ingest_adoption_mod.normalize_historical_roots([("hist", hist)])
    ) == before
    by_id = {row.run_id: row for row in report.dispositions}
    assert by_id["run-safe-sibling"].classification == "RECOVERABLE_EXACT"
    assert by_id["run-safe-sibling"].action == "adopt"
    assert by_id["run-adapt-failed"].action == "block"
    assert by_id["run-adapt-failed"].classification == "NEEDS_ADAPTER"


def test_w7_current_conflict_rolls_back_sibling(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    conflict = _manifest(run_id="run-conflict-current")
    sibling = _manifest(run_id="run-safe-absent")
    _write_manifest(hist, conflict)
    _write_manifest(hist, sibling)
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-conflict-current", "run-safe-absent"],
        all_historical=False,
    )
    assert preview.blocked is False

    seeded = adapt_recap_manifest_to_extraction_run(conflict).model_copy(
        update={"source_artifact_id": "artifact:recap:seeded-conflict"}
    )
    original_import = import_extraction_runs_from_registry

    def seed_then_import(root: Path, *, dry_run: bool = False):
        create_extraction_run(seeded)
        return original_import(root, dry_run=dry_run)

    monkeypatch.setattr(
        ingest_adoption_mod, "import_extraction_runs_from_registry", seed_then_import
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-conflict-current", "run-safe-absent"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is True
    assert report.applied is False
    ids = {run.run_id for run in list_extraction_runs()}
    assert "run-safe-absent" not in ids
    assert ids == {"run-conflict-current"}
    assert get_extraction_run("run-conflict-current").source_artifact_id == (
        "artifact:recap:seeded-conflict"
    )


def test_w8_w9_replay_is_idempotent_and_roots_unchanged(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-replay"))
    roots = ingest_adoption_mod.normalize_historical_roots([("hist", hist)])
    before = historical_roots_digest(roots)
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-replay"],
        all_historical=False,
    )
    first = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-replay"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert first.applied is True
    assert first.historical_roots_unchanged == "true"
    assert historical_roots_digest(roots) == before
    first_fp = _durable_run_fingerprint(get_extraction_run("run-replay"))
    replay_preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-replay"],
        all_historical=False,
    )
    replay = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-replay"],
        all_historical=False,
        expected_set_sha256=replay_preview.target_set_sha256,
    )
    assert replay.blocked is False
    assert replay.applied is True
    assert replay.dispositions[0].classification == "CURRENT_EXACT"
    assert replay.dispositions[0].action == "noop"
    assert replay.importer_imported == 0
    assert len(list_extraction_runs()) == 1
    assert _durable_run_fingerprint(get_extraction_run("run-replay")) == first_fp
    assert historical_roots_digest(roots) == before
    assert replay.historical_roots_unchanged == "true"


def test_w10_catalog_survives_without_manifests(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(
        hist,
        _manifest(run_id="run-catalog", campaign_id="longmont-c1", session_id="session-03"),
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-catalog"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-catalog"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.applied is True
    assert "run-catalog" in _catalog_ids()
    manifest = hist / "out/graph_memory/runs/run-catalog/graph_ingest_run_manifest.json"
    manifest.unlink()
    assert list(hist.glob("out/graph_memory/runs/**/graph_ingest_run_manifest.json")) == []
    assert "run-catalog" in _catalog_ids()
    loaded = get_extraction_run("run-catalog")
    assert loaded.run_id == "run-catalog"
    assert loaded.campaign_id == "longmont-c1"


def test_w12_post_commit_failure_keeps_rows_and_redacts_secrets(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    from contextlib import redirect_stdout
    from io import StringIO

    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-verify-fail"))
    secret = "hunter2-not-for-logs"
    fake_dsn = (
        f"postgresql://buddy:{secret}@127.0.0.1:54329/dungeonbuddy_application_state"
    )
    raise_on_seam = {"on": False}
    original_verify = ingest_adoption_mod._verify_product_seam
    original_import = import_extraction_runs_from_registry

    def exploding_verify(*, dispositions, pins):
        if raise_on_seam["on"]:
            raise ApplicationStateUnavailableError(
                f"APP-STATE unavailable using {fake_dsn}"
            )
        return original_verify(dispositions=dispositions, pins=pins)

    def import_then_arm(root: Path, *, dry_run: bool = False):
        result = original_import(root, dry_run=dry_run)
        raise_on_seam["on"] = True
        return result

    monkeypatch.setattr(ingest_adoption_mod, "_verify_product_seam", exploding_verify)
    monkeypatch.setattr(
        ingest_adoption_mod, "import_extraction_runs_from_registry", import_then_arm
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-verify-fail"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-verify-fail"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.blocked is False
    assert report.applied is True
    assert report.importer_imported == 1
    assert report.product_verification == "failed"
    assert report.detail == "adoption committed; product verification failed"
    blob = "\n".join(
        part
        for part in (report.detail, report.product_verification_detail)
        if part
    )
    assert secret not in blob
    assert fake_dsn not in blob
    assert get_extraction_run("run-verify-fail").run_id == "run-verify-fail"

    script = (
        Path(__file__).resolve().parents[2] / "scripts" / "adopt_historical_ingest_runs.py"
    )
    spec = importlib.util.spec_from_file_location(
        "adopt_historical_ingest_cli_secret", script
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    buf = StringIO()
    with redirect_stdout(buf):
        module._print_report(report)
    printed = buf.getvalue()
    assert secret not in printed
    assert fake_dsn not in printed

    raise_on_seam["on"] = False
    replay_preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-verify-fail"],
        all_historical=False,
    )
    replay = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-verify-fail"],
        all_historical=False,
        expected_set_sha256=replay_preview.target_set_sha256,
    )
    assert replay.dispositions[0].classification == "CURRENT_EXACT"
    assert replay.dispositions[0].action == "noop"
    assert replay.product_verification == "passed"
    assert len(list_extraction_runs()) == 1


def test_w12_post_commit_root_digest_failure_keeps_rows(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-digest-fail"))
    raise_on_digest = {"on": False}
    original_digest = ingest_adoption_mod.historical_roots_digest
    original_import = import_extraction_runs_from_registry

    def digest_maybe_raise(roots):
        if raise_on_digest["on"]:
            raise OSError("historical root unreadable after commit")
        return original_digest(roots)

    def import_then_arm(root: Path, *, dry_run: bool = False):
        result = original_import(root, dry_run=dry_run)
        raise_on_digest["on"] = True
        return result

    monkeypatch.setattr(ingest_adoption_mod, "historical_roots_digest", digest_maybe_raise)
    monkeypatch.setattr(
        ingest_adoption_mod, "import_extraction_runs_from_registry", import_then_arm
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-digest-fail"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-digest-fail"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.applied is True
    assert report.product_verification == "failed"
    assert report.detail == "adoption committed; product verification failed"
    assert "rolled back" not in (report.detail or "").lower()
    assert get_extraction_run("run-digest-fail").run_id == "run-digest-fail"


def test_w13_missing_component_bytes_do_not_hide_catalog_row(
    application_state_dsn: str, tmp_path: Path
) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    missing_uri = "out/graph_memory/runs/run-missing-bytes/candidate_graph.json"
    _write_manifest(
        hist,
        _manifest(run_id="run-missing-bytes", candidate_uri=missing_uri),
    )
    preview = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-missing-bytes"],
        all_historical=False,
    )
    report = apply_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-missing-bytes"],
        all_historical=False,
        expected_set_sha256=preview.target_set_sha256,
    )
    assert report.applied is True
    assert report.product_verification == "passed"
    assert report.unavailable_component_count >= 1
    loaded = get_extraction_run("run-missing-bytes")
    assert loaded.run_id == "run-missing-bytes"
    assert loaded.components["candidate_graph"].uri == missing_uri
    assert "run-missing-bytes" in _catalog_ids()
    assert not (current / missing_uri).is_file()
    assert not (hist / missing_uri).is_file()
