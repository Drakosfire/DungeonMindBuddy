import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  commitTiptapMarkdownWrite,
  createWorldContainer,
  getWorkspaceDocumentSnapshot,
  listWorkspaceDocuments,
  listWorldContainers,
  prepareTiptapMarkdownWrite,
  updateWorkspaceDocumentMetadata,
} from "../api/liveApi";
import type {
  WorldContainerRecord,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../api/types";
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
import type {
  BuildSourceDestinationIntent,
  BuildSourceDestinationOption,
} from "./BuildDocumentCreateControl";

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
  worldId: string,
): {
  kind: "worldbuilding_source";
  campaignId: string;
  title: string;
  worldId: string;
  documentClass: string;
  authorityState: "draft";
  visibilityState: "internal";
} {
  return {
    kind: "worldbuilding_source",
    campaignId,
    title,
    worldId,
    documentClass: "lore",
    authorityState: "draft",
    visibilityState: "internal",
  };
}

/**
 * Create or reconcile one managed world via server-owned idempotence.
 * On ambiguous create failure, retry POST rather than reimplementing the
 * server's casefold/whitespace duplicate rule in the client.
 */
async function ensureManagedWorld(name: string): Promise<WorldContainerRecord> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new Error("That world name is required.");
  }
  try {
    return await createWorldContainer({ name: trimmed });
  } catch (firstError) {
    try {
      return await createWorldContainer({ name: trimmed });
    } catch {
      throw firstError instanceof Error
        ? firstError
        : new Error("Could not create the world.");
    }
  }
}

async function resolveBuildDestinationScope(
  destination: BuildSourceDestinationIntent,
): Promise<{ campaignId: string; worldId: string; createdNewWorld: boolean }> {
  if (destination.kind === "campaign") {
    const campaignId = destination.campaignId.trim();
    const worldId = resolveWorldIdForBuildCreate(campaignId);
    if (!worldId) {
      throw new Error("Choose a campaign mapped to an admitted world");
    }
    return { campaignId, worldId, createdNewWorld: false };
  }
  if (destination.kind === "world") {
    const worldId = destination.worldId.trim();
    if (!worldId) {
      throw new Error("Choose a destination");
    }
    return { campaignId: worldId, worldId, createdNewWorld: false };
  }
  const world = await ensureManagedWorld(destination.name);
  return {
    campaignId: world.world_id,
    worldId: world.world_id,
    createdNewWorld: true,
  };
}

const PENDING_SOURCE_IMPORT_STORAGE_KEY = "dmb.build.pendingSourceImport.v1";

function readPendingImportDocumentIdFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(PENDING_SOURCE_IMPORT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { documentId?: string };
    const documentId = parsed.documentId?.trim();
    return documentId || null;
  } catch {
    return null;
  }
}

function writePendingImportDocumentIdToStorage(documentId: string | null): void {
  if (typeof window === "undefined") return;
  if (documentId) {
    sessionStorage.setItem(
      PENDING_SOURCE_IMPORT_STORAGE_KEY,
      JSON.stringify({ documentId }),
    );
  } else {
    sessionStorage.removeItem(PENDING_SOURCE_IMPORT_STORAGE_KEY);
  }
}

/** Pending-lifecycle empty draft only — never reuse an arbitrary active Canvas draft. */
function isPendingImportableDraft(
  record: WorkspaceDocumentRecord | null | undefined,
  campaignId: string,
  worldId: string | null,
): boolean {
  return (
    record != null &&
    record.kind === "worldbuilding_source" &&
    record.status === "active" &&
    record.content_status === "draft" &&
    record.campaign_id === campaignId &&
    (record.world_id ?? null) === worldId
  );
}

function recordMatchesImportScope(
  record: WorkspaceDocumentRecord,
  campaignId: string,
  worldId: string | null,
): boolean {
  return record.campaign_id === campaignId && (record.world_id ?? null) === worldId;
}

function isSnapshotImportCommitted(
  snapshot: WorkspaceDocumentSnapshot,
  expectedMarkdown: string,
): boolean {
  return (
    snapshot.record.content_status === "committed" &&
    snapshot.file_exists &&
    snapshot.markdown === expectedMarkdown
  );
}

function isSnapshotActivationReady(snapshot: WorkspaceDocumentSnapshot): boolean {
  return snapshot.record.content_status === "committed" && snapshot.file_exists;
}

async function applyImportTitleIfNeeded(
  record: WorkspaceDocumentRecord,
  title: string,
): Promise<WorkspaceDocumentRecord> {
  if (record.title === title) return record;
  return updateWorkspaceDocumentMetadata(record.document_id, {
    title,
    expected_revision: record.revision,
  });
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
  createDocument: (payload: {
    title: string;
    destination: BuildSourceDestinationIntent;
  }) => void;
  importSourceDocument: (payload: {
    title: string;
    destination: BuildSourceDestinationIntent;
    markdown: string;
  }) => void;
  retryImportSource: (payload: { markdown: string }) => void;
  retryCreatedDocument: () => void;
  refreshDocuments: () => void;
  /** Existing campaign + managed-world destinations for New Source / Import. */
  destinationOptions: BuildSourceDestinationOption[];
  suggestedDestinationValue: string | null;
  /** @deprecated Prefer destinationOptions; retained for transitional callers. */
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
  const [managedWorlds, setManagedWorlds] = useState<WorldContainerRecord[]>([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [activationError, setActivationError] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [pendingImportDocumentId, setPendingImportDocumentIdState] = useState<string | null>(
    () => readPendingImportDocumentIdFromStorage(),
  );
  const pendingImportDocumentIdRef = useRef<string | null>(pendingImportDocumentId);
  pendingImportDocumentIdRef.current = pendingImportDocumentId;
  const persistPendingImportDocumentId = useCallback((documentId: string | null) => {
    pendingImportDocumentIdRef.current = documentId;
    setPendingImportDocumentIdState(documentId);
    writePendingImportDocumentIdToStorage(documentId);
  }, []);
  const importCommittedRef = useRef(false);

  const createControllerRef = useRef(createWorkspaceDocumentCreationController());
  const activeRecordRef = useRef<WorkspaceDocumentRecord | null>(null);
  activeRecordRef.current = activeRecord;
  const locationSearchRef = useRef(locationSearch);
  locationSearchRef.current = locationSearch;
  const documentLoadGenerationRef = useRef(0);
  const selectorListGenerationRef = useRef(0);

  const activeDocumentId = activeRecord?.document_id ?? null;
  const refreshManagedWorlds = useCallback(async () => {
    try {
      const listed = await listWorldContainers();
      setManagedWorlds(listed.records);
    } catch {
      // Keep last-known managed worlds; source create still fails closed if root missing.
    }
  }, []);

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
    void refreshManagedWorlds();
  }, [refreshDocuments, refreshManagedWorlds]);

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
          if (!pendingImportDocumentIdRef.current) {
            importCommittedRef.current = false;
          }
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
    [persistPendingImportDocumentId, refreshDocuments],
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
      if (documentId !== pendingImportDocumentIdRef.current) {
        persistPendingImportDocumentId(null);
        importCommittedRef.current = false;
      }
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
    [documents, loadBuildDocument, persistPendingImportDocumentId],
  );

  const activateCreatedRecord = useCallback(
    async (record: WorkspaceDocumentRecord): Promise<boolean> => {
      if (typeof window === "undefined") return false;
      const search = buildDocumentSelectionSearch(
        window.location.search,
        record.document_id,
        record.campaign_id,
      );
      const createState = createControllerRef.current.getState();
      const canUseCreateControllerActivate =
        createState.record != null &&
        createState.record.document_id === record.document_id &&
        (createState.phase === "created" ||
          createState.phase === "activation_failed" ||
          createState.phase === "activating" ||
          createState.phase === "activated");

      if (!canUseCreateControllerActivate) {
        const applied = await loadBuildDocument(search, { mode: "push", search }, "create_activate");
        if (applied) {
          setActivationError(null);
          persistPendingImportDocumentId(null);
          importCommittedRef.current = false;
        }
        return applied;
      }

      const { applied } = await createControllerRef.current.activate(async () =>
        loadBuildDocument(search, { mode: "push", search }, "create_activate"),
      );
      if (applied) {
        setActivationError(null);
        persistPendingImportDocumentId(null);
        importCommittedRef.current = false;
      }
      return applied;
    },
    [loadBuildDocument, persistPendingImportDocumentId],
  );

  const commitSourceImport = useCallback(
    async (record: WorkspaceDocumentRecord, markdown: string): Promise<WorkspaceDocumentRecord> => {
      try {
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
        persistPendingImportDocumentId(record.document_id);
        return committed.committed_record;
      } catch (error) {
        const snapshot = await getWorkspaceDocumentSnapshot(record.document_id);
        if (isSnapshotImportCommitted(snapshot, markdown)) {
          importCommittedRef.current = true;
          persistPendingImportDocumentId(record.document_id);
          return snapshot.record;
        }
        if (
          snapshot.record.content_status === "committed" &&
          snapshot.file_exists &&
          snapshot.markdown !== markdown
        ) {
          throw new Error("Imported content does not match pasted Markdown");
        }
        throw error;
      }
    },
    [persistPendingImportDocumentId],
  );

  const resolveImportRecordForRetry = useCallback(
    async (expectedMarkdown: string): Promise<WorkspaceDocumentRecord> => {
      const pendingId = pendingImportDocumentIdRef.current;
      if (pendingId) {
        const snapshot = await getWorkspaceDocumentSnapshot(pendingId);
        if (isSnapshotImportCommitted(snapshot, expectedMarkdown)) {
          importCommittedRef.current = true;
          return snapshot.record;
        }
        if (
          snapshot.record.content_status === "committed" &&
          snapshot.file_exists &&
          snapshot.markdown !== expectedMarkdown
        ) {
          throw new Error("Imported content does not match pasted Markdown");
        }
        return snapshot.record;
      }

      const retained = createControllerRef.current.getState().record;
      if (retained == null) {
        throw new Error("No created source is available to import into");
      }
      const snapshot = await getWorkspaceDocumentSnapshot(retained.document_id);
      if (isSnapshotImportCommitted(snapshot, expectedMarkdown)) {
        importCommittedRef.current = true;
        return snapshot.record;
      }
      if (
        snapshot.record.content_status === "committed" &&
        snapshot.file_exists &&
        snapshot.markdown !== expectedMarkdown
      ) {
        throw new Error("Imported content does not match pasted Markdown");
      }
      return snapshot.record;
    },
    [],
  );

  const creatableCampaignIds = useMemo(
    () =>
      resolveBuildCreateCampaignChoices({
        documents,
        activeCampaignId: activeRecord?.campaign_id,
      }),
    [activeRecord?.campaign_id, documents],
  );

  const destinationOptions = useMemo((): BuildSourceDestinationOption[] => {
    const options: BuildSourceDestinationOption[] = [];
    const seen = new Set<string>();
    for (const campaignId of creatableCampaignIds) {
      const worldId = resolveWorldIdForBuildCreate(campaignId);
      if (!worldId) continue;
      const value = `campaign:${campaignId}`;
      if (seen.has(value)) continue;
      seen.add(value);
      options.push({
        kind: "campaign",
        campaignId,
        worldId,
        label: campaignId,
        value,
      });
    }
    for (const world of managedWorlds) {
      // Kind-qualified values stay distinct even when world_id collides with a
      // campaign id (e.g. managed world "Longmont C2" → world_id longmont-c2).
      const value = `world:${world.world_id}`;
      if (seen.has(value)) continue;
      seen.add(value);
      options.push({
        kind: "world",
        worldId: world.world_id,
        label: world.name,
        value,
      });
    }
    return options;
  }, [creatableCampaignIds, managedWorlds]);

  const createDocument = useCallback(
    async ({
      title,
      destination,
    }: {
      title: string;
      destination: BuildSourceDestinationIntent;
    }) => {
      setCreating(true);
      setCreateError(null);
      setActivationError(null);
      setImportError(null);
      importCommittedRef.current = false;
      persistPendingImportDocumentId(null);
      let worldCreated = false;
      try {
        const scope = await resolveBuildDestinationScope(destination);
        worldCreated = scope.createdNewWorld;
        void refreshManagedWorlds();
        const created = await createControllerRef.current.create(
          buildWorldbuildingCreateIntent(title, scope.campaignId, scope.worldId),
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
        const message =
          error instanceof WorkspaceDocumentCreationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "Failed to create worldbuilding source";
        if (worldCreated) {
          setCreateError(
            `The world was created, but the source could not be created. ${message}`,
          );
        } else if (error instanceof WorkspaceDocumentCreationError) {
          if (error.code === "create_failed") {
            setCreateError(message);
          }
        } else {
          setCreateError(message);
        }
      } finally {
        setCreating(false);
      }
    },
    [activateCreatedRecord, persistPendingImportDocumentId, refreshDocuments, refreshManagedWorlds],
  );

  const importSourceDocument = useCallback(
    async ({
      title,
      destination,
      markdown,
    }: {
      title: string;
      destination: BuildSourceDestinationIntent;
      markdown: string;
    }) => {
      if (markdown.trim().length === 0) {
        setImportError("Paste non-empty Markdown to import");
        return;
      }
      setCreating(true);
      setCreateError(null);
      setActivationError(null);
      setImportError(null);
      let worldCreated = false;
      try {
        const scope = await resolveBuildDestinationScope(destination);
        worldCreated = scope.createdNewWorld;
        void refreshManagedWorlds();
        const campaign = scope.campaignId;
        const worldId = scope.worldId;

        let record: WorkspaceDocumentRecord;
        let skipCommit = false;
        const pendingId = pendingImportDocumentIdRef.current;
        if (pendingId) {
          // Only the persisted pending-import lifecycle may reuse an identity.
          // Fresh Import never targets the currently active Canvas draft.
          const snapshot = await getWorkspaceDocumentSnapshot(pendingId);
          const pendingRecord = snapshot.record;
          if (!recordMatchesImportScope(pendingRecord, campaign, worldId)) {
            throw new Error(
              "This source belongs to a different destination.",
            );
          }
          if (isSnapshotImportCommitted(snapshot, markdown)) {
            record = pendingRecord;
            importCommittedRef.current = true;
            skipCommit = true;
          } else if (isPendingImportableDraft(pendingRecord, campaign, worldId)) {
            record = await applyImportTitleIfNeeded(pendingRecord, title);
            persistPendingImportDocumentId(record.document_id);
          } else if (snapshot.file_exists && pendingRecord.content_status === "committed") {
            throw new Error("Imported content does not match pasted Markdown");
          } else {
            throw new Error(
              "A pending import source exists but cannot be reused for this import",
            );
          }
        } else {
          importCommittedRef.current = false;
          const created = await createControllerRef.current.create(
            buildWorldbuildingCreateIntent(title, campaign, worldId),
          );
          void refreshDocuments();
          if (!created.intentCurrent) {
            return;
          }
          record = created.record;
          persistPendingImportDocumentId(record.document_id);
        }

        let committedRecord = record;
        if (!skipCommit && !importCommittedRef.current) {
          committedRecord = await commitSourceImport(record, markdown);
        } else if (importCommittedRef.current && !skipCommit) {
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
        if (worldCreated && !(pendingImportDocumentIdRef.current || createControllerRef.current.getState().record)) {
          setImportError(
            `The world was created, but the source could not be created. ${message}`,
          );
        } else if (error instanceof WorkspaceDocumentCreationError && error.code === "create_failed") {
          setImportError(message);
        } else {
          setImportError(message);
          const retained = createControllerRef.current.getState().record;
          if (retained != null) {
            persistPendingImportDocumentId(retained.document_id);
          } else if (pendingImportDocumentIdRef.current) {
            persistPendingImportDocumentId(pendingImportDocumentIdRef.current);
          }
        }
      } finally {
        setCreating(false);
      }
    },
    [
      activateCreatedRecord,
      commitSourceImport,
      persistPendingImportDocumentId,
      refreshDocuments,
      refreshManagedWorlds,
    ],
  );

  const retryImportSource = useCallback(
    async ({ markdown }: { markdown: string }) => {
      if (markdown.trim().length === 0) {
        setImportError("Paste non-empty Markdown to import");
        return;
      }
      setCreating(true);
      setImportError(null);
      setActivationError(null);
      try {
        const record = await resolveImportRecordForRetry(markdown);
        if (importCommittedRef.current) {
          await activateCreatedRecord(record);
          return;
        }
        const committedRecord = await commitSourceImport(record, markdown);
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
      const pendingId = pendingImportDocumentIdRef.current;
      if (pendingId) {
        const snapshot = await getWorkspaceDocumentSnapshot(pendingId);
        if (isSnapshotActivationReady(snapshot)) {
          importCommittedRef.current = true;
        }
      }
      if (importCommittedRef.current && pendingId) {
        const snapshot = await getWorkspaceDocumentSnapshot(pendingId);
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
  const suggestedDestinationValue = useMemo(() => {
    const activeCampaign = activeRecord?.campaign_id?.trim() ?? "";
    const activeWorld = activeRecord?.world_id?.trim() ?? "";

    // World-level Build sources use campaign_id === world_id. Prefer the
    // kind-qualified world destination before any campaign suggestion so a
    // colliding campaign id cannot steal the default (e.g. managed world
    // longmont-c2 vs campaign longmont-c2).
    if (activeWorld && activeWorld === activeCampaign) {
      const worldMatch = destinationOptions.find(
        (option) => option.kind === "world" && option.worldId === activeWorld,
      );
      if (worldMatch) return worldMatch.value;
    }

    if (suggestedCreateCampaignId) {
      const match = destinationOptions.find(
        (option) =>
          option.kind === "campaign" && option.campaignId === suggestedCreateCampaignId,
      );
      if (match) return match.value;
    }

    if (activeCampaign) {
      const campaignMatch = destinationOptions.find(
        (option) =>
          option.kind === "campaign" && option.campaignId === activeCampaign,
      );
      if (campaignMatch) return campaignMatch.value;
      const worldMatch = destinationOptions.find(
        (option) => option.kind === "world" && option.worldId === activeCampaign,
      );
      if (worldMatch) return worldMatch.value;
    }
    return destinationOptions[0]?.value ?? null;
  }, [activeRecord?.campaign_id, activeRecord?.world_id, destinationOptions, suggestedCreateCampaignId]);

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
    destinationOptions,
    suggestedDestinationValue,
    creatableCampaignIds,
    suggestedCreateCampaignId,
    pendingImportDocumentId,
  };
}
