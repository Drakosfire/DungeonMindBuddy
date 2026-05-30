"""Read-only C2S23 activated planning corpus manifest.

Composes the in-bounds planning sources for a campaign planning session into one
session-scoped activation object. Each source carries a ``source_role`` (what the
source *is*), an ``authority`` (what kind of truth it carries), a session scope, a
route (repo-relative path), whether that route resolves on disk, and allowed /
forbidden uses.

This module is deterministic and offline:

* It never calls the network and never constructs an OpenAI client.
* It never mutates the corpus or the live workspace. It writes only to the
  ``--out`` / ``--markdown-out`` paths passed on the CLI.
* It *references* sources by route; it never inlines corpus prose.

Retrieval, admission, ranking, and embedding are deliberately out of scope (the
manifest is the composition layer; query/admission over it is a later slice).

The closed vocabularies mirror:

* ``Docs/Plans/ROADMAP-c2s23-authority-activation-and-dogfood.md`` §"Source Role
  and Authority Axis" (the ``source_role`` axis), and
* ``Docs/Plans/BENCHMARK-c2s23-dogfood-planning-charter.md`` §"Source authority
  roles" (the 7-value ``authority`` axis).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.corpus.session_recap_paths import (
    breadcrumbed_relpath,
    campaign_number_from_id,
    normalized_basename_from_disk,
    normalized_recap_relpath,
    session_memory_jsonl_relpath,
    session_memory_meta_relpath,
    session_recaps_prefix,
)
from src.live_play.session_paths import repo_root

SCHEMA_ID = "dmb_c2s23_planning_corpus_manifest_v0"

# Closed vocab — mirror ROADMAP § "Source Role and Authority Axis".
SOURCE_ROLE = Literal[
    "table_notes",
    "play_recap",
    "session_memory",
    "prep_scaffold",
    "roll_table",
    "live_packet",
    "live_event",
    "fresh_recap",
    "hub_evidence",
]
# Closed vocab — mirror BENCHMARK charter § "Source authority roles".
AUTHORITY = Literal[
    "pre_canonical_evidence",
    "canon_play",
    "derived_memory",
    "planning_scaffold",
    "reference_tool",
    "live_observation",
    "audit",
]

SOURCE_ROLES: tuple[str, ...] = (
    "table_notes",
    "play_recap",
    "session_memory",
    "prep_scaffold",
    "roll_table",
    "live_packet",
    "live_event",
    "fresh_recap",
    "hub_evidence",
)
AUTHORITIES: tuple[str, ...] = (
    "pre_canonical_evidence",
    "canon_play",
    "derived_memory",
    "planning_scaffold",
    "reference_tool",
    "live_observation",
    "audit",
)

# role -> authority (one of the 7 charter authorities for every role).
_AUTHORITY_BY_ROLE: dict[str, str] = {
    "table_notes": "pre_canonical_evidence",
    "play_recap": "canon_play",
    "session_memory": "derived_memory",
    "prep_scaffold": "planning_scaffold",
    "roll_table": "reference_tool",
    "live_packet": "planning_scaffold",
    "live_event": "live_observation",
    "fresh_recap": "pre_canonical_evidence",
    "hub_evidence": "canon_play",
}

_ALLOWED_BY_ROLE: dict[str, list[str]] = {
    "table_notes": ["provenance", "pre_recap_evidence"],
    "play_recap": ["play_facts", "open_loops", "planning_context", "continuity"],
    "session_memory": ["play_facts", "search", "routing", "evidence_support"],
    "prep_scaffold": ["planning_context", "reusable_prep"],
    "roll_table": ["table_use", "table_patch"],
    "live_packet": ["active_session_orientation", "planning_context"],
    "live_event": ["observed_play", "planning_observation", "audit_evidence"],
    "fresh_recap": ["planning_input"],
    "hub_evidence": ["planning_context", "continuity", "npc_grounding"],
}

# Roles that may never prove a play fact (the manifest's hard authority floor).
# ``table_notes`` and ``fresh_recap`` are conditional: they only forbid play_facts
# once a materialized play_recap exists for the same session.
_FORBIDDEN_BY_ROLE: dict[str, list[str]] = {
    "table_notes": [],
    "play_recap": [],
    "session_memory": [],
    "prep_scaffold": ["play_facts"],
    "roll_table": ["play_facts"],
    "live_packet": ["play_facts"],
    "live_event": ["play_facts"],
    "fresh_recap": [],
    "hub_evidence": [],
}

PLAY_FACT_USE = "play_facts"


@dataclass(frozen=True)
class ManifestEntry:
    source_id: str
    source_role: SOURCE_ROLE
    authority: AUTHORITY
    session_scope: list[int]
    route: str
    route_exists: bool
    admissible: bool
    allowed_uses: list[str]
    forbidden_uses: list[str]
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_role": self.source_role,
            "authority": self.authority,
            "session_scope": list(self.session_scope),
            "route": self.route,
            "route_exists": self.route_exists,
            "admissible": self.admissible,
            "allowed_uses": list(self.allowed_uses),
            "forbidden_uses": list(self.forbidden_uses),
            "notes": self.notes,
        }


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "x"


def _make_source_id(role: str, session_scope: list[int], route: str) -> str:
    p = Path(route)
    disc = _slug(f"{p.parent.name}-{p.name}")
    return f"{role}-s{min(session_scope)}-{disc}"


def _relativize(abs_path: Path, repo: Path, fallback: Path) -> str:
    """Return ``abs_path`` relative to the repo root when possible.

    Falls back to a path relative to ``fallback`` (e.g. a tmp corpus root used in
    tests that lives outside the repo), then to the absolute path.
    """
    for base in (repo, fallback):
        try:
            return abs_path.relative_to(base).as_posix()
        except ValueError:
            continue
    return abs_path.as_posix()


def _route_and_exists(abs_path: Path, *, repo: Path, fallback: Path) -> tuple[str, bool]:
    resolved = abs_path.resolve()
    return _relativize(resolved, repo, fallback), abs_path.is_file()


def _matched_session(name: str, sessions: list[int]) -> int | None:
    for n in sessions:
        if re.search(rf"(?i)session[ _]0*{n}(?![0-9])", name):
            return n
    return None


def _campaign_dir_relpath(campaign_number: int) -> str:
    return f"Longmont Campaign/Campaign {campaign_number}"


def _staging_notes_relpath(campaign_number: int, session: int) -> str:
    return f"{_campaign_dir_relpath(campaign_number)}/_ingest_staging/session_{session}_raw_notes.md"


def _recap_derivative_routes(
    corpus_root: Path,
    campaign_number: int,
    session: int,
) -> dict[str, str]:
    """Corpus-relative routes for the recap derivatives of one session.

    Uses the canonical ``session_recap_paths`` helpers when the session has been
    ingested (a single normalized recap resolves on disk). When the session is not
    yet ingested, falls back to a deterministic ``(uningested)`` basename so the
    manifest still emits honest ``route_exists: false`` rows instead of dropping
    the source.
    """
    prefix = session_recaps_prefix(campaign_number)
    try:
        base = normalized_basename_from_disk(
            corpus_root, campaign_number=campaign_number, session=session
        )
        normalized = normalized_recap_relpath(
            campaign_number=campaign_number, session=session, corpus_root=corpus_root
        )
        breadcrumbed = breadcrumbed_relpath(
            campaign_number=campaign_number, session=session, corpus_root=corpus_root
        )
        sm_jsonl = session_memory_jsonl_relpath(
            campaign_number=campaign_number, session=session, corpus_root=corpus_root
        )
        sm_json = session_memory_meta_relpath(
            campaign_number=campaign_number, session=session, corpus_root=corpus_root
        )
    except FileNotFoundError:
        base = f"Session {session:02d} - (uningested)"
        normalized = f"{prefix}/_normalized/{base}.md"
        breadcrumbed = f"{prefix}/_breadcrumbed/{base}.breadcrumbed.md"
        sm_jsonl = f"{prefix}/_session_memory/{base}.records_meta.jsonl"
        sm_json = f"{prefix}/_session_memory/{base}.records_meta.json"
    return {
        "play_recap": f"{prefix}/{base}.md",
        "normalized": normalized,
        "breadcrumbed": breadcrumbed,
        "session_memory_jsonl": sm_jsonl,
        "session_memory_json": sm_json,
    }


def _build_entry(
    role: str,
    session_scope: list[int],
    route: str,
    route_exists: bool,
    *,
    notes: str | None,
    forbid_play_facts: bool = False,
) -> ManifestEntry:
    scope = sorted(set(session_scope))
    forbidden = list(_FORBIDDEN_BY_ROLE[role])
    if forbid_play_facts and PLAY_FACT_USE not in forbidden:
        forbidden.append(PLAY_FACT_USE)
    # Non-materialized routes must not advertise allowed uses (especially play_facts).
    admissible = route_exists
    allowed = list(_ALLOWED_BY_ROLE[role]) if admissible else []
    if not admissible and PLAY_FACT_USE not in forbidden:
        forbidden.append(PLAY_FACT_USE)
    return ManifestEntry(
        source_id=_make_source_id(role, scope, route),
        source_role=role,  # type: ignore[arg-type]
        authority=_AUTHORITY_BY_ROLE[role],  # type: ignore[arg-type]
        session_scope=scope,
        route=route,
        route_exists=route_exists,
        admissible=admissible,
        allowed_uses=allowed,
        forbidden_uses=forbidden,
        notes=notes,
    )


def _resolve_live_workspace_session(
    live_workspace_dir: Path,
    *,
    planning_session: int,
    allow_session_mismatch: bool,
) -> int:
    packet_path = live_workspace_dir / "live_packet.json"
    if not packet_path.is_file():
        return int(planning_session)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_session = int(packet.get("session", planning_session))
    if packet_session != planning_session and not allow_session_mismatch:
        raise ValueError(
            f"live_packet.session ({packet_session}) does not match planning_session "
            f"({planning_session}) for workspace {live_workspace_dir}; bootstrap a "
            f"session_{planning_session} workspace or pass allow_live_workspace_session_mismatch=True"
        )
    return packet_session


def _live_workspace_relpath(live_workspace_dir: Path, repo: Path) -> str:
    return _relativize(live_workspace_dir.resolve(), repo, live_workspace_dir)


def build_planning_corpus_manifest(
    *,
    campaign_id: str,
    planning_session: int,
    source_sessions: list[int],
    corpus_root: Path,
    live_workspace_dir: Path | None,
    allow_live_workspace_session_mismatch: bool = False,
) -> dict[str, Any]:
    """Compose in-bounds planning sources into the manifest dict.

    Pure and deterministic. Never raises on a missing source file (those are
    recorded with ``route_exists: false`` and ``admissible: false``); raises
    ``ValueError`` on bad inputs (unknown ``campaign_id``, empty
    ``source_sessions``, or ``live_packet.session`` ≠ ``planning_session`` when
    a live workspace is supplied without ``allow_live_workspace_session_mismatch``).
    """
    campaign_number = campaign_number_from_id(campaign_id)
    if not source_sessions:
        raise ValueError("source_sessions must not be empty")

    repo = repo_root()
    corpus_root = Path(corpus_root)
    lwd = Path(live_workspace_dir) if live_workspace_dir is not None else None
    src_sessions = sorted(set(int(s) for s in source_sessions))
    window = sorted(set(src_sessions) | {int(planning_session)})

    entries: list[ManifestEntry] = []
    materialized_recap_sessions: set[int] = set()

    # 1) Recap derivatives per source session (play_recap + session_memory).
    for session in src_sessions:
        routes = _recap_derivative_routes(corpus_root, campaign_number, session)
        for key, role, note in (
            ("play_recap", "play_recap", "Played recap of what happened; canonical play memory."),
            ("normalized", "play_recap", "Normalized recap; canonical play memory."),
            ("breadcrumbed", "play_recap", "Breadcrumbed (route-anchored) recap; canonical play memory."),
            ("session_memory_jsonl", "session_memory", "Retrieval records derived from the recap."),
            ("session_memory_json", "session_memory", "Retrieval-record metadata derived from the recap."),
        ):
            route, exists = _route_and_exists(
                corpus_root / routes[key], repo=repo, fallback=corpus_root
            )
            entry_note = note if exists else f"{note} Not yet materialized (session not ingested)."
            entries.append(_build_entry(role, [session], route, exists, notes=entry_note))
            if role == "play_recap" and exists:
                materialized_recap_sessions.add(session)

    # 2) Staged table notes per source session (only when present on disk).
    for session in src_sessions:
        rel = _staging_notes_relpath(campaign_number, session)
        route, exists = _route_and_exists(
            corpus_root / rel, repo=repo, fallback=corpus_root
        )
        if not exists:
            continue
        recap_exists = session in materialized_recap_sessions
        note = (
            "Pre-canonical table notes; provenance only now that the recap exists."
            if recap_exists
            else "Pre-canonical table notes; current evidence until a recap is written."
        )
        entries.append(
            _build_entry(
                "table_notes",
                [session],
                route,
                exists,
                notes=note,
                forbid_play_facts=recap_exists,
            )
        )

    planning_live_workspace_dir: str | None = None

    # 3) Live workspace: roll tables (from the packet), the packet, and event log.
    roll_routes: set[str] = set()
    if lwd is not None:
        packet_session = _resolve_live_workspace_session(
            lwd,
            planning_session=int(planning_session),
            allow_session_mismatch=allow_live_workspace_session_mismatch,
        )
        planning_live_workspace_dir = _live_workspace_relpath(lwd, repo)
        packet_path = lwd / "live_packet.json"
        if packet_path.is_file():
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            for table in packet.get("known_roll_tables", []):
                source_path = table.get("source_path")
                if not source_path:
                    continue
                route, exists = _route_and_exists(
                    repo / source_path, repo=repo, fallback=repo
                )
                roll_routes.add(route)
                title = table.get("title") or table.get("table_id") or "roll table"
                entries.append(
                    _build_entry(
                        "roll_table",
                        [int(planning_session)],
                        route,
                        exists,
                        notes=f"Prep roll table ({title}); a tool, not a played fact.",
                    )
                )
        route, exists = _route_and_exists(packet_path, repo=repo, fallback=lwd)
        entries.append(
            _build_entry(
                "live_packet",
                [int(planning_session)],
                route,
                exists,
                notes=(
                    f"Active live-control packet for Session {planning_session} planning "
                    f"workspace."
                ),
            )
        )
        event_log = lwd / "event_log.jsonl"
        route, exists = _route_and_exists(event_log, repo=repo, fallback=lwd)
        entries.append(
            _build_entry(
                "live_event",
                [int(planning_session)],
                route,
                exists,
                notes="Live event log; observations appended during play, not retroactive canon.",
            )
        )
        recap_md = lwd / "recap.md"
        if recap_md.is_file():
            route, exists = _route_and_exists(recap_md, repo=repo, fallback=lwd)
            entries.append(
                _build_entry(
                    "fresh_recap",
                    [int(planning_session)],
                    route,
                    exists,
                    notes="Fresh recap bootstrapped into the workspace; planning input until ingested.",
                    forbid_play_facts=int(planning_session) in materialized_recap_sessions,
                )
            )

    # 4) Prep scaffold: session-tagged top-level prep docs + per-session prep dirs.
    prep_dir = corpus_root / f"{_campaign_dir_relpath(campaign_number)}/Session Prep"
    if prep_dir.is_dir():
        for path in sorted(prep_dir.glob("*.md")):
            matched = _matched_session(path.name, window)
            if matched is None:
                continue
            route, exists = _route_and_exists(path, repo=repo, fallback=corpus_root)
            entries.append(
                _build_entry(
                    "prep_scaffold",
                    [matched],
                    route,
                    exists,
                    notes="GM prep scaffold; planning intent, not a played fact.",
                )
            )
        for session in window:
            sub = prep_dir / f"session_{session}"
            if not sub.is_dir():
                continue
            for path in sorted(sub.glob("*.md")):
                if path.name == "README.md":
                    continue
                route, exists = _route_and_exists(path, repo=repo, fallback=corpus_root)
                if route in roll_routes:
                    continue
                entries.append(
                    _build_entry(
                        "prep_scaffold",
                        [session],
                        route,
                        exists,
                        notes="GM prep scaffold; planning intent, not a played fact.",
                    )
                )

    # 5) Hub evidence: campaign hub READMEs (excluding Session Prep READMEs).
    campaign_dir = corpus_root / _campaign_dir_relpath(campaign_number)
    if campaign_dir.is_dir():
        for readme in sorted(campaign_dir.glob("**/README.md")):
            rel_parts = readme.relative_to(corpus_root).parts
            if "Session Prep" in rel_parts:
                continue
            route, exists = _route_and_exists(readme, repo=repo, fallback=corpus_root)
            entries.append(
                _build_entry(
                    "hub_evidence",
                    window,
                    route,
                    exists,
                    notes="Campaign hub index; canonical reference for continuity and grounding.",
                )
            )

    entries.sort(key=lambda e: (e.source_role, min(e.session_scope), e.source_id))

    seen: set[str] = set()
    for entry in entries:
        if entry.source_id in seen:
            raise ValueError(f"duplicate source_id: {entry.source_id}")
        seen.add(entry.source_id)

    payload: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "campaign_id": campaign_id,
        "planning_session": int(planning_session),
        "source_sessions": src_sessions,
        "generated_at": _now_utc(),
        "entries": [entry.to_dict() for entry in entries],
    }
    if planning_live_workspace_dir is not None:
        payload["planning_live_workspace_dir"] = planning_live_workspace_dir
    return payload


def render_manifest_markdown(manifest: dict[str, Any]) -> str:
    """Deterministic GM-readable mirror grouped by source_role then session."""
    lines: list[str] = []
    lines.append(f"# Activated planning corpus manifest — {manifest['campaign_id']}")
    lines.append("")
    lines.append(f"- **schema:** `{manifest['schema']}`")
    lines.append(f"- **planning_session:** {manifest['planning_session']}")
    lines.append(
        f"- **source_sessions:** {', '.join(str(s) for s in manifest['source_sessions'])}"
    )
    lines.append(f"- **entries:** {len(manifest['entries'])}")
    if manifest.get("planning_live_workspace_dir"):
        lines.append(
            f"- **planning_live_workspace_dir:** `{manifest['planning_live_workspace_dir']}`"
        )
    lines.append("")
    lines.append(
        "Routes are repo-relative references; this manifest inlines no corpus prose. "
        "`route_exists: false` / `admissible: false` marks an in-bounds source that is "
        "not yet materialized and must not be used for admission."
    )
    lines.append("")

    by_role: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest["entries"]:
        by_role.setdefault(entry["source_role"], []).append(entry)

    for role in SOURCE_ROLES:
        rows = by_role.get(role)
        if not rows:
            continue
        authority = rows[0]["authority"]
        lines.append(f"## {role} — authority: {authority}")
        lines.append("")
        lines.append("| Session | Route | Exists | Admissible | Allowed | Forbidden |")
        lines.append("|---|---|---|---|---|---|")
        for entry in sorted(rows, key=lambda e: (min(e["session_scope"]), e["source_id"])):
            scope = ", ".join(str(s) for s in entry["session_scope"])
            exists = "yes" if entry["route_exists"] else "no"
            admissible = "yes" if entry["admissible"] else "no"
            allowed = ", ".join(entry["allowed_uses"]) or "—"
            forbidden = ", ".join(entry["forbidden_uses"]) or "—"
            lines.append(
                f"| {scope} | `{entry['route']}` | {exists} | {admissible} | {allowed} | {forbidden} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only, session-scoped activated planning corpus manifest "
            "(source_role + authority + session scope + routes + allowed/forbidden uses)."
        ),
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--planning-session", type=int, required=True)
    parser.add_argument("--source-sessions", type=int, nargs="+", required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--live-workspace-dir", type=Path, default=None)
    parser.add_argument(
        "--allow-live-workspace-session-mismatch",
        action="store_true",
        help=(
            "Allow live_packet.session to differ from --planning-session (escape hatch "
            "for dogfood only; default is to fail fast)."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write the canonical JSON manifest here. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        default=None,
        help="Optional GM-readable markdown mirror.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        manifest = build_planning_corpus_manifest(
            campaign_id=args.campaign_id,
            planning_session=args.planning_session,
            source_sessions=args.source_sessions,
            corpus_root=args.corpus_root,
            live_workspace_dir=args.live_workspace_dir,
            allow_live_workspace_session_mismatch=args.allow_live_workspace_session_mismatch,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 2

    if args.out is not None:
        _write_json(args.out, manifest)
        print(f"wrote manifest: {args.out} ({len(manifest['entries'])} entries)", flush=True)
    else:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))

    if args.markdown_out is not None:
        markdown = render_manifest_markdown(manifest)
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
        print(f"wrote markdown mirror: {args.markdown_out}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
