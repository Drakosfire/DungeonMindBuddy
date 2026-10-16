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
        self._results: dict[str, _Result] = {}
        self._delivered: dict[tuple[str, str], list[_Result]] = {}

    def _remember(self, tool: str, payload: str, result: _Result) -> str:
        entries = self._delivered.setdefault((tool, payload), [])
        if not any(entry is result for entry in entries):
            entries.append(result)
        return payload

    def present(self, tool: str, arguments: dict, raw: str, event_id: UUID) -> str:
        result = _Result(tool, event_id, raw, json.loads(raw))
        payload = self.cache.present(tool, arguments, self.scope, raw)
        value = json.loads(payload)
        if value.get("schema") == OVERVIEW_SCHEMA:
            # Keep parent admission and model-facing workflow aligned. Source
            # opening supplies passage evidence, not a hidden assertion target.
            value["detailUse"] = (
                "For factual claims, fetch the needed complete detail record via resultPageToken. "
                "Do not drain unrelated pages."
            )
            value["interpretation"] = (
                "Discovery only; source reads do not admit hidden targets. Preserve qualifications. "
                "Open the supporting source before citing."
            )
            payload = json.dumps(
                value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            )
            from .graph_tool_transport import PAGE_BYTES

            if len(payload.encode()) > PAGE_BYTES:
                raise ValueError("Parent overview exceeds presentation budget")
        if value.get("schema") in {PAGE_SCHEMA, OVERVIEW_SCHEMA}:
            self._results[value["resultId"]] = result
        elif payload != raw:
            raise ValueError("Parent presentation did not preserve the result")
        return self._remember(tool, payload, result)

    def continuation(self, tool: str, arguments: dict) -> str:
        payload = self.cache.continuation(tool, arguments, self.scope)
        if payload is None:
            raise ValueError("Continuation token required")
        value = json.loads(payload)
        result = self._results.get(value.get("resultId"))
        if result is None:
            raise ValueError(value.get("code", "unknown_graph_result_page"))
        return self._remember(tool, payload, result)

    def inclusion(self, tool: str, payloads: list[str]) -> list[Exposure]:
        groups: dict[UUID, tuple[_Result, list[str]]] = {}
        for payload in set(payloads):
            matches = self._delivered.get((tool, payload), [])
            if len(matches) != 1:
                raise ValueError("Unknown or ambiguous parent presentation")
            result = matches[0]
            groups.setdefault(result.event_id, (result, []))[1].append(payload)
        return [self._exposure(result, pages) for result, pages in groups.values()]

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
                if page.get("schema") == OVERVIEW_SCHEMA:
                    # An index may drop provenance/qualification. It establishes
                    # discovery only; exact records remain on detail pages.
                    continue
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
        )
