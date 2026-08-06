import { useEffect, useMemo, useState } from "react";

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
import { BuildReferenceCapability } from "./reference/BuildReferenceCapability";
import { BUILD_SURFACE_LABEL, BUILD_SURFACE_ROUTE } from "./buildSurfaceConfig";
import {
  BUILD_KNOWN_CAMPAIGN_IDS,
  bareBuildAutoCreateKey,
  resolveBareBuildCampaignId,
  writeBuildLastCampaignId,
} from "./buildBareEntryCampaign";
import "./buildSurface.css";

const DEFAULT_DRAFT_TITLE = "Untitled worldbuilding source";
const DEFAULT_DOCUMENT_CLASS = "lore";
const DEFAULT_AUTHORITY_STATE: WorldbuildingAuthorityState = "draft";
const DEFAULT_VISIBILITY_STATE: WorldbuildingVisibilityState = "internal";

function navigateToDocument(documentId: string, campaignId: string): void {
  const url = new URL(window.location.href);
  url.pathname = BUILD_SURFACE_ROUTE;
  url.searchParams.set("documentId", documentId);
  url.searchParams.set("campaign", campaignId);
  window.history.pushState({}, "", url.toString());
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function chooseCampaignOnBareBuild(campaignId: string): void {
  const url = new URL(window.location.href);
  url.pathname = BUILD_SURFACE_ROUTE;
  url.searchParams.set("campaign", campaignId.trim());
  writeBuildLastCampaignId(campaignId);
  window.history.pushState({}, "", url.toString());
  window.dispatchEvent(new PopStateEvent("popstate"));
}

type BareCreateResult = { documentId: string; campaignId: string };

type BareCreateLatch = {
  key: string;
  promise: Promise<BareCreateResult>;
} | null;

/**
 * Module-scoped create latch so React StrictMode's effect rehearsal cannot
 * mint two workspace documents for one bare `/build` entry identity.
 * Keyed by campaign so route/campaign replacement cannot reuse a stale create.
 */
let bareBuildAutoCreateLatch: BareCreateLatch = null;

/** @internal Vitest helper — clears the bare-entry create latch between tests. */
export function resetBuildBareEntryAutoCreateForTests(): void {
  bareBuildAutoCreateLatch = null;
}

function startBareBuildAutoCreate(campaignId: string): Promise<BareCreateResult> {
  const key = bareBuildAutoCreateKey(campaignId);
  if (bareBuildAutoCreateLatch?.key === key) {
    return bareBuildAutoCreateLatch.promise;
  }
  const promise = createWorkspaceDocument({
    title: DEFAULT_DRAFT_TITLE,
    campaign_id: campaignId,
    kind: "worldbuilding_source",
    source_domain: "worldbuilding",
    document_class: DEFAULT_DOCUMENT_CLASS,
    authority_state: DEFAULT_AUTHORITY_STATE,
    visibility_state: DEFAULT_VISIBILITY_STATE,
  }).then((created) => ({
    documentId: created.document_id,
    campaignId,
  }));
  bareBuildAutoCreateLatch = { key, promise };
  return promise;
}

/** Route + last-Build memory only — do not subscribe to AgentInteraction here (lease publish loops). */
function useBareBuildCampaignId(): string | null {
  const [locationSearch, setLocationSearch] = useState(
    () => (typeof window !== "undefined" ? window.location.search : ""),
  );

  useEffect(() => {
    const sync = () => setLocationSearch(window.location.search);
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  return useMemo(
    () => resolveBareBuildCampaignId({ search: locationSearch }),
    [locationSearch],
  );
}

export function BuildSurfacePage() {
  const documentId = useWorkspaceDocumentUrlSelection();
  const bareCampaignId = useBareBuildCampaignId();
  const [openingError, setOpeningError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (documentId) {
      bareBuildAutoCreateLatch = null;
      return;
    }
    if (!bareCampaignId) {
      return;
    }

    const createKey = bareBuildAutoCreateKey(bareCampaignId);
    let cancelled = false;
    setOpeningError(null);

    void startBareBuildAutoCreate(bareCampaignId)
      .then((created) => {
        if (cancelled) return;
        const liveCampaign = resolveBareBuildCampaignId({
          search: window.location.search,
        });
        if (bareBuildAutoCreateKey(created.campaignId) !== createKey) return;
        if (!liveCampaign || bareBuildAutoCreateKey(liveCampaign) !== createKey) return;
        writeBuildLastCampaignId(created.campaignId);
        navigateToDocument(created.documentId, created.campaignId);
      })
      .catch((error: unknown) => {
        if (bareBuildAutoCreateLatch?.key === createKey) {
          bareBuildAutoCreateLatch = null;
        }
        if (cancelled) return;
        setOpeningError(
          error instanceof Error ? error.message : "Unable to open worldbuilding source.",
        );
      });

    return () => {
      cancelled = true;
    };
  }, [bareCampaignId, documentId, retryToken]);

  useEffect(() => {
    if (!documentId || !bareCampaignId) return;
    writeBuildLastCampaignId(bareCampaignId);
  }, [bareCampaignId, documentId]);

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
          ) : bareCampaignId ? (
            <p>Opening worldbuilding source…</p>
          ) : (
            <div className="build-surface-campaign-pick" data-testid="build-campaign-pick">
              <p>Choose a campaign for this worldbuilding source.</p>
              <div className="build-surface-campaign-pick__actions">
                {BUILD_KNOWN_CAMPAIGN_IDS.map((campaignId) => (
                  <button
                    key={campaignId}
                    type="button"
                    data-testid={`build-campaign-pick-${campaignId}`}
                    onClick={() => chooseCampaignOnBareBuild(campaignId)}
                  >
                    {campaignId}
                  </button>
                ))}
              </div>
            </div>
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
