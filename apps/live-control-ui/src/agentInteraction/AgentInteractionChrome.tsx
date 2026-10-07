import { agentSurfaceLabel, surfaceContextSubtitle } from "./surfaceContextDisplay";
import { useAskPluginSlot } from "./AskPluginSlot";
import { useAgentInteraction } from "./useAgentInteraction";
import dungeonBuddyAgentImage from "../assets/dungeonbuddy-agent.png";
import { useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent, type KeyboardEvent } from "react";

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
  const isPlan = surfaceId === "plan";
  const [planPanelWidth, setPlanPanelWidth] = useState(440);
  const [planSheetHeight, setPlanSheetHeight] = useState(() => (
    typeof window === "undefined" ? 440 : Math.round(window.innerHeight * 0.64)
  ));
  const shellElement = useRef<HTMLElement | null>(null);
  const planWidthOwner = useRef<{
    element: HTMLElement;
    previousValue: string;
    previousPriority: string;
  } | null>(null);
  const resizeStart = useRef<{
    pointerId: number;
    orientation: "horizontal" | "vertical";
    coordinate: number;
    value: number;
  } | null>(null);
  const planPanelStyle = {
    "--agent-plan-panel-width": `${planPanelWidth}px`,
    "--agent-plan-sheet-height": `${planSheetHeight}px`,
  } as CSSProperties;

  useLayoutEffect(() => {
    if (!isPlan || !open || !askPluginPresent) return;
    // Agent chrome is a sibling of the app shell, so publish its width at #root.
    const appRoot = shellElement.current?.closest<HTMLElement>("#root");
    if (!appRoot) return;

    const property = "--agent-plan-panel-width";
    planWidthOwner.current = {
      element: appRoot,
      previousValue: appRoot.style.getPropertyValue(property),
      previousPriority: appRoot.style.getPropertyPriority(property),
    };
    return () => {
      const owner = planWidthOwner.current;
      if (!owner || owner.element !== appRoot) return;
      if (owner.previousValue) {
        appRoot.style.setProperty(property, owner.previousValue, owner.previousPriority);
      } else {
        appRoot.style.removeProperty(property);
      }
      planWidthOwner.current = null;
    };
  }, [askPluginPresent, isPlan, open]);

  useLayoutEffect(() => {
    if (!isPlan || !open || !askPluginPresent) return;
    const appRoot = shellElement.current?.closest<HTMLElement>("#root");
    if (!appRoot) return;

    const syncEffectivePanelWidth = () => {
      const viewportLimit = Math.round(window.innerWidth * 0.72);
      const effectiveWidth = Math.max(320, Math.min(planPanelWidth, viewportLimit));
      appRoot.style.setProperty("--agent-plan-panel-width", `${effectiveWidth}px`);
    };
    syncEffectivePanelWidth();
    window.addEventListener("resize", syncEffectivePanelWidth);
    return () => window.removeEventListener("resize", syncEffectivePanelWidth);
  }, [askPluginPresent, isPlan, open, planPanelWidth]);

  function handleResizePointerDown(
    event: PointerEvent<HTMLButtonElement>,
    orientation: "horizontal" | "vertical",
  ) {
    event.preventDefault();
    resizeStart.current = {
      pointerId: event.pointerId,
      orientation,
      coordinate: orientation === "vertical" ? event.clientX : event.clientY,
      value: orientation === "vertical" ? planPanelWidth : planSheetHeight,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function handleResizePointerMove(event: PointerEvent<HTMLButtonElement>) {
    const start = resizeStart.current;
    if (!start || start.pointerId !== event.pointerId) return;
    if (start.orientation === "vertical") {
      const requestedWidth = start.value + start.coordinate - event.clientX;
      setPlanPanelWidth(Math.max(320, Math.min(Math.round(window.innerWidth * 0.72), requestedWidth)));
      return;
    }
    const requestedHeight = start.value + start.coordinate - event.clientY;
    setPlanSheetHeight(Math.max(240, Math.min(Math.round(window.innerHeight * 0.78), requestedHeight)));
  }

  function handleResizePointerUp(event: PointerEvent<HTMLButtonElement>) {
    if (resizeStart.current?.pointerId !== event.pointerId) return;
    resizeStart.current = null;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
  }

  function handleResizeKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    orientation: "horizontal" | "vertical",
  ) {
    const delta = orientation === "vertical"
      ? event.key === "ArrowLeft" ? 24 : event.key === "ArrowRight" ? -24 : 0
      : event.key === "ArrowUp" ? 24 : event.key === "ArrowDown" ? -24 : 0;
    if (delta === 0) return;
    event.preventDefault();
    if (orientation === "vertical") {
      setPlanPanelWidth((value) => Math.max(320, Math.min(Math.round(window.innerWidth * 0.72), value + delta)));
    } else {
      setPlanSheetHeight((value) => Math.max(240, Math.min(Math.round(window.innerHeight * 0.78), value + delta)));
    }
  }

  const launcher = (
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
  );

  if (!askPluginPresent) return null;

  return (
    <section
      className={`plan-agent-shell agent-interaction-shell${isPlan ? " agent-interaction-shell--plan" : ""}${open ? " open" : ""}`}
      aria-label="DungeonBuddy agent"
      data-testid="agent-interaction-chrome"
      data-ask-available={askPluginPresent ? "true" : "false"}
      data-surface-id={surfaceId ?? "none"}
      style={isPlan ? planPanelStyle : undefined}
      ref={shellElement}
    >
      {isPlan ? (
        <>
          <button
            type="button"
            className="agent-interaction-exit"
            onClick={() => setPaneOpen(false)}
            aria-label="Close chat"
            hidden={!open}
          >
            Close
          </button>
          <button
            type="button"
            role="separator"
            aria-label="Resize Buddy panel"
            aria-orientation="vertical"
            aria-valuemin={320}
            aria-valuemax={Math.round(window.innerWidth * 0.72)}
            aria-valuenow={planPanelWidth}
            className="agent-interaction-resize agent-interaction-resize--vertical"
            hidden={!open}
            onPointerDown={(event) => handleResizePointerDown(event, "vertical")}
            onPointerMove={handleResizePointerMove}
            onPointerUp={handleResizePointerUp}
            onPointerCancel={handleResizePointerUp}
            onKeyDown={(event) => handleResizeKeyDown(event, "vertical")}
          />
          <button
            type="button"
            role="separator"
            aria-label="Resize Buddy sheet"
            aria-orientation="horizontal"
            aria-valuemin={240}
            aria-valuemax={Math.round(window.innerHeight * 0.78)}
            aria-valuenow={planSheetHeight}
            className="agent-interaction-resize agent-interaction-resize--horizontal"
            hidden={!open}
            onPointerDown={(event) => handleResizePointerDown(event, "horizontal")}
            onPointerMove={handleResizePointerMove}
            onPointerUp={handleResizePointerUp}
            onPointerCancel={handleResizePointerUp}
            onKeyDown={(event) => handleResizeKeyDown(event, "horizontal")}
          />
          <div
            className="agent-interaction-ask-host"
            data-testid="agent-interaction-ask-host"
            hidden={!open}
            ref={setHostElement}
          />
          <div hidden={open}>{launcher}</div>
        </>
      ) : open ? (
        <>
          <button
            type="button"
            className="agent-interaction-exit"
            onClick={() => setPaneOpen(false)}
            aria-label="Close chat"
          >
            Close
          </button>
          <div className="agent-interaction-ask-host" data-testid="agent-interaction-ask-host" ref={setHostElement} />
        </>
      ) : launcher}
    </section>
  );
}
