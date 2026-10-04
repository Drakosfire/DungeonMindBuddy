import { useMemo } from "react";
import { generateHTML, mergeAttributes, type JSONContent } from "@tiptap/core";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { GraphNodeReferenceNode } from "../../tiptap/extensions/GraphNodeReferenceNode";
import { classifyImageUrl, classifyLinkUrl } from "../../markdownReader/markdownReaderUrlPolicy";
import {
  indexPlayableStructure,
  indexPlayableStructureV2,
  type PlayableStructureElement,
  type PlayableStructureElementV2,
} from "../../tiptap/playable/playableStructureIndex";
import {
  parsePlayableHtmlComment,
  playableMarkerVersionProbe,
  PLAYABLE_ELEMENT_MARKER_PREFIX,
  type PlayableElementKind,
} from "../../tiptap/playable/playableElementIdentity";
import { slicePlayableBodies } from "../../playSurface/runbook/nativeRunbookProjection";

type ProjectionVersion = "v1" | "v2";
type ProjectionDiagnostic = { code: string; message: string };

export type WorldPlanCardBasis =
  | { status: "verified"; revision: number; contentSha256: string }
  | { status: "server-draft" }
  | { status: "unavailable" };

export type WorldPlanCardTarget = { kind: PlayableElementKind; id: string };

export function worldPlanCardTargetKey(target: WorldPlanCardTarget): string {
  return `${target.kind}\u001f${target.id}`;
}

export type WorldPlanCardNode = {
  id: string;
  kind: "scene" | "beat" | "choice" | "option";
  title: string;
  titleContent: JSONContent[];
  bodyText: string;
  bodyContent: JSONContent[];
  order: number;
  parentId: string | null;
  children: WorldPlanCardNode[];
  beatKind?: string | null;
  sceneId?: string | null;
  activates?: string[];
  suppresses?: string[];
};

const StaticGraphNodeReferenceNode = GraphNodeReferenceNode.extend({
  renderHTML({ node, HTMLAttributes }) {
    const attrs = node.attrs as { nodeId?: unknown; label?: unknown };
    const nodeId = typeof attrs.nodeId === "string" ? attrs.nodeId : "";
    const label = typeof attrs.label === "string" && attrs.label.length > 0 ? attrs.label : nodeId;
    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        class: "graph-node-reference-pill recap-node-token",
        "data-graph-node-id": nodeId,
        "data-plan-card-reference": "graph",
        contenteditable: "false",
      }),
      label,
    ];
  },
});

const PLAN_CARD_SCHEMA_EXTENSIONS = DEFAULT_MARKDOWN_EDITOR_EXTENSIONS.map((extension) => (
  extension.name === GraphNodeReferenceNode.name ? StaticGraphNodeReferenceNode : extension
));

function unsupportedCardContentReason(content: JSONContent): string | null {
  const inspect = (node: unknown): string | null => {
    if (node == null || typeof node !== "object" || Array.isArray(node)) return "malformed content";
    const record = node as { type?: unknown; attrs?: unknown; marks?: unknown; content?: unknown };
    const type = typeof record.type === "string" ? record.type : "";
    const attrs = record.attrs != null && typeof record.attrs === "object"
      ? record.attrs as Record<string, unknown>
      : {};

    if (["image", "video", "audio", "iframe", "embed"].includes(type)) {
      const src = typeof attrs.src === "string" ? attrs.src : "";
      return classifyImageUrl(src) === "unsafe"
        ? "unsafe embedded media"
        : "embedded media is not supported in Cards";
    }
    if ("src" in attrs || "href" in attrs) return "unsupported URL-bearing node";

    if (Array.isArray(record.marks)) {
      for (const mark of record.marks) {
        if (mark == null || typeof mark !== "object" || Array.isArray(mark)) return "malformed mark";
        const markRecord = mark as { type?: unknown; attrs?: unknown };
        const markAttrs = markRecord.attrs != null && typeof markRecord.attrs === "object"
          ? markRecord.attrs as Record<string, unknown>
          : {};
        if (markRecord.type === "link") {
          if (typeof markAttrs.href !== "string") return "malformed link";
          const linkKind = classifyLinkUrl(markAttrs.href);
          if (linkKind === "unsafe" || linkKind === "relative_visible") {
            return "link destination is not safe to navigate from Cards";
          }
        } else if ("href" in markAttrs || "src" in markAttrs) {
          return "unsupported URL-bearing mark";
        }
      }
    }

    if (Array.isArray(record.content)) {
      for (const child of record.content) {
        const reason = inspect(child);
        if (reason) return reason;
      }
    }
    return null;
  };

  return inspect(content);
}

function cardContentDocument(node: WorldPlanCardNode): JSONContent {
  return {
    type: "doc",
    content: [
      {
        type: "heading",
        attrs: { level: 3 },
        content: node.titleContent.length > 0
          ? node.titleContent
          : [{ type: "text", text: node.title || "Untitled marked element" }],
      },
      ...node.bodyContent,
    ],
  };
}

export type WorldPlanCardProjectionModel =
  | { status: "empty" }
  | { status: "blocked"; diagnostics: ProjectionDiagnostic[] }
  | { status: "ready"; version: ProjectionVersion; roots: WorldPlanCardNode[] };

export function worldPlanCardTargetKeys(model: WorldPlanCardProjectionModel): Set<string> {
  if (model.status !== "ready") return new Set();
  const counts = new Map<string, number>();
  const visit = (nodes: readonly WorldPlanCardNode[]) => {
    for (const node of nodes) {
      const key = worldPlanCardTargetKey({ kind: node.kind, id: node.id });
      counts.set(key, (counts.get(key) ?? 0) + 1);
      visit(node.children);
    }
  };
  visit(model.roots);
  return new Set([...counts].filter(([, count]) => count === 1).map(([key]) => key));
}

function scanSourceMarkers(markdown: string): { versions: Set<ProjectionVersion>; diagnostics: ProjectionDiagnostic[] } {
  const versions = new Set<ProjectionVersion>();
  const diagnostics: ProjectionDiagnostic[] = [];
  let fence: { char: string; length: number } | null = null;

  for (const [index, line] of markdown.split(/\r\n|\r|\n/).entries()) {
    const opening = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (fence) {
      if (opening && opening[1]![0] === fence.char && opening[1]!.length >= fence.length
        && /^ {0,3}(?:`{3,}|~{3,})[ \t]*$/.test(line)) {
        fence = null;
      }
      continue;
    }
    if (opening) {
      fence = { char: opening[1]![0]!, length: opening[1]!.length };
      continue;
    }
    if (!line.includes(PLAYABLE_ELEMENT_MARKER_PREFIX)) continue;

    const parsed = parsePlayableHtmlComment(line.trim());
    if (parsed.status !== "canonical") {
      const probedVersion = playableMarkerVersionProbe(line);
      diagnostics.push({
        code: probedVersion && probedVersion !== "v1" && probedVersion !== "v2" ? "unknown_version" : "malformed_marker",
        message: probedVersion && probedVersion !== "v1" && probedVersion !== "v2"
          ? `Unsupported Playable marker version on line ${index + 1}.`
          : `Malformed Playable marker on line ${index + 1}.`,
      });
      continue;
    }
    versions.add(parsed.identity.version ?? "v1");
  }

  if (versions.size > 1) {
    diagnostics.push({ code: "mixed_grammar", message: "This Plan mixes v1 and v2 Playable markers." });
  }
  return { versions, diagnostics };
}

function createNodes(
  elements: readonly (PlayableStructureElement | PlayableStructureElementV2)[],
  version: ProjectionVersion,
  document: JSONContent,
): { roots: WorldPlanCardNode[]; diagnostics: ProjectionDiagnostic[] } {
  const slices = slicePlayableBodies(document);
  const nodes = new Map<string, WorldPlanCardNode>();
  const diagnostics: ProjectionDiagnostic[] = [];

  for (const element of elements) {
    const slice = slices.get(element.id);
    if (!slice) {
      diagnostics.push({
        code: "missing_body_slice",
        message: `Playable element ${element.id} has no readable source slice.`,
      });
      continue;
    }

    const node: WorldPlanCardNode = {
      id: element.id,
      kind: element.kind,
      title: slice.title,
      titleContent: slice.titleContent,
      bodyText: slice.bodyText,
      bodyContent: slice.bodyContent,
      order: element.order,
      parentId: null,
      children: [],
    };
    if (version === "v1") {
      const legacyElement = element as PlayableStructureElement;
      if (legacyElement.kind === "beat" || legacyElement.kind === "choice") node.parentId = legacyElement.sceneId;
      if (legacyElement.kind === "option") node.parentId = legacyElement.choiceId;
    } else {
      const beatFirstElement = element as PlayableStructureElementV2;
      if (beatFirstElement.kind === "scene" || beatFirstElement.kind === "choice") node.parentId = beatFirstElement.beatId;
      if (beatFirstElement.kind === "option") node.parentId = beatFirstElement.choiceId;
      if (beatFirstElement.kind === "beat") node.beatKind = beatFirstElement.beatKind;
      if (beatFirstElement.kind === "choice") node.sceneId = beatFirstElement.sceneId;
    }
    nodes.set(element.id, node);
  }

  if (version === "v2") {
    const indexed = indexPlayableStructureV2(document);
    if (indexed.status === "ready") {
      for (const option of indexed.index.options) {
        const node = nodes.get(option.optionId);
        if (!node) continue;
        node.activates = option.activates;
        node.suppresses = option.suppresses;
      }
    }
  }

  const roots: WorldPlanCardNode[] = [];
  for (const element of elements) {
    const node = nodes.get(element.id);
    if (!node) continue;
    if (!node.parentId) {
      roots.push(node);
      continue;
    }
    const parent = nodes.get(node.parentId);
    if (!parent) {
      diagnostics.push({
        code: "invalid_parent",
        message: `Playable element ${node.id} has no indexed parent ${node.parentId}.`,
      });
      continue;
    }
    parent.children.push(node);
  }

  return { roots, diagnostics };
}

export function buildWorldPlanCardProjectionModel(input: {
  document: JSONContent;
  markdown: string;
  sourceWarnings?: readonly string[];
}): WorldPlanCardProjectionModel {
  const source = scanSourceMarkers(input.markdown);
  const diagnostics = [...source.diagnostics];
  if (input.sourceWarnings?.length) {
    diagnostics.push({ code: "source_warning", message: "The editor cannot verify this Plan's Markdown safely." });
  }
  if (diagnostics.length) return { status: "blocked", diagnostics };

  const v1 = indexPlayableStructure(input.document);
  const v2 = indexPlayableStructureV2(input.document);
  if (source.versions.size === 0) {
    const hasEditorIdentities = (v1.status === "ready" && v1.index.elements.length > 0)
      || (v2.status === "ready" && v2.index.elements.length > 0);
    return hasEditorIdentities
      ? { status: "blocked", diagnostics: [{ code: "source_mismatch", message: "The editor structure does not match the saved Markdown source." }] }
      : { status: "empty" };
  }

  const version = [...source.versions][0]!;
  const indexed = version === "v1" ? v1 : v2;
  if (indexed.status === "blocked") {
    return {
      status: "blocked",
      diagnostics: indexed.diagnostics.map(({ code, message }) => ({ code, message })),
    };
  }
  const elements = indexed.index.elements;
  if (elements.length === 0) {
    return { status: "blocked", diagnostics: [{ code: "source_mismatch", message: "Playable markers were not admitted into the editor document." }] };
  }
  const projected = createNodes(elements, version, input.document);
  if (projected.diagnostics.length) return { status: "blocked", diagnostics: projected.diagnostics };
  return { status: "ready", version, roots: projected.roots };
}

function CardNodeView({
  node,
  worldId,
  documentId,
  selectableTargetKeys,
  editableTargetKeys,
  selectedTarget,
  selectedEditTarget,
  onSelectTarget,
  onSelectEditTarget,
}: {
  node: WorldPlanCardNode;
  worldId: string;
  documentId: string;
  selectableTargetKeys: ReadonlySet<string>;
  editableTargetKeys: ReadonlySet<string>;
  selectedTarget: WorldPlanCardTarget | null;
  selectedEditTarget: WorldPlanCardTarget | null;
  onSelectTarget?: (target: WorldPlanCardTarget) => void;
  onSelectEditTarget?: (target: WorldPlanCardTarget) => void;
}) {
  const semanticContent = useMemo(() => cardContentDocument(node), [node]);
  const contentKey = useMemo(() => JSON.stringify([
    worldId,
    documentId,
    node.kind,
    node.id,
    semanticContent,
  ]), [worldId, documentId, node.kind, node.id, semanticContent]);
  const renderedContent = useMemo(() => {
    if (unsupportedCardContentReason(semanticContent)) return null;
    try {
      const content = semanticContent.content ?? [];
      const titleContent = content[0];
      if (!titleContent) return null;
      return {
        titleHtml: generateHTML({ type: "doc", content: [titleContent] }, PLAN_CARD_SCHEMA_EXTENSIONS),
        bodyHtml: content.length > 1
          ? generateHTML({ type: "doc", content: content.slice(1) }, PLAN_CARD_SCHEMA_EXTENSIONS)
          : "",
      };
    } catch {
      return null;
    }
  // The serialized key is the exact semantic identity. A fresh JSON object for
  // unchanged editor content must not regenerate the card HTML.
  }, [contentKey]);
  const target = { kind: node.kind, id: node.id };
  const selected = selectedTarget?.kind === target.kind && selectedTarget.id === target.id;
  const selectedForEdit = selectedEditTarget?.kind === target.kind && selectedEditTarget.id === target.id;
  const selectable = selectableTargetKeys.has(worldPlanCardTargetKey(target));
  const editable = editableTargetKeys.has(worldPlanCardTargetKey(target));
  return (
    <li className={`world-plan-card-node world-plan-card-node--${node.kind}`} data-element-id={node.id} data-element-kind={node.kind}>
      <article className="world-plan-card">
        <header className="world-plan-card__header">
          <p className="world-plan-card__kind">{node.kind}{node.beatKind ? ` · ${node.beatKind}` : ""}</p>
          <code>{node.id}</code>
          {renderedContent === null ? null : (
            <div
              className="world-plan-card__title"
              data-testid={`world-plan-card-title-${node.kind}-${node.id}`}
              dangerouslySetInnerHTML={{ __html: renderedContent.titleHtml }}
            />
          )}
          <div className="world-plan-card__actions">
            <button
              type="button"
              className="world-plan-card__ask-target"
              data-target-kind={node.kind}
              data-target-id={node.id}
              aria-pressed={selected}
              disabled={!selectable || !onSelectTarget}
              title={selectable ? "Use this exact card from the committed Plan for Ask" : "A unique matching card is not available in both the saved Plan and this view"}
              onClick={() => onSelectTarget?.(target)}
            >
              {selected ? "Selected for Ask" : "Select for Ask"}
            </button>
            <button
              type="button"
              className="world-plan-card__edit-target"
              data-edit-target-kind={node.kind}
              data-edit-target-id={node.id}
              aria-pressed={selectedForEdit}
              disabled={!editable || !onSelectEditTarget}
              title={editable ? "Use this exact current card body for a Compose proposal" : "This card is not a unique editable target in the current Plan draft"}
              onClick={() => onSelectEditTarget?.(target)}
            >
              {selectedForEdit ? "Selected for Edit" : "Select for Edit"}
            </button>
          </div>
        </header>
        {node.sceneId ? <p className="world-plan-card__relationship">Associated scene: <code>{node.sceneId}</code></p> : null}
        {renderedContent === null ? (
          <p
            className="world-plan-card__content-unavailable"
            data-testid={`world-plan-card-content-unavailable-${node.kind}-${node.id}`}
            role="status"
          >
            This card contains content Cards cannot display safely. Open Document to view it.
          </p>
        ) : (
          renderedContent.bodyHtml ? (
            <div
              className="world-plan-card__content"
              data-testid={`world-plan-card-content-${node.kind}-${node.id}`}
              dangerouslySetInnerHTML={{ __html: renderedContent.bodyHtml }}
            />
          ) : null
        )}
        {node.activates?.length || node.suppresses?.length ? (
          <ul className="world-plan-card__edges" aria-label="Authored relationships">
            {node.activates?.map((target) => <li key={`activates:${target}`}>Authored activates: <code>{target}</code></li>)}
            {node.suppresses?.map((target) => <li key={`suppresses:${target}`}>Authored suppresses: <code>{target}</code></li>)}
          </ul>
        ) : null}
      </article>
      {node.children.length ? (
        <ol className="world-plan-card-children">
          {node.children.map((child) => (
            <CardNodeView
              key={child.id}
              node={child}
              worldId={worldId}
              documentId={documentId}
              selectableTargetKeys={selectableTargetKeys}
              editableTargetKeys={editableTargetKeys}
              selectedTarget={selectedTarget}
              selectedEditTarget={selectedEditTarget}
              onSelectTarget={onSelectTarget}
              onSelectEditTarget={onSelectEditTarget}
            />
          ))}
        </ol>
      ) : null}
    </li>
  );
}

export function WorldPlanCardProjection({
  worldId,
  documentId,
  document,
  markdown,
  sourceWarnings,
  basis,
  isDirty,
  onReturnToDocument,
  selectableTargetKeys = new Set<string>(),
  editableTargetKeys = new Set<string>(),
  selectedTarget = null,
  selectedEditTarget = null,
  onSelectTarget,
  onSelectEditTarget,
  selectionStale = false,
}: {
  worldId: string;
  documentId: string;
  document: JSONContent;
  markdown: string;
  sourceWarnings: readonly string[];
  basis: WorldPlanCardBasis;
  isDirty: boolean;
  onReturnToDocument: () => void;
  selectableTargetKeys?: ReadonlySet<string>;
  editableTargetKeys?: ReadonlySet<string>;
  selectedTarget?: WorldPlanCardTarget | null;
  selectedEditTarget?: WorldPlanCardTarget | null;
  onSelectTarget?: (target: WorldPlanCardTarget) => void;
  onSelectEditTarget?: (target: WorldPlanCardTarget) => void;
  selectionStale?: boolean;
}) {
  const model = useMemo(() => buildWorldPlanCardProjectionModel({ document, markdown, sourceWarnings }), [document, markdown, sourceWarnings]);
  if (model.status === "blocked") {
    return (
      <section className="world-plan-cards world-plan-cards--blocked" data-testid="world-plan-cards" role="alert" aria-label="Cards unavailable">
        <header><p className="world-plan-card__kind">Cards</p><h2>Cards are unavailable for this Plan</h2></header>
        <p>No partial or inferred cards are shown. The full Plan remains available in Document view.</p>
        <ul>{model.diagnostics.map((diagnostic) => <li key={`${diagnostic.code}:${diagnostic.message}`}>{diagnostic.message}</li>)}</ul>
        <button type="button" onClick={onReturnToDocument}>Return to Document</button>
      </section>
    );
  }
  if (model.status === "empty") {
    return (
      <section className="world-plan-cards" data-testid="world-plan-cards" aria-label="Plan cards">
        <header><p className="world-plan-card__kind">Cards</p><h2>No marked scenes yet</h2></header>
        <p>Nothing was inferred. The complete Plan is still available in Document.</p>
        <button type="button" onClick={onReturnToDocument}>Open Document</button>
      </section>
    );
  }
  const cardState = isDirty
    ? "Draft / unsaved"
    : basis.status === "verified"
      ? "Saved Plan"
      : basis.status === "server-draft"
        ? "Server draft / uncommitted"
        : "Saved basis unavailable";
  const basisLabel = basis.status === "verified"
    ? "Committed snapshot"
    : basis.status === "server-draft"
      ? "Uncommitted server draft"
      : "Unavailable";
  return (
    <section className="world-plan-cards" data-testid="world-plan-cards" aria-label="Plan cards">
      <header className="world-plan-cards__heading">
        <div><p className="world-plan-card__kind">Read-only Cards · {model.version}</p><h2>Plan cards</h2></div>
        <p className="world-plan-cards__state">{cardState}</p>
      </header>
      <details className="world-plan-cards__basis">
        <summary>Plan basis details</summary>
        <dl>
          <dt>World</dt><dd><code>{worldId}</code></dd>
          <dt>Document</dt><dd><code>{documentId}</code></dd>
          <dt>Basis</dt><dd>{basisLabel}</dd>
          <dt>Revision</dt><dd>{basis.status === "verified" ? basis.revision : "Unavailable"}</dd>
          <dt>Content SHA-256</dt><dd><code>{basis.status === "verified" ? basis.contentSha256 : "Unavailable"}</code></dd>
        </dl>
      </details>
      <p className="world-plan-cards__source-note">Only marked elements appear as cards. Unmarked Plan prose stays in Document.</p>
      <p className="world-plan-cards__target-note" role="note">
        Select one uniquely matching card for Ask. A targeted answer uses the committed Plan revision; unsaved edits are not sent.
      </p>
      <p className="world-plan-cards__target-note" role="note">
        Select for Edit targets the exact body in the current draft. When the Plan is dirty, the proposal uses unsaved draft content; Apply still changes only the mounted draft and Save remains separate.
      </p>
      {basis.status !== "verified" ? (
        <p className="world-plan-cards__target-warning" role="status">
          Card targeting is unavailable until a committed Plan snapshot is verified.
        </p>
      ) : null}
      {selectionStale ? (
        <p className="world-plan-cards__target-warning" role="alert">
          The selected card is no longer uniquely present in both this view and the committed Plan. Select a card again or clear the target before asking.
        </p>
      ) : null}
      <ol className="world-plan-card-roots">
        {model.roots.map((node) => (
          <CardNodeView
            key={node.id}
            node={node}
            worldId={worldId}
            documentId={documentId}
            selectableTargetKeys={selectableTargetKeys}
            editableTargetKeys={editableTargetKeys}
            selectedTarget={selectedTarget}
            selectedEditTarget={selectedEditTarget}
            onSelectTarget={onSelectTarget}
            onSelectEditTarget={onSelectEditTarget}
          />
        ))}
      </ol>
    </section>
  );
}
