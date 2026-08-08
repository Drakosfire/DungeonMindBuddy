import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import { useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { buildPlanSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import type { PlanViewProjection } from "../api/types";
import { PlanAgentInteractionBar } from "./components/PlanAgentInteractionBar";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { PlanDogfoodPanel } from "./dogfood/PlanDogfoodPanel";
import { dogfoodModeFromLocation } from "./dogfood/planDogfoodState";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import {
  replaceDocumentIdInLocationSearch,
  resolvePlanningDocument,
} from "./config/planSessionDescriptor";
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
  const skipNextDocumentLoadRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => setLocationSearch(window.location.search);
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const loadPlanningDocument = useCallback(async () => {
    setDocumentLoadStatus("loading");
    setDocumentLoadError(null);
    try {
      const document = await resolvePlanningDocument({ planView, locationSearch });
      setPlanningDocument(document);
      setDocumentLoadStatus("ready");
    } catch (error) {
      setPlanningDocument(null);
      setDocumentLoadStatus("error");
      setDocumentLoadError(error instanceof Error ? error.message : "Failed to load planning document");
    }
  }, [locationSearch, planView]);

  useEffect(() => {
    if (skipNextDocumentLoadRef.current) {
      skipNextDocumentLoadRef.current = false;
      return;
    }
    void loadPlanningDocument();
  }, [loadPlanningDocument]);

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

  const switchPlanningDocument = useCallback((document: PlanDocumentDescriptor) => {
    const nextSearch = replaceDocumentIdInLocationSearch(
      typeof window !== "undefined" ? window.location.search : locationSearch,
      document.documentId,
    );
    if (typeof window !== "undefined") {
      const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;
      window.history.replaceState(window.history.state, "", nextUrl);
    }
    skipNextDocumentLoadRef.current = true;
    setPlanningDocument(document);
    setLocationSearch(nextSearch);
    setDocumentLoadStatus("ready");
    setDocumentLoadError(null);
  }, [locationSearch]);

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
              <PlanSurfaceCanvas
                sessionDescriptor={config.sessionDescriptor}
                theme={config.theme}
                onEditorToolsChange={onEditorToolsChange}
                onSaveStatusChange={setSaveStatusLabel}
                onPlanningDocumentCommitted={setPlanningDocument}
                onPlanningDocumentSwitch={switchPlanningDocument}
              />
            </div>
          </div>
          <PlanAgentInteractionBar planView={planView} sessionDescriptor={config.sessionDescriptor} />
        </div>
      </PlanGraphReferenceResolverProvider>
    </EditCapabilityProvider>
  );
}
