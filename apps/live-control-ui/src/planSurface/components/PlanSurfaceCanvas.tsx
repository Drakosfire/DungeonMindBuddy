import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Content } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import type { AppChromeTools } from "../../chrome/AppChrome";
import { CalloutNode } from "../../tiptap/extensions/CalloutNode";
import { RunbookReferenceNode } from "../../tiptap/extensions/RunbookReferenceNode";
import {
  getTiptapRunbookDescriptor,
  TIPTAP_RUNBOOK_DESCRIPTORS,
} from "../../tiptap/descriptors/tiptapRunbookDescriptors";
import {
  buildInitialWorkingBoardState,
  readTiptapWorkingBoardState,
  writeTiptapWorkingBoardState,
} from "../../tiptap/state/tiptapLocalState";
import { createCorpusDerivedViewsReader } from "../derivedViews/derivedViewsAdapter";
import { useEditCapability } from "../edit/editCapability";
import { useProjection } from "../projection/projectionContext";
import { readReferenceFromElement, resolveReference } from "../reference/referenceResolver";
import type { SurfaceCanvasConfig, SurfaceThemeConfig } from "../types";
import "../../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "../../tiptap/tiptapSpike.css";

interface PlanSurfaceCanvasProps {
  canvas: SurfaceCanvasConfig;
  theme: SurfaceThemeConfig;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

export function PlanSurfaceCanvas({ canvas, theme, onEditorToolsChange }: PlanSurfaceCanvasProps) {
  const descriptor = useMemo(
    () => getTiptapRunbookDescriptor(canvas.documentId),
    [canvas.documentId],
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

  return (
    <section className="plan-surface-canvas" aria-label="Plan canvas">
      <div className="plan-canvas-heading">
        <p className="plan-surface-kicker">Working board</p>
        <h2>{descriptor.title}</h2>
        <label htmlFor="plan-runbook-document" className="plan-canvas-doc-label">
          Runbook document
        </label>
        <select
          id="plan-runbook-document"
          value={descriptor.documentId}
          onChange={(event) => {
            const params = new URLSearchParams(window.location.search);
            params.set("doc", event.target.value);
            window.location.href = `/plan?${params.toString()}`;
          }}
        >
          {TIPTAP_RUNBOOK_DESCRIPTORS.map((option) => (
            <option key={option.documentId} value={option.documentId}>
              {option.title}
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
