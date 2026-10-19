import { preserveLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
import { parseMarkdownAst } from "../tiptap/markdown/parseMarkdownAst";
import { parsePlayableHtmlComment } from "../tiptap/playable/playableElementIdentity";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { Extension, type Editor } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin, PluginKey, TextSelection } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { closeHistory } from "@tiptap/pm/history";

export type CardScope = { active: boolean; sceneId: string | null };
export const planCardScopeKey = new PluginKey<CardScope>("planCardScope");
const unscoped: CardScope = { active: false, sceneId: null };

/** Resolve on every transaction. Ordinary headings and Choices stay in the scene. */
export function planCardRange(doc: PMNode, sceneId: string | null) {
  if (!sceneId) return null;
  const matches: Array<{ heading: number; from: number; to: number }> = [];
  let current: (typeof matches)[number] | null = null;
  doc.forEach((node, pos) => {
    if (node.type.name !== "heading") return;
    const kind = node.attrs.playableElementKind;
    if (kind !== "scene" && kind !== "beat") return;
    if (current) { current.to = pos; current = null; }
    if (kind === "scene" && node.attrs.playableElementId === sceneId) {
      current = { heading: pos, from: pos + node.nodeSize, to: doc.content.size };
      matches.push(current);
    }
  });
  return matches.length === 1 ? matches[0]! : null;
}
function anchors(doc: PMNode) {
  const result: unknown[] = [];
  doc.descendants(node => {
    if (node.attrs.playableElementKind || node.attrs.playableElementId) result.push([node.type.name, node.attrs]);
  });
  return JSON.stringify(result);
}
export function planCardChangeAllowed(before: PMNode, after: PMNode, sceneId: string | null) {
  const old = planCardRange(before, sceneId), next = planCardRange(after, sceneId);
  return Boolean(old && next
    && before.slice(0, old.from).eq(after.slice(0, next.from))
    && before.slice(old.to).eq(after.slice(next.to))
    && anchors(before) === anchors(after));
}
export function planCardSelectionAllowed(editor: Editor) {
  const scope = planCardScopeKey.getState(editor.state);
  if (!scope?.active) return true;
  const range = planCardRange(editor.state.doc, scope.sceneId);
  return Boolean(range && editor.state.selection.from >= range.from && editor.state.selection.to <= range.to);
}
export function setPlanCardScope(editor: Editor, scope: CardScope) {
  const old = planCardScopeKey.getState(editor.state);
  if (old?.active === scope.active && old.sceneId === scope.sceneId) return;
  let tr = closeHistory(editor.state.tr).setMeta(planCardScopeKey, scope).setMeta("addToHistory", false);
  const range = scope.active ? planCardRange(tr.doc, scope.sceneId) : null;
  if (range && (tr.selection.from < range.from || tr.selection.to > range.to)) {
    tr = tr.setSelection(TextSelection.near(tr.doc.resolve(range.from), 1));
  }
  editor.view.dispatch(tr);
}
export const PlanCardEditing = Extension.create<{ onBlocked: () => void }>({
  name: "planCardEditing",
  addOptions: () => ({ onBlocked: () => {} }),
  addProseMirrorPlugins() {
    return [new Plugin<CardScope>({
      key: planCardScopeKey,
      state: { init: () => unscoped, apply: (tr, state) => tr.getMeta(planCardScopeKey) ?? state },
      filterTransaction: (tr, state) => {
        const scope = planCardScopeKey.getState(state);
        if (!tr.docChanged || !scope?.active) return true;
        if (planCardChangeAllowed(state.doc, tr.doc, scope.sceneId)) return true;
        queueMicrotask(this.options.onBlocked);
        return false;
      },
      props: {
        decorations(state) {
          const scope = planCardScopeKey.getState(state);
          if (!scope?.active) return null;
          const range = planCardRange(state.doc, scope.sceneId);
          const decorations: Decoration[] = [];
          state.doc.forEach((node, pos) => {
            if (!range || pos < range.heading || pos >= range.to) {
              decorations.push(Decoration.node(pos, pos + node.nodeSize, { class: "plan-card-outside", "aria-hidden": "true" }));
            } else if (pos === range.heading) {
              decorations.push(Decoration.node(pos, pos + node.nodeSize, { contenteditable: "false", class: "plan-card-title" }));
            }
          });
          return DecorationSet.create(state.doc, decorations);
        },
        handleKeyDown(view, event) {
          const scope = planCardScopeKey.getState(view.state);
          if (!scope?.active) return false;
          const range = planCardRange(view.state.doc, scope.sceneId);
          if (!range) return false;
          const all = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "a";
          const home = (event.ctrlKey || event.metaKey) && event.key === "Home";
          const end = (event.ctrlKey || event.metaKey) && event.key === "End";
          if (!all && !home && !end) return false;
          const start = TextSelection.near(view.state.doc.resolve(range.from), 1).from;
          const finish = TextSelection.near(view.state.doc.resolve(range.to), -1).to;
          view.dispatch(view.state.tr.setSelection(TextSelection.create(view.state.doc, end ? finish : start, all ? finish : end ? finish : start)));
          return true;
        },
      },
    })];
  },
});

/** Preserve every byte outside the edited scene, including noncanonical spacing. */
export function exportPlanCardMarkdown(editor: Editor, source: string, canonical: string): string {
  const scope = planCardScopeKey.getState(editor.state);
  if (!scope?.active) return preserveLeadingYamlFrontmatter(source, canonical);
  const range = planCardRange(editor.state.doc, scope.sceneId);
  if (!range) throw new Error("The selected scene cannot be resolved. Open Document.");
  const nodes = parseMarkdownAst(source).children;
  const markers = nodes.map((node, index) => ({ node, index, parsed: node.type === "html" ? parsePlayableHtmlComment(node.value) : null }))
    .filter(item => item.parsed?.status === "canonical");
  const matches = markers.filter(item => item.parsed?.status === "canonical" && item.parsed.identity.kind === "scene" && item.parsed.identity.id === scope.sceneId);
  if (matches.length !== 1) throw new Error("The source scene is ambiguous. Open Document.");
  const match = matches[0]!;
  const heading = nodes[match.index + 1];
  if (heading?.type !== "heading" || heading.position?.end.offset == null) throw new Error("The source scene heading is unavailable. Open Document.");
  const next = markers.find(item => item.index > match.index && item.parsed?.status === "canonical" && ["scene", "beat"].includes(item.parsed.identity.kind));
  const end = next?.node.position?.start.offset ?? source.length;
  const body = tiptapJsonToSemanticMarkdown({type:"doc",content:editor.state.doc.slice(range.from,range.to).content.toJSON()});
  const result = source.slice(0,heading.position.end.offset) + "\n\n" + body.trimEnd() + "\n\n" + source.slice(end);
  if (tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(result).doc) !== tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(canonical).doc)) throw new Error("The scene edit cannot preserve this document. Open Document.");
  return result;
}
