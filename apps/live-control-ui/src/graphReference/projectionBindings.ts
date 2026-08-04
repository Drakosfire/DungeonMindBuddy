import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "./types";

export const GRAPH_REFERENCE_RESOLUTION_BINDING_ID = "graph-reference-resolution" as const;
export const GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID = "graph-reference-projection-state" as const;
export const GRAPH_REFERENCE_BINDING_ID = "graph-reference-binding" as const;

function assertBindingPresent<T>(
  bindings: Readonly<Record<string, unknown>>,
  bindingId: string,
): T {
  if (!Object.prototype.hasOwnProperty.call(bindings, bindingId)) {
    throw new Error(`Missing required projection binding: ${bindingId}`);
  }
  const value = bindings[bindingId];
  if (value === null || value === undefined) {
    throw new Error(`Required projection binding is null: ${bindingId}`);
  }
  return value as T;
}

export function readGraphReferenceResolutionBinding(
  bindings: Readonly<Record<string, unknown>>,
): GraphReferenceResolution {
  return assertBindingPresent<GraphReferenceResolution>(bindings, GRAPH_REFERENCE_RESOLUTION_BINDING_ID);
}

export function readGraphReferenceProjectionStateBinding(
  bindings: Readonly<Record<string, unknown>>,
): GraphReferenceProjectionState | null | undefined {
  if (!Object.prototype.hasOwnProperty.call(bindings, GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID)) {
    return undefined;
  }
  return bindings[GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID] as GraphReferenceProjectionState | null | undefined;
}

export function readGraphReferenceBinding(
  bindings: Readonly<Record<string, unknown>>,
): GraphReferenceProjectionBinding | null | undefined {
  if (!Object.prototype.hasOwnProperty.call(bindings, GRAPH_REFERENCE_BINDING_ID)) {
    return undefined;
  }
  return bindings[GRAPH_REFERENCE_BINDING_ID] as GraphReferenceProjectionBinding | null | undefined;
}
