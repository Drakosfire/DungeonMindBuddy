import { type ReactNode, useLayoutEffect, useRef } from "react";

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
import {
  SurfaceContextHost,
} from "../surfaceInteraction/contextHost";
import { APP_NAV_ITEMS, type AppRouteKey } from "./appChromeConfig";
import { AppChromeWorldGraphStatus } from "./AppChromeWorldGraphStatus";
import { appendLensQueryToHref } from "../graphLens/sessionCampaignContext";

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

/** Distinguishes absent / false / true for signature-driven republication. */
function encodeOptionalBoolean(value: boolean | undefined): 0 | 1 | 2 {
  if (value === undefined) return 0;
  if (value === false) return 1;
  return 2;
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

export interface AppChromeToolsGeneration {
  target: SurfaceInteractionWorkObjectIdentity;
  tools: AppChromeTools;
}

interface AppChromeProps {
  activeRoute: AppRouteKey;
  pageActions?: AppChromeAction[];
  editorTools?: AppChromeToolsGeneration | null;
  editToolboxLayout?: "overlay" | "dock";
  children: ReactNode;
}

function isValidEditTarget(
  target: SurfaceInteractionWorkObjectIdentity | null | undefined,
): target is SurfaceInteractionWorkObjectIdentity {
  if (!target) return false;
  return target.kind.trim() !== "" && target.id.trim() !== "";
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

function hasEditorToolsContent(tools: AppChromeTools | null | undefined): boolean {
  if (!tools) return false;
  if ((tools.pinnedActions?.length ?? 0) > 0) return true;
  return (tools.sections ?? []).some(
    (section) => section.actions.length > 0 || section.panel != null,
  );
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
  const generationTools = editorTools?.tools;
  const pageActionSignature = JSON.stringify(
    pageActions.map((action) => [
      action.id,
      action.disabled === true,
      action.label,
      action.eyebrow ?? null,
      callbackIdentityKey(action.onClick),
    ]),
  );
  const targetSignature = JSON.stringify(
    editorTools?.target
      ? [editorTools.target.kind, editorTools.target.id]
      : null,
  );
  const pinnedSignature = JSON.stringify(
    (generationTools?.pinnedActions ?? []).map((action) => [
      action.id,
      action.disabled === true,
      action.label,
      action.eyebrow ?? null,
      encodeOptionalBoolean(action.pressed),
      callbackIdentityKey(action.onClick),
    ]),
  );
  const sectionSignature = JSON.stringify(
    (generationTools?.sections ?? []).map((section) => [
      section.id,
      section.title,
      encodeOptionalBoolean(section.defaultOpen),
      section.panel != null,
      section.actions.map((action) => [
        action.id,
        action.disabled === true,
        action.label,
        action.eyebrow ?? null,
        encodeOptionalBoolean(action.pressed),
        callbackIdentityKey(action.onClick),
      ]),
    ]),
  );
  const editorToolsGenerationSignature = `${targetSignature}|${pinnedSignature}|${sectionSignature}`;

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

  const suppliedTarget = editorTools && isValidEditTarget(editorTools.target)
    ? editorTools.target
    : null;
  const shouldPublishEditInventory = suppliedTarget != null
    && hasEditorToolsContent(generationTools);

  const legacyPanels = shouldPublishEditInventory
    ? buildLegacyEditPanels(generationTools, suppliedTarget)
    : [];

  const matchingEditCommands = (effectivePublication?.editCommands ?? []).filter((command) =>
    targetsMatch(command.target, effectivePublication?.canvas?.workObject ?? null),
  );
  const matchingLegacyPanels = legacyPanels.filter((panel) =>
    targetsMatch(panel.target, effectivePublication?.canvas?.workObject ?? null),
  );
  const hasEditContent =
    matchingEditCommands.length > 0 || matchingLegacyPanels.length > 0;

  const isDockedEdit = editToolboxLayout === "dock" && hasEditContent;

  useLayoutEffect(() => {
    const publish = publishAppChromeCompatibilityRef.current;
    const currentBase = agentInteractionRef.current?.surfaceInteractionBasePublication ?? null;
    if (!publish || !currentBase) return;
    const currentGeneration = editorToolsRef.current;
    const currentTarget = currentGeneration && isValidEditTarget(currentGeneration.target)
      ? currentGeneration.target
      : null;
    const currentTools = currentGeneration?.tools;
    const publishEditInventory = currentTarget != null
      && hasEditorToolsContent(currentTools);
    return publish(
      buildAppChromeCompatibilityFragment({
        pageActions: pageActionsRef.current,
        editorTools: publishEditInventory ? currentTools : null,
        basePublication: currentBase,
        editCommandTarget: publishEditInventory ? currentTarget : null,
      }),
    );
    // Intentionally omit `basePublication` object identity: every lease
    // bind/update allocates a new publication reference; depending on it
    // re-fires this effect → chrome unregister/register → Maximum update depth
    // when a surface also updates publication every render (Build).
  }, [
    basePublicationSyncKey,
    hasEffectivePublication,
    agentInteraction.publishAppChromeCompatibility,
    pageActionSignature,
    editorToolsGenerationSignature,
  ]);

  const shellClassName = [
    "app-shell",
    isDockedEdit ? "app-shell--edit-dock" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const editHost = (
    <EditHost
      layout={editToolboxLayout}
      legacyPanels={legacyPanels}
    />
  );

  const mainContent = (
    <div className="app-wrap">
      <header className="app-chrome-header" data-testid="app-chrome-header">
        <nav className="app-site-nav" aria-label="Command board navigation">
          <div className="app-site-nav__routes">
            {APP_NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className={item.route === activeRoute ? "active" : undefined}
                onClick={(event) => {
                  // Read lens at click time so World Graph replaceState updates ride along.
                  const next = appendLensQueryToHref(item.href);
                  if (next === item.href) return;
                  event.preventDefault();
                  window.location.assign(next);
                }}
              >
                {item.label}
              </a>
            ))}
          </div>
          <AppChromeWorldGraphStatus />
        </nav>
        <SurfaceContextHost />
      </header>

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
