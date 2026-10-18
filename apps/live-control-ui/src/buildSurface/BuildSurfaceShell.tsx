import { mediaMarkdown } from "../media/mediaReferences";
import { MediaImageWizard } from "../media/MediaImageWizard";
import { createBuildComposeBridge, type BuildComposeBridge, type BuildComposeEditorState } from "./buildComposeBridge";
import { BUILD_STARTER_CONTENT, buildStarterKey, requestBuildStudioAction } from "./buildStudioActions";
import { BUILD_FIND_EXISTING_TOOL_ID } from "./reference/buildReferenceIds";
import { useEffect, useMemo, useRef, useState } from "react";

import { DocumentConversationDock, type PlanConversationPresentationHosts } from "../planSurface/components/PlanConversationDockAdapter";
import { usePublishWorldBuildConversation, type SavedWorldBuildConversationContext } from "../agentInteraction/WorldAgentConversation";
import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import { authenticatedApiFetch, getBuildSourceNavigation } from "../api/liveApi";
import { MarkdownCanvas } from "../markdownCanvas/MarkdownCanvas";
import {
  useMarkdownCanvasSession,
  type MarkdownCanvasSessionValue,
} from "../markdownCanvas/MarkdownCanvasSession";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { parseBuildSourceNavigationQuery } from "../sourceNavigation/sourceNavigation";
import { BuildGraphObjectContext, parseBuildGraphPointerFromLocation } from "./BuildGraphObjectContext";
import { BUILD_DOCUMENT_SAVE_COMMAND_ID } from "./buildDocumentCommands";
import { useBuildAutosave } from "./useBuildAutosave";
import "./buildAutosave.css";
import { useBuildMarkdownCanvasSlots } from "./buildMarkdownCanvasAdapter";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import {
  BuildSourceReader,
  type BuildSourceNavigationTarget,
} from "./BuildSourceReader";

/** Rejected authority diagnostics stay in the page UI; Agent Interaction gets no UUID/rev/path/hash. */
export const BUILD_AUTHORITY_REJECTION_AMBIENT = "Document rejected by Build authority";

function isPresentableSourcePhase(phase: string): boolean {
  return !["unloaded", "loading", "load_error", "conflict"].includes(phase);
}

const IDLE_SOURCE_NAVIGATION_TARGET: BuildSourceNavigationTarget = { status: "none" };

function BuildPresentableSourceView({
  session,
  editSlots,
  navigationTarget,
  composeBridge,
  onEditorTools,
}: {
  composeBridge: BuildComposeBridge;
  session: MarkdownCanvasSessionValue;
  editSlots: MarkdownCanvasSlots;
  navigationTarget: BuildSourceNavigationTarget;
  onEditorTools?: (tools: AppChromeToolsGeneration | null) => void;
}) {
  useBuildAutosave(session);
  const [outlineVersion, setOutlineVersion] = useState(0);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [mediaError,setMediaError]=useState('');
  const mediaCapture=useRef<Awaited<ReturnType<BuildComposeBridge['capture']>>|null>(null);
  async function openMedia() {
    try { mediaCapture.current=await composeBridge.capture();setMediaError('');setMediaOpen(true); }
    catch(reason) {setMediaError(reason instanceof Error?reason.message:'Open an editable page first.');}
  }
  const { openTool, setPaneOpen, surfaceInteractionPublication } = useAgentInteraction();
  const referenceTool = surfaceInteractionPublication?.tools.find(tool => tool.id === BUILD_FIND_EXISTING_TOOL_ID);
  useEffect(() => {
    const editor = session.editor;
    const record = session.record;
    if (!editor || !record || navigationTarget.status !== "none") return;
    const key = buildStarterKey(record.document_id);
    if (sessionStorage.getItem(key) !== "worldbuilding") return;
    // Wait for the editor's document-key hydration to settle before consuming
    // the explicit create intent. It must never target a replaced editor.
    const timer = window.setTimeout(() => {
      if (editor.isDestroyed) return;
      if (editor.isEmpty && !session.snapshot?.markdown.trim() && !session.dirty) {
        editor.commands.insertContent(BUILD_STARTER_CONTENT);
        session.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
      }
      sessionStorage.removeItem(key);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [session.editor, session.documentKey, session.record, session.snapshot, session.dirty, session.handleEditorUpdate, navigationTarget.status]);
  useEffect(() => {
    const editor = session.editor;
    if (!editor) return;
    const update = () => setOutlineVersion(value => value + 1);
    editor.on("update", update);
    editor.on("selectionUpdate", update);
    return () => { editor.off("update", update); editor.off("selectionUpdate", update); };
  }, [session.editor]);

  useEffect(() => {
    const editor = session.editor;
    const headings: { position: number; level: number; text: string }[] = [];
    editor?.state.doc.descendants((node, position) => {
      if (node.type.name === "heading") headings.push({ position, level: node.attrs.level, text: node.textContent });
    });
    onEditorTools?.({ target: { kind: "document", id: session.record!.document_id },
      tools: { sections: [{ id: "build-document", title: "Document", defaultOpen: true, actions: [],
        panel: <><div className="build-formatting" role="group" aria-label="Text formatting">
          <button type="button" disabled={!editor} aria-pressed={editor?.isActive("bold") ?? false}
            onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</button>
          <button type="button" disabled={!editor} aria-pressed={editor?.isActive("italic") ?? false}
            onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</button>
          <button type="button" disabled={!editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}>Heading</button>
          <button type="button" disabled={!editor?.can().undo()} onClick={() => editor?.chain().focus().undo().run()}>Undo</button>
          <button type="button" disabled={!editor?.can().redo()} onClick={() => editor?.chain().focus().redo().run()}>Redo</button>
        </div><nav className="markdown-document-outline" aria-label="On this page">
          {headings.length ? <ol>{headings.map(heading => <li key={heading.position}
            style={{ paddingInlineStart: `${Math.min(heading.level - 1, 2) * 0.75}rem` }}>
            <button type="button" onClick={() => editor?.chain().focus().setTextSelection(heading.position + 1).scrollIntoView().run()}>
              {heading.text || "Untitled section"}
            </button>
          </li>)}</ol> : <p>No headings in this document.</p>}
        </nav></> }] } });
    return () => onEditorTools?.(null);
  }, [onEditorTools, session.editor, session.record?.document_id, outlineVersion]);

  const showEmptySourcePrompt = session.record?.kind === "worldbuilding_source"
    && navigationTarget.status === "none"
    && (session.editor?.isEmpty ?? !session.snapshot?.markdown.trim());
  const startWith = (heading: string) => {
    const editor = session.editor;
    if (!editor?.isEmpty) return;
    editor.chain().focus().insertContent([
      { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: heading }] },
      { type: "paragraph" },
    ]).run();
  };

  return <div className="build-surface-shell" data-testid="build-surface-shell">
    {navigationTarget.status !== "none" ? <details className="build-source-evidence" open>
      <summary>Saved evidence passage</summary>
      <BuildSourceReader showOutline={false} title={session.record!.title}
        markdown={session.snapshot!.markdown} dirty={session.dirty} navigationTarget={navigationTarget} />
    </details> : null}
    {showEmptySourcePrompt ? <section className="build-empty-document-prompt" data-testid="build-empty-document-prompt" aria-label="A beginning for this page">
      <div className="build-empty-document-prompt__art" aria-hidden="true">
        <svg viewBox="0 0 120 104" fill="none">
          <path d="M7 83c17-13 29-13 43 0s26 13 42 0 17-12 21-10" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 4" />
          <path d="M17 24 34 9l14 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M29 14v14m-7-7h14" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
          <rect x="42" y="20" width="53" height="68" rx="4" fill="#fffaf0" stroke="currentColor" strokeWidth="1.5" />
          <path d="M52 34h32M52 42h24M52 58c8-7 15-7 22 0s13 7 18 1" stroke="#c8ad72" strokeWidth="1.4" strokeLinecap="round" />
          <path d="m82 73 3.2 6.5 7.2 1-5.2 5 .9 7-6.1-3.4-6.3 3.4 1.2-7-5.3-5 7.1-1L82 73Z" fill="#e0b34d" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
          <circle cx="103" cy="22" r="2" fill="#c58b33" />
          <circle cx="109" cy="32" r="1.25" fill="#c58b33" />
        </svg>
      </div>
      <div className="build-empty-document-prompt__copy">
        <p className="build-empty-document-prompt__eyebrow">A FRESH PAGE</p>
        <h2>Every world starts somewhere.</h2>
        <p>Pick a first thread—or skip the prompt and start typing below.</p>
        <div className="build-empty-document-prompt__starters" role="group" aria-label="Choose a first heading">
          {(["A place", "A person", "A mystery"] as const).map(heading =>
            <button key={heading} type="button" onClick={() => startWith(heading)}>{heading}</button>)}
        </div>
      </div>
    </section> : null}
    <div className="build-authoring-toolbar" role="toolbar" aria-label="Page authoring">
      <div role="group" aria-label="Format page">
        <button type="button" aria-pressed={session.editor?.isActive("bold") ?? false} disabled={!session.editor} onClick={() => session.editor?.chain().focus().toggleBold().run()}>Bold</button>
        <button type="button" aria-pressed={session.editor?.isActive("italic") ?? false} disabled={!session.editor} onClick={() => session.editor?.chain().focus().toggleItalic().run()}>Italic</button>
        <button type="button" disabled={!session.editor} onClick={() => session.editor?.chain().focus().toggleHeading({level:2}).run()}>Heading</button>
        <button type="button" disabled={!session.editor} onClick={() => session.editor?.chain().focus().toggleBulletList().run()}>List</button>
        <button type="button" disabled={!session.editor?.can().undo()} onClick={() => session.editor?.chain().focus().undo().run()}>Undo</button>
      </div>
      <div role="group" aria-label="Worldbuilding tools">
        <button type="button" disabled={referenceTool?.availability.status !== "enabled"} onClick={() => openTool(BUILD_FIND_EXISTING_TOOL_ID)}>Link existing node</button>
        <button type="button" onClick={() => setPaneOpen(true)}>Ask Agent</button>
        <button type="button" onClick={() => void openMedia()}>Create image</button>
      </div>
    </div>
    {mediaError&&<p role="alert">{mediaError}</p>}
    {mediaOpen && <aside className="build-media-studio"><MediaImageWizard onClose={() => setMediaOpen(false)} onChoose={async(image,_result,placement)=>{
      const origin=mediaCapture.current;
      if (!origin || image.state!=='ready' || !composeBridge.pickInsertion) throw new Error('Save this image and open an editable page first.');
      const target=await composeBridge.pickInsertion({...placement,assetId:image.asset_id});
      placement.signal.throwIfAborted();
      if (target.basis.world_id!==origin.basis.world_id || target.basis.document_id!==origin.basis.document_id || target.basis.registry_revision!==origin.basis.registry_revision || target.basis.content_sha256!==origin.basis.content_sha256) throw new Error('The page changed. Open Image Studio again on the intended page.');
      const {response}=await authenticatedApiFetch(`/api/live/media/images/${image.asset_id}/metadata`,{signal:placement.signal});
      const asset=await response.json();
      placement.signal.throwIfAborted();
      if(!response.ok || asset.asset_id!==image.asset_id || asset.state!=='ready') throw new Error('Save this image before placing it.');
      composeBridge.insert(target,mediaMarkdown(image.asset_id,'Saved artwork'));
      setMediaOpen(false);setMediaError('');
    }} /></aside>}
    <MarkdownCanvas slots={editSlots} />
  </div>;
}

function BuildConversationBinding({ source, hosts, composeBridge }: { source: SavedWorldBuildConversationContext | null; hosts: PlanConversationPresentationHosts; composeBridge?: BuildComposeBridge }) {
  usePublishWorldBuildConversation(source, hosts, composeBridge);
  return null;
}

/** Build's no-document landing is still a framed projection with the same conversation dock. */
export function BuildEmptyLanding({ loadStatus }: { loadStatus: "idle" | "loading" | "ready" | "empty" | "error" }) {
  const isLoading = loadStatus === "idle" || loadStatus === "loading";
  const hasError = loadStatus === "error";
  const reader = (
    <div className="build-surface-with-graph-context document-projection" data-document-surface="build">
      <main
        className={`build-surface-shell build-empty-landing${hasError ? " build-empty-landing--error" : ""}`}
        data-testid="build-surface-empty"
        aria-busy={isLoading}
        aria-labelledby="build-empty-landing-title"
      >
        <div className="build-empty-landing__welcome">
          <div className="build-empty-landing__hero">
            <p className="build-empty-landing__eyebrow">YOUR WORLDBUILDING STUDIO</p>
            <h1 id="build-empty-landing-title">
              {hasError ? (
                "That page took a wrong turn."
              ) : (
                <>
                  Start with a spark.<br />
                  <em>Build a world around it.</em>
                </>
              )}
            </h1>
            <p className="build-empty-landing__intro">
              {hasError
                ? "Choose another page from the Build bar, or start fresh from Source actions."
                : "A place, a person, a strange rumor—give one idea a page, then let the rest of the world grow around it."}
            </p>
          </div>
          <div className="build-empty-landing__illustration" aria-hidden="true">
            <svg viewBox="0 0 420 240" role="presentation" aria-hidden="true" focusable="false">
              <path
                className="build-empty-landing__contour"
                d="M31 178c43-58 85-59 120-32s57 32 87-2 75-43 151 3M22 202c51-41 94-41 129-16s59 24 92-5 78-39 150-2M70 145c30-39 57-40 83-20s45 23 66 0 52-31 96-10"
              />
              <path
                className="build-empty-landing__route"
                d="M75 106c47 0 49 52 100 52s54-74 107-74 53 50 88 50"
              />
              <circle className="build-empty-landing__node" cx="75" cy="106" r="7" />
              <circle className="build-empty-landing__node" cx="175" cy="158" r="7" />
              <circle className="build-empty-landing__node" cx="282" cy="84" r="7" />
              <circle className="build-empty-landing__node" cx="370" cy="134" r="7" />
              <g className="build-empty-landing__page" transform="translate(177 48) rotate(-5 34 43)">
                <path d="M8 3h47l14 14v66H8z" />
                <path d="M55 3v15h14M19 34h38M19 44h31M19 54h35M19 64h25" />
                <path
                  className="build-empty-landing__page-star"
                  d="m18 20 2.2 4.5 4.8.7-3.5 3.4.8 4.8-4.3-2.3-4.3 2.3.8-4.8-3.5-3.4 4.8-.7z"
                />
              </g>
              <path
                className="build-empty-landing__spark"
                d="m328 37 3 7 7 3-7 3-3 7-3-7-7-3 7-3zM112 46l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"
              />
            </svg>
            <div className="build-empty-landing__illustration-caption">
              <span>PLACES</span><i /> <span>PEOPLE</span><i /> <span>WHAT-IFS</span>
            </div>
          </div>
        </div>
        {!isLoading && !hasError ? <button type="button" className="build-studio-start" onClick={() => requestBuildStudioAction("new")}>Make this page yours →</button> : null}
        {isLoading ? (
          <p className="build-empty-landing__status" role="status">Finding your worldbuilding sources…</p>
        ) : hasError ? (
          <p className="build-empty-landing__status" role="alert">The requested source is unavailable. You can choose another from the Build bar.</p>
        ) : (
          <section className="build-empty-landing__begin" aria-labelledby="build-empty-landing-steps">
            <p className="build-empty-landing__eyebrow" id="build-empty-landing-steps">CHOOSE YOUR FIRST STEP</p>
            <div className="build-empty-landing__paths" aria-label="Ways to begin">
              <button type="button" onClick={() => requestBuildStudioAction("open")}>
                <span className="build-empty-landing__step">01</span>
                <div>
                  <p className="build-empty-landing__path-label">PICK UP WHERE YOU LEFT OFF</p>
                  <h2>Open a page</h2>
                  <p>Choose a saved worldbuilding source in the Build bar above.</p>
                </div>
              </button>
              <button type="button" onClick={() => requestBuildStudioAction("new")}>
                <span className="build-empty-landing__step">02</span>
                <div>
                  <p className="build-empty-landing__path-label">BEGIN WITH A CLEAN PAGE</p>
                  <h2>Start something new</h2>
                  <p>
                    Give this starter a title, then make it your own.
                  </p>
                </div>
              </button>
              <button type="button" onClick={() => requestBuildStudioAction("import")}>
                <span className="build-empty-landing__step">03</span>
                <div>
                  <p className="build-empty-landing__path-label">ALREADY HAVE NOTES?</p>
                  <h2>Bring your lore</h2>
                  <p>
                    Continue from your existing Markdown notes.
                  </p>
                </div>
              </button>
            </div>
          </section>
        )}
        <p className="build-empty-landing__footnote">
          <span aria-hidden="true">✦</span>
          Nothing is created until you choose to begin. Your page and its world tools share this workspace.
        </p>
      </main>
    </div>
  );

  return (
    <div className="build-workspace-projection">
      <DocumentConversationDock surface="build" contextLabel="Worldbuilding source" reader={reader}>
        {hosts => <BuildConversationBinding source={null} hosts={hosts} />}
      </DocumentConversationDock>
    </div>
  );
}

/**
 * Build document workspace: shared authoring and conversation publication.
 * Document authority lives on MarkdownCanvasSession (provider is owned by BuildSurfacePage).
 * Saved evidence remains separate from the directly editable working document.
 */
export function BuildSurfaceShell({ onEditorTools }: { onEditorTools?: (tools: AppChromeToolsGeneration | null) => void }) {
  const session = useMarkdownCanvasSession();
  const { rehydrateScope, publishSurfaceContext, surfaceInteractionPublication } = useAgentInteraction();
  const hasSharedEditSave = (surfaceInteractionPublication?.editCommands ?? []).some(
    (command) => command.id === BUILD_DOCUMENT_SAVE_COMMAND_ID,
  );
  const slots = useBuildMarkdownCanvasSlots({ hideFooterSave: hasSharedEditSave, hideDraftTools: true });
  const conversationContext = useMemo(() => session.record?.world_id && session.record.content_status === "committed"
    && session.snapshot && isPresentableSourcePhase(session.phase) ? {
      worldId: session.record.world_id, documentId: session.record.document_id,
      revision: session.snapshot.loaded_revision, contentSha256: session.snapshot.content_sha256,
      surfaceInstanceId: `build:${session.record.document_id}`, title: session.record.title, dirty: session.dirty,
    } : null, [session.record, session.snapshot, session.phase, session.dirty]);
  const composeGeneration = useRef({ draft: 0, selection: 0 });
  const composeCurrent = useRef<BuildComposeEditorState | null>(null);
  const composeChanged = useRef(session.handleEditorUpdate);
  composeChanged.current = session.handleEditorUpdate;
  composeCurrent.current = conversationContext && session.editor ? {
    editor: session.editor, worldId: conversationContext.worldId, documentId: conversationContext.documentId,
    revision: conversationContext.revision, contentSha256: conversationContext.contentSha256,
    visibility: session.record?.visibility_state === "player_safe" ? "player_safe" : "internal",
    draftGeneration: composeGeneration.current.draft, selectionGeneration: composeGeneration.current.selection,
    canEdit: Boolean(session.lookupAdmission("editable").ok) && !session.activeCommand,
  } : null;
  useEffect(() => {
    const editor = session.editor;
    if (!editor) return;
    const draft = () => { composeGeneration.current.draft++; if (composeCurrent.current?.editor === editor) composeCurrent.current.draftGeneration = composeGeneration.current.draft; };
    const selection = () => { composeGeneration.current.selection++; if (composeCurrent.current?.editor === editor) composeCurrent.current.selectionGeneration = composeGeneration.current.selection; };
    editor.on("update", draft); editor.on("selectionUpdate", selection);
    return () => { editor.off("update", draft); editor.off("selectionUpdate", selection); };
  }, [session.editor]);
  const composeBridge = useMemo(() => createBuildComposeBridge(() => composeCurrent.current,
    editor => composeChanged.current(editor.getJSON(), editor, { programmatic: false })), []);
  const lastAcceptedCampaignRef = useRef<string>("build");
  const [navigationTarget, setNavigationTarget] = useState<BuildSourceNavigationTarget>(
    IDLE_SOURCE_NAVIGATION_TARGET,
  );

  const isPresentable =
    session.record != null
    && session.snapshot != null
    && isPresentableSourcePhase(session.phase);

  useEffect(() => {
    if (session.record?.campaign_id) {
      lastAcceptedCampaignRef.current = session.record.campaign_id;
    }
  }, [session.record?.campaign_id]);

  useEffect(() => {
    const publishNeutral = (ambientSummary: string) => {
      rehydrateScope({
        campaignId: lastAcceptedCampaignRef.current || "build",
        sessionNumber: null,
        surfaceId: "build",
        documentId: null,
      });
      publishSurfaceContext({
        surfaceId: "build",
        label: BUILD_SURFACE_LABEL,
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary,
        sourceEnvelope: null,
        updatedAt: new Date().toISOString(),
      });
    };

    if (session.phase === "unloaded" || session.phase === "loading") {
      publishNeutral("Loading worldbuilding source…");
      return;
    }

    if (session.phase === "load_error") {
      publishNeutral(BUILD_AUTHORITY_REJECTION_AMBIENT);
      return;
    }

    // No accepted record (including conflict after quarantined snapshot) must not
    // retain a prior UUID/path/hash in Agent Interaction.
    if (!session.record) {
      publishNeutral(
        session.phase === "conflict"
          ? "Document reconciliation required"
          : "Build surface idle",
      );
      return;
    }

    rehydrateScope({
      campaignId: session.record.campaign_id,
      sessionNumber: null,
      surfaceId: "build",
      documentId: session.record.document_id,
    });
    const contentStatus = session.record.content_status;
    const loadedRevision = session.snapshot?.loaded_revision ?? session.record.revision;
    const contentSha = session.snapshot?.content_sha256 ?? null;
    publishSurfaceContext({
      surfaceId: "build",
      label: `${BUILD_SURFACE_LABEL} · ${session.record.title}`,
      campaignId: session.record.campaign_id,
      documentId: session.record.document_id,
      sessionNumber: null,
      ambientSummary: [
        session.record.document_class ?? "worldbuilding source",
        `rev ${loadedRevision}`,
        session.dirty ? "local dirty" : "local clean",
        contentStatus === "committed" ? "durable committed" : "durable draft",
        `phase ${session.phase}`,
      ].join(" · "),
      sourceEnvelope: {
        schema: "agent_interaction_source_envelope_v1",
        artifactRefs: [
          { kind: "workspace_document", value: session.record.document_id },
          ...(session.record.target_relpath
            ? [{ kind: "path" as const, value: session.record.target_relpath }]
            : []),
        ],
        provenanceSummary: [
          `revision=${loadedRevision}`,
          contentSha ? `content_sha256=${contentSha}` : null,
          `dirty=${session.dirty ? "true" : "false"}`,
          `content_status=${contentStatus}`,
          `phase=${session.phase}`,
        ].filter(Boolean).join("; "),
        warnings: session.error ? [session.error] : [],
      },
      updatedAt: new Date().toISOString(),
    });
  }, [
    session.dirty,
    session.error,
    session.phase,
    session.record,
    session.snapshot?.content_sha256,
    session.snapshot?.loaded_revision,
    publishSurfaceContext,
    rehydrateScope,
  ]);

  // Leaving Build (or remounting for a new documentId) must not leave prior accepted context.
  useEffect(() => {
    return () => {
      rehydrateScope({
        campaignId: lastAcceptedCampaignRef.current || "build",
        sessionNumber: null,
        surfaceId: "build",
        documentId: null,
      });
      publishSurfaceContext({
        surfaceId: "build",
        label: BUILD_SURFACE_LABEL,
        campaignId: null,
        documentId: null,
        sessionNumber: null,
        ambientSummary: "Build surface idle",
        sourceEnvelope: null,
        updatedAt: new Date().toISOString(),
      });
    };
  }, [publishSurfaceContext, rehydrateScope]);

  const sourceNavigationQuery = parseBuildSourceNavigationQuery(window.location.search);
  const acceptedDocumentId = session.record?.document_id ?? null;
  const savedContentSha256 = session.snapshot?.content_sha256 ?? null;

  useEffect(() => {
    if (!sourceNavigationQuery) {
      setNavigationTarget(IDLE_SOURCE_NAVIGATION_TARGET);
      return;
    }

    const targetKey = `${sourceNavigationQuery.sourceArtifactId}:${sourceNavigationQuery.sourceSpanRefId}`;
    if (!acceptedDocumentId) {
      setNavigationTarget({ status: "pending", targetKey });
      return;
    }

    let cancelled = false;
    setNavigationTarget({ status: "pending", targetKey });

    void getBuildSourceNavigation(sourceNavigationQuery)
      .then((result) => {
        if (cancelled) return;

        const resolvedTargetKey = `${result.sourceArtifactId}:${result.sourceSpanRefId}`;
        if (result.documentId !== acceptedDocumentId) {
          setNavigationTarget({
            status: "document_mismatch",
            message:
              result.message
              || "This source passage belongs to a different Build document than the one currently open.",
            targetKey: resolvedTargetKey,
          });
          return;
        }

        const digestMatchesSaved =
          savedContentSha256 != null
          && result.currentContentSha256 === result.artifactContentSha256
          && savedContentSha256 === result.currentContentSha256;

        if (result.status === "stale" || !result.canHighlight || !digestMatchesSaved) {
          setNavigationTarget({
            status: "stale",
            message:
              result.message
              || "Source has changed since this evidence was admitted. The cited line range cannot be highlighted exactly.",
            targetKey: resolvedTargetKey,
          });
          return;
        }

        setNavigationTarget({
          status: "exact",
          startLine: result.startLine,
          endLine: result.endLine,
          targetKey: resolvedTargetKey,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setNavigationTarget({
          status: "error",
          message: error instanceof Error ? error.message : "Source navigation could not be resolved.",
          targetKey,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [
    acceptedDocumentId,
    savedContentSha256,
    sourceNavigationQuery?.sourceArtifactId,
    sourceNavigationQuery?.sourceSpanRefId,
  ]);

  // Document-backed graph context must wait for an accepted record. While the
  // document is loading, conflicted, or rejected, session.record is null — mounting
  // then would skip scope admission and race a later rejection.
  const graphPointer = parseBuildGraphPointerFromLocation();
  const acceptedDocumentCampaignId = session.record?.campaign_id ?? null;

  const editSlots: MarkdownCanvasSlots = {
    ...slots,
    // Outer shell owns build-surface-shell when presentable; avoid nested duplicate.
    dataTestId: "build-surface-editor-shell",
    className: "build-surface-editor-shell",
  };

  const projection = (
    <div className="build-surface-with-graph-context document-projection" data-document-surface="build">
      {graphPointer && acceptedDocumentCampaignId ? (
        <BuildGraphObjectContext
          documentCampaignId={acceptedDocumentCampaignId}
          requireDocumentScope
        />
      ) : null}
      {!isPresentable ? (
        <MarkdownCanvas slots={slots} />
      ) : (
        <BuildPresentableSourceView
          key={session.record!.document_id}
          session={session}
          editSlots={editSlots}
          navigationTarget={navigationTarget}
          composeBridge={composeBridge}
          onEditorTools={onEditorTools}
        />
      )}
    </div>
  );
  return <div className="build-workspace-projection">
    <DocumentConversationDock surface="build" contextLabel={session.record?.title ?? "Worldbuilding source"} reader={projection}>
      {hosts => <BuildConversationBinding source={conversationContext} hosts={hosts} composeBridge={composeBridge} />}
    </DocumentConversationDock>
  </div>;
}
