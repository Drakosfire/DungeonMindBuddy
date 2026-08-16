import {
  PLAYABLE_ELEMENT_DIAGNOSTIC,
  duplicatePlayableIds,
  validatePlayableHeadingAttrs,
  walkJsonNodes,
  type PlayableElementIdentity,
} from "./playableElementIdentity";

export const PLAYABLE_STRUCTURE_DIAGNOSTIC = {
  nonDocRoot: "Playable structure index requires a TipTap document root.",
  orphanBeat: "Marked Beat has no preceding marked Scene.",
  orphanChoice: "Marked Choice has no preceding marked Scene.",
  orphanOption: "Marked Option has no active marked Choice.",
} as const;

export type PlayableStructureDiagnostic = {
  code:
    | "non_doc_root"
    | "invalid_identity"
    | "duplicate_identity"
    | "nested_identity"
    | "orphan_beat"
    | "orphan_choice"
    | "orphan_option";
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

export function indexPlayableStructure(document: unknown): PlayableStructureIndexResult {
  if (!isTiptapDocument(document)) {
    return blocked([{
      code: "non_doc_root",
      message: PLAYABLE_STRUCTURE_DIAGNOSTIC.nonDocRoot,
    }]);
  }

  const diagnostics: PlayableStructureDiagnostic[] = [];
  const rootIdentities: PlayableElementIdentity[] = [];

  walkJsonNodes(document, (node, parentType) => {
    if (node.type !== "heading") return;
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

    rootIdentities.push(validated.identity);
  });

  for (const id of duplicatePlayableIds(rootIdentities)) {
    diagnostics.push({
      code: "duplicate_identity",
      message: PLAYABLE_ELEMENT_DIAGNOSTIC.duplicateAttrs,
      elementId: id,
    });
  }

  diagnostics.push(...collectMembershipDiagnostics(rootIdentities));

  if (diagnostics.length > 0) {
    return blocked(diagnostics);
  }
  return { status: "ready", index: buildReadyIndex(rootIdentities) };
}
