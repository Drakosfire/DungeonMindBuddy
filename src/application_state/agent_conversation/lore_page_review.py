"""User text witness for an inert standalone lore-page review."""

import re
from typing import Literal

from pydantic import Field, field_validator

from .collaboration import Closed


_PAGE_REQUEST = re.compile(
    r'(?:^|(?<=[.!?])\s+|(?<=[,;])\s+then\s+)(?P<request>(?:please\s+)?(?:create|open|make)\s+'
    r'(?:a\s+)?(?P<modifiers>(?:(?:new|blank|standalone|lore)\s+)*)page\s+'
    r'(?:for|about|called|named|titled)\s+'
    r"""(?P<subject>"[^"\r\n]+"|“[^”\r\n]+”|'[^'\r\n]+'|[^,.!?;\r\n]+))""",
    re.IGNORECASE,
)


def _requested_title(subject: str) -> str:
    subject = subject.strip()
    if (subject[0], subject[-1]) in {('"', '"'), ('“', '”'), ("'", "'")}:
        return subject[1:-1].strip()
    if re.search(r"\b(?:and|or)\b", subject, re.IGNORECASE):
        raise ValueError("Lore page request has a compound destination. Quote one intended title.")
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

    def bind(self, author_text: str, *, has_body: bool = False) -> str:
        """Check the literal witness against the producing author turn."""
        if self.instruction != self.instruction.strip() or self.title != self.title.strip():
            raise ValueError("Lore page witness has surrounding whitespace")
        if not self.title or not self.instruction or author_text.count(self.instruction) != 1:
            raise ValueError("Lore page instruction must occur once in the author turn")
        request, title = _explicit_request(author_text)
        if not self.instruction.startswith(request["request"].rstrip()):
            raise ValueError("Lore page witness must quote the explicit page request")
        if self.title != title:
            raise ValueError("Lore page title differs from the explicit page request")
        if has_body and _requests_blank_page(request):
            raise ValueError("Blank lore-page request cannot carry a populated body")
        return self.title


def _explicit_request(author_text: str) -> tuple[re.Match[str], str]:
    requests = list(_PAGE_REQUEST.finditer(author_text))
    if len(requests) != 1:
        raise ValueError("Lore page requires one explicit page request")
    request = requests[0]
    subject = request["subject"].strip()
    if subject.startswith(('"', "“", "'")):
        if re.match(r"\s+(?:and|or)\s+(?!(?:populate|fill|leave|keep)\b)",
                    author_text[request.end():], re.IGNORECASE):
            raise ValueError("Lore page request has a compound destination. Quote one intended title.")
    else:
        subject = re.split(
            r"\s+and\s+(?:populate|fill|leave|keep)\b", subject,
            maxsplit=1, flags=re.IGNORECASE,
        )[0]
    return request, _requested_title(subject)


def _requests_blank_page(request: re.Match[str]) -> bool:
    return "blank" in request["modifiers"].lower().split()


def explicit_blank_lore_page(author_text: str) -> bool:
    request, _ = _explicit_request(author_text)
    return _requests_blank_page(request)


def explicit_lore_page_witness(author_text: str) -> LorePageTitleWitness:
    """Derive the review destination from the author's literal instruction."""
    request, title = _explicit_request(author_text)
    witness = LorePageTitleWitness(instruction=request["request"].rstrip(), title=title)
    witness.bind(author_text)
    return witness


class ProposedLorePage(Closed):
    """Review an author-requested standalone page in conversation. Use no answer segments
    for a blank page. For a populated page, put its body in source passage claims and
    use invented-idea segments only for material explicitly presented as proposed."""
    kind: Literal["lore_page"]
    destination: LorePageTitleWitness

    open_questions: tuple[str, ...] = Field(default=(), max_length=24,
        exclude_if=lambda value: not value)

    @field_validator("open_questions")
    @classmethod
    def meaningful_questions(cls, value):
        if any(not question.strip() or len(question) > 1000 or "\n" in question or "\r" in question
               for question in value):
            raise ValueError("Open questions require concise nonblank text")
        return value
