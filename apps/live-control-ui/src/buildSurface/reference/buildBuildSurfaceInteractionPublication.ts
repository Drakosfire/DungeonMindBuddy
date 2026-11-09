import { STATBLOCK_WORKBENCH_TOOL, STATBLOCK_WORKBENCH_PROJECTION } from "../../statblocks/statblockWorkbenchProjection";
import { RULES_LOOKUP_TOOL, RULES_LOOKUP_PROJECTION } from "../../rulesLookup/rulesLookupProjection";
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
import type {InspectionPin} from "../../api/nativeGraphInspection";

const BUILD_SURFACE_ID = "build" as const;
const BUILD_WORLD_REFERENCE_GROUP_ID = "build-world-reference" as const;
const BUILD_WORLD_REFERENCE_GROUP_LABEL = "World references" as const;
const BUILD_WORLD_REFERENCE_GROUP_ORDER = 10;
const BUILD_DOCUMENT_EDIT_GROUP_ID = "build-document" as const;
const BUILD_DOCUMENT_EDIT_GROUP_LABEL = "Document" as const;
const BUILD_DOCUMENT_EDIT_GROUP_ORDER = 0;

export interface BuildReferenceContextBinding {
  schema: "dmb_build_reference_context_v3";
  documentId: string;
  worldId: string;
  insertChip: (pin: InspectionPin, nodeId: string, label: string) => void;
  editorInsertDisabled: boolean;
}

export interface BuildDocumentSavePublication {
  saveDisabled: boolean;
  disabledReason?: string;
  save: () => void | Promise<void>;
}

export interface BuildSurfaceInteractionPublicationInput {
  documentId: string | null;
  acceptedDocument: { documentId: string; worldId: string | null } | null;
  referenceContext: BuildReferenceContextBinding | null;
  documentSave?: BuildDocumentSavePublication | null;
}

function buildBuildIdentity(documentId: string | null) {
  return buildSurfaceInteractionIdentity({
    surfaceId: BUILD_SURFACE_ID,
    instanceParts: [BUILD_SURFACE_ID, documentId ?? "__new_source__"],
  });
}

function buildDocumentIndependentPublication(documentId: string | null): SurfaceInteractionPublication {
  return {
    surfaceId: BUILD_SURFACE_ID,
    label: BUILD_SURFACE_LABEL,
    identity: buildBuildIdentity(documentId),
    canvas: null,
    agentContext: null,
    tools: [RULES_LOOKUP_TOOL, STATBLOCK_WORKBENCH_TOOL],
    editCommands: [],
    projections: [RULES_LOOKUP_PROJECTION, STATBLOCK_WORKBENCH_PROJECTION],
    projectionBindings: [],
  };
}

function isAcceptedDocument(
  documentId: string | null,
  acceptedDocument: { documentId: string; worldId: string | null } | null,
): acceptedDocument is { documentId: string; worldId: string | null } {
  if (!documentId?.trim() || !acceptedDocument) return false;
  return acceptedDocument.documentId === documentId;
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

  if (!isAcceptedDocument(documentId, acceptedDocument)) {
    return buildDocumentIndependentPublication(documentId);
  }

  const admittedDocumentId = acceptedDocument.documentId;
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
      RULES_LOOKUP_TOOL,
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
        availability: referenceContext ? {status: "enabled"} : {status: "disabled", disabledReason: "Open a document in a managed World to find its objects."},
        activation: {
          kind: "projection",
          projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        },
      },
      STATBLOCK_WORKBENCH_TOOL,
    ],
    editCommands,
    projections: [
      RULES_LOOKUP_PROJECTION,
      {
        id: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        kind: "tool",
        preferredSize: "wide",
        bindingIds: [BUILD_REFERENCE_CONTEXT_BINDING_ID],
      },
      STATBLOCK_WORKBENCH_PROJECTION,
    ],
    projectionBindings: [{ id: BUILD_REFERENCE_CONTEXT_BINDING_ID, value: referenceContext }],
  };
}
