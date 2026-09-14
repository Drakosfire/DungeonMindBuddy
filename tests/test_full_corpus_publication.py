from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("full_corpus_publication", ROOT / "tools" / "publish_full_corpus_world_graph.py")
assert spec and spec.loader
pub = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pub
spec.loader.exec_module(pub)


def test_both_candidate_arms_are_sealed_and_complete() -> None:
    for arm in pub.ARMS:
        seal = pub.verify_seal(arm)
        assert seal["candidate_count"] == 42
        assert seal["model_calls"] == 0
        assert [(r["campaign"], r["session"]) for r in seal["sessions"]] == pub.jobs()


@pytest.mark.parametrize("dsn", [
    "postgresql://x@localhost/full_corpus_live",
    "postgresql://x@localhost/eldyrwild_full_corpus",
    "postgresql://x@localhost/unlabelled",
])
def test_isolation_guard_refuses_non_rehearsal_authority(dsn: str) -> None:
    with pytest.raises(pub.PublicationError):
        pub.assert_isolated_dsn(dsn)


def test_isolation_guard_accepts_explicit_isolated_authority() -> None:
    pub.assert_isolated_dsn("postgresql://x@localhost/dungeonmind_full_corpus_openai")
