"""Reversible lexical source hints; Core membership and evidence stay unchanged."""
import re

_SESSION_REFERENCE = r'(?:sessions?\s*\d+|c\d+\s*s\d+)'
_TEMPORAL_SESSION = re.compile(
    rf'\b(?:before|after|by|through|until|since|as\s+of)\s+'
    rf'(?:(?:the\s+)?(?:end|start|beginning)\s+of\s+)?{_SESSION_REFERENCE}\b'
    rf'|\bat\s+(?:the\s+)?(?:end|start|beginning)\s+of\s+{_SESSION_REFERENCE}\b'
    rf'|\bbetween\s+{_SESSION_REFERENCE}\s+and\s+(?:{_SESSION_REFERENCE}|\d+)\b'
    rf'|\b{_SESSION_REFERENCE}\s*(?:[-–—]|to\b|through\b|until\b)\s*(?:{_SESSION_REFERENCE}|\d+)\b'
)


def _campaign_number(value):
    # Lexical ID suffix only, not a canonical campaign ordinal or identity alias.
    match = re.fullmatch(r"(?:.*[-_])?c(\d+)", value.casefold())
    return int(match[1]) if match else None


def preferred_source_pairs(question, displays, *, opened_reference_pairs=()):
    """Return a hinted view, or None when no admitted source positively matches.

    Unknown/stale labels remain visible. Names only add sources to an explicit
    campaign/session view; an entity name alone never excludes recap material.
    """
    query = question.casefold()
    # These require semantic exclusion reasoning; this positive-hint view does
    # not guess its inverse. Keep the broad catalog for the controller instead.
    scope_query = query
    if opened_reference_pairs:
        # A terminal non-writing directive is not a source exclusion. Keep
        # other negation conservative, including any earlier scope clause.
        scope_query = re.sub(r"(?:^|(?<=[.!?])\s+)(?:discuss only;\s*)?(?:do not|don['’]t)\s+(?:edit|save|publish)"
            r"(?:\s*(?:,|\bor\b|\band\b)\s*(?:edit|save|publish))*[.!]?\s*$", "", query)
    if re.search(r"\b(?:no|not|never|cannot|except|exclude|excluding|outside|without)\b|\bother than\b|\b\w+n['’]t\b", scope_query):
        return None
    hints = {(int(c), int(s)) for c, s in re.findall(r"\bc(\d+)\s*s(\d+)\b", query)}
    campaigns = {(int(c), None) for c in re.findall(r"\bcampaign\s+(\d+)\b", query)}
    hints.update(campaigns)
    sessions = {int(s) for s in re.findall(r"\bsession\s*(\d+)\b", query)}
    ids = {d['campaign_id'].casefold() for d in displays.values()
        if isinstance(d.get('campaign_id'), str) and d['campaign_id'] and
        re.search(r"(?<!\w)" + re.escape(d['campaign_id'].casefold()) + r"(?!\w)", query)}
    if _TEMPORAL_SESSION.search(query):
        # A cutoff/range is not a request for only its endpoint document. Keep
        # independently stated campaign scope, but never hide another compact
        # campaign reference or invent its relation to an opaque campaign ID.
        compact_campaigns = {c for c, session in hints if session is not None}
        id_numbers = {_campaign_number(identity) for identity in ids}
        allowed = {c for c, _ in campaigns} | (id_numbers - {None})
        if compact_campaigns and (None in id_numbers or not compact_campaigns <= allowed):
            return None
        hints, sessions = campaigns, set()
        if not hints and not ids:
            return None  # Do not re-narrow through opened references or labels.
    if not hints and not sessions and not ids:
        # Successful human reads are an initial navigation hint, not a source
        # restriction. Unknown/stale labels and explicitly named alternatives
        # must not disappear behind that hint.
        references = set(opened_reference_pairs)
        if not references:
            return None
        known = {pair for pair, display in displays.items()
            if display.get('status') == 'available'
            and display.get('origin_matches_current_metadata') is True}
        selected = references & known
        named_other = any(pair not in references and isinstance(display.get('label'), str)
            and display['label'].strip() and re.search(r"(?<!\w)" + re.escape(display['label'].casefold()) + r"(?!\w)", query)
            for pair, display in displays.items())
        return frozenset(selected | (set(displays) - known)) if selected and not named_other else None
    kept, matched = set(), False
    for pair, display in displays.items():
        if (display.get('status') != 'available' or
                display.get('origin_matches_current_metadata') is not True or
                display.get('kind') != 'recap'):
            kept.add(pair)
            continue
        campaign = display.get('campaign_id')
        session = display.get('session_id')
        number = _campaign_number(campaign) if isinstance(campaign, str) else None
        session_match = re.fullmatch(r"(?:session[-_ ]?)?(\d+)", session.casefold()) if isinstance(session, str) else None
        session_number = int(session_match[1]) if session_match else None
        positive = (isinstance(campaign, str) and campaign.casefold() in ids or
            any(number == c and (s is None or session_number == s) for c, s in hints) or
            session_number in sessions)
        unknown = (bool(hints) and number is None or
            bool(sessions or any(s is not None and number == c for c, s in hints)) and session_number is None)
        name = display.get('label')
        named = isinstance(name, str) and bool(name.strip()) and re.search(
            r"(?<!\w)" + re.escape(name.casefold()) + r"(?!\w)", query)
        if positive or unknown or named:
            kept.add(pair)
        matched = matched or bool(positive)
    return frozenset(kept) if matched else None
