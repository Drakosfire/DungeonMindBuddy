"""Exact immutable descriptor selection; no new descriptor authority."""

import pytest
from dungeonmind.contracts.vnext import DomainContractRef
from dungeonmind.contracts.semantic_profile import SemanticProfileRef
from graph_memory.vnext import domain_runtime as runtime


def refs(revision="2"):
    return (
        DomainContractRef(
            domain_id=runtime.DUNGEONBUDDY_DOMAIN_ID,
            domain_revision=runtime.DUNGEONBUDDY_DOMAIN_REVISION,
            descriptor_sha256=runtime.DUNGEONBUDDY_DOMAIN_DIGEST,
        ),
        SemanticProfileRef(
            profile_id=runtime.DUNGEONBUDDY_PROFILE_ID,
            profile_revision=revision,
            descriptor_sha256=(
                runtime.DUNGEONBUDDY_CUSTOM_PROFILE_DIGEST
                if revision == "2"
                else runtime.DUNGEONBUDDY_PROFILE_DIGEST
            ),
        ),
    )


@pytest.mark.parametrize("revision", ("1", "2"))
def test_exact_accepted_refs(revision):
    domain, profile = refs(revision)
    actual_domain, actual_profile = runtime.resolve_dungeonbuddy_descriptors(
        domain_ref=domain, profile_ref=profile
    )
    assert (
        runtime.canonical_sha256(actual_domain.model_dump(mode="json"))
        == domain.descriptor_sha256
    )
    assert (
        runtime.canonical_sha256(actual_profile.model_dump(mode="json"))
        == profile.descriptor_sha256
    )
    assert actual_profile.profile_revision == revision


@pytest.mark.parametrize(
    "target,change,code",
    (
        ("domain", {"domain_id": "foreign.world"}, "descriptor_unsupported"),
        ("domain", {"domain_revision": "99"}, "descriptor_unsupported"),
        ("domain", {"descriptor_sha256": "0" * 64}, "descriptor_mismatch"),
        ("profile", {"profile_id": "foreign.profile"}, "descriptor_unsupported"),
        ("profile", {"profile_revision": "99"}, "descriptor_unsupported"),
        ("profile", {"descriptor_sha256": "0" * 64}, "descriptor_mismatch"),
    ),
)
def test_no_fallback(target, change, code):
    domain, profile = refs()
    if target == "domain":
        domain = domain.model_copy(update=change)
    else:
        profile = profile.model_copy(update=change)
    with pytest.raises(runtime.DungeonBuddyDescriptorError) as caught:
        runtime.resolve_dungeonbuddy_descriptors(domain_ref=domain, profile_ref=profile)
    assert caught.value.code == code


@pytest.mark.parametrize("revision", ("1", "2"))
def test_declaration_drift(monkeypatch, revision):
    domain, profile = refs(revision)
    monkeypatch.setattr(runtime, "canonical_sha256", lambda _: "0" * 64)
    with pytest.raises(runtime.DungeonBuddyDescriptorError) as caught:
        runtime.resolve_dungeonbuddy_descriptors(domain_ref=domain, profile_ref=profile)
    assert caught.value.code == "descriptor_drift"
