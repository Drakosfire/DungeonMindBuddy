import type { ReactNode } from "react";

import type {
  AppChromeAction,
  AppChromeNavbarStatus,
  AppChromeToolSection,
  AppChromeTools,
} from "../chrome/AppChrome";

export type MarkdownEditorToolAction = {
  id: string;
  label: string;
  eyebrow?: string;
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
};

export type MarkdownEditorNavbarStatus = {
  id: string;
  label: string;
  eyebrow?: string;
  tone?: AppChromeNavbarStatus["tone"];
};

export type MarkdownEditorToolSection = {
  id: string;
  title: string;
  defaultOpen?: boolean;
  actions: MarkdownEditorToolAction[];
  panel?: ReactNode;
};

export type MarkdownEditorToolbarModel = {
  /** Persistent top-level nav status (graph load, etc.). */
  navbarStatuses?: MarkdownEditorNavbarStatus[];
  /** Persistent top-level nav actions (Edit / Save / surface checkpoint). */
  navbarActions?: MarkdownEditorToolAction[];
  pinnedActions?: MarkdownEditorToolAction[];
  sections?: MarkdownEditorToolSection[];
};

function toAppChromeAction(action: MarkdownEditorToolAction): AppChromeAction {
  return {
    id: action.id,
    label: action.label,
    eyebrow: action.eyebrow,
    onClick: action.onClick,
    disabled: action.disabled,
    pressed: action.pressed,
  };
}

function toAppChromeNavbarStatus(status: MarkdownEditorNavbarStatus): AppChromeNavbarStatus {
  return {
    id: status.id,
    label: status.label,
    eyebrow: status.eyebrow,
    tone: status.tone,
  };
}

function toAppChromeSection(section: MarkdownEditorToolSection): AppChromeToolSection {
  return {
    id: section.id,
    title: section.title,
    defaultOpen: section.defaultOpen,
    actions: section.actions.map(toAppChromeAction),
    panel: section.panel,
  };
}

export function toAppChromeTools(model: MarkdownEditorToolbarModel): AppChromeTools {
  return {
    navbarStatuses: model.navbarStatuses?.map(toAppChromeNavbarStatus),
    navbarActions: model.navbarActions?.map(toAppChromeAction),
    pinnedActions: model.pinnedActions?.map(toAppChromeAction),
    sections: model.sections?.map(toAppChromeSection),
  };
}

export function MarkdownEditorToolbar({
  model,
  "aria-label": ariaLabel = "Markdown editor toolbar",
}: {
  model: MarkdownEditorToolbarModel;
  "aria-label"?: string;
}) {
  const tools = toAppChromeTools(model);
  const pinned = tools.pinnedActions ?? [];
  const sections = tools.sections ?? [];

  return (
    <div className="markdown-editor-toolbar" aria-label={ariaLabel} data-testid="markdown-editor-toolbar">
      {pinned.length > 0 ? (
        <div className="markdown-editor-toolbar__pinned" role="group" aria-label="Pinned actions">
          {pinned.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={action.onClick}
              disabled={action.disabled}
              aria-pressed={action.pressed}
            >
              {action.eyebrow ? <span>{action.eyebrow}</span> : null}
              <strong>{action.label}</strong>
            </button>
          ))}
        </div>
      ) : null}
      {sections.map((section) => (
        <details key={section.id} className="markdown-editor-toolbar__section" open={section.defaultOpen}>
          <summary>{section.title}</summary>
          <div className="markdown-editor-toolbar__actions">
            {section.actions.map((action) => (
              <button
                key={action.id}
                type="button"
                onClick={action.onClick}
                disabled={action.disabled}
                aria-pressed={action.pressed}
              >
                {action.eyebrow ? <span>{action.eyebrow}</span> : null}
                <strong>{action.label}</strong>
              </button>
            ))}
          </div>
          {section.panel}
        </details>
      ))}
    </div>
  );
}
