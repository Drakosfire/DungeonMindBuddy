"""Isolated local frontend evidence; never substitutes an unrecorded working tree."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
NODE = "v22.23.0"
NPM = "10.9.8"
LOCK = Path(f"/tmp/dungeonmind-frontend-verification-{os.getuid()}.lock")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def resource_lock(path=LOCK):
    # Never unlink a lock inode: waiting/new processes must use the same inode.
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            raise ValueError("resource lock has a foreign owner")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(
                "another local frontend verification owns the resource lock"
            ) from exc
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps({"pid": os.getpid()}).encode())
        yield
    finally:
        os.close(fd)


def resources(workers, available=None, cpu=None, proc=Path("/proc")):
    if not 1 <= workers <= 32:
        raise ValueError("workers must be between 1 and 32")
    cpu = os.cpu_count() if cpu is None else cpu
    if not cpu or workers > cpu:
        raise ValueError("worker count exceeds visible logical CPUs")
    if available is None:
        memory = dict(
            line.split(":", 1) for line in (proc / "meminfo").read_text().splitlines()
        )
        available = int(memory["MemAvailable"].split()[0]) * 1024
    if available < max(4, workers) * 1024**3:
        raise ValueError("insufficient available memory for requested workers")
    competitors = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            raw = (entry / "cmdline").read_bytes().split(b"\0")
            # Check actual argv, not command text embedded in a shell or editor.
            if raw and (
                (
                    Path(os.fsdecode(raw[0])).name in {"node", "nodejs"}
                    and any(b"vitest" in arg for arg in raw[1:3])
                )
                or raw[0].startswith(b"node (vitest")
            ):
                competitors.append(int(entry.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    if competitors:
        raise ValueError(f"competing Vitest processes visible: {competitors}")
    return {
        "logical_cpus": cpu,
        "available_memory_bytes": available,
        "workers": workers,
        "visible_competing_vitest_pids": competitors,
        "scope": "per-user global advisory lock and visible process namespace; other tools must honor the lock",
    }


def group_alive(pgid):
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != "Z":
                return True
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return False


def stop_group(pgid):
    # A direct parent's exit is not proof that its grandchildren exited.
    for sig, grace in ((signal.SIGTERM, 2), (signal.SIGKILL, 5)):
        if not group_alive(pgid):
            return
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + grace
        while group_alive(pgid) and time.monotonic() < deadline:
            time.sleep(0.05)
    if group_alive(pgid):
        raise RuntimeError(f"owned process group {pgid} failed to stop")


def command(argv, cwd, log, env):
    started = time.monotonic()
    with Path(log).open("w") as stream:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = proc.wait(timeout=1800)
        finally:
            stop_group(proc.pid)
            proc.wait(timeout=10)
    return {
        "argv": argv,
        "exit_code": code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "log": Path(log).name,
    }


def frontend_plan(catalog, suite):
    steps = catalog["contracts"]["hosted-frontend"]["steps"]
    if catalog["version"] != 1 or any(
        step["cwd"] != "apps/live-control-ui" for step in steps
    ):
        raise ValueError("unsupported frontend contract")
    install = [step["argv"] for step in steps if step["argv"] == ["npm", "ci"]]
    build = [step["argv"] for step in steps if step["argv"] == ["npm", "run", "build"]]
    tests = [
        step["argv"] for step in steps if step["argv"][:3] == ["npm", "test", "--"]
    ]
    if (
        len(install) != 1
        or len(build) != 1
        or len(tests) + 2 != len(steps)
        or not tests
    ):
        raise ValueError(
            "unclassified shared frontend command; update the verifier before running"
        )
    # Default discovery uses the SAME npm test script, without hosted allowlist filters.
    return (
        install[0],
        ([["npm", "test", "--"]] if suite == "discovered" else tests),
        build[0],
    )


def inventory_keys(items, frontend):
    return Counter(
        (str(Path(item["file"]).relative_to(frontend)), item["name"]) for item in items
    )


def result_keys(result, frontend):
    return Counter(
        (
            str(Path(file["name"]).relative_to(frontend)),
            " > ".join([*case["ancestorTitles"], case["title"]]),
        )
        for file in result["testResults"]
        for case in file["assertionResults"]
    )


def case_parity(expected, result, frontend, argv):
    actual = result_keys(result, frontend)
    skipped = Counter()
    failed = 0
    for file in result["testResults"]:
        for case in file["assertionResults"]:
            key = (
                str(Path(file["name"]).relative_to(frontend)),
                " > ".join([*case["ancestorTitles"], case["title"]]),
            )
            if case["status"] in {"skipped", "pending", "todo"}:
                skipped[key] += 1
            if case["status"] == "failed":
                failed += 1
    extra = actual - expected
    filtered = any(
        arg in {"-t", "--testNamePattern"} or arg.startswith("--testNamePattern=")
        for arg in argv
    )
    # Existing hosted name filters report unselected skipped cases in Vitest JSON.
    # Default discovery permits no invented exclusion or additional case.
    allowed = (
        filtered and not (extra - skipped) and not any(key in expected for key in extra)
    )
    return {
        "collection_parity": bool(expected)
        and not (expected - actual)
        and (not extra or allowed),
        "reported_unselected_skips": sum(extra.values()) if allowed else 0,
        "failed_cases": failed,
    }


def validate(report_path, expected_sha, suite, max_age=86400):
    path = Path(report_path)
    report = json.loads(path.read_text())
    if (
        report["version"] != 1
        or report["verified_sha"] != expected_sha
        or report["suite"] != suite
    ):
        raise ValueError("stale or mismatched source/suite evidence")
    receipt_path = path.parent / "run-receipt.json"
    if report["artifacts"].get(receipt_path.name) != digest(receipt_path) or json.loads(
        receipt_path.read_text()
    ) != {key: value for key, value in report.items() if key != "artifacts"}:
        raise ValueError("run receipt/source provenance mismatch")
    provenance_path = path.parent / "source-provenance.json"
    if report["artifacts"].get(provenance_path.name) != digest(provenance_path):
        raise ValueError("unbound source provenance")
    provenance = json.loads(provenance_path.read_text())
    if (
        provenance["sha"],
        provenance["suite"],
        provenance["runner_sha"],
        provenance["frontend_path"],
        provenance["workers"],
    ) != (
        expected_sha,
        suite,
        report["runner_sha"],
        report["source_frontend_path"],
        report["workers"],
    ):
        raise ValueError("source or suite provenance mismatch")
    raw_catalog = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{expected_sha}:ci/contracts.json"]
    )
    raw_lock = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "show",
            f"{expected_sha}:apps/live-control-ui/package-lock.json",
        ]
    )
    if (
        hashlib.sha256(raw_catalog).hexdigest() != report["contract_sha256"]
        or hashlib.sha256(raw_lock).hexdigest() != report["package_lock_sha256"]
    ):
        raise ValueError("source contract/lockfile mismatch")
    install, planned_tests, build = frontend_plan(json.loads(raw_catalog), suite)
    if len(planned_tests) != len(report["tests"]) or report["build"]["argv"] != build:
        raise ValueError("source command plan mismatch")
    workers = [f"--maxWorkers={report['workers']}", f"--minWorkers={report['workers']}"]
    for expected, step in zip(planned_tests, report["tests"], strict=True):
        result_file = str(Path(provenance["output_dir"]) / step["results_file"])
        if step["argv"] != [
            *expected,
            *workers,
            "--reporter=json",
            f"--outputFile={result_file}",
        ]:
            raise ValueError("test command mismatch")
    age = time.time() - report["finished_unix"]
    if age < -60 or age > max_age:
        raise ValueError("stale evidence timestamp")
    if (
        report["mode"] != "isolated-exact-sha"
        or report["runner_dirty"]
        or report["source_dirty_before"]
        or report["source_dirty_after"]
    ):
        raise ValueError(
            "working-tree diagnostics cannot qualify exact-SHA verification"
        )
    if not report["cleanup_complete"] or report["error"] or report["exit_code"] != 0:
        raise ValueError("incomplete or failed verification")
    if report["node"] != NODE or report["npm"] != NPM:
        raise ValueError("tool version mismatch")
    if (
        not report["tests"]
        or any(
            step["exit_code"]
            or not step["collection_parity"]
            or step.get("failed_cases", 0)
            for step in report["tests"]
        )
        or not report["build"]
        or report["build"]["exit_code"] != 0
    ):
        raise ValueError("test/build failure")
    for name, expected in report["artifacts"].items():
        if Path(name).name != name or digest(path.parent / name) != expected:
            raise ValueError("missing or mismatched evidence artifact")
    frontend = Path(report["source_frontend_path"])
    for step in report["tests"]:
        names = [step["inventory_file"], step["results_file"]]
        if any(
            Path(name).name != name or name not in report["artifacts"] for name in names
        ):
            raise ValueError("unbound test evidence")
        expected = inventory_keys(
            json.loads((path.parent / names[0]).read_text()), frontend
        )
        parity = case_parity(
            expected,
            json.loads((path.parent / names[1]).read_text()),
            frontend,
            step["argv"],
        )
        if (
            not expected
            or not parity["collection_parity"]
            or parity["failed_cases"]
            or sum(expected.values()) != step["discovered_cases"]
        ):
            raise ValueError("discovery/result mismatch")
    return report


def verify(args):
    repo = Path(args.repo).resolve()
    if (
        not re.fullmatch(r"[0-9a-f]{40}", args.sha)
        or git(repo, "rev-parse", args.sha + "^{commit}") != args.sha
    ):
        raise ValueError("a full existing commit SHA is required")
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {
        "version": 1,
        "verified_sha": args.sha,
        "runner_sha": git(ROOT, "rev-parse", "HEAD"),
        "runner_dirty": bool(git(ROOT, "status", "--porcelain")),
        "caller_dirty": bool(git(repo, "status", "--porcelain")),
        "suite": args.suite,
        "workers": args.workers,
        "tests": [],
        "build": None,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "test_exit_code": None,
        "build_exit_code": None,
        "source_dirty_before": None,
        "source_dirty_after": None,
        "cleanup_complete": False,
        "error": None,
        "exit_code": 1,
        "artifacts": {},
        "hosted_gate_replacement": False,
    }
    report["mode"] = (
        "working-tree-diagnostic" if report["runner_dirty"] else "isolated-exact-sha"
    )
    env = dict(os.environ)
    forbidden = [
        key
        for key in env
        if key.startswith("VITEST") or key in {"NODE_OPTIONS", "npm_config_argv"}
    ]
    source = None
    with ExitStack() as stack:
        try:
            stack.enter_context(resource_lock())
            if forbidden:
                raise ValueError(f"inherited test controls forbidden: {forbidden}")
            report["resources"] = resources(args.workers)
            report["node"] = subprocess.check_output(
                ["node", "--version"], text=True
            ).strip()
            report["npm"] = subprocess.check_output(
                ["npm", "--version"], text=True
            ).strip()
            if (report["node"], report["npm"]) != (NODE, NPM):
                raise ValueError(f"require Node {NODE} and npm {NPM}")
            with tempfile.TemporaryDirectory(prefix="dmb-local-frontend-") as temp:
                source = Path(temp) / "source"
                try:
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(repo),
                            "worktree",
                            "add",
                            "--detach",
                            str(source),
                            args.sha,
                        ],
                        check=True,
                    )
                    frontend = source / "apps/live-control-ui"
                    report["source_frontend_path"] = str(frontend)
                    report["source_dirty_before"] = bool(
                        git(source, "status", "--porcelain")
                    )
                    report["package_lock_sha256"] = digest(
                        frontend / "package-lock.json"
                    )
                    report["contract_sha256"] = digest(source / "ci/contracts.json")
                    install, tests, build = frontend_plan(
                        json.loads((source / "ci/contracts.json").read_text()),
                        args.suite,
                    )
                    (out / "source-provenance.json").write_text(
                        json.dumps(
                            {
                                "sha": git(source, "rev-parse", "HEAD"),
                                "suite": args.suite,
                                "runner_sha": report["runner_sha"],
                                "frontend_path": str(frontend),
                                "workers": args.workers,
                                "output_dir": str(out),
                            },
                            indent=2,
                        )
                        + "\n"
                    )
                    for name in ("npm-user-config", "npm-global-config"):
                        (out / name).write_text("")
                    report["install"] = command(
                        [
                            *install,
                            f"--userconfig={out / 'npm-user-config'}",
                            f"--globalconfig={out / 'npm-global-config'}",
                        ],
                        frontend,
                        out / "install.log",
                        env,
                    )
                    if report["install"]["exit_code"]:
                        raise ValueError("locked dependency installation failed")
                    report["vitest"] = json.loads(
                        (frontend / "node_modules/vitest/package.json").read_text()
                    )["version"]
                    worker_args = [
                        f"--maxWorkers={args.workers}",
                        f"--minWorkers={args.workers}",
                    ]
                    for index, test in enumerate(tests):
                        selected = test[3:]
                        inventory = out / f"inventory-{index}.json"
                        listing = command(
                            [
                                "node",
                                "node_modules/vitest/vitest.mjs",
                                "list",
                                f"--json={inventory}",
                                *selected,
                                *worker_args,
                            ],
                            frontend,
                            out / f"inventory-{index}.log",
                            env,
                        )
                        try:
                            keys = (
                                inventory_keys(
                                    json.loads(inventory.read_text()), frontend
                                )
                                if listing["exit_code"] == 0
                                else Counter()
                            )
                        except (ValueError, KeyError):
                            keys = Counter()
                        result_path = out / f"results-{index}.json"
                        result = command(
                            [
                                *test,
                                *worker_args,
                                "--reporter=json",
                                f"--outputFile={result_path}",
                            ],
                            frontend,
                            out / f"tests-{index}.log",
                            env,
                        )
                        result["inventory_file"] = inventory.name
                        result["results_file"] = result_path.name
                        result["discovered_cases"] = sum(keys.values())
                        try:
                            result.update(
                                case_parity(
                                    keys,
                                    json.loads(result_path.read_text()),
                                    frontend,
                                    result["argv"],
                                )
                            )
                        except (OSError, ValueError, KeyError):
                            result["collection_parity"] = False
                        report["tests"].append(result)
                    # Even assertion failures must not suppress build/type evidence.
                    report["build"] = command(build, frontend, out / "build.log", env)
                    report["build_exit_code"] = report["build"]["exit_code"]
                    report["test_exit_code"] = next(
                        (
                            step["exit_code"]
                            for step in report["tests"]
                            if step["exit_code"]
                        ),
                        int(
                            any(
                                not step["collection_parity"]
                                or step.get("failed_cases", 0)
                                for step in report["tests"]
                            )
                        ),
                    )
                    report["source_dirty_after"] = bool(
                        git(source, "status", "--porcelain")
                    )
                    if (
                        digest(frontend / "package-lock.json")
                        != report["package_lock_sha256"]
                    ):
                        raise ValueError("lockfile changed during verification")
                    report["exit_code"] = int(
                        report["runner_dirty"]
                        or report["source_dirty_before"]
                        or report["source_dirty_after"]
                        or any(
                            step["exit_code"]
                            or not step["collection_parity"]
                            or step.get("failed_cases", 0)
                            for step in report["tests"]
                        )
                        or report["build"]["exit_code"] != 0
                    )
                finally:
                    if source.exists():
                        subprocess.run(
                            [
                                "git",
                                "-C",
                                str(repo),
                                "worktree",
                                "remove",
                                "--force",
                                str(source),
                            ],
                            check=True,
                        )
                    report["cleanup_complete"] = not source.exists()
        except (Exception, KeyboardInterrupt) as exc:
            report["error"] = str(exc) or type(exc).__name__
            report["exit_code"] = 1
        finally:
            report["finished_unix"] = time.time()
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            (out / "run-receipt.json").write_text(
                json.dumps(
                    {key: value for key, value in report.items() if key != "artifacts"},
                    indent=2,
                )
                + "\n"
            )
            report["artifacts"] = {
                p.name: digest(p) for p in out.iterdir() if p.is_file()
            }
            (out / "evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    return report["exit_code"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--repo", default=str(ROOT))
    run.add_argument("--sha", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--suite", choices=["discovered", "hosted"], default="discovered")
    run.add_argument("--workers", type=int, default=8)
    check = sub.add_parser("validate")
    check.add_argument("evidence")
    check.add_argument("--sha", required=True)
    check.add_argument("--suite", choices=["discovered", "hosted"], required=True)
    args = parser.parse_args()
    old_handler = signal.signal(
        signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError("terminated"))
    )
    try:
        if args.action == "validate":
            validate(args.evidence, args.sha, args.suite)
            return 0
        return verify(args)
    except (ValueError, OSError, subprocess.SubprocessError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, old_handler)


if __name__ == "__main__":
    raise SystemExit(main())
