"""Worker-local presentation cache for already authorized immutable Graph results.

This cache grants no Graph or citation authority. All continuations are bound to
an active scope and the original request and never execute another operation.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import secrets
from threading import RLock
from time import monotonic
from typing import Any

PAGE_BYTES = 8_000
CACHE_BYTES = 8_000_000
CACHE_SECONDS = 300
PAGE_SCHEMA = "dmb_graph_tool_page_v1"
PAGED_TOOLS = frozenset(
    {"expand_graph_retrieval", "read_graph_source", "read_related_recap_context"}
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _size(value: Any) -> int:
    return len(_json(value).encode("utf-8"))


def _error(code: str) -> str:
    return _json(
        {
            "schema": "dmb_world_graph_retrieval_error_v1",
            "code": code,
            "statusCode": 409,
            "message": "Graph result page unavailable. The original operation was not repeated. Request a fresh operation explicitly if needed.",
            "diagnostics": [],
        }
    )


def _request_key(arguments: Mapping[str, Any]) -> str:
    clean = {k: v for k, v in arguments.items() if k != "resultPageToken"}
    return hashlib.sha256(_json(clean).encode()).hexdigest()


@dataclass(frozen=True)
class TransportScope:
    retrieval_session_id: str
    world_id: str
    revision_id: str


@dataclass
class _Entry:
    scope: TransportScope
    tool: str
    request_key: str
    expires: float
    pages: list[str]
    tokens: dict[str, int]
    byte_count: int


class GraphToolPageCache:
    def __init__(
        self, *, clock=monotonic, lifetime=CACHE_SECONDS, max_bytes=CACHE_BYTES
    ):
        self._clock = clock
        self._lifetime = lifetime
        self._max_bytes = max_bytes
        self._entries: OrderedDict[str, _Entry] = OrderedDict()
        self._lock = RLock()

    def _prune(self):
        for key in list(self._entries):
            if self._entries[key].expires <= self._clock():
                del self._entries[key]
        while sum(e.byte_count for e in self._entries.values()) > self._max_bytes:
            self._entries.popitem(last=False)

    def continuation(
        self, tool: str, arguments: Mapping[str, Any], scope: TransportScope
    ) -> str | None:
        if "resultPageToken" not in arguments:
            return None
        token = arguments["resultPageToken"]
        if not isinstance(token, str) or not token:
            return _error("invalid_graph_result_page")
        with self._lock:
            self._prune()
            for entry in self._entries.values():
                if token not in entry.tokens:
                    continue
                if (
                    entry.scope != scope
                    or entry.tool != tool
                    or entry.request_key != _request_key(arguments)
                ):
                    return _error("foreign_graph_result_page")
                return entry.pages[entry.tokens[token]]
        return _error("expired_or_unknown_graph_result_page")

    def present(
        self, tool: str, arguments: Mapping[str, Any], scope: TransportScope, raw: str
    ) -> str:
        """Keep small results unchanged; page oversized results without losing records."""
        if len(raw.encode()) <= PAGE_BYTES:
            return raw
        value = json.loads(raw)
        if not isinstance(value, dict):
            return _error("invalid_graph_result_shape")
        # The complete ledger remains authoritative in its original session.
        # Only operation-local claims already identified by the producer travel.
        value = dict(value)
        if isinstance(value.get("claimLedger"), list):
            ids = set(value.get("addedClaimIds") or [])
            value["claimDelta"] = [
                c
                for c in value.pop("claimLedger")
                if c.get("claim_id", c.get("claimId")) in ids
            ]
        result_id = secrets.token_hex(16)
        header = {
            "schema": PAGE_SCHEMA,
            "resultId": result_id,
            "tool": tool,
            "retrievalSessionId": scope.retrieval_session_id,
            "worldId": scope.world_id,
            "revisionId": scope.revision_id,
            "resultSchema": value.get("schema"),
            "outcome": value.get("outcome"),
            "coreCoverage": value.get("coverage"),
            "coreTruncated": bool(
                value.get("truncated")
                or value.get("outcome") == "truncated"
                or (value.get("coverage") or {}).get("truncatedFields")
            ),
            "ledgerDelivery": "operation-local claims; complete ledger remains in Graph session",
        }
        priority = [
            "reviewedSourceObservationMatches",
            "reviewedSourceObservations",
            "nodes",
            "attributes",
            "relationships",
            "sourceAnchors",
            "claimDelta",
        ]
        keys = [k for k in priority if k in value] + [
            k for k in value if k not in priority
        ]
        records = []
        for key in keys:
            item = value[key]
            units = (
                [([key, i], v) for i, v in enumerate(item)]
                if isinstance(item, list) and item
                else [([key], item)]
            )
            for path, row in units:
                record = {"path": path, "value": row}
                if _size(record) <= 6_000:
                    records.append(record)
                    continue
                # A fragment is explicitly not a complete assertion. Unicode
                # offsets/digest let the consumer reconstruct the exact value.
                text = row if isinstance(row, str) else _json(row)
                digest = hashlib.sha256(text.encode()).hexdigest()
                offset = 0
                while offset < len(text):
                    end = min(offset + 800, len(text))
                    records.append(
                        {
                            "path": path,
                            "fragmentEncoding": "text"
                            if isinstance(row, str)
                            else "json",
                            "fragment": text[offset:end],
                            "start": offset,
                            "end": end,
                            "length": len(text),
                            "sha256": digest,
                            "requiresReassembly": True,
                        }
                    )
                    offset = end
        batches = []
        batch = []
        # Reserve every wrapper/token/count byte before admitting a record.
        for record in records:
            probe = {
                **header,
                "pageIndex": len(batches),
                "records": batch + [record],
                "transportTruncated": True,
                "nextPageToken": "x" * 48,
                "remainingRecords": len(records),
                "recordCount": len(records),
            }
            if _size(probe) > PAGE_BYTES:
                if not batch:
                    return _error("graph_result_record_over_budget")
                batches.append(batch)
                batch = []
                probe["records"] = [record]
                if _size(probe) > PAGE_BYTES:
                    return _error("graph_result_record_over_budget")
            batch.append(record)
        if batch:
            batches.append(batch)
        tokens = [secrets.token_hex(24) for _ in batches]
        pages = []
        delivered = 0
        for i, batch in enumerate(batches):
            delivered += len(batch)
            page = {
                **header,
                "pageIndex": i,
                "records": batch,
                "transportTruncated": i + 1 < len(batches),
                "nextPageToken": tokens[i + 1] if i + 1 < len(batches) else None,
                "remainingRecords": len(records) - delivered,
                "recordCount": len(records),
            }
            encoded = _json(page)
            if len(encoded.encode()) > PAGE_BYTES:
                return _error("graph_result_page_over_budget")
            pages.append(encoded)
        byte_count = sum(len(p.encode()) for p in pages)
        if not pages or byte_count > self._max_bytes:
            return _error("graph_result_cache_over_budget")
        entry = _Entry(
            scope,
            tool,
            _request_key(arguments),
            self._clock() + self._lifetime,
            pages,
            {token: i for i, token in enumerate(tokens)},
            byte_count,
        )
        with self._lock:
            self._entries[result_id] = entry
            self._prune()
        return pages[0]
