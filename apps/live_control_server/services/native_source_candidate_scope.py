"""Reversible lexical source hints; Core membership and evidence stay unchanged."""
import re

from application_state.agent_conversation.corpus_source_search import session_cutoff


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
    hints.update((int(c), None) for c in re.findall(r"\bcampaign\s+(\d+)\b", query))
    sessions = {int(s) for s in re.findall(r"\bsession\s*(\d+)\b", query)}
    ids = {d['campaign_id'].casefold() for d in displays.values()
        if isinstance(d.get('campaign_id'), str) and d['campaign_id'] and
        re.search(r"(?<!\w)" + re.escape(d['campaign_id'].casefold()) + r"(?!\w)", query)}
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


def post_cutoff_source_pairs(question, displays):
    """Identify registered recap sessions later than an explicit cutoff."""
    cutoff = session_cutoff(question)
    if cutoff is None:
        return set()
    end = int(cutoff[1])
    excluded = set()
    for pair, display in displays.items():
        if (display.get("kind") != "recap" or display.get("status") != "available"
                or display.get("origin_matches_current_metadata") is not True):
            continue
        session = re.fullmatch(r"session-(\d+)", display.get("session_id") or "")
        if session is not None and int(session[1]) > end:
            excluded.add(pair)
    return excluded


def post_named_recap_source_pairs(bound, displays):
    """Limit only verified later recaps in the Event support's campaign."""
    if bound is None:
        return set()
    anchor = displays.get((bound.source_artifact_id, bound.source_revision_id), {})
    campaign = anchor.get("campaign_id")
    endpoint = re.fullmatch(r"session-(\d+)", anchor.get("session_id") or "")
    if (not campaign or endpoint is None or anchor.get("kind") != "recap"
            or anchor.get("status") != "available"
            or anchor.get("origin_matches_current_metadata") is not True):
        return set()
    excluded = set()
    for pair, metadata in displays.items():
        if (metadata.get("campaign_id") != campaign or metadata.get("kind") != "recap"
                or metadata.get("status") != "available"
                or metadata.get("origin_matches_current_metadata") is not True):
            continue
        session = re.fullmatch(r"session-(\d+)", metadata.get("session_id") or "")
        if session is not None and int(session[1]) > int(endpoint[1]):
            excluded.add(pair)
    return excluded


def as_of_passage_handles(question, hits, addresses, displays):
    """Suggest a recent campaign window when the named cutoff is supported."""
    from collections import defaultdict
    from application_state.agent_conversation.corpus_source_search import terms

    cutoff = session_cutoff(question)
    if cutoff is None:
        return set()
    end = int(cutoff[1])
    topic = {word for word in terms(question[:cutoff.start()] + " " + question[cutoff.end():])
             if len(word) >= 4}
    campaigns = defaultdict(lambda: defaultdict(set))
    matched_handles = defaultdict(list)
    for handle, words in hits.items():
        display = displays.get(addresses.get(handle), {})
        if (display.get("kind") != "recap" or display.get("status") != "available"
                or display.get("origin_matches_current_metadata") is not True):
            continue
        session = re.fullmatch(r"session-(\d+)", display.get("session_id") or "")
        campaign = display.get("campaign_id")
        matched = topic & words
        if session is None or not campaign or not matched:
            continue
        number = int(session[1])
        if end - 2 <= number <= end:
            campaigns[campaign][number].update(matched)
            matched_handles[campaign].append((handle, matched))
    continuity = {
        campaign: sessions[end] & sessions[end - 1] & sessions[end - 2]
        for campaign, sessions in campaigns.items()
    }
    supported = [campaign for campaign, shared in continuity.items() if shared]
    if len(supported) != 1:
        return set()
    campaign = supported[0]
    return {handle for handle, matched in matched_handles[campaign] if matched & continuity[campaign]}


def rare_named_section_handles(question, hits):
    """Preserve a bounded set of exact mentions of an explicit written name."""
    words = re.findall(r"\b[^\W\d_]+\b", question)
    names = {word.casefold() for word in words[1:] if len(word) >= 4 and word.istitle()}
    sections = {
        name: {handle for handle, matched in hits.items() if name in matched}
        for name in names
    }
    rare = set().union(*(handles for handles in sections.values() if 1 <= len(handles) <= 3))
    return rare if len(rare) <= 3 else set()


def chronological_passage_handles(question, hits, addresses, displays):
    """Offer evidence between matched endpoints for explicit from/to questions."""
    from collections import Counter, defaultdict

    match = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)", question.casefold())
    if match is None:
        return set()
    route = bool(re.search(r"\b(?:route|path|journey)\b", question[:match.start()], re.I))
    if not route and "," not in match[2]:
        return set()
    tokens = lambda text: {term for term in re.findall(r"[^\W\d_]+", text) if len(term) >= 4}
    subject = tokens(question.casefold()[:match.start()])
    origin = tokens(match[1])
    destination = tokens(match[2]) - origin
    frequency = Counter(term for terms in hits.values() for term in terms)
    by_campaign = defaultdict(list)
    for handle, terms in hits.items():
        display = displays.get(addresses.get(handle), {})
        if (display.get('kind') != 'recap' or display.get('status') != 'available'
                or display.get('origin_matches_current_metadata') is not True):
            continue
        campaign, session = display.get('campaign_id'), display.get('session_id')
        position = re.fullmatch(r"session-(\d+)", session or "")
        if campaign and position:
            by_campaign[campaign].append((int(position[1]), handle, terms))
    if route:
        windows = []
        for rows in by_campaign.values():
            for start, first, first_terms in rows:
                early = first_terms & origin
                if not early:
                    continue
                for end, last, last_terms in rows:
                    late = last_terms & destination
                    if not 1 <= end - start <= 3 or len(late) < 2:
                        continue
                    rank = (
                        sum(1 / frequency[term] for term in sorted(early)),
                        len(late),
                        sum(1 / frequency[term] for term in sorted(late)),
                    )
                    interior = {handle for session, handle, _ in rows if start < session < end}
                    windows.append((rank, frozenset({first, last} | interior)))
        if not windows:
            return set()
        best = max(rank for rank, _ in windows)
        choices = {handles for rank, handles in windows if rank == best}
        return set(next(iter(choices))) if len(choices) == 1 else set()

    windows = []
    for rows in by_campaign.values():
        starts = [session for session, _, terms in rows if terms & subject and terms & origin]
        if not starts:
            continue
        start = min(starts)
        for end, _, terms in rows:
            late = terms & destination
            if end <= start or not late or not terms & subject:
                continue
            rank = (len(late), sum(1 / frequency[term] for term in sorted(late)))
            windows.append((rank, start, end, rows))
    if not windows:
        return set()
    best = max(rank for rank, *_ in windows)
    included = set()
    for rank, start, end, rows in windows:
        if rank != best:
            continue
        per_session = defaultdict(list)
        for session, handle, terms in rows:
            if start <= session <= end:
                per_session[session].append((len(terms), handle))
        for passages in per_session.values():
            strongest = max(score for score, _ in passages)
            included.update(handle for score, handle in passages if score == strongest)
    return included


def preceding_recap_passage_handles(question, anchors, hits, addresses, displays):
    """Offer nearby matching recap sections for questions spanning several days."""
    if not re.search(
        r"\b(?:over|across|during)\s+(?:the\s+)?"
        r"(?:several|multiple|two|three|four|five|six|seven|[2-9]|[1-9]\d+)\s+days\b",
        question, re.I,
    ):
        return set()
    positions = {}
    for handle in hits:
        display = displays.get(addresses.get(handle), {})
        if (display.get("kind") != "recap" or display.get("status") != "available"
                or display.get("origin_matches_current_metadata") is not True):
            continue
        campaign = display.get("campaign_id")
        session = re.fullmatch(r"session-(\d+)", display.get("session_id") or "")
        if campaign and session:
            positions[handle] = (campaign, int(session[1]))
    selected = {positions[handle] for handle in anchors if handle in positions}
    wanted = {(campaign, session - offset) for campaign, session in selected for offset in (1, 2)}
    best = {}
    for handle, position in positions.items():
        if position not in wanted or position in selected:
            continue
        score = len(hits[handle])
        if position not in best or score > best[position][0]:
            best[position] = (score, {handle})
        elif score == best[position][0]:
            best[position][1].add(handle)
    return {next(iter(handles)) for _, handles in best.values() if len(handles) == 1}
