import { useEffect, useMemo, useState, type FormEvent } from "react";

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
  LiveQueryBackend,
  LiveQueryResponse,
  PlanViewProjection,
  SourceUnit,
  WorldGraphAnchorCitation,
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
import {
  PREP_MEMORY_PROMPTS,
  answerHeading,
  hasGrounding,
  isHermesGraphAgentResponse,
  parseHermesGraphGrounding,
  prepMemoryLabel,
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
  const candidate = citation as LegacyPathCitation;
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
): { kind: string; sessionId: string | null } | null {
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
  return bundle.units
    .filter((unit) => unit.evidenceRole !== "diagnostic_only")
    .filter((unit) => numberField(unit.fields.sessionNumber) === session);
}

function representativeUnits(bundle: IngestionSourceBundle, activeSession: number): SourceUnit[] {
  const activeSessionUnits = unitsForSession(bundle, activeSession);
  const fallbackUnits = bundle.units.filter((unit) => unit.evidenceRole !== "diagnostic_only");
  return (activeSessionUnits.length ? activeSessionUnits : fallbackUnits).slice(0, 8);
}

function sessionNumbers(bundle: IngestionSourceBundle): number[] {
  const sessions = new Set<number>();
  for (const unit of bundle.units) {
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
  const { projection, projectionState, projectionError } = usePlanGraphReferenceResolver();
  const planWorldGraphContext = getPlanWorldGraphContext(sessionDescriptor);
  const hasSupportedGraphContext = planWorldGraphContext != null;
  const graphContextInitializing = hasSupportedGraphContext && projectionState === "loading";
  const open = agentInteraction.paneState.isOpen;
  const setOpen = agentInteraction.setPaneOpen;
  const [status, setStatus] = useState<BundleStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<IngestionSourceBundle | null>(null);
  const [question, setQuestion] = useState("");
  const [queryBackend, setQueryBackend] = useState<LiveQueryBackend>("live");
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
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [freshnessChecking, setFreshnessChecking] = useState(false);

  const memorySessionLabel = prepMemoryLabel(sessionDescriptor);
  // Outer /api/live/query must match the loaded live packet session (liveSession),
  // not memorySession (packet-1). World-graph focus still uses memorySession via planWorldGraphContext.
  const querySession = sessionDescriptor.liveSession;

  useEffect(() => {
    agentInteraction.rehydrateScope({
      campaignId: sessionDescriptor.campaignId,
      sessionNumber: sessionDescriptor.prepSession,
      surfaceId: "plan",
    });
    agentInteraction.publishSurfaceContext({
      surfaceId: "plan",
      label: `Plan · Session ${sessionDescriptor.prepSession}`,
      campaignId: sessionDescriptor.campaignId,
      sessionNumber: sessionDescriptor.prepSession,
      ambientSummary: `Plan prep for ${sessionDescriptor.campaignLabel}, ${memorySessionLabel}`,
      sourceEnvelope: null,
      updatedAt: new Date().toISOString(),
    });
  }, [
    sessionDescriptor.campaignId,
    sessionDescriptor.campaignLabel,
    sessionDescriptor.prepSession,
    memorySessionLabel,
  ]);

  useEffect(() => {
    if (!thread) {
      setActiveTurnId(null);
      return;
    }
    setActiveTurnId(thread.uiState?.scrollAnchorTurnId ?? thread.turns[0]?.turnId ?? null);
    setQueryBackend(thread.activeBackend);
  }, [thread]);

  const activeTurn = useMemo(
    () => turns.find((turn) => turn.turnId === activeTurnId) ?? turns[0] ?? null,
    [turns, activeTurnId],
  );
  const answer = activeTurn ? (() => {
    const fromTurn = {
      answer: activeTurn.answer,
      status: activeTurn.status,
      mode: activeTurn.trace?.mode
        ?? (activeTurn.grounding?.schema === "dmb_hermes_graph_grounding_v1" ? "hermes_graph_agent" : undefined),
      citations: activeTurn.citations ?? [],
      warnings: activeTurn.warnings ?? [],
      agent_trace: activeTurn.trace ?? null,
      context_packet: null,
      classification: {} as never,
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: {},
      retrieval_freshness: activeTurn.retrievalFreshness ?? null,
      grounding: activeTurn.grounding ?? null,
      world_graph_context: activeTurn.worldGraphContext ?? null,
    } satisfies LiveQueryResponse;
    const wire = turnResponses[activeTurn.turnId];
    if (!wire) return fromTurn;
    // Keep wire-only fields (context packet, diagnostics), but never prefer raw
    // grounding / citations / warnings / agent_trace over the sanitized turn.
    return {
      ...wire,
      answer: activeTurn.answer,
      status: activeTurn.status,
      citations: activeTurn.citations ?? [],
      warnings: activeTurn.warnings ?? [],
      agent_trace: activeTurn.trace ?? null,
      grounding: activeTurn.grounding ?? null,
      retrieval_freshness: activeTurn.retrievalFreshness ?? wire.retrieval_freshness ?? null,
    };
  })() : null;
  const packetReview = answer ? buildPacketReview(answer) : null;
  const citationCards = answer ? evidenceCardsFromAnswer(answer) : [];
  const hermesCitationValidation = answer && isHermesGraphAgentResponse(answer)
    ? validateHermesGraphCitations(
        // Prefer wire citations/grounding so drop warnings remain visible after
        // turnFromResponse has already filtered the persisted turn copy.
        (activeTurn ? turnResponses[activeTurn.turnId]?.citations : undefined) ?? answer.citations,
        (activeTurn ? turnResponses[activeTurn.turnId]?.grounding : undefined) ?? answer.grounding,
      )
    : { citations: [] as WorldGraphAnchorCitation[], contractWarning: null as string | null };
  const graphCitationCards = hermesCitationValidation.citations;
  const hermesGrounding = answer ? parseHermesGraphGroundingView(answer) : { kind: "none" as const };
  const answerHeadingLabel = answer ? answerHeading(answer) : "";
  const threadTitle = thread?.title ?? "New prep thread";
  const traceVisible = thread?.uiState?.traceVisible ?? false;
  const corpusFreshness = activeTurn?.corpusFreshness ?? null;
  const corpusSignalStatus = corpusFreshness?.status ?? (activeTurn?.evidenceSnapshots?.length ? "unknown" : "unknown");

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
    if (nextThread) setQueryBackend(nextThread.activeBackend);
    resetSourceReader();
    setTurnResponses({});
    setAskStatus("idle");
  }

  async function openPane() {
    setOpen(true);
    if (bundle || status === "loading") return;
    setStatus("loading");
    setError(null);
    try {
      const response = await loadBundle("campaign-ingested", sessionDescriptor.campaignId);
      setBundle(response);
      setStatus("ready");
    } catch (loadError) {
      setStatus("error");
      setError(loadError instanceof Error ? loadError.message : "Unable to load source bundle");
    }
  }

  async function toggleDrawer() {
    if (open) {
      setOpen(false);
      return;
    }
    await openPane();
  }

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
      queryBackend,
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
  }

  function saveRename() {
    const baseThread = thread ?? createAgentInteractionThread(
      sessionDescriptor.campaignId,
      querySession,
      "plan",
      queryBackend,
    );
    const nextThread = agentInteraction.renameThread(titleDraft) ?? baseThread;
    activateThread(nextThread);
    setRenaming(false);
  }

  function deleteThread(threadId: string) {
    agentInteraction.deleteThread(threadId);
    activateThread(agentInteraction.activeThread);
  }


  async function checkCurrentSourceState() {
    if (!activeTurn) return;
    const snapshots = activeTurn.evidenceSnapshots ?? [];
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
      const nextTurns: AgentInteractionTurn[] = turns.map((turn) => turn.turnId === activeTurn.turnId ? {
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
      const nextTurns: AgentInteractionTurn[] = turns.map((turn) => turn.turnId === activeTurn.turnId ? {
        ...turn,
        corpusFreshness: { status: "unavailable" as const, checked_at: new Date().toISOString(), diagnostics: [], warnings: ["citation freshness check failed"] },
      } : turn);
      setTurns(nextTurns);
    } finally {
      setFreshnessChecking(false);
    }
  }

  async function openCitationSource(card: EvidenceCard) {
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

  async function openGraphCitationSource(citation: WorldGraphAnchorCitation) {
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
    if (!trimmed || askStatus === "asking") return;
    setAskStatus("asking");
    setAskError(null);
    try {
      const currentThread = thread ?? createAgentInteractionThread(
        sessionDescriptor.campaignId,
        querySession,
        "plan",
        queryBackend,
        threadTitleFromQuestion(trimmed),
      );
      const response = await askCorpus(
        trimmed,
        sessionDescriptor.campaignId,
        querySession,
        queryBackend,
        {
          agentThreadId: currentThread.threadId,
          ...(queryBackend === "live"
            ? { hermesSessionId: currentThread.hermesSession?.sessionId ?? null }
            : {}),
          traceRequested: currentThread.uiState?.traceVisible ?? false,
          worldGraphContext: planWorldGraphContext && projectionState !== "loading"
            ? buildPlanAgentWorldGraphQueryContextRequest(planWorldGraphContext, {
                revisionPin: projection?.snapshot.revisionId ?? null,
              })
            : null,
          ...(queryBackend === "hermes"
            ? {
                conversationHistory: buildHermesConversationHistory(currentThread.turns),
              }
            : {}),
        },
      );
      const nextTurn = turnFromResponse(trimmed, response, queryBackend);
      const nextTurns = [nextTurn, ...turns].slice(0, AGENT_TURN_HISTORY_CAP);
      const isHermesGraphAgentTurn = response.mode === "hermes_graph_agent"
        || response.agent_trace?.mode === "hermes_graph_agent";
      const nextThread: AgentInteractionThread = {
        ...currentThread,
        threadId: response.agent_thread_id ?? currentThread.threadId,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(trimmed),
        updatedAt: new Date().toISOString(),
        activeBackend: queryBackend,
        hermesSession: isHermesGraphAgentTurn
          ? null
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
  const unitCount = numberField(coverage.unitCount) ?? bundle?.units.length ?? 0;
  const artifactCount = numberField(coverage.artifactCount) ?? bundle?.artifacts.length ?? 0;
  const routesOnDisk = numberField(coverage.ingestRoutesOnDisk);
  const dogfoodRoutes = numberField(coverage.ingestRoutesInDogfoodFullManifest);
  const slimRoutes = numberField(coverage.ingestRoutesInC2S23Manifest);
  const activeSessionUnits = bundle ? unitsForSession(bundle, querySession) : [];
  const activeStageKinds = new Set(activeSessionUnits.map(sourceKind));
  const missingStages = REQUIRED_INGEST_STAGES.filter((stage) => !activeStageKinds.has(stage));
  const activeSessionComplete = bundle ? missingStages.length === 0 : false;
  const latestSessions = bundle ? sessionNumbers(bundle).slice(0, 5) : [];

  return (
    <section
      className={`plan-agent-shell ${open ? "open" : "closed"}`}
      aria-label="Ask prep memory"
    >
      {open ? (
        <div className="plan-agent-pane" role="complementary" aria-label="Prep memory drawer">
          <header className="plan-agent-pane-header">
            <div>
              <p className="plan-surface-kicker">Ask prep memory</p>
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
              <p>{memorySessionLabel}</p>
              <p>Ask grounded questions against reviewed campaign memory while writing prep.</p>
            </div>
            <div className="plan-agent-pane-actions">
              <button type="button" onClick={() => {
                setTitleDraft(threadTitle);
                setRenaming(true);
              }}>
                Rename
              </button>
              <button type="button" onClick={createNewThread}>New prep thread</button>
              <button type="button" onClick={() => setThreadSwitcherOpen((value) => !value)}>Prep threads</button>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close prep memory drawer">
                Close
              </button>
            </div>
          </header>
          {threadSwitcherOpen ? (
            <section className="plan-agent-thread-switcher" aria-label="Prep memory threads">
              <h3>Prep threads</h3>
              {threadSummaries.length ? (
                <ul>
                  {threadSummaries.map((summary) => (
                    <li key={summary.threadId} data-active={summary.threadId === thread?.threadId}>
                      <button type="button" onClick={() => switchThread(summary.threadId)}>
                        <strong>{summary.title}</strong>
                        <span>{summary.turnCount} turns · {summary.activeBackend} · updated {new Date(summary.updatedAt).toLocaleString()}</span>
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
            <form className="plan-agent-ask" onSubmit={submitQuestion}>
                <h3>Ask prep memory</h3>
                <fieldset className="plan-agent-backend-picker">
                  <legend>Answer mode</legend>
                  <label>
                    <input
                      type="radio"
                      name="plan-agent-query-backend"
                      value="live"
                      checked={queryBackend === "live"}
                      onChange={() => setQueryBackend("live")}
                    />
                    <span>Live retrieval</span>
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="plan-agent-query-backend"
                      value="hermes"
                      checked={queryBackend === "hermes"}
                      onChange={() => setQueryBackend("hermes")}
                    />
                    <span>Hermes tools</span>
                  </label>
                </fieldset>
                <div className="plan-agent-prompt-suggestions" aria-label="Suggested prep questions">
                  {PREP_MEMORY_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="plan-agent-prompt-suggestion"
                      onClick={() => setQuestion(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
                <label>
                  <span>Question</span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.currentTarget.value)}
                    placeholder="What should I remember about the North Gate pressure sequence?"
                    rows={3}
                  />
                </label>
                {graphContextInitializing ? (
                  <p className="plan-agent-muted">Initializing world graph context…</p>
                ) : null}
                {hasSupportedGraphContext && projectionState === "error" ? (
                  <p className="plan-agent-warning">
                    World graph projection error: {projectionError ?? "unknown error"}.
                    {queryBackend === "hermes"
                      ? " The server will resolve the authoritative revision for Hermes graph queries."
                      : " Query will continue with an unpinned revision."}
                  </p>
                ) : null}
                <button
                  type="submit"
                  disabled={!question.trim() || askStatus === "asking" || graphContextInitializing}
                >
                  {askStatus === "asking" ? "Asking…" : "Ask prep memory"}
                </button>
                {askStatus === "error" ? (
                  <p className="plan-agent-error">{askError ?? "Unable to ask corpus."}</p>
                ) : null}

                {turns.length ? (
                  <section className="plan-agent-history" aria-label="Conversation history">
                    <div className="plan-agent-history-header">
                      <h4>Conversation ({turns.length})</h4>
                      <button type="button" onClick={() => {
                        const baseThread = thread ?? createAgentInteractionThread(
                          sessionDescriptor.campaignId,
                          querySession,
                          "plan",
                          queryBackend,
                        );
                        const nextThread = { ...baseThread, uiState: { ...baseThread.uiState, traceVisible: !traceVisible } };
                        setThread(nextThread);
                      }}>{traceVisible ? "Trace On" : "Trace Off"}</button>
                      <button type="button" className="plan-agent-history-clear" onClick={clearHistory}>
                        Clear history
                      </button>
                    </div>
                    <ul className="plan-agent-history-list">
                      {turns.map((turn) => (
                        <li key={turn.turnId}>
                          <button
                            type="button"
                            className="plan-agent-history-item"
                            data-active={turn.turnId === activeTurnId}
                            onClick={() => {
                              setActiveTurnId(turn.turnId);
                              resetSourceReader();
                              if (thread) {
                                setThread({
                                  ...thread,
                                  uiState: { ...thread.uiState, scrollAnchorTurnId: turn.turnId, traceVisible },
                                });
                              }
                            }}
                          >
                            <strong>{turn.question}</strong>
                            <span>
                              {turn.backend} · {turn.status}
                              {turn.trace?.elapsed_ms != null ? ` · ${turn.trace.elapsed_ms}ms` : ""}
                              {turn.contextSummary?.admitted_count != null
                                ? ` · admitted ${turn.contextSummary.admitted_count}`
                                : ""}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {answer ? (
                  <div className="plan-agent-answer">
                    {activeTurn?.trace && traceVisible ? (
                      <TraceDetailsPanel
                        trace={activeTurn.trace}
                        answer={packetReview ? null : answer.answer}
                      />
                    ) : null}
                    {!isHermesGraphAgentResponse(answer) && !hasGrounding(answer) ? (
                      <p className="plan-agent-grounding-warning">
                        {UNGROUNDED_ANSWER_WARNING}
                      </p>
                    ) : null}
                    {hermesCitationValidation.contractWarning ? (
                      <p className="plan-agent-error">{hermesCitationValidation.contractWarning}</p>
                    ) : null}
                    {hermesGrounding.kind === "malformed" ? (
                      <p className="plan-agent-error">{hermesGrounding.reason}</p>
                    ) : null}
                    {hermesGrounding.kind === "valid" && hermesGrounding.grounding.state === "error" ? (
                      <div className="plan-agent-graph-grounding-error">
                        {hermesGrounding.grounding.diagnostic_codes.length ? (
                          <ul>
                            {hermesGrounding.grounding.diagnostic_codes.map((code) => (
                              <li key={code}><code>{code}</code></li>
                            ))}
                          </ul>
                        ) : (
                          <p className="plan-agent-muted">Hermes graph query failed without diagnostic codes.</p>
                        )}
                      </div>
                    ) : null}
                    {hermesGrounding.kind === "valid" && hermesGrounding.grounding.state === "partial" && hermesGrounding.grounding.warnings.length ? (
                      <ul className="plan-agent-graph-grounding-warnings">
                        {hermesGrounding.grounding.warnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    ) : null}
                    {!(activeTurn?.trace && traceVisible && !packetReview) ? (
                      <section
                        className={`plan-agent-answer-card plan-agent-answer-card-${hermesGrounding.kind === "valid" ? hermesGrounding.grounding.state : "legacy"}`}
                        aria-label={answerHeadingLabel}
                      >
                        <p className="plan-surface-kicker plan-agent-grounding-label">{answerHeadingLabel}</p>
                        <p>{answer.answer}</p>
                      </section>
                    ) : null}
                    <RetrievalFreshnessPanel decision={answer.retrieval_freshness} />
                    {activeTurn ? (
                      <WorldGraphQueryContextPanel
                        context={
                          turnResponses[activeTurn.turnId]?.world_graph_context
                          ?? activeTurn.worldGraphContext
                          ?? null
                        }
                        summary={activeTurn.worldGraphContextSummary}
                        persistedOnly={
                          !turnResponses[activeTurn.turnId]?.world_graph_context
                          && !activeTurn.worldGraphContext
                          && Boolean(activeTurn.worldGraphContextSummary)
                        }
                      />
                    ) : null}
                    {activeTurn && turnHasLegacyPathEvidence(activeTurn) ? (
                      <CorpusChangeSignalPanel
                        status={corpusSignalStatus}
                        snapshotCount={activeTurn.evidenceSnapshots?.length ?? 0}
                        checkedAt={corpusFreshness?.checked_at ?? null}
                        warnings={corpusFreshness?.warnings ?? []}
                        checking={freshnessChecking}
                        onCheck={() => void checkCurrentSourceState()}
                      />
                    ) : null}
                    {graphCitationCards.length ? (
                      <section className="plan-agent-graph-citation-cards" aria-label="Graph evidence">
                        <h4>Graph evidence</h4>
                        <ul>
                          {graphCitationCards.map((citation, index) => (
                            <li
                              key={graphCitationKey(citation)}
                              data-selected={selectedCitationKey === graphCitationKey(citation)}
                            >
                              <strong>Graph evidence {index + 1}</strong>
                              <details className="plan-agent-graph-anchor-id">
                                <summary><code>{shortenAnchorId(citation.anchor_id)}</code></summary>
                                <code>{citation.anchor_id}</code>
                              </details>
                              <span className="plan-agent-muted plan-agent-graph-revision">
                                Pinned revision · <code>{citation.revision_id}</code>
                              </span>
                              <button type="button" onClick={() => void openGraphCitationSource(citation)}>
                                Open evidence
                              </button>
                            </li>
                          ))}
                        </ul>
                      </section>
                    ) : null}
                    {citationCards.length ? (
                      <details className="plan-agent-metadata-drawer">
                        <summary>Supporting sources ({citationCards.length})</summary>
                        <section className="plan-agent-citation-cards" aria-label="Supporting sources">
                          <h4>Supporting sources</h4>
                          <ul>
                            {citationCards.map((card) => (
                              <li key={`${card.path}-${card.evidenceId}`} data-selected={selectedCitationKey === citationKey(card.path, card.evidenceId)}>
                                <strong>{card.sourceRole} · {card.authority} · {card.lineLabel}</strong>
                                <span className="plan-agent-muted">{card.evidenceId}</span>
                                <code>{card.path}</code>
                                {card.textExcerpt ? <p>{card.textExcerpt}</p> : null}
                                <button type="button" onClick={() => void openCitationSource(card)}>
                                  Open source
                                </button>
                              </li>
                            ))}
                          </ul>
                        </section>
                      </details>
                    ) : null}
                    {graphReadStatus !== "idle" ? (
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
                    {sourceStatus !== "idle" ? (
                      <section className="plan-agent-source-reader" aria-label="Source preview">
                        <div>
                          <p className="plan-surface-kicker">Source preview</p>
                          <h4>{sourceStatus === "loading" ? "Loading source…" : sourceResponse?.path ?? "Source unavailable"}</h4>
                          {sourceResponse ? <code>{sourceResponse.path}</code> : null}
                        </div>
                        {sourceStatus === "loading" ? <p className="plan-agent-muted">Reading current source content…</p> : null}
                        {sourceStatus === "error" ? <p className="plan-agent-error">{sourceError ?? "Unable to read citation source."}</p> : null}
                        {sourceResponse ? (
                          <pre>{renderSourceWithHighlight(sourceResponse)}</pre>
                        ) : null}
                      </section>
                    ) : null}
                    {packetReview ? (
                      <ContextSufficiencyPanel review={packetReview} />
                    ) : null}
                    {!packetReview && !activeTurn?.trace ? (
                      <p className="plan-agent-muted">No trace or context packet returned.</p>
                    ) : null}
                    {answer.citations?.length ? (
                      <p className="plan-agent-muted plan-agent-citation-count">
                        Citations returned: {answer.citations.length}
                      </p>
                    ) : null}
                  </div>
                ) : activeTurn ? (
                  <div className="plan-agent-answer">
                    <p className="plan-agent-muted">Stored turn from this prep thread.</p>
                    <p>{activeTurn.answer}</p>
                  </div>
                ) : null}
            </form>

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
        </div>
      ) : null}

      <div className="plan-agent-bar">
        <div>
          <p className="plan-surface-kicker">Ask prep memory</p>
          <strong>Ask prep memory · {threadTitle}</strong>
        </div>
        <button type="button" onClick={toggleDrawer} aria-expanded={open}>
          {open ? "Close drawer" : "Open drawer"}
        </button>
      </div>
    </section>
  );
}
