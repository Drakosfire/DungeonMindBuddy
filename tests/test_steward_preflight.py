from __future__ import annotations

import subprocess
from pathlib import Path

import scripts.steward_preflight as sp


def _write_handoff(
    path: Path,
    *,
    branch: str = "agent/candidate",
    lease: tuple[str, ...] = ("src/candidate.py",),
    runtime: str = "Not applicable — fixture",
    base: str = "a" * 40,
) -> Path:
    rows = "\n".join(f"| Modify | `{item}` | fixture |" for item in lease)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# HANDOFF — fixture

**Status:** ACTIVE — fixture
**Base revision:** `{base}`

## §1 Mission and merge-ready invariant

fixture

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Branch / isolated checkout | `{branch}` |
| Runtime/state ownership | {runtime} |

## §3 Observable paths and adversarial sequences

fixture

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
{rows}

## §5 Explicitly out of scope / collision boundary

| Path | Why |
|---|---|
| `other/**` | fixture |

## §6 Implementation contract

fixture

## §7 Evidence required to merge

```bash
true
```

## §8 Required review handback

fixture

## §9 Acceptance rubric

- [ ] fixture
""",
        encoding="utf-8",
    )
    return path


def _git_snapshot(*, base: str = "a" * 40, main: str | None = None) -> dict[str, object]:
    main_sha = main or base
    return {
        "repo_root": "/repo",
        "head_sha": "b" * 40,
        "local_main_sha": main_sha,
        "observed_origin_main_sha": main_sha,
        "worktrees": [],
        "base_relation": {
            "candidate_base": base,
            "local_main_sha": main_sha,
            "observed_origin_main_sha": main_sha,
            "matches_local_main": base == main_sha,
            "matches_observed_origin_main": base == main_sha,
            "base_is_ancestor_of_local_main": True,
        },
    }


def test_leases_overlap_exact_literal_and_wildcard() -> None:
    assert sp.leases_overlap("src/shared.ts", "src/shared.ts")
    assert sp.leases_overlap("tests/test_*.py", "tests/test_widget.py")
    assert sp.leases_overlap("src/**/schema.py", "src/foo/schema.py")
    assert sp.leases_overlap("src/foo/**", "src/foo/*.py")
    assert not sp.leases_overlap("src/a.py", "src/b.py")
    assert not sp.leases_overlap("tests/a_*.py", "src/a.py")


def test_parse_worktree_porcelain_normalizes_branch() -> None:
    parsed = sp.parse_worktree_porcelain(
        """worktree /repo
HEAD 1111111111111111111111111111111111111111
branch refs/heads/main

worktree /tmp/lane
HEAD 2222222222222222222222222222222222222222
detached
"""
    )

    assert parsed == [
        sp.Worktree(
            path="/repo",
            head="1111111111111111111111111111111111111111",
            branch="main",
            detached=False,
        ),
        sp.Worktree(
            path="/tmp/lane",
            head="2222222222222222222222222222222222222222",
            branch=None,
            detached=True,
        ),
    ]


def test_git_state_warns_when_local_main_differs_from_observed_origin(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local_main = "1" * 40
    origin_main = "2" * 40
    candidate = "0" * 40

    def fake_run(
        cmd: list[str],
        *,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, check
        key = tuple(cmd)
        outputs = {
            ("git", "rev-parse", "HEAD"): (0, "3" * 40 + "\n", ""),
            ("git", "rev-parse", "main"): (0, local_main + "\n", ""),
            ("git", "rev-parse", "--verify", "origin/main"): (
                0,
                origin_main + "\n",
                "",
            ),
            ("git", "worktree", "list", "--porcelain"): (0, "", ""),
            ("git", "merge-base", "--is-ancestor", candidate, local_main): (0, "", ""),
        }
        returncode, stdout, stderr = outputs[key]
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(sp, "_run", fake_run)

    state, warnings = sp._git_state(tmp_path, candidate)

    assert state["local_main_sha"] == local_main
    assert state["observed_origin_main_sha"] == origin_main
    assert state["base_relation"]["matches_observed_origin_main"] is False
    assert any("local main differs" in warning for warning in warnings)


def test_review_cycles_count_explicit_distinct_heads_and_surface_anomalies() -> None:
    reviews = [
        {
            "id": 1,
            "body": "Review Cycle 1 — CHANGES REQUESTED",
            "commit_id": "head-a",
            "state": "COMMENTED",
        },
        {
            "id": 2,
            "body": "Review Cycle 1 — repeated evidence note",
            "commit_id": "head-a",
            "state": "COMMENTED",
        },
        {
            "id": 3,
            "body": "Review Cycle 2 — APPROVE",
            "commit_id": "head-b",
            "state": "COMMENTED",
        },
        {
            "id": 4,
            "body": "ordinary review comment without formal label",
            "commit_id": "head-c",
            "state": "COMMENTED",
        },
    ]

    result = sp.summarize_review_cycles(reviews)

    assert result["count"] == 2
    assert result["distinct_head_shas"] == ["head-a", "head-b"]
    assert len(result["formal_entries"]) == 3
    assert result["anomalies"] == [
        {
            "kind": "multiple_formal_cycle_entries_same_head",
            "commit_id": "head-a",
            "review_ids": [1, 2],
        }
    ]


def test_review_cycle_reused_across_heads_is_an_anomaly() -> None:
    result = sp.summarize_review_cycles(
        [
            {"id": 1, "body": "Review Cycle 1", "commit_id": "head-a"},
            {"id": 2, "body": "Review Cycle 1", "commit_id": "head-b"},
        ]
    )

    assert result["count"] == 2
    assert result["anomalies"] == [
        {
            "kind": "cycle_label_reused_across_heads",
            "cycle_label": 1,
            "commit_ids": ["head-a", "head-b"],
        }
    ]


def test_find_conflicts_detects_pr_overlap_and_excludes_only_same_branch_pr() -> None:
    candidate = sp.Lane(
        kind="candidate",
        identity="candidate",
        branch="agent/candidate",
        paths=("src/shared.ts",),
    )
    other_pr = sp.Lane(
        kind="pr",
        identity="PR #1",
        branch="agent/other",
        paths=("src/shared.ts",),
    )
    same_branch_pr = sp.Lane(
        kind="pr",
        identity="PR #2",
        branch="agent/candidate",
        paths=("src/shared.ts",),
    )
    same_branch_handoff = sp.Lane(
        kind="handoff",
        identity="Docs/Plans/HANDOFF-BUILD-duplicate.md",
        branch="agent/candidate",
        paths=("src/shared.ts",),
    )

    conflicts = sp.find_conflicts(candidate, [other_pr, same_branch_pr, same_branch_handoff])

    assert conflicts == [
        sp.Conflict(
            candidate_path="src/shared.ts",
            other_path="src/shared.ts",
            lane_kind="pr",
            lane_identity="PR #1",
            branch="agent/other",
        ),
        sp.Conflict(
            candidate_path="src/shared.ts",
            other_path="src/shared.ts",
            lane_kind="handoff",
            lane_identity="Docs/Plans/HANDOFF-BUILD-duplicate.md",
            branch="agent/candidate",
        ),
    ]


def test_build_snapshot_blocks_on_pr_overlap_without_active_handoff(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handoff = _write_handoff(tmp_path / "Docs/Plans/HANDOFF-DOCUMENTS-candidate.md")
    monkeypatch.setattr(sp, "_git_state", lambda *_args, **_kwargs: (_git_snapshot(), []))
    monkeypatch.setattr(sp, "discover_active_handoff_lanes", lambda *_args: [])
    monkeypatch.setattr(sp, "_detect_repo_name", lambda _root: "owner/repo")

    remote_lane = sp.Lane(
        kind="pr",
        identity="PR #99",
        branch="agent/other",
        paths=("src/candidate.py",),
        provenance={"number": 99},
    )

    snapshot = sp.build_snapshot(
        handoff_path=handoff,
        repo_root=tmp_path,
        repo_name=None,
        local_only=False,
        pr_number=None,
        github_lane_reader=lambda _root, _repo: [remote_lane],
    )

    assert snapshot["status"] == "block"
    assert snapshot["github"]["complete"] is True
    assert snapshot["conflicts"][0]["lane_identity"] == "PR #99"
    assert snapshot["blockers"] == ["1 concrete write-lease overlap(s) detected"]


def test_github_unavailable_keeps_local_conflict_and_marks_remote_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handoff = _write_handoff(tmp_path / "Docs/Plans/HANDOFF-DOCUMENTS-candidate.md")
    local_lane = sp.Lane(
        kind="handoff",
        identity="Docs/Plans/HANDOFF-BUILD-other.md",
        branch="agent/other",
        paths=("src/candidate.py",),
    )
    monkeypatch.setattr(sp, "_git_state", lambda *_args, **_kwargs: (_git_snapshot(), []))
    monkeypatch.setattr(sp, "discover_active_handoff_lanes", lambda *_args: [local_lane])
    monkeypatch.setattr(sp, "_detect_repo_name", lambda _root: "owner/repo")

    def unavailable(_root: Path, _repo: str) -> list[sp.Lane]:
        raise RuntimeError("gh unavailable")

    snapshot = sp.build_snapshot(
        handoff_path=handoff,
        repo_root=tmp_path,
        repo_name=None,
        local_only=False,
        pr_number=None,
        github_lane_reader=unavailable,
    )

    assert snapshot["status"] == "block"
    assert snapshot["github"]["complete"] is False
    assert len(snapshot["conflicts"]) == 1
    assert "remote PR/review coverage is incomplete" in snapshot["warnings"][0]


def test_local_only_marks_remote_coverage_not_requested(tmp_path: Path, monkeypatch) -> None:
    handoff = _write_handoff(tmp_path / "Docs/Plans/HANDOFF-DOCUMENTS-candidate.md")
    monkeypatch.setattr(sp, "_git_state", lambda *_args, **_kwargs: (_git_snapshot(), []))
    monkeypatch.setattr(sp, "discover_active_handoff_lanes", lambda *_args: [])

    snapshot = sp.build_snapshot(
        handoff_path=handoff,
        repo_root=tmp_path,
        repo_name=None,
        local_only=True,
        pr_number=None,
    )

    assert snapshot["status"] == "pass"
    assert snapshot["github"]["requested"] is False
    assert snapshot["github"]["complete"] is None


def test_local_only_with_pr_warns_that_cycle_metadata_was_skipped(
    tmp_path: Path,
    monkeypatch,
) -> None:
    handoff = _write_handoff(tmp_path / "Docs/Plans/HANDOFF-DOCUMENTS-candidate.md")
    monkeypatch.setattr(sp, "_git_state", lambda *_args, **_kwargs: (_git_snapshot(), []))
    monkeypatch.setattr(sp, "discover_active_handoff_lanes", lambda *_args: [])

    snapshot = sp.build_snapshot(
        handoff_path=handoff,
        repo_root=tmp_path,
        repo_name=None,
        local_only=True,
        pr_number=574,
    )

    assert snapshot["status"] == "warn"
    assert snapshot["review_cycles"] is None
    assert "review-cycle metadata was skipped" in snapshot["warnings"][0]


def test_base_drift_is_warning_not_block(tmp_path: Path, monkeypatch) -> None:
    base = "a" * 40
    main = "c" * 40
    handoff = _write_handoff(
        tmp_path / "Docs/Plans/HANDOFF-DOCUMENTS-candidate.md",
        base=base,
    )
    warning = (
        "candidate base differs from local main; this is not automatically invalid, "
        "but the steward must re-check predecessor assumptions"
    )
    monkeypatch.setattr(
        sp,
        "_git_state",
        lambda *_args, **_kwargs: (_git_snapshot(base=base, main=main), [warning]),
    )
    monkeypatch.setattr(sp, "discover_active_handoff_lanes", lambda *_args: [])

    snapshot = sp.build_snapshot(
        handoff_path=handoff,
        repo_root=tmp_path,
        repo_name=None,
        local_only=True,
        pr_number=None,
    )

    assert snapshot["status"] == "warn"
    assert snapshot["blockers"] == []
    assert snapshot["git"]["base_relation"]["matches_local_main"] is False
    assert warning in snapshot["warnings"]


def test_empty_candidate_lease_blocks(tmp_path: Path, monkeypatch) -> None:
    handoff = _write_handoff(
        tmp_path / "Docs/Plans/HANDOFF-DOCUMENTS-candidate.md",
        lease=(),
    )
    monkeypatch.setattr(sp, "_git_state", lambda *_args, **_kwargs: (_git_snapshot(), []))
    monkeypatch.setattr(sp, "discover_active_handoff_lanes", lambda *_args: [])

    snapshot = sp.build_snapshot(
        handoff_path=handoff,
        repo_root=tmp_path,
        repo_name=None,
        local_only=True,
        pr_number=None,
    )

    assert snapshot["status"] == "block"
    assert snapshot["blockers"] == ["candidate §4 write lease is empty or unparseable"]
