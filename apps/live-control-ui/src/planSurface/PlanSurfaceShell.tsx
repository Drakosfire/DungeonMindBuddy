import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";

import type { AppChromeTools } from "../chrome/AppChrome";
import type { PlanViewProjection } from "../api/types";
import { PlanAgentInteractionBar } from "./components/PlanAgentInteractionBar";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { PlanDogfoodPanel } from "./dogfood/PlanDogfoodPanel";
import { dogfoodModeFromLocation } from "./dogfood/planDogfoodState";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import { resolvePlanningDocument } from "./config/planSessionDescriptor";
import { EditCapabilityProvider } from "./edit/editCapability";
import { AdaptiveProjectionContainer } from "./projection/AdaptiveProjectionContainer";
import { useBindProjectionSurface } from "./projection/projectionContext";
import { PlanGraphLensProvider } from "./PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import type { PlanDocumentDescriptor, PlanSurfaceConfig } from "./types";
import "./planSurface.css";

interface PlanSurfaceShellProps {
  planView: PlanViewProjection;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
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
    void loadPlanningDocument();
  }, [loadPlanningDocument]);

  const config = useMemo(
    () => (planningDocument ? createPlanSurfaceConfig(planView, planningDocument, locationSearch) : null),
    [locationSearch, planView, planningDocument],
  );
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
    <PlanSurfaceBoundShell
      config={config}
      planView={planView}
      saveStatusLabel={saveStatusLabel}
      setSaveStatusLabel={setSaveStatusLabel}
      setPlanningDocument={setPlanningDocument}
      onEditorToolsChange={onEditorToolsChange}
      dogfoodMode={dogfoodMode}
    />
  );
}

function PlanSurfaceBoundShell({
  config,
  planView,
  saveStatusLabel,
  setSaveStatusLabel,
  setPlanningDocument,
  onEditorToolsChange,
  dogfoodMode,
}: {
  config: PlanSurfaceConfig;
  planView: PlanViewProjection;
  saveStatusLabel: string;
  setSaveStatusLabel: (label: string) => void;
  setPlanningDocument: (document: PlanDocumentDescriptor | null) => void;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
  dogfoodMode: boolean;
}) {
  useBindProjectionSurface(config);

  return (
    <EditCapabilityProvider>
      <PlanGraphLensProvider planCampaignId={config.sessionDescriptor.campaignId}>
        <PlanGraphReferenceResolverProvider sessionDescriptor={config.sessionDescriptor}>
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
                />
              </div>
              <AdaptiveProjectionContainer config={config} />
            </div>
            <PlanAgentInteractionBar planView={planView} sessionDescriptor={config.sessionDescriptor} />
          </div>
        </PlanGraphReferenceResolverProvider>
      </PlanGraphLensProvider>
    </EditCapabilityProvider>
  );
}
