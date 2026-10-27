import type { EditorView } from '@tiptap/pm/view';
import { closeHistory } from '@tiptap/pm/history';
import { isPlainTableCaption } from '../markdown/tableCaption';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

const mime = 'application/x-dungeonbuddy-table-move';
const drags = new WeakMap<EditorView, { token: string; doc: EditorView['state']['doc']; range: { from: number; to: number } }>();

/** Never adopt a Plan identity, marked title or inline reference as editable table chrome. */
export function isTableCaption(node: ProseMirrorNode | null | undefined): node is ProseMirrorNode {
  return isPlainTableCaption(node?.toJSON());
}

export function tableMoveRange(view: EditorView, position: number) {
  const table = view.state.doc.nodeAt(position);
  if (table?.type.name !== 'table' || view.state.doc.resolve(position).depth !== 0) return null;
  const previous = view.state.doc.resolve(position).nodeBefore;
  const from = isTableCaption(previous) ? position - previous.nodeSize : position;
  return { from, to: position + table.nodeSize };
}

export function moveTable(view: EditorView, range: { from: number; to: number }, destination: number) {
  if (!view.editable) return false;
  if (destination < 0 || destination > view.state.doc.content.size || view.state.doc.resolve(destination).depth !== 0) return false;
  // A drop must not separate another table from its adjacent caption.
  if (view.state.doc.nodeAt(destination)?.type.name === 'table') {
    destination = tableMoveRange(view, destination)?.from ?? destination;
  }
  if (destination >= range.from && destination <= range.to) return false;
  const content = view.state.doc.slice(range.from, range.to).content;
  const target = destination > range.to ? destination - (range.to - range.from) : destination;
  view.dispatch(closeHistory(view.state.tr).delete(range.from, range.to).insert(target, content).scrollIntoView());
  return true;
}

/** Own only same-editor, exact-document drags; leave ordinary editor drag/drop alone. */
export function embeddedTableMove(view: EditorView, getPos: () => number | undefined) {
  const handle = document.createElement('button');
  handle.type = 'button'; handle.draggable = true;
  handle.textContent = '⠿'; handle.className = 'embedded-content-frame__drag';
  handle.setAttribute('aria-label', 'Move table');
  handle.title = 'Drag to move · Alt+Up/Down to reorder';
  const start = (event: DragEvent) => {
    const position = getPos();
    const range = position === undefined ? null : tableMoveRange(view, position);
    if (!event.dataTransfer || !view.editable || !range) { event.preventDefault(); return; }
    const pending = { token: crypto.randomUUID(), doc: view.state.doc, range };
    drags.set(view, pending);
    event.dataTransfer.setData(mime, pending.token);
    event.dataTransfer.effectAllowed = 'move';
    event.stopPropagation();
  };
  const over = (event: DragEvent) => {
    if (drags.has(view) && event.dataTransfer?.types.includes(mime)) event.preventDefault();
  };
  const drop = (event: DragEvent) => {
    const pending = drags.get(view);
    if (!pending || event.dataTransfer?.getData(mime) !== pending.token) return;
    event.preventDefault(); event.stopPropagation();
    const source = pending; drags.delete(view);
    if (view.state.doc !== source.doc) return;
    const hit = view.posAtCoords({ left: event.clientX, top: event.clientY });
    if (!hit) return;
    const resolved = view.state.doc.resolve(hit.pos);
    let destination = hit.pos;
    if (resolved.depth > 0) {
      const before = resolved.before(1);
      const element = view.nodeDOM(before);
      const box = element instanceof Element ? element.getBoundingClientRect() : null;
      destination = box && event.clientY > box.top + box.height / 2 ? resolved.after(1) : before;
    }
    moveTable(view, source.range, destination);
  };
  const end = () => { drags.delete(view); };
  const key = (event: KeyboardEvent) => {
    if (!event.altKey || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const position = getPos(); const range = position === undefined ? null : tableMoveRange(view, position);
    if (!range) return;
    const previous = view.state.doc.resolve(range.from).nodeBefore;
    const next = view.state.doc.resolve(range.to).nodeAfter;
    if (event.key === 'ArrowUp' && previous) {
      const before = range.from - previous.nodeSize;
      moveTable(view, range, previous.type.name === 'table' ? tableMoveRange(view, before)?.from ?? before : before);
    }
    if (event.key === 'ArrowDown' && next) {
      let after = range.to + next.nodeSize;
      if (isTableCaption(next) && view.state.doc.nodeAt(after)?.type.name === 'table') {
        after += view.state.doc.nodeAt(after)!.nodeSize;
      }
      moveTable(view, range, after);
    }
  };
  handle.addEventListener('dragstart', start); handle.addEventListener('dragend', end); handle.addEventListener('keydown', key);
  view.dom.addEventListener('dragover', over, true); view.dom.addEventListener('drop', drop, true);
  return { handle, destroy() {
    handle.removeEventListener('dragstart', start); handle.removeEventListener('dragend', end); handle.removeEventListener('keydown', key);
    view.dom.removeEventListener('dragover', over, true); view.dom.removeEventListener('drop', drop, true);
  } };
}
