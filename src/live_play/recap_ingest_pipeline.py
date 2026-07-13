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
from scripts.materialize_session_memory import _check_one, _materialize_one
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
from src.live_play.recap_stage_paths import RecapStagePaths, corpus_root

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
) -> tuple[str, str | None]:
    """Return (outcome, error). Outcome is created, reused, or failed."""
    allowed, reason = is_writable_corpus_path(recap_rel, "create")
    if not allowed:
        return "failed", reason
    target = (corpus / recap_rel).resolve()
    try:
        target.relative_to(corpus.resolve())
    except ValueError:
        return "failed", "canonical recap path escapes corpus root"

    if target.exists() and not force_recap:
        return "reused", None

    if target.exists() and force_recap:
        target.write_text(recap_text if recap_text.endswith("\n") else recap_text + "\n", encoding="utf-8")
        return "created", None

    preview = write_corpus_file(
        corpus,
        path=recap_rel,
        mode="create",
        content=recap_text,
        dry_run=True,
    )
    if not preview.get("ok"):
        return "failed", str(preview.get("error") or "recap preview failed")
    commit = write_corpus_file(
        corpus,
        path=recap_rel,
        mode="create",
        content=recap_text,
        dry_run=False,
        confirm_token=str(preview.get("confirm_token") or ""),
    )
    if not commit.get("ok"):
        return "failed", str(commit.get("error") or "recap commit failed")
    return "created", None


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
) -> tuple[str, str | None]:
    """Return (outcome, error). Outcome is created, reused, or failed."""
    normalized_target = (corpus / normalized_recap_rel).resolve()
    if normalized_target.is_file():
        return "reused", None

    recap_path = (corpus / canonical_recap_rel).resolve()
    if not recap_path.is_file():
        return "failed", f"canonical recap missing for normalize step: {canonical_recap_rel}"

    text = recap_path.read_text(encoding="utf-8")
    fm, body = _parse_minimal_frontmatter(text)
    title = str(fm.get("title") or "").strip()
    if _GENERIC_RECAP_TITLE_RE.match(title):
        return "failed", "normalize blocked: generic recap title requires non-generic slug/title"
    recap_raw, _ = _extract_recap_raw(body)
    clean = _clean_body(recap_raw)
    content = _build_normalized_content(
        fm=fm,
        body_clean=clean,
        session=int(fm.get("session") or 0),
        normalized_from=canonical_recap_rel,
        title=title,
    )
    preview = write_corpus_file(
        corpus,
        path=normalized_recap_rel,
        mode="create",
        content=content,
        dry_run=True,
    )
    if not preview.get("ok"):
        return "failed", str(preview.get("error") or "normalize preview failed")
    commit = write_corpus_file(
        corpus,
        path=normalized_recap_rel,
        mode="create",
        content=content,
        dry_run=False,
        confirm_token=str(preview.get("confirm_token") or ""),
    )
    if not commit.get("ok"):
        return "failed", str(commit.get("error") or "normalize commit failed")
    return "created", None


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
        ok, err = _safe_write_recap(
            corpus=corpus_dir,
            recap_rel=paths.canonical_recap_rel,
            recap_text=recap_preview,
            force_recap=options.force_recap,
        )
        if ok == "failed":
            status.add_error(err or "failed to apply canonical recap")
            return status.to_dict()
        if ok == "reused":
            status.add_state("recap_reused")
        else:
            status.add_state("recap_applied")

    if options.normalize:
        ok, err = _normalize_one(
            corpus=corpus_dir,
            canonical_recap_rel=paths.canonical_recap_rel,
            normalized_recap_rel=paths.normalized_recap_rel,
        )
        if ok == "failed":
            status.add_state("normalized_skipped")
            status.add_error(err or "normalize step failed")
            return status.to_dict()
        if ok == "reused":
            status.add_state("normalized_reused")
        else:
            status.add_state("normalized_created")
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
        summary = _materialize_one(
            corpus_root=corpus_dir,
            campaign_number=paths.campaign_number,
            session=options.session,
            dry_run=False,
        )
        status.add_state("session_memory_materialized")
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

    normalized_path = (corpus_dir / str(status.paths["normalized_recap"])).resolve()
    if normalized_path.is_file():
        status.add_state("normalized_reused")

    frontmatter_seed_path = (corpus_dir / str(status.paths["frontmatter_seed"])).resolve()
    if frontmatter_seed_path.is_file():
        status.add_state("frontmatter_seed_found")
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

    if breadcrumb_path.is_file():
        status.add_state("breadcrumb_found")
    else:
        status.add_state("breadcrumb_required")
        status.add_next_action(
            f"Review/bless frontmatter seed, run breadcrumb_query_run --ingest-routing-only "
            f"for Session {session}, then rerun --materialize-session-memory."
        )

    memory_jsonl = (corpus_dir / str(status.paths["session_memory_jsonl"])).resolve()
    if memory_jsonl.is_file():
        status.add_state("session_memory_materialized")
        status.add_state("ready_for_planning_activation")
        status.add_next_action("Ingest complete. Proceed with planning activation.")
    elif "breadcrumb_found" in status.states:
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
