"""Check local links in a small set of maintained documentation entry points.

Run ``uv run python scripts/check_docs_links.py .`` from the repository root.
External and root-relative URLs, shortcut references and non-Markdown fragments
are outside this check. Heading IDs are approximated, not GitHub-rendered.
"""

from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from markdown_it.common.utils import normalizeReference

ENTRYPOINTS = (
    "README.md",
    "Docs/README.md",
    "evals/README.md",
    "apps/live-control-ui/README.md",
    "Docs/Guides/GUIDE-local-world-storage.md",
    "Docs/Guides/GUIDE-source-ingestion-and-evidence.md",
    "Docs/Guides/GUIDE-surface-contributor-map.md",
    "Docs/Guides/GUIDE-agent-context-and-runtime.md",
    "Docs/Guides/GUIDE-handoff-and-evidence-navigation.md",
    "Docs/Guides/GUIDE-development-verification.md",
    "Docs/Runbooks/RUNBOOK-local-play-dogfood.md",
)


def observe_reference(state, silent):
    """Report unresolved explicit/collapsed references before escape loss."""
    if silent or state.src[state.pos] != "[":
        return False
    end = state.md.helpers.parseLinkLabel(state, state.pos, True)
    if end < 0 or end + 1 >= state.posMax or state.src[end + 1] != "[":
        return False
    label_end = state.md.helpers.parseLinkLabel(state, end + 1)
    if label_end < 0:
        return False
    label = state.src[end + 2 : label_end] or state.src[state.pos + 1 : end]
    if normalizeReference(label) not in state.env.get("references", {}):
        state.env.setdefault("unresolved", []).append(state.src[state.pos : label_end + 1])
    return False


class IDs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.update(value for key, value in attrs if key == "id" and value is not None)


def anchors(parser, text):
    result = set()
    tokens = parser.parse(text)
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = "".join(
            child.content
            for child in tokens[index + 1].children or []
            if child.type in ("text", "code_inline")
        )
        base = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        slug = base
        suffix = 0
        while slug in result:
            suffix += 1
            slug = f"{base}-{suffix}"
        result.add(slug)
    html = IDs()
    for token in tokens:
        if token.type == "html_block":
            html.feed(token.content)
        for child in token.children or []:
            if child.type == "html_inline":
                html.feed(child.content)
    return result | html.ids


def check(root: Path, names=ENTRYPOINTS):
    root = root.resolve()
    parser = MarkdownIt()
    parser.inline.ruler.before("link", "observe_explicit_reference", observe_reference)
    errors = []
    checked = 0
    for name in names:
        source = root / name
        if not source.is_file():
            errors.append(f"{name}: missing entry point")
            continue
        env = {}
        tokens = parser.parse(source.read_text(encoding="utf-8"), env)
        errors.extend(f"{name}: unresolved explicit reference: {x}" for x in env.get("unresolved", []))
        for token in tokens:
            for child in token.children or []:
                if child.type not in ("link_open", "image"):
                    continue
                dest = child.attrGet("href" if child.type == "link_open" else "src") or ""
                link = urlsplit(dest)
                if link.scheme or link.netloc or link.path.startswith("/"):
                    continue
                target = (source.parent / unquote(link.path)).resolve() if link.path else source
                checked += 1
                if not target.is_relative_to(root) or not target.exists():
                    errors.append(f"{name}: {dest}: missing or out-of-repository target")
                    continue
                if link.fragment and target.is_file() and target.suffix.lower() == ".md":
                    if unquote(link.fragment) not in anchors(parser, target.read_text(encoding="utf-8")):
                        errors.append(f"{name}: {dest}: missing or unsupported fragment")
    return checked, errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/check_docs_links.py REPOSITORY_ROOT")
    count, problems = check(Path(sys.argv[1]))
    print(f"{count} local links checked; {len(problems)} errors")
    if problems:
        print("\n".join(problems))
    raise SystemExit(bool(problems))
