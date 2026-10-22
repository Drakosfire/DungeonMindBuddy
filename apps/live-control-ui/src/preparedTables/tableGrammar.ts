/** Explicit authored tables. Kept separate from numeric-table preview and RNG. */
export const TABLE_LANGUAGE = 'dmb-roll-table-v1';
export type PreparedRow = {row_id:string; min:number; max:number; outcome:string};
export type PreparedTable = {schema_version:'dmb_roll_table_v1';table_id:string;title:string;die_sides:number;rows:PreparedRow[]};

// JSON.parse alone silently accepts duplicate object keys. Scan its already valid
// JSON tokens recursively to reject them before projecting into the shared editor.
function uniqueKeys(raw:string) {
  const tokens=raw.match(/"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null|[{}\[\],:]/g) ?? [];
  let pos=0;
  function value():void {
    const token=tokens[pos++];
    if(token==='{') {
      const keys=new Set<string>();
      while(tokens[pos]!=='}') {
        const key=JSON.parse(tokens[pos++]) as string;
        if(keys.has(key))throw new Error('Duplicate JSON key');
        keys.add(key); pos++; value();
        if(tokens[pos]!==',')break;
        pos++;
      }
      pos++;
    } else if(token==='[') {
      while(tokens[pos]!==']') {value();if(tokens[pos]!==',')break;pos++;}
      pos++;
    }
  }
  value();
}
function exactKeys(value:unknown, keys:string[]):value is Record<string,unknown> {
  return value!==null && typeof value==='object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',')===keys.sort().join(',');
}
export function parseTableJson(raw:string):PreparedTable {
  const table:unknown=JSON.parse(raw); uniqueKeys(raw);
  if(!exactKeys(table,['schema_version','table_id','title','die_sides','rows'])
    ||table.schema_version!=='dmb_roll_table_v1'||typeof table.table_id!=='string'
    ||!/^table:[a-z0-9][a-z0-9._-]{0,127}$/.test(table.table_id)
    ||typeof table.title!=='string'||!table.title.trim()
    ||typeof table.die_sides!=='number'||!Number.isSafeInteger(table.die_sides)||table.die_sides<2
    ||!Array.isArray(table.rows))throw new Error('Invalid prepared table');
  let next=1;const ids=new Set<string>();
  for(const row of table.rows) {
    if(!exactKeys(row,['row_id','min','max','outcome'])||typeof row.row_id!=='string'
      ||!/^row:[a-z0-9][a-z0-9._-]{0,127}$/.test(row.row_id)||ids.has(row.row_id)
      ||typeof row.min!=='number'||!Number.isSafeInteger(row.min)||row.min!==next
      ||typeof row.max!=='number'||!Number.isSafeInteger(row.max)||row.max<row.min||row.max>table.die_sides
      ||typeof row.outcome!=='string'||!row.outcome.trim())throw new Error('Invalid prepared-table rows');
    ids.add(row.row_id);next=row.max+1;
  }
  if(next!==table.die_sides+1)throw new Error('Rows must cover the whole die');
  return table as PreparedTable;
}

export function parseTableFence(raw:string):PreparedTable {
  const lines=raw.split('\n');
  const start=/^ {0,3}(`{3,}|~{3,})dmb-roll-table-v1[ \t]*$/.exec(lines[0]);
  if(!start||!new RegExp('^ {0,3}'+start[1][0]+'{'+start[1].length+',}[ \\t]*$').test(lines.at(-1)??''))throw new Error('Unterminated prepared table');
  return parseTableJson(lines.slice(1,-1).join('\n'));
}
