import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { sameSurfaceInteractionIdentity } from "../surfaceIdentity";
import type {
  SurfaceInteractionCommandTarget,
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionIdentity,
  SurfaceInteractionWorkObjectIdentity,
} from "../types";
import { activateEditContribution } from "./activateEditContribution";
import { groupEditCommands, type EditHostGroup } from "./groupEditCommands";

export interface LegacyEditPanelAttachment {
  groupId: string;
  groupLabel: string;
  groupOrder: number;
  groupDefaultOpen?: boolean;
  target: SurfaceInteractionCommandTarget;
  /** Compatibility-only rich panel — never enters publication. */
  panel: ReactNode;
}

export interface EditHostProps {
  layout: "overlay" | "dock";
  /** Named Legacy/Compatibility — rich section panels from AppChrome editorTools. */
  legacyPanels?: readonly LegacyEditPanelAttachment[];
}

type EditHostCloseReason = "dismiss" | "identity" | "inventory" | "work-object";

interface EditHostRenderGroup extends EditHostGroup {
  panel: ReactNode | null;
}

function sameWorkObject(
  left: SurfaceInteractionWorkObjectIdentity | null | undefined,
  right: SurfaceInteractionWorkObjectIdentity | null | undefined,
): boolean {
  if (!left && !right) return true;
  if (!left || !right) return false;
  return left.kind === right.kind && left.id === right.id;
}

function targetsMatch(
  left: SurfaceInteractionCommandTarget,
  right: SurfaceInteractionWorkObjectIdentity,
): boolean {
  return left.kind === right.kind && left.id === right.id;
}

function layoutDefaultOpen(layout: "overlay" | "dock"): boolean {
  return layout === "dock";
}

function mergeGroupsWithPanels(
  commandGroups: readonly EditHostGroup[],
  panels: readonly LegacyEditPanelAttachment[],
): EditHostRenderGroup[] {
  const merged: EditHostRenderGroup[] = commandGroups.map((group) => ({
    ...group,
    panel: null,
  }));

  for (const attachment of panels) {
    const existing = merged.find(
      (group) =>
        group.groupId === attachment.groupId
        && group.groupOrder === attachment.groupOrder,
    );
    if (existing) {
      existing.panel = attachment.panel;
      continue;
    }
    merged.push({
      groupId: attachment.groupId,
      groupLabel: attachment.groupLabel,
      groupOrder: attachment.groupOrder,
      groupDefaultOpen: attachment.groupDefaultOpen === true,
      commands: [],
      panel: attachment.panel,
    });
  }

  return merged.sort((left, right) => {
    const leftPinned = left.groupId === null;
    const rightPinned = right.groupId === null;
    if (leftPinned !== rightPinned) return leftPinned ? -1 : 1;
    if (left.groupOrder !== right.groupOrder) return left.groupOrder - right.groupOrder;
    const leftId = left.groupId ?? "";
    const rightId = right.groupId ?? "";
    if (leftId !== rightId) return leftId < rightId ? -1 : 1;
    return 0;
  });
}

/**
 * Singular app-level Edit Host (BLD-SIH-05).
 * Renders Edit commands from the active lease's effective publication.editCommands
 * plus compatibility-only legacy panels. Does not close after command invoke.
 */
export function EditHost({
  layout,
  legacyPanels = [],
}: EditHostProps) {
  const { surfaceInteractionPublication } = useAgentInteraction();
  const publication = surfaceInteractionPublication;
  const identity = publication?.identity ?? null;
  const workObject = publication?.canvas?.workObject ?? null;

  const matchingCommands: SurfaceInteractionEditCommandContribution[] = workObject
    ? (publication?.editCommands ?? []).filter((command) =>
      targetsMatch(command.target, workObject))
    : [];
  const matchingPanels = workObject
    ? legacyPanels.filter((panel) => targetsMatch(panel.target, workObject))
    : [];
  const hasInventory = matchingCommands.length > 0 || matchingPanels.length > 0;

  const defaultOpen = layoutDefaultOpen(layout);
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const toggleRef = useRef<HTMLButtonElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const wasOpenRef = useRef(false);
  const closeReasonRef = useRef<EditHostCloseReason | null>(null);
  const previousIdentityRef = useRef<SurfaceInteractionIdentity | null>(identity);
  const previousWorkObjectRef = useRef<SurfaceInteractionWorkObjectIdentity | null>(workObject);
  const hadInventoryRef = useRef(hasInventory);

  function setHostOpen(next: boolean, reason: EditHostCloseReason | null = null) {
    if (!next && reason) {
      closeReasonRef.current = reason;
    }
    setIsOpen(next);
  }

  // Identity or work-object change → reset to layout default.
  useEffect(() => {
    const identityChanged = !sameSurfaceInteractionIdentity(
      previousIdentityRef.current,
      identity,
    );
    const workObjectChanged = !sameWorkObject(previousWorkObjectRef.current, workObject);
    if (identityChanged || workObjectChanged) {
      setHostOpen(defaultOpen, identityChanged ? "identity" : "work-object");
      previousIdentityRef.current = identity;
      previousWorkObjectRef.current = workObject;
    }
  }, [identity, workObject, defaultOpen]);

  // Empty inventory discards open state; returning inventory uses layout default
  // (no resurrection of the previous user open/closed choice).
  useEffect(() => {
    if (!hasInventory) {
      if (hadInventoryRef.current || isOpen !== defaultOpen) {
        setHostOpen(defaultOpen, "inventory");
      }
      hadInventoryRef.current = false;
      return;
    }
    if (!hadInventoryRef.current) {
      setHostOpen(defaultOpen, null);
      hadInventoryRef.current = true;
    }
  }, [hasInventory, defaultOpen, isOpen]);

  useEffect(() => {
    if (!hasInventory) return;
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
  }, [hasInventory, isOpen]);

  useEffect(() => {
    if (!isOpen || !hasInventory) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      setHostOpen(false, "dismiss");
    }
    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [isOpen, hasInventory]);

  if (!hasInventory) {
    return null;
  }

  const groups = mergeGroupsWithPanels(
    groupEditCommands(matchingCommands),
    matchingPanels,
  );
  const navGroups = groups.filter((group) => group.groupId !== null);
  const isDocked = layout === "dock";

  function handleActivate(commandId: string) {
    activateEditContribution({
      publication,
      commandId,
      expectedTarget: workObject,
    });
    // Edit Host does not close after invoking Edit commands.
  }

  return (
    <div
      className={[
        "app-edit-toolbox",
        isDocked ? "app-edit-toolbox--docked" : "",
        isOpen ? "open" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      data-layout={layout}
      data-testid="surface-edit-host"
    >
      <button
        ref={toggleRef}
        type="button"
        className="app-edit-toolbox-toggle"
        onClick={() => setHostOpen(!isOpen, isOpen ? "dismiss" : null)}
        aria-expanded={isOpen}
        aria-controls="app-edit-toolbox-drawer"
        title="Edit"
        hidden={isOpen}
      >
        Edit
      </button>
      <div
        className="app-edit-toolbox-backdrop"
        hidden={!isOpen}
        onClick={() => setHostOpen(false, "dismiss")}
        aria-hidden="true"
      />
      {isOpen ? (
        <aside
          id="app-edit-toolbox-drawer"
          className="app-edit-toolbox-drawer"
          aria-label="Edit toolbar"
        >
          <header className="app-edit-toolbox-hd">
            <div>
              <div className="app-edit-toolbox-eyebrow">Command Board</div>
              <h2 className="app-edit-toolbox-title">Edit</h2>
            </div>
            <button
              ref={closeRef}
              type="button"
              className="app-edit-toolbox-close"
              onClick={() => setHostOpen(false, "dismiss")}
              aria-label="Close Edit"
            >
              x
            </button>
          </header>
          {navGroups.length > 0 ? (
            <nav className="app-edit-toolbox-nav" aria-label="Edit tool groups">
              {navGroups.map((group) => (
                <button
                  key={group.groupId ?? "pinned"}
                  type="button"
                  className="app-edit-toolbox-nav-btn active"
                >
                  {group.groupLabel ?? "Edit"}
                </button>
              ))}
            </nav>
          ) : null}
          <div className="app-edit-toolbox-body">
            {groups.map((group) => (
              <details
                key={`${group.groupOrder}:${group.groupId ?? "pinned"}`}
                className="app-edit-fold"
                open={group.groupDefaultOpen}
              >
                <summary>{group.groupLabel ?? "Edit state"}</summary>
                <div className="app-edit-fold-bd">
                  {group.commands.length > 0 ? (
                    <div className="app-edit-actions">
                      {group.commands.map((command) => {
                        const disabled = command.availability.status !== "enabled";
                        return (
                          <button
                            key={command.id}
                            type="button"
                            disabled={disabled}
                            aria-pressed={command.pressed}
                            title={
                              disabled && command.availability.status === "disabled"
                                ? command.availability.disabledReason
                                : undefined
                            }
                            onClick={() => handleActivate(command.id)}
                          >
                            {command.eyebrow ? <span>{command.eyebrow}</span> : null}
                            <strong>{command.label}</strong>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                  {group.panel ? (
                    <div className="app-edit-fold-panel">{group.panel}</div>
                  ) : null}
                </div>
              </details>
            ))}
          </div>
        </aside>
      ) : null}
    </div>
  );
}
