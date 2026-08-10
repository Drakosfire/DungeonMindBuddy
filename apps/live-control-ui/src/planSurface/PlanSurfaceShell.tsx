import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import { listWorkspaceDocuments } from "../api/liveApi";
import type { PlanViewProjection, WorkspaceDocumentRecord } from "../api/types";
import { useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { buildPlanSurfaceIdentity } from "../agentInteraction/projectionSurfacePublication";
import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import {
  createWorkspaceDocumentCreationController,
  WorkspaceDocumentCreationError,
} from "../workspaceDocument/workspaceDocumentCreation";
import { workspaceDocumentSelectionSearch } from "../workspaceDocument/workspaceDocumentNavigation";
import { PlanAgentInteractionBar } from "./components/PlanAgentInteractionBar";
import { PlanDocumentCreateControl } from "./components/PlanDocumentCreateControl";
import { PlanDocumentSelector } from "./components/PlanDocumentSelector";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { PlanDogfoodPanel } from "./dogfood/PlanDogfoodPanel";
import { dogfoodModeFromLocation } from "./dogfood/planDogfoodState";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import {
  defaultSessionPrepTitle,
  durablePlanTargetRelpath,
  NoActivePlanningDocumentsError,
  planDocumentSelectionSearch,
  resolvePlanningDocument,
  suggestNextPlanTargetSession,
} from "./config/planSessionDescriptor";
import { formatReviewCampaignLabel } from "./sessionCampaignContext";
import { EditCapabilityProvider } from "./edit/editCapability";
import { PlanReferenceProjectionBinding } from "./reference/PlanReferenceProjectionBinding";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import type { PlanDocumentDescriptor, PlanSurfaceConfig } from "./types";
import "./planSurface.css";

interface PlanSurfaceShellProps {
  planView: PlanViewProjection;
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
}

/** How a successful/failed document resolve may commit browser URL identity. */
type DocumentUrlCommit =
  | { mode: "push"; search: string }
  | { mode: "history" };

function themeStyle(config: PlanSurfaceConfig): CSSProperties {
  return (config.theme.tokens ?? {}) as CSSProperties;
}

export function PlanSurfaceShell({ planView, onEditorToolsChange }: PlanSurfaceShellProps) {
  const [locationSearch, setLocationSearch] = useState(
    () => (typeof window !== "undefined" ? window.location.search : ""),
  );
  const [planningDocument, setPlanningDocument] = useState<PlanDocumentDescriptor | null>(null);
  const [documentLoadStatus, setDocumentLoadStatus] = useState<
    "loading" | "ready" | "error" | "empty"
  >("loading");
  const [documentLoadError, setDocumentLoadError] = useState<string | null>(null);
  const [documentSwitching, setDocumentSwitching] = useState(false);
  const [documentSwitchError, setDocumentSwitchError] = useState<string | null>(null);
  const [selectorRecords, setSelectorRecords] = useState<WorkspaceDocumentRecord[] | null>(null);
  const [selectorListStatus, setSelectorListStatus] = useState<"loading" | "ready" | "error">("loading");
  const [creatingDocument, setCreatingDocument] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createActivationError, setCreateActivationError] = useState<string | null>(null);

  const createControllerRef = useRef(createWorkspaceDocumentCreationController());

  const planningDocumentRef = useRef<PlanDocumentDescriptor | null>(null);
  planningDocumentRef.current = planningDocument;
  const locationSearchRef = useRef(locationSearch);
  locationSearchRef.current = locationSearch;
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
   * switches. Resolve first, then commit URL identity: selector success uses
   * pushState; bare/default and history success canonicalize with replaceState;
   * failed history keeps Canvas + restores the retained exact URL. A resolution
   * applies only while it is the newest request; a failed switch never falls
   * back to a different record.
   */
  const loadPlanningDocument = useCallback(
    async (
      search: string,
      urlCommit: DocumentUrlCommit,
      purpose: "default" | "create_activate" = "default",
    ): Promise<boolean> => {
      const generation = ++documentLoadGenerationRef.current;
      const switching = planningDocumentRef.current != null && purpose !== "create_activate";
      const retainedSearch = locationSearchRef.current;
      if (switching) {
        setDocumentSwitching(true);
        setDocumentSwitchError(null);
      } else if (purpose !== "create_activate") {
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

        if (typeof window !== "undefined") {
          if (urlCommit.mode === "push") {
            window.history.pushState({}, "", `${window.location.pathname}${urlCommit.search}`);
            setLocationSearch(urlCommit.search);
          } else {
            const named = new URLSearchParams(window.location.search).get("documentId");
            if (named === document.documentId) {
              setLocationSearch(window.location.search);
            } else {
              const canonical = planDocumentSelectionSearch(
                window.location.search,
                document.documentId,
              );
              window.history.replaceState({}, "", `${window.location.pathname}${canonical}`);
              setLocationSearch(canonical);
            }
          }
        }
        return true;
      } catch (error) {
        if (generation !== documentLoadGenerationRef.current) return false;
        if (!switching && error instanceof NoActivePlanningDocumentsError) {
          setPlanningDocument(null);
          setDocumentLoadStatus("empty");
          setDocumentLoadError(null);
          setDocumentSwitching(false);
          setDocumentSwitchError(null);
          void loadSelectorDocuments();
          return false;
        }
        const message = error instanceof Error ? error.message : "Failed to load planning document";
        if (purpose === "create_activate") {
          setDocumentSwitching(false);
          throw error instanceof Error ? error : new Error(message);
        }
        if (switching) {
          setDocumentSwitching(false);
          setDocumentSwitchError(message);
          setDocumentLoadStatus("ready");
          // History already moved the browser URL; put exact current identity back.
          if (urlCommit.mode === "history" && typeof window !== "undefined") {
            const retainedUrl = `${window.location.pathname}${retainedSearch}`;
            const currentUrl = `${window.location.pathname}${window.location.search}`;
            if (currentUrl !== retainedUrl) {
              window.history.replaceState({}, "", retainedUrl);
            }
          }
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

  // Initial load and browser back/forward: resolve, then commit URL identity.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => {
      void loadPlanningDocument(window.location.search, { mode: "history" });
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
      void loadPlanningDocument(search, { mode: "push", search });
    },
    [loadPlanningDocument],
  );

  const campaignLabel = useMemo(
    () => formatReviewCampaignLabel(planView.campaign_id),
    [planView.campaign_id],
  );

  const occupiedTargetSessions = useMemo(
    () => selectorRecords?.map((record) => record.target_session) ?? [],
    [selectorRecords],
  );

  const suggestedCreateSession = useMemo(
    () => suggestNextPlanTargetSession(planView.session, occupiedTargetSessions),
    [occupiedTargetSessions, planView.session],
  );

  const suggestedCreateTitle = useMemo(
    () => defaultSessionPrepTitle(campaignLabel, suggestedCreateSession),
    [campaignLabel, suggestedCreateSession],
  );

  const activateCreatedRecord = useCallback(
    async (record: WorkspaceDocumentRecord): Promise<boolean> => {
      if (typeof window === "undefined") return false;
      const search = workspaceDocumentSelectionSearch(window.location.search, record.document_id);
      const { applied } = await createControllerRef.current.activate(async () =>
        loadPlanningDocument(search, { mode: "push", search }, "create_activate"),
      );
      if (applied) {
        setCreateActivationError(null);
      }
      return applied;
    },
    [loadPlanningDocument],
  );

  const handleCreatePlanningDocument = useCallback(
    async ({ title, targetSession }: { title: string; targetSession: number }) => {
      const targetRelpath = durablePlanTargetRelpath(planView.campaign_id, targetSession);
      if (targetRelpath == null) return;

      setCreatingDocument(true);
      setCreateError(null);
      setCreateActivationError(null);
      try {
        const created = await createControllerRef.current.create({
          kind: "plan",
          campaignId: planView.campaign_id,
          title,
          targetSession,
          targetRelpath,
        });
        void loadSelectorDocuments();
        try {
          await activateCreatedRecord(created);
        } catch (error) {
          const message =
            error instanceof WorkspaceDocumentCreationError
              ? error.message
              : error instanceof Error
                ? error.message
                : "Failed to open created planning document";
          setCreateActivationError(message);
        }
      } catch (error) {
        if (error instanceof WorkspaceDocumentCreationError) {
          if (error.code === "create_failed") {
            setCreateError(error.message);
          }
        } else if (error instanceof Error) {
          setCreateError(error.message);
        } else {
          setCreateError("Failed to create planning document");
        }
      } finally {
        setCreatingDocument(false);
      }
    },
    [activateCreatedRecord, loadSelectorDocuments, planView.campaign_id],
  );

  const handleRetryOpenCreatedDocument = useCallback(async () => {
    const record = createControllerRef.current.getState().record;
    if (record == null) {
      setCreateActivationError("No created planning document is available to open");
      return;
    }
    setCreatingDocument(true);
    setCreateActivationError(null);
    try {
      await activateCreatedRecord(record);
    } catch (error) {
      const message =
        error instanceof WorkspaceDocumentCreationError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Failed to open created planning document";
      setCreateActivationError(message);
    } finally {
      setCreatingDocument(false);
    }
  }, [activateCreatedRecord]);

  const createControlProps = {
    campaignId: planView.campaign_id,
    campaignLabel,
    suggestedSession: suggestedCreateSession,
    suggestedTitle: suggestedCreateTitle,
    creating: creatingDocument,
    createError,
    activationError: createActivationError,
    onSubmit: handleCreatePlanningDocument,
    onRetryOpen: createActivationError ? handleRetryOpenCreatedDocument : undefined,
    disabled: documentSwitching,
  };

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

  if (documentLoadStatus === "loading") {
    return (
      <main className="app-status">
        <p>Loading planning document…</p>
      </main>
    );
  }

  if (documentLoadStatus === "empty") {
    return (
      <main className="plan-surface-empty" data-testid="plan-surface-empty">
        <h1>Plan</h1>
        <p>No prep documents yet</p>
        <PlanDocumentCreateControl {...createControlProps} />
      </main>
    );
  }

  if (documentLoadStatus === "error" || !config) {
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
              <div className="plan-document-toolbar" data-testid="plan-document-toolbar">
                <PlanDocumentSelector
                  documents={selectorRecords}
                  listStatus={selectorListStatus}
                  activeDocument={config.sessionDescriptor.planningDocument}
                  switching={documentSwitching}
                  switchError={documentSwitchError}
                  onSelect={handleSelectPlanningDocument}
                  onRetryList={() => void loadSelectorDocuments()}
                />
                <PlanDocumentCreateControl {...createControlProps} />
              </div>
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
