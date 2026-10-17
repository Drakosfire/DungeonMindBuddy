import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import type { EditorView, NodeView, ViewMutationRecord } from '@tiptap/pm/view';
import { embeddedContentFrame } from './embeddedContentFrame';
import { readRollTable, rollFace } from './rollTable';
import { embeddedTableMove, isTableCaption } from './EmbeddedTableMove';
import { closeHistory } from '@tiptap/pm/history';

const collapsedByEditor = new WeakMap<EditorView, WeakMap<ProseMirrorNode, boolean>>();
const resultsByEditor = new WeakMap<EditorView, WeakMap<ProseMirrorNode, string>>();
export const EMBEDDED_TABLE_CONTEXT_UPDATE = 'dmb-table-context-update';

export class EmbeddedTableView implements NodeView {
  private node: ProseMirrorNode;
  private frame: ReturnType<typeof embeddedContentFrame>;
  private collapsed: WeakMap<ProseMirrorNode, boolean>;
  readonly dom: HTMLDivElement;
  private table: HTMLTableElement;
  private columns: HTMLTableColElement;
  readonly contentDOM: HTMLTableSectionElement;
  private titleInput = document.createElement('input');
  private rollButton = document.createElement('button');
  private result = document.createElement('div');
  private results: WeakMap<ProseMirrorNode, string>;
  private view: EditorView;
  private getPos: () => number | undefined;
  private move: ReturnType<typeof embeddedTableMove>;

  constructor(node: ProseMirrorNode, view: EditorView, getPos: () => number | undefined) {
    this.node = node;
    this.view = view; this.getPos = getPos;
    this.results = resultsByEditor.get(view) ?? new WeakMap();
    resultsByEditor.set(view, this.results);
    this.collapsed = collapsedByEditor.get(view) ?? new WeakMap();
    collapsedByEditor.set(view, this.collapsed);
    this.frame = embeddedContentFrame('Table', this.collapsed.get(node) ?? false,
      value => this.collapsed.set(this.node, value));
    this.dom = this.frame.dom;
    this.move = embeddedTableMove(view, getPos);
    this.frame.header.insertBefore(this.move.handle, this.frame.title);
    this.titleInput.className = 'embedded-content-frame__title';
    this.titleInput.setAttribute('aria-label', 'Table title');
    this.titleInput.placeholder = 'Name this table';
    this.titleInput.maxLength = 160;
    this.titleInput.addEventListener('change', this.rename);
    this.titleInput.addEventListener('keydown', this.titleKey);
    this.titleInput.addEventListener('blur', this.refreshTitle);
    view.dom.addEventListener(EMBEDDED_TABLE_CONTEXT_UPDATE, this.refreshTitle);
    this.frame.title.replaceWith(this.titleInput);
    this.rollButton.type = 'button';
    this.rollButton.addEventListener('click', this.roll);
    this.frame.header.insertBefore(this.rollButton, this.frame.toggle);
    this.result.className = 'embedded-content-frame__result';
    this.result.contentEditable = 'false';
    this.result.setAttribute('role', 'status');
    this.result.setAttribute('aria-live', 'polite');
    this.dom.insertBefore(this.result, this.frame.content);
    this.table = this.frame.content.appendChild(document.createElement('table'));
    this.columns = this.table.appendChild(document.createElement('colgroup'));
    this.contentDOM = this.table.appendChild(document.createElement('tbody'));
    this.table.className = 'md-table';
    this.paint();
  }
  private precedingHeading() {
    const pos = this.getPos();
    if (pos === undefined) return null;
    const previous = this.view.state.doc.resolve(pos).nodeBefore;
    return isTableCaption(previous) ? { node: previous, pos: pos - previous.nodeSize } : null;
  }
  private rename = () => {
    const title = this.titleInput.value.trim().replace(/[\r\n]+/g, ' ').slice(0, 160);
    const pos = this.getPos();
    if (!title || pos === undefined || !this.view.editable) { this.paint(); return; }
    const before = this.precedingHeading();
    if (before?.node.textContent === title) return;
    const heading = this.view.state.schema.nodes.heading!.create({ level: 2 }, this.view.state.schema.text(title));
    const transaction = closeHistory(this.view.state.tr);
    if (before) transaction.replaceWith(before.pos, before.pos + before.node.nodeSize, heading);
    else transaction.insert(pos, heading);
    this.view.dispatch(transaction);
    this.paint();
  };
  private titleKey = (event: KeyboardEvent) => {
    if (event.key === 'Enter') { event.preventDefault(); this.rename(); this.titleInput.blur(); }
  };
  private roll = () => {
    const table = readRollTable(this.node);
    if (!table) return;
    const face = rollFace(table.sides);
    const entry = table.entries.find(item => face >= item.from && face <= item.to)!;
    const text = `d${table.sides} → ${face}: ${entry.text}`;
    this.results.set(this.node, text);
    this.result.textContent = text;
    this.result.hidden = false;
  };
  private refreshTitle = () => {
    const caption = this.precedingHeading()?.node.textContent ?? '';
    if (document.activeElement !== this.titleInput) this.titleInput.value = caption;
    this.dom.dataset.hasTitle = String(Boolean(caption));
  };
  private paint() {
    this.refreshTitle();
    this.titleInput.disabled = !this.view.editable;
    const rollTable = readRollTable(this.node);
    this.rollButton.hidden = !rollTable;
    this.rollButton.textContent = rollTable ? `Roll d${rollTable.sides}` : '';
    const result = this.results.get(this.node) ?? '';
    this.result.textContent = result;
    this.result.hidden = !result;
    const header = this.node.firstChild;
    const hasHeader = header?.firstChild?.type.name === 'tableHeader';
    const start = hasHeader ? 1 : 0;
    const rows = this.node.childCount - start;
    this.frame.setSummary(`${rows} ${rows === 1 ? 'row' : 'rows'}`);
    this.columns.replaceChildren();
    for (let column = 0; column < (header?.childCount ?? 0); column++) {
      const col = this.columns.appendChild(document.createElement('col'));
      let numeric = rows > 0;
      for (let row = start; row < this.node.childCount; row++) {
        const value = this.node.child(row).maybeChild(column)?.textContent ?? '';
        if (!/^\d{1,3}(?:[–-]\d{1,3})?$/.test(value.trim())) numeric = false;
      }
      if (numeric) col.className = 'embedded-content-frame__numeric-column';
    }
  }
  update(node: ProseMirrorNode) {
    if (node.type !== this.node.type) return false;
    const changed = node !== this.node;
    this.node = node;
    // A changed table invalidates an old result; identity-equal view reattachment preserves it.
    if (changed) this.results.delete(node);
    this.collapsed.set(node, this.frame.isCollapsed());
    this.paint();
    return true;
  }
  stopEvent(event: Event) { return event.target instanceof Node && this.frame.header.contains(event.target); }
  ignoreMutation(mutation: ViewMutationRecord) {
    return mutation.type !== 'selection' && !this.contentDOM.contains(mutation.target);
  }
  destroy() {
    this.titleInput.removeEventListener('change', this.rename);
    this.titleInput.removeEventListener('keydown', this.titleKey);
    this.titleInput.removeEventListener('blur', this.refreshTitle);
    this.view.dom.removeEventListener(EMBEDDED_TABLE_CONTEXT_UPDATE, this.refreshTitle);
    this.rollButton.removeEventListener('click', this.roll);
    this.move.destroy();
    this.frame.destroy();
  }
}
