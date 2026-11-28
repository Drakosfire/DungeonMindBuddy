"""Actions available to surface-specific opening intent decisions."""

from types import MappingProxyType


# Preserve the distinct owning wire labels for equivalent conversational actions.
UNIVERSAL_OPENING_ACTIONS = MappingProxyType({
    'discuss': MappingProxyType({'build': 'discuss', 'plan': 'discuss', 'play': 'discuss'}),
    'clarify_request': MappingProxyType({'build': 'clarify_request', 'plan': 'clarify', 'play': 'clarify_request'}),
})


_PLAN_DESCRIPTIONS = MappingProxyType({
    UNIVERSAL_OPENING_ACTIONS['discuss']['plan']: 'Answer, explain, critique or discuss in conversation without a requested page edit.',
    UNIVERSAL_OPENING_ACTIONS['clarify_request']['plan']: 'The intended work or content needs an author decision. Missing or ambiguous placement alone is not this intent.',
    'write_current_page': 'Draft, revise or place usable writing on this Plan, even when its destination is missing or ambiguous.',
    'different_destination': 'Edit another existing page/object or create an unsupported object, rather than writing this Plan.',
    'review_connected_page': 'Create a new connected location page through its existing review; further requested edits remain deferred.',
})


_PLAY_DESCRIPTIONS = MappingProxyType({
    UNIVERSAL_OPENING_ACTIONS["discuss"]["play"]: "Discuss, explain, or brainstorm using the supplied conversation.",
    UNIVERSAL_OPENING_ACTIONS["clarify_request"]["play"]: "Ask what the user wants when the action or referent remains unclear.",
    "read_source": "Consult Rules or saved sources for facts the user needs.",
    "play_edit": "Prepare a reviewable change to the current session scene.",
    "different_destination": "The request belongs to another surface or to an explicit operator control.",
})


def plan_work_options(operation, *, write_choices=None, connected_page=True):
    """Project both current and retained authoring menus in their original order."""
    discuss = UNIVERSAL_OPENING_ACTIONS["discuss"]["plan"]
    clarify = UNIVERSAL_OPENING_ACTIONS["clarify_request"]["plan"]
    if operation == "discuss":
        return discuss, clarify
    if write_choices is None:
        local = ("write_current_page", "different_destination")
    else:
        local = ("different_destination", *write_choices)
    if operation == "write_current_page":
        return (clarify, *local)
    if connected_page and operation is None:
        return (discuss, clarify, *local, "review_connected_page")
    return (discuss, clarify, *local)


def opening_action_menu(surface, *, plan_operation=None):
    """Project the offered intent labels and definitions from the owning contract."""
    if surface == "build":
        from .build_intentional_response import SCOPED_BUILD_MENU_DIGEST, _menu_work, question

        return question(work_options=_menu_work(SCOPED_BUILD_MENU_DIGEST))["criteria"]
    if surface == "plan":
        return {name: _PLAN_DESCRIPTIONS[name] for name in plan_work_options(plan_operation)}
    if surface == "play":
        return dict(_PLAY_DESCRIPTIONS)
    raise ValueError(f"No opening action catalog registered for {surface!r}")


def validate_opening_action_wire(expected, raw: bytes) -> None:
    """Validate the provider envelope against the owning choice projection."""
    from .source_writer_output import strict_json

    actual = strict_json(raw.decode("utf-8"))
    questions = {
        q.name: {
            "type": "choice",
            "instructions": q.question,
            "criteria": {option: (q.option_descriptions or {}).get(option) for option in q.options},
        }
        for q in expected.questions
    }
    if actual != {"model": expected.model, "state": expected.state, "questions": questions}:
        raise ValueError("Opening action wire differs from its offered semantic choices")
