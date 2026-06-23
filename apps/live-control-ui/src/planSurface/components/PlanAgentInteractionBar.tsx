import { useEffect, useMemo, useState, type FormEvent } from "react";

import { getSourceBundle, postLiveQuery } from "../../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  IngestionSourceBundle,
  LiveQueryBackend,
  LiveQueryResponse,
  PlanViewProjection,
  SourceUnit,
} from "../../api/types";

import {
  AGENT_TURN_HISTORY_CAP,
  clearAgentThread,
  createAgentInteractionThread,
  loadAgentThread,
  persistAgentThread,
  threadTitleFromQuestion,
  turnFromResponse,
} from "./agentInteractionHistory";
import { ContextSufficiencyPanel } from "./ContextSufficiencyPanel";
import { buildPacketReview } from "./contextSufficiencyLadder";
import { TraceDetailsPanel } from "./TraceDetailsPanel";

interface PlanAgentInteractionBarProps {
  planView: PlanViewProjection;
  loadBundle?: typeof getSourceBundle;
  askCorpus?: typeof postLiveQuery;
}

type BundleStatus = "idle" | "loading" | "ready" | "error";
type AskStatus = "idle" | "asking" | "answered" | "error";

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

  useEffect(() => {
    const storedThread = loadAgentThread(planView.campaign_id, "plan");
    if (storedThread) {
      setThread(storedThread);
      setTurns(storedThread.turns);
      setActiveTurnId(storedThread.uiState?.scrollAnchorTurnId ?? storedThread.turns[0]?.turnId ?? null);
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
  } satisfies LiveQueryResponse)) : null;
  const packetReview = answer ? buildPacketReview(answer) : null;
  const threadTitle = thread?.title ?? "New prep thread";
  const traceVisible = thread?.uiState?.traceVisible ?? false;

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
    if (thread) clearAgentThread(thread);
    setThread(null);
    setTurns([]);
    setActiveTurnId(null);
    setAskStatus("idle");
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
        },
      };
      setThread(nextThread);
      setTurns(nextTurns);
      setActiveTurnId(nextTurn.turnId);
      setTurnResponses((previous) => ({ ...previous, [nextTurn.turnId]: response }));
      persistAgentThread(nextThread);
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
              <h2>{threadTitle}</h2>
              <p>Ingested corpus interaction proof</p>
              <p>
                This local `/plan` pane consumes the future Agent Interaction contract before the
                global provider is built.
              </p>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close Agent Interaction drawer">
              Close
            </button>
          </header>

          {status === "loading" ? <p className="plan-agent-muted">Loading source bundle…</p> : null}
          {status === "error" ? (
            <p className="plan-agent-error">{error ?? "Unable to load source bundle."}</p>
          ) : null}
          {bundle ? (
            <div className="plan-agent-content">
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
                            onClick={() => setActiveTurnId(turn.turnId)}
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
