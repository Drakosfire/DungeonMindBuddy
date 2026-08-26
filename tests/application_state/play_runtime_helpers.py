"""Shared fixtures for AS3 Play Runtime owning-boundary tests."""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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

V2_SOURCE_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:arrival -->",
        "## Arrival",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->",
        "### The Gate",
        "",
        "<!-- dmb-playable-element:v2 kind=choice id=choice:route -->",
        "### Which route do they take?",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:fire -->",
        "- Burn through the growth",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:wait -->",
        "- Wait and watch",
        "",
    ]
)

V2_SURVIVING_TARGET_MARKDOWN = V2_SOURCE_MARKDOWN + "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:inside -->",
        "## Inside",
        "",
    ]
)

AS2_FILE_BACKED_BASE_SHA = "b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0"


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
    campaign_id: str | None = None,
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
        campaign_id=campaign_id or snapshot.record.campaign_id,
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


def corrupt_play_run_progress(dsn: str, run_id: str, progress: dict) -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE play.run SET progress = %(progress)s WHERE run_id = %(run_id)s",
            {"progress": Jsonb(progress), "run_id": run_id},
        )


def corrupt_play_run_manifest_document(dsn: str, run_id: str, manifest: dict) -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            "UPDATE play.run_manifest SET manifest = %(manifest)s WHERE run_id = %(run_id)s",
            {"manifest": Jsonb(manifest), "run_id": run_id},
        )


def fetch_play_runtime_state(dsn: str, run_id: str) -> dict:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT run_revision, progress, playable_revision_n,
                       playable_content_sha256, rebased_from_run_revision,
                       created_at, updated_at
                FROM play.run
                WHERE run_id = %s
                """,
                (run_id,),
            )
            run = cur.fetchone()
            cur.execute(
                """
                SELECT playable_work_object_id, playable_revision_n,
                       playable_work_revision_id, playable_content_sha256,
                       manifest, sealed_at
                FROM play.run_manifest
                WHERE run_id = %s
                """,
                (run_id,),
            )
            manifest = cur.fetchone()
    assert run is not None
    assert manifest is not None
    return {"run": dict(run), "manifest": dict(manifest)}


def unknown_schema_manifest(document: dict) -> dict:
    corrupted = dict(document)
    corrupted["schema_version"] = "dmb_play_run_reference_manifest_v9"
    return corrupted


def write_legacy_active_run_pointer(root: Path, *, run_id: str, selected_at: str) -> Path:
    from apps.live_control_server.services.play_active_run import (
        PLAY_ACTIVE_RUN_SCHEMA,
        play_active_run_path,
    )

    path = play_active_run_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        {
            "schema_version": PLAY_ACTIVE_RUN_SCHEMA,
            "run_id": run_id,
            "selected_at": selected_at,
        },
    )
    return path


_BASELINE_LATENCY_SCRIPT = r"""
from __future__ import annotations

import json
import statistics
import time
import uuid
from pathlib import Path

from apps.live_control_server.services.play_run_registry import (
    PlayRunProgress,
    create_or_replay_play_run,
    get_play_run,
    replace_play_run_progress,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    seal_or_replay_play_run_reference_manifest,
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

MARKDOWN = "\n".join(
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
SAMPLES = 30
RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def percentile(samples: list[float], p: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def measure(fn) -> tuple[float, float]:
    timings = []
    for _ in range(SAMPLES):
        started = time.perf_counter()
        fn()
        timings.append((time.perf_counter() - started) * 1000)
    return statistics.median(timings), percentile(timings, 95)


root = Path("baseline-root")
root.mkdir()
record = create_workspace_document(
    root,
    title="Runbook latency",
    campaign_id="longmont-c2",
    kind="runbook",
    target_relpath="evals/c2_live_prep/mireward-prep/content/tiptap/latency.md",
)
prepared = prepare_tiptap_markdown_write(
    root=root,
    request=TiptapMarkdownWritePrepareRequest(
        document_id=record.document_id,
        markdown=MARKDOWN,
        expected_revision=record.revision,
    ),
)
commit_tiptap_markdown_write(
    root=root,
    request=TiptapMarkdownWriteCommitRequest(
        document_id=record.document_id,
        markdown=MARKDOWN,
        writer_confirm_token=prepared.writer_confirm_token,
        expected_revision=record.revision,
    ),
)
committed = get_committed_playable_revision(record.document_id, kind=None)


def start_and_seal() -> None:
    run_id = str(uuid.uuid4())
    create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=record.document_id,
        expected_playable_revision=committed.revision_n,
        expected_playable_content_sha256=committed.content_sha256,
    )
    seal_or_replay_play_run_reference_manifest(root, run_id)


start_p50, start_p95 = measure(start_and_seal)
durable = create_or_replay_play_run(
    root,
    run_id=RUN_ID,
    playable_artifact_id=record.document_id,
    expected_playable_revision=committed.revision_n,
    expected_playable_content_sha256=committed.content_sha256,
)
seal_or_replay_play_run_reference_manifest(root, RUN_ID)
replace_play_run_progress(
    root,
    run_id=RUN_ID,
    expected_run_revision=durable.run_revision,
    progress=PlayRunProgress(
        current_scene_id="scene:gate",
        current_beat_id="beat:arrival",
        resolved_beat_ids=["beat:arrival"],
        selections={"choice:route": "option:fire"},
        notes_by_element_id={"scene:gate": "Noted."},
    ),
)


def cas() -> None:
    current = get_play_run(root, RUN_ID)
    replace_play_run_progress(
        root,
        run_id=RUN_ID,
        expected_run_revision=current.run_revision,
        progress=PlayRunProgress(
            current_scene_id="scene:gate",
            current_beat_id="beat:arrival",
            resolved_beat_ids=["beat:arrival"],
            selections={"choice:route": "option:fire"},
            notes_by_element_id={"scene:gate": str(uuid.uuid4())},
        ),
    )


cas_p50, cas_p95 = measure(cas)
print(
    json.dumps(
        {
            "start_plus_seal_p50_ms": start_p50,
            "start_plus_seal_p95_ms": start_p95,
            "cas_p50_ms": cas_p50,
            "cas_p95_ms": cas_p95,
        }
    )
)
"""


def measure_file_backed_baseline_latency() -> dict[str, float]:
    """Time AS2 file-backed Start+seal and CAS at the exact predecessor SHA."""
    import psycopg
    from psycopg import sql

    from application_state.config import APPLICATION_STATE_DSN_ENV, TEST_ADMIN_DSN_ENV
    from application_state.naming import assert_safe_application_state_database_name

    repo = Path(__file__).resolve().parents[2]
    worktree = Path(tempfile.gettempdir()) / f"as3-as2-baseline-{uuid.uuid4().hex}"
    admin = os.environ.get(TEST_ADMIN_DSN_ENV, "").strip() or (
        "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/postgres"
    )
    db_name = f"dungeonbuddy_app_state_test_{uuid.uuid4().hex[:12]}"
    parsed = urlparse(admin)
    dsn = urlunparse(parsed._replace(path=f"/{db_name}"))
    created_db = False
    added_worktree = False
    try:
        subprocess.check_call(
            ["git", "worktree", "add", "--detach", str(worktree), AS2_FILE_BACKED_BASE_SHA],
            cwd=repo,
        )
        added_worktree = True
        assert_safe_application_state_database_name(db_name)
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        created_db = True
        env = {
            **os.environ,
            APPLICATION_STATE_DSN_ENV: dsn,
            "PYTHONPATH": os.pathsep.join((str(worktree / "src"), str(worktree))),
        }
        subprocess.check_call(
            [
                sys.executable,
                "-c",
                "from application_state.cli import upgrade_to_head; upgrade_to_head()",
            ],
            cwd=worktree,
            env=env,
        )
        output = subprocess.check_output(
            [sys.executable, "-c", _BASELINE_LATENCY_SCRIPT],
            cwd=worktree,
            env=env,
            text=True,
        )
        payload = json.loads(output.strip().splitlines()[-1])
        return {key: float(value) for key, value in payload.items()}
    finally:
        if created_db:
            with psycopg.connect(admin, autocommit=True) as conn:
                conn.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (db_name,),
                )
                conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
        if added_worktree:
            subprocess.call(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=repo,
            )
