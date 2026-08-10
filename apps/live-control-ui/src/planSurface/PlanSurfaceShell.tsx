import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import { useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { buildPlanSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import { listWorkspaceDocuments } from "../api/liveApi";
import type { PlanViewProjection, WorkspaceDocumentRecord } from "../api/types";
import { PlanAgentInteractionBar } from "./components/PlanAgentInteractionBar";
import { PlanDocumentSelector } from "./components/PlanDocumentSelector";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { PlanDogfoodPanel } from "./dogfood/PlanDogfoodPanel";
import { dogfoodModeFromLocation } from "./dogfood/planDogfoodState";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import { planDocumentSelectionSearch, resolvePlanningDocument } from "./config/planSessionDescriptor";
import { EditCapabilityProvider } from "./edit/editCapability";
import { PlanReferenceProjectionBinding } from "./reference/PlanReferenceProjectionBinding";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import type { PlanDocumentDescriptor, PlanSurfaceConfig } from "./types";
import "./planSurface.css";

interface PlanSurfaceShellProps {
  planView: PlanViewProjection;
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
}

function themeStyle(config: PlanSurfaceConfig): CSSProperties {
  return (config.theme.tokens ?? {}) as CSSProperties;
}

export function PlanSurfaceShell({ planView, onEditorToolsChange }: PlanSurfaceShellProps) {
  const [locationSearch, setLocationSearch] = useState(
    () => (typeof window !== "undefined" ? window.location.search : ""),
  );
  const [planningDocument, setPlanningDocument] = useState<PlanDocumentDescriptor | null>(null);
  const [documentLoadStatus, setDocumentLoadStatus] = useState<"loading" | "ready" | "error">("loading");
  const [documentLoadError, setDocumentLoadError] = useState<string | null>(null);
  const [documentSwitching, setDocumentSwitching] = useState(false);
  const [documentSwitchError, setDocumentSwitchError] = useState<string | null>(null);
  const [selectorRecords, setSelectorRecords] = useState<WorkspaceDocumentRecord[] | null>(null);
  const [selectorListStatus, setSelectorListStatus] = useState<"loading" | "ready" | "error">("loading");

  const planningDocumentRef = useRef<PlanDocumentDescriptor | null>(null);
  planningDocumentRef.current = planningDocument;
  /** Monotonic generation so a stale resolution cannot clobber a newer document choice. */
  const documentLoadGenerationRef = useRef(0);
  const selectorListGenerationRef = useRef(0);

  const loadSelectorDocuments = useCallback(async () => {
    const generation = ++selectorListGenerationRef.current;
    setSelectorListStatus("loading");
    try {
      const list = await listWorkspaceDocuments({
        campaign_id: planView.campaign_id,
        kind: "plan",
        status: "active",
      });
      if (generation !== selectorListGenerationRef.current) return;
      setSelectorRecords(list.records);
      setSelectorListStatus("ready");
    } catch {
      if (generation !== selectorListGenerationRef.current) return;
      setSelectorListStatus("error");
    }
  }, [planView.campaign_id]);

  useEffect(() => {
    void loadSelectorDocuments();
  }, [loadSelectorDocuments]);

  /**
   * Single resolution path for initial load, browser navigation, and selector
   * switches. A resolution applies only while it is the newest request; a
   * failed switch keeps the current document authoritative and never falls
   * back to a different record.
   */
  const loadPlanningDocument = useCallback(
    async (search: string): Promise<boolean> => {
      const generation = ++documentLoadGenerationRef.current;
      const switching = planningDocumentRef.current != null;
      if (switching) {
        setDocumentSwitching(true);
        setDocumentSwitchError(null);
      } else {
        setDocumentLoadStatus("loading");
        setDocumentLoadError(null);
      }
      try {
        const document = await resolvePlanningDocument({ planView, locationSearch: search });
        if (generation !== documentLoadGenerationRef.current) return false;
        setPlanningDocument(document);
        setDocumentLoadStatus("ready");
        setDocumentSwitching(false);
        setDocumentSwitchError(null);
        void loadSelectorDocuments();
        return true;
      } catch (error) {
        if (generation !== documentLoadGenerationRef.current) return false;
        const message = error instanceof Error ? error.message : "Failed to load planning document";
        if (switching) {
          setDocumentSwitching(false);
          setDocumentSwitchError(message);
          setDocumentLoadStatus("ready");
        } else {
          setPlanningDocument(null);
          setDocumentLoadStatus("error");
          setDocumentLoadError(message);
        }
        return false;
      }
    },
    [loadSelectorDocuments, planView],
  );

  // Initial load and browser back/forward resolve the document the URL names.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => {
      setLocationSearch(window.location.search);
      void loadPlanningDocument(window.location.search);
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [loadPlanningDocument]);

  // Selector switches resolve the exact document first; only a successful
  // resolution earns a history entry and a URL naming it.
  const handleSelectPlanningDocument = useCallback(
    (documentId: string) => {
      if (typeof window === "undefined") return;
      if (documentId === planningDocumentRef.current?.documentId) return;
      const search = planDocumentSelectionSearch(window.location.search, documentId);
      void loadPlanningDocument(search).then((applied) => {
        if (!applied) return;
        window.history.pushState({}, "", `${window.location.pathname}${search}`);
        setLocationSearch(search);
      });
    },
    [loadPlanningDocument],
  );

  const config = useMemo(
    () => (planningDocument ? createPlanSurfaceConfig(planView, planningDocument, locationSearch) : null),
    [locationSearch, planView, planningDocument],
  );
  const { publishProjectionSurface, updateProjectionSurfaceConfig } = useAgentInteraction();

  // Identity registration and same-identity config updates are separate
  // operations: a config-only change (e.g. a document commit recreating the
  // config with an unchanged identity) must not unbind the surface lease.
  const publication = useMemo(
    () =>
      config
        ? {
            identity: buildPlanSurfaceIdentity({
              documentId: config.sessionDescriptor.planningDocument.documentId,
              campaignId: config.sessionDescriptor.campaignId,
              liveSession: config.context.liveSession,
              memorySession: config.sessionDescriptor.memorySession,
            }),
            config,
          }
        : null,
    [config],
  );
  const publicationInstanceKey = publication?.identity.instanceKey ?? null;
  const publicationRef = useRef(publication);
  publicationRef.current = publication;

  useEffect(() => {
    if (documentLoadStatus !== "ready" || !publicationRef.current) {
      return publishProjectionSurface(null);
    }
    return publishProjectionSurface(publicationRef.current);
  }, [documentLoadStatus, publicationInstanceKey, publishProjectionSurface]);

  useEffect(() => {
    if (documentLoadStatus !== "ready" || !publication) return;
    updateProjectionSurfaceConfig(publication);
  }, [documentLoadStatus, publication, updateProjectionSurfaceConfig]);

  const [saveStatusLabel, setSaveStatusLabel] = useState("Local draft · not yet saved to Markdown");
  const dogfoodMode = dogfoodModeFromLocation();

  if (documentLoadStatus === "loading" || !config) {
    return (
      <main className="app-status">
        <p>Loading planning document…</p>
      </main>
    );
  }

  if (documentLoadStatus === "error") {
    return (
      <main className="app-status app-error">
        <h1>Plan</h1>
        <p>{documentLoadError ?? "Unable to load planning document."}</p>
      </main>
    );
  }

  return (
    <EditCapabilityProvider>
      <PlanGraphReferenceResolverProvider sessionDescriptor={config.sessionDescriptor}>
        <PlanReferenceProjectionBinding />
        <div
          className="plan-surface-root"
          data-surface={config.id}
          data-md-theme={config.theme.themeId}
          style={themeStyle(config)}
        >
          {dogfoodMode ? (
            <PlanDogfoodPanel
              sessionDescriptor={config.sessionDescriptor}
              saveStatusLabel={saveStatusLabel}
            />
          ) : null}
          <div className="plan-surface-layout">
            <div className="plan-surface-main">
              <PlanDocumentSelector
                documents={selectorRecords}
                listStatus={selectorListStatus}
                activeDocument={config.sessionDescriptor.planningDocument}
                switching={documentSwitching}
                switchError={documentSwitchError}
                onSelect={handleSelectPlanningDocument}
                onRetryList={() => void loadSelectorDocuments()}
              />
              <PlanSurfaceCanvas
                sessionDescriptor={config.sessionDescriptor}
                theme={config.theme}
                onEditorToolsChange={onEditorToolsChange}
                onSaveStatusChange={setSaveStatusLabel}
                onPlanningDocumentCommitted={setPlanningDocument}
              />
            </div>
          </div>
          <PlanAgentInteractionBar planView={planView} sessionDescriptor={config.sessionDescriptor} />
        </div>
      </PlanGraphReferenceResolverProvider>
    </EditCapabilityProvider>
  );
}
