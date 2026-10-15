"""Read bounded native support for one explicitly selected Graph subject."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from graph_memory.interaction.expansion_executor import execute_read_graph_source
from graph_memory.interaction.session import SourceReadReceiptV2
from graph_memory.interaction.session_store import replace_session

MAX_ANCHORS = 16
MAX_CHARACTERS = 24000
MAX_PER_ANCHOR = 3000


def _focus(value):
    value = value if isinstance(value, Mapping) else {}
    return (
        value.get("kind", "none"),
        value.get("session_id", value.get("sessionId")),
        value.get("campaign_id", value.get("campaignId")),
    )


def _snapshot_matches(snapshot, session):
    expected = session.snapshot
    return isinstance(snapshot, Mapping) and all(
        (
            snapshot.get("worldId") == expected.world_id,
            snapshot.get("campaignId") == expected.campaign_id,
            snapshot.get("revisionId") == expected.revision_id,
            snapshot.get("scopeMode") == expected.scope_mode,
            snapshot.get("admissibility") == expected.admissibility,
            _focus(snapshot.get("focus")) == _focus(expected.focus),
        )
    )


def hydrate_selected_subject_sources(
    session, envelope: Mapping[str, Any], *, root: Path
):
    """Return private opened bodies/coverage; never introduce Graph assertions."""
    ids = envelope.get("matched_node_ids") or []
    if not (
        envelope.get("excerpt_policy") == "provenance_context_not_citation"
        and envelope.get("completeness") == "complete"
        and (len(ids) == 1)
        and (session.snapshot.admissibility == "gm")
        and (envelope.get("admissibility") == "gm")
        and (envelope.get("world_id") == session.snapshot.world_id)
        and (envelope.get("revision_id") == session.snapshot.revision_id)
        and (envelope.get("campaign_id") == session.snapshot.campaign_id)
        and (
            envelope.get("retrieval_scope_mode", envelope.get("scope_mode"))
            == session.snapshot.scope_mode
        )
        and (_focus(envelope.get("focus")) == _focus(session.snapshot.focus))
    ):
        return None
    subject = ids[0]
    claims = [
        c for c in session.claims if subject in (c.subject_node_id, c.object_node_id)
    ]
    declared = sorted({a for c in claims for a in c.support.source_anchor_ids})
    admitted = {a.anchor_id: a for a in session.source_anchors}
    eligible = [a for a in declared if a in admitted and admitted[a].readable]
    selected = eligible[:MAX_ANCHORS]
    expected_refs = {
        a: {
            ref
            for c in claims
            if a in c.support.source_anchor_ids
            for ref in c.evidence_ref_ids
        }
        for a in selected
    }
    opened, bodies, gaps, attempted, truncated = (set(), [], [], [], set())
    if len(eligible) < len(declared):
        gaps.append("selected_support_missing_or_unreadable")
    if len(selected) < len(eligible):
        gaps.append("selected_support_anchor_budget")
    remaining = MAX_CHARACTERS
    for start in range(0, len(selected), 8):
        batch = selected[start : start + 8]
        per_anchor = min(MAX_PER_ANCHOR, remaining // (len(selected) - start))
        if per_anchor < 1:
            gaps.append("selected_support_character_budget")
            break
        before = session.model_copy(deep=True)
        attempted.extend(batch)
        try:
            packet = execute_read_graph_source(
                {
                    "retrievalSessionId": session.id,
                    "anchorIds": batch,
                    "maxChars": per_anchor,
                },
                root=root,
                receipt_version=2,
            )
            if not packet.get("schema") == "dmb_internal_read_graph_source_batch_v2":
                raise ValueError("Invalid native selected-source read")
            if not packet.get("retrievalSessionId") == session.id:
                raise ValueError("Invalid native selected-source read")
            rows = packet.get("reads")
            if not (isinstance(rows, list) and len(rows) == len(batch)):
                raise ValueError("Invalid native selected-source read")
            seen, valid, characters, partial = (set(), [], 0, set())
            for row in rows:
                result = row.get("result")
                if not isinstance(result, Mapping):
                    raise ValueError("Invalid native selected-source read")
                anchor = result.get("anchorId")
                if not (anchor in batch and anchor not in seen):
                    raise ValueError("Invalid native selected-source read")
                seen.add(anchor)
                content, outcome = (result.get("content"), result.get("outcome"))
                if outcome not in {"enough", "partial", "truncated"}:
                    if not (
                        outcome in {"denied", "unavailable", "empty"} and (not content)
                    ):
                        raise ValueError("Invalid native selected-source read")
                    failures = [
                        entry
                        for entry in session.source_reads[len(before.source_reads) :]
                        if entry.anchor_id == anchor
                    ]
                    anchor_state = next(
                        (a for a in session.source_anchors if a.anchor_id == anchor),
                        None,
                    )
                    if (
                        result.get("schema") != "dmb_world_graph_source_anchor_read_v1"
                        or row.get("receipt") is not None
                        or len(failures) != 1
                        or failures[0].source_read_id != row.get("sourceReadId")
                        or failures[0].outcome != outcome
                        or failures[0].receipt_v2 is not None
                        or anchor_state is None
                        or anchor_state.opened
                        or (
                            result.get("snapshot") is not None
                            and not _snapshot_matches(result["snapshot"], session)
                        )
                    ):
                        raise ValueError("Inconsistent native non-content read")
                    continue
                if not result.get("schema") == "dmb_world_graph_source_anchor_read_v1":
                    raise ValueError("Invalid native selected-source read")
                if not (
                    isinstance(content, str)
                    and content
                    and (len(content) <= per_anchor)
                ):
                    raise ValueError("Invalid native selected-source read")
                if not _snapshot_matches(result.get("snapshot"), session):
                    raise ValueError("Invalid native selected-source read")
                receipt = SourceReadReceiptV2.model_validate(row.get("receipt"))
                if not (
                    receipt.anchor_id == anchor
                    and receipt.retrieval_session_id == session.id
                ):
                    raise ValueError("Invalid native selected-source read")
                if not receipt.graph_revision == session.snapshot.revision_id:
                    raise ValueError("Invalid native selected-source read")
                if not receipt.source_read_id == row.get("sourceReadId"):
                    raise ValueError("Invalid native selected-source read")
                if not receipt.source_artifact_id == result.get("sourceArtifactId"):
                    raise ValueError("Invalid native selected-source read")
                if not receipt.source_span_ref_id == result.get("sourceSpanRefId"):
                    raise ValueError("Invalid native selected-source read")
                if not receipt.evidence_ref_id == result.get("evidenceRefId"):
                    raise ValueError("Invalid native selected-source read")
                if receipt.evidence_ref_id not in expected_refs[anchor]:
                    raise ValueError("Invalid native selected-source read")
                if not receipt.read_content_sha256 == result.get("contentSha256"):
                    raise ValueError("Invalid native selected-source read")
                if (
                    receipt.locator_kind != "json_pointer"
                    and receipt.source_revision_sha256.removeprefix("sha256:")
                    != receipt.read_content_sha256.removeprefix("sha256:")
                ):
                    raise ValueError("Invalid native selected-source read")
                if not (
                    receipt.outcome == outcome
                    and receipt.truncated == bool(result.get("truncated"))
                ):
                    raise ValueError("Invalid native selected-source read")
                if not any(
                    (
                        r.source_read_id == receipt.source_read_id
                        and r.receipt_v2 == receipt
                        for r in session.source_reads
                    )
                ):
                    raise ValueError("Invalid native selected-source read")
                characters += len(content)
                valid.append(row)
                if outcome != "enough" or receipt.truncated:
                    partial.add(anchor)
            appended = session.source_reads[len(before.source_reads) :]
            if (
                len(appended) != len(rows)
                or len({r.source_read_id for r in appended}) != len(appended)
                or bool(
                    {r.source_read_id for r in appended}
                    & {r.source_read_id for r in before.source_reads}
                )
                or {r.source_read_id for r in appended}
                != {r.get("sourceReadId") for r in rows}
                or any(r.anchor_id not in batch for r in appended)
            ):
                raise ValueError("Inconsistent native batch read ledger")
            if not (seen == set(batch) and characters <= remaining):
                raise ValueError("Invalid native selected-source read")
            for operation in session.operations[len(before.operations) :]:
                operation.requested_by = "server_initial"
            replace_session(session)
            bodies.extend(valid)
            opened.update((r["result"]["anchorId"] for r in valid))
            truncated.update(partial)
            remaining -= characters
            if len(valid) != len(batch):
                gaps.append("selected_support_read_unavailable")
            if partial:
                gaps.append("selected_support_partial_read")
        except Exception:
            for field in type(session).model_fields:
                setattr(session, field, getattr(before, field))
            replace_session(session)
            gaps.append("selected_support_batch_invalid")
    coverage = {
        "declared": len(declared),
        "eligible": len(eligible),
        "selected": len(selected),
        "attempted": len(attempted),
        "opened": len(opened),
        "truncated": len(truncated),
        "unread": len(set(declared) - opened),
        "returnedCharacters": MAX_CHARACTERS - remaining,
        "state": "complete"
        if declared and len(opened) == len(declared) and (not gaps)
        else "partial",
        "gapCodes": sorted(set(gaps)),
        "scope": "selected_subject_admitted_support_only",
    }
    return {
        "initial_opened_source_reads": bodies,
        "initial_source_read_coverage": coverage,
    }
