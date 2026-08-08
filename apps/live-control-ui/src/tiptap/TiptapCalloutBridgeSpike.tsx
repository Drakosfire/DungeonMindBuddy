import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content, Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import { getWorkspaceDocumentSnapshot } from "../api/liveApi";
import { useWorkspaceDocumentAuthoring } from "../workspaceDocument/useWorkspaceDocumentAuthoring";
import { defaultMarkdownDocumentAdapter } from "./MarkdownDocumentAdapter";
import { MarkdownEditorCore } from "./MarkdownEditorCore";
import {
  toAppChromeToolsGeneration,
  type MarkdownEditorToolbarModel,
} from "./MarkdownEditorToolbar";
import {
  CALLOUT_KINDS,
  defaultCalloutLabel,
  tiptapJsonToSemanticMarkdown,
  type CalloutKind,
} from "./markdown/calloutMarkdown";
import type { MarkdownImportDiagnostic } from "./markdown/markdownToTiptap";
import type { RunbookReferenceAttrs } from "./references/runbookReferences";
import {
  buildInitialWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
} from "./state/tiptapLocalState";
import {
  initialCalloutContent,
  resolveRunbookSpikeDocument,
  type TiptapRunbookDescriptor,
} from "./descriptors/tiptapRunbookDescriptors";
import "../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "./tiptapSpike.css";

export { initialCalloutContent };

export const RUNBOOK_REFERENCE_SAMPLES: RunbookReferenceAttrs[] = [
  { kind: "ref", refType: "npc", refId: "lysandro-ironveil", label: "Lysandro Ironveil" },
  { kind: "ref", refType: "location", refId: "north-reach-gate", label: "North Reach Gate" },
  { kind: "ref", refType: "statblock", refId: "sewer-meat-creature", label: "Sewer Meat Creature" },
  { kind: "ref", refType: "roll-table", refId: "gate-dilemma-d12", label: "Gate Dilemma d12" },
  { kind: "ref", refType: "citation", refId: "c2s22-ending", label: "Session 22 ending" },
  { kind: "action", refType: "combat", refId: "north-gate-combat", label: "North Gate Combat" },
];

type SpikeStatusOverlay = "reset_to_starter" | "imported_committed";
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

const BLOCK_SELECTOR = "aside.md-callout, aside.md-decision-consequence, h1, h2, h3, h4, h5, h6, p, li, blockquote";

function displayStatusLabel(
  overlay: SpikeStatusOverlay | null,
  authoringStatusLabel: string,
): string {
  if (overlay === "reset_to_starter") return "Reset to starter";
  if (overlay === "imported_committed") return "Imported committed Markdown";
  return authoringStatusLabel;
}

function classifyRunbookBlock(
  element: HTMLElement,
  options: { locked: boolean; displayStatus: string; committed: boolean },
): RunbookBlockBoundary {
  if (options.locked) return RUNBOOK_BLOCK_BOUNDARIES.locked;
  if (element.querySelector('[data-md-ref-kind="action"]')) return RUNBOOK_BLOCK_BOUNDARIES.operational;
  if (element.querySelector('[data-md-ref-kind="ref"], [data-md-ref-kind="invalid"]')) return RUNBOOK_BLOCK_BOUNDARIES.reference;
  if (options.committed) return RUNBOOK_BLOCK_BOUNDARIES.committed;
  if (
    options.displayStatus === "Imported committed Markdown"
    || options.displayStatus === "Unsaved local changes"
    || options.displayStatus === "Reset to starter"
  ) {
    return RUNBOOK_BLOCK_BOUNDARIES.draft;
  }
  return RUNBOOK_BLOCK_BOUNDARIES.local;
}

interface TiptapCalloutBridgeSpikeProps {
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
}

interface RunbookSpikeEditorProps {
  descriptor: TiptapRunbookDescriptor;
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
  onImportComplete?: (result: { status: string; diagnostics: MarkdownImportDiagnostic[] }) => void;
  initialStatusOverlay?: SpikeStatusOverlay | null;
  persistedImportStatus?: string;
  persistedImportDiagnostics?: MarkdownImportDiagnostic[];
}

function RunbookSpikeEditor({
  descriptor,
  onEditorToolsChange,
  onImportComplete,
  initialStatusOverlay = null,
  persistedImportStatus = "",
  persistedImportDiagnostics = [],
}: RunbookSpikeEditorProps) {
  const authoring = useWorkspaceDocumentAuthoring({
    documentId: descriptor.documentId,
    surface: "runbook",
    kind: "runbook",
    emptyMarkdownFallback: descriptor.starterContent,
  });

  const [statusOverlay, setStatusOverlay] = useState<SpikeStatusOverlay | null>(initialStatusOverlay);
  const [copyMessage, setCopyMessage] = useState("");
  const [isEditorLocked, setIsEditorLocked] = useState(false);
  const [importStatus, setImportStatus] = useState(persistedImportStatus);
  const [importError, setImportError] = useState("");
  const [importDiagnostics, setImportDiagnostics] = useState<MarkdownImportDiagnostic[]>(persistedImportDiagnostics);
  const [activeBlockBoundary, setActiveBlockBoundary] = useState<RunbookBlockBoundary>(RUNBOOK_BLOCK_BOUNDARIES.local);
  const [editorRevision, setEditorRevision] = useState(0);
  const activeBlockRef = useRef<HTMLElement | null>(null);
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const previousDocumentKeyRef = useRef(authoring.documentKey);

  if (previousDocumentKeyRef.current !== authoring.documentKey) {
    previousDocumentKeyRef.current = authoring.documentKey;
    editorRef.current = null;
  }

  const displayStatus = displayStatusLabel(statusOverlay, authoring.statusLabel);
  const exportedMarkdown = useMemo(() => {
    if (editorRef.current) {
      return tiptapJsonToSemanticMarkdown(editorRef.current.getJSON());
    }
    return tiptapJsonToSemanticMarkdown(authoring.editorContent);
  }, [authoring.documentKey, authoring.editorContent, editorRevision]);
  const hasCommitReceipt = Boolean(authoring.lastCommitReceipt);
  const editorReady = editorRef.current != null;

  useEffect(() => {
    if (authoring.dirty && statusOverlay) {
      setStatusOverlay(null);
    }
  }, [authoring.dirty, statusOverlay]);

  const handleEditorChange = useCallback((nextEditor: Editor | null) => {
    editorRef.current = nextEditor;
    authoring.setEditor(nextEditor);
    setEditorRevision((revision) => revision + 1);
  }, [authoring.setEditor]);

  const handleEditorUpdate = useCallback((
    json: Parameters<typeof authoring.handleEditorUpdate>[0],
    editor: Parameters<typeof authoring.handleEditorUpdate>[1],
    meta: Parameters<typeof authoring.handleEditorUpdate>[2],
  ) => {
    authoring.handleEditorUpdate(json, editor, meta);
    setEditorRevision((revision) => revision + 1);
  }, [authoring.handleEditorUpdate]);

  const insertCallout = useCallback((kind: CalloutKind) => {
    const ed = editorRef.current;
    if (!ed) return;
    ed.chain().focus().insertCallout({ kind }).run();
    ed.view.dispatch(ed.state.tr);
    authoring.markDirty();
  }, [authoring.markDirty]);

  const insertDecisionConsequence = useCallback(() => {
    const ed = editorRef.current;
    if (!ed) return;
    ed.chain().focus().insertDecisionConsequence().run();
    ed.view.dispatch(ed.state.tr);
    authoring.markDirty();
  }, [authoring.markDirty]);

  const insertRunbookReference = useCallback((attrs: RunbookReferenceAttrs) => {
    const ed = editorRef.current;
    if (!ed) return;
    ed.chain().focus().insertRunbookReference(attrs).run();
    ed.view.dispatch(ed.state.tr);
    authoring.markDirty();
  }, [authoring.markDirty]);

  const removeActiveBlock = useCallback(() => {
    editorRef.current?.chain().focus().deleteActiveBlock().run();
  }, []);

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
      displayStatus,
      committed: hasCommitReceipt,
    });
    clearActiveBlockDecoration();
    block.setAttribute("data-runbook-block-state", boundary.state);
    block.setAttribute("data-runbook-block-label", boundary.label);
    if (selected) block.setAttribute("data-runbook-block-selected", "true");
    activeBlockRef.current = block;
    setActiveBlockBoundary(boundary);
  }, [clearActiveBlockDecoration, displayStatus, hasCommitReceipt, isEditorLocked]);

  const toggleEditorLock = useCallback(() => {
    const nextLocked = !isEditorLocked;
    setIsEditorLocked(nextLocked);

    const activeBlock = activeBlockRef.current;
    if (!activeBlock) {
      setActiveBlockBoundary(nextLocked ? RUNBOOK_BLOCK_BOUNDARIES.locked : RUNBOOK_BLOCK_BOUNDARIES.local);
      return;
    }

    const boundary = nextLocked
      ? RUNBOOK_BLOCK_BOUNDARIES.locked
      : classifyRunbookBlock(activeBlock, {
        locked: false,
        displayStatus,
        committed: hasCommitReceipt,
      });
    activeBlock.setAttribute("data-runbook-block-state", boundary.state);
    activeBlock.setAttribute("data-runbook-block-label", boundary.label);
    setActiveBlockBoundary(boundary);
  }, [displayStatus, hasCommitReceipt, isEditorLocked]);

  const resetLocalDraft = useCallback(async () => {
    const snapshot = authoring.snapshot;
    const starterMarkdown = defaultMarkdownDocumentAdapter.exportMarkdown(descriptor.starterContent);
    const snapshotMarkdown = snapshot?.markdown ?? "";
    const differsFromSnapshot = starterMarkdown !== snapshotMarkdown;
    const now = new Date().toISOString();
    const resetState = {
      ...buildInitialWorkspaceDocumentLocalState({
        documentId: descriptor.documentId,
        title: descriptor.title,
        campaignId: descriptor.campaignId,
        kind: "runbook",
        targetSession: descriptor.session,
        surface: "runbook",
        baseRevision: snapshot?.loaded_revision ?? 1,
        baseContentSha256: snapshot?.content_sha256 ?? "",
        starterContent: descriptor.starterContent,
        now,
      }),
      tiptap_json: descriptor.starterContent,
      exported_markdown: starterMarkdown,
      dirty: differsFromSnapshot,
      updated_at: now,
      last_local_save_at: now,
    };
    writeWorkspaceDocumentLocalState(window.localStorage, resetState);
    setStatusOverlay("reset_to_starter");
    setCopyMessage("");
    setImportStatus("");
    setImportError("");
    clearActiveBlockDecoration();
    setActiveBlockBoundary(RUNBOOK_BLOCK_BOUNDARIES.local);
    await authoring.reloadFromSnapshot();
  }, [authoring, clearActiveBlockDecoration, descriptor]);

  const importCommittedMarkdown = useCallback(async () => {
    setImportStatus("");
    setImportError("");
    setImportDiagnostics([]);

    const starterMarkdown = defaultMarkdownDocumentAdapter.exportMarkdown(descriptor.starterContent);
    const shouldConfirm = authoring.dirty || exportedMarkdown !== starterMarkdown;
    if (shouldConfirm && !window.confirm("Importing committed Markdown will replace this local draft. Continue?")) {
      return;
    }

    try {
      const snapshot = authoring.snapshot ?? await getWorkspaceDocumentSnapshot(descriptor.documentId);
      const markdown = snapshot.markdown.trim()
        ? snapshot.markdown
        : await (async () => {
          const importPath = `/${descriptor.targetRelpath}`;
          const response = await fetch(importPath);
          if (!response.ok) {
            throw new Error(`Import failed for ${descriptor.targetRelpath}: ${response.status} ${response.statusText}`.trim());
          }
          return response.text();
        })();
      const imported = defaultMarkdownDocumentAdapter.importMarkdown(markdown);
      const now = new Date().toISOString();
      const importedState = {
        ...buildInitialWorkspaceDocumentLocalState({
          documentId: descriptor.documentId,
          title: descriptor.title,
          campaignId: descriptor.campaignId,
          kind: "runbook",
          targetSession: descriptor.session,
          surface: "runbook",
          baseRevision: snapshot.loaded_revision,
          baseContentSha256: snapshot.content_sha256,
          starterContent: descriptor.starterContent,
          now,
        }),
        tiptap_json: imported.doc,
        exported_markdown: defaultMarkdownDocumentAdapter.exportMarkdown(imported.doc),
        dirty: false,
        updated_at: now,
        last_local_save_at: now,
      };

      writeWorkspaceDocumentLocalState(window.localStorage, importedState);
      onImportComplete?.({
        status: `Imported committed Markdown from ${descriptor.targetRelpath}.`,
        diagnostics: imported.diagnostics,
      });
    } catch (error) {
      setImportStatus("");
      setImportError(error instanceof Error ? error.message : "Import committed Markdown failed.");
    }
  }, [descriptor, exportedMarkdown, onImportComplete]);

  const copyMarkdown = useCallback(async () => {
    if (!navigator.clipboard?.writeText) {
      setCopyMessage("Copy unavailable in this browser; select the Markdown export manually.");
      return;
    }

    try {
      await navigator.clipboard.writeText(exportedMarkdown);
      setCopyMessage("Markdown copied.");
    } catch {
      setCopyMessage("Copy unavailable in this browser; select the Markdown export manually.");
    }
  }, [exportedMarkdown]);

  const saveMarkdown = useCallback(async () => {
    setImportStatus("");
    setImportError("");
    await authoring.saveMarkdown();
  }, [authoring]);

  useEffect(() => () => clearActiveBlockDecoration(), [clearActiveBlockDecoration]);

  useEffect(() => {
    const toolbarModel: MarkdownEditorToolbarModel = {
      pinnedActions: [
        {
          id: "tiptap-edit-lock",
          eyebrow: isEditorLocked ? "Editing locked" : "Editing unlocked",
          label: isEditorLocked ? "Unlock editing" : "Lock editing",
          onClick: toggleEditorLock,
          disabled: !editorReady,
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
              disabled: !editorReady,
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
          actions: [
            ...CALLOUT_KINDS.map((kind) => ({
              id: `insert-${kind}`,
              eyebrow: "Insert",
              label: defaultCalloutLabel(kind),
              onClick: () => insertCallout(kind),
              disabled: !editorReady || isEditorLocked,
            })),
            {
              id: "insert-decision-consequence",
              eyebrow: "Insert",
              label: "Decision / Consequence",
              onClick: insertDecisionConsequence,
              disabled: !editorReady || isEditorLocked,
            },
          ],
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
            disabled: !editorReady || isEditorLocked,
          })),
        },
        {
          id: "tiptap-edit-blocks",
          title: "Edit blocks",
          defaultOpen: true,
          actions: [
            {
              id: "tiptap-remove-block",
              eyebrow: "Remove",
              label: "Remove block",
              onClick: removeActiveBlock,
              disabled: !editorReady || isEditorLocked,
            },
          ],
        },
        {
          id: "tiptap-file-write",
          title: "File write",
          actions: [
            { id: "tiptap-import-committed-markdown", eyebrow: "Import", label: "Import committed Markdown", onClick: importCommittedMarkdown, disabled: !editorReady },
            { id: "tiptap-save-markdown", eyebrow: "Write", label: "Save", onClick: () => void saveMarkdown(), disabled: authoring.saveDisabled },
          ],
        },
      ],
    };

    onEditorToolsChange?.(toAppChromeToolsGeneration(toolbarModel, {
      kind: "spike",
      id: "tiptap-callout-spike",
    }));

    return () => onEditorToolsChange?.(null);
  }, [
    authoring.saveDisabled,
    copyMarkdown,
    editorReady,
    importCommittedMarkdown,
    insertCallout,
    insertDecisionConsequence,
    insertRunbookReference,
    isEditorLocked,
    onEditorToolsChange,
    removeActiveBlock,
    resetLocalDraft,
    saveMarkdown,
    toggleEditorLock,
  ]);

  const editorThemeClass = "md-theme-command";

  if (authoring.phase === "loading" || authoring.phase === "unloaded") {
    return (
      <main className="tiptap-spike-page">
        <p>Loading runbook document…</p>
      </main>
    );
  }

  if (authoring.phase === "load_error") {
    return (
      <main className="tiptap-spike-page">
        <p>{authoring.error ?? "Failed to load runbook document"}</p>
      </main>
    );
  }

  if (authoring.phase === "conflict") {
    return (
      <main className="tiptap-spike-page">
        <header className="tiptap-spike-header">
          <div>
            <p className="tiptap-spike-kicker">Runbook authoring dogfood</p>
            <h1>Tiptap Session Runbook Editor</h1>
          </div>
        </header>
        <section className="tiptap-spike-panel" role="alert">
          <p>{authoring.reconciliation?.conflictReason ?? "Local draft conflicts with server content."}</p>
          <div className="tiptap-local-actions">
            <button type="button" onClick={() => void authoring.reloadFromSnapshot()}>
              Reload from server
            </button>
            <button type="button" onClick={() => void authoring.discardLocalDraft()}>
              Discard local draft
            </button>
          </div>
        </section>
      </main>
    );
  }

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
            <button type="button" onClick={resetLocalDraft} disabled={!editorReady}>Reset local draft</button>
            <button type="button" onClick={copyMarkdown}>Copy Markdown</button>
          </div>
        </div>

        <div className="tiptap-local-state" aria-live="polite">
          <p>Working board state is saved locally in this browser. No backend or corpus write happens here.</p>
          <dl>
            <div><dt>Document</dt><dd>{descriptor.title}</dd></div>
            <div><dt>Document ID</dt><dd><code>{descriptor.documentId}</code></dd></div>
            <div><dt>Target</dt><dd>{descriptor.targetRelpath}</dd></div>
            <div><dt>State</dt><dd>{displayStatus}</dd></div>
            <div><dt>Active block</dt><dd><span className={`tiptap-block-boundary-pill tiptap-block-boundary-${activeBlockBoundary.state}`}>{activeBlockBoundary.label}</span></dd></div>
          </dl>
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
              <button type="button" onClick={toggleEditorLock} disabled={!editorReady}>
                {isEditorLocked ? "Unlock live block" : "Lock live block"}
              </button>
            )}
          </div>
          <MarkdownEditorCore
            content={authoring.editorContent as Content}
            documentKey={authoring.documentKey}
            editable={!isEditorLocked}
            onEditorChange={handleEditorChange}
            onUpdate={handleEditorUpdate}
          >
            {(ed) => <EditorContent editor={ed} />}
          </MarkdownEditorCore>
        </div>
      </section>

      <div className="tiptap-spike-grid">
        <section className="tiptap-spike-panel" aria-labelledby="json-heading">
          <h2 id="json-heading">Editor JSON</h2>
          <pre data-testid="editor-json">{JSON.stringify(authoring.editorContent, null, 2)}</pre>
        </section>
        <section className="tiptap-spike-panel" aria-labelledby="markdown-heading">
          <h2 id="markdown-heading">Exported Markdown</h2>
          <pre data-testid="markdown-export">{exportedMarkdown}</pre>
        </section>
      </div>

      <section className="tiptap-spike-panel tiptap-write-panel" aria-labelledby="file-write-heading">
        <h2 id="file-write-heading">File write preview</h2>
        <p>
          Editing is still local. Saving asks the backend to prepare and commit the Markdown artifact.
          It does not write canon or operational state.
        </p>
        <div className="tiptap-write-form">
          <label htmlFor="tiptap-target-path">Target path</label>
          <output id="tiptap-target-path" className="tiptap-target-path-display">{descriptor.targetRelpath}</output>
          <div className="tiptap-local-actions">
            <button type="button" onClick={importCommittedMarkdown}>Import committed Markdown</button>
            <button type="button" onClick={() => void saveMarkdown()} disabled={authoring.saveDisabled}>Save</button>
          </div>
        </div>
        {importStatus && <p className="tiptap-write-success">{importStatus}</p>}
        {importDiagnostics.map((diagnostic) => (
          <p className="tiptap-write-warning" key={`${diagnostic.level}-${diagnostic.line ?? "none"}-${diagnostic.message}`}>
            {diagnostic.line ? `${diagnostic.message} at line ${diagnostic.line}.` : diagnostic.message}
          </p>
        ))}
        {importError && <p className="tiptap-write-error" role="alert">{importError}</p>}
        {authoring.error && <p className="tiptap-write-error" role="alert">{authoring.error}</p>}
        {displayStatus === "Committed" || authoring.phase === "committed" || authoring.phase === "committed_verification_pending" ? (
          <p className="tiptap-write-success">{authoring.statusLabel}</p>
        ) : null}
        {authoring.lastCommitReceipt && (
          <dl className="tiptap-write-success">
            <div><dt>Path</dt><dd>{authoring.lastCommitReceipt.target_display_path}</dd></div>
            <div><dt>Bytes written</dt><dd>{authoring.lastCommitReceipt.bytes_written}</dd></div>
            <div><dt>Fingerprint</dt><dd>{authoring.lastCommitReceipt.file_fingerprint}</dd></div>
            {authoring.lastCommitReceipt.backup_relpath && (
              <div><dt>Backup</dt><dd>{authoring.lastCommitReceipt.backup_relpath}</dd></div>
            )}
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

export function TiptapCalloutBridgeSpike({ onEditorToolsChange }: TiptapCalloutBridgeSpikeProps) {
  const [descriptor, setDescriptor] = useState<TiptapRunbookDescriptor | null>(null);
  const [descriptorError, setDescriptorError] = useState<string | null>(null);
  const [documentSessionKey, setDocumentSessionKey] = useState(0);
  const [importStatus, setImportStatus] = useState("");
  const [importDiagnostics, setImportDiagnostics] = useState<MarkdownImportDiagnostic[]>([]);
  const [importStatusOverlay, setImportStatusOverlay] = useState<SpikeStatusOverlay | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const loaded = await resolveRunbookSpikeDocument();
        if (!cancelled) {
          setDescriptor(loaded);
          setDescriptorError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setDescriptorError(error instanceof Error ? error.message : "Failed to load runbook document");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!descriptor) {
    return (
      <main className="tiptap-spike-page">
        <p>{descriptorError ?? "Loading runbook document…"}</p>
      </main>
    );
  }

  return (
    <RunbookSpikeEditor
      key={documentSessionKey}
      descriptor={descriptor}
      onEditorToolsChange={onEditorToolsChange}
      initialStatusOverlay={importStatusOverlay}
      persistedImportStatus={importStatus}
      persistedImportDiagnostics={importDiagnostics}
      onImportComplete={(result) => {
        setImportStatus(result.status);
        setImportDiagnostics(result.diagnostics);
        setImportStatusOverlay("imported_committed");
        setDocumentSessionKey((key) => key + 1);
      }}
    />
  );
}
