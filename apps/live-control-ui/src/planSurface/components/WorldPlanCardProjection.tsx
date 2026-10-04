import { useMemo } from "react";
import type { JSONContent } from "@tiptap/core";
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
} from "../../tiptap/playable/playableElementIdentity";
import { slicePlayableBodies } from "../../playSurface/runbook/nativeRunbookProjection";

type ProjectionVersion = "v1" | "v2";
type ProjectionDiagnostic = { code: string; message: string };

export type WorldPlanCardNode = {
  id: string;
  kind: "scene" | "beat" | "choice" | "option";
  title: string;
  bodyText: string;
  order: number;
  parentId: string | null;
  children: WorldPlanCardNode[];
  beatKind?: string | null;
  sceneId?: string | null;
  activates?: string[];
  suppresses?: string[];
};

export type WorldPlanCardProjectionModel =
  | { status: "empty" }
  | { status: "blocked"; diagnostics: ProjectionDiagnostic[] }
  | { status: "ready"; version: ProjectionVersion; roots: WorldPlanCardNode[] };

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
      bodyText: slice.bodyText,
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

function CardNodeView({ node }: { node: WorldPlanCardNode }) {
  return (
    <li className={`world-plan-card-node world-plan-card-node--${node.kind}`} data-element-id={node.id} data-element-kind={node.kind}>
      <article className="world-plan-card">
        <header className="world-plan-card__header">
          <p className="world-plan-card__kind">{node.kind}{node.beatKind ? ` · ${node.beatKind}` : ""}</p>
          <h3>{node.title || "Untitled marked element"}</h3>
          <code>{node.id}</code>
        </header>
        {node.sceneId ? <p className="world-plan-card__relationship">Associated scene: <code>{node.sceneId}</code></p> : null}
        {node.bodyText ? <p className="world-plan-card__body">{node.bodyText}</p> : null}
        {node.activates?.length || node.suppresses?.length ? (
          <ul className="world-plan-card__edges" aria-label="Authored relationships">
            {node.activates?.map((target) => <li key={`activates:${target}`}>Authored activates: <code>{target}</code></li>)}
            {node.suppresses?.map((target) => <li key={`suppresses:${target}`}>Authored suppresses: <code>{target}</code></li>)}
          </ul>
        ) : null}
      </article>
      {node.children.length ? (
        <ol className="world-plan-card-children">
          {node.children.map((child) => <CardNodeView key={child.id} node={child} />)}
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
  revision,
  contentSha256,
  isDirty,
  onReturnToDocument,
}: {
  worldId: string;
  documentId: string;
  document: JSONContent;
  markdown: string;
  sourceWarnings: readonly string[];
  revision: number | null;
  contentSha256: string | null;
  isDirty: boolean;
  onReturnToDocument: () => void;
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
  return (
    <section className="world-plan-cards" data-testid="world-plan-cards" aria-label="Plan cards">
      <header className="world-plan-cards__heading">
        <div><p className="world-plan-card__kind">Read-only Cards · {model.version}</p><h2>Plan cards</h2></div>
        <p className="world-plan-cards__state">{isDirty ? "Draft / unsaved" : "Saved Plan"}</p>
      </header>
      <details className="world-plan-cards__basis">
        <summary>Saved revision details</summary>
        <dl>
          <dt>World</dt><dd><code>{worldId}</code></dd>
          <dt>Document</dt><dd><code>{documentId}</code></dd>
          <dt>Revision</dt><dd>{revision ?? "Unavailable"}</dd>
          <dt>Content SHA-256</dt><dd><code>{contentSha256 ?? "Unavailable"}</code></dd>
        </dl>
      </details>
      <p className="world-plan-cards__source-note">Only marked elements appear as cards. Unmarked Plan prose stays in Document.</p>
      <ol className="world-plan-card-roots">
        {model.roots.map((node) => <CardNodeView key={node.id} node={node} />)}
      </ol>
    </section>
  );
}
