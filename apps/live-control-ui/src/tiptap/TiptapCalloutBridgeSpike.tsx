import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { AppChromeTools } from "../chrome/AppChrome";
import { commitTiptapMarkdownWrite, prepareTiptapMarkdownWrite } from "../api/liveApi";
import type {
  TiptapMarkdownWriteCommitResponse,
  TiptapMarkdownWritePrepareResponse,
} from "../api/types";
import { CalloutNode } from "./extensions/CalloutNode";
import { RunbookReferenceNode } from "./extensions/RunbookReferenceNode";
import {
  CALLOUT_KINDS,
  defaultCalloutLabel,
  tiptapJsonToSemanticMarkdown,
  type CalloutKind,
} from "./markdown/calloutMarkdown";
import { markdownToTiptapDoc, type MarkdownImportDiagnostic } from "./markdown/markdownToTiptap";
import type { RunbookReferenceAttrs } from "./references/runbookReferences";
import {
  buildInitialWorkingBoardState,
  initialCalloutContent,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
  type TiptapWorkingBoardState,
} from "./state/tiptapLocalState";
import {
  getTiptapRunbookDescriptor,
  isKnownTiptapRunbookDocumentId,
  TIPTAP_RUNBOOK_DESCRIPTORS,
} from "./descriptors/tiptapRunbookDescriptors";
import "../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "./tiptapSpike.css";

export { initialCalloutContent };

export function activeTiptapRunbookDescriptorFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return getTiptapRunbookDescriptor(params.get("doc"));
}

function unknownDocumentIdFromLocation(): string | null {
  const documentId = new URLSearchParams(window.location.search).get("doc");
  return documentId && !isKnownTiptapRunbookDocumentId(documentId) ? documentId : null;
}


export const RUNBOOK_REFERENCE_SAMPLES: RunbookReferenceAttrs[] = [
  { kind: "ref", refType: "npc", refId: "lysandro-ironveil", label: "Lysandro Ironveil" },
  { kind: "ref", refType: "location", refId: "north-reach-gate", label: "North Reach Gate" },
  { kind: "ref", refType: "statblock", refId: "sewer-meat-creature", label: "Sewer Meat Creature" },
  { kind: "ref", refType: "roll-table", refId: "gate-dilemma-d12", label: "Gate Dilemma d12" },
  { kind: "ref", refType: "citation", refId: "c2s22-ending", label: "Session 22 ending" },
  { kind: "action", refType: "combat", refId: "north-gate-combat", label: "North Gate Combat" },
];

type LocalStateStatus = "Loaded starter content" | "Loaded local draft" | "Saved locally" | "Reset to starter" | "Imported committed Markdown";
type RunbookBlockSaveState = "local" | "draft" | "committed" | "locked" | "reference" | "operational";

interface RunbookBlockBoundary {
  state: RunbookBlockSaveState;
  label: string;
  description: string;
}

const RUNBOOK_BLOCK_BOUNDARIES: Record<RunbookBlockSaveState, RunbookBlockBoundary> = {
  local: { state: "local", label: "Local scratch", description: "Browser-only working text; prepare a file write before expecting a committed artifact." },
  draft: { state: "draft", label: "Saved draft", description: "Saved in local browser storage; not committed to the runbook Markdown file." },
  committed: { state: "committed", label: "Committed prep", description: "Imported from or written to the reviewed Markdown artifact; edit with file-write expectations." },
  locked: { state: "locked", label: "Locked for live", description: "Editing is locked while this block is treated as live-play material." },
  reference: { state: "reference", label: "Read-only reference", description: "A corpus/reference chip is present; edit surrounding prose, not the referenced canon identity." },
  operational: { state: "operational", label: "Operational", description: "This block points at a live operation/action. Confirm intent before changing expectations or launching tools." },
};

const BLOCK_SELECTOR = "aside.md-callout, h1, h2, h3, h4, h5, h6, p, li, blockquote";

function classifyRunbookBlock(element: HTMLElement, options: { locked: boolean; status: LocalStateStatus; committed: boolean }): RunbookBlockBoundary {
  if (options.locked) return RUNBOOK_BLOCK_BOUNDARIES.locked;
  if (element.querySelector('[data-md-ref-kind="action"]')) return RUNBOOK_BLOCK_BOUNDARIES.operational;
  if (element.querySelector('[data-md-ref-kind="ref"], [data-md-ref-kind="invalid"]')) return RUNBOOK_BLOCK_BOUNDARIES.reference;
  if (options.committed || options.status === "Imported committed Markdown") return RUNBOOK_BLOCK_BOUNDARIES.committed;
  if (options.status === "Saved locally" || options.status === "Loaded local draft") return RUNBOOK_BLOCK_BOUNDARIES.draft;
  return RUNBOOK_BLOCK_BOUNDARIES.local;
}

interface TiptapCalloutBridgeSpikeProps {
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

export function TiptapCalloutBridgeSpike({ onEditorToolsChange }: TiptapCalloutBridgeSpikeProps) {
  const descriptor = useMemo(activeTiptapRunbookDescriptorFromLocation, []);
  const unknownDocumentId = useMemo(unknownDocumentIdFromLocation, []);
  const [workingState, setWorkingState] = useState<TiptapWorkingBoardState>(() => (
    readTiptapWorkingBoardState(window.localStorage, descriptor) ?? buildInitialWorkingBoardState(descriptor)
  ));
  const [localStateStatus, setLocalStateStatus] = useState<LocalStateStatus>(() => (
    readTiptapWorkingBoardState(window.localStorage, descriptor) ? "Loaded local draft" : "Loaded starter content"
  ));
  const [copyMessage, setCopyMessage] = useState("");
  const [isEditorLocked, setIsEditorLocked] = useState(false);
  const [targetRelpath, setTargetRelpath] = useState(descriptor.targetRelpath);
  const [preparedWrite, setPreparedWrite] = useState<TiptapMarkdownWritePrepareResponse | null>(null);
  const [preparedMarkdown, setPreparedMarkdown] = useState("");
  const [writeStatus, setWriteStatus] = useState("");
  const [writeError, setWriteError] = useState("");
  const [commitResult, setCommitResult] = useState<TiptapMarkdownWriteCommitResponse | null>(null);
  const [importStatus, setImportStatus] = useState("");
  const [importError, setImportError] = useState("");
  const [importDiagnostics, setImportDiagnostics] = useState<MarkdownImportDiagnostic[]>([]);
  const [activeBlockBoundary, setActiveBlockBoundary] = useState<RunbookBlockBoundary>(RUNBOOK_BLOCK_BOUNDARIES.local);
  const activeBlockRef = useRef<HTMLElement | null>(null);
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const editor = useEditor({
    extensions: [StarterKit, CalloutNode, RunbookReferenceNode],
    content: workingState.tiptap_json as Content,
    editable: !isEditorLocked,
    onUpdate: ({ editor: nextEditor }) => {
      const tiptapJson = nextEditor.getJSON();
      const now = new Date().toISOString();
      setCommitResult(null);
      setWriteStatus("");
      setImportStatus("");
      setImportError("");
      setWorkingState((current) => {
        const nextState = {
          ...current,
          tiptap_json: tiptapJson,
          exported_markdown: tiptapJsonToSemanticMarkdown(tiptapJson),
          dirty: false,
          updated_at: now,
          last_local_save_at: now,
        };
        writeTiptapWorkingBoardState(window.localStorage, descriptor, nextState);
        return nextState;
      });
      setLocalStateStatus("Saved locally");
    },
  });

  const insertCallout = useCallback((kind: CalloutKind) => {
    editor?.chain().focus().insertCallout({ kind }).run();
  }, [editor]);

  const insertRunbookReference = useCallback((attrs: RunbookReferenceAttrs) => {
    editor?.chain().focus().insertRunbookReference(attrs).run();
  }, [editor]);

  const clearActiveBlockDecoration = useCallback(() => {
    activeBlockRef.current?.removeAttribute("data-runbook-block-state");
    activeBlockRef.current?.removeAttribute("data-runbook-block-label");
    activeBlockRef.current?.removeAttribute("data-runbook-block-selected");
    activeBlockRef.current = null;
  }, []);

  const decorateActiveBlock = useCallback((target: EventTarget | null, selected = false) => {
    const root = editorShellRef.current;
    if (!(target instanceof HTMLElement) || !root) return;
    const block = target.closest(BLOCK_SELECTOR);
    if (!(block instanceof HTMLElement) || !root.contains(block)) return;
    const boundary = classifyRunbookBlock(block, {
      locked: isEditorLocked,
      status: localStateStatus,
      committed: Boolean(commitResult),
    });
    clearActiveBlockDecoration();
    block.setAttribute("data-runbook-block-state", boundary.state);
    block.setAttribute("data-runbook-block-label", boundary.label);
    if (selected) block.setAttribute("data-runbook-block-selected", "true");
    activeBlockRef.current = block;
    setActiveBlockBoundary(boundary);
  }, [clearActiveBlockDecoration, commitResult, isEditorLocked, localStateStatus]);

  const toggleEditorLock = useCallback(() => {
    const nextLocked = !isEditorLocked;
    setIsEditorLocked(nextLocked);
    editor?.setEditable(!nextLocked);
    setActiveBlockBoundary(nextLocked ? RUNBOOK_BLOCK_BOUNDARIES.locked : RUNBOOK_BLOCK_BOUNDARIES.local);
    if (activeBlockRef.current) {
      activeBlockRef.current.setAttribute("data-runbook-block-state", nextLocked ? "locked" : "local");
      activeBlockRef.current.setAttribute("data-runbook-block-label", nextLocked ? "Locked for live" : "Local scratch");
    }
  }, [editor, isEditorLocked]);

  const resetLocalDraft = useCallback(() => {
    if (!editor) return;
    const now = new Date().toISOString();
    const resetState = buildInitialWorkingBoardState(descriptor, now);
    editor.commands.setContent(descriptor.starterContent as Content, false);
    writeTiptapWorkingBoardState(window.localStorage, descriptor, resetState);
    setWorkingState(resetState);
    setLocalStateStatus("Reset to starter");
    setCopyMessage("");
    setCommitResult(null);
    setWriteStatus("");
    clearActiveBlockDecoration();
    setActiveBlockBoundary(RUNBOOK_BLOCK_BOUNDARIES.local);
  }, [clearActiveBlockDecoration, descriptor, editor]);


  const importCommittedMarkdown = useCallback(async () => {
    if (!editor) return;
    setImportStatus("");
    setImportError("");
    setImportDiagnostics([]);
    setCommitResult(null);
    setPreparedWrite(null);
    setPreparedMarkdown("");

    const starterMarkdown = tiptapJsonToSemanticMarkdown(descriptor.starterContent);
    const shouldConfirm = localStateStatus !== "Loaded starter content" || workingState.exported_markdown !== starterMarkdown;
    if (shouldConfirm && !window.confirm("Importing committed Markdown will replace this local draft. Continue?")) {
      return;
    }

    const importPath = `/${descriptor.targetRelpath}`;
    try {
      const response = await fetch(importPath);
      if (!response.ok) throw new Error(`Import failed for ${descriptor.targetRelpath}: ${response.status} ${response.statusText}`.trim());
      const markdown = await response.text();
      const imported = markdownToTiptapDoc(markdown);
      const now = new Date().toISOString();
      const importedState: TiptapWorkingBoardState = {
        ...buildInitialWorkingBoardState(descriptor, now),
        tiptap_json: imported.doc,
        exported_markdown: tiptapJsonToSemanticMarkdown(imported.doc),
        dirty: false,
        updated_at: now,
        last_local_save_at: now,
      };

      editor.commands.setContent(imported.doc as Content, false);
      writeTiptapWorkingBoardState(window.localStorage, descriptor, importedState);
      setWorkingState(importedState);
      setLocalStateStatus("Imported committed Markdown");
      setImportDiagnostics(imported.diagnostics);
      setImportStatus(`Imported committed Markdown from ${descriptor.targetRelpath}.`);
    } catch (error) {
      setImportStatus("");
      setImportError(error instanceof Error ? error.message : "Import committed Markdown failed.");
    }
  }, [descriptor, editor, localStateStatus, workingState.exported_markdown]);

  const copyMarkdown = useCallback(async () => {
    if (!navigator.clipboard?.writeText) {
      setCopyMessage("Copy unavailable in this browser; select the Markdown export manually.");
      return;
    }

    try {
      await navigator.clipboard.writeText(workingState.exported_markdown);
      setCopyMessage("Markdown copied.");
    } catch {
      setCopyMessage("Copy unavailable in this browser; select the Markdown export manually.");
    }
  }, [workingState.exported_markdown]);

  const prepareFileWrite = useCallback(async () => {
    setWriteError("");
    setWriteStatus("Preparing file write…");
    setCommitResult(null);
    try {
      const response = await prepareTiptapMarkdownWrite({
        document_id: workingState.document_id,
        title: workingState.title,
        target_relpath: targetRelpath,
        markdown: workingState.exported_markdown,
      });
      setPreparedWrite(response);
      setPreparedMarkdown(workingState.exported_markdown);
      setWriteStatus(response.writer_ok ? "File write prepared. Review the diff before committing." : "");
    } catch (error) {
      setPreparedWrite(null);
      setPreparedMarkdown("");
      setWriteStatus("");
      setWriteError(error instanceof Error ? error.message : "File write prepare failed.");
    }
  }, [targetRelpath, workingState]);

  const canCommit = Boolean(
    preparedWrite?.writer_ok
      && preparedWrite.writer_confirm_token
      && preparedMarkdown === workingState.exported_markdown
      && preparedWrite.target_relpath === targetRelpath,
  );

  const commitFileWrite = useCallback(async () => {
    if (!preparedWrite?.writer_confirm_token || !canCommit) return;
    setWriteError("");
    setWriteStatus("Committing reviewed file write…");
    try {
      const response = await commitTiptapMarkdownWrite({
        document_id: workingState.document_id,
        title: workingState.title,
        target_relpath: preparedWrite.target_relpath,
        markdown: preparedMarkdown,
        writer_confirm_token: preparedWrite.writer_confirm_token,
      });
      setCommitResult(response);
      setWriteStatus("File written. Local draft remains available for further edits.");
    } catch (error) {
      setWriteStatus("");
      setWriteError(error instanceof Error ? error.message : "File write commit failed.");
    }
  }, [canCommit, preparedMarkdown, preparedWrite, workingState.document_id, workingState.title]);

  useEffect(() => () => clearActiveBlockDecoration(), [clearActiveBlockDecoration]);

  useEffect(() => {
    onEditorToolsChange?.({
      pinnedActions: [
        {
          id: "tiptap-edit-lock",
          eyebrow: isEditorLocked ? "Editing locked" : "Editing unlocked",
          label: isEditorLocked ? "Unlock editing" : "Lock editing",
          onClick: toggleEditorLock,
          disabled: !editor,
          pressed: isEditorLocked,
        },
      ],
      sections: [
        {
          id: "tiptap-local-state",
          title: "Local working state",
          defaultOpen: true,
          actions: [
            {
              id: "tiptap-reset-local-draft",
              eyebrow: "Browser storage",
              label: "Reset local draft",
              onClick: resetLocalDraft,
              disabled: !editor,
            },
            {
              id: "tiptap-copy-markdown",
              eyebrow: "Export",
              label: "Copy Markdown",
              onClick: copyMarkdown,
            },
          ],
        },
        {
          id: "tiptap-insert-blocks",
          title: "Insert blocks",
          defaultOpen: true,
          actions: CALLOUT_KINDS.map((kind) => ({
            id: `insert-${kind}`,
            eyebrow: "Insert",
            label: defaultCalloutLabel(kind),
            onClick: () => insertCallout(kind),
            disabled: !editor || isEditorLocked,
          })),
        },
        {
          id: "tiptap-insert-refs",
          title: "Insert refs",
          defaultOpen: true,
          actions: RUNBOOK_REFERENCE_SAMPLES.map((sample) => ({
            id: `insert-${sample.kind}-${sample.refType}`,
            eyebrow: sample.kind === "action" ? "Action" : sample.refType,
            label: sample.label,
            onClick: () => insertRunbookReference(sample),
            disabled: !editor || isEditorLocked,
          })),
        },
        {
          id: "tiptap-file-write",
          title: "File write",
          actions: [
            { id: "tiptap-import-committed-markdown", eyebrow: "Import", label: "Import committed Markdown", onClick: importCommittedMarkdown, disabled: !editor },
            { id: "tiptap-prepare-file-write", eyebrow: "Preview", label: "Prepare file write", onClick: prepareFileWrite },
            { id: "tiptap-commit-file-write", eyebrow: "Write", label: "Commit reviewed file write", onClick: commitFileWrite, disabled: !canCommit },
          ],
        },
      ],
    });

    return () => onEditorToolsChange?.(null);
  }, [canCommit, commitFileWrite, copyMarkdown, editor, importCommittedMarkdown, insertCallout, insertRunbookReference, isEditorLocked, onEditorToolsChange, prepareFileWrite, resetLocalDraft, toggleEditorLock]);

  const updatedAt = new Date(workingState.updated_at).toLocaleString();
  const editorThemeClass = `md-theme-${descriptor.themeId}`;

  return (
    <main className="tiptap-spike-page">
      <header className="tiptap-spike-header">
        <div>
          <p className="tiptap-spike-kicker">Runbook authoring dogfood</p>
          <h1>Tiptap Session Runbook Editor</h1>
          <p>Editable local working board that exports semantic Markdown for the static Command Board.</p>
        </div>
        <a href="/">Back to launcher</a>
      </header>

      <section className="tiptap-spike-panel" aria-labelledby="editor-heading">
        <div className="tiptap-spike-section-heading">
          <div>
            <p className="tiptap-spike-kicker">Working board state</p>
            <h2 id="editor-heading">Editor</h2>
          </div>
          <div className="tiptap-local-actions">
            <button type="button" onClick={resetLocalDraft} disabled={!editor}>Reset local draft</button>
            <button type="button" onClick={copyMarkdown}>Copy Markdown</button>
          </div>
        </div>

        <div className="tiptap-local-state" aria-live="polite">
          <p>Working board state is saved locally in this browser. No backend or corpus write happens here.</p>
          <dl>
            <div><dt>Document</dt><dd>{descriptor.title}</dd></div>
            <div><dt>Descriptor</dt><dd>{descriptor.documentId}</dd></div>
            <div><dt>Target</dt><dd>{descriptor.targetRelpath}</dd></div>
            <div><dt>State</dt><dd>{localStateStatus}</dd></div>
            <div><dt>Active block</dt><dd><span className={`tiptap-block-boundary-pill tiptap-block-boundary-${activeBlockBoundary.state}`}>{activeBlockBoundary.label}</span></dd></div>
            <div><dt>Updated</dt><dd>{updatedAt}</dd></div>
          </dl>
          {unknownDocumentId && (
            <p className="tiptap-write-warning">Unknown document id &quot;{unknownDocumentId}&quot;; loaded default descriptor.</p>
          )}
          <label htmlFor="tiptap-runbook-document">Runbook document</label>
          <select
            id="tiptap-runbook-document"
            aria-label="Runbook document"
            value={descriptor.documentId}
            onChange={(event) => { window.location.href = `/tiptap-callout-spike?doc=${event.target.value}`; }}
          >
            {TIPTAP_RUNBOOK_DESCRIPTORS.map((option) => (
              <option key={option.documentId} value={option.documentId}>{option.title}</option>
            ))}
          </select>
          {copyMessage && <p className="tiptap-copy-message">{copyMessage}</p>}
        </div>

        <div
          ref={editorShellRef}
          className={`tiptap-spike-editor md-content ${editorThemeClass}`}
          data-md-theme={descriptor.themeId}
          data-testid="tiptap-editor"
          onMouseMove={(event) => decorateActiveBlock(event.target)}
          onClick={(event) => decorateActiveBlock(event.target, true)}
          onMouseLeave={() => { clearActiveBlockDecoration(); setActiveBlockBoundary(RUNBOOK_BLOCK_BOUNDARIES.local); }}
        >
          <div className="tiptap-block-boundary-help" aria-live="polite">
            <strong>{activeBlockBoundary.label}</strong>
            <span>{activeBlockBoundary.description}</span>
            {(activeBlockBoundary.state === "operational" || activeBlockBoundary.state === "locked") && (
              <button type="button" onClick={toggleEditorLock} disabled={!editor}>
                {isEditorLocked ? "Unlock live block" : "Lock live block"}
              </button>
            )}
          </div>
          <EditorContent editor={editor} />
        </div>
      </section>

      <div className="tiptap-spike-grid">
        <section className="tiptap-spike-panel" aria-labelledby="json-heading">
          <h2 id="json-heading">Editor JSON</h2>
          <pre data-testid="editor-json">{JSON.stringify(workingState.tiptap_json, null, 2)}</pre>
        </section>
        <section className="tiptap-spike-panel" aria-labelledby="markdown-heading">
          <h2 id="markdown-heading">Exported Markdown</h2>
          <pre data-testid="markdown-export">{workingState.exported_markdown}</pre>
        </section>
      </div>

      <section className="tiptap-spike-panel tiptap-write-panel" aria-labelledby="file-write-heading">
        <h2 id="file-write-heading">File write preview</h2>
        <p>
          Editing is still local. Preparing a write asks the backend to preview the Markdown artifact.
          Committing writes the reviewed runbook Markdown file. It does not write canon or operational state.
        </p>
        <div className="tiptap-write-form">
          <label htmlFor="tiptap-target-path">Target path</label>
          <input
            id="tiptap-target-path"
            value={targetRelpath}
            onChange={(event) => {
              setTargetRelpath(event.target.value);
              setCommitResult(null);
              setWriteStatus("");
            }}
          />
          <div className="tiptap-local-actions">
            <button type="button" onClick={importCommittedMarkdown} disabled={!editor}>Import committed Markdown</button>
            <button type="button" onClick={prepareFileWrite}>Prepare file write</button>
            <button type="button" onClick={commitFileWrite} disabled={!canCommit}>Commit reviewed file write</button>
          </div>
        </div>
        {importStatus && <p className="tiptap-write-success">{importStatus}</p>}
        {importDiagnostics.map((diagnostic) => (
          <p className="tiptap-write-warning" key={`${diagnostic.level}-${diagnostic.line ?? "none"}-${diagnostic.message}`}>
            {diagnostic.line ? `${diagnostic.message} at line ${diagnostic.line}.` : diagnostic.message}
          </p>
        ))}
        {importError && <p className="tiptap-write-error" role="alert">{importError}</p>}
        {preparedWrite && preparedMarkdown !== workingState.exported_markdown && (
          <p className="tiptap-write-warning">Editor changed after prepare. Re-prepare before committing.</p>
        )}
        {preparedWrite && preparedWrite.target_relpath !== targetRelpath && (
          <p className="tiptap-write-warning">Target path changed after prepare. Re-prepare before committing.</p>
        )}
        {preparedWrite?.writer_diff != null && <pre className="tiptap-write-diff">{preparedWrite.writer_diff}</pre>}
        {preparedWrite?.warnings.map((warning) => <p className="tiptap-write-warning" key={warning}>{warning}</p>)}
        {preparedWrite?.diagnostics.map((diagnostic) => <p key={diagnostic}>{diagnostic}</p>)}
        {writeError && <p className="tiptap-write-error" role="alert">{writeError}</p>}
        {writeStatus && <p className={commitResult ? "tiptap-write-success" : ""}>{writeStatus}</p>}
        {commitResult && (
          <dl className="tiptap-write-success">
            <div><dt>Path</dt><dd>{commitResult.target_display_path}</dd></div>
            <div><dt>Bytes written</dt><dd>{commitResult.bytes_written}</dd></div>
            <div><dt>Fingerprint</dt><dd>{commitResult.file_fingerprint}</dd></div>
            {commitResult.backup_relpath && <div><dt>Backup</dt><dd>{commitResult.backup_relpath}</dd></div>}
          </dl>
        )}
      </section>

      <aside className="tiptap-spike-note" aria-labelledby="bridge-notes-heading">
        <h2 id="bridge-notes-heading">Bridge notes</h2>
        <p>
          This is working board state only. Exported Markdown is for review/corpus handoff. No canon writes happen here.
        </p>
      </aside>
    </main>
  );
}
