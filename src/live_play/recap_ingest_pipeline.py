from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from scripts.materialize_normalized_recaps import (
    _build_normalized_content,
    _clean_body,
    _extract_recap_raw,
    _parse_minimal_frontmatter,
)
from scripts.materialize_session_memory import (
    _check_one,
    _expected_session_memory_outputs,
    _materialize_one,
)
from src.agent.recap_frontmatter_seed import build_frontmatter_seed
from src.agent.corpus_writer import is_writable_corpus_path, write_corpus_file
from src.agent.recap_ingest_helpers import assemble_recap
from src.corpus.session_recap_paths import (
    breadcrumbed_relpath,
    canonical_recap_candidates,
    frontmatter_seed_relpath,
    is_generic_recap_tail,
    normalized_recap_candidates,
    normalized_recap_relpath,
    pick_normalized_basename_from_disk,
    resolve_under_corpus,
    session_memory_jsonl_relpath,
    session_memory_meta_relpath,
    session_recaps_prefix,
)
from src.live_play.recap_ingest_status import RecapIngestStatus
from src.live_play.recap_derivative_provenance import (
    archive_existing,
    provenance_path,
    record_archived_artifacts,
    read_provenance_state,
    sha256_bytes,
    sha256_file,
)
from src.live_play.recap_stage_paths import RecapStagePaths, corpus_root
from src.session_memory.breadcrumb_normalize import BreadcrumbNormalizeError

_GENERIC_RECAP_TITLE_RE = re.compile(r"^Session\s+\d+\s*(?:-\s*)?Recap\s*:?\s*$", re.IGNORECASE)
_SESSION_TITLE_RE = re.compile(r"^Session\s+\d+\s*(?:-\s*)?(.+?)\s*$", re.IGNORECASE)
_NAME_TOKEN_RE = re.compile(r"\b[A-Z][a-zA-Z]{3,}\b")


@dataclass(frozen=True)
class PipelineOptions:
    campaign_id: str
    session: int
    raw_path: Path | None
    raw_stdin: bool
    title: str | None
    slug: str | None
    stage: bool
    preview: bool
    apply: bool
    normalize: bool
    materialize_session_memory: bool
    check: bool
    force_stage: bool
    force_recap: bool
    json_output: bool
    force_normalize: bool = False
    force_session_memory: bool = False


def _parse_args(argv: list[str] | None = None) -> PipelineOptions:
    parser = argparse.ArgumentParser(
        description=(
            "Raw recap intake + deterministic ingestion orchestrator "
            "(stage/preview/apply/normalize/session-memory)."
        )
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--raw-path", type=Path, default=None)
    parser.add_argument("--raw-stdin", action="store_true")
    parser.add_argument("--title", default=None)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--normalize", action="store_true")
    parser.add_argument("--materialize-session-memory", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--force-stage", action="store_true")
    parser.add_argument("--force-recap", action="store_true")
    parser.add_argument("--force-normalize", action="store_true")
    parser.add_argument("--force-session-memory", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    ns = parser.parse_args(argv)

    if ns.raw_path is not None and ns.raw_stdin:
        parser.error("pass either --raw-path or --raw-stdin, not both")
    if ns.raw_path is None and not ns.raw_stdin and (ns.stage or ns.preview or ns.apply):
        parser.error(
            "raw recap source required for stage/preview/apply "
            "(use --raw-path or --raw-stdin)"
        )

    op_flags = (ns.stage, ns.preview, ns.apply, ns.normalize, ns.materialize_session_memory)
    if not any(op_flags):
        ns.stage = True
        ns.preview = True

    return PipelineOptions(
        campaign_id=str(ns.campaign_id).strip(),
        session=ns.session,
        raw_path=ns.raw_path,
        raw_stdin=bool(ns.raw_stdin),
        title=str(ns.title).strip() if ns.title else None,
        slug=str(ns.slug).strip() if ns.slug else None,
        stage=bool(ns.stage),
        preview=bool(ns.preview),
        apply=bool(ns.apply),
        normalize=bool(ns.normalize),
        materialize_session_memory=bool(ns.materialize_session_memory),
        check=bool(ns.check),
        force_stage=bool(ns.force_stage),
        force_recap=bool(ns.force_recap),
        json_output=bool(ns.json_output),
        force_normalize=bool(ns.force_normalize),
        force_session_memory=bool(ns.force_session_memory),
    )


def _slug_tail(*, session: int, title: str | None, slug: str | None) -> str:
    if slug:
        return slug
    if title:
        match = _SESSION_TITLE_RE.match(title.strip())
        if match:
            return match.group(1).strip()
        return title.strip()
    return "Recap"


def _effective_title(*, session: int, title: str | None, slug: str | None) -> str | None:
    if title:
        return title
    if slug:
        return f"Session {session} - {slug}"
    return None


def _is_generic_title(*, session: int, title: str | None, slug: str | None) -> bool:
    if slug and slug.strip().lower() != "recap":
        return False
    if title is None:
        return True
    if _GENERIC_RECAP_TITLE_RE.match(title):
        return True
    tail = _slug_tail(session=session, title=title, slug=slug).strip().lower().rstrip(":")
    return tail in {"", "recap"}


def _read_raw_text(
    *, raw_path: Path | None, raw_stdin: bool, stdin: TextIO
) -> str | None:
    if raw_stdin:
        return stdin.read()
    if raw_path is None:
        return None
    if not raw_path.is_absolute() and ".." in raw_path.parts:
        raise ValueError("raw path traversal is not allowed")
    resolved = raw_path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"raw recap file not found: {resolved}")
    return resolved.read_text(encoding="utf-8")


def _validate_raw_text(raw: str) -> None:
    if not raw.strip():
        raise ValueError("raw recap text is empty")


def _preview_diff(existing_text: str | None, new_text: str, rel_path: str) -> str:
    old = (existing_text or "").splitlines(keepends=True)
    new = new_text.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(old, new, fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}", n=3)
    )


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            replace = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, replace))
        prev = cur
    return prev[-1]


def _spelling_audit(raw_text: str) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    originals: dict[str, str] = {}
    for token in _NAME_TOKEN_RE.findall(raw_text):
        key = token.lower()
        counts[key] = counts.get(key, 0) + 1
        originals.setdefault(key, token)
    keys = sorted(counts.keys())
    seen_pairs: set[tuple[str, str]] = set()
    out: list[dict[str, object]] = []
    for idx, a in enumerate(keys):
        for b in keys[idx + 1 :]:
            if a[0] != b[0]:
                continue
            if abs(len(a) - len(b)) > 2:
                continue
            dist = _levenshtein(a, b)
            if dist == 0 or dist > 2:
                continue
            pair = (a, b)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            candidates = sorted((a, b), key=lambda k: (-counts[k], len(k), k))
            canonical = originals[candidates[0]]
            variants = [originals[a], originals[b]]
            out.append(
                {
                    "canonical_guess": canonical,
                    "variants": variants,
                    "action": "review_only",
                }
            )
    return out


def _safe_write_recap(
    *,
    corpus: Path,
    recap_rel: str,
    recap_text: str,
    force_recap: bool,
) -> tuple[str, str | None, list[dict[str, str]]]:
    """Return outcome, error, and any reversibly archived prior recap."""
    allowed, reason = is_writable_corpus_path(recap_rel, "create")
    if not allowed:
        return "failed", reason, []
    target = (corpus / recap_rel).resolve()
    try:
        target.relative_to(corpus.resolve())
    except ValueError:
        return "failed", "canonical recap path escapes corpus root", []

    content = recap_text if recap_text.endswith("\n") else recap_text + "\n"
    archived: list[dict[str, str]] = []
    if target.is_file():
        if target.read_text(encoding="utf-8") == content:
            return "reused", None, []
        if not force_recap:
            return (
                "stale",
                "canonical recap already exists with different content; explicit refresh is required",
                [],
            )
        archived = archive_existing(paths=[target], corpus_root=corpus)

    preview = write_corpus_file(
        corpus,
        path=recap_rel,
        mode="create",
        content=recap_text,
        dry_run=True,
    )
    if not preview.get("ok"):
        return "failed", str(preview.get("error") or "recap preview failed"), archived
    commit = write_corpus_file(
        corpus,
        path=recap_rel,
        mode="create",
        content=recap_text,
        dry_run=False,
        confirm_token=str(preview.get("confirm_token") or ""),
    )
    if not commit.get("ok"):
        return "failed", str(commit.get("error") or "recap commit failed"), archived
    return ("refreshed" if archived else "created"), None, archived


def _disk_derivative_paths(
    corpus_dir: Path,
    *,
    campaign_number: int,
    session: int,
) -> dict[str, str]:
    """Resolve derivative recap paths from the single on-disk normalized basename."""
    return {
        "normalized_recap": normalized_recap_relpath(
            campaign_number=campaign_number,
            session=session,
            corpus_root=corpus_dir,
        ),
        "breadcrumbed_recap": breadcrumbed_relpath(
            campaign_number=campaign_number,
            session=session,
            corpus_root=corpus_dir,
        ),
        "frontmatter_seed": frontmatter_seed_relpath(
            campaign_number=campaign_number,
            session=session,
            corpus_root=corpus_dir,
        ),
        "session_memory_jsonl": session_memory_jsonl_relpath(
            campaign_number=campaign_number,
            session=session,
            corpus_root=corpus_dir,
        ),
        "session_memory_meta": session_memory_meta_relpath(
            campaign_number=campaign_number,
            session=session,
            corpus_root=corpus_dir,
        ),
    }


def _resolve_canonical_recap_rel(
    corpus_dir: Path,
    *,
    campaign_number: int,
    session: int,
    slug_default_rel: str,
    normalized_rel: str | None,
) -> str:
    """Prefer the titled on-disk canonical that matches the normalized stem.

    Slug-default paths like ``Session N - Recap.md`` are only kept when no titled
    sibling exists beside the resolved normalized recap.
    """
    prefix = session_recaps_prefix(campaign_number)
    if normalized_rel:
        stem = Path(str(normalized_rel)).stem
        titled_rel = f"{prefix}/{stem}.md"
        if (corpus_dir / titled_rel).is_file():
            return titled_rel
        for candidate in canonical_recap_candidates(
            corpus_dir,
            campaign_number=campaign_number,
            session=session,
        ):
            if candidate.stem == stem:
                return f"{prefix}/{candidate.name}"
    if (corpus_dir / slug_default_rel).is_file():
        return slug_default_rel
    candidates = canonical_recap_candidates(
        corpus_dir,
        campaign_number=campaign_number,
        session=session,
    )
    if len(candidates) == 1:
        return f"{prefix}/{candidates[0].name}"
    return slug_default_rel


def _resolve_breadcrumb_path(
    corpus_dir: Path,
    *,
    campaign_number: int,
    session: int,
    slug_derived_rel: str,
) -> tuple[Path, str]:
    """Prefer the blessed on-disk chain over slug-derived paths when unambiguous."""
    try:
        disk_paths = _disk_derivative_paths(
            corpus_dir,
            campaign_number=campaign_number,
            session=session,
        )
    except FileNotFoundError:
        disk_paths = None
    if disk_paths is not None:
        rel = disk_paths["breadcrumbed_recap"]
        return resolve_under_corpus(corpus_dir, rel), rel
    return (corpus_dir / slug_derived_rel).resolve(), slug_derived_rel


def _normalize_one(
    *,
    corpus: Path,
    canonical_recap_rel: str,
    normalized_recap_rel: str,
    force: bool = False,
) -> tuple[str, str | None, list[dict[str, str]]]:
    """Return outcome, error, and any reversibly archived prior artifact."""
    normalized_target = (corpus / normalized_recap_rel).resolve()
    try:
        content = _expected_normalized_content(
            corpus=corpus,
            canonical_recap_rel=canonical_recap_rel,
        )
    except (FileNotFoundError, ValueError) as exc:
        return "failed", str(exc), []
    if normalized_target.is_file():
        existing = normalized_target.read_text(encoding="utf-8")
        if existing == content:
            return "reused", None, []
        if not force:
            return (
                "stale",
                "normalized recap differs from the current canonical recap; explicit refresh is required",
                [],
            )
        archived = archive_existing(paths=[normalized_target], corpus_root=corpus)
    else:
        archived = []
    preview = write_corpus_file(
        corpus,
        path=normalized_recap_rel,
        mode="create",
        content=content,
        dry_run=True,
    )
    if not preview.get("ok"):
        return "failed", str(preview.get("error") or "normalize preview failed"), archived
    commit = write_corpus_file(
        corpus,
        path=normalized_recap_rel,
        mode="create",
        content=content,
        dry_run=False,
        confirm_token=str(preview.get("confirm_token") or ""),
    )
    if not commit.get("ok"):
        return "failed", str(commit.get("error") or "normalize commit failed"), archived
    return ("refreshed" if archived else "created"), None, archived


def _expected_normalized_content(*, corpus: Path, canonical_recap_rel: str) -> str:
    recap_path = resolve_under_corpus(corpus, canonical_recap_rel)
    if not recap_path.is_file():
        raise FileNotFoundError(
            f"canonical recap missing for normalize step: {canonical_recap_rel}"
        )
    text = recap_path.read_text(encoding="utf-8")
    fm, body = _parse_minimal_frontmatter(text)
    title = str(fm.get("title") or "").strip()
    if _GENERIC_RECAP_TITLE_RE.match(title):
        raise ValueError("normalize blocked: generic recap title requires non-generic slug/title")
    recap_raw, _ = _extract_recap_raw(body)
    clean = _clean_body(recap_raw)
    return _build_normalized_content(
        fm=fm,
        body_clean=clean,
        session=int(fm.get("session") or 0),
        normalized_from=canonical_recap_rel,
        title=title,
    )


def run_pipeline(
    options: PipelineOptions,
    *,
    stdin: TextIO = sys.stdin,
    corpus: Path | None = None,
) -> dict[str, object]:
    status = RecapIngestStatus(campaign_id=options.campaign_id, session=options.session)
    corpus_dir = (corpus or corpus_root()).resolve()
    is_generic = _is_generic_title(
        session=options.session, title=options.title, slug=options.slug
    )
    paths = RecapStagePaths.build(
        campaign_id=options.campaign_id,
        session=options.session,
        slug_tail=_slug_tail(session=options.session, title=options.title, slug=options.slug),
    )
    status.paths = {
        "staged_raw_notes": paths.staged_raw_notes_rel,
        "canonical_recap": paths.canonical_recap_rel,
        "normalized_recap": paths.normalized_recap_rel,
        "frontmatter_seed": paths.frontmatter_seed_rel,
        "breadcrumbed_recap": paths.breadcrumbed_recap_rel,
        "session_memory_jsonl": paths.session_memory_jsonl_rel,
        "session_memory_meta": paths.session_memory_meta_rel,
    }

    raw_text: str | None = None
    try:
        raw_text = _read_raw_text(raw_path=options.raw_path, raw_stdin=options.raw_stdin, stdin=stdin)
        if raw_text is not None:
            _validate_raw_text(raw_text)
            status.add_state("raw_text_received")
            status.entity_spelling_audit = _spelling_audit(raw_text)
            if status.entity_spelling_audit:
                status.add_warning("entity spelling variants detected; review_only")
    except (FileNotFoundError, UnicodeDecodeError, ValueError) as exc:
        status.add_error(str(exc))
        return status.to_dict()

    staged_path = (corpus_dir / paths.staged_raw_notes_rel).resolve()
    recap_text_for_assembly: str | None = raw_text
    if options.stage:
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        if staged_path.exists():
            if raw_text is None:
                recap_text_for_assembly = staged_path.read_text(encoding="utf-8")
                status.add_state("staged_raw_notes_reused")
            else:
                existing = staged_path.read_text(encoding="utf-8")
                if existing == raw_text:
                    status.add_state("staged_raw_notes_reused")
                elif options.force_stage:
                    staged_path.write_text(raw_text, encoding="utf-8")
                    status.add_state("staged_raw_notes_created")
                else:
                    recap_text_for_assembly = existing
                    status.add_state("staged_raw_notes_reused")
                    status.add_state("staged_raw_notes_conflict")
                    status.add_warning(
                        "staged raw notes already exists; pasted raw text was not used"
                    )
                    status.add_next_action(
                        "Review the preview generated from the existing staged notes, "
                        "or enable --force-stage to overwrite them with the pasted text."
                    )
        else:
            if raw_text is None:
                status.add_error("cannot stage without raw recap source")
                return status.to_dict()
            staged_path.write_text(raw_text, encoding="utf-8")
            status.add_state("staged_raw_notes_created")

    if recap_text_for_assembly is None and (options.preview or options.apply):
        if staged_path.is_file():
            recap_text_for_assembly = staged_path.read_text(encoding="utf-8")
            status.add_state("staged_raw_notes_reused")
        else:
            status.add_error("preview/apply requires raw input or an existing staged raw notes file")
            return status.to_dict()

    recap_preview: str | None = None
    if options.preview or options.apply:
        assert recap_text_for_assembly is not None
        title = _effective_title(
            session=options.session, title=options.title, slug=options.slug
        )
        recap_preview, ingest_report = assemble_recap(
            raw_notes=recap_text_for_assembly,
            session=options.session,
            campaign_id=options.campaign_id,
            title=title,
            remove_duplicates=True,
        )
        status.add_state("recap_preview_created")
        status.ingest_report = {
            "title_line_stripped": ingest_report.title_line_stripped,
            "duplicates_detected": len(ingest_report.duplicates_detected),
            "duplicates_removed": len(ingest_report.duplicates_removed),
            "paragraph_count_in": ingest_report.paragraph_count_in,
            "paragraph_count_out": ingest_report.paragraph_count_out,
        }
        existing = None
        target = (corpus_dir / paths.canonical_recap_rel).resolve()
        if target.is_file():
            existing = target.read_text(encoding="utf-8")
        status.ingest_report["preview_diff"] = _preview_diff(
            existing, recap_preview, paths.canonical_recap_rel
        )
        if is_generic:
            status.add_warning("slug_required_for_apply")

    if options.apply:
        if is_generic:
            status.add_state("recap_apply_blocked_slug_required")
            status.add_error(
                "apply blocked: pass non-generic --slug or --title "
                "(generic Session N - Recap is not allowed)"
            )
            return status.to_dict()
        if recap_preview is None:
            status.add_error("apply requested but no recap preview is available")
            return status.to_dict()
        ok, err, archived = _safe_write_recap(
            corpus=corpus_dir,
            recap_rel=paths.canonical_recap_rel,
            recap_text=recap_preview,
            force_recap=options.force_recap,
        )
        if ok == "failed":
            status.add_error(err or "failed to apply canonical recap")
            return status.to_dict()
        if ok == "stale":
            status.add_state("canonical_recap_conflict")
            status.add_state("derivative_reconciliation_required")
            status.add_warning(err or "canonical recap differs from the staged source")
            status.add_next_action(
                "Review the canonical recap and preview, then explicitly refresh the canonical source if replacement is intended."
            )
            _annotate_corpus_impact(status, corpus_dir)
            return status.to_dict()
        if ok == "reused":
            status.add_state("recap_reused")
        else:
            status.add_state("recap_applied")
            if ok == "refreshed":
                status.add_state("canonical_recap_refreshed")
            if archived:
                record_archived_artifacts(status.ingest_report, archived)

    if options.normalize:
        ok, err, archived = _normalize_one(
            corpus=corpus_dir,
            canonical_recap_rel=paths.canonical_recap_rel,
            normalized_recap_rel=paths.normalized_recap_rel,
            force=options.force_normalize,
        )
        if ok == "failed":
            status.add_state("normalized_skipped")
            status.add_error(err or "normalize step failed")
            return status.to_dict()
        if ok == "stale":
            status.add_state("normalized_stale")
            status.add_state("derivative_reconciliation_required")
            status.add_warning(err or "normalized recap is stale")
            status.add_next_action(
                "Review and refresh the normalized recap from the current canonical recap before continuing."
            )
            _annotate_corpus_impact(status, corpus_dir)
            return status.to_dict()
        if ok == "reused":
            status.add_state("normalized_reused")
        else:
            status.add_state("normalized_refreshed" if ok == "refreshed" else "normalized_created")
            if archived:
                record_archived_artifacts(status.ingest_report, archived)
        status.add_state("normalized_current")
    else:
        status.add_state("normalized_skipped")

    duplicate_candidates = _annotate_normalized_duplicates(
        status,
        corpus_dir,
        campaign_number=paths.campaign_number,
        session=options.session,
    )
    if _normalized_duplicates_block_progress(duplicate_candidates):
        _annotate_corpus_impact(status, corpus_dir)
        return status.to_dict()
    if len(duplicate_candidates) > 1:
        try:
            disk_paths = _disk_derivative_paths(
                corpus_dir,
                campaign_number=paths.campaign_number,
                session=options.session,
            )
            status.paths.update(
                {key: disk_paths[key] for key in disk_paths if key in status.paths}
            )
            status.add_warning("continuing with recommended normalized recap among duplicates")
        except FileNotFoundError:
            pass

    try:
        breadcrumb_path, breadcrumb_rel = _resolve_breadcrumb_path(
            corpus_dir,
            campaign_number=paths.campaign_number,
            session=options.session,
            slug_derived_rel=paths.breadcrumbed_recap_rel,
        )
    except FileNotFoundError as exc:
        status.add_error(str(exc))
        return status.to_dict()

    if breadcrumb_rel != paths.breadcrumbed_recap_rel:
        status.paths["breadcrumbed_recap"] = breadcrumb_rel
        try:
            disk_paths = _disk_derivative_paths(
                corpus_dir,
                campaign_number=paths.campaign_number,
                session=options.session,
            )
            status.paths.update(
                {key: disk_paths[key] for key in disk_paths if key in status.paths}
            )
        except FileNotFoundError:
            pass
        status.add_warning("slug_mismatch_used_disk_breadcrumb")

    derivative_status = inspect_recap_ingest_status(
        campaign_id=options.campaign_id,
        session=options.session,
        title=options.title,
        slug=options.slug,
        corpus=corpus_dir,
    )
    derivative_states = set(derivative_status.get("states", []))
    upstream_blockers = {
        "normalized_stale",
        "normalized_provenance_unknown",
        "frontmatter_seed_stale",
        "frontmatter_seed_provenance_unknown",
        "frontmatter_seed_corrupt",
        "breadcrumb_stale",
        "breadcrumb_provenance_unknown",
        "breadcrumb_corrupt",
        "breadcrumb_blocked_by_upstream",
    }
    refreshing_only_stale_memory = (
        options.materialize_session_memory
        and options.force_session_memory
        and "breadcrumb_current" in derivative_states
        and "session_memory_stale" in derivative_states
        and not upstream_blockers.intersection(derivative_states)
    )
    for state in derivative_status.get("states", []):
        if refreshing_only_stale_memory and state in {
            "session_memory_stale",
            "derivative_reconciliation_required",
        }:
            continue
        if state == "derivative_reconciliation_required" or state.startswith(
            ("normalized_", "frontmatter_seed_", "breadcrumb_", "session_memory_")
        ):
            status.add_state(state)
    for warning in derivative_status.get("warnings", []):
        if refreshing_only_stale_memory and warning == (
            "session-memory files differ from the validated breadcrumb output; existing files were preserved"
        ):
            continue
        status.add_warning(warning)
    for action in derivative_status.get("next_actions", []):
        if refreshing_only_stale_memory and action == (
            "Review the breadcrumb, then explicitly refresh session memory to archive and replace the stale outputs."
        ):
            continue
        status.add_next_action(action)
    derivative_report = derivative_status.get("ingest_report", {}).get("derivative_stages")
    if isinstance(derivative_report, dict):
        status.ingest_report["derivative_stages"] = derivative_report

    frontmatter_seed_path = (corpus_dir / str(status.paths["frontmatter_seed"])).resolve()
    if frontmatter_seed_path.is_file():
        status.add_state("frontmatter_seed_found")
    elif "normalized_created" in status.states or "normalized_reused" in status.states:
        status.add_state("frontmatter_seed_required")
        status.add_next_action(
            "Build deterministic frontmatter seed skeleton: "
            f"uv run python scripts/build_recap_frontmatter_seed.py "
            f"--campaign {paths.campaign_number} --session {options.session}"
        )

    if breadcrumb_path.is_file():
        status.add_state("breadcrumb_found")
    else:
        status.add_state("breadcrumb_required")
        status.add_next_action(
            f"Review/bless frontmatter seed, run breadcrumb_query_run --ingest-routing-only "
            f"for Session {options.session}, then rerun --materialize-session-memory."
        )

    if options.materialize_session_memory:
        if not breadcrumb_path.is_file():
            status.add_state("session_memory_skipped")
            return status.to_dict()
        verified_states = set(derivative_status.get("states", []))
        if "breadcrumb_current" not in verified_states:
            status.add_state("session_memory_skipped")
            status.add_state("derivative_reconciliation_required")
            status.add_next_action(
                "Resolve upstream recap, seed, or breadcrumb lineage before materializing session memory."
            )
            return status.to_dict()
        try:
            summary = _materialize_one(
                corpus_root=corpus_dir,
                campaign_number=paths.campaign_number,
                session=options.session,
                dry_run=False,
                force=options.force_session_memory,
            )
        except (OSError, ValueError, BreadcrumbNormalizeError) as exc:
            status.add_state("session_memory_failed")
            status.add_state("derivative_reconciliation_required")
            status.add_warning(f"session-memory materialization failed: {exc}")
            status.add_next_action(
                "Review and correct the validated breadcrumb before materializing session memory again."
            )
            _annotate_corpus_impact(status, corpus_dir)
            return status.to_dict()
        if summary.get("outcome") == "stale":
            status.add_state("session_memory_stale")
            status.add_state("derivative_reconciliation_required")
            status.add_warning("session-memory files differ from the current breadcrumb and were preserved")
            status.add_next_action(
                "Review the current breadcrumb, then explicitly refresh session memory to archive and replace the stale files."
            )
            status.ingest_report["session_memory_outcome"] = "stale"
            _annotate_corpus_impact(status, corpus_dir)
            return status.to_dict()
        status.add_state("session_memory_materialized")
        status.add_state("session_memory_current")
        status.ingest_report["session_memory_outcome"] = summary.get("outcome")
        if summary.get("archived_artifacts"):
            record_archived_artifacts(
                status.ingest_report,
                list(summary["archived_artifacts"]),
            )
        status.ingest_report["session_memory_record_count"] = summary.get("record_count")
        if options.check:
            if _check_one(
                corpus_root=corpus_dir,
                campaign_number=paths.campaign_number,
                session=options.session,
            ):
                status.ingest_report["session_memory_check"] = "ok"
            else:
                status.add_error("session-memory --check failed")
                return status.to_dict()
        status.add_state("ready_for_planning_activation")
    else:
        status.add_state("session_memory_skipped")

    _annotate_corpus_impact(status, corpus_dir)
    return status.to_dict()


def _normalized_candidate_rows(
    corpus_dir: Path,
    *,
    campaign_number: int,
    session: int,
) -> list[dict[str, object]]:
    """Structured metadata for every ``_normalized`` recap candidate of a session."""
    candidates = normalized_recap_candidates(
        corpus_dir, campaign_number=campaign_number, session=session
    )
    prefix = session_recaps_prefix(campaign_number)
    rows: list[dict[str, object]] = []
    for path in candidates:
        try:
            stat = path.stat()
            size_bytes = stat.st_size
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            size_bytes = 0
            modified_at = ""
        rows.append(
            {
                "basename": path.stem,
                "relpath": f"{prefix}/_normalized/{path.name}",
                "size_bytes": size_bytes,
                "modified_at": modified_at,
                "is_generic": is_generic_recap_tail(path.stem),
            }
        )
    non_generic = [row for row in rows if not row["is_generic"]]
    recommended = pick_normalized_basename_from_disk(
        corpus_dir, campaign_number=campaign_number, session=session
    )
    if recommended is None and len(non_generic) == 1:
        recommended = str(non_generic[0]["basename"])
    for row in rows:
        row["recommended"] = bool(recommended) and row["basename"] == recommended
    return rows


def _normalized_duplicates_block_progress(rows: list[dict[str, object]]) -> bool:
    """True when duplicate normalized recaps exist and no recommended pick was resolved."""
    if len(rows) <= 1:
        return False
    return not any(bool(row.get("recommended")) for row in rows)


def _annotate_normalized_duplicates(
    status: RecapIngestStatus,
    corpus_dir: Path,
    *,
    campaign_number: int,
    session: int,
) -> list[dict[str, object]]:
    """Surface duplicate normalized recaps so the UI can offer reconciliation."""
    rows = _normalized_candidate_rows(
        corpus_dir, campaign_number=campaign_number, session=session
    )
    if len(rows) > 1:
        status.add_state("normalized_recap_duplicates")
        status.add_warning(
            f"found {len(rows)} normalized recaps for this session; expected exactly one"
        )
        status.ingest_report["normalized_recap_candidates"] = rows
        status.add_next_action(
            "Resolve duplicate normalized recaps: keep one canonical recap and archive the rest."
        )
    return rows


def _annotate_corpus_impact(status: RecapIngestStatus, corpus_dir: Path) -> None:
    """Attach small read-only previews/counts for the artifacts the ingest pipeline touched."""
    rows: list[dict[str, object]] = []
    for key in (
        "canonical_recap",
        "normalized_recap",
        "frontmatter_seed",
        "breadcrumbed_recap",
        "session_memory_jsonl",
        "session_memory_meta",
    ):
        rel = status.paths.get(key)
        if not rel:
            continue
        path = (corpus_dir / str(rel)).resolve()
        try:
            path.relative_to(corpus_dir)
        except ValueError:
            continue
        row: dict[str, object] = {
            "key": key,
            "relpath": str(rel),
            "exists": path.is_file(),
        }
        if path.is_file():
            stat = path.stat()
            row["size_bytes"] = stat.st_size
            row["modified_at"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            if key == "session_memory_jsonl":
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                row["record_count"] = len([line for line in lines if line.strip()])
                row["preview"] = "\n".join(lines[:3])
            elif path.suffix.lower() in {".md", ".json"}:
                row["preview"] = path.read_text(encoding="utf-8", errors="replace")[:1600]
        rows.append(row)
    status.ingest_report["corpus_impact"] = rows


def reconcile_normalized_recap(
    *,
    campaign_id: str,
    session: int,
    keep_basename: str,
    corpus: Path | None = None,
) -> dict[str, object]:
    """Archive every normalized recap (and matching derivatives) except ``keep_basename``.

    Moves rejected artifacts into sibling ``_archive`` folders (reversible, no deletes),
    then returns a fresh read-only status probe so the caller can prove the result.
    """
    from src.corpus.session_recap_paths import campaign_number_from_id

    corpus_dir = (corpus or corpus_root()).resolve()
    campaign_number = campaign_number_from_id(campaign_id)
    keep = keep_basename.strip()
    if not keep:
        raise ValueError("keep_basename is required to reconcile duplicate recaps")

    candidates = normalized_recap_candidates(
        corpus_dir, campaign_number=campaign_number, session=session
    )
    if len(candidates) < 2:
        raise ValueError(
            "reconcile requires more than one normalized recap; "
            f"found {len(candidates)} for C{campaign_number}S{session}"
        )
    stems = {path.stem for path in candidates}
    if keep not in stems:
        raise ValueError(
            f"keep_basename {keep!r} is not one of the normalized recaps on disk: {sorted(stems)}"
        )

    prefix = session_recaps_prefix(campaign_number)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived: list[dict[str, str]] = []

    def _archive(path: Path) -> None:
        try:
            path.resolve().relative_to(corpus_dir)
        except ValueError as exc:
            raise ValueError(f"refusing to archive path outside corpus: {path}") from exc
        archive_dir = path.parent / "_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        target = archive_dir / f"{path.stem}__{stamp}{path.suffix}"
        shutil.move(str(path), str(target))
        archived.append(
            {
                "from": str(path.relative_to(corpus_dir)),
                "to": str(target.relative_to(corpus_dir)),
            }
        )

    session_dir = corpus_dir / prefix
    for path in candidates:
        if path.stem == keep:
            continue
        _archive(path)
        # Downstream derivatives keyed on the rejected basename.
        derivatives = [
            session_dir / "_breadcrumbed" / f"{path.stem}.breadcrumbed.md",
            session_dir / "_breadcrumbed" / f"{path.stem}.frontmatter_seed.md",
            session_dir / "_session_memory" / f"{path.stem}.records_meta.jsonl",
            session_dir / "_session_memory" / f"{path.stem}.records_meta.json",
        ]
        for derivative in derivatives:
            if derivative.is_file():
                _archive(derivative)

    status = inspect_recap_ingest_status(
        campaign_id=campaign_id,
        session=session,
        title=None,
        slug=None,
        corpus=corpus_dir,
    )
    status["states"] = list(dict.fromkeys([*status.get("states", []), "normalized_recap_reconciled"]))
    report = status.setdefault("ingest_report", {})
    if isinstance(report, dict):
        report["reconciled_kept_basename"] = keep
        report["reconciled_archived"] = archived
    return status


def inspect_recap_ingest_status(
    *,
    campaign_id: str,
    session: int,
    title: str | None,
    slug: str | None,
    corpus: Path | None = None,
) -> dict[str, object]:
    """Read-only probe of on-disk recap ingest artifacts for wizard resume."""
    status = RecapIngestStatus(campaign_id=campaign_id, session=session)
    corpus_dir = (corpus or corpus_root()).resolve()
    paths = RecapStagePaths.build(
        campaign_id=campaign_id,
        session=session,
        slug_tail=_slug_tail(session=session, title=title, slug=slug),
    )
    status.paths = {
        "staged_raw_notes": paths.staged_raw_notes_rel,
        "canonical_recap": paths.canonical_recap_rel,
        "normalized_recap": paths.normalized_recap_rel,
        "frontmatter_seed": paths.frontmatter_seed_rel,
        "breadcrumbed_recap": paths.breadcrumbed_recap_rel,
        "session_memory_jsonl": paths.session_memory_jsonl_rel,
        "session_memory_meta": paths.session_memory_meta_rel,
    }

    slug_default_canonical = paths.canonical_recap_rel
    try:
        disk_paths = _disk_derivative_paths(
            corpus_dir,
            campaign_number=paths.campaign_number,
            session=session,
        )
        status.paths.update(disk_paths)
        if disk_paths["normalized_recap"] != paths.normalized_recap_rel:
            status.add_warning("slug_mismatch_used_disk_breadcrumb")
    except FileNotFoundError:
        disk_paths = None

    duplicate_candidates = _annotate_normalized_duplicates(
        status,
        corpus_dir,
        campaign_number=paths.campaign_number,
        session=session,
    )
    if _normalized_duplicates_block_progress(duplicate_candidates):
        _annotate_corpus_impact(status, corpus_dir)
        return status.to_dict()
    if len(duplicate_candidates) > 1:
        try:
            disk_paths = _disk_derivative_paths(
                corpus_dir,
                campaign_number=paths.campaign_number,
                session=session,
            )
            status.paths.update(disk_paths)
            status.add_warning("continuing with recommended normalized recap among duplicates")
        except FileNotFoundError:
            disk_paths = None

    status.paths["canonical_recap"] = _resolve_canonical_recap_rel(
        corpus_dir,
        campaign_number=paths.campaign_number,
        session=session,
        slug_default_rel=slug_default_canonical,
        normalized_rel=str(status.paths.get("normalized_recap") or "") or None,
    )
    if (
        status.paths["canonical_recap"] != slug_default_canonical
        and "slug_mismatch_used_disk_breadcrumb" not in status.warnings
    ):
        status.add_warning("slug_mismatch_used_disk_breadcrumb")

    staged_path = (corpus_dir / str(status.paths["staged_raw_notes"])).resolve()
    if staged_path.is_file():
        status.add_state("staged_raw_notes_reused")
        raw_text = staged_path.read_text(encoding="utf-8")
        status.entity_spelling_audit = _spelling_audit(raw_text)
        if status.entity_spelling_audit:
            status.add_warning("entity spelling variants detected; review_only")

    canonical_path = (corpus_dir / str(status.paths["canonical_recap"])).resolve()
    if canonical_path.is_file():
        status.add_state("recap_reused")

    normalized_state = "missing"
    normalized_path = (corpus_dir / str(status.paths["normalized_recap"])).resolve()
    if normalized_path.is_file():
        status.add_state("normalized_reused")
        try:
            expected_normalized = _expected_normalized_content(
                corpus=corpus_dir,
                canonical_recap_rel=str(status.paths["canonical_recap"]),
            )
        except (FileNotFoundError, UnicodeDecodeError, ValueError) as exc:
            normalized_state = "unknown"
            status.add_state("normalized_provenance_unknown")
            status.add_state("derivative_reconciliation_required")
            status.add_warning(f"normalized recap could not be checked against its canonical source: {exc}")
        else:
            expected_digest = sha256_bytes(expected_normalized.encode("utf-8"))
            actual_digest = sha256_bytes(normalized_path.read_bytes())
            if expected_digest == actual_digest:
                normalized_state = "current"
                status.add_state("normalized_current")
            else:
                normalized_state = "stale"
                status.add_state("normalized_stale")
                status.add_state("derivative_reconciliation_required")
                status.add_warning("normalized recap differs from the deterministic output for the current canonical recap")
                status.add_next_action(
                    "Review and refresh the normalized recap before building or routing downstream artifacts."
                )
            status.ingest_report.setdefault("derivative_stages", {})["normalized_recap"] = {
                "state": normalized_state,
                "expected_sha256": expected_digest,
                "output_sha256": actual_digest,
            }

    frontmatter_seed_path = (corpus_dir / str(status.paths["frontmatter_seed"])).resolve()
    seed_provenance_path = provenance_path(frontmatter_seed_path)
    status.paths["frontmatter_seed_provenance"] = seed_provenance_path.resolve().relative_to(corpus_dir).as_posix()
    seed_state = "missing"
    if frontmatter_seed_path.is_file():
        status.add_state("frontmatter_seed_found")
        if normalized_path.is_file():
            try:
                generated_seed = build_frontmatter_seed(
                    corpus_root=corpus_dir,
                    campaign_number=paths.campaign_number,
                    session=session,
                )
                generated_seed_bytes = (
                    generated_seed if generated_seed.endswith("\n") else generated_seed + "\n"
                ).encode("utf-8")
                seed_input_digests = {
                    "normalized_recap": sha256_file(normalized_path),
                    "generated_seed": sha256_bytes(generated_seed_bytes),
                }
                seed_state, _ = read_provenance_state(
                    output_path=frontmatter_seed_path,
                    corpus_root=corpus_dir,
                    stage="frontmatter_seed",
                    campaign_number=paths.campaign_number,
                    session=session,
                    input_digests=seed_input_digests,
                )
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                seed_state = "unknown"
                status.add_warning(f"frontmatter seed lineage could not be checked: {exc}")
            status.ingest_report.setdefault("derivative_stages", {})["frontmatter_seed"] = {
                "state": seed_state,
                "provenance_path": status.paths["frontmatter_seed_provenance"],
            }
            if seed_state == "current":
                status.add_state("frontmatter_seed_current")
            elif seed_state == "edited_current_inputs":
                status.add_state("frontmatter_seed_edited_current_inputs")
            else:
                stage_state = "provenance_unknown" if seed_state == "unknown" else seed_state
                status.add_state(f"frontmatter_seed_{stage_state}")
                status.add_state("derivative_reconciliation_required")
                status.add_warning(f"frontmatter seed is {stage_state}; preserve it and explicitly refresh/review before routing")
                status.add_next_action(
                    "Refresh the frontmatter seed from the current normalized recap, then review it before routing."
                )
        else:
            seed_state = "unknown"
            status.add_state("frontmatter_seed_provenance_unknown")
            status.add_state("derivative_reconciliation_required")
            status.add_warning("frontmatter seed cannot be verified because its normalized recap is missing")
    elif "normalized_reused" in status.states:
        status.add_state("frontmatter_seed_required")
        status.add_next_action(
            "Build deterministic frontmatter seed skeleton: "
            f"uv run python scripts/build_recap_frontmatter_seed.py "
            f"--campaign {paths.campaign_number} --session {session}"
        )

    try:
        breadcrumb_path, breadcrumb_rel = _resolve_breadcrumb_path(
            corpus_dir,
            campaign_number=paths.campaign_number,
            session=session,
            slug_derived_rel=str(status.paths["breadcrumbed_recap"]),
        )
    except FileNotFoundError as exc:
        status.add_error(str(exc))
        return status.to_dict()

    if breadcrumb_rel != status.paths["breadcrumbed_recap"]:
        status.paths["breadcrumbed_recap"] = breadcrumb_rel

    breadcrumb_sidecar = provenance_path(breadcrumb_path)
    status.paths["breadcrumbed_recap_provenance"] = breadcrumb_sidecar.resolve().relative_to(corpus_dir).as_posix()
    if breadcrumb_path.is_file():
        status.add_state("breadcrumb_found")
        if normalized_path.is_file() and frontmatter_seed_path.is_file():
            try:
                breadcrumb_input_digests = {
                    "normalized_recap": sha256_file(normalized_path),
                    "frontmatter_seed": sha256_file(frontmatter_seed_path),
                }
                breadcrumb_state, _ = read_provenance_state(
                    output_path=breadcrumb_path,
                    corpus_root=corpus_dir,
                    stage="breadcrumbed_recap",
                    campaign_number=paths.campaign_number,
                    session=session,
                    input_digests=breadcrumb_input_digests,
                )
            except OSError as exc:
                breadcrumb_state = "unknown"
                status.add_warning(f"breadcrumb lineage could not be checked: {exc}")
        else:
            breadcrumb_state = "unknown"
        status.ingest_report.setdefault("derivative_stages", {})["breadcrumbed_recap"] = {
            "state": breadcrumb_state,
            "provenance_path": status.paths["breadcrumbed_recap_provenance"],
        }
        upstream_current = normalized_state == "current" and seed_state in {
            "current",
            "edited_current_inputs",
        }
        if breadcrumb_state == "current" and upstream_current:
            status.add_state("breadcrumb_current")
        elif breadcrumb_state == "current":
            status.add_state("breadcrumb_blocked_by_upstream")
            status.add_state("derivative_reconciliation_required")
            status.ingest_report["derivative_stages"]["breadcrumbed_recap"]["readiness"] = "blocked_upstream"
            status.add_warning("breadcrumb matches its direct inputs, but an upstream recap derivative is stale or unverified")
            status.add_next_action(
                "Resolve the normalized recap and frontmatter seed lineage before using this breadcrumb downstream."
            )
        else:
            stage_state = "provenance_unknown" if breadcrumb_state == "unknown" else breadcrumb_state
            status.add_state(f"breadcrumb_{stage_state}")
            status.add_state("derivative_reconciliation_required")
            status.add_warning(f"breadcrumb is {stage_state}; automatic reuse is blocked")
            status.add_next_action(
                "Review current normalized recap and frontmatter seed, then explicitly rerun breadcrumb routing."
            )
    else:
        status.add_state("breadcrumb_required")
        status.add_next_action(
            f"Review/bless frontmatter seed, run breadcrumb_query_run --ingest-routing-only "
            f"for Session {session}, then rerun --materialize-session-memory."
        )

    memory_jsonl = (corpus_dir / str(status.paths["session_memory_jsonl"])).resolve()
    memory_meta = (corpus_dir / str(status.paths["session_memory_meta"])).resolve()
    memory_files = [path for path in (memory_jsonl, memory_meta) if path.is_file()]
    if "breadcrumb_current" in status.states:
        try:
            expected_memory = _expected_session_memory_outputs(
                corpus_root=corpus_dir,
                campaign_number=paths.campaign_number,
                session=session,
            )
            expected_jsonl = bytes(expected_memory["jsonl_bytes"])
            expected_meta = bytes(expected_memory["meta_bytes"])
            memory_current = (
                memory_jsonl.is_file()
                and memory_meta.is_file()
                and memory_jsonl.read_bytes() == expected_jsonl
                and memory_meta.read_bytes() == expected_meta
            )
        except (OSError, BreadcrumbNormalizeError, ValueError) as exc:
            memory_current = False
            status.add_warning(f"session-memory outputs could not be validated: {exc}")
        if memory_current:
            status.add_state("session_memory_materialized")
            status.add_state("session_memory_current")
            status.add_state("ready_for_planning_activation")
            status.add_next_action("Ingest complete. Proceed with planning activation.")
        elif memory_files:
            status.add_state("session_memory_stale")
            status.add_state("derivative_reconciliation_required")
            status.add_warning("session-memory files differ from the validated breadcrumb output; existing files were preserved")
            status.add_next_action("Review the breadcrumb, then explicitly refresh session memory to archive and replace the stale outputs.")
        else:
            status.add_next_action("Run Materialize Session Memory.")

    status.add_state("ingest_status_inspected")
    _annotate_corpus_impact(status, corpus_dir)
    return status.to_dict()


def _print_human(status: dict[str, object]) -> None:
    print(f"status: {status.get('status')}")
    print(f"campaign/session: {status.get('campaign_id')} / {status.get('session')}")
    states = status.get("states", [])
    if isinstance(states, list) and states:
        print("states:")
        for row in states:
            print(f"  - {row}")
    warnings = status.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        print("warnings:")
        for row in warnings:
            print(f"  - {row}")
    errors = status.get("errors", [])
    if isinstance(errors, list) and errors:
        print("errors:")
        for row in errors:
            print(f"  - {row}")
    next_actions = status.get("next_actions", [])
    if isinstance(next_actions, list) and next_actions:
        print("next_actions:")
        for row in next_actions:
            print(f"  - {row}")


def main(argv: list[str] | None = None) -> int:
    options = _parse_args(argv)
    status = run_pipeline(options)
    if options.json_output:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        _print_human(status)
    errors = status.get("errors", [])
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
