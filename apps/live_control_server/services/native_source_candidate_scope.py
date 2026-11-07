"""Reversible lexical source hints; Core membership and evidence stay unchanged."""
import re


def _campaign_number(value):
    # Lexical ID suffix only, not a canonical campaign ordinal or identity alias.
    match = re.fullmatch(r"(?:.*[-_])?c(\d+)", value.casefold())
    return int(match[1]) if match else None


def preferred_source_pairs(question, displays):
    """Return a hinted view, or None when no admitted source positively matches.

    Unknown/stale labels remain visible. Names only add sources to an explicit
    campaign/session view; an entity name alone never excludes recap material.
    """
    query = question.casefold()
    # These require semantic exclusion reasoning; this positive-hint view does
    # not guess its inverse. Keep the broad catalog for the controller instead.
    if re.search(r"\b(?:not|except|exclude|excluding|outside|without)\b|\bother than\b", query):
        return None
    hints = {(int(c), int(s)) for c, s in re.findall(r"\bc(\d+)\s*s(\d+)\b", query)}
    hints.update((int(c), None) for c in re.findall(r"\bcampaign\s+(\d+)\b", query))
    sessions = {int(s) for s in re.findall(r"\bsession\s+(\d+)\b", query)}
    ids = {d['campaign_id'].casefold() for d in displays.values()
        if isinstance(d.get('campaign_id'), str) and d['campaign_id'] and
        re.search(r"(?<!\w)" + re.escape(d['campaign_id'].casefold()) + r"(?!\w)", query)}
    if not hints and not sessions and not ids:
        return None
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
