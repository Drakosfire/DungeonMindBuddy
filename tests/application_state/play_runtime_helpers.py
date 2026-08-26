"""Shared fixtures for AS3 Play Runtime owning-boundary tests."""

from __future__ import annotations

import os
import statistics
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    create_or_replay_play_run,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    derive_sealed_manifest,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)
from src.live_play.live_store import write_json

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

SOURCE_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
        "## The Gate",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->",
        "### Arrival",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:briefing -->",
        "### Briefing",
        "",
        "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
        "### Which route do they take?",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
        "#### Burn through the growth",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
        "#### Wait and watch",
        "",
    ]
)

SURVIVING_TARGET_MARKDOWN = SOURCE_MARKDOWN + "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:keep -->",
        "## The Keep",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:inside -->",
        "### Inside",
        "",
    ]
)

INVALID_PLAYABLE_MARKDOWN = "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n"


def commit_runbook_markdown(root: Path, document_id: str, markdown: str, expected_revision: int) -> None:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=expected_revision,
        ),
    )
    assert prepared.writer_ok
    assert prepared.writer_confirm_token
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=expected_revision,
        ),
    )


def create_committed_runbook(
    root: Path,
    *,
    name: str = "as3-play",
    markdown: str = SOURCE_MARKDOWN,
    campaign_id: str = "longmont-c2",
):
    record = create_workspace_document(
        root,
        title=f"Runbook {name}",
        campaign_id=campaign_id,
        kind="runbook",
        target_relpath=f"evals/c2_live_prep/mireward-prep/content/tiptap/{name}.md",
    )
    commit_runbook_markdown(root, record.document_id, markdown, record.revision)
    return get_workspace_document_snapshot(root, record.document_id)


def playable_of(snapshot) -> tuple[int, str]:
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    return committed.revision_n, committed.content_sha256


def create_run(root: Path, snapshot, *, run_id: str = RUN_ID_A):
    revision_n, sha = playable_of(snapshot)
    return create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=snapshot.record.document_id,
        expected_playable_revision=revision_n,
        expected_playable_content_sha256=sha,
    )


def empty_progress() -> PlayRunProgress:
    return PlayRunProgress(
        current_scene_id=None,
        current_beat_id=None,
        resolved_beat_ids=[],
        selections={},
        notes_by_element_id={},
    )


def gate_progress() -> PlayRunProgress:
    return PlayRunProgress(
        current_scene_id="scene:gate",
        current_beat_id="beat:arrival",
        resolved_beat_ids=["beat:arrival"],
        selections={"choice:route": "option:fire"},
        notes_by_element_id={"scene:gate": "Noted."},
    )


def count_play_rows(dsn: str) -> tuple[int, int]:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        runs = conn.execute("SELECT count(*) FROM play.run").fetchone()[0]
        manifests = conn.execute("SELECT count(*) FROM play.run_manifest").fetchone()[0]
    return int(runs), int(manifests)


@contextmanager
def hidden_legacy_runtime_dirs(root: Path) -> Iterator[None]:
    dirs = [
        root / "out/runtime/play/runs",
        root / "out/runtime/play/reference-manifests",
        root / "out/runtime/play/rebase-intents",
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0)
    try:
        yield
    finally:
        for directory in dirs:
            os.chmod(directory, 0o755)


def write_legacy_run_and_manifest(
    root: Path,
    *,
    run_id: str,
    snapshot,
    run_revision: int = 1,
    progress: PlayRunProgress | None = None,
    created_at: str = "2026-01-01T00:00:00Z",
    playable_revision: int | None = None,
    playable_content_sha256: str | None = None,
    markdown: str | None = None,
) -> None:
    from apps.live_control_server.services.play_run_registry import (
        PlayRunRecord,
        play_run_path,
    )
    from apps.live_control_server.services.play_run_reference_manifest import (
        play_run_reference_manifest_path,
    )

    revision_n, sha = playable_of(snapshot)
    if playable_revision is not None:
        revision_n = playable_revision
    if playable_content_sha256 is not None:
        sha = playable_content_sha256
    record = PlayRunRecord(
        run_id=run_id,
        campaign_id=snapshot.record.campaign_id,
        playable_artifact_id=snapshot.record.document_id,
        playable_revision=revision_n,
        playable_content_sha256=sha,
        run_revision=run_revision,
        created_at=created_at,
        updated_at=created_at,
        progress=progress or empty_progress(),
    )
    run_path = play_run_path(root, run_id)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(run_path, record.model_dump(mode="json"))
    manifest = derive_sealed_manifest(
        snapshot.markdown if markdown is None else markdown,
        run_id=run_id,
        playable_artifact_id=snapshot.record.document_id,
        playable_revision=revision_n,
        playable_content_sha256=sha,
        sealed_at=created_at,
    )
    manifest_path = play_run_reference_manifest_path(root, run_id)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest.model_dump(mode="json", exclude_none=True))


def percentile(samples: list[float], p: float) -> float:
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    index = min(len(ordered) - 1, max(0, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def measure_ms(fn, samples: int = 30) -> tuple[float, float, float]:
    timings: list[float] = []
    for _ in range(samples):
        started = time.perf_counter()
        fn()
        timings.append((time.perf_counter() - started) * 1000)
    return statistics.median(timings), percentile(timings, 95), max(timings)
