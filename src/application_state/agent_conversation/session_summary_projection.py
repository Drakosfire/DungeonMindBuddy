"""Host projection of admitted session support; no retrieval or new citation authority."""
from urllib.parse import urlencode

from .types import SessionSummaryV1


def citation_target(world_id, support):
    if not isinstance(world_id, str) or not world_id.strip():
        raise ValueError("Session citation requires its owning World")
    fragment = (f"source-{support.source_ordinal}-{support.entry_identity}-"
                f"{support.body_sha256}-{support.owner_sha256}-{support.checkpoint_content_sha256}")
    return "/play?" + urlencode({"world": world_id, "run": support.object_id,
                                  "evidence_revision": support.revision}) + "#" + fragment


def summary_markdown(segment, world_id, first_number=1):
    if not isinstance(segment, SessionSummaryV1):
        return segment.text, first_number
    references = []
    seen = set()
    for support in segment.supports:
        target = citation_target(world_id, support)
        if target in seen:
            continue
        seen.add(target)
        label = "Closing reflections" if support.entry_kind == "closing_reflections" else "Scene notes"
        title = (support.source_name + " · " + label).replace("\\", "\\\\").replace('"', '\\"')
        references.append(f'[{first_number}]({target} "{title}")')
        first_number += 1
    return segment.text + " " + " ".join(references), first_number
