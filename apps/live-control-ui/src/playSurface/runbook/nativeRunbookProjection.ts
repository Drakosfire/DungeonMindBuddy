import type { JSONContent } from "@tiptap/core";

import type {
  PlayRunProgress,
  PlayRunRecord,
  PlayRunReferenceElement,
  PlayRunReferenceManifest,
  PlayRunReferenceManifestV1,
  PlayRunReferenceManifestV2,
  WorkspaceCommittedRevision,
  WorkspaceDocumentSnapshot,
} from "../../api/types";
import {
  hasBlockingMarkdownImportDiagnostics,
  markdownToTiptapDoc,
} from "../../tiptap/markdown/markdownToTiptap";
import type {
  PlayableBeatKind,
  PlayableElementKind,
} from "../../tiptap/playable/playableElementIdentity";
import {
  indexPlayableStructure,
  indexPlayableStructureV2,
  type PlayableStructureElement,
  type PlayableStructureIndex,
  type PlayableStructureIndexV2,
} from "../../tiptap/playable/playableStructureIndex";
import {
  compareV2Membership,
  deriveAuthoredRelevance,
  deriveV2OpeningBeatId,
  v2RelevanceTargetIds,
  type AuthoredRelevance,
} from "./v2RuntimeProjection";

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
  grammar: "v1";
  run: PlayRunRecord;
  manifest: PlayRunReferenceManifestV1;
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

export type NativeRunbookOptionV2 = {
  kind: "option";
  id: string;
  title: string;
  bodyText: string;
  choiceId: string;
};

export type NativeRunbookChoiceV2 = {
  kind: "choice";
  id: string;
  title: string;
  bodyText: string;
  beatId: string;
  sceneId: string | null;
  options: NativeRunbookOptionV2[];
};

export type NativeRunbookSceneV2 = {
  kind: "scene";
  id: string;
  title: string;
  bodyText: string;
  beatId: string;
  relevance: AuthoredRelevance;
};

export type NativeRunbookBeatV2 = {
  kind: "beat";
  id: string;
  title: string;
  bodyText: string;
  beatKind: PlayableBeatKind | null;
  relevance: AuthoredRelevance;
  scenes: NativeRunbookSceneV2[];
  choices: NativeRunbookChoiceV2[];
};

export type NativeRunbookReadyV2 = {
  status: "ready";
  grammar: "v2";
  run: PlayRunRecord;
  manifest: PlayRunReferenceManifestV2;
  snapshot: WorkspaceDocumentSnapshot;
  importedDoc: JSONContent;
  structure: PlayableStructureIndexV2;
  beats: NativeRunbookBeatV2[];
  currentBeatId: string;
  currentSceneId: string | null;
  openingBeatId: string;
  relevanceByTargetId: Record<string, AuthoredRelevance>;
};

export type NativeRunbookFailure = {
  status: NativeRunbookFailureStatus;
  reason: string;
};

export type NativeRunbookAdmission =
  | NativeRunbookReadyDeck
  | NativeRunbookReadyV2
  | NativeRunbookFailure;

export function isNativeRunbookReadyV2(
  admission: NativeRunbookAdmission,
): admission is NativeRunbookReadyV2 {
  return admission.status === "ready" && admission.grammar === "v2";
}

export function isNativeRunbookReadyV1(
  admission: NativeRunbookAdmission,
): admission is NativeRunbookReadyDeck {
  return admission.status === "ready" && admission.grammar === "v1";
}

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
};

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

function compareMembership(
  structure: PlayableStructureIndex,
  manifest: PlayRunReferenceManifestV1,
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
  manifest: PlayRunReferenceManifestV1 | PlayRunReferenceManifestV2,
): string | null {
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
  committed: WorkspaceCommittedRevision,
): NativeRunbookFailure | null {
  if (committed.document_id !== run.playable_artifact_id) {
    return failed(
      "integrity_failure",
      "committed revision document ID does not match run.playable_artifact_id",
    );
  }
  if (committed.kind !== "runbook") {
    return failed("integrity_failure", "committed revision kind is not the admitted Runbook kind");
  }
  if (committed.status !== "active") {
    return failed("integrity_failure", "runbook workspace document is discarded");
  }
  if (committed.revision_n !== run.playable_revision) {
    return failed(
      "integrity_failure",
      "committed revision_n does not match the Run Playable binding",
    );
  }
  if (committed.content_sha256 !== run.playable_content_sha256) {
    return failed(
      "integrity_failure",
      "committed revision digest does not match the Run Playable binding",
    );
  }
  if (!CANONICAL_SHA256_RE.test(run.playable_content_sha256) || !CANONICAL_SHA256_RE.test(committed.content_sha256)) {
    return failed("integrity_failure", "Playable content digest is not a canonical SHA-256");
  }
  return null;
}

function snapshotFromCommitted(committed: WorkspaceCommittedRevision): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: {
      schema_version: "dmb_workspace_document_record_v1",
      document_id: committed.document_id,
      title: committed.title,
      campaign_id: committed.campaign_id,
      target_session: null,
      kind: committed.kind,
      target_relpath: committed.target_relpath,
      status: committed.status,
      content_status: "committed",
      revision: committed.revision_n,
      created_at: "",
      updated_at: "",
    },
    markdown: committed.markdown,
    content_sha256: committed.content_sha256,
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: committed.revision_n,
  };
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
        };
      });
      return {
        kind: "choice",
        id: choiceId,
        sceneId: scene.sceneId,
        title: slice?.title ?? choiceId,
        bodyText: slice?.bodyText ?? "",
        options,
      };
    });
    return {
      kind: "scene" as const,
      id: scene.sceneId,
      title: sceneSlice?.title ?? scene.sceneId,
      bodyText: sceneSlice?.bodyText ?? "",
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

function projectV2Beats(
  structure: PlayableStructureIndexV2,
  slices: Map<string, AuthoredSlice>,
  relevanceByTargetId: Record<string, AuthoredRelevance>,
): NativeRunbookBeatV2[] {
  const choiceById = new Map(structure.choices.map((choice) => [choice.choiceId, choice]));
  const sceneById = new Map(structure.scenes.map((scene) => [scene.sceneId, scene]));
  return structure.beats.map((beat) => {
    const beatSlice = slices.get(beat.beatId);
    const scenes: NativeRunbookSceneV2[] = beat.sceneOrder.map((sceneId) => {
      const scene = sceneById.get(sceneId);
      const slice = slices.get(sceneId);
      return {
        kind: "scene",
        id: sceneId,
        beatId: scene?.beatId ?? beat.beatId,
        title: slice?.title ?? sceneId,
        bodyText: slice?.bodyText ?? "",
        relevance: relevanceByTargetId[sceneId] ?? "default",
      };
    });
    const choices: NativeRunbookChoiceV2[] = beat.choiceOrder.map((choiceId) => {
      const choice = choiceById.get(choiceId);
      const slice = slices.get(choiceId);
      const options: NativeRunbookOptionV2[] = (choice?.optionOrder ?? []).map((optionId) => {
        const optionSlice = slices.get(optionId);
        return {
          kind: "option",
          id: optionId,
          choiceId,
          title: optionSlice?.title ?? optionId,
          bodyText: optionSlice?.bodyText ?? "",
        };
      });
      return {
        kind: "choice",
        id: choiceId,
        beatId: choice?.beatId ?? beat.beatId,
        sceneId: choice?.sceneId ?? null,
        title: slice?.title ?? choiceId,
        bodyText: slice?.bodyText ?? "",
        options,
      };
    });
    return {
      kind: "beat",
      id: beat.beatId,
      beatKind: beat.beatKind,
      title: beatSlice?.title ?? beat.beatId,
      bodyText: beatSlice?.bodyText ?? "",
      relevance: relevanceByTargetId[beat.beatId] ?? "default",
      scenes,
      choices,
    };
  });
}

function admitNativeRunbookV2(input: {
  run: PlayRunRecord;
  manifest: PlayRunReferenceManifestV2;
  committed: WorkspaceCommittedRevision;
}): NativeRunbookAdmission {
  const { run, manifest, committed } = input;
  const manifestFailure = bindingMismatch(run, manifest);
  if (manifestFailure) return failed("integrity_failure", manifestFailure);

  if (hasBlockingMarkdownImportDiagnostics(committed.markdown)) {
    return failed("integrity_failure", "bound Runbook Markdown failed P1 admission");
  }

  const imported = markdownToTiptapDoc(committed.markdown);
  const indexed = indexPlayableStructureV2(imported.doc);
  if (indexed.status === "blocked") {
    return failed("integrity_failure", "bound Runbook failed v2 Playable structure indexing");
  }

  const membershipFailure = compareV2Membership(indexed.index, manifest);
  if (membershipFailure) return failed("integrity_failure", membershipFailure);

  const openingBeatId = deriveV2OpeningBeatId(indexed.index);
  if (openingBeatId == null) {
    return failed("integrity_failure", "v2 Playable has no Beat; native READY is fail-closed");
  }

  const currentBeatId = run.progress.current_beat_id;
  if (currentBeatId == null) {
    return failed(
      "integrity_failure",
      "v2 READY requires a durable current_beat_id",
    );
  }

  const knownBeats = new Set(indexed.index.beatOrder);
  if (!knownBeats.has(currentBeatId)) {
    return failed("integrity_failure", "current_beat_id is not admitted by the sealed v2 Playable");
  }

  const currentSceneId = run.progress.current_scene_id;
  if (currentSceneId != null) {
    const scene = indexed.index.scenes.find((entry) => entry.sceneId === currentSceneId);
    if (scene == null) {
      return failed("integrity_failure", "current_scene_id is not admitted by the sealed v2 Playable");
    }
    if (scene.beatId !== currentBeatId) {
      return failed("integrity_failure", "current_scene_id does not belong to current_beat_id");
    }
  }

  const relevanceByTargetId = deriveAuthoredRelevance(
    manifest.edges,
    run.progress.selections,
    v2RelevanceTargetIds(manifest),
  );
  const slices = slicePlayableBodies(imported.doc);
  const beats = projectV2Beats(indexed.index, slices, relevanceByTargetId);

  return {
    status: "ready",
    grammar: "v2",
    run,
    manifest,
    snapshot: snapshotFromCommitted(committed),
    importedDoc: imported.doc,
    structure: indexed.index,
    beats,
    currentBeatId,
    currentSceneId,
    openingBeatId,
    relevanceByTargetId,
  };
}

export function overlayRuntimeOnV2(
  admission: NativeRunbookReadyV2,
  run: PlayRunRecord,
): NativeRunbookReadyV2 | null {
  if (!sameAdmittedRunBinding(admission.run, run)) return null;
  const currentBeatId = run.progress.current_beat_id;
  if (currentBeatId == null) return null;
  if (!admission.structure.beatOrder.includes(currentBeatId)) return null;
  const currentSceneId = run.progress.current_scene_id;
  if (currentSceneId != null) {
    const scene = admission.structure.scenes.find((entry) => entry.sceneId === currentSceneId);
    if (scene == null || scene.beatId !== currentBeatId) return null;
  }
  const relevanceByTargetId = deriveAuthoredRelevance(
    admission.manifest.edges,
    run.progress.selections,
    v2RelevanceTargetIds(admission.manifest),
  );
  return {
    ...admission,
    run,
    beats: projectV2Beats(
      admission.structure,
      slicePlayableBodies(admission.importedDoc),
      relevanceByTargetId,
    ),
    currentBeatId,
    currentSceneId,
    relevanceByTargetId,
  };
}

export function admitNativeRunbook(input: {
  run: PlayRunRecord;
  manifest: PlayRunReferenceManifest;
  committed: WorkspaceCommittedRevision;
}): NativeRunbookAdmission {
  const { run, manifest, committed } = input;

  if (run.schema_version !== "dmb_play_run_record_v1") {
    return failed("integrity_failure", "Run schema_version is not dmb_play_run_record_v1");
  }
  if (!isCanonicalUuid(run.run_id) || !isCanonicalUuid(run.playable_artifact_id)) {
    return failed("integrity_failure", "Run identity is not a canonical UUID");
  }

  const workspaceFailure = workspaceBindingFailure(run, committed);
  if (workspaceFailure) return workspaceFailure;

  if (manifest.schema_version === "dmb_play_run_reference_manifest_v2") {
    return admitNativeRunbookV2({ run, manifest, committed });
  }
  if (manifest.schema_version !== "dmb_play_run_reference_manifest_v1") {
    return failed(
      "integrity_failure",
      "sealed reference manifest schema_version is not admitted",
    );
  }

  const manifestFailure = bindingMismatch(run, manifest);
  if (manifestFailure) return failed("integrity_failure", manifestFailure);

  if (!Array.isArray(manifest.elements)) {
    return failed("integrity_failure", "sealed reference manifest is malformed");
  }

  if (hasBlockingMarkdownImportDiagnostics(committed.markdown)) {
    return failed("integrity_failure", "bound Runbook Markdown failed P1 admission");
  }

  const imported = markdownToTiptapDoc(committed.markdown);
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
    grammar: "v1",
    run,
    manifest,
    snapshot: snapshotFromCommitted(committed),
    importedDoc: imported.doc,
    structure: indexed.index,
    scenes,
    ...displayed,
  };
}

export function manifestElementSignature(element: PlayRunReferenceElement): string {
  return membershipKey(element);
}
