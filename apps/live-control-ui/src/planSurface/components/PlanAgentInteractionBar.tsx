import { useEffect, useMemo, useState, type FormEvent } from "react";

import { getSourceBundle, postCitationFreshness, postCitationSource, postLiveQuery } from "../../api/liveApi";
import type {
  AgentInteractionThreadSummary,
  AgentInteractionThread,
  CitationFreshnessResponse,
  CitationSourceResponse,
  AgentInteractionTurn,
  IngestionSourceBundle,
  LiveQueryBackend,
  LiveQueryResponse,
  PlanViewProjection,
  SourceUnit,
} from "../../api/types";

import {
  AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS,
  AGENT_TURN_HISTORY_CAP,
  clearAgentThread,
  createAgentInteractionThread,
  deleteAgentThread,
  listAgentThreads,
  loadAgentThread,
  loadAgentThreadById,
  persistAgentThread,
  renameAgentThread,
  setActiveAgentThread,
  threadTitleFromQuestion,
  turnFromResponse,
} from "./agentInteractionHistory";
import { ContextSufficiencyPanel } from "./ContextSufficiencyPanel";
import { buildPacketReview } from "./contextSufficiencyLadder";
import { TraceDetailsPanel } from "./TraceDetailsPanel";
import { RetrievalFreshnessPanel } from "./RetrievalFreshnessPanel";
import { CorpusChangeSignalPanel } from "./CorpusChangeSignalPanel";

interface PlanAgentInteractionBarProps {
  planView: PlanViewProjection;
  loadBundle?: typeof getSourceBundle;
  askCorpus?: typeof postLiveQuery;
  readCitationSource?: typeof postCitationSource;
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
  planView,
  loadBundle = getSourceBundle,
  askCorpus = postLiveQuery,
  readCitationSource = postCitationSource,
  checkCitationFreshness = postCitationFreshness,
}: PlanAgentInteractionBarProps) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<BundleStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<IngestionSourceBundle | null>(null);
  const [question, setQuestion] = useState("");
  const [queryBackend, setQueryBackend] = useState<LiveQueryBackend>("live");
  const [askStatus, setAskStatus] = useState<AskStatus>("idle");
  const [askError, setAskError] = useState<string | null>(null);
  const [thread, setThread] = useState<AgentInteractionThread | null>(null);
  const [turns, setTurns] = useState<AgentInteractionTurn[]>([]);
  const [turnResponses, setTurnResponses] = useState<Record<string, LiveQueryResponse>>({});
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const [selectedCitationKey, setSelectedCitationKey] = useState<string | null>(null);
  const [sourceStatus, setSourceStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [sourceResponse, setSourceResponse] = useState<CitationSourceResponse | null>(null);
  const [threadSummaries, setThreadSummaries] = useState<AgentInteractionThreadSummary[]>([]);
  const [threadSwitcherOpen, setThreadSwitcherOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [freshnessChecking, setFreshnessChecking] = useState(false);

  useEffect(() => {
    const storedThread = loadAgentThread(planView.campaign_id, "plan");
    setThreadSummaries(listAgentThreads(planView.campaign_id, "plan"));
    if (storedThread) {
      setThread(storedThread);
      setTurns(storedThread.turns);
      setActiveTurnId(storedThread.uiState?.scrollAnchorTurnId ?? storedThread.turns[0]?.turnId ?? null);
      setQueryBackend(storedThread.activeBackend);
    }
  }, [planView.campaign_id]);

  const activeTurn = useMemo(
    () => turns.find((turn) => turn.turnId === activeTurnId) ?? turns[0] ?? null,
    [turns, activeTurnId],
  );
  const answer = activeTurn ? (turnResponses[activeTurn.turnId] ?? ({
    answer: activeTurn.answer,
    status: activeTurn.status,
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
  } satisfies LiveQueryResponse)) : null;
  const packetReview = answer ? buildPacketReview(answer) : null;
  const citationCards = answer ? evidenceCardsFromAnswer(answer) : [];
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
  }

  function refreshThreadSummaries() {
    setThreadSummaries(listAgentThreads(planView.campaign_id, "plan"));
  }

  function activateThread(nextThread: AgentInteractionThread | null) {
    setThread(nextThread);
    setTurns(nextThread?.turns ?? []);
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
      const response = await loadBundle("campaign-ingested", planView.campaign_id);
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
      clearAgentThread(thread);
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
    setTurns([]);
    setActiveTurnId(null);
    setAskStatus("idle");
    resetSourceReader();
  }

  function createNewThread() {
    const nextThread = createAgentInteractionThread(
      planView.campaign_id,
      planView.session,
      "plan",
      queryBackend,
    );
    persistAgentThread(nextThread);
    setActiveAgentThread(planView.campaign_id, "plan", nextThread.threadId);
    activateThread(nextThread);
    refreshThreadSummaries();
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
    persistAgentThread(nextThread);
    refreshThreadSummaries();
  }

  function switchThread(threadId: string) {
    const nextThread = loadAgentThreadById(planView.campaign_id, threadId);
    if (!nextThread) return;
    setActiveAgentThread(planView.campaign_id, "plan", threadId);
    activateThread(nextThread);
    refreshThreadSummaries();
  }

  function saveRename() {
    const baseThread = thread ?? createAgentInteractionThread(planView.campaign_id, planView.session, "plan", queryBackend);
    const nextThread = renameAgentThread(baseThread, titleDraft);
    setThread(nextThread);
    refreshThreadSummaries();
    setRenaming(false);
  }

  function deleteThread(threadId: string) {
    const doomed = loadAgentThreadById(planView.campaign_id, threadId);
    if (!doomed) return;
    deleteAgentThread(doomed);
    const nextActive = loadAgentThread(planView.campaign_id, "plan");
    activateThread(nextActive);
    refreshThreadSummaries();
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
          fingerprint_algorithm: snapshot.fingerprint_algorithm,
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
        persistAgentThread(nextThread);
        refreshThreadSummaries();
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

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || askStatus === "asking") return;
    setAskStatus("asking");
    setAskError(null);
    try {
      const currentThread = thread ?? createAgentInteractionThread(
        planView.campaign_id,
        planView.session,
        "plan",
        queryBackend,
        threadTitleFromQuestion(trimmed),
      );
      const response = await askCorpus(
        trimmed,
        planView.campaign_id,
        planView.session,
        queryBackend,
        {
          agentThreadId: currentThread.threadId,
          hermesSessionId: currentThread.hermesSession?.sessionId ?? null,
          traceRequested: currentThread.uiState?.traceVisible ?? false,
        },
      );
      const nextTurn = turnFromResponse(trimmed, response, queryBackend);
      const nextTurns = [nextTurn, ...turns].slice(0, AGENT_TURN_HISTORY_CAP);
      const nextThread: AgentInteractionThread = {
        ...currentThread,
        threadId: response.agent_thread_id ?? currentThread.threadId,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(trimmed),
        updatedAt: new Date().toISOString(),
        activeBackend: queryBackend,
        hermesSession: response.hermes_session ?? currentThread.hermesSession ?? null,
        turns: nextTurns,
        uiState: {
          traceVisible: currentThread.uiState?.traceVisible ?? false,
          scrollAnchorTurnId: nextTurn.turnId,
          newThreadSuggestionDismissed: currentThread.uiState?.newThreadSuggestionDismissed ?? false,
        },
      };
      setThread(nextThread);
      setTurns(nextTurns);
      setActiveTurnId(nextTurn.turnId);
      resetSourceReader();
      setTurnResponses((previous) => ({ ...previous, [nextTurn.turnId]: response }));
      persistAgentThread(nextThread);
      refreshThreadSummaries();
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
  const activeSessionUnits = bundle ? unitsForSession(bundle, planView.session) : [];
  const activeStageKinds = new Set(activeSessionUnits.map(sourceKind));
  const missingStages = REQUIRED_INGEST_STAGES.filter((stage) => !activeStageKinds.has(stage));
  const activeSessionComplete = bundle ? missingStages.length === 0 : false;
  const latestSessions = bundle ? sessionNumbers(bundle).slice(0, 5) : [];

  return (
    <section
      className={`plan-agent-shell ${open ? "open" : "closed"}`}
      aria-label="Agent Interaction placeholder"
    >
      {open ? (
        <div className="plan-agent-pane" role="complementary" aria-label="Agent Interaction drawer">
          <header className="plan-agent-pane-header">
            <div>
              <p className="plan-surface-kicker">Agent Interaction</p>
              {renaming ? (
                <div className="plan-agent-title-editor">
                  <label>
                    <span>Thread title</span>
                    <input value={titleDraft} onChange={(event) => setTitleDraft(event.currentTarget.value)} />
                  </label>
                  <button type="button" onClick={saveRename}>Save title</button>
                  <button type="button" onClick={() => setRenaming(false)}>Cancel</button>
                </div>
              ) : (
                <h2>{threadTitle}</h2>
              )}
              <p>Ingested corpus interaction proof</p>
              <p>
                This local `/plan` pane consumes the future Agent Interaction contract before the
                global provider is built.
              </p>
            </div>
            <div className="plan-agent-pane-actions">
              <button type="button" onClick={() => {
                setTitleDraft(threadTitle);
                setRenaming(true);
              }}>
                Rename
              </button>
              <button type="button" onClick={createNewThread}>New thread</button>
              <button type="button" onClick={() => setThreadSwitcherOpen((value) => !value)}>Threads</button>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close Agent Interaction drawer">
                Close
              </button>
            </div>
          </header>
          {threadSwitcherOpen ? (
            <section className="plan-agent-thread-switcher" aria-label="Agent Interaction threads">
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

          {status === "loading" ? <p className="plan-agent-muted">Loading source bundle…</p> : null}
          {status === "error" ? (
            <p className="plan-agent-error">{error ?? "Unable to load source bundle."}</p>
          ) : null}
          {bundle ? (
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
                <h3>Ask ingested corpus</h3>
                <p>
                  Ask first. Results show admitted campaign text, a preliminary sufficiency verdict,
                  agent trace metadata, and suggested source reads before advanced metadata.
                </p>
                <fieldset className="plan-agent-backend-picker">
                  <legend>Query backend</legend>
                  <label>
                    <input
                      type="radio"
                      name="plan-agent-query-backend"
                      value="live"
                      checked={queryBackend === "live"}
                      onChange={() => setQueryBackend("live")}
                    />
                    <span>Live loop</span>
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
                <label>
                  <span>Question</span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.currentTarget.value)}
                    placeholder="What changed after the latest ingested recap?"
                    rows={3}
                  />
                </label>
                <button type="submit" disabled={!question.trim() || askStatus === "asking"}>
                  {askStatus === "asking" ? "Asking…" : "Ask"}
                </button>
                {askStatus === "error" ? (
                  <p className="plan-agent-error">{askError ?? "Unable to ask corpus."}</p>
                ) : null}

                {turns.length ? (
                  <section className="plan-agent-history" aria-label="Conversation history">
                    <div className="plan-agent-history-header">
                      <h4>Conversation ({turns.length})</h4>
                      <button type="button" onClick={() => {
                        const baseThread = thread ?? createAgentInteractionThread(planView.campaign_id, planView.session, "plan", queryBackend);
                        const nextThread = { ...baseThread, uiState: { ...baseThread.uiState, traceVisible: !traceVisible } };
                        setThread(nextThread);
                        persistAgentThread(nextThread);
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
                                persistAgentThread({
                                  ...thread,
                                  uiState: { ...thread.uiState, scrollAnchorTurnId: turn.turnId, traceVisible },
                                });
                                refreshThreadSummaries();
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
                    {answer.agent_trace && traceVisible ? (
                      <TraceDetailsPanel
                        trace={answer.agent_trace}
                        answer={packetReview ? null : answer.answer}
                      />
                    ) : null}
                    {!(answer.agent_trace && traceVisible && !packetReview) ? (
                      <section className="plan-agent-answer-card" aria-label="Agent answer">
                        <p className="plan-surface-kicker">Answer</p>
                        <p>{answer.answer}</p>
                      </section>
                    ) : null}
                    <RetrievalFreshnessPanel decision={answer.retrieval_freshness} />
                    {activeTurn ? (
                      <CorpusChangeSignalPanel
                        status={corpusSignalStatus}
                        snapshotCount={activeTurn.evidenceSnapshots?.length ?? 0}
                        checkedAt={corpusFreshness?.checked_at ?? null}
                        warnings={corpusFreshness?.warnings ?? []}
                        checking={freshnessChecking}
                        onCheck={() => void checkCurrentSourceState()}
                      />
                    ) : null}
                    {citationCards.length ? (
                      <section className="plan-agent-citation-cards" aria-label="Citation cards">
                        <h4>Citation card</h4>
                        <ul>
                          {citationCards.map((card) => (
                            <li key={`${card.path}-${card.evidenceId}`} data-selected={selectedCitationKey === citationKey(card.path, card.evidenceId)}>
                              <strong>{card.evidenceId}</strong>
                              <span>{card.sourceRole} · {card.authority} · {card.lineLabel}</span>
                              <code>{card.path}</code>
                              {card.textExcerpt ? <p>{card.textExcerpt}</p> : null}
                              <button type="button" onClick={() => void openCitationSource(card)}>
                                Open source
                              </button>
                            </li>
                          ))}
                        </ul>
                      </section>
                    ) : null}
                    {sourceStatus !== "idle" ? (
                      <section className="plan-agent-source-reader" aria-label="Current source reader">
                        <div>
                          <p className="plan-surface-kicker">Current source reader</p>
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
                    {!packetReview && !answer.agent_trace ? (
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
                    <p className="plan-agent-muted">Stored turn from this Agent Interaction thread.</p>
                    <p>{activeTurn.answer}</p>
                  </div>
                ) : null}
              </form>

              <section className="plan-agent-proof" aria-label="Ingestion proof">
                <div>
                  <p className="plan-surface-kicker">Ingestion proof</p>
                  <h3>
                    {activeSessionComplete
                      ? `Session ${planView.session} has all expected ingest layers`
                      : `Session ${planView.session} is missing ${missingStages.length} ingest layers`}
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

              <details className="plan-agent-advanced">
                <summary>Advanced source metadata</summary>
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
                      {representativeUnits(bundle, planView.session).map((unit) => (
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
              </details>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="plan-agent-bar">
        <div>
          <p className="plan-surface-kicker">Agent Interaction</p>
          <strong>Agent Interaction · {threadTitle}</strong>
        </div>
        <button type="button" onClick={toggleDrawer} aria-expanded={open}>
          {open ? "Close drawer" : "Open drawer"}
        </button>
      </div>
    </section>
  );
}
