import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import { openIndexedDbLocalWorldRepository, LOCAL_WORLD_DATABASE_NAME } from "../indexedDbLocalWorldRepository";
import { hasPendingWorldNotesDrafts } from "../localWorldDocumentAuthoring";
import type { CommitSemanticResult, LocalWorldConflictCandidate, LocalWorldId, LocalWorldPackageRepository, LocalWorldRecord, WriteLayoutResult } from "../localWorldRepository";
import { createLocalWorldGraphAdapter } from "../worldGraphCanvas/localWorldGraphAdapter";
import type { WorldGraphEditorDraft, WorldGraphEditorDraftField } from "../worldGraphCanvas/WorldGraphCanvas";
import { LocalWorldNotesEditor } from "./LocalWorldNotesEditor";
import "./localWorldSurface.css";

const WorldGraphCanvas = lazy(() => import("../worldGraphCanvas/WorldGraphCanvas").then((module) => ({ default: module.WorldGraphCanvas })));

// Keep unsaved title candidates while App routes/components remount in this tab.
// This is deliberately volatile presentation state, not a second durable ledger.
interface PendingTitleDraft {
  readonly value: string;
  readonly token: symbol;
}

const pendingTitleDrafts = new Map<LocalWorldId, PendingTitleDraft>();
interface SavedGraphEditorDraft {
  readonly version: number;
  readonly draft: WorldGraphEditorDraft | null;
}
const graphEditorDrafts = new Map<LocalWorldId, SavedGraphEditorDraft>();
interface FirstObjectDraft { readonly name: string; readonly kind: string }
interface SavedFirstObjectDraft { readonly version: number; readonly draft: FirstObjectDraft | null }
const firstObjectDrafts = new Map<LocalWorldId, SavedFirstObjectDraft>();
const graphEditorDraftListeners = new Set<() => void>();
const pendingLocalWrites = new Set<symbol>();
let beforeUnloadProtectionInstalled = false;
const MAX_GRAPH_EDITOR_SESSIONS = 3;

function warnBeforeLeavingWithLocalWork(event: BeforeUnloadEvent): void {
  event.preventDefault();
  event.returnValue = "";
}

function syncBeforeUnloadProtection(): void {
  if (typeof window === "undefined") return;
  const hasGraphDraft = [...graphEditorDrafts.values()].some((item) => item.draft !== null);
  const hasFirstObjectDraft = [...firstObjectDrafts.values()].some((item) => item.draft !== null);
  const shouldProtect = pendingTitleDrafts.size > 0 || hasGraphDraft || hasFirstObjectDraft || hasPendingWorldNotesDrafts() || pendingLocalWrites.size > 0;
  if (shouldProtect && !beforeUnloadProtectionInstalled) {
    window.addEventListener("beforeunload", warnBeforeLeavingWithLocalWork);
    beforeUnloadProtectionInstalled = true;
  } else if (!shouldProtect && beforeUnloadProtectionInstalled) {
    window.removeEventListener("beforeunload", warnBeforeLeavingWithLocalWork);
    beforeUnloadProtectionInstalled = false;
  }
}

function notifyGraphEditorDraftListeners(): void {
  for (const listener of graphEditorDraftListeners) listener();
}

function readGraphEditorDraft(worldId: LocalWorldId): SavedGraphEditorDraft {
  return graphEditorDrafts.get(worldId) ?? { version: 0, draft: null };
}

function writeGraphEditorDraft(worldId: LocalWorldId, draft: WorldGraphEditorDraft | null, version: number, expectedVersion?: number): void {
  const current = readGraphEditorDraft(worldId);
  if (expectedVersion !== undefined && current.version !== expectedVersion) return;
  if (version < current.version) return;
  graphEditorDrafts.set(worldId, { version, draft });
  syncBeforeUnloadProtection();
  notifyGraphEditorDraftListeners();
}

function clearGraphEditorDraftSubmission(worldId: LocalWorldId, field: WorldGraphEditorDraftField, submittedToken: number): void {
  const saved = readGraphEditorDraft(worldId);
  const current = saved.draft;
  if (!current) return;
  const tokenMatches = field === "rename" ? current.renameToken === submittedToken
    : field === "object" ? current.objectToken === submittedToken
      : current.relationshipToken === submittedToken;
  if (!tokenMatches) return;

  const version = saved.version + 1;
  const next: WorldGraphEditorDraft = field === "rename"
    ? { ...current, version, renameToken: current.renameToken + 1, renameId: null, renameValue: "" }
    : field === "object"
      ? { ...current, version, objectToken: current.objectToken + 1, showObjectForm: false, objectName: "" }
      : { ...current, version, relationshipToken: current.relationshipToken + 1, showRelationshipForm: false, relationshipKind: "" };
  const hasUnresolvedDraft = next.renameId !== null || next.showObjectForm || next.objectName.length > 0 ||
    next.showRelationshipForm || next.relationshipKind.length > 0;
  writeGraphEditorDraft(worldId, hasUnresolvedDraft ? next : null, version, saved.version);
}

function subscribeGraphEditorDrafts(listener: () => void): () => void {
  graphEditorDraftListeners.add(listener);
  return () => graphEditorDraftListeners.delete(listener);
}

function readFirstObjectDraft(worldId: LocalWorldId): SavedFirstObjectDraft {
  return firstObjectDrafts.get(worldId) ?? { version: 0, draft: null };
}

function saveFirstObjectDraft(worldId: LocalWorldId, name: string, kind: string): void {
  const current = readFirstObjectDraft(worldId);
  const version = current.version + 1;
  writeFirstObjectDraft(worldId, name.trim() ? { name, kind } : null, version, name.trim() ? undefined : current.version);
}

function writeFirstObjectDraft(worldId: LocalWorldId, draft: FirstObjectDraft | null, version: number, expectedVersion?: number): void {
  const current = readFirstObjectDraft(worldId);
  if (expectedVersion !== undefined && current.version !== expectedVersion) return;
  if (version < current.version) return;
  firstObjectDrafts.set(worldId, { version, draft });
  syncBeforeUnloadProtection();
  notifyGraphEditorDraftListeners();
}

function setPendingTitleDraft(worldId: LocalWorldId, draft: string, committedTitle: string): void {
  if (draft.trim() === committedTitle) pendingTitleDrafts.delete(worldId);
  else pendingTitleDrafts.set(worldId, { value: draft, token: Symbol("local-world-title-draft") });
  syncBeforeUnloadProtection();
}

function clearPendingTitleDraft(worldId: LocalWorldId, expectedToken?: symbol): void {
  const current = pendingTitleDrafts.get(worldId);
  if (!current || (expectedToken !== undefined && current.token !== expectedToken)) return;
  pendingTitleDrafts.delete(worldId);
  syncBeforeUnloadProtection();
}

function beginPendingLocalWrite(): () => void {
  const token = Symbol("local-world-write");
  pendingLocalWrites.add(token);
  syncBeforeUnloadProtection();
  notifyGraphEditorDraftListeners();
  return () => {
    pendingLocalWrites.delete(token);
    syncBeforeUnloadProtection();
    notifyGraphEditorDraftListeners();
  };
}

type RepositoryResult = { readonly status: "opened"; readonly repository: LocalWorldPackageRepository; readonly close?: () => void }
  | { readonly status: "error"; readonly message: string };
type OpenRepository = () => Promise<RepositoryResult>;
type SaveStatus = "loading" | "saved" | "dirty" | "saving" | "error" | "conflict";

const defaultOpenRepository: OpenRepository = async () => {
  const result = await openIndexedDbLocalWorldRepository(LOCAL_WORLD_DATABASE_NAME);
  return result.status === "opened"
    ? { status: "opened", repository: result.repository, close: () => (result.repository as typeof result.repository & { close?: () => void }).close?.() }
    : { status: "error", message: result.message };
};

function makePublication(input: {
  readonly localWorldId: string | null;
  readonly title: string | null;
  readonly status: SaveStatus;
  readonly editing: boolean;
  readonly titleDirty: boolean;
  readonly canExport: boolean;
  readonly onEditTitle: () => void;
  readonly onSaveTitle: () => void;
  readonly onExport: () => void;
}) {
  const surfaceId = "index";
  const target = input.localWorldId ? { kind: "local-world", id: input.localWorldId } : null;
  return {
    surfaceId,
    label: "Buddy Surface",
    identity: buildSurfaceInteractionIdentity({ surfaceId, instanceParts: ["local-world", input.localWorldId ?? "empty"] }),
    canvas: target ? { canvasId: "local-world-canvas", workObject: target } : null,
    agentContext: {
      label: "Buddy Surface",
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: input.title ? `Local World · ${input.title} · ${input.status === "saved" ? "saved in this browser" : "local draft"}` : "No local World is open.",
      pointers: [],
    },
    tools: input.localWorldId ? [{
      id: "local-world-export",
      label: "Export package",
      eyebrow: "Save menu",
      placement: { groupId: "local-world-save", groupLabel: "Save", groupOrder: 0, itemOrder: 1 },
      availability: input.canExport ? { status: "enabled" as const } : { status: "disabled" as const, disabledReason: "Save or finish the title edit before exporting." },
      activation: { kind: "command" as const, invoke: input.onExport },
    }] : [],
    editCommands: target ? [
      {
        id: "local-world-edit-title",
        label: input.editing ? "Title editing" : "Edit World title",
        placement: { groupId: "local-world-title", groupLabel: "World title", groupOrder: 0, itemOrder: 0 },
        availability: { status: "enabled" as const },
        target,
        pressed: input.editing,
        invoke: input.onEditTitle,
      },
      {
        id: "local-world-save-title",
        label: "Save in this browser",
        eyebrow: input.titleDirty ? "Unsaved title" : "Local revision",
        placement: { groupId: "local-world-title", groupLabel: "World title", groupOrder: 0, itemOrder: 1 },
        availability: input.titleDirty
          ? { status: "enabled" as const }
          : { status: "disabled" as const, disabledReason: "There are no unsaved title changes." },
        target,
        invoke: input.onSaveTitle,
      },
    ] : [],
    projections: [],
    projectionBindings: [],
  };
}

function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.hidden = true;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function safeFileName(title: string): string {
  const stem = title.normalize("NFKC").replace(/[^a-z0-9-_]+/gi, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "local-world";
  return `${stem}.dmb-world.zip`;
}

export function LocalWorldSurface({
  openRepository = defaultOpenRepository,
  children,
}: {
  openRepository?: OpenRepository;
  children?: ReactNode;
}) {
  const { publishSurfaceContext } = useAgentInteraction();
  const [repository, setRepository] = useState<LocalWorldPackageRepository | null>(null);
  const [repositoryError, setRepositoryError] = useState<string | null>(null);
  const [records, setRecords] = useState<readonly LocalWorldRecord[]>([]);
  const [record, setRecord] = useState<LocalWorldRecord | null>(null);
  const recordRef = useRef<LocalWorldRecord | null>(record);
  recordRef.current = record;
  const [graphSessions, setGraphSessions] = useState<readonly LocalWorldRecord[]>([]);
  const [graphDraftRevision, setGraphDraftRevision] = useState(0);
  const [graphConflict, setGraphConflict] = useState<LocalWorldConflictCandidate | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [firstObjectName, setFirstObjectName] = useState("");
  const [firstObjectKind, setFirstObjectKind] = useState("person");
  const [titleDraft, setTitleDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<SaveStatus>("loading");
  const [notesStatus, setNotesStatus] = useState<"loading" | "ready" | "dirty" | "saving" | "saved" | "conflict" | "error">("ready");
  const [message, setMessage] = useState<string | null>(null);
  const mounted = useRef(false);
  const operationGeneration = useRef(0);
  const busyRef = useRef(false);
  const closeRepositoryRef = useRef<(() => void) | null>(null);
  const saveNotesRef = useRef<(() => void) | null>(null);
  const firstObjectDraftWorldRef = useRef<LocalWorldId | null>(null);
  const firstObjectDraftVersionRef = useRef(-1);
  useEffect(() => subscribeGraphEditorDrafts(() => setGraphDraftRevision((revision) => revision + 1)), []);
  useEffect(() => {
    if (!record) return;
    const worldId = record.snapshot.worldId;
    const saved = readFirstObjectDraft(worldId);
    if (firstObjectDraftWorldRef.current === worldId && firstObjectDraftVersionRef.current === saved.version) return;
    firstObjectDraftWorldRef.current = worldId;
    firstObjectDraftVersionRef.current = saved.version;
    setFirstObjectName(saved.draft?.name ?? "");
    setFirstObjectKind(saved.draft?.kind ?? "person");
  }, [graphDraftRevision, record?.snapshot.worldId]);
  const updateActiveRecord = useCallback((nextRecord: LocalWorldRecord | null) => {
    recordRef.current = nextRecord;
    setRecord(nextRecord);
  }, []);
  const rememberGraphRecord = useCallback((nextRecord: LocalWorldRecord) => {
    if (!nextRecord.snapshot.objects.length) return;
    setGraphSessions((current) => {
      const withoutCurrent = current.filter((item) => item.snapshot.worldId !== nextRecord.snapshot.worldId);
      return [...withoutCurrent, nextRecord];
    });
  }, []);
  const prepareGraphSessionSlot = useCallback((worldId: LocalWorldId, title: string) => {
    if (graphSessions.some((item) => item.snapshot.worldId === worldId) || graphSessions.length < MAX_GRAPH_EDITOR_SESSIONS) return true;
    const oldest = graphSessions[0];
    const shouldEvict = window.confirm(`This tab keeps unfinished graph editor drafts for up to ${MAX_GRAPH_EDITOR_SESSIONS} Worlds. Opening “${title}” will remove the editor draft for “${oldest.snapshot.title}”; its already saved World remains safe. Continue?`);
    if (!shouldEvict) return false;
    setGraphSessions((current) => current.filter((item) => item.snapshot.worldId !== oldest.snapshot.worldId));
    return true;
  }, [graphSessions]);
  const dirty = record !== null && titleDraft.trim() !== record.snapshot.title;
  const onNotesRecordChange = useCallback((nextRecord: LocalWorldRecord) => {
    const current = recordRef.current;
    if (!current || current.snapshot.worldId !== nextRecord.snapshot.worldId || nextRecord.localRevision < current.localRevision) return;
    updateActiveRecord(nextRecord);
    rememberGraphRecord(nextRecord);
    setRecords((items) => items.map((item) => item.snapshot.worldId === nextRecord.snapshot.worldId && item.localRevision <= nextRecord.localRevision ? nextRecord : item));
  }, [rememberGraphRecord, updateActiveRecord]);
  const onNotesBusyChange = useCallback((nextBusy: boolean) => {
    busyRef.current = nextBusy;
    setBusy(nextBusy);
  }, []);
  const registerNotesSaveRequest = useCallback((save: (() => void) | null) => { saveNotesRef.current = save; }, []);
  const displayStatus: SaveStatus = status === "error" || notesStatus === "error" ? "error"
    : status === "conflict" || notesStatus === "conflict" ? "conflict"
      : status === "saving" || notesStatus === "saving" ? "saving"
        : dirty || status === "dirty" || notesStatus === "dirty" ? "dirty"
          : notesStatus === "loading" ? "loading" : status;

  const refreshList = useCallback(async (repo: LocalWorldPackageRepository, generation: number) => {
    const result = await repo.listWorlds();
    if (!mounted.current || generation !== operationGeneration.current) return false;
    if (result.status !== "found") {
      setRepositoryError(result.message);
      return false;
    }
    setRecords(result.records);
    setRepositoryError(null);
    return true;
  }, []);

  const openStore = useCallback(async () => {
    const generation = ++operationGeneration.current;
    setStatus("loading");
    setRepositoryError(null);
    try {
      const result = await openRepository();
      if (!mounted.current || generation !== operationGeneration.current) {
        if (result.status === "opened") result.close?.();
        return;
      }
      if (result.status !== "opened") {
        setRepository(null);
        setRepositoryError(result.message);
        setStatus("error");
        return;
      }
      closeRepositoryRef.current?.();
      closeRepositoryRef.current = result.close ?? (() => {
        (result.repository as LocalWorldPackageRepository & { close?: () => void }).close?.();
      });
      setRepository(result.repository);
      const listed = await refreshList(result.repository, generation);
      if (mounted.current && generation === operationGeneration.current) setStatus(listed ? "saved" : "error");
    } catch (error) {
      if (!mounted.current || generation !== operationGeneration.current) return;
      setRepositoryError(error instanceof Error ? error.message : "Local storage could not be opened.");
      setStatus("error");
    }
  }, [openRepository, refreshList]);

  useEffect(() => {
    mounted.current = true;
    void openStore();
    return () => {
      mounted.current = false;
      operationGeneration.current += 1;
      closeRepositoryRef.current?.();
      closeRepositoryRef.current = null;
    };
  }, [openStore]);

  useEffect(() => {
    publishSurfaceContext({
      surfaceId: "index",
      label: "Buddy Surface",
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: record ? `Local World · ${record.snapshot.title}` : "Browser-local World workspace",
      sourceEnvelope: null,
      updatedAt: new Date().toISOString(),
    });
  }, [publishSurfaceContext, record]);

  const selectWorld = useCallback(async (worldId: string) => {
    if (!repository) return;
    const listedWorld = records.find((item) => item.snapshot.worldId === worldId as LocalWorldRecord["snapshot"]["worldId"]);
    if (listedWorld?.snapshot.objects.length && !prepareGraphSessionSlot(listedWorld.snapshot.worldId, listedWorld.snapshot.title)) return;
    const currentRecord = recordRef.current;
    if (currentRecord?.snapshot.objects.length) rememberGraphRecord(currentRecord);
    const generation = ++operationGeneration.current;
    setStatus("loading");
    setNotesStatus("loading");
    setMessage(null);
    updateActiveRecord(null);
    setGraphConflict(null);
    try {
      const result = await repository.readWorld(worldId as LocalWorldRecord["snapshot"]["worldId"]);
      if (!mounted.current || generation !== operationGeneration.current) return;
      if (result.status !== "found") {
        setMessage(result.status === "missing" ? "That local World is no longer available." : result.message);
        setStatus("error");
        await refreshList(repository, generation);
        return;
      }
      const localWorldId = worldId as LocalWorldId;
      const pendingDraft = pendingTitleDrafts.get(localWorldId);
      const firstObjectDraft = readFirstObjectDraft(localWorldId).draft;
      const hasPendingChanges = pendingDraft !== undefined && pendingDraft.value.trim() !== result.record.snapshot.title;
      if (pendingDraft !== undefined && !hasPendingChanges) clearPendingTitleDraft(localWorldId);
      updateActiveRecord(result.record);
      rememberGraphRecord(result.record);
      setGraphConflict(null);
      setTitleDraft(hasPendingChanges ? pendingDraft.value : result.record.snapshot.title);
      setEditing(hasPendingChanges);
      setFirstObjectName(firstObjectDraft?.name ?? "");
      setFirstObjectKind(firstObjectDraft?.kind ?? "person");
      setStatus(hasPendingChanges ? "dirty" : "saved");
    } catch (error) {
      if (!mounted.current || generation !== operationGeneration.current) return;
      setMessage(error instanceof Error ? error.message : "The local World could not be opened.");
      setStatus("error");
    }
  }, [prepareGraphSessionSlot, records, refreshList, rememberGraphRecord, repository, updateActiveRecord]);

  const createWorld = useCallback(async (event: FormEvent) => {
    event.preventDefault();
    if (!repository || repositoryError || busyRef.current || !newTitle.trim()) return;
    if (recordRef.current?.snapshot.objects.length) rememberGraphRecord(recordRef.current);
    busyRef.current = true;
    setBusy(true);
    setStatus("saving");
    setMessage(null);
    const finishPendingWrite = beginPendingLocalWrite();
    const generation = ++operationGeneration.current;
    const title = newTitle.trim();
    try {
      const result = await repository.createWorld({ title });
      if (!mounted.current || generation !== operationGeneration.current) return;
      if (result.status !== "created") {
        setMessage(result.message);
        setStatus("error");
        return;
      }
      setNotesStatus("loading");
      updateActiveRecord(result.record);
      setGraphConflict(null);
      setTitleDraft(result.record.snapshot.title);
      setNewTitle("");
      const firstObjectDraft = readFirstObjectDraft(result.record.snapshot.worldId).draft;
      setFirstObjectName(firstObjectDraft?.name ?? "");
      setFirstObjectKind(firstObjectDraft?.kind ?? "person");
      setEditing(false);
      setStatus("saved");
      await refreshList(repository, generation);
    } catch (error) {
      if (mounted.current && generation === operationGeneration.current) {
        setMessage(error instanceof Error ? error.message : "The local World could not be created.");
        setStatus("error");
      }
    } finally {
      busyRef.current = false;
      finishPendingWrite();
      if (mounted.current) setBusy(false);
    }
  }, [newTitle, refreshList, rememberGraphRecord, repository, repositoryError, updateActiveRecord]);

  const saveTitle = useCallback(async () => {
    if (!repository || repositoryError || !record || !dirty || busyRef.current) return;
    const nextTitle = titleDraft.trim();
    if (!nextTitle) {
      setMessage("Enter a World title before saving.");
      setStatus("error");
      return;
    }
    busyRef.current = true;
    setBusy(true);
    setStatus("saving");
    setMessage(null);
    const finishPendingWrite = beginPendingLocalWrite();
    const generation = operationGeneration.current;
    const savedRecord = record;
    const savedDraftToken = pendingTitleDrafts.get(savedRecord.snapshot.worldId)?.token;
    try {
      const result = await repository.commitSemanticEdit({
        worldId: savedRecord.snapshot.worldId,
        expectedLocalRevision: savedRecord.localRevision,
        nextSnapshot: { ...savedRecord.snapshot, title: nextTitle },
        edit: { classification: "buddy-local-only", description: "Renamed local World" },
      });
      if (result.status === "committed") {
        if (savedDraftToken !== undefined) clearPendingTitleDraft(savedRecord.snapshot.worldId, savedDraftToken);
        if (!mounted.current || generation !== operationGeneration.current) return;
        updateActiveRecord(result.record);
        rememberGraphRecord(result.record);
        setRecords((current) => current.map((item) => item.snapshot.worldId === result.record.snapshot.worldId ? result.record : item)
          .sort((left, right) => left.snapshot.title.localeCompare(right.snapshot.title) || left.snapshot.worldId.localeCompare(right.snapshot.worldId)));
        setTitleDraft(result.record.snapshot.title);
        setEditing(false);
        setStatus("saved");
        return;
      }
      if (!mounted.current || generation !== operationGeneration.current) return;
      if (result.status === "conflict") {
        updateActiveRecord(result.committed);
        rememberGraphRecord(result.committed);
        setRecords((current) => current.map((item) => item.snapshot.worldId === result.committed.snapshot.worldId ? result.committed : item));
        setMessage("Another tab saved a newer version. Your title is kept as a conflict candidate; choose whether to retry it.");
        setStatus("conflict");
      } else {
        setMessage(result.status === "missing" ? "This local World was removed before the title could be saved." : result.message);
        setStatus("error");
      }
    } catch (error) {
      if (mounted.current && generation === operationGeneration.current) {
        setMessage(error instanceof Error ? error.message : "The local title could not be saved.");
        setStatus("error");
      }
    } finally {
      busyRef.current = false;
      finishPendingWrite();
      if (mounted.current && generation === operationGeneration.current) setBusy(false);
    }
  }, [dirty, record, rememberGraphRecord, repository, repositoryError, titleDraft, updateActiveRecord]);

  const exportPackage = useCallback(async () => {
    if (!repository || repositoryError || !record || dirty || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setMessage(null);
    const generation = operationGeneration.current;
    try {
      const latest = await repository.readWorldExportSnapshot(record.snapshot.worldId);
      if (latest.status !== "found") throw new Error(latest.status === "missing" ? "Local World is missing." : latest.message);
      const [{ encodeLocalWorldPackageV1 }, { encodeLocalWorldPackageZipV1 }] = await Promise.all([
        import("../localWorldPackageV1"),
        import("../localWorldPackageZipV1"),
      ]);
      const encoded = await encodeLocalWorldPackageV1(latest.record, latest.data);
      if (encoded.status !== "encoded") throw new Error(encoded.message);
      const archived = await encodeLocalWorldPackageZipV1(encoded.members);
      if (archived.status !== "encoded") throw new Error(archived.message);
      if (!mounted.current || generation !== operationGeneration.current) return;
      downloadBlob(archived.blob, safeFileName(latest.record.snapshot.title));
      setMessage("Package downloaded. It includes the current local World and its stored attachments.");
      setStatus("saved");
    } catch (error) {
      if (mounted.current && generation === operationGeneration.current) {
        setMessage(error instanceof Error ? error.message : "Package export failed validation.");
        setStatus("error");
      }
    } finally {
      busyRef.current = false;
      if (mounted.current && generation === operationGeneration.current) setBusy(false);
    }
  }, [dirty, record, repository, repositoryError]);

  const cancelTitleEdit = useCallback(() => {
    if (busyRef.current || !record) return;
    clearPendingTitleDraft(record.snapshot.worldId);
    setTitleDraft(record.snapshot.title);
    setEditing(false);
    setMessage(null);
    setStatus("saved");
  }, [record]);

  const graphAdapter = useMemo(() => repository ? createLocalWorldGraphAdapter(repository) : null, [repository]);

  const isCurrentGraphOperation = (worldId: LocalWorldId, generation: number) =>
    mounted.current && generation === operationGeneration.current && recordRef.current?.snapshot.worldId === worldId;

  const executeGraphSemantic = useCallback(async (
    submittedRecord: LocalWorldRecord,
    command: () => Promise<CommitSemanticResult>,
  ): Promise<CommitSemanticResult> => {
    const generation = operationGeneration.current;
    const current = recordRef.current;
    if (!mounted.current || busyRef.current || !current || current.snapshot.worldId !== submittedRecord.snapshot.worldId ||
        current.localRevision !== submittedRecord.localRevision) {
      return { status: "error", message: "This World changed before the edit started. Review the latest graph and retry." };
    }
    busyRef.current = true;
    setBusy(true);
    setStatus("saving");
    const finishPendingWrite = beginPendingLocalWrite();
    try {
      return await command();
    } catch (error) {
      return { status: "error", message: error instanceof Error ? error.message : "The graph edit could not be saved." };
    } finally {
      busyRef.current = false;
      finishPendingWrite();
      if (mounted.current && generation === operationGeneration.current) setBusy(false);
    }
  }, []);

  const executeGraphLayout = useCallback(async (
    submittedRecord: LocalWorldRecord,
    command: () => Promise<WriteLayoutResult>,
  ): Promise<WriteLayoutResult> => {
    const generation = operationGeneration.current;
    const current = recordRef.current;
    if (!mounted.current || busyRef.current || !current || current.snapshot.worldId !== submittedRecord.snapshot.worldId ||
        current.layoutRevision !== submittedRecord.layoutRevision) {
      return { status: "error", message: "This World layout changed before the move started. Review the latest canvas and retry." };
    }
    busyRef.current = true;
    setBusy(true);
    setStatus("saving");
    const finishPendingWrite = beginPendingLocalWrite();
    try {
      return await command();
    } catch (error) {
      return { status: "error", message: error instanceof Error ? error.message : "The canvas layout could not be saved." };
    } finally {
      busyRef.current = false;
      finishPendingWrite();
      if (mounted.current && generation === operationGeneration.current) setBusy(false);
    }
  }, []);

  const applyGraphSemanticResult = useCallback((worldId: LocalWorldId, generation: number, result: CommitSemanticResult) => {
    if (!isCurrentGraphOperation(worldId, generation)) return;
    if (result.status === "committed" || result.status === "conflict") {
      const incoming = result.status === "committed" ? result.record : result.committed;
      const current = recordRef.current;
      if (!current || current.snapshot.worldId !== worldId || incoming.localRevision < current.localRevision) return;
      const accepted = incoming.layoutRevision < current.layoutRevision
        ? { ...incoming, layout: current.layout, layoutRevision: current.layoutRevision }
        : incoming;
      updateActiveRecord(accepted);
      rememberGraphRecord(accepted);
      const titleDraft = pendingTitleDrafts.get(worldId);
      if (!titleDraft || titleDraft.value.trim() === accepted.snapshot.title) {
        if (titleDraft) clearPendingTitleDraft(worldId, titleDraft.token);
        setTitleDraft(accepted.snapshot.title);
      }
      setRecords((items) => items.map((item) => {
        if (item.snapshot.worldId !== worldId || item.localRevision > accepted.localRevision) return item;
        return item.layoutRevision > accepted.layoutRevision
          ? { ...accepted, layout: item.layout, layoutRevision: item.layoutRevision }
          : accepted;
      }));
      if (result.status === "committed") {
        setGraphConflict(null);
        setMessage(null);
        setStatus("saved");
      } else {
        setGraphConflict(result.candidate);
        setMessage("Your graph proposal is saved as a local conflict candidate. The canvas now shows the committed version; review it, then submit your still-open edit again if it remains appropriate.");
        setStatus("conflict");
      }
      return;
    }
    setMessage(result.status === "missing" ? "This local World was removed before the graph edit could be saved." : result.message);
    setStatus("error");
  }, [rememberGraphRecord, updateActiveRecord]);

  const applyGraphLayoutResult = useCallback((worldId: LocalWorldId, generation: number, result: WriteLayoutResult) => {
    if (!isCurrentGraphOperation(worldId, generation)) return;
    if (result.status === "written" || result.status === "conflict") {
      const current = recordRef.current;
      if (!current || current.snapshot.worldId !== worldId || result.record.snapshot.worldId !== worldId || result.record.layoutRevision < current.layoutRevision) return;
      const accepted = { ...current, layout: result.record.layout, layoutRevision: result.record.layoutRevision };
      updateActiveRecord(accepted);
      rememberGraphRecord(accepted);
      setRecords((items) => items.map((item) => item.snapshot.worldId === worldId && item.layoutRevision <= accepted.layoutRevision
        ? { ...item, layout: accepted.layout, layoutRevision: accepted.layoutRevision }
        : item));
      setMessage(result.status === "conflict" ? "Another tab changed this graph layout. The newest saved positions are shown; move the nodes again if you still want to change them." : null);
      setStatus(result.status === "written" ? "saved" : "conflict");
      return;
    }
    setMessage(result.status === "missing" ? "This local World was removed before its layout could be saved." : result.message);
    setStatus("error");
  }, [rememberGraphRecord, updateActiveRecord]);

  const seedStarterGraph = useCallback(async () => {
    const current = recordRef.current;
    if (!repository || !current || current.snapshot.objects.length || current.snapshot.relationships.length || busyRef.current || pendingLocalWrites.size > 0 || firstObjectName.trim()) return;
    if (!prepareGraphSessionSlot(current.snapshot.worldId, current.snapshot.title)) return;
    const generation = operationGeneration.current;
    const people = [
      { id: repository.allocateObjectId(current.snapshot.worldId), name: "Mara Venn", kind: "person", properties: {} },
      { id: repository.allocateObjectId(current.snapshot.worldId), name: "Tomas Reed", kind: "person", properties: {} },
    ];
    const location = { id: repository.allocateObjectId(current.snapshot.worldId), name: "Amber Quay", kind: "location", properties: {} };
    const event = { id: repository.allocateObjectId(current.snapshot.worldId), name: "Lantern Festival", kind: "event", properties: {} };
    const objects = [...people, location, event];
    const relationships = [
      { fromObjectId: people[0].id, toObjectId: people[1].id, kind: "knows" },
      { fromObjectId: people[0].id, toObjectId: event.id, kind: "attends" },
      { fromObjectId: people[1].id, toObjectId: event.id, kind: "attends" },
      { fromObjectId: event.id, toObjectId: location.id, kind: "held at" },
    ].map((relationship) => ({ ...relationship, id: repository.allocateRelationshipId(current.snapshot.worldId), properties: {} }));
    const result = await executeGraphSemantic(current, () => repository.commitSemanticEdit({
      worldId: current.snapshot.worldId,
      expectedLocalRevision: current.localRevision,
      nextSnapshot: { ...current.snapshot, objects, relationships },
      edit: { classification: "buddy-local-only", description: "Started a small example graph" },
    }));
    applyGraphSemanticResult(current.snapshot.worldId, generation, result);
  }, [applyGraphSemanticResult, executeGraphSemantic, firstObjectName, prepareGraphSessionSlot, repository]);

  const createFirstObject = useCallback(async (event: FormEvent) => {
    event.preventDefault();
    const current = recordRef.current;
    if (!repository || !graphAdapter || !current || current.snapshot.objects.length || current.snapshot.relationships.length ||
        !firstObjectName.trim() || busyRef.current || pendingLocalWrites.size > 0 || !prepareGraphSessionSlot(current.snapshot.worldId, current.snapshot.title)) return;
    const generation = operationGeneration.current;
    const worldId = current.snapshot.worldId;
    const submittedDraft = readFirstObjectDraft(worldId);
    const result = await executeGraphSemantic(current, () => graphAdapter.createObject(current, { name: firstObjectName.trim(), kind: firstObjectKind }));
    applyGraphSemanticResult(current.snapshot.worldId, generation, result);
    if (result.status === "committed") {
      writeFirstObjectDraft(worldId, null, submittedDraft.version + 1, submittedDraft.version);
      if (mounted.current && generation === operationGeneration.current && recordRef.current?.snapshot.worldId === worldId) {
        setFirstObjectName("");
        setFirstObjectKind("person");
      }
    }
  }, [applyGraphSemanticResult, executeGraphSemantic, firstObjectKind, firstObjectName, graphAdapter, prepareGraphSessionSlot, repository]);

  const publication = useMemo(() => makePublication({
    localWorldId: record?.snapshot.worldId ?? null,
    title: record?.snapshot.title ?? null,
    status: displayStatus,
    editing,
    titleDirty: dirty,
    canExport: !!record && !repositoryError && !dirty && !busy && notesStatus !== "dirty" && notesStatus !== "saving" && notesStatus !== "conflict" && notesStatus !== "error" && status !== "loading" && status !== "saving" && status !== "conflict",
    onEditTitle: () => { if (record && !busy) { setTitleDraft(record.snapshot.title); setEditing(true); } },
    onSaveTitle: () => { void saveTitle(); },
    onExport: () => { void exportPackage(); },
  }), [busy, dirty, displayStatus, editing, exportPackage, notesStatus, record, repositoryError, saveTitle]);
  usePublishSurfaceInteraction(publication);

  return (
    <main className="local-world-surface" aria-label="Buddy Surface">
      <header className="local-world-surface__header">
        <p className="local-world-surface__eyebrow">A WORLD, YOURS TO SHAPE</p>
        <h1>Buddy Surface</h1>
        <p className="local-world-surface__intro">Start with a name. Your work stays in this browser until you choose to export it.</p>
      </header>

      <div className="local-world-surface__grid">
        <section className="local-world-surface__workspace" aria-labelledby="local-world-heading">
          {status === "loading" && !repository ? <p role="status">Opening local storage…</p> : null}
          {repositoryError ? <div className="local-world-surface__notice local-world-surface__notice--error" role="alert"><p>{repositoryError}</p><button type="button" onClick={() => void openStore()}>Retry storage</button></div> : null}
          {repository ? <>
            <div className="local-world-surface__world-picker">
              <h2 id="local-world-heading">Your local Worlds</h2>
              {records.length === 0
                ? <p className="local-world-surface__muted">No local Worlds yet. Create one when you’re ready.</p>
                : <ul aria-label="Resume a local World">
                  {records.map((item) => <li key={item.snapshot.worldId}>
                    <button type="button" className={record?.snapshot.worldId === item.snapshot.worldId ? "is-selected" : ""} onClick={() => void selectWorld(item.snapshot.worldId)} disabled={busy}>
                      <span>{item.snapshot.title}</span><small>Local revision {item.localRevision}</small>
                    </button>
                  </li>)}
                </ul>}
            </div>
            <form className="local-world-surface__create" onSubmit={(event) => void createWorld(event)}>
              <label htmlFor="local-world-new-title">Create a World</label>
              <div className="local-world-surface__create-row">
                <input id="local-world-new-title" value={newTitle} onChange={(event) => setNewTitle(event.target.value)} maxLength={160} placeholder="A name to begin with" disabled={busy} />
                <button type="submit" disabled={busy || !!repositoryError || !newTitle.trim()}>Create World</button>
              </div>
            </form>
          </> : null}

          {record ? <section className="local-world-surface__canvas" aria-label="Local World canvas">
            <div className="local-world-surface__canvas-topline"><span>LOCAL WORLD</span><span>Revision {record.localRevision}</span></div>
            <div className="local-world-surface__title-row">
              {editing ? <form onSubmit={(event) => { event.preventDefault(); void saveTitle(); }}>
                <label htmlFor="local-world-title">World title</label>
                <input id="local-world-title" autoFocus value={titleDraft} maxLength={160} disabled={busy} onChange={(event) => { const nextDraft = event.target.value; setTitleDraft(nextDraft); if (record) setPendingTitleDraft(record.snapshot.worldId, nextDraft, record.snapshot.title); setMessage(null); if (status === "error" || status === "conflict") setStatus("dirty"); }} onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); cancelTitleEdit(); } }} />
                <div className="local-world-surface__title-actions">
                  <button type="submit" disabled={busy || !dirty || !titleDraft.trim()}>{busy && status === "saving" ? "Saving…" : "Save title"}</button>
                  <button type="button" className="local-world-surface__quiet" disabled={busy} onClick={cancelTitleEdit}>Cancel</button>
                </div>
              </form> : <>
                <h2>{record.snapshot.title}</h2>
                <button type="button" className="local-world-surface__pencil" aria-label="Edit World title" title="Edit World title" disabled={busy} onClick={() => { setTitleDraft(record.snapshot.title); setEditing(true); setStatus("saved"); }}><span aria-hidden="true">✎</span></button>
              </>}
            </div>
            {record.snapshot.objects.length === 0 && record.snapshot.relationships.length === 0 ? (
              <div className="local-world-surface__empty-canvas" aria-label="Empty World canvas">
                <span className="local-world-surface__spark" aria-hidden="true">✦</span>
                <p>Your World begins here.</p>
                <small>Add connected people, a place and an event in one step. You can then rename, add, connect and move objects.</small>
                <div className="local-world-surface__graph-start-actions">
                  <button type="button" disabled={busy || pendingLocalWrites.size > 0 || !!repositoryError || !!firstObjectName.trim()} onClick={() => void seedStarterGraph()}>Start with an example graph</button>
                </div>
                {graphAdapter ? <form className="local-world-surface__first-object" onSubmit={(event) => void createFirstObject(event)}>
                  <label htmlFor="local-world-first-object-name">Or add your first object</label>
                  <input id="local-world-first-object-name" value={firstObjectName} onChange={(event) => { const name = event.target.value; setFirstObjectName(name); if (record) saveFirstObjectDraft(record.snapshot.worldId, name, firstObjectKind); }} maxLength={160} placeholder="Object name" disabled={busy || pendingLocalWrites.size > 0} />
                  <label htmlFor="local-world-first-object-kind">Type</label>
                  <select id="local-world-first-object-kind" value={firstObjectKind} onChange={(event) => { const kind = event.target.value; setFirstObjectKind(kind); if (record) saveFirstObjectDraft(record.snapshot.worldId, firstObjectName, kind); }} disabled={busy || pendingLocalWrites.size > 0}>
                    <option value="person">Person</option><option value="location">Location</option><option value="event">Event</option><option value="faction">Faction</option>
                  </select>
                  <button type="submit" disabled={busy || pendingLocalWrites.size > 0 || !!repositoryError || !firstObjectName.trim()}>Add first object</button>
                </form> : null}
              </div>
            ) : null}
            {graphConflict && graphConflict.worldId === record.snapshot.worldId ? (
              <section className="local-world-surface__graph-conflict" aria-label="Saved graph conflict candidate">
                <h3>Graph edit needs review</h3>
                <p>{graphConflict.edit.description} was saved as a local conflict candidate based on revision {graphConflict.baseLocalRevision}; the current World is at revision {graphConflict.currentLocalRevision}.</p>
                <p>The graph now shows the committed version. The canvas keeps the proposal open so you can review and submit it again against the current World.</p>
                <button type="button" className="local-world-surface__quiet" onClick={() => setGraphConflict(null)}>Dismiss this notice</button>
              </section>
            ) : null}
            {repository ? <LocalWorldNotesEditor
              repository={repository}
              record={record}
              disabled={busy}
              onRecordChange={onNotesRecordChange}
              onBusyChange={onNotesBusyChange}
              onStatusChange={setNotesStatus}
              onPendingChange={syncBeforeUnloadProtection}
              beginPendingWrite={beginPendingLocalWrite}
              registerSaveRequest={registerNotesSaveRequest}
            /> : null}
          </section> : null}

          {graphAdapter ? graphSessions.map((sessionRecord) => {
            const active = record?.snapshot.worldId === sessionRecord.snapshot.worldId;
            const canvasRecord = active ? record! : sessionRecord;
            const generation = operationGeneration.current;
            return <div className="local-world-surface__graph-session" key={sessionRecord.snapshot.worldId} hidden={!active} aria-hidden={!active}>
              <Suspense fallback={<p className="local-world-surface__graph-loading" role="status">Opening the local graph editor…</p>}>
                <WorldGraphCanvas
                  key={sessionRecord.snapshot.worldId}
                  record={canvasRecord}
                  editorDraftState={readGraphEditorDraft(sessionRecord.snapshot.worldId)}
                  onEditorDraftChange={(draft, version, expectedVersion) => writeGraphEditorDraft(sessionRecord.snapshot.worldId, draft, version, expectedVersion)}
                  onEditorDraftCommit={(field, submittedToken) => clearGraphEditorDraftSubmission(sessionRecord.snapshot.worldId, field, submittedToken)}
                  onRenameObject={(submitted, objectId, name) => executeGraphSemantic(submitted, () => graphAdapter.renameObject(submitted, objectId, name))}
                  onCreateObject={(submitted, input) => executeGraphSemantic(submitted, () => graphAdapter.createObject(submitted, input))}
                  onCreateRelationship={(submitted, input) => executeGraphSemantic(submitted, () => graphAdapter.createRelationship(submitted, input))}
                  onMoveObjects={(submitted, positions) => executeGraphLayout(submitted, () => graphAdapter.moveObjects(submitted, positions))}
                  onSemanticResult={(result) => applyGraphSemanticResult(sessionRecord.snapshot.worldId, generation, result)}
                  onLayoutResult={(result) => applyGraphLayoutResult(sessionRecord.snapshot.worldId, generation, result)}
                />
              </Suspense>
            </div>;
          }) : null}

          <details className="local-world-surface__save-menu">
            <summary>Save menu</summary>
            <p>Local Worlds are saved in this browser. Export creates a portable package you control.</p>
            <div>
              <button type="button" onClick={() => { if (dirty) void saveTitle(); else saveNotesRef.current?.(); }} disabled={(!dirty && notesStatus !== "dirty" && notesStatus !== "error") || busy || notesStatus === "conflict"}>{busy && (status === "saving" || notesStatus === "saving") ? "Saving…" : "Save in this browser"}</button>
              <button type="button" onClick={() => void exportPackage()} disabled={!record || !!repositoryError || dirty || busy || notesStatus === "loading" || notesStatus === "dirty" || notesStatus === "saving" || notesStatus === "conflict" || notesStatus === "error" || status === "loading" || status === "saving" || status === "conflict"}>Download World package</button>
            </div>
          </details>
          <p className={`local-world-surface__save-status local-world-surface__save-status--${status}`} role="status" aria-live="polite">
            {notesStatus === "saving" || status === "saving" ? "Saving to this browser…" : notesStatus === "conflict" || status === "conflict" ? "Conflict needs your choice" : notesStatus === "error" || status === "error" ? "Could not complete this local action" : dirty || status === "dirty" ? "Unsaved title change" : notesStatus === "dirty" ? "Unsaved notes" : status === "loading" ? "Loading local World…" : record ? "Saved in this browser" : "Ready to create a local World"}
          </p>
          {message ? <div className={`local-world-surface__notice ${status === "error" ? "local-world-surface__notice--error" : ""}`} role={status === "error" ? "alert" : "status"}>
            <p>{message}</p>
            {status === "conflict" && record && titleDraft.trim() && titleDraft.trim() !== record.snapshot.title
              ? <button type="button" disabled={busy} onClick={() => void saveTitle()}>Save my title on the current version</button>
              : null}
          </div> : null}
        </section>
        {children ? <aside className="local-world-surface__assistant" aria-label="Assistant">{children}</aside> : null}
      </div>
      <footer className="local-world-surface__footer">Browser storage is not a backup. Export a package to keep a portable copy.</footer>
    </main>
  );
}
