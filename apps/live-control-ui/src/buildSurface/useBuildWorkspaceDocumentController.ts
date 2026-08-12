import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  commitTiptapMarkdownWrite,
  getWorkspaceDocumentSnapshot,
  listWorkspaceDocuments,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import {
  classifyBuildDocumentScope,
  getWorldIdForCampaign,
} from "../worldGraph/worldGraphSurfaceContext";
import {
  createWorkspaceDocumentCreationController,
  WorkspaceDocumentCreationError,
} from "../workspaceDocument/workspaceDocumentCreation";
import { buildDocumentSelectionSearch } from "./buildDocumentNavigation";
import {
  readBuildLastCampaignId,
  resolveBareBuildCampaignId,
  resolveBuildCreateCampaignChoices,
  resolveSuggestedBuildCreateCampaignId,
  writeBuildLastCampaignId,
} from "./buildBareEntryCampaign";

export type BuildDocumentListStatus = "loading" | "ready" | "error";
export type BuildDocumentLoadStatus = "idle" | "loading" | "ready" | "empty" | "error";

/** How a successful/failed document resolve may commit browser URL identity. */
type DocumentUrlCommit =
  | { mode: "push"; search: string }
  | { mode: "history" };

function readDocumentIdFromSearch(search: string): string | null {
  const raw = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search)
    .get("documentId")
    ?.trim();
  return raw || null;
}

function validateBuildSourceRecord(
  record: WorkspaceDocumentRecord,
  requestedId: string,
): WorkspaceDocumentRecord {
  if (record.document_id !== requestedId) {
    throw new Error("Document identity mismatch");
  }
  if (record.kind !== "worldbuilding_source") {
    throw new Error("Not a worldbuilding source");
  }
  if (record.status !== "active") {
    throw new Error("Document is not active");
  }
  return record;
}

export function resolveWorldIdForBuildCreate(campaignId: string): string | null {
  const mapped = getWorldIdForCampaign(campaignId);
  if (mapped) return mapped;
  const scope = classifyBuildDocumentScope(campaignId);
  if (scope.kind === "world") return scope.worldId;
  return null;
}

function buildWorldbuildingCreateIntent(
  title: string,
  campaignId: string,
): {
  kind: "worldbuilding_source";
  campaignId: string;
  title: string;
  worldId?: string;
  documentClass: string;
  authorityState: "draft";
  visibilityState: "internal";
} {
  const worldId = resolveWorldIdForBuildCreate(campaignId);
  return {
    kind: "worldbuilding_source",
    campaignId,
    title,
    ...(worldId ? { worldId } : {}),
    documentClass: "lore",
    authorityState: "draft",
    visibilityState: "internal",
  };
}

export interface BuildWorkspaceDocumentController {
  activeRecord: WorkspaceDocumentRecord | null;
  activeDocumentId: string | null;
  documents: WorkspaceDocumentRecord[] | null;
  listStatus: BuildDocumentListStatus;
  loadStatus: BuildDocumentLoadStatus;
  switching: boolean;
  switchError: string | null;
  creating: boolean;
  createError: string | null;
  activationError: string | null;
  importError: string | null;
  selectDocument: (documentId: string) => void;
  createDocument: (payload: { title: string; campaignId: string }) => void;
  importSourceDocument: (payload: {
    title: string;
    campaignId: string;
    markdown: string;
  }) => void;
  retryImportSource: (payload: { markdown: string }) => void;
  retryCreatedDocument: () => void;
  refreshDocuments: () => void;
  /** Campaigns New Source may create into (visible select == POST validation). */
  creatableCampaignIds: string[];
  suggestedCreateCampaignId: string | null;
  /** Retained empty source from a failed import lifecycle, if any. */
  pendingImportDocumentId: string | null;
}

export function useBuildWorkspaceDocumentController(): BuildWorkspaceDocumentController {
  const [locationSearch, setLocationSearch] = useState(
    () => (typeof window !== "undefined" ? window.location.search : ""),
  );
  const [activeRecord, setActiveRecord] = useState<WorkspaceDocumentRecord | null>(null);
  const [loadStatus, setLoadStatus] = useState<BuildDocumentLoadStatus>(() =>
    readDocumentIdFromSearch(
      typeof window !== "undefined" ? window.location.search : "",
    )
      ? "loading"
      : "empty",
  );
  const [switching, setSwitching] = useState(false);
  const [switchError, setSwitchError] = useState<string | null>(null);
  const switchingRef = useRef(false);
  switchingRef.current = switching;
  const [documents, setDocuments] = useState<WorkspaceDocumentRecord[] | null>(null);
  const [listStatus, setListStatus] = useState<BuildDocumentListStatus>("loading");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [activationError, setActivationError] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [pendingImportDocumentId, setPendingImportDocumentId] = useState<string | null>(
    null,
  );
  const importCommittedRef = useRef(false);

  const createControllerRef = useRef(createWorkspaceDocumentCreationController());
  const activeRecordRef = useRef<WorkspaceDocumentRecord | null>(null);
  activeRecordRef.current = activeRecord;
  const locationSearchRef = useRef(locationSearch);
  locationSearchRef.current = locationSearch;
  const documentLoadGenerationRef = useRef(0);
  const selectorListGenerationRef = useRef(0);

  const activeDocumentId = activeRecord?.document_id ?? null;
  const refreshDocuments = useCallback(async () => {
    const generation = ++selectorListGenerationRef.current;
    setListStatus("loading");
    try {
      const list = await listWorkspaceDocuments({
        kind: "worldbuilding_source",
        status: "active",
      });
      if (generation !== selectorListGenerationRef.current) return;
      setDocuments(list.records);
      setListStatus("ready");
    } catch {
      if (generation !== selectorListGenerationRef.current) return;
      setListStatus("error");
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  const loadBuildDocument = useCallback(
    async (
      search: string,
      urlCommit: DocumentUrlCommit,
      purpose: "default" | "create_activate" = "default",
    ): Promise<boolean> => {
      const generation = ++documentLoadGenerationRef.current;
      const requestedId = readDocumentIdFromSearch(search);
      const switchingNow =
        activeRecordRef.current != null &&
        purpose !== "create_activate" &&
        requestedId != null &&
        requestedId !== activeRecordRef.current.document_id;
      const retainedSearch = locationSearchRef.current;

      if (!requestedId) {
        if (generation !== documentLoadGenerationRef.current) return false;
        setActiveRecord(null);
        setLoadStatus("empty");
        setSwitching(false);
        setSwitchError(null);
        void refreshDocuments();
        return false;
      }

      if (switchingNow) {
        setSwitching(true);
        setSwitchError(null);
      } else if (purpose !== "create_activate") {
        setLoadStatus("loading");
      }

      try {
        const snapshot = await getWorkspaceDocumentSnapshot(requestedId);
        const record = validateBuildSourceRecord(snapshot.record, requestedId);
        if (generation !== documentLoadGenerationRef.current) return false;

        setActiveRecord(record);
        setLoadStatus("ready");
        setSwitching(false);
        setSwitchError(null);
        writeBuildLastCampaignId(record.campaign_id);

        if (purpose !== "create_activate") {
          createControllerRef.current.reconcileActivatedDocument(record.document_id);
          setCreateError(null);
          setActivationError(null);
          setImportError(null);
          setPendingImportDocumentId(null);
          importCommittedRef.current = false;
        }
        void refreshDocuments();

        if (typeof window !== "undefined") {
          const canonical = buildDocumentSelectionSearch(
            search,
            record.document_id,
            record.campaign_id,
          );
          if (urlCommit.mode === "push") {
            window.history.pushState({}, "", `${window.location.pathname}${canonical}`);
            setLocationSearch(canonical);
          } else {
            const currentParams = new URLSearchParams(window.location.search);
            const currentCampaign = currentParams.get("campaign")?.trim() ?? "";
            if (
              currentParams.get("documentId") === record.document_id &&
              currentCampaign === record.campaign_id
            ) {
              setLocationSearch(window.location.search);
            } else {
              window.history.replaceState(
                {},
                "",
                `${window.location.pathname}${canonical}`,
              );
              setLocationSearch(canonical);
            }
          }
        }
        return true;
      } catch (error) {
        if (generation !== documentLoadGenerationRef.current) return false;
        const message =
          error instanceof Error ? error.message : "Failed to load worldbuilding source";

        if (purpose === "create_activate") {
          setSwitching(false);
          throw error instanceof Error ? error : new Error(message);
        }

        if (switchingNow) {
          setSwitching(false);
          setSwitchError("Could not open that source. Try another.");
          setLoadStatus("ready");
          if (urlCommit.mode === "history" && typeof window !== "undefined") {
            const retainedUrl = `${window.location.pathname}${retainedSearch}`;
            const currentUrl = `${window.location.pathname}${window.location.search}`;
            if (currentUrl !== retainedUrl) {
              window.history.replaceState({}, "", retainedUrl);
              setLocationSearch(retainedSearch);
            }
          }
        } else {
          setActiveRecord(null);
          setLoadStatus("error");
        }
        return false;
      }
    },
    [refreshDocuments],
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => {
      createControllerRef.current.supersedePendingCreateIntent();
      void loadBuildDocument(window.location.search, { mode: "history" });
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [loadBuildDocument]);

  const selectDocument = useCallback(
    (documentId: string) => {
      if (typeof window === "undefined") return;
      if (documentId === activeRecordRef.current?.document_id && !switchingRef.current) return;
      createControllerRef.current.supersedePendingCreateIntent();
      setCreateError(null);
      setActivationError(null);
      setImportError(null);
      setPendingImportDocumentId(null);
      importCommittedRef.current = false;
      const record = documents?.find((entry) => entry.document_id === documentId);
      const campaignHint =
        record?.campaign_id ??
        activeRecordRef.current?.campaign_id ??
        resolveBareBuildCampaignId({ search: window.location.search }) ??
        readBuildLastCampaignId() ??
        "";
      const search = buildDocumentSelectionSearch(
        window.location.search,
        documentId,
        campaignHint,
      );
      void loadBuildDocument(search, { mode: "push", search });
    },
    [documents, loadBuildDocument],
  );

  const activateCreatedRecord = useCallback(
    async (record: WorkspaceDocumentRecord): Promise<boolean> => {
      if (typeof window === "undefined") return false;
      const search = buildDocumentSelectionSearch(
        window.location.search,
        record.document_id,
        record.campaign_id,
      );
      const { applied } = await createControllerRef.current.activate(async () =>
        loadBuildDocument(search, { mode: "push", search }, "create_activate"),
      );
      if (applied) {
        setActivationError(null);
        setPendingImportDocumentId(null);
        importCommittedRef.current = false;
      }
      return applied;
    },
    [loadBuildDocument],
  );

  const commitSourceImport = useCallback(
    async (record: WorkspaceDocumentRecord, markdown: string): Promise<WorkspaceDocumentRecord> => {
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: record.document_id,
        markdown,
        expected_revision: record.revision,
        write_mode: "source_import",
      });
      if (!prepared.writer_confirm_token) {
        throw new Error("Source import prepare did not return a confirm token");
      }
      const committed = await commitTiptapMarkdownWrite({
        document_id: record.document_id,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
        expected_revision: record.revision,
        write_mode: "source_import",
      });
      importCommittedRef.current = true;
      setPendingImportDocumentId(record.document_id);
      return committed.committed_record;
    },
    [],
  );

  const resolveImportRecordForRetry = useCallback(async (): Promise<WorkspaceDocumentRecord> => {
    const retained = createControllerRef.current.getState().record;
    if (retained == null) {
      throw new Error("No created source is available to import into");
    }
    if (importCommittedRef.current) {
      const snapshot = await getWorkspaceDocumentSnapshot(retained.document_id);
      if (snapshot.record.content_status === "committed") {
        return snapshot.record;
      }
    }
    return retained;
  }, []);

  const creatableCampaignIds = useMemo(
    () =>
      resolveBuildCreateCampaignChoices({
        documents,
        activeCampaignId: activeRecord?.campaign_id,
      }),
    [activeRecord?.campaign_id, documents],
  );
  const creatableCampaignIdsRef = useRef(creatableCampaignIds);
  creatableCampaignIdsRef.current = creatableCampaignIds;

  const createDocument = useCallback(
    async ({ title, campaignId }: { title: string; campaignId: string }) => {
      const campaign = campaignId.trim();
      if (!creatableCampaignIdsRef.current.includes(campaign)) {
        setCreateError("Choose a campaign from the list");
        return;
      }
      const worldId = resolveWorldIdForBuildCreate(campaign);
      if (!worldId) {
        setCreateError("Choose a campaign mapped to an admitted world");
        return;
      }
      setCreating(true);
      setCreateError(null);
      setActivationError(null);
      setImportError(null);
      importCommittedRef.current = false;
      setPendingImportDocumentId(null);
      try {
        const created = await createControllerRef.current.create(
          buildWorldbuildingCreateIntent(title, campaign),
        );
        void refreshDocuments();
        if (!created.intentCurrent) {
          return;
        }
        try {
          await activateCreatedRecord(created.record);
        } catch (error) {
          const message =
            error instanceof WorkspaceDocumentCreationError
              ? error.message
              : error instanceof Error
                ? error.message
                : "Failed to open created worldbuilding source";
          setActivationError(message);
        }
      } catch (error) {
        if (error instanceof WorkspaceDocumentCreationError) {
          if (error.code === "create_failed") {
            setCreateError(error.message);
          }
        } else if (error instanceof Error) {
          setCreateError(error.message);
        } else {
          setCreateError("Failed to create worldbuilding source");
        }
      } finally {
        setCreating(false);
      }
    },
    [activateCreatedRecord, refreshDocuments],
  );

  const importSourceDocument = useCallback(
    async ({
      title,
      campaignId,
      markdown,
    }: {
      title: string;
      campaignId: string;
      markdown: string;
    }) => {
      const campaign = campaignId.trim();
      const body = markdown.trim();
      if (!body) {
        setImportError("Paste non-empty Markdown to import");
        return;
      }
      if (!creatableCampaignIdsRef.current.includes(campaign)) {
        setImportError("Choose a campaign from the list");
        return;
      }
      const worldId = resolveWorldIdForBuildCreate(campaign);
      if (!worldId) {
        setImportError("Choose a campaign mapped to an admitted world");
        return;
      }
      setCreating(true);
      setCreateError(null);
      setActivationError(null);
      setImportError(null);
      try {
        let record: WorkspaceDocumentRecord;
        const createState = createControllerRef.current.getState();
        if (
          createState.record != null &&
          createState.phase !== "create_failed" &&
          pendingImportDocumentId === createState.record.document_id &&
          !importCommittedRef.current
        ) {
          record = createState.record;
        } else {
          importCommittedRef.current = false;
          const created = await createControllerRef.current.create(
            buildWorldbuildingCreateIntent(title, campaign),
          );
          void refreshDocuments();
          if (!created.intentCurrent) {
            return;
          }
          record = created.record;
          setPendingImportDocumentId(record.document_id);
        }

        let committedRecord = record;
        if (!importCommittedRef.current) {
          committedRecord = await commitSourceImport(record, body);
        } else {
          const snapshot = await getWorkspaceDocumentSnapshot(record.document_id);
          committedRecord = snapshot.record;
        }

        try {
          await activateCreatedRecord(committedRecord);
        } catch (error) {
          const message =
            error instanceof WorkspaceDocumentCreationError
              ? error.message
              : error instanceof Error
                ? error.message
                : "Failed to open imported source";
          setActivationError(
            importCommittedRef.current
              ? "Source imported; could not open it yet"
              : message,
          );
        }
      } catch (error) {
        const message =
          error instanceof WorkspaceDocumentCreationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "Failed to import source";
        if (error instanceof WorkspaceDocumentCreationError && error.code === "create_failed") {
          setImportError(message);
        } else {
          setImportError(message);
          const retained = createControllerRef.current.getState().record;
          if (retained != null) {
            setPendingImportDocumentId(retained.document_id);
          }
        }
      } finally {
        setCreating(false);
      }
    },
    [
      activateCreatedRecord,
      commitSourceImport,
      pendingImportDocumentId,
      refreshDocuments,
    ],
  );

  const retryImportSource = useCallback(
    async ({ markdown }: { markdown: string }) => {
      const body = markdown.trim();
      if (!body) {
        setImportError("Paste non-empty Markdown to import");
        return;
      }
      setCreating(true);
      setImportError(null);
      setActivationError(null);
      try {
        if (importCommittedRef.current) {
          const record = await resolveImportRecordForRetry();
          await activateCreatedRecord(record);
          return;
        }
        const record = await resolveImportRecordForRetry();
        const committedRecord = await commitSourceImport(record, body);
        try {
          await activateCreatedRecord(committedRecord);
        } catch (error) {
          setActivationError("Source imported; could not open it yet");
          void error;
        }
      } catch (error) {
        setImportError(error instanceof Error ? error.message : "Failed to import source");
      } finally {
        setCreating(false);
      }
    },
    [activateCreatedRecord, commitSourceImport, resolveImportRecordForRetry],
  );

  const retryCreatedDocument = useCallback(async () => {
    setCreating(true);
    setActivationError(null);
    try {
      if (importCommittedRef.current && pendingImportDocumentId) {
        const snapshot = await getWorkspaceDocumentSnapshot(pendingImportDocumentId);
        await activateCreatedRecord(snapshot.record);
        return;
      }
      const record = createControllerRef.current.getState().record;
      if (record == null) {
        setActivationError("No created source is available to open");
        return;
      }
      await activateCreatedRecord(record);
    } catch (error) {
      const message =
        error instanceof WorkspaceDocumentCreationError
          ? error.message
          : error instanceof Error
            ? error.message
            : importCommittedRef.current
              ? "Source imported; could not open it yet"
              : "Failed to open created worldbuilding source";
      setActivationError(message);
    } finally {
      setCreating(false);
    }
  }, [activateCreatedRecord, pendingImportDocumentId]);

  const suggestedCreateCampaignId = useMemo(
    () =>
      resolveSuggestedBuildCreateCampaignId({
        activeCampaignId: activeRecord?.campaign_id,
        search: locationSearch,
        creatableCampaignIds,
      }),
    [activeRecord?.campaign_id, creatableCampaignIds, locationSearch],
  );
  return {
    activeRecord,
    activeDocumentId,
    documents,
    listStatus,
    loadStatus,
    switching,
    switchError,
    creating,
    createError,
    activationError,
    importError,
    selectDocument,
    createDocument: (payload) => void createDocument(payload),
    importSourceDocument: (payload) => void importSourceDocument(payload),
    retryImportSource: (payload) => void retryImportSource(payload),
    retryCreatedDocument: () => void retryCreatedDocument(),
    refreshDocuments: () => void refreshDocuments(),
    creatableCampaignIds,
    suggestedCreateCampaignId,
    pendingImportDocumentId,
  };
}
