import { type ReactNode, useState } from "react";

import { APP_NAV_ITEMS, type AppRouteKey } from "./appChromeConfig";

export interface AppChromeAction {
  id: string;
  label: string;
  eyebrow?: string;
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
}

export interface AppChromeToolSection {
  id: string;
  title: string;
  actions: AppChromeAction[];
  defaultOpen?: boolean;
  /** Optional rich panel under the section actions (e.g. graph search). */
  panel?: ReactNode;
}

export interface AppChromeTools {
  pinnedActions?: AppChromeAction[];
  sections?: AppChromeToolSection[];
}

interface AppChromeProps {
  activeRoute: AppRouteKey;
  pageActions?: AppChromeAction[];
  editorTools?: AppChromeTools | null;
  editToolboxLayout?: "overlay" | "dock";
  children: ReactNode;
}

function ChromeActionButton({ action }: { action: AppChromeAction }) {
  return (
    <button type="button" onClick={action.onClick} disabled={action.disabled} aria-pressed={action.pressed}>
      {action.eyebrow ? <span>{action.eyebrow}</span> : null}
      <strong>{action.label}</strong>
    </button>
  );
}

interface EditToolboxDrawerProps {
  pinnedActions: AppChromeAction[];
  sections: AppChromeToolSection[];
  onClose: () => void;
}

function EditToolboxDrawer({ pinnedActions, sections, onClose }: EditToolboxDrawerProps) {
  return (
    <aside id="app-edit-toolbox-drawer" className="app-edit-toolbox-drawer" aria-label="Edit toolbar">
      <header className="app-edit-toolbox-hd">
        <div>
          <div className="app-edit-toolbox-eyebrow">Command Board</div>
          <h2 className="app-edit-toolbox-title">Edit</h2>
        </div>
        <button type="button" className="app-edit-toolbox-close" onClick={onClose} aria-label="Close Edit">
          x
        </button>
      </header>
      <nav className="app-edit-toolbox-nav" aria-label="Edit tool groups">
        <button type="button" className="app-edit-toolbox-nav-btn active">
          Tiptap
        </button>
      </nav>
      <div className="app-edit-toolbox-body">
        {pinnedActions.length > 0 ? (
          <details className="app-edit-fold" open>
            <summary>Edit state</summary>
            <div className="app-edit-fold-bd app-edit-actions">
              {pinnedActions.map((action) => (
                <ChromeActionButton key={action.id} action={action} />
              ))}
            </div>
          </details>
        ) : null}

        {sections.map((section) => (
          <details key={section.id} className="app-edit-fold" open={section.defaultOpen}>
            <summary>{section.title}</summary>
            <div className="app-edit-fold-bd">
              {section.actions.length > 0 ? (
                <div className="app-edit-actions">
                  {section.actions.map((action) => (
                    <ChromeActionButton key={action.id} action={action} />
                  ))}
                </div>
              ) : null}
              {section.panel ? <div className="app-edit-fold-panel">{section.panel}</div> : null}
            </div>
          </details>
        ))}
      </div>
    </aside>
  );
}

interface EditToolboxProps {
  layout: "overlay" | "dock";
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
  pinnedActions: AppChromeAction[];
  sections: AppChromeToolSection[];
}

function EditToolbox({
  layout,
  isOpen,
  onToggle,
  onClose,
  pinnedActions,
  sections,
}: EditToolboxProps) {
  const isDocked = layout === "dock";

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
    >
      <button
        type="button"
        className="app-edit-toolbox-toggle"
        onClick={onToggle}
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
        onClick={onClose}
        aria-hidden="true"
      />
      {isOpen ? <EditToolboxDrawer pinnedActions={pinnedActions} sections={sections} onClose={onClose} /> : null}
    </div>
  );
}

export function AppChrome({
  activeRoute,
  pageActions = [],
  editorTools,
  editToolboxLayout = "overlay",
  children,
}: AppChromeProps) {
  const [isEditOpen, setIsEditOpen] = useState(editToolboxLayout === "dock");
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const pinnedActions = editorTools?.pinnedActions ?? [];
  const sections = editorTools?.sections ?? [];
  const hasEditTools = pinnedActions.length > 0 || sections.length > 0;
  const hasPageTools = pageActions.length > 0;
  const isDockedEdit = editToolboxLayout === "dock" && hasEditTools;

  const shellClassName = [
    "app-shell",
    isDockedEdit ? "app-shell--edit-dock" : "",
    isDockedEdit && isEditOpen ? "app-shell--edit-dock-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const mainContent = (
    <div className="app-wrap">
      <nav className="app-site-nav" aria-label="Command board navigation">
        {APP_NAV_ITEMS.map((item) => (
          <a key={item.href} href={item.href} className={item.route === activeRoute ? "active" : undefined}>
            {item.label}
          </a>
        ))}
      </nav>

      {children}
    </div>
  );

  return (
    <div className={shellClassName}>
      <div className="app-shell-layout">
        {isDockedEdit ? (
          <EditToolbox
            layout="dock"
            isOpen={isEditOpen}
            onToggle={() => setIsEditOpen((current) => !current)}
            onClose={() => setIsEditOpen(false)}
            pinnedActions={pinnedActions}
            sections={sections}
          />
        ) : null}
        {mainContent}
      </div>

      {hasEditTools && !isDockedEdit ? (
        <EditToolbox
          layout="overlay"
          isOpen={isEditOpen}
          onToggle={() => setIsEditOpen((current) => !current)}
          onClose={() => setIsEditOpen(false)}
          pinnedActions={pinnedActions}
          sections={sections}
        />
      ) : null}

      {hasPageTools ? (
        <div className={`app-tools-toolbox${isToolsOpen ? " open" : ""}`}>
          <button
            type="button"
            className="app-tools-toolbox-toggle"
            onClick={() => setIsToolsOpen((current) => !current)}
            aria-expanded={isToolsOpen}
            aria-controls="app-tools-toolbox-drawer"
            title="Tools"
          >
            Tools
          </button>
          <div
            className="app-tools-toolbox-backdrop"
            hidden={!isToolsOpen}
            onClick={() => setIsToolsOpen(false)}
            aria-hidden="true"
          />
          <aside id="app-tools-toolbox-drawer" className="app-tools-toolbox-drawer" aria-label="Tools toolbar">
            <header className="app-tools-toolbox-hd">
              <div>
                <div className="app-tools-toolbox-eyebrow">Command Board</div>
                <h2 className="app-tools-toolbox-title">Tools</h2>
              </div>
              <button
                type="button"
                className="app-tools-toolbox-close"
                onClick={() => setIsToolsOpen(false)}
                aria-label="Close Tools"
              >
                x
              </button>
            </header>
            <nav className="app-tools-toolbox-nav" aria-label="Tool groups">
              <button type="button" className="app-tools-toolbox-nav-btn active">
                Page
              </button>
            </nav>
            <div className="app-tools-toolbox-body">
              <details className="app-tools-fold" open>
                <summary>Page tools</summary>
                <div className="app-tools-fold-bd app-tools-actions">
                  {pageActions.map((action) => (
                    <ChromeActionButton key={action.id} action={action} />
                  ))}
                </div>
              </details>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
