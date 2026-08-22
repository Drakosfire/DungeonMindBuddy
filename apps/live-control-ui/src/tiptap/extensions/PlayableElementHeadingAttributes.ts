import { Extension } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Mapping } from "@tiptap/pm/transform";

import {
  generatePlayableElementId,
  headingLevelForPlayableKind,
  headingLevelForPlayableKindV2,
  isCanonicalPlayableElementId,
  isPlayableBeatKind,
  isPlayableElementKind,
  isPlayableElementVersion,
  PLAYABLE_ACTIVATES_HTML_ATTR,
  PLAYABLE_BEAT_KIND_HTML_ATTR,
  PLAYABLE_ELEMENT_ID_HTML_ATTR,
  PLAYABLE_ELEMENT_KIND_HTML_ATTR,
  PLAYABLE_ELEMENT_VERSION_HTML_ATTR,
  PLAYABLE_SCENE_ID_HTML_ATTR,
  PLAYABLE_SUPPRESSES_HTML_ATTR,
  type PlayableElementKind,
  type PlayableElementVersion,
} from "../playable/playableElementIdentity";

const playableHeadingIntegrityKey = new PluginKey("playableHeadingIntegrity");

function playableKindOf(node: ProseMirrorNode): PlayableElementKind | null {
  return node.type.name === "heading" && isPlayableElementKind(node.attrs.playableElementKind)
    ? node.attrs.playableElementKind
    : null;
}

function playableIdOf(node: ProseMirrorNode): string | null {
  const id = node.attrs.playableElementId;
  return typeof id === "string" && id ? id : null;
}

function playableVersionOf(node: ProseMirrorNode): PlayableElementVersion {
  const version = node.attrs.playableElementVersion;
  return isPlayableElementVersion(version) ? version : "v1";
}

function expectedLevelFor(node: ProseMirrorNode, kind: PlayableElementKind): number | null {
  return playableVersionOf(node) === "v2"
    ? headingLevelForPlayableKindV2(kind)
    : headingLevelForPlayableKind(kind);
}

/** v2 Options live on list items; every other kind stays on headings. */
function playableOptionKindOf(node: ProseMirrorNode): "option" | null {
  return node.type.name === "listItem" && node.attrs.playableElementKind === "option"
    ? "option"
    : null;
}

function parseEdgeListAttr(element: HTMLElement, attr: string): string[] | null {
  const raw = element.getAttribute(attr);
  if (raw === null) return null;
  if (raw.trim() === "") return null;
  const ids = raw.split(",").map((entry) => entry.trim()).filter(Boolean);
  const valid = ids.every(
    (id) => isCanonicalPlayableElementId("beat", id) || isCanonicalPlayableElementId("scene", id),
  );
  return valid ? ids : null;
}

function renderEdgeListAttr(value: unknown): string | null {
  if (!Array.isArray(value) || value.length === 0) return null;
  const valid = value.every(
    (id) => typeof id === "string"
      && (isCanonicalPlayableElementId("beat", id) || isCanonicalPlayableElementId("scene", id)),
  );
  return valid ? (value as string[]).join(",") : null;
}

export const PlayableElementHeadingAttributes = Extension.create({
  name: "playableElementHeadingAttributes",

  addGlobalAttributes() {
    return [
      {
        types: ["heading"],
        attributes: {
          playableElementKind: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const kind = element.getAttribute(PLAYABLE_ELEMENT_KIND_HTML_ATTR);
              return isPlayableElementKind(kind) ? kind : null;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              if (!isPlayableElementKind(attributes.playableElementKind)) return {};
              return { [PLAYABLE_ELEMENT_KIND_HTML_ATTR]: attributes.playableElementKind };
            },
          },
          playableElementId: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const kind = element.getAttribute(PLAYABLE_ELEMENT_KIND_HTML_ATTR);
              const id = element.getAttribute(PLAYABLE_ELEMENT_ID_HTML_ATTR);
              if (!isPlayableElementKind(kind) || !id || !isCanonicalPlayableElementId(kind, id)) {
                return null;
              }
              return id;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              const kind = attributes.playableElementKind;
              const id = attributes.playableElementId;
              if (!isPlayableElementKind(kind) || typeof id !== "string" || !isCanonicalPlayableElementId(kind, id)) {
                return {};
              }
              return { [PLAYABLE_ELEMENT_ID_HTML_ATTR]: id };
            },
          },
          playableElementVersion: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const version = element.getAttribute(PLAYABLE_ELEMENT_VERSION_HTML_ATTR);
              return isPlayableElementVersion(version) ? version : null;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              const version = attributes.playableElementVersion;
              if (!isPlayableElementVersion(version)) return {};
              return { [PLAYABLE_ELEMENT_VERSION_HTML_ATTR]: version };
            },
          },
          playableBeatKind: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const beatKind = element.getAttribute(PLAYABLE_BEAT_KIND_HTML_ATTR);
              return isPlayableBeatKind(beatKind) ? beatKind : null;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              const beatKind = attributes.playableBeatKind;
              if (!isPlayableBeatKind(beatKind)) return {};
              return { [PLAYABLE_BEAT_KIND_HTML_ATTR]: beatKind };
            },
          },
          playableSceneId: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const sceneId = element.getAttribute(PLAYABLE_SCENE_ID_HTML_ATTR);
              return typeof sceneId === "string" && isCanonicalPlayableElementId("scene", sceneId)
                ? sceneId
                : null;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              const sceneId = attributes.playableSceneId;
              if (typeof sceneId !== "string" || !isCanonicalPlayableElementId("scene", sceneId)) {
                return {};
              }
              return { [PLAYABLE_SCENE_ID_HTML_ATTR]: sceneId };
            },
          },
        },
      },
      {
        // v2 Options are marked list items (Beat-first grammar). Identity and
        // transition edges ride on the listItem node; the Markdown serializer
        // emits the option marker immediately before the item line.
        types: ["listItem"],
        attributes: {
          playableElementKind: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const kind = element.getAttribute(PLAYABLE_ELEMENT_KIND_HTML_ATTR);
              return kind === "option" ? "option" : null;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              return attributes.playableElementKind === "option"
                ? { [PLAYABLE_ELEMENT_KIND_HTML_ATTR]: "option" }
                : {};
            },
          },
          playableElementId: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const kind = element.getAttribute(PLAYABLE_ELEMENT_KIND_HTML_ATTR);
              const id = element.getAttribute(PLAYABLE_ELEMENT_ID_HTML_ATTR);
              if (kind !== "option" || !id || !isCanonicalPlayableElementId("option", id)) {
                return null;
              }
              return id;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              const id = attributes.playableElementId;
              if (attributes.playableElementKind !== "option") return {};
              if (typeof id !== "string" || !isCanonicalPlayableElementId("option", id)) {
                return {};
              }
              return { [PLAYABLE_ELEMENT_ID_HTML_ATTR]: id };
            },
          },
          playableElementVersion: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) => {
              const version = element.getAttribute(PLAYABLE_ELEMENT_VERSION_HTML_ATTR);
              return isPlayableElementVersion(version) ? version : null;
            },
            renderHTML: (attributes: Record<string, unknown>) => {
              const version = attributes.playableElementVersion;
              if (!isPlayableElementVersion(version)) return {};
              return { [PLAYABLE_ELEMENT_VERSION_HTML_ATTR]: version };
            },
          },
          playableActivates: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) =>
              parseEdgeListAttr(element, PLAYABLE_ACTIVATES_HTML_ATTR),
            renderHTML: (attributes: Record<string, unknown>) => {
              const joined = renderEdgeListAttr(attributes.playableActivates);
              return joined ? { [PLAYABLE_ACTIVATES_HTML_ATTR]: joined } : {};
            },
          },
          playableSuppresses: {
            default: null,
            keepOnSplit: false,
            parseHTML: (element: HTMLElement) =>
              parseEdgeListAttr(element, PLAYABLE_SUPPRESSES_HTML_ATTR),
            renderHTML: (attributes: Record<string, unknown>) => {
              const joined = renderEdgeListAttr(attributes.playableSuppresses);
              return joined ? { [PLAYABLE_SUPPRESSES_HTML_ATTR]: joined } : {};
            },
          },
        },
      },
    ];
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: playableHeadingIntegrityKey,
        appendTransaction(transactions, oldState, newState) {
          if (!transactions.some((transaction) => transaction.docChanged)) return null;

          const mapping = new Mapping();
          for (const transaction of transactions) {
            mapping.appendMapping(transaction.mapping);
          }
          const kindOfAny = (node: ProseMirrorNode): PlayableElementKind | null =>
            playableKindOf(node) ?? playableOptionKindOf(node);

          const mappedOwnerById = new Map<string, number>();
          oldState.doc.descendants((node, pos) => {
            const kind = kindOfAny(node);
            const id = playableIdOf(node);
            if (!kind || !id || mappedOwnerById.has(id)) return;
            mappedOwnerById.set(id, mapping.map(pos));
          });

          const newCounts = new Map<string, number>();
          newState.doc.descendants((node) => {
            const id = playableIdOf(node);
            if (!id || !kindOfAny(node)) return;
            newCounts.set(id, (newCounts.get(id) ?? 0) + 1);
          });

          let transaction = newState.tr;
          let changed = false;
          newState.doc.descendants((node, pos) => {
            if (node.type.name !== "heading" && node.type.name !== "listItem") return;
            const kind = kindOfAny(node);
            const id = playableIdOf(node);
            if (!kind && !id) return;

            const nextAttrs = { ...node.attrs };
            let nextKind = kind;
            if (nextKind && node.type.name === "heading") {
              const expectedLevel = expectedLevelFor(node, nextKind);
              if (expectedLevel !== null && nextAttrs.level !== expectedLevel) {
                nextAttrs.level = expectedLevel;
              }
            }

            if (nextKind && id && (newCounts.get(id) ?? 0) > 1 && mappedOwnerById.has(id)) {
              const ownerPos = mappedOwnerById.get(id);
              if (ownerPos !== pos) {
                nextAttrs.playableElementKind = nextKind;
                nextAttrs.playableElementId = generatePlayableElementId(nextKind);
              }
            }

            if (
              nextAttrs.level !== node.attrs.level
              || nextAttrs.playableElementId !== node.attrs.playableElementId
            ) {
              transaction = transaction.setNodeMarkup(pos, undefined, nextAttrs);
              changed = true;
            }
          });
          return changed ? transaction : null;
        },
      }),
    ];
  },
});
