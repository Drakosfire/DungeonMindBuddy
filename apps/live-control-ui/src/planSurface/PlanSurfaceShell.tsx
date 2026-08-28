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
import { PlanSurfaceContext } from "./components/PlanSurfaceContext";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { PlanDogfoodPanel } from "./dogfood/PlanDogfoodPanel";
import { dogfoodModeFromLocation } from "./dogfood/planDogfoodState";
import { createPlanSurfaceConfig, planLocationOverridesFromSearch } from "./config/planSurfaceConfig";
import {
  defaultSessionPrepTitle,
  NoActivePlanningDocumentsError,
  planDocumentSelectionSearch,
  resolvePlanningDocument,
  suggestNextPlanTargetSession,
} from "./config/planSessionDescriptor";
import { formatReviewCampaignLabel, requestedDocumentIdFromLocation } from "./sessionCampaignContext";
import { EditCapabilityProvider } from "./edit/editCapability";
import { PlanReferenceProjectionBinding } from "./reference/PlanReferenceProjectionBinding";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import {
  adoptCreatedPlanIdentity,
  createPlanLocalDraftMetadata,
  nextPlanShellState,
  planLocalDraftToDescriptor,
  planShellAgentDocumentId,
  planShellWorkObject,
  retainCreatedPlan,
  type PlanAuthoringShellState,
  type PlanShellIdentity,
} from "./planBlankAuthoringState";
import type { PlanDocumentDescriptor, PlanSurfaceConfig } from "./types";
import "./planSurface.css";

interface PlanSurfaceShellProps {
  planView: PlanViewProjection;
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
}

type DocumentUrlCommit =
  | { mode: "push"; search: string }
  | { mode: "history" };

function themeStyle(config: PlanSurfaceConfig): CSSProperties {
  return (config.theme.tokens ?? {}) as CSSProperties;
}

function appChromeToolsPublicationSignature(tools: AppChromeToolsGeneration): string {
  const generation = tools.tools;
  return JSON.stringify({
    target: tools.target,
    pinned: (generation.pinnedActions ?? []).map((action) => [
      action.id,
      action.disabled === true,
      action.disabledReason ?? null,
      action.label,
      action.pressed === true,
    ]),
    sections: (generation.sections ?? []).map((section) => [
      section.id,
      section.actions.map((action) => [
        action.id,
        action.disabled === true,
        action.disabledReason ?? null,
        action.label,
      ]),
    ]),
  });
}

function shellIdentityFromPlanView(
  planView: PlanViewProjection,
  locationSearch: string,
): PlanShellIdentity {
  const overrides = planLocationOverridesFromSearch(locationSearch);
  return {
    campaignId: planView.campaign_id,
    liveSession: planView.session,
    memorySession: overrides.memorySession ?? null,
  };
}

export function PlanSurfaceShell({ planView, onEditorToolsChange }: PlanSurfaceShellProps) {
  const [locationSearch, setLocationSearch] = useState(
    () => (typeof window !== "undefined" ? window.location.search : ""),
  );
  const [shellState, setShellState] = useState<PlanAuthoringShellState>(() => ({
    kind: "resolving",
    shell: shellIdentityFromPlanView(planView, typeof window !== "undefined" ? window.location.search : ""),
    requestedDocumentId: requestedDocumentIdFromLocation(
      typeof window !== "undefined" ? window.location.search : null,
    ),
  }));
  const [documentSwitching, setDocumentSwitching] = useState(false);
  const [documentSwitchError, setDocumentSwitchError] = useState<string | null>(null);
  const [selectorRecords, setSelectorRecords] = useState<WorkspaceDocumentRecord[] | null>(null);
  const [selectorListStatus, setSelectorListStatus] = useState<"loading" | "ready" | "error">("loading");
  const [creatingDocument, setCreatingDocument] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createActivationError, setCreateActivationError] = useState<string | null>(null);

  const createControllerRef = useRef(createWorkspaceDocumentCreationController());

  const shellStateRef = useRef(shellState);
  shellStateRef.current = shellState;
  const locationSearchRef = useRef(locationSearch);
  locationSearchRef.current = locationSearch;
  const documentLoadGenerationRef = useRef(0);
  const selectorListGenerationRef = useRef(0);

  const planningDocument = useMemo((): PlanDocumentDescriptor | null => {
    if (shellState.kind === "durable_ready") return shellState.document;
    if (shellState.kind === "blank_ready" || shellState.kind === "promoting") {
      return planLocalDraftToDescriptor(shellState.draft);
    }
    if (
      shellState.kind === "load_error"
      && shellState.localDraft
      && shellState.inventoryUnavailable
    ) {
      return planLocalDraftToDescriptor(shellState.localDraft);
    }
    return null;
  }, [shellState]);

  const loadSelectorDocuments = useCallback(async () => {
    const generation = ++selectorListGenerationRef.current;
    setSelectorListStatus("loading");
    try {
      const list = await listWorkspaceDocuments({
        campaign_id: planView.campaign_id,
        kind: "plan",
        status: "active",
      });
      if (generation !== selectorListGenerationRef.current) return list;
      setSelectorRecords(list.records);
      setSelectorListStatus("ready");
      return list;
    } catch {
      if (generation !== selectorListGenerationRef.current) return null;
      setSelectorListStatus("error");
      return null;
    }
  }, [planView.campaign_id]);

  useEffect(() => {
    void loadSelectorDocuments();
  }, [loadSelectorDocuments]);

  const buildBlankDraft = useCallback(
    (occupiedSessions: Array<number | null | undefined>) => {
      const campaignLabel = formatReviewCampaignLabel(planView.campaign_id);
      const targetSession = suggestNextPlanTargetSession(planView.session, occupiedSessions);
      return createPlanLocalDraftMetadata({
        campaignId: planView.campaign_id,
        title: defaultSessionPrepTitle(campaignLabel, targetSession),
        targetSession,
      });
    },
    [planView.campaign_id, planView.session],
  );

  const loadPlanningDocument = useCallback(
    async (
      search: string,
      urlCommit: DocumentUrlCommit,
      purpose: "default" | "create_activate" = "default",
    ): Promise<boolean> => {
      const generation = ++documentLoadGenerationRef.current;
      const shell = shellIdentityFromPlanView(planView, search);
      const requestedDocumentId = requestedDocumentIdFromLocation(search);
      const switching =
        shellStateRef.current.kind === "durable_ready" && purpose !== "create_activate";
      const retainedSearch = locationSearchRef.current;

      if (switching) {
        setDocumentSwitching(true);
        setDocumentSwitchError(null);
      } else if (purpose !== "create_activate" && requestedDocumentId) {
        setShellState({
          kind: "resolving",
          shell,
          requestedDocumentId,
        });
      }

      const listResult = await loadSelectorDocuments();
      const selectorListAvailable = listResult != null;
      const selectorListEmpty = listResult?.records.length === 0;
      const occupiedSessions = listResult?.records.map((record) => record.target_session) ?? [];

      if (!requestedDocumentId && !selectorListAvailable) {
        if (generation !== documentLoadGenerationRef.current) return false;
        const blankDraft = buildBlankDraft(occupiedSessions);
        setShellState({
          kind: "load_error",
          shell,
          requestedDocumentId: null,
          message:
            "Active Plan inventory is unavailable; target session cannot be chosen safely.",
          localDraft: blankDraft,
          inventoryUnavailable: true,
        });
        setDocumentSwitching(false);
        setDocumentSwitchError(null);
        return false;
      }

      if (!switching && purpose !== "create_activate" && !requestedDocumentId) {
        setShellState({
          kind: "resolving",
          shell,
          requestedDocumentId,
        });
      }

      try {
        const document = await resolvePlanningDocument({ planView, locationSearch: search });
        if (generation !== documentLoadGenerationRef.current) return false;
        setShellState(adoptCreatedPlanIdentity(document));
        setDocumentSwitching(false);
        setDocumentSwitchError(null);
        if (purpose !== "create_activate") {
          createControllerRef.current.reconcileActivatedDocument(document.documentId);
          setCreateError(null);
          setCreateActivationError(null);
        }

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
        const blankDraft = !requestedDocumentId ? buildBlankDraft(occupiedSessions) : null;
        const nextState = nextPlanShellState({
          shell,
          outcome: {
            requestedDocumentId,
            resolvedDocument: null,
            resolveError: error instanceof Error ? error : new Error(String(error)),
            selectorListAvailable,
            selectorListEmpty,
          },
          blankDraft,
        });

        if (purpose === "create_activate") {
          setDocumentSwitching(false);
          throw error instanceof Error ? error : new Error(String(error));
        }

        if (switching && !(error instanceof NoActivePlanningDocumentsError)) {
          setDocumentSwitching(false);
          setDocumentSwitchError(
            error instanceof Error ? error.message : "Failed to load planning document",
          );
          setShellState((current) =>
            current.kind === "durable_ready"
              ? current
              : {
                  kind: "load_error",
                  shell,
                  requestedDocumentId,
                  message: error instanceof Error ? error.message : "Failed to load planning document",
                },
          );
          if (urlCommit.mode === "history" && typeof window !== "undefined") {
            const retainedUrl = `${window.location.pathname}${retainedSearch}`;
            const currentUrl = `${window.location.pathname}${window.location.search}`;
            if (currentUrl !== retainedUrl) {
              window.history.replaceState({}, "", retainedUrl);
            }
          }
          return false;
        }

        setShellState(nextState);
        setDocumentSwitching(false);
        setDocumentSwitchError(null);
        return false;
      }
    },
    [buildBlankDraft, loadSelectorDocuments, planView],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => {
      createControllerRef.current.supersedePendingCreateIntent();
      void loadPlanningDocument(window.location.search, { mode: "history" });
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [loadPlanningDocument]);

  const handleSelectPlanningDocument = useCallback(
    (documentId: string) => {
      if (typeof window === "undefined") return;
      if (planningDocument?.documentId === documentId) return;
      createControllerRef.current.supersedePendingCreateIntent();
      setCreateError(null);
      setCreateActivationError(null);
      const search = planDocumentSelectionSearch(window.location.search, documentId);
      void loadPlanningDocument(search, { mode: "push", search });
    },
    [loadPlanningDocument, planningDocument?.documentId],
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
      setCreatingDocument(true);
      setCreateError(null);
      setCreateActivationError(null);
      try {
        const created = await createControllerRef.current.create({
          kind: "plan",
          campaignId: planView.campaign_id,
          title,
          targetSession,
        });
        void loadSelectorDocuments();
        if (!created.intentCurrent) return;
        try {
          await activateCreatedRecord(created.record);
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

  const handleBlankPromoted = useCallback(
    (document: PlanDocumentDescriptor) => {
      setShellState(adoptCreatedPlanIdentity(document));
      createControllerRef.current.reconcileActivatedDocument(document.documentId);
      void loadSelectorDocuments();
      if (typeof window !== "undefined") {
        setLocationSearch(window.location.search);
      }
    },
    [loadSelectorDocuments],
  );

  const handlePlanningDocumentCommitted = useCallback((document: PlanDocumentDescriptor) => {
    setShellState(adoptCreatedPlanIdentity(document));
  }, []);

  const handleBlankPromotionStateChange = useCallback(
    (args: { promoting: boolean; retainedCreateId: string | null; error: string | null }) => {
      setShellState((current) => {
        if (current.kind !== "blank_ready" && current.kind !== "promoting") return current;
        if (args.retainedCreateId) {
          return retainCreatedPlan(current, args.retainedCreateId);
        }
        if (args.promoting) {
          return {
            kind: "promoting",
            draft: current.draft,
            retainedCreateId: null,
            selectorListAvailable: current.selectorListAvailable,
          };
        }
        if (current.kind === "promoting" && current.retainedCreateId) {
          return current;
        }
        return {
          kind: "blank_ready",
          draft: current.draft,
          selectorListAvailable: current.selectorListAvailable,
        };
      });
    },
    [],
  );

  const activeDocumentsForCreate = useMemo(
    () =>
      selectorRecords?.map((record) => ({
        title: record.title,
        targetSession: record.target_session,
      })) ?? [],
    [selectorRecords],
  );

  const createControlProps = useMemo(
    () => ({
      campaignId: planView.campaign_id,
      campaignLabel,
      suggestedSession: suggestedCreateSession,
      suggestedTitle: suggestedCreateTitle,
      activeDocuments: activeDocumentsForCreate,
      creating: creatingDocument,
      createError,
      activationError: createActivationError,
      onSubmit: handleCreatePlanningDocument,
      onRetryOpen: createActivationError ? handleRetryOpenCreatedDocument : undefined,
      disabled: documentSwitching,
    }),
    [
      activeDocumentsForCreate,
      createActivationError,
      campaignLabel,
      createError,
      creatingDocument,
      documentSwitching,
      handleCreatePlanningDocument,
      handleRetryOpenCreatedDocument,
      planView.campaign_id,
      suggestedCreateSession,
      suggestedCreateTitle,
    ],
  );

  const canvasWorkObject = useMemo(() => planShellWorkObject(shellState), [shellState]);
  const agentDocumentId = useMemo(() => planShellAgentDocumentId(shellState), [shellState]);

  const config = useMemo((): PlanSurfaceConfig | null => {
    if (!planningDocument) {
      if (shellState.kind === "load_error" || shellState.kind === "resolving") {
        const placeholder = planLocalDraftToDescriptor(
          createPlanLocalDraftMetadata({
            campaignId: shellState.shell.campaignId,
            title: "Plan",
            targetSession: null,
          }),
        );
        return createPlanSurfaceConfig(planView, placeholder, locationSearch, {
          documentId: agentDocumentId,
          workObject: canvasWorkObject,
        });
      }
      return null;
    }
    return createPlanSurfaceConfig(planView, planningDocument, locationSearch, {
      documentId: agentDocumentId,
      workObject: canvasWorkObject,
    });
  }, [agentDocumentId, canvasWorkObject, locationSearch, planView, planningDocument, shellState]);

  const { publishProjectionSurface, updateProjectionSurfaceConfig } = useAgentInteraction();

  const publication = useMemo(
    () =>
      config
        ? {
            identity: buildPlanSurfaceIdentity({
              documentId: agentDocumentId,
              localDraftId:
                shellState.kind === "blank_ready" || shellState.kind === "promoting"
                  ? shellState.draft.localId
                  : null,
              campaignId: config.sessionDescriptor.campaignId,
              liveSession: config.context.liveSession,
              memorySession: config.sessionDescriptor.memorySession,
            }),
            config,
          }
        : null,
    [agentDocumentId, config, shellState],
  );
  const publicationInstanceKey = publication?.identity.instanceKey ?? null;
  const publicationRef = useRef(publication);
  publicationRef.current = publication;

  const publicationConfigSignature = useMemo(() => {
    if (!config) return null;
    const doc = config.sessionDescriptor.planningDocument;
    return JSON.stringify({
      agentDocumentId,
      workKind: canvasWorkObject.kind,
      workId: canvasWorkObject.id,
      documentId: doc.documentId,
      revision: doc.revision,
      title: doc.title,
      targetSession: doc.targetSession,
      targetRelpath: doc.targetRelpath,
      contentStatus: doc.contentStatus,
      memorySession: config.sessionDescriptor.memorySession,
      liveSession: config.context.liveSession,
      label: config.label,
    });
  }, [agentDocumentId, canvasWorkObject, config]);

  const editorToolsPublisherEpochRef = useRef(0);
  const lastEditorToolsSignatureRef = useRef<string | null>(null);
  const boundPublicationInstanceKeyRef = useRef<string | null>(null);
  const lastPublicationConfigSignatureRef = useRef<string | null>(null);
  const onEditorToolsChangeRef = useRef(onEditorToolsChange);
  onEditorToolsChangeRef.current = onEditorToolsChange;

  const handleEditorToolsChange = useCallback((tools: AppChromeToolsGeneration | null) => {
    if (tools != null) {
      const signature = appChromeToolsPublicationSignature(tools);
      if (lastEditorToolsSignatureRef.current === signature) {
        return;
      }
      lastEditorToolsSignatureRef.current = signature;
      editorToolsPublisherEpochRef.current += 1;
      onEditorToolsChangeRef.current?.(tools);
      return;
    }
    const epochAtClear = editorToolsPublisherEpochRef.current;
    queueMicrotask(() => {
      if (editorToolsPublisherEpochRef.current !== epochAtClear) {
        return;
      }
      lastEditorToolsSignatureRef.current = null;
      onEditorToolsChangeRef.current?.(null);
    });
  }, []);

  useEffect(() => {
    if (!publicationRef.current) {
      boundPublicationInstanceKeyRef.current = null;
      lastPublicationConfigSignatureRef.current = null;
      return publishProjectionSurface(null);
    }
    return publishProjectionSurface(publicationRef.current);
  }, [publicationInstanceKey, publishProjectionSurface]);

  useEffect(() => {
    if (!publicationRef.current || publicationInstanceKey == null || publicationConfigSignature == null) {
      return;
    }
    if (boundPublicationInstanceKeyRef.current !== publicationInstanceKey) {
      boundPublicationInstanceKeyRef.current = publicationInstanceKey;
      lastPublicationConfigSignatureRef.current = publicationConfigSignature;
      return;
    }
    if (lastPublicationConfigSignatureRef.current === publicationConfigSignature) {
      return;
    }
    lastPublicationConfigSignatureRef.current = publicationConfigSignature;
    updateProjectionSurfaceConfig(publicationRef.current);
  }, [publicationConfigSignature, publicationInstanceKey, updateProjectionSurfaceConfig]);

  const [saveStatusLabel, setSaveStatusLabel] = useState("Local draft · not yet saved to Markdown");
  const dogfoodMode = dogfoodModeFromLocation();

  const memorySession = useMemo(
    () => planLocationOverridesFromSearch(locationSearch).memorySession ?? null,
    [locationSearch],
  );

  const handleRetryList = useCallback(async () => {
    const list = await loadSelectorDocuments();
    if (list == null) return;
    const current = shellStateRef.current;
    if (
      current.kind === "load_error"
      && current.inventoryUnavailable
      && !current.requestedDocumentId
    ) {
      const applied = await loadPlanningDocument(locationSearchRef.current, { mode: "history" });
      if (
        !applied
        && shellStateRef.current.kind === "load_error"
        && shellStateRef.current.inventoryUnavailable
      ) {
        const draft =
          current.localDraft
          ?? buildBlankDraft(list.records.map((record) => record.target_session));
        setShellState({
          kind: "blank_ready",
          draft,
          selectorListAvailable: true,
        });
      }
    }
  }, [buildBlankDraft, loadPlanningDocument, loadSelectorDocuments]);

  const planSurfaceContextProps = useMemo(
    () => ({
      campaignId: planView.campaign_id,
      liveSession: planView.session,
      memorySession,
      documents: selectorRecords,
      listStatus: selectorListStatus,
      activeDocument: planningDocument,
      switching: documentSwitching,
      switchError: documentSwitchError,
      saveStatusLabel,
      onSelect: handleSelectPlanningDocument,
      onRetryList: handleRetryList,
      createControlProps,
    }),
    [
      createControlProps,
      documentSwitchError,
      documentSwitching,
      handleRetryList,
      handleSelectPlanningDocument,
      memorySession,
      planView.campaign_id,
      planView.session,
      planningDocument,
      saveStatusLabel,
      selectorListStatus,
      selectorRecords,
    ],
  );

  const inventoryUnavailable =
    shellState.kind === "load_error" && shellState.inventoryUnavailable === true;
  const loadErrorMessage =
    shellState.kind === "load_error" && !inventoryUnavailable ? shellState.message : null;

  if (!config) {
    return (
      <main className="app-status">
        <p>Loading planning document…</p>
      </main>
    );
  }

  return (
    <EditCapabilityProvider>
      <PlanSurfaceContext {...planSurfaceContextProps} />
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
                shellState={shellState}
                loadErrorMessage={loadErrorMessage}
                selectorListAvailable={selectorListStatus !== "error"}
                createController={createControllerRef.current}
                onEditorToolsChange={handleEditorToolsChange}
                onSaveStatusChange={setSaveStatusLabel}
                onPlanningDocumentCommitted={handlePlanningDocumentCommitted}
                onBlankPromoted={handleBlankPromoted}
                onBlankPromotionStateChange={handleBlankPromotionStateChange}
              />
            </div>
          </div>
          <PlanAgentInteractionBar planView={planView} sessionDescriptor={config.sessionDescriptor} />
        </div>
      </PlanGraphReferenceResolverProvider>
    </EditCapabilityProvider>
  );
}
