from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Literal, TypedDict

from graph_memory.union_supergraph.model import UnionIdentityRedirect

RedirectDiagnosticKind = Literal[
    "duplicate_active_from_node_id",
    "self_redirect",
    "active_cycle",
]


class RedirectDiagnostic(TypedDict):
    kind: RedirectDiagnosticKind
    message: str


def active_identity_redirect_map(
    redirects: Iterable[UnionIdentityRedirect],
) -> dict[str, UnionIdentityRedirect]:
    """Build a lookup map of active redirects keyed by merged-away node id."""
    result: dict[str, UnionIdentityRedirect] = {}
    for redirect in redirects:
        if redirect.status != "active":
            continue
        result[redirect.from_node_id] = redirect
    return result


def _coerce_active_redirect_map(
    redirects: Mapping[str, UnionIdentityRedirect] | Iterable[UnionIdentityRedirect],
) -> dict[str, UnionIdentityRedirect]:
    if isinstance(redirects, Mapping):
        return {
            from_node_id: redirect
            for from_node_id, redirect in redirects.items()
            if redirect.status == "active"
        }
    return active_identity_redirect_map(redirects)


def resolve_union_node_id(
    node_id: str,
    redirects: Mapping[str, UnionIdentityRedirect] | Iterable[UnionIdentityRedirect],
) -> str:
    """Resolve active graph identity redirects transitively and cycle-safely."""
    redirect_map = _coerce_active_redirect_map(redirects)
    visited: set[str] = set()
    current = node_id
    while current in redirect_map:
        if current in visited:
            return node_id
        visited.add(current)
        current = redirect_map[current].to_node_id
    return current


def is_redirected_node_id(
    node_id: str,
    redirects: Mapping[str, UnionIdentityRedirect] | Iterable[UnionIdentityRedirect],
) -> bool:
    redirect_map = _coerce_active_redirect_map(redirects)
    return node_id in redirect_map


def redirect_chain(
    node_id: str,
    redirects: Mapping[str, UnionIdentityRedirect] | Iterable[UnionIdentityRedirect],
) -> list[str]:
    """Return the redirect chain from node_id, including cycle terminus when present."""
    redirect_map = _coerce_active_redirect_map(redirects)
    chain = [node_id]
    visited: set[str] = {node_id}
    current = node_id
    while current in redirect_map:
        next_id = redirect_map[current].to_node_id
        chain.append(next_id)
        if next_id in visited:
            break
        visited.add(next_id)
        current = next_id
    return chain


def collect_redirect_diagnostics(
    redirects: Iterable[UnionIdentityRedirect],
) -> list[RedirectDiagnostic]:
    """Collect structural problems in identity redirect records."""
    diagnostics: list[RedirectDiagnostic] = []
    active_by_from: dict[str, list[UnionIdentityRedirect]] = {}

    for redirect in redirects:
        if redirect.from_node_id == redirect.to_node_id:
            diagnostics.append(
                {
                    "kind": "self_redirect",
                    "message": (
                        f"redirect {redirect.redirect_id} has identical "
                        f"from_node_id and to_node_id ({redirect.from_node_id})"
                    ),
                }
            )
        if redirect.status == "active":
            active_by_from.setdefault(redirect.from_node_id, []).append(redirect)

    for from_node_id, entries in active_by_from.items():
        if len(entries) > 1:
            redirect_ids = ", ".join(entry.redirect_id for entry in entries)
            diagnostics.append(
                {
                    "kind": "duplicate_active_from_node_id",
                    "message": (
                        f"multiple active identity redirects for from_node_id "
                        f"{from_node_id}: {redirect_ids}"
                    ),
                }
            )

    active_map = active_identity_redirect_map(redirects)
    for from_node_id in active_map:
        chain = redirect_chain(from_node_id, active_map)
        if len(chain) >= 2 and chain[-1] in chain[:-1]:
            diagnostics.append(
                {
                    "kind": "active_cycle",
                    "message": (
                        f"active identity redirect cycle detected starting at "
                        f"{from_node_id}: {' -> '.join(chain)}"
                    ),
                }
            )
            break

    return diagnostics


def validate_identity_redirects(
    redirects: Iterable[UnionIdentityRedirect],
) -> list[str]:
    """Return human-readable validation errors for identity redirects."""
    return [item["message"] for item in collect_redirect_diagnostics(redirects)]


def identity_redirect_dicts_from_fixture(
    fixture: Mapping[str, Any],
) -> list[dict[str, Any]]:
    raw = fixture.get("identity_redirects", [])
    return raw if isinstance(raw, list) else []
