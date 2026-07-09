import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { AppChromeTools } from "../../chrome/AppChrome";
import { CalloutNode } from "../../tiptap/extensions/CalloutNode";
import { RunbookReferenceNode } from "../../tiptap/extensions/RunbookReferenceNode";
import {
  listSelectablePlanDocuments,
  planDocumentToRunbookDescriptor,
} from "../config/planSessionDescriptor";
import {
  buildInitialWorkingBoardState,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
} from "../../tiptap/state/tiptapLocalState";
import { createCorpusDerivedViewsReader } from "../derivedViews/derivedViewsAdapter";
import { useEditCapability } from "../edit/editCapability";
import { useProjection } from "../projection/projectionContext";
import { readReferenceFromElement, resolveReference } from "../reference/referenceResolver";
import type { SurfaceCanvasConfig, SurfaceConfig, SurfaceThemeConfig } from "../types";
import "../../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "../../tiptap/tiptapSpike.css";

interface PlanSurfaceCanvasProps {
  canvas: SurfaceCanvasConfig;
  sessionDescriptor?: SurfaceConfig["sessionDescriptor"];
  theme: SurfaceThemeConfig;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

export function PlanSurfaceCanvas({
  canvas,
  sessionDescriptor,
  theme,
  onEditorToolsChange,
}: PlanSurfaceCanvasProps) {
  const descriptor = useMemo(() => {
    if (sessionDescriptor) {
      return planDocumentToRunbookDescriptor(sessionDescriptor);
    }
    throw new Error("PlanSurfaceCanvas requires a session descriptor.");
  }, [sessionDescriptor]);
  const documentOptions = useMemo(
    () => (sessionDescriptor ? listSelectablePlanDocuments(sessionDescriptor) : []),
    [sessionDescriptor],
  );
  const { isLocked, canEdit, toggleLock } = useEditCapability();
  const { openContentFromChip } = useProjection();
  const derivedViews = useMemo(
    () => createCorpusDerivedViewsReader(resolveReference),
    [],
  );
  const editorShellRef = useRef<HTMLDivElement | null>(null);
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
    },
  });

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
      sections: [],
    });
    return () => onEditorToolsChange?.(null);
  }, [isLocked, onEditorToolsChange, toggleLock]);

  const editorThemeClass = `md-theme-${theme.themeId ?? descriptor.themeId}`;
  const planningDocument = sessionDescriptor?.planningDocument;

  return (
    <section className="plan-surface-canvas" aria-label="Plan canvas">
      <div className="plan-canvas-heading">
        <p className="plan-surface-kicker">Working board</p>
        <h2 data-testid="plan-canvas-title">{descriptor.title}</h2>
        {planningDocument ? (
          <p className="plan-canvas-meta" data-testid="plan-canvas-document-id">
            Document <code>{planningDocument.documentId}</code> · local draft · corpus writes not enabled yet
          </p>
        ) : null}
        <label htmlFor="plan-runbook-document" className="plan-canvas-doc-label">
          Planning document
        </label>
        <select
          id="plan-runbook-document"
          value={canvas.documentId}
          onChange={(event) => {
            const params = new URLSearchParams(window.location.search);
            params.set("doc", event.target.value);
            window.location.href = `/plan?${params.toString()}`;
          }}
        >
          {documentOptions.map((option) => (
            <option key={option.documentId} value={option.documentId}>
              {option.title}
              {option.starterKind === "legacy_north_gate" ? " (legacy demo)" : ""}
            </option>
          ))}
        </select>
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
    </section>
  );
}
