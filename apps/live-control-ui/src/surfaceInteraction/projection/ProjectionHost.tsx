import { useEffect, type CSSProperties, type ReactNode } from "react";

import type {
  ActiveProjection,
  ProjectionHostLabels,
  ProjectionHostNavigationItem,
  ProjectionHostTheme,
  ProjectionSize,
} from "./types";
import "./projectionHost.css";

export interface ProjectionHostProps {
  active: ActiveProjection | null;
  navigationItems: readonly ProjectionHostNavigationItem[];
  labels: ProjectionHostLabels;
  theme?: ProjectionHostTheme | null;
  body: ReactNode;
  onNavigate: (itemId: string) => void;
  onToggle: () => void;
  onClose: () => void;
  onExpand: () => void;
}

function projectionDrawerClass(size: ProjectionSize | undefined): string {
  if (size === "fullscreen") {
    return "surface-projection-drawer surface-projection-drawer--fullscreen";
  }
  if (size === "wide") {
    return "surface-projection-drawer surface-projection-drawer--wide";
  }
  return "surface-projection-drawer surface-projection-drawer--compact";
}

const DEFAULT_LABELS: ProjectionHostLabels = {
  toggleTitle: "Plan toolbox",
  closedDrawerLabel: "Plan toolbox",
  navigationLabel: "Toolbox tools",
  closeLabel: "Close toolbox",
  toolKicker: "Command Board",
  contentKicker: "Reference",
  toolTitle: "Toolbox",
  contentTitle: "Reference",
};

/**
 * Controlled Projection host shell (BLD-SIH-03a).
 * Owns DOM/lifecycle only — no Plan policy, registry, or selected-state ownership.
 */
export function ProjectionHost({
  active,
  navigationItems,
  labels: labelsInput,
  theme,
  body,
  onNavigate,
  onToggle,
  onClose,
  onExpand,
}: ProjectionHostProps) {
  const labels = { ...DEFAULT_LABELS, ...labelsInput };
  const isOpen = active !== null;
  const activeToolId = active?.kind === "tool" ? active.key : null;
  const showModalBackdrop = isOpen && active?.kind === "tool";
  const drawerClass = projectionDrawerClass(active?.size);
  const rootClass = [
    "surface-projection-host",
    isOpen ? "surface-projection-host--open" : "",
    active?.kind === "tool" ? `surface-projection-host--tool-${active.key}` : "",
    active?.kind === "content" ? "surface-projection-host--reference" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const themeStyle = (theme?.tokens ?? {}) as CSSProperties;
  const firstNavId = navigationItems[0]?.id;

  useEffect(() => {
    document.body.classList.toggle("surface-projection-open", isOpen);
    return () => {
      document.body.classList.remove("surface-projection-open");
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [isOpen, onClose]);

  return (
    <div className={rootClass} style={themeStyle} data-md-theme={theme?.themeId}>
      <button
        type="button"
        className="surface-projection-toggle"
        aria-expanded={isOpen}
        aria-controls="surface-projection-drawer"
        title={labels.toggleTitle}
        onClick={() => {
          if (isOpen) {
            onClose();
            return;
          }
          if (firstNavId) onToggle();
        }}
      >
        Tools
      </button>
      <div
        className="surface-projection-backdrop"
        hidden={!showModalBackdrop}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        id="surface-projection-drawer"
        className={drawerClass}
        aria-label={active ? `${active.title} projection` : labels.closedDrawerLabel}
      >
        <header className="surface-projection-header">
          <div>
            <p className="surface-projection-kicker">
              {active?.kind === "content" ? labels.contentKicker : labels.toolKicker}
            </p>
            <h2>{active?.kind === "content" ? labels.contentTitle : labels.toolTitle}</h2>
          </div>
          <div className="surface-projection-header-actions">
            {active?.kind === "content" && active.glanceOnly ? (
              <button type="button" onClick={onExpand}>
                Expand
              </button>
            ) : null}
            <button type="button" onClick={onClose} aria-label={labels.closeLabel}>
              ×
            </button>
          </div>
        </header>
        <nav
          className="surface-projection-nav"
          aria-label={labels.navigationLabel}
          hidden={active?.kind === "content"}
        >
          {navigationItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeToolId === item.id ? "active" : undefined}
              aria-pressed={activeToolId === item.id}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="surface-projection-body">{body}</div>
      </aside>
    </div>
  );
}
