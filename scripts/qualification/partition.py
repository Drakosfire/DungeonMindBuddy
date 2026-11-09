"""Versioned full-suite execution buckets, never changed-file test selection."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSION = 1
PARTITIONS = 4
DEFAULT_DESELECTIONS = 36


def bucket(path: str) -> int:
    value = PurePosixPath(path)
    if (value.is_absolute() or not value.parts or value.parts[0] != "tests"
            or ".." in value.parts or "\\" in path or str(value) != path or value.suffix != ".py"):
        raise ValueError(f"unsupported collected file: {path}")
    return int.from_bytes(hashlib.sha256(path.encode("utf-8")).digest()[:8], "big") % PARTITIONS


def plan(nodeids: list[str]) -> list[list[str]]:
    if not nodeids or len(set(nodeids)) != len(nodeids):
        raise ValueError("empty or duplicate unpartitioned collection")
    groups = [[] for _ in range(PARTITIONS)]
    for nodeid in nodeids:
        if "::" not in nodeid:
            raise ValueError(f"unsupported collected case: {nodeid}")
        groups[bucket(nodeid.split("::", 1)[0])].append(nodeid)
    if Counter(node for group in groups for node in group) != Counter(nodeids):
        raise ValueError("partition union differs from actual collection")
    return groups


def report(index: int, nodeids: list[str], default_deselected: list[str], sha: str, *, collection_only: bool = False) -> dict:
    if type(index) is not int or index not in range(PARTITIONS):
        raise ValueError("invalid qualification partition")
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise ValueError("qualification source must be an exact SHA")
    if type(collection_only) is not bool:
        raise ValueError("invalid collection-only mode")
    groups = plan(nodeids)
    if not groups[index]:
        raise ValueError("empty qualification partition")
    if len(default_deselected) != DEFAULT_DESELECTIONS or len(set(default_deselected)) != DEFAULT_DESELECTIONS:
        raise ValueError("default deselection contract changed")
    if set(default_deselected) & set(nodeids):
        raise ValueError("default deselection overlaps selected collection")
    return {"version": VERSION, "partitions": PARTITIONS, "index": index, "source_sha": sha, "collection_only": collection_only,
            "unpartitioned_nodeids": nodeids, "selected_nodeids": groups[index],
            "default_deselected_nodeids": default_deselected,
            "partition_counts": [len(group) for group in groups]}


def verify_reports(reports: list[dict], *, expected_sha: str | None = None, collection_only_proof: bool = False) -> dict:
    if len(reports) != PARTITIONS or sorted(r["index"] for r in reports) != list(range(PARTITIONS)):
        raise ValueError("missing or duplicate partition reports")
    reference = reports[0]
    if expected_sha is not None and reference["source_sha"] != expected_sha:
        raise ValueError("partition source differs from verifier checkout")
    files = Counter(n.split("::", 1)[0] for n in reference["unpartitioned_nodeids"])
    # Only generated UUID parameter labels can differ across same-SHA jobs.
    # Selection and the exact per-collection union never normalize node IDs.
    def label_shape(nodeid):
        prefix, separator, parameters = nodeid.partition("[")
        return prefix + separator + re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "<generated-uuid>", parameters,
        )
    shapes = Counter(map(label_shape, reference["unpartitioned_nodeids"]))
    selected_files: Counter = Counter()
    for item in reports:
        if (type(item["version"]) is not int or item["version"] != VERSION
                or type(item["partitions"]) is not int or item["partitions"] != PARTITIONS):
            raise ValueError("partition contract version changed")
        if item["source_sha"] != reference["source_sha"]:
            raise ValueError("partition sources differ")
        if item["collection_only"] and not collection_only_proof:
            raise ValueError("collection-only diagnostic cannot qualify execution")
        expected = report(item["index"], item["unpartitioned_nodeids"],
                          item["default_deselected_nodeids"], item["source_sha"], collection_only=item["collection_only"])
        if item != expected:
            raise ValueError("partition report differs from actual collection plan")
        if Counter(item["default_deselected_nodeids"]) != Counter(reference["default_deselected_nodeids"]):
            raise ValueError("default deselections differ")
        if (Counter(n.split("::", 1)[0] for n in item["unpartitioned_nodeids"]) != files
                or Counter(map(label_shape, item["unpartitioned_nodeids"])) != shapes):
            raise ValueError("unpartitioned file/parameter collections differ")
        selected_files.update(n.split("::", 1)[0] for n in item["selected_nodeids"])
    if selected_files != files:
        raise ValueError("assigned file union differs from full collection")
    return {"source_sha": reference["source_sha"], "version": VERSION,
            "unpartitioned_cases": sum(files.values()), "files": len(files),
            "partition_counts": [len(r["selected_nodeids"]) for r in sorted(reports, key=lambda r: r["index"])],
            "default_deselections": DEFAULT_DESELECTIONS, "omissions": 0, "duplicates": 0,
            "collection_only_proof": collection_only_proof}


def source_sha() -> str:
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("qualification collection requires clean committed source")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def pytest_addoption(parser):
    group = parser.getgroup("full qualification")
    group.addoption("--qualification-partition", type=int, default=None)
    group.addoption("--qualification-report", default=None)


def reviewed_cli(config) -> bool:
    # The production runner has fixed argv. Allow its output/isolation flags
    # and explicit collection diagnostics, never an unknown plugin selector.
    arguments = getattr(getattr(config, "invocation_params", None), "args", ())
    switches = {"--collect-only", "--co", "--disable-warnings", "--strict-config", "--strict-markers", "-s", "--full-trace"}
    values = {"-p", "--qualification-partition", "--qualification-report", "--durations", "--durations-min",
              "--junitxml", "--junit-xml", "--basetemp", "-o", "--override-ini", "--tb", "--show-capture",
              "--capture", "--color", "-m"}
    position = 0
    while position < len(arguments):
        argument = str(arguments[position])
        name = argument.split("=", 1)[0]
        if name in values:
            position += 1 if "=" in argument else 2
        elif argument == "tests" or argument in switches or re.fullmatch(r"-[qv]+", argument):
            position += 1
        else:
            return False
    return position == len(arguments)


def pytest_configure(config):
    index = config.getoption("qualification_partition")
    output = config.getoption("qualification_report")
    if index is None and output is None:
        return
    if index not in range(PARTITIONS) or not output:
        raise pytest.UsageError("qualification requires an index 0..3 and a report path")
    if any(os.environ.get(name) for name in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD")):
        raise pytest.UsageError("qualification forbids inherited pytest selection/plugin options")
    forbidden = ("ignore", "ignore_glob", "confcutdir", "noconftest", "pyargs", "doctestmodules", "doctestglob",
                 "continue_on_collection_errors", "maxfail", "stepwise", "stepwise_skip", "disable_plugin_autoload")
    overrides = getattr(config.option, "override_ini", None) or []
    plugins = getattr(config.option, "plugins", None) or []
    if (not reviewed_cli(config) or config.args != ["tests"] or config.option.markexpr != "not live_llm"
            or config.option.keyword or config.option.deselect or config.option.lf
            or any(getattr(config.option, name, None) for name in forbidden)
            or getattr(config.option, "importmode", "prepend") != "prepend"
            or any(value.split("=", 1)[0] not in {"cache_dir", "faulthandler_timeout"} for value in overrides)
            or any(name not in {"scripts.qualification.partition", "tests.application_state.isolate_dsn"} for name in plugins)
            or Path(getattr(config, "rootpath", ROOT)).resolve() != ROOT
            or Path(getattr(config, "inipath", ROOT / "pyproject.toml")).resolve() != ROOT / "pyproject.toml"):
        raise pytest.UsageError("qualification partitions require the full default tests collection without discovery overrides")
    config._qualification_default_deselected = []
    config._qualification_partitioning = False


def pytest_deselected(items):
    if not items:
        return
    config = items[0].config
    if hasattr(config, "_qualification_default_deselected") and not config._qualification_partitioning:
        config._qualification_default_deselected.extend(item.nodeid for item in items)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    index = config.getoption("qualification_partition")
    if index is None:
        return
    try:
        for item in items:
            actual = item.path.resolve().relative_to(ROOT).as_posix()
            if actual != item.nodeid.split("::", 1)[0]:
                raise ValueError("collected path differs from node identity")
        sha = source_sha()
        result = report(index, [item.nodeid for item in items], config._qualification_default_deselected, sha,
                        collection_only=config.option.collectonly)
        selected = set(result["selected_nodeids"])
        removed = [item for item in items if item.nodeid not in selected]
        items[:] = [item for item in items if item.nodeid in selected]
        output = Path(config.getoption("qualification_report"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
        config._qualification_partitioning = True
        try:
            config.hook.pytest_deselected(items=removed)
        finally:
            config._qualification_partitioning = False
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise pytest.UsageError(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--collection-only-proof", action="store_true", help="diagnostic parity only; never execution qualification")
    args = parser.parse_args()
    reports = [json.loads(path.read_text()) for path in sorted(args.directory.rglob("collection.json"))]
    try:
        result = verify_reports(reports, expected_sha=source_sha(), collection_only_proof=args.collection_only_proof)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
