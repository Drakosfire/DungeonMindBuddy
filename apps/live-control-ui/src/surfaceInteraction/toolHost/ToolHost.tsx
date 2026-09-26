import { useCallback, useEffect, useRef, useState } from "react";

import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { sameSurfaceInteractionIdentity } from "../surfaceIdentity";
import type { SurfaceInteractionIdentity } from "../types";
import { activateToolContribution } from "./activateToolContribution";
import { groupToolContributions } from "./groupTools";
import { ToolHostView, type ToolHostViewGroup } from "./ToolHostView";

type ToolHostCloseReason = "dismiss" | "projection-launch" | "identity" | "inventory";

/**
 * Singular app-level Tool Host (BLD-SIH-04).
 * Renders launchers from the active lease's effective publication.tools.
 * Projection / AppChrome no longer own Tool launcher DOM.
 */
export function ToolHost() {
  const {
    surfaceInteractionPublication,
    activateProjectionTool,
  } = useAgentInteraction();
  const tools = surfaceInteractionPublication?.tools ?? [];
  const identity = surfaceInteractionPublication?.identity ?? null;
  const usesIngestPeek = surfaceInteractionPublication?.surfaceId === "ingest";

  const [isOpen, setIsOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const wasOpenRef = useRef(false);
  const isOpenRef = useRef(false);
  const closeReasonRef = useRef<ToolHostCloseReason | null>(null);
  const previousIdentityRef = useRef<SurfaceInteractionIdentity | null>(identity);
  isOpenRef.current = isOpen;

  const closeDrawer = useCallback((reason: ToolHostCloseReason) => {
    closeReasonRef.current = reason;
    setIsOpen(false);
  }, []);
  const dismissPeek = useCallback(() => closeDrawer("dismiss"), [closeDrawer]);

  // Close launcher on exact identity change (surface switch / lease replace).
  useEffect(() => {
    const previous = previousIdentityRef.current;
    if (!sameSurfaceInteractionIdentity(previous, identity)) {
      if (isOpen) {
        closeDrawer("identity");
      }
      previousIdentityRef.current = identity;
    }
  }, [identity, isOpen]);

  // Empty inventory closes an open drawer under the same identity.
  useEffect(() => {
    if (tools.length === 0 && isOpen) {
      closeDrawer("inventory");
    }
  }, [isOpen, tools.length]);

  useEffect(() => {
    if (isOpen) {
      closeRef.current?.focus();
      wasOpenRef.current = true;
      return;
    }
    if (wasOpenRef.current) {
      if (closeReasonRef.current === "dismiss") {
        toggleRef.current?.focus();
      }
      wasOpenRef.current = false;
      closeReasonRef.current = null;
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      closeDrawer("dismiss");
    }
    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [isOpen]);

  if (tools.length === 0) {
    return null;
  }

  const groups: readonly ToolHostViewGroup[] = groupToolContributions(tools).map((group) => ({
    groupId: group.groupId,
    groupLabel: group.groupLabel,
    groupOrder: group.groupOrder,
    tools: group.tools.map((tool) => ({
      id: tool.id,
      label: tool.label,
      eyebrow: tool.eyebrow,
      availability: tool.availability.status === "enabled"
        ? { status: "enabled" as const }
        : { status: "disabled" as const, disabledReason: tool.availability.disabledReason },
    })),
  }));

  function handleActivate(toolId: string) {
    const resultOrPromise = activateToolContribution({
      publication: surfaceInteractionPublication,
      toolId,
      openProjectionTool: activateProjectionTool,
    });

    if (resultOrPromise instanceof Promise) {
      void resultOrPromise.then((result) => {
        if (result.status === "opened" || result.status === "invoked") {
          closeDrawer(result.status === "opened" ? "projection-launch" : "dismiss");
          return;
        }
        // Async activation aborted or declined — keep drawer open when still
        // visible; otherwise park focus on the Tools toggle (visible control).
        if (!isOpenRef.current) {
          toggleRef.current?.focus();
          return;
        }
        // Tool button may have unmounted (same-identity auth loss). Park on a
        // still-visible launcher control rather than leaving focus on body.
        const hostRoot = toggleRef.current?.closest('[data-testid="surface-tool-host"]');
        const active = document.activeElement;
        if (!hostRoot || !active || !hostRoot.contains(active)) {
          closeRef.current?.focus();
        }
      });
      return;
    }

    if (resultOrPromise.status === "opened" || resultOrPromise.status === "invoked") {
      closeDrawer(resultOrPromise.status === "opened" ? "projection-launch" : "dismiss");
    }
  }

  return (
    <ToolHostView
      groups={groups}
      isOpen={isOpen}
      usesIngestPeek={usesIngestPeek}
      toggleRef={toggleRef}
      closeRef={closeRef}
      onToggle={() => setIsOpen((current) => !current)}
      onDismiss={dismissPeek}
      onActivate={handleActivate}
    />
  );
}
