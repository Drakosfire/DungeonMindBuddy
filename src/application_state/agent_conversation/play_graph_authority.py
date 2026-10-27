"""Native Play intent/source algorithms; wire models belong to the APP type owner."""
from __future__ import annotations

from . import types as t
from .rules_authority_types import canonical_sha256


def play_graph_intent_fingerprint(intent: t.PlayGraphIntentV1) -> str:
    """New explicit protocol; never reinterprets a historical intent algorithm."""
    checked = t.PlayGraphIntentV1.model_validate_json(intent.model_dump_json(by_alias=True))
    return canonical_sha256(checked.model_dump(mode='json', by_alias=True, exclude={'client_thread_id'}))


def play_source_frame(sources: tuple[t.PlaySourcePayloadV1, ...]) -> t.PlaySourceFrameV1:
    pairs = sorted(((t.source_entry(source), source) for source in sources), key=lambda pair: pair[0].source_id)
    entries = tuple((entry for entry, _ in pairs))
    seal = canonical_sha256({'schema': 'dmb_play_source_manifest_v1', 'entries': [entry.model_dump(mode='json', by_alias=True) for entry in entries]})
    return t.PlaySourceFrameV1(manifest=t.PlaySourceManifestV1(entries=entries, manifest_sha256=seal), sources=tuple((source for _, source in pairs)))


def validate_play_source_owner_join(frame: t.PlaySourceFrameV1, basis: t.PlayRunTurnContextReceiptV2, *, owner_resolved_current_moment_text: str | None) -> None:
    """Check exact owner values, NOT obtain their authority or prove provider inclusion.

    Admission must supply the independently Run/edition-owner-resolved basis/text.
    Passing arbitrary model/caller text here cannot turn it into source authority.
    Actual first/final provider input inclusion remains a separate required proof.
    """
    checked = t.PlaySourceFrameV1.model_validate_json(frame.model_dump_json(by_alias=True))
    basis = t.PlayRunTurnContextReceiptV2.model_validate_json(basis.model_dump_json(by_alias=True))
    expected = (basis.world_id, basis.run_id, basis.run_revision, basis.edition_revision, basis.edition_revision_id, basis.content_sha256, basis.beat_id, basis.scene_id)
    kinds = set()
    for source in checked.sources:
        loc = source.locator
        actual = (loc.world_id, loc.run_id, loc.run_revision, loc.edition.edition_revision, loc.edition.edition_revision_id, loc.edition.content_sha256, loc.beat_id, loc.scene_id)
        if actual != expected or source.source_kind in kinds:
            raise ValueError('Play source differs from its exact owning Run/edition/target')
        kinds.add(source.source_kind)
        text = basis.scene_note if source.source_kind == 'scene_note' else owner_resolved_current_moment_text
        if text is None or source.text != text:
            raise ValueError('Play source body was not supplied by its independent source owner')


def play_graph_execution_policy_digest(context_receipt_sha256: str, policy: t.NativePlayGraphPolicyV1) -> str:
    cls = (t.PlayCorpusSourceSectionsPolicyV1 if isinstance(policy,t.PlayCorpusSourceSectionsPolicyV1) else
        t.PlayNativeSourceSectionsPolicyV1 if isinstance(policy,t.PlayNativeSourceSectionsPolicyV1) else t.NativePlayGraphPolicyV1)
    checked = cls.model_validate_json(policy.model_dump_json(by_alias=True))
    return canonical_sha256({'schema': 'dmb_play_world_graph_execution_v1', 'context_receipt_sha256': context_receipt_sha256, 'policy': checked.model_dump(mode='json', by_alias=True)})
