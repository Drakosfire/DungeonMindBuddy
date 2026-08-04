import { type ReactNode, useLayoutEffect, useRef, useState } from "react";

import {
  BLANK_COMMAND_TARGET,
  buildAppChromeCompatibilityFragment,
} from "../agentInteraction/surfaceInteractionCompat";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import {
  EditHost,
  type LegacyEditPanelAttachment,
} from "../surfaceInteraction/editHost/EditHost";
import type { SurfaceInteractionWorkObjectIdentity } from "../surfaceInteraction/types";
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

function buildLegacyEditPanels(
  editorTools: AppChromeTools | null | undefined,
  workObject: SurfaceInteractionWorkObjectIdentity | null,
): LegacyEditPanelAttachment[] {
  const target = workObject ?? BLANK_COMMAND_TARGET;
  const sections = editorTools?.sections ?? [];
  const panels: LegacyEditPanelAttachment[] = [];
  for (let index = 0; index < sections.length; index += 1) {
    const section = sections[index];
    if (!section?.panel) continue;
    panels.push({
      groupId: section.id,
      groupLabel: section.title,
      groupOrder: index,
      ...(section.defaultOpen !== undefined
        ? { groupDefaultOpen: section.defaultOpen }
        : {}),
      target,
      panel: section.panel,
    });
  }
  return panels;
}

function targetsMatch(
  left: { kind: string; id: string },
  right: SurfaceInteractionWorkObjectIdentity | null,
): boolean {
  if (!right) return false;
  return left.kind === right.kind && left.id === right.id;
}

export function AppChrome({
  activeRoute,
  pageActions = [],
  editorTools,
  editToolboxLayout = "overlay",
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
  const pinnedSignature = JSON.stringify(
    (editorTools?.pinnedActions ?? []).map((action) => [
      action.id,
      action.disabled === true,
      action.label,
      action.eyebrow ?? null,
      action.pressed === true,
      callbackIdentityKey(action.onClick),
    ]),
  );
  const sectionSignature = JSON.stringify(
    (editorTools?.sections ?? []).map((section) => [
      section.id,
      section.title,
      section.defaultOpen === true,
      section.actions.map((action) => [
        action.id,
        action.disabled === true,
        action.label,
        action.eyebrow ?? null,
        action.pressed === true,
        callbackIdentityKey(action.onClick),
      ]),
    ]),
  );

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
  const hasEffectivePublication = effectivePublication != null;
  const workObject = basePublication?.canvas?.workObject ?? null;
  const legacyPanels = buildLegacyEditPanels(editorTools, workObject);

  const matchingEditCommands = (effectivePublication?.editCommands ?? []).filter((command) =>
    targetsMatch(command.target, effectivePublication?.canvas?.workObject ?? null),
  );
  const matchingLegacyPanels = legacyPanels.filter((panel) =>
    targetsMatch(panel.target, effectivePublication?.canvas?.workObject ?? null),
  );
  const hasEditContent =
    matchingEditCommands.length > 0 || matchingLegacyPanels.length > 0;

  const [isEditOpen, setIsEditOpen] = useState(editToolboxLayout === "dock");
  const isDockedEdit = editToolboxLayout === "dock" && hasEditContent;

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
    pinnedSignature,
    sectionSignature,
  ]);

  const shellClassName = [
    "app-shell",
    isDockedEdit ? "app-shell--edit-dock" : "",
    isDockedEdit && isEditOpen ? "app-shell--edit-dock-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const editHost = (
    <EditHost
      layout={editToolboxLayout}
      legacyPanels={legacyPanels}
      onOpenChange={setIsEditOpen}
    />
  );

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
        {editToolboxLayout === "dock" ? editHost : null}
        {mainContent}
      </div>

      {editToolboxLayout !== "dock" ? editHost : null}
      {/* Tool launcher DOM lives in surfaceInteraction/toolHost/ToolHost (BLD-SIH-04).
          Edit command DOM lives in surfaceInteraction/editHost/EditHost (BLD-SIH-05).
          pageActions / editorTools still publish through the chrome compatibility fragment above. */}
    </div>
  );
}
