"""Claim-owned immutable source catalogs. Labels are navigation, never evidence."""
from __future__ import annotations

from hashlib import sha256
from dataclasses import dataclass, field
from uuid import UUID
import re
from time import perf_counter

from application_state.errors import ApplicationStateValidationError
from application_state.source import repository as sources
from . import types as t
from .native_source_navigation import origin_payload

SELECTOR = "markdown_sections_v1"


@dataclass(frozen=True)
class NativeSourceCatalogMaterial:
    """Ephemeral host cache material; never a writer/model input or citation."""
    navigation_id: UUID
    catalog_event_id: UUID
    app_source_revision_id: UUID
    source_artifact_id: str
    native_source_revision_id: str
    content_sha256: str
    markdown: str = field(repr=False)


def section_catalog(markdown, *, source_artifact_id, native_source_revision_id, content_sha256):
    if sha256(markdown.encode("utf-8")).hexdigest() != content_sha256 or not markdown.strip():
        raise ValueError("Catalog source bytes differ from immutable revision")
    lines = markdown.splitlines(keepends=True)
    starts, cursor = [], 0
    for line in lines:
        starts.append(cursor)
        cursor += len(line)
    headings, parents, fence = [], [], None
    previous_plain = None
    for index, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
            previous_plain = None
            continue
        if marker:
            fence = (marker[1][0], len(marker[1]))
            previous_plain = None
            continue
        atx = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$", line)
        setext = re.match(r"^ {0,3}(=+|-+)[ \t]*$", line)
        if atx:
            level, label, start = len(atx[1]), re.sub(r"[ \t]+#+[ \t]*$", "", atx[2] or "").strip(), index
        elif setext and previous_plain is not None:
            level, label, start = (1 if setext[1][0] == "=" else 2), previous_plain[1], previous_plain[0]
        else:
            previous_plain = (index, line.strip()) if line.strip() and not line.startswith("    ") else None
            continue
        previous_plain = None
        label = label or "Untitled section"
        while parents and parents[-1][0] >= level:
            parents.pop()
        parents.append((level, label))
        headings.append((start, " › ".join(item[1] for item in parents)))
    if not headings:
        headings = [(0, "Full source")]
    elif headings[0][0] > 0:
        headings.insert(0, (0, "Introduction"))
    result = []
    for ordinal, (start, label) in enumerate(headings):
        end = headings[ordinal+1][0] if ordinal+1 < len(headings) else len(lines)
        identity = {"selector_policy": SELECTOR, "source_artifact_id": source_artifact_id,
            "native_source_revision_id": native_source_revision_id, "content_sha256": content_sha256,
            "line_start": start+1, "line_end": end}
        result.append(t.NativeSourceSectionDescriptorV1(section_id=t._canonical_sha256(identity), label=label,
            line_start=start+1, line_end=end, char_start=starts[start],
            char_end=starts[end] if end < len(lines) else len(markdown)))
    return result


def catalog_digest(event):
    return t._canonical_sha256({"selector_policy": event.selector_policy,
        "source_artifact_id": event.source_artifact_id, "native_source_revision_id": event.native_source_revision_id,
        "content_sha256": event.content_sha256,
        "app_source_revision_id": str(event.app_source_revision_id) if event.app_source_revision_id else None,
        "outcome": event.outcome, "sections": [s.model_dump(mode="json") for s in event.sections]})


def validate_catalog_record(event):
    if event.catalog_sha256 != catalog_digest(event):
        raise ValueError("Native source catalog commitment differs")
    if event.outcome == "complete":
        if (event.failure_code is not None or not event.sections or event.app_source_revision_id is None
                or event.lineage_sha256 is None or event.observed_body_sha256 != event.content_sha256
                or event.body_read_chars < 1 or event.body_read_bytes < event.body_read_chars):
            raise ValueError("Complete catalog requires exact immutable body proof")
        previous_line, previous_char = 0, 0
        for section in event.sections:
            identity = {"selector_policy": event.selector_policy, "source_artifact_id": event.source_artifact_id,
                "native_source_revision_id": event.native_source_revision_id, "content_sha256": event.content_sha256,
                "line_start": section.line_start, "line_end": section.line_end}
            if (section.section_id != t._canonical_sha256(identity)
                    or section.line_start != previous_line+1 or section.char_start != previous_char):
                raise ValueError("Catalog ranges must form one exact nonoverlapping sequence")
            previous_line, previous_char = section.line_end, section.char_end
        if previous_char != event.body_read_chars:
            raise ValueError("Catalog must cover the complete immutable source")
    elif (event.sections or event.app_source_revision_id is not None or event.lineage_sha256 is not None
            or event.failure_code not in {"source_unavailable", "source_scope_mismatch", "source_identity_mismatch",
                "source_hash_mismatch", "source_lineage_mismatch", "source_encoding_mismatch"}):
        raise ValueError("Unavailable catalog cannot grant source sections")


def current_navigation(turn, navigation_id):
    execution = turn.graph_context_execution
    if execution is None:
        raise ValueError("Turn has no native source execution")
    navs = [e for e in execution.events if isinstance(e, t.NativeSourceNavigationAuthorizedV1)
            and e.navigation_id == navigation_id]
    if len(navs) != 1:
        raise ValueError("Catalog requires one earlier source navigation authorization")
    nav = navs[0]
    latest = next((e for e in reversed(execution.events) if isinstance(e, t.ProviderAttemptAuthorizedEventV1)), None)
    outcomes = [e for e in execution.events if isinstance(e, t.ProviderOutcomeEventV1)
                and e.provider_attempt_id == nav.provider_attempt_id]
    if latest is None or latest.provider_attempt_id != nav.provider_attempt_id or not outcomes or outcomes[-1].outcome != "response_received":
        raise ValueError("Catalog navigation is no longer the acknowledged provider scope")
    if any(isinstance(e, t.NativeSourceCatalogObservedV1) and e.navigation_id == navigation_id for e in execution.events):
        raise ValueError("Navigation body/catalog has already been acquired")
    return nav


def materialize_catalog_locked(conn, turn, *, navigation_id, event_id):
    execution = turn.graph_context_execution
    for prior in execution.events if execution else ():
        if prior.event_id == event_id:
            if not isinstance(prior, t.NativeSourceCatalogObservedV1) or prior.navigation_id != navigation_id:
                raise ApplicationStateValidationError("Catalog event identity was reused with changed target")
            return prior, None
    try:
        nav = current_navigation(turn, navigation_id)
        t.validate_selected_source_binding(turn.graph_context_receipt, execution)
        proof, _, pin = origin_payload(nav)
    except ValueError as exc:
        raise ApplicationStateValidationError(str(exc)) from exc
    started = perf_counter()
    artifact = proof["resolution"]["artifact"]
    digest = proof["revision"]["content_sha256"]
    metadata = sources.get_source_artifact(conn, pin.source_artifact_id, lock=True)
    source, failure, body = None, None, None
    if metadata is None:
        failure = "source_unavailable"
    elif any(metadata[key] != expected for key, expected in {
            "world_id": nav.world_id, "source_domain": artifact["source_domain"],
            "campaign_id": artifact.get("campaign_id"), "session_id": artifact.get("session_id")}.items()):
        failure = "source_scope_mismatch"
    else:
        source = sources.get_source_markdown(conn, source_artifact_id=pin.source_artifact_id, content_sha256=digest)
        if source is None:
            failure = "source_unavailable"
        elif (source.source_artifact_id != pin.source_artifact_id or source.content_sha256 != digest
                or source.world_id != nav.world_id or source.source_domain != artifact["source_domain"]
                or source.campaign_id != artifact.get("campaign_id") or source.session_id != artifact.get("session_id")):
            failure = "source_identity_mismatch"
        elif source.media_type != "text/markdown" or source.encoding.lower() != "utf-8":
            failure = "source_encoding_mismatch"
        elif sha256(source.markdown.encode("utf-8")).hexdigest() != digest or not source.markdown.strip():
            failure = "source_hash_mismatch"
        else:
            ref = artifact.get("workspace_document_ref")
            if ref and (source.lineage.get("workspace_document_id") != ref["document_id"]
                    or source.lineage.get("workspace_document_revision") != ref["revision"]):
                failure = "source_lineage_mismatch"
            else:
                body = source.markdown
    read_elapsed_ms = max(0, int((perf_counter()-started)*1000))
    catalog_started = perf_counter()
    sections = section_catalog(body, source_artifact_id=pin.source_artifact_id,
        native_source_revision_id=pin.source_revision_id, content_sha256=digest) if body is not None else []
    values = dict(kind="native_source_catalog_observed_v1", event_id=event_id, sequence=len(execution.events),
        navigation_id=navigation_id, source_artifact_id=pin.source_artifact_id,
        native_source_revision_id=pin.source_revision_id, content_sha256=digest,
        app_source_revision_id=source.source_revision_id if body is not None else None,
        selector_policy=SELECTOR, outcome="complete" if body is not None else "unavailable", failure_code=failure,
        sections=sections, lineage_sha256=t._canonical_sha256(source.lineage) if body is not None else None,
        observed_body_sha256=sha256(source.markdown.encode("utf-8")).hexdigest() if source else None,
        body_read_bytes=len(source.markdown.encode("utf-8")) if source else 0,
        body_read_chars=len(source.markdown) if source else 0,
        body_read_elapsed_ms=read_elapsed_ms,
        catalog_elapsed_ms=max(0, int((perf_counter()-catalog_started)*1000)))
    from types import SimpleNamespace
    values["catalog_sha256"] = catalog_digest(SimpleNamespace(**values))
    event = t.NativeSourceCatalogObservedV1(**values)
    material = NativeSourceCatalogMaterial(navigation_id, event_id, source.source_revision_id,
        pin.source_artifact_id, pin.source_revision_id, digest, body) if body is not None else None
    return event, material


def validate_catalog_events(execution):
    navs, completed = {}, set()
    provider, outcome = None, None
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            provider, outcome = event.provider_attempt_id, None
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event, t.NativeSourceNavigationAuthorizedV1):
            navs[event.navigation_id] = event
        elif isinstance(event, t.NativeSourceCatalogObservedV1):
            nav = navs.get(event.navigation_id)
            if (nav is None or event.navigation_id in completed
                    or provider != nav.provider_attempt_id or outcome != "response_received"):
                raise ValueError("Catalog requires one unique earlier acknowledged navigation")
            proof, _, pin = origin_payload(nav)
            if (event.source_artifact_id != pin.source_artifact_id
                    or event.native_source_revision_id != pin.source_revision_id
                    or event.content_sha256 != proof["revision"]["content_sha256"]):
                raise ValueError("Catalog source tuple differs from navigation authorization")
            completed.add(event.navigation_id)
