"""Parent-owned, turn-local presentation of validated immutable tool results.

The cache owns bytes, not Graph authority. Inclusion is recomputed from the exact
current provider envelope; earlier requests never complete later fragments.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any
from uuid import UUID

from .graph_tool_transport import (
    GraphToolPageCache,
    OVERVIEW_SCHEMA,
    PAGE_SCHEMA,
    TransportScope,
)


@dataclass(frozen=True)
class Exposure:
    event_id: UUID
    assertion_ids: frozenset[str] = frozenset()
    relationship_ids: frozenset[str] = frozenset()
    evidence_ref_ids: frozenset[str] = frozenset()
    complete: bool = False
    # Complete per-target records; authorization separately intersects their
    # declared refs with final-envelope admitted evidence, never event unions.
    claim_evidence: tuple[tuple[str, str, tuple[str, ...]], ...] = ()


@dataclass
class _Result:
    tool: str
    event_id: UUID
    raw: str
    value: dict


class GraphToolPresentation:
    def __init__(self, scope: TransportScope, *, cache=None):
        self.scope = scope
        self.cache = cache if cache is not None else GraphToolPageCache()
        self._bundles: dict[str, tuple[Exposure, tuple[Exposure, ...]]] = {}
        # Only exact literal packets in this turn can donate source bodies.
        self._source_donors: dict[tuple, tuple[str, str]] = {}
        self._bundle_dependencies: dict[str, frozenset[str]] = {}
        self._results: dict[str, _Result] = {}
        self._delivered: dict[tuple[str, str], list[_Result]] = {}

    def _remember(self, tool: str, payload: str, result: _Result) -> str:
        entries = self._delivered.setdefault((tool, payload), [])
        if not any(entry is result for entry in entries):
            entries.append(result)
        return payload

    def present(self, tool: str, arguments: dict, raw: str, event_id: UUID, *,
                source_pins: dict[str, Any] | None = None) -> str:
        result = _Result(tool, event_id, raw, json.loads(raw))
        from .graph_tool_transport import PAGE_BYTES
        if (tool == "expand_graph_retrieval" and arguments.get("operation") == "neighborhood"
                and result.value.get("schema") == "dmb_world_graph_retrieval_result_v1"
                and isinstance(result.value.get("snapshot"), dict)
                and len(raw.encode()) > PAGE_BYTES):
            try:
                # Complete qualified records often fit once repeated anchor
                # metadata is factored. No source was opened by this operation.
                return self.present_bundle(raw, event_id, [])
            except ValueError as exc:
                if str(exc) not in {"evidence_bundle_overflow", "bundle claim lacks exact evidence closure"}:
                    raise
                # Genuinely oversized/incomplete results retain exact paging.
        payload = self.cache.present(tool, arguments, self.scope, raw)
        value = json.loads(payload)
        if value.get("schema") == OVERVIEW_SCHEMA:
            # A targeted object can avoid discovery when its first verified
            # detail page delivers a whole claim and all its source anchors.
            # Remaining records retain explicit continuation metadata.
            if (tool == "expand_graph_retrieval" and arguments.get("operation") in {"object", "observations"}
                    and self.cache.page_bytes == 32_000):
                detail = self.cache.continuation(tool, {
                    **arguments, "resultPageToken": value["detailPageToken"],
                }, self.scope)
                page = json.loads(detail) if detail is not None else {}
                if page.get("schema") == PAGE_SCHEMA:
                    exposure = self._exposure(result, [detail])
                    complete_claim = any(
                        row.get("evidenceRefIds") and set(row["evidenceRefIds"]).issubset(exposure.evidence_ref_ids)
                        and row.get("assertionId", row.get("edgeId")) in (exposure.assertion_ids | exposure.relationship_ids)
                        for key in ("reviewedSourceObservations", "attributes", "relationships")
                        for row in result.value.get(key, [])
                    )
                    if page.get("nextPageToken") is None or complete_claim:
                        payload, value = detail, page
            if value.get("schema") == OVERVIEW_SCHEMA:
                if arguments.get("operation") in {"object", "observations"}:
                    payload = self._initial_records(value, result.value)
                else:
                    # Search/neighborhood exist to discover the next target.
                    # Do not spend their hint budget on unrelated exact edges.
                    value["detailUse"] = (
                        "Fetch the needed complete detail record via resultPageToken before claiming facts. "
                        "Do not drain unrelated pages."
                    )
                    value["interpretation"] = (
                        "Discovery only; use subjectNodeId for object expansion. "
                        "Source reads do not admit hidden targets. Open the supporting source."
                    )
                    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                    from .graph_tool_transport import PAGE_BYTES
                    if len(payload.encode()) > PAGE_BYTES:
                        raise ValueError("Parent discovery exceeds presentation budget")
        if value.get("schema") in {PAGE_SCHEMA, OVERVIEW_SCHEMA}:
            self._results[value["resultId"]] = result
        elif payload != raw:
            raise ValueError("Parent presentation did not preserve the result")
        if tool == "read_graph_source" and self._exposure(result, [payload]).complete:
            rows = result.value.get("reads", [result.value])
            keys = [self._source_identity(row, source_pins or {}) for row in rows]
            if rows and all(key is not None for key in keys):
                # Identical literal bytes and exact pins retain their original
                # receipt binding; a repeated read must not make it ambiguous.
                if all(key in self._source_donors and self._source_donors[key][0] == payload for key in keys):
                    return payload
                for row, key in zip(rows, keys, strict=True):
                    self._source_donors.setdefault(key, (payload, row["anchorId"]))
        return self._remember(tool, payload, result)

    def present_bundle(self, graph_raw: str, event_id: UUID,
                       sources: list[tuple[UUID, str]], *, compact_refs: bool = False, source_read_stop_code: str | None = None,
                       source_pins: dict[str, Any] | None = None) -> str:
        from .graph_evidence_bundle import build_evidence_packet
        graph = json.loads(graph_raw)
        snapshot = graph.get("snapshot", {})
        if (snapshot.get("worldId") != self.scope.world_id
                or snapshot.get("revisionId") != self.scope.revision_id):
            raise ValueError("bundle Graph scope differs from parent")
        source_results = []
        source_exposures = []
        read_groups = []
        for sid, raw in sources:
            value = json.loads(raw)
            rows = value.get("reads", [value])
            source_results.extend(rows)
            read_groups.append((self._exposure(_Result("read_graph_source", sid, raw, value), [raw]), rows))
        packet = build_evidence_packet(graph, source_results, bundle_id=event_id,
            session_id=self.scope.retrieval_session_id, world_id=self.scope.world_id,
            revision_id=self.scope.revision_id, compact_refs=compact_refs,
            source_read_stop_code=source_read_stop_code)
        by_anchor = {row["anchorId"]: row for row in packet["sources"]}
        dependencies = set()
        literal_keys = []
        for exposure, rows in read_groups:
            keys = [self._source_identity(row, source_pins or {}) for row in rows]
            # An execution receipt covers its whole batch. Never expose a later
            # batch receipt for just a subset whose body survived presentation.
            if keys and all(key is not None and key in self._source_donors for key in keys):
                for row, key in zip(rows, keys, strict=True):
                    donor, anchor = self._source_donors[key]
                    dependencies.add(donor)
                    presented = by_anchor[row["anchorId"]]
                    presented["content"] = None
                    donor_value = json.loads(donor)
                    presented["contentRef"] = {
                        **{key: donor_value[key] for key in ("bundleId", "resultId") if key in donor_value},
                        "packetSha256": hashlib.sha256(donor.encode()).hexdigest(),
                        "anchorId": anchor,
                    }
            else:
                source_exposures.append(exposure)
                literal_keys.extend((key, row["anchorId"]) for row, key in zip(rows, keys, strict=True)
                                    if key is not None)
        if dependencies:
            packet["interpretation"] += (
                " A contentRef refers to the identical source body in an earlier literal tool packet "
                "present in this request. Resolve packetSha256 and anchorId there; it grants no new authority."
            )
        payload = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode()) > self.cache.page_bytes:
            raise ValueError("evidence_bundle_overflow")
        graph_exposure = self._exposure(_Result("expand_graph_retrieval", event_id, graph_raw, graph), [graph_raw])
        self._bundles[payload] = (graph_exposure, tuple(source_exposures))
        self._bundle_dependencies[payload] = frozenset(dependencies)
        if not dependencies and all(row.get("content") and row.get("outcome") == "enough"
                                    and not row.get("truncated") for row in packet["sources"]):
            for key, anchor in literal_keys:
                self._source_donors.setdefault(key, (payload, anchor))
        return payload

    def _source_identity(self, row: dict, pins: dict[str, Any]) -> tuple | None:
        content = row.get("content")
        pin = pins.get(row.get("anchorId"))
        if (pin is None or not isinstance(content, str) or not content
                or row.get("outcome") != "enough" or row.get("truncated", False)):
            return None
        def field(name):
            return pin.get(name) if isinstance(pin, dict) else getattr(pin, name, None)
        artifact, revision, evidence = (field(name) for name in (
            "source_artifact_id", "source_revision_id", "evidence_ref_id"))
        if (not all(isinstance(value, str) and value for value in (artifact, revision, evidence))
                or row.get("sourceArtifactId") != artifact or row.get("evidenceRefId") != evidence
                or not isinstance(row.get("lineStart"), int) or not isinstance(row.get("lineEnd"), int)):
            return None
        return (self.scope.retrieval_session_id, self.scope.world_id, self.scope.revision_id,
                row["anchorId"], evidence, artifact, revision, row["lineStart"], row["lineEnd"],
                row["outcome"], bool(row.get("truncated", False)), hashlib.sha256(content.encode()).hexdigest())

    def _validate_bundle_donors(self, payloads: list[str], source_payloads: list[str]) -> None:
        current = set(payloads) | set(source_payloads)
        if any(not self._bundle_dependencies.get(payload, frozenset()).issubset(current)
               for payload in current):
            raise ValueError("Source body reference lacks its exact current-envelope literal donor")

    def bundled_source_inclusion(self, payloads: list[str], *, source_payloads: list[str] = ()) -> list[Exposure]:
        # Whole exact packets only: no substring/handle or old-envelope union.
        self._validate_bundle_donors(payloads, source_payloads)
        by_id = {}
        for payload in set(payloads):
            if payload in self._bundles:
                for item in self._bundles[payload][1]:
                    by_id[item.event_id] = item
        return list(by_id.values())

    @staticmethod
    def _initial_records(overview: dict, original: dict) -> str:
        from .graph_tool_transport import PAGE_BYTES

        def encode():
            return json.dumps(overview, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

        discovery = overview["view"]
        overview["view"] = {key: [] for key in discovery}
        for counts in overview["counts"].values():
            counts.update(shown=0, omitted=counts["total"])
        overview["records"] = []
        overview["completeRecordCounts"] = {"included": 0, "omitted": 0}
        overview["detailUse"] = (
            "Complete records below are available for claims. For a discovery-only target, fetch the "
            "needed complete detail record via resultPageToken. Do not drain unrelated pages."
        )
        overview["interpretation"] = (
            "Only exact complete records grant claim authority; view is discovery only. Preserve qualifications. "
            "Open the supporting source and cite substantive support, not a document header."
        )
        anchors = original.get("sourceAnchors", [])
        included_paths = set()
        claim_groups = ("reviewedSourceObservations", "attributes", "relationships")
        total = sum(len(original.get(key, [])) for key in claim_groups)
        overview["completeRecordCounts"]["omitted"] = total
        if len(encode().encode()) > PAGE_BYTES:
            raise ValueError("Parent overview exceeds presentation budget")
        for key in claim_groups:
            for index, row in enumerate(original.get(key, [])):
                refs = set(row.get("evidenceRefIds") or [])
                if not refs:
                    continue
                supporting = [(i, anchor) for i, anchor in enumerate(anchors)
                              if anchor.get("evidenceRefId") in refs]
                if refs != {anchor.get("evidenceRefId") for _, anchor in supporting}:
                    continue
                bundle = [{"path": [key, index], "value": row}]
                bundle += [{"path": ["sourceAnchors", i], "value": anchor}
                           for i, anchor in supporting if ("sourceAnchors", i) not in included_paths]
                before = len(overview["records"])
                overview["records"].extend(bundle)
                counts = overview["completeRecordCounts"]
                counts["included"] += 1
                counts["omitted"] -= 1
                if len(encode().encode()) > PAGE_BYTES:
                    del overview["records"][before:]
                    counts["included"] -= 1
                    counts["omitted"] += 1
                else:
                    included_paths.update(tuple(record["path"]) for record in bundle)
        # Retain a compact pointer when an oversized description could not
        # appear in the cache's discovery view. A pointer grants no authority.
        for key in claim_groups:
            id_key = "edgeId" if key == "relationships" else "assertionId"
            shown_ids = {row.get(id_key) for row in discovery.get(key, [])}
            for row in original.get(key, []):
                if row.get(id_key) and row[id_key] not in shown_ids:
                    discovery.setdefault(key, []).append({
                        name: row[name] for name in (
                            id_key, "subjectNodeId", "sourceNodeId", "targetNodeId", "predicate",
                            "epistemicKind", "temporalScope", "visibility",
                        ) if name in row
                    })
            for row in discovery.get(key, []):
                row["discoveryOnly"] = True
        # Fill remaining room with the existing bounded discovery rows. Their
        # counts describe only this view, independently of complete records.
        for key, rows in discovery.items():
            for row in rows:
                overview["view"][key].append(row)
                counts = overview["counts"][key]
                counts["shown"] += 1
                counts["omitted"] -= 1
                if len(encode().encode()) > PAGE_BYTES:
                    overview["view"][key].pop()
                    counts["shown"] -= 1
                    counts["omitted"] += 1
        return encode()

    def continuation(self, tool: str, arguments: dict) -> str:
        payload = self.cache.continuation(tool, arguments, self.scope)
        if payload is None:
            raise ValueError("Continuation token required")
        value = json.loads(payload)
        result = self._results.get(value.get("resultId"))
        if result is None:
            raise ValueError(value.get("code", "unknown_graph_result_page"))
        return self._remember(tool, payload, result)

    def inclusion(self, tool: str, payloads: list[str], *, source_payloads: list[str] = ()) -> list[Exposure]:
        if tool == "expand_graph_retrieval":
            self._validate_bundle_donors(payloads, source_payloads)
        groups: dict[UUID, tuple[_Result, list[str]]] = {}
        bundles = []
        for payload in set(payloads):
            if tool == "expand_graph_retrieval" and payload in self._bundles:
                bundles.append(self._bundles[payload][0])
                continue
            matches = self._delivered.get((tool, payload), [])
            if len(matches) != 1:
                raise ValueError("Unknown or ambiguous parent presentation")
            result = matches[0]
            groups.setdefault(result.event_id, (result, []))[1].append(payload)
        return [*bundles, *[self._exposure(result, pages) for result, pages in groups.values()]]

    @staticmethod
    def _exposure(result: _Result, pages: list[str]) -> Exposure:
        if result.raw in pages:
            complete = True
            rows = result.value
        else:
            records: dict[tuple, Any] = {}
            fragments: dict[tuple, dict[int, dict]] = {}
            for payload in pages:
                page = json.loads(payload)
                # Both initial presentations and detail pages can carry exact
                # complete records. Discovery rows are never interpreted here.
                for record in page.get("records", []):
                    path = tuple(record["path"])
                    if "value" in record:
                        records[path] = record["value"]
                    elif record.get("requiresReassembly"):
                        fragments.setdefault(path, {})[record["start"]] = record
            for path, parts in fragments.items():
                ordered = sorted(parts.values(), key=lambda part: part["start"])
                offset, chunks = 0, []
                for part in ordered:
                    if part["start"] != offset:
                        break
                    chunks.append(part["fragment"])
                    offset = part["end"]
                else:
                    text = "".join(chunks)
                    if (
                        ordered
                        and offset == ordered[0]["length"]
                        and hashlib.sha256(text.encode()).hexdigest()
                        == ordered[0]["sha256"]
                    ):
                        records[path] = (
                            text
                            if ordered[0]["fragmentEncoding"] == "text"
                            else json.loads(text)
                        )
            # Only exact complete records count. Paths originate in the parent's
            # own presenter; no worker-supplied path or row is interpreted here.
            rows = {}
            for key, original in result.value.items():
                if key == "claimLedger":
                    continue
                if isinstance(original, list) and original:
                    rows[key] = [
                        row
                        for i, row in enumerate(original)
                        if (key, i) in records and records[(key, i)] == row
                    ]
                elif (key,) in records and records[(key,)] == original:
                    rows[key] = original
            complete = all(
                rows.get(key) == original and key in rows
                for key, original in result.value.items()
            )
        closures = []
        for key, kind, id_key in (
            ("attributes", "assertion", "assertionId"),
            ("reviewedSourceObservations", "assertion", "assertionId"),
            ("relationships", "relationship", "edgeId"),
        ):
            for row in rows.get(key, []):
                refs = row.get("evidenceRefIds")
                target = row.get(id_key)
                if (isinstance(target, str) and target and isinstance(refs, list) and refs
                        and all(isinstance(ref, str) and ref and ref == ref.strip() for ref in refs)):
                    closures.append((kind, target, tuple(sorted(set(refs)))))
        return Exposure(
            event_id=result.event_id,
            assertion_ids=frozenset(
                row["assertionId"]
                for key in ("attributes", "reviewedSourceObservations")
                for row in rows.get(key, [])
                if row.get("assertionId")
            ),
            relationship_ids=frozenset(
                row["edgeId"]
                for row in rows.get("relationships", [])
                if row.get("edgeId")
            ),
            evidence_ref_ids=frozenset(
                row["evidenceRefId"]
                for row in rows.get("sourceAnchors", [])
                if row.get("evidenceRefId")
            ),
            complete=complete,
            claim_evidence=tuple(sorted(set(closures))),
        )
