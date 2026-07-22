from __future__ import annotations

import pytest

from graph_memory.source_span import build_stable_source_span_id


def test_stable_span_id_is_namespaced_by_artifact_digest() -> None:
    span_id = build_stable_source_span_id(
        source_artifact_id="artifact:worldbuilding:doc:r2:abcdef",
        content_sha256="abcdef0123456789",
        start_line=3,
        end_line=5,
    )
    assert span_id.startswith("artifact:worldbuilding:doc:r2:abcdef:span:abcdef012345:")
    assert span_id.endswith(":3-5")


def test_stable_span_id_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        build_stable_source_span_id(
            source_artifact_id="artifact:x",
            content_sha256="abc",
            start_line=5,
            end_line=2,
        )
