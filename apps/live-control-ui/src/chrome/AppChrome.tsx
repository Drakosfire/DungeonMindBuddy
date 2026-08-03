import { type ReactNode, useLayoutEffect, useRef, useState } from "react";

import { buildAppChromeCompatibilityFragment } from "../agentInteraction/surfaceInteractionCompat";
import {
  resolveGuardedEditInvoke,
  resolveGuardedToolInvoke,
} from "../agentInteraction/surfaceInteractionLease";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { APP_NAV_ITEMS, type AppRouteKey } from "./appChromeConfig";

const callbackIdentityKeys = new WeakMap<() => void, number>();
let nextCallbackIdentityKey = 1;

function callbackIdentityKey(callback: () => void): number {
  let key = callbackIdentityKeys.get(callback);
  if (key === undefined) {
    key = nextCallbackIdentityKey;
    nextCallbackIdentityKey += 1;
    callbackIdentityKeys.set(callback, key);
  }
  return key;
}

export interface AppChromeAction {
  id: string;
  label: string;
  eyebrow?: string;
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
}

/** Read-only site-nav status (graph load, etc.) — not a lease-guarded command. */
export interface AppChromeNavbarStatus {
  id: string;
  label: string;
  eyebrow?: string;
  tone?: "neutral" | "loading" | "ready" | "error" | "unavailable";
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
  /** Persistent read-only status in the site nav (e.g. World Graph load). */
  navbarStatuses?: AppChromeNavbarStatus[];
  /** Persistent actions rendered in the site nav (write gate, Save, surface checkpoint). */
  navbarActions?: AppChromeAction[];
  pinnedActions?: AppChromeAction[];
  sections?: AppChromeToolSection[];
}

interface AppChromeProps {
  activeRoute: AppRouteKey;
  pageActions?: AppChromeAction[];
  editorTools?: AppChromeTools | null;
  editToolboxLayout?: "overlay" | "dock";
  /** Optional controlled Edit-dock open state. */
  editToolboxOpen?: boolean;
  onEditToolboxOpenChange?: (open: boolean) => void;
  children: ReactNode;
}

interface GuardedActionButtonProps {
  action: AppChromeAction;
  guardedInvoke: ((id: string) => (() => void | Promise<void>) | null) | null;
  leaseBridgeActive: boolean;
  hasEffectivePublication: boolean;
}

function GuardedActionButton({
  action,
  guardedInvoke,
  leaseBridgeActive,
  hasEffectivePublication,
}: GuardedActionButtonProps) {
  const guarded = leaseBridgeActive && hasEffectivePublication && guardedInvoke
    ? guardedInvoke(action.id)
    : null;
  const bypassAllowed = !leaseBridgeActive;
  const disabled = action.disabled || (leaseBridgeActive && (!hasEffectivePublication || !guarded));

  return (
    <button
      type="button"
      onClick={() => {
        if (guarded) {
          void guarded();
          return;
        }
        if (bypassAllowed) {
          action.onClick();
        }
      }}
      disabled={disabled}
      aria-pressed={action.pressed}
    >
      {action.eyebrow ? <span>{action.eyebrow}</span> : null}
      <strong>{action.label}</strong>
    </button>
  );
}

interface EditToolboxDrawerProps {
  pinnedActions: AppChromeAction[];
  sections: AppChromeToolSection[];
  onClose: () => void;
  resolveEditInvoke: ((id: string) => (() => void | Promise<void>) | null) | null;
  leaseBridgeActive: boolean;
  hasEffectivePublication: boolean;
}

function EditToolboxDrawer({
  pinnedActions,
  sections,
  onClose,
  resolveEditInvoke,
  leaseBridgeActive,
  hasEffectivePublication,
}: EditToolboxDrawerProps) {
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
                <GuardedActionButton
                  key={action.id}
                  action={action}
                  guardedInvoke={resolveEditInvoke}
                  leaseBridgeActive={leaseBridgeActive}
                  hasEffectivePublication={hasEffectivePublication}
                />
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
                    <GuardedActionButton
                      key={action.id}
                      action={action}
                      guardedInvoke={resolveEditInvoke}
                      leaseBridgeActive={leaseBridgeActive}
                      hasEffectivePublication={hasEffectivePublication}
                    />
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
  resolveEditInvoke: ((id: string) => (() => void | Promise<void>) | null) | null;
  leaseBridgeActive: boolean;
  hasEffectivePublication: boolean;
}

function EditToolbox({
  layout,
  isOpen,
  onToggle,
  onClose,
  pinnedActions,
  sections,
  resolveEditInvoke,
  leaseBridgeActive,
  hasEffectivePublication,
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
      {isOpen ? (
        <EditToolboxDrawer
          pinnedActions={pinnedActions}
          sections={sections}
          onClose={onClose}
          resolveEditInvoke={resolveEditInvoke}
          leaseBridgeActive={leaseBridgeActive}
          hasEffectivePublication={hasEffectivePublication}
        />
      ) : null}
    </div>
  );
}

export function AppChrome({
  activeRoute,
  pageActions = [],
  editorTools,
  editToolboxLayout = "overlay",
  editToolboxOpen,
  onEditToolboxOpenChange,
  children,
}: AppChromeProps) {
  const agentInteraction = useAgentInteraction();
  const pageActionsRef = useRef(pageActions);
  pageActionsRef.current = pageActions;
  const editorToolsRef = useRef(editorTools);
  editorToolsRef.current = editorTools;
  const pageActionSignature = JSON.stringify(
    pageActions.map((action) => [
      action.id,
      action.disabled === true,
      action.label,
      action.eyebrow ?? null,
      callbackIdentityKey(action.onClick),
    ]),
  );
  const navbarStatusSignature = JSON.stringify(
    (editorTools?.navbarStatuses ?? []).map((status) => [
      status.id,
      status.label,
      status.eyebrow ?? null,
      status.tone ?? null,
    ]),
  );
  const navbarSignature = JSON.stringify(
    (editorTools?.navbarActions ?? []).map((action) => [
      action.id,
      action.disabled === true,
      action.label,
      action.eyebrow ?? null,
      action.pressed === true,
      callbackIdentityKey(action.onClick),
    ]),
  );
  const pinnedSignature = JSON.stringify(
    (editorTools?.pinnedActions ?? []).map((action) => [
      action.id,
      action.disabled === true,
      action.label,
      action.eyebrow ?? null,
      callbackIdentityKey(action.onClick),
    ]),
  );
  const sectionSignature = JSON.stringify(
    (editorTools?.sections ?? []).map((section) => [
      section.id,
      section.title,
      section.actions.map((action) => [
        action.id,
        action.disabled === true,
        action.label,
        action.eyebrow ?? null,
        callbackIdentityKey(action.onClick),
      ]),
    ]),
  );
  const [uncontrolledEditOpen, setUncontrolledEditOpen] = useState(editToolboxLayout === "dock");
  const isEditOpen = editToolboxOpen ?? uncontrolledEditOpen;
  const setIsEditOpen = (next: boolean | ((current: boolean) => boolean)) => {
    const resolved = typeof next === "function" ? next(isEditOpen) : next;
    if (editToolboxOpen === undefined) {
      setUncontrolledEditOpen(resolved);
    }
    onEditToolboxOpenChange?.(resolved);
  };
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const navbarStatuses = editorTools?.navbarStatuses ?? [];
  const navbarActions = editorTools?.navbarActions ?? [];
  const pinnedActions = editorTools?.pinnedActions ?? [];
  const sections = editorTools?.sections ?? [];
  const hasEditTools = pinnedActions.length > 0 || sections.length > 0;
  const hasPageTools = pageActions.length > 0;
  const isDockedEdit = editToolboxLayout === "dock" && hasEditTools;
  const hasNavbarChrome = navbarStatuses.length > 0 || navbarActions.length > 0;

  const agentInteractionRef = useRef(agentInteraction);
  agentInteractionRef.current = agentInteraction;
  // Canonical base publication object identity changes on every bind/update, so
  // the bridge republishes under the current lease even when instanceKey alone
  // would collide across surfaceIds. Content tuple also tracks Canvas targets.
  const basePublication = agentInteraction?.surfaceInteractionBasePublication ?? null;
  const basePublicationSyncKey = JSON.stringify([
    basePublication?.identity.surfaceId ?? null,
    basePublication?.identity.instanceKey ?? null,
    basePublication?.canvas?.canvasId ?? null,
    basePublication?.canvas?.workObject.kind ?? null,
    basePublication?.canvas?.workObject.id ?? null,
  ]);

  const publishAppChromeCompatibilityRef = useRef(agentInteraction.publishAppChromeCompatibility);
  publishAppChromeCompatibilityRef.current = agentInteraction.publishAppChromeCompatibility;

  const effectivePublication = agentInteraction?.surfaceInteractionPublication ?? null;
  const leaseBridgeActive = agentInteraction != null;
  const hasEffectivePublication = effectivePublication != null;

  useLayoutEffect(() => {
    const publish = publishAppChromeCompatibilityRef.current;
    const currentBase = agentInteractionRef.current?.surfaceInteractionBasePublication ?? null;
    if (!publish || !currentBase) return;
    return publish(
      buildAppChromeCompatibilityFragment({
        pageActions: pageActionsRef.current,
        editorTools: editorToolsRef.current,
        basePublication: currentBase,
      }),
    );
  }, [
    basePublication,
    basePublicationSyncKey,
    hasEffectivePublication,
    agentInteraction.publishAppChromeCompatibility,
    pageActionSignature,
    navbarStatusSignature,
    navbarSignature,
    pinnedSignature,
    sectionSignature,
  ]);

  const resolveToolInvoke = leaseBridgeActive
    ? (id: string) => resolveGuardedToolInvoke(effectivePublication, id)
    : null;
  const resolveEditInvoke = leaseBridgeActive
    ? (id: string) => resolveGuardedEditInvoke(effectivePublication, id)
    : null;

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
        {hasNavbarChrome ? (
          <div className="app-site-nav-actions" role="group" aria-label="Surface navbar chrome">
            {navbarStatuses.length > 0 ? (
              <div className="app-site-nav-statuses" role="status" aria-label="Surface status">
                {navbarStatuses.map((status) => (
                  <div
                    key={status.id}
                    className={[
                      "app-site-nav-status",
                      status.tone ? `app-site-nav-status--${status.tone}` : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    data-testid={status.id}
                  >
                    {status.eyebrow ? <span>{status.eyebrow}</span> : null}
                    <strong>{status.label}</strong>
                  </div>
                ))}
              </div>
            ) : null}
            {navbarActions.map((action) => (
              <GuardedActionButton
                key={action.id}
                action={action}
                guardedInvoke={resolveEditInvoke}
                leaseBridgeActive={leaseBridgeActive}
                hasEffectivePublication={hasEffectivePublication}
              />
            ))}
          </div>
        ) : null}
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
            resolveEditInvoke={resolveEditInvoke}
            leaseBridgeActive={leaseBridgeActive}
            hasEffectivePublication={hasEffectivePublication}
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
          resolveEditInvoke={resolveEditInvoke}
          leaseBridgeActive={leaseBridgeActive}
          hasEffectivePublication={hasEffectivePublication}
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
                    <GuardedActionButton
                      key={action.id}
                      action={action}
                      guardedInvoke={resolveToolInvoke}
                      leaseBridgeActive={leaseBridgeActive}
                      hasEffectivePublication={hasEffectivePublication}
                    />
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
