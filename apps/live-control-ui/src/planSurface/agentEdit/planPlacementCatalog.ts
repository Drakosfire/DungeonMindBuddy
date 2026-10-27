import type {Editor} from '@tiptap/core';
import {isTableCaptionAt} from '../../tiptap/markdown/tableCaption';

/** Navigation over one frozen editor snapshot. Positions never enter model state. */
export interface PlanPlacementOption {
  selector: string;
  kind: 'captured_target'|'before_heading'|'after_section'|'end_page';
  label: string;
  root_boundary: number|null;
  position: number|null;
}
export class PlanPlacementError extends Error {}

type Heading = {index:number;level:number;text:string;path:string};

export function compilePlanPlacementOptions(
  editor:Editor, editorJson:string, targetKind:'insert_at_caret'|'replace_selection'|'replace_playable_body',
):readonly PlanPlacementOption[] {
  if(JSON.stringify(editor.getJSON())!==editorJson)
    throw new PlanPlacementError('The page changed before its locations could be captured.');
  const current:PlanPlacementOption={selector:'captured',kind:'captured_target',
    label:targetKind==='insert_at_caret'?'At the captured text caret'
      :targetKind==='replace_selection'?'Replace only the captured selection':'Replace only the captured playable body',
    root_boundary:null,position:null};
  // An explicit replacement never offers broader insertion authority.
  if(targetKind!=='insert_at_caret')return Object.freeze([Object.freeze(current)]);
  const doc=editor.state.doc,content=doc.toJSON().content??[];
  const offsets:number[]=[],headings:Heading[]=[],ancestors:Heading[]=[];
  doc.forEach((node,position,index)=>{
    offsets[index]=position;
    if(node.type.name!=='heading'||isTableCaptionAt(content,index))return;
    const level=Number(node.attrs.level),text=node.textContent.trim();
    if(!Number.isInteger(level)||level<1||level>6||!text)return;
    while(ancestors.length&&ancestors.at(-1)!.level>=level)ancestors.pop();
    const heading={index,level,text,path:[...ancestors.map(row=>row.text),text].join(' / ')};
    headings.push(heading);ancestors.push(heading);
  });
  offsets[doc.childCount]=doc.content.size;
  const totals=new Map<string,number>(),seen=new Map<string,number>();
  for(const heading of headings)totals.set(heading.path,(totals.get(heading.path)??0)+1);
  const options:PlanPlacementOption[]=[current];
  headings.forEach((heading,index)=>{
    const ordinal=(seen.get(heading.path)??0)+1;seen.set(heading.path,ordinal);
    const total=totals.get(heading.path)??1;
    const label=heading.path+(total>1?` · ${ordinal} of ${total}`:'');
    const end=headings.slice(index+1).find(next=>next.level<=heading.level)?.index??doc.childCount;
    options.push({selector:`before:${heading.index}`,kind:'before_heading',label:`Before ${label}`,
      root_boundary:heading.index,position:offsets[heading.index]!});
    options.push({selector:`after:${heading.index}`,kind:'after_section',label:`After the entire section ${label}`,
      root_boundary:end,position:offsets[end]!});
  });
  options.push({selector:'end',kind:'end_page',label:'At the end of the page',
    root_boundary:doc.childCount,position:doc.content.size});
  return Object.freeze(options.map(option=>Object.freeze(option)));
}

/** Recompute from the matching live editor; never trust a returned numeric offset. */
export function resolvePlanPlacementOption(
  editor:Editor,editorJson:string,targetKind:'insert_at_caret'|'replace_selection'|'replace_playable_body',
  offered:PlanPlacementOption,
):PlanPlacementOption {
  const actual=compilePlanPlacementOptions(editor,editorJson,targetKind).find(row=>row.selector===offered.selector);
  if(!actual||actual.kind!==offered.kind||actual.label!==offered.label
    ||actual.root_boundary!==offered.root_boundary||actual.position!==offered.position)
    throw new PlanPlacementError('The offered page location no longer identifies this captured boundary.');
  return actual;
}

/** Deliberately excludes editor positions, root indices and target digests. */
export function planPlacementModelChoices(options:readonly PlanPlacementOption[]) {
  return options.map(({selector,label})=>({selector,label}));
}
