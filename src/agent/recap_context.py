"""Deterministic recap-context resolver for the ``recap-write`` skill.

Given a campaign corpus root, return the canonical context the skill needs
**without any model judgment**:

- the active campaign (auto-detected from the recap with the highest ``session: N``,
  or pinned by an explicit ``campaign_id`` argument),
- the session number being ingested (``target_session = max(session) + 1`` for that
  campaign by default, or pinned by ``target_session``),
- the K most recent recap files **strictly older than** ``target_session``, sorted
  descending by frontmatter ``session`` (not by filename — recap titles are
  inconsistent: ``"Session 10 - Recap:"`` vs ``"Session 19 - Recap"``),
- the companion prep doc at ``Session Prep/session_<target>_*.md`` if exactly one
  exists; raises on >1 to force the **one-prep-doc-per-session naming convention**.

This module is the source of truth for "which prior recaps to read." The
``get_recap_context`` planner tool wraps it; the ``recap-write`` skill protocol
calls that tool **once** and then ``read_corpus_file`` on every path it returns.
The model never lists ``Session Recaps/`` itself, never picks recaps by filename,
and never globs for prep docs.

See ``Docs/Plans/PROCESSING-NOTES-Session-20-Manual-Ingest.md`` for the analysis
that motivated removing this guesswork from the model.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# NB: ``src.ingestion.frontmatter`` would be the natural source of these helpers,
# but importing it pulls in the optional ``docx`` dep via ``src.ingestion.__init__``.
# The recap workflow doesn't need that surface — we inline a permissive parse here
# scoped to the keys we care about (``session``, ``campaign_id``, ``title``).

RECENT_RECAP_K: int = 3
"""Hard-coded number of prior recaps the skill reads for shape survey.

Frozen at 3 — see the design discussion in the recap-write skill `See also`
section. Do **not** make this configurable; one number across all callers keeps
the benchmark assertions stable.
"""

_RECAPS_DIR_NAME = "Session Recaps"
_PREP_DIR_NAME = "Session Prep"
_NPCS_DIR_NAME = "NPCs"

# Match ``session_<N>_*.md`` and ``session_<N>.md`` under ``Session Prep/``. The
# trailing-underscore form is the convention; the bare-number form is tolerated for
# the rare single-file case. Anything else is **not** a prep doc and is ignored.
_PREP_DOC_RE_TEMPLATE = r"^session_{n}(?:_.*)?\.md$"


def _parse_minimal_frontmatter(text: str) -> dict[str, Any] | None:
    """Permissive ``---``-fenced YAML-ish parse → ``{key: value}`` dict, or ``None``.

    Scoped to scalar lines (``key: value``) and the small set of keys recap files
    use; ignores comments and blank lines. Quoted strings are unwrapped. Anything
    that isn't a clean ``key: value`` line is skipped silently — recap frontmatter
    is shape-stable in this corpus, and we only need a handful of fields.
    Returns ``None`` when no frontmatter fence is found.
    """
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None
    lines = text.splitlines(keepends=False)
    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None
    payload: dict[str, Any] = {}
    for raw in lines[1:end_idx]:
        s = raw.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        key, _, value = s.partition(":")
        key = key.strip()
        value = value.strip()
        if value in {"", "null", "NULL", "None", "none", "~"}:
            payload[key] = None
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        elif value.lstrip("-").isdigit():
            try:
                payload[key] = int(value)
                continue
            except ValueError:
                pass
        payload[key] = value
    return payload


class RecapContextError(RuntimeError):
    """Raised when ``resolve_recap_context`` cannot return a unique answer.

    The skill prompt instructs the model to surface the error message verbatim to
    the GM rather than trying to recover — duplicate prep docs and ambiguous
    campaigns are operator-fixable corpus-state problems, not modeling problems.
    """


@dataclass(frozen=True)
class RecapEntry:
    """One recap file resolved from the corpus, with frontmatter facts only."""

    path: str
    """Corpus-relative path (POSIX separators), e.g.
    ``Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md``."""

    session: int
    """Frontmatter ``session: N`` (the source of truth for "what session this is")."""

    title: str
    """Frontmatter ``title`` value, raw (callers may want to surface this verbatim)."""

    campaign_id: str
    """Frontmatter ``campaign_id`` (used to group recaps into campaigns)."""


@dataclass(frozen=True)
class RecapContext:
    """Canonical recap-ingest context for one campaign and one target session."""

    campaign_id: str
    campaign_hub: str
    """Corpus-relative campaign-hub folder (parent of ``Session Recaps``)."""

    session_recaps_dir: str
    session_prep_dir: str | None
    """``<hub>/Session Prep`` if it exists on disk, else ``None``."""

    npcs_dir: str | None
    """``<hub>/NPCs`` if it exists on disk, else ``None``."""

    target_session: int
    """The session number being ingested (e.g. 20 when ingesting Session 20 notes)."""

    next_session_after_target: int
    """Always ``target_session + 1``. Informational; useful when the GM is
    ingesting an out-of-order older session."""

    recent_recaps: list[RecapEntry]
    """Up to :data:`RECENT_RECAP_K` recaps with ``session < target_session``,
    sorted **descending** by ``session`` (newest first)."""

    prep_doc_path: str | None
    """Companion prep doc for ``target_session`` (corpus-relative path), or
    ``None`` if no file matches ``session_<target>_*.md`` in
    ``<hub>/Session Prep``."""

    notes: list[str] = field(default_factory=list)
    """Non-fatal observations the skill should surface to the GM (e.g. "fewer than
    K prior recaps available, only 2 returned")."""

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view used by the planner tool wire format."""
        d = asdict(self)
        d["recent_recaps"] = [asdict(r) for r in self.recent_recaps]
        return d


def _list_session_recaps_dirs(corpus_root: Path) -> list[Path]:
    """All directories named ``Session Recaps`` anywhere under ``corpus_root``.

    The corpus layout currently has at most one ``Session Recaps/`` per campaign
    hub; this function does not assume that — multi-campaign repos and future
    nested hubs are handled by the campaign-id grouping below.
    """
    return sorted(p for p in corpus_root.rglob(_RECAPS_DIR_NAME) if p.is_dir())


def _read_recap_frontmatter(md_path: Path) -> dict[str, Any] | None:
    """Permissive frontmatter parse → dict, or ``None`` for files we can't use.

    Skips files that are not recap-shaped: missing frontmatter, missing required
    keys, non-int ``session``. We deliberately do **not** schema-validate (an
    index file like ``Session Recaps (index)`` may legitimately appear in the
    folder with a different ``document_class`` and we just want to ignore it).
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    payload = _parse_minimal_frontmatter(text)
    if payload is None:
        return None
    sess_raw = payload.get("session")
    if sess_raw is None:
        return None
    try:
        payload["session"] = int(sess_raw)
    except (TypeError, ValueError):
        return None
    cid = payload.get("campaign_id")
    if cid is None or not str(cid).strip():
        return None
    payload["campaign_id"] = str(cid).strip()
    payload["title"] = str(payload.get("title", "") or "")
    return payload


def _scan_recap_entries(corpus_root: Path) -> list[tuple[Path, RecapEntry]]:
    """All recap files with parseable frontmatter, anywhere in the corpus.

    Returns ``(absolute_path, RecapEntry)`` so callers can also know which
    ``Session Recaps/`` directory the file came from (used to derive the
    campaign hub).
    """
    out: list[tuple[Path, RecapEntry]] = []
    for recaps_dir in _list_session_recaps_dirs(corpus_root):
        for md in sorted(recaps_dir.glob("*.md")):
            fm = _read_recap_frontmatter(md)
            if fm is None:
                continue
            rel = md.resolve().relative_to(corpus_root.resolve()).as_posix()
            out.append(
                (
                    md,
                    RecapEntry(
                        path=rel,
                        session=int(fm["session"]),
                        title=str(fm["title"]),
                        campaign_id=str(fm["campaign_id"]),
                    ),
                )
            )
    return out


def _campaign_hub_for_recaps_dir(corpus_root: Path, recaps_dir: Path) -> str:
    """Corpus-relative path of the campaign-hub folder (``Session Recaps``'s parent)."""
    return recaps_dir.parent.resolve().relative_to(corpus_root.resolve()).as_posix()


def _resolve_prep_doc(
    corpus_root: Path, hub_abs: Path, target_session: int
) -> tuple[str | None, str]:
    """Find the unique ``session_<target>_*.md`` (or ``session_<target>.md``).

    Returns ``(corpus_relative_path_or_None, prep_dir_corpus_relpath_or_empty)``.

    Raises :class:`RecapContextError` if more than one file matches — the project
    convention is **one prep doc per session**, and we surface the duplication as
    an operator-fixable error rather than silently picking one.
    """
    prep_dir = hub_abs / _PREP_DIR_NAME
    if not prep_dir.is_dir():
        return None, ""
    pat = re.compile(_PREP_DOC_RE_TEMPLATE.format(n=target_session))
    matches = sorted(p for p in prep_dir.iterdir() if p.is_file() and pat.match(p.name))
    rel_dir = prep_dir.resolve().relative_to(corpus_root.resolve()).as_posix()
    if not matches:
        return None, rel_dir
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise RecapContextError(
            f"Multiple prep docs match session_{target_session}_*.md in "
            f"'{rel_dir}': [{names}]. Project convention is one prep doc per "
            "session — consolidate or rename so exactly one file matches."
        )
    return matches[0].resolve().relative_to(corpus_root.resolve()).as_posix(), rel_dir


def resolve_recap_context(
    corpus_root: Path,
    *,
    campaign_id: str | None = None,
    target_session: int | None = None,
) -> RecapContext:
    """Build the canonical recap-ingest context.

    Args:
        corpus_root: Absolute path to the campaign corpus root (e.g. the directory
            that contains ``Longmont Campaign/`` and ``Elderwyld/``).
        campaign_id: Pin the active campaign (e.g. ``"longmont-c2"``). When
            ``None``, picks the campaign whose recap set has the highest
            ``session`` value. Pin explicitly when ingesting a session out of
            order (an older Campaign 1 recap while Campaign 2 is more recent).
        target_session: The session number being ingested. When ``None``, picks
            ``max(session) + 1`` for the chosen campaign — i.e. "the next
            session." Pin explicitly when re-ingesting an existing session for
            replay/regression purposes.

    Raises:
        RecapContextError: when no recaps are found, when ``campaign_id`` is set
            but no recaps for that campaign exist, or when more than one prep
            doc matches the target session.
    """
    corpus_root = corpus_root.resolve()
    if not corpus_root.is_dir():
        raise RecapContextError(f"corpus_root is not a directory: {corpus_root}")

    scanned = _scan_recap_entries(corpus_root)
    if not scanned:
        raise RecapContextError(
            f"No recap files with parseable frontmatter were found anywhere under "
            f"{corpus_root}. Expected at least one .md file in a 'Session Recaps' "
            "directory with 'session: N' and 'campaign_id: ...' frontmatter."
        )

    by_campaign: dict[str, list[tuple[Path, RecapEntry]]] = {}
    for abs_path, entry in scanned:
        by_campaign.setdefault(entry.campaign_id, []).append((abs_path, entry))

    if campaign_id is None:
        chosen_id = max(
            by_campaign.keys(),
            key=lambda cid: max(e.session for _p, e in by_campaign[cid]),
        )
    else:
        if campaign_id not in by_campaign:
            available = sorted(by_campaign.keys())
            raise RecapContextError(
                f"campaign_id={campaign_id!r} has no recaps in this corpus. "
                f"Available campaigns: {available}."
            )
        chosen_id = campaign_id

    chosen_entries = by_campaign[chosen_id]
    chosen_recaps_dir = chosen_entries[0][0].parent
    hub_abs = chosen_recaps_dir.parent
    hub_rel = _campaign_hub_for_recaps_dir(corpus_root, chosen_recaps_dir)
    recaps_dir_rel = chosen_recaps_dir.resolve().relative_to(corpus_root).as_posix()
    npcs_abs = hub_abs / _NPCS_DIR_NAME
    npcs_rel = (
        npcs_abs.resolve().relative_to(corpus_root).as_posix() if npcs_abs.is_dir() else None
    )

    sessions_present = sorted({e.session for _p, e in chosen_entries})
    if target_session is None:
        target = max(sessions_present) + 1
    else:
        target = int(target_session)

    eligible = [e for _p, e in chosen_entries if e.session < target]
    eligible.sort(key=lambda e: e.session, reverse=True)
    recent = eligible[:RECENT_RECAP_K]

    notes: list[str] = []
    if len(recent) < RECENT_RECAP_K:
        notes.append(
            f"Only {len(recent)} prior recap(s) available for {chosen_id} with "
            f"session < {target}; expected up to {RECENT_RECAP_K}."
        )
    if target in sessions_present:
        notes.append(
            f"target_session={target} already exists in {chosen_id} recaps "
            "(re-ingest / replay scenario); pre-state cleanup may be required "
            "before write_corpus_file create succeeds."
        )

    prep_path, prep_dir_rel = _resolve_prep_doc(corpus_root, hub_abs, target)
    if not prep_path and prep_dir_rel:
        notes.append(
            f"No prep doc matched session_{target}_*.md in '{prep_dir_rel}' "
            "(prep doc is optional)."
        )
    elif not prep_dir_rel:
        notes.append(
            f"Campaign hub '{hub_rel}' has no 'Session Prep/' folder "
            "(prep doc is optional)."
        )

    return RecapContext(
        campaign_id=chosen_id,
        campaign_hub=hub_rel,
        session_recaps_dir=recaps_dir_rel,
        session_prep_dir=prep_dir_rel or None,
        npcs_dir=npcs_rel,
        target_session=target,
        next_session_after_target=target + 1,
        recent_recaps=recent,
        prep_doc_path=prep_path,
        notes=notes,
    )
