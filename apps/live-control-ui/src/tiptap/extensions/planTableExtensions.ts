import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import { EmbeddedTableView, EMBEDDED_TABLE_CONTEXT_UPDATE } from './EmbeddedTableView';
import { Plugin } from '@tiptap/pm/state';

/** GFM-style tables for Plan Board / MarkdownEditor (non-resizable). */
export const PLAN_TABLE_EXTENSIONS = [
  Table.extend({
    addNodeView() { return ({ node, view, getPos }) => new EmbeddedTableView(node, view, getPos); },
    addProseMirrorPlugins() {
      return [...(this.parent?.() ?? []), new Plugin({ view() { return {
        update(view, previous) {
          if (view.state.doc !== previous.doc) view.dom.dispatchEvent(new Event(EMBEDDED_TABLE_CONTEXT_UPDATE));
        },
      }; } })];
    },
  }).configure({
    resizable: false,
    HTMLAttributes: {
      class: "md-table",
    },
  }),
  TableRow,
  TableHeader,
  TableCell,
];
