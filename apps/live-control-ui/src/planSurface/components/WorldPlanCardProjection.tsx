import { useEffect, useMemo, useRef, useState } from "react";
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
    const label = typeof attrs.label === "string" ? attrs.label : "";
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

function unsupportedCardContentReason(content: readonly JSONContent[]): string | null {
  const inspect = (node: unknown): string | null => {
    if (node == null || typeof node !== "object" || Array.isArray(node)) return "malformed content";
    const record = node as { type?: unknown; attrs?: unknown; marks?: unknown; content?: unknown };
    if (typeof record.type !== "string" || record.type.length === 0) return "missing node type";
    const attrs = record.attrs == null
      ? {}
      : typeof record.attrs === "object" && !Array.isArray(record.attrs)
        ? record.attrs as Record<string, unknown>
        : null;
    if (attrs == null) return "malformed node attributes";

    if (["image", "video", "audio", "iframe", "embed"].includes(record.type)) {
      const src = typeof attrs.src === "string" ? attrs.src : "";
      return classifyImageUrl(src) === "unsafe"
        ? "unsafe embedded media"
        : "embedded media is not supported in Cards";
    }
    if ("src" in attrs || "href" in attrs) return "unsupported URL-bearing node";

    if (record.type === "graphNodeReference") {
      if (typeof attrs.nodeId !== "string" || attrs.nodeId.length === 0
        || typeof attrs.label !== "string" || attrs.label.length === 0) {
        return "malformed Graph reference";
      }
    }
    if (record.type === "runbookReference") {
      if ((attrs.kind !== undefined && attrs.kind !== "ref" && attrs.kind !== "action")
        || typeof attrs.refType !== "string" || attrs.refType.length === 0
        || typeof attrs.refId !== "string" || attrs.refId.length === 0
        || typeof attrs.label !== "string" || attrs.label.length === 0) {
        return "malformed Runbook reference";
      }
    }

    if (record.marks !== undefined && !Array.isArray(record.marks)) return "malformed marks";
    if (Array.isArray(record.marks)) {
      for (const mark of record.marks) {
        if (mark == null || typeof mark !== "object" || Array.isArray(mark)) return "malformed mark";
        const markRecord = mark as { type?: unknown; attrs?: unknown };
        const markAttrs = markRecord.attrs == null
          ? {}
          : typeof markRecord.attrs === "object" && !Array.isArray(markRecord.attrs)
            ? markRecord.attrs as Record<string, unknown>
            : null;
        if (typeof markRecord.type !== "string" || markAttrs == null) return "malformed mark";
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

    if (record.content !== undefined && !Array.isArray(record.content)) return "malformed child content";
    if (Array.isArray(record.content)) {
      for (const child of record.content) {
        const reason = inspect(child);
        if (reason) return reason;
      }
    }
    return null;
  };

  for (const node of content) {
    const reason = inspect(node);
    if (reason) return reason;
  }
  return null;
}

function cardTitleContent(node: WorldPlanCardNode, level: number): JSONContent {
  const titleContent = node.titleContent.length > 0
    ? node.titleContent
    : node.title === node.id || node.title.length === 0
      ? [{ type: "text", text: node.title || "Untitled marked element" }]
      : [{ type: "unsupportedPlayableTitle" }];
  return {
    type: "heading",
    attrs: { level },
    content: titleContent,
  };
}

function authoredInlineText(nodes: readonly JSONContent[]): string {
  return nodes.map((node) => {
    if (node.type === "text") return typeof node.text === "string" ? node.text : "";
    if (node.type === "graphNodeReference" || node.type === "runbookReference") {
      return typeof node.attrs?.label === "string" ? node.attrs.label : "";
    }
    return authoredInlineText(node.content ?? []);
  }).join("");
}

function StaticPlanCardContent({
  identity,
  content,
  className,
}: {
  identity: string;
  content: JSONContent[];
  className: string;
}) {
  const contentKey = useMemo(() => JSON.stringify([identity, content]), [identity, content]);
  const html = useMemo(() => {
    if (unsupportedCardContentReason(content)) return null;
    try {
      return generateHTML({ type: "doc", content }, PLAN_CARD_SCHEMA_EXTENSIONS);
    } catch {
      return null;
    }
  }, [contentKey]);

  if (html === null) {
    return (
      <p className={`${className} world-plan-card__content-unavailable`} role="status">
        This authored content cannot be displayed safely in Cards. Open Document to view it.
      </p>
    );
  }
  if (!html) return null;
  return <div className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

export type WorldPlanCardProjectionModel =
  | { status: "empty" }
  | { status: "blocked"; diagnostics: ProjectionDiagnostic[] }
  | { status: "ready"; version: ProjectionVersion; roots: WorldPlanCardNode[] };

function flattenNodes(nodes: readonly WorldPlanCardNode[]): WorldPlanCardNode[] {
  return nodes.flatMap((node) => [node, ...flattenNodes(node.children)]);
}

function descendantsOf(node: WorldPlanCardNode): WorldPlanCardNode[] {
  return flattenNodes(node.children);
}

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
  onFocusScene,
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
  onFocusScene?: (scene: WorldPlanCardNode) => void;
}) {
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
          <StaticPlanCardContent
            identity={`${worldId}\u001f${documentId}\u001f${node.kind}\u001f${node.id}\u001ftitle`}
            content={[cardTitleContent(node, 3)]}
            className="world-plan-card__title"
          />
          <code>{node.id}</code>
          {onSelectTarget ? (
            <button
              type="button"
              className="world-plan-card__ask-target"
              data-target-kind={node.kind}
              data-target-id={node.id}
              aria-pressed={selected}
              disabled={!selectable}
              title={selectable ? "Use this exact card from the committed Plan for Ask" : "A unique matching card is not available in both the saved Plan and this view"}
              onClick={() => onSelectTarget(target)}
            >
              {selected ? "Selected for Ask" : "Select for Ask"}
            </button>
          ) : null}
          {node.kind === "scene" && onFocusScene ? (
            <button
              type="button"
              className="world-plan-card__focus-scene"
              data-focus-scene-id={node.id}
              aria-label={`Read scene: ${authoredInlineText(node.titleContent).trim() || node.title || node.id}`}
              onClick={() => onFocusScene(node)}
            >Read scene</button>
          ) : null}
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
        </header>
        {node.sceneId ? <p className="world-plan-card__relationship">Associated scene: <code>{node.sceneId}</code></p> : null}
        {node.bodyContent.length ? (
          <StaticPlanCardContent
            identity={`${worldId}\u001f${documentId}\u001f${node.kind}\u001f${node.id}\u001fbody`}
            content={node.bodyContent}
            className="world-plan-card__content"
          />
        ) : null}
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
              onFocusScene={onFocusScene}
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
  onSelectTarget?: (target: WorldPlanCardTarget | null) => void;
  onSelectEditTarget?: (target: WorldPlanCardTarget) => void;
  selectionStale?: boolean;
}) {
  const model = useMemo(() => buildWorldPlanCardProjectionModel({ document, markdown, sourceWarnings }), [document, markdown, sourceWarnings]);
  const nodes = useMemo(() => model.status === "ready" ? flattenNodes(model.roots) : [], [model]);
  const scenes = useMemo(() => nodes.filter((node) => node.kind === "scene"), [nodes]);
  const [focusedSceneId, setFocusedSceneId] = useState<string | null>(null);
  const basisIdentity = basis.status === "verified"
    ? `verified:${basis.revision}:${basis.contentSha256}`
    : basis.status;
  const focusIdentity = `${worldId}\u001f${documentId}\u001f${basisIdentity}`;
  const focusIdentityRef = useRef(focusIdentity);
  const focusedScene = scenes.find((scene) => scene.id === focusedSceneId) ?? null;
  const focusedSceneIndex = focusedScene ? scenes.findIndex((scene) => scene.id === focusedScene.id) : -1;
  const parentBeat = focusedScene?.parentId
    ? nodes.find((node) => node.id === focusedScene.parentId && node.kind === "beat") ?? null
    : null;
  const focusedDescendantIds = focusedScene
    ? new Set([focusedScene.id, ...descendantsOf(focusedScene).map((node) => node.id)])
    : new Set<string>();
  const associatedChoices = focusedScene
    ? nodes.filter((node) => node.kind === "choice"
      && node.sceneId === focusedScene.id
      && !focusedDescendantIds.has(node.id))
    : [];
  const focusedTarget = focusedScene ? { kind: focusedScene.kind, id: focusedScene.id } : null;
  const focusedTargetSelectable = Boolean(focusedTarget
    && basis.status === "verified"
    && selectableTargetKeys.has(worldPlanCardTargetKey(focusedTarget)));
  const focusedTargetSelected = Boolean(focusedTarget
    && selectedTarget?.kind === focusedTarget.kind
    && selectedTarget.id === focusedTarget.id);

  useEffect(() => {
    if (focusIdentityRef.current === focusIdentity) return;
    focusIdentityRef.current = focusIdentity;
    setFocusedSceneId(null);
    onSelectTarget?.(null);
  }, [focusIdentity, onSelectTarget]);

  useEffect(() => {
    if (!focusedSceneId || focusedScene) return;
    setFocusedSceneId(null);
    onSelectTarget?.(null);
  }, [focusedScene, focusedSceneId, onSelectTarget]);

  const focusScene = (scene: WorldPlanCardNode) => {
    setFocusedSceneId(scene.id);
    const target = { kind: scene.kind, id: scene.id } satisfies WorldPlanCardTarget;
    onSelectTarget?.(basis.status === "verified"
      && selectableTargetKeys.has(worldPlanCardTargetKey(target))
      ? target
      : null);
  };

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
  if (focusedScene) {
    const previousScene = focusedSceneIndex > 0 ? scenes[focusedSceneIndex - 1] : null;
    const nextScene = focusedSceneIndex >= 0 && focusedSceneIndex < scenes.length - 1
      ? scenes[focusedSceneIndex + 1]
      : null;
    return (
      <section className="world-plan-cards world-plan-cards--reader" data-testid="world-plan-scene-reader" aria-label="Focused Plan scene">
        <nav className="world-plan-scene-reader__navigation" aria-label="Scene navigation">
          <button type="button" disabled={!previousScene} onClick={() => previousScene && focusScene(previousScene)}>Previous scene</button>
          <button type="button" onClick={() => setFocusedSceneId(null)}>Back to outline</button>
          <button type="button" disabled={!nextScene} onClick={() => nextScene && focusScene(nextScene)}>Next scene</button>
        </nav>
        <header className="world-plan-scene-reader__heading">
          <p className="world-plan-card__kind">Focused Scene · {model.version}</p>
          <StaticPlanCardContent
            identity={`${worldId}\u001f${documentId}\u001f${focusedScene.kind}\u001f${focusedScene.id}\u001ftitle-reader`}
            content={[cardTitleContent(focusedScene, 2)]}
            className="world-plan-scene-reader__title"
          />
          <code>{focusedScene.id}</code>
          {parentBeat ? (
            <section className="world-plan-scene-reader__context" aria-label="Authored Beat context">
              <StaticPlanCardContent
                identity={`${worldId}\u001f${documentId}\u001f${parentBeat.kind}\u001f${parentBeat.id}\u001ftitle-context`}
                content={[cardTitleContent(parentBeat, 3)]}
                className="world-plan-scene-reader__context-title"
              />
              {parentBeat.bodyContent[0] ? (
                <StaticPlanCardContent
                  identity={`${worldId}\u001f${documentId}\u001f${parentBeat.kind}\u001f${parentBeat.id}\u001fobjective`}
                  content={[parentBeat.bodyContent[0]]}
                  className="world-plan-scene-reader__objective"
                />
              ) : null}
              {parentBeat.bodyContent.length > 1 ? (
                <details className="world-plan-scene-reader__beat-details">
                  <summary>Beat details</summary>
                  <StaticPlanCardContent
                    identity={`${worldId}\u001f${documentId}\u001f${parentBeat.kind}\u001f${parentBeat.id}\u001fdetails`}
                    content={parentBeat.bodyContent.slice(1)}
                    className="world-plan-scene-reader__details-content"
                  />
                </details>
              ) : null}
            </section>
          ) : null}
          <p className="world-plan-scene-reader__target" role="status">
            {focusedTargetSelectable && focusedTargetSelected
              ? `New Ask uses this Scene from committed Plan revision ${basis.status === "verified" ? basis.revision : ""}. Submitted requests keep their original target.`
              : focusedTargetSelectable
                ? "This Scene is available in the verified saved Plan, but it is not the selected Ask target. Return to the outline to set it again."
                : "This Scene is not available in the verified saved Plan. The default Ask card target is cleared; no draft content will be sent."}
          </p>
        </header>
        <div className="world-plan-scene-reader__content">
          <ol className="world-plan-card-roots">
            <CardNodeView
              node={focusedScene}
              worldId={worldId}
              documentId={documentId}
              selectableTargetKeys={selectableTargetKeys}
              editableTargetKeys={editableTargetKeys}
              selectedTarget={selectedTarget}
              selectedEditTarget={selectedEditTarget}
              onSelectEditTarget={onSelectEditTarget}
            />
            {associatedChoices.map((choice) => (
              <CardNodeView
                key={choice.id}
                node={choice}
                worldId={worldId}
                documentId={documentId}
                selectableTargetKeys={selectableTargetKeys}
                editableTargetKeys={editableTargetKeys}
                selectedTarget={selectedTarget}
                selectedEditTarget={selectedEditTarget}
                onSelectEditTarget={onSelectEditTarget}
              />
            ))}
          </ol>
        </div>
      </section>
    );
  }
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
      {scenes.length ? (
        <nav className="world-plan-scene-outline" aria-label="Scene outline">
          <h3>Scenes</h3>
          <ol>
            {scenes.map((scene) => (
              <li key={scene.id}>
                <button type="button" onClick={() => focusScene(scene)}>Open scene: {scene.title || "Untitled marked scene"}</button>
                <code>{scene.id}</code>
              </li>
            ))}
          </ol>
        </nav>
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
            onSelectTarget={onSelectTarget ? (target) => onSelectTarget(target) : undefined}
            onSelectEditTarget={onSelectEditTarget}
            onFocusScene={focusScene}
          />
        ))}
      </ol>
    </section>
  );
}
