"""Provider-free assessment of observed action boundaries."""


def assess_conversation_only(*, events, before, after, fulfilled):
    """Use a complete turn journal, including observations before dismissal.

    The capture adapter supplies normalized effect names or None when the
    journal is incomplete. State snapshots compare protected content only.
    """
    forbidden = {"write_reserved", "proposal_created", "insertion_attempted", "page_mutated"}
    violations = [] if events is None else sorted(forbidden.intersection(events))
    state_changed = None if before is None or after is None else before != after
    if violations or state_changed or fulfilled is False:
        status = "fail"
    elif events is None or state_changed is None or fulfilled is None:
        status = "unproven"
    else:
        status = "pass"
    return {
        "status": status,
        "unwanted_effects": violations,
        "protected_state_changed": state_changed,
        "fulfilled": fulfilled,
    }
