from __future__ import annotations

import json
from pathlib import Path

from src.live_play.recap_derivative_provenance import (
    archive_existing,
    provenance_path,
    read_provenance_state,
    sha256_bytes,
    store_provenanced_artifact,
)


def _store(root: Path, output: Path, *, force: bool = False, content: bytes = b"routed"):
    return store_provenanced_artifact(
        output_path=output,
        corpus_root=root,
        stage="breadcrumbed_recap",
        campaign_number=2,
        session=29,
        input_digests={"normalized_recap": "normalized-v1", "frontmatter_seed": "seed-v1"},
        content=content,
        force=force,
    )


def test_provenance_round_trip_and_changed_input_detection(tmp_path: Path) -> None:
    output = tmp_path / "Session Recaps/_breadcrumbed/Session 29 - Example.breadcrumbed.md"
    output.parent.mkdir(parents=True)
    state, archived = _store(tmp_path, output)

    assert state == "created"
    assert archived == []
    assert output.read_bytes() == b"routed"
    assert read_provenance_state(
        output_path=output,
        corpus_root=tmp_path,
        stage="breadcrumbed_recap",
        campaign_number=2,
        session=29,
        input_digests={"normalized_recap": "normalized-v1", "frontmatter_seed": "seed-v1"},
    )[0] == "current"
    assert read_provenance_state(
        output_path=output,
        corpus_root=tmp_path,
        stage="breadcrumbed_recap",
        campaign_number=2,
        session=29,
        input_digests={"normalized_recap": "normalized-v2", "frontmatter_seed": "seed-v1"},
    )[0] == "stale"


def test_missing_or_corrupt_sidecar_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "Session Recaps/_breadcrumbed/Session 29 - Example.breadcrumbed.md"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"legacy")
    expected = {
        "stage": "breadcrumbed_recap",
        "campaign_number": 2,
        "session": 29,
        "input_digests": {"normalized_recap": "n", "frontmatter_seed": "s"},
    }
    assert read_provenance_state(
        output_path=output, corpus_root=tmp_path, **expected
    )[0] == "unknown"

    provenance_path(output).write_text("{bad json", encoding="utf-8")
    assert read_provenance_state(
        output_path=output, corpus_root=tmp_path, **expected
    )[0] == "corrupt"


def test_edited_seed_with_current_inputs_is_distinguishable(tmp_path: Path) -> None:
    output = tmp_path / "Session Recaps/_breadcrumbed/Session 29 - Example.frontmatter_seed.md"
    output.parent.mkdir(parents=True)
    _store(tmp_path, output, content=b"generated seed")
    output.write_bytes(b"reviewed seed")

    state = read_provenance_state(
        output_path=output,
        corpus_root=tmp_path,
        stage="breadcrumbed_recap",
        campaign_number=2,
        session=29,
        input_digests={"normalized_recap": "normalized-v1", "frontmatter_seed": "seed-v1"},
    )[0]
    assert state == "edited_current_inputs"


def test_refresh_archives_old_artifact_and_sidecar_before_replacement(tmp_path: Path) -> None:
    output = tmp_path / "Session Recaps/_breadcrumbed/Session 29 - Example.breadcrumbed.md"
    output.parent.mkdir(parents=True)
    _store(tmp_path, output, content=b"old")

    state, archived = _store(tmp_path, output, force=True, content=b"new")

    assert state == "refreshed"
    assert output.read_bytes() == b"new"
    assert len(archived) == 2
    assert {Path(row["from"]).name for row in archived} == {
        output.name,
        provenance_path(output).name,
    }
    assert all((tmp_path / row["to"]).is_file() for row in archived)
    assert json.loads(provenance_path(output).read_text(encoding="utf-8"))["output_sha256"] == sha256_bytes(b"new")


def test_archive_refuses_paths_outside_corpus(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    try:
        archive_existing(paths=[outside], corpus_root=tmp_path)
    except ValueError as exc:
        assert "outside corpus" in str(exc)
    else:
        raise AssertionError("outside path should not be archived")
    assert outside.read_text(encoding="utf-8") == "keep"
