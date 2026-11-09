import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import { openIndexedDbLocalWorldRepository, LOCAL_WORLD_DATABASE_NAME } from "../indexedDbLocalWorldRepository";
import type { LocalWorldId, LocalWorldPackageRepository, LocalWorldRecord } from "../localWorldRepository";
import "./localWorldSurface.css";

// Keep unsaved title candidates while App routes/components remount in this tab.
// This is deliberately volatile presentation state, not a second durable ledger.
interface PendingTitleDraft {
  readonly value: string;
  readonly token: symbol;
}

const pendingTitleDrafts = new Map<LocalWorldId, PendingTitleDraft>();
const pendingLocalWrites = new Set<symbol>();
let beforeUnloadProtectionInstalled = false;

function warnBeforeLeavingWithLocalWork(event: BeforeUnloadEvent): void {
  event.preventDefault();
  event.returnValue = "";
}

function syncBeforeUnloadProtection(): void {
  if (typeof window === "undefined") return;
  const shouldProtect = pendingTitleDrafts.size > 0 || pendingLocalWrites.size > 0;
  if (shouldProtect && !beforeUnloadProtectionInstalled) {
    window.addEventListener("beforeunload", warnBeforeLeavingWithLocalWork);
    beforeUnloadProtectionInstalled = true;
  } else if (!shouldProtect && beforeUnloadProtectionInstalled) {
    window.removeEventListener("beforeunload", warnBeforeLeavingWithLocalWork);
    beforeUnloadProtectionInstalled = false;
  }
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
  return () => {
    pendingLocalWrites.delete(token);
    syncBeforeUnloadProtection();
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
  const [newTitle, setNewTitle] = useState("");
  const [titleDraft, setTitleDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<SaveStatus>("loading");
  const [message, setMessage] = useState<string | null>(null);
  const mounted = useRef(false);
  const operationGeneration = useRef(0);
  const busyRef = useRef(false);
  const closeRepositoryRef = useRef<(() => void) | null>(null);
  const dirty = record !== null && titleDraft.trim() !== record.snapshot.title;

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
    const generation = ++operationGeneration.current;
    setStatus("loading");
    setMessage(null);
    setRecord(null);
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
      const hasPendingChanges = pendingDraft !== undefined && pendingDraft.value.trim() !== result.record.snapshot.title;
      if (pendingDraft !== undefined && !hasPendingChanges) clearPendingTitleDraft(localWorldId);
      setRecord(result.record);
      setTitleDraft(hasPendingChanges ? pendingDraft.value : result.record.snapshot.title);
      setEditing(hasPendingChanges);
      setStatus(hasPendingChanges ? "dirty" : "saved");
    } catch (error) {
      if (!mounted.current || generation !== operationGeneration.current) return;
      setMessage(error instanceof Error ? error.message : "The local World could not be opened.");
      setStatus("error");
    }
  }, [refreshList, repository]);

  const createWorld = useCallback(async (event: FormEvent) => {
    event.preventDefault();
    if (!repository || repositoryError || busyRef.current || !newTitle.trim()) return;
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
      setRecord(result.record);
      setTitleDraft(result.record.snapshot.title);
      setNewTitle("");
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
  }, [newTitle, refreshList, repository, repositoryError]);

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
        setRecord(result.record);
        setRecords((current) => current.map((item) => item.snapshot.worldId === result.record.snapshot.worldId ? result.record : item)
          .sort((left, right) => left.snapshot.title.localeCompare(right.snapshot.title) || left.snapshot.worldId.localeCompare(right.snapshot.worldId)));
        setTitleDraft(result.record.snapshot.title);
        setEditing(false);
        setStatus("saved");
        return;
      }
      if (!mounted.current || generation !== operationGeneration.current) return;
      if (result.status === "conflict") {
        setRecord(result.committed);
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
  }, [dirty, record, repository, repositoryError, titleDraft]);

  const exportPackage = useCallback(async () => {
    if (!repository || repositoryError || !record || dirty || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setMessage(null);
    const generation = operationGeneration.current;
    try {
      const latest = await repository.readWorld(record.snapshot.worldId);
      if (latest.status !== "found") throw new Error(latest.status === "missing" ? "Local World is missing." : latest.message);
      const supplemental = await repository.readPackageData(record.snapshot.worldId);
      if (supplemental.status === "error") throw new Error(supplemental.message);
      if (supplemental.status === "missing") throw new Error("Local World disappeared before export.");
      const [{ encodeLocalWorldPackageV1 }, { encodeLocalWorldPackageZipV1 }] = await Promise.all([
        import("../localWorldPackageV1"),
        import("../localWorldPackageZipV1"),
      ]);
      const encoded = await encodeLocalWorldPackageV1(latest.record, supplemental.status === "found" ? supplemental.data : undefined);
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

  const publication = useMemo(() => makePublication({
    localWorldId: record?.snapshot.worldId ?? null,
    title: record?.snapshot.title ?? null,
    status,
    editing,
    titleDirty: dirty,
    canExport: !!record && !repositoryError && !dirty && !busy && status !== "loading" && status !== "saving" && status !== "conflict",
    onEditTitle: () => { if (record && !busy) { setTitleDraft(record.snapshot.title); setEditing(true); } },
    onSaveTitle: () => { void saveTitle(); },
    onExport: () => { void exportPackage(); },
  }), [busy, dirty, editing, exportPackage, record, repositoryError, saveTitle, status]);
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
            <div className="local-world-surface__empty-canvas" aria-label="Empty World canvas">
              <span className="local-world-surface__spark" aria-hidden="true">✦</span>
              <p>Your World begins here.</p>
              <small>People, places and moments can come later.</small>
            </div>
          </section> : null}

          <details className="local-world-surface__save-menu">
            <summary>Save menu</summary>
            <p>Local Worlds are saved in this browser. Export creates a portable package you control.</p>
            <div>
              <button type="button" onClick={() => { if (dirty) void saveTitle(); }} disabled={!dirty || busy}>{busy && status === "saving" ? "Saving…" : "Save in this browser"}</button>
              <button type="button" onClick={() => void exportPackage()} disabled={!record || !!repositoryError || dirty || busy || status === "loading" || status === "saving" || status === "conflict"}>Download World package</button>
            </div>
          </details>
          <p className={`local-world-surface__save-status local-world-surface__save-status--${status}`} role="status" aria-live="polite">
            {status === "loading" ? "Loading local World…" : status === "saving" ? "Saving to this browser…" : status === "conflict" ? "Conflict needs your choice" : status === "error" ? "Could not complete this local action" : status === "dirty" || dirty ? "Unsaved title change" : record ? "Saved in this browser" : "Ready to create a local World"}
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
