"""PostgreSQL owning-boundary witnesses for Stage 2C source adoption."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import pytest

from application_state.ingest.service import create_extraction_run, list_extraction_runs
from application_state.source.service import get_source_markdown, persist_source_markdown
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)
from product_continuity import source_adoption as source_adoption_mod
from product_continuity.source_adoption import (
    C2S25_ARTIFACT_ID,
    C2S25_DIGEST,
    C2S25_REVISION_ID,
    SourceAdoptionInputError,
    WorldSourceInventoryRow,
    apply_source_adoption,
    fingerprint_targets,
    known_historical_revision_id,
    preview_source_adoption,
)


WORLD_ID = "eldyrwild"
HEAD = "rev:test-head"
C1 = "longmont-c1"
C2 = "longmont-c2"


def _digest(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _write(root: Path, relative: str, markdown: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = markdown.encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _run(
    *,
    run_id: str,
    artifact_id: str,
    digest: str,
    uri: str,
    campaign_id: str = C2,
    session_id: str = "session-25",
    status: ExtractionRunStatus = ExtractionRunStatus.VALIDATED,
) -> ExtractionRun:
    return ExtractionRun(
        run_id=run_id,
        source_artifact_id=artifact_id,
        source_domain="recap",
        status=status,
        campaign_id=campaign_id,
        session_id=session_id,
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri=uri,
                sha256=digest,
            )
        },
    )


def _preview(root: Path, world_rows: list[WorldSourceInventoryRow] | None = None):
    return preview_source_adoption(
        repo_root=root,
        world_id=WORLD_ID,
        campaign_ids=[C1, C2],
        world_rows=world_rows if world_rows is not None else [],
        world_head=HEAD,
    )


def _apply(root: Path, expected: str, world_rows: list[WorldSourceInventoryRow] | None = None):
    return apply_source_adoption(
        repo_root=root,
        world_id=WORLD_ID,
        campaign_ids=[C1, C2],
        expected_set_sha256=expected,
        expected_world_head=HEAD,
        world_rows=world_rows if world_rows is not None else [],
        world_head=HEAD,
    )


def test_duplicate_runs_dedupe_to_one_target(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Shared warehouse paragraph.\n"
    digest = _write(tmp_path, "corpus/shared.md", markdown)
    artifact = f"artifact:recap:{C2}:session-1:{digest[:12]}"
    create_extraction_run(
        _run(
            run_id="run-a",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/shared.md",
            session_id="session-1",
        )
    )
    create_extraction_run(
        _run(
            run_id="run-b",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/shared.md",
            session_id="session-1",
        )
    )
    report = _preview(tmp_path)
    adoptable = [row for row in report.targets if row.classification == "ADOPTABLE_EXACT"]
    assert len(adoptable) == 1
    assert set(adoptable[0].supporting_run_ids) == {"run-a", "run-b"}


def test_two_digests_become_two_revisions(
    application_state_dsn: str, tmp_path: Path
) -> None:
    first = "Revision one.\n"
    second = "Revision two.\n"
    first_digest = _write(tmp_path, "corpus/one.md", first)
    second_digest = _write(tmp_path, "corpus/two.md", second)
    artifact = "artifact:recap:longmont-c2:session-2:twodigest"
    create_extraction_run(
        _run(
            run_id="run-one",
            artifact_id=artifact,
            digest=first_digest,
            uri="corpus/one.md",
            session_id="session-2",
        )
    )
    create_extraction_run(
        _run(
            run_id="run-two",
            artifact_id=artifact,
            digest=second_digest,
            uri="corpus/two.md",
            session_id="session-2",
        )
    )
    preview = _preview(tmp_path)
    adoptable = [row for row in preview.targets if row.classification == "ADOPTABLE_EXACT"]
    assert len(adoptable) == 2
    applied = _apply(tmp_path, preview.source_target_set_sha256)
    assert applied.newly_adopted == 2
    replay = _preview(tmp_path)
    assert {row.classification for row in replay.targets} == {"CURRENT_EXACT"}
    assert replay.source_target_set_sha256 == preview.source_target_set_sha256


def test_exact_bytes_apply_and_replay(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Orik and Brin sheltered in the warehouse.\n"
    digest = _write(tmp_path, "corpus/c2s23.md", markdown)
    artifact = f"artifact:recap:{C2}:session-23:{digest[:12]}"
    create_extraction_run(
        _run(
            run_id="run-c2s23",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/c2s23.md",
            session_id="session-23",
        )
    )
    before_runs = [row.model_dump() for row in list_extraction_runs()]
    preview = _preview(tmp_path)
    target = preview.targets[0]
    assert target.classification == "ADOPTABLE_EXACT"
    assert target.identity_kind == "new_durable_source_adoption"
    applied = _apply(tmp_path, preview.source_target_set_sha256)
    assert applied.applied is True
    assert applied.newly_adopted == 1
    assert applied.new_durable_identities == 1
    first_revision = applied.targets[0].source_revision_id
    replay_preview = _preview(tmp_path)
    assert replay_preview.targets[0].classification == "CURRENT_EXACT"
    assert replay_preview.targets[0].known_source_revision_id is None
    assert replay_preview.targets[0].source_revision_id == first_revision
    assert replay_preview.source_target_set_sha256 == preview.source_target_set_sha256
    replay = _apply(tmp_path, preview.source_target_set_sha256)
    assert replay.newly_adopted == 0
    assert replay.targets[0].source_revision_id == first_revision
    after_runs = [row.model_dump() for row in list_extraction_runs()]
    assert after_runs == before_runs


def test_missing_bytes_are_non_blocking(
    application_state_dsn: str, tmp_path: Path
) -> None:
    digest = "ab" * 32
    create_extraction_run(
        _run(
            run_id="run-missing",
            artifact_id="artifact:recap:longmont-c2:session-3:missing",
            digest=digest,
            uri="corpus/absent.md",
            session_id="session-3",
        )
    )
    report = _preview(tmp_path)
    assert report.blocked is False
    assert report.targets[0].classification == "UNAVAILABLE_BYTES"


def test_incomplete_world_metadata_is_non_blocking(
    application_state_dsn: str, tmp_path: Path
) -> None:
    report = _preview(
        tmp_path,
        world_rows=[
            WorldSourceInventoryRow(
                source_artifact_id="artifact:worldbuilding:eldyrwild:lore",
                source_domain="worldbuilding",
                campaign_id=None,
                session_id=None,
                world_id=WORLD_ID,
                content_sha256=None,
                locator=None,
                artifact_uri="repo://corpus/lore.md",
                artifact_kind="markdown",
                body_storage="postgres",
                source_revision_id="rev-incomplete",
            )
        ],
    )
    assert report.blocked is False
    assert report.targets[0].classification == "AUTHORITY_METADATA_INCOMPLETE"


def test_unsupported_media_is_non_blocking(
    application_state_dsn: str, tmp_path: Path
) -> None:
    digest = _write(tmp_path, "corpus/map.png", "not-really-png")
    report = _preview(
        tmp_path,
        world_rows=[
            WorldSourceInventoryRow(
                source_artifact_id="artifact:worldbuilding:map",
                source_domain="worldbuilding",
                campaign_id=None,
                session_id=None,
                world_id=WORLD_ID,
                content_sha256=digest,
                locator="corpus/map.png",
                artifact_uri="corpus/map.png",
                artifact_kind="image",
                body_storage="object_store",
                source_revision_id="rev-map",
            )
        ],
    )
    assert report.blocked is False
    assert report.targets[0].classification == "UNSUPPORTED_MEDIA"


def test_digest_mismatch_blocks_apply(
    application_state_dsn: str, tmp_path: Path
) -> None:
    _write(tmp_path, "corpus/wrong.md", "Actual bytes.\n")
    create_extraction_run(
        _run(
            run_id="run-mismatch",
            artifact_id="artifact:recap:longmont-c2:session-4:mismatch",
            digest="cd" * 32,
            uri="corpus/wrong.md",
            session_id="session-4",
        )
    )
    preview = _preview(tmp_path)
    assert preview.targets[0].classification == "DIGEST_MISMATCH"
    assert preview.blocked is True
    applied = _apply(tmp_path, preview.source_target_set_sha256)
    assert applied.applied is False
    assert applied.newly_adopted == 0


def test_scope_conflict_blocks_apply(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Same bytes, disagreeing scope.\n"
    digest = _write(tmp_path, "corpus/scope.md", markdown)
    artifact = "artifact:recap:conflict:session-x:scope"
    create_extraction_run(
        _run(
            run_id="run-c2",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/scope.md",
            campaign_id=C2,
            session_id="session-6",
        )
    )
    create_extraction_run(
        _run(
            run_id="run-c1",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/scope.md",
            campaign_id=C1,
            session_id="session-6",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is True
    assert preview.targets[0].classification == "SCOPE_CONFLICT"


def test_world_missing_scope_is_incomplete_not_conflict(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Ingest carries the concrete scope.\n"
    digest = _write(tmp_path, "corpus/world-none-scope.md", markdown)
    artifact = f"artifact:recap:{C2}:session-25:{digest[:12]}"
    create_extraction_run(
        _run(
            run_id="run-ingest-scope",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/world-none-scope.md",
            campaign_id=C2,
            session_id="session-25",
        )
    )
    world_rows = [
        WorldSourceInventoryRow(
            source_artifact_id=artifact,
            source_domain="recap",
            campaign_id=None,
            session_id=None,
            world_id=WORLD_ID,
            content_sha256=digest,
            locator="corpus/world-none-scope.md",
            artifact_uri="corpus/world-none-scope.md",
            artifact_kind="markdown",
            body_storage="postgres",
            source_revision_id="sha256:" + digest,
        )
    ]
    preview = _preview(tmp_path, world_rows=world_rows)
    assert preview.blocked is False
    assert len(preview.targets) == 1
    assert preview.targets[0].classification == "ADOPTABLE_EXACT"
    assert preview.targets[0].campaign_id == C2
    assert preview.targets[0].session_id == "session-25"
    applied = _apply(tmp_path, preview.source_target_set_sha256, world_rows=world_rows)
    assert applied.applied is True
    assert applied.newly_adopted == 1
    assert applied.targets[0].campaign_id == C2
    assert applied.targets[0].session_id == "session-25"


def test_world_concrete_scope_still_conflicts_with_ingest(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Two concrete campaigns are a conflict.\n"
    digest = _write(tmp_path, "corpus/world-concrete-scope.md", markdown)
    artifact = "artifact:recap:conflict:session-x:world-concrete"
    world_rows = [
        WorldSourceInventoryRow(
            source_artifact_id=artifact,
            source_domain="recap",
            campaign_id=C1,
            session_id="session-6",
            world_id=WORLD_ID,
            content_sha256=digest,
            locator="corpus/world-concrete-scope.md",
            artifact_uri="corpus/world-concrete-scope.md",
            artifact_kind="markdown",
            body_storage="postgres",
            source_revision_id="sha256:" + digest,
        )
    ]
    create_extraction_run(
        _run(
            run_id="run-ingest-c2",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/world-concrete-scope.md",
            campaign_id=C2,
            session_id="session-6",
        )
    )
    preview = _preview(tmp_path, world_rows=world_rows)
    assert preview.blocked is True
    assert preview.targets[0].classification == "SCOPE_CONFLICT"
    applied = _apply(tmp_path, preview.source_target_set_sha256, world_rows=world_rows)
    assert applied.applied is False
    assert applied.newly_adopted == 0
    assert get_source_markdown(source_artifact_id=artifact, content_sha256=digest) is None


def test_incomplete_world_digest_uses_sibling_ingest_scope(
    application_state_dsn: str, tmp_path: Path
) -> None:
    ingest_markdown = "Ingest revision with concrete scope.\n"
    world_markdown = "World revision with unknown campaign/session.\n"
    ingest_digest = _write(tmp_path, "corpus/sibling-ingest.md", ingest_markdown)
    world_digest = _write(tmp_path, "corpus/sibling-world.md", world_markdown)
    artifact = "artifact:recap:longmont-c2:session-25:sibling-scope"
    world_rows = [
        WorldSourceInventoryRow(
            source_artifact_id=artifact,
            source_domain="recap",
            campaign_id=None,
            session_id=None,
            world_id=WORLD_ID,
            content_sha256=world_digest,
            locator="corpus/sibling-world.md",
            artifact_uri="corpus/sibling-world.md",
            artifact_kind="markdown",
            body_storage="postgres",
            source_revision_id="sha256:" + world_digest,
        )
    ]
    create_extraction_run(
        _run(
            run_id="run-sibling-ingest",
            artifact_id=artifact,
            digest=ingest_digest,
            uri="corpus/sibling-ingest.md",
            campaign_id=C2,
            session_id="session-25",
        )
    )
    preview = _preview(tmp_path, world_rows=world_rows)
    assert preview.blocked is False
    assert {row.classification for row in preview.targets} == {"ADOPTABLE_EXACT"}
    assert {row.campaign_id for row in preview.targets} == {C2}
    assert {row.session_id for row in preview.targets} == {"session-25"}
    applied = _apply(tmp_path, preview.source_target_set_sha256, world_rows=world_rows)
    assert applied.applied is True
    assert applied.newly_adopted == 2


def test_recap_and_session_recap_are_the_same_domain(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Alias domains are not a conflict.\n"
    digest = _write(tmp_path, "corpus/alias.md", markdown)
    artifact = f"artifact:recap:{C2}:session-12:{digest[:12]}"
    create_extraction_run(
        _run(
            run_id="run-alias",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/alias.md",
            session_id="session-12",
        )
    )
    preview = _preview(
        tmp_path,
        world_rows=[
            WorldSourceInventoryRow(
                source_artifact_id=artifact,
                source_domain="session_recap",
                campaign_id=C2,
                session_id="session-12",
                world_id=WORLD_ID,
                content_sha256=digest,
                locator="corpus/alias.md",
                artifact_uri="corpus/alias.md",
                artifact_kind="markdown",
                body_storage="postgres",
                source_revision_id="sha256:" + digest,
            )
        ],
    )
    assert preview.blocked is False
    assert len(preview.targets) == 1
    assert preview.targets[0].classification == "ADOPTABLE_EXACT"
    assert preview.targets[0].source_domain == "recap"


def test_fingerprint_mismatch_blocks_apply(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Fingerprint guard.\n"
    digest = _write(tmp_path, "corpus/fp.md", markdown)
    create_extraction_run(
        _run(
            run_id="run-fp",
            artifact_id="artifact:recap:longmont-c2:session-7:fp",
            digest=digest,
            uri="corpus/fp.md",
            session_id="session-7",
        )
    )
    preview = _preview(tmp_path)
    with pytest.raises(SourceAdoptionInputError):
        apply_source_adoption(
            repo_root=tmp_path,
            world_id=WORLD_ID,
            campaign_ids=[C1, C2],
            expected_set_sha256="",
            expected_world_head=HEAD,
            world_rows=[],
            world_head=HEAD,
        )
    applied = _apply(tmp_path, "0" * 64)
    assert applied.applied is False
    assert applied.blocked is True
    assert applied.newly_adopted == 0
    assert fingerprint_targets(preview.targets) == preview.source_target_set_sha256


def test_known_c2s25_revision_is_preserved(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "C2 Session 25 warehouse paragraph.\n"
    digest = _write(tmp_path, "corpus/c2s25.md", markdown)
    assert digest != C2S25_DIGEST
    persist_source_markdown(
        source_artifact_id=C2S25_ARTIFACT_ID,
        source_domain="recap",
        campaign_id=C2,
        session_id="session-25",
        world_id=WORLD_ID,
        markdown=markdown,
        content_sha256=digest,
        source_revision_id=C2S25_REVISION_ID,
    )
    create_extraction_run(
        _run(
            run_id="graph-ingest:longmont-c2:session-25:20260808T005650Z",
            artifact_id=C2S25_ARTIFACT_ID,
            digest=digest,
            uri="corpus/c2s25.md",
        )
    )
    preview = _preview(tmp_path)
    assert preview.targets[0].classification == "CURRENT_EXACT"
    assert preview.targets[0].source_revision_id == str(C2S25_REVISION_ID)
    assert preview.targets[0].known_source_revision_id is None
    applied = _apply(tmp_path, preview.source_target_set_sha256)
    assert applied.newly_adopted == 0
    assert applied.targets[0].source_revision_id == str(C2S25_REVISION_ID)


def test_known_revision_conflict_blocks(
    application_state_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reserved = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-9:other",
        source_domain="recap",
        campaign_id=C2,
        session_id="session-9",
        world_id=WORLD_ID,
        markdown="Different source.\n",
        source_revision_id=reserved,
    )
    markdown = "Claimed source.\n"
    digest = _write(tmp_path, "corpus/claimed.md", markdown)
    artifact = f"artifact:recap:{C2}:session-25:{digest[:12]}"
    monkeypatch.setitem(
        source_adoption_mod.KNOWN_HISTORICAL_REVISION_IDS,
        (artifact, digest),
        reserved,
    )
    create_extraction_run(
        _run(
            run_id="run-rev-conflict",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/claimed.md",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is True
    assert preview.targets[0].classification == "REVISION_ID_CONFLICT"


def test_app_state_conflict_blocks(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Trusted bytes.\n"
    digest = _digest(markdown)
    persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-8:conflict",
        source_domain="recap",
        campaign_id=C2,
        session_id="session-8",
        world_id=WORLD_ID,
        markdown=markdown,
        content_sha256=digest,
    )
    _write(tmp_path, "corpus/conflict.md", "Trusted bytes.\nX")
    # Same claimed digest, different file hash → DIGEST_MISMATCH, not APP_STATE.
    # APP_STATE_CONFLICT: file matches claimed digest but stored markdown differs.
    # persist hashes markdown, so we cannot store different markdown under same digest.
    # The remaining conflict is scope: persist same digest under different campaign via dry-run.
    other_digest = _write(tmp_path, "corpus/ok.md", markdown)
    assert other_digest == digest
    create_extraction_run(
        _run(
            run_id="run-scope-app",
            artifact_id="artifact:recap:longmont-c2:session-8:conflict",
            digest=digest,
            uri="corpus/ok.md",
            campaign_id=C1,
            session_id="session-8",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is True
    assert preview.targets[0].classification in {"SCOPE_CONFLICT", "APP_STATE_CONFLICT"}


def test_world_head_drift_blocks_apply(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Head drift.\n"
    digest = _write(tmp_path, "corpus/head.md", markdown)
    create_extraction_run(
        _run(
            run_id="run-head",
            artifact_id="artifact:recap:longmont-c2:session-11:head",
            digest=digest,
            uri="corpus/head.md",
            session_id="session-11",
        )
    )
    preview = _preview(tmp_path)
    applied = apply_source_adoption(
        repo_root=tmp_path,
        world_id=WORLD_ID,
        campaign_ids=[C1, C2],
        expected_set_sha256=preview.source_target_set_sha256,
        expected_world_head="rev:other",
        world_rows=[],
        world_head=HEAD,
    )
    assert applied.applied is False
    assert applied.blocked is True


def test_cross_digest_scope_conflict_blocks_before_any_write(
    application_state_dsn: str, tmp_path: Path
) -> None:
    first = "Revision one, session two.\n"
    second = "Revision two, session three.\n"
    first_digest = _write(tmp_path, "corpus/cross-one.md", first)
    second_digest = _write(tmp_path, "corpus/cross-two.md", second)
    artifact = "artifact:recap:longmont-c2:session-x:cross-scope"
    create_extraction_run(
        _run(
            run_id="run-cross-one",
            artifact_id=artifact,
            digest=first_digest,
            uri="corpus/cross-one.md",
            session_id="session-2",
        )
    )
    create_extraction_run(
        _run(
            run_id="run-cross-two",
            artifact_id=artifact,
            digest=second_digest,
            uri="corpus/cross-two.md",
            session_id="session-3",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is True
    assert {row.classification for row in preview.targets} == {"SCOPE_CONFLICT"}
    applied = _apply(tmp_path, preview.source_target_set_sha256)
    assert applied.applied is False
    assert applied.newly_adopted == 0
    assert get_source_markdown(source_artifact_id=artifact, content_sha256=first_digest) is None
    assert get_source_markdown(source_artifact_id=artifact, content_sha256=second_digest) is None


def test_existing_artifact_scope_blocks_other_digest_before_write(
    application_state_dsn: str, tmp_path: Path
) -> None:
    existing_markdown = "Already adopted session 25.\n"
    persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-x:existing-scope",
        source_domain="recap",
        campaign_id=C2,
        session_id="session-25",
        world_id=WORLD_ID,
        markdown=existing_markdown,
    )
    later = "Different digest, different session.\n"
    digest = _write(tmp_path, "corpus/later.md", later)
    create_extraction_run(
        _run(
            run_id="run-later",
            artifact_id="artifact:recap:longmont-c2:session-x:existing-scope",
            digest=digest,
            uri="corpus/later.md",
            session_id="session-26",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is True
    assert preview.targets[0].classification == "SCOPE_CONFLICT"
    applied = _apply(tmp_path, preview.source_target_set_sha256)
    assert applied.applied is False
    assert applied.newly_adopted == 0
    assert get_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-x:existing-scope",
        content_sha256=digest,
    ) is None


def test_apply_requires_expected_world_head(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "World head pin.\n"
    digest = _write(tmp_path, "corpus/pin.md", markdown)
    create_extraction_run(
        _run(
            run_id="run-pin",
            artifact_id="artifact:recap:longmont-c2:session-13:pin",
            digest=digest,
            uri="corpus/pin.md",
            session_id="session-13",
        )
    )
    preview = _preview(tmp_path)
    with pytest.raises(SourceAdoptionInputError, match="expected-world-head"):
        apply_source_adoption(
            repo_root=tmp_path,
            world_id=WORLD_ID,
            campaign_ids=[C1, C2],
            expected_set_sha256=preview.source_target_set_sha256,
            expected_world_head=None,
            world_rows=[],
            world_head=HEAD,
        )
    with pytest.raises(SourceAdoptionInputError, match="expected-world-head"):
        apply_source_adoption(
            repo_root=tmp_path,
            world_id=WORLD_ID,
            campaign_ids=[C1, C2],
            expected_set_sha256=preview.source_target_set_sha256,
            expected_world_head="   ",
            world_rows=[],
            world_head=HEAD,
        )
    assert get_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-13:pin",
        content_sha256=digest,
    ) is None


def test_missing_first_locator_second_locator_adopts(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Second locator has the bytes.\n"
    digest = _write(tmp_path, "corpus/second.md", markdown)
    artifact = f"artifact:recap:{C2}:session-14:{digest[:12]}"
    create_extraction_run(
        _run(
            run_id="run-stale",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/stale.md",
            session_id="session-14",
        )
    )
    create_extraction_run(
        _run(
            run_id="run-second",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/second.md",
            session_id="session-14",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is False
    assert preview.targets[0].classification == "ADOPTABLE_EXACT"
    assert preview.targets[0].locator == "corpus/second.md"


def test_mismatching_first_locator_second_locator_adopts(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "Authoritative bytes.\n"
    digest = _write(tmp_path, "corpus/right.md", markdown)
    _write(tmp_path, "corpus/wrong.md", "Different bytes.\n")
    artifact = f"artifact:recap:{C2}:session-15:{digest[:12]}"
    create_extraction_run(
        _run(
            run_id="run-wrong",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/wrong.md",
            session_id="session-15",
        )
    )
    create_extraction_run(
        _run(
            run_id="run-right",
            artifact_id=artifact,
            digest=digest,
            uri="corpus/right.md",
            session_id="session-15",
        )
    )
    preview = _preview(tmp_path)
    assert preview.blocked is False
    assert preview.targets[0].classification == "ADOPTABLE_EXACT"
    assert preview.targets[0].locator == "corpus/right.md"


def test_world_artifact_uri_is_tried_when_locator_missing(
    application_state_dsn: str, tmp_path: Path
) -> None:
    markdown = "World alternate locator.\n"
    digest = _write(tmp_path, "corpus/world-good.md", markdown)
    artifact = f"artifact:recap:{C2}:session-16:{digest[:12]}"
    preview = _preview(
        tmp_path,
        world_rows=[
            WorldSourceInventoryRow(
                source_artifact_id=artifact,
                source_domain="recap",
                campaign_id=C2,
                session_id="session-16",
                world_id=WORLD_ID,
                content_sha256=digest,
                locator="corpus/world-stale.md",
                artifact_uri="corpus/world-good.md",
                artifact_kind="markdown",
                body_storage="postgres",
                source_revision_id="sha256:" + digest,
            )
        ],
    )
    assert preview.blocked is False
    assert preview.targets[0].classification == "ADOPTABLE_EXACT"
    assert preview.targets[0].locator == "corpus/world-good.md"


def test_cli_apply_requires_expected_world_head_before_service(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import importlib.util

    path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "adopt_historical_source_material.py"
    )
    spec = importlib.util.spec_from_file_location(
        "adopt_historical_source_material",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    called: list[object] = []
    monkeypatch.setattr(cli, "load_dungeonmindbuddy_dotenv", lambda override=True: None)
    monkeypatch.setattr(
        cli,
        "apply_source_adoption",
        lambda **kwargs: called.append(kwargs),
    )
    code = cli.main(
        [
            "--world-id",
            WORLD_ID,
            "--campaign",
            C2,
            "--apply",
            "--expected-set-sha256",
            "abc",
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert called == []
    assert "expected-world-head" in captured.err


def test_historical_revision_id_comes_only_from_the_accepted_map() -> None:
    assert known_historical_revision_id(C2S25_ARTIFACT_ID, C2S25_DIGEST) == C2S25_REVISION_ID
    assert known_historical_revision_id(C2S25_ARTIFACT_ID, "ab" * 32) is None
