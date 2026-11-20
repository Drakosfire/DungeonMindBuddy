"""Readable source attribution from registered metadata; never read authority."""
from collections.abc import Mapping
import re


def registered_source_name(artifact: Mapping) -> str | None:
    lineage = artifact.get("lineage")
    name = lineage.get("source_name") if isinstance(lineage, Mapping) else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    # The producer key is opaque (for example dungeonbuddy.recap). An explicit
    # generic family governs presentation; a conflicting key cannot override it.
    domain = artifact.get("source_domain")
    if domain is None:
        # Retain exact legacy key-only metadata; never infer from IDs or paths.
        domain = artifact.get("source_domain_key")
    domain = getattr(domain, "value", domain)
    session = artifact.get("session_id")
    if domain in {"recap", "session_recap"} and isinstance(session, str):
        match = re.fullmatch(r"session-([1-9][0-9]*)", session)
        if match:
            return f"Session {match.group(1)} recap"
    return None
