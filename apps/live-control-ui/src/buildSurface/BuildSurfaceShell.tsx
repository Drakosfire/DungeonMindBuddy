import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import type { Content, Editor } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import {
  commitTiptapMarkdownWrite,
  createWorkspaceDocument,
  getWorkspaceDocument,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import type { AppChromeTools } from "../chrome/AppChrome";
import { EditCapabilityProvider, useEditCapability } from "../planSurface/edit/editCapability";
import { ProjectionProvider } from "../planSurface/projection/projectionContext";
import {
  defaultMarkdownDocumentAdapter,
  hasCommitBlockingDiagnostics,
} from "../tiptap/MarkdownDocumentAdapter";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { toAppChromeTools, type MarkdownEditorToolbarModel } from "../tiptap/MarkdownEditorToolbar";
import {
  buildDraftFromRecord,
  readBuildLocalDraft,
  writeBuildLocalDraft,
} from "./buildLocalDraft";
import {
  BUILD_DEFAULT_CAMPAIGN_ID,
  BUILD_DEFAULT_DOCUMENT_CLASS,
  BUILD_SURFACE_KICKER,
  BUILD_SURFACE_LABEL,
  createBuildSurfaceConfig,
} from "./buildSurfaceConfig";
import "../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "../tiptap/tiptapSpike.css";

const EMPTY_DOC: Content = {
  type: "doc",
  content: [{ type: "paragraph" }],
};

function documentIdFromLocation(): string | null {
  const value = new URLSearchParams(window.location.search).get("documentId");
  return value?.trim() || null;
}

function setDocumentIdInLocation(documentId: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("documentId", documentId);
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
}

type SaveStatus = "idle" | "dirty" | "saving" | "committed" | "error";

interface BuildSurfaceShellProps {
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
}

function themeStyle(tokens: Record<string, string> | undefined): CSSProperties {
  return (tokens ?? {}) as CSSProperties;
}

function BuildSurfaceBody({
  record,
  onEditorToolsChange,
  onRecordCommitted,
}: {
  record: WorkspaceDocumentRecord;
  onEditorToolsChange?: (tools: AppChromeTools | null) => void;
  onRecordCommitted: (next: WorkspaceDocumentRecord) => void;
}) {
  const config = useMemo(() => createBuildSurfaceConfig(record), [record]);
  const { publishSurfaceContext, rehydrateScope } = useAgentInteraction();
  const { isLocked, canEdit, toggleLock } = useEditCapability();
  const initialDraft = useMemo(() => {
    const stored = readBuildLocalDraft(window.localStorage, record.document_id);
    if (stored) return stored;
    return buildDraftFromRecord(record, EMPTY_DOC, false);
  }, [record]);

  const [editor, setEditor] = useState<Editor | null>(null);
  const [content, setContent] = useState<Content>(initialDraft.tiptap_json);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>(
    initialDraft.dirty ? "dirty" : record.content_status === "committed" ? "committed" : "idle",
  );
  const [statusMessage, setStatusMessage] = useState(
    initialDraft.dirty
      ? "Local edits not yet committed"
      : record.content_status === "committed"
        ? "Committed source revision loaded"
        : "Draft source ready",
  );
  const [saveError, setSaveError] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<string[]>([]);
  const skipNextUpdateRef = useRef(true);
  const recordRef = useRef(record);
  recordRef.current = record;

  useEffect(() => {
    rehydrateScope({
      campaignId: record.campaign_id,
      sessionNumber: 0,
      surfaceId: "build",
      documentId: record.document_id,
    });
    publishSurfaceContext({
      surfaceId: "build",
      label: `${BUILD_SURFACE_LABEL} · ${record.title}`,
      campaignId: record.campaign_id,
      documentId: record.document_id,
      ambientSummary: [
        record.kind,
        record.source_domain,
        record.document_class,
        record.authority_state,
        record.visibility_state,
        `rev ${record.revision}`,
      ]
        .filter(Boolean)
        .join(" · "),
      sourceEnvelope: {
        schema: "agent_interaction_source_envelope_v1",
        artifactRefs: record.target_relpath
          ? [{ kind: "path", value: record.target_relpath }]
          : [],
        provenanceSummary: `workspace document ${record.document_id}`,
      },
      updatedAt: new Date().toISOString(),
    });
  }, [publishSurfaceContext, record, rehydrateScope]);

  const persistLocalDraft = useCallback(
    (nextContent: Content, dirty: boolean, nextRecord = recordRef.current) => {
      writeBuildLocalDraft(
        window.localStorage,
        buildDraftFromRecord(nextRecord, nextContent, dirty),
      );
    },
    [],
  );

  const saveMarkdown = useCallback(async () => {
    if (!editor) return;
    const currentRecord = recordRef.current;
    const markdown = defaultMarkdownDocumentAdapter.exportMarkdown(editor.getJSON());
    const imported = defaultMarkdownDocumentAdapter.importMarkdown(markdown);
    if (hasCommitBlockingDiagnostics(imported.diagnostics)) {
      setSaveStatus("error");
      setSaveError("Unsupported Markdown would be lossy; fix diagnostics before save.");
      setDiagnostics(
        imported.diagnostics
          .filter((entry) => entry.level === "warning")
          .map((entry) => entry.message),
      );
      persistLocalDraft(editor.getJSON(), true, currentRecord);
      return;
    }

    setSaveStatus("saving");
    setSaveError(null);
    setStatusMessage("Preparing durable write…");
    try {
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: currentRecord.document_id,
        markdown,
        expected_revision: currentRecord.revision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token) {
        setSaveStatus("error");
        setSaveError("Prepare blocked the write.");
        setDiagnostics(prepared.diagnostics);
        setStatusMessage("Save blocked");
        persistLocalDraft(editor.getJSON(), true, currentRecord);
        return;
      }
      const committed = await commitTiptapMarkdownWrite({
        document_id: currentRecord.document_id,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
        expected_revision: currentRecord.revision,
      });
      const refreshed = await getWorkspaceDocument(currentRecord.document_id);
      onRecordCommitted(refreshed);
      persistLocalDraft(editor.getJSON(), false, refreshed);
      setSaveStatus("committed");
      setStatusMessage(`Committed ${committed.bytes_written ?? 0} bytes`);
      setDiagnostics(committed.diagnostics);
    } catch (error) {
      setSaveStatus("error");
      setSaveError(error instanceof Error ? error.message : "Save failed");
      setStatusMessage("Save failed");
      persistLocalDraft(editor.getJSON(), true, currentRecord);
    }
  }, [editor, onRecordCommitted, persistLocalDraft]);

  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(() => ({
    pinnedActions: [
      {
        id: "build-lock-editing",
        label: isLocked ? "Unlock editing" : "Lock editing",
        onClick: toggleLock,
        pressed: isLocked,
      },
    ],
    sections: [
      {
        id: "build-markdown-save",
        title: "Source save",
        defaultOpen: true,
        actions: [
          {
            id: "build-save-markdown",
            label: "Save to Markdown",
            onClick: () => {
              void saveMarkdown();
            },
            disabled: !editor || !canEdit || saveStatus === "saving",
          },
        ],
      },
    ],
  }), [canEdit, editor, isLocked, saveMarkdown, saveStatus, toggleLock]);

  useEffect(() => {
    onEditorToolsChange?.(toAppChromeTools(toolbarModel));
    return () => onEditorToolsChange?.(null);
  }, [onEditorToolsChange, toolbarModel]);

  return (
    <ProjectionProvider config={config}>
      <div
        className="build-surface-root"
        data-surface={config.id}
        data-md-theme={config.theme.themeId}
        data-testid="build-surface"
        style={themeStyle(config.theme.tokens)}
      >
        <header className="build-surface-header">
          <p className="plan-surface-kicker">{BUILD_SURFACE_KICKER}</p>
          <h1 data-testid="build-surface-title">{record.title}</h1>
          <p data-testid="build-surface-save-status">{statusMessage}</p>
          <dl className="build-source-metadata" data-testid="build-source-metadata">
            <div>
              <dt>Document ID</dt>
              <dd><code data-testid="build-document-id">{record.document_id}</code></dd>
            </div>
            <div>
              <dt>Kind</dt>
              <dd>{record.kind}</dd>
            </div>
            <div>
              <dt>Source domain</dt>
              <dd>{record.source_domain}</dd>
            </div>
            <div>
              <dt>Document class</dt>
              <dd>{record.document_class}</dd>
            </div>
            <div>
              <dt>Authority</dt>
              <dd>{record.authority_state}</dd>
            </div>
            <div>
              <dt>Visibility</dt>
              <dd>{record.visibility_state}</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd>{record.target_relpath}</dd>
            </div>
            <div>
              <dt>Revision</dt>
              <dd data-testid="build-revision">{record.revision}</dd>
            </div>
          </dl>
        </header>

        <div
          className={`tiptap-spike-editor md-content md-theme-${config.theme.themeId}`}
          data-testid="build-surface-editor"
        >
          <MarkdownEditorCore
            content={content}
            documentKey={record.document_id}
            editable={canEdit}
            onEditorChange={setEditor}
            onUpdate={(json) => {
              if (skipNextUpdateRef.current) {
                skipNextUpdateRef.current = false;
                return;
              }
              setContent(json);
              setSaveStatus("dirty");
              setStatusMessage("Local edits not yet committed");
              persistLocalDraft(json, true);
            }}
          >
            {(ed) => <EditorContent editor={ed} />}
          </MarkdownEditorCore>
        </div>

        {saveError ? (
          <p role="alert" data-testid="build-save-error">{saveError}</p>
        ) : null}
        {diagnostics.length > 0 ? (
          <ul data-testid="build-save-diagnostics">
            {diagnostics.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </ProjectionProvider>
  );
}

export function BuildSurfaceShell({ onEditorToolsChange }: BuildSurfaceShellProps) {
  const [record, setRecord] = useState<WorkspaceDocumentRecord | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadKey, setLoadKey] = useState(0);

  const loadOrCreateDocument = useCallback(async () => {
    setLoadError(null);
    setRecord(null);
    try {
      const requestedId = documentIdFromLocation();
      let nextRecord: WorkspaceDocumentRecord;
      if (requestedId) {
        nextRecord = await getWorkspaceDocument(requestedId);
      } else {
        nextRecord = await createWorkspaceDocument({
          title: "Untitled worldbuilding source",
          campaign_id: BUILD_DEFAULT_CAMPAIGN_ID,
          kind: "worldbuilding_source",
          source_domain: "worldbuilding",
          document_class: BUILD_DEFAULT_DOCUMENT_CLASS,
          authority_state: "draft",
          visibility_state: "internal",
        });
        setDocumentIdInLocation(nextRecord.document_id);
      }
      if (nextRecord.kind !== "worldbuilding_source") {
        throw new Error("Build only opens worldbuilding_source documents");
      }
      setRecord(nextRecord);
    } catch (error) {
      setRecord(null);
      setLoadError(error instanceof Error ? error.message : "Failed to load Build document");
    }
  }, []);

  useEffect(() => {
    void loadOrCreateDocument();
  }, [loadOrCreateDocument, loadKey]);

  if (loadError) {
    return (
      <main className="build-surface-root app-status app-error" aria-label="Build surface">
        <p className="plan-surface-kicker">{BUILD_SURFACE_KICKER}</p>
        <h1>{BUILD_SURFACE_LABEL}</h1>
        <p role="alert" data-testid="build-load-error">{loadError}</p>
        <button type="button" onClick={() => setLoadKey((key) => key + 1)}>
          Retry
        </button>
      </main>
    );
  }

  if (!record) {
    return (
      <main className="build-surface-root app-status" aria-label="Build surface">
        <p>Loading Build surface…</p>
      </main>
    );
  }

  return (
    <EditCapabilityProvider>
      <BuildSurfaceBody
        key={record.document_id}
        record={record}
        onEditorToolsChange={onEditorToolsChange}
        onRecordCommitted={setRecord}
      />
    </EditCapabilityProvider>
  );
}
