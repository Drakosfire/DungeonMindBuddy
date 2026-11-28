"""Actions available to surface-specific opening intent decisions."""

from types import MappingProxyType


_PLAN_DESCRIPTIONS = MappingProxyType({
    'discuss': 'Answer, explain, critique or discuss in conversation without a requested page edit.',
    'clarify': 'The intended work or content needs an author decision. Missing or ambiguous placement alone is not this intent.',
    'write_current_page': 'Draft, revise or place usable writing on this Plan, even when its destination is missing or ambiguous.',
    'different_destination': 'Edit another existing page/object or create an unsupported object, rather than writing this Plan.',
    'review_connected_page': 'Create a new connected location page through its existing review; further requested edits remain deferred.',
})


def plan_action_menu(operation=None):
    """Return Plan intent choices in stable wire order for the author operation."""
    if operation == "discuss":
        options = ("discuss", "clarify")
    elif operation is None:
        options = _PLAN_DESCRIPTIONS
    else:
        options = ("clarify", "write_current_page", "different_destination")
    return {name: _PLAN_DESCRIPTIONS[name] for name in options}


def opening_action_menu(surface, *, plan_operation=None):
    """Project the offered intent labels and definitions from the owning contract."""
    if surface == "build":
        from .build_intentional_response import question

        return question()["criteria"]
    if surface == "plan":
        return plan_action_menu(plan_operation)
    raise ValueError(f"No opening action catalog registered for {surface!r}")
