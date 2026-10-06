import { Editor, type JSONContent } from "@tiptap/core";

import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "../../tiptap/markdown/semanticMarkdownSafety";
import {
  formatPlayableElementMarker,
  isCanonicalPlayableElementId,
  playableSerializationFailures,
  validatePlayableHeadingAttrs,
  validatePlayableOptionItemAttrs,
  type PlayableElementKind,
  type PlayableElementVersion,
} from "../../tiptap/playable/playableElementIdentity";

export type PlayableBodyTarget = { kind: PlayableElementKind; id: string };
export type PlayableBodyScope = "heading_body" | "beat_direct_body" | "option_item_content";

export interface CapturedPlayableBodyRange {
  target: PlayableBodyTarget;
  markerGrammarVersion: PlayableElementVersion;
  bodyScope: PlayableBodyScope;
  rangeSemanticsVersion: "plan-playable-ranges-v1";
  bodySerializationVersion: "plan-playable-body-markdown-v1";
  targetBodyMarkdown: string;
  targetBodySha256: string;
  from: number;
  to: number;
  /** Root body interval for heading targets. Includes the target heading in the prefix. */
  rootStartIndex: number;
  rootEndIndex: number;
  /** Present only for a v2 top-level Option list item. */
  optionPath?: { rootIndex: number; itemIndex: number };
  /** Ordered identities for references authored inside this body. */
  protectedReferences: string[];
}

export class PlayableBodyTargetError extends Error {}

type RootEntry = { node: JSONContent; position: number; nodeSize: number };
type HeadingIdentity = { kind: PlayableElementKind; id: string; version: PlayableElementVersion };
type IndexedHeadingIdentity = HeadingIdentity & { rootIndex: number };
type OptionIdentity = { kind: "option"; id: string; version: "v2" };

function canonicalJsonValue(value: unknown, parentKey?: string): unknown {
  if (Array.isArray(value)) return value.map((item) => canonicalJsonValue(item));
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const entries = Object.entries(record)
        .filter(([key, item]) => item !== undefined
          && !(parentKey === "attrs" && item === null)
          && !(key === "content" && Array.isArray(item) && item.length === 0 && record.type === "heading"))
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, canonicalJsonValue(item, key)] as const)
        .filter(([key, item]) => !(record.type === "listItem" && key === "attrs"
          && item !== null
          && typeof item === "object"
          && !Array.isArray(item)
          && Object.keys(item).length === 0));
    return Object.fromEntries(entries);
  }
  return value;
}

function sameJson(left: unknown, right: unknown): boolean {
  return JSON.stringify(canonicalJsonValue(left)) === JSON.stringify(canonicalJsonValue(right));
}

function sameAttrs(left: unknown, right: unknown): boolean {
  return JSON.stringify(canonicalJsonValue(left, "attrs")) === JSON.stringify(canonicalJsonValue(right, "attrs"));
}

function digestHex(value: string): Promise<string> {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)).then((digest) =>
    Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join(""));
}

function headingIdentity(node: JSONContent): HeadingIdentity | null {
  if (node.type !== "heading") return null;
  const validated = validatePlayableHeadingAttrs(node.attrs);
  if (validated.status !== "canonical") return null;
  return {
    kind: validated.identity.kind,
    id: validated.identity.id,
    version: validated.identity.version ?? "v1",
  };
}

function optionIdentity(node: JSONContent): OptionIdentity | null {
  if (node.type !== "listItem") return null;
  const validated = validatePlayableOptionItemAttrs(node.attrs);
  if (validated.status !== "canonical") return null;
  return { kind: "option", id: validated.identity.id, version: "v2" };
}

function allRootIdentities(rootContent: JSONContent[]): Array<HeadingIdentity | OptionIdentity> {
  const identities: Array<HeadingIdentity | OptionIdentity> = [];
  for (const node of rootContent) {
    const heading = headingIdentity(node);
    if (heading) identities.push(heading);
    if (node.type !== "bulletList" && node.type !== "orderedList") continue;
    for (const item of node.content ?? []) {
      const option = optionIdentity(item);
      if (option) identities.push(option);
    }
  }
  return identities;
}

function hasOptionInList(node: JSONContent): boolean {
  return (node.type === "bulletList" || node.type === "orderedList")
    && (node.content ?? []).some((item) => optionIdentity(item) !== null);
}

function semanticProjection(nodes: JSONContent[] | undefined): unknown[] {
  return (nodes ?? []).map((node) => {
    const attrs = node.attrs
      ? Object.fromEntries(Object.entries(node.attrs)
        .filter(([, value]) => value !== null && value !== undefined)
        .sort(([left], [right]) => left.localeCompare(right)))
      : undefined;
    const marks = node.marks?.map((mark) => ({
      type: mark.type,
      ...(mark.attrs
        ? { attrs: Object.fromEntries(Object.entries(mark.attrs).sort(([left], [right]) => left.localeCompare(right))) }
        : {}),
    }));
    return {
      type: node.type,
      ...(node.text !== undefined
        ? { text: marks?.some((mark) => mark.type === "code") ? node.text : node.text.replace(/\s+/g, " ") }
        : {}),
      ...(attrs && Object.keys(attrs).length ? { attrs } : {}),
      ...(marks?.length ? { marks } : {}),
      ...(node.content?.length ? { content: semanticProjection(node.content) } : {}),
    };
  });
}

function protectedReferenceInventory(nodes: JSONContent[] | undefined): string[] {
  const references: string[] = [];
  const visit = (node: JSONContent) => {
    if (node.type === "graphNodeReference") {
      references.push(JSON.stringify({
        type: node.type,
        nodeId: node.attrs?.nodeId ?? null,
        label: node.attrs?.label ?? null,
      }));
    } else if (node.type === "runbookReference") {
      references.push(JSON.stringify({
        type: node.type,
        kind: node.attrs?.kind ?? null,
        refType: node.attrs?.refType ?? null,
        refId: node.attrs?.refId ?? null,
        label: node.attrs?.label ?? null,
      }));
    }
    for (const child of node.content ?? []) visit(child);
  };
  for (const node of nodes ?? []) visit(node);
  return references;
}

function bodyMarkdownFor(content: JSONContent[]): string {
  const fragment = { type: "doc", content };
  if (semanticMarkdownSerializationDiagnostics(fragment).length || playableSerializationFailures(fragment).length) {
    throw new PlayableBodyTargetError("This card body contains content that cannot be represented safely in Markdown.");
  }
  const markdown = tiptapJsonToSemanticMarkdown(fragment);
  if (markdown === "\n" || Array.from(markdown).length > 8_000) {
    throw new PlayableBodyTargetError("This card has an empty body or exceeds the 8,000-character proposal limit.");
  }
  const imported = markdownToTiptapDoc(markdown);
  if (imported.diagnostics.some((item) => item.level === "warning")
    || semanticMarkdownSerializationDiagnostics(imported.doc).length
    || tiptapJsonToSemanticMarkdown(imported.doc) !== markdown
    || JSON.stringify(semanticProjection(content)) !== JSON.stringify(semanticProjection(imported.doc.content))) {
    throw new PlayableBodyTargetError("This card body changes structure during Markdown reload and is unavailable for edit proposals.");
  }
  return markdown;
}

function resolveHeadingTarget(
  rootContent: JSONContent[],
  roots: RootEntry[],
  target: PlayableBodyTarget,
  identity: IndexedHeadingIdentity,
): Omit<CapturedPlayableBodyRange, "targetBodyMarkdown" | "targetBodySha256" | "protectedReferences"> & { bodyContent: JSONContent[] } {
  const headingIndex = identity.rootIndex;
  let bodyEndIndex = rootContent.length;
  for (let index = headingIndex + 1; index < rootContent.length; index += 1) {
    const node = rootContent[index]!;
    const marked = headingIdentity(node);
    if (marked) {
      bodyEndIndex = index;
      break;
    }
    if (node.type === "heading") {
      const validated = validatePlayableHeadingAttrs(node.attrs);
      if (validated.status === "invalid") {
        throw new PlayableBodyTargetError("A malformed Playable heading makes this card range ambiguous. Correct the marker, then select the card again.");
      }
      if (validated.status === "absent" && Number(node.attrs?.level) <= 2) {
        bodyEndIndex = index;
        break;
      }
    }
  }

  if (identity.version === "v2" && identity.kind === "choice") {
    const optionListIndexes = rootContent
      .slice(headingIndex + 1, bodyEndIndex)
      .flatMap((node, offset) => hasOptionInList(node) ? [headingIndex + 1 + offset] : []);
    if (optionListIndexes.length) {
      const firstOptionList = optionListIndexes[0]!;
      const allTrailing = optionListIndexes.every((index, offset) =>
        offset === 0 || index === optionListIndexes[offset - 1]! + 1)
        && optionListIndexes.at(-1) === bodyEndIndex - 1;
      const listsAreOptionsOnly = optionListIndexes.every((index) => {
        const node = rootContent[index]!;
        return (node.content ?? []).length > 0
          && (node.content ?? []).every((item) => optionIdentity(item) !== null);
      });
      if (!allTrailing || !listsAreOptionsOnly) {
        throw new PlayableBodyTargetError("This Choice body is split by marked Options and cannot be replaced as one safe range.");
      }
      bodyEndIndex = firstOptionList;
    }
  }

  const bodyContent = rootContent.slice(headingIndex + 1, bodyEndIndex);
  if (!bodyContent.length) {
    throw new PlayableBodyTargetError("This card has no editable body before its next Playable boundary.");
  }
  const from = roots[headingIndex]!.position + roots[headingIndex]!.nodeSize;
  const to = bodyEndIndex < roots.length
    ? roots[bodyEndIndex]!.position
    : roots.at(-1)!.position + roots.at(-1)!.nodeSize;
  if (bodyEndIndex <= headingIndex + 1 || to <= from) {
    throw new PlayableBodyTargetError("This card has no contiguous editable body range.");
  }
  return {
    target,
    markerGrammarVersion: identity.version,
    bodyScope: identity.version === "v2" && identity.kind === "beat" ? "beat_direct_body" : "heading_body",
    rangeSemanticsVersion: "plan-playable-ranges-v1",
    bodySerializationVersion: "plan-playable-body-markdown-v1",
    from,
    to,
    rootStartIndex: headingIndex + 1,
    rootEndIndex: bodyEndIndex,
    bodyContent,
  };
}

function editorNodeSize(node: JSONContent): number {
  if (node.type === "text") return node.text?.length ?? 0;
  if (!node.content) return 1;
  return 2 + node.content.reduce((sum, child) => sum + editorNodeSize(child), 0);
}

export async function resolvePlayableBodyTarget(
  editor: Editor,
  target: PlayableBodyTarget,
): Promise<CapturedPlayableBodyRange> {
  if (editor.isDestroyed) throw new PlayableBodyTargetError("The Plan editor is no longer mounted.");
  if (!isCanonicalPlayableElementId(target.kind, target.id)) {
    throw new PlayableBodyTargetError("The selected card identity is malformed. Select the card again.");
  }
  const document = editor.getJSON();
  if (semanticMarkdownSerializationDiagnostics(document).length || playableSerializationFailures(document).length) {
    throw new PlayableBodyTargetError("This Plan contains malformed or unsupported Playable content. Resolve it before proposing a card edit.");
  }
  const fullDraftMarkdown = tiptapJsonToSemanticMarkdown(document);
  const fullDraftRoundTrip = markdownToTiptapDoc(fullDraftMarkdown);
  if (fullDraftRoundTrip.diagnostics.some((item) => item.level === "warning")
    || semanticMarkdownSerializationDiagnostics(fullDraftRoundTrip.doc).length
    || JSON.stringify(semanticProjection(document.content)) !== JSON.stringify(semanticProjection(fullDraftRoundTrip.doc.content))) {
    throw new PlayableBodyTargetError("This Plan draft changes structure during Markdown reload and is unavailable for card edit proposals.");
  }
  const rootContent = document.content ?? [];
  const roots: RootEntry[] = [];
  editor.state.doc.forEach((node, position) => {
    roots.push({ node: node.toJSON() as JSONContent, position, nodeSize: node.nodeSize });
  });
  if (roots.length !== rootContent.length) {
    throw new PlayableBodyTargetError("The editor's Playable structure cannot be mapped to the current draft. Capture again.");
  }

  const identities = allRootIdentities(rootContent);
  const versions = new Set(identities.map((item) => item.version));
  if (versions.size !== 1) {
    throw new PlayableBodyTargetError("This Plan has mixed or missing Playable marker grammar and cannot be targeted safely.");
  }
  const grammar = identities[0]!.version;
  const matches: Array<{ kind: "heading"; rootIndex: number; identity: IndexedHeadingIdentity } | { kind: "option"; rootIndex: number; itemIndex: number; identity: OptionIdentity }> = [];
  for (const [rootIndex, node] of rootContent.entries()) {
    const heading = headingIdentity(node);
    if (heading?.kind === target.kind && heading.id === target.id) {
      matches.push({ kind: "heading", rootIndex, identity: { ...heading, rootIndex } });
    }
    if (node.type !== "bulletList" && node.type !== "orderedList") continue;
    for (const [itemIndex, item] of (node.content ?? []).entries()) {
      const option = optionIdentity(item);
      if (option?.kind === target.kind && option.id === target.id) {
        matches.push({ kind: "option", rootIndex, itemIndex, identity: option });
      }
    }
  }
  if (matches.length !== 1) {
    throw new PlayableBodyTargetError(matches.length
      ? "This card identity is duplicated in the current draft. Correct the duplicate, then select the card again."
      : "This card is no longer present in the current draft. Select the card again.");
  }

  let range: ReturnType<typeof resolveHeadingTarget>;
  let optionPath: CapturedPlayableBodyRange["optionPath"];
  if (matches[0]!.kind === "heading") {
    range = resolveHeadingTarget(rootContent, roots, target, matches[0]!.identity);
  } else {
    const match = matches[0]!;
    if (grammar !== "v2") throw new PlayableBodyTargetError("Options can be edited only with the v2 Playable grammar.");
    const root = rootContent[match.rootIndex]!;
    if ((root.content ?? []).length !== 1) {
      throw new PlayableBodyTargetError("This Option marker does not identify exactly one top-level list item.");
    }
    const item = root.content?.[match.itemIndex];
    const bodyContent = item?.content ?? [];
    if (!bodyContent.length) throw new PlayableBodyTargetError("This Option has no editable body content.");
    if (bodyContent.filter((node) => node.type === "paragraph").length > 1) {
      throw new PlayableBodyTargetError("This Option has multiple paragraphs and is unavailable for edit proposals.");
    }
    const rootNode = editor.state.doc.child(match.rootIndex);
    let itemPosition = roots[match.rootIndex]!.position + 1;
    for (let index = 0; index < match.itemIndex; index += 1) itemPosition += editorNodeSize(rootNode.child(index).toJSON() as JSONContent);
    const optionNode = rootNode.child(match.itemIndex);
    range = {
      target,
      markerGrammarVersion: "v2",
      bodyScope: "option_item_content",
      rangeSemanticsVersion: "plan-playable-ranges-v1",
      bodySerializationVersion: "plan-playable-body-markdown-v1",
      from: itemPosition + 1,
      to: itemPosition + optionNode.nodeSize - 1,
      rootStartIndex: match.rootIndex,
      rootEndIndex: match.rootIndex + 1,
      bodyContent,
    };
    optionPath = { rootIndex: match.rootIndex, itemIndex: match.itemIndex };
  }
  const targetBodyMarkdown = bodyMarkdownFor(range.bodyContent);
  return {
    target: { ...target },
    markerGrammarVersion: range.markerGrammarVersion,
    bodyScope: range.bodyScope,
    rangeSemanticsVersion: range.rangeSemanticsVersion,
    bodySerializationVersion: range.bodySerializationVersion,
    targetBodyMarkdown,
    targetBodySha256: await digestHex(targetBodyMarkdown),
    protectedReferences: protectedReferenceInventory(range.bodyContent),
    from: range.from,
    to: range.to,
    rootStartIndex: range.rootStartIndex,
    rootEndIndex: range.rootEndIndex,
    ...(optionPath ? { optionPath } : {}),
  };
}

export function samePlayableBodyTarget(
  left: CapturedPlayableBodyRange,
  right: CapturedPlayableBodyRange,
): boolean {
  return left.target.kind === right.target.kind
    && left.target.id === right.target.id
    && left.markerGrammarVersion === right.markerGrammarVersion
    && left.bodyScope === right.bodyScope
    && left.rangeSemanticsVersion === right.rangeSemanticsVersion
    && left.bodySerializationVersion === right.bodySerializationVersion
    && left.targetBodyMarkdown === right.targetBodyMarkdown
    && left.targetBodySha256 === right.targetBodySha256
    && left.from === right.from
    && left.to === right.to
    && left.rootStartIndex === right.rootStartIndex
    && left.rootEndIndex === right.rootEndIndex
    && JSON.stringify(left.protectedReferences) === JSON.stringify(right.protectedReferences)
    && JSON.stringify(left.optionPath ?? null) === JSON.stringify(right.optionPath ?? null);
}

export function playableBodyProtectedStructureMatches(
  before: JSONContent,
  after: JSONContent,
  captured: CapturedPlayableBodyRange,
): boolean {
  const beforeRoot = before.content ?? [];
  const afterRoot = after.content ?? [];
  if (!captured.optionPath) {
    const prefix = beforeRoot.slice(0, captured.rootStartIndex);
    const suffix = beforeRoot.slice(captured.rootEndIndex);
    const suffixStart = afterRoot.length - suffix.length;
    const beforeBody = beforeRoot.slice(captured.rootStartIndex, captured.rootEndIndex);
    const afterBody = afterRoot.slice(captured.rootStartIndex, suffixStart);
    return afterRoot.length >= prefix.length + suffix.length
      && sameJson(afterRoot.slice(0, prefix.length), prefix)
      && suffixStart >= prefix.length
      && sameJson(afterRoot.slice(suffixStart), suffix)
      && JSON.stringify(protectedReferenceInventory(beforeBody)) === JSON.stringify(captured.protectedReferences)
      && JSON.stringify(protectedReferenceInventory(afterBody)) === JSON.stringify(captured.protectedReferences);
  }
  const { rootIndex, itemIndex } = captured.optionPath;
  if (beforeRoot.length !== afterRoot.length) return false;
  for (let index = 0; index < beforeRoot.length; index += 1) {
    if (index !== rootIndex && !sameJson(beforeRoot[index], afterRoot[index])) return false;
  }
  const beforeList = beforeRoot[rootIndex];
  const afterList = afterRoot[rootIndex];
  if (beforeList?.type !== afterList?.type
    || !sameAttrs(beforeList?.attrs ?? null, afterList?.attrs ?? null)
    || !sameJson(beforeList?.marks ?? null, afterList?.marks ?? null)) return false;
  const beforeItems = beforeList?.content ?? [];
  const afterItems = afterList?.content ?? [];
  if (beforeItems.length !== afterItems.length) return false;
  return beforeItems.every((item, index) => {
    const candidate = afterItems[index];
    if (index !== itemIndex) return sameJson(item, candidate);
    if (!candidate || item.type !== candidate.type
      || !sameAttrs(item.attrs ?? null, candidate.attrs ?? null)
      || !sameJson(item.marks ?? null, candidate.marks ?? null)) return false;
    return JSON.stringify(protectedReferenceInventory(item.content)) === JSON.stringify(captured.protectedReferences)
      && JSON.stringify(protectedReferenceInventory(candidate.content)) === JSON.stringify(captured.protectedReferences);
  });
}

export function replacePlayableBodyInDocument(
  document: JSONContent,
  captured: CapturedPlayableBodyRange,
  content: JSONContent[],
): JSONContent {
  const rootContent = [...(document.content ?? [])];
  if (captured.optionPath) {
    const { rootIndex, itemIndex } = captured.optionPath;
    const list = rootContent[rootIndex];
    if (!list || !list.content?.[itemIndex]) throw new PlayableBodyTargetError("The selected Option range is stale. Compose again.");
    const items = [...list.content];
    items[itemIndex] = { ...items[itemIndex]!, content };
    rootContent[rootIndex] = { ...list, content: items };
  } else {
    rootContent.splice(captured.rootStartIndex, captured.rootEndIndex - captured.rootStartIndex, ...content);
  }
  return { ...document, content: rootContent };
}

export function playableTargetReceipt(captured: CapturedPlayableBodyRange) {
  return {
    schema_version: "dmb_plan_playable_target_receipt_v1" as const,
    kind: captured.target.kind,
    id: captured.target.id,
    marker_grammar_version: captured.markerGrammarVersion,
    body_scope: captured.bodyScope,
    range_semantics_version: captured.rangeSemanticsVersion,
    body_serialization_version: captured.bodySerializationVersion,
    target_body_sha256: captured.targetBodySha256,
  };
}

export function playableMarkerForTarget(target: PlayableBodyTarget, version: PlayableElementVersion): string {
  return formatPlayableElementMarker({ kind: target.kind, id: target.id, version });
}
