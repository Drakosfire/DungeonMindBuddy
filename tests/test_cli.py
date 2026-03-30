from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from src.cli import DungeonBuddyCLI


def test_ask_require_campaign_fails_fast_without_campaign(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line('ask "What happened?" --require-campaign')
    output = capture.getvalue()
    assert "campaign scope is required" in output.lower()


def test_compact_command_runs(tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    cli = DungeonBuddyCLI(store_dir=store_dir, verbose=False)
    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line("compact")
    output = capture.getvalue()
    assert "compaction complete" in output.lower()


def test_ingest_without_frontmatter_and_no_layer_fails_fast(tmp_path: Path) -> None:
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nNo metadata.\n", encoding="utf-8")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}" --no-frontmatter')
    output = capture.getvalue().lower()
    assert "--layer is required" in output


def test_ingest_frontmatter_makes_layer_optional(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "battle.md"
    source.write_text(
        (
            "---\n"
            'title: "Battle with The Wolf and Aftermath"\n'
            "document_class: play\n"
            "canon_layer: campaign\n"
            "campaign_id: longmont-c1\n"
            "session: 8\n"
            "source_class: observed_session_recap\n"
            "---\n\n"
            "# Encounter\n\n"
            "The wolf receives a killing blow.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}"')
    output = capture.getvalue().lower()
    assert "openai_api_key is required for ingest" in output
    assert "--layer is required" not in output


def test_ingest_frontmatter_conflict_with_cli_flags_fails(tmp_path: Path) -> None:
    source = tmp_path / "battle.md"
    source.write_text(
        (
            "---\n"
            'title: "Battle with The Wolf and Aftermath"\n'
            "document_class: play\n"
            "canon_layer: campaign\n"
            "campaign_id: longmont-c1\n"
            "session: 8\n"
            "source_class: observed_session_recap\n"
            "---\n\n"
            "# Encounter\n\n"
            "The wolf receives a killing blow.\n"
        ),
        encoding="utf-8",
    )
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}" --layer world')
    output = capture.getvalue().lower()
    assert "frontmatter conflicts with cli arguments" in output


def test_ingest_missing_frontmatter_runs_inference_loop(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "no_meta.md"
    source.write_text("# Session 2 Recap\n\nThe council reconvenes.\n", encoding="utf-8")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    monkeypatch.setattr("src.cli.infer_frontmatter_metadata", lambda **_: None)

    def _fake_confirm(self, source_path, text):  # noqa: ANN001
        _ = text
        source_path.write_text(
            (
                "---\n"
                'title: "Session 2 Recap"\n'
                "document_class: play\n"
                "canon_layer: campaign\n"
                "campaign_id: longmont-c1\n"
                "session: 2\n"
                "source_class: observed_session_recap\n"
                "---\n\n"
                "# Session 2 Recap\n\nThe council reconvenes.\n"
            ),
            encoding="utf-8",
        )
        return True

    monkeypatch.setattr(DungeonBuddyCLI, "_confirm_inferred_frontmatter", _fake_confirm)
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}"')
    output = capture.getvalue().lower()
    assert "openai_api_key is required for ingest" in output


def test_ingest_writes_stage_artifacts_and_gate_report(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "world.md"
    source.write_text(
        (
            "---\n"
            'title: "Mirathorn Primer"\n'
            "document_class: world\n"
            "canon_layer: world\n"
            "source_class: seed_reference\n"
            "---\n\n"
            "# Primer\n\n"
            "Mirathorn is prosperous and active.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class _DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            _ = (args, kwargs)

    monkeypatch.setattr("src.cli.AsyncOpenAIResponsesEntityClient", _DummyClient)
    monkeypatch.setattr("src.cli.AsyncOpenAIResponsesFactClient", _DummyClient)

    def _mock_entity_extraction(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        return [
            {
                "schema_version": "0.1.0",
                "created_at": "2026-03-27T00:00:00Z",
                "updated_at": "2026-03-27T00:00:00Z",
                "record_status": "active",
                "entity_id": "ent_mirathorn",
                "entity_type": "location",
                "display_name": "Mirathorn",
                "canonical_name": None,
                "aliases": ["City of Mirathorn"],
                "entity_status": "provisional",
                "merged_into_entity_id": None,
                "source_mention_ids": ["men_ent_mirathorn"],
                "review_state": "unreviewed",
                "notes": None,
            }
        ]

    def _mock_fact_extraction(evidence_units, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        _ = (args, kwargs)
        return [
            {
                "schema_version": "0.1.0",
                "created_at": "2026-03-27T00:00:00Z",
                "updated_at": "2026-03-27T00:00:00Z",
                "record_status": "active",
                "fact_id": "fact_store_001",
                "subject_entity_id": "ent_mirathorn",
                "attribute": "operational_status",
                "value": {
                    "kind": "state",
                    "label": "Prosperous and active",
                    "normalized": "prosperous",
                },
                "truth_state": "CANON",
                "source_authority": "seed_prep",
                "evidence_ids": [evidence_units[0]["evidence_id"]],
                "asserted_in_session": None,
                "sequence_index_within_session": None,
            }
        ]

    monkeypatch.setattr("src.cli.run_entity_extraction", _mock_entity_extraction)
    monkeypatch.setattr("src.cli.run_fact_extraction", _mock_fact_extraction)

    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}"')

    artifacts_root = tmp_path / "store" / "logs" / "ingest_artifacts"
    runs = list(artifacts_root.glob("ingest-*"))
    assert len(runs) == 1
    gate_report_path = runs[0] / "gate_report.json"
    assert (runs[0] / "stage_chunks.json").exists()
    assert (runs[0] / "stage_entities.json").exists()
    assert (runs[0] / "stage_facts.json").exists()
    assert gate_report_path.exists()

    gate_report = json.loads(gate_report_path.read_text(encoding="utf-8"))
    assert gate_report["overall_pass"] is True
    assert (tmp_path / "store" / "facts.json").exists()


def test_ingest_gate_failure_prevents_store_mutation(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "world.md"
    source.write_text(
        (
            "---\n"
            'title: "Mirathorn Primer"\n'
            "document_class: world\n"
            "canon_layer: world\n"
            "source_class: seed_reference\n"
            "---\n\n"
            "# Primer\n\n"
            "Mirathorn is prosperous and active.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class _DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            _ = (args, kwargs)

    monkeypatch.setattr("src.cli.AsyncOpenAIResponsesEntityClient", _DummyClient)
    monkeypatch.setattr("src.cli.AsyncOpenAIResponsesFactClient", _DummyClient)

    def _mock_entity_extraction(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = (args, kwargs)
        return [
            {
                "schema_version": "0.1.0",
                "created_at": "2026-03-27T00:00:00Z",
                "updated_at": "2026-03-27T00:00:00Z",
                "record_status": "active",
                "entity_id": "ent_mirathorn",
                "entity_type": "location",
                "display_name": "Mirathorn",
                "canonical_name": None,
                "aliases": ["City of Mirathorn"],
                "entity_status": "provisional",
                "merged_into_entity_id": None,
                "source_mention_ids": ["men_ent_mirathorn"],
                "review_state": "unreviewed",
                "notes": None,
            }
        ]

    monkeypatch.setattr("src.cli.run_entity_extraction", _mock_entity_extraction)
    monkeypatch.setattr("src.cli.run_fact_extraction", lambda *args, **kwargs: [])

    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}"')
    output = capture.getvalue().lower()
    assert "stage gates failed" in output

    artifacts_root = tmp_path / "store" / "logs" / "ingest_artifacts"
    runs = list(artifacts_root.glob("ingest-*"))
    assert len(runs) == 1
    gate_report = json.loads((runs[0] / "gate_report.json").read_text(encoding="utf-8"))
    assert gate_report["overall_pass"] is False
    assert not (tmp_path / "store" / "facts.json").exists()


def test_ingest_invalid_concurrency_fails_fast(tmp_path: Path) -> None:
    source = tmp_path / "world.md"
    source.write_text(
        (
            "---\n"
            'title: "Mirathorn Primer"\n'
            "document_class: world\n"
            "canon_layer: world\n"
            "source_class: seed_reference\n"
            "---\n\n"
            "# Primer\n\n"
            "Mirathorn is prosperous and active.\n"
        ),
        encoding="utf-8",
    )
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}" --entity-concurrency 0')
    output = capture.getvalue().lower()
    assert "--entity-concurrency must be >= 1" in output
    assert "openai_api_key is required for ingest" not in output


def test_ingest_passes_concurrency_options_to_extractors(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "world.md"
    source.write_text(
        (
            "---\n"
            'title: "Mirathorn Primer"\n'
            "document_class: world\n"
            "canon_layer: world\n"
            "source_class: seed_reference\n"
            "---\n\n"
            "# Primer\n\n"
            "Mirathorn is prosperous and active.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class _DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            _ = (args, kwargs)

    monkeypatch.setattr("src.cli.AsyncOpenAIResponsesEntityClient", _DummyClient)
    monkeypatch.setattr("src.cli.AsyncOpenAIResponsesFactClient", _DummyClient)

    captured: dict[str, int] = {}

    def _mock_entity_extraction(*args, **kwargs):  # noqa: ANN002, ANN003
        _ = args
        captured["entity_concurrency"] = int(kwargs["concurrency"])
        return [
            {
                "schema_version": "0.1.0",
                "created_at": "2026-03-27T00:00:00Z",
                "updated_at": "2026-03-27T00:00:00Z",
                "record_status": "active",
                "entity_id": "ent_mirathorn",
                "entity_type": "location",
                "display_name": "Mirathorn",
                "canonical_name": None,
                "aliases": ["City of Mirathorn"],
                "entity_status": "provisional",
                "merged_into_entity_id": None,
                "source_mention_ids": ["men_ent_mirathorn"],
                "review_state": "unreviewed",
                "notes": None,
            }
        ]

    def _mock_fact_extraction(evidence_units, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        _ = args
        captured["fact_concurrency"] = int(kwargs["concurrency"])
        return [
            {
                "schema_version": "0.1.0",
                "created_at": "2026-03-27T00:00:00Z",
                "updated_at": "2026-03-27T00:00:00Z",
                "record_status": "active",
                "fact_id": "fact_store_001",
                "subject_entity_id": "ent_mirathorn",
                "attribute": "operational_status",
                "value": {
                    "kind": "state",
                    "label": "Prosperous and active",
                    "normalized": "prosperous",
                },
                "truth_state": "CANON",
                "source_authority": "seed_prep",
                "evidence_ids": [evidence_units[0]["evidence_id"]],
                "asserted_in_session": None,
                "sequence_index_within_session": None,
            }
        ]

    monkeypatch.setattr("src.cli.run_entity_extraction", _mock_entity_extraction)
    monkeypatch.setattr("src.cli.run_fact_extraction", _mock_fact_extraction)

    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    with redirect_stdout(io.StringIO()):
        cli.handle_line(f'ingest "{source}" --entity-concurrency 3 --fact-concurrency 5')

    assert captured["entity_concurrency"] == 3
    assert captured["fact_concurrency"] == 5
