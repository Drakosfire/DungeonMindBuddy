"""Optional lexical navigation hints; no source access or evidence authority."""
from hashlib import sha256
import json

from .corpus_source_search import terms

KEYWORD_KIND = 'Optional literal content keyword hint; navigation metadata only, never a source read'
KEYWORD_PREFIX = 'native-corpus-keyword:'
KEYWORD_GUIDANCE = (
    'Select literal query tokens that describe existing material to find in source text. '
    'Exclude grammar, conversational framing, source/campaign/session/time routing and creative '
    'instructions for what to invent next. Dialogue resolves references, never evidence. '
    'Preserve meaningful rare or misspelled topic words. Keywords prioritize the first section view '
    'only; no match does not establish absence. Full-source access and broad recovery remain '
    'available. Keyword votes alone do not select a retrieval action or prevent the fallback from ending retrieval.'
)


def keyword_catalog(question, scope_sha256):
    """Exact scope includes World, source revision, request and product attempt."""
    return {KEYWORD_PREFIX + sha256(json.dumps([scope_sha256, question, word],
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(): word
        for word in terms(question)}
