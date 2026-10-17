import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import type { EditorView, NodeView, ViewMutationRecord } from '@tiptap/pm/view';
import { embeddedContentFrame } from './embeddedContentFrame';

const collapsedByEditor = new WeakMap<EditorView, WeakMap<ProseMirrorNode, boolean>>();

export class EmbeddedTableView implements NodeView {
  private node: ProseMirrorNode;
  private frame: ReturnType<typeof embeddedContentFrame>;
  private collapsed: WeakMap<ProseMirrorNode, boolean>;
  readonly dom: HTMLDivElement;
  private table: HTMLTableElement;
  private columns: HTMLTableColElement;
  readonly contentDOM: HTMLTableSectionElement;

  constructor(node: ProseMirrorNode, view: EditorView) {
    this.node = node;
    this.collapsed = collapsedByEditor.get(view) ?? new WeakMap();
    collapsedByEditor.set(view, this.collapsed);
    this.frame = embeddedContentFrame('Table', this.collapsed.get(node) ?? false,
      value => this.collapsed.set(this.node, value));
    this.dom = this.frame.dom;
    this.table = this.frame.content.appendChild(document.createElement('table'));
    this.columns = this.table.appendChild(document.createElement('colgroup'));
    this.contentDOM = this.table.appendChild(document.createElement('tbody'));
    this.table.className = 'md-table';
    this.paint();
  }
  private paint() {
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
    this.node = node;
    this.collapsed.set(node, this.frame.isCollapsed());
    this.paint();
    return true;
  }
  stopEvent(event: Event) { return event.target instanceof Node && this.frame.header.contains(event.target); }
  ignoreMutation(mutation: ViewMutationRecord) {
    return mutation.type !== 'selection' && !this.contentDOM.contains(mutation.target);
  }
  destroy() { this.frame.destroy(); }
}
