#!/usr/bin/env python3
"""Stage 4J Campaign 2 DeepSeek graph rehearsal batch runner.

Experimental notebook tooling — not production defaults. Refuses live Eldyrwild
World authority (:54330 / dungeonmind_cutover_live) unless explicitly overridden.

Usage (from repo root):
  uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py census
  uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py extract --sessions 1,2,3
  uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py promote --dry-run
  uv run python tools/stage4j_c2_deepseek_graph_rehearsal.py dogfood
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.corpus.session_recap_paths import (
    campaign_id_from_number,
    normalized_recap_candidates,
    normalized_recap_relpath,
)
from src.graph_memory.extraction.deepseek_category_graph_pass_client import (
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekCategoryGraphPassClient,
)
from src.graph_memory.extraction.stage4j_rehearsal_guards import (
    Stage4JRehearsalGuardError,
    assert_rehearsal_world_db_url,
    rehearsal_world_database_url,
)

CAMPAIGN_NUMBER = 2
DEFAULT_SESSION_START = 1
DEFAULT_SESSION_END = 27
OUT_REL = "out/stage4j_c2_deepseek_graph_rehearsal"
CORPUS_ROOT = REPO_ROOT / "corpus" / "eldyrwild-markdown"
DEFAULT_WORLD_ID = "eldyrwild"
CATEGORY_PASSES_PER_SESSION = 7  # 5 node + beat + edge (+ claimed_fill conditional)
PREPARED_BY = "stage4j-c2-deepseek-graph-rehearsal"
CONFIRMING_PRINCIPAL = "stage4j-c2-deepseek-graph-rehearsal"


@dataclass(frozen=True)
class SessionRecapRef:
    session: int
    relpath: str | None
    exists: bool


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_stage4j_dotenv() -> None:
    """Load repo env without clobbering an operator-set rehearsal World DSN."""
    preserved = {
        key: os.environ[key]
        for key in (
            "DUNGEONMIND_WORLD_GRAPH_AUTHORITY",
            "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        )
        if os.environ.get(key, "").strip()
    }
    load_dungeonmindbuddy_dotenv()
    for key, value in preserved.items():
        os.environ[key] = value


def _output_root(custom: Path | None = None) -> Path:
    return (custom or (REPO_ROOT / OUT_REL)).resolve()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_sessions(
    *,
    sessions: str | None,
    session_start: int,
    session_end: int,
) -> list[int]:
    if sessions:
        out: list[int] = []
        for part in sessions.split(","):
            part = part.strip()
            if not part:
                continue
            out.append(int(part))
        return sorted(set(out))
    return list(range(session_start, session_end + 1))


def _session_refs(sessions: Sequence[int]) -> list[SessionRecapRef]:
    refs: list[SessionRecapRef] = []
    for session in sessions:
        candidates = normalized_recap_candidates(
            CORPUS_ROOT, campaign_number=CAMPAIGN_NUMBER, session=session
        )
        if candidates:
            rel = candidates[0].relative_to(REPO_ROOT).as_posix()
            refs.append(SessionRecapRef(session=session, relpath=rel, exists=True))
            continue
        try:
            rel = normalized_recap_relpath(
                campaign_number=CAMPAIGN_NUMBER,
                session=session,
                corpus_root=CORPUS_ROOT,
            )
            full = REPO_ROOT / "corpus" / "eldyrwild-markdown" / rel
            refs.append(
                SessionRecapRef(
                    session=session,
                    relpath=f"corpus/eldyrwild-markdown/{rel}",
                    exists=full.is_file(),
                )
            )
        except FileNotFoundError:
            refs.append(SessionRecapRef(session=session, relpath=None, exists=False))
    return refs


def cmd_census(args: argparse.Namespace) -> int:
    sessions = _parse_sessions(
        sessions=args.sessions,
        session_start=args.session_start,
        session_end=args.session_end,
    )
    refs = _session_refs(sessions)
    present = [r for r in refs if r.exists]
    missing = [r for r in refs if not r.exists]
    estimated_requests = len(present) * CATEGORY_PASSES_PER_SESSION

    payload = {
        "schema": "dmb_stage4j_c2_census_v0",
        "generated_at": _utc_now(),
        "campaign_number": CAMPAIGN_NUMBER,
        "campaign_id": campaign_id_from_number(CAMPAIGN_NUMBER),
        "session_range": [min(sessions), max(sessions)],
        "present_count": len(present),
        "missing_count": len(missing),
        "estimated_category_pass_requests": estimated_requests,
        "category_passes_per_session_estimate": CATEGORY_PASSES_PER_SESSION,
        "present": [{"session": r.session, "relpath": r.relpath} for r in present],
        "missing": [{"session": r.session, "relpath": r.relpath} for r in missing],
        "dry_run": bool(args.dry_run),
    }
    out_root = _output_root(Path(args.output) if args.output else None)
    census_path = out_root / "census.json"
    if not args.dry_run:
        _write_json(census_path, payload)

    print(f"C2 normalized recap census: {len(present)} present, {len(missing)} missing")
    for r in missing:
        print(f"  missing session {r.session:02d}")
    print(
        f"Estimated category-pass requests (if all present): {estimated_requests} "
        f"({CATEGORY_PASSES_PER_SESSION} passes × {len(present)} sessions)"
    )
    if not args.dry_run:
        print(f"Wrote {census_path}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    _load_stage4j_dotenv()
    sessions = _parse_sessions(
        sessions=args.sessions,
        session_start=args.session_start,
        session_end=args.session_end,
    )
    refs = [r for r in _session_refs(sessions) if r.exists]
    if not refs:
        print("No normalized recaps found for requested sessions.", file=sys.stderr)
        return 1

    out_root = _output_root(Path(args.output) if args.output else None)
    client = DeepSeekCategoryGraphPassClient(model_id=args.model_id or DEFAULT_DEEPSEEK_MODEL)
    campaign_id = campaign_id_from_number(CAMPAIGN_NUMBER)

    from apps.live_control_server.services.graph_preview_runner import (
        run_recap_production_extraction,
    )

    exit_code = 0
    for ref in refs:
        session_dir = out_root / f"session_{ref.session:02d}"
        receipt_path = out_root / "receipts" / f"session_{ref.session:02d}.json"
        recap_path = REPO_ROOT / ref.relpath  # type: ignore[arg-type]
        session_id = f"session-{ref.session}"

        if args.dry_run:
            receipt = {
                "schema": "dmb_stage4j_c2_extract_receipt_v0",
                "session": ref.session,
                "session_id": session_id,
                "relpath": ref.relpath,
                "dry_run": True,
                "model_id": args.model_id or DEFAULT_DEEPSEEK_MODEL,
            }
            print(f"[dry-run] would extract {session_id} from {ref.relpath}")
            if not args.no_write:
                _write_json(receipt_path, receipt)
            continue

        print(f"Extracting {session_id} …")
        try:
            result = run_recap_production_extraction(
                repo_root=REPO_ROOT,
                campaign_id=campaign_id,
                session_id=session_id,
                recap_path=recap_path,
                model_id=args.model_id or DEFAULT_DEEPSEEK_MODEL,
                allow_llm=True,
                category_client=client,
                output_dir=session_dir,
            )
        except Exception as exc:  # noqa: BLE001 — record per-session failure
            receipt = {
                "schema": "dmb_stage4j_c2_extract_receipt_v0",
                "session": ref.session,
                "session_id": session_id,
                "relpath": ref.relpath,
                "ok": False,
                "failure_kind": "exception",
                "error": str(exc),
                "generated_at": _utc_now(),
            }
            _write_json(receipt_path, receipt)
            print(f"  FAILED: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        ok = result.failure_kind is None and result.candidate_graph is not None
        candidate_path = _resolve_candidate_graph_path(
            session_dir, run_id=result.run.run_id
        )
        if ok and candidate_path is not None:
            canonical = session_dir / "candidate_graph.json"
            if candidate_path != canonical:
                canonical.write_text(
                    candidate_path.read_text(encoding="utf-8"), encoding="utf-8"
                )
        receipt = {
            "schema": "dmb_stage4j_c2_extract_receipt_v0",
            "session": ref.session,
            "session_id": session_id,
            "relpath": ref.relpath,
            "ok": ok,
            "failure_kind": result.failure_kind,
            "run_id": result.run.run_id,
            "run_status": str(result.run.status),
            "model_id": result.model_id,
            "diagnostics": list(result.diagnostics or []),
            "output_dir": str(session_dir.relative_to(REPO_ROOT)),
            "candidate_graph_path": (
                str(candidate_path.relative_to(REPO_ROOT))
                if candidate_path is not None
                else None
            ),
            "generated_at": _utc_now(),
        }
        _write_json(receipt_path, receipt)
        if ok:
            print(f"  OK run_id={result.run.run_id}")
        else:
            print(f"  FAILED kind={result.failure_kind}", file=sys.stderr)
            exit_code = 1

    if not args.skip_promote:
        print("Note: run `promote` separately (or omit --skip-promote is extract-only by default).")
    return exit_code


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_candidate_graph_path(
    session_dir: Path,
    *,
    run_id: str | None = None,
) -> Path | None:
    """Locate candidate_graph.json under a session output dir (flat or run-scoped)."""
    direct = session_dir / "candidate_graph.json"
    if direct.is_file():
        return direct
    if run_id:
        nested = session_dir / run_id / "candidate_graph.json"
        if nested.is_file():
            return nested
    for nested in sorted(session_dir.glob("*/candidate_graph.json")):
        if nested.is_file():
            return nested
    return None


def _select_all_selectable(review_items: Sequence[dict[str, Any]]) -> list[str]:
    selected: list[str] = []
    for item in review_items:
        if not isinstance(item, Mapping):
            continue
        if not item.get("selectable"):
            continue
        sqid = str(item.get("slice_qualified_id") or "").strip()
        if sqid:
            selected.append(sqid)
    return selected


def _select_non_edge_selectable(review_items: Sequence[dict[str, Any]]) -> list[str]:
    """Experiment fallback when edge qualification blocks select-all confirm."""
    non_edge_kinds = {"edge", "relationship"}
    selected: list[str] = []
    for item in review_items:
        if not isinstance(item, Mapping):
            continue
        if not item.get("selectable"):
            continue
        if str(item.get("kind") or "").strip().lower() in non_edge_kinds:
            continue
        sqid = str(item.get("slice_qualified_id") or "").strip()
        if sqid:
            selected.append(sqid)
    return selected


def _edge_inexpressible_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    markers = (
        "edge endpoint kinds are not admitted",
        "edge predicate has no dungeonmind mapping",
        "node kind has no dungeonmind mapping",
        "governed_write_inexpressible",
    )
    return any(marker in message for marker in markers)


def cmd_promote(args: argparse.Namespace) -> int:
    _load_stage4j_dotenv()
    try:
        database_url = rehearsal_world_database_url()
    except Stage4JRehearsalGuardError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    sessions = _parse_sessions(
        sessions=args.sessions,
        session_start=args.session_start,
        session_end=args.session_end,
    )
    out_root = _output_root(Path(args.output) if args.output else None)
    receipts_dir = out_root / "receipts"

    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from graph_memory.extract_promote_ops import prepare_extract_promote

    exit_code = 0
    for session in sessions:
        receipt_path = receipts_dir / f"session_{session:02d}.json"
        extract_receipt: dict[str, Any] = {}
        if receipt_path.is_file():
            extract_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not extract_receipt.get("ok"):
            print(f"Skipping session {session:02d}: no successful extract receipt")
            continue

        session_dir = out_root / f"session_{session:02d}"
        receipt_candidate = str(extract_receipt.get("candidate_graph_path") or "").strip()
        candidate_path = (
            (REPO_ROOT / receipt_candidate).resolve()
            if receipt_candidate
            else None
        )
        if candidate_path is None or not candidate_path.is_file():
            candidate_path = _resolve_candidate_graph_path(
                session_dir,
                run_id=str(extract_receipt.get("run_id") or "") or None,
            )
        if candidate_path is None or not candidate_path.is_file():
            print(
                f"Skipping session {session:02d}: missing candidate_graph under {session_dir}",
                file=sys.stderr,
            )
            exit_code = 1
            continue

        relpath = str(extract_receipt.get("relpath") or "")
        source_path = REPO_ROOT / relpath
        source_uri = f"repo://{relpath}"
        source_revision_id = f"sha256:{_sha256_file(source_path)}"
        candidate_graph = json.loads(candidate_path.read_text(encoding="utf-8"))

        if args.dry_run:
            print(
                f"[dry-run] would prepare+confirm session {session:02d} "
                f"against rehearsal DB ({database_url.split('@')[-1]})"
            )
            continue

        try:
            mutation_context = world_graph_writes.load_production_mutation_context(
                DEFAULT_WORLD_ID,
                database_url=database_url,
            )
            prepare_result = prepare_extract_promote(
                candidate_graph=candidate_graph,
                source_uri=source_uri,
                source_revision_id=source_revision_id,
                prepared_by=PREPARED_BY,
                world_id=DEFAULT_WORLD_ID,
                campaign_scope=campaign_id_from_number(CAMPAIGN_NUMBER),
                candidate_graph_path=str(candidate_path.relative_to(REPO_ROOT)),
                repo_root=REPO_ROOT,
                mutation_context=mutation_context,
            )
            sealed = world_graph_writes.bind_identity_ledger_to_package(
                prepare_result.review_package,
                mutation_context,
            )
            selected = _select_all_selectable(prepare_result.review_items)
            if not selected:
                raise RuntimeError("prepare returned no selectable review_items")

            promote_mode = "select_all"
            confirm_request = type(
                "ConfirmRequest",
                (),
                {
                    "review_package": sealed,
                    "assertion_ids": selected,
                },
            )()
            try:
                confirm_payload = world_graph_writes.confirm_extract_promote_via_dungeonmind(
                    confirm_request,
                    database_url=database_url,
                    confirming_principal=CONFIRMING_PRINCIPAL,
                    assertion_ids=tuple(selected),
                    repo_root=REPO_ROOT,
                )
            except Exception as confirm_exc:
                if not _edge_inexpressible_error(confirm_exc):
                    raise
                fallback = _select_non_edge_selectable(prepare_result.review_items)
                if not fallback:
                    raise
                promote_mode = "non_edge_fallback"
                selected = fallback
                confirm_request = type(
                    "ConfirmRequest",
                    (),
                    {
                        "review_package": sealed,
                        "assertion_ids": selected,
                    },
                )()
                confirm_payload = world_graph_writes.confirm_extract_promote_via_dungeonmind(
                    confirm_request,
                    database_url=database_url,
                    confirming_principal=CONFIRMING_PRINCIPAL,
                    assertion_ids=tuple(selected),
                    repo_root=REPO_ROOT,
                )
        except Exception as exc:  # noqa: BLE001 — per-session promote failure
            promote_receipt = {
                **extract_receipt,
                "promote_ok": False,
                "promote_error": str(exc),
                "promote_generated_at": _utc_now(),
                "experiment_auto_confirm": True,
                "non_production": True,
            }
            _write_json(receipt_path, promote_receipt)
            print(f"Promote FAILED session {session:02d}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        promote_receipt = {
            **extract_receipt,
            "promote_ok": True,
            "proposal_id": prepare_result.proposal_id,
            "proposal_digest": prepare_result.proposal_digest,
            "parent_revision_id": prepare_result.parent_revision_id,
            "selected_assertion_count": len(selected),
            "promote_mode": promote_mode,
            "confirm_outcome": confirm_payload.get("outcome"),
            "committed_revision_id": confirm_payload.get("committed_revision_id"),
            "promote_generated_at": _utc_now(),
            "experiment_auto_confirm": True,
            "non_production": True,
        }
        _write_json(receipt_path, promote_receipt)
        _write_json(session_dir / "review_package.json", sealed)
        print(
            f"Promoted session {session:02d}: "
            f"revision={confirm_payload.get('committed_revision_id')} "
            f"selected={len(selected)} mode={promote_mode}"
        )
    return exit_code


def cmd_dogfood(args: argparse.Namespace) -> int:
    _load_stage4j_dotenv()
    out_root = _output_root(Path(args.output) if args.output else None)
    template_path = out_root / "session_28_dogfood_checklist.md"

    checklist = """# Session 28 dogfood checklist (Stage 4J)

Forcing question: **Would I prep Session 28 from this graph, or reopen twenty-seven recaps?**

## Preconditions
- Rehearsal World head published via `promote` (not live Eldyrwild :54330)
- `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` points at rehearsal DB

## Query checklist
1. Who is traveling with the party at the end of Session 27?
2. What unresolved threads carry into Session 28 from Mireward / Lysandro arcs?
3. Which locations are currently reachable vs blocked?
4. What objects or clues does the party still possess?
5. Which NPC identities might fragment (same person, multiple node ids)?
6. What beats from Sessions 25–27 must be preserved for table continuity?

## Retrieval probe (when live server available)
```bash
curl -sS -X POST http://127.0.0.1:8765/api/live/world-graph/retrieval/search \\
  -H 'Content-Type: application/json' \\
  -d '{"schema":"dmb_world_graph_search_request_v1","world_id":"eldyrwild","campaign_id":"longmont-c2","query_text":"Session 28 prep: party companions and unresolved Mireward threads"}'
```

Record: answer quality, missing continuity, identity fragmentation, table-usable object detail.
Verdict: GRAPH / REOPEN RECAPS / MIXED
"""
    if not args.dry_run:
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(checklist, encoding="utf-8")

    print(checklist)
    if not args.dry_run:
        print(f"\nWrote template: {template_path}")

    try:
        database_url = rehearsal_world_database_url()
    except Stage4JRehearsalGuardError:
        print("\nRehearsal DB not configured — retrieval probe skipped.", file=sys.stderr)
        return 0

    try:
        import os

        os.environ["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"] = database_url
        from apps.live_control_server.services.world_graph_retrieval import (
            search_campaign_graph,
        )
        from graph_memory.retrieval.models import (
            RETRIEVAL_SEARCH_REQUEST_SCHEMA,
            WorldGraphSearchRequest,
        )

        request = WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "worldId": DEFAULT_WORLD_ID,
                "campaignId": campaign_id_from_number(CAMPAIGN_NUMBER),
                "queryText": (
                    "Session 28 prep: party companions and unresolved Mireward threads"
                ),
            }
        )
        if args.dry_run:
            print("[dry-run] would run world-graph retrieval search against rehearsal DB")
        else:
            result = search_campaign_graph(request)
            probe_path = out_root / "session_28_retrieval_probe.json"
            _write_json(
                probe_path,
                result.model_dump(mode="json", by_alias=True),
            )
            print(f"Wrote retrieval probe: {probe_path}")
    except Exception as exc:  # noqa: BLE001 — optional probe
        print(f"\nRetrieval probe unavailable: {exc}", file=sys.stderr)
    return 0


def _add_common_cli_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Plan without paid LLM or writes")
    parser.add_argument("--output", type=str, default=None, help=f"Output root (default: {OUT_REL})")
    parser.add_argument("--sessions", type=str, default=None, help="Comma-separated session numbers")
    parser.add_argument("--session-start", type=int, default=DEFAULT_SESSION_START)
    parser.add_argument("--session-end", type=int, default=DEFAULT_SESSION_END)
    parser.add_argument(
        "--model-id",
        type=str,
        default=None,
        help=f"OpenRouter model (default: {DEFAULT_DEEPSEEK_MODEL})",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _add_common_cli_args(parser)

    common = argparse.ArgumentParser(add_help=False)
    _add_common_cli_args(common)

    sub = parser.add_subparsers(dest="command", required=True)

    census = sub.add_parser(
        "census",
        parents=[common],
        help="List normalized recap availability and estimate pass volume",
    )
    census.set_defaults(func=cmd_census)

    extract = sub.add_parser(
        "extract",
        parents=[common],
        help="Run production category extraction with DeepSeek client",
    )
    extract.add_argument("--skip-promote", action="store_true")
    extract.add_argument("--no-write", action="store_true", help="Dry-run receipt writes")
    extract.set_defaults(func=cmd_extract)

    promote = sub.add_parser(
        "promote",
        parents=[common],
        help="Prepare + experiment auto-confirm into rehearsal World",
    )
    promote.set_defaults(func=cmd_promote)

    dogfood = sub.add_parser(
        "dogfood",
        parents=[common],
        help="Session 28 query checklist + optional retrieval probe",
    )
    dogfood.set_defaults(func=cmd_dogfood)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _load_stage4j_dotenv()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    guard_url = os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "")
    if args.command in {"promote", "dogfood"} and guard_url.strip():
        try:
            assert_rehearsal_world_db_url(guard_url)
        except Stage4JRehearsalGuardError as exc:
            if args.command == "promote":
                print(str(exc), file=sys.stderr)
                return 1
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
