#!/usr/bin/env python3
"""Safely reset local live-session artifacts created during dogfood runs."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

SESSION_DIR_ENV = "DUNGEONMIND_LIVE_SESSION_DIR"
GENERATED_CORPUS_REL = Path(
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated"
)
SESSION_DOGFOOD_DIRS = ("statblock_drafts", "statblock_retrieval")
CURRENT_COMBAT_REL = Path("combat/current_combat.json")


@dataclass(frozen=True)
class ResetPlan:
    session_dir: Path
    repo_root: Path
    session_targets: tuple[Path, ...]
    generated_corpus_targets: tuple[Path, ...]

    @property
    def targets(self) -> tuple[Path, ...]:
        return self.session_targets + self.generated_corpus_targets


def _resolve(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _refuse(condition: bool, message: str) -> None:
    if condition:
        raise ValueError(message)


def validate_session_dir(session_dir: Path, repo_root: Path) -> Path:
    resolved = _resolve(session_dir)
    root = _resolve(repo_root)
    home = _resolve(Path.home())

    _refuse(resolved == Path(resolved.anchor), "refusing to operate on filesystem root")
    _refuse(resolved == home, "refusing to operate on the home directory")
    _refuse(resolved == root, "refusing to operate on the repository root")
    _refuse(resolved == root / "evals", "refusing to operate on the evals parent directory")
    _refuse(resolved == root / "evals" / "c2_live_prep", "refusing to operate on the prep parent directory")
    _refuse(resolved == root / "evals" / "c2_live_prep" / "live", "refusing to operate on the live parent directory")
    _refuse(not resolved.exists(), f"session dir does not exist: {resolved}")
    _refuse(not resolved.is_dir(), f"session dir is not a directory: {resolved}")
    _refuse(not (resolved / "live_packet.json").is_file(), f"live_packet.json not found in session dir: {resolved}")
    return resolved


def generated_corpus_dir(repo_root: Path) -> Path:
    return _resolve(repo_root) / GENERATED_CORPUS_REL


def validate_generated_corpus_dir(path: Path, repo_root: Path) -> Path:
    expected = generated_corpus_dir(repo_root)
    resolved = _resolve(path)
    _refuse(resolved != expected, f"generated corpus path is outside the approved reset scope: {resolved}")
    _refuse(not _is_relative_to(resolved, _resolve(repo_root)), "generated corpus path is outside the repository")
    return resolved


def build_plan(
    *,
    session_dir: Path,
    repo_root: Path,
    purge_generated_corpus: bool = False,
) -> ResetPlan:
    root = _resolve(repo_root)
    safe_session_dir = validate_session_dir(session_dir, root)

    session_targets: list[Path] = []
    for dirname in SESSION_DOGFOOD_DIRS:
        target = safe_session_dir / dirname
        if target.exists():
            session_targets.append(target)

    current_combat = safe_session_dir / CURRENT_COMBAT_REL
    if current_combat.exists():
        session_targets.append(current_combat)

    generated_targets: list[Path] = []
    generated_dir = validate_generated_corpus_dir(generated_corpus_dir(root), root)
    if purge_generated_corpus and generated_dir.exists():
        generated_targets.extend(sorted(path for path in generated_dir.glob("*.md") if path.is_file()))

    return ResetPlan(
        session_dir=safe_session_dir,
        repo_root=root,
        session_targets=tuple(session_targets),
        generated_corpus_targets=tuple(generated_targets),
    )


def apply_plan(plan: ResetPlan) -> None:
    for target in plan.targets:
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    combat_dir = plan.session_dir / "combat"
    if combat_dir.exists() and combat_dir.is_dir() and not any(combat_dir.iterdir()):
        combat_dir.rmdir()


def _session_dir_from_args(value: str | None) -> Path:
    if value:
        return Path(value)
    env_value = os.environ.get(SESSION_DIR_ENV, "").strip()
    if env_value:
        return Path(env_value)
    raise ValueError(f"--session-dir is required unless {SESSION_DIR_ENV} is set")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", help=f"Live session directory; defaults to {SESSION_DIR_ENV}.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to the current working directory.")
    parser.add_argument("--apply", action="store_true", help="Actually delete planned targets. Default is dry-run.")
    parser.add_argument(
        "--purge-generated-corpus",
        action="store_true",
        help="Plan generated statblock markdown deletion from the approved generated corpus folder.",
    )
    parser.add_argument(
        "--yes-delete-generated-corpus",
        action="store_true",
        help="Second confirmation required with --purge-generated-corpus and --apply before corpus markdown is deleted.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.purge_generated_corpus and args.apply and not args.yes_delete_generated_corpus:
            raise ValueError(
                "--purge-generated-corpus with --apply also requires --yes-delete-generated-corpus"
            )
        session_dir = _session_dir_from_args(args.session_dir)
        plan = build_plan(
            session_dir=session_dir,
            repo_root=Path(args.repo_root),
            purge_generated_corpus=args.purge_generated_corpus,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"Mode: {mode}")
    print(f"Session dir: {plan.session_dir}")
    print(f"Generated corpus dir: {generated_corpus_dir(plan.repo_root)}")
    if not plan.targets:
        print("No dogfood artifacts found.")
        return 0

    if plan.generated_corpus_targets:
        print(
            "GENERATED CORPUS PURGE REQUESTED: "
            f"{len(plan.generated_corpus_targets)} markdown file(s) under the approved generated statblock folder."
        )
        if not args.apply:
            print("Corpus purge is dry-run only unless --apply is provided.")
        elif not args.yes_delete_generated_corpus:
            print("Corpus purge requires --yes-delete-generated-corpus with --apply.")

    print("Planned deletions:")
    for target in plan.targets:
        print(f"- {target}")

    if args.apply:
        apply_plan(plan)
        print("Reset complete.")
    else:
        print("Dry run only. Re-run with --apply to delete these paths.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
