import { useEffect, useState } from "react";
import { agentSurfaceLabel, surfaceContextSubtitle } from "./surfaceContextDisplay";
import { useAskPluginSlot } from "./AskPluginSlot";
import { useAgentInteraction } from "./useAgentInteraction";
import dungeonBuddyAgentImage from "../assets/dungeonbuddy-agent.png";

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
  const focusedPrototype = new URLSearchParams(window.location.search).get("prototype") === "focused";
  const [prototypeWidth, setPrototypeWidth] = useState(420);
  useEffect(() => {
    if (!focusedPrototype) return;
    document.documentElement.style.setProperty("--focused-chat-width", `${prototypeWidth}px`);
    return () => { document.documentElement.style.removeProperty("--focused-chat-width"); };
  }, [focusedPrototype, prototypeWidth]);
  const resizePrototype = (width: number) => setPrototypeWidth(Math.max(300, Math.min(window.innerWidth * .55, width)));

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
          {focusedPrototype && <div className="focused-chat-resize" role="separator" aria-label="Resize conversation" aria-orientation="vertical" aria-valuemin={300} aria-valuemax={Math.round(window.innerWidth * .55)} aria-valuenow={prototypeWidth} tabIndex={0}
            onPointerDown={event => event.currentTarget.setPointerCapture(event.pointerId)}
            onPointerMove={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) resizePrototype(window.innerWidth - event.clientX); }}
            onPointerUp={event => event.currentTarget.releasePointerCapture(event.pointerId)}
            onKeyDown={event => { if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); resizePrototype(prototypeWidth + (event.key === "ArrowLeft" ? 24 : -24)); } }} />}
          <button
            type="button"
            className="agent-interaction-exit"
            onClick={() => setPaneOpen(false)}
            aria-label="Close chat"
          >
            Close
          </button>
          <div
            className="agent-interaction-ask-host"
            data-testid="agent-interaction-ask-host"
            ref={setHostElement}
          />
        </>
      ) : (
        <div className="plan-agent-bar agent-interaction-bar" data-testid="agent-interaction-bar">
          <button
            type="button"
            onClick={() => setPaneOpen(true)}
            aria-expanded={open}
            aria-label="Open"
            title={[
              "Ask DungeonBuddy",
              surfaceLabel,
              threadTitle,
              surfaceSubtitle ?? "Graph-grounded ask ready",
            ].filter(Boolean).join(" · ")}
            data-testid="agent-interaction-open"
          >
            <img src={dungeonBuddyAgentImage} alt="" aria-hidden="true" />
          </button>
        </div>
      )}
    </section>
  );
}
