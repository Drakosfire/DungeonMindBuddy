#!/usr/bin/env python3
"""External-agent PR review helpers — token-efficient versions of the
manual `gh + git + sed` dance the parent agent runs against every PR
opened by an external (Codex-style) worker.

Subcommands map onto `.cursor/rules/external-agent-pr-loop.mdc` § 2
("PR review — gates before reading the diff"):

    fetch   — Produce a single structured pre-review summary combining PR
              metadata, the file-level diff, and (when ``--handoff`` is
              given) §4 allowlist / §5 denylist checks plus the §7
              verification command list parsed from the markdown.
              Optional ``--extract-rubric`` adds §9 acceptance bullets
              (markdown list lines) so verdict writers do not re-open the
              handoff for copy/paste.
              One JSON blob replaces 6–10 ad-hoc ``gh pr view`` /
              ``git diff`` / ``git show`` calls.

    verify  — Auto-stash uncommitted edits (including untracked files),
              checkout the PR head, run the §7 verification commands
              (parsed from the handoff or supplied via ``--command``),
              then restore the original branch and pop the stash.
              Optional ``--parse-counts`` runs a pytest-style
              ``N passed`` regex over each command's captured tail and
              emits ``passed_count`` per result for checklist templating.
              The reviewer never has to do the stash/checkout/restore
              dance by hand.

    post    — POST a review (event + body + line-anchored comments)
              from a JSON spec. Handles the GitHub 422
              ``Can not request changes on your own pull request`` by
              transparently falling back to ``event=COMMENT`` with a
              verdict banner prepended to the body — the parent and
              external workers regularly share an account, so this
              fallback is the common path, not the exception.

    merge   — Merge an approved PR (``gh pr merge --merge --delete-branch``
              by default), fast-forward local ``main``, auto-handle the
              dirty-tree overlap stash dance, and emit the merge-commit
              hash + timestamp the post-merge atomic doc-sync needs.
              Replaces the 9-call ``gh pr view → merge → view → fetch →
              stash → pull → pop → status`` ceremony with one call. If
              the PR was already merged (re-run after a partial sync),
              short-circuits to capture-state mode and emits the same
              JSON without re-merging.

Design constraints:

- **No new dependencies.** The repo already vendors ``pyyaml``; we use
  it for nothing structural — handoff parsing is markdown-heuristic.
- **Read-only by default.** ``fetch`` never writes to the repo.
  ``verify`` writes only to the working tree (stash + checkout +
  restore) and is idempotent on success. ``post`` writes only to GitHub
  via ``gh api``.
- **Deterministic JSON output.** ``fetch`` and ``post`` emit pretty-
  printed JSON to stdout so agents can pipe into ``jq`` or read it
  back with ``json.load``.

See ``.cursor/rules/external-agent-pr-loop.mdc`` § "Reviewer scripts
(token-efficient)" for end-to-end usage patterns.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Shell helpers
# --------------------------------------------------------------------------- #


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Thin wrapper around ``subprocess.run`` that always uses ``text=True``."""
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def _gh_json(args: list[str]) -> Any:
    """Invoke ``gh api ...`` and parse the JSON response.

    Raises ``RuntimeError`` with the API body on non-zero exit so callers
    can surface the GitHub error message to the user (the most common
    failure mode is HTTP 422 with a useful ``errors`` field).
    """
    proc = subprocess.run(
        ["gh", "api", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh api {' '.join(args)} failed (exit={proc.returncode}): "
            f"{proc.stderr.strip()} | stdout={proc.stdout.strip()}"
        )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


# --------------------------------------------------------------------------- #
# Handoff parsing (markdown heuristics)
# --------------------------------------------------------------------------- #


_SECTION_RE = re.compile(r"^##\s+§(\d+)(?:\.(\d+))?\s+(.*?)\s*$", re.MULTILINE)
_BACKTICK_RUN_RE = re.compile(r"`([^`]+)`")
_BASH_FENCE_RE = re.compile(r"```bash\s*\n(.*?)```", re.DOTALL)


def _table_rows(body: str) -> list[list[str]]:
    """Extract markdown-table rows from a section body.

    Returns a list of rows, each a list of cell strings (excluding the
    leading and trailing empty cells from the surrounding ``|``). Header
    and separator rows are dropped — only data rows are returned. If
    multiple tables appear in the body, all of them are returned in
    document order; downstream callers re-key on column names.
    """
    rows: list[list[str]] = []
    in_table = False
    header_seen = False
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            header_seen = False
            continue
        # Strip leading/trailing pipes, split on |, trim cells.
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        # Detect separator row: cells like "---", ":---:", "---|".
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            in_table = True
            header_seen = True
            continue
        if not header_seen:
            # First |...| row is the header; remember it on the rows list
            # under a sentinel index so the caller can pick the column.
            rows.append([f"__HEADER__:{c}" for c in cells])
            continue
        if in_table:
            rows.append(cells)
    return rows


def _extract_path_column(rows: list[list[str]]) -> list[str]:
    """Pick out the cell values in any column whose header is ``Path``.

    Multiple tables in one section are scanned independently — if §4 has
    one table with header ``[Action, Path, Purpose]`` and §5 has another
    with header ``[Path, Why, Risk]``, both Path columns are extracted
    correctly.
    """
    out: list[str] = []
    current_path_idx: int | None = None
    for row in rows:
        if row and row[0].startswith("__HEADER__:"):
            headers = [c.removeprefix("__HEADER__:").lower() for c in row]
            current_path_idx = next(
                (i for i, h in enumerate(headers) if h == "path"),
                None,
            )
            continue
        if current_path_idx is None or current_path_idx >= len(row):
            continue
        cell = row[current_path_idx]
        # Cells often contain code spans + prose. Pull every backticked
        # token; each is a candidate path.
        for m in _BACKTICK_RUN_RE.findall(cell):
            tok = m.strip()
            if tok:
                out.append(tok)
    return out


@dataclass
class HandoffSections:
    """A parsed handoff document."""

    path: Path
    raw: str
    sections: dict[str, str] = field(default_factory=dict)

    def section(self, key: str) -> str:
        """Look up a section body by its ``§N`` or ``§N.M`` key."""
        return self.sections.get(key, "")


def parse_handoff(path: Path) -> HandoffSections:
    """Parse a ``HANDOFF-*.md`` file into a flat dict keyed by ``§N``.

    The parser is intentionally heuristic — it matches the structure
    documented in `.cursor/rules/external-agent-pr-loop.mdc` § 1 and
    will silently skip any handoff that uses a different section
    layout. Callers should treat empty sections as "not parsed" and
    fall back to manual review.
    """
    raw = path.read_text(encoding="utf-8")
    matches = list(_SECTION_RE.finditer(raw))
    sections: dict[str, str] = {}
    for idx, m in enumerate(matches):
        major, minor, _title = m.groups()
        key = f"§{major}" if minor is None else f"§{major}.{minor}"
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        sections[key] = raw[start:end].strip()
    return HandoffSections(path=path, raw=raw, sections=sections)


def extract_allowlist_paths(handoff: HandoffSections) -> list[str]:
    """Pull file paths from the ``Path`` column of the §4 markdown table."""
    rows = _table_rows(handoff.section("§4"))
    return sorted(set(_extract_path_column(rows)))


def extract_denylist_patterns(handoff: HandoffSections) -> list[str]:
    """Pull paths and globs from the ``Path`` column of the §5 table.

    §5 mixes literal paths (``src/lexicon_phase_b/schemas.py``) and
    glob-ish patterns (``tests/test_token_resolution_*.py``,
    ``Docs/Plans/archive/**``). The handoff sometimes uses ``...`` as a
    shorthand for an intermediate directory level — we normalize that
    to ``**`` so the glob matcher behaves sensibly.
    """
    rows = _table_rows(handoff.section("§5"))
    raw = _extract_path_column(rows)
    normalized: list[str] = []
    for tok in raw:
        # `evals/.../artifacts/lexicon/foo.jsonl` → `evals/**/artifacts/lexicon/foo.jsonl`.
        normalized.append(tok.replace("/.../", "/**/").replace("...", "**"))
    return sorted(set(normalized))


def extract_rubric_bullets(handoff: HandoffSections) -> list[str]:
    """Return non-empty list items from the §9 body (acceptance rubric).

    Heuristic: lines matching ``-`` / ``- [ ]`` / ``- [x]`` list syntax at
    column 0 (after optional whitespace). Blockquote lines (``>``) are
    skipped. Intended for ``fetch --extract-rubric`` so verdict bodies can
    quote rubric text without re-reading the full handoff.
    """
    body = handoff.section("§9")
    bullets: list[str] = []
    line_re = re.compile(
        r"^\s*-\s*(?:\[[ xX]\]\s*)?(?P<text>.+?)\s*$",
    )
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(">"):
            continue
        m = line_re.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        # Markdown horizontal rules look like list items (`---`).
        if not text or re.fullmatch(r"-{3,}", text):
            continue
        bullets.append(text)
    return bullets


_PYTEST_PASSED_RE = re.compile(r"(\d+)\s+passed\b", re.IGNORECASE)


def parse_passed_count_from_tail(tail: str) -> int | None:
    """Best-effort pytest ``N passed`` count from trailing command output.

    Uses the **last** ``(\\d+) passed`` match in ``tail`` so multi-suite
    logs still surface the final summary line when pytest prints it last.
    Returns ``None`` when no pytest-style summary is detected.
    """
    matches = _PYTEST_PASSED_RE.findall(tail)
    if not matches:
        return None
    return int(matches[-1])


def extract_verification_commands(handoff: HandoffSections) -> list[str]:
    """Extract individual shell commands from the §7 ```bash``` fences.

    Comment-only lines (``# foo``) and blank lines are skipped. Multi-
    line continuations (``\\``) are joined into single commands.
    """
    body = handoff.section("§7")
    out: list[str] = []
    for fence in _BASH_FENCE_RE.findall(body):
        # Join continuation lines.
        lines: list[str] = []
        buf = ""
        for line in fence.splitlines():
            stripped = line.rstrip()
            if not stripped or stripped.lstrip().startswith("#"):
                if buf:
                    lines.append(buf)
                    buf = ""
                continue
            if stripped.endswith("\\"):
                buf += stripped[:-1].rstrip() + " "
            else:
                buf += stripped
                lines.append(buf)
                buf = ""
        if buf:
            lines.append(buf)
        out.extend(lines)
    return out


def _glob_matches(pattern: str, path: str) -> bool:
    """Match ``path`` against a handoff-style ``**`` / ``*`` / ``?`` glob.

    We can't use ``fnmatch`` directly because ``fnmatch`` does not
    treat ``**`` as a multi-segment wildcard. ``Path.match`` does,
    so we delegate when the pattern looks recursive.
    """
    if "**" in pattern:
        # Path.match treats `**` as recursive directory match.
        try:
            return Path(path).match(pattern)
        except ValueError:
            return False
    import fnmatch

    return fnmatch.fnmatch(path, pattern)


def denylist_hits(
    changed_paths: Iterable[str], patterns: Iterable[str]
) -> list[dict[str, str]]:
    """Return ``[{path, matched_pattern}]`` for any PR file matching any pattern."""
    hits: list[dict[str, str]] = []
    for path in changed_paths:
        for pat in patterns:
            if _glob_matches(pat, path) or pat == path:
                hits.append({"path": path, "matched_pattern": pat})
                break
    return hits


# --------------------------------------------------------------------------- #
# fetch
# --------------------------------------------------------------------------- #


def cmd_fetch(args: argparse.Namespace) -> int:
    if args.extract_rubric and not args.handoff:
        print(
            "fetch: --extract-rubric requires --handoff",
            file=sys.stderr,
        )
        return 2

    pr_meta = _gh_json([
        f"repos/{args.repo}/pulls/{args.pr}",
    ])
    files_meta = _gh_json([
        f"repos/{args.repo}/pulls/{args.pr}/files",
        "--paginate",
    ])
    changed_paths = sorted(f["filename"] for f in files_meta)

    summary: dict[str, Any] = {
        "pr": {
            "number": pr_meta.get("number"),
            "title": pr_meta.get("title"),
            "state": pr_meta.get("state"),
            "head_sha": pr_meta.get("head", {}).get("sha"),
            "head_branch": pr_meta.get("head", {}).get("ref"),
            "base_branch": pr_meta.get("base", {}).get("ref"),
            "author": pr_meta.get("user", {}).get("login"),
            "additions": pr_meta.get("additions"),
            "deletions": pr_meta.get("deletions"),
            "changed_files": pr_meta.get("changed_files"),
            "mergeable": pr_meta.get("mergeable"),
            "url": pr_meta.get("html_url"),
        },
        "files": [
            {
                "path": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
            }
            for f in files_meta
        ],
    }

    if args.handoff:
        handoff_path = Path(args.handoff)
        if not handoff_path.is_file():
            raise FileNotFoundError(f"handoff not found: {handoff_path}")
        handoff = parse_handoff(handoff_path)
        allowlist = extract_allowlist_paths(handoff)
        denylist = extract_denylist_patterns(handoff)
        verification = extract_verification_commands(handoff)

        actual = set(changed_paths)
        expected = set(allowlist)
        extras = sorted(actual - expected)
        missing = sorted(expected - actual)
        allowlist_status = "pass" if not extras and not missing else (
            "extras" if extras and not missing
            else "missing" if missing and not extras
            else "extras_and_missing"
        )

        denylist_hit = denylist_hits(changed_paths, denylist)
        denylist_status = "pass" if not denylist_hit else "hit"

        summary["handoff"] = {
            "path": str(handoff_path),
            "sections_parsed": sorted(handoff.sections.keys()),
        }
        summary["allowlist_check"] = {
            "status": allowlist_status,
            "expected": sorted(expected),
            "actual": sorted(actual),
            "extras": extras,
            "missing": missing,
        }
        summary["denylist_check"] = {
            "status": denylist_status,
            "patterns": denylist,
            "hits": denylist_hit,
        }
        summary["verification_commands"] = verification

        if args.extract_rubric:
            summary["handoff"]["rubric_bullets"] = extract_rubric_bullets(handoff)

    json.dump(summary, sys.stdout, indent=2, sort_keys=False, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


# --------------------------------------------------------------------------- #
# verify
# --------------------------------------------------------------------------- #


def _git(*args: str, check: bool = True) -> str:
    proc = _run(["git", *args], check=check)
    return proc.stdout.strip()


def cmd_verify(args: argparse.Namespace) -> int:
    # 1. Resolve commands.
    commands: list[str] = []
    if args.handoff:
        commands.extend(extract_verification_commands(parse_handoff(Path(args.handoff))))
    if args.command:
        commands.extend(args.command)
    if not commands:
        print(
            "no verification commands resolved; pass --handoff PATH or --command 'cmd ...'",
            file=sys.stderr,
        )
        return 2

    # 2. Save current branch + stash uncommitted state.
    original_branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    stash_label = f"review-pr-{args.pr}-{os.getpid()}"
    stash_msg = _run(
        ["git", "stash", "push", "--include-untracked", "-m", stash_label],
        check=False,
    ).stdout.strip()
    stashed = "No local changes to save" not in stash_msg

    pr_local_branch = f"pr-{args.pr}-review"
    try:
        # 3. Fetch + checkout PR.
        _run(
            ["git", "fetch", "origin", f"pull/{args.pr}/head:{pr_local_branch}", "--force"],
            check=True,
        )
        _run(["git", "checkout", pr_local_branch], check=True)
        head_sha = _git("rev-parse", "HEAD")
        print(f"# checked out {pr_local_branch} at {head_sha}", file=sys.stderr)

        # 4. Run each command.
        results: list[dict[str, Any]] = []
        for cmd in commands:
            print(f"\n$ {cmd}", file=sys.stderr)
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
            )
            combined = proc.stdout + proc.stderr
            tail = "\n".join(combined.splitlines()[-args.tail :])
            row: dict[str, Any] = {
                "command": cmd,
                "exit_code": proc.returncode,
                "tail": tail,
            }
            if args.parse_counts:
                row["passed_count"] = parse_passed_count_from_tail(tail)
            results.append(row)
            print(tail, file=sys.stderr)
            if proc.returncode != 0 and args.fail_fast:
                print(f"# fail-fast on non-zero exit: {cmd}", file=sys.stderr)
                break

        # 5. Emit JSON summary on stdout.
        summary = {
            "pr": args.pr,
            "head_sha": head_sha,
            "passed": all(r["exit_code"] == 0 for r in results),
            "results": results,
        }
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if summary["passed"] else 1

    finally:
        # Always restore: checkout original branch, pop stash, delete pr branch.
        _run(["git", "checkout", original_branch], check=False)
        if stashed:
            _run(["git", "stash", "pop"], check=False)
        _run(["git", "branch", "-D", pr_local_branch], check=False)


# --------------------------------------------------------------------------- #
# post
# --------------------------------------------------------------------------- #


_VERDICT_TO_EVENT = {
    "request_changes": "REQUEST_CHANGES",
    "comment": "COMMENT",
    "approve": "APPROVE",
}

_VERDICT_HUMAN = {
    "request_changes": "REQUEST CHANGES",
    "comment": "COMMENT",
    "approve": "APPROVE",
}

# Inline-comment marker on the review-markdown format. Agents prefer
# writing prose-like markdown over hand-encoded JSON; the parser below
# turns one markdown file into the GitHub-Reviews payload shape.
_INLINE_MARKER_RE = re.compile(r"^@comment\s+(?P<spec>\S.*?)\s*$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)


def parse_review_markdown(text: str) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    """Parse a markdown review-spec file into ``(metadata, body, comments)``.

    Format:

        ---
        verdict: approve            # optional (also via --verdict)
        pr_number: 4                # optional (also via --pr)
        ---

        <review body markdown — anything before the first @comment marker>

        @comment <path>:<line>[:<side>]
        <inline comment markdown until the next @comment or EOF>

        @comment <path>:<line>
        <another inline comment>

    Notes:

    - Frontmatter is optional. Any keys not in
      ``{"verdict", "pr_number"}`` are passed through as metadata for
      future use (e.g. embedded review-tool versioning).
    - ``side`` defaults to ``RIGHT`` (the new file). Pass ``LEFT`` only
      when commenting on a context line in the original file.
    - The ``@comment`` marker MUST start at column 0; markers indented
      inside code blocks are intentionally treated as content so that
      review prose can quote the syntax without triggering a parse.
    - Trailing whitespace is stripped from each section body.

    Returns:
        meta: Frontmatter dict. May contain ``verdict``, ``pr_number``,
              and any forward-compat extras.
        body: The review body markdown (string, possibly empty).
        comments: List of ``{"path", "line", "side", "body"}`` dicts in
                  document order.
    """
    meta: dict[str, Any] = {}
    fm_match = _FRONTMATTER_RE.match(text)
    if fm_match:
        for line in fm_match.group("body").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        text = text[fm_match.end():]
    if "pr_number" in meta:
        try:
            meta["pr_number"] = int(meta["pr_number"])
        except ValueError as exc:
            raise ValueError(
                f"frontmatter pr_number must be an integer, got {meta['pr_number']!r}"
            ) from exc

    body_lines: list[str] = []
    comments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        m = _INLINE_MARKER_RE.match(raw_line)
        if m:
            if current is not None:
                current["body"] = "\n".join(current.pop("_lines")).strip()
                comments.append(current)
            spec = m.group("spec")
            # Use rsplit so paths containing colons (rare on Linux) survive.
            parts = spec.rsplit(":", 2)
            if len(parts) == 2:
                path_str, line_str = parts
                side = "RIGHT"
            elif len(parts) == 3:
                path_str, line_str, side = parts
            else:
                raise ValueError(
                    f"malformed @comment marker: {raw_line!r} "
                    "(expected '@comment <path>:<line>[:<side>]')"
                )
            try:
                line_no = int(line_str.strip())
            except ValueError as exc:
                raise ValueError(
                    f"malformed @comment marker: line must be an integer, got {line_str!r}"
                ) from exc
            side_norm = side.strip().upper() or "RIGHT"
            if side_norm not in ("RIGHT", "LEFT"):
                raise ValueError(
                    f"malformed @comment marker: side must be RIGHT or LEFT, got {side!r}"
                )
            current = {
                "path": path_str.strip(),
                "line": line_no,
                "side": side_norm,
                "_lines": [],
            }
        elif current is not None:
            current["_lines"].append(raw_line)
        else:
            body_lines.append(raw_line)
    if current is not None:
        current["body"] = "\n".join(current.pop("_lines")).strip()
        comments.append(current)

    body = "\n".join(body_lines).strip()
    return meta, body, comments


def cmd_post(args: argparse.Namespace) -> int:
    if bool(args.spec) == bool(args.review_md):
        raise ValueError("exactly one of --spec or --review-md is required")

    meta: dict[str, Any] = {}
    if args.spec:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        verdict = (spec.get("verdict") or "comment").lower()
        body = spec.get("body") or ""
        comments = spec.get("comments") or []
        pr_number = spec.get("pr_number")
    else:
        meta, body, comments = parse_review_markdown(
            Path(args.review_md).read_text(encoding="utf-8")
        )
        verdict = str(meta.get("verdict") or "comment").lower()
        pr_number = meta.get("pr_number")

    if args.verdict:
        verdict = args.verdict.lower()
    if args.pr:
        pr_number = args.pr

    if verdict not in _VERDICT_TO_EVENT:
        raise ValueError(
            f"unknown verdict {verdict!r}; expected one of "
            f"{sorted(_VERDICT_TO_EVENT)}"
        )
    if not pr_number:
        raise ValueError("pr_number required (in spec/frontmatter or via --pr)")

    event = _VERDICT_TO_EVENT[verdict]
    payload = {"event": event, "body": body, "comments": comments}

    repo = args.repo
    payload_path = Path("/tmp") / f"review-pr-{pr_number}-{os.getpid()}.json"

    def _post(payload_obj: dict[str, Any]) -> dict[str, Any]:
        payload_path.write_text(
            json.dumps(payload_obj, ensure_ascii=False), encoding="utf-8"
        )
        return _gh_json([
            f"repos/{repo}/pulls/{pr_number}/reviews",
            "--method", "POST",
            "--input", str(payload_path),
        ])

    try:
        result = _post(payload)
    except RuntimeError as exc:
        msg = str(exc)
        # GitHub blocks both REQUEST_CHANGES and APPROVE from the PR
        # author account. The parent + Codex worker frequently share
        # the same GitHub account on this repo, so the canonical
        # fallback is to demote to COMMENT and inject a verdict banner
        # so the verdict is still legible to humans reading the review.
        self_review_block = (
            "Can not request changes on your own pull request" in msg
            or "Can not approve your own pull request" in msg
        )
        if event in ("REQUEST_CHANGES", "APPROVE") and self_review_block:
            human = _VERDICT_HUMAN[verdict]
            banner = (
                f"## Review verdict: {human} — posted as "
                f"`event: COMMENT` because GitHub blocks `{event}` from "
                "the PR author account (parent + worker share this "
                f"account on this repo). Treat this review's verdict as "
                f"{verdict.replace('_', '-')} regardless of the GitHub "
                "event type.\n\n"
            )
            fallback_payload = dict(payload)
            fallback_payload["event"] = "COMMENT"
            fallback_payload["body"] = banner + body
            print(
                f"# {event} blocked by GitHub (self-review); "
                "falling back to COMMENT with verdict banner",
                file=sys.stderr,
            )
            result = _post(fallback_payload)
        else:
            payload_path.unlink(missing_ok=True)
            raise

    payload_path.unlink(missing_ok=True)

    out = {
        "review_id": result.get("id"),
        "state": result.get("state"),
        "url": result.get("html_url"),
        "submitted_at": result.get("submitted_at"),
        "comment_count": len(comments),
        "verdict_requested": verdict,
        "event_posted": result.get("state"),
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


# --------------------------------------------------------------------------- #
# merge
# --------------------------------------------------------------------------- #


def _changed_files_in_range(rev_a: str, rev_b: str) -> list[str]:
    """Files touched by ``git diff --name-only rev_a..rev_b``.

    Returns an empty list on any git error so the caller can degrade
    gracefully — used only for an *advisory* dirty-tree overlap check.
    """
    proc = _run(["git", "diff", "--name-only", f"{rev_a}..{rev_b}"], check=False)
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _dirty_files_with_status() -> list[tuple[str, str]]:
    """Return ``(porcelain_status, path)`` pairs for every dirty entry.

    Includes both tracked-modified (``M``, `` M``, ``A`` …) and untracked
    (``??``) entries. Renames (``R  old -> new``) are reduced to the new
    path. The status code is preserved so the merge command can decide
    when an overlap actually requires a stash.
    """
    proc = _run(["git", "status", "--porcelain"], check=False)
    out: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        out.append((status, path))
    return out


def cmd_merge(args: argparse.Namespace) -> int:
    pr = args.pr
    repo = args.repo

    # 1. Pre-flight: state, mergeability, mergeStateStatus.
    pr_meta = _gh_json([f"repos/{repo}/pulls/{pr}"])

    if pr_meta.get("merged"):
        # Idempotent re-run: surface the merge data without re-merging.
        summary = {
            "pr": pr,
            "merge_commit": pr_meta.get("merge_commit_sha"),
            "merged_at": pr_meta.get("merged_at"),
            "url": pr_meta.get("html_url"),
            "title": pr_meta.get("title"),
            "merge_strategy": "already_merged",
            "ff_pull_ok": None,
            "overlap_files": [],
            "stashed": False,
            "stash_pop_clean": None,
            "head_after_pull": None,
            "note": (
                "PR was already merged before this command ran; "
                "no merge or local-tree action taken. Re-run "
                "`scripts/review_external_pr.py merge` after fetching to "
                "fast-forward local main if you haven't already."
            ),
        }
        json.dump(summary, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if pr_meta.get("state") != "open":
        print(
            f"PR #{pr} is not open (state={pr_meta.get('state')}); refusing to merge.",
            file=sys.stderr,
        )
        return 2
    if pr_meta.get("mergeable") is False:
        print(
            f"PR #{pr} reports mergeable=False (conflicts on {pr_meta.get('base', {}).get('ref')}). "
            "Resolve conflicts and retry.",
            file=sys.stderr,
        )
        return 2

    # mergeStateStatus is exposed via gh's GraphQL bridge (`gh pr view`),
    # not the v3 REST endpoint. Refuse anything but CLEAN unless --force.
    state_proc = _run(
        [
            "gh", "pr", "view", str(pr),
            "--repo", repo,
            "--json", "mergeStateStatus,mergeable",
        ],
        check=False,
    )
    if state_proc.returncode != 0:
        print(f"gh pr view failed: {state_proc.stderr.strip()}", file=sys.stderr)
        return 2
    state_status = json.loads(state_proc.stdout).get("mergeStateStatus", "UNKNOWN")
    if state_status != "CLEAN" and not args.force:
        print(
            f"mergeStateStatus={state_status} (expected CLEAN). "
            "Pass --force to merge anyway.",
            file=sys.stderr,
        )
        return 2

    # 2. Snapshot pre-merge main sha for the dirty-tree overlap check below.
    pre_main_sha = _git("rev-parse", "main")

    # 3. Merge.
    merge_cmd = [
        "gh", "pr", "merge", str(pr),
        f"--{args.strategy}",
        "--repo", repo,
    ]
    if args.delete_branch:
        merge_cmd.append("--delete-branch")
    print(f"# {' '.join(merge_cmd)}", file=sys.stderr)
    merge_proc = _run(merge_cmd, check=False)
    if merge_proc.returncode != 0:
        print(
            f"gh pr merge failed (exit={merge_proc.returncode}): "
            f"{merge_proc.stderr.strip() or merge_proc.stdout.strip()}",
            file=sys.stderr,
        )
        return merge_proc.returncode

    # 4. Capture merge commit + timestamp from the post-merge PR state.
    merged_meta = _gh_json([f"repos/{repo}/pulls/{pr}"])
    merge_sha = merged_meta.get("merge_commit_sha")
    merged_at = merged_meta.get("merged_at")
    if not merge_sha:
        print(
            "merge succeeded but merge_commit_sha is empty; re-run the "
            "command to fetch the post-merge state.",
            file=sys.stderr,
        )
        return 1

    # 5. Fast-forward local main with dirty-tree overlap auto-stash.
    _run(["git", "fetch", "origin", "main"], check=True)
    pr_changed = set(_changed_files_in_range(pre_main_sha, merge_sha))
    dirty = _dirty_files_with_status()
    # Conflict candidates: tracked-modified files that intersect the PR's
    # changed set. Untracked files (??) almost never block --ff-only and
    # have a different failure mode (collision-on-pop), so we treat them
    # separately and stash everything --include-untracked when in doubt.
    overlap = sorted({path for status, path in dirty if path in pr_changed})

    stashed = False
    stash_pop_clean: bool | None = None
    if overlap:
        stash_proc = _run(
            [
                "git", "stash", "push", "--include-untracked",
                "-m", f"pre-pr{pr}-merge",
            ],
            check=False,
        )
        stashed = "No local changes to save" not in (stash_proc.stdout or "")

    pull_proc = _run(["git", "pull", "--ff-only", "origin", "main"], check=False)
    pull_ok = pull_proc.returncode == 0
    if not pull_ok:
        print(
            f"git pull --ff-only failed: {pull_proc.stderr.strip()}",
            file=sys.stderr,
        )

    if stashed:
        pop_proc = _run(["git", "stash", "pop"], check=False)
        stash_pop_clean = pop_proc.returncode == 0
        if not stash_pop_clean:
            print(
                "git stash pop reported conflicts; resolve manually then "
                "`git stash drop` to finish cleanup.",
                file=sys.stderr,
            )

    head_after = _git("rev-parse", "HEAD") if pull_ok else None

    # 6. Emit JSON. Includes the data the post-merge atomic doc-sync needs:
    #    `merge_commit` (full hash), `merged_at` (ISO timestamp), `url`,
    #    `title`. Also includes ff/stash diagnostics so the agent can
    #    detect pop conflicts without re-running git.
    summary = {
        "pr": pr,
        "merge_commit": merge_sha,
        "merged_at": merged_at,
        "url": merged_meta.get("html_url"),
        "title": merged_meta.get("title"),
        "merge_strategy": args.strategy,
        "ff_pull_ok": pull_ok,
        "overlap_files": overlap,
        "stashed": stashed,
        "stash_pop_clean": stash_pop_clean,
        "head_after_pull": head_after,
    }
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if not pull_ok:
        return 1
    if stash_pop_clean is False:
        return 1
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _default_repo() -> str:
    """Detect ``owner/name`` from ``git remote get-url origin``."""
    try:
        url = _git("remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        return ""
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    return m.group(1) if m else ""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="review_external_pr",
        description=__doc__.split("\n\n")[0],
    )
    default_repo = _default_repo()
    p.add_argument(
        "--repo",
        default=default_repo or None,
        help=f"owner/name (default: {default_repo or 'autodetect via git remote'})",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser(
        "fetch",
        help="Print a structured pre-review summary (PR meta + allowlist/denylist diff).",
    )
    p_fetch.add_argument("pr", type=int, help="PR number")
    p_fetch.add_argument(
        "--handoff",
        type=str,
        default=None,
        help="Path to the HANDOFF-*.md the PR was dispatched from.",
    )
    p_fetch.add_argument(
        "--extract-rubric",
        action="store_true",
        help=(
            "With --handoff, include §9 rubric list lines as "
            "`handoff.rubric_bullets[]` in the JSON (verdict / checklist "
            "templating)."
        ),
    )
    p_fetch.set_defaults(func=cmd_fetch)

    p_verify = sub.add_parser(
        "verify",
        help="Run §7 verification commands on the PR head, restoring local state when done.",
    )
    p_verify.add_argument("pr", type=int, help="PR number")
    p_verify.add_argument(
        "--handoff",
        type=str,
        default=None,
        help="Path to the HANDOFF-*.md (commands parsed from §7).",
    )
    p_verify.add_argument(
        "--command",
        action="append",
        default=[],
        help="Extra shell command to run (repeatable). Combined with --handoff commands.",
    )
    p_verify.add_argument(
        "--tail",
        type=int,
        default=20,
        help="Number of trailing output lines to capture per command (default: 20).",
    )
    p_verify.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first failing command (default: run all).",
    )
    p_verify.add_argument(
        "--parse-counts",
        action="store_true",
        help=(
            "Add `passed_count` (int or null) per result by scanning each "
            "command's tail for pytest-style `N passed`."
        ),
    )
    p_verify.set_defaults(func=cmd_verify)

    p_post = sub.add_parser(
        "post",
        help="POST a review (event + body + line comments) from a markdown or JSON spec.",
        description=(
            "Post a PR review from either a markdown spec (preferred — write "
            "prose directly) or a JSON spec (programmatic). Markdown format: "
            "optional `--- frontmatter ---` block with `verdict:` / `pr_number:`, "
            "followed by review body, then `@comment <path>:<line>[:<side>]` "
            "markers (one per line, column 0) each followed by inline-comment "
            "markdown until the next marker. Side defaults to RIGHT."
        ),
    )
    p_post_src = p_post.add_mutually_exclusive_group(required=True)
    p_post_src.add_argument(
        "--review-md",
        type=str,
        default=None,
        help="Path to a markdown review-spec file (preferred — see post --help).",
    )
    p_post_src.add_argument(
        "--spec",
        type=str,
        default=None,
        help="Path to JSON spec: {pr_number, verdict, body, comments[]}.",
    )
    p_post.add_argument(
        "--pr",
        type=int,
        default=None,
        help="Override pr_number from the spec/frontmatter.",
    )
    p_post.add_argument(
        "--verdict",
        choices=sorted(_VERDICT_TO_EVENT),
        default=None,
        help="Override verdict from the spec/frontmatter.",
    )
    p_post.set_defaults(func=cmd_post)

    p_merge = sub.add_parser(
        "merge",
        help="Merge an approved PR, ff local main, and emit doc-sync data.",
        description=(
            "Run the full merge ceremony in one call: verify mergeability, "
            "`gh pr merge --merge --delete-branch` (override with --strategy), "
            "fast-forward local main, auto-handle dirty-tree overlap "
            "(stash --include-untracked + pull --ff-only + stash pop), and "
            "emit JSON with merge_commit, merged_at, and ff/stash diagnostics. "
            "Refuses to merge unless mergeStateStatus == CLEAN; pass --force "
            "to override. Idempotent: re-running on an already-merged PR "
            "short-circuits to capture-state mode."
        ),
    )
    p_merge.add_argument("pr", type=int, help="PR number")
    p_merge.add_argument(
        "--strategy",
        choices=("merge", "squash", "rebase"),
        default="merge",
        help=(
            "gh pr merge strategy (default: merge — matches PR #2/#3/#4 "
            "merge-commit style on this repo)."
        ),
    )
    p_merge.add_argument(
        "--no-delete-branch",
        dest="delete_branch",
        action="store_false",
        default=True,
        help="Do NOT pass --delete-branch to gh pr merge (default: delete).",
    )
    p_merge.add_argument(
        "--force",
        action="store_true",
        help="Merge even if mergeStateStatus != CLEAN.",
    )
    p_merge.set_defaults(func=cmd_merge)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.repo:
        print("--repo is required (and could not be auto-detected)", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
