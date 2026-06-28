import type {
  AgentEvidenceSnapshot,
  AgentInteractionThread,
  AgentInteractionThreadSummary,
  AgentInteractionTurn,
  CitationFreshnessCheckResult,
  CitationSourceResponse,
  LiveQueryCitation,
  LiveQueryBackend,
} from "../api/types";

export type AgentInteractionSurfaceId = "plan" | "play" | "build" | string;

export type AgentInteractionPaneState = {
  isOpen: boolean;
  mode: "bar" | "pane";
};

export type AgentInteractionSourceLocator = {
  kind: "source_artifact" | "source_anchor" | "source_unit" | "citation" | "artifact" | string;
  value: string;
};

export type AgentInteractionSourceEnvelope = {
  schema: "dmb_agent_interaction_source_envelope_v1";
  artifactIds?: string[];
  anchorIds?: string[];
  unitIds?: string[];
  locators?: AgentInteractionSourceLocator[];
  displaySummary?: string | null;
  canonState?: string | null;
  lifecycleState?: string | null;
  evidenceRole?: string | null;
  authorityState?: string | null;
  visibilityState?: string | null;
  diagnostics?: string[];
  warnings?: string[];
};

export type AgentInteractionToolProofPointer = {
  schema: "dmb_agent_interaction_tool_proof_pointer_v1";
  intent?: string | null;
  toolPlanPreviewId?: string | null;
  toolCallResultId?: string | null;
  draftArtifactId?: string | null;
  artifactPointer?: string | null;
  confirmationState?: "not_required" | "preview" | "awaiting_confirmation" | "confirmed" | "rejected" | string;
  sourceEnvelope?: AgentInteractionSourceEnvelope | null;
  citationLocators?: AgentInteractionSourceLocator[];
  warnings?: string[];
};

export type AgentInteractionSurfaceContext = {
  surfaceId: AgentInteractionSurfaceId;
  label: string;
  campaignId?: string | null;
  sessionNumber?: number | null;
  ambientSummary?: string | null;
  sourceEnvelope?: AgentInteractionSourceEnvelope | null;
  updatedAt: string;
};

export type AgentInteractionSelectedSource = {
  citationKey: string | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  response: CitationSourceResponse | null;
};

export type AgentInteractionProviderState = {
  activeThreadId: string | null;
  activeThread: AgentInteractionThread | null;
  threads: AgentInteractionThreadSummary[];
  paneState: AgentInteractionPaneState;
  activeSurfaceContext: AgentInteractionSurfaceContext | null;
  selectedSource: AgentInteractionSelectedSource;
};

export type AgentInteractionTurnPersistenceShape = Pick<
  AgentInteractionTurn,
  | "turnId"
  | "askedAt"
  | "completedAt"
  | "question"
  | "answer"
  | "backend"
  | "status"
  | "contextSummary"
  | "citations"
  | "trace"
  | "warnings"
  | "retrievalFreshness"
  | "evidenceSnapshots"
  | "corpusFreshness"
> & {
  sourceEnvelope?: AgentInteractionSourceEnvelope | null;
  toolProofPointers?: AgentInteractionToolProofPointer[];
  sourceCurrentnessMetadata?: CitationFreshnessCheckResult[];
};

export type AgentInteractionThreadPersistenceShape = Omit<AgentInteractionThread, "turns"> & {
  turns: AgentInteractionTurnPersistenceShape[];
  activeBackend: LiveQueryBackend;
};

export type AgentInteractionCitationProof = {
  citations?: LiveQueryCitation[];
  evidenceSnapshots?: AgentEvidenceSnapshot[];
};
