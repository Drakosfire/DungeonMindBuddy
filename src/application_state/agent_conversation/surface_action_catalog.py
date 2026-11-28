"""Actions available to surface-specific opening intent decisions."""

from types import MappingProxyType


# Preserve the distinct owning wire labels for equivalent conversational actions.
UNIVERSAL_OPENING_ACTIONS = MappingProxyType({
    'discuss': MappingProxyType({'build': 'discuss', 'plan': 'discuss'}),
    'clarify_request': MappingProxyType({'build': 'clarify_request', 'plan': 'clarify'}),
})


_PLAN_DESCRIPTIONS = MappingProxyType({
    UNIVERSAL_OPENING_ACTIONS['discuss']['plan']: 'Answer, explain, critique or discuss in conversation without a requested page edit.',
    UNIVERSAL_OPENING_ACTIONS['clarify_request']['plan']: 'The intended work or content needs an author decision. Missing or ambiguous placement alone is not this intent.',
    'write_current_page': 'Draft, revise or place usable writing on this Plan, even when its destination is missing or ambiguous.',
    'different_destination': 'Edit another existing page/object or create an unsupported object, rather than writing this Plan.',
    'review_connected_page': 'Create a new connected location page through its existing review; further requested edits remain deferred.',
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
        from .build_intentional_response import opening_work_question, question

        definition = question()["criteria"]
        return {name: definition[name] for name in opening_work_question()["criteria"]}
    if surface == "plan":
        return {name: _PLAN_DESCRIPTIONS[name] for name in plan_work_options(plan_operation)}
    raise ValueError(f"No opening action catalog registered for {surface!r}")
