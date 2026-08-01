import type {
  AgentEvidenceSnapshot,
  AgentInteractionThread,
  AgentInteractionThreadSummary,
  AgentInteractionTurn,
  CitationFreshnessCheckResult,
  LiveQueryCitation,
  LiveQueryResponse,
} from "../api/types";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  OpenGraphReferenceArgs,
} from "../graphReference/types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "../planSurface/projection/projectionBindings";
import type { ActiveProjection, ProjectionSize } from "../planSurface/types";
import type {
  ProjectionSurfacePublication,
  ValidatedProjectionSurface,
} from "./projectionSurfacePublication";

export type AgentInteractionSurfaceId = "plan" | "play" | "build" | string;

export interface AgentInteractionSourceLocator {
  kind: "opaque" | "path" | "anchor" | "unit" | string;
  value: string;
}

export interface AgentInteractionSourceUnitRef {
  unitId: string;
  label: string;
  sourceAnchor?: AgentInteractionSourceLocator | null;
  canonState?: string | null;
  lifecycleState?: string | null;
  evidenceRole?: string | null;
  authorityState?: string | null;
  visibilityState?: string | null;
  displaySummary?: string | null;
  diagnostics?: string[];
}

export interface AgentInteractionSourceEnvelope {
  schema: "agent_interaction_source_envelope_v1";
  artifactRefs?: AgentInteractionSourceLocator[];
  anchorRefs?: AgentInteractionSourceLocator[];
  unitRefs?: AgentInteractionSourceUnitRef[];
  provenanceSummary?: string | null;
  warnings?: string[];
}

export interface AgentInteractionToolProofPointer {
  pointerId: string;
  kind: "tool_plan_preview" | "tool_call_result" | "draft_artifact" | "confirmation" | string;
  label: string;
  artifactId?: string | null;
  locator?: AgentInteractionSourceLocator | null;
  status?: "preview" | "proposed" | "confirmed" | "rejected" | string;
  createdAt: string;
}

export interface AgentInteractionSelectedSource {
  citationKey: string;
  path: string;
  evidenceId?: string | null;
  lineStart?: number | null;
  lineEnd?: number | null;
}

export interface AgentInteractionPaneState {
  isOpen: boolean;
  mode: "bar" | "pane";
}

export interface AgentInteractionSurfaceContext {
  surfaceId: AgentInteractionSurfaceId;
  label: string;
  campaignId?: string | null;
  documentId?: string | null;
  sessionNumber?: number | null;
  ambientSummary?: string | null;
  sourceEnvelope?: AgentInteractionSourceEnvelope | null;
  updatedAt: string;
}

export interface AgentInteractionProviderState {
  activeThreadId: string | null;
  threads: AgentInteractionThread[];
  threadSummaries: AgentInteractionThreadSummary[];
  paneState: AgentInteractionPaneState;
  activeSurfaceContext: AgentInteractionSurfaceContext | null;
  selectedSource: AgentInteractionSelectedSource | null;
}

export interface AgentInteractionScope {
  campaignId: string;
  sessionNumber: number | null;
  surfaceId?: AgentInteractionSurfaceId;
  documentId?: string | null;
}

export interface AgentInteractionActions {
  publishSurfaceContext: (context: AgentInteractionSurfaceContext) => void;
  setPaneOpen: (isOpen: boolean) => void;
  setPaneMode: (mode: AgentInteractionPaneState["mode"]) => void;
  setSelectedSource: (source: AgentInteractionSelectedSource | null) => void;
  ensureThread: (title?: string) => AgentInteractionThread;
  createThread: (title?: string) => AgentInteractionThread;
  switchThread: (threadId: string) => AgentInteractionThread | null;
  deleteThread: (threadId: string) => void;
  renameThread: (title: string) => AgentInteractionThread | null;
  clearThread: () => AgentInteractionThread | null;
  updateThread: (thread: AgentInteractionThread) => AgentInteractionThread;
  updateActiveTurn: (turnId: string) => void;
}

export interface AgentInteractionProjectionState {
  projectionSurface: ValidatedProjectionSurface | null;
  active: ActiveProjection | null;
  activeGraphReference: GraphReferenceResolution | null;
  graphReferenceProjectionState: GraphReferenceProjectionState | null;
  graphReferenceBinding: GraphReferenceProjectionBinding | null;
  graphReviewDiagnosticsPayload: GraphReviewDiagnosticsProjectionPayload | null;
}

export interface AgentInteractionProjectionActions {
  publishProjectionSurface: (publication: ProjectionSurfacePublication | null) => () => void;
  /**
   * Same-identity config update on the current surface lease. No-op unless the
   * publication identity matches the current registration; never unbinds.
   */
  updateProjectionSurfaceConfig: (publication: ProjectionSurfacePublication) => void;
  openTool: (toolId: string) => void;
  openGraphReference: (args: OpenGraphReferenceArgs) => void;
  expandContent: () => void;
  close: () => void;
  registerGraphReferenceBinding: (binding: GraphReferenceProjectionBinding) => () => void;
  registerToolProjectionPayload: <K extends RegisterableToolProjectionId>(
    toolId: K,
    payload: ToolProjectionPayloadMap[K],
  ) => () => void;
}

export interface AgentInteractionContextValue
  extends AgentInteractionProviderState,
    AgentInteractionActions,
    AgentInteractionProjectionState,
    AgentInteractionProjectionActions {
  scope: AgentInteractionScope | null;
  activeThread: AgentInteractionThread | null;
  turns: AgentInteractionTurn[];
  traceVisible: boolean;
  rehydrateScope: (scope: AgentInteractionScope) => void;
  appendResponseTurn: (question: string, response: LiveQueryResponse) => AgentInteractionThread;
  updateTurnFreshness: (turnId: string, freshness: CitationFreshnessCheckResult) => AgentInteractionThread | null;
}

export type { ProjectionSize };

export type AgentInteractionEvidenceSnapshot = AgentEvidenceSnapshot;
export type AgentInteractionCitation = LiveQueryCitation;
