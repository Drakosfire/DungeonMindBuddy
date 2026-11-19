"""Sealed values for the pure, two-stage first-World compiler.

These packets establish neither current source admission nor publication eligibility.
B2 owns live source authorization, reservation, ancestry and native APP activation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from dungeonmind.contracts.vnext.native_source import NativeUtf8SpanProofV1
from dungeonmind.contracts.vnext.prospective_aliases import ProspectiveAliasContributionV1
from dungeonmind.contracts.vnext.contribution import ContributionDisposition
from dungeonmind.contracts.vnext.source import SourceRevisionV2


class FirstWorldCompilationError(ValueError):
    """A closed compiler refusal; callers must not substitute a classic write."""

    def __init__(self, code: str, field: str = "") -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code}: {field}" if field else code)


@dataclass(frozen=True, slots=True)
class FirstWorldNativeIntent:
    """Canonical reviewed input and mapping; never an executable Kernel request."""

    canonical_json: str
    sha256: str

    @property
    def audit(self) -> dict:
        return json.loads(self.canonical_json)

    @property
    def publishing(self) -> bool:
        return bool(self.audit["nodes"])


@dataclass(frozen=True, slots=True)
class FirstWorldNativeSpanBinding:
    """Owner-supplied raw-reference to native-proof association, sealed on creation.

    Core proofs bind intervals and IDs, not mutable source authorization. The binder
    checks these against retained source bytes and the actual parsed parent. The
    sealed revision binds the full body digest, beyond the cited slice. Neither
    record proves the raw-to-native document association or live source authority.
    """

    reviewed_evidence_ref_id: str
    proof_json: str
    source_revision_json: str

    @classmethod
    def from_proof(
        cls, reviewed_evidence_ref_id: str, proof: NativeUtf8SpanProofV1,
        *, source_revision: SourceRevisionV2,
    ) -> FirstWorldNativeSpanBinding:
        validated = NativeUtf8SpanProofV1.model_validate(proof.model_dump(mode="python"))
        revision = SourceRevisionV2.model_validate(source_revision.model_dump(mode="python"))
        return cls(reviewed_evidence_ref_id, validated.model_dump_json(), revision.model_dump_json())

    @property
    def proof(self) -> NativeUtf8SpanProofV1:
        return NativeUtf8SpanProofV1.model_validate_json(self.proof_json)


    @property
    def source_revision(self) -> SourceRevisionV2:
        return SourceRevisionV2.model_validate_json(self.source_revision_json)


@dataclass(frozen=True, slots=True)
class BoundFirstWorldNativeCompilation:
    """Fresh public models on every access; no mutable model is retained."""

    intent_sha256: str
    request_json: str
    dispositions_json: str
    request_sha256: str
    parent_revision_id: str
    parent_semantic_digest: str

    @property
    def request(self) -> ProspectiveAliasContributionV1:
        return ProspectiveAliasContributionV1.model_validate_json(self.request_json)

    @property
    def dispositions(self) -> list[ContributionDisposition]:
        return [
            ContributionDisposition.model_validate(row)
            for row in json.loads(self.dispositions_json)
        ]
