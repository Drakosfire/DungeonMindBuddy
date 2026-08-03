import { useEffect, useRef, useState } from "react";

import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { sameSurfaceInteractionIdentity } from "../surfaceIdentity";
import type { SurfaceInteractionIdentity } from "../types";
import { activateToolContribution } from "./activateToolContribution";
import { groupToolContributions } from "./groupTools";

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

  const [isOpen, setIsOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const wasOpenRef = useRef(false);
  const isOpenRef = useRef(false);
  const closeReasonRef = useRef<ToolHostCloseReason | null>(null);
  const previousIdentityRef = useRef<SurfaceInteractionIdentity | null>(identity);
  isOpenRef.current = isOpen;

  function closeDrawer(reason: ToolHostCloseReason) {
    closeReasonRef.current = reason;
    setIsOpen(false);
  }

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

  const groups = groupToolContributions(tools);
  const navGroups = groups.filter((group) => group.groupId !== null);

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
        }
      });
      return;
    }

    if (resultOrPromise.status === "opened" || resultOrPromise.status === "invoked") {
      closeDrawer(resultOrPromise.status === "opened" ? "projection-launch" : "dismiss");
    }
  }

  return (
    <div className={`app-tools-toolbox${isOpen ? " open" : ""}`} data-testid="surface-tool-host">
      <button
        ref={toggleRef}
        type="button"
        className="app-tools-toolbox-toggle"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
        aria-controls="surface-tool-host-drawer"
        title="Tools"
      >
        Tools
      </button>
      <div
        className="app-tools-toolbox-backdrop"
        hidden={!isOpen}
        onClick={() => closeDrawer("dismiss")}
        aria-hidden="true"
      />
      <aside
        id="surface-tool-host-drawer"
        className="app-tools-toolbox-drawer"
        aria-label="Tools toolbar"
      >
        <header className="app-tools-toolbox-hd">
          <div>
            <div className="app-tools-toolbox-eyebrow">Command Board</div>
            <h2 className="app-tools-toolbox-title">Tools</h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="app-tools-toolbox-close"
            onClick={() => closeDrawer("dismiss")}
            aria-label="Close Tools"
          >
            x
          </button>
        </header>
        {navGroups.length > 0 ? (
          <nav className="app-tools-toolbox-nav" aria-label="Tool groups">
            {navGroups.map((group) => (
              <button
                key={group.groupId ?? "pinned"}
                type="button"
                className="app-tools-toolbox-nav-btn active"
              >
                {group.groupLabel ?? "Tools"}
              </button>
            ))}
          </nav>
        ) : null}
        <div className="app-tools-toolbox-body">
          {groups.map((group) => (
            <details
              key={`${group.groupOrder}:${group.groupId ?? "pinned"}`}
              className="app-tools-fold"
              open
            >
              <summary>{group.groupLabel ?? "Tools"}</summary>
              <div className="app-tools-fold-bd app-tools-actions">
                {group.tools.map((tool) => {
                  const disabled = tool.availability.status !== "enabled";
                  return (
                    <button
                      key={tool.id}
                      type="button"
                      disabled={disabled}
                      title={
                        disabled && tool.availability.status === "disabled"
                          ? tool.availability.disabledReason
                          : undefined
                      }
                      onClick={() => handleActivate(tool.id)}
                    >
                      {tool.eyebrow ? <span>{tool.eyebrow}</span> : null}
                      <strong>{tool.label}</strong>
                    </button>
                  );
                })}
              </div>
            </details>
          ))}
        </div>
      </aside>
    </div>
  );
}
