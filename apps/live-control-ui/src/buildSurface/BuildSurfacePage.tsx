import { useEffect, useState } from "react";

import { createWorkspaceDocument } from "../api/liveApi";
import type {
  WorldbuildingAuthorityState,
  WorldbuildingVisibilityState,
} from "../api/types";
import { AppChrome } from "../chrome/AppChrome";
import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { useWorkspaceDocumentUrlSelection } from "../workspaceDocument/useWorkspaceDocumentUrlSelection";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceShell } from "./BuildSurfaceShell";
import { parseBuildGraphPointerFromLocation } from "./BuildGraphObjectContext";
import { BuildReferenceCapability } from "./reference/BuildReferenceCapability";
import { BUILD_SURFACE_LABEL, BUILD_SURFACE_ROUTE } from "./buildSurfaceConfig";
import "./buildSurface.css";

const DEFAULT_DRAFT_TITLE = "Untitled worldbuilding source";
const DEFAULT_CAMPAIGN_ID = "longmont-c2";
const DEFAULT_DOCUMENT_CLASS = "lore";
const DEFAULT_AUTHORITY_STATE: WorldbuildingAuthorityState = "draft";
const DEFAULT_VISIBILITY_STATE: WorldbuildingVisibilityState = "internal";

function navigateToDocument(documentId: string): void {
  const url = new URL(window.location.href);
  url.pathname = BUILD_SURFACE_ROUTE;
  url.searchParams.set("documentId", documentId);
  window.history.pushState({}, "", url.toString());
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function resolveDefaultCampaignId(): string {
  const fromPointer = parseBuildGraphPointerFromLocation()?.campaignId?.trim();
  if (fromPointer) return fromPointer;
  const fromUrl = new URL(window.location.href).searchParams.get("campaign")?.trim();
  if (fromUrl) return fromUrl;
  return DEFAULT_CAMPAIGN_ID;
}

/**
 * Module-scoped create latch so React StrictMode's effect rehearsal cannot
 * mint two workspace documents for one bare `/build` entry.
 */
let bareBuildAutoCreatePromise: Promise<string> | null = null;

/** @internal Vitest helper — clears the bare-entry create latch between tests. */
export function resetBuildBareEntryAutoCreateForTests(): void {
  bareBuildAutoCreatePromise = null;
}

function startBareBuildAutoCreate(): Promise<string> {
  if (!bareBuildAutoCreatePromise) {
    bareBuildAutoCreatePromise = createWorkspaceDocument({
      title: DEFAULT_DRAFT_TITLE,
      campaign_id: resolveDefaultCampaignId(),
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: DEFAULT_DOCUMENT_CLASS,
      authority_state: DEFAULT_AUTHORITY_STATE,
      visibility_state: DEFAULT_VISIBILITY_STATE,
    }).then((created) => created.document_id);
  }
  return bareBuildAutoCreatePromise;
}

export function BuildSurfacePage() {
  const documentId = useWorkspaceDocumentUrlSelection();
  const [openingError, setOpeningError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (documentId) {
      bareBuildAutoCreatePromise = null;
      return;
    }

    let cancelled = false;
    setOpeningError(null);

    void startBareBuildAutoCreate()
      .then((createdId) => {
        if (cancelled) return;
        navigateToDocument(createdId);
      })
      .catch((error: unknown) => {
        bareBuildAutoCreatePromise = null;
        if (cancelled) return;
        setOpeningError(
          error instanceof Error ? error.message : "Unable to open worldbuilding source.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, [documentId, retryToken]);

  if (!documentId) {
    return (
      <AppChrome activeRoute="build">
        <BuildReferenceCapability documentId={null} />
        <main className="build-surface-opening" data-testid="build-opening-draft">
          <h1>{BUILD_SURFACE_LABEL}</h1>
          {openingError ? (
            <>
              <p role="alert">{openingError}</p>
              <button
                type="button"
                data-testid="build-opening-retry"
                onClick={() => {
                  setOpeningError(null);
                  setRetryToken((token) => token + 1);
                }}
              >
                Retry
              </button>
            </>
          ) : (
            <p>Opening worldbuilding source…</p>
          )}
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="build">
      <MarkdownCanvasSessionProvider
        key={documentId}
        documentId={documentId}
        surface={BUILD_MARKDOWN_CANVAS.surface}
        kind={BUILD_MARKDOWN_CANVAS.kind}
        saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
      >
        <BuildReferenceCapability documentId={documentId} />
        <BuildIngestToolbar documentId={documentId} />
        <BuildSurfaceShell />
      </MarkdownCanvasSessionProvider>
    </AppChrome>
  );
}
