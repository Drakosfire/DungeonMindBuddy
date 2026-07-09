import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { AppChromeTools } from "../../chrome/AppChrome";
import { CalloutNode } from "../../tiptap/extensions/CalloutNode";
import { RunbookReferenceNode } from "../../tiptap/extensions/RunbookReferenceNode";
import { planDocumentToRunbookDescriptor } from "../config/planSessionDescriptor";
import {
  buildInitialWorkingBoardState,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
} from "../../tiptap/state/tiptapLocalState";
import { createCorpusDerivedViewsReader } from "../derivedViews/derivedViewsAdapter";
import { useEditCapability } from "../edit/editCapability";
import { useProjection } from "../projection/projectionContext";
import { readReferenceFromElement, resolveReference } from "../reference/referenceResolver";
import { usePlanMarkdownSave } from "../save/usePlanMarkdownSave";
import type { PlanSessionDescriptor, SurfaceThemeConfig } from "../types";
import "../../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "../../tiptap/tiptapSpike.css";

interface PlanSurfaceCanvasProps {
  sessionDescriptor: PlanSessionDescriptor;
  theme: SurfaceThemeConfig;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
  onSaveStatusChange?: (statusLabel: string) => void;
}

export function PlanSurfaceCanvas({
  sessionDescriptor,
  theme,
  onEditorToolsChange,
  onSaveStatusChange,
}: PlanSurfaceCanvasProps) {
  const descriptor = useMemo(
    () => planDocumentToRunbookDescriptor(sessionDescriptor),
    [sessionDescriptor],
  );
  const { isLocked, canEdit, toggleLock } = useEditCapability();
  const { openContentFromChip } = useProjection();
  const derivedViews = useMemo(
    () => createCorpusDerivedViewsReader(resolveReference),
    [],
  );
  const editorShellRef = useRef<HTMLDivElement | null>(null);
  const markDirtyRef = useRef<() => void>(() => {});
  const skipNextDirtyRef = useRef(true);
  const [workingState] = useState(() =>
    readTiptapWorkingBoardState(window.localStorage, descriptor)
      ?? buildInitialWorkingBoardState(descriptor),
  );

  const editor = useEditor({
    extensions: [StarterKit, CalloutNode, RunbookReferenceNode],
    content: workingState.tiptap_json as Content,
    editable: canEdit,
    onUpdate: ({ editor: nextEditor }) => {
      const tiptapJson = nextEditor.getJSON();
      const now = new Date().toISOString();
      const nextState = {
        ...workingState,
        tiptap_json: tiptapJson,
        updated_at: now,
        last_local_save_at: now,
      };
      writeTiptapWorkingBoardState(window.localStorage, descriptor, nextState);
      if (skipNextDirtyRef.current) {
        skipNextDirtyRef.current = false;
        return;
      }
      markDirtyRef.current();
    },
  });

  const {
    state: saveState,
    statusLabel,
    saveDisabled,
    canCommit,
    markDirty,
    prepareSave,
    commitSave,
    exportCurrentMarkdown,
  } = usePlanMarkdownSave({ editor, sessionDescriptor });

  useEffect(() => {
    markDirtyRef.current = markDirty;
  }, [markDirty]);

  useEffect(() => {
    onSaveStatusChange?.(statusLabel);
  }, [onSaveStatusChange, statusLabel]);

  useEffect(() => {
    editor?.setEditable(canEdit);
  }, [canEdit, editor]);

  const handleChipActivate = useCallback(
    async (target: EventTarget | null) => {
      if (!(target instanceof HTMLElement) || !editorShellRef.current?.contains(target)) return;
      const chip = target.closest(".md-ref-chip");
      if (!(chip instanceof HTMLElement)) return;
      const ref = readReferenceFromElement(chip);
      if (!ref) return;
      const resolution = await derivedViews.resolveReference(ref);
      openContentFromChip(ref, resolution, true);
    },
    [derivedViews, openContentFromChip],
  );

  useEffect(() => {
    onEditorToolsChange?.({
      pinnedActions: [
        {
          id: "plan-canvas-edit-lock",
          eyebrow: isLocked ? "Editing locked" : "Editing unlocked",
          label: isLocked ? "Unlock editing" : "Lock editing",
          onClick: toggleLock,
          pressed: isLocked,
        },
      ],
      sections: [
        {
          id: "plan-markdown-save",
          title: "Markdown save",
          defaultOpen: true,
          actions: [
            {
              id: "plan-preview-markdown-save",
              label: "Preview Markdown Save",
              onClick: () => {
                void prepareSave();
              },
              disabled: saveDisabled || saveState.status === "preparing",
            },
            {
              id: "plan-commit-markdown-save",
              label: "Commit Markdown",
              onClick: () => {
                void commitSave();
              },
              disabled: !canCommit || saveState.status === "committing",
            },
          ],
        },
      ],
    });
    return () => onEditorToolsChange?.(null);
  }, [
    canCommit,
    commitSave,
    isLocked,
    onEditorToolsChange,
    prepareSave,
    saveDisabled,
    saveState.status,
    toggleLock,
  ]);

  const editorThemeClass = `md-theme-${theme.themeId ?? descriptor.themeId}`;
  const planningDocument = sessionDescriptor.planningDocument;
  const currentMarkdown = exportCurrentMarkdown();
  const preparedMarkdownStale = Boolean(
    saveState.prepared
      && saveState.preparedMarkdown
      && currentMarkdown !== saveState.preparedMarkdown,
  );

  return (
    <section className="plan-surface-canvas" aria-label="Plan canvas">
      <div className="plan-canvas-heading">
        <p className="plan-surface-kicker">Working board</p>
        <h2 data-testid="plan-canvas-title">{descriptor.title}</h2>
        <p className="plan-canvas-meta" data-testid="plan-canvas-document-id">
          Document <code>{planningDocument.documentId}</code> · {statusLabel}
        </p>
      </div>
      <div
        ref={editorShellRef}
        className={`tiptap-spike-editor md-content ${editorThemeClass}`}
        data-md-theme={theme.themeId ?? descriptor.themeId}
        data-testid="plan-surface-canvas-editor"
        onClick={(event) => {
          void handleChipActivate(event.target);
        }}
      >
        <EditorContent editor={editor} />
      </div>

      {(saveState.status === "preview_ready" || saveState.status === "committing" || saveState.committed || saveState.error) && (
        <section
          className="plan-markdown-save-panel"
          aria-label="Markdown save preview"
          data-testid="plan-markdown-save-panel"
        >
          <p className="plan-surface-kicker">Durable save</p>
          <p className="plan-markdown-save-target" data-testid="plan-markdown-save-target">
            Target: {planningDocument.targetRelpath}
            {saveState.prepared ? ` · ${saveState.prepared.file_exists ? "replace existing file" : "new file"}` : null}
          </p>
          {preparedMarkdownStale && (
            <p className="plan-markdown-save-warning" role="alert">
              Editor changed after preview. Preview the save again before committing.
            </p>
          )}
          {saveState.prepared?.writer_diff != null && (
            <pre className="plan-markdown-save-diff" data-testid="plan-markdown-save-diff">
              {saveState.prepared.writer_diff}
            </pre>
          )}
          {saveState.prepared?.warnings.map((warning) => (
            <p className="plan-markdown-save-warning" key={warning}>
              {warning}
            </p>
          ))}
          {saveState.prepared?.diagnostics.map((diagnostic) => (
            <p className="plan-markdown-save-diagnostic" key={diagnostic}>
              {diagnostic}
            </p>
          ))}
          {saveState.error && (
            <p className="plan-markdown-save-error" role="alert" data-testid="plan-markdown-save-error">
              {saveState.error}
            </p>
          )}
          {saveState.committed && (
            <dl className="plan-markdown-save-success" data-testid="plan-markdown-save-success">
              <div>
                <dt>Path</dt>
                <dd>{saveState.committed.target_display_path}</dd>
              </div>
              <div>
                <dt>Bytes written</dt>
                <dd>{saveState.committed.bytes_written}</dd>
              </div>
              {saveState.committed.backup_relpath && (
                <div>
                  <dt>Backup</dt>
                  <dd>{saveState.committed.backup_relpath}</dd>
                </div>
              )}
            </dl>
          )}
        </section>
      )}
    </section>
  );
}
