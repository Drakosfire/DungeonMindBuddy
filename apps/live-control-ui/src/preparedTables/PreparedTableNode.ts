import {Node} from '@tiptap/core';
import type {DOMOutputSpec} from '@tiptap/pm/model';
import {parseTableFence} from './tableGrammar';

/** Atomic visual projection; edit the original typed block in normal Markdown mode. */
export const PreparedTableNode=Node.create({
  name:'preparedTable',group:'block',atom:true,selectable:true,
  addAttributes(){return {source:{default:'',rendered:false}};},
  parseHTML(){return [];},
  renderHTML({node}):DOMOutputSpec {
    const table=parseTableFence(String(node.attrs.source));
    return ['section',{'data-prepared-table':table.table_id},
      ['h4',{},`${table.title} · d${table.die_sides}`],
      ['table',{},['tbody',{},...table.rows.map(row=>['tr',{},
        ['th',{},row.min===row.max?String(row.min):`${row.min}–${row.max}`],['td',{},row.outcome]] as DOMOutputSpec)]],
      ['small',{},'Prepared table · edit in Markdown']];
  },
});
