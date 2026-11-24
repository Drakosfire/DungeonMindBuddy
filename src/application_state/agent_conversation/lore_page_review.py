"""Versioned destinations for inert standalone lore-page reviews."""

import re
from typing import Literal

from pydantic import Field, field_validator

from .collaboration import Closed


_PAGE_REQUEST = re.compile(
    r'(?:^|(?<=[.!?])\s+|(?<=[,;])\s+then\s+)(?P<request>(?:please\s+)?(?:create|open|make)\s+'
    r'(?:(?:a|the)\s+)?(?P<modifiers>(?:(?:new|blank|standalone|lore)\s+)*)page\s+'
    r'(?P<relation>for|about|called|named|titled)\s+'
    r"""(?P<subject>"[^"\r\n]+"|“[^”\r\n]+”|'[^'\r\n]+'|[^,.!?;\r\n]+))""",
    re.IGNORECASE,
)


_NAMED_PAGE_REQUEST = re.compile(
    r'(?:^|(?<=[.!?])\s+|(?<=[,;])\s+then\s+)(?P<request>(?:please\s+)?(?:create|open|make)\s+'
    r'(?:(?:a|the)\s+)?(?P<modifiers>(?:(?:new|blank|standalone|lore)\s+)*)'
    r"""(?P<relation>)(?P<subject>"[^"\r\n]+"|“[^”\r\n]+”|'[^'\r\n]+'|[^,.!?;\r\n]+?)\s+page\b)""",
    re.IGNORECASE,
)


def _requested_title(subject: str, *, conversational: bool = False) -> str:
    subject = subject.strip()
    if (subject[0], subject[-1]) in {('"', '"'), ('“', '”'), ("'", "'")}:
        return subject[1:-1].strip()
    if re.search(r"\b(?:and|or)\b", subject, re.IGNORECASE):
        raise ValueError("Lore page request has a compound destination. Quote one intended title.")
    # A request may describe the subject before giving its explicit name.
    title = re.split(r'\bthat is\b', subject, flags=re.IGNORECASE)[-1].strip()
    if conversational:
        title = re.sub(r'\s+now$', '', title, flags=re.IGNORECASE)
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

    def bind(self, author_text: str, *, has_body: bool = False, conversational: bool = False) -> str:
        """Check the literal witness against the producing author turn."""
        if self.instruction != self.instruction.strip() or self.title != self.title.strip():
            raise ValueError("Lore page witness has surrounding whitespace")
        if not self.title or not self.instruction or author_text.count(self.instruction) != 1:
            raise ValueError("Lore page instruction must occur once in the author turn")
        request, title = _explicit_request(author_text, conversational=conversational)
        if not self.instruction.startswith(request["request"].rstrip()):
            raise ValueError("Lore page witness must quote the explicit page request")
        if self.title != title:
            raise ValueError("Lore page title differs from the explicit page request")
        if has_body and _requests_blank_page(request):
            raise ValueError("Blank lore-page request cannot carry a populated body")
        return self.title


def _explicit_request(author_text: str, *, conversational: bool = False) -> tuple[re.Match[str], str]:
    requests = list(_PAGE_REQUEST.finditer(author_text))
    # Extend only previously unrecognized requests. Historical witnesses must
    # still bind under their original grammar, even in mixed imperative prose.
    if not requests:
        for candidate in _NAMED_PAGE_REQUEST.finditer(author_text):
            subject = candidate['subject'].strip()
            if subject.casefold() in {'new', 'blank', 'standalone', 'lore', 'this', 'that', 'current', 'existing'}:
                continue
            requests.append(candidate)
    if len(requests) != 1:
        raise ValueError("Lore page requires one explicit page request")
    request = requests[0]
    subject = request["subject"].strip()
    named_before_page = request.re is _NAMED_PAGE_REQUEST
    if named_before_page and re.match(
            r'\s*(?:[,—:-]\s*)?(?:(?:called|named|titled)\b|with\s+(?:(?:a|the)\s+)?(?:name|title)\b)',
            author_text[request.end():], re.IGNORECASE):
        raise ValueError("Lore page request has multiple naming clauses. Quote one intended title.")
    if named_before_page or subject.startswith(('"', "“", "'")):
        if re.match(r"\s+(?:and|or)\s+(?!(?:populate|fill|leave|keep)\b)",
                    author_text[request.end():], re.IGNORECASE):
            raise ValueError("Lore page request has a compound destination. Quote one intended title.")
    else:
        subject = re.split(
            r"\s+and\s+(?:populate|fill|leave|keep)\b", subject,
            maxsplit=1, flags=re.IGNORECASE,
        )[0]
    has_timing = conversational and request["relation"].lower() in {"for", "about"}
    return request, _requested_title(subject, conversational=has_timing)


def _requests_blank_page(request: re.Match[str]) -> bool:
    return "blank" in request["modifiers"].lower().split()


def explicit_blank_lore_page(author_text: str) -> bool:
    request, _ = _explicit_request(author_text)
    return _requests_blank_page(request)


def explicit_lore_page_witness(author_text: str, *, conversational: bool = False) -> LorePageTitleWitness:
    """Derive the review destination from the author's literal instruction."""
    request, title = _explicit_request(author_text, conversational=conversational)
    witness = LorePageTitleWitness(instruction=request["request"].rstrip(), title=title)
    witness.bind(author_text, conversational=conversational)
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


LORE_REQUEST_FORMAT = "surface_native_lore_request_reference_v2"


class LorePageRequestReference(Closed):
    """Local selection of the producing request; title remains a reviewed proposal."""
    request: Literal["current_author_request"]
    title: str = Field(min_length=1, max_length=200, pattern=r"^[^\n\r]+$",
        description="Propose the requested page title, preserving articles, punctuation and Unicode. The author reviews this exact title before saving.")

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title_formatting(cls, value):
        return value.strip() if isinstance(value, str) else value

    def bind(self, author_text: str, *, has_body=False, conversational=False) -> str:
        # Identity is proved by exact producing input/schema reconstruction, not
        # by copying an instruction or parsing natural language a second time.
        if not author_text.strip() or self.title != self.title.strip():
            raise ValueError("Lore page reference requires a current request and nonblank proposed title")
        return self.title


class ProposedLorePageReference(ProposedLorePage):
    """Review a standalone page using sourced claims or explicitly labeled proposals.
    For an ordinary acknowledgment or clarification, leave collaboration null and
    use discussion segments. An acknowledgment is not an invented idea or page body.
    """
    destination: LorePageRequestReference
    open_questions: tuple[str, ...] = Field(default=(), max_length=24,
        exclude_if=lambda value: not value,
        description="Preserve all author-declared unresolved issues, including identities, motives, relationships, chronology and origins. Put questions here instead of duplicating them in the body. Whitespace is normalized for review.")

    @field_validator("open_questions", mode="before")
    @classmethod
    def normalize_question_formatting(cls, value):
        if not isinstance(value, (tuple, list)):
            return value
        return tuple(" ".join(question.split()) if isinstance(question, str) else question
                     for question in value)
