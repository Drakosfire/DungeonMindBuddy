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
}

export interface AppChromeTools {
  pinnedActions?: AppChromeAction[];
  sections?: AppChromeToolSection[];
}

interface AppChromeProps {
  activeRoute: AppRouteKey;
  pageActions?: AppChromeAction[];
  editorTools?: AppChromeTools | null;
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

export function AppChrome({ activeRoute, pageActions = [], editorTools, children }: AppChromeProps) {
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const pinnedActions = editorTools?.pinnedActions ?? [];
  const sections = editorTools?.sections ?? [];
  const hasEditTools = pinnedActions.length > 0 || sections.length > 0;
  const hasPageTools = pageActions.length > 0;

  return (
    <div className="app-shell">
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

      <div className={`app-edit-toolbox${isEditOpen ? " open" : ""}`}>
        <button
          type="button"
          className="app-edit-toolbox-toggle"
          onClick={() => setIsEditOpen((current) => !current)}
          aria-expanded={isEditOpen}
          aria-controls="app-edit-toolbox-drawer"
          title="Edit"
        >
          Edit
        </button>
        <div
          className="app-edit-toolbox-backdrop"
          hidden={!isEditOpen}
          onClick={() => setIsEditOpen(false)}
          aria-hidden="true"
        />
        <aside id="app-edit-toolbox-drawer" className="app-edit-toolbox-drawer" aria-label="Edit toolbar">
          <header className="app-edit-toolbox-hd">
            <div>
              <div className="app-edit-toolbox-eyebrow">Command Board</div>
              <h2 className="app-edit-toolbox-title">Edit</h2>
            </div>
            <button
              type="button"
              className="app-edit-toolbox-close"
              onClick={() => setIsEditOpen(false)}
              aria-label="Close Edit"
            >
              x
            </button>
          </header>
          <nav className="app-edit-toolbox-nav" aria-label="Edit tool groups">
            <button type="button" className="app-edit-toolbox-nav-btn active">
              {hasEditTools ? "Tiptap" : "No tools"}
            </button>
          </nav>
          <div className="app-edit-toolbox-body">
            {hasEditTools ? (
              <>
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
                    <div className="app-edit-fold-bd app-edit-actions">
                      {section.actions.map((action) => (
                        <ChromeActionButton key={action.id} action={action} />
                      ))}
                    </div>
                  </details>
                ))}
              </>
            ) : (
              <p className="app-edit-empty">No edit tools for this surface.</p>
            )}
          </div>
        </aside>
      </div>

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
              {hasPageTools ? "Page" : "No tools"}
            </button>
          </nav>
          <div className="app-tools-toolbox-body">
            {hasPageTools ? (
              <details className="app-tools-fold" open>
                <summary>Page tools</summary>
                <div className="app-tools-fold-bd app-tools-actions">
                  {pageActions.map((action) => (
                    <ChromeActionButton key={action.id} action={action} />
                  ))}
                </div>
              </details>
            ) : (
              <p className="app-tools-empty">No tools for this surface.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
