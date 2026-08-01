import { useEffect, useMemo, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import {
  getSourceBundle,
  postCitationFreshness,
  postCitationSource,
  postLiveQuery,
  postWorldGraphSourceAnchorRead,
} from "../../api/liveApi";
import type {
  AgentInteractionThread,
  CitationFreshnessResponse,
  CitationSourceResponse,
  AgentInteractionTurn,
  HermesGraphGrounding,
  IngestionSourceBundle,
  LegacyPathCitation,
  LiveQueryResponse,
  PlanViewProjection,
  SourceUnit,
  WorldGraphAnchorCitation,
  WorldGraphProjectionFocus,
  WorldGraphSourceAnchorReadResponse,
} from "../../api/types";
import type { PlanSessionDescriptor } from "../types";

import {
  AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS,
  AGENT_TURN_HISTORY_CAP,
  createAgentInteractionThread,
  threadTitleFromQuestion,
  turnFromResponse,
} from "../../agentInteraction/agentInteractionStorage";
import {
  useAskPluginSlotOptional,
  useRegisterAskPluginPresence,
} from "../../agentInteraction/AskPluginSlot";
import { buildHermesConversationHistory } from "../../agentInteraction/hermesConversationHistory";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { ContextSufficiencyPanel } from "./ContextSufficiencyPanel";
import { buildPacketReview } from "./contextSufficiencyLadder";
import { TraceDetailsPanel } from "./TraceDetailsPanel";
import { RetrievalFreshnessPanel } from "./RetrievalFreshnessPanel";
import { CorpusChangeSignalPanel } from "./CorpusChangeSignalPanel";
import { WorldGraphQueryContextPanel } from "./WorldGraphQueryContextPanel";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import {
  buildPlanAgentWorldGraphQueryContextRequest,
  getPlanWorldGraphContext,
} from "../reference/planGraphContextRequest";
import { usePlanGraphLens } from "../PlanGraphLensContext";
import { isFocusValidationBlocking } from "../planGraphFocusOptions";
import {
  hasGrounding,
  isConversationContext,
  isHermesGraphAgentResponse,
  parseHermesGraphGrounding,
  prepMemoryLabel,
  s1SupportFromTurn,
  UNGROUNDED_ANSWER_WARNING,
  validateHermesGraphCitations,
} from "./prepMemoryQa";

interface PlanAgentInteractionBarProps {
  planView: PlanViewProjection;
  sessionDescriptor: PlanSessionDescriptor;
  loadBundle?: typeof getSourceBundle;
  askCorpus?: typeof postLiveQuery;
  readCitationSource?: typeof postCitationSource;
  readGraphSourceAnchor?: typeof postWorldGraphSourceAnchorRead;
  checkCitationFreshness?: typeof postCitationFreshness;
}

type BundleStatus = "idle" | "loading" | "ready" | "error";
type AskStatus = "idle" | "asking" | "answered" | "error";


interface EvidenceCard {
  evidenceId: string;
  path: string;
  sourceRole: string;
  authority: string;
  lineLabel: string;
  lineStart: number | null;
  lineEnd: number | null;
  textExcerpt: string | null;
}

function citationKey(path: string, evidenceId: string | null | undefined): string {
  return `${path}::${evidenceId ?? "unknown"}`;
}

function lineLabel(lineStart?: number | null, lineEnd?: number | null): string {
  if (lineStart == null && lineEnd == null) return "lines n/a";
  if (lineStart != null && lineEnd != null && lineStart !== lineEnd) return `lines ${lineStart}-${lineEnd}`;
  return `line ${lineStart ?? lineEnd}`;
}

const SOURCE_ANCHOR_READ_SCHEMA = "dmb_world_graph_source_anchor_read_v1";
const CANONICAL_SOURCE_ANCHOR_OUTCOMES = [
  "enough",
  "partial",
  "empty",
  "denied",
  "truncated",
  "unavailable",
] as const;
type CanonicalSourceAnchorOutcome = (typeof CANONICAL_SOURCE_ANCHOR_OUTCOMES)[number];
/** Outcomes that require string content when present; partial may legitimately omit content. */
const REQUIRED_CONTENT_SOURCE_ANCHOR_OUTCOMES: readonly CanonicalSourceAnchorOutcome[] = [
  "enough",
  "truncated",
];

type HermesGroundingParseResult =
  | { kind: "none" }
  | { kind: "malformed"; reason: string }
  | { kind: "valid"; grounding: HermesGraphGrounding };

function parseHermesGraphGroundingView(answer: LiveQueryResponse): HermesGroundingParseResult {
  if (!isHermesGraphAgentResponse(answer)) return { kind: "none" };
  const grounding = parseHermesGraphGrounding(answer.grounding);
  if (!grounding) {
    return { kind: "malformed", reason: "Missing or invalid Hermes graph grounding envelope." };
  }
  return { kind: "valid", grounding };
}

function isLegacyPathCitation(citation: unknown): citation is LegacyPathCitation {
  if (!citation || typeof citation !== "object") return false;
  const candidate = citation as { kind?: string; path?: unknown; evidence_id?: unknown };
  if (candidate.kind === "world_graph_anchor") return false;
  return typeof candidate.path === "string" && typeof candidate.evidence_id === "string";
}

function turnHasLegacyPathEvidence(turn: AgentInteractionTurn): boolean {
  if ((turn.evidenceSnapshots?.length ?? 0) > 0) return true;
  return (turn.citations ?? []).some((citation) => isLegacyPathCitation(citation));
}

function graphCitationKey(citation: WorldGraphAnchorCitation): string {
  return `graph:${citation.anchor_id}:${citation.revision_id}`;
}

function shortenAnchorId(anchorId: string): string {
  if (anchorId.length <= 28) return anchorId;
  return `${anchorId.slice(0, 14)}…${anchorId.slice(-10)}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function parseSnapshotFocus(
  value: unknown,
): WorldGraphProjectionFocus | null {
  if (!isRecord(value)) return null;
  if (typeof value.kind !== "string") return null;
  if (!(value.sessionId === null || typeof value.sessionId === "string")) return null;
  if (value.kind === "none") {
    if (value.sessionId !== null) return null;
    return { kind: "none", sessionId: null };
  }
  if (value.kind === "session") {
    if (!isNonEmptyString(value.sessionId)) return null;
    return { kind: "session", sessionId: value.sessionId };
  }
  return null;
}

function parseSourceAnchorSnapshot(
  value: unknown,
): WorldGraphSourceAnchorReadResponse["snapshot"] | null {
  if (!isRecord(value)) return null;
  if (!isNonEmptyString(value.worldId)) return null;
  if (!isNonEmptyString(value.campaignId)) return null;
  if (!isNonEmptyString(value.revisionId)) return null;
  if (typeof value.headRevisionId !== "string") return null;
  if (typeof value.isHead !== "boolean") return null;
  if (!isNonEmptyString(value.admissibility)) return null;
  const focus = parseSnapshotFocus(value.focus);
  if (!focus) return null;
  return {
    worldId: value.worldId,
    campaignId: value.campaignId,
    revisionId: value.revisionId,
    headRevisionId: value.headRevisionId,
    isHead: value.isHead,
    focus,
    admissibility: value.admissibility,
  };
}

function snapshotMatchesCitation(
  citation: WorldGraphAnchorCitation,
  snapshot: NonNullable<WorldGraphSourceAnchorReadResponse["snapshot"]>,
): boolean {
  if (snapshot.worldId !== citation.world_id) return false;
  if (snapshot.campaignId !== citation.campaign_id) return false;
  if (snapshot.admissibility !== citation.admissibility) return false;
  if (snapshot.revisionId !== citation.revision_id) return false;
  if (snapshot.focus.kind !== citation.focus.kind) return false;
  const citationSessionId = citation.focus.session_id ?? null;
  return snapshot.focus.sessionId === citationSessionId;
}

function parseSourceAnchorDiagnostics(
  value: unknown,
): WorldGraphSourceAnchorReadResponse["diagnostics"] | null {
  if (value == null) return [];
  if (!Array.isArray(value)) return null;
  const diagnostics: WorldGraphSourceAnchorReadResponse["diagnostics"] = [];
  for (const item of value) {
    if (!isRecord(item)) return null;
    if (typeof item.code !== "string" || typeof item.message !== "string") return null;
    diagnostics.push({
      code: item.code,
      message: item.message,
      severity: typeof item.severity === "string" ? item.severity : "info",
    });
  }
  return diagnostics;
}

function isCanonicalSourceAnchorOutcome(value: unknown): value is CanonicalSourceAnchorOutcome {
  return typeof value === "string"
    && (CANONICAL_SOURCE_ANCHOR_OUTCOMES as readonly string[]).includes(value);
}

function validateGraphSourceAnchorRead(
  citation: WorldGraphAnchorCitation,
  response: unknown,
): { ok: true; response: WorldGraphSourceAnchorReadResponse } | { ok: false; reason: string } {
  if (!isRecord(response)) {
    return { ok: false, reason: "Source-anchor read response was not an object." };
  }
  if (response.schema !== SOURCE_ANCHOR_READ_SCHEMA) {
    return { ok: false, reason: "Source-anchor read response schema mismatch." };
  }
  if (!isCanonicalSourceAnchorOutcome(response.outcome)) {
    return { ok: false, reason: "Source-anchor read outcome is not canonical." };
  }
  if (response.anchorId !== citation.anchor_id) {
    return { ok: false, reason: "Source-anchor read anchorId does not match the citation." };
  }

  const diagnostics = parseSourceAnchorDiagnostics(response.diagnostics);
  if (diagnostics === null) {
    return { ok: false, reason: "Source-anchor read diagnostics are malformed." };
  }

  if (response.outcome === "unavailable") {
    if (response.snapshot == null) {
      return {
        ok: true,
        response: {
          ...(response as unknown as WorldGraphSourceAnchorReadResponse),
          schema: SOURCE_ANCHOR_READ_SCHEMA,
          outcome: "unavailable",
          snapshot: null,
          content: typeof response.content === "string" ? response.content : null,
          diagnostics,
        },
      };
    }
    const snapshot = parseSourceAnchorSnapshot(response.snapshot);
    if (!snapshot) {
      return { ok: false, reason: "Source-anchor unavailable response has malformed snapshot." };
    }
    if (!snapshotMatchesCitation(citation, snapshot)) {
      return { ok: false, reason: "Source-anchor unavailable snapshot does not match the pinned citation." };
    }
    return {
      ok: true,
      response: {
        ...(response as unknown as WorldGraphSourceAnchorReadResponse),
        schema: SOURCE_ANCHOR_READ_SCHEMA,
        outcome: "unavailable",
        snapshot,
        content: typeof response.content === "string" ? response.content : null,
        diagnostics,
      },
    };
  }

  const snapshot = parseSourceAnchorSnapshot(response.snapshot);
  if (!snapshot) {
    return { ok: false, reason: "Source-anchor read requires a matching snapshot." };
  }
  if (!snapshotMatchesCitation(citation, snapshot)) {
    return { ok: false, reason: "Source-anchor read snapshot does not match the pinned citation." };
  }

  if (REQUIRED_CONTENT_SOURCE_ANCHOR_OUTCOMES.includes(response.outcome)) {
    if (typeof response.content !== "string") {
      return { ok: false, reason: "Content-bearing source-anchor outcomes require string content." };
    }
  } else if (response.content != null && typeof response.content !== "string") {
    return { ok: false, reason: "Source-anchor content must be a string or null." };
  }

  return {
    ok: true,
    response: {
      ...(response as unknown as WorldGraphSourceAnchorReadResponse),
      schema: SOURCE_ANCHOR_READ_SCHEMA,
      outcome: response.outcome,
      snapshot,
      content: typeof response.content === "string" ? response.content : null,
      diagnostics,
    },
  };
}

function graphSourceAnchorHasContent(outcome: string, content: string | null | undefined): boolean {
  if (typeof content !== "string" || !content) return false;
  return outcome === "enough" || outcome === "partial" || outcome === "truncated";
}

function evidenceCardsFromAnswer(answer: LiveQueryResponse): EvidenceCard[] {
  const cards = new Map<string, EvidenceCard>();
  for (const item of answer.context_packet?.admitted_evidence ?? []) {
    cards.set(citationKey(item.path, item.evidence_id), {
      evidenceId: item.evidence_id ?? item.unit_id ?? "admitted evidence",
      path: item.path,
      sourceRole: item.source_role,
      authority: item.authority,
      lineLabel: lineLabel(item.line_start, item.line_end),
      lineStart: item.line_start ?? null,
      lineEnd: item.line_end ?? null,
      textExcerpt: item.text_excerpt ?? null,
    });
  }
  for (const citation of answer.citations ?? []) {
    if (!isLegacyPathCitation(citation)) continue;
    const key = citationKey(citation.path, citation.evidence_id);
    if (cards.has(key)) continue;
    cards.set(key, {
      evidenceId: citation.evidence_id,
      path: citation.path,
      sourceRole: citation.source_role,
      authority: citation.authority,
      lineLabel: lineLabel(citation.line_start, citation.line_end),
      lineStart: citation.line_start ?? null,
      lineEnd: citation.line_end ?? null,
      textExcerpt: null,
    });
  }
  return Array.from(cards.values());
}

function liveQueryResponseFromTurn(
  turn: AgentInteractionTurn,
  wire: LiveQueryResponse | undefined,
): LiveQueryResponse {
  const fromTurn = {
    answer: turn.answer,
    status: turn.status,
    mode: turn.trace?.mode
      ?? (turn.grounding?.schema === "dmb_hermes_graph_grounding_v1" ? "hermes_graph_agent" : undefined),
    citations: turn.citations ?? [],
    warnings: turn.warnings ?? [],
    agent_trace: turn.trace ?? null,
    context_packet: null,
    classification: {} as never,
    events_written: [],
    jobs_queued: [],
    next_suggestions: [],
    diagnostics: {},
    provenance: {},
    retrieval_freshness: turn.retrievalFreshness ?? null,
    grounding: turn.grounding ?? null,
    world_graph_context: turn.worldGraphContext ?? null,
  } satisfies LiveQueryResponse;
  if (!wire) return fromTurn;
  return {
    ...wire,
    answer: turn.answer,
    status: turn.status,
    citations: turn.citations ?? [],
    warnings: turn.warnings ?? [],
    agent_trace: turn.trace ?? null,
    grounding: turn.grounding ?? null,
    retrieval_freshness: turn.retrievalFreshness ?? wire.retrieval_freshness ?? null,
  };
}

function renderSourceWithHighlight(source: CitationSourceResponse) {
  const excerpt = source.highlight.text_excerpt?.trim();
  if (!excerpt) return source.content;
  const index = source.content.indexOf(excerpt);
  if (index < 0) return source.content;
  return (
    <>
      {source.content.slice(0, index)}
      <mark>{excerpt}</mark>
      {source.content.slice(index + excerpt.length)}
    </>
  );
}

const REQUIRED_INGEST_STAGES = [
  "canon_recap",
  "normalized",
  "breadcrumbed",
  "frontmatter_seed",
  "session_memory_jsonl",
  "session_memory_meta",
];

function numberField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function sourceKind(unit: SourceUnit): string {
  return stringField(unit.fields.sourceKind) ?? unit.unitKind;
}

function unitsForSession(bundle: IngestionSourceBundle, session: number): SourceUnit[] {
  return (bundle.units ?? [])
    .filter((unit) => unit.evidenceRole !== "diagnostic_only")
    .filter((unit) => numberField(unit.fields.sessionNumber) === session);
}

function representativeUnits(bundle: IngestionSourceBundle, activeSession: number): SourceUnit[] {
  const activeSessionUnits = unitsForSession(bundle, activeSession);
  const fallbackUnits = (bundle.units ?? []).filter((unit) => unit.evidenceRole !== "diagnostic_only");
  return (activeSessionUnits.length ? activeSessionUnits : fallbackUnits).slice(0, 8);
}

function sessionNumbers(bundle: IngestionSourceBundle): number[] {
  const sessions = new Set<number>();
  for (const unit of bundle.units ?? []) {
    const session = numberField(unit.fields.sessionNumber);
    if (session !== null) sessions.add(session);
  }
  return Array.from(sessions).sort((a, b) => b - a);
}

export function PlanAgentInteractionBar({
  planView: _planView,
  sessionDescriptor,
  loadBundle = getSourceBundle,
  askCorpus = postLiveQuery,
  readCitationSource = postCitationSource,
  readGraphSourceAnchor = postWorldGraphSourceAnchorRead,
  checkCitationFreshness = postCitationFreshness,
}: PlanAgentInteractionBarProps) {
  const agentInteraction = useAgentInteraction();
  useRegisterAskPluginPresence(true);
  const askSlot = useAskPluginSlotOptional();
  const { projection, projectionState, projectionError } = usePlanGraphReferenceResolver();
  const {
    lens,
    derived,
    summaryLabel,
    focusValidationStatus,
  } = usePlanGraphLens();
  const focusValidationPending = isFocusValidationBlocking(focusValidationStatus);
  const planWorldGraphContext = getPlanWorldGraphContext(sessionDescriptor, { lens });
  const hasSupportedGraphContext = planWorldGraphContext != null;
  const graphContextInitializing =
    focusValidationPending
    || (hasSupportedGraphContext && projectionState === "loading");
  const lensAllowsAsk = derived != null && !focusValidationPending;
  const open = agentInteraction.paneState.isOpen;
  const setOpen = agentInteraction.setPaneOpen;
  const [status, setStatus] = useState<BundleStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<IngestionSourceBundle | null>(null);
  const [question, setQuestion] = useState("");
  const [askStatus, setAskStatus] = useState<AskStatus>("idle");
  const [askError, setAskError] = useState<string | null>(null);
  const thread = agentInteraction.activeThread;
  const turns = agentInteraction.turns;
  const setThread = agentInteraction.updateThread;
  const setTurns = (nextTurns: AgentInteractionTurn[]) => {
    if (thread) agentInteraction.updateThread({ ...thread, turns: nextTurns, updatedAt: new Date().toISOString() });
  };
  const [turnResponses, setTurnResponses] = useState<Record<string, LiveQueryResponse>>({});
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const [selectedCitationKey, setSelectedCitationKey] = useState<string | null>(null);
  const [sourceStatus, setSourceStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [sourceResponse, setSourceResponse] = useState<CitationSourceResponse | null>(null);
  const [graphReadStatus, setGraphReadStatus] = useState<"idle" | "loading" | "ready" | "error" | "contract_error">("idle");
  const [graphReadError, setGraphReadError] = useState<string | null>(null);
  const [graphReadResponse, setGraphReadResponse] = useState<WorldGraphSourceAnchorReadResponse | null>(null);
  const [graphReadWarnings, setGraphReadWarnings] = useState<string[]>([]);
  const threadSummaries = agentInteraction.threadSummaries;
  const [threadSwitcherOpen, setThreadSwitcherOpen] = useState(false);
  const [configMenuOpen, setConfigMenuOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [freshnessChecking, setFreshnessChecking] = useState(false);

  const memorySessionLabel = prepMemoryLabel(sessionDescriptor);
  const planningDocumentId = sessionDescriptor.planningDocument.documentId;
  // Outer /api/live/query must match the loaded live packet session (liveSession),
  // not memorySession. World-graph focus uses memorySession when ?session= is set;
  // otherwise focus is world-union (kind: none).
  const querySession = sessionDescriptor.liveSession;

  useEffect(() => {
    const { planningDocument } = sessionDescriptor;
    agentInteraction.rehydrateScope({
      campaignId: sessionDescriptor.campaignId,
      sessionNumber: sessionDescriptor.liveSession,
      surfaceId: "plan",
      documentId: planningDocument.documentId,
    });
    agentInteraction.publishSurfaceContext({
      surfaceId: "plan",
      label: planningDocument.title,
      campaignId: sessionDescriptor.campaignId,
      documentId: planningDocument.documentId,
      sessionNumber: sessionDescriptor.liveSession,
      ambientSummary: `Plan prep for ${sessionDescriptor.campaignLabel}, ${memorySessionLabel}`,
      sourceEnvelope: null,
      updatedAt: new Date().toISOString(),
    });
  }, [
    sessionDescriptor.campaignId,
    sessionDescriptor.campaignLabel,
    sessionDescriptor.liveSession,
    sessionDescriptor.planningDocument.documentId,
    sessionDescriptor.planningDocument.title,
    memorySessionLabel,
  ]);

  useEffect(() => {
    if (!thread) {
      setActiveTurnId(null);
      return;
    }
    setActiveTurnId(thread.uiState?.scrollAnchorTurnId ?? thread.turns[0]?.turnId ?? null);
  }, [thread]);

  useEffect(() => {
    const anchorId = thread?.uiState?.scrollAnchorTurnId;
    if (!anchorId) return;
    const element = document.querySelector(`[data-turn-id="${anchorId}"]`);
    element?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [thread?.uiState?.scrollAnchorTurnId, turns.length]);

  const chronologicalTurns = useMemo(() => [...turns].reverse(), [turns]);

  const activeTurn = useMemo(
    () => turns.find((turn) => turn.turnId === activeTurnId) ?? turns[0] ?? null,
    [turns, activeTurnId],
  );
  const threadTitle = thread?.title ?? "New prep thread";
  const traceVisible = thread?.uiState?.traceVisible ?? false;

  const showNewThreadSuggestion = Boolean(
    thread &&
      turns.length > 0 &&
      turns.length >= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS &&
      !thread.uiState?.newThreadSuggestionDismissed,
  );

  function resetSourceReader() {
    setSelectedCitationKey(null);
    setSourceStatus("idle");
    setSourceError(null);
    setSourceResponse(null);
    setGraphReadStatus("idle");
    setGraphReadError(null);
    setGraphReadResponse(null);
    setGraphReadWarnings([]);
  }

  function refreshThreadSummaries() {
    // Provider refreshes summaries when thread state changes.
  }

  function activateThread(nextThread: AgentInteractionThread | null) {
    setActiveTurnId(nextThread?.uiState?.scrollAnchorTurnId ?? nextThread?.turns[0]?.turnId ?? null);
    resetSourceReader();
    setTurnResponses({});
    setAskStatus("idle");
  }

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setStatus("loading");
    setError(null);
    (async () => {
      try {
        const response = await loadBundle("campaign-ingested", sessionDescriptor.campaignId);
        if (!cancelled) {
          setBundle(response);
          setStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Unable to load source bundle");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, loadBundle, sessionDescriptor.campaignId]);

  function clearHistory() {
    if (thread) {
      agentInteraction.clearThread();
      const nextThread = {
        ...thread,
        turns: [],
        updatedAt: new Date().toISOString(),
        uiState: {
          ...thread.uiState,
          scrollAnchorTurnId: null,
          traceVisible,
          newThreadSuggestionDismissed: false,
        },
      };
      setThread(nextThread);
      refreshThreadSummaries();
    }
    setActiveTurnId(null);
    setAskStatus("idle");
    resetSourceReader();
  }

  function createNewThread() {
    const nextThread = createAgentInteractionThread(
      sessionDescriptor.campaignId,
      querySession,
      "plan",
      "hermes",
      "New prep thread",
      planningDocumentId,
    );
    agentInteraction.updateThread(nextThread);
    activateThread(nextThread);
    setThreadSwitcherOpen(false);
  }

  function dismissNewThreadSuggestion() {
    if (!thread) return;
    const nextThread: AgentInteractionThread = {
      ...thread,
      updatedAt: new Date().toISOString(),
      uiState: {
        traceVisible,
        scrollAnchorTurnId: thread.uiState?.scrollAnchorTurnId ?? activeTurnId,
        newThreadSuggestionDismissed: true,
      },
    };
    setThread(nextThread);
  }

  function switchThread(threadId: string) {
    const nextThread = agentInteraction.switchThread(threadId);
    if (!nextThread) return;
    activateThread(nextThread);
    setThreadSwitcherOpen(false);
  }

  function saveRename() {
    const baseThread = thread ?? createAgentInteractionThread(
      sessionDescriptor.campaignId,
      querySession,
      "plan",
      "hermes",
      "New prep thread",
      planningDocumentId,
    );
    const nextThread = agentInteraction.renameThread(titleDraft) ?? baseThread;
    activateThread(nextThread);
    setRenaming(false);
  }

  function deleteThread(threadId: string) {
    agentInteraction.deleteThread(threadId);
    activateThread(agentInteraction.activeThread);
  }


  async function checkCurrentSourceState(turnId = activeTurnId) {
    const targetTurn = turns.find((turn) => turn.turnId === turnId) ?? activeTurn;
    if (!targetTurn) return;
    const snapshots = targetTurn.evidenceSnapshots ?? [];
    if (!snapshots.length) return;
    setFreshnessChecking(true);
    try {
      const results: CitationFreshnessResponse[] = [];
      for (const snapshot of snapshots) {
        results.push(await checkCitationFreshness({
          path: snapshot.path,
          line_start: snapshot.line_start ?? null,
          line_end: snapshot.line_end ?? null,
          expected_fingerprint: snapshot.fingerprint_algorithm === "sha256:source-lines-v1" ? snapshot.fingerprint : null,
          fingerprint_algorithm: snapshot.fingerprint_algorithm === "sha256:source-lines-v1" ? snapshot.fingerprint_algorithm : null,
        }));
      }
      const rank = { current: 0, unknown: 1, unavailable: 2, changed: 3 } as const;
      const status = results.reduce((worst, result) => rank[result.status] > rank[worst] ? result.status : worst, "current" as CitationFreshnessResponse["status"]);
      const nextTurns: AgentInteractionTurn[] = turns.map((turn) => turn.turnId === targetTurn.turnId ? {
        ...turn,
        corpusFreshness: {
          status,
          checked_at: new Date().toISOString(),
          diagnostics: results.flatMap((result) => result.diagnostics ?? []),
          warnings: results.flatMap((result) => result.warnings ?? []),
        },
      } : turn);
      setTurns(nextTurns);
      if (thread) {
        const nextThread = { ...thread, turns: nextTurns, updatedAt: new Date().toISOString() };
        setThread(nextThread);
      }
    } catch {
      const nextTurns: AgentInteractionTurn[] = turns.map((turn) => turn.turnId === targetTurn.turnId ? {
        ...turn,
        corpusFreshness: { status: "unavailable" as const, checked_at: new Date().toISOString(), diagnostics: [], warnings: ["citation freshness check failed"] },
      } : turn);
      setTurns(nextTurns);
    } finally {
      setFreshnessChecking(false);
    }
  }

  async function openCitationSource(turnId: string, card: EvidenceCard) {
    setActiveTurnId(turnId);
    if (thread) {
      setThread({
        ...thread,
        uiState: { ...thread.uiState, scrollAnchorTurnId: turnId, traceVisible },
      });
    }
    setSelectedCitationKey(citationKey(card.path, card.evidenceId));
    setSourceStatus("loading");
    setSourceError(null);
    setSourceResponse(null);
    setGraphReadStatus("idle");
    setGraphReadError(null);
    setGraphReadResponse(null);
    setGraphReadWarnings([]);
    try {
      const response = await readCitationSource({
        path: card.path,
        line_start: card.lineStart,
        line_end: card.lineEnd,
        text_excerpt: card.textExcerpt,
      });
      setSourceResponse(response);
      setSourceStatus("ready");
    } catch (loadError) {
      setSourceStatus("error");
      setSourceError(loadError instanceof Error ? loadError.message : "Unable to read citation source");
    }
  }

  async function openGraphCitationSource(turnId: string, citation: WorldGraphAnchorCitation) {
    setActiveTurnId(turnId);
    if (thread) {
      setThread({
        ...thread,
        uiState: { ...thread.uiState, scrollAnchorTurnId: turnId, traceVisible },
      });
    }
    setSelectedCitationKey(graphCitationKey(citation));
    setGraphReadStatus("loading");
    setGraphReadError(null);
    setGraphReadResponse(null);
    setGraphReadWarnings([]);
    setSourceStatus("idle");
    setSourceError(null);
    setSourceResponse(null);
    try {
      const response = await readGraphSourceAnchor({
        schema: "dmb_world_graph_source_anchor_read_request_v1",
        worldId: citation.world_id,
        campaignId: citation.campaign_id,
        focus: {
          kind: citation.focus.kind,
          sessionId: citation.focus.session_id ?? null,
        },
        admissibility: citation.admissibility,
        revisionPin: citation.revision_id,
        anchorId: citation.anchor_id,
        maxChars: 4000,
      });
      const validated = validateGraphSourceAnchorRead(citation, response);
      if (!validated.ok) {
        setGraphReadStatus("contract_error");
        setGraphReadError(validated.reason);
        return;
      }
      setGraphReadResponse(validated.response);
      setGraphReadWarnings(
        validated.response.diagnostics
          .map((item) => item.message)
          .filter(Boolean),
      );
      setGraphReadStatus("ready");
    } catch (loadError) {
      setGraphReadStatus("error");
      setGraphReadError(loadError instanceof Error ? loadError.message : "Unable to read graph source anchor");
    }
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (
      !trimmed
      || askStatus === "asking"
      || !derived
      || focusValidationPending
      || !planWorldGraphContext
    ) {
      return;
    }
    setAskStatus("asking");
    setAskError(null);
    try {
      const currentThread = thread ?? createAgentInteractionThread(
        sessionDescriptor.campaignId,
        querySession,
        "plan",
        "hermes",
        threadTitleFromQuestion(trimmed),
        planningDocumentId,
      );
      // Outer campaign/session must match the loaded live packet (Plan descriptor).
      // Graph lens campaign + scopeMode live only in worldGraphContext.
      const response = await askCorpus(
        trimmed,
        sessionDescriptor.campaignId,
        querySession,
        "hermes",
        {
          agentThreadId: currentThread.threadId,
          traceRequested: currentThread.uiState?.traceVisible ?? false,
          worldGraphContext: projectionState !== "loading"
            ? buildPlanAgentWorldGraphQueryContextRequest(planWorldGraphContext, {
                revisionPin: projection?.snapshot.revisionId ?? null,
              })
            : null,
          conversationHistory: buildHermesConversationHistory(currentThread.turns),
          hermesSessionPointer: currentThread.hermesSession?.sessionId ?? null,
        },
      );
      const nextTurn = turnFromResponse(trimmed, response, "hermes");
      const nextTurns = [nextTurn, ...turns].slice(0, AGENT_TURN_HISTORY_CAP);
      const isHermesGraphAgentTurn = response.mode === "hermes_graph_agent"
        || response.agent_trace?.mode === "hermes_graph_agent";
      const nextThread: AgentInteractionThread = {
        ...currentThread,
        documentId: currentThread.documentId ?? planningDocumentId,
        threadId: response.agent_thread_id ?? currentThread.threadId,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(trimmed),
        updatedAt: new Date().toISOString(),
        activeBackend: "hermes",
        hermesSession: isHermesGraphAgentTurn
          ? (response.hermes_session ?? currentThread.hermesSession ?? null)
          : (response.hermes_session ?? currentThread.hermesSession ?? null),
        turns: nextTurns,
        uiState: {
          traceVisible: currentThread.uiState?.traceVisible ?? false,
          scrollAnchorTurnId: nextTurn.turnId,
          newThreadSuggestionDismissed: currentThread.uiState?.newThreadSuggestionDismissed ?? false,
        },
      };
      setThread(nextThread);
      setActiveTurnId(nextTurn.turnId);
      resetSourceReader();
      setTurnResponses((previous) => ({ ...previous, [nextTurn.turnId]: response }));
      
      setQuestion("");
      setAskStatus("answered");
    } catch (loadError) {
      setAskStatus("error");
      setAskError(loadError instanceof Error ? loadError.message : "Unable to ask corpus");
    }
  }

  const coverage = bundle?.coverage ?? {};
  const unitCount = numberField(coverage.unitCount) ?? bundle?.units?.length ?? 0;
  const artifactCount = numberField(coverage.artifactCount) ?? bundle?.artifacts?.length ?? 0;
  const routesOnDisk = numberField(coverage.ingestRoutesOnDisk);
  const dogfoodRoutes = numberField(coverage.ingestRoutesInDogfoodFullManifest);
  const slimRoutes = numberField(coverage.ingestRoutesInC2S23Manifest);
  const activeSessionUnits = bundle ? unitsForSession(bundle, querySession) : [];
  const activeStageKinds = new Set(activeSessionUnits.map(sourceKind));
  const missingStages = REQUIRED_INGEST_STAGES.filter((stage) => !activeStageKinds.has(stage));
  const activeSessionComplete = bundle ? missingStages.length === 0 : false;
  const latestSessions = bundle ? sessionNumbers(bundle).slice(0, 5) : [];

  // R10b: shell/bar live in AgentInteractionChrome; this component is the Plan Ask plugin.
  const askPane = (
        <div className="plan-agent-pane" role="complementary" aria-label="Ask DungeonBuddy">
          <header className="plan-agent-pane-header">
            <div>
              {renaming ? (
                <div className="plan-agent-title-editor">
                  <label>
                    <span>Prep thread title</span>
                    <input value={titleDraft} onChange={(event) => setTitleDraft(event.currentTarget.value)} />
                  </label>
                  <button type="button" onClick={saveRename}>Save title</button>
                  <button type="button" onClick={() => setRenaming(false)}>Cancel</button>
                </div>
              ) : (
                <h2>{threadTitle}</h2>
              )}
              <p>{summaryLabel}</p>
            </div>
            <div className="plan-agent-pane-actions">
              <div className="plan-agent-config-menu">
                <button
                  type="button"
                  aria-expanded={configMenuOpen}
                  aria-controls="plan-agent-config-panel"
                  onClick={() => setConfigMenuOpen((value) => !value)}
                >
                  Config
                </button>
                {configMenuOpen ? (
                  <div
                    id="plan-agent-config-panel"
                    className="plan-agent-config-panel"
                    role="region"
                    aria-label="Agent configuration"
                  >
                    <div className="plan-agent-config-actions">
                      <button
                        type="button"
                        onClick={() => {
                          setTitleDraft(threadTitle);
                          setRenaming(true);
                          setConfigMenuOpen(false);
                        }}
                      >
                        Rename thread
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          createNewThread();
                          setConfigMenuOpen(false);
                        }}
                      >
                        New prep thread
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setThreadSwitcherOpen((value) => !value);
                          setConfigMenuOpen(false);
                        }}
                      >
                        Prep threads
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const baseThread = thread ?? createAgentInteractionThread(
                            sessionDescriptor.campaignId,
                            querySession,
                            "plan",
                            "hermes",
                            "New prep thread",
                            planningDocumentId,
                          );
                          const nextThread = {
                            ...baseThread,
                            uiState: {
                              ...baseThread.uiState,
                              traceVisible: !traceVisible,
                            },
                          };
                          setThread(nextThread);
                        }}
                      >
                        {traceVisible ? "Trace On" : "Trace Off"}
                      </button>
                      <button
                        type="button"
                        onClick={clearHistory}
                        disabled={!turns.length}
                      >
                        Clear history
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close Ask DungeonBuddy">
                Close
              </button>
            </div>
          </header>
          {threadSwitcherOpen ? (
            <section className="plan-agent-thread-switcher" aria-label="DungeonBuddy threads">
              <h3>Prep threads</h3>
              {threadSummaries.length ? (
                <ul>
                  {threadSummaries.map((summary) => (
                    <li key={summary.threadId} data-active={summary.threadId === thread?.threadId}>
                      <button type="button" onClick={() => switchThread(summary.threadId)}>
                        <strong>{summary.title}</strong>
                        <span>{summary.turnCount} turns · updated {new Date(summary.updatedAt).toLocaleString()}</span>
                      </button>
                      <button type="button" onClick={() => deleteThread(summary.threadId)} aria-label={`Delete ${summary.title}`}>
                        Delete
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="plan-agent-muted">No saved prep threads yet.</p>
              )}
            </section>
          ) : null}

          <div className="plan-agent-content">
            {showNewThreadSuggestion ? (
              <section className="plan-agent-thread-suggestion" aria-label="Thread getting long">
                <div>
                  <p className="plan-surface-kicker">Thread getting long</p>
                  <p>
                    This thread has {turns.length} turns. Start a new prep thread for a fresh topic?
                  </p>
                </div>
                <div>
                  <button type="button" onClick={createNewThread}>Start new thread</button>
                  <button type="button" onClick={dismissNewThreadSuggestion}>Keep going</button>
                </div>
              </section>
            ) : null}

            {turns.length ? (
              <section className="plan-agent-transcript" aria-label="Conversation transcript">
                <div className="plan-agent-transcript-scroll">
                  {chronologicalTurns.map((turn) => {
                    const wire = turnResponses[turn.turnId];
                    const turnAnswer = liveQueryResponseFromTurn(turn, wire);
                    const turnS1Support = s1SupportFromTurn(turn, wire);
                    const turnPacketReview = buildPacketReview(turnAnswer);
                    const turnCitationCards = evidenceCardsFromAnswer(turnAnswer);
                    const turnHermesCitationValidation = isHermesGraphAgentResponse(turnAnswer)
                      ? validateHermesGraphCitations(
                          wire?.citations ?? turnAnswer.citations,
                          wire?.grounding ?? turnAnswer.grounding,
                        )
                      : { citations: [] as WorldGraphAnchorCitation[], contractWarning: null as string | null };
                    const turnGraphCitationCards = turnHermesCitationValidation.citations;
                    const turnHermesGrounding = parseHermesGraphGroundingView(turnAnswer);
                    const turnIsConversationContext = turnHermesGrounding.kind === "valid"
                      && isConversationContext(turnHermesGrounding.grounding);
                    const turnCorpusFreshness = turn.corpusFreshness ?? null;
                    const turnCorpusSignalStatus = turnCorpusFreshness?.status
                      ?? (turn.evidenceSnapshots?.length ? "unknown" : "unknown");
                    const isInspectedTurn = activeTurnId === turn.turnId;

                    return (
                      <article
                        key={turn.turnId}
                        className="plan-agent-transcript-turn"
                        data-turn-id={turn.turnId}
                        data-active={isInspectedTurn}
                      >
                        <div className="plan-agent-chat-row plan-agent-chat-row-user">
                          <div className="plan-agent-chat-bubble plan-agent-chat-bubble-user">
                            <p className="plan-surface-kicker">You</p>
                            <p>{turn.question}</p>
                          </div>
                        </div>
                        <div className="plan-agent-chat-row plan-agent-chat-row-assistant">
                          <div
                            className="plan-agent-chat-bubble plan-agent-chat-bubble-assistant"
                            role="region"
                            aria-label="Hermes reply"
                          >
                            <p className="plan-surface-kicker">Hermes</p>
                            <p className="plan-agent-chat-answer">{turn.answer}</p>
                          </div>
                        </div>
                        {turnS1Support ? (
                          <details className="plan-agent-s1-support">
                            <summary>Latest-recap comparison support</summary>
                            {turnS1Support.lagDisclosure ? (
                              <p className="plan-agent-s1-support-lag">{turnS1Support.lagDisclosure}</p>
                            ) : null}
                            {turnS1Support.admittedRecapExcerpt ? (
                              <pre className="plan-agent-s1-support-excerpt">
                                {turnS1Support.admittedRecapExcerpt}
                              </pre>
                            ) : null}
                          </details>
                        ) : null}
                        <details
                          className="plan-agent-turn-inspection"
                          open={false}
                        >
                          <summary>Evidence and diagnostics</summary>
                          <div className="plan-agent-answer">
                          {turnIsConversationContext ? (
                            <p className="plan-agent-conversation-context-note">
                              Hermes answered from this conversation&rsquo;s visible history —
                              no World Graph query was needed for this turn.
                            </p>
                          ) : (
                            <>
                            {!isHermesGraphAgentResponse(turnAnswer) && !hasGrounding(turnAnswer) ? (
                              <p className="plan-agent-grounding-warning">
                                {UNGROUNDED_ANSWER_WARNING}
                              </p>
                            ) : null}
                            {turnHermesCitationValidation.contractWarning ? (
                              <p className="plan-agent-error">{turnHermesCitationValidation.contractWarning}</p>
                            ) : null}
                            {turnHermesGrounding.kind === "malformed" ? (
                              <p className="plan-agent-error">{turnHermesGrounding.reason}</p>
                            ) : null}
                            {turnHermesGrounding.kind === "valid" && turnHermesGrounding.grounding.state === "error" ? (
                              <div className="plan-agent-graph-grounding-error">
                                {turnHermesGrounding.grounding.diagnostic_codes.length ? (
                                  <ul>
                                    {turnHermesGrounding.grounding.diagnostic_codes.map((code) => (
                                      <li key={code}><code>{code}</code></li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="plan-agent-muted">Hermes graph query failed without diagnostic codes.</p>
                                )}
                              </div>
                            ) : null}
                            {turnHermesGrounding.kind === "valid"
                              && turnHermesGrounding.grounding.state === "partial"
                              && turnHermesGrounding.grounding.warnings.length ? (
                              <ul className="plan-agent-graph-grounding-warnings">
                                {turnHermesGrounding.grounding.warnings.map((warning) => (
                                  <li key={warning}>{warning}</li>
                                ))}
                              </ul>
                            ) : null}
                            {turn.trace && traceVisible ? (
                              <TraceDetailsPanel
                                trace={turn.trace}
                                question={turn.question}
                                answer={turn.answer}
                              />
                            ) : null}
                            <RetrievalFreshnessPanel decision={turnAnswer.retrieval_freshness} />
                            <WorldGraphQueryContextPanel
                              context={wire?.world_graph_context ?? turn.worldGraphContext ?? null}
                              summary={turn.worldGraphContextSummary}
                              grounding={wire?.grounding ?? turn.grounding ?? null}
                              retrievalSessionId={
                                wire?.retrieval_session_id
                                ?? turn.worldGraphContextSummary?.retrievalSessionId
                                ?? null
                              }
                              graphReferences={wire?.graph_references ?? null}
                              sourceCitations={wire?.source_citations ?? null}
                              persistedOnly={
                                !wire?.world_graph_context
                                && !turn.worldGraphContext
                                && Boolean(turn.worldGraphContextSummary)
                              }
                            />
                            {turnHasLegacyPathEvidence(turn) ? (
                              <CorpusChangeSignalPanel
                                status={turnCorpusSignalStatus}
                                snapshotCount={turn.evidenceSnapshots?.length ?? 0}
                                checkedAt={turnCorpusFreshness?.checked_at ?? null}
                                warnings={turnCorpusFreshness?.warnings ?? []}
                                checking={freshnessChecking && isInspectedTurn}
                                onCheck={() => void checkCurrentSourceState(turn.turnId)}
                              />
                            ) : null}
                            {turnGraphCitationCards.length ? (
                              <section className="plan-agent-graph-citation-cards" aria-label="Graph evidence">
                                <h4>Graph evidence</h4>
                                <ul>
                                  {turnGraphCitationCards.map((citation, index) => (
                                    <li
                                      key={graphCitationKey(citation)}
                                      data-selected={isInspectedTurn && selectedCitationKey === graphCitationKey(citation)}
                                    >
                                      <strong>Graph evidence {index + 1}</strong>
                                      <details className="plan-agent-graph-anchor-id">
                                        <summary><code>{shortenAnchorId(citation.anchor_id)}</code></summary>
                                        <code>{citation.anchor_id}</code>
                                      </details>
                                      <span className="plan-agent-muted plan-agent-graph-revision">
                                        Pinned revision · <code>{citation.revision_id}</code>
                                      </span>
                                      <button
                                        type="button"
                                        onClick={() => void openGraphCitationSource(turn.turnId, citation)}
                                      >
                                        Open evidence
                                      </button>
                                    </li>
                                  ))}
                                </ul>
                              </section>
                            ) : null}
                            {turnCitationCards.length ? (
                              <details className="plan-agent-metadata-drawer">
                                <summary>Supporting sources ({turnCitationCards.length})</summary>
                                <section className="plan-agent-citation-cards" aria-label="Supporting sources">
                                  <h4>Supporting sources</h4>
                                  <ul>
                                    {turnCitationCards.map((card) => (
                                      <li
                                        key={`${card.path}-${card.evidenceId}`}
                                        data-selected={
                                          isInspectedTurn
                                          && selectedCitationKey === citationKey(card.path, card.evidenceId)
                                        }
                                      >
                                        <strong>{card.sourceRole} · {card.authority} · {card.lineLabel}</strong>
                                        <span className="plan-agent-muted">{card.evidenceId}</span>
                                        <code>{card.path}</code>
                                        {card.textExcerpt ? <p>{card.textExcerpt}</p> : null}
                                        <button
                                          type="button"
                                          onClick={() => void openCitationSource(turn.turnId, card)}
                                        >
                                          Open source
                                        </button>
                                      </li>
                                    ))}
                                  </ul>
                                </section>
                              </details>
                            ) : null}
                            {isInspectedTurn && graphReadStatus !== "idle" ? (
                              <section className="plan-agent-graph-source-reader" aria-label="Graph evidence preview">
                                <div>
                                  <p className="plan-surface-kicker">Graph evidence preview</p>
                                  <h4>
                                    {graphReadStatus === "loading"
                                      ? "Loading graph evidence…"
                                      : graphReadResponse?.anchorId ?? "Graph evidence unavailable"}
                                  </h4>
                                </div>
                                {graphReadStatus === "loading" ? (
                                  <p className="plan-agent-muted">Reading pinned source anchor…</p>
                                ) : null}
                                {graphReadStatus === "error" ? (
                                  <p className="plan-agent-error">{graphReadError ?? "Unable to read graph source anchor."}</p>
                                ) : null}
                                {graphReadStatus === "contract_error" ? (
                                  <p className="plan-agent-error">{graphReadError ?? "Graph source-anchor contract error."}</p>
                                ) : null}
                                {graphReadStatus === "ready" && graphReadResponse ? (
                                  <>
                                    {graphReadWarnings.length ? (
                                      <ul className="plan-agent-graph-read-warnings">
                                        {graphReadWarnings.map((warning) => (
                                          <li key={warning}>{warning}</li>
                                        ))}
                                      </ul>
                                    ) : null}
                                    {graphSourceAnchorHasContent(
                                      graphReadResponse.outcome,
                                      graphReadResponse.content,
                                    ) ? (
                                      <pre>{graphReadResponse.content}</pre>
                                    ) : (
                                      <p className="plan-agent-muted plan-agent-graph-read-empty">
                                        {graphReadResponse.outcome === "empty"
                                          ? "No content at this pinned source anchor."
                                          : graphReadResponse.outcome === "denied"
                                            ? "Source anchor read denied for this admissibility scope."
                                            : graphReadResponse.outcome === "unavailable"
                                              ? "Source anchor content is unavailable."
                                              : graphReadResponse.outcome === "partial"
                                                ? "Qualified source-anchor read returned no readable content."
                                                : "No readable content returned for this source anchor."}
                                      </p>
                                    )}
                                  </>
                                ) : null}
                              </section>
                            ) : null}
                            {isInspectedTurn && sourceStatus !== "idle" ? (
                              <section className="plan-agent-source-reader" aria-label="Source preview">
                                <div>
                                  <p className="plan-surface-kicker">Source preview</p>
                                  <h4>
                                    {sourceStatus === "loading"
                                      ? "Loading source…"
                                      : sourceResponse?.path ?? "Source unavailable"}
                                  </h4>
                                  {sourceResponse ? <code>{sourceResponse.path}</code> : null}
                                </div>
                                {sourceStatus === "loading" ? (
                                  <p className="plan-agent-muted">Reading current source content…</p>
                                ) : null}
                                {sourceStatus === "error" ? (
                                  <p className="plan-agent-error">{sourceError ?? "Unable to read citation source."}</p>
                                ) : null}
                                {sourceResponse ? (
                                  <pre>{renderSourceWithHighlight(sourceResponse)}</pre>
                                ) : null}
                              </section>
                            ) : null}
                            {turnPacketReview ? (
                              <ContextSufficiencyPanel review={turnPacketReview} />
                            ) : null}
                            {!turnPacketReview && !turn.trace ? (
                              <p className="plan-agent-muted">No trace or context packet returned.</p>
                            ) : null}
                            {turnAnswer.citations?.length ? (
                              <p className="plan-agent-muted plan-agent-citation-count">
                                Citations returned: {turnAnswer.citations.length}
                              </p>
                            ) : null}
                            </>
                          )}
                          </div>
                        </details>
                      </article>
                    );
                  })}
                </div>
              </section>
            ) : null}

            <details className="plan-agent-diagnostics-drawer">
              <summary>Memory coverage diagnostics</summary>
              {status === "loading" ? <p className="plan-agent-muted">Loading source bundle…</p> : null}
              {status === "error" ? (
                <p className="plan-agent-error">{error ?? "Unable to load source bundle."}</p>
              ) : null}
              {bundle ? (
                <>
                <section className="plan-agent-proof" aria-label="Ingestion proof">
                  <div>
                    <p className="plan-surface-kicker">Ingestion proof</p>
                    <h3>
                      {activeSessionComplete
                        ? `Session ${querySession} has all expected ingest layers`
                        : `Session ${querySession} is missing ${missingStages.length} ingest layers`}
                    </h3>
                    <p>
                      The bundle exposes {unitCount} SourceUnits across {artifactCount} artifacts.
                      Latest sessions visible in the scan:{" "}
                      {latestSessions.length ? latestSessions.join(", ") : "none"}.
                    </p>
                    {!activeSessionComplete ? (
                      <p className="plan-agent-warning">Missing: {missingStages.join(", ")}</p>
                    ) : null}
                  </div>
                  <div className="plan-agent-proof-pills">
                    {REQUIRED_INGEST_STAGES.map((stage) => (
                      <span key={stage} data-present={activeStageKinds.has(stage)}>
                        {stage.replaceAll("_", " ")}
                      </span>
                    ))}
                  </div>
                </section>

                <div className="plan-agent-proof-grid">
                  <div className="plan-agent-stat">
                    <span>Ingest routes</span>
                    <strong>{routesOnDisk ?? "n/a"}</strong>
                  </div>
                  <div className="plan-agent-stat">
                    <span>Dogfood-full overlap</span>
                    <strong>{dogfoodRoutes ?? "n/a"}</strong>
                  </div>
                  <div className="plan-agent-stat">
                    <span>Slim overlap</span>
                    <strong>{slimRoutes ?? "n/a"}</strong>
                  </div>

                  <div className="plan-agent-units">
                    <h3>Representative SourceUnits</h3>
                    <ul>
                      {representativeUnits(bundle, querySession).map((unit) => (
                        <li key={unit.unitId}>
                          <strong>{unit.label}</strong>
                          <span>
                            {sourceKind(unit)} · {unit.authorityState} · {unit.evidenceRole} ·{" "}
                            <code>{unit.sourceAnchor.locator.value}</code>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="plan-agent-diagnostics">
                    <h3>Diagnostics</h3>
                    <ul>
                      {bundle.diagnostics.map((diagnostic) => (
                        <li key={diagnostic}>{diagnostic}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                </>
              ) : null}
            </details>
          </div>

          <form className="plan-agent-ask" onSubmit={submitQuestion}>
            <label>
              <span className="sr-only">Question</span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.currentTarget.value)}
                placeholder="Ask about campaign memory…"
                rows={1}
              />
            </label>
            {focusValidationStatus === "unavailable" ? (
              <p className="plan-agent-muted">
                Session focus validation unavailable — retry or clear focus on Plan Board.
              </p>
            ) : focusValidationPending ? (
              <p className="plan-agent-muted">Validating session focus…</p>
            ) : graphContextInitializing ? (
              <p className="plan-agent-muted">Initializing world graph context…</p>
            ) : null}
            {hasSupportedGraphContext && projectionState === "error" ? (
              <p className="plan-agent-warning">
                World graph projection error: {projectionError ?? "unknown error"}.
                The server will resolve the authoritative revision for Hermes graph queries.
              </p>
            ) : null}
            {derived == null ? (
              <p className="plan-agent-warning">Select at least one campaign on Plan Board.</p>
            ) : null}
            <button
              type="submit"
              disabled={
                !question.trim()
                || askStatus === "asking"
                || graphContextInitializing
                || !lensAllowsAsk
              }
            >
              {askStatus === "asking" ? "Asking…" : "Ask DungeonBuddy"}
            </button>
            {askStatus === "error" ? (
              <p className="plan-agent-error">{askError ?? "Unable to ask corpus."}</p>
            ) : null}
          </form>
        </div>
  );

  if (askSlot?.hostElement) {
    return createPortal(askPane, askSlot.hostElement);
  }

  // Test / no-chrome fallback: render the Ask pane only when already open.
  if (open) {
    return (
      <section
        className="plan-agent-shell open"
        aria-label="Ask DungeonBuddy"
        data-expanded="true"
        data-testid="plan-ask-fallback-shell"
      >
        {askPane}
      </section>
    );
  }

  return null;
}
