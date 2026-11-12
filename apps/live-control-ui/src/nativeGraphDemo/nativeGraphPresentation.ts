import type { NativeGraphNode } from "./nativeGraphDemoApi";

const DISPLAY_KINDS: Readonly<Record<string, string>> = {
  "dnd5e:npc": "npc",
  "dnd5e:pc": "pc",
  "dnd5e:player_character": "pc",
  "dnd5e:item": "item",
  "dungeonbuddy:item": "item",
  "dnd5e:event": "event",
  "dungeonbuddy:event": "event",
  "dnd5e:location": "location",
  "dungeonbuddy:character": "character (role unspecified)",
  "dungeonbuddy:session_beat": "session beat",
};

/** Read-only labels, never a source for create kinds or identity decisions. */
export function nativeGraphPresentation(node: NativeGraphNode): {
  displayName: string;
  displayKind: string;
  recordedNames: readonly string[];
  classificationTerms: readonly string[];
} {
  // Code-unit sorting is deterministic and retains case/spacing distinctions.
  const recordedNames = [...new Set(node.presentation?.recorded_names ?? [])].sort();
  const classificationTerms = [...new Set(node.presentation?.classification_terms ?? [])].sort();
  const visibleNames = recordedNames.filter((name) => name.trim().length > 0);
  const displayName = visibleNames.length === 0 ? node.name
    : visibleNames.slice(0, 2).join(" / ") + (visibleNames.length > 2 ? ` (+${visibleNames.length - 2} more)` : "");
  const displayKind = !node.presentation ? node.kind
    : classificationTerms.length > 1 ? "object (mixed classifications)"
      : classificationTerms.length === 0 ? "object (classification unspecified)"
        : Object.hasOwn(DISPLAY_KINDS, classificationTerms[0]!)
          ? DISPLAY_KINDS[classificationTerms[0]!]!
          : "object (unsupported classification)";
  return { displayName, displayKind, recordedNames, classificationTerms };
}
