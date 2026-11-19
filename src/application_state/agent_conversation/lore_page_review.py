"""User text witness for an inert standalone lore-page review."""

import re
from typing import Literal

from pydantic import Field

from .collaboration import Closed


_PAGE_REQUEST = re.compile(
    r'(?:^|(?<=[.!?])\s+)(?P<request>(?:create|open|make)\s+'
    r'(?:a\s+)?(?:(?:new|blank|standalone|lore)\s+)*page\s+'
    r'(?:for|about|called|named|titled)\s+'
    r'(?P<subject>"[^"\r\n]+"|“[^”\r\n]+”|[^,.!?;\r\n]+))',
    re.IGNORECASE,
)


def _requested_title(subject: str) -> str:
    subject = subject.strip()
    if (subject[0], subject[-1]) in {('"', '"'), ('“', '”')}:
        return subject[1:-1].strip()
    # A request may describe the subject before giving its explicit name.
    title = re.split(r'\bthat is\b', subject, flags=re.IGNORECASE)[-1].strip()
    return re.sub(r'^the\s+', '', title, flags=re.IGNORECASE)


class LorePageTitleWitness(Closed):
    instruction: str = Field(
        min_length=1,
        max_length=2000,
        description="Quote the exact author instruction requesting this page.",
    )
    title: str = Field(
        min_length=1,
        max_length=200,
        pattern=r"^[^\n\r]+$",
        description="Quote the requested page title from that instruction.",
    )

    def bind(self, author_text: str) -> str:
        """Check the literal witness against the producing author turn."""
        if self.instruction != self.instruction.strip() or self.title != self.title.strip():
            raise ValueError("Lore page witness has surrounding whitespace")
        if not self.title or not self.instruction or author_text.count(self.instruction) != 1:
            raise ValueError("Lore page instruction must occur once in the author turn")
        requests = list(_PAGE_REQUEST.finditer(author_text))
        if len(requests) != 1:
            raise ValueError("Lore page requires one explicit page request")
        request = requests[0]
        if not self.instruction.startswith(request["request"].rstrip()):
            raise ValueError("Lore page witness must quote the explicit page request")
        subject = re.split(r'\s+and\s+(?:populate|fill|leave|keep)\b', request["subject"],
                           maxsplit=1, flags=re.IGNORECASE)[0]
        if not subject.strip() or self.title != _requested_title(subject):
            raise ValueError("Lore page title differs from the explicit page request")
        return self.title


class ProposedLorePage(Closed):
    """Review an author-requested standalone page in conversation. Use no answer segments
    for a blank page. For a populated page, put its body in source passage claims and
    use invented-idea segments only for material explicitly presented as proposed."""
    kind: Literal["lore_page"]
    destination: LorePageTitleWitness
