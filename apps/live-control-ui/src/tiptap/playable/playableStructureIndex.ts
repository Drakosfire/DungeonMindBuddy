import {
  PLAYABLE_ELEMENT_DIAGNOSTIC,
  duplicatePlayableIds,
  validatePlayableHeadingAttrs,
  validatePlayableOptionItemAttrs,
  walkJsonNodes,
  type PlayableBeatKind,
  type PlayableElementIdentity,
} from "./playableElementIdentity";

export const PLAYABLE_STRUCTURE_DIAGNOSTIC = {
  nonDocRoot: "Playable structure index requires a TipTap document root.",
  orphanBeat: "Marked Beat has no preceding marked Scene.",
  orphanChoice: "Marked Choice has no preceding marked Scene.",
  orphanOption: "Marked Option has no active marked Choice.",
  orphanSceneV2: "Marked Scene has no preceding marked Beat.",
  orphanChoiceV2: "Marked Choice has no preceding marked Beat.",
  badSceneAssociation: "Choice scene association must reference a Scene in the same Beat.",
  badEdge: "Option transition edge targets an unknown Beat or Scene id.",
  unsupportedVersion: "Document carries a different Playable grammar version than this index.",
} as const;

export type PlayableStructureDiagnostic = {
  code:
    | "non_doc_root"
    | "invalid_identity"
    | "duplicate_identity"
    | "nested_identity"
    | "orphan_beat"
    | "orphan_choice"
    | "orphan_option"
    | "orphan_scene"
    | "bad_scene_association"
    | "bad_edge"
    | "unsupported_version";
  message: string;
  elementId?: string;
};

export type PlayableStructureScene = {
  sceneId: string;
  order: number;
  beatOrder: string[];
  choiceOrder: string[];
};

export type PlayableStructureChoice = {
  choiceId: string;
  sceneId: string;
  order: number;
  optionOrder: string[];
};

export type PlayableStructureElement =
  | { kind: "scene"; id: string; order: number }
  | { kind: "beat"; id: string; order: number; sceneId: string }
  | { kind: "choice"; id: string; order: number; sceneId: string }
  | { kind: "option"; id: string; order: number; sceneId: string; choiceId: string };

export type PlayableStructureIndex = {
  sceneOrder: string[];
  scenes: PlayableStructureScene[];
  choices: PlayableStructureChoice[];
  elements: PlayableStructureElement[];
};

export type PlayableStructureIndexResult =
  | { status: "ready"; index: PlayableStructureIndex }
  | { status: "blocked"; diagnostics: PlayableStructureDiagnostic[] };

function isTiptapDocument(document: unknown): document is { type: "doc"; content?: unknown } {
  return document !== null
    && typeof document === "object"
    && (document as { type?: unknown }).type === "doc";
}

function headingElementId(attrs: unknown): string | undefined {
  const id = (attrs as { playableElementId?: unknown } | null | undefined)?.playableElementId;
  return typeof id === "string" && id.length > 0 ? id : undefined;
}

function emptyIndex(): PlayableStructureIndex {
  return { sceneOrder: [], scenes: [], choices: [], elements: [] };
}

function blocked(diagnostics: PlayableStructureDiagnostic[]): PlayableStructureIndexResult {
  return { status: "blocked", diagnostics };
}

function collectMembershipDiagnostics(
  identities: readonly PlayableElementIdentity[],
): PlayableStructureDiagnostic[] {
  const diagnostics: PlayableStructureDiagnostic[] = [];
  let currentSceneId: string | null = null;
  let currentChoiceId: string | null = null;

  for (const identity of identities) {
    switch (identity.kind) {
      case "scene":
        currentSceneId = identity.id;
        currentChoiceId = null;
        break;
      case "beat":
        if (currentSceneId == null) {
          diagnostics.push({
            code: "orphan_beat",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanBeat,
            elementId: identity.id,
          });
        }
        currentChoiceId = null;
        break;
      case "choice":
        if (currentSceneId == null) {
          diagnostics.push({
            code: "orphan_choice",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanChoice,
            elementId: identity.id,
          });
          currentChoiceId = null;
          break;
        }
        currentChoiceId = identity.id;
        break;
      case "option":
        if (currentSceneId == null || currentChoiceId == null) {
          diagnostics.push({
            code: "orphan_option",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanOption,
            elementId: identity.id,
          });
        }
        break;
    }
  }

  return diagnostics;
}

function buildReadyIndex(identities: readonly PlayableElementIdentity[]): PlayableStructureIndex {
  const index = emptyIndex();
  let currentSceneId: string | null = null;
  let currentChoice: PlayableStructureChoice | null = null;

  for (const identity of identities) {
    switch (identity.kind) {
      case "scene": {
        currentSceneId = identity.id;
        currentChoice = null;
        index.sceneOrder.push(identity.id);
        index.scenes.push({
          sceneId: identity.id,
          order: index.scenes.length,
          beatOrder: [],
          choiceOrder: [],
        });
        index.elements.push({
          kind: "scene",
          id: identity.id,
          order: index.elements.length,
        });
        break;
      }
      case "beat": {
        const scene = index.scenes[index.scenes.length - 1];
        if (currentSceneId == null || scene == null) {
          throw new Error("Playable structure index reached a Beat without a current Scene after validation.");
        }
        currentChoice = null;
        scene.beatOrder.push(identity.id);
        index.elements.push({
          kind: "beat",
          id: identity.id,
          order: index.elements.length,
          sceneId: currentSceneId,
        });
        break;
      }
      case "choice": {
        const scene = index.scenes[index.scenes.length - 1];
        if (currentSceneId == null || scene == null) {
          throw new Error("Playable structure index reached a Choice without a current Scene after validation.");
        }
        scene.choiceOrder.push(identity.id);
        currentChoice = {
          choiceId: identity.id,
          sceneId: currentSceneId,
          order: index.choices.length,
          optionOrder: [],
        };
        index.choices.push(currentChoice);
        index.elements.push({
          kind: "choice",
          id: identity.id,
          order: index.elements.length,
          sceneId: currentSceneId,
        });
        break;
      }
      case "option": {
        if (currentSceneId == null || currentChoice == null) {
          throw new Error("Playable structure index reached an Option without an active Choice after validation.");
        }
        currentChoice.optionOrder.push(identity.id);
        index.elements.push({
          kind: "option",
          id: identity.id,
          order: index.elements.length,
          sceneId: currentSceneId,
          choiceId: currentChoice.choiceId,
        });
        break;
      }
    }
  }

  return index;
}

type CollectedIdentities = {
  identities: PlayableElementIdentity[];
  diagnostics: PlayableStructureDiagnostic[];
};

/** Collect versioned playable identities (v1/v2 headings, v2 option list items)
 * in document order with placement/validity diagnostics. */
function collectVersionedIdentities(document: unknown): CollectedIdentities {
  const diagnostics: PlayableStructureDiagnostic[] = [];
  const identities: PlayableElementIdentity[] = [];

  const rootLists = new Set<object>();
  if (document !== null && typeof document === "object") {
    const rootContent = (document as { content?: unknown }).content;
    if (Array.isArray(rootContent)) {
      for (const child of rootContent) {
        if (child === null || typeof child !== "object") continue;
        const childType = (child as { type?: unknown }).type;
        if (childType === "bulletList" || childType === "orderedList") {
          rootLists.add(child);
        }
      }
    }
  }

  walkJsonNodes(document, (node, parentType, parentNode) => {
    if (node.type === "heading") {
      const validated = validatePlayableHeadingAttrs(node.attrs);
      if (validated.status === "absent") return;

      const elementId = headingElementId(node.attrs);
      if (parentType !== "doc") {
        diagnostics.push({
          code: "nested_identity",
          message: PLAYABLE_ELEMENT_DIAGNOSTIC.nested,
          ...(elementId ? { elementId } : {}),
        });
        return;
      }
      if (validated.status === "invalid") {
        diagnostics.push({
          code: "invalid_identity",
          message: validated.reason,
          ...(elementId ? { elementId } : {}),
        });
        return;
      }
      identities.push(validated.identity);
      return;
    }
    if (node.type !== "listItem") return;
    const validated = validatePlayableOptionItemAttrs(node.attrs);
    if (validated.status === "absent") return;
    const elementId = headingElementId(node.attrs);
    if (parentNode === null || !rootLists.has(parentNode)) {
      diagnostics.push({
        code: "nested_identity",
        message: PLAYABLE_ELEMENT_DIAGNOSTIC.nestedOption,
        ...(elementId ? { elementId } : {}),
      });
      return;
    }
    if (validated.status === "invalid") {
      diagnostics.push({
        code: "invalid_identity",
        message: validated.reason,
        ...(elementId ? { elementId } : {}),
      });
      return;
    }
    identities.push(validated.identity);
  });

  for (const id of duplicatePlayableIds(identities)) {
    diagnostics.push({
      code: "duplicate_identity",
      message: PLAYABLE_ELEMENT_DIAGNOSTIC.duplicateAttrs,
      elementId: id,
    });
  }
  return { identities, diagnostics };
}

export function indexPlayableStructure(document: unknown): PlayableStructureIndexResult {
  if (!isTiptapDocument(document)) {
    return blocked([{
      code: "non_doc_root",
      message: PLAYABLE_STRUCTURE_DIAGNOSTIC.nonDocRoot,
    }]);
  }

  const { identities, diagnostics } = collectVersionedIdentities(document);

  // v1 index is v1-only: v2 structural identities fail closed here so a
  // Beat-first document can never be misread through the Scene-first index.
  for (const identity of identities) {
    if (identity.version === "v2") {
      diagnostics.push({
        code: "unsupported_version",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.unsupportedVersion,
        elementId: identity.id,
      });
    }
  }

  diagnostics.push(...collectMembershipDiagnostics(identities));

  if (diagnostics.length > 0) {
    return blocked(diagnostics);
  }
  return { status: "ready", index: buildReadyIndex(identities) };
}

// ---------------------------------------------------------------------------
// Beat-first (v2) structure index
// ---------------------------------------------------------------------------

export type PlayableStructureBeatV2 = {
  beatId: string;
  beatKind: PlayableBeatKind | null;
  /** Document-order projection derived from the admitted document bytes. */
  order: number;
  sceneOrder: string[];
  choiceOrder: string[];
};

export type PlayableStructureSceneV2 = {
  sceneId: string;
  beatId: string;
  order: number;
};

export type PlayableStructureChoiceV2 = {
  choiceId: string;
  beatId: string;
  sceneId: string | null;
  order: number;
  optionOrder: string[];
};

export type PlayableStructureOptionV2 = {
  optionId: string;
  choiceId: string;
  order: number;
  activates: string[];
  suppresses: string[];
};

export type PlayableStructureElementV2 =
  | { kind: "beat"; id: string; order: number; beatKind: PlayableBeatKind | null }
  | { kind: "scene"; id: string; order: number; beatId: string }
  | { kind: "choice"; id: string; order: number; beatId: string; sceneId: string | null }
  | { kind: "option"; id: string; order: number; choiceId: string };

export type PlayableStructureIndexV2 = {
  beatOrder: string[];
  beats: PlayableStructureBeatV2[];
  scenes: PlayableStructureSceneV2[];
  choices: PlayableStructureChoiceV2[];
  options: PlayableStructureOptionV2[];
  elements: PlayableStructureElementV2[];
};

export type PlayableStructureIndexV2Result =
  | { status: "ready"; index: PlayableStructureIndexV2 }
  | { status: "blocked"; diagnostics: PlayableStructureDiagnostic[] };

function emptyIndexV2(): PlayableStructureIndexV2 {
  return { beatOrder: [], beats: [], scenes: [], choices: [], options: [], elements: [] };
}

export function indexPlayableStructureV2(document: unknown): PlayableStructureIndexV2Result {
  if (!isTiptapDocument(document)) {
    return {
      status: "blocked",
      diagnostics: [{
        code: "non_doc_root",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.nonDocRoot,
      }],
    };
  }

  const { identities, diagnostics } = collectVersionedIdentities(document);

  // v2 index is v2-only: any v1 structural identity means a mixed document,
  // which fails closed rather than being read through the wrong grammar.
  for (const identity of identities) {
    if (identity.version !== "v2") {
      diagnostics.push({
        code: "unsupported_version",
        message: PLAYABLE_STRUCTURE_DIAGNOSTIC.unsupportedVersion,
        elementId: identity.id,
      });
    }
  }
  if (diagnostics.length > 0) {
    return { status: "blocked", diagnostics };
  }

  const index = emptyIndexV2();
  let currentBeat: PlayableStructureBeatV2 | null = null;
  let currentChoice: PlayableStructureChoiceV2 | null = null;
  let scenesInCurrentBeat: Set<string> = new Set();
  const pendingEdges: { optionId: string; targets: string[] }[] = [];

  for (const identity of identities) {
    switch (identity.kind) {
      case "beat": {
        currentBeat = {
          beatId: identity.id,
          beatKind: identity.beatKind ?? null,
          order: index.beats.length,
          sceneOrder: [],
          choiceOrder: [],
        };
        currentChoice = null;
        scenesInCurrentBeat = new Set();
        index.beats.push(currentBeat);
        index.beatOrder.push(identity.id);
        index.elements.push({
          kind: "beat",
          id: identity.id,
          order: index.elements.length,
          beatKind: currentBeat.beatKind,
        });
        break;
      }
      case "scene": {
        if (currentBeat === null) {
          diagnostics.push({
            code: "orphan_scene",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanSceneV2,
            elementId: identity.id,
          });
          break;
        }
        currentChoice = null;
        scenesInCurrentBeat.add(identity.id);
        currentBeat.sceneOrder.push(identity.id);
        index.scenes.push({
          sceneId: identity.id,
          beatId: currentBeat.beatId,
          order: index.scenes.length,
        });
        index.elements.push({
          kind: "scene",
          id: identity.id,
          order: index.elements.length,
          beatId: currentBeat.beatId,
        });
        break;
      }
      case "choice": {
        if (currentBeat === null) {
          diagnostics.push({
            code: "orphan_choice",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanChoiceV2,
            elementId: identity.id,
          });
          break;
        }
        const sceneRef = identity.sceneId ?? null;
        if (sceneRef !== null && !scenesInCurrentBeat.has(sceneRef)) {
          diagnostics.push({
            code: "bad_scene_association",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.badSceneAssociation,
            elementId: identity.id,
          });
          break;
        }
        currentChoice = {
          choiceId: identity.id,
          beatId: currentBeat.beatId,
          sceneId: sceneRef,
          order: index.choices.length,
          optionOrder: [],
        };
        currentBeat.choiceOrder.push(identity.id);
        index.choices.push(currentChoice);
        index.elements.push({
          kind: "choice",
          id: identity.id,
          order: index.elements.length,
          beatId: currentBeat.beatId,
          sceneId: sceneRef,
        });
        break;
      }
      case "option": {
        if (currentChoice === null) {
          diagnostics.push({
            code: "orphan_option",
            message: PLAYABLE_STRUCTURE_DIAGNOSTIC.orphanOption,
            elementId: identity.id,
          });
          break;
        }
        currentChoice.optionOrder.push(identity.id);
        index.options.push({
          optionId: identity.id,
          choiceId: currentChoice.choiceId,
          order: index.options.length,
          activates: [...(identity.activates ?? [])],
          suppresses: [...(identity.suppresses ?? [])],
        });
        index.elements.push({
          kind: "option",
          id: identity.id,
          order: index.elements.length,
          choiceId: currentChoice.choiceId,
        });
        pendingEdges.push({
          optionId: identity.id,
          targets: [...(identity.activates ?? []), ...(identity.suppresses ?? [])],
        });
        break;
      }
    }
  }

  if (diagnostics.length > 0) {
    return { status: "blocked", diagnostics };
  }

  const knownIds = new Set([
    ...index.beatOrder,
    ...index.scenes.map((scene) => scene.sceneId),
  ]);
  for (const edge of pendingEdges) {
    for (const target of edge.targets) {
      if (!knownIds.has(target)) {
        diagnostics.push({
          code: "bad_edge",
          message: PLAYABLE_STRUCTURE_DIAGNOSTIC.badEdge,
          elementId: edge.optionId,
        });
      }
    }
  }

  if (diagnostics.length > 0) {
    return { status: "blocked", diagnostics };
  }
  return { status: "ready", index };
}
