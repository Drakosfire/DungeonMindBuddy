import { GRAPH_REFERENCE_RESOLUTION_BINDING_ID } from "../../graphReference/projectionBindings";
import type {
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
import { BUILD_SURFACE_LABEL } from "../buildSurfaceConfig";
import {
  BUILD_FIND_EXISTING_TOOL_ID,
  BUILD_REFERENCE_CONTEXT_BINDING_ID,
  BUILD_REFERENCE_SEARCH_PROJECTION_ID,
} from "./buildReferenceIds";
import type { BuildGraphLensResolution } from "./resolveBuildGraphLens";

const BUILD_SURFACE_ID = "build" as const;
const BUILD_WORLD_REFERENCE_GROUP_ID = "build-world-reference" as const;
const BUILD_WORLD_REFERENCE_GROUP_LABEL = "World references" as const;
const BUILD_WORLD_REFERENCE_GROUP_ORDER = 10;

const EMPTY_GRAPH_REFERENCE_RESOLUTION: GraphReferenceResolution = {
  kind: "unresolved",
  locator: "",
  reference: null,
  projectionState: null,
  message: "No object selected.",
};

export interface BuildReferenceContextBinding {
  schema: "dmb_build_reference_context_v1";
  documentId: string;
  documentCampaignId: string;
  lens: BuildGraphLensResolution;
  projectionState: GraphReferenceProjectionState;
  projectionError: string | null;
  requestedRevisionId: string | null;
  loadedRevisionId: string | null;
  items: readonly GraphReferenceSearchItem[];
  selectCampaign: (campaignId: string) => void;
  viewExact: (item: GraphReferenceSearchItem) => void;
}

export interface BuildSurfaceInteractionPublicationInput {
  documentId: string | null;
  acceptedDocument: { documentId: string; campaignId: string } | null;
  referenceContext: BuildReferenceContextBinding | null;
}

function buildBuildIdentity(documentId: string | null) {
  return buildSurfaceInteractionIdentity({
    surfaceId: BUILD_SURFACE_ID,
    instanceParts: [BUILD_SURFACE_ID, documentId ?? "__new_source__"],
  });
}

function buildEmptyInventoryPublication(documentId: string | null): SurfaceInteractionPublication {
  return {
    surfaceId: BUILD_SURFACE_ID,
    label: BUILD_SURFACE_LABEL,
    identity: buildBuildIdentity(documentId),
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}

function isAcceptedDocument(
  documentId: string | null,
  acceptedDocument: { documentId: string; campaignId: string } | null,
): acceptedDocument is { documentId: string; campaignId: string } {
  if (!documentId?.trim() || !acceptedDocument) return false;
  return acceptedDocument.documentId === documentId && acceptedDocument.campaignId.trim() !== "";
}

export function buildBuildSurfaceInteractionPublication(
  input: BuildSurfaceInteractionPublicationInput,
): SurfaceInteractionPublication {
  const { documentId, acceptedDocument, referenceContext } = input;

  if (!isAcceptedDocument(documentId, acceptedDocument) || referenceContext == null) {
    return buildEmptyInventoryPublication(documentId);
  }

  return {
    surfaceId: BUILD_SURFACE_ID,
    label: BUILD_SURFACE_LABEL,
    identity: buildBuildIdentity(documentId),
    canvas: {
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: documentId },
    },
    agentContext: null,
    tools: [
      {
        id: BUILD_FIND_EXISTING_TOOL_ID,
        label: "Find existing object",
        eyebrow: "World Graph",
        placement: {
          groupId: BUILD_WORLD_REFERENCE_GROUP_ID,
          groupLabel: BUILD_WORLD_REFERENCE_GROUP_LABEL,
          groupOrder: BUILD_WORLD_REFERENCE_GROUP_ORDER,
          itemOrder: 0,
        },
        availability: { status: "enabled" },
        activation: {
          kind: "projection",
          projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        },
      },
    ],
    editCommands: [],
    projections: [
      {
        id: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        kind: "tool",
        preferredSize: "wide",
        bindingIds: [BUILD_REFERENCE_CONTEXT_BINDING_ID],
      },
      {
        id: GRAPH_REFERENCE_PROJECTION_ID,
        kind: "content",
        preferredSize: "wide",
        bindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
      },
    ],
    projectionBindings: [
      { id: BUILD_REFERENCE_CONTEXT_BINDING_ID, value: referenceContext },
      {
        id: GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
        value: EMPTY_GRAPH_REFERENCE_RESOLUTION,
      },
    ],
  };
}
