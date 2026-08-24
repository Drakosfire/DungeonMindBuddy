"""Graph Kernel identity classification (PR004).

``resolve_identity`` / ``classify_identity_outcome`` are pure classifiers: they
return an explicit outcome and do **not** mutate the durable graph. Mutations
happen only through decision-record APIs in ``identity_decisions``.

The storage-neutral algorithm lives in ``world_graph_mutation_context``. This
module adapts a file-backed ``UnionSupergraphStore`` into that context.
"""

from __future__ import annotations

from collections.abc import Iterable

from graph_memory.kernel.identity_models import (
    IdentityCandidate,
    IdentityDecisionRecord,
    IdentityResolution,
)
from graph_memory.kernel.identity_policy import IdentityResolutionPolicy
from graph_memory.union_supergraph.model import UnionSupergraphStore


def _load_decision_records(store: UnionSupergraphStore) -> list[IdentityDecisionRecord]:
    records: list[IdentityDecisionRecord] = []
    for raw in store.identity_decisions:
        try:
            records.append(IdentityDecisionRecord.model_validate(raw))
        except Exception:
            continue
    return records


def classify_identity_outcome(
    store: UnionSupergraphStore,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy | None = None,
) -> IdentityResolution:
    """Classify a candidate into an explicit identity outcome without mutating ``store``.

    File-mode wrapper: adapt the store into ``WorldGraphMutationContext`` and
    run the single storage-neutral classifier.
    """
    from graph_memory.world_graph_mutation_context import (
        mutation_context_from_store,
        resolve_identity_against_context,
    )

    context = mutation_context_from_store(
        store,
        world_id=candidate.world_id,
        revision_id="",
        head_revision_id="",
    )
    return resolve_identity_against_context(context, candidate, policy=policy)


def resolve_identity(
    store: UnionSupergraphStore,
    candidate: IdentityCandidate,
    *,
    policy: IdentityResolutionPolicy | None = None,
) -> IdentityResolution:
    """Resolve identity outcome. Does not mutate ``store``."""
    return classify_identity_outcome(store, candidate, policy=policy)


def iter_active_identity_decisions(
    store: UnionSupergraphStore,
) -> Iterable[IdentityDecisionRecord]:
    for record in _load_decision_records(store):
        if record.status == "active":
            yield record
