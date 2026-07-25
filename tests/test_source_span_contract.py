from __future__ import annotations

import hashlib

import pytest

from graph_memory.source_span import (
    build_source_span_index_for_text,
    build_stable_source_span_id,
    source_artifact_text_from_markdown,
    source_span_index_from_dict,
    source_span_index_to_dict,
    source_span_refs_from_index,
    validate_source_span_ref_for_artifact,
    resolve_source_span_ref,
)


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


def test_span_index_round_trip_and_resolution() -> None:
    text = "# Lore\n\nBody paragraph.\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    artifact_id = "artifact:worldbuilding:doc:r1:" + digest[:12]
    index = build_source_span_index_for_text(
        source_artifact_id=artifact_id,
        content_sha256=digest,
        text=text,
    )
    assert index.content_sha256 == digest
    assert index.source_artifact_id == artifact_id
    assert len(index.spans) >= 1

    restored = source_span_index_from_dict(source_span_index_to_dict(index))
    ref = source_span_refs_from_index(restored)[0]
    validate_source_span_ref_for_artifact(
        ref,
        source_artifact_id=artifact_id,
        content_sha256=digest,
    )
    text_artifact = source_artifact_text_from_markdown(
        source_artifact_id=artifact_id,
        text=text,
    )
    evidence = resolve_source_span_ref(
        ref,
        text_artifacts={artifact_id: text_artifact},
    )
    assert evidence.can_highlight_span is True
    assert evidence.preview_snippet


def test_span_ref_rejects_digest_namespace_mismatch() -> None:
    text = "Body\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    artifact_id = "artifact:worldbuilding:doc:r1:" + digest[:12]
    index = build_source_span_index_for_text(
        source_artifact_id=artifact_id,
        content_sha256=digest,
        text=text,
    )
    ref = source_span_refs_from_index(index)[0]
    with pytest.raises(ValueError, match="namespaced by artifact digest"):
        validate_source_span_ref_for_artifact(
            ref,
            source_artifact_id=artifact_id,
            content_sha256="0" * 64,
        )


def test_source_span_index_from_dict_requires_exact_schema_and_version() -> None:
    text = "Body\n"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    artifact_id = "artifact:worldbuilding:doc:r1:" + digest[:12]
    index = build_source_span_index_for_text(
        source_artifact_id=artifact_id,
        content_sha256=digest,
        text=text,
    )
    payload = source_span_index_to_dict(index)

    missing_schema = dict(payload)
    missing_schema.pop("schema")
    with pytest.raises(ValueError, match="schema is required"):
        source_span_index_from_dict(missing_schema)

    foreign = dict(payload)
    foreign["schema"] = "unrelated_contract"
    with pytest.raises(ValueError, match="dmb_source_span_index_v1"):
        source_span_index_from_dict(foreign)

    bad_version = dict(payload)
    bad_version["version"] = "9.9"
    with pytest.raises(ValueError, match="version must be"):
        source_span_index_from_dict(bad_version)
