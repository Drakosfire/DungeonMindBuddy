import { agentSurfaceLabel, surfaceContextSubtitle } from "./surfaceContextDisplay";
import { useAskPluginSlot } from "./AskPluginSlot";
import { useAgentInteraction } from "./useAgentInteraction";

/**
 * App-scoped Agent Interaction shell (R10b).
 *
 * Owns the compact dock and expandable pane chrome wherever a real Ask plugin
 * is registered. Plan fills the ask portal host with its Ask pane when mounted.
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

  if (!askPluginPresent) return null;

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
        </>
      ) : (
        <div className="plan-agent-bar agent-interaction-bar" data-testid="agent-interaction-bar">
          <div>
            <strong>
              Ask DungeonBuddy
              {surfaceLabel ? ` · ${surfaceLabel}` : ""}
              {` · ${threadTitle}`}
            </strong>
            <span className="plan-agent-muted">
              {surfaceSubtitle ?? "Graph-grounded ask ready"}
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
