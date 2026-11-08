import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { splitLeadingYamlFrontmatter } from "../../tiptap/markdown/stripLeadingYamlFrontmatter";
import {
  getPendingWorldNotesDraft,
  setPendingWorldNotesDraft,
  clearPendingWorldNotesDraft,
  readWorldNotesPackageData,
} from "../localWorldDocumentAuthoring";
import type {
  LocalConflictId,
  LocalWorldConflictCandidate,
  LocalWorldPackageRepository,
  LocalWorldRecord,
} from "../localWorldRepository";

type NotesStatus = "loading" | "ready" | "dirty" | "saving" | "saved" | "conflict" | "error";

const MarkdownEditorCore = lazy(() => import("../../tiptap/MarkdownEditorCore").then((module) => ({ default: module.MarkdownEditorCore })));

export interface LocalWorldNotesEditorProps {
  readonly repository: LocalWorldPackageRepository;
  readonly record: LocalWorldRecord;
  readonly disabled: boolean;
  readonly onRecordChange: (record: LocalWorldRecord) => void;
  readonly onBusyChange: (busy: boolean) => void;
  readonly onStatusChange: (status: NotesStatus) => void;
  readonly onPendingChange: () => void;
  readonly beginPendingWrite: () => () => void;
  readonly registerSaveRequest: (save: (() => void) | null) => void;
}

function notesFromCandidate(candidate: LocalWorldConflictCandidate): string | null {
  if (!candidate.proposedPackageData) return null;
  const result = readWorldNotesPackageData(candidate.proposedPackageData, candidate.worldId);
  return result.status === "found" && result.documentExists ? result.markdown : null;
}

export function LocalWorldNotesEditor({
  repository,
  record,
  disabled,
  onRecordChange,
  onBusyChange,
  onStatusChange,
  onPendingChange,
  beginPendingWrite,
  registerSaveRequest,
}: LocalWorldNotesEditorProps) {
  const worldId = record.snapshot.worldId;
  const recordRef = useRef(record);
  recordRef.current = record;
  const [loaded, setLoaded] = useState(false);
  const [documentExists, setDocumentExists] = useState(false);
  const [markdown, setMarkdown] = useState("");
  const [status, setStatus] = useState<NotesStatus>("loading");
  const [message, setMessage] = useState<string | null>(null);
  const [conflictCandidates, setConflictCandidates] = useState<readonly LocalWorldConflictCandidate[]>([]);
  const [selectedConflictId, setSelectedConflictId] = useState<LocalConflictId | null>(null);
  const [editorKey, setEditorKey] = useState(worldId + ":loading");
  const [editorRevision, setEditorRevision] = useState(0);
  const mounted = useRef(false);
  const generation = useRef(0);
  const busy = useRef(false);
  const saveTimer = useRef<number | null>(null);
  const latestDraft = useRef("");
  const savedRef = useRef("");
  const notesStatus = useRef<NotesStatus>("loading");
  const selectedConflict = useRef<LocalConflictId | null>(null);
  const frontmatter = useRef("");

  const updateStatus = useCallback((next: NotesStatus) => {
    notesStatus.current = next;
    setStatus(next);
    onStatusChange(next);
  }, [onStatusChange]);

  const loadNotes = useCallback(async () => {
    const current = ++generation.current;
    updateStatus("loading");
    setMessage(null);
    try {
      const result = await repository.readWorldNotes(worldId);
      if (!mounted.current || current !== generation.current) return;
      if (result.status !== "found") {
        setMessage(result.status === "missing" ? "This local World is no longer available." : result.message);
        updateStatus("error");
        return;
      }
      const saved = result.state.markdown;
      const firstConflict = result.state.conflictCandidates[0] ?? null;
      const pending = getPendingWorldNotesDraft(worldId);
      const hasDraft = firstConflict === null && pending !== undefined && pending.value !== saved;
      const activeSource = hasDraft ? pending!.value : saved;
      frontmatter.current = splitLeadingYamlFrontmatter(activeSource).frontmatter;
      setDocumentExists(result.state.documentExists);
      savedRef.current = saved;
      latestDraft.current = activeSource;
      setMarkdown(latestDraft.current);
      setConflictCandidates(result.state.conflictCandidates);
      // A persisted conflict must be chosen through Recover/Keep saved version;
      // never bind its action to the currently committed markdown by default.
      const selected = null;
      selectedConflict.current = selected;
      setSelectedConflictId(selected);
      setEditorKey(worldId + ":load:" + String(current));
      setEditorRevision((value) => value + 1);
      setLoaded(true);
      updateStatus(firstConflict ? "conflict" : hasDraft ? "dirty" : "saved");
      if (firstConflict) setMessage("A previous notes edit is preserved as a local conflict candidate. Choose Recover or Keep saved version.");
      else if (hasDraft) setMessage("An unsaved notes draft was restored in this tab. Save it to keep the current revision.");
    } catch (error) {
      if (!mounted.current || current !== generation.current) return;
      setMessage(error instanceof Error ? error.message : "World notes could not be read.");
      updateStatus("error");
    }
  }, [onStatusChange, repository, updateStatus, worldId]);

  useEffect(() => {
    mounted.current = true;
    void loadNotes();
    return () => {
      mounted.current = false;
      generation.current += 1;
      if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
      registerSaveRequest(null);
      if (busy.current) onBusyChange(false);
    };
  }, [loadNotes, onBusyChange, registerSaveRequest]);

  const saveNotes = useCallback(async (value: string, conflictId: LocalConflictId | null = selectedConflict.current) => {
    if (busy.current || disabled) return;
    const capturedValue = value;
    const capturedToken = getPendingWorldNotesDraft(worldId)?.token;
    const capturedGeneration = generation.current;
    const expectedLocalRevision = recordRef.current.localRevision;
    const releaseUnload = beginPendingWrite();
    busy.current = true;
    onBusyChange(true);
    updateStatus("saving");
    setMessage(null);
    try {
      const result = await repository.commitWorldNotes({
        worldId,
        expectedLocalRevision,
        markdown: capturedValue,
      });
      if (result.status === "committed") {
        savedRef.current = capturedValue;
        setDocumentExists(true);
        setConflictCandidates((current) => current.filter((candidate) => candidate.id !== conflictId));
        recordRef.current = result.record;
        if (mounted.current && capturedGeneration === generation.current) onRecordChange(result.record);
        if (capturedToken !== undefined) clearPendingWorldNotesDraft(worldId, capturedToken);
        onPendingChange();
        if (conflictId) {
          const discarded = await repository.discardWorldNotesConflict(worldId, conflictId);
          if (discarded !== "discarded") setMessage("The note was saved, but an older conflict candidate remains available for explicit cleanup.");
        }
        if (!mounted.current || capturedGeneration !== generation.current) return;
        const pending = getPendingWorldNotesDraft(worldId);
        if (pending && pending.value !== capturedValue) {
          latestDraft.current = pending.value;
          setMarkdown(pending.value);
          updateStatus("dirty");
          setMessage("A newer note draft remains unsaved.");
        } else {
          latestDraft.current = capturedValue;
          setMarkdown(capturedValue);
          selectedConflict.current = null;
          setSelectedConflictId(null);
          updateStatus("saved");
        }
        return;
      }
      if (result.status === "conflict") {
        recordRef.current = result.committed;
        if (mounted.current && capturedGeneration === generation.current) onRecordChange(result.committed);
        const refreshed = await repository.readWorldNotes(worldId);
        if (!mounted.current || capturedGeneration !== generation.current) return;
        if (refreshed.status === "found") {
          savedRef.current = refreshed.state.markdown;
          setConflictCandidates(refreshed.state.conflictCandidates);
        }
        setConflictCandidates((current) => current.some((candidate) => candidate.id === result.candidate.id)
          ? current
          : [...current, result.candidate]);
        selectedConflict.current = result.candidate.id;
        setSelectedConflictId(result.candidate.id);
        setMarkdown(capturedValue);
        latestDraft.current = capturedValue;
        updateStatus("conflict");
        setMessage("Another tab saved a newer revision. Your complete note is stored as a conflict candidate; choose whether to reapply it or keep the saved version.");
        return;
      }
      if (!mounted.current || capturedGeneration !== generation.current) return;
      setMessage(result.status === "missing" ? "This local World is no longer available." : result.message);
      updateStatus("error");
    } catch (error) {
      if (mounted.current && capturedGeneration === generation.current) {
        setMessage(error instanceof Error ? error.message : "The local notes could not be saved.");
        updateStatus("error");
      }
    } finally {
      releaseUnload();
      busy.current = false;
      onBusyChange(false);
    }
  }, [beginPendingWrite, disabled, onBusyChange, onPendingChange, onRecordChange, repository, updateStatus, worldId]);

  const saveNotesRef = useRef(saveNotes);
  saveNotesRef.current = saveNotes;
  const requestSave = useCallback(() => {
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
    void saveNotesRef.current(latestDraft.current, selectedConflict.current);
  }, []);

  useEffect(() => {
    registerSaveRequest(requestSave);
    return () => registerSaveRequest(null);
  }, [registerSaveRequest, requestSave]);

  const startWriting = useCallback(() => {
    latestDraft.current = "";
    setMarkdown("");
    void saveNotes("", null);
  }, [saveNotes]);

  const onUpdate = useCallback((_json: JSONContent, editor: Editor, meta: { programmatic: boolean }) => {
    if (meta.programmatic) return;
    try {
      const body = tiptapJsonToSemanticMarkdown(editor.getJSON());
      if (markdownToTiptapDoc(body).diagnostics.some((diagnostic) => diagnostic.level === "warning")) {
        updateStatus("error");
        setMessage("This edit contains Markdown that the local notes editor cannot preserve safely. The committed document was left unchanged; reload to restore it.");
        return;
      }
      const next = frontmatter.current + body;
      latestDraft.current = next;
      setMarkdown(next);
      if (!selectedConflict.current && next === savedRef.current) {
        if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
        saveTimer.current = null;
        clearPendingWorldNotesDraft(worldId);
        onPendingChange();
        updateStatus("saved");
        setMessage(null);
        return;
      }
      setPendingWorldNotesDraft(worldId, next, savedRef.current);
      onPendingChange();
      if (selectedConflict.current) {
        updateStatus("conflict");
        setMessage("This is a recovered conflict draft. Use the explicit reapply action to save it.");
        return;
      }
      updateStatus("dirty");
      setMessage(null);
      if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(() => {
        saveTimer.current = null;
        void saveNotesRef.current(latestDraft.current, null);
      }, 700);
    } catch {
      updateStatus("error");
      setMessage("This editor change cannot be represented safely as Markdown and was not saved.");
    }
  }, [onPendingChange, updateStatus, worldId]);

  const recoverConflict = useCallback((candidate: LocalWorldConflictCandidate) => {
    const body = notesFromCandidate(candidate);
    if (body === null) {
      setMessage("The selected conflict candidate is invalid and was left unchanged.");
      updateStatus("error");
      return;
    }
    frontmatter.current = splitLeadingYamlFrontmatter(body).frontmatter;
    latestDraft.current = body;
    setMarkdown(body);
    setPendingWorldNotesDraft(worldId, body, savedRef.current);
    onPendingChange();
    selectedConflict.current = candidate.id;
    setSelectedConflictId(candidate.id);
    setEditorKey(worldId + ":conflict:" + candidate.id + ":" + String(editorRevision + 1));
    setEditorRevision((value) => value + 1);
    updateStatus("conflict");
    setMessage("This recovered draft is a read-only preview. Reapply it first to continue editing from that revision, or keep the saved version.");
  }, [editorRevision, onPendingChange, updateStatus, worldId]);

  const keepSavedVersion = useCallback(async (candidate: LocalWorldConflictCandidate) => {
    if (busy.current || disabled) return;
    const capturedDraftToken = getPendingWorldNotesDraft(worldId)?.token;
    busy.current = true;
    onBusyChange(true);
    try {
      const result = await repository.discardWorldNotesConflict(worldId, candidate.id);
      if (result !== "discarded") {
        setMessage("The conflict candidate could not be discarded and remains stored.");
        updateStatus("error");
        return;
      }
      setConflictCandidates((current) => current.filter((item) => item.id !== candidate.id));
      if (capturedDraftToken !== undefined) clearPendingWorldNotesDraft(worldId, capturedDraftToken);
      onPendingChange();
      selectedConflict.current = null;
      setSelectedConflictId(null);
      latestDraft.current = savedRef.current;
      setMarkdown(savedRef.current);
      frontmatter.current = splitLeadingYamlFrontmatter(savedRef.current).frontmatter;
      setEditorKey(worldId + ":saved:" + String(editorRevision + 1));
      setEditorRevision((value) => value + 1);
      setMessage("Kept the current saved note and discarded the selected conflict candidate.");
      updateStatus("saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The conflict candidate could not be discarded.");
      updateStatus("error");
    } finally {
      busy.current = false;
      onBusyChange(false);
    }
  }, [disabled, editorRevision, onBusyChange, onPendingChange, repository, updateStatus, worldId]);

  const markdownParts = useMemo(() => splitLeadingYamlFrontmatter(markdown), [markdown]);
  const parsedMarkdown = useMemo(() => markdownToTiptapDoc(markdownParts.markdown), [markdownParts.markdown]);
  const unsupportedSource = parsedMarkdown.diagnostics.some((diagnostic) => diagnostic.level === "warning");
  const content = parsedMarkdown.doc;
  const selectedCandidate = conflictCandidates.find((candidate) => candidate.id === selectedConflictId) ?? null;
  const showEditor = loaded && documentExists;

  return (
    <section className="local-world-notes" aria-labelledby="local-world-notes-heading">
      <div className="local-world-notes__heading">
        <div>
          <h3 id="local-world-notes-heading">World notes</h3>
          <p>One local Markdown document, included in your exported World package.</p>
        </div>
        {showEditor ? <span className={"local-world-notes__status local-world-notes__status--" + status} role="status" aria-live="polite">
          {status === "loading" ? "Loading notes…" : status === "saving" ? "Saving…" : status === "dirty" ? "Unsaved notes" : status === "conflict" ? "Conflict draft retained" : status === "error" ? "Notes need attention" : "Saved in this browser"}
        </span> : null}
      </div>
      {!loaded ? <p role="status">Loading World notes…</p> : null}
      {loaded && !documentExists ? <div className="local-world-notes__empty">
        <p>No notes document exists yet. Starting one creates a real local document.</p>
        <button type="button" onClick={startWriting} disabled={disabled}>Start writing</button>
      </div> : null}
      {showEditor ? <div className="local-world-notes__editor">
        {unsupportedSource ? <p className="local-world-notes__message">This imported Markdown includes features the editor cannot preserve yet. The original stays intact and read-only; it remains available in package export.</p> : null}
        <Suspense fallback={<p role="status">Opening the Markdown editor…</p>}>
          <MarkdownEditorCore
            content={content}
            editable={!disabled && status !== "loading" && status !== "conflict" && selectedConflictId === null && !unsupportedSource}
            documentKey={editorKey}
            onUpdate={onUpdate}
            dataTestId="local-world-notes-editor"
          />
        </Suspense>
      </div> : null}
      {conflictCandidates.length > 0 ? <div className="local-world-notes__conflicts" aria-label="Recovered World notes drafts">
        <p>{conflictCandidates.length} saved conflict {conflictCandidates.length === 1 ? "draft" : "drafts"} need an explicit choice.</p>
        <ul>
          {conflictCandidates.map((candidate, index) => <li key={candidate.id}>
            <span>Draft {index + 1}, based on revision {candidate.baseLocalRevision}; current revision {candidate.currentLocalRevision}</span>
            <div>
              <button type="button" disabled={disabled} onClick={() => recoverConflict(candidate)}>Recover draft {index + 1}</button>
              {selectedConflictId === candidate.id ? <button type="button" className="local-world-notes__quiet" disabled={disabled} onClick={() => void keepSavedVersion(candidate)}>Keep saved version</button> : null}
            </div>
          </li>)}
        </ul>
        {selectedCandidate ? <button type="button" disabled={disabled || status === "saving"} onClick={() => void saveNotes(markdown, selectedCandidate.id)}>
          Reapply recovered draft on current revision
        </button> : null}
      </div> : null}
      {showEditor && status !== "saved" && status !== "loading" ? <button type="button" disabled={disabled || status === "saving" || (status === "conflict" && !selectedConflictId)} onClick={requestSave}>
        {status === "saving" ? "Saving notes…" : status === "conflict" ? "Reapply selected draft" : "Save notes in this browser"}
      </button> : null}
      {message ? <p className={"local-world-notes__message local-world-notes__message--" + status} role={status === "error" ? "alert" : "status"}>{message}</p> : null}
    </section>
  );
}
