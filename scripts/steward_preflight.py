#!/usr/bin/env python3
"""Read-only process preflight for DungeonMindBuddy steward lanes.

The command reconciles mechanical facts before dispatch/review:

- candidate HANDOFF §4 write lease + declared base/branch/runtime ownership;
- active top-level HANDOFF write leases;
- local Git main/head/worktrees;
- optional open GitHub PR changed paths;
- optional explicitly-labelled Review Cycle judgments for one PR.

It deliberately does not create branches/worktrees, edit handoffs, transfer leases,
post reviews, merge PRs, or decide whether a capability should be split.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

try:  # Executed as ``python scripts/steward_preflight.py``.
    from review_external_pr import extract_allowlist_paths, parse_handoff
except ModuleNotFoundError:  # Imported as ``scripts.steward_preflight`` in tests.
    from scripts.review_external_pr import extract_allowlist_paths, parse_handoff

_STATUS_ACTIVE_RE = re.compile(r"^\*\*Status:\*\*\s*ACTIVE\b", re.MULTILINE | re.IGNORECASE)
_BASE_RE = re.compile(
    r"^\*\*Base revision:\*\*\s*`?([0-9a-fA-F]{7,40})`?\s*$",
    re.MULTILINE,
)
_REVIEW_CYCLE_RE = re.compile(r"^\s*Review Cycle\s+(\d+)\b", re.MULTILINE | re.IGNORECASE)
_MARKDOWN_CELL_RE = re.compile(r"`([^`]+)`")
_GLOB_CHARS = frozenset("*?[")


@dataclass(frozen=True)
class Worktree:
    path: str
    head: str | None = None
    branch: str | None = None
    detached: bool = False


@dataclass(frozen=True)
class Lane:
    kind: str
    identity: str
    branch: str | None
    paths: tuple[str, ...]
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Conflict:
    candidate_path: str
    other_path: str
    lane_kind: str
    lane_identity: str
    branch: str | None


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def _strip_markdown_cell(value: str) -> str:
    match = _MARKDOWN_CELL_RE.search(value)
    if match:
        return match.group(1).strip()
    return value.strip().strip("`")


def _section_table_field(raw: str, field_name: str) -> str | None:
    """Return a simple two-column markdown-table field from a handoff."""
    wanted = field_name.casefold()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2 or cells[0].casefold() != wanted:
            continue
        value = _strip_markdown_cell(cells[1])
        return value or None
    return None


def _normalize_lease_path(value: str) -> str:
    path = value.strip().strip("`").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.rstrip("/") if path != "/" else path


def _has_glob(path: str) -> bool:
    return any(char in path for char in _GLOB_CHARS)


def _literal_prefix(pattern: str) -> str:
    indexes = [pattern.find(char) for char in _GLOB_CHARS if char in pattern]
    if not indexes:
        return pattern
    return pattern[: min(indexes)]


def leases_overlap(left: str, right: str) -> bool:
    """Conservatively detect whether two declared write-lease entries overlap."""
    a = _normalize_lease_path(left)
    b = _normalize_lease_path(right)
    if not a or not b:
        return False
    if a == b:
        return True

    a_glob = _has_glob(a)
    b_glob = _has_glob(b)
    if a_glob and not b_glob:
        return fnmatch.fnmatchcase(b, a)
    if b_glob and not a_glob:
        return fnmatch.fnmatchcase(a, b)
    if a_glob and b_glob:
        # Exact glob intersection is expensive and surprising. Report a possible
        # collision when the literal roots overlap; the steward resolves it.
        a_prefix = _literal_prefix(a).rstrip("/")
        b_prefix = _literal_prefix(b).rstrip("/")
        if not a_prefix or not b_prefix:
            return True
        return a_prefix.startswith(b_prefix) or b_prefix.startswith(a_prefix)

    return False


def parse_worktree_porcelain(text: str) -> list[Worktree]:
    records: list[Worktree] = []
    current: dict[str, Any] = {}

    def flush() -> None:
        if "worktree" not in current:
            current.clear()
            return
        branch = current.get("branch")
        if isinstance(branch, str) and branch.startswith("refs/heads/"):
            branch = branch.removeprefix("refs/heads/")
        records.append(
            Worktree(
                path=str(current["worktree"]),
                head=current.get("HEAD"),
                branch=branch,
                detached=bool(current.get("detached", False)),
            )
        )
        current.clear()

    for line in text.splitlines():
        if not line.strip():
            flush()
            continue
        key, _, value = line.partition(" ")
        if key == "detached":
            current[key] = True
        else:
            current[key] = value
    flush()
    return records


def read_handoff_lane(path: Path, *, kind: str = "handoff") -> Lane:
    handoff = parse_handoff(path)
    paths = tuple(_normalize_lease_path(p) for p in extract_allowlist_paths(handoff))
    branch = _section_table_field(handoff.raw, "Branch / isolated checkout")
    return Lane(
        kind=kind,
        identity=str(path),
        branch=branch,
        paths=tuple(sorted(p for p in paths if p)),
        provenance={"handoff": str(path)},
    )


def discover_active_handoff_lanes(plans_dir: Path, candidate: Path) -> list[Lane]:
    candidate_resolved = candidate.resolve()
    lanes: list[Lane] = []
    if not plans_dir.exists():
        return lanes
    for path in sorted(plans_dir.glob("HANDOFF-*.md")):
        if path.resolve() == candidate_resolved:
            continue
        raw = path.read_text(encoding="utf-8")
        if not _STATUS_ACTIVE_RE.search(raw):
            continue
        lane = read_handoff_lane(path)
        lanes.append(lane)
    return lanes


def _git_state(repo_root: Path, candidate_base: str | None) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    main = _run(["git", "rev-parse", "main"], cwd=repo_root).stdout.strip()
    worktree_text = _run(["git", "worktree", "list", "--porcelain"], cwd=repo_root).stdout
    worktrees = parse_worktree_porcelain(worktree_text)

    base_relation: dict[str, Any] = {
        "candidate_base": candidate_base,
        "main_sha": main,
        "matches_main": candidate_base == main if candidate_base else None,
        "base_is_ancestor_of_main": None,
    }
    if candidate_base:
        proc = _run(
            ["git", "merge-base", "--is-ancestor", candidate_base, main],
            cwd=repo_root,
            check=False,
        )
        if proc.returncode == 0:
            base_relation["base_is_ancestor_of_main"] = True
        elif proc.returncode == 1:
            base_relation["base_is_ancestor_of_main"] = False
        else:
            warnings.append(
                "could not determine candidate base ancestry against local main: "
                + proc.stderr.strip()
            )
        if candidate_base != main:
            warnings.append(
                "candidate base differs from local main; this is not automatically invalid, "
                "but the steward must re-check predecessor assumptions"
            )

    return (
        {
            "repo_root": str(repo_root),
            "head_sha": head,
            "main_sha": main,
            "worktrees": [asdict(item) for item in worktrees],
            "base_relation": base_relation,
        },
        warnings,
    )


def _gh_json(cmd: list[str], *, cwd: Path) -> Any:
    proc = _run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh command failed")
    return json.loads(proc.stdout)


def _detect_repo_name(repo_root: Path) -> str:
    proc = _run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=repo_root,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "could not detect GitHub repository")
    return proc.stdout.strip()


def discover_open_pr_lanes(repo_root: Path, repo_name: str) -> list[Lane]:
    summaries = _gh_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_name,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,headRefName,headRefOid,url",
        ],
        cwd=repo_root,
    )
    lanes: list[Lane] = []
    for summary in summaries:
        number = int(summary["number"])
        detail = _gh_json(
            [
                "gh",
                "pr",
                "view",
                str(number),
                "--repo",
                repo_name,
                "--json",
                "number,headRefName,headRefOid,url,files",
            ],
            cwd=repo_root,
        )
        paths = tuple(
            sorted(
                _normalize_lease_path(str(item.get("path", "")))
                for item in detail.get("files", [])
                if item.get("path")
            )
        )
        lanes.append(
            Lane(
                kind="pr",
                identity=f"PR #{number}",
                branch=detail.get("headRefName"),
                paths=paths,
                provenance={
                    "number": number,
                    "url": detail.get("url"),
                    "head_sha": detail.get("headRefOid"),
                },
            )
        )
    return lanes


def summarize_review_cycles(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    explicit: list[dict[str, Any]] = []
    for review in reviews:
        body = str(review.get("body") or "")
        match = _REVIEW_CYCLE_RE.search(body)
        commit_id = review.get("commit_id") or review.get("commitId")
        if not match or not commit_id:
            continue
        explicit.append(
            {
                "cycle_label": int(match.group(1)),
                "commit_id": str(commit_id),
                "review_id": review.get("id"),
                "state": review.get("state"),
                "user": (review.get("user") or {}).get("login"),
                "submitted_at": review.get("submitted_at") or review.get("submittedAt"),
            }
        )

    by_head: dict[str, list[dict[str, Any]]] = {}
    labels: dict[int, set[str]] = {}
    for entry in explicit:
        by_head.setdefault(entry["commit_id"], []).append(entry)
        labels.setdefault(entry["cycle_label"], set()).add(entry["commit_id"])

    anomalies: list[dict[str, Any]] = []
    for commit_id, entries in sorted(by_head.items()):
        if len(entries) > 1:
            anomalies.append(
                {
                    "kind": "multiple_formal_cycle_entries_same_head",
                    "commit_id": commit_id,
                    "review_ids": [entry["review_id"] for entry in entries],
                }
            )
    for label, heads in sorted(labels.items()):
        if len(heads) > 1:
            anomalies.append(
                {
                    "kind": "cycle_label_reused_across_heads",
                    "cycle_label": label,
                    "commit_ids": sorted(heads),
                }
            )

    return {
        "count": len(by_head),
        "distinct_head_shas": sorted(by_head),
        "formal_entries": explicit,
        "anomalies": anomalies,
    }


def fetch_review_cycle_summary(repo_root: Path, repo_name: str, pr_number: int) -> dict[str, Any]:
    pages = _gh_json(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo_name}/pulls/{pr_number}/reviews?per_page=100",
        ],
        cwd=repo_root,
    )
    reviews: list[dict[str, Any]] = []
    for page in pages:
        if isinstance(page, list):
            reviews.extend(item for item in page if isinstance(item, dict))
    summary = summarize_review_cycles(reviews)
    summary["pr_number"] = pr_number
    return summary


def find_conflicts(candidate: Lane, other_lanes: list[Lane]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    for lane in other_lanes:
        if candidate.branch and lane.branch and candidate.branch == lane.branch:
            # This is the same source lane (e.g. preflight during its open PR review).
            continue
        for candidate_path in candidate.paths:
            for other_path in lane.paths:
                if leases_overlap(candidate_path, other_path):
                    conflicts.append(
                        Conflict(
                            candidate_path=candidate_path,
                            other_path=other_path,
                            lane_kind=lane.kind,
                            lane_identity=lane.identity,
                            branch=lane.branch,
                        )
                    )
    return conflicts


def build_snapshot(
    *,
    handoff_path: Path,
    repo_root: Path,
    repo_name: str | None,
    local_only: bool,
    pr_number: int | None,
    github_lane_reader: Callable[[Path, str], list[Lane]] = discover_open_pr_lanes,
    review_reader: Callable[[Path, str, int], dict[str, Any]] = fetch_review_cycle_summary,
) -> dict[str, Any]:
    handoff_path = handoff_path.resolve()
    if not handoff_path.exists():
        raise FileNotFoundError(f"handoff not found: {handoff_path}")

    handoff = parse_handoff(handoff_path)
    candidate = read_handoff_lane(handoff_path, kind="candidate")
    base_match = _BASE_RE.search(handoff.raw)
    candidate_base = base_match.group(1) if base_match else None
    runtime_ownership = _section_table_field(handoff.raw, "Runtime/state ownership")

    warnings: list[str] = []
    blockers: list[str] = []
    if not candidate.paths:
        blockers.append("candidate §4 write lease is empty or unparseable")
    if not runtime_ownership:
        warnings.append("candidate handoff does not declare Runtime/state ownership")

    git_state, git_warnings = _git_state(repo_root, candidate_base)
    warnings.extend(git_warnings)

    plans_dir = repo_root / "Docs" / "Plans"
    active_handoffs = discover_active_handoff_lanes(plans_dir, handoff_path)

    remote_complete = local_only
    remote_lanes: list[Lane] = []
    review_cycles: dict[str, Any] | None = None
    resolved_repo = repo_name
    if not local_only:
        try:
            resolved_repo = resolved_repo or _detect_repo_name(repo_root)
            remote_lanes = github_lane_reader(repo_root, resolved_repo)
            remote_complete = True
            if pr_number is not None:
                review_cycles = review_reader(repo_root, resolved_repo, pr_number)
        except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
            warnings.append(
                "GitHub discovery unavailable; remote PR/review coverage is incomplete: " + str(exc)
            )
            remote_complete = False

    local_conflicts = find_conflicts(candidate, active_handoffs)
    remote_conflicts = find_conflicts(candidate, remote_lanes)
    conflicts = local_conflicts + remote_conflicts
    if conflicts:
        blockers.append(f"{len(conflicts)} concrete write-lease overlap(s) detected")

    if blockers:
        status = "block"
    elif warnings:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "candidate": {
            "handoff": str(handoff_path),
            "branch": candidate.branch,
            "base_revision": candidate_base,
            "write_lease": list(candidate.paths),
            "runtime_state_ownership": runtime_ownership,
        },
        "git": git_state,
        "active_handoffs": [asdict(lane) for lane in active_handoffs],
        "github": {
            "requested": not local_only,
            "complete": remote_complete,
            "repo": resolved_repo,
            "open_pr_lanes": [asdict(lane) for lane in remote_lanes],
        },
        "conflicts": [asdict(conflict) for conflict in conflicts],
        "review_cycles": review_cycles,
        "warnings": warnings,
        "blockers": blockers,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only steward lane/write-lease preflight; emits JSON.",
    )
    parser.add_argument("--handoff", required=True, type=Path, help="candidate HANDOFF path")
    parser.add_argument("--repo", help="GitHub owner/name; auto-detected when omitted")
    parser.add_argument("--pr", type=int, help="optional PR number for explicit review-cycle summary")
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="skip GitHub/gh discovery and report local repo/handoff facts only",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo_root_proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        repo_root = Path(repo_root_proc.stdout.strip()).resolve()
        handoff_path = args.handoff
        if not handoff_path.is_absolute():
            handoff_path = repo_root / handoff_path
        snapshot = build_snapshot(
            handoff_path=handoff_path,
            repo_root=repo_root,
            repo_name=args.repo,
            local_only=args.local_only,
            pr_number=args.pr,
        )
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 2

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 1 if snapshot["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
