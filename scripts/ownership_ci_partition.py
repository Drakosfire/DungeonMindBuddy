"""Split only the slow ordinary Build module across existing isolated CI jobs.

SHA-256 of the complete pytest ID is stable across processes/Python versions.
Every possible ID has exactly one owner; new parameter cases need no manifest edit.
All other modules retain their existing ownership and fixtures.
"""

import hashlib

MODULE = "tests/test_surface_native_build_ordinary.py"
BUCKET_OWNERS = (
    "world-and-content",
    "ingestion-and-review",
    "saved-page-readers",
    "world-and-content",
)
SUITES = (*dict.fromkeys(BUCKET_OWNERS), "query-and-answer")


def owner(nodeid: str) -> str:
    bucket = int(hashlib.sha256(nodeid.encode()).hexdigest(), 16) % len(BUCKET_OWNERS)
    return BUCKET_OWNERS[bucket]


def pytest_addoption(parser):
    parser.addoption("--ownership-suite", choices=SUITES, default=None)


def pytest_collection_modifyitems(config, items):
    suite = config.getoption("--ownership-suite")
    if suite is None:
        return
    kept, deselected = [], []
    for item in items:
        target = item.nodeid.split("::", 1)[0] == MODULE
        (deselected if target and owner(item.nodeid) != suite else kept).append(item)
    items[:] = kept
    if deselected:
        config.hook.pytest_deselected(items=deselected)
