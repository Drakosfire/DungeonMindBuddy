"""Apply live-portable ``perturbation_setup`` fields to a tmp recap-ingest corpus.

Offline-only fabricated tool traces (``trace_variant``) are not reproduced here;
see :func:`log_trace_variant_live_portability`.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Callable

from src.agent.recap_context import RecapContext

_LOG_PREFIX = "[recap-ingest]"

# Variants that only change the offline synthetic trace (no deterministic live hook).
_OFFLINE_ONLY_TRACE_VARIANTS = frozenset(
    {
        "guarded_staging_read_then_recover",
        "assemble_raw_notes_path_traversal",
    }
)

_CAMPAIGN_HUB_DEFAULT = "Longmont Campaign/Campaign 2"
_CAMPAIGN_ID_DEFAULT = "longmont-c2"


def log_trace_variant_live_portability(
    scenario: dict[str, Any],
    *,
    scenario_id: str,
    log: Callable[[str], None] | None,
) -> None:
    """Emit one-line notices for ``trace_variant`` (offline-only vs covered by inject)."""
    setup = scenario.get("perturbation_setup") or {}
    raw = str(setup.get("trace_variant", "baseline_preview_commit")).strip()
    if not raw:
        raw = "baseline_preview_commit"
    inject = bool(setup.get("inject_existing_target_recap_after_snapshot"))

    if raw in ("baseline_preview_commit",):
        return
    if raw == "commit_rejected_existing_target":
        if inject:
            if log:
                log(
                    f"{_LOG_PREFIX} perturbation: trace_variant=commit_rejected_existing_target "
                    "— offline trace is synthetic; live uses inject_existing_target_recap_after_snapshot."
                )
        else:
            if log:
                log(
                    f"{_LOG_PREFIX} WARNING: scenario {scenario_id!r} uses "
                    "trace_variant=commit_rejected_existing_target without "
                    "inject_existing_target_recap_after_snapshot; offline-only."
                )
        return
    if raw in _OFFLINE_ONLY_TRACE_VARIANTS:
        if log:
            log(
                f"{_LOG_PREFIX} WARNING: scenario {scenario_id!r} uses trace_variant={raw!r} "
                "which is offline-only; no live equivalent applied."
            )
        return
    if log:
        log(
            f"{_LOG_PREFIX} WARNING: scenario {scenario_id!r} uses unknown trace_variant={raw!r}."
        )


def _hub_paths(corpus_root: Path, campaign_hub: str) -> tuple[Path, Path]:
    hub = corpus_root / str(campaign_hub).strip("/")
    return hub / "Session Recaps", hub / "Session Prep"


def _write_session_recap_file(
    corpus_root: Path,
    *,
    campaign_hub: str,
    filename: str,
    session: int,
    campaign_id: str = _CAMPAIGN_ID_DEFAULT,
) -> None:
    title = f"Session {session} - Recap"
    body = textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        document_class: play
        canon_layer: campaign
        campaign_id: {campaign_id}
        temporal_scope: session_specific
        session: {session}
        origin_session: {session}
        last_updated_session: {session}
        source_class: observed_session_recap
        ---
        # {title}

        Body of session {session}.
        """
    )
    recaps_dir, _ = _hub_paths(corpus_root, campaign_hub)
    recaps_dir.mkdir(parents=True, exist_ok=True)
    (recaps_dir / filename).write_text(body, encoding="utf-8")


def _strip_to_single_recap_no_prep(
    corpus_root: Path,
    *,
    campaign_hub: str,
    log: Callable[[str], None] | None,
    report: dict[str, Any],
) -> None:
    recaps_dir, prep_dir = _hub_paths(corpus_root, campaign_hub)
    if not recaps_dir.is_dir():
        raise FileNotFoundError(f"Session Recaps missing: {recaps_dir}")
    removed_recaps: list[str] = []
    for md in sorted(recaps_dir.glob("*.md")):
        if md.name != "Session 19 - Recap.md":
            removed_recaps.append(md.name)
            md.unlink()
    if not (recaps_dir / "Session 19 - Recap.md").is_file():
        _write_session_recap_file(
            corpus_root,
            campaign_hub=campaign_hub,
            filename="Session 19 - Recap.md",
            session=19,
        )
        report["single_recap_wrote_session_19"] = True
    else:
        report["single_recap_wrote_session_19"] = False
    report["single_recap_removed_files"] = removed_recaps

    removed_prep: list[str] = []
    if prep_dir.is_dir():
        for p in sorted(prep_dir.glob("session_20*.md")):
            removed_prep.append(p.name)
            p.unlink(missing_ok=True)
    report["single_recap_removed_session_20_prep"] = removed_prep

    if log:
        log(
            f"{_LOG_PREFIX} perturbation: seed_kind=single_recap_no_prep "
            f"(kept Session 19 only; removed {len(removed_recaps)} other recap(s); "
            f"removed {len(removed_prep)} session_20 prep file(s))."
        )


def _apply_malformed_prep(
    corpus_root: Path,
    *,
    campaign_hub: str,
    log: Callable[[str], None] | None,
    report: dict[str, Any],
) -> None:
    _, prep_dir = _hub_paths(corpus_root, campaign_hub)
    prep_dir.mkdir(parents=True, exist_ok=True)
    removed: list[str] = []
    for p in sorted(prep_dir.glob("session_20*.md")):
        removed.append(p.name)
        p.unlink(missing_ok=True)
    report["malformed_prep_removed_session_20_files"] = removed
    malformed = textwrap.dedent(
        """\
        ---
        title: "Session 20 prep"
        document_class prep
        campaign_id: longmont-c2
        ---
        Prep body with malformed frontmatter.
        """
    )
    target = prep_dir / "session_20_ref.md"
    target.write_text(malformed, encoding="utf-8")
    report["malformed_prep_written"] = str(
        target.resolve().relative_to(corpus_root.resolve()).as_posix()
    )
    if log:
        log(
            f"{_LOG_PREFIX} perturbation: prep_variant=malformed_frontmatter "
            f"(removed {len(removed)} session_20 prep file(s); wrote session_20_ref.md)."
        )


def apply_perturbation_setup_pre_snapshot(
    corpus_root: Path,
    scenario: dict[str, Any],
    *,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Mutate ``corpus_root`` for ``seed_kind`` and ``prep_variant`` before ``resolve_recap_context``."""
    report: dict[str, Any] = {"phase": "pre_snapshot"}
    setup = scenario.get("perturbation_setup") or {}
    campaign_hub = str(scenario.get("campaign_hub") or _CAMPAIGN_HUB_DEFAULT).strip()

    seed_kind = str(setup.get("seed_kind", "campaign_2_happy_path")).strip()
    if seed_kind == "campaign_2_happy_path":
        report["seed_kind"] = seed_kind
        if log:
            log(
                f"{_LOG_PREFIX} perturbation: seed_kind=campaign_2_happy_path "
                "(no extra seeding; pre-state corpus already matches this shape)."
            )
    elif seed_kind == "single_recap_no_prep":
        report["seed_kind"] = seed_kind
        _strip_to_single_recap_no_prep(
            corpus_root, campaign_hub=campaign_hub, log=log, report=report
        )
    else:
        raise ValueError(f"unknown perturbation_setup.seed_kind: {seed_kind!r}")

    prep_variant = str(setup.get("prep_variant", "")).strip()
    if prep_variant == "malformed_frontmatter":
        _apply_malformed_prep(
            corpus_root, campaign_hub=campaign_hub, log=log, report=report
        )
    elif prep_variant:
        raise ValueError(f"unknown perturbation_setup.prep_variant: {prep_variant!r}")
    elif log and prep_variant == "":
        pass

    return report


def inject_existing_target_recap_after_snapshot(
    corpus_root: Path,
    scenario: dict[str, Any],
    snapshot: RecapContext,
    *,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """After ``resolve_recap_context``, seed the target recap file so create-mode commit fails."""
    report: dict[str, Any] = {"phase": "post_snapshot_inject"}
    setup = scenario.get("perturbation_setup") or {}
    if not setup.get("inject_existing_target_recap_after_snapshot"):
        report["skipped"] = True
        return report

    campaign_hub = str(scenario.get("campaign_hub") or _CAMPAIGN_HUB_DEFAULT).strip()
    session = int(snapshot.target_session)
    filename = f"Session {session} - Recap.md"
    _write_session_recap_file(
        corpus_root,
        campaign_hub=campaign_hub,
        filename=filename,
        session=session,
    )
    rel = (
        (corpus_root / campaign_hub / "Session Recaps" / filename)
        .resolve()
        .relative_to(corpus_root.resolve())
        .as_posix()
    )
    report["injected_path"] = rel
    report["target_session"] = session
    if log:
        log(
            f"{_LOG_PREFIX} perturbation: inject_existing_target_recap_after_snapshot "
            f"wrote {rel!r} (snapshot still pre-inject; corpus_writer should reject create)."
        )
    return report
