import { agentSurfaceLabel, surfaceContextSubtitle } from "./surfaceContextDisplay";
import { useAskPluginSlot } from "./AskPluginSlot";
import { useAgentInteraction } from "./useAgentInteraction";

/**
 * App-scoped Agent Interaction shell (R10b).
 *
 * Owns the persistent bottom bar and expandable pane chrome across surfaces.
 * Plan fills the ask portal host with its Ask pane when mounted. Without a
 * registered Ask plugin, the shell shows an honest empty pane — Ask is not
 * invented on Ingest/Build.
 *
 * Surface identity comes from `activeSurfaceContext.surfaceId` published by
 * each surface — not from the URL.
 */
export function AgentInteractionChrome() {
  const { paneState, setPaneOpen, activeThread, activeSurfaceContext } = useAgentInteraction();
  const { setHostElement, askPluginPresent } = useAskPluginSlot();
  const open = paneState.isOpen;
  const threadTitle = activeThread?.title?.trim() || "New thread";
  const surfaceId = activeSurfaceContext?.surfaceId ?? null;
  const surfaceLabel = agentSurfaceLabel(surfaceId);
  const surfaceSubtitle = surfaceContextSubtitle(activeSurfaceContext);

  return (
    <section
      className={`plan-agent-shell agent-interaction-shell${open ? " open" : ""}`}
      aria-label="DungeonBuddy agent"
      data-testid="agent-interaction-chrome"
      data-ask-available={askPluginPresent ? "true" : "false"}
      data-surface-id={surfaceId ?? "none"}
    >
      {open ? (
        <>
          <div
            className="agent-interaction-ask-host"
            data-testid="agent-interaction-ask-host"
            ref={setHostElement}
          />
          {!askPluginPresent ? (
            <div className="plan-agent-pane agent-interaction-pane" data-testid="agent-interaction-pane">
              <header className="plan-agent-pane-header">
                <div>
                  <strong>Ask DungeonBuddy</strong>
                  <p className="plan-agent-muted">
                    Ask is unavailable for the current surface.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setPaneOpen(false)}
                  aria-label="Close Ask DungeonBuddy"
                >
                  Close
                </button>
              </header>
              <div
                className="plan-agent-content agent-interaction-empty"
                data-testid="agent-interaction-ask-empty"
              >
                <p className="plan-agent-muted">
                  No surface has registered an Ask plugin yet. Open a surface that supports Ask
                  (Plan or Play with a loaded Run) to start a graph-grounded thread.
                </p>
                {surfaceLabel ? (
                  <p className="plan-agent-muted" data-testid="agent-interaction-current-surface">
                    Current surface: {surfaceLabel}
                    {activeSurfaceContext?.ambientSummary?.trim()
                      ? ` · ${activeSurfaceContext.ambientSummary.trim()}`
                      : ""}
                  </p>
                ) : (
                  <p className="plan-agent-muted">No surface has published context yet.</p>
                )}
              </div>
            </div>
          ) : null}
        </>
      ) : (
        <div className="plan-agent-bar agent-interaction-bar" data-testid="agent-interaction-bar">
          <div>
            <strong>
              Ask DungeonBuddy
              {surfaceLabel ? ` · ${surfaceLabel}` : ""}
              {askPluginPresent ? ` · ${threadTitle}` : ""}
            </strong>
            <span className="plan-agent-muted">
              {askPluginPresent
                ? surfaceSubtitle ?? "Graph-grounded ask ready"
                : surfaceSubtitle
                  ? `${surfaceSubtitle} · Ask unavailable here`
                  : surfaceLabel
                    ? `${surfaceLabel} · Ask unavailable here`
                    : "Ask unavailable for this surface"}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setPaneOpen(true)}
            aria-expanded={open}
            data-testid="agent-interaction-open"
          >
            Open
          </button>
        </div>
      )}
    </section>
  );
}
