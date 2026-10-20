import { useMemo } from "react";
import type { JSONContent } from "@tiptap/core";
import { ReadOnlyBodyContent } from "../../markdownReader/ReadOnlyBodyContent";
import { SceneCard, type SceneCardChoice, type SceneCardElement } from "../../shared/SceneCard";
import {
  indexPlayableStructureV2,
  type PlayableStructureElementV2,
} from "../../tiptap/playable/playableStructureIndex";
import {
  parsePlayableHtmlComment,
  playableMarkerVersionProbe,
  PLAYABLE_ELEMENT_MARKER_PREFIX,
  type PlayableElementKind,
} from "../../tiptap/playable/playableElementIdentity";
import { slicePlayableBodies } from "../../playSurface/runbook/nativeRunbookProjection";

type ProjectionVersion = "v2";
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

function planSceneCardElement(node: WorldPlanCardNode, level: 2 | 3 | 4): SceneCardElement {
  return {
    id: node.id,
    title: node.title,
    titleBlock: cardTitleContent(node, level),
    bodyText: node.bodyText,
    bodyContent: node.bodyContent,
  };
}

/** A Scene sees Beat-wide and explicitly associated Choices. */
export function planFocusedSceneChoices(scene: WorldPlanCardNode, parentBeat: WorldPlanCardNode | null): SceneCardChoice[] {
  const choiceNodes = [
    ...(parentBeat?.children.filter((child) => child.kind === "choice"
      && (child.sceneId == null || child.sceneId === scene.id)) ?? []),
  ];
  return choiceNodes.map((choice) => ({
    ...planSceneCardElement(choice, 3),
    associatedSceneId: choice.sceneId,
    options: choice.children.filter((child) => child.kind === "option").map((option) => ({
      ...planSceneCardElement(option, 4),
      activates: option.activates,
      suppresses: option.suppresses,
    })),
  }));
}

function selectEditTargetWithScroll(button: HTMLButtonElement, target: WorldPlanCardTarget,
  onSelectEditTarget?: (target: WorldPlanCardTarget) => void): void {
  onSelectEditTarget?.(target);
  if (!(window.matchMedia?.("(max-width: 42rem)").matches ?? false)) return;

  const card = button.closest<HTMLElement>(".world-plan-card, .shared-scene-card");
  if (!card) return;
  const cardTop = card.getBoundingClientRect().top;
  const chromeTop = Number.parseFloat(getComputedStyle(card).getPropertyValue("--app-chrome-top")) || 0;
  const readingTop = chromeTop + 12;
  const nextScrollTop = Math.max(0, window.scrollY + cardTop - readingTop);
  if (Math.abs(nextScrollTop - window.scrollY) > 4) window.scrollTo({ top: nextScrollTop, behavior: "auto" });
}

export type WorldPlanCardProjectionModel =
  | { status: "empty" }
  | { status: "blocked"; diagnostics: ProjectionDiagnostic[] }
  | { status: "ready"; version: ProjectionVersion; roots: WorldPlanCardNode[] };

export function flattenNodes(nodes: readonly WorldPlanCardNode[]): WorldPlanCardNode[] {
  return nodes.flatMap((node) => [node, ...flattenNodes(node.children)]);
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

function scanSourceMarkers(markdown: string): { versions: Set<string>; diagnostics: ProjectionDiagnostic[] } {
  const versions = new Set<string>();
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
    const version = parsed.identity.version;
    if (version !== "v2") diagnostics.push({ code: "unsupported_version", message: `Cards require v2 Playable markers (line ${index + 1}). Open Document to edit the source.` });
    versions.add(version ?? "unsupported");
  }

  if (versions.size > 1) {
    diagnostics.push({ code: "mixed_grammar", message: "This Plan mixes v1 and v2 Playable markers." });
  }
  return { versions, diagnostics };
}

function createNodes(
  elements: readonly PlayableStructureElementV2[],
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
    if (element.kind === "scene" || element.kind === "choice") node.parentId = element.beatId;
    if (element.kind === "option") node.parentId = element.choiceId;
    if (element.kind === "beat") node.beatKind = element.beatKind;
    if (element.kind === "choice") node.sceneId = element.sceneId;
    nodes.set(element.id, node);
  }

  {
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

  const v2 = indexPlayableStructureV2(input.document);
  if (source.versions.size === 0) {
    const hasEditorIdentities = v2.status === "blocked" || v2.index.elements.length > 0;
    return hasEditorIdentities
      ? { status: "blocked", diagnostics: [{ code: "source_mismatch", message: "The editor structure does not match the saved Markdown source." }] }
      : { status: "empty" };
  }

  const indexed = v2;
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
  const projected = createNodes(elements, input.document);
  if (projected.diagnostics.length) return { status: "blocked", diagnostics: projected.diagnostics };
  return { status: "ready", version: "v2", roots: projected.roots };
}

/** Pure current-scene projection. The surface owns navigation and the mounted writer. */
export function WorldPlanCardProjection({ worldId, documentId, document, markdown, sourceWarnings,
  basis, isDirty, onReturnToDocument, sceneId, editableTargetKeys = new Set<string>(),
  selectedEditTarget = null, onSelectEditTarget, selectionStale = false, onActivateGraphNode }: {
  worldId: string; documentId: string; document: JSONContent; markdown: string;
  sourceWarnings: readonly string[]; basis: WorldPlanCardBasis; isDirty: boolean;
  sceneId: string | null; onReturnToDocument: () => void;
  editableTargetKeys?: ReadonlySet<string>; selectedEditTarget?: WorldPlanCardTarget | null;
  onSelectEditTarget?: (target: WorldPlanCardTarget) => void; selectionStale?: boolean;
  onActivateGraphNode?: (nodeId: string, trigger?: HTMLElement) => void;
}) {
  const model = useMemo(() => buildWorldPlanCardProjectionModel({ document, markdown, sourceWarnings }), [document, markdown, sourceWarnings]);
  const nodes = model.status === "ready" ? flattenNodes(model.roots) : [];
  const scene = nodes.find(node => node.kind === "scene" && node.id === sceneId);
  if (model.status === "blocked") return <section className="world-plan-cards world-plan-cards--blocked"
    data-testid="world-plan-cards" role="alert" aria-label="Cards unavailable">
    <h2>Cards are unavailable for this Plan</h2>
    <ul>{model.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}:${index}`}>{diagnostic.message}</li>)}</ul>
    <button type="button" onClick={onReturnToDocument}>Open Document</button>
  </section>;
  if (!scene) return <section className="world-plan-cards" data-testid="world-plan-cards" aria-label="Cards unavailable">
    <h2>{nodes.some(node => node.kind === "scene") ? "Choose a scene in Contents" : "No marked scenes yet"}</h2>
    <button type="button" onClick={onReturnToDocument}>Open Document</button>
  </section>;
  const beat = nodes.find(node => node.kind === "beat" && node.id === scene.parentId);
  const editAction = (kind: "scene" | "choice" | "option", id: string) => {
    const target = { kind, id } satisfies WorldPlanCardTarget;
    const editable = editableTargetKeys.has(worldPlanCardTargetKey(target));
    return <button type="button" className="world-plan-card__edit-target" data-edit-target-kind={kind}
      data-edit-target-id={id} aria-pressed={selectedEditTarget?.kind === kind && selectedEditTarget.id === id}
      disabled={!editable || !onSelectEditTarget}
      onClick={event => selectEditTargetWithScroll(event.currentTarget, target, onSelectEditTarget)}>
      {selectedEditTarget?.kind === kind && selectedEditTarget.id === id ? "Selected for Agent edit" : `Use ${kind} for Agent edit`}
    </button>;
  };
  return <section className="world-plan-cards world-plan-cards--reader" data-testid="world-plan-scene-reader" aria-label="Focused Plan scene">
    {selectionStale ? <p role="alert">The selected Ask card is stale. Select a matching saved card again before asking.</p> : null}
    <SceneCard identity={{ worldId, documentId, sceneId: scene.id,
      revision: basis.status === "verified" && !isDirty ? basis.revision : null,
      contentSha256: basis.status === "verified" && !isDirty ? basis.contentSha256 : null,
      sourceState: isDirty || basis.status !== "verified" ? "draft" : "verified" }}
      scene={planSceneCardElement(scene, 2)} choices={planFocusedSceneChoices(scene, beat ?? null)}
      variant="plan" kicker="" compactHeader headingId="world-plan-focused-scene-heading"
      sceneActions={onSelectEditTarget ? editAction("scene", scene.id) : null}
      choiceActions={{ renderChoiceActions: choice => editAction("choice", choice.id),
        renderOptionActions: (_choice, option) => editAction("option", option.id) }}
      context={beat?.bodyContent.length ? <section className="world-plan-scene-reader__context" aria-label="Authored Beat context" data-beat-id={beat.id}>
        <ReadOnlyBodyContent content={[cardTitleContent(beat, 3)]} className="world-plan-scene-reader__context-title" onActivateGraphNode={onActivateGraphNode} />
        <ReadOnlyBodyContent content={beat.bodyContent.slice(0, 1)} className="world-plan-scene-reader__objective" onActivateGraphNode={onActivateGraphNode} />
        {beat.bodyContent.length > 1 ? <details className="world-plan-scene-reader__beat-details"><summary>Beat details</summary>
          <ReadOnlyBodyContent content={beat.bodyContent.slice(1)} className="world-plan-scene-reader__details-content" onActivateGraphNode={onActivateGraphNode} />
        </details> : null}
      </section> : null}
      onActivateGraphNode={onActivateGraphNode}
      unsupportedMessage="This authored content cannot be displayed safely in Cards. Open Document to view it." />
  </section>;
}
