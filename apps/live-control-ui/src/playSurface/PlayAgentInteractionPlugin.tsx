import { useEffect, useMemo, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import { postAgentQuery } from "../api/liveApi";
import type { AgentInteractionThread, PlayRunRecord } from "../api/types";
import {
  AGENT_TURN_HISTORY_CAP,
  createAgentInteractionThread,
  threadTitleFromQuestion,
  turnFromResponse,
} from "../agentInteraction/agentInteractionStorage";
import {
  useAskPluginSlotOptional,
  useRegisterAskPluginPresence,
} from "../agentInteraction/AskPluginSlot";
import { buildPlayAgentSurfaceContextRequest } from "../agentInteraction/agentSurfaceContextRequest";
import { buildHermesConversationHistory } from "../agentInteraction/hermesConversationHistory";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { AgentTraceInspector } from "../agentInteraction/trace/AgentTraceInspector";
import { buildPlayAgentWorldGraphQueryContextRequest } from "./playAgentQueryContext";

interface PlayAgentInteractionPluginProps {
  run: PlayRunRecord;
  askAgent?: typeof postAgentQuery;
}

type AskStatus = "idle" | "asking" | "answered" | "error";

export function PlayAgentInteractionPlugin({
  run,
  askAgent = postAgentQuery,
}: PlayAgentInteractionPluginProps) {
  useRegisterAskPluginPresence(true);
  const askSlot = useAskPluginSlotOptional();
  const agentInteraction = useAgentInteraction();
  const open = agentInteraction.paneState.isOpen;

  const [question, setQuestion] = useState("");
  const [askStatus, setAskStatus] = useState<AskStatus>("idle");
  const [askError, setAskError] = useState<string | null>(null);

  const thread = agentInteraction.activeThread;
  const turns = agentInteraction.turns;
  const worldGraphContext = useMemo(
    () => buildPlayAgentWorldGraphQueryContextRequest(run),
    [run],
  );
  const hasWorldMapping = worldGraphContext != null;

  useEffect(() => {
    agentInteraction.rehydrateScope({
      campaignId: run.campaign_id,
      sessionNumber: null,
      surfaceId: "play",
      documentId: run.playable_artifact_id,
      surfaceInstanceId: run.run_id,
    });
  }, [run.campaign_id, run.playable_artifact_id, run.run_id]);

  const chronologicalTurns = useMemo(() => [...turns].reverse(), [turns]);
  const threadTitle = thread?.title ?? "New thread";
  const traceVisible = thread?.uiState?.traceVisible ?? false;
  const activeTurn = turns[0] ?? null;

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || askStatus === "asking" || !hasWorldMapping) {
      return;
    }

    const surfaceContext = buildPlayAgentSurfaceContextRequest(
      agentInteraction.surfaceInteractionPublication,
    );
    if (!surfaceContext) {
      return;
    }

    setAskStatus("asking");
    setAskError(null);
    try {
      const currentThread = thread ?? createAgentInteractionThread(
        run.campaign_id,
        null,
        "play",
        "hermes",
        threadTitleFromQuestion(trimmed),
        run.playable_artifact_id,
        run.run_id,
      );
      const response = await askAgent(trimmed, {
        agentThreadId: currentThread.threadId,
        traceRequested: true,
        worldGraphContext: worldGraphContext!,
        conversationHistory: buildHermesConversationHistory(currentThread.turns),
        hermesSessionPointer: currentThread.hermesSession?.sessionId ?? null,
        surfaceContext,
      });
      const nextTurn = turnFromResponse(trimmed, response, "hermes");
      const nextTurns = [nextTurn, ...turns].slice(0, AGENT_TURN_HISTORY_CAP);
      const isHermesGraphAgentTurn = response.mode === "hermes_graph_agent"
        || response.agent_trace?.mode === "hermes_graph_agent";
      const nextThread: AgentInteractionThread = {
        ...currentThread,
        documentId: currentThread.documentId ?? run.playable_artifact_id,
        surfaceInstanceId: run.run_id,
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
      agentInteraction.updateThread(nextThread);
      setQuestion("");
      setAskStatus("answered");
    } catch (loadError) {
      setAskStatus("error");
      setAskError(loadError instanceof Error ? loadError.message : "Unable to ask");
    }
  }

  const askPane = (
    <div
      className="plan-agent-pane"
      role="complementary"
      aria-label="Ask DungeonBuddy"
      data-testid="play-agent-interaction-pane"
    >
      <header className="plan-agent-pane-header">
        <div>
          <strong>{threadTitle}</strong>
          <p className="plan-agent-muted">Play · graph-grounded ask for this Run</p>
        </div>
        <button
          type="button"
          onClick={() => agentInteraction.createThread("New thread")}
          data-testid="play-agent-new-thread"
        >
          New thread
        </button>
      </header>
      <div className="plan-agent-content">
        {!hasWorldMapping ? (
          <p className="plan-agent-warning" data-testid="play-agent-no-world-mapping">
            No world graph mapping for this campaign — Ask is disabled.
          </p>
        ) : null}
        <div className="plan-agent-transcript" data-testid="play-agent-transcript">
          {chronologicalTurns.length === 0 ? (
            <p className="plan-agent-muted">Ask about this Run while you play.</p>
          ) : (
            chronologicalTurns.map((turn) => (
              <article key={turn.turnId} className="plan-agent-turn" data-turn-id={turn.turnId}>
                <p><strong>You:</strong> {turn.question}</p>
                <p><strong>DungeonBuddy:</strong> {turn.answer}</p>
              </article>
            ))
          )}
        </div>
        {traceVisible && activeTurn?.trace ? (
          <AgentTraceInspector trace={activeTurn.trace} />
        ) : null}
        <form onSubmit={submitQuestion} data-testid="play-agent-ask-form">
          <label htmlFor="play-agent-question">Question</label>
          <textarea
            id="play-agent-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            data-testid="play-agent-question-input"
          />
          <button
            type="submit"
            disabled={!question.trim() || askStatus === "asking" || !hasWorldMapping}
            data-testid="play-agent-submit"
          >
            {askStatus === "asking" ? "Asking…" : "Ask DungeonBuddy"}
          </button>
          {askStatus === "error" ? (
            <p className="plan-agent-error" data-testid="play-agent-ask-error">
              {askError ?? "Unable to ask."}
            </p>
          ) : null}
        </form>
      </div>
    </div>
  );

  if (askSlot?.hostElement) {
    return createPortal(askPane, askSlot.hostElement);
  }

  if (open) {
    return (
      <section
        className="plan-agent-shell open"
        aria-label="Ask DungeonBuddy"
        data-testid="play-ask-fallback-shell"
      >
        {askPane}
      </section>
    );
  }

  return null;
}
