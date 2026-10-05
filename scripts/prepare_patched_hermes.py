#!/usr/bin/env python3
"""Prepare the exact pinned Hermes source patch for `uv sync --locked`.

The generated source is ignored under ``out/hermes-agent``. This script does
not install packages or edit site-packages. Run it before ``uv sync --locked``
from a fresh checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_REPOSITORY = "https://github.com/NousResearch/hermes-agent.git"
UPSTREAM_COMMIT = "861d69c7bba8d2ea6a1cd170e989c901c74d32d1"
PATCH_RELATIVE_PATH = Path("patches/hermes-agent/0001-pre-dispatch-budget-veto.patch")
OUTPUT_RELATIVE_PATH = Path("out/hermes-agent")
MANIFEST_RELATIVE_PATH = Path("out/hermes-agent-manifest.json")
MANIFEST_SCHEMA = "dmb_patched_hermes_source_v1"


class PreparationError(RuntimeError):
    pass


def _run_git(repo: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode:
        raise PreparationError(completed.stderr.strip() or f"git {args[0]} failed")
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_hash(repo: Path) -> str:
    _run_git(repo, "add", "-A")
    return _run_git(repo, "write-tree")


def _exclude_build_artifacts(repo: Path) -> None:
    """Keep setuptools' in-source build output out of the source identity."""
    exclude_path = Path(_run_git(repo, "rev-parse", "--git-path", "info/exclude"))
    if not exclude_path.is_absolute():
        exclude_path = repo / exclude_path
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    marker = "# DungeonMindBuddy generated Hermes build artifacts\n/build/\n"
    if marker not in existing:
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        exclude_path.write_text(existing + ("\n" if existing and not existing.endswith("\n") else "") + marker)


def _verify_generated(
    *, output: Path, manifest_path: Path, expected_patch_sha256: str
) -> dict[str, str]:
    if not output.is_dir() or not manifest_path.is_file():
        raise PreparationError(
            "Patched Hermes source is not prepared. Run `python3 scripts/prepare_patched_hermes.py` before `uv sync --locked`."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreparationError("Patched Hermes manifest is unreadable; rerun the prepare script.") from exc
    if (
        manifest.get("schema") != MANIFEST_SCHEMA
        or manifest.get("upstream_commit") != UPSTREAM_COMMIT
        or manifest.get("patch_sha256") != expected_patch_sha256
        or _run_git(output, "rev-parse", "HEAD") != UPSTREAM_COMMIT
    ):
        raise PreparationError("Prepared Hermes source does not match the pinned source/patch; rerun the prepare script.")
    diff = subprocess.run(
        ["git", "-C", str(output), "diff", "--quiet"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if diff.returncode != 0:
        raise PreparationError("Prepared Hermes source has local edits; preserve it and investigate before syncing.")
    if _tree_hash(output) != manifest.get("tree_sha"):
        raise PreparationError("Prepared Hermes source tree hash changed; rerun the prepare script.")
    if manifest.get("tree_sha") != manifest.get("expected_tree_sha"):
        raise PreparationError("Prepared Hermes manifest tree identities disagree.")
    return manifest


def prepare(repo_root: Path, *, upstream_repository: str = UPSTREAM_REPOSITORY) -> dict[str, str]:
    patch_path = repo_root / PATCH_RELATIVE_PATH
    output = repo_root / OUTPUT_RELATIVE_PATH
    manifest_path = repo_root / MANIFEST_RELATIVE_PATH
    if not patch_path.is_file():
        raise PreparationError(f"Required checked-in patch is missing: {patch_path}")
    patch_sha = _sha256(patch_path)
    if output.exists() or manifest_path.exists():
        if not output.is_dir() or not manifest_path.is_file():
            raise PreparationError(
                "A generated Hermes path exists without its manifest; preserve it and inspect it manually."
            )
        try:
            old = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PreparationError("Generated Hermes manifest is unreadable; preserve the path for inspection.") from exc
        if old.get("schema") != MANIFEST_SCHEMA:
            raise PreparationError("Generated Hermes path is not owned by this script; refusing to replace it.")
        if old.get("patch_sha256") == patch_sha:
            return _verify_generated(
                output=output,
                manifest_path=manifest_path,
                expected_patch_sha256=patch_sha,
            )
        _verify_generated(
            output=output,
            manifest_path=manifest_path,
            expected_patch_sha256=old.get("patch_sha256", ""),
        )

    out_parent = output.parent
    out_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hermes-prepare-", dir=out_parent) as temp_name:
        candidate = Path(temp_name) / "source"
        init = subprocess.run(
            ["git", "init", str(candidate)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if init.returncode:
            raise PreparationError(init.stderr.strip() or "Could not initialize temporary Hermes checkout.")
        _run_git(candidate, "remote", "add", "origin", upstream_repository)
        fetched = subprocess.run(
            [
                "git",
                "-C",
                str(candidate),
                "-c",
                "protocol.file.allow=always",
                "fetch",
                "--depth=1",
                "--filter=blob:none",
                "origin",
                UPSTREAM_COMMIT,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if fetched.returncode:
            raise PreparationError(
                "Could not fetch the pinned Hermes source commit; no generated source was installed. "
                + (fetched.stderr.strip() or "")
            )
        _run_git(candidate, "checkout", "--detach", "FETCH_HEAD")
        source_commit = _run_git(candidate, "rev-parse", "HEAD")
        if source_commit != UPSTREAM_COMMIT:
            raise PreparationError(f"Fetched Hermes source {source_commit} does not match pinned commit.")
        if _run_git(candidate, "status", "--porcelain", "--untracked-files=all"):
            raise PreparationError("Fresh Hermes checkout is not clean before patch application.")
        check = subprocess.run(
            ["git", "-C", str(candidate), "apply", "--check", str(patch_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if check.returncode:
            raise PreparationError("Checked-in Hermes patch does not apply cleanly: " + check.stderr.strip())
        applied = subprocess.run(
            ["git", "-C", str(candidate), "apply", str(patch_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode:
            raise PreparationError("Could not apply checked-in Hermes patch: " + applied.stderr.strip())
        _exclude_build_artifacts(candidate)
        tree_sha = _tree_hash(candidate)
        clean_worktree = subprocess.run(
            ["git", "-C", str(candidate), "diff", "--quiet"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if clean_worktree.returncode:
            raise PreparationError("Patched Hermes working tree differs from its prepared index.")
        candidate_manifest = {
            "schema": MANIFEST_SCHEMA,
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit": source_commit,
            "patch_sha256": patch_sha,
            "tree_sha": tree_sha,
            "expected_tree_sha": tree_sha,
        }
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(candidate), str(output))
        manifest_path.write_text(
            json.dumps(candidate_manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return _verify_generated(
        output=output,
        manifest_path=manifest_path,
        expected_patch_sha256=patch_sha,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify an existing prepared source without fetching")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if args.verify:
            patch_sha = _sha256(repo_root / PATCH_RELATIVE_PATH)
            manifest = _verify_generated(
                output=repo_root / OUTPUT_RELATIVE_PATH,
                manifest_path=repo_root / MANIFEST_RELATIVE_PATH,
                expected_patch_sha256=patch_sha,
            )
        else:
            manifest = prepare(repo_root)
    except PreparationError as exc:
        print(f"prepare_patched_hermes: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
