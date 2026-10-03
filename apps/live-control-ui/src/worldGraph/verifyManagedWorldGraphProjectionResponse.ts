import type {
  ManagedWorldGraphProjectionResponse,
  WorldGraphProjectionRequest,
} from "../api/types";
import { verifyWorldGraphProjectionResponse } from "./verifyWorldGraphProjectionResponse";

/** Verify Buddy owner provenance before applying the native projection checks. */
export function verifyManagedWorldGraphProjectionResponse(input: {
  managedWorldId: string;
  request: WorldGraphProjectionRequest;
  response: ManagedWorldGraphProjectionResponse;
  revisionKind: "head" | "pinned";
  pinnedRevisionId?: string | null;
}): string | null {
  const { managedWorldId, request, response, revisionKind, pinnedRevisionId } = input;
  if (request.worldId !== managedWorldId) {
    return `Projection request owner ${request.worldId} does not match selected World ${managedWorldId}.`;
  }
  if (response.schema !== "dmb_managed_world_graph_projection_v1") {
    return "Managed World projection has an unsupported envelope schema.";
  }
  if (response.managedWorldId !== managedWorldId) {
    return `Projection owner ${response.managedWorldId} does not match selected World ${managedWorldId}.`;
  }
  if (!response.nativeWorldId.trim() || !Number.isSafeInteger(response.bindingVersion) || response.bindingVersion <= 0) {
    return "Managed World projection is missing valid native binding provenance.";
  }
  if (response.projection.schema !== "dmb_world_graph_projection_v1") {
    return "Managed World projection contains an unsupported native projection schema.";
  }
  if (response.projection.snapshot.worldId !== response.nativeWorldId) {
    return `Native projection world ${response.projection.snapshot.worldId} does not match envelope world ${response.nativeWorldId}.`;
  }

  return verifyWorldGraphProjectionResponse({
    request: { ...request, worldId: response.nativeWorldId },
    response: response.projection,
    revisionKind,
    pinnedRevisionId,
  });
}
