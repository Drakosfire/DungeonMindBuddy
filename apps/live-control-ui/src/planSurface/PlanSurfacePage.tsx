import {useStatblockWorkbenchProjection,STATBLOCK_WORKBENCH_TOOL,STATBLOCK_WORKBENCH_PROJECTION} from '../statblocks/statblockWorkbenchProjection';
import {useTourNavigationOwner,useTourNavigationGuard,useTourNavigationRegistry} from '../guidedTour/Navigation';
import {planPin as guidedPlanPin} from '../guidedTour/ownerPins';
import {useGuidedTour} from '../guidedTour/GuidedTour';
import {TourImageProvider,collectTourMediaAssets} from '../guidedTour/ImageObservations';
import {planPin} from '../guidedTour/ownerPins';
import {PlanTourObservation,type TourPlanSave} from '../guidedTour/OwnerObservations';
import {capturePlanPlacementCatalog} from './agentEdit/planPlacementCatalog';
import {readPlanAuthoringReview,type PlanReviewApplication} from "../api/planAuthoringReviewApi";
import {SurfaceContextPopover} from '../surfaceInteraction/contextHost';
import {SceneEncounterLauncher} from '../combat/SceneEncounterLauncher';
import {deferredComponent} from '../ui/deferredComponent';
import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import { readPlanScenePosition, writePlanScenePosition } from "./planScenePosition";
import {COMBAT_TOOL, COMBAT_PROJECTION, useCombatProjection} from "../combat/combatProjection";
import { useSurfaceImageStudio } from "../shared/useSurfaceImageStudio";
import { CardSceneNavigation } from "../shared/CardSceneNavigation";
import { PlanCardEditing, exportPlanCardMarkdown, planCardRange, planCardSelectionAllowed, setPlanCardScope } from "./planCardEditing";
import { PlanCardDeck } from "./components/PlanCardDeck";
import { SurfaceNavbarIconButton } from "../surfaceInteraction/contextHost/SurfaceNavbarIconButton";
import { useWorkspaceInventoryVersion } from "../workspaceLifecycle/workspaceInventoryChange";
import { clearTrashedPlanRecovery } from "./clearTrashedPlanRecovery";
import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { preserveLeadingYamlFrontmatter, splitLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
import { insertPlanStructure, planStructureActions, promotePlanHeading } from "./planPlayableAuthoring";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import {
  commitWorldOwnedPlanMarkdownWrite,
  createWorldOwnedPlan,
  getManagedWorldPlanContext,
  LiveApiError,
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedPlanSnapshot,
  listWorldOwnedPlans,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorldOwnedPlanRecordV2, WorldOwnedPlanSnapshotV2 } from "../api/types";
import { DurableSaveStatus, type DurableSaveState } from "../components/DurableSaveStatus";
import { DocumentImageStudio } from "../media/DocumentImageStudio";
import { createDocumentMediaBridge, type DocumentMediaState } from "../media/documentMediaBridge";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { PlanMarkdownSource } from "./components/PlanMarkdownSource";
import { defaultMarkdownDocumentAdapter } from "../tiptap/MarkdownDocumentAdapter";
import { AppChrome } from "../chrome/AppChrome";
import { SurfaceWorldPicker } from "../shared/SurfaceWorldPicker";
import { markdownToTiptapDoc, type MarkdownImportDiagnostic } from "../tiptap/markdown/markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "../tiptap/markdown/semanticMarkdownSafety";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { isCanonicalUuid, CANONICAL_SHA256_RE } from "../playSurface/runbook/nativeRunbookProjection";
import { WorldPlanSurfaceContext } from "./components/PlanSurfaceContext";
import {
  useWorldPlanGraphReferenceActivation,
  WorldPlanGraphReferenceActivationProvider,
} from "./components/WorldPlanGraphReferenceActivation";
import { PlanSurfaceCanvasFrame } from "./components/PlanSurfaceCanvas";
import { PlanConversationDockAdapter } from "./components/PlanConversationDockAdapter";
import { WorldPlanConversationRegistration } from "../agentInteraction/WorldAgentConversation";
import {
  buildWorldPlanCardProjectionModel,
  flattenNodes,
  WorldPlanCardProjection,
  worldPlanCardTargetKey,
  worldPlanCardTargetKeys,
  type WorldPlanCardBasis,
  type WorldPlanCardTarget,
  type WorldPlanCardNode,
} from "./components/WorldPlanCardProjection";
import "./components/WorldPlanCardProjection.css";
import {
  applyWorldPlanEditProposal,
  captureWorldPlanEditTarget,
  captureWorldPlanAuthoringTarget,
  sealWorldPlanAuthoringTarget,
  restorePlanAuthoringTarget,
  preparePlanAuthoringApplication,
  previewWorldPlanEditProposal,
  restoreWorldPlanSelection,
  type WorldPlanEditBridge,
  type WorldPlanEditEditorState,
} from "./agentEdit/planAgentEditProposal";
import { toAppChromeToolsGeneration, type MarkdownEditorToolbarModel } from "../tiptap/MarkdownEditorToolbar";
import { CALLOUT_KINDS, defaultCalloutLabel } from "../tiptap/markdown/calloutMarkdown";
import { SemanticMarkdownPaste } from "../tiptap/extensions/SemanticMarkdownPaste";
import { RULES_LOOKUP_TOOL, RULES_LOOKUP_PROJECTION, useRulesLookupProjection } from '../rulesLookup/rulesLookupProjection';
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { buildWorldPlanSurfaceIdentity, createWorldPlanLocalDraftId, worldPlanWorkObject } from "./worldPlanIdentity";
import "../tiptap/prepMarkdownThemes.css";
import "../tiptap/tiptapSpike.css";

type LoadStatus = "loading" | "ready" | "error";

type SelectedWorldPlanPlayableTarget = {
  target: WorldPlanCardTarget;
  worldId: string;
  documentId: string;
  revision: number;
  contentSha256: string;
  stale: boolean;
};

type SelectedWorldPlanPlayableEditTarget = {
  target: WorldPlanCardTarget;
  worldId: string;
  documentId: string;
  revision: number;
  contentSha256: string;
  generation: number;
  stale: boolean;
};

const DeferredSessionStart=deferredComponent(()=>import('../playSurface/StartRunPanel').then(module=>({default:module.StartRunPanel})),'Start session');

function markdownFidelityWarnings(
  importDiagnostics: readonly MarkdownImportDiagnostic[],
  editorDocument: JSONContent,
): string[] {
  const importWarnings = importDiagnostics
    .filter((diagnostic) => diagnostic.level === "warning")
    .map((diagnostic) => `${diagnostic.line != null ? `Line ${diagnostic.line}: ` : ""}${diagnostic.message}`);
  let serializationWarnings: string[];
  try {
    serializationWarnings = semanticMarkdownSerializationDiagnostics(editorDocument)
      .map((diagnostic) => diagnostic.message);
  } catch {
    serializationWarnings = ["The editor could not verify this document's Markdown serialization safely."];
  }
  return [...new Set([...importWarnings, ...serializationWarnings])];
}

function markdownFidelityDetails(warnings: readonly string[]): string {
  const details = warnings.slice(0, 4).map((warning) => `• ${warning}`).join(" ");
  const remainder = warnings.length > 4 ? ` ${warnings.length - 4} more issue(s) are not shown.` : "";
  return `${details}${remainder}`;
}

function markdownFidelityWarningText(warnings: readonly string[]): string {
  return `This Plan contains Markdown the editor cannot safely preserve. Visual editing and autosave are paused to protect the saved text. Use Markdown to resolve these constructs; the original and local recovery copy remain unchanged. ${markdownFidelityDetails(warnings)}`;
}

function markdownFidelityRejectionText(warnings: readonly string[]): string {
  return `This edit was reverted to protect the saved Plan. The editor was restored from the last safe Markdown, and the saved text and local recovery copy are unchanged. ${markdownFidelityDetails(warnings)}`;
}

async function verifyGuidedPlanSelection(snapshot:WorldOwnedPlanSnapshotV2,pin:import('../guidedTour/protocol').TargetPin){
 const committed=await getWorldOwnedPlanCommittedRevision(pin.objectId);
 if(pin.kind!=='plan'||!pin.revisionId||snapshot.record.world_id!==pin.worldId||snapshot.record.document_id!==pin.objectId
  ||snapshot.loaded_revision!==committed.object_revision||snapshot.content_sha256!==pin.digest
  ||committed.schema_version!=='dmb_workspace_committed_revision_v2'||committed.scope_mode!=='world'||committed.world_id!==pin.worldId||committed.document_id!==pin.objectId
  ||committed.kind!=='plan'||committed.campaign_id!==null||committed.status!=='active'||committed.has_divergent_working_copy
  ||committed.revision_n!==pin.revision||committed.work_revision_id!==pin.revisionId||committed.content_sha256!==pin.digest)
  throw new Error('The exact bound Plan version is unavailable. Your current Plan and draft were retained.');
}

export function PlanSurfacePage() {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  if (selectedWorld.kind === "loading") {
    return <AppChrome activeRoute="plan"><main className="app-status"><p>Resolving selected World…</p></main></AppChrome>;
  }
  if (selectedWorld.kind === "error") {
    return <AppChrome activeRoute="plan"><main className="app-status app-error"><h1>Plan</h1><p>{selectedWorld.message}</p></main></AppChrome>;
  }
  if (managedWorldId) return (
    <WorldPlanGraphReferenceActivationProvider worldId={managedWorldId}>
      <WorldOwnedPlanPage key={managedWorldId} worldId={managedWorldId} worldName={selectedWorld.kind === "managed" ? selectedWorld.name : managedWorldId} />
    </WorldPlanGraphReferenceActivationProvider>
  );

  return (
    <AppChrome activeRoute="plan">
      <main className="app-status plan-world-entry" aria-label="Plan workspace">
        <h1>Plan your next session</h1>
        <SurfaceWorldPicker surface="plan" />
      </main>
    </AppChrome>
  );
}

interface WorldPlanLocalDraftV2 {
  schema_version: "dmb_plan_promotion_recovery_v2";
  scope_mode: "world";
  world_id: string;
  document_id: string | null;
  local_draft_id?: string | null;
  title: string;
  markdown: string;
  revision: number | null;
  edit_generation?: number;
  create_uncertain?: boolean;
  uncertain_create_draft?: {
    title: string;
    markdown: string;
    edit_generation: number;
    bound_document_id?: string | null;
  } | null;
  pending_write?: {
    phase: "prepare" | "commit";
    base_revision: number;
    prepared_revision: number | null;
    base_markdown: string;
    markdown: string;
    title?: string;
    base_title?: string;
    edit_generation: number;
  } | null;
}

interface PlanApplicationHold {world_id:string;document_id:string;action_id:string;application_id:string}
function planApplicationHoldPrefix(world:string,document:string){
  return `dmb:plan-application-hold:v1:${encodeURIComponent(world)}:${encodeURIComponent(document)}:`;
}
function planApplicationHoldKey(hold:PlanApplicationHold){
  return `${planApplicationHoldPrefix(hold.world_id,hold.document_id)}${encodeURIComponent(hold.action_id)}:${encodeURIComponent(hold.application_id)}`;
}
// Each pending application has its own immutable pointer. Document navigation and
// ordinary draft persistence cannot erase another application's recovery fence.
function readPlanApplicationHold(world:string,document:string|null):unknown {
  if(!document)return null;
  const prefix=planApplicationHoldPrefix(world,document),values:unknown[]=[];
  try {
    for(let i=0;i<localStorage.length;i++){
      const key=localStorage.key(i);if(!key?.startsWith(prefix))continue;
      const value=JSON.parse(localStorage.getItem(key)!);
      if(!value||value.world_id!==world||value.document_id!==document||planApplicationHoldKey(value)!==key)return {conflict:true};
      values.push(value);
    }
  } catch {return {unavailable:true};}
  return values.length===0?null:values.length===1?values[0]:{conflict:true};
}
async function retainPlanApplicationHold(hold:PlanApplicationHold){
  if(!navigator.locks)throw new Error('This browser cannot coordinate application recovery between tabs. Nothing was inserted.');
  await navigator.locks.request(planApplicationHoldPrefix(hold.world_id,hold.document_id),()=>{
    if(readPlanApplicationHold(hold.world_id,hold.document_id)!==null)
      throw new Error('Resolve the pending application for this Plan before applying another.');
    const key=planApplicationHoldKey(hold),bytes=JSON.stringify(hold);
    localStorage.setItem(key,bytes);
    if(localStorage.getItem(key)!==bytes)throw new Error('The application recovery hold could not be retained. Nothing was inserted.');
  });
}
function clearPlanApplicationHold(hold:PlanApplicationHold){
  const key=planApplicationHoldKey(hold),bytes=localStorage.getItem(key);
  if(bytes===null)return;
  if(bytes!==JSON.stringify(hold))throw new Error('The application hold changed and was preserved.');
  localStorage.removeItem(key);
  if(localStorage.getItem(key)!==null)throw new Error('The resolved application hold could not be cleared.');
}

function worldPlanLocalDraftKey(worldId: string): string {
  return `dmb:world-plan-local-draft:v2:${worldId}`;
}

function readWorldPlanLocalDraft(worldId: string): WorldPlanLocalDraftV2 | null {
  try {
    const raw = localStorage.getItem(worldPlanLocalDraftKey(worldId));
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<WorldPlanLocalDraftV2>;
    if (value.schema_version !== "dmb_plan_promotion_recovery_v2" || value.scope_mode !== "world"
      || value.world_id !== worldId || typeof value.title !== "string" || typeof value.markdown !== "string") return null;
    const documentId = typeof value.document_id === "string" ? value.document_id : null;
    const existingLocalId = typeof value.local_draft_id === "string"
      && value.local_draft_id.startsWith(`local-plan:${worldId}:`)
      ? value.local_draft_id : null;
    const localDraftId = existingLocalId ?? (documentId === null ? createWorldPlanLocalDraftId(worldId) : null);
    const draft: WorldPlanLocalDraftV2 = {
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: documentId,
      local_draft_id: localDraftId,
      title: value.title,
      markdown: value.markdown,
      revision: typeof value.revision === "number" ? value.revision : null,
      edit_generation: typeof value.edit_generation === "number" ? value.edit_generation : 0,
      create_uncertain: value.create_uncertain === true,
      uncertain_create_draft: value.uncertain_create_draft
        && typeof value.uncertain_create_draft === "object"
        && typeof value.uncertain_create_draft.title === "string"
        && typeof value.uncertain_create_draft.markdown === "string"
        && typeof value.uncertain_create_draft.edit_generation === "number"
        ? {
          title: value.uncertain_create_draft.title,
          markdown: value.uncertain_create_draft.markdown,
          edit_generation: value.uncertain_create_draft.edit_generation,
          bound_document_id: typeof value.uncertain_create_draft.bound_document_id === "string"
            ? value.uncertain_create_draft.bound_document_id
            : null,
        }
        : null,
      pending_write: value.pending_write && typeof value.pending_write === "object"
        && (value.pending_write.phase === "prepare" || value.pending_write.phase === "commit")
        && typeof value.pending_write.base_revision === "number"
        && typeof value.pending_write.base_markdown === "string"
        && typeof value.pending_write.markdown === "string"
        && typeof value.pending_write.edit_generation === "number"
        ? {
          phase: value.pending_write.phase,
          base_revision: value.pending_write.base_revision,
          prepared_revision: typeof value.pending_write.prepared_revision === "number"
            ? value.pending_write.prepared_revision
            : null,
          base_markdown: value.pending_write.base_markdown,
          markdown: value.pending_write.markdown,
          ...("title" in value.pending_write ? {title: typeof value.pending_write.title === "string" ? value.pending_write.title : ""} : {}),
          ...("base_title" in value.pending_write ? {base_title: typeof value.pending_write.base_title === "string" ? value.pending_write.base_title : ""} : {}),
          edit_generation: value.pending_write.edit_generation,
        }
        : null,
    };
    return draft;
  } catch {
    return null;
  }
}

function persistWorldPlanLocalDraft(
  worldId: string,
  draft: Pick<WorldPlanLocalDraftV2, "document_id" | "title" | "markdown" | "revision">
    & Partial<Pick<WorldPlanLocalDraftV2, "local_draft_id" | "edit_generation" | "create_uncertain" | "uncertain_create_draft" | "pending_write">>,
): void {
  try {
    const previous = readWorldPlanLocalDraft(worldId);
    const uncertainCreateDraft = Object.hasOwn(draft, "uncertain_create_draft")
      ? draft.uncertain_create_draft ?? null
      : previous?.uncertain_create_draft ?? null;
    localStorage.setItem(worldPlanLocalDraftKey(worldId), JSON.stringify({
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      local_draft_id: previous?.local_draft_id ?? null,
      edit_generation: 0,
      create_uncertain: false,
      pending_write: null,
      uncertain_create_draft: uncertainCreateDraft,
      ...draft,
    } satisfies WorldPlanLocalDraftV2));
  } catch {
    // Browser-local recovery is best effort; durable Save remains server-owned.
  }
}

function worldPlanCardBasisFromSnapshot(
  snapshot: WorldOwnedPlanSnapshotV2,
  hasPendingWrite = false,
): WorldPlanCardBasis {
  if (hasPendingWrite) return { status: "unavailable" };
  if (snapshot.record.content_status === "committed") {
    return {
      status: "verified",
      revision: snapshot.loaded_revision,
      contentSha256: snapshot.content_sha256,
    };
  }
  if (snapshot.record.content_status === "draft") return { status: "server-draft" };
  return { status: "unavailable" };
}

function durableTimestamp(value: string | null | undefined): string | null {
  return value && Number.isFinite(Date.parse(value)) ? value : null;
}

function WorldOwnedPlanPage({ worldId, worldName }: { worldId: string; worldName: string }) {
 const guidance=useGuidedTour();
 const tourNavigation=useTourNavigationRegistry();
  const { activateNode } = useWorldPlanGraphReferenceActivation();
  const [localDraft] = useState(() => {
    const existing = readWorldPlanLocalDraft(worldId);
    const requestedDocumentId = new URLSearchParams(window.location.search).get("documentId")?.trim();
    if (existing || requestedDocumentId) return existing;
    const fresh: WorldPlanLocalDraftV2 = {
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: null,
      local_draft_id: createWorldPlanLocalDraftId(worldId),
      title: "Plan",
      markdown: "",
      revision: null,
    };
    persistWorldPlanLocalDraft(worldId, fresh);
    return fresh;
  });
  const [initialDocumentId] = useState(() =>
    new URLSearchParams(window.location.search).get("documentId")?.trim() || localDraft?.document_id || null,
  );
  const initialLocalDraft = localDraft?.document_id === initialDocumentId ? localDraft : null;
  const [records, setRecords] = useState<WorldOwnedPlanRecordV2[]>([]);
  const [documentId, setDocumentId] = useState<string | null>(initialDocumentId);
  const [localDraftId, setLocalDraftId] = useState(() => initialLocalDraft?.local_draft_id ?? createWorldPlanLocalDraftId(worldId));
  const [title, setTitle] = useState(initialLocalDraft?.title ?? "Plan");
  // Accepted visual edits already have a fidelity-validated import. Keep it
  // paired with its exact source in immutable state; every other source write
  // drops the pair, so load/recovery cannot reuse an outgoing document's parse.
  const [markdownState, setMarkdownState] = useState<{
    markdown: string;
    validated?: { editorIdentity: string; imported: ReturnType<typeof markdownToTiptapDoc> };
  }>(() => ({ markdown: initialLocalDraft?.markdown ?? "" }));
  const markdown = markdownState.markdown;
  const setMarkdown = useCallback((value: string) => setMarkdownState({ markdown: value }), []);
  const [sourceEditing, setSourceEditing] = useState(false);
  const sourceEditingRef = useRef(sourceEditing);
  sourceEditingRef.current = sourceEditing;
  const [tourPlanSave,setTourPlanSave]=useState<TourPlanSave|null>(null);
  const [savedBasis, setSavedBasis] = useState<WorldPlanCardBasis>({ status: "unavailable" });
  const [createUncertain, setCreateUncertain] = useState(initialLocalDraft?.create_uncertain ?? false);
  const [uncertainCreateDraft, setUncertainCreateDraft] = useState(localDraft?.uncertain_create_draft ?? null);
  const [recoveryConflict, setRecoveryConflict] = useState(false);
  const [serverDraft, setServerDraft] = useState<{
    title: string;
    markdown: string;
    revision: number;
    contentSha256: string;
    contentStatus: WorldOwnedPlanRecordV2["content_status"];
  } | null>(null);
  const [editorGeneration, setEditorGeneration] = useState(0);
  const [selectionGeneration, setSelectionGeneration] = useState(0);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [routeCardsViewRequested, setRouteCardsViewRequested] = useState(
    () => new URLSearchParams(window.location.search).get("view") === "cards",
  );
  const [selectedCardViewIdentity, setSelectedCardViewIdentity] = useState<string | null>(null);
  const [sceneNavigation, setSceneNavigation] = useState<{ identity: string; sceneId: string | null } | null>(null);
  const [documentSceneJump, setDocumentSceneJump] = useState<{ identity: string; sceneId: string } | null>(null);
  const [sceneNavigationNotice, setSceneNavigationNotice] = useState<{ identity: string; message: string } | null>(null);
  const [selectedPlayableTarget, setSelectedPlayableTarget] = useState<SelectedWorldPlanPlayableTarget | null>(null);
  const selectedPlayableTargetRef=useRef(selectedPlayableTarget);selectedPlayableTargetRef.current=selectedPlayableTarget;
  const [selectedPlayableEditTarget, setSelectedPlayableEditTarget] = useState<SelectedWorldPlanPlayableEditTarget | null>(null);
  const [playableEditTargetGeneration, setPlayableEditTargetGeneration] = useState(0);
  const editorIdentity = `${worldId}:${documentId ?? localDraftId}:${editorGeneration}`;
  const importedMarkdown = useMemo(() => {
    const accepted = markdownState.validated;
    return accepted?.editorIdentity === editorIdentity
      ? accepted.imported
      : markdownToTiptapDoc(markdownState.markdown);
  }, [markdownState, editorIdentity]);
  const editorContent = importedMarkdown.doc;
  const fidelityWarnings = useMemo(
    () => markdownFidelityWarnings(importedMarkdown.diagnostics, editorContent),
    [importedMarkdown, editorContent],
  );
  const fidelityBlocked = fidelityWarnings.length > 0;
  const trashInventoryVersion = useWorkspaceInventoryVersion(worldId);
  useEffect(() => {
    if (trashInventoryVersion === 0) return;
    let cancelled = false;
    void listWorldOwnedPlans(worldId).then(result => { if (!cancelled) setRecords(result.records); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [worldId, trashInventoryVersion]);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [initialLoadAttempt, setInitialLoadAttempt] = useState(0);
  const [retryTarget, setRetryTarget] = useState<
    { kind: "initial" } | { kind: "document"; documentId: string } | null
  >(null);
  const [saving, setSaving] = useState(false);
  const [autoSavePaused, setAutoSavePaused] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [startingPlay, setStartingPlay] = useState(false);
  const [startPlayError, setStartPlayError] = useState<string | null>(null);
  const planVerificationRequestRef = useRef(0);
  const tourPlanVerificationAttemptRef = useRef<string | null>(null);
  const [tourVerifiedPlan,setTourVerifiedPlan]=useState<{documentId:string;worldId:string;objectRevision:number;pin:{revisionN:number;workRevisionId:string;contentSha256:string};assetIds:string[]}|null>(null);
  const [sessionStart,setSessionStart]=useState<{documentId:string;worldId:string;pin:{revisionN:number;workRevisionId:string;contentSha256:string};sceneId:string|null}|null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(false);
  const selectionEpochRef = useRef(0);
  const documentIdRef = useRef(initialDocumentId);
  const localDraftIdRef = useRef(localDraftId);
  const revisionRef = useRef<number | null>(initialLocalDraft?.revision ?? null);
  const titleRef = useRef(initialLocalDraft?.title ?? "Plan");
  const markdownRef = useRef(initialLocalDraft?.markdown ?? "");
  const serverDigestRef = useRef<string | null>(null);
  const editGenerationRef = useRef(initialLocalDraft?.edit_generation ?? 0);
  const selectionGenerationRef = useRef(0);
  const selectedPlayableEditTargetRef = useRef<SelectedWorldPlanPlayableEditTarget | null>(null);
  const playableEditTargetGenerationRef = useRef(0);
  const playableEditTargetStaleRef = useRef(false);
  selectedPlayableEditTargetRef.current = selectedPlayableEditTarget;
  const pendingWriteRef = useRef(initialLocalDraft?.pending_write ?? null);
  const [initialAuthoringHold]=useState(()=>readPlanApplicationHold(worldId,initialDocumentId));
  const authoringHoldRef=useRef<unknown>(initialAuthoringHold);
  const uncertainCreateDraftRef = useRef(localDraft?.uncertain_create_draft ?? null);
  const savingRef = useRef(false);
  const startPlayRequestRef = useRef(0);
  const statusRef = useRef(status);
  statusRef.current = status;
  const switchingDocumentRef = useRef(false);
  const serverTitleRef = useRef("");
  const serverMarkdownRef = useRef("");
  const editorRef = useRef<Editor | null>(null);
  const getLiveFidelityWarnings = useCallback((editorDocument?: JSONContent) => {
    const currentMarkdown = markdownRef.current;
    const currentImport = currentMarkdown === markdown
      ? importedMarkdown
      : markdownToTiptapDoc(currentMarkdown);
    return markdownFidelityWarnings(
      currentImport.diagnostics,
      editorDocument ?? editorRef.current?.getJSON() ?? currentImport.doc,
    );
  }, [importedMarkdown, markdown]);
  const workObject = useMemo(() => worldPlanWorkObject({ worldId, documentId, localDraftId }), [worldId, documentId, localDraftId]);
  const surfaceIdentity = useMemo(() => buildWorldPlanSurfaceIdentity({ worldId, documentId, localDraftId }), [worldId, documentId, localDraftId]);
  const activePublication = useMemo<SurfaceInteractionPublication | null>(() => status === "ready" ? {
    surfaceId: "plan",
    label: "World Plan",
    identity: surfaceIdentity,
    canvas: {
      canvasId: "markdown-canvas",
      workObject,
    },
    agentContext: null,
    tools: [RULES_LOOKUP_TOOL, COMBAT_TOOL,STATBLOCK_WORKBENCH_TOOL],
    editCommands: [],
    projections: [RULES_LOOKUP_PROJECTION, COMBAT_PROJECTION,STATBLOCK_WORKBENCH_PROJECTION],
    projectionBindings: [],
  } : null, [status, surfaceIdentity, workObject]);
  usePublishSurfaceInteraction(activePublication);
  useRulesLookupProjection("plan", activePublication !== null);


  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const selectedViewIsCurrent = (epoch: number, expectedDocumentId: string | null) =>
    mountedRef.current
    && selectionEpochRef.current === epoch
    && documentIdRef.current === expectedDocumentId;

  const navigationIdentity = `${worldId}:${documentId ?? localDraftId}:${selectionEpochRef.current}`;
  const editorIdentityRef = useRef(editorIdentity);
  editorIdentityRef.current = editorIdentity;
  const isCurrentEditTarget = useMemo(() => {
    const epoch = selectionEpochRef.current;
    return (allowDuringSave = false) => mountedRef.current
      && !switchingDocumentRef.current
      && selectionEpochRef.current === epoch
      && documentIdRef.current === documentId
      && localDraftIdRef.current === localDraftId
      && editorIdentityRef.current === editorIdentity
      && statusRef.current === "ready"
      && (allowDuringSave || !savingRef.current);
  }, [documentId, localDraftId, editorIdentity]);
  const setCurrentEditor = (next: Editor | null) => {
    editorRef.current = next;
    setEditor(next);
  };

  useLayoutEffect(() => {
    if (!editor) return;
    const onSelectionUpdate = () => {
      selectionGenerationRef.current += 1;
      setSelectionGeneration(selectionGenerationRef.current);
    };
    editor.on("selectionUpdate", onSelectionUpdate);
    return () => { editor.off("selectionUpdate", onSelectionUpdate); };
  }, [editor]);

  const worldEditStateGetterRef = useRef<(applicationId?:string) => WorldPlanEditEditorState>(() => ({
    editor: null,
    documentId: null,
    worldId,
    baseRevision: null,
    baseContentSha256: null,
    sourceMarkdown: "",
    draftGeneration: 0,
    selectionGeneration: 0,
    playableTarget: null,
    playableTargetGeneration: 0,
    playableTargetStale: false,
    canEdit: false,
  }));
  worldEditStateGetterRef.current = (applicationId) => ({
    editor: editorRef.current,
    documentId: documentIdRef.current,
    worldId,
    baseRevision: revisionRef.current,
    baseContentSha256: serverDigestRef.current,
    sourceMarkdown: markdownRef.current,
    draftGeneration: editGenerationRef.current,
    selectionGeneration: selectionGenerationRef.current,
    playableTarget: selectedPlayableEditTargetRef.current?.target ?? null,
    playableTargetGeneration: playableEditTargetGenerationRef.current,
    playableTargetStale: playableEditTargetStaleRef.current,
    currentSceneTarget: selectedPlayableTargetRef.current?.target.kind === "scene" ? selectedPlayableTargetRef.current.target : null,
    currentSceneTargetStale: selectedPlayableTargetRef.current!==null&&selectedPlayableTargetStale,
    currentSceneTargetLabel: cardTargetLabel(selectedPlayableTargetRef.current?.target ?? null),
    playableTargetLabel: cardTargetLabel(selectedPlayableEditTargetRef.current?.target ?? null),
    canEdit: Boolean(
      !sourceEditingRef.current
      && documentIdRef.current
      && serverDigestRef.current
      && isCurrentEditTarget()
      && !savingRef.current
      && !createUncertain
      && !recoveryConflict
      && pendingWriteRef.current === null
      && (authoringHoldRef.current === null || (applicationId !== undefined
        && typeof authoringHoldRef.current === 'object' && authoringHoldRef.current !== null
        && 'application_id' in authoringHoldRef.current && authoringHoldRef.current.application_id === applicationId))
      && getLiveFidelityWarnings(editorRef.current?.getJSON()).length === 0
    ),
  });
  const authoringMoveCaptureRef=useRef<NonNullable<WorldPlanEditBridge['captureAuthoringAt']>>(async()=>{throw new Error('Plan placement owner unavailable');});
  const authoringSaveRef=useRef<NonNullable<WorldPlanEditBridge['saveAuthoring']>>(async()=>{throw new Error('Plan Save owner unavailable');});
  const authoringReconcileRef=useRef<NonNullable<WorldPlanEditBridge['reconcileAuthoring']>>(async()=>{throw new Error('Plan recovery owner unavailable');});
  const authoringAckRef=useRef<(application:PlanReviewApplication)=>Promise<void>>(async()=>{throw new Error('Plan Save receipt owner unavailable');});
  const worldPlanEditBridge = useMemo<WorldPlanEditBridge>(() => ({
    captureAuthoring: (identity,applicationId) => captureWorldPlanAuthoringTarget(
      worldEditStateGetterRef.current(applicationId), () => worldEditStateGetterRef.current(applicationId), identity,
    ),
    sealAuthoring:sealWorldPlanAuthoringTarget,
    capturePlacementCatalog:(target,capture)=>capturePlanPlacementCatalog(target.editor,capture),
    captureAuthoringAt:(...args)=>authoringMoveCaptureRef.current(...args),
    restoreAuthoring:(capture,identity)=>restorePlanAuthoringTarget(capture,
      worldEditStateGetterRef.current(),()=>worldEditStateGetterRef.current(),identity),
    prepareAuthoring:(target,markdown,action,expected,binding)=>preparePlanAuthoringApplication(
      target,markdown,action,()=>worldEditStateGetterRef.current(),expected,binding),
    saveAuthoring:(...args)=>authoringSaveRef.current(...args),
    acknowledgeAuthoring:application=>authoringAckRef.current(application),
    reconcileAuthoring:(...args)=>authoringReconcileRef.current(...args),
    authoringTitle:()=>titleRef.current.trim()||'Plan',
    matchesAuthoringAfter:async application=>mountedRef.current&&worldEditStateGetterRef.current().editor!==null
      &&statusRef.current==='ready'&&!switchingDocumentRef.current
      &&application.capture.world_id===worldId&&application.capture.document_id===documentIdRef.current
      &&JSON.stringify(editorRef.current?.getJSON())===application.after_editor_json
      &&markdownRef.current===application.after_markdown&&(titleRef.current.trim()||'Plan')===application.after_title,
    preview: previewWorldPlanEditProposal,
    capture: () => captureWorldPlanEditTarget(
      worldEditStateGetterRef.current(),
      () => worldEditStateGetterRef.current(),
    ),
    restoreSelection: (anchor, draftSha256, selectedTextSha256, expectedBasis, isOriginCurrent) =>
      restoreWorldPlanSelection(anchor, draftSha256, selectedTextSha256, expectedBasis,
        isOriginCurrent, () => worldEditStateGetterRef.current()),
    apply: (captured, admitted, expectedAgentBinding, getAgentBinding) => applyWorldPlanEditProposal({
      captured,
      admitted,
      getCurrent: () => worldEditStateGetterRef.current(),
      expectedAgentBinding,
      getAgentBinding,
    }),
  }), []);

  const structureProtectionRef = useRef(false);
  structureProtectionRef.current = sourceEditing || createUncertain || recoveryConflict || pendingWriteRef.current !== null || saving || fidelityBlocked;
  const toolbarModel = useMemo<MarkdownEditorToolbarModel>(() => {
    const action = (id: string, label: string, invoke: (active: Editor) => void, disabled = false) => ({
      id,
      label,
      onClick: () => {
        const active = editorRef.current;
        if (!active || sourceEditingRef.current || !isCurrentEditTarget() || disabled) return;
        const fidelityIssues = getLiveFidelityWarnings(active.getJSON());
        if (fidelityIssues.length) {
          setError(markdownFidelityWarningText(fidelityIssues));
          return;
        }
        invoke(active);
      },
      disabled: sourceEditing || !editor || status !== "ready" || saving || fidelityBlocked || disabled,
    });
    const structureState = editor?.state;
    const structureDraftGeneration = editGenerationRef.current;
    const structureSelectionGeneration = selectionGenerationRef.current;
    const structureActions = planStructureActions(editor);
    const structureProtected = saving || createUncertain || recoveryConflict || pendingWriteRef.current !== null;
    return {
      sections: [
        {
          id: "world-plan-structure",
          title: "Playable structure",
          defaultOpen: true,
          panel: <div><p>Beats contain Scenes. Put the cursor in an ordinary heading to make it playable without rewriting its text.</p>{structureActions.filter(item => item.disabledReason).map(item => <p key={item.kind}>{item.label}: {item.disabledReason}</p>)}</div>,
          actions: structureActions.map(item => ({
            ...action(`world-plan-add-${item.kind}`, item.label, active => {
              if (!structureState || structureProtectionRef.current || !active.isEditable || active.isDestroyed) return;
              try {
                if (structureDraftGeneration !== editGenerationRef.current || structureSelectionGeneration !== selectionGenerationRef.current) throw new Error("The Plan or cursor changed. Choose the structure action again.");
                if(item.operation==='promote')promotePlanHeading(active,item.kind,structureState);
                else insertPlanStructure(active, item.kind, structureState);
                setError(null);
              }
              catch (cause) { setError(cause instanceof Error ? cause.message : "Could not add playable structure."); }
            }, structureProtected || Boolean(item.disabledReason)),
            disabledReason: item.disabledReason ?? undefined,
          })),
        },
        {
          id: "world-plan-format",
          title: "Text",
          defaultOpen: true,
          actions: [
            action("world-plan-bold", "Bold", (active) => { active.chain().focus().toggleBold().run(); }),
            action("world-plan-italic", "Italic", (active) => { active.chain().focus().toggleItalic().run(); }),
            action("world-plan-heading", "Heading", (active) => { active.chain().focus().toggleHeading({ level: 2 }).run(); }),
          ],
        },
        {
          id: "world-plan-blocks",
          title: "Insert blocks",
          defaultOpen: true,
          actions: CALLOUT_KINDS.map((kind) => action(
            `world-plan-insert-${kind}`,
            defaultCalloutLabel(kind),
            (active) => { active.chain().focus().insertCallout({ kind }).run(); },
          )),
        },
      ],
    };
  }, [editor, fidelityBlocked, getLiveFidelityWarnings, isCurrentEditTarget, saving, status, markdown, title, selectionGeneration, createUncertain, recoveryConflict, sourceEditing]);

  useEffect(() => {
    let cancelled = false;
    const destination=initialDocumentId?tourNavigation?.claimDestination('plan',worldId,initialDocumentId):null;
    const assertDestinationCurrent=()=>{if(destination&&!destination.isCurrent())throw new Error("Guided navigation canceled. Choose a Plan explicitly or retry to open it normally.");};
    void (async () => {
      try {
        const context = await getManagedWorldPlanContext(worldId);
        if (context.schema_version !== "dmb_managed_world_plan_context_v2"
          || context.scope_mode !== "world" || context.world_id !== worldId
          || context.campaign_id !== null || context.session !== null) {
          throw new Error("Managed Plan context does not match the selected World.");
        }
        const inventory = await listWorldOwnedPlans(worldId);
        if (inventory.world_id !== worldId) throw new Error("World Plan inventory does not match the selected World.");
        if (cancelled) return;
        setRecords(inventory.records);
        if (initialDocumentId) {
          const snapshot = await getWorldOwnedPlanSnapshot(initialDocumentId);
          if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null || snapshot.record.kind !== "plan") {
            throw new Error("This Plan does not belong to the selected World.");
          }
          assertDestinationCurrent();
          const requestedPin=destination?.pin;
          if(requestedPin)await verifyGuidedPlanSelection(snapshot,requestedPin);
          if (cancelled) return;
          assertDestinationCurrent();
          destination?.complete();
          const recoverLocal = localDraft?.document_id === initialDocumentId;
          setLastSavedAt(snapshot.record.content_status === "committed"
            ? durableTimestamp(snapshot.record.updated_at)
            : null);
          const revisionChangedUnderDraft = recoverLocal
            && localDraft.revision !== snapshot.loaded_revision
            && !localDraft.pending_write;
          const nextTitle = recoverLocal ? localDraft.title : snapshot.record.title;
          const nextMarkdown = recoverLocal ? localDraft.markdown : snapshot.markdown;
          documentIdRef.current = initialDocumentId;
          revisionRef.current = snapshot.loaded_revision;
          titleRef.current = nextTitle;
          markdownRef.current = nextMarkdown;
          serverTitleRef.current = snapshot.record.title;
          serverMarkdownRef.current = snapshot.markdown;
          serverDigestRef.current = snapshot.content_sha256;
          setSavedBasis(worldPlanCardBasisFromSnapshot(snapshot, recoverLocal && Boolean(localDraft.pending_write)));
          pendingWriteRef.current = recoverLocal ? localDraft.pending_write ?? null : null;
          authoringHoldRef.current=readPlanApplicationHold(worldId,initialDocumentId);
          setAutoSavePaused(pendingWriteRef.current !== null || authoringHoldRef.current !== null);
          setTitle(nextTitle);
          setMarkdown(nextMarkdown);
          setEditorGeneration((value) => value + 1);
          if (revisionChangedUnderDraft) {
            setRecoveryConflict(true);
            setServerDraft({
              title: snapshot.record.title,
              markdown: snapshot.markdown,
              revision: snapshot.loaded_revision,
              contentSha256: snapshot.content_sha256,
              contentStatus: snapshot.record.content_status,
            });
            setError("The saved Plan changed since this local draft. Your draft is preserved; choose which version to keep before saving.");
          }
          if (!new URLSearchParams(window.location.search).has("documentId")) {
            const url = new URL(window.location.href);
            url.searchParams.set("world", worldId);
            url.searchParams.set("documentId", initialDocumentId);
            window.history.replaceState({}, "", `${url.pathname}${url.search}`);
          }
          persistWorldPlanLocalDraft(worldId, {
            document_id: initialDocumentId,
            title: nextTitle,
            markdown: nextMarkdown,
            revision: snapshot.loaded_revision,
            edit_generation: initialLocalDraft?.edit_generation ?? 0,
            pending_write: pendingWriteRef.current,
            create_uncertain: false,
          });
        }
        else if (localDraft?.document_id === null) {
          documentIdRef.current = null;
          revisionRef.current = null;
          serverDigestRef.current = null;
          setSavedBasis({ status: "unavailable" });
          persistWorldPlanLocalDraft(worldId, localDraft);
        }
        if (!cancelled) {
          setRetryTarget(null);
          setStatus("ready");
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "World Plan could not be loaded.");
          setRetryTarget({ kind: "initial" });
          setStatus("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, [initialDocumentId, initialLoadAttempt, localDraft, worldId]);

  const openPlan = async (nextDocumentId: string, allowRetry = false, isCurrent:()=>boolean = ()=>true, expectedPin?:import('../guidedTour/protocol').TargetPin) => {
    if(!isCurrent())return;
    if(!expectedPin)tourNavigation?.discardDestination('plan');
    if (savingRef.current || (statusRef.current !== "ready" && !allowRetry)) return;
    const epoch = ++selectionEpochRef.current;
    const priorDocumentId = documentIdRef.current;
    const priorSavedBasis = savedBasis;
    startPlayRequestRef.current += 1;
    setStartingPlay(false);
    setStartPlayError(null);
    // Close the outgoing edit lease before React paints the loading state.
    switchingDocumentRef.current = true;
    setSavedBasis({ status: "unavailable" });
    setLastSavedAt(null);
    editorRef.current?.setEditable(false);
    editorIdentityRef.current = `${worldId}:${nextDocumentId}:${editorGeneration + 1}`;
    editorRef.current = null;
    setEditor(null);
    setStatus("loading");
    setRetryTarget({ kind: "document", documentId: nextDocumentId });
    setError(null);
    try {
      const snapshot = await getWorldOwnedPlanSnapshot(nextDocumentId);
      if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null || snapshot.record.kind !== "plan") {
        throw new Error("This Plan does not belong to the selected World.");
      }
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      if(expectedPin&&isCurrent())await verifyGuidedPlanSelection(snapshot,expectedPin);
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      if(!isCurrent()){
        switchingDocumentRef.current=false;setSavedBasis(priorSavedBasis);setStatus('ready');setEditorGeneration(value=>value+1);
        setError('Guided selection canceled. Your current Plan and draft are retained.');return;
      }
      const preservedUncertainDraft = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
        ?? uncertainCreateDraftRef.current;
      const url = new URL(window.location.href);
      url.searchParams.set("world", worldId);
      url.searchParams.set("documentId", nextDocumentId);
      url.searchParams.delete("view");
      window.history.pushState({}, "", `${url.pathname}${url.search}`);
      setRouteCardsViewRequested(false);
      setSelectedCardViewIdentity(null);
      documentIdRef.current = nextDocumentId;
      revisionRef.current = snapshot.loaded_revision;
      titleRef.current = snapshot.record.title;
      markdownRef.current = snapshot.markdown;
      serverTitleRef.current = snapshot.record.title;
      serverMarkdownRef.current = snapshot.markdown;
      serverDigestRef.current = snapshot.content_sha256;
      setLastSavedAt(snapshot.record.content_status === "committed"
        ? durableTimestamp(snapshot.record.updated_at)
        : null);
      setSavedBasis(worldPlanCardBasisFromSnapshot(snapshot));
      pendingWriteRef.current = null;
      authoringHoldRef.current=readPlanApplicationHold(worldId,nextDocumentId);
      setAutoSavePaused(authoringHoldRef.current!==null);
      uncertainCreateDraftRef.current = preservedUncertainDraft;
      setUncertainCreateDraft(preservedUncertainDraft);
      setDocumentId(nextDocumentId);
      setTitle(snapshot.record.title);
      setMarkdown(snapshot.markdown);
      setEditorGeneration((value) => value + 1);
      setRecoveryConflict(false);
      setServerDraft(null);
      setCreateUncertain(false);
      persistWorldPlanLocalDraft(worldId, {
        document_id: nextDocumentId,
        title: snapshot.record.title,
        markdown: snapshot.markdown,
        revision: snapshot.loaded_revision,
        edit_generation: editGenerationRef.current,
        pending_write: null,
        create_uncertain: false,
      });
      setMessage(null);
      switchingDocumentRef.current = false;
      setRetryTarget(null);
      setStatus("ready");
    } catch (reason) {
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      setError(expectedPin&&!isCurrent()?"Guided selection canceled. Your current Plan and draft were retained.":reason instanceof Error ? reason.message : "Plan could not be opened.");
      if(expectedPin){switchingDocumentRef.current=false;setSavedBasis(priorSavedBasis);setStatus('ready');setEditorGeneration(value=>value+1);}else setStatus("error");
    }
  };

  const retryPlanLoad = () => {
    if (statusRef.current !== "error" || !retryTarget) return;
    if (retryTarget.kind === "document") {
      void openPlan(retryTarget.documentId, true);
      return;
    }
    tourNavigation?.discardDestination('plan');
    setStatus("loading");
    setError(null);
    setInitialLoadAttempt((attempt) => attempt + 1);
  };

  const resetBlankPlan = () => {
    if (statusRef.current !== "ready" || savingRef.current) return;
    ++selectionEpochRef.current;
    startPlayRequestRef.current += 1;
    setStartingPlay(false);
    setStartPlayError(null);
    switchingDocumentRef.current = false;
    editorIdentityRef.current = `${worldId}:blank:${editorGeneration + 1}`;
    editorRef.current = null;
    setEditor(null);
    documentIdRef.current = null;
    const nextLocalDraftId = createWorldPlanLocalDraftId(worldId);
    localDraftIdRef.current = nextLocalDraftId;
    setLocalDraftId(nextLocalDraftId);
    revisionRef.current = null;
    titleRef.current = "Plan";
    markdownRef.current = "";
    serverTitleRef.current = "";
    serverMarkdownRef.current = "";
    serverDigestRef.current = null;
    setSavedBasis({ status: "unavailable" });
    setLastSavedAt(null);
    setAutoSavePaused(false);
    pendingWriteRef.current = null;
    authoringHoldRef.current=null;
    setRecoveryConflict(false);
    setServerDraft(null);
    setCreateUncertain(false);
    const url = new URL(window.location.href);
    url.searchParams.set("world", worldId);
    url.searchParams.delete("documentId");
    url.searchParams.delete("view");
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setRouteCardsViewRequested(false);
    setSelectedCardViewIdentity(null);
    setDocumentId(null);
    setTitle("Plan");
    setMarkdown("");
    setEditorGeneration((value) => value + 1);
    persistWorldPlanLocalDraft(worldId, {
      document_id: null,
      local_draft_id: nextLocalDraftId,
      title: "Plan",
      markdown: "",
      revision: null,
      edit_generation: ++editGenerationRef.current,
      pending_write: null,
      create_uncertain: false,
    });
    setMessage(null);
    setError(null);
    setStatus("ready");
  };

  const save = async (announceSuccess = true) => {
 const tourDispatch=guidance?.captureScope()??null;
    if (statusRef.current !== "ready") return;
    const fidelityIssues = getLiveFidelityWarnings(editorRef.current?.getJSON());
    if (fidelityIssues.length) {
      if (!fidelityBlocked) setError(markdownFidelityWarningText(fidelityIssues));
      return;
    }
    if (savingRef.current || authoringHoldRef.current !== null
      || readPlanApplicationHold(worldId,documentIdRef.current)!==null
      || createUncertain || recoveryConflict
      || (uncertainCreateDraftRef.current && !documentIdRef.current)
      || (!documentIdRef.current && !markdownRef.current.trim())) return;
    const epoch = selectionEpochRef.current;
    const initialId = documentIdRef.current;
    let uiDocumentId = initialId;
    const isCurrent = () => selectedViewIsCurrent(epoch, uiDocumentId);
    let exactId = initialId;
    let currentRevision = revisionRef.current;
    let submittedTitle = titleRef.current.trim() || "Plan";
    let submittedMarkdown = markdownRef.current;
    let submittedGeneration = editGenerationRef.current;
    savingRef.current = true;
    setSaving(true);
    setAutoSavePaused(false);
    if (isCurrent()) setSavedBasis({ status: "unavailable" });
    setError(null);
    setMessage(null);
    try {
      if (!exactId) {
        const blankDraft = readWorldPlanLocalDraft(worldId);
        submittedTitle = blankDraft?.title ?? submittedTitle;
        submittedMarkdown = blankDraft?.markdown ?? submittedMarkdown;
        submittedGeneration = blankDraft?.edit_generation ?? submittedGeneration;
        const quarantinedDraft = {
          title: submittedTitle,
          markdown: submittedMarkdown,
          edit_generation: submittedGeneration,
          bound_document_id: null,
        };
        uncertainCreateDraftRef.current = quarantinedDraft;
        if (isCurrent()) setUncertainCreateDraft(quarantinedDraft);
        persistWorldPlanLocalDraft(worldId, {
          document_id: null,
          title: submittedTitle,
          markdown: submittedMarkdown,
          revision: null,
          edit_generation: submittedGeneration,
          create_uncertain: true,
          uncertain_create_draft: quarantinedDraft,
          pending_write: null,
        });
        if (isCurrent()) setCreateUncertain(true);
        let created: WorldOwnedPlanRecordV2;
        try {
          created = await createWorldOwnedPlan({
            schema_version: "dmb_workspace_document_create_v2",
            scope_mode: "world",
            world_id: worldId,
            title: submittedTitle,
          });
        } catch (reason) {
          const latest = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: null,
            title: latest?.title ?? submittedTitle,
            markdown: latest?.markdown ?? submittedMarkdown,
            revision: null,
            edit_generation: latest?.edit_generation ?? submittedGeneration,
            create_uncertain: true,
            uncertain_create_draft: {
              title: latest?.title ?? submittedTitle,
              markdown: latest?.markdown ?? submittedMarkdown,
              edit_generation: latest?.edit_generation ?? submittedGeneration,
              bound_document_id: null,
            },
            pending_write: null,
          });
          if (isCurrent()) {
            setError(`World Plan creation response was uncertain. Refresh Saved Plans and select the Plan if it appears; automatic retry is disabled to prevent a duplicate. ${reason instanceof Error ? reason.message : ""}`.trim());
          }
          return;
        }
        if (created.world_id !== worldId || created.campaign_id !== null || created.kind !== "plan") {
          const latest = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: null,
            title: latest?.title ?? submittedTitle,
            markdown: latest?.markdown ?? submittedMarkdown,
            revision: null,
            edit_generation: latest?.edit_generation ?? submittedGeneration,
            create_uncertain: true,
            uncertain_create_draft: {
              title: latest?.title ?? submittedTitle,
              markdown: latest?.markdown ?? submittedMarkdown,
              edit_generation: latest?.edit_generation ?? submittedGeneration,
              bound_document_id: null,
            },
            pending_write: null,
          });
          throw new Error("Server returned a Plan outside the selected World; creation outcome is quarantined.");
        }
        exactId = created.document_id;
        currentRevision = created.revision;
        const latest = readWorldPlanLocalDraft(worldId);
        submittedTitle = latest?.document_id === null ? latest.title : submittedTitle;
        submittedMarkdown = latest?.document_id === null ? latest.markdown : submittedMarkdown;
        submittedGeneration = latest?.edit_generation ?? submittedGeneration;
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: submittedTitle,
          markdown: submittedMarkdown,
          revision: currentRevision,
          edit_generation: submittedGeneration,
          create_uncertain: false,
          uncertain_create_draft: null,
          pending_write: null,
        });
        uncertainCreateDraftRef.current = null;
        if (isCurrent() && documentIdRef.current === null) {
          uiDocumentId = exactId;
          documentIdRef.current = exactId;
          revisionRef.current = currentRevision;
          titleRef.current = submittedTitle;
          markdownRef.current = submittedMarkdown;
          serverTitleRef.current = created.title;
          serverMarkdownRef.current = "";
          serverDigestRef.current = null;
          setSavedBasis({ status: "unavailable" });
          setCreateUncertain(false);
          setUncertainCreateDraft(null);
          setDocumentId(exactId);
          setRecords((current) => [created, ...current]);
          const url = new URL(window.location.href);
          url.searchParams.set("world", worldId);
          url.searchParams.set("documentId", exactId);
          window.history.replaceState({}, "", `${url.pathname}${url.search}`);
        }
      }

      if (!exactId || currentRevision == null) {
        throw new Error("The exact World Plan identity or revision is unavailable.");
      }

      let savedLocal = readWorldPlanLocalDraft(worldId);
      if (savedLocal?.document_id === exactId) {
        submittedTitle = isCurrent() ? titleRef.current.trim() || "Plan" : savedLocal.title;
        submittedMarkdown = isCurrent() ? markdownRef.current : savedLocal.markdown;
        submittedGeneration = isCurrent() ? editGenerationRef.current : (savedLocal.edit_generation ?? 0);
      }

      const previousPending = savedLocal?.document_id === exactId
        ? savedLocal.pending_write ?? null
        : pendingWriteRef.current;
      if (previousPending) {
        const snapshot = await getWorldOwnedPlanSnapshot(exactId);
        if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null) {
          throw new Error("Pending write recovery resolved outside the selected World.");
        }
        let committedMarkdown: string | null = null;
        try {
          const committedRevision = await getWorldOwnedPlanCommittedRevision(exactId);
          if (committedRevision.world_id !== worldId || committedRevision.campaign_id !== null) {
            throw new Error("Committed revision recovery resolved outside the selected World.");
          }
          committedMarkdown = committedRevision.markdown;
        } catch (reason) {
          if (!(reason instanceof LiveApiError && (reason.status === 404 || reason.status === 409))) {
            throw reason;
          }
        }

        const committed = committedMarkdown === previousPending.markdown
          && (previousPending.title === undefined || snapshot.record.title === previousPending.title);
        const priorTitleMatches = previousPending.base_title === undefined || snapshot.record.title === previousPending.base_title;
        const preparedCopy = priorTitleMatches && previousPending.prepared_revision !== null
          && snapshot.loaded_revision === previousPending.prepared_revision
          && snapshot.markdown === previousPending.markdown;
        const prepareApplied = priorTitleMatches && previousPending.phase === "prepare"
          && snapshot.loaded_revision === previousPending.base_revision + 1
          && snapshot.markdown === previousPending.markdown;
        const prepareDidNotApply = priorTitleMatches && previousPending.phase === "prepare"
          && snapshot.loaded_revision === previousPending.base_revision
          && snapshot.markdown === previousPending.base_markdown;
        if (!committed && !preparedCopy && !prepareApplied && !prepareDidNotApply) {
          if (isCurrent()) {
            setRecoveryConflict(true);
            setServerDraft({
              title: snapshot.record.title,
              markdown: snapshot.markdown,
              revision: snapshot.loaded_revision,
              contentSha256: snapshot.content_sha256,
              contentStatus: snapshot.record.content_status,
            });
            setError("The previous save outcome cannot be proven against the current World revision. Your local draft is preserved and saving is blocked until you choose a version.");
          }
          return;
        }
        currentRevision = snapshot.loaded_revision;
        revisionRef.current = currentRevision;
        serverTitleRef.current = snapshot.record.title;
        serverMarkdownRef.current = committed ? committedMarkdown ?? snapshot.markdown : snapshot.markdown;
        serverDigestRef.current = snapshot.content_sha256;
        if (committed && snapshot.record.content_status === "committed") {
          setLastSavedAt(durableTimestamp(snapshot.record.updated_at));
        }
        if (isCurrent()) {
          setSavedBasis(committed && snapshot.record.content_status === "committed"
            ? worldPlanCardBasisFromSnapshot(snapshot)
            : { status: "unavailable" });
        }
        pendingWriteRef.current = null;
        const latest = readWorldPlanLocalDraft(worldId);
        const preserveLatest = latest?.document_id === exactId
          && (latest.edit_generation ?? 0) > previousPending.edit_generation;
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: preserveLatest ? latest.title : submittedTitle,
          markdown: preserveLatest ? latest.markdown : submittedMarkdown,
          revision: currentRevision,
          edit_generation: preserveLatest ? latest.edit_generation ?? submittedGeneration : submittedGeneration,
          create_uncertain: false,
          pending_write: null,
        });
        if (committed && !preserveLatest) {
          const currentRecovery = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
            ?? uncertainCreateDraftRef.current;
          const recoveryWasSubmitted = currentRecovery?.bound_document_id === exactId
            && currentRecovery.edit_generation <= previousPending.edit_generation
            && currentRecovery.markdown === previousPending.markdown;
          const remainingRecovery = recoveryWasSubmitted ? null : currentRecovery;
          uncertainCreateDraftRef.current = remainingRecovery;
          if (isCurrent()) setUncertainCreateDraft(remainingRecovery);
          persistWorldPlanLocalDraft(worldId, {
            document_id: exactId,
            title: submittedTitle,
            markdown: submittedMarkdown,
            revision: currentRevision,
            edit_generation: submittedGeneration,
            create_uncertain: false,
            uncertain_create_draft: remainingRecovery,
            pending_write: null,
          });
          if (isCurrent()) {
            setMessage(announceSuccess ? "Saved to this World." : null);
            setSaving(false);
          }
          return;
        }
        savedLocal = readWorldPlanLocalDraft(worldId);
        if (savedLocal?.document_id === exactId) {
          submittedTitle = isCurrent() ? titleRef.current.trim() || "Plan" : savedLocal.title;
          submittedMarkdown = isCurrent() ? markdownRef.current : savedLocal.markdown;
          submittedGeneration = isCurrent() ? editGenerationRef.current : (savedLocal.edit_generation ?? 0);
        }
      }

      const baseRevision = currentRevision;
      const baseMarkdown = serverMarkdownRef.current;
      const preparing = {
        phase: "prepare" as const,
        base_revision: baseRevision,
        prepared_revision: null,
        base_markdown: baseMarkdown,
        markdown: submittedMarkdown,
        title: submittedTitle,
        base_title: serverTitleRef.current,
        edit_generation: submittedGeneration,
      };
      pendingWriteRef.current = preparing;
      const beforePrepare = readWorldPlanLocalDraft(worldId);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: beforePrepare?.title ?? submittedTitle,
        markdown: beforePrepare?.markdown ?? submittedMarkdown,
        revision: baseRevision,
        edit_generation: beforePrepare?.edit_generation ?? submittedGeneration,
        create_uncertain: false,
        pending_write: preparing,
      });
      const scope = {
        schema_version: "dmb_tiptap_markdown_write_prepare_v2" as const,
        scope_mode: "world" as const,
        world_id: worldId,
      };
      const prepared = await prepareTiptapMarkdownWrite({
        ...scope,
        document_id: exactId,
        markdown: submittedMarkdown,
        title: submittedTitle,
        expected_revision: baseRevision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token || prepared.world_id !== worldId || prepared.title !== submittedTitle) {
        throw new Error(prepared.warnings.join(" ") || "Plan write could not be prepared.");
      }
      currentRevision = prepared.registry_revision;
      revisionRef.current = currentRevision;
      const preparedWrite = {
        ...preparing,
        phase: "commit" as const,
        prepared_revision: prepared.registry_revision,
      };
      pendingWriteRef.current = preparedWrite;
      const afterPrepare = readWorldPlanLocalDraft(worldId);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: afterPrepare?.title ?? submittedTitle,
        markdown: afterPrepare?.markdown ?? submittedMarkdown,
        revision: prepared.registry_revision,
        edit_generation: afterPrepare?.edit_generation ?? submittedGeneration,
        create_uncertain: false,
        pending_write: preparedWrite,
      });

      const committed = await commitWorldOwnedPlanMarkdownWrite({
        schema_version: "dmb_tiptap_markdown_write_commit_v2",
        scope_mode: "world",
        world_id: worldId,
        document_id: exactId,
        markdown: submittedMarkdown,
        title: submittedTitle,
        expected_revision: prepared.registry_revision,
        writer_confirm_token: prepared.writer_confirm_token,
      });
      if (committed.world_id !== worldId || committed.committed_record.schema_version !== "dmb_world_owned_plan_record_v2" || committed.title !== submittedTitle || committed.committed_record.title !== submittedTitle) {
        throw new Error("Commit receipt did not preserve World-owned Plan scope.");
      }
      const committedAt = durableTimestamp(committed.committed_record.updated_at);
      currentRevision = committed.registry_revision;
      revisionRef.current = currentRevision;
      serverTitleRef.current = committed.title;
      serverMarkdownRef.current = submittedMarkdown;
      serverDigestRef.current = committed.normalized_content_sha256;
      if (isCurrent()) {
        setLastSavedAt(committedAt);
        setTourPlanSave(committedAt?{dispatchScope:tourDispatch,worldId,documentId:exactId,revision:committed.registry_revision,digest:committed.normalized_content_sha256,observedAt:committedAt}:null);
        setSavedBasis({
          status: "verified",
          revision: committed.registry_revision,
          contentSha256: committed.normalized_content_sha256,
        });
      }
      pendingWriteRef.current = null;
      const latest = readWorldPlanLocalDraft(worldId);
      const preserveLatest = latest?.document_id === exactId
        && (latest.edit_generation ?? 0) > submittedGeneration;
      const finalTitle = preserveLatest ? latest.title : committed.title;
      const finalMarkdown = preserveLatest ? latest.markdown : submittedMarkdown;
      const finalGeneration = preserveLatest ? latest.edit_generation ?? submittedGeneration : submittedGeneration;
      const currentRecovery = readWorldPlanLocalDraft(worldId)?.uncertain_create_draft
        ?? uncertainCreateDraftRef.current;
      const recoveryWasSubmitted = currentRecovery?.bound_document_id === exactId
        && currentRecovery.edit_generation <= submittedGeneration
        && currentRecovery.markdown === submittedMarkdown;
      const remainingRecovery = recoveryWasSubmitted ? null : currentRecovery;
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: finalTitle,
        markdown: finalMarkdown,
        revision: currentRevision,
        edit_generation: finalGeneration,
        create_uncertain: false,
        uncertain_create_draft: remainingRecovery,
        pending_write: null,
      });
      uncertainCreateDraftRef.current = remainingRecovery;
      if (isCurrent()) {
        setUncertainCreateDraft(remainingRecovery);
        if (!preserveLatest) {
          titleRef.current = committed.title;
          markdownRef.current = submittedMarkdown;
          setTitle(committed.title);
          setMarkdown(submittedMarkdown);
          // Acknowledging these exact bytes must not reset the mounted editor
          // selection/undo history or the active Cards view.
        }
        setRecords((current) => current.map((record) => record.document_id === exactId ? committed.committed_record : record));
        setCreateUncertain(false);
        setRecoveryConflict(false);
        setServerDraft(null);
        setMessage(announceSuccess ? "Saved to this World." : null);
      }
    } catch (reason) {
      if (isCurrent()) {
        setAutoSavePaused(true);
        setError(reason instanceof Error ? reason.message : "Plan could not be saved.");
      }
    } finally {
      savingRef.current = false;
      if (isCurrent()) setSaving(false);
    }
  };

  // Proposal Save uses the same Content owner; adopting its receipt never
  // replaces mounted editor content or a newer local working copy.
  authoringAckRef.current=async application=>{
    const exactId=application.capture.document_id,epoch=selectionEpochRef.current;
    if(application.outcome!=='saved'||application.capture.world_id!==worldId
      ||documentIdRef.current!==exactId)throw new Error('The Plan Save receipt belongs to another page.');
    const [snapshot,committed]=await Promise.all([
      getWorldOwnedPlanSnapshot(exactId),getWorldOwnedPlanCommittedRevision(exactId),
    ]);
    if(!selectedViewIsCurrent(epoch,exactId))throw new Error('The page changed while checking its saved suggestion.');
    if(snapshot.record.world_id!==worldId||snapshot.record.document_id!==exactId
      ||snapshot.record.kind!=='plan'||snapshot.record.campaign_id!==null||snapshot.record.status!=='active'
      ||committed.work_revision_id!==application.saved_work_revision_id
      ||committed.revision_n!==application.saved_revision_n||committed.object_revision!==snapshot.loaded_revision
      ||committed.world_id!==worldId||committed.document_id!==exactId
      ||snapshot.markdown!==application.after_markdown||snapshot.content_sha256!==application.after_draft_sha256
      ||committed.content_sha256!==application.after_draft_sha256||snapshot.record.title!==application.after_title){
      setRecoveryConflict(true);setServerDraft({title:snapshot.record.title,markdown:snapshot.markdown,
        revision:snapshot.loaded_revision,contentSha256:snapshot.content_sha256,contentStatus:snapshot.record.content_status});
      throw new Error('The saved page changed after this suggestion. Your local draft is retained; inspect both copies.');
    }
    const retained=readWorldPlanLocalDraft(worldId);
    if(retained?.document_id===exactId){
      const hold=readPlanApplicationHold(worldId,exactId);
      if(hold!=null && (typeof hold!=='object'||!('application_id' in hold)||hold.application_id!==application.application_id))
        throw new Error('Another application owns the retained Plan draft. Both copies remain available.');
      const matchesMounted=retained.markdown===markdownRef.current&&retained.title===titleRef.current;
      if(matchesMounted)persistWorldPlanLocalDraft(worldId,{...retained,revision:snapshot.loaded_revision});
    }
    revisionRef.current=snapshot.loaded_revision;serverTitleRef.current=snapshot.record.title;
    serverMarkdownRef.current=snapshot.markdown;serverDigestRef.current=snapshot.content_sha256;
    const hold=readPlanApplicationHold(worldId,exactId);
    if(hold!==null){
      if(typeof hold!=='object'||!('action_id' in hold))throw new Error('The application recovery hold needs inspection.');
      clearPlanApplicationHold({world_id:worldId,document_id:exactId,action_id:String(hold.action_id),application_id:application.application_id});
    }
    authoringHoldRef.current=readPlanApplicationHold(worldId,exactId);setAutoSavePaused(authoringHoldRef.current!==null);
    setSavedBasis(worldPlanCardBasisFromSnapshot(snapshot));setLastSavedAt(durableTimestamp(snapshot.record.updated_at));
    setRecords(current=>current.map(record=>record.document_id===exactId?snapshot.record:record));
    setRecoveryConflict(false);setServerDraft(null);setCreateUncertain(false);
    setMessage('Suggestion saved to this Plan.');
  };
  authoringReconcileRef.current=async(actionId,applicationId)=>{
    const exactId=documentIdRef.current,epoch=selectionEpochRef.current;
    const snapshot=await readPlanAuthoringReview(worldId,actionId);
    if(!selectedViewIsCurrent(epoch,exactId))throw new Error('The page changed during application recovery.');
    const review=snapshot.review,application=review?.applications.find(item=>item.application_id===applicationId);
    if(!application||application.capture.document_id!==exactId||application.capture.world_id!==worldId)
      throw new Error('The saved review does not identify this Plan application.');
    if(application.outcome==='saved'){await authoringAckRef.current(application);return;}
    if(application.outcome!=='not_applied'&&application.outcome!=='superseded')
      throw new Error('This application is still unresolved. Inspect its review before continuing.');
    const hold=readPlanApplicationHold(worldId,exactId);
    if(hold===null){authoringHoldRef.current=null;setAutoSavePaused(false);return;}
    if(!exactId||typeof hold!=='object'
      ||!('application_id' in hold)||hold.application_id!==applicationId
      ||!('action_id' in hold)||hold.action_id!==actionId)
      throw new Error('Another application owns this draft recovery hold. It was preserved.');
    clearPlanApplicationHold({world_id:worldId,document_id:exactId,action_id:actionId,application_id:applicationId});
    authoringHoldRef.current=readPlanApplicationHold(worldId,exactId);setAutoSavePaused(authoringHoldRef.current!==null);
    setMessage('Application reconciled. Your current draft is unchanged.');
  };
  authoringSaveRef.current=async(target,prepared,application,expected,binding,commit)=>{
    if(savingRef.current||authoringHoldRef.current!==null||pendingWriteRef.current||!isCurrentEditTarget())
      throw new Error('Resolve the current Plan Save before applying this suggestion.');
    if(application.outcome!=='applying'||application.capture.world_id!==worldId
      ||application.capture.document_id!==target.request.document_id
      ||application.capture.editor_json!==target.editorJson||application.capture.selection_json!==target.selectionJson
      ||application.capture.draft_sha256!==target.request.draft_sha256
      ||application.capture.base_revision!==target.request.base_revision
      ||application.after_editor_json!==prepared.afterEditorJson||application.after_editor_sha256!==prepared.afterEditorSha256
      ||application.after_markdown!==prepared.afterMarkdown||application.after_draft_sha256!==prepared.afterDraftSha256
      ||application.markdown!==prepared.admitted.canonicalMarkdown||(titleRef.current.trim()||'Plan')!==application.after_title)
      throw new Error('The sealed application differs from the reviewed Plan change. Nothing was inserted.');
    const epoch=selectionEpochRef.current,exactId=documentIdRef.current;
    if(!exactId)throw new Error('Open the saved Plan before applying.');
    const hold={world_id:worldId,document_id:exactId,action_id:prepared.admitted.response.action_id,application_id:application.application_id};
    await retainPlanApplicationHold(hold);
    if(!selectedViewIsCurrent(epoch,exactId))throw new Error('The page changed before applying. Its recovery hold is retained.');
    authoringHoldRef.current=hold;setAutoSavePaused(true);
    try {
      await applyWorldPlanEditProposal({captured:target,admitted:prepared.admitted,
        getCurrent:()=>worldEditStateGetterRef.current(application.application_id),expectedAgentBinding:expected,getAgentBinding:binding});
      if(JSON.stringify(editorRef.current?.getJSON())!==application.after_editor_json
        ||markdownRef.current!==application.after_markdown||(titleRef.current.trim()||'Plan')!==application.after_title)
        throw new Error('The local application differs from its sealed copy. Inspect the retained draft before saving.');
      savingRef.current=true;setSaving(true);
      const saved=await commit();
      const result=saved.applications.at(-1);
      if(saved.state!=='applied'||result?.application_id!==application.application_id)
        throw new Error('The Plan did not acknowledge this application. Its exact identity is retained.');
      await authoringAckRef.current(result);
      return saved;
    } catch(reason){
      if(selectedViewIsCurrent(epoch,exactId)){setAutoSavePaused(true);setError(reason instanceof Error?reason.message:'Suggestion Save is uncertain.');}
      throw reason;
    } finally {savingRef.current=false;if(selectedViewIsCurrent(epoch,exactId))setSaving(false);}
  };

  const refreshSavedPlans = async () => {
    const epoch = selectionEpochRef.current;
    const selectedId = documentIdRef.current;
    try {
      const inventory = await listWorldOwnedPlans(worldId);
      if (!selectedViewIsCurrent(epoch, selectedId) || inventory.world_id !== worldId) return;
      setRecords(inventory.records);
      setMessage("Saved Plans refreshed. Opening a candidate will not bind the recovered draft; you can choose that explicitly afterward.");
      setError(null);
    } catch (reason) {
      if (selectedViewIsCurrent(epoch, selectedId)) {
        setError(reason instanceof Error ? reason.message : "Saved Plans could not be refreshed.");
      }
    }
  };

  const useServerVersion = () => {
    if (statusRef.current !== "ready" || !serverDraft) return;
    titleRef.current = serverDraft.title;
    markdownRef.current = serverDraft.markdown;
    serverTitleRef.current = serverDraft.title;
    serverMarkdownRef.current = serverDraft.markdown;
    serverDigestRef.current = serverDraft.contentSha256;
    revisionRef.current = serverDraft.revision;
    setSavedBasis(serverDraft.contentStatus === "committed"
      ? { status: "verified", revision: serverDraft.revision, contentSha256: serverDraft.contentSha256 }
      : serverDraft.contentStatus === "draft"
        ? { status: "server-draft" }
        : { status: "unavailable" });
    pendingWriteRef.current = null;
    setAutoSavePaused(false);
    const generation = ++editGenerationRef.current;
    setTitle(serverDraft.title);
    setMarkdown(serverDraft.markdown);
    setEditorGeneration((value) => value + 1);
    setRecoveryConflict(false);
    setServerDraft(null);
    setError(null);
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: serverDraft.title,
      markdown: serverDraft.markdown,
      revision: serverDraft.revision,
      edit_generation: generation,
      create_uncertain: false,
      pending_write: null,
    });
  };

  const restoreUncertainDraftIntoSelectedPlan = () => {
    const recovery = uncertainCreateDraftRef.current;
    const selectedId = documentIdRef.current;
    if (statusRef.current !== "ready" || !recovery || !selectedId || savingRef.current) return;
    const generation = Math.max(editGenerationRef.current, recovery.edit_generation) + 1;
    const boundRecovery = { ...recovery, edit_generation: generation, bound_document_id: selectedId };
    uncertainCreateDraftRef.current = boundRecovery;
    editGenerationRef.current = generation;
    titleRef.current = recovery.title;
    markdownRef.current = recovery.markdown;
    setUncertainCreateDraft(boundRecovery);
    setTitle(recovery.title);
    setMarkdown(recovery.markdown);
    setEditorGeneration((value) => value + 1);
    persistWorldPlanLocalDraft(worldId, {
      document_id: selectedId,
      title: recovery.title,
      markdown: recovery.markdown,
      revision: revisionRef.current,
      edit_generation: generation,
      create_uncertain: false,
      uncertain_create_draft: boundRecovery,
      pending_write: null,
    });
    setMessage("Recovered draft is now explicitly associated with this Plan. Save to write it to the World.");
    setError(null);
  };

  const discardUncertainDraft = () => {
    if (statusRef.current !== "ready" || !uncertainCreateDraftRef.current || savingRef.current) return;
    uncertainCreateDraftRef.current = null;
    setUncertainCreateDraft(null);
    setCreateUncertain(false);
    const current = readWorldPlanLocalDraft(worldId);
    const discardActiveDraft = documentIdRef.current === null;
    const nextTitle = discardActiveDraft ? "Plan" : titleRef.current;
    const nextMarkdown = discardActiveDraft ? "" : markdownRef.current;
    const nextGeneration = discardActiveDraft ? ++editGenerationRef.current : editGenerationRef.current;
    if (discardActiveDraft) {
      titleRef.current = nextTitle;
      markdownRef.current = nextMarkdown;
      setTitle(nextTitle);
      setMarkdown(nextMarkdown);
      setEditorGeneration((value) => value + 1);
    }
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: nextTitle,
      markdown: nextMarkdown,
      revision: discardActiveDraft ? null : revisionRef.current,
      edit_generation: nextGeneration,
      create_uncertain: false,
      uncertain_create_draft: null,
      pending_write: current?.pending_write ?? pendingWriteRef.current,
    });
    setMessage("Recovered draft discarded.");
    setError(null);
  };

  const persistEditorDraft = (nextTitle: string, nextMarkdown: string, generation: number) => {
    if (statusRef.current !== "ready") return;
    const saved = readWorldPlanLocalDraft(worldId);
    const existingRecovery = saved?.uncertain_create_draft ?? uncertainCreateDraftRef.current;
    const isPendingCreate = createUncertain || saved?.create_uncertain === true;
    const recoveryIsBoundHere = Boolean(documentIdRef.current)
      && existingRecovery?.bound_document_id === documentIdRef.current;
    const nextRecovery = isPendingCreate || recoveryIsBoundHere
      ? {
        title: nextTitle,
        markdown: nextMarkdown,
        edit_generation: generation,
        bound_document_id: existingRecovery?.bound_document_id ?? null,
      }
      : existingRecovery;
    uncertainCreateDraftRef.current = nextRecovery ?? null;
    setUncertainCreateDraft(nextRecovery ?? null);
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: nextTitle,
      markdown: nextMarkdown,
      revision: revisionRef.current,
      edit_generation: generation,
      create_uncertain: isPendingCreate,
      uncertain_create_draft: nextRecovery ?? null,
      pending_write: saved?.pending_write ?? pendingWriteRef.current,
    });
  };

  const saveRef = useRef(save);
  saveRef.current = save;
  const persistEditorDraftRef = useRef(persistEditorDraft);
  persistEditorDraftRef.current = persistEditorDraft;

  useEffect(() => {
    if (status !== "ready" || saving || savingRef.current || authoringHoldRef.current !== null || autoSavePaused
      || fidelityBlocked || createUncertain || recoveryConflict
      || (uncertainCreateDraft && !documentId) || pendingWriteRef.current !== null) return;
    const dirty = documentId
      ? title !== serverTitleRef.current || markdown !== serverMarkdownRef.current
      : markdown.trim().length > 0;
    if (!dirty) return;

    const epoch = selectionEpochRef.current;
    const targetDocumentId = documentId;
    const targetDraftId = localDraftId;
    const generation = editGenerationRef.current;
    const timer = window.setTimeout(() => {
      if (!selectedViewIsCurrent(epoch, targetDocumentId)
        || localDraftIdRef.current !== targetDraftId
        || editGenerationRef.current !== generation
        || savingRef.current || authoringHoldRef.current !== null) return;
      void saveRef.current(false);
    }, 700);
    return () => window.clearTimeout(timer);
  }, [autoSavePaused, createUncertain, documentId, fidelityBlocked, localDraftId,
    markdown, recoveryConflict, saving, status, title, uncertainCreateDraft, worldId]);

  const documentActions = useMemo(() => ({
    onTitleChange: (next: string) => {
      if (!isCurrentEditTarget(true) || getLiveFidelityWarnings(editorRef.current?.getJSON()).length > 0) return;
      titleRef.current = next;
      const generation = ++editGenerationRef.current;
      setAutoSavePaused((pendingWriteRef.current !== null || authoringHoldRef.current !== null) && !savingRef.current);
      setTitle(next);
      persistEditorDraftRef.current(next, markdownRef.current, generation);
    },
    onSave: () => {
      if (isCurrentEditTarget()) void saveRef.current();
    },
  }), [getLiveFidelityWarnings, isCurrentEditTarget]);
  const editorToolsGeneration = useMemo(() => status === "ready" ? toAppChromeToolsGeneration({
    sections: [
      {
        id: "world-plan-document",
        title: "Document",
        defaultOpen: true,
        actions: [{
          id: "world-plan-save",
          label: saving ? "Saving…" : "Save Plan",
          onClick: documentActions.onSave,
          disabled: saving || fidelityBlocked || createUncertain || recoveryConflict
            || Boolean(uncertainCreateDraft && !documentId) || !markdown.trim(),
        }],
        panel: <label className="world-plan-edit-panel">Plan title
          <input value={title} disabled={fidelityBlocked} onChange={(event) => documentActions.onTitleChange(event.target.value)} />
        </label>,
      },
      ...(toolbarModel.sections ?? []),
    ],
  }, workObject) : null, [status, saving, fidelityBlocked, createUncertain, recoveryConflict, uncertainCreateDraft,
    documentId, markdown, title, documentActions, toolbarModel, workObject]);
  const [cardEditNotice, setCardEditNotice] = useState<string | null>(null);
  const cardEditingExtensions = useMemo(() => [SemanticMarkdownPaste, PlanCardEditing.configure({ onBlocked: () => setCardEditNotice("This change reaches outside the selected scene or changes its structure. Use Document to make it.") })], []);
  const cardsViewActive = Boolean(documentId) && status === "ready"
    && (selectedCardViewIdentity === navigationIdentity
      || (routeCardsViewRequested && documentId === initialDocumentId));
  const selectPlanView = (view: "cards" | "document") => {
    const url = new URL(window.location.href);
    if (view === "cards") {
      url.searchParams.set("view", "cards");
      if (sceneNavigation?.identity !== navigationIdentity) {
        setSceneNavigation({ identity: navigationIdentity, sceneId: navigationSceneId });
        const target = navigationSceneId ? { kind: "scene" as const, id: navigationSceneId } : null;
        selectPlayableTarget(target && selectableTargetKeys.has(worldPlanCardTargetKey(target)) ? target : null);
      }
    }
    else url.searchParams.delete("view");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
    setRouteCardsViewRequested(false);
    setSelectedCardViewIdentity(view === "cards" ? navigationIdentity : null);
    if (view === "document" && cardsViewActive && navigationSceneId) {
      setSceneNavigation({ identity: navigationIdentity, sceneId: navigationSceneId });
      setDocumentSceneJump({ identity: editorIdentity, sceneId: navigationSceneId });
    }
  };
  const cardProjectionDocument = editor?.getJSON() ?? editorContent;
  const cardProjectionDirty = documentId !== null
    && (markdown !== serverMarkdownRef.current || title !== serverTitleRef.current);
  const savedPlanDirty = Boolean(documentId && (title !== serverTitleRef.current || markdown !== serverMarkdownRef.current));
  const durableSaveState: DurableSaveState = status === "error"
    ? "needs-attention"
    : saving
      ? "saving"
      : autoSavePaused || createUncertain || recoveryConflict
        ? "needs-attention"
        : status !== "ready" || (documentId && savedBasis.status !== "verified")
          ? "checking"
          : !documentId
            ? markdown.trim() ? "unsaved" : "draft"
            : savedPlanDirty ? "unsaved" : lastSavedAt ? "saved" : "checking";
  const canStartPlayFromSavedPlan = Boolean(
    documentId
    && documentIdRef.current === documentId
    && status === "ready"
    && savedBasis.status === "verified"
    && !cardProjectionDirty
    && !saving
    && !savingRef.current
    && pendingWriteRef.current === null
    && !createUncertain
    && !recoveryConflict
    && !fidelityBlocked
    && !startingPlay
  );
  const tourVerificationScope = guidance?.tracking ? guidance.captureScope() : null;
  const tourVerificationKey = JSON.stringify([tourVerificationScope?.walkthroughId, tourVerificationScope?.epoch,
    worldId, documentId, savedBasis, markdown, title]);
  // One owner predicate for explicit Play preview and read-only tour re-entry.
  // The caller owns cancellation; this function never creates a session.
  const verifySelectedSavedPlan = async (isCurrent: () => boolean) => {
    if (!canStartPlayFromSavedPlan || !documentId || savedBasis.status !== "verified") return null;
    const selectedDocumentId = documentId;
    const selectedBasis = savedBasis;
    const selectionEpoch = selectionEpochRef.current;
    const editGeneration = editGenerationRef.current;
    const committed = await getWorldOwnedPlanCommittedRevision(selectedDocumentId);
    if (!isCurrent() || !selectedViewIsCurrent(selectionEpoch, selectedDocumentId)) return null;
    // The authoring writer collapses trailing LF before the content owner
    // normalizes CRLF/CR. Keep the editor's bytes/undo intact while comparing
    // against that exact directional transformation, never arbitrary trimming.
    const savedAuthoringMarkdown = (serverMarkdownRef.current.replace(/\n+$/, "") + "\n")
      .replace(/\r\n?/g, "\n");
    if (
      committed.schema_version !== "dmb_workspace_committed_revision_v2"
      || committed.scope_mode !== "world"
      || committed.world_id !== worldId
      || committed.document_id !== selectedDocumentId
      || committed.kind !== "plan"
      || committed.campaign_id !== null
      || committed.status !== "active"
      || committed.has_divergent_working_copy
      || committed.object_revision !== selectedBasis.revision
      || committed.content_sha256 !== selectedBasis.contentSha256
      || (committed.markdown !== serverMarkdownRef.current && committed.markdown !== savedAuthoringMarkdown)
      || revisionRef.current !== selectedBasis.revision
      || serverDigestRef.current !== selectedBasis.contentSha256
      || !isCanonicalUuid(committed.work_revision_id)
      || !CANONICAL_SHA256_RE.test(committed.content_sha256)
      || editGenerationRef.current !== editGeneration
      || markdownRef.current !== serverMarkdownRef.current
      || titleRef.current !== serverTitleRef.current
      || pendingWriteRef.current !== null
      || savingRef.current
    ) {
      throw new Error("The selected Plan no longer matches its verified saved revision. Save and reopen the Plan before starting Play.");
    }
    const location = new URLSearchParams(window.location.search);
    if (
      location.get("world") !== worldId
      || location.get("documentId") !== selectedDocumentId
      || documentIdRef.current !== selectedDocumentId
    ) {
      throw new Error("The selected Plan or World changed before Play could start. Reopen the Plan and try again.");
    }
    const verified = {documentId:selectedDocumentId,worldId,objectRevision:committed.object_revision,pin:{revisionN:committed.revision_n,workRevisionId:committed.work_revision_id,contentSha256:committed.content_sha256},assetIds:collectTourMediaAssets(cardProjectionDocument)};
    setTourVerifiedPlan(verified);
    return verified;
  };
  const startPlayFromSavedPlan = async (tourIsCurrent:()=>boolean = ()=>true) => {
    if(!tourIsCurrent())return;
    if (!canStartPlayFromSavedPlan || !documentId) return;
    const selectedDocumentId = documentId;
    const selectionEpoch = selectionEpochRef.current;
    const request = ++startPlayRequestRef.current;
    const verification = ++planVerificationRequestRef.current;
    tourPlanVerificationAttemptRef.current = tourVerificationKey;
    const isCurrent = () => tourIsCurrent() && startPlayRequestRef.current === request
      && planVerificationRequestRef.current === verification
      && selectedViewIsCurrent(selectionEpoch, selectedDocumentId);
    setStartingPlay(true);
    setStartPlayError(null);
    try {
      const verified = await verifySelectedSavedPlan(isCurrent);
      if (verified && isCurrent()) setSessionStart({documentId:verified.documentId,worldId:verified.worldId,pin:verified.pin,sceneId:navigationSceneId});
    } catch (reason) {
      if (isCurrent()) {
        setTourVerifiedPlan(null);
        setStartPlayError(reason instanceof Error ? reason.message : "The saved Plan could not be verified for Play.");
      }
    } finally {
      if (startPlayRequestRef.current === request && selectedViewIsCurrent(selectionEpoch, selectedDocumentId)) setStartingPlay(false);
    }
  };
  const currentCardProjection = useMemo(
    () => buildWorldPlanCardProjectionModel({
      document: cardProjectionDocument,
      markdown,
      sourceWarnings: fidelityWarnings,
    }),
    [cardProjectionDocument, markdown, fidelityWarnings],
  );
  const navigationNodes = useMemo(() => currentCardProjection.status === "ready"
    ? flattenNodes(currentCardProjection.roots) : [], [currentCardProjection]);
  const navigationScenes = navigationNodes.filter(node => node.kind === "scene");
  const rememberedSceneId = useMemo(() => documentId
    ? readPlanScenePosition(worldId, documentId) : null, [worldId, documentId, navigationIdentity]);
  const requestedSceneId = sceneNavigation?.identity === navigationIdentity
    ? sceneNavigation.sceneId : rememberedSceneId;
  // Cards always opens a scene. Null/stale cursors cannot revive the retired outline destination.
  const {activateProjectionTool:openSceneEncounterTool}=useAgentInteraction();
  const navigationSceneId = navigationScenes.some(scene => scene.id === requestedSceneId)
    ? requestedSceneId : navigationScenes[0]?.id ?? null;
  const cardScopeEpoch = useRef({ key: "", generation: 0 });
  const navigationSceneTitle=navigationScenes.find(scene=>scene.id===navigationSceneId)?.title ?? "Scene";
  const currentTourPlan=canStartPlayFromSavedPlan&&!savedPlanDirty&&savedBasis.status==="verified"&&tourVerifiedPlan?.documentId===documentId&&tourVerifiedPlan.worldId===worldId&&tourVerifiedPlan.objectRevision===savedBasis.revision&&tourVerifiedPlan.pin.contentSha256===savedBasis.contentSha256?tourVerifiedPlan:null;
  useEffect(() => {
    if (!guidance?.tracking) { tourPlanVerificationAttemptRef.current = null; return; }
    if (!tourVerificationScope || !canStartPlayFromSavedPlan
      || tourPlanVerificationAttemptRef.current === tourVerificationKey) return;
    tourPlanVerificationAttemptRef.current = tourVerificationKey;
    let active = true, pending = true;
    setTourVerifiedPlan(null);
    const scope = tourVerificationScope;
    const verification = ++planVerificationRequestRef.current;
    const isCurrent = () => active && planVerificationRequestRef.current === verification && guidance.isScopeCurrent(scope);
    setStartPlayError(null);
    void verifySelectedSavedPlan(isCurrent).catch(reason => {
      pending = false;
      if (!isCurrent()) return;
      setTourVerifiedPlan(null);
      setStartPlayError(reason instanceof Error ? reason.message : "The saved Plan could not be verified. Use Start Play to retry its verification.");
    }).finally(() => { pending = false; });
    return () => {
      active = false;
      if (pending && planVerificationRequestRef.current === verification
        && tourPlanVerificationAttemptRef.current === tourVerificationKey) tourPlanVerificationAttemptRef.current = null;
    };
    // One read per eligible clean basis/resume, not per render or failure.
    // Both callers use the same live-ref checks above; manual preview supersedes this read.
  }, [guidance?.tracking, tourVerificationScope?.walkthroughId, tourVerificationScope?.epoch,
    canStartPlayFromSavedPlan, documentId, worldId, savedBasis, savedPlanDirty, markdown, title, tourVerificationKey]);
  const sceneEncounterContext=useMemo(()=>documentId && navigationSceneId ? {
    worldId,documentId,sceneId:navigationSceneId,
    sceneTitle:navigationSceneTitle,
    canCreate:canStartPlayFromSavedPlan,
    objectRevision:savedBasis.status==="verified"?savedBasis.revision:null,
    contentSha256:savedBasis.status==="verified"?savedBasis.contentSha256:null,
    verifiedPlan:currentTourPlan?.pin??null,
  }:null,[worldId,documentId,navigationSceneId,navigationSceneTitle,canStartPlayFromSavedPlan,savedBasis,currentTourPlan]);
  useCombatProjection("plan",activePublication!==null,sceneEncounterContext);
  const cardScopeKey = `${navigationIdentity}:${cardsViewActive}:${navigationSceneId}`;
  if (cardScopeEpoch.current.key !== cardScopeKey) cardScopeEpoch.current = { key: cardScopeKey, generation: cardScopeEpoch.current.generation + 1 };
  const focusedCardEditable = Boolean(cardsViewActive && editor && planCardRange(editor.state.doc, navigationSceneId));
  useLayoutEffect(() => {
    if (editor && !editor.isDestroyed) setPlanCardScope(editor, { active: cardsViewActive, sceneId: navigationSceneId });
    setCardEditNotice(null);
  }, [editor, cardsViewActive, navigationSceneId, navigationIdentity]);

  const navigatePlanScene = (sceneId: string | null) => {
    if (!isCurrentEditTarget(true) || (sceneId !== null && !navigationScenes.some(scene => scene.id === sceneId))) return;
    setSceneNavigation({ identity: navigationIdentity, sceneId });
    if (documentId) writePlanScenePosition(worldId, documentId, sceneId);
    setSceneNavigationNotice(null);
    const target = sceneId ? { kind: "scene" as const, id: sceneId } : null;
    selectPlayableTarget(target && selectableTargetKeys.has(worldPlanCardTargetKey(target)) ? target : null);
    if (!cardsViewActive && sceneId) setDocumentSceneJump({ identity: editorIdentity, sceneId });
  };
  useEffect(() => {
    if (sceneNavigation?.identity !== navigationIdentity || !sceneNavigation.sceneId
      || currentCardProjection.status !== "ready"
      || navigationScenes.some(scene => scene.id === sceneNavigation.sceneId)) return;
    setSceneNavigation({ identity: navigationIdentity, sceneId: null });
    if (documentId) writePlanScenePosition(worldId, documentId, null);
    setSceneNavigationNotice({ identity: navigationIdentity, message: "The selected scene is no longer in this draft. Choose another scene or use Document." });
  }, [currentCardProjection, navigationIdentity, sceneNavigation]);
  useLayoutEffect(() => {
    if (!documentSceneJump || cardsViewActive || sourceEditing || !editor
      || documentSceneJump.identity !== editorIdentity || !isCurrentEditTarget(true)) return;
    const heading = Array.from(editor.view.dom.querySelectorAll('[data-dmb-playable-kind="scene"]'))
      .find(element => element.getAttribute("data-dmb-playable-id") === documentSceneJump.sceneId);
    heading?.scrollIntoView?.({ block: "start" });
    setDocumentSceneJump(null);
  }, [documentSceneJump, cardsViewActive, sourceEditing, editor, editorIdentity, isCurrentEditTarget]);
  const savedCardProjection = useMemo(() => {
    if (savedBasis.status !== "verified" || !documentId) return null;
    const imported = markdownToTiptapDoc(serverMarkdownRef.current);
    return buildWorldPlanCardProjectionModel({
      document: imported.doc,
      markdown: serverMarkdownRef.current,
      sourceWarnings: markdownFidelityWarnings(imported.diagnostics, imported.doc),
    });
  }, [documentId, savedBasis]);
  function cardTargetLabel(target: WorldPlanCardTarget | null): string | undefined {
    if (!target || currentCardProjection.status !== "ready") return undefined;
    const pending = [...currentCardProjection.roots];
    while (pending.length) {
      const node = pending.pop()!;
      if (node.kind === target.kind && node.id === target.id) return node.title;
      pending.push(...node.children);
    }
    return undefined;
  }
  const selectableTargetKeys = useMemo(() => {
    if (savedBasis.status !== "verified" || !savedCardProjection) return new Set<string>();
    const currentKeys = worldPlanCardTargetKeys(currentCardProjection);
    const savedKeys = worldPlanCardTargetKeys(savedCardProjection);
    return new Set([...currentKeys].filter((key) => savedKeys.has(key)));
  }, [currentCardProjection, savedBasis, savedCardProjection]);
  const editableTargetKeys = useMemo(() => {
    if (savedBasis.status !== "verified") return new Set<string>();
    return worldPlanCardTargetKeys(currentCardProjection);
  }, [currentCardProjection, savedBasis]);
  const selectedTargetBasisMatches = Boolean(selectedPlayableTarget
    && selectedPlayableTarget.worldId === worldId
    && selectedPlayableTarget.documentId === documentId
    && savedBasis.status === "verified"
    && selectedPlayableTarget.revision === savedBasis.revision
    && selectedPlayableTarget.contentSha256 === savedBasis.contentSha256);
  const selectedPlayableTargetStale = Boolean(selectedPlayableTarget
    && (!selectedTargetBasisMatches
      || selectedPlayableTarget.stale
      || !selectableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableTarget.target))));
  const selectedEditTargetBasisMatches = Boolean(selectedPlayableEditTarget
    && selectedPlayableEditTarget.worldId === worldId
    && selectedPlayableEditTarget.documentId === documentId
    && savedBasis.status === "verified"
    && selectedPlayableEditTarget.revision === savedBasis.revision
    && selectedPlayableEditTarget.contentSha256 === savedBasis.contentSha256);
  const selectedPlayableEditTargetStale = Boolean(selectedPlayableEditTarget
    && (!selectedEditTargetBasisMatches
      || selectedPlayableEditTarget.stale
      || !editableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableEditTarget.target))));
  playableEditTargetStaleRef.current = selectedPlayableEditTargetStale;

  useEffect(() => {
    if (!selectedPlayableTarget) return;
    if (selectedPlayableTarget.worldId !== worldId || selectedPlayableTarget.documentId !== documentId) {
      setSelectedPlayableTarget(null);
      return;
    }
    if (savedBasis.status === "verified"
      && (selectedPlayableTarget.revision !== savedBasis.revision
        || selectedPlayableTarget.contentSha256 !== savedBasis.contentSha256)) {
      if (!selectedPlayableTarget.stale) setSelectedPlayableTarget({ ...selectedPlayableTarget, stale: true });
      return;
    }
    if ((!selectedTargetBasisMatches || !selectableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableTarget.target)))
      && !selectedPlayableTarget.stale) {
      setSelectedPlayableTarget({ ...selectedPlayableTarget, stale: true });
    }
  }, [documentId, savedBasis, selectableTargetKeys, selectedPlayableTarget, selectedTargetBasisMatches, worldId]);

  useEffect(() => {
    if (!selectedPlayableEditTarget) return;
    if (selectedPlayableEditTarget.worldId !== worldId || selectedPlayableEditTarget.documentId !== documentId) {
      setSelectedPlayableEditTarget(null);
      selectedPlayableEditTargetRef.current = null;
      playableEditTargetGenerationRef.current += 1;
      setPlayableEditTargetGeneration(playableEditTargetGenerationRef.current);
      return;
    }
    if (savedBasis.status === "verified"
      && (selectedPlayableEditTarget.revision !== savedBasis.revision
        || selectedPlayableEditTarget.contentSha256 !== savedBasis.contentSha256)) {
      setSelectedPlayableEditTarget(null);
      selectedPlayableEditTargetRef.current = null;
      playableEditTargetGenerationRef.current += 1;
      setPlayableEditTargetGeneration(playableEditTargetGenerationRef.current);
      return;
    }
    if ((!selectedEditTargetBasisMatches
      || !editableTargetKeys.has(worldPlanCardTargetKey(selectedPlayableEditTarget.target)))
      && !selectedPlayableEditTarget.stale) {
      setSelectedPlayableEditTarget({ ...selectedPlayableEditTarget, stale: true });
    }
  }, [documentId, editableTargetKeys, savedBasis, selectedEditTargetBasisMatches, selectedPlayableEditTarget, worldId]);

  const selectPlayableTarget = useCallback((target: WorldPlanCardTarget | null) => {
    if (target === null) {
      setSelectedPlayableTarget(null);
      return;
    }
    if (savedBasis.status !== "verified" || !documentId
      || !selectableTargetKeys.has(worldPlanCardTargetKey(target))) return;
    setSelectedPlayableTarget({
      target,
      worldId,
      documentId,
      revision: savedBasis.revision,
      contentSha256: savedBasis.contentSha256,
      stale: false,
    });
  }, [documentId, savedBasis, selectableTargetKeys, worldId]);

  useLayoutEffect(() => {
    if (status !== "ready" || currentCardProjection.status !== "ready" || !documentId
      || sceneNavigation?.identity === navigationIdentity || !rememberedSceneId
      || !navigationScenes.some(scene => scene.id === rememberedSceneId)) return;
    setSceneNavigation({ identity: navigationIdentity, sceneId: rememberedSceneId });
    const target = { kind: "scene" as const, id: rememberedSceneId };
    selectPlayableTarget(selectableTargetKeys.has(worldPlanCardTargetKey(target)) ? target : null);
    if (!cardsViewActive) setDocumentSceneJump({ identity: editorIdentity, sceneId: rememberedSceneId });
  }, [status, currentCardProjection, documentId, navigationIdentity, rememberedSceneId,
    sceneNavigation, cardsViewActive, editorIdentity, selectableTargetKeys, selectPlayableTarget]);

  const selectPlayableEditTarget = useCallback((target: WorldPlanCardTarget) => {
    if (savedBasis.status !== "verified" || !documentId
      || !editableTargetKeys.has(worldPlanCardTargetKey(target))) return;
    const generation = playableEditTargetGenerationRef.current + 1;
    playableEditTargetGenerationRef.current = generation;
    setPlayableEditTargetGeneration(generation);
    const selected = {
      target,
      worldId,
      documentId,
      revision: savedBasis.revision,
      contentSha256: savedBasis.contentSha256,
      generation,
      stale: false,
    };
    selectedPlayableEditTargetRef.current = selected;
    playableEditTargetStaleRef.current = false;
    setSelectedPlayableEditTarget(selected);
  }, [documentId, editableTargetKeys, savedBasis, worldId]);

  const clearPlayableEditTarget = useCallback(() => {
    playableEditTargetGenerationRef.current += 1;
    setPlayableEditTargetGeneration(playableEditTargetGenerationRef.current);
    selectedPlayableEditTargetRef.current = null;
    playableEditTargetStaleRef.current = false;
    setSelectedPlayableEditTarget(null);
  }, []);

  authoringMoveCaptureRef.current=async(position,identity)=>{
    const state=worldEditStateGetterRef.current(),editor=state.editor;
    if(!state.canEdit||!editor||editor.isDestroyed||!Number.isSafeInteger(position)||position<0||position>editor.state.doc.content.size)
      throw new Error('Choose a valid position in the editable Plan.');
    if(cardsViewActive)throw new Error('Switch to Document view to move this suggestion. Its current placement is retained.');
    clearPlayableEditTarget();selectedPlayableTargetRef.current=null;setSelectedPlayableTarget(null);
    if(!editor.commands.setTextSelection(position))throw new Error('The Plan could not select that placement.');
    return captureWorldPlanAuthoringTarget(worldEditStateGetterRef.current(),()=>worldEditStateGetterRef.current(),identity);
  };

  const planTrashCacheBasis = documentId && revisionRef.current !== null ? {
    document_id:documentId, revision:revisionRef.current, title:serverTitleRef.current,
    markdown:serverMarkdownRef.current, edit_generation:editGenerationRef.current,
  } : null;
  const mediaIdentity = `${worldId}:${documentId ?? localDraftId}`;
  const imageStudio = useSurfaceImageStudio(mediaIdentity, Boolean(documentId) && status === "ready" && !fidelityBlocked && !recoveryConflict);
  const tourSelection=useRef<symbol|null>(null),tourInspection=useRef<symbol|null>(null);
  const navigationPlan=!savedPlanDirty&&savedBasis.status==='verified'&&tourVerifiedPlan?.documentId===documentId&&tourVerifiedPlan.worldId===worldId&&tourVerifiedPlan.objectRevision===savedBasis.revision&&tourVerifiedPlan.pin.contentSha256===savedBasis.contentSha256?guidedPlanPin(worldId,tourVerifiedPlan.documentId,tourVerifiedPlan.pin):null;
  useStatblockWorkbenchProjection("plan",navigationPlan);
  useTourNavigationGuard({worldId,reason:(impact,reservation)=>{
    if(startingPlay&&reservation!==tourInspection.current)return 'Wait for the saved Plan preview to finish opening.';
    if(imageStudio.session)return 'Finish or close Image Studio before navigating away from its work.';
    if(impact!=='departure')return null;
    if(savedPlanDirty||savingRef.current||pendingWriteRef.current||createUncertain||recoveryConflict||fidelityBlocked)return 'Finish saving or resolve the retained Plan work before navigating.';
    if(status!=='ready'&&reservation!==tourSelection.current)return 'Wait for Plan selection to finish.';
    return null;
  }});
  useTourNavigationOwner({worldId,surface:'plan',objectId:documentId,targets:navigationPlan?[navigationPlan]:[],select:async(pin,request)=>{
    if(!request.isCurrent())return;tourSelection.current=request.reservation;
    try{await openPlan(pin.objectId,false,request.isCurrent,pin);}finally{if(tourSelection.current===request.reservation)tourSelection.current=null;}
  },inspections:[
    ...(['plan','play'] as const).map(step=>({id:'plan-preview',label:'Open saved Plan preview',step,target:navigationPlan,impact:'projection' as const,ownedReservation:tourInspection.current??undefined,unavailable:!canStartPlayFromSavedPlan?'Save and verify a clean Plan first.':undefined,perform:async(request:import('../guidedTour/Navigation').InspectionRequest)=>{if(!request.isCurrent())return;tourInspection.current=request.reservation;try{await startPlayFromSavedPlan(request.isCurrent);}finally{if(tourInspection.current===request.reservation)tourInspection.current=null;}}})),
    ...(['encounter','mechanics','adoption'] as const).map(step=>({id:'plan-encounter',label:'Open scene encounter controls',step,target:navigationPlan,impact:'projection' as const,unavailable:!sceneEncounterContext?'Select the intended scene in a saved Plan.':undefined,perform:async(request:import('../guidedTour/Navigation').InspectionRequest)=>{if(request.scope.sceneId&&request.scope.sceneId!==navigationSceneId)throw new Error('Select the scene recorded by this step before opening its encounter.');if(request.isCurrent()&&!await openSceneEncounterTool('combat'))throw new Error('The scene encounter controls are not available.');}})),
    {id:'plan-mechanics',label:'Open Statblocks',step:'mechanics',target:navigationPlan,impact:'projection',unavailable:!navigationPlan?'Select and verify the saved Plan first.':undefined,perform:async request=>{if(request.isCurrent()&&!await openSceneEncounterTool('statblock-workbench'))throw new Error('Statblocks is not available.');}},
    {id:'plan-generation',label:'Open Statblocks',step:'generation',target:navigationPlan,impact:'projection',unavailable:!navigationPlan?'Select and verify the saved Plan first.':undefined,perform:async request=>{if(request.isCurrent()&&!await openSceneEncounterTool('statblock-workbench'))throw new Error('Statblocks is not available.');}},
    {id:'plan-images',label:'Open Image Studio',step:'image',target:navigationPlan,impact:'projection',perform:request=>{if(request.isCurrent()&&!imageStudio.open())throw new Error('Image Studio is not available.');}},
  ]});
  const mediaState = useRef<DocumentMediaState | null>(null);
  mediaState.current = editor ? { editor, identity: mediaIdentity,
    version: `${revisionRef.current}:${editGenerationRef.current}:${editorIdentity}:${cardScopeEpoch.current.generation}`,
    canEdit: Boolean(documentId) && !sourceEditing && (!cardsViewActive || focusedCardEditable) && planCardSelectionAllowed(editor) && !fidelityBlocked && !recoveryConflict
      && pendingWriteRef.current === null && isCurrentEditTarget(),
  } : null;
  const mediaBridge = useMemo(() => createDocumentMediaBridge(() => mediaState.current), [mediaIdentity]);

  const focusTitle = (() => {
    if (!selectedPlayableTarget || savedCardProjection?.status !== "ready") return null;
    const find = (nodes: WorldPlanCardNode[]): string | null => {
      for (const node of nodes) {
        if (node.id === selectedPlayableTarget.target.id && node.kind === selectedPlayableTarget.target.kind) return node.title;
        const child = find(node.children); if (child) return child;
      }
      return null;
    };
    return find(savedCardProjection.roots);
  })();
  return (
    <TourImageProvider worldId={worldId} documentId={documentId} blockedReason={!documentId || status !== "ready" || fidelityBlocked || recoveryConflict ? "Open a ready Plan and resolve its recovery or fidelity block before using Image Studio." : null} verified={currentTourPlan?{pin:planPin(worldId,currentTourPlan.documentId,currentTourPlan.pin),assetIds:currentTourPlan.assetIds}:null}><AppChrome activeRoute="plan" editorTools={editorToolsGeneration} editToolboxLayout="dock" workspaceLayout="bounded">
      <PlanTourObservation label={title} verified={currentTourPlan} error={startPlayError} saved={tourPlanSave} registryRevision={savedBasis.status==="verified"?savedBasis.revision:null}/>
      <WorldPlanSurfaceContext
        worldId={worldId}
        worldName={worldName}
        documentId={documentId}
        localDraftId={localDraftId}
        records={records}
        disabled={saving || status !== "ready"}
        onSelect={(nextId) => { void openPlan(nextId); }}
        onNewPlan={resetBlankPlan}
        toolbar={<div className="world-plan-context-toolbar" data-plan-toolbar-identity={editorIdentity} role="group" aria-label="Plan controls">
          <nav className="world-plan-view-switch" role="group" aria-label="Plan view" data-testid="world-plan-view-switch">
            <button
              type="button"
              aria-pressed={!cardsViewActive && !sourceEditing}
              onClick={() => { setSourceEditing(false); selectPlanView("document"); }}
            >Document</button>
            <button type="button" aria-pressed={!cardsViewActive && sourceEditing} title="Edit raw Markdown source"
              disabled={status !== "ready"}
              onClick={() => { selectPlanView("document"); setSourceEditing(true); setEditorGeneration(value => value + 1); }}>Markdown</button>
            <button
              type="button"
              aria-pressed={cardsViewActive}
              disabled={!documentId || status !== "ready" || !editor}
              onClick={() => { setSourceEditing(false); selectPlanView("cards"); }}
            >Cards</button>
          </nav>
          <button type="button" aria-label="Open Image Studio" data-guided-control="image" aria-expanded={Boolean(imageStudio.session)} disabled={!documentId || status !== "ready" || fidelityBlocked || recoveryConflict}
            onClick={() => { if (imageStudio.open()) setSourceEditing(false); }}>Images</button>
          <WorkspaceTrashControl showTrash={false} worldId={worldId}
            current={documentId && revisionRef.current ? {kind:"document", id:documentId, title, surface:"plan", revision:revisionRef.current} : null}
            blocked={durableSaveState !== "saved" || startingPlay || pendingWriteRef.current !== null}
            onTrashed={() => {
              if (planTrashCacheBasis) clearTrashedPlanRecovery(worldId, planTrashCacheBasis);
              window.location.assign(`/plan?world=${encodeURIComponent(worldId)}`);
            }}
            />
          <span className="world-plan-context-toolbar__save">
            <DurableSaveStatus state={durableSaveState} savedAt={lastSavedAt} />
          </span>
          {autoSavePaused && !createUncertain && !recoveryConflict && !fidelityBlocked ? (
            <SurfaceNavbarIconButton icon="save" label="Retry save" className="world-plan-context-toolbar__retry"
              onClick={() => { setAutoSavePaused(false); void saveRef.current(); }} />
          ) : null}
          <SurfaceContextPopover title="Start session" open={sessionStart?.documentId===documentId&&sessionStart?.worldId===worldId} onOpenChange={open=>{if(!open)setSessionStart(null);}} align="end" trigger={<SurfaceNavbarIconButton icon="play" label={startingPlay ? "Verifying saved Plan…" : "Start Play from this Plan"} className="world-plan-context-toolbar__start" data-testid="world-plan-start-play" data-guided-control="plan start-play"
            aria-describedby={status === "ready" && !canStartPlayFromSavedPlan && !startingPlay && documentId ? "world-plan-start-play-reason" : undefined}
            title={canStartPlayFromSavedPlan ? "Start Play from this saved Plan" : "Save and reopen a clean, committed Plan before starting Play."}
            disabled={!canStartPlayFromSavedPlan} onClick={() => { void startPlayFromSavedPlan(); }} />}>
            {sessionStart&&<DeferredSessionStart verifiedWorldId={sessionStart.worldId} initialPlanId={sessionStart.documentId} initialPlanRevisionPin={sessionStart.pin} initialSceneId={sessionStart.sceneId} onStarted={runId=>{
              const params=new URLSearchParams({world:sessionStart.worldId,run:runId});window.history.pushState({},'',`/play?${params}`);window.dispatchEvent(new PopStateEvent('popstate'));
            }}/>}
          </SurfaceContextPopover>
          {status === "ready" && documentId && !canStartPlayFromSavedPlan && !startingPlay ? (
            <span id="world-plan-start-play-reason" className="sr-only" data-testid="world-plan-start-play-disabled">
              Save and reopen a clean, committed Plan before starting Play.
            </span>
          ) : null}
        </div>}
      />
      {imageStudio.session ? <DocumentImageStudio key={mediaIdentity} initialPrompt={imageStudio.session.prompt} bridge={mediaBridge} targetLabel="Plan" onClose={imageStudio.close} /> : null}
      <PlanConversationDockAdapter contextLabel={focusTitle ? `${focusTitle} · Full saved Plan` : `${worldName} · Full saved Plan`} reader={(
      <main
        className="app-status world-owned-plan"
        data-testid="world-owned-plan"
        data-plan-surface-identity={editorIdentity}
        aria-labelledby="world-owned-plan-title"
      >
        <h1 id="world-owned-plan-title" className="sr-only">
          {documentId ? title || "Untitled Plan" : "New Plan"}
        </h1>
        {sceneNavigationNotice?.identity === navigationIdentity ? <p role="status">{sceneNavigationNotice.message}</p> : null}
        {startPlayError ? <p role="alert" data-testid="world-plan-start-play-error">{startPlayError}</p> : null}
        {createUncertain ? (
          <section role="alert">
            <p>Plan creation may have succeeded, but its response was lost. Refresh Saved Plans and open a candidate if one appears. Its identity is not assumed; the recovered text stays separate until you explicitly restore it into a Plan or discard it. Automatic creation retry is blocked to avoid duplicates.</p>
            <button type="button" onClick={() => void refreshSavedPlans()} disabled={saving || status !== "ready"}>Refresh Saved Plans</button>
            <button type="button" onClick={discardUncertainDraft} disabled={saving || status !== "ready"}>Discard recovered draft</button>
          </section>
        ) : null}
        {uncertainCreateDraft && !createUncertain ? (
          <section role="status" aria-label="Recovered Plan draft">
            <p>An unsaved draft from an uncertain Plan creation is preserved separately. It has not been assumed to belong to the selected Plan.</p>
            {documentId ? <button type="button" onClick={restoreUncertainDraftIntoSelectedPlan} disabled={saving || status !== "ready"}>Restore recovered draft into this Plan</button> : null}
            <button type="button" onClick={discardUncertainDraft} disabled={saving || status !== "ready"}>Discard recovered draft</button>
          </section>
        ) : null}
        {recoveryConflict && serverDraft ? (
          <section role="alert">
            <p>The server Plan changed while a local draft was pending. Your local text is preserved, but cannot overwrite the newer server version silently.</p>
            <button type="button" onClick={useServerVersion}>Use saved Plan version</button>
          </section>
        ) : null}
        {fidelityWarnings.length ? (
          <section role="alert" aria-label="Markdown preservation warning">
            <p>This Plan contains Markdown the editor cannot safely preserve. Visual editing and autosave are paused to protect the saved text. Use Markdown to resolve these constructs; the original and local recovery copy remain unchanged.</p>
            <ul>{fidelityWarnings.map((warning, index) => <li key={`${index}:${warning}`}>{warning}</li>)}</ul>
          </section>
        ) : null}

        {sceneEncounterContext && <div className="plan-scene-encounter-entry"><SceneEncounterLauncher onOpen={()=>void openSceneEncounterTool("combat")}/></div>}
        <div className="plan-cards-workspace" data-plan-view={cardsViewActive ? "cards" : sourceEditing ? "source" : "document"}>
          {documentId && status === "ready" ? <PlanCardDeck key={navigationIdentity} visible={true} scenes={navigationScenes} nodes={navigationNodes}
            sceneId={navigationSceneId} onSelect={navigatePlanScene} /> : null}
        <div
          className="world-plan-document-view"
          data-testid="world-plan-document-view"
          role={cardsViewActive && focusedCardEditable ? "region" : undefined}
          aria-label={cardsViewActive && focusedCardEditable ? "Focused Plan scene" : undefined}
          hidden={cardsViewActive && !focusedCardEditable}
          aria-hidden={cardsViewActive && !focusedCardEditable}
        >
          <CardSceneNavigation scenes={navigationScenes} sceneId={navigationSceneId} onSelect={navigatePlanScene}
            hidden={!cardsViewActive || !focusedCardEditable} />
          {sourceEditing ? <PlanMarkdownSource value={splitLeadingYamlFrontmatter(markdown).markdown} disabled={status !== "ready"}
            onChange={body => {
              const next = preserveLeadingYamlFrontmatter(markdownRef.current, body);
              if (!isCurrentEditTarget(true) || next === markdownRef.current) return;
              markdownRef.current = next;
              const generation = ++editGenerationRef.current;
              const pendingRecovery = (pendingWriteRef.current !== null || authoringHoldRef.current !== null) && !savingRef.current;
              setAutoSavePaused(pendingRecovery);
              setMarkdown(next);
              persistEditorDraft(titleRef.current, next, generation);
              setEditorGeneration(value => value + 1);
              if (!pendingRecovery) setError(null);
              setMessage(null);
            }} /> : null}
          <div className="world-plan-visual-editor" hidden={sourceEditing && !cardsViewActive}>
          <PlanSurfaceCanvasFrame
            className="world-owned-plan__canvas"
            cardLayout
            testId="world-owned-plan-editor"
            identityLabel={cardsViewActive ? "" : documentId ? "Plan editor" : "Unsaved Plan draft"}
            themeId="mireward-runbook"
          >
            <MarkdownEditorCore
              content={editorContent}
              documentKey={editorIdentity}
              editable={status === "ready" && !fidelityBlocked}
              extensions={cardEditingExtensions}
              onEditorChange={setCurrentEditor}
              dataTestId="world-owned-plan-markdown-editor"
              onUpdate={(json: JSONContent, updatedEditor: Editor, meta) => {
                if (!meta.programmatic && !switchingDocumentRef.current && status === "ready" && updatedEditor === editorRef.current && isCurrentEditTarget(true)) {
                  const currentFidelityIssues = getLiveFidelityWarnings(json);
                  if (currentFidelityIssues.length) {
                    if (!fidelityBlocked) {
                      setError(markdownFidelityRejectionText(currentFidelityIssues));
                    }
                    setEditorGeneration((value) => value + 1);
                    return;
                  }
                  let next: string;
                  try {
                    const canonical = defaultMarkdownDocumentAdapter.exportMarkdown(json);
                    next = exportPlanCardMarkdown(updatedEditor, markdownRef.current, canonical);
                  } catch (cause) {
                    setError(cause instanceof Error ? cause.message : "Could not preserve the scene edit.");
                    setEditorGeneration(value => value + 1);
                    return;
                  }
                  const nextImport = markdownToTiptapDoc(next);
                  const nextFidelityIssues = markdownFidelityWarnings(nextImport.diagnostics, json);
                  if (nextFidelityIssues.length) {
                    setError(markdownFidelityRejectionText(nextFidelityIssues));
                    setEditorGeneration((value) => value + 1);
                    return;
                  }
                  if (next === markdownRef.current) return;
                  markdownRef.current = next;
                  const generation = ++editGenerationRef.current;
                  const pendingRecovery = (pendingWriteRef.current !== null || authoringHoldRef.current !== null) && !savingRef.current;
                  setAutoSavePaused(pendingRecovery);
                  setMarkdownState({ markdown: next, validated: { editorIdentity, imported: nextImport } });
                  persistEditorDraft(titleRef.current, next, generation);
                  if (!pendingRecovery) setError(null);
                }
              }}
            >
              {(editor) => <EditorContent editor={editor} aria-label="Markdown plan" />}
            </MarkdownEditorCore>
          </PlanSurfaceCanvasFrame>
          </div>
        </div>
        <div className="plan-cards-workspace__reader" hidden={!cardsViewActive || focusedCardEditable}>
          {documentId && cardsViewActive && !focusedCardEditable ? <WorldPlanCardProjection
            key={editorIdentity}
            sceneId={navigationSceneId}
            worldId={worldId}
            documentId={documentId}
            document={cardProjectionDocument}
            markdown={markdown}
            sourceWarnings={fidelityWarnings}
            basis={savedBasis}
            isDirty={cardProjectionDirty}
            onReturnToDocument={() => selectPlanView("document")}
            editableTargetKeys={editableTargetKeys}
            selectedEditTarget={selectedPlayableEditTarget?.target ?? null}
            onSelectEditTarget={selectPlayableEditTarget}
            selectionStale={selectedPlayableTargetStale}
            onActivateGraphNode={activateNode}
          /> : null}
          </div>
        </div>
        {cardEditNotice ? <p role="status">{cardEditNotice} <button type="button" onClick={() => selectPlanView("document")}>Open Document</button></p> : null}
        {status === "loading" ? <p role="status">Loading World Plan…</p> : null}
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
        {status === "error" ? <button type="button" onClick={retryPlanLoad}>Retry Plan load</button> : null}
      </main>
      )}>
      {(presentationHosts) => <WorldPlanConversationRegistration
        presentationHosts={presentationHosts}
        worldId={worldId}
        worldName={worldName}
        documentId={documentId}
        surfaceInstanceId={surfaceIdentity.instanceKey}
        revision={revisionRef.current}
        editBridge={documentId ? worldPlanEditBridge : null}
        draftGeneration={editGenerationRef.current}
        selectionGeneration={selectionGeneration}
        savedDirty={savedPlanDirty}
        pageReady={status === "ready"}
        saveInFlight={saving || pendingWriteRef.current !== null}
        imagePromptHost={{
          unavailableReason: imageStudio.session ? "Close the current Image Studio before opening another prompt."
            : !documentId || status !== "ready" || fidelityBlocked || recoveryConflict ? "Reopen a ready Plan to use this image prompt." : null,
          open: (prompt) => {
            if (!imageStudio.open(prompt)) return false;
            setSourceEditing(false);
            return true;
          },
        }}
        playableTarget={selectedPlayableTarget?.target ?? null}
        playableTargetBasis={selectedPlayableTarget ? {
          revision: selectedPlayableTarget.revision,
          contentSha256: selectedPlayableTarget.contentSha256,
        } : null}
        playableTargetStale={selectedPlayableTargetStale}
        onClearPlayableTarget={() => setSelectedPlayableTarget(null)}
        playableEditTarget={selectedPlayableEditTarget ? {
          ...selectedPlayableEditTarget.target,
          generation: selectedPlayableEditTarget.generation,
        } : null}
        playableEditTargetGeneration={playableEditTargetGeneration}
        playableEditTargetStale={selectedPlayableEditTargetStale}
        playableEditTargetDirty={cardProjectionDirty}
        editorSelectionActive={Boolean(editor && !editor.state.selection.empty)}
        playableTargetLabel={cardTargetLabel(selectedPlayableTarget?.target ?? null)}
        playableEditTargetLabel={cardTargetLabel(selectedPlayableEditTarget?.target ?? null)}
        onSavePlan={() => {
          const current = worldEditStateGetterRef.current();
          if (current.documentId === documentId && current.worldId === worldId
            && (titleRef.current !== serverTitleRef.current || markdownRef.current !== serverMarkdownRef.current)) documentActions.onSave();
        }}
        savePlanEnabled={savedPlanDirty && !saving && !fidelityBlocked && !createUncertain && !recoveryConflict
          && !Boolean(uncertainCreateDraft && !documentId) && Boolean(markdown.trim())}
        onClearPlayableEditTarget={clearPlayableEditTarget}
      />}
      </PlanConversationDockAdapter>
    </AppChrome></TourImageProvider>
  );
}
