import type {Editor} from '@tiptap/core';
import type {PlanOriginalAuthoringCapture,PlanAuthoringCapture,PlanPlacementCatalog} from '../../api/planAuthoringReviewApi';
import {canonical} from '../../shared/sourcePassageProtocol';
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


export function planRootBoundaryPosition(editor:Editor,index:number):number {
  const doc=editor.state.doc;
  if(!Number.isSafeInteger(index)||index<0||index>doc.childCount
    ||index>0&&isTableCaptionAt(doc.toJSON().content??[],index-1))
    throw new PlanPlacementError('The location is not an indivisible page boundary.');
  if(index===doc.childCount)return doc.content.size;
  let position:number|undefined;
  doc.forEach((_node,offset,rootIndex)=>{if(rootIndex===index)position=offset;});
  if(position===undefined)throw new PlanPlacementError('The page boundary is unavailable.');
  return position;
}
async function digest(value:unknown) {
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(value)));
  return Array.from(new Uint8Array(hash),byte=>byte.toString(16).padStart(2,'0')).join('');
}
export async function capturePlanPlacementCatalog(editor:Editor,original:PlanOriginalAuthoringCapture):Promise<PlanPlacementCatalog> {
  const options=compilePlanPlacementOptions(editor,original.editor_json,original.target_kind);
  const entries=await Promise.all(options.map(async option=>{
    const target:PlanAuthoringCapture=option.kind==='captured_target'?original:{...original,
      schema:'dmb_plan_authoring_boundary_capture_v1',target_kind:'insert_at_boundary',
      root_boundary:option.root_boundary!,from:option.position!,to:option.position!};
    return {...option,target_capture_sha256:await digest(target)};
  }));
  const originalHash=await digest(original);
  // Hashing can yield: retain the exact Send-time selection and snapshot.
  if(JSON.stringify(editor.getJSON())!==original.editor_json
    ||JSON.stringify(editor.state.selection.toJSON())!==original.selection_json)
    throw new PlanPlacementError('The page or selection changed while capturing its locations.');
  return {schema:'dmb_plan_placement_catalog_v1',original_capture_sha256:originalHash,
    editor_sha256:original.editor_sha256,entries};
}
