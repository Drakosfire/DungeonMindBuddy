"""Guarded corpus write utilities for the session-recap workflow.

Two-phase commit and a strict path allowlist keep the static character/world
bible (dossier, seed, statblock) read-only while letting the planner add new
session recaps and append rows to NPC timelines / hub READMEs.

Public surface:
    - ``is_writable_corpus_path(rel_path, mode)``: allowlist predicate.
    - ``write_corpus_file(...)``: dry-run -> ``confirm_token`` -> commit.
    - ``append_timeline_row(...)``: specialized helper for NPC ``timeline.md`` rows.
    - ``recompute_corpus_fingerprint(corpus_dir)``: thin wrapper for post-write reporting.

Two-phase contract: a first call with ``dry_run=True`` (default) returns a
unified-diff preview and a ``confirm_token`` derived from
``(path, mode, content, file_state_token)``. The commit call must echo the
same token; if the file or proposed content changed in between, the token
mismatches and the write is refused. The behavioral safety (operator review
of the diff before commit) lives in the SKILL; the token is the technical
floor.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

import blake3

_ALLOWED_MODES: tuple[str, ...] = ("create", "append")

# Allowlist of corpus-relative paths the writer may touch.
_CREATE_ALLOWED_RE = re.compile(r"(?:^|/)Session Recaps/Session \d+ - .+\.md$")
_TIMELINE_RE = re.compile(r"(?:^|/)NPCs/[^/]+/timeline\.md$")
_HUB_README_RE = re.compile(r"(?:^|/)NPCs/[^/]+/README\.md$")
_SETTING_HUB_NPC_README_RE = re.compile(
    r"^Elderwyld/Cities and Towns/[^/]+/NPCs/[^/]+/README\.md$"
)
_SETTING_HUB_NPC_SEED_RE = re.compile(
    r"^Elderwyld/Cities and Towns/[^/]+/NPCs/[^/]+/character_seed\.md$"
)
_CAMPAIGN_DOSSIER_CREATE_RE = re.compile(
    r"^Longmont Campaign/Campaign \d+/NPCs/[^/]+/[^/]+_character_dossier\.md$"
)
_LOCATIONS_CREATE_RE = re.compile(r"^Elderwyld/Locations/[^/]+\.md$")
_PREP_SESSION_APPEND_RE = re.compile(
    r"^Longmont Campaign/Campaign \d+/Session Prep/[^/]+\.md$"
)

# Forbidden basenames regardless of mode: the static character/world bible.
_DENY_BASENAMES = re.compile(
    r"(?:^|/)(?:[^/]*_character_dossier\.md|character_seed\.md|[^/]*_statblock[^/]*\.md)$",
    re.IGNORECASE,
)


def _normalize_relpath(rel_path: str) -> str:
    return rel_path.strip().replace("\\", "/").lstrip("/")


def _resolve_corpus_target(corpus_dir: Path, rel_path: str) -> Path | None:
    """Return absolute path under ``corpus_dir``; ``None`` for traversal or non-``.md``."""
    root = corpus_dir.resolve()
    cleaned = _normalize_relpath(rel_path)
    if not cleaned or ".." in Path(cleaned).parts:
        return None
    candidate = (root / cleaned).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.suffix.lower() != ".md":
        return None
    return candidate


def _prep_footer_append_payload_ok(payload: str) -> bool:
    """Session Prep appends must be a blockquote line opening with bold marker."""
    seg = payload.strip()
    if not seg.startswith(">"):
        return False
    first_line = seg.split("\n", 1)[0]
    return "**" in first_line


def is_writable_corpus_path(rel_path: str, mode: str) -> tuple[bool, str]:
    """Return ``(allowed, reason)``. Reason is empty when allowed."""
    if mode not in _ALLOWED_MODES:
        return False, f"mode must be one of {_ALLOWED_MODES}; got {mode!r}"
    cleaned = _normalize_relpath(rel_path)
    if not cleaned:
        return False, "path is empty"
    if _DENY_BASENAMES.search(cleaned):
        if mode == "create" and (
            _SETTING_HUB_NPC_SEED_RE.match(cleaned)
            or _CAMPAIGN_DOSSIER_CREATE_RE.match(cleaned)
        ):
            pass
        else:
            return False, (
                "Forbidden: dossier, seed, and statblock files are read-only "
                "(`*_character_dossier.md`, `character_seed.md`, `*_statblock*.md`)."
            )
    if mode == "create":
        if _CREATE_ALLOWED_RE.search(cleaned):
            return True, ""
        if _SETTING_HUB_NPC_README_RE.match(cleaned):
            return True, ""
        if _SETTING_HUB_NPC_SEED_RE.match(cleaned):
            return True, ""
        if _CAMPAIGN_DOSSIER_CREATE_RE.match(cleaned):
            return True, ""
        if _LOCATIONS_CREATE_RE.match(cleaned):
            return True, ""
        return False, (
            "create mode is not allowed for this path (allowed: "
            "`**/Session Recaps/Session NN - <slug>.md`, "
            "Elderwyld `.../Cities and Towns/<town>/NPCs/<slug>/{README.md,character_seed.md}`, "
            "campaign `.../NPCs/<slug>/*_character_dossier.md`, "
            "or `Elderwyld/Locations/<stub>.md`)."
        )
    if (
        _TIMELINE_RE.search(cleaned)
        or _HUB_README_RE.search(cleaned)
        or _PREP_SESSION_APPEND_RE.match(cleaned)
    ):
        return True, ""
    return False, (
        "append mode is not allowed for this path (allowed: "
        "`**/NPCs/<slug>/timeline.md`, `**/NPCs/<slug>/README.md`, "
        "or `Longmont Campaign/Campaign N/Session Prep/*.md`)."
    )


def _file_state_token(target: Path) -> str:
    """Stable token for the pre-write file state; commit must see the same value."""
    if target.exists():
        try:
            st = target.stat()
            return f"present:{st.st_mtime_ns}:{st.st_size}"
        except OSError:
            return "present:unknown"
    return "absent"


def _compute_confirm_token(
    cleaned_path: str, mode: str, content: str, file_state: str
) -> str:
    payload = "\n".join([cleaned_path, mode, content, file_state]).encode("utf-8")
    return blake3.blake3(payload).hexdigest()[:32]


def _project_new_content(existing: str | None, mode: str, payload: str) -> str:
    """Compose the would-be file body for ``mode`` so the diff reflects what commit writes."""
    if mode == "create":
        body = payload if payload.endswith("\n") else payload + "\n"
        return body
    base = existing or ""
    if base and not base.endswith("\n"):
        base = base + "\n"
    new_segment = payload if payload.endswith("\n") else payload + "\n"
    return base + new_segment


def _render_unified_diff(existing: str, new_full: str, rel_path: str) -> str:
    a = existing.splitlines(keepends=True)
    b = new_full.splitlines(keepends=True)
    diff = difflib.unified_diff(
        a, b, fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}", n=3
    )
    return "".join(diff)


def write_corpus_file(
    corpus_dir: Path,
    *,
    path: str,
    mode: str,
    content: str,
    dry_run: bool = True,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Allowlist-guarded, two-phase write under ``corpus_dir``.

    First call (default ``dry_run=True``) returns a ``preview`` payload with a unified
    diff and a ``confirm_token``. Second call with ``dry_run=False`` and the same token
    actually writes; mismatching tokens (file changed, content changed) abort the write.
    """
    allowed, reason = is_writable_corpus_path(path, mode)
    if not allowed:
        return {"ok": False, "error": reason}

    cleaned = _normalize_relpath(path)
    target = _resolve_corpus_target(corpus_dir, cleaned)
    if target is None:
        return {
            "ok": False,
            "error": "path must be a corpus-relative `.md` file under the corpus root.",
        }

    if mode == "create" and target.exists():
        return {"ok": False, "error": f"create mode but file already exists: {cleaned}"}
    if mode == "append" and not target.exists():
        return {"ok": False, "error": f"append mode but file does not exist: {cleaned}"}

    if mode == "append" and _PREP_SESSION_APPEND_RE.match(cleaned):
        if not _prep_footer_append_payload_ok(content):
            return {
                "ok": False,
                "error": (
                    "Session Prep append content must be a Markdown blockquote starting with "
                    "`>` whose first line includes `**`."
                ),
            }

    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    new_full = _project_new_content(existing or None, mode, content)
    file_state = _file_state_token(target)
    token = _compute_confirm_token(cleaned, mode, content, file_state)
    diff = _render_unified_diff(existing, new_full, cleaned)

    if dry_run:
        return {
            "ok": True,
            "phase": "preview",
            "path": cleaned,
            "mode": mode,
            "confirm_token": token,
            "diff": diff,
            "new_size_bytes": len(new_full.encode("utf-8")),
            "next_call": (
                "After operator approves the diff, re-call with the same arguments plus "
                f"`dry_run=false` and `confirm_token={token!r}`."
            ),
        }

    if not confirm_token:
        return {"ok": False, "error": "commit requires confirm_token from a prior dry_run"}
    if confirm_token != token:
        return {
            "ok": False,
            "error": (
                "stale confirm_token (file or content changed since dry_run). "
                "Re-run with dry_run=true to get a fresh token."
            ),
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_full, encoding="utf-8")

    new_fp = ""
    try:
        new_fp = recompute_corpus_fingerprint(corpus_dir)
    except Exception:  # pragma: no cover - fingerprint is best-effort reporting
        new_fp = ""

    return {
        "ok": True,
        "phase": "committed",
        "path": cleaned,
        "mode": mode,
        "bytes_written": len(new_full.encode("utf-8")),
        "new_corpus_fingerprint": new_fp,
        "fingerprint_reminder": (
            f"Corpus changed; new fingerprint = {new_fp or '<unavailable>'}. "
            "Update `evals/lysandra_vertical_slice/gold/step0_environment.json` "
            "(`expected_fingerprint`) and run `uv run pytest tests/test_lysandra_vertical_slice_step0.py`."
        ),
    }


# ---------------------------------------------------------------------------
# Timeline row helper
# ---------------------------------------------------------------------------


def _format_timeline_row(session: int, beat: str, recap_relpath: str) -> str:
    beat_clean = beat.strip().replace("\n", " ").replace("|", "\\|")
    return f"| **{session}** | {beat_clean} | `{recap_relpath}` |"


def _find_timeline_for_slug(corpus_dir: Path, npc_slug: str) -> tuple[Path | None, list[str]]:
    """Return ``(unique_match, all_candidates)``. ``unique_match`` is ``None`` when ambiguous."""
    root = corpus_dir.resolve()
    matches = sorted(
        p for p in root.rglob(f"NPCs/{npc_slug}/timeline.md") if p.is_file()
    )
    rels = [p.relative_to(root).as_posix() for p in matches]
    if len(matches) == 1:
        return matches[0], rels
    return None, rels


def append_timeline_row(
    corpus_dir: Path,
    *,
    npc_slug: str,
    session: int,
    beat: str,
    recap_path: str,
    timeline_path: str | None = None,
    dry_run: bool = True,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    """Append one row to the campaign-hub ``NPCs/<slug>/timeline.md``.

    Wraps :func:`write_corpus_file` so the model cannot accidentally rewrite the existing
    table. ``recap_path`` must already exist under the corpus. When multiple
    ``NPCs/<slug>/timeline.md`` files match (e.g. campaign 1 vs campaign 2), pass
    ``timeline_path`` explicitly to disambiguate.
    """
    if not npc_slug or "/" in npc_slug:
        return {"ok": False, "error": "npc_slug must be a single folder slug (no slashes)"}
    try:
        sess_int = int(session)
    except (TypeError, ValueError):
        return {"ok": False, "error": "session must be an integer"}
    if sess_int < 1:
        return {"ok": False, "error": "session must be a positive integer"}
    beat_text = (beat or "").strip()
    if not beat_text:
        return {"ok": False, "error": "beat must be non-empty"}
    recap_rel = _normalize_relpath(recap_path or "")
    if not recap_rel:
        return {"ok": False, "error": "recap_path must be a corpus-relative path"}

    recap_target = _resolve_corpus_target(corpus_dir, recap_rel)
    if recap_target is None or not recap_target.is_file():
        return {
            "ok": False,
            "error": f"recap_path does not exist under corpus root: {recap_rel}",
        }

    if timeline_path:
        cleaned_tp = _normalize_relpath(timeline_path)
    else:
        located, candidates = _find_timeline_for_slug(corpus_dir, npc_slug)
        if located is None:
            if not candidates:
                return {
                    "ok": False,
                    "error": (
                        f"no `NPCs/{npc_slug}/timeline.md` found under corpus; "
                        "create one first or pass `timeline_path` explicitly."
                    ),
                }
            return {
                "ok": False,
                "error": (
                    f"multiple timelines for slug {npc_slug!r}; "
                    "pass `timeline_path` to disambiguate. candidates: "
                    + ", ".join(candidates)
                ),
            }
        cleaned_tp = located.relative_to(corpus_dir.resolve()).as_posix()

    row = _format_timeline_row(sess_int, beat_text, recap_rel)
    return write_corpus_file(
        corpus_dir,
        path=cleaned_tp,
        mode="append",
        content=row,
        dry_run=dry_run,
        confirm_token=confirm_token,
    )


# ---------------------------------------------------------------------------
# Fingerprint reporting
# ---------------------------------------------------------------------------


def recompute_corpus_fingerprint(corpus_dir: Path) -> str:
    """Recompute the planner-cache corpus fingerprint after a write."""
    # Local import: ``planner_cache`` already imports ``planner``; keep this module decoupled.
    from src.agent.planner_cache import corpus_fingerprint

    return corpus_fingerprint(corpus_dir)


def update_step0_expected_fingerprint(
    step0_path: Path,
    *,
    new_fingerprint: str,
) -> dict[str, Any]:
    """Operator-invoked helper: rewrite ``expected_fingerprint`` in a step0 gold JSON.

    Returns ``{"ok": bool, "old": str, "new": str, "path": str}`` (or ``{"ok": False, "error": ...}``).
    Never called automatically by the planner — leave the decision to the operator after
    they review the new recap and timeline rows in git.
    """
    import json as _json

    if not step0_path.is_file():
        return {"ok": False, "error": f"step0 file not found: {step0_path}"}
    try:
        data = _json.loads(step0_path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"failed to read step0 json: {exc}"}
    old = str(data.get("expected_fingerprint", ""))
    if not new_fingerprint or not isinstance(new_fingerprint, str):
        return {"ok": False, "error": "new_fingerprint must be a non-empty string"}
    data["expected_fingerprint"] = new_fingerprint
    step0_path.write_text(_json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(step0_path),
        "old": old,
        "new": new_fingerprint,
    }
