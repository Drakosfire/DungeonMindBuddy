import type { AppChromeAction, AppChromeTools } from "../chrome/AppChrome";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import { validateSurfaceInteractionPublication } from "../surfaceInteraction/publication";
import type {
  SurfaceInteractionAgentContextContribution,
  SurfaceInteractionCanvasContribution,
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionPlacement,
  SurfaceInteractionProjectionDescriptor,
  SurfaceInteractionPublication,
  SurfaceInteractionToolContribution,
  SurfaceInteractionWorkObjectIdentity,
} from "../surfaceInteraction/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../surfaceInteraction/projection/projectionCatalog";
import type {
  ProjectionSurfacePublication,
  ValidatedProjectionSurface,
} from "./projectionSurfacePublication";
import type { SurfaceInteractionChromeFragment } from "./surfaceInteractionLease";

const LEGACY_CONTEXT_UNAVAILABLE = "Required legacy projection context is unavailable.";
const LEGACY_APPCHROME_DISABLED = "Unavailable in the current legacy AppChrome state.";

const PAGE_TOOLS_GROUP_ID = "legacy-page-tools";
const PAGE_TOOLS_GROUP_LABEL = "Page tools";
const PAGE_TOOLS_GROUP_ORDER = 100;

const BLANK_COMMAND_TARGET = { kind: "", id: "" } as const;

function enabledAvailability() {
  return { status: "enabled" as const };
}

function disabledAvailability(reason: string) {
  return { status: "disabled" as const, disabledReason: reason };
}

function canvasWorkObject(
  publication: SurfaceInteractionPublication | null,
): SurfaceInteractionWorkObjectIdentity | null {
  return publication?.canvas?.workObject ?? null;
}

function boundedAmbientSummary(label: string, headerLabel?: string): string {
  const parts = [label, headerLabel].filter((entry): entry is string => Boolean(entry && entry.trim()));
  const combined = parts.join(" · ");
  return combined.length > 500 ? combined.slice(0, 500) : combined;
}

function buildAgentContextFromLegacy(
  publication: ProjectionSurfacePublication,
): SurfaceInteractionAgentContextContribution | null {
  const { identity, config } = publication;
  const context = config.context;
  if (!context) return null;
  const documentId = config.canvas.documentId ?? null;
  const sessionNumber =
    identity.surfaceId === "ingest" ? context.ingestSession : context.liveSession;
  return {
    label: context.headerLabel,
    campaignId: context.campaignId,
    documentId,
    sessionNumber,
    ambientSummary: boundedAmbientSummary(config.label, context.headerLabel),
    pointers: [],
  };
}

function buildCanvasFromLegacy(
  publication: ProjectionSurfacePublication,
): SurfaceInteractionCanvasContribution | null {
  const documentId = publication.config.canvas.documentId;
  if (documentId == null || documentId === "") return null;
  return {
    canvasId: "markdown-canvas",
    workObject: { kind: "document", id: documentId },
  };
}

export function adaptProjectionSurfaceToNeutralBase(
  validated: ValidatedProjectionSurface,
): SurfaceInteractionPublication {
  const { identity, config } = validated.publication;
  const hasContext = config.context != null;
  const tools: SurfaceInteractionToolContribution[] = config.tools.map((tool, index) => ({
    id: tool.id,
    label: tool.label,
    placement: {
      groupId: null,
      groupLabel: null,
      groupOrder: 0,
      itemOrder: index,
    } satisfies SurfaceInteractionPlacement,
    availability: hasContext ? enabledAvailability() : disabledAvailability(LEGACY_CONTEXT_UNAVAILABLE),
    activation: hasContext
      ? { kind: "projection", projectionId: tool.id }
      : { kind: "command", invoke: () => undefined },
  }));

  return {
    surfaceId: config.id,
    label: config.label,
    identity: {
      surfaceId: identity.surfaceId,
      instanceKey: identity.instanceKey,
    },
    canvas: buildCanvasFromLegacy(validated.publication),
    agentContext: buildAgentContextFromLegacy(validated.publication),
    tools,
    editCommands: [],
    projections: [
      ...config.tools.map((tool) => ({
        id: tool.id,
        kind: "tool" as const,
        preferredSize: tool.size,
        bindingIds: [],
      })),
      ...(identity.surfaceId === "plan" && config.id === "plan"
        ? [{
            id: GRAPH_REFERENCE_PROJECTION_ID,
            kind: "content" as const,
            preferredSize: "wide" as const,
            bindingIds: [] as readonly string[],
          } satisfies SurfaceInteractionProjectionDescriptor]
        : []),
    ],
    projectionBindings: [],
  };
}

function mapPageAction(action: AppChromeAction, index: number): SurfaceInteractionToolContribution {
  return {
    id: action.id,
    label: action.label,
    ...(action.eyebrow !== undefined ? { eyebrow: action.eyebrow } : {}),
    placement: {
      groupId: PAGE_TOOLS_GROUP_ID,
      groupLabel: PAGE_TOOLS_GROUP_LABEL,
      groupOrder: PAGE_TOOLS_GROUP_ORDER,
      itemOrder: index,
    },
    availability: action.disabled ? disabledAvailability(LEGACY_APPCHROME_DISABLED) : enabledAvailability(),
    activation: { kind: "command", invoke: action.onClick },
  };
}

function editTarget(workObject: SurfaceInteractionWorkObjectIdentity | null): SurfaceInteractionWorkObjectIdentity {
  return workObject ?? BLANK_COMMAND_TARGET;
}

function mapPinnedEditAction(
  action: AppChromeAction,
  index: number,
  workObject: SurfaceInteractionWorkObjectIdentity | null,
): SurfaceInteractionEditCommandContribution {
  return {
    id: action.id,
    label: action.label,
    ...(action.eyebrow !== undefined ? { eyebrow: action.eyebrow } : {}),
    placement: {
      groupId: null,
      groupLabel: null,
      groupOrder: 0,
      itemOrder: index,
    },
    availability: action.disabled ? disabledAvailability(LEGACY_APPCHROME_DISABLED) : enabledAvailability(),
    target: editTarget(workObject),
    ...(action.pressed !== undefined ? { pressed: action.pressed } : {}),
    invoke: action.onClick,
  };
}

function mapSectionEditAction(
  action: AppChromeAction,
  section: { id: string; title: string; defaultOpen?: boolean },
  sectionIndex: number,
  actionIndex: number,
  workObject: SurfaceInteractionWorkObjectIdentity | null,
): SurfaceInteractionEditCommandContribution {
  return {
    id: action.id,
    label: action.label,
    ...(action.eyebrow !== undefined ? { eyebrow: action.eyebrow } : {}),
    placement: {
      groupId: section.id,
      groupLabel: section.title,
      groupOrder: sectionIndex,
      itemOrder: actionIndex,
      ...(section.defaultOpen !== undefined
        ? { groupDefaultOpen: section.defaultOpen }
        : {}),
    },
    availability: action.disabled ? disabledAvailability(LEGACY_APPCHROME_DISABLED) : enabledAvailability(),
    target: editTarget(workObject),
    ...(action.pressed !== undefined ? { pressed: action.pressed } : {}),
    invoke: action.onClick,
  };
}

export function buildAppChromeCompatibilityFragment(input: {
  pageActions: readonly AppChromeAction[];
  editorTools: AppChromeTools | null | undefined;
  basePublication: SurfaceInteractionPublication | null;
  /** When provided, stamps edit commands to this target instead of basePublication canvas. */
  editCommandTarget?: SurfaceInteractionWorkObjectIdentity | null;
}): SurfaceInteractionChromeFragment {
  const workObject = input.editCommandTarget !== undefined
    ? input.editCommandTarget
    : canvasWorkObject(input.basePublication);
  const pinnedActions = input.editorTools?.pinnedActions ?? [];
  const sections = input.editorTools?.sections ?? [];
  return {
    tools: input.pageActions.map(mapPageAction),
    editCommands: [
      ...pinnedActions.map((action, index) => mapPinnedEditAction(action, index, workObject)),
      ...sections.flatMap((section, sectionIndex) =>
        section.actions.map((action, actionIndex) =>
          mapSectionEditAction(action, section, sectionIndex, actionIndex, workObject),
        ),
      ),
    ],
  };
}

export function buildIndexRouteCompatibilityPublication(): SurfaceInteractionPublication {
  return {
    surfaceId: "index",
    label: "Command Board",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "index", instanceParts: ["index"] }),
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}

export function buildSurfaceRouteCompatibilityPublication(): SurfaceInteractionPublication {
  return {
    surfaceId: "surface",
    label: "Live Control",
    identity: buildSurfaceInteractionIdentity({
      surfaceId: "surface",
      instanceParts: ["surface", "live-control"],
    }),
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}

export function buildTiptapCalloutSpikeRouteCompatibilityPublication(): SurfaceInteractionPublication {
  return {
    surfaceId: "tiptap-callout-spike",
    label: "Tiptap Callout Spike",
    identity: buildSurfaceInteractionIdentity({
      surfaceId: "tiptap-callout-spike",
      instanceParts: ["tiptap-callout-spike"],
    }),
    canvas: {
      canvasId: "tiptap-callout-spike",
      workObject: { kind: "spike", id: "tiptap-callout-spike" },
    },
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}

export function assertValidRouteCompatibilityPublication(publication: SurfaceInteractionPublication): void {
  const result = validateSurfaceInteractionPublication(publication);
  if (!result.valid) {
    throw new Error(
      `Route compatibility publication failed validation: ${result.issues.map((issue) => issue.code).join(", ")}`,
    );
  }
}

export const ROUTE_COMPATIBILITY_PUBLICATIONS = {
  index: buildIndexRouteCompatibilityPublication(),
  surface: buildSurfaceRouteCompatibilityPublication(),
  tiptapCalloutSpike: buildTiptapCalloutSpikeRouteCompatibilityPublication(),
} as const;

assertValidRouteCompatibilityPublication(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
assertValidRouteCompatibilityPublication(ROUTE_COMPATIBILITY_PUBLICATIONS.surface);
assertValidRouteCompatibilityPublication(ROUTE_COMPATIBILITY_PUBLICATIONS.tiptapCalloutSpike);

export { BLANK_COMMAND_TARGET, LEGACY_APPCHROME_DISABLED, LEGACY_CONTEXT_UNAVAILABLE };
