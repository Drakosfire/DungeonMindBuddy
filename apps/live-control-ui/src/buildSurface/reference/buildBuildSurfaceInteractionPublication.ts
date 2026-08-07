import { GRAPH_REFERENCE_RESOLUTION_BINDING_ID } from "../../graphReference/projectionBindings";
import type {
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import type {
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionPublication,
} from "../../surfaceInteraction/types";
import { BUILD_DOCUMENT_SAVE_COMMAND_ID } from "../buildDocumentCommands";
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
const BUILD_DOCUMENT_EDIT_GROUP_ID = "build-document" as const;
const BUILD_DOCUMENT_EDIT_GROUP_LABEL = "Document" as const;
const BUILD_DOCUMENT_EDIT_GROUP_ORDER = 0;

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
  /** True only when a head request verified snapshot.isHead. */
  loadedIsHead: boolean;
  items: readonly GraphReferenceSearchItem[];
  selectCampaign: (campaignId: string) => void;
  viewExact: (item: GraphReferenceSearchItem) => void;
  /**
   * Insert a graph-node chip into the Build markdown canvas.
   * Pass a node id only; the capability resolves the canonical projection item,
   * verifies the live load key, and applies object-level campaign admission
   * before inserting.
   */
  insertChip: (nodeId: string) => void;
  /** Global editor-lock disable only; View stays available. Per-object tenancy is separate. */
  insertDisabled: boolean;
}

export interface BuildDocumentSavePublication {
  saveDisabled: boolean;
  disabledReason?: string;
  save: () => void | Promise<void>;
}

export interface BuildSurfaceInteractionPublicationInput {
  documentId: string | null;
  acceptedDocument: { documentId: string; campaignId: string } | null;
  referenceContext: BuildReferenceContextBinding | null;
  documentSave?: BuildDocumentSavePublication | null;
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

function buildDocumentSaveCommand(
  documentId: string,
  documentSave: BuildDocumentSavePublication,
): SurfaceInteractionEditCommandContribution {
  return {
    id: BUILD_DOCUMENT_SAVE_COMMAND_ID,
    label: "Save",
    eyebrow: "Document",
    placement: {
      groupId: BUILD_DOCUMENT_EDIT_GROUP_ID,
      groupLabel: BUILD_DOCUMENT_EDIT_GROUP_LABEL,
      groupOrder: BUILD_DOCUMENT_EDIT_GROUP_ORDER,
      itemOrder: 0,
    },
    availability: documentSave.saveDisabled
      ? {
          status: "disabled",
          disabledReason: documentSave.disabledReason?.trim() || "Save is unavailable for this document.",
        }
      : { status: "enabled" },
    target: { kind: "document", id: documentId },
    invoke: () => documentSave.save(),
  };
}

export function buildBuildSurfaceInteractionPublication(
  input: BuildSurfaceInteractionPublicationInput,
): SurfaceInteractionPublication {
  const { documentId, acceptedDocument, referenceContext, documentSave = null } = input;

  if (!isAcceptedDocument(documentId, acceptedDocument) || referenceContext == null) {
    return buildEmptyInventoryPublication(documentId);
  }

  const admittedDocumentId = acceptedDocument.documentId;
  const lens = referenceContext.lens;
  // selection_required stays enabled (campaign picker is the action).
  // invalid lenses disable the Tool with the resolver's exact reason.
  const toolAvailability =
    lens.status === "invalid"
      ? { status: "disabled" as const, disabledReason: lens.reason }
      : { status: "enabled" as const };

  const editCommands = documentSave
    ? [buildDocumentSaveCommand(admittedDocumentId, documentSave)]
    : [];

  return {
    surfaceId: BUILD_SURFACE_ID,
    label: BUILD_SURFACE_LABEL,
    identity: buildBuildIdentity(admittedDocumentId),
    canvas: {
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: admittedDocumentId },
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
        availability: toolAvailability,
        activation: {
          kind: "projection",
          projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        },
      },
    ],
    editCommands,
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
