import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

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

/**
 * Controlled Projection host shell (BLD-SIH-03a).
 * Owns projection drawer DOM/lifecycle only — Tool launchers belong to ToolHost (BLD-SIH-04).
 */
export function ProjectionHost({
  active,
  navigationItems,
  labels,
  theme,
  body,
  onNavigate,
  onClose,
  onExpand,
}: ProjectionHostProps) {
  const isOpen = active !== null;
  const activeNavigationId =
    active?.kind === "tool" ? (active.launchingToolId ?? active.key) : null;
  const showModalBackdrop = isOpen && active?.kind === "tool";
  const drawerClass = projectionDrawerClass(active?.size);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const rootClass = [
    "surface-projection-host",
    isOpen ? "surface-projection-host--open" : "",
    active?.kind === "content" ? "surface-projection-host--reference" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const themeStyle = (theme?.tokens ?? {}) as CSSProperties;

  useEffect(() => {
    document.body.classList.toggle("surface-projection-open", isOpen);
    return () => {
      document.body.classList.remove("surface-projection-open");
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    closeButtonRef.current?.focus();
  }, [isOpen, active?.key]);

  useEffect(() => {
    if (!isOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={rootClass}
      style={themeStyle}
      data-md-theme={theme?.themeId}
      data-projection-key={active?.key}
    >
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
            <button
              type="button"
              ref={closeButtonRef}
              onClick={onClose}
              aria-label={labels.closeLabel}
            >
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
              className={activeNavigationId === item.id ? "active" : undefined}
              aria-pressed={activeNavigationId === item.id}
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
