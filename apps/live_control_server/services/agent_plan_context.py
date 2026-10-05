"""Pure extraction from a validated exact committed Plan, never a draft."""

import re


def selected_scene_markdown(markdown: str, scene_id: str) -> str:
    lines = markdown.replace("\r\n", "\n").splitlines(keepends=True)
    fence = None
    start = None
    level = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"^(`{3,}|~{3,})", stripped)
        if match:
            mark = match.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence):
                fence = None
            continue
        if fence:
            continue
        if start is None and re.match(
            r"^<!-- dmb-playable-element:v[12] kind=scene id="
            + re.escape(scene_id)
            + r" -->$",
            stripped,
        ):
            start = i
            continue
        heading = re.match(r"^(#{1,6}) ", line)
        if start is not None and heading:
            depth = len(heading.group(1))
            if level is None:
                level = depth
            elif depth <= level:
                end = (
                    i - 1
                    if i
                    and lines[i - 1].strip().startswith("<!-- dmb-playable-element:")
                    else i
                )
                return "".join(lines[start:end])
    if start is None or level is None:
        raise ValueError("The selected scene is unavailable in the committed Plan.")
    return "".join(lines[start:])
