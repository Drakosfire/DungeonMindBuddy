import {
  validatePlayableOptionItemAttrs,
  walkJsonNodes,
  type PlayableElementKind,
} from "../../tiptap/playable/playableElementIdentity";
import {
  isSupportedRunbookReference,
  normalizeRunbookReferenceAttrs,
  runbookReferenceClasses,
} from "../../tiptap/references/runbookReferences";

export type PlayableBodyChip = {
  key: string;
  label: string;
  className: string;
};

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

function playableOptionListItemIdentity(node: unknown): { id: string } | null {
  if (node == null || typeof node !== "object") return null;
  const record = node as { type?: unknown; attrs?: unknown };
  if (record.type !== "listItem") return null;
  const validated = validatePlayableOptionItemAttrs(
    record.attrs as Parameters<typeof validatePlayableOptionItemAttrs>[0],
  );
  if (validated.status !== "canonical") return null;
  return { id: validated.identity.id };
}

function collectChipsFromNodes(nodes: unknown[]): PlayableBodyChip[] {
  const seen = new Set<string>();
  const chips: PlayableBodyChip[] = [];
  for (const node of nodes) {
    walkJsonNodes(node, (candidate) => {
      const type = candidate.type;
      const attrs = (candidate.attrs ?? {}) as Record<string, unknown>;
      if (type === "runbookReference") {
        const normalized = normalizeRunbookReferenceAttrs(attrs, { labelSource: "semantic" });
        if (!isSupportedRunbookReference(normalized) || normalized.label.length === 0) return;
        const key = `${normalized.kind}:${normalized.refType}:${normalized.refId}`;
        if (seen.has(key)) return;
        seen.add(key);
        chips.push({
          key,
          label: normalized.label,
          className: runbookReferenceClasses(normalized),
        });
        return;
      }
      if (type === "graphNodeReference") {
        const nodeId = typeof attrs.nodeId === "string" ? attrs.nodeId : "";
        const label = (typeof attrs.label === "string" ? attrs.label : nodeId).trim();
        if (nodeId.length === 0 || label.length === 0) return;
        const key = `graph:${nodeId}`;
        if (seen.has(key)) return;
        seen.add(key);
        chips.push({
          key,
          label,
          className: "md-ref-chip md-ref-chip-graph-node graph-node-reference-pill",
        });
      }
    });
  }
  return chips;
}

/**
 * Authored graph/corpus chips in a Playable element's body. Matches
 * `slicePlayableBodies` ownership so Option lists do not leak into Scene/Beat.
 */
export function collectPlayableBodyChips(document: unknown, elementId: string): PlayableBodyChip[] {
  if (document == null || typeof document !== "object") return [];
  const content = (document as { content?: unknown }).content;
  if (!Array.isArray(content)) return [];

  let current: { id: string; bodyNodes: unknown[] } | null = null;
  let matched: unknown[] | null = null;

  const flush = () => {
    if (current && current.id === elementId) matched = current.bodyNodes;
  };

  for (const node of content) {
    const identity = playableHeadingIdentity(node);
    if (identity) {
      flush();
      current = { id: identity.id, bodyNodes: [] };
      continue;
    }
    if (isOrdinaryRootInstructionHeading(node)) {
      flush();
      current = null;
      continue;
    }
    if (node != null && typeof node === "object") {
      const record = node as { type?: unknown; content?: unknown };
      if (
        (record.type === "bulletList" || record.type === "orderedList")
        && Array.isArray(record.content)
      ) {
        const unmarkedItems: unknown[] = [];
        let sawOption = false;
        for (const item of record.content) {
          const option = playableOptionListItemIdentity(item);
          if (option) {
            sawOption = true;
            if (option.id === elementId) {
              const children = Array.isArray((item as { content?: unknown }).content)
                ? (item as { content: unknown[] }).content
                : [];
              return collectChipsFromNodes(children.slice(1));
            }
            continue;
          }
          unmarkedItems.push(item);
        }
        if (sawOption) {
          if (current && unmarkedItems.length > 0) current.bodyNodes.push(...unmarkedItems);
          continue;
        }
      }
    }
    if (current) current.bodyNodes.push(node);
  }
  flush();
  return matched ? collectChipsFromNodes(matched) : [];
}
