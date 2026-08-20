import type { JSONContent } from "@tiptap/core";

import type {
  PlayRunProgress,
  PlayRunRecord,
  PlayRunReferenceElement,
  PlayRunReferenceManifest,
  WorkspaceDocumentSnapshot,
} from "../../api/types";
import {
  hasBlockingMarkdownImportDiagnostics,
  markdownToTiptapDoc,
} from "../../tiptap/markdown/markdownToTiptap";
import type { PlayableElementKind } from "../../tiptap/playable/playableElementIdentity";
import {
  indexPlayableStructure,
  type PlayableStructureElement,
  type PlayableStructureIndex,
} from "../../tiptap/playable/playableStructureIndex";

export const CANONICAL_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export const CANONICAL_SHA256_RE = /^[0-9a-f]{64}$/;

export type NativeRunbookFailureStatus =
  | "rebase_required"
  | "integrity_failure"
  | "unavailable"
  | "miss"
  | "recovery_pending";

export type NativeRunbookAdmissionStatus = "ready" | NativeRunbookFailureStatus;

export type NativeRunbookAuthoredElement = {
  kind: PlayableElementKind;
  id: string;
  title: string;
  bodyText: string;
  /** Exact admitted TipTap body fragment; never a second Markdown parse. */
  bodyDoc: JSONContent;
  sceneId?: string;
  choiceId?: string;
};

export type NativeRunbookOption = NativeRunbookAuthoredElement & {
  kind: "option";
  sceneId: string;
  choiceId: string;
};

export type NativeRunbookChoice = NativeRunbookAuthoredElement & {
  kind: "choice";
  sceneId: string;
  options: NativeRunbookOption[];
};

export type NativeRunbookBeat = NativeRunbookAuthoredElement & {
  kind: "beat";
  sceneId: string;
};

export type NativeRunbookScene = NativeRunbookAuthoredElement & {
  kind: "scene";
  beats: NativeRunbookBeat[];
  choices: NativeRunbookChoice[];
};

export type NativeRunbookReadyDeck = {
  status: "ready";
  run: PlayRunRecord;
  manifest: PlayRunReferenceManifest;
  snapshot: WorkspaceDocumentSnapshot;
  importedDoc: JSONContent;
  structure: PlayableStructureIndex;
  scenes: NativeRunbookScene[];
  previewSceneId: string | null;
  previewBeatId: string | null;
  displayedSceneId: string | null;
  displayedBeatId: string | null;
  currentIsPreview: boolean;
};

export type NativeRunbookFailure = {
  status: NativeRunbookFailureStatus;
  reason: string;
};

export type NativeRunbookAdmission = NativeRunbookReadyDeck | NativeRunbookFailure;

export function isCanonicalUuid(value: string): boolean {
  return CANONICAL_UUID_RE.test(value);
}

export function emptyPlayRunProgress(): PlayRunProgress {
  return {
    current_scene_id: null,
    current_beat_id: null,
    resolved_beat_ids: [],
    selections: {},
    notes_by_element_id: {},
  };
}

export function canonicalizePlayRunProgress(progress: PlayRunProgress): PlayRunProgress {
  return {
    current_scene_id: progress.current_scene_id,
    current_beat_id: progress.current_beat_id,
    resolved_beat_ids: [...new Set(progress.resolved_beat_ids)].sort(),
    selections: { ...progress.selections },
    notes_by_element_id: { ...progress.notes_by_element_id },
  };
}

function failed(status: NativeRunbookFailureStatus, reason: string): NativeRunbookFailure {
  return { status, reason };
}

function membershipKey(element: {
  kind: string;
  element_id: string;
  scene_id?: string | null;
  choice_id?: string | null;
}): string {
  return [
    element.kind,
    element.element_id,
    element.scene_id ?? "",
    element.choice_id ?? "",
  ].join("\0");
}

function structureMembershipKey(element: PlayableStructureElement): string {
  if (element.kind === "scene") {
    return membershipKey({ kind: "scene", element_id: element.id });
  }
  if (element.kind === "option") {
    return membershipKey({
      kind: "option",
      element_id: element.id,
      scene_id: element.sceneId,
      choice_id: element.choiceId,
    });
  }
  return membershipKey({
    kind: element.kind,
    element_id: element.id,
    scene_id: element.sceneId,
  });
}

function collectNodeText(node: unknown): string {
  if (node == null || typeof node !== "object") return "";
  const record = node as { type?: unknown; text?: unknown; content?: unknown };
  if (record.type === "text" && typeof record.text === "string") return record.text;
  if (!Array.isArray(record.content)) return "";
  return record.content.map(collectNodeText).join("");
}

function playableHeadingIdentity(node: unknown): { kind: PlayableElementKind; id: string } | null {
  if (node == null || typeof node !== "object") return null;
  const record = node as { type?: unknown; attrs?: unknown };
  if (record.type !== "heading") return null;
  const attrs = record.attrs as
    | { playableElementKind?: unknown; playableElementId?: unknown }
    | null
    | undefined;
  const kind = attrs?.playableElementKind;
  const id = attrs?.playableElementId;
  if (
    (kind === "scene" || kind === "beat" || kind === "choice" || kind === "option")
    && typeof id === "string"
    && id.length > 0
  ) {
    return { kind, id };
  }
  return null;
}

function isOrdinaryRootInstructionHeading(node: unknown): boolean {
  if (playableHeadingIdentity(node) != null) return false;
  if (node == null || typeof node !== "object") return false;
  const record = node as { type?: unknown; attrs?: unknown };
  if (record.type !== "heading") return false;
  const level = (record.attrs as { level?: unknown } | null | undefined)?.level;
  return level === 1 || level === 2;
}

type AuthoredSlice = {
  kind: PlayableElementKind;
  id: string;
  title: string;
  bodyText: string;
  bodyDoc: JSONContent;
};

function wrapBodyDoc(bodyNodes: unknown[]): JSONContent {
  return {
    type: "doc",
    content: bodyNodes as JSONContent[],
  };
}

const EMPTY_BODY_DOC: JSONContent = { type: "doc", content: [] };

/**
 * Disjoint authored bodies: each Playable heading owns nodes until the next
 * root Playable heading or an ordinary unmarked document-root H1/H2. Sibling
 * Beat/Choice/Option slices never inherit the previous sibling's body, and
 * unmarked Runbook-level sections after playable material stay outside the
 * preceding element's body.
 */
export function slicePlayableBodies(document: unknown): Map<string, AuthoredSlice> {
  const slices = new Map<string, AuthoredSlice>();
  if (document == null || typeof document !== "object") return slices;
  const content = (document as { content?: unknown }).content;
  if (!Array.isArray(content)) return slices;

  let current: { kind: PlayableElementKind; id: string; title: string; bodyNodes: unknown[] } | null =
    null;

  const flush = () => {
    if (!current) return;
    const bodyText = current.bodyNodes
      .map((node) => collectNodeText(node).replace(/\s+/g, " ").trim())
      .filter((text) => text.length > 0)
      .join("\n\n");
    slices.set(current.id, {
      kind: current.kind,
      id: current.id,
      title: current.title,
      bodyText,
      bodyDoc: wrapBodyDoc(current.bodyNodes),
    });
  };

  for (const node of content) {
    const identity = playableHeadingIdentity(node);
    if (identity) {
      flush();
      current = {
        kind: identity.kind,
        id: identity.id,
        title: collectNodeText(node).replace(/\s+/g, " ").trim(),
        bodyNodes: [],
      };
      continue;
    }
    if (isOrdinaryRootInstructionHeading(node)) {
      flush();
      current = null;
      continue;
    }
    if (current) current.bodyNodes.push(node);
  }
  flush();
  return slices;
}

const SCENE_LIST_LABEL = /^scenes\.?$/i;

/**
 * Display listings nested under a Beat body, taken from the admitted TipTap
 * fragment. Looks for a root paragraph/heading labeled "Scenes" and the
 * following bullet list. Not a second Markdown parse and not Playable identity.
 */
export function extractSceneListingsFromBody(bodyDoc: JSONContent | undefined): string[] {
  const content = bodyDoc?.content;
  if (!Array.isArray(content)) return [];
  for (let index = 0; index < content.length; index += 1) {
    const node = content[index];
    if (node == null || typeof node !== "object") continue;
    const record = node as { type?: unknown };
    if (record.type !== "paragraph" && record.type !== "heading") continue;
    if (!SCENE_LIST_LABEL.test(collectNodeText(node).trim())) continue;
    const next = content[index + 1];
    if (next == null || typeof next !== "object") return [];
    const list = next as { type?: unknown; content?: unknown };
    if (list.type !== "bulletList" || !Array.isArray(list.content)) return [];
    return list.content
      .map((item) => collectNodeText(item).replace(/\s+/g, " ").trim())
      .filter((title) => title.length > 0);
  }
  return [];
}

function isScenesListLabel(node: unknown): boolean {
  if (node == null || typeof node !== "object") return false;
  const record = node as { type?: unknown };
  if (record.type !== "paragraph" && record.type !== "heading") return false;
  return SCENE_LIST_LABEL.test(collectNodeText(node).trim());
}

function isBulletList(node: unknown): boolean {
  return node != null && typeof node === "object" && (node as { type?: unknown }).type === "bulletList";
}

/**
 * Drop the hoisted Scenes label + following bullet list from a Beat body so the
 * strip is the listing and the stage keeps the remaining Beat prose.
 */
export function omitHoistedSceneListings(bodyDoc: JSONContent | undefined): JSONContent | undefined {
  if (bodyDoc == null || !Array.isArray(bodyDoc.content)) return bodyDoc;
  const next: JSONContent[] = [];
  for (let index = 0; index < bodyDoc.content.length; index += 1) {
    const node = bodyDoc.content[index];
    if (isScenesListLabel(node) && isBulletList(bodyDoc.content[index + 1])) {
      index += 1;
      continue;
    }
    next.push(node);
  }
  return { ...bodyDoc, content: next };
}

function compareMembership(
  structure: PlayableStructureIndex,
  manifest: PlayRunReferenceManifest,
): string | null {
  const fromStructure = new Set(structure.elements.map(structureMembershipKey));
  const fromManifest = new Set(manifest.elements.map((element) => membershipKey(element)));
  if (fromStructure.size !== fromManifest.size) {
    return "client P1 structure and sealed manifest disagree on Playable membership";
  }
  for (const key of fromStructure) {
    if (!fromManifest.has(key)) {
      return "client P1 structure and sealed manifest disagree on Playable membership";
    }
  }
  return null;
}

function bindingMismatch(
  run: PlayRunRecord,
  manifest: PlayRunReferenceManifest,
): string | null {
  if (manifest.schema_version !== "dmb_play_run_reference_manifest_v1") {
    return "sealed reference manifest schema_version is not dmb_play_run_reference_manifest_v1";
  }
  if (manifest.run_id !== run.run_id) {
    return "sealed reference manifest run_id does not match the Run";
  }
  if (manifest.playable_artifact_id !== run.playable_artifact_id) {
    return "sealed reference manifest playable_artifact_id does not match the Run";
  }
  if (manifest.playable_revision !== run.playable_revision) {
    return "sealed reference manifest playable_revision does not match the Run";
  }
  if (manifest.playable_content_sha256 !== run.playable_content_sha256) {
    return "sealed reference manifest playable_content_sha256 does not match the Run";
  }
  return null;
}

function workspaceBindingFailure(
  run: PlayRunRecord,
  snapshot: WorkspaceDocumentSnapshot,
): NativeRunbookFailure | null {
  if (snapshot.record.document_id !== run.playable_artifact_id) {
    return failed(
      "integrity_failure",
      "workspace snapshot document ID does not match run.playable_artifact_id",
    );
  }
  if (snapshot.record.kind !== "runbook") {
    return failed("integrity_failure", "workspace snapshot kind is not the admitted Runbook kind");
  }
  if (snapshot.record.status !== "active") {
    return failed("integrity_failure", "runbook workspace document is discarded");
  }
  if (snapshot.record.content_status !== "committed") {
    return failed("integrity_failure", "runbook workspace document is not committed");
  }
  if (!snapshot.file_exists) {
    return failed("integrity_failure", "committed runbook workspace target file is missing");
  }
  if (
    snapshot.record.revision !== run.playable_revision
    || snapshot.loaded_revision !== run.playable_revision
  ) {
    return failed(
      "rebase_required",
      "workspace Runbook revision does not match the Run binding",
    );
  }
  if (snapshot.content_sha256 !== run.playable_content_sha256) {
    return failed(
      "rebase_required",
      "workspace Runbook content digest does not match the Run binding",
    );
  }
  if (!CANONICAL_SHA256_RE.test(run.playable_content_sha256) || !CANONICAL_SHA256_RE.test(snapshot.content_sha256)) {
    return failed("integrity_failure", "Playable content digest is not a canonical SHA-256");
  }
  return null;
}

function projectScenes(
  structure: PlayableStructureIndex,
  slices: Map<string, AuthoredSlice>,
): NativeRunbookScene[] {
  const choiceById = new Map(structure.choices.map((choice) => [choice.choiceId, choice]));
  return structure.scenes.map((scene) => {
    const sceneSlice = slices.get(scene.sceneId);
    const beats: NativeRunbookBeat[] = scene.beatOrder.map((beatId) => {
      const slice = slices.get(beatId);
      return {
        kind: "beat",
        id: beatId,
        sceneId: scene.sceneId,
        title: slice?.title ?? beatId,
        bodyText: slice?.bodyText ?? "",
        bodyDoc: slice?.bodyDoc ?? EMPTY_BODY_DOC,
      };
    });
    const choices: NativeRunbookChoice[] = scene.choiceOrder.map((choiceId) => {
      const choice = choiceById.get(choiceId);
      const slice = slices.get(choiceId);
      const options: NativeRunbookOption[] = (choice?.optionOrder ?? []).map((optionId) => {
        const optionSlice = slices.get(optionId);
        return {
          kind: "option",
          id: optionId,
          sceneId: scene.sceneId,
          choiceId,
          title: optionSlice?.title ?? optionId,
          bodyText: optionSlice?.bodyText ?? "",
          bodyDoc: optionSlice?.bodyDoc ?? EMPTY_BODY_DOC,
        };
      });
      return {
        kind: "choice",
        id: choiceId,
        sceneId: scene.sceneId,
        title: slice?.title ?? choiceId,
        bodyText: slice?.bodyText ?? "",
        bodyDoc: slice?.bodyDoc ?? EMPTY_BODY_DOC,
        options,
      };
    });
    return {
      kind: "scene" as const,
      id: scene.sceneId,
      title: sceneSlice?.title ?? scene.sceneId,
      bodyText: sceneSlice?.bodyText ?? "",
      bodyDoc: sceneSlice?.bodyDoc ?? EMPTY_BODY_DOC,
      beats,
      choices,
    };
  });
}

export function displayedSceneAndBeat(
  scenes: NativeRunbookScene[],
  progress: PlayRunProgress,
): {
  previewSceneId: string | null;
  previewBeatId: string | null;
  displayedSceneId: string | null;
  displayedBeatId: string | null;
  currentIsPreview: boolean;
} {
  const previewSceneId = scenes[0]?.id ?? null;
  const currentScene = scenes.find((scene) => scene.id === progress.current_scene_id) ?? null;
  const displayedScene = currentScene ?? (previewSceneId
    ? scenes.find((scene) => scene.id === previewSceneId) ?? null
    : null);
  const previewBeatId = displayedScene?.beats[0]?.id ?? null;
  const currentBeat =
    displayedScene?.beats.find((beat) => beat.id === progress.current_beat_id) ?? null;
  const displayedBeatId = currentBeat?.id ?? previewBeatId;
  return {
    previewSceneId,
    previewBeatId,
    displayedSceneId: displayedScene?.id ?? null,
    displayedBeatId,
    currentIsPreview: progress.current_scene_id == null && previewSceneId != null,
  };
}

export function sameAdmittedRunBinding(admitted: PlayRunRecord, next: PlayRunRecord): boolean {
  return (
    admitted.run_id === next.run_id
    && admitted.playable_artifact_id === next.playable_artifact_id
    && admitted.playable_revision === next.playable_revision
    && admitted.playable_content_sha256 === next.playable_content_sha256
  );
}

/**
 * Overlay Runtime progress onto an already-admitted deck.
 * Returns null when the Run's Playable binding changed — callers must
 * re-admit or block rather than keep the old scenes READY.
 */
export function overlayRuntimeOnDeck(
  admission: NativeRunbookReadyDeck,
  run: PlayRunRecord,
): NativeRunbookReadyDeck | null {
  if (!sameAdmittedRunBinding(admission.run, run)) return null;
  const displayed = displayedSceneAndBeat(admission.scenes, run.progress);
  return {
    ...admission,
    run,
    ...displayed,
  };
}

export function admitNativeRunbook(input: {
  run: PlayRunRecord;
  manifest: PlayRunReferenceManifest;
  snapshot: WorkspaceDocumentSnapshot;
}): NativeRunbookAdmission {
  const { run, manifest, snapshot } = input;

  if (run.schema_version !== "dmb_play_run_record_v1") {
    return failed("integrity_failure", "Run schema_version is not dmb_play_run_record_v1");
  }
  if (!isCanonicalUuid(run.run_id) || !isCanonicalUuid(run.playable_artifact_id)) {
    return failed("integrity_failure", "Run identity is not a canonical UUID");
  }

  const workspaceFailure = workspaceBindingFailure(run, snapshot);
  if (workspaceFailure) return workspaceFailure;

  const manifestFailure = bindingMismatch(run, manifest);
  if (manifestFailure) return failed("integrity_failure", manifestFailure);

  if (!Array.isArray(manifest.elements)) {
    return failed("integrity_failure", "sealed reference manifest is malformed");
  }

  if (hasBlockingMarkdownImportDiagnostics(snapshot.markdown)) {
    return failed("integrity_failure", "bound Runbook Markdown failed P1 admission");
  }

  const imported = markdownToTiptapDoc(snapshot.markdown);
  const indexed = indexPlayableStructure(imported.doc);
  if (indexed.status === "blocked") {
    return failed("integrity_failure", "bound Runbook failed P1 Playable structure indexing");
  }

  const membershipFailure = compareMembership(indexed.index, manifest);
  if (membershipFailure) return failed("integrity_failure", membershipFailure);

  const slices = slicePlayableBodies(imported.doc);
  const scenes = projectScenes(indexed.index, slices);
  const displayed = displayedSceneAndBeat(scenes, run.progress);

  return {
    status: "ready",
    run,
    manifest,
    snapshot,
    importedDoc: imported.doc,
    structure: indexed.index,
    scenes,
    ...displayed,
  };
}

export function manifestElementSignature(element: PlayRunReferenceElement): string {
  return membershipKey(element);
}
