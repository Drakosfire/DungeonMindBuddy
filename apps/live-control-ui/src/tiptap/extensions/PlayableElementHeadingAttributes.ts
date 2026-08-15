import { Extension } from "@tiptap/core";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Mapping } from "@tiptap/pm/transform";

import {
  generatePlayableElementId,
  headingLevelForPlayableKind,
  isPlayableElementKind,
  type PlayableElementKind,
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
            rendered: false,
          },
          playableElementId: {
            default: null,
            keepOnSplit: false,
            rendered: false,
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
          const mappedOwnerById = new Map<string, number>();
          oldState.doc.descendants((node, pos) => {
            const kind = playableKindOf(node);
            const id = playableIdOf(node);
            if (!kind || !id || mappedOwnerById.has(id)) return;
            mappedOwnerById.set(id, mapping.map(pos));
          });

          const newCounts = new Map<string, number>();
          newState.doc.descendants((node) => {
            const id = playableIdOf(node);
            if (!id || !playableKindOf(node)) return;
            newCounts.set(id, (newCounts.get(id) ?? 0) + 1);
          });

          let transaction = newState.tr;
          let changed = false;
          newState.doc.descendants((node, pos) => {
            if (node.type.name !== "heading") return;
            const kind = playableKindOf(node);
            const id = playableIdOf(node);
            if (!kind && !id) return;

            const nextAttrs = { ...node.attrs };
            let nextKind = kind;
            if (nextKind) {
              const expectedLevel = headingLevelForPlayableKind(nextKind);
              if (nextAttrs.level !== expectedLevel) {
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
