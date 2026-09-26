import type { Ref } from "react";

import { PeekClaim } from "../peekHost";
import "./ToolHostView.css";

/** A display-only tool. Authority callbacks and contribution objects stay in ToolHost. */
export interface ToolHostViewTool {
  id: string;
  label: string;
  eyebrow?: string;
  availability:
    | { status: "enabled" }
    | { status: "disabled"; disabledReason: string };
}

export interface ToolHostViewGroup {
  groupId: string | null;
  groupLabel: string | null;
  groupOrder: number;
  tools: readonly ToolHostViewTool[];
}

export interface ToolHostViewProps {
  groups: readonly ToolHostViewGroup[];
  isOpen: boolean;
  usesIngestPeek: boolean;
  toggleRef?: Ref<HTMLButtonElement>;
  closeRef?: Ref<HTMLButtonElement>;
  onToggle: () => void;
  onDismiss: () => void;
  onActivate: (toolId: string) => void;
}

/** DOM and paint only. Activation is an id intent, never a captured contribution. */
export function ToolHostView({
  groups,
  isOpen,
  usesIngestPeek,
  toggleRef,
  closeRef,
  onToggle,
  onDismiss,
  onActivate,
}: ToolHostViewProps) {
  const navGroups = groups.filter((group) => group.groupId !== null);
  const drawer = (
    <aside id="surface-tool-host-drawer" className="app-tools-toolbox-drawer" aria-label="Tools toolbar">
      <header className="app-tools-toolbox-hd">
        <div>
          <div className="app-tools-toolbox-eyebrow">Command Board</div>
          <h2 className="app-tools-toolbox-title">Tools</h2>
        </div>
        <button
          ref={closeRef}
          type="button"
          className="app-tools-toolbox-close"
          onClick={onDismiss}
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
          <details key={`${group.groupOrder}:${group.groupId ?? "pinned"}`} className="app-tools-fold" open>
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
                    onClick={() => onActivate(tool.id)}
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
  );

  return (
    <div
      className={`app-tools-toolbox${isOpen ? " open" : ""}${usesIngestPeek ? " app-tools-toolbox--peek" : ""}`}
      data-testid="surface-tool-host"
    >
      <button
        ref={toggleRef}
        type="button"
        className="app-tools-toolbox-toggle"
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-controls="surface-tool-host-drawer"
        title="Tools"
      >
        Tools
      </button>
      {usesIngestPeek ? (
        <PeekClaim kind="tools" active={isOpen} label="Tools" onDismiss={onDismiss}>
          {drawer}
        </PeekClaim>
      ) : (
        <>
          <div className="app-tools-toolbox-backdrop" hidden={!isOpen} onClick={onDismiss} aria-hidden="true" />
          {drawer}
        </>
      )}
    </div>
  );
}
