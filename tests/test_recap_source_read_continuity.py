"""Recap source-read continuity: canonical span identity survives write → read.

Localization: the frozen candidate and contribution already carry a first-class
``source_span_ref_id``. ``_recap_extraction_evidence_view`` was dropping it and
stamping the revision file URI onto both ``locator`` and ``uri``. DungeonMind's
v1→v2 lift copies those fields and hardcodes ``source_span_ref_id=None``.
Ordinary source-read then classified the replay-shaped anchor as
``unsupported_locator``.

This module never treats ``evidence_ref_id`` as a hidden locator protocol.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    _map_contribution_evidence_ref,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    _classify_locator_kind,
    _product_source_span_ref_id,
    _read_admitted_repo_span,
    _source_anchor_views,
    extract_span_from_revision_bound_text,
    list_recap_context_direct_v2,
    read_recap_context_direct_v2,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    _recap_extraction_evidence_view,
)
from apps.live_control_server.services.world_graph_retrieval import _resolved_repo_root
from dungeonmind.application.graph_snapshot import GraphEvidenceRecord
from dungeonmind.application.world_graph_retrieval import SourceAnchorMetadata
from dungeonmind.application.world_graph_retrieval import (
    RecapContextSectionSelectorV2, RecapSourceContextV2,
    SourceContextIndexResult, SourceContextResolution,
)
from dungeonmind.contracts.evidence import SourceDomain
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.contracts.projection_v2 import ScopeModeV2
from graph_memory.retrieval.models import (
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    WorldGraphRetrievalTrustBoundary,
    WorldGraphSourceAnchorReadRequest,
    RecapContextIndexRequestV2,
    RecapContextReadRequestV2,
)
from graph_memory.source_span import build_stable_source_span_id
from tests.test_candidate_graph_admission_contract import _candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ID = "artifact:recap:longmont-c2:session-22:ad4ecd013dad"
SPAN_ID = f"{ARTIFACT_ID}:span:ad4ecd013dad:16-16"
EVIDENCE_ID = f"evidence:{ARTIFACT_ID}:{SPAN_ID}"
REPO_URI = (
    "repo://out/registries/source_content/recap/longmont-c2/"
    "session-22/ad4ecd013dad.md"
)
TOKEN = "sha256:" + ("ab" * 32)

pytest_plugins = ("tests.application_state.conftest",)


def _digest_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _assertion(
    *,
    evidence_ref_id: str = EVIDENCE_ID,
    span_id: str | None = SPAN_ID,
    artifact_id: str = ARTIFACT_ID,
    include_embedded: bool = True,
) -> SimpleNamespace:
    embedded: list[dict[str, Any]] = []
    if include_embedded:
        row: dict[str, Any] = {
            "evidence_ref_id": evidence_ref_id,
            "source_artifact_id": artifact_id,
            "source_domain": "recap",
        }
        if span_id is not None:
            row["source_span_ref_id"] = span_id
        embedded.append(row)
    return SimpleNamespace(
        source_artifact_id=artifact_id,
        source_revision_id=TOKEN,
        evidence_ref_ids=[evidence_ref_id],
        value={"evidence": embedded} if include_embedded else {},
    )


def _contribution(assertion: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        accepted_assertions=[assertion],
        candidate_assertions=[],
        rejected_assertions=[],
    )


class _FakeSources:
    def __init__(self, locator: str = REPO_URI, digest: str | None = None) -> None:
        self.locator = locator
        self.digest = digest

    def get_revision(self, revision_id: str) -> SimpleNamespace | None:
        if self.digest is None and self.locator is None:
            return None
        return SimpleNamespace(locator=self.locator, content_sha256=self.digest)


def _mapped_recap_evidence(
    *,
    span_id: str | None = SPAN_ID,
    include_embedded: bool = True,
    evidence_ref_id: str = EVIDENCE_ID,
) -> Any:
    assertion = _assertion(
        evidence_ref_id=evidence_ref_id,
        span_id=span_id,
        include_embedded=include_embedded,
    )
    view = _recap_extraction_evidence_view(
        _contribution(assertion),
        pair_to_dm={(ARTIFACT_ID, TOKEN): TOKEN},
        sources=_FakeSources(),
    )
    return _map_contribution_evidence_ref(
        view,
        evidence_ref_id,
        fallback_source_artifact_id=ARTIFACT_ID,
        source_revision_id=TOKEN,
    )


def _evidence_record(
    *,
    domain: str = "session_recap",
    evidence_ref_id: str = EVIDENCE_ID,
) -> GraphEvidenceRecord:
    return GraphEvidenceRecord(
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=ARTIFACT_ID,
        source_revision_id=TOKEN,
        source_domain=domain,
        can_open_source=True,
        can_highlight_span=True,
        locator=SPAN_ID,
        uri=REPO_URI,
    )


def _anchor(
    *,
    locator_identity: str,
    source_span_ref_id: str | None = None,
    uri: str = REPO_URI,
    domain: str = "session_recap",
    evidence_ref_id: str = EVIDENCE_ID,
    can_open_source: bool = True,
) -> SourceAnchorMetadata:
    return SourceAnchorMetadata(
        anchor_id="source-anchor:v1:test-recap-span",
        evidence_ref_id=evidence_ref_id,
        source_artifact_id=ARTIFACT_ID,
        source_revision_id=TOKEN,
        locator_identity=locator_identity,
        source_span_ref_id=source_span_ref_id,
        can_open_source=can_open_source,
        can_highlight_span=bool(source_span_ref_id or locator_identity),
        supporting_object_ids=(),
        supporting_relationship_ids=(),
        supporting_assertion_ids=(),
        evidence=_evidence_record(domain=domain, evidence_ref_id=evidence_ref_id),
        artifact=SimpleNamespace(uri=uri),
    )


def _read_request() -> WorldGraphSourceAnchorReadRequest:
    return WorldGraphSourceAnchorReadRequest.model_validate(
        {
            "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
            "worldId": "world:recap-source-read-continuity",
            "campaignId": "longmont-c2",
            "anchorId": "source-anchor:v1:test-recap-span",
            "maxChars": 4000,
        }
    )


def _read_base(**overrides: Any) -> dict[str, Any]:
    payload = {
        "snapshot": None,
        "anchor_id": "source-anchor:v1:test-recap-span",
        "evidence_ref_id": EVIDENCE_ID,
        "source_artifact_id": ARTIFACT_ID,
        "source_domain": "session_recap",
        "source_span_ref_id": SPAN_ID,
        "locator_kind": "source_span",
        "trust_boundary": WorldGraphRetrievalTrustBoundary(),
    }
    payload.update(overrides)
    return payload


def test_write_stamps_canonical_span_onto_locator_not_file_uri() -> None:
    mapped = _mapped_recap_evidence()
    assert mapped.source_domain == SourceDomain.SESSION_RECAP
    assert mapped.locator == SPAN_ID
    assert mapped.uri == REPO_URI
    assert mapped.can_highlight_span is True
    assert mapped.can_open_source is True


def test_write_does_not_parse_span_out_of_evidence_ref_id() -> None:
    mapped = _mapped_recap_evidence(span_id=None, include_embedded=True)
    assert mapped.locator == REPO_URI
    assert mapped.uri == REPO_URI
    assert mapped.can_highlight_span is False


def test_write_without_embedded_evidence_does_not_invent_span() -> None:
    mapped = _mapped_recap_evidence(include_embedded=False)
    assert mapped.locator == REPO_URI
    assert mapped.can_highlight_span is False


def test_classifier_uses_locator_identity_for_recap_digest_bound_span() -> None:
    anchor = _anchor(locator_identity=SPAN_ID, source_span_ref_id=None)
    assert _product_source_span_ref_id(anchor) == SPAN_ID
    assert _classify_locator_kind(anchor) == "source_span"
    views = _source_anchor_views([anchor], revision_id="rev:child")
    assert views[0].source_span_ref_id == SPAN_ID
    assert views[0].locator_kind == "source_span"
    assert views[0].readable is True


def test_classifier_keeps_replay_shaped_file_uri_unsupported() -> None:
    anchor = _anchor(locator_identity=REPO_URI, source_span_ref_id=None)
    assert _product_source_span_ref_id(anchor) is None
    assert _classify_locator_kind(anchor) == "unsupported"


def test_legacy_opaque_recap_span_remains_provenance_but_unreadable() -> None:
    anchor = _anchor(locator_identity="span:session-22:mireward", source_span_ref_id="span:session-22:mireward")
    view = _source_anchor_views([anchor], revision_id="rev:child")[0]
    assert view.source_span_ref_id == "span:session-22:mireward"
    assert view.locator_kind == "unsupported"
    assert view.readable is False


def _context_fixture(tmp_path: Path):
    raw = b'title: recap\n\n# Session 22 Recap\nfirst line\nsecond line\n'
    digest = hashlib.sha256(raw).hexdigest()
    path = tmp_path / 's22.md'
    path.write_bytes(raw)
    selector = RecapContextSectionSelectorV2(expected_session_id='session-22', canonical_heading='# Session 22 Recap', legacy_session_heading="## Session 22:", legacy_recap_marker="**Recap**:")
    descriptor = RecapSourceContextV2(
        context_anchor_id='dm-context-anchor:v2:test', world_id='eldyrwild',
        campaign_id='longmont-c2', graph_revision_id='rev:test',
        source_artifact_id='artifact:s22', source_revision_id='sha256:' + digest,
        source_uri='repo://s22.md', content_sha256=digest, section_selector=selector,
    )
    snapshot = SimpleNamespace(
        world_id='eldyrwild', campaign_id='longmont-c2', revision_id='rev:test',
        head_revision_id='rev:test', is_head=True, admissibility=Admissibility.GM,
        scope_mode=ScopeModeV2.CAMPAIGN,
    )
    retrieval = SimpleNamespace(
        list_source_context_index=lambda req: SourceContextIndexResult(
            snapshot=snapshot, eligible_count=1, max_entries=req.max_entries,
            status='complete', entries=(descriptor,),
        ),
        resolve_source_context=lambda _req, context_anchor_id, allow_selector_v2=False: SourceContextResolution(
            snapshot=snapshot, found=context_anchor_id == descriptor.context_anchor_id,
            context_anchor_id=context_anchor_id,
            context=descriptor if context_anchor_id == descriptor.context_anchor_id else None,
        ),
    )
    services = SimpleNamespace(retrieval=retrieval, binding=SimpleNamespace(legacy_buddy_revision_id=None))
    common = dict(worldId='eldyrwild', campaignId='longmont-c2', scopeMode='campaign', revisionPin='rev:test')
    index_request = RecapContextIndexRequestV2.model_validate({'schema':'dmb_recap_context_index_request_v2', **common})
    read_request = RecapContextReadRequestV2.model_validate({'schema':'dmb_recap_context_read_request_v2', **common,
        'contextAnchorId':descriptor.context_anchor_id, 'maxChars':5})
    return services, index_request, read_request, path, digest


def test_recap_context_core_descriptor_opens_verified_section_with_continuation(tmp_path: Path) -> None:
    services, index_request, read_request, _path, digest = _context_fixture(tmp_path)
    index = list_recap_context_direct_v2(services, index_request)
    assert index.status == 'complete'
    assert index.entries[0].content_sha256 == digest
    first = read_recap_context_direct_v2(services, read_request, repo_root=tmp_path)
    assert (first.heading_line, first.line_start, first.line_end) == (3, 4, 5)
    assert first.content == 'first'
    assert first.truncated and first.next_continuation
    tail = []
    current = first
    while current.next_continuation:
        current = read_recap_context_direct_v2(services, read_request.model_copy(update={'continuation': current.next_continuation}), repo_root=tmp_path)
        tail.append(current.content)
    assert first.content + ''.join(tail) == 'first line\nsecond line\n'
    assert current.section_sha256 == first.section_sha256


def test_recap_context_opens_campaign_recap_from_ordinary_world_scope(tmp_path: Path) -> None:
    services, index_request, read_request, _path, digest = _context_fixture(tmp_path)
    native_index = services.retrieval.list_source_context_index(SimpleNamespace(max_entries=index_request.max_entries))
    campaign_snapshot = native_index.snapshot
    world_snapshot = SimpleNamespace(
        **{**vars(campaign_snapshot), 'campaign_id': None, 'scope_mode': ScopeModeV2.WORLD_CROSS_CAMPAIGN}
    )
    native_resolution = services.retrieval.resolve_source_context(None, context_anchor_id=read_request.context_anchor_id)
    services.retrieval.list_source_context_index = lambda req: replace(native_index, snapshot=world_snapshot)
    services.retrieval.resolve_source_context = lambda req, context_anchor_id, allow_selector_v2=False: replace(native_resolution, snapshot=world_snapshot)
    world_index_request = RecapContextIndexRequestV2.model_validate({
        **index_request.model_dump(mode='json', by_alias=True), 'campaignId': '', 'scopeMode': 'world',
    })
    world_read_request = RecapContextReadRequestV2.model_validate({
        **read_request.model_dump(mode='json', by_alias=True), 'campaignId': '', 'scopeMode': 'world',
    })
    index = list_recap_context_direct_v2(services, world_index_request)
    assert index.snapshot.scope_mode == 'world'
    assert index.entries[0].campaign_id == 'longmont-c2'
    read = read_recap_context_direct_v2(services, world_read_request, repo_root=tmp_path)
    assert read.context is not None and read.context.content_sha256 == digest
    assert read.content == 'first'


def test_recap_context_refuses_changed_bytes_and_tampered_continuation(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import DirectWorldGraphReadError
    services, _index_request, request, path, _digest = _context_fixture(tmp_path)
    with pytest.raises(DirectWorldGraphReadError):
        read_recap_context_direct_v2(services, request.model_copy(update={'continuation':'recap-page:v1:bad:5'}), repo_root=tmp_path)
    path.write_text('# Session 22 Recap\nchanged\n')
    with pytest.raises(DirectWorldGraphReadError):
        read_recap_context_direct_v2(services, request, repo_root=tmp_path)


def test_recap_context_ignores_fenced_fake_headings(tmp_path: Path) -> None:
    services, _index_request, request, path, _digest = _context_fixture(tmp_path)
    source = (
        '```markdown\n# Session 22 Recap\n```\n'
        '# Session 22 Recap\nfirst line\n'
        '~~~~ example\n# Fake next heading\n~~~~\n'
        'last line\n# Actual next heading\nexcluded\n'
    ).encode('utf-8')
    path.write_bytes(source)
    native = services.retrieval.resolve_source_context(None, context_anchor_id=request.context_anchor_id)
    descriptor = replace(native.context, content_sha256=hashlib.sha256(source).hexdigest())
    services.retrieval.resolve_source_context = lambda _req, context_anchor_id, allow_selector_v2=False: replace(native, context=descriptor)
    opened = read_recap_context_direct_v2(services, request.model_copy(update={'max_chars': 4000}), repo_root=tmp_path)
    assert (opened.heading_line, opened.line_start, opened.line_end) == (4, 5, 9)
    assert opened.content == 'first line\n~~~~ example\n# Fake next heading\n~~~~\nlast line\n'


def test_recap_context_rejects_heading_only_inside_fence(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import DirectWorldGraphReadError
    services, _index_request, request, path, _digest = _context_fixture(tmp_path)
    source = b'```markdown\n# Session 22 Recap\n```\nbody\n'
    path.write_bytes(source)
    native = services.retrieval.resolve_source_context(None, context_anchor_id=request.context_anchor_id)
    descriptor = replace(native.context, content_sha256=hashlib.sha256(source).hexdigest())
    services.retrieval.resolve_source_context = lambda _req, context_anchor_id, allow_selector_v2=False: replace(native, context=descriptor)
    with pytest.raises(DirectWorldGraphReadError):
        read_recap_context_direct_v2(services, request, repo_root=tmp_path)


@pytest.mark.parametrize('source', [
    b'# Wrong heading\nbody\n',
    b'# Session 22 Recap\none\n# Session 22 Recap\ntwo\n',
    b'\xff# Session 22 Recap\n',
])
def test_recap_context_rejects_unreadable_section_bytes(tmp_path: Path, source: bytes) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import DirectWorldGraphReadError
    services, _index_request, request, path, _digest = _context_fixture(tmp_path)
    path.write_bytes(source)
    native = services.retrieval.resolve_source_context(None, context_anchor_id=request.context_anchor_id)
    revised = replace(native.context, content_sha256=hashlib.sha256(source).hexdigest())
    services.retrieval.resolve_source_context = lambda _req, context_anchor_id, allow_selector_v2=False: replace(native, context=revised)
    with pytest.raises(DirectWorldGraphReadError):
        read_recap_context_direct_v2(services, request, repo_root=tmp_path)


def test_recap_context_rejects_foreign_uri_and_revision(tmp_path: Path) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import DirectWorldGraphReadError
    services, _index_request, request, _path, _digest = _context_fixture(tmp_path)
    native = services.retrieval.resolve_source_context(None, context_anchor_id=request.context_anchor_id)
    for change in ({'source_uri':'repo://../outside.md'}, {'graph_revision_id':'rev:foreign'}):
        revised = replace(native.context, **change)
        services.retrieval.resolve_source_context = lambda _req, context_anchor_id, allow_selector_v2=False: replace(native, context=revised)
        with pytest.raises(DirectWorldGraphReadError):
            read_recap_context_direct_v2(services, request, repo_root=tmp_path)


def test_recap_context_miss_and_overflow_never_open_source(tmp_path: Path) -> None:
    services, index_request, request, path, _digest = _context_fixture(tmp_path)
    request = request.model_copy(update={'context_anchor_id':'dm-context-anchor:v2:missing'})
    missed = read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    assert missed.outcome == 'empty' and missed.content is None
    assert path.exists()
    native = services.retrieval.list_source_context_index(SimpleNamespace(max_entries=index_request.max_entries))
    services.retrieval.list_source_context_index = lambda req: replace(native,
        status='overflow', eligible_count=513, entries=())
    overflow = list_recap_context_direct_v2(services, index_request)
    assert overflow.status == 'overflow' and overflow.entries == []


def test_classifier_ignores_span_syntax_inside_evidence_ref_id() -> None:
    decoy = f"evidence:{ARTIFACT_ID}:{SPAN_ID}"
    anchor = _anchor(
        locator_identity=REPO_URI,
        source_span_ref_id=None,
        evidence_ref_id=decoy,
    )
    assert SPAN_ID in decoy
    assert _product_source_span_ref_id(anchor) is None
    assert _classify_locator_kind(anchor) == "unsupported"


def test_heading_and_json_pointer_locators_are_unchanged() -> None:
    heading = _anchor(
        locator_identity="heading:Mireward",
        source_span_ref_id=None,
        uri="repo://corpus/notes.md",
    )
    assert _classify_locator_kind(heading) == "heading"
    pointer = _anchor(
        locator_identity="jsonptr:/nodes/0",
        source_span_ref_id=None,
        uri="graph-data://payload.json",
    )
    assert _classify_locator_kind(pointer) == "json_pointer"
    unknown = _anchor(
        locator_identity="https://example.invalid/recap",
        source_span_ref_id=None,
        uri="https://example.invalid/recap",
    )
    assert _classify_locator_kind(unknown) == "unsupported"


def test_worldbuilding_still_requires_explicit_source_span_ref_id() -> None:
    anchor = _anchor(
        locator_identity=SPAN_ID,
        source_span_ref_id=None,
        domain="worldbuilding",
    )
    assert _classify_locator_kind(anchor) == "unsupported"


def test_extract_span_returns_exact_digest_bound_line() -> None:
    digest = "ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f"
    lines = [f"line-{index}" for index in range(1, 20)]
    text = "\n".join(lines) + "\n"
    extracted = extract_span_from_revision_bound_text(
        text=text, span_id=SPAN_ID, digest=digest
    )
    assert extracted == ("line-16", 16, 16)


def test_extract_span_rejects_unknown_and_mismatched_identities() -> None:
    digest = "ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f"
    text = "only one line\n"
    assert (
        extract_span_from_revision_bound_text(
            text=text, span_id=SPAN_ID, digest=digest
        )
        is None
    )
    other = f"{ARTIFACT_ID}:span:ffffffffffff:1-1"
    assert (
        extract_span_from_revision_bound_text(
            text=text, span_id=other, digest=digest
        )
        is None
    )
    assert (
        extract_span_from_revision_bound_text(
            text=text,
            span_id="session-9:recap:paragraph:009",
            digest=digest,
        )
        is None
    )


def test_admitted_repo_span_read_is_digest_verified(tmp_path: Path) -> None:
    relative = "out/registries/source_content/recap/longmont-c2/session-22/ad4ecd013dad.md"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    lines = [f"line-{index}" for index in range(1, 20)]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    digest = _digest_hex(payload)
    span = build_stable_source_span_id(
        source_artifact_id=ARTIFACT_ID,
        content_sha256=digest,
        start_line=16,
        end_line=16,
    )
    services = SimpleNamespace(
        bundle=SimpleNamespace(sources=_FakeSources(locator=f"repo://{relative}", digest=digest))
    )
    anchor = _anchor(
        locator_identity=span,
        source_span_ref_id=None,
        uri=f"repo://{relative}",
    )
    result = _read_admitted_repo_span(
        services,
        anchor,
        request=_read_request(),
        repo_root=tmp_path,
        base=_read_base(source_span_ref_id=span),
    )
    assert result.outcome == "enough"
    assert result.content == "line-16"
    assert result.content_sha256 == digest
    assert result.line_start == 16
    assert result.line_end == 16


def test_admitted_recap_spans_use_configured_artifact_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    code_root = tmp_path / "code"
    code_root.mkdir()
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    relative = "out/registries/source_content/recap/longmont-c2/session-22/source.md"
    source = artifact_root / relative
    source.parent.mkdir(parents=True)
    source.write_text("first line\nsecond line\n", encoding="utf-8")
    digest = _digest_hex(source.read_bytes())
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(artifact_root))

    selected = _resolved_repo_root(root=None, repo_root=None)
    assert selected == artifact_root
    assert _resolved_repo_root(root=None, repo_root=code_root) == code_root
    services = SimpleNamespace(bundle=SimpleNamespace(sources=_FakeSources(
        locator=f"repo://{relative}", digest=digest,
    )))
    for line, expected in ((1, "first line"), (2, "second line")):
        span = build_stable_source_span_id(
            source_artifact_id=ARTIFACT_ID,
            content_sha256=digest,
            start_line=line,
            end_line=line,
        )
        result = _read_admitted_repo_span(
            services,
            _anchor(locator_identity=span, source_span_ref_id=None,
                    uri=f"repo://{relative}"),
            request=_read_request(),
            repo_root=selected,
            base=_read_base(source_span_ref_id=span),
        )
        assert result.outcome == "enough"
        assert result.content == expected
        assert result.content_sha256 == digest
        assert (result.line_start, result.line_end) == (line, line)

    missing_under_code = _read_admitted_repo_span(
        services,
        _anchor(locator_identity=span, source_span_ref_id=None,
                uri=f"repo://{relative}"),
        request=_read_request(),
        repo_root=code_root,
        base=_read_base(source_span_ref_id=span),
    )
    assert missing_under_code.outcome == "unavailable"
    assert missing_under_code.diagnostics[0].code == "source_unavailable"


def test_source_batch_v2_opens_split_root_recap_spans_with_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
    from apps.live_control_server.services import world_graph_retrieval as retrieval
    from graph_memory.interaction.expansion_executor import execute_read_graph_source
    from graph_memory.interaction.session import (
        GraphRetrievalSession, SessionSnapshot, SourceAnchorState,
    )
    from graph_memory.interaction.session_store import clear_sessions, create_session
    from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot

    artifact_root = tmp_path / "artifact-root"
    artifact_root.mkdir()
    relative = "out/registries/source_content/recap/longmont-c2/session-22/source.md"
    source = artifact_root / relative
    source.parent.mkdir(parents=True)
    source.write_text("first line\nsecond line\n", encoding="utf-8")
    digest = _digest_hex(source.read_bytes())
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(artifact_root))
    assert not (REPO_ROOT / relative).exists()

    anchors = {}
    for line in (1, 2):
        span = build_stable_source_span_id(
            source_artifact_id=ARTIFACT_ID, content_sha256=digest,
            start_line=line, end_line=line,
        )
        anchor = replace(
            _anchor(locator_identity=span, uri=f"repo://{relative}"),
            anchor_id=f"source-anchor:v1:split-root-{line}",
        )
        anchors[anchor.anchor_id] = anchor
    snapshot = SimpleNamespace(
        world_id="world:recap-source-read-continuity", revision_id="rev:split-root",
        revision_pin="rev:split-root",
    )
    services = SimpleNamespace(
        binding=object(),
        bundle=SimpleNamespace(sources=_FakeSources(
            locator=f"repo://{relative}", digest=digest,
        )),
        retrieval=SimpleNamespace(resolve_source_anchors=lambda request: SimpleNamespace(
            snapshot=snapshot,
            resolutions=tuple(SimpleNamespace(
                found=True, anchor=anchors[anchor_id], anchor_id=anchor_id, snapshot=snapshot,
            ) for anchor_id in request.anchor_ids),
        )),
    )
    monkeypatch.setattr(retrieval, "_require_mounted_native_read", lambda _root: None)
    monkeypatch.setattr(direct, "direct_services_from_config", lambda _world: services)
    monkeypatch.setattr(direct, "_map_retrieval_context", lambda *_args: snapshot)
    monkeypatch.setattr(direct, "_dnd_anchor_id", lambda anchor_id: anchor_id)
    monkeypatch.setattr(direct, "_retrieval_snapshot_view", lambda _snapshot, *, focus: (
        WorldGraphRetrievalSnapshot(
            world_id="world:recap-source-read-continuity", campaign_id="longmont-c2",
            revision_id="rev:split-root", head_revision_id="rev:split-root",
            is_head=True, focus=focus, admissibility="gm",
        )
    ))
    clear_sessions()
    try:
        session = GraphRetrievalSession(
            snapshot=SessionSnapshot(
                world_id="world:recap-source-read-continuity",
                campaign_id="longmont-c2", revision_id="rev:split-root",
            ),
            source_anchors=[
                SourceAnchorState(anchor_id=anchor_id, readable=True)
                for anchor_id in anchors
            ],
        )
        create_session(session)
        batch = execute_read_graph_source({
            "retrievalSessionId": session.id,
            "anchorIds": list(anchors),
            "maxChars": 4000,
        }, receipt_version=2)
        assert batch["schema"] == "dmb_internal_read_graph_source_batch_v2"
        for line, item in enumerate(batch["reads"], start=1):
            assert item["result"].get("outcome") == "enough", item
            assert item["result"]["content"] == f"{('first', 'second')[line - 1]} line"
            assert item["result"]["contentSha256"] == digest
            assert item["receipt"]["read_content_sha256"] == digest
            assert item["receipt"]["source_revision_sha256"] == digest
            assert item["receipt"]["line_start"] == line
            assert item["receipt"]["line_end"] == line
    finally:
        clear_sessions()


def test_admitted_repo_span_fails_closed_on_tampered_bytes(tmp_path: Path) -> None:
    relative = "out/registries/source_content/recap/longmont-c2/session-22/ad4ecd013dad.md"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    original = b"The marsh town sits on the river.\n"
    path.write_bytes(original)
    digest = _digest_hex(original)
    span = build_stable_source_span_id(
        source_artifact_id=ARTIFACT_ID,
        content_sha256=digest,
        start_line=1,
        end_line=1,
    )
    services = SimpleNamespace(
        bundle=SimpleNamespace(sources=_FakeSources(locator=f"repo://{relative}", digest=digest))
    )
    path.write_bytes(b"tampered recap bytes\n")
    result = _read_admitted_repo_span(
        services,
        _anchor(locator_identity=span, source_span_ref_id=None, uri=f"repo://{relative}"),
        request=_read_request(),
        repo_root=tmp_path,
        base=_read_base(),
    )
    assert result.outcome == "unavailable"
    assert result.content is None
    assert result.content_sha256 is None
    assert [item.code for item in result.diagnostics] == ["source_integrity_error"]


def test_admitted_repo_span_fails_closed_when_revision_missing(tmp_path: Path) -> None:
    services = SimpleNamespace(
        bundle=SimpleNamespace(sources=_FakeSources(locator=REPO_URI, digest=None))
    )
    services.bundle.sources.get_revision = lambda _rid: None  # type: ignore[method-assign]
    result = _read_admitted_repo_span(
        services,
        _anchor(locator_identity=SPAN_ID, source_span_ref_id=None),
        request=_read_request(),
        repo_root=tmp_path,
        base=_read_base(),
    )
    assert result.outcome == "unavailable"
    assert result.content is None
    assert result.diagnostics[0].code == "unsupported_locator"


def _span_candidate(*, artifact_id: str, span_id: str, node_id: str, campaign_id: str, session_id: str) -> dict:
    candidate = copy.deepcopy(_candidate())
    candidate["campaign_id"] = campaign_id
    candidate["session_id"] = session_id
    candidate["source_artifact_ids"] = [artifact_id]
    node = candidate["nodes"][0]
    node["node_id"] = node_id
    node["label"] = node_id.rsplit(":", 1)[-1].replace("-", " ").title()
    node["node_type"] = "location" if "mireward" in node_id else "character"
    ref = node["evidence_refs"][0]
    ref["source_artifact_id"] = artifact_id
    ref["source_span_ref_id"] = span_id
    ref["source_ref_id"] = f"{artifact_id}:text"
    return candidate


def _artifact(
    *,
    uri: str,
    content_sha256: str,
    source_artifact_id: str,
    campaign_id: str,
    session_id: str,
    world_id: str,
) -> SimpleNamespace:
    from datetime import UTC, datetime

    return SimpleNamespace(
        source_artifact_id=source_artifact_id,
        source_domain="recap",
        campaign_id=campaign_id,
        session_id=session_id,
        uri=uri,
        content_sha256=content_sha256,
        artifact_kind="markdown",
        document_class="recap",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=world_id,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


def _confirm_via_product_seam(prepared: SimpleNamespace) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        confirm_extract_promote_via_dungeonmind,
    )
    from apps.live_control_server.models.extract_promote import ExtractPromoteConfirmRequest
    from apps.live_control_server.services.candidate_graph_admission import (
        confirm_candidate_graph_admission,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )

    assertion_ids = [
        str(item["assertion_id"])
        for item in (prepared.package.get("effect") or {}).get("accepted_proposals")
        or []
        if item.get("assertion_id")
    ]
    request = ExtractPromoteConfirmRequest(
        review_package=prepared.package,
        assertion_ids=assertion_ids,
    )
    return confirm_candidate_graph_admission(
        review_package=prepared.package,
        candidate_graph=prepared.candidate,
        source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(
            database_url=prepared.dsn
        ),
        governed_confirm=lambda: confirm_extract_promote_via_dungeonmind(
            request,
            database_url=prepared.dsn,
            confirming_principal="recap-source-read-continuity",
            assertion_ids=tuple(assertion_ids),
            repo_root=prepared.repo,
        ),
    )


def _prepare_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
    *,
    world_id: str,
    campaign_id: str,
    session_id: str,
    node_id: str,
    recap_text: str,
    parent_revision_id: str | None = None,
    genesis: SimpleNamespace | None = None,
) -> SimpleNamespace:
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        bind_identity_ledger_to_package,
    )
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisConfirmRequest,
        RecapWorldGenesisPrepareRequest,
    )
    from apps.live_control_server.services.candidate_graph_admission import (
        prepare_candidate_graph_admission,
    )
    from apps.live_control_server.services.recap_world_genesis import (
        confirm_recap_world_genesis,
        prepare_recap_world_genesis,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import (
        TRUNCATE_SQL,
        ensure_migrated,
        require_test_dsn,
    )
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    monkeypatch.setenv(
        "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn
    )
    dsn = require_test_dsn()
    ensure_migrated(dsn)
    database = PostgresDatabase(dsn)
    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    if genesis is None:
        with database.connect() as conn:
            conn.execute(TRUNCATE_SQL)
            conn.commit()
        repo.mkdir()
        world_root.mkdir()
        from apps.live_control_server import config as wg_config

        monkeypatch.setenv(
            wg_config.WORLD_GRAPH_AUTHORITY_ENV,
            wg_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
        )
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
        registry = (
            repo
            / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json"
        )
        registry.parent.mkdir(parents=True)
        shutil.copyfile(
            REPO_ROOT
            / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json",
            registry,
        )
        genesis_authority = DungeonMindWorldGraphInitializationAdapter(database_url=dsn)
        genesis_plan = prepare_recap_world_genesis(
            RecapWorldGenesisPrepareRequest(
                world_id=world_id,
                campaign_id="longmont-c1",
                baseline_roster_key="1",
                requested_by="recap-source-read-continuity",
            ),
            repo=repo,
            authority=genesis_authority,
        )
        published_genesis = confirm_recap_world_genesis(
            RecapWorldGenesisConfirmRequest(
                plan=genesis_plan, confirming_principal="recap-source-read-continuity"
            ),
            repo=repo,
            authority=genesis_authority,
        )
        parent = published_genesis.published_revision_id
    else:
        dsn = genesis.dsn
        repo = genesis.repo
        parent = parent_revision_id or genesis.d0

    digest = _digest_hex(recap_text.encode("utf-8"))
    artifact_id = f"artifact:recap:{campaign_id}:{session_id}:{digest[:12]}"
    relative = (
        f"out/registries/source_content/recap/{campaign_id}/{session_id}/{digest}.md"
    )
    source = repo / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(recap_text, encoding="utf-8")
    uri = f"repo://{relative}"
    span_id = build_stable_source_span_id(
        source_artifact_id=artifact_id,
        content_sha256=digest,
        start_line=1,
        end_line=1,
    )
    candidate = _span_candidate(
        artifact_id=artifact_id,
        span_id=span_id,
        node_id=node_id,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    candidate_path = tmp_path / f"{campaign_id}-{session_id}.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    graph_authority = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    context = graph_authority.mutation_context(world_id, parent)
    recap = _artifact(
        uri=uri,
        content_sha256=digest,
        source_artifact_id=artifact_id,
        campaign_id=campaign_id,
        session_id=session_id,
        world_id=world_id,
    )
    result = prepare_candidate_graph_admission(
        candidate_graph=candidate,
        source_uri=uri,
        source_revision_id=f"sha256:{digest}",
        prepared_by="recap-source-read-continuity",
        world_id=world_id,
        source_artifact_id=artifact_id,
        source_artifact=recap,
        campaign_scope=campaign_id,
        repo_root=repo,
        mutation_context=context,
        candidate_graph_path=str(candidate_path),
        source_admission=DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn),
    )
    package = bind_identity_ledger_to_package(result.review_package, context)
    return SimpleNamespace(
        dsn=dsn,
        repo=repo,
        world_id=world_id,
        d0=parent if genesis is None else genesis.d0,
        parent=parent,
        graph_authority=graph_authority,
        candidate=candidate,
        package=package,
        result=result,
        artifact_id=artifact_id,
        span_id=span_id,
        digest=digest,
        node_id=node_id,
        campaign_id=campaign_id,
        uri=uri,
    )


@pytest.mark.integration
def test_fresh_recap_publication_source_read_is_digest_verified(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        build_direct_world_graph_read_services,
        get_evidence_direct,
        get_object_direct,
        read_source_anchor_direct,
    )
    from graph_memory.retrieval.models import (
        RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
        RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        WorldGraphEvidenceRequest,
        WorldGraphObjectRequest,
        WorldGraphSourceAnchorReadRequest,
    )

    world_id = "world:recap-source-read-continuity"
    c2 = _prepare_session(
        tmp_path,
        monkeypatch,
        application_state_dsn,
        world_id=world_id,
        campaign_id="longmont-c2",
        session_id="session-22",
        node_id="node:location:mireward",
        recap_text="The marsh town of Mireward sits on the river.\n",
    )
    assert c2.result.confirmable is True
    published_c2 = _confirm_via_product_seam(c2)
    c2_rev = published_c2["committed_revision_id"]
    services = build_direct_world_graph_read_services(c2.dsn, world_id)
    found = get_object_direct(
        services,
        WorldGraphObjectRequest.model_validate(
            {
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "nodeId": "node:location:mireward",
            }
        ),
    )
    assert found.outcome != "empty"
    evidence = get_evidence_direct(
        services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "node:location:mireward"},
            }
        ),
    )
    assert evidence.source_anchors
    anchor = evidence.source_anchors[0]
    assert anchor.source_span_ref_id == c2.span_id
    assert anchor.locator_kind == "source_span"
    read = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "anchorId": anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert read.outcome in {"enough", "truncated"}
    assert read.content_sha256 == c2.digest
    assert read.content is not None
    assert "Mireward sits on the river" in read.content
    assert read.source_span_ref_id == c2.span_id

    replay = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "anchorId": anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert replay.content == read.content
    assert replay.content_sha256 == read.content_sha256

    c1 = _prepare_session(
        tmp_path,
        monkeypatch,
        application_state_dsn,
        world_id=world_id,
        campaign_id="longmont-c1",
        session_id="session-10",
        node_id="node:character:torbin",
        recap_text="Torbin keeps the historical pin honest.\n",
        parent_revision_id=c2_rev,
        genesis=c2,
    )
    published_c1 = _confirm_via_product_seam(c1)
    c1_rev = published_c1["committed_revision_id"]
    assert c1_rev != c2_rev
    historical = get_evidence_direct(
        services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "node:location:mireward"},
            }
        ),
    )
    historical_anchor = historical.source_anchors[0]
    historical_read = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c2",
                "revisionPin": c2_rev,
                "scopeMode": "world",
                "anchorId": historical_anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert historical_read.outcome in {"enough", "truncated"}
    assert historical_read.content_sha256 == c2.digest
    assert historical_read.snapshot is not None
    assert historical_read.snapshot.revision_id == c2_rev
    assert historical_read.snapshot.head_revision_id == c1_rev
    assert "Torbin" not in (historical_read.content or "")

    c1_services = build_direct_world_graph_read_services(c1.dsn, world_id)
    c1_evidence = get_evidence_direct(
        c1_services,
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c1",
                "revisionPin": c1_rev,
                "scopeMode": "world",
                "target": {"kind": "node", "id": "node:character:torbin"},
            }
        ),
    )
    c1_anchor = c1_evidence.source_anchors[0]
    c1_read = read_source_anchor_direct(
        c1_services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c1",
                "revisionPin": c1_rev,
                "scopeMode": "world",
                "anchorId": c1_anchor.anchor_id,
            }
        ),
        repo_root=c1.repo,
    )
    assert c1_read.outcome in {"enough", "truncated"}
    assert c1_read.content_sha256 == c1.digest
    assert "Torbin keeps the historical pin honest" in (c1_read.content or "")

    foreign = read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "worldId": world_id,
                "campaignId": "longmont-c1",
                "revisionPin": c1_rev,
                "scopeMode": "world",
                "anchorId": anchor.anchor_id,
            }
        ),
        repo_root=c2.repo,
    )
    assert foreign.outcome in {"empty", "partial", "unavailable", "denied"}
    assert foreign.content is None


LEGACY_PRELUDE_V2 = (
    "## Session 16:\n## Major Beats:\nSynthetic prelude A.\n"
    "## Next Beats :\nSynthetic prelude B.\n**Recap**:\n"
    "Synthetic recap body.\n## Afterword\nExcluded afterword.\n"
    "## Session 17:\n**Recap**:\nOther session body.\n"
)


def _context_fixture_v2(tmp_path, raw=LEGACY_PRELUDE_V2.encode()):
    from dungeonmind.application.world_graph_retrieval import RecapContextSectionSelectorV2, RecapSourceContextV2
    from graph_memory.retrieval.models import RecapContextIndexRequestV2, RecapContextReadRequestV2
    path = tmp_path / "s16.md"
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    common = dict(world_id="eldyrwild", campaign_id="longmont-c1", graph_revision_id="rev:test",
        source_artifact_id="artifact:synthetic:s16", source_revision_id="sha256:" + digest,
        source_uri="repo://s16.md", content_sha256=digest)
    v2 = RecapSourceContextV2(context_anchor_id="dm-context-anchor:v2:synthetic",
        section_selector=RecapContextSectionSelectorV2(expected_session_id="session-16",
            canonical_heading="# Session 16 Recap", legacy_session_heading="## Session 16:", legacy_recap_marker="**Recap**:"), **common)
    snapshot = SimpleNamespace(world_id="eldyrwild", campaign_id="longmont-c1", revision_id="rev:test",
        head_revision_id="rev:test", is_head=True, admissibility=Admissibility.GM, scope_mode=ScopeModeV2.CAMPAIGN)
    descriptors = {v2.context_anchor_id: v2}
    def index(request):
        assert request.selector_policy == "markdown-session-recap-v2"
        selected = v2
        return SourceContextIndexResult(snapshot=snapshot, eligible_count=1, max_entries=request.max_entries, status="complete", entries=(selected,))
    def resolve(projection, *, context_anchor_id, allow_selector_v2=False):
        selected = descriptors.get(context_anchor_id)
        if context_anchor_id.startswith("dm-context-anchor:v2:") and not allow_selector_v2:
            selected = None
        return SourceContextResolution(snapshot=snapshot, context_anchor_id=context_anchor_id, found=selected is not None, context=selected)
    services = SimpleNamespace(retrieval=SimpleNamespace(list_source_context_index=index, resolve_source_context=resolve),
        binding=SimpleNamespace(legacy_buddy_revision_id=None))
    base = dict(worldId="eldyrwild", campaignId="longmont-c1", scopeMode="campaign", revisionPin="rev:test")
    request = RecapContextReadRequestV2.model_validate({"schema":"dmb_recap_context_read_request_v2", **base, "contextAnchorId":v2.context_anchor_id,"maxChars":5})
    listed = RecapContextIndexRequestV2.model_validate({"schema":"dmb_recap_context_index_request_v2", **base})
    return services, listed, request, path, descriptors


def test_recap_context_v2_exact_prelude_and_contiguous_original_pages(tmp_path):
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import list_recap_context_direct_v2, read_recap_context_direct_v2
    services, listed, request, path, _ = _context_fixture_v2(tmp_path)
    index = list_recap_context_direct_v2(services, listed)
    assert index.entries[0].selector_policy == "markdown-session-recap-v2"
    pages = []
    while True:
        page = read_recap_context_direct_v2(services, request, repo_root=tmp_path)
        assert page.selected_form == "legacy_h2"
        assert (page.session_heading_line,page.recap_marker_line,page.line_start,page.line_end)==(1,6,7,7)
        assert page.offset_chars == sum(map(len,pages))
        pages.append(page.content)
        if not page.truncated:
            break
        request = request.model_copy(update={"continuation":page.next_continuation})
    assert "".join(pages) == "Synthetic recap body.\n"
    assert path.read_bytes() == LEGACY_PRELUDE_V2.encode()


def test_recap_context_v2_canonical_bytes_ranges_and_rejects_old_cursor(tmp_path):
    raw = b"# Session 16 Recap\r\nUnicode \xce\xa9 text.\r\n## Still in recap\r\nTail.\r\n# Next\r\nExcluded.\r\n"
    services, _, request, path, _ = _context_fixture_v2(tmp_path, raw)
    page = read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    assert page.selected_form == "canonical_h1"
    assert (page.session_heading_line, page.recap_marker_line, page.line_start, page.line_end) == (1, None, 2, 4)
    assert page.next_continuation.startswith("recap-page:v2:")
    parts = [page.content]
    while page.next_continuation:
        page = read_recap_context_direct_v2(services, request.model_copy(update={"continuation":page.next_continuation}), repo_root=tmp_path)
        parts.append(page.content)
    assert "".join(parts) == "Unicode Ω text.\r\n## Still in recap\r\nTail.\r\n"
    assert path.read_bytes() == raw
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import DirectWorldGraphReadError
    with pytest.raises(DirectWorldGraphReadError):
        read_recap_context_direct_v2(services, request.model_copy(update={"continuation":"recap-page:v1:" + "a"*64 + ":5"}), repo_root=tmp_path)


@pytest.mark.parametrize("raw", [
    "## Session 17:\n**Recap**:\nWrong session.\n",
    "## Session 16:\n## Major Beats:\nNo marker.\n## Session 17:\n**Recap**:\nOther.\n",
    "## Session 16:\n**Recap**:\nFirst.\n**Recap**:\nSecond.\n",
    "## Session 16:\n**Recap**:\nFirst.\n## Session 16:\n**Recap**:\nSecond.\n",
    "# Session 16 Recap\nCanonical.\n## Session 16:\n**Recap**:\nLegacy.\n",
    "## Session 16:\n```md\n**Recap**:\nFenced.\n```\n",
    "## Session 16:\n> **Recap**:\nQuoted.\n",
    "## Session 16:\n    **Recap**:\nIndented.\n",
    "```\n## Session 16:\n**Recap**:\nFake.\n```\n",
    "## Session 16:\n**Recap**:",
    "## Session 16:\nRecap: inline\nUnsupported.\n",
])
def test_recap_context_v2_rejects_unsupported_or_ambiguous_structure(tmp_path,raw):
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import read_recap_context_direct_v2,DirectWorldGraphReadError
    services,_,request,_,_ = _context_fixture_v2(tmp_path,raw.encode())
    with pytest.raises(DirectWorldGraphReadError) as error:
        read_recap_context_direct_v2(services,request,repo_root=tmp_path)
    assert error.value.code=="source_unavailable" and error.value.status_code==409


def test_recap_context_v2_fenced_fake_boundaries_and_subordinate_headings_are_exact(tmp_path):
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import read_recap_context_direct_v2
    raw="## Session 16:\n**Recap**:\nBody.\n### Detail\n```\n# Fake boundary\n## Fake boundary\n**Recap**:\n```\nTail.\n## End\nExcluded.\n"
    services,_,request,_,_ = _context_fixture_v2(tmp_path,raw.encode())
    page=read_recap_context_direct_v2(services,request.model_copy(update={"max_chars":12000}),repo_root=tmp_path)
    assert page.content=="Body.\n### Detail\n```\n# Fake boundary\n## Fake boundary\n**Recap**:\n```\nTail.\n"


@pytest.mark.parametrize("fault",["bytes","utf8","uri","campaign","revision","cursor","source_revision"])
def test_recap_context_v2_revalidates_every_page_and_authority(tmp_path,fault):
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import read_recap_context_direct_v2,DirectWorldGraphReadError
    services,_,request,path,descriptors = _context_fixture_v2(tmp_path)
    page=read_recap_context_direct_v2(services,request,repo_root=tmp_path)
    request=request.model_copy(update={"continuation":page.next_continuation})
    descriptor=descriptors[request.context_anchor_id]
    if fault=="bytes":
        path.write_bytes(b"changed")
    elif fault=="utf8":
        path.write_bytes(b"\xff")
        descriptors[request.context_anchor_id]=replace(descriptor,content_sha256=hashlib.sha256(b"\xff").hexdigest())
    elif fault=="uri":
        descriptors[request.context_anchor_id]=replace(descriptor,source_uri="repo://../escape.md")
    elif fault=="campaign":
        descriptors[request.context_anchor_id]=replace(descriptor,campaign_id="foreign")
    elif fault=="revision":
        descriptors[request.context_anchor_id]=replace(descriptor,graph_revision_id="rev:foreign")
    elif fault=="source_revision":
        descriptors[request.context_anchor_id]=replace(descriptor,source_revision_id="revision:changed")
    else:
        request=request.model_copy(update={"continuation":page.next_continuation+"0"})
    with pytest.raises(DirectWorldGraphReadError) as error:
        read_recap_context_direct_v2(services,request,repo_root=tmp_path)
    assert error.value.code=="source_unavailable"


def test_recap_context_v2_empty_canonical_body(tmp_path):
    services, _, request, _, _ = _context_fixture_v2(tmp_path, b"# Session 16 Recap\n# Next\n")
    page = read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    assert page.selected_form == "canonical_h1"
    assert (page.content, page.line_start, page.line_end) == ("", 2, 1)
    assert page.section_sha256 == hashlib.sha256(b"").hexdigest()
