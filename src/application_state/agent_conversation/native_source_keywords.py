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


RETAINED_KEYWORD_KIND = 'Previously acknowledged literal content keyword; navigation focus only, not acquired evidence'
RECOVERY_KEYWORD_GUIDANCE = (
    'Carry selected_content_keywords into broad recovery. Broad expansion broadens source availability; '
    "it does not expand the user's topic. These literal choices are provisional navigation hints, "
    'not an exhaustive vocabulary, evidence, source restrictions or completeness. Prefer candidates '
    'that contribute a distinct requested detail beyond acquired subjects rather than incidental '
    'same-word mentions. Include differently worded evidence whenever a requested detail needs it.'
)


def acknowledged_keyword_catalog(turn):
    """Reuse admitted choices; do not require execution ownership for plain listings."""
    from .native_retrieval import NativeRetrievalSelectedV1, scope_digest
    handles = {handle for event in turn.graph_context_execution.events
        if type(event) is NativeRetrievalSelectedV1 and event.operation == 'select_candidates'
        for handle in event.selected_handles if handle.startswith(KEYWORD_PREFIX)}
    if not handles:
        return {}
    catalog = keyword_catalog(turn.user_text, scope_digest(turn))
    return {handle: word for handle, word in catalog.items() if handle in handles}


def retained_keyword_candidates(turn):
    from .jev_retrieval_contract import RetrievalCandidate
    return tuple(RetrievalCandidate(handle=handle, label=word, kind=RETAINED_KEYWORD_KIND)
        for handle, word in acknowledged_keyword_catalog(turn).items())
