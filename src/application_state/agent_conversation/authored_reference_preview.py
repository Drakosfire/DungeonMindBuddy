"""Lightweight display of saved author input, never read or retry authority."""
from pydantic import TypeAdapter
from application_state.errors import ApplicationStateIntegrityError
from .authored_graph_references import AuthoredReferenceInput

# Use the same input-capture event as reference_input(), across real surfaces.
# Capture precedes provider dispatch/acquisition; it is not proof of a read.
# Only the existing bundle crosses this read port, never the full execution.
SELECT = """jsonb_path_query_array(t.graph_context_execution,
    '$.events[*] ? (@.kind == "build_authored_references_captured_v1").references')
    AS authored_reference_inputs"""

_INPUT = TypeAdapter(AuthoredReferenceInput)

def project(inputs, world):
    """Validate only display shape/scope through the existing selection owner."""
    if inputs is None or inputs == []:
        return None
    try:
        if not isinstance(inputs, list) or len(inputs) != 1:
            raise ValueError('Ambiguous saved reference input')
        selected = _INPUT.validate_python(inputs[0])
        selected.require_world(world)
        return selected.model_dump(mode='json', by_alias=True)
    except (ValueError, TypeError) as exc:
        raise ApplicationStateIntegrityError('Saved reference input cannot be displayed safely.') from exc
