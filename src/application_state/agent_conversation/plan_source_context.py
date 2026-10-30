"""Typed Plan capability bases; no cross-family revision or authority aliases."""
from __future__ import annotations
from dataclasses import dataclass
from . import types as t
from .native_corpus import NativeCorpusAuthorityV1


@dataclass(frozen=True)
class PlanCapabilityBases:
    receipt: t.PlanWorldGraphContextReceiptV1 | t.PlanSourceContextReceiptV1
    graph: t.PlanWorldGraphContextReceiptV1 | None
    source: NativeCorpusAuthorityV1 | t.NativeCorpusUnavailableV1 | None

    @property
    def plan_basis(self):
        return self.receipt.plan_basis


def capability_bases(receipt):
    if isinstance(receipt, t.PlanSourceContextReceiptV1):
        return PlanCapabilityBases(receipt, receipt.graph_capability, receipt.source_authority)
    if isinstance(receipt, t.PlanWorldGraphContextReceiptV1):
        return PlanCapabilityBases(receipt, receipt, None)
    raise ValueError("Resolved Plan capability receipt required")


def require_graph(receipt):
    graph = capability_bases(receipt).graph
    if graph is None:
        raise ValueError("This Plan turn has no authorized Graph capability")
    return graph
