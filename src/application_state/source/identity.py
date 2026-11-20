"""Buddy producer identity normalization shared by native admission and reads."""


def canonical_source_domain_key(raw: str) -> str:
    """Preserve the existing Buddy-native recap producer fingerprint contract.

    This is the admission producer's key normalization, not a mapping from an
    arbitrary opaque key to DungeonMind's independent provenance family.
    """
    key = str(raw or "").strip()
    if key == "recap":
        return "session_recap"
    return key
